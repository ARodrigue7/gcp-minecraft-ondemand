import functions_framework
import os
import time
import json
import urllib.request
import re
import hmac
from config import (
    validate_config,
    PROJECT_ID,
    ZONE,
    INSTANCE_NAME,
    DOMAIN_NAME,
    DISCORD_WEBHOOK_URL,
    ADMIN_PASSCODE,
    logger
)
from templates import get_whitelist_approved_html, get_whitelist_denied_html
from gcp_client import (
    compute,
    get_instance_status_and_ip,
    start_instance,
    update_dns_record,
    is_minecraft_ready,
    get_backups_list,
    download_backup_file,
    get_minecraft_logs
)
from discord_auth import generate_signature
from admin_auth import check_admin_auth
from whitelist_manager import (
    add_to_gce_metadata_whitelist,
    remove_from_gce_metadata_whitelist,
    enqueue_admin_command,
    add_to_gce_metadata_pending,
    remove_from_gce_metadata_pending,
    update_whitelist_state,
    get_whitelist_sets
)
from discord_webhook import send_discord_webhook

# Validate configuration on module loading to fail fast
validate_config()

def get_cors_headers(request, for_preflight=False):
    allowed_origins_str = os.environ.get('ALLOWED_ORIGINS', '*')
    request_origin = request.headers.get('Origin', '')
    
    if allowed_origins_str == '*':
        allow_origin = '*'
    else:
        allowed_origins = [o.strip() for o in allowed_origins_str.split(',')]
        allow_origin = request_origin if request_origin in allowed_origins else allowed_origins[0]

    if for_preflight:
        return {
            'Access-Control-Allow-Origin': allow_origin,
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-User',
            'Access-Control-Max-Age': '3600'
        }
    else:
        return {
            'Access-Control-Allow-Origin': allow_origin,
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-User',
            'Content-Type': 'application/json'
        }

@functions_framework.cloud_event
def start_minecraft(cloudevent):
    """Cloud Function entry point triggered by Pub/Sub event."""
    logger.info("Received DNS query event trigger. Checking Minecraft VM...")
    
    status, ip = get_instance_status_and_ip()
    logger.info(f"Current VM state: {status}, IP: {ip}")
    
    # If the VM is stopped, start it
    if status == 'TERMINATED':
        logger.info(f"Starting VM: {INSTANCE_NAME}...")
        start_instance()
        # We do not block here; DNS will be updated by the next HTTP status check poll
    elif status != 'RUNNING':
        logger.info(f"VM is in state '{status}'. Waiting for transition to 'RUNNING'...")
    else:
        # Update DNS if IP is available and VM is RUNNING
        if ip:
            update_dns_record(ip)
        else:
            logger.error("VM is running but does not have a public IP address.")

