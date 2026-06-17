import time
import json
import urllib.request
import re
import hmac
from config import validate_config, PROJECT_ID, ZONE, INSTANCE_NAME, FUNCTION_REGION, DISCORD_WEBHOOK_URL, logger
from templates import get_whitelist_approved_html
from gcp_client import get_instance_status_and_ip, start_instance, update_dns_record
from discord_auth import verify_discord_signature
from discord_webhook import generate_signature, send_discord_webhook
from whitelist_manager import add_to_gce_metadata_whitelist

# Validate configuration on module loading to fail fast
validate_config()

def start_minecraft(event, context):
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

def get_status_http(request):
    """HTTP Cloud Function that retrieves VM status, handles whitelist submissions, and approves players."""
    # Set CORS headers for preflight request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

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
            if not request_json or 'username' not in request_json:
                return (json.dumps({"error": "Missing 'username' in request payload."}), 400, headers)

            username = request_json['username'].strip()
            if not username:
                return (json.dumps({"error": "Username cannot be empty."}), 400, headers)

            # Validate username is standard Minecraft alphanumeric + underscores (3-16 chars)
            if not re.match(r'^[a-zA-Z0-9_]{3,16}$', username):
                return (json.dumps({"error": "Invalid Minecraft username format. Usernames must be 3-16 characters long and contain only letters, numbers, and underscores."}), 400, headers)

            # Send whitelist request to Discord with the signature base URL
            status_url = f"https://{FUNCTION_REGION}-{PROJECT_ID}.cloudfunctions.net/minecraft-status"
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
