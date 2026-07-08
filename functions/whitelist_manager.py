from gcp_client import compute, get_cached_instance, invalidate_instance_cache
from config import PROJECT_ID, ZONE, INSTANCE_NAME, logger

def get_whitelist_states():
    """Retrieves both approved-whitelist and pending-whitelist lists from GCE instance metadata."""
    logger.info(f"Fetching whitelist states from GCE instance {INSTANCE_NAME}...")
    try:
        instance = get_cached_instance()
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

def update_whitelist_state(username, action, enqueue_cmd=None):
    """Updates the VM instance metadata for whitelist operations in a single atomic transaction.
    This avoids sequential metadata update race conditions/fingerprint mismatch errors.
    
    action can be:
      - 'request': Add username to pending-whitelist.
      - 'approve': Add username to approved-whitelist and remove from pending-whitelist.
      - 'deny': Remove username from pending-whitelist.
      - 'remove': Remove username from approved-whitelist.
    """
    logger.info(f"Performing atomic GCE metadata update for '{username}' with action='{action}', command='{enqueue_cmd}'...")
    try:
        instance = get_cached_instance()
    except Exception as e:
        logger.error(f"Failed to fetch GCE instance details for metadata update: {e}")
        raise
    
    metadata = instance.get('metadata', {})
    items = metadata.get('items', [])
    
    # Extract current lists
    approved_item = next((i for i in items if i.get('key') == 'approved-whitelist'), None)
    pending_item = next((i for i in items if i.get('key') == 'pending-whitelist'), None)
    commands_item = next((i for i in items if i.get('key') == 'pending-commands'), None)
    
    approved_players = set([x.strip() for x in approved_item.get('value', '').split(',') if x.strip()]) if approved_item else set()
    pending_players = set([x.strip() for x in pending_item.get('value', '').split(',') if x.strip()]) if pending_item else set()
    pending_commands = [x.strip() for x in commands_item.get('value', '').split(',') if x.strip()] if commands_item else []
    
    # Modify sets based on action
    if action == 'request':
        pending_players.add(username)
    elif action == 'approve':
        approved_players.add(username)
        pending_players.discard(username)
    elif action == 'deny':
        pending_players.discard(username)
    elif action == 'remove':
        approved_players.discard(username)
        
    if enqueue_cmd:
        if enqueue_cmd not in pending_commands:
            pending_commands.append(enqueue_cmd)
            
    # Rebuild updated metadata items
    new_approved_val = ','.join(approved_players)
    new_pending_val = ','.join(pending_players)
    new_commands_val = ','.join(pending_commands)
    
    updated_items = []
    keys_handled = set()
    
    for item in items:
        key = item.get('key')
        if key == 'approved-whitelist':
            updated_items.append({**item, 'value': new_approved_val})
            keys_handled.add(key)
        elif key == 'pending-whitelist':
            updated_items.append({**item, 'value': new_pending_val})
            keys_handled.add(key)
        elif key == 'pending-commands':
            updated_items.append({**item, 'value': new_commands_val})
            keys_handled.add(key)
        else:
            updated_items.append({**item})
            
    if 'approved-whitelist' not in keys_handled:
        updated_items.append({'key': 'approved-whitelist', 'value': new_approved_val})
    if 'pending-whitelist' not in keys_handled:
        updated_items.append({'key': 'pending-whitelist', 'value': new_pending_val})
    if 'pending-commands' not in keys_handled:
        updated_items.append({'key': 'pending-commands', 'value': new_commands_val})
        
    logger.info(f"Saving metadata to {INSTANCE_NAME}. Approved: '{new_approved_val}', Pending: '{new_pending_val}', Commands: '{new_commands_val}'")
    
    try:
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
        invalidate_instance_cache()
        logger.info("Metadata successfully updated on GCE VM instance.")
    except Exception as e:
        logger.error(f"Failed to update GCE metadata: {e}")
        raise

def add_to_gce_metadata_whitelist(username):
    """Appends a username to the approved-whitelist metadata attribute on the VM using immutable patterns."""
    update_whitelist_state(username, 'approve')

def remove_from_gce_metadata_whitelist(username):
    """Removes a username from the approved-whitelist metadata attribute on the VM using immutable patterns."""
    update_whitelist_state(username, 'remove')

def add_to_gce_metadata_pending(username):
    """Appends a username to the pending-whitelist metadata attribute on the VM using immutable patterns."""
    update_whitelist_state(username, 'request')

def remove_from_gce_metadata_pending(username):
    """Removes a username from the pending-whitelist metadata attribute on the VM using immutable patterns."""
    update_whitelist_state(username, 'deny')

def enqueue_admin_command(command):
    """Appends a command to GCE metadata pending-commands using immutable patterns."""
    logger.info(f"Fetching GCE instance details to enqueue command: {command}...")
    instance = get_cached_instance()
    
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
    invalidate_instance_cache()
    logger.info(f"Command '{command}' enqueued successfully.")
