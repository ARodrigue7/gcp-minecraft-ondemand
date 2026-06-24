from gcp_client import compute
from config import PROJECT_ID, ZONE, INSTANCE_NAME, logger

def get_whitelist_states():
    """Retrieves both approved-whitelist and pending-whitelist lists from GCE instance metadata."""
    logger.info(f"Fetching whitelist states from GCE instance {INSTANCE_NAME}...")
    try:
        request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
        instance = request.execute()
    except Exception as e:
        logger.error(f"Failed to fetch GCE instance details: {e}")
        return [], []
    
    metadata = instance.get('metadata', {})
    items = metadata.get('items', [])
    
    approved_item = next((item for item in items if item.get('key') == 'approved-whitelist'), None)
    pending_item = next((item for item in items if item.get('key') == 'pending-whitelist'), None)
    
    approved_players = []
    if approved_item:
        approved_players = [p.strip() for p in approved_item.get('value', '').split(',') if p.strip()]
        
    pending_players = []
    if pending_item:
        pending_players = [p.strip() for p in pending_item.get('value', '').split(',') if p.strip()]
        
    return approved_players, pending_players

def _update_gce_metadata_list(key, username, action='add'):
    """Helper to add or remove a username from a comma-separated list in GCE metadata immutably."""
    logger.info(f"Fetching GCE instance details to {action} {username} in {key}...")
    request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    instance = request.execute()
    
    metadata = instance.get('metadata', {})
    items = metadata.get('items', [])
    
    item = next((i for i in items if i.get('key') == key), None)
    if item:
        elements = [x.strip() for x in item.get('value', '').split(',') if x.strip()]
    else:
        elements = []
        
    if action == 'add':
        if username not in elements:
            new_elements = elements + [username]
        else:
            new_elements = list(elements)
    elif action == 'remove':
        new_elements = [x for x in elements if x != username]
    else:
        new_elements = list(elements)
        
    new_value = ','.join(new_elements)
    
    updated_items = []
    found = False
    for i in items:
        if i.get('key') == key:
            updated_items.append({**i, 'value': new_value})
            found = True
        else:
            updated_items.append({**i})
            
    if not found:
        updated_items.append({'key': key, 'value': new_value})
        
    logger.info(f"Updating metadata for {INSTANCE_NAME}: {key} list is now '{new_value}'")
    
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

def add_to_gce_metadata_whitelist(username):
    """Appends a username to the approved-whitelist metadata attribute on the VM using immutable patterns."""
    _update_gce_metadata_list('approved-whitelist', username, 'add')

def remove_from_gce_metadata_whitelist(username):
    """Removes a username from the approved-whitelist metadata attribute on the VM using immutable patterns."""
    _update_gce_metadata_list('approved-whitelist', username, 'remove')

def add_to_gce_metadata_pending(username):
    """Appends a username to the pending-whitelist metadata attribute on the VM using immutable patterns."""
    _update_gce_metadata_list('pending-whitelist', username, 'add')

def remove_from_gce_metadata_pending(username):
    """Removes a username from the pending-whitelist metadata attribute on the VM using immutable patterns."""
    _update_gce_metadata_list('pending-whitelist', username, 'remove')

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
