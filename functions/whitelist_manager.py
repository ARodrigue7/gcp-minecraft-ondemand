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
