import os
import time
import json
import urllib.request
import re
import hmac
import hashlib
from googleapiclient import discovery

# Read configuration from environment variables
PROJECT_ID = os.environ.get('PROJECT_ID')
ZONE = os.environ.get('ZONE')
INSTANCE_NAME = os.environ.get('INSTANCE_NAME')
DNS_ZONE_NAME = os.environ.get('DNS_ZONE_NAME')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME')
WHITELIST_SECRET = os.environ.get('WHITELIST_SECRET')
FUNCTION_REGION = os.environ.get('FUNCTION_REGION', 'us-central1')

# Build the client services
# cache_discovery=False prevents file-locking warnings in read-only environments
compute = discovery.build('compute', 'v1', cache_discovery=False)
dns = discovery.build('dns', 'v1', cache_discovery=False)

def get_instance_status_and_ip():
    """Retrieves the current status and public IP address of the VM instance."""
    request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    response = request.execute()
    status = response.get('status')
    
    ip = None
    network_interfaces = response.get('networkInterfaces', [])
    if network_interfaces:
        access_configs = network_interfaces[0].get('accessConfigs', [])
        if access_configs:
            ip = access_configs[0].get('natIP')
            
    return status, ip

def start_instance():
    """Triggers the start request for the VM instance."""
    request = compute.instances().start(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    return request.execute()

def update_dns_record(new_ip):
    """Updates the Cloud DNS A-record to point to the new IP address."""
    # Ensure domain ends with a period for Cloud DNS API
    record_name = f"{DOMAIN_NAME}." if not DOMAIN_NAME.endswith('.') else DOMAIN_NAME
    
    # Check current DNS record
    request = dns.resourceRecordSets().list(
        project=PROJECT_ID,
        managedZone=DNS_ZONE_NAME,
        name=record_name,
        type='A'
    )
    response = request.execute()
    records = response.get('rrsets', [])
    
    old_ip = None
    existing_record = None
    if records:
        existing_record = records[0]
        rrdatas = existing_record.get('rrdatas', [])
        if rrdatas:
            old_ip = rrdatas[0]
            
    # If the record already points to the correct IP, we skip the update
    if old_ip == new_ip:
        print(f"DNS record for {record_name} already matches new IP {new_ip}. No update needed.")
        return
        
    change_body = {}
    additions = [
        {
            "name": record_name,
            "type": "A",
            "ttl": 60,  # 60s TTL to speed up propagation
            "rrdatas": [new_ip]
        }
    ]
    deletions = []
    
    if existing_record:
        deletions.append(existing_record)
        
    change_body["additions"] = additions
    if deletions:
        change_body["deletions"] = deletions
        
    print(f"Updating DNS for {record_name}: changing from {old_ip} to {new_ip}")
    request = dns.changes().create(
        project=PROJECT_ID,
        managedZone=DNS_ZONE_NAME,
        body=change_body
    )
    request.execute()

def start_minecraft(event, context):
    """Cloud Function entry point triggered by Pub/Sub event."""
    print("Received DNS query event trigger. Checking Minecraft VM...")
    
    status, ip = get_instance_status_and_ip()
    print(f"Current VM state: {status}, IP: {ip}")
    
    # If the VM is stopped, start it and wait for IP
    if status == 'TERMINATED':
        print(f"Starting VM: {INSTANCE_NAME}...")
        start_instance()
        
        # Poll VM until it is RUNNING and has a public IP
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)
            status, ip = get_instance_status_and_ip()
            print(f"Polling VM status ({attempt + 1}/{max_attempts}): status={status}, IP={ip}")
            if status == 'RUNNING' and ip:
                break
        else:
            raise Exception("Timeout waiting for VM to start and obtain an IP address.")
            
    # If the VM is in any other transitioning state (e.g. PROVISIONING), wait for it to be RUNNING
    elif status != 'RUNNING':
        print(f"VM is in state '{status}'. Waiting for transition to 'RUNNING'...")
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(2)
            status, ip = get_instance_status_and_ip()
            print(f"Polling VM status ({attempt + 1}/{max_attempts}): status={status}, IP={ip}")
            if status == 'RUNNING' and ip:
                break
        else:
            raise Exception("Timeout waiting for VM to transition to RUNNING.")
            
    # Update DNS if IP is available
    if ip:
        update_dns_record(ip)
    else:
        print("Error: VM is running but does not have a public IP address.")

def generate_signature(username):
    """Generates a secure HMAC-SHA256 signature for a username."""
    if not WHITELIST_SECRET:
        raise ValueError("WHITELIST_SECRET is not configured.")
    return hmac.new(WHITELIST_SECRET.encode('utf-8'), username.encode('utf-8'), hashlib.sha256).hexdigest()