@functions_framework.http
def get_status_http(request):
    """HTTP Cloud Function that retrieves VM status, handles whitelist submissions, and approves players."""
    # Set CORS headers for preflight request
    if request.method == 'OPTIONS':
        headers = get_cors_headers(request, for_preflight=True)
        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = get_cors_headers(request, for_preflight=False)

    # Handle Admin endpoints
    action = request.args.get('action')
    if action in ['admin_status', 'admin_logs', 'admin_command', 'admin_whitelist_add', 'admin_whitelist_remove', 'admin_download_backup', 'admin_power']:
        is_auth = False
        if action == 'admin_download_backup':
            passcode = request.args.get('passcode')
            username = request.args.get('username')
            is_auth = False
            if passcode and username and hmac.compare_digest(passcode, ADMIN_PASSCODE):
                approved_set, _ = get_whitelist_sets()
                if username.lower() in approved_set:
                    is_auth = True
        else:
            is_auth = check_admin_auth(request)
            
        if not is_auth:
            return (json.dumps({"error": "Unauthorized"}), 401, headers)
            
        if request.method == 'GET':
            if action == 'admin_status':
                try:
                    vm = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME).execute()
                    
                    status = vm.get('status')
                    ip = None
                    network_interfaces = vm.get('networkInterfaces', [])
                    if network_interfaces:
                        access_configs = network_interfaces[0].get('accessConfigs', [])
                        if access_configs:
                            ip = access_configs[0].get('natIP')
                            
                    if status == 'RUNNING' and ip:
                        try:
                            update_dns_record(ip)
                        except Exception as dns_err:
                            print(f"Error updating DNS in admin status: {dns_err}")
                    
                    metadata = vm.get('metadata', {})
                    items = metadata.get('items', [])
                    
                    players_item = next((item for item in items if item['key'] == 'online-players'), None)
                    online_players = players_item['value'] if players_item else "none"
                    
                    whitelist_item = next((item for item in items if item['key'] == 'approved-whitelist'), None)
                    approved_whitelist = whitelist_item['value'] if whitelist_item else ""
                    
                    backups = get_backups_list()
                    
                    return (
                        json.dumps({
                            "status": status,
                            "ip": ip,
                            "online_players": online_players,
                            "whitelist": [p.strip() for p in approved_whitelist.split(',') if p.strip()],
                            "backups": backups
                        }),
                        200,
                        headers
                    )
                except Exception as e:
                    print(f"Error loading admin status: {e}")
                    return (json.dumps({"error": str(e)}), 500, headers)
                    
            elif action == 'admin_logs':
                logs = get_minecraft_logs()
                return (json.dumps({"logs": logs}), 200, headers)
                
            elif action == 'admin_download_backup':
                generation = request.args.get('generation')
                if not generation:
                    return ("Missing generation parameter", 400)
                file_content, code, custom_headers = download_backup_file(generation)
                if code == 200:
                    merged_headers = {**headers, **custom_headers}
                    return (file_content, code, merged_headers)
                else:
                    return (file_content, code, headers)
                    
        elif request.method == 'POST':
            try:
                request_json = request.get_json(silent=True) or {}
                
                if action == 'admin_command':
                    command = request_json.get('command')
                    if not command:
                        return (json.dumps({"error": "Missing command in payload"}), 400, headers)
                    
                    enqueue_admin_command(command)
                    return (json.dumps({"success": True, "message": f"Command '{command}' enqueued successfully."}), 200, headers)
                    
                elif action == 'admin_whitelist_add':
                    username = request_json.get('username')
                    if not username:
                        return (json.dumps({"error": "Missing username in payload"}), 400, headers)
                    
                    # Single atomic call for approved-whitelist addition, pending-whitelist removal, and command enqueuing
                    update_whitelist_state(username, 'approve', enqueue_cmd=f"whitelist add {username}")
                    return (json.dumps({"success": True, "message": f"Player '{username}' added to whitelist."}), 200, headers)
                    
                elif action == 'admin_whitelist_remove':
                    username = request_json.get('username')
                    if not username:
                        return (json.dumps({"error": "Missing username in payload"}), 400, headers)
                    
                    # Single atomic call for approved-whitelist removal and command enqueuing
                    update_whitelist_state(username, 'remove', enqueue_cmd=f"whitelist remove {username}")
                    return (json.dumps({"success": True, "message": f"Player '{username}' removed from whitelist."}), 200, headers)
                    
                elif action == 'admin_power':
                    command = request_json.get('command')
                    if not command:
                        return (json.dumps({"error": "Missing command in payload"}), 400, headers)
                    
                    if command == 'start':
                        print(f"Admin starting VM: {INSTANCE_NAME}...")
                        start_instance()
                        return (json.dumps({"success": True, "message": "VM startup initiated."}), 200, headers)
                    elif command == 'stop':
                        print(f"Admin stopping VM: {INSTANCE_NAME}...")
                        compute.instances().stop(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME).execute()
                        return (json.dumps({"success": True, "message": "VM shutdown initiated."}), 200, headers)
                    elif command == 'restart':
                        print(f"Admin restarting VM: {INSTANCE_NAME}...")
                        compute.instances().reset(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME).execute()
                        return (json.dumps({"success": True, "message": "VM restart initiated."}), 200, headers)
                    else:
                        return (json.dumps({"error": f"Invalid power command: {command}"}), 400, headers)
                    
            except Exception as e:
                print(f"Error handling admin post request: {e}")
                return (json.dumps({"error": str(e)}), 500, headers)

    if request.method == 'GET':
        action = request.args.get('action')
        
        # Whitelist Approval Flow (GET link clicked from Discord)
        if action == 'approve':
            username = request.args.get('username')
            sig = request.args.get('sig')
            message_id = request.args.get('message_id')
            
            if not username or not sig:
                return ("Missing 'username' or 'sig' query parameters.", 400)
                
            try:
                # Cryptographically verify signature
                expected_sig = generate_signature(username)
                if not hmac.compare_digest(sig, expected_sig):
                    logger.warning(f"HMAC validation failed for GET whitelist approval link (username: {username}).")
                    return ("Authentication failed: Invalid signature.", 403)
                
                # Append to GCE VM approved-whitelist metadata and remove from pending (done atomically inside wrapper)
                add_to_gce_metadata_whitelist(username)
                
                # Delete the Discord webhook message to keep the channel clean
                if message_id:
                    try:
                        if DISCORD_WEBHOOK_URL:
                            delete_url = f"{DISCORD_WEBHOOK_URL}/messages/{message_id}"
                            del_req = urllib.request.Request(
                                delete_url,
                                method='DELETE',
                                headers={'User-Agent': 'GCP-Minecraft-On-Demand-Webhook'}
                            )
                            with urllib.request.urlopen(del_req) as del_resp:
                                pass
                    except Exception as e:
                        logger.error(f"Failed to delete Discord message: {e}")
                
                # Return confirmation landing page HTML from templates module
                html = get_whitelist_approved_html(username)
                return (html, 200, {'Content-Type': 'text/html'})
            except Exception as e:
                logger.error(f"Error handling whitelist approval: {e}")
                return (f"Failed to process approval: {str(e)}", 500)

        # Whitelist Denial/Dismiss Flow (GET link clicked from Discord)
        elif action == 'deny':
            username = request.args.get('username')
            sig = request.args.get('sig')
            message_id = request.args.get('message_id')
            
            if not username or not sig:
                return ("Missing 'username' or 'sig' query parameters.", 400)
                
            try:
                # Cryptographically verify signature
                expected_sig = generate_signature(username)
                if not hmac.compare_digest(sig, expected_sig):
                    logger.warning(f"HMAC validation failed for GET whitelist deny link (username: {username}).")
                    return ("Authentication failed: Invalid signature.", 403)
                # Remove from GCE VM pending-whitelist metadata
                remove_from_gce_metadata_pending(username)
                
                # Delete the Discord webhook message to keep the channel clean
                if message_id:
                    try:
                        if DISCORD_WEBHOOK_URL:
                            delete_url = f"{DISCORD_WEBHOOK_URL}/messages/{message_id}"
                            del_req = urllib.request.Request(
                                delete_url,
                                method='DELETE',
                                headers={'User-Agent': 'GCP-Minecraft-On-Demand-Webhook'}
                            )
                            with urllib.request.urlopen(del_req) as del_resp:
                                pass
                    except Exception as e:
                        logger.error(f"Failed to delete Discord message on deny: {e}")
                
                # Return denied landing page HTML from templates module
                html = get_whitelist_denied_html(username)
                return (html, 200, {'Content-Type': 'text/html'})
            except Exception as e:
                logger.error(f"Error handling whitelist deny: {e}")
                return (f"Failed to process deny request: {str(e)}", 500)

        # Standard GET Status checking
        try:
            status, ip = get_instance_status_and_ip()
            
            # If GCE VM is RUNNING, check if the Minecraft container is actually listening yet
            if status == 'RUNNING' and ip:
                try:
                    update_dns_record(ip)
                except Exception as dns_err:
                    print(f"Error updating DNS in standard status: {dns_err}")
                
                if not is_minecraft_ready(ip):
                    status = 'STARTING' # Override status so UI waits

            return (
                json.dumps({
                    "status": status,
                    "ip": ip if status == 'RUNNING' else None,
                    "domain": DOMAIN_NAME
                }),
                200,
                headers
            )
        except Exception as e:
            logger.error(f"Error fetching VM status: {e}")
            return (json.dumps({"error": str(e)}), 500, headers)

    elif request.method == 'POST':
        try:
            request_json = request.get_json(silent=True)
            if not request_json:
                return (json.dumps({"error": "Missing request payload."}), 400, headers)

            action = request_json.get('action')

            # 1. Wake Up / Start Server action
            if action == 'start':
                passcode = request_json.get('passcode')
                username = request_json.get('username')
                

                # Enforce Minecraft username check
                if not username:
                    return (json.dumps({"error": "Missing Minecraft username. Wake up request denied."}), 400, headers)
                
                # Verify that the player is whitelisted
                approved_set, _ = get_whitelist_sets()
                if username.lower() not in approved_set:
                    return (json.dumps({"error": f"Player '{username}' is not whitelisted. Wake up request denied."}), 403, headers)
                
                # Check status and start if stopped
                status, ip = get_instance_status_and_ip()
                if status == 'TERMINATED':
                    print(f"Starting GCE instance {INSTANCE_NAME} via HTTP start command...")
                    start_instance()
                    return (json.dumps({"success": True, "message": "Server startup initiated successfully."}), 200, headers)
                else:
                    return (json.dumps({"success": True, "message": f"Server is already in state: {status}."}), 200, headers)

            # 2. Whitelist Request (default if action is not start)
            if 'username' not in request_json:
                return (json.dumps({"error": "Missing 'username' or 'action' in request payload."}), 400, headers)

            username = request_json['username'].strip()
            if not username:
                return (json.dumps({"error": "Username cannot be empty."}), 400, headers)

            # Validate username is standard Minecraft alphanumeric + underscores (3-16 chars)
            if not re.match(r'^[a-zA-Z0-9_]{3,16}$', username):
                return (json.dumps({"error": "Invalid Minecraft username format. Usernames must be 3-16 characters long and contain only letters, numbers, and underscores."}), 400, headers)

            # Fetch approved and pending lists to prevent duplicate requests
            approved_set, pending_set = get_whitelist_sets()
            
            username_lower = username.lower()
            
            if username_lower in approved_set:
                return (json.dumps({
                    "success": True, 
                    "status": "approved", 
                    "message": f"'{username}' is already whitelisted! You can connect to the server."
                }), 200, headers)
                
            if username_lower in pending_set:
                return (json.dumps({
                    "success": True, 
                    "status": "pending", 
                    "message": f"A whitelist request for '{username}' is already pending approval from the administrator."
                }), 200, headers)
            
            # Add to GCE VM pending-whitelist metadata
            add_to_gce_metadata_pending(username)

            # Send whitelist request to Discord with the signature base URL
            status_url = request.base_url
            if status_url.endswith('/'):
                status_url = status_url[:-1]
            success = send_discord_webhook(username, status_url)
            if success:
                return (json.dumps({
                    "success": True,
                    "status": "submitted",
                    "message": f"Whitelist request for '{username}' submitted successfully! Please wait for the administrator to approve it."
                }), 200, headers)
            else:
                # If webhook fails, clean up the pending state so they can try again later
                try:
                    remove_from_gce_metadata_pending(username)
                except Exception as cleanup_err:
                    logger.error(f"Failed to clean up pending list after webhook failure: {cleanup_err}")
                return (json.dumps({"error": "Failed to route whitelist request. Please contact the administrator directly."}), 500, headers)

        except Exception as e:
            logger.error(f"Error handling whitelist request: {e}")
            return (json.dumps({"error": str(e)}), 500, headers)

    else:
        return (json.dumps({"error": "Method not allowed."}), 405, headers)
