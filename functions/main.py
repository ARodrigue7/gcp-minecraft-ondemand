import functions_framework
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
    WAKEUP_PASSCODE,
    ADMIN_PASSCODE,
    logger
)
from templates import get_whitelist_approved_html
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
from discord_auth import (
    verify_discord_signature,
    generate_signature
)
from admin_auth import check_admin_auth
from whitelist_manager import (
    add_to_gce_metadata_whitelist,
    remove_from_gce_metadata_whitelist,
    enqueue_admin_command
)
from discord_webhook import send_discord_webhook

# Validate configuration on module loading to fail fast
validate_config()

@functions_framework.cloud_event
def start_minecraft(cloudevent):
    """Cloud Function entry point triggered by Pub/Sub event."""
    logger.info("Received DNS query event trigger. Checking Minecraft VM...")
    
    status, ip = get_instance_status_and_ip()
    logger.info(f"Current VM state: {status}, IP: {ip}")
    
    # If the VM is stopped, start it and wait for IP
    if status == 'TERMINATED':
        logger.info(f"Starting VM: {INSTANCE_NAME}...")
        start_instance()
        
        # Poll VM until it is RUNNING and has a public IP
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)
            status, ip = get_instance_status_and_ip()
            logger.info(f"Polling VM status ({attempt + 1}/{max_attempts}): status={status}, IP={ip}")
            if status == 'RUNNING' and ip:
                break
        else:
            raise Exception("Timeout waiting for VM to start and obtain an IP address.")
            
    # If the VM is in any other transitioning state (e.g. PROVISIONING), wait for it to be RUNNING
    elif status != 'RUNNING':
        logger.info(f"VM is in state '{status}'. Waiting for transition to 'RUNNING'...")
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)
            status, ip = get_instance_status_and_ip()
            logger.info(f"Polling VM status ({attempt + 1}/{max_attempts}): status={status}, IP={ip}")
            if status == 'RUNNING' and ip:
                break
        else:
            raise Exception("Timeout waiting for VM to transition to RUNNING.")
            
    # Update DNS if IP is available
    if ip:
        update_dns_record(ip)
    else:
        logger.error("VM is running but does not have a public IP address.")

@functions_framework.http
def get_status_http(request):
    """HTTP Cloud Function that retrieves VM status, handles whitelist submissions, and approves players."""
    # Set CORS headers for preflight request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

    # Handle Admin endpoints
    action = request.args.get('action')
    if action in ['admin_status', 'admin_logs', 'admin_command', 'admin_whitelist_remove', 'admin_download_backup', 'admin_power']:
        is_auth = False
        if action == 'admin_download_backup':
            passcode = request.args.get('passcode')
            is_auth = (passcode == ADMIN_PASSCODE)
        else:
            is_auth = check_admin_auth(request)
            
        if not is_auth:
            return (json.dumps({"error": "Unauthorized"}), 401, headers)
            
        if request.method == 'GET':
            if action == 'admin_status':
                try:
                    status, ip = get_instance_status_and_ip()
                    
                    if status == 'RUNNING' and ip:
                        try:
                            update_dns_record(ip)
                        except Exception as dns_err:
                            print(f"Error updating DNS in admin status: {dns_err}")
                    
                    vm = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME).execute()
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
                    
                elif action == 'admin_whitelist_remove':
                    username = request_json.get('username')
                    if not username:
                        return (json.dumps({"error": "Missing username in payload"}), 400, headers)
                    
                    remove_from_gce_metadata_whitelist(username)
                    enqueue_admin_command(f"whitelist remove {username}")
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

    # Parse and verify Discord Interaction signature headers
    signature = request.headers.get('X-Signature-Ed25519')
    timestamp = request.headers.get('X-Signature-Timestamp')
    
    if signature and timestamp:
        body_str = request.get_data(as_text=True)
        if not verify_discord_signature(signature, timestamp, body_str):
            return ("Invalid request signature", 401)
            
        try:
            interaction = json.loads(body_str)
        except Exception as e:
            logger.error(f"Invalid interaction JSON payload: {e}")
            return ("Invalid JSON payload", 400)
            
        inter_type = interaction.get('type')
        
        # type = 1 is PING (Verification request)
        if inter_type == 1:
            return (json.dumps({"type": 1}), 200, {'Content-Type': 'application/json'})
            
        # type = 3 is Message Component (Button click)
        elif inter_type == 3:
            data = interaction.get('data', {})
            custom_id = data.get('custom_id', '')
            
            if not custom_id:
                return ("Missing custom_id", 400)
                
            try:
                parts = custom_id.split(':')
                if len(parts) != 3:
                    return ("Invalid custom_id format", 400)
                    
                action, username, sig = parts
                
                # Verify HMAC signature
                expected_sig = generate_signature(username)
                if not hmac.compare_digest(sig, expected_sig):
                    logger.warning(f"Unauthorized component action for {username} - HMAC mismatch.")
                    return ("Unauthorized action", 403)
                    
                if action == 'approve_whitelist':
                    add_to_gce_metadata_whitelist(username)
                    
                    approver = "Unknown Admin"
                    member = interaction.get('member')
                    if member and 'user' in member:
                        approver = member['user'].get('username', approver)
                    elif 'user' in interaction:
                        approver = interaction['user'].get('username', approver)
                        
                    response_payload = {
                        "type": 7,  # UPDATE_MESSAGE
                        "data": {
                            "content": f"✓ **{username}** has been approved and whitelisted by **@{approver}**!",
                            "embeds": [],
                            "components": []  # Removes the buttons!
                        }
                    }
                    return (json.dumps(response_payload), 200, {'Content-Type': 'application/json'})
                    
                elif action == 'deny_whitelist':
                    denier = "Unknown Admin"
                    member = interaction.get('member')
                    if member and 'user' in member:
                        denier = member['user'].get('username', denier)
                    elif 'user' in interaction:
                        denier = interaction['user'].get('username', denier)
                        
                    response_payload = {
                        "type": 7,  # UPDATE_MESSAGE
                        "data": {
                            "content": f"✗ Whitelist request for **{username}** was denied by **@{denier}**.",
                            "embeds": [],
                            "components": []
                        }
                    }
                    return (json.dumps(response_payload), 200, {'Content-Type': 'application/json'})
                    
                else:
                    return ("Invalid action", 400)
            except Exception as e:
                logger.error(f"Error processing interaction component: {e}")
                return (f"Internal error: {str(e)}", 500)
                
        return ("Unknown interaction type", 400)

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
                
                # Append to GCE VM approved-whitelist metadata
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
                
                # Enforce passcode check if configured
                if WAKEUP_PASSCODE and passcode != WAKEUP_PASSCODE:
                    return (json.dumps({"error": "Invalid passcode. Wake up request denied."}), 403, headers)
                
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

            # Send whitelist request to Discord with the signature base URL
            status_url = request.base_url
            if status_url.endswith('/'):
                status_url = status_url[:-1]
            success = send_discord_webhook(username, status_url)
            if success:
                return (json.dumps({"success": True, "message": f"Whitelist request for '{username}' sent successfully to the server administrator!"}), 200, headers)
            else:
                return (json.dumps({"error": "Failed to route whitelist request. Please contact the administrator directly."}), 500, headers)

        except Exception as e:
            logger.error(f"Error handling whitelist request: {e}")
            return (json.dumps({"error": str(e)}), 500, headers)

    else:
        return (json.dumps({"error": "Method not allowed."}), 405, headers)