def add_to_gce_metadata_whitelist(username):
    """Appends a username to the approved-whitelist metadata attribute on the VM."""
    # 1. Fetch current GCE VM details
    request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    instance = request.execute()
    
    metadata = instance.get('metadata', {})
    items = metadata.get('items', [])
    
    # 2. Locate the approved-whitelist attribute or initialize it
    whitelist_item = next((item for item in items if item['key'] == 'approved-whitelist'), None)
    
    if whitelist_item:
        players = [p.strip() for p in whitelist_item['value'].split(',') if p.strip()]
    else:
        players = []
        
    if username not in players:
        players.append(username)
        
    new_value = ','.join(players)
    
    if whitelist_item:
        whitelist_item['value'] = new_value
    else:
        items.append({'key': 'approved-whitelist', 'value': new_value})
        
    # 3. Save modified metadata back to GCE
    update_request = compute.instances().setMetadata(
        project=PROJECT_ID,
        zone=ZONE,
        instance=INSTANCE_NAME,
        body={
            'fingerprint': metadata.get('fingerprint'),
            'items': items
        }
    )
    update_request.execute()

def send_discord_webhook(username, status_url):
    """Sends a formatted alert about a whitelist request to Discord with a one-click approval link."""
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL environment variable is not configured.")
        return False

    # Generate signature and initial approval link
    sig = generate_signature(username)
    temp_approval_url = f"{status_url}?action=approve&username={username}&sig={sig}"

    payload = {
        "content": None,
        "embeds": [
            {
                "title": "🎮 Whitelist Request Received",
                "description": f"A player has requested access to the Minecraft server.\n\n[🟢 Click here to Approve Whitelist]({temp_approval_url})",
                "color": 5814783, # Purple Accent
                "fields": [
                    {
                        "name": "Minecraft Username",
                        "value": f"**`{username}`**",
                        "inline": True
                    },
                    {
                        "name": "Manual SSH Command",
                        "value": f"```bash\ngcloud compute ssh {INSTANCE_NAME} --zone={ZONE} --command=\"docker exec minecraft mc-send-to-rcon whitelist add {username}\"\n```",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "GCP Minecraft On-Demand Player Hub"
                },
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        ]
    }

    try:
        # 1. Post to webhook with wait=true to get the message ID
        data = json.dumps(payload).encode('utf-8')
        post_url = f"{webhook_url}?wait=true"
        req = urllib.request.Request(
            post_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'GCP-Minecraft-On-Demand-Webhook'
            }
        )
        message_id = None
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode('utf-8')
            if resp_body:
                resp_json = json.loads(resp_body)
                message_id = resp_json.get('id')

        # If we failed to get a message ID, return success (message was still sent)
        if not message_id:
            return True

        # 2. Update approval URL with the real message ID and PATCH the message to edit the link
        real_approval_url = f"{status_url}?action=approve&username={username}&sig={sig}&message_id={message_id}"
        payload["embeds"][0]["description"] = f"A player has requested access to the Minecraft server.\n\n[🟢 Click here to Approve Whitelist]({real_approval_url})"
        
        patch_data = json.dumps(payload).encode('utf-8')
        patch_url = f"{webhook_url}/messages/{message_id}"
        patch_req = urllib.request.Request(
            patch_url,
            data=patch_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'GCP-Minecraft-On-Demand-Webhook'
            },
            method='PATCH'
        )
        with urllib.request.urlopen(patch_req) as patch_response:
            pass

        return True
    except Exception as e:
        print(f"Error executing Discord Webhook: {e}")
        return False

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
                    return ("Authentication failed: Invalid signature.", 403)
                
                # Append to GCE VM approved-whitelist metadata
                add_to_gce_metadata_whitelist(username)
                
                # Delete the Discord webhook message to keep the channel clean
                if message_id:
                    try:
                        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
                        if webhook_url:
                            delete_url = f"{webhook_url}/messages/{message_id}"
                            del_req = urllib.request.Request(
                                delete_url,
                                method='DELETE',
                                headers={'User-Agent': 'GCP-Minecraft-On-Demand-Webhook'}
                            )
                            with urllib.request.urlopen(del_req) as del_resp:
                                pass
                    except Exception as e:
                        print(f"Failed to delete Discord message: {e}")
                
                # Return confirmation landing page
                html = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Whitelist Approved</title>
                    <link rel="preconnect" href="https://fonts.googleapis.com">
                    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                    <style>
                        @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&display=swap');
                        
                        body {{
                            font-family: 'Fredoka', sans-serif;
                            background: radial-gradient(circle at center, #102e1c 0%, #091a10 70%, #040d08 100%);
                            color: #fffbeb;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0;
                            overflow: hidden;
                            position: relative;
                            padding: 1.5rem;
                        }}
                        
                        /* Fireflies animation */
                        .firefly {{
                            position: absolute;
                            width: 6px;
                            height: 6px;
                            background: #fde047;
                            border-radius: 50%;
                            filter: drop-shadow(0 0 4px #fbbf24);
                            opacity: 0;
                            animation: float-glow 8s infinite ease-in-out;
                            pointer-events: none;
                        }}
                        
                        .ff-1 {{ top: 15%; left: 10%; animation-delay: 0s; }}
                        .ff-2 {{ top: 45%; left: 85%; animation-delay: 2s; }}
                        .ff-3 {{ top: 75%; left: 25%; animation-delay: 4.5s; }}
                        .ff-4 {{ top: 25%; left: 70%; animation-delay: 1s; }}
                        .ff-5 {{ top: 85%; left: 80%; animation-delay: 6s; }}
                        
                        @keyframes float-glow {{
                            0%, 100% {{ transform: translateY(0) scale(0.8); opacity: 0; }}
                            50% {{ transform: translateY(-20px) scale(1.2); opacity: 0.8; }}
                        }}
                        
                        /* Woodland wooden card */
                        .card {{
                            background-color: rgba(16, 37, 24, 0.85);
                            border: 4px solid #422006;
                            border-radius: 28px;
                            padding: 3rem 2.5rem;
                            text-align: center;
                            max-width: 440px;
                            width: 100%;
                            box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.7),
                                        inset 0 0 20px rgba(0, 0, 0, 0.5);
                            position: relative;
                            z-index: 10;
                        }}
                        
                        .card::before {{
                            content: "";
                            position: absolute;
                            top: 4px;
                            left: 4px;
                            right: 4px;
                            bottom: 4px;
                            border: 2px dashed rgba(255, 255, 255, 0.08);
                            border-radius: 22px;
                            pointer-events: none;
                        }}
                        
                        /* Checkmark badge */
                        .badge-circle {{
                            display: inline-flex;
                            justify-content: center;
                            align-items: center;
                            width: 76px;
                            height: 76px;
                            background: linear-gradient(135deg, #10b981, #047857);
                            border: 3px solid #143520;
                            border-radius: 50%;
                            margin-bottom: 1.5rem;
                            color: #fffbeb;
                            box-shadow: 0 6px 0 #143520,
                                        inset 0 2px 4px rgba(255, 255, 255, 0.3);
                        }}
                        
                        .badge-circle svg {{
                            filter: drop-shadow(0 2px 2px rgba(0,0,0,0.3));
                        }}
                        
                        /* Header 3D outline styling */
                        h1 {{
                            font-family: 'Fredoka', sans-serif;
                            font-size: 2.2rem;
                            font-weight: 700;
                            margin-top: 0;
                            margin-bottom: 1.25rem;
                            color: #ffffff;
                            text-shadow: 2px 2px 0 #422006,
                                         -2px -2px 0 #422006,
                                         2px -2px 0 #422006,
                                         -2px 2px 0 #422006,
                                         0 4px 0 #422006,
                                         0 8px 12px rgba(0, 0, 0, 0.5);
                        }}
                        
                        p {{
                            color: #a7f3d0;
                            line-height: 1.6;
                            font-size: 1.05rem;
                            margin-bottom: 1.75rem;
                            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
                        }}
                        
                        /* Wood-plank-style username badge */
                        .username-badge {{
                            display: inline-block;
                            background: linear-gradient(to bottom, #c2844a, #8c5325);
                            border: 3px solid #422006;
                            color: #fffbeb;
                            padding: 0.6rem 1.75rem;
                            border-radius: 14px;
                            font-weight: 700;
                            font-size: 1.25rem;
                            margin-bottom: 1.75rem;
                            box-shadow: 0 5px 0 #422006,
                                        inset 0 1px 0 rgba(255, 255, 255, 0.3);
                            letter-spacing: 0.03em;
                            text-shadow: 2px 2px 0 #422006;
                        }}
                        
                        .note {{
                            font-size: 0.9rem;
                            color: #a7f3d0;
                            opacity: 0.8;
                            border-top: 2px dashed rgba(255, 255, 255, 0.08);
                            padding-top: 1.5rem;
                            margin-bottom: 0;
                            line-height: 1.5;
                        }}
                    </style>
                </head>
                <body>
                    <div class="firefly ff-1"></div>
                    <div class="firefly ff-2"></div>
                    <div class="firefly ff-3"></div>
                    <div class="firefly ff-4"></div>
                    <div class="firefly ff-5"></div>
                    <div class="card">
                        <div class="badge-circle">
                            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                        </div>
                        <h1>✓ Whitelist Approved</h1>
                        <p>The player's request has been authorized and queued.</p>
                        <div class="username-badge">{username}</div>
                        <p class="note">The watchdog on the GCE server checks metadata changes and will execute the whitelist sync within 60 seconds.</p>
                    </div>
                </body>
                </html>
                """
                return (html, 200, {'Content-Type': 'text/html'})
            except Exception as e:
                print(f"Error handling whitelist approval: {e}")
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
            print(f"Error fetching VM status: {e}")
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
            print(f"Error handling whitelist request: {e}")
            return (json.dumps({"error": str(e)}), 500, headers)

    else:
        return (json.dumps({"error": "Method not allowed."}), 405, headers)
