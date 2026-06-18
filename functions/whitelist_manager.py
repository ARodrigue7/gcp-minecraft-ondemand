from gcp_client import compute
from config import PROJECT_ID, ZONE, INSTANCE_NAME, logger

def add_to_gce_metadata_whitelist(username):
    """Appends a username to the approved-whitelist metadata attribute on the VM using immutable patterns."""
    logger.info(f"Fetching GCE instance details for {INSTANCE_NAME}...")
    request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    instance = request.execute()
    
    metadata = instance.get('metadata', {})
    items = metadata.get('items', [])
    
    # Locate the approved-whitelist attribute or initialize it
    whitelist_item = next((item for item in items if item.get('key') == 'approved-whitelist'), None)
    
    if whitelist_item:
        players = [p.strip() for p in whitelist_item.get('value', '').split(',') if p.strip()]
    else:
        players = []
        
    if username not in players:
        # Create a new list containing the new username to preserve immutability
        new_players = players + [username]
    else:
        new_players = list(players)  # Make a new copy
        
    new_value = ','.join(new_players)
    
    # Build a new items list immutably (no side-effects/mutations on the original list/dict)
    updated_items = []
    found = False
    for item in items:
        if item.get('key') == 'approved-whitelist':
            updated_items.append({**item, 'value': new_value})
            found = True
        else:
            updated_items.append({**item})
            
    if not found:
        updated_items.append({'key': 'approved-whitelist', 'value': new_value})
        
    logger.info(f"Updating metadata for {INSTANCE_NAME}: approved-whitelist list is now '{new_value}'")
    
    # Save modified metadata back to GCE
    update_request = compute.instances().setMetadata(
        project=PROJECT_ID,
        zone=ZONE,
        instance=INSTANCE_NAME,
        body={
            'fingerprint': metadata.get('fingerprint'),
            'items': updated_items
        }
    )
    update_request.execute()
    logger.info("Metadata successfully updated on GCE VM instance.")

def remove_from_gce_metadata_whitelist(username):
    """Removes a username from the approved-whitelist metadata attribute on the VM using immutable patterns."""
    logger.info(f"Fetching GCE instance details to remove player {username}...")
    request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    instance = request.execute()
    
    metadata = instance.get('metadata', {})
    items = metadata.get('items', [])
    
    whitelist_item = next((item for item in items if item.get('key') == 'approved-whitelist'), None)
    
    if whitelist_item:
        players = [p.strip() for p in whitelist_item.get('value', '').split(',') if p.strip()]
    else:
        players = []
        
    if username in players:
        new_players = [p for p in players if p != username]
    else:
        new_players = list(players)
        
    new_value = ','.join(new_players)
    
    updated_items = []
    found = False
    for item in items:
        if item.get('key') == 'approved-whitelist':
            updated_items.append({**item, 'value': new_value})
            found = True
        else:
            updated_items.append({**item})
            
    if not found:
        updated_items.append({'key': 'approved-whitelist', 'value': new_value})
        
    logger.info(f"Updating metadata for {INSTANCE_NAME}: approved-whitelist list is now '{new_value}'")
    
    update_request = compute.instances().setMetadata(
        project=PROJECT_ID,
        zone=ZONE,
        instance=INSTANCE_NAME,
        body={
            'fingerprint': metadata.get('fingerprint'),
            'items': updated_items
        }
    )
    update_request.execute()
    logger.info("Metadata successfully updated on GCE VM instance.")

def enqueue_admin_command(command):
    """Appends a command to GCE metadata pending-commands using immutable patterns."""
    logger.info(f"Fetching GCE instance details to enqueue command: {command}...")
    request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    instance = request.execute()
    
    metadata = instance.get('metadata', {})
    items = metadata.get('items', [])
    
    commands_item = next((item for item in items if item.get('key') == 'pending-commands'), None)
    
    if commands_item:
        commands = [c.strip() for c in commands_item.get('value', '').split(',') if c.strip()]
    else:
        commands = []
        
    if command not in commands:
        new_commands = commands + [command]
    else:
        new_commands = list(commands)
        
    new_value = ','.join(new_commands)
    
    updated_items = []
    found = False
    for item in items:
        if item.get('key') == 'pending-commands':
            updated_items.append({**item, 'value': new_value})
            found = True
        else:
            updated_items.append({**item})
            
    if not found:
        updated_items.append({'key': 'pending-commands', 'value': new_value})
        
    logger.info(f"Updating metadata for {INSTANCE_NAME}: pending-commands list is now '{new_value}'")
    
    update_request = compute.instances().setMetadata(
        project=PROJECT_ID,
        zone=ZONE,
        instance=INSTANCE_NAME,
        body={
            'fingerprint': metadata.get('fingerprint'),
            'items': updated_items
        }
    )
    update_request.execute()
    logger.info("Metadata successfully updated on GCE VM instance.")

