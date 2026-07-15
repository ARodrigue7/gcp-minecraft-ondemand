import json
import urllib.request
import time
from config import DISCORD_WEBHOOK_URL, INSTANCE_NAME, ZONE, logger
from discord_auth import generate_signature

def delete_discord_message(message_id):
    """Deletes a Discord webhook message by ID to keep the channel clean."""
    if not message_id or not DISCORD_WEBHOOK_URL:
        return
    try:
        delete_url = f"{DISCORD_WEBHOOK_URL}/messages/{message_id}"
        req = urllib.request.Request(
            delete_url,
            method='DELETE',
            headers={'User-Agent': 'GCP-Minecraft-On-Demand-Webhook'}
        )
        with urllib.request.urlopen(req) as resp:
            pass
        logger.info(f"Successfully deleted Discord message {message_id}.")
    except Exception as e:
        logger.error(f"Failed to delete Discord message {message_id}: {e}")

def send_discord_webhook(username, status_url):
    """Sends a formatted alert about a whitelist request to Discord with a one-click approval link."""
    if not DISCORD_WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not configured.")
        return False

    # Generate signature, approval and deny links
    sig = generate_signature(username)
    temp_approval_url = f"{status_url}?action=approve&username={username}&sig={sig}"
    temp_deny_url = f"{status_url}?action=deny&username={username}&sig={sig}"

    payload = {
        "content": None,
        "embeds": [
            {
                "title": "🎮 Whitelist Request Received",
                "description": f"A player has requested access to the Minecraft server.\n\n[🟢 Approve Request]({temp_approval_url})  |  [🔴 Deny & Dismiss]({temp_deny_url})",
                "color": 5814783,  # Purple Accent
                "fields": [
                    {
                        "name": "Minecraft Username",
                        "value": f"**`{username}`**",
                        "inline": True
                    },
                    {
                        "name": "Manual SSH Command",
                        "value": f"```bash\ngcloud compute ssh {INSTANCE_NAME} --zone={ZONE} --command=\"docker exec minecraft rcon-cli whitelist add {username}\"\n```",
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
        logger.info("Sending initial webhook request to Discord...")
        data = json.dumps(payload).encode('utf-8')
        post_url = f"{DISCORD_WEBHOOK_URL}?wait=true"
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
            logger.info("Webhook sent successfully, but did not receive message ID.")
            return True

        # 2. Update approval and deny URLs with the real message ID and PATCH the message to edit the link
        logger.info(f"Webhook message ID received: {message_id}. Patching with final action URLs...")
        real_approval_url = f"{status_url}?action=approve&username={username}&sig={sig}&message_id={message_id}"
        real_deny_url = f"{status_url}?action=deny&username={username}&sig={sig}&message_id={message_id}"
        payload["embeds"][0]["description"] = f"A player has requested access to the Minecraft server.\n\n[🟢 Approve Request]({real_approval_url})  |  [🔴 Deny & Dismiss]({real_deny_url})"
        
        patch_data = json.dumps(payload).encode('utf-8')
        patch_url = f"{DISCORD_WEBHOOK_URL}/messages/{message_id}"
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

        logger.info("Successfully patched Discord webhook message.")
        return True
    except Exception as e:
        logger.error(f"Error executing Discord Webhook: {e}")
        return False
