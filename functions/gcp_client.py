from googleapiclient import discovery
from config import PROJECT_ID, ZONE, INSTANCE_NAME, DNS_ZONE_NAME, DOMAIN_NAME, logger

# Build client services
# cache_discovery=False prevents file-locking warnings in read-only environments
compute = discovery.build('compute', 'v1', cache_discovery=False)
dns = discovery.build('dns', 'v1', cache_discovery=False)

def get_instance_status_and_ip():
    """Retrieves the current status and public IP address of the VM instance."""
    logger.info(f"Retrieving GCE instance status for {INSTANCE_NAME}...")
    request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    response = request.execute()
    status = response.get('status')
    
    ip = None
    network_interfaces = response.get('networkInterfaces', [])
    if network_interfaces:
        access_configs = network_interfaces[0].get('accessConfigs', [])
        if access_configs:
            ip = access_configs[0].get('natIP')
            
    logger.info(f"VM instance {INSTANCE_NAME} status: {status}, IP: {ip}")
    return status, ip

def start_instance():
    """Triggers the start request for the VM instance."""
    logger.info(f"Triggering start for GCE instance {INSTANCE_NAME}...")
    request = compute.instances().start(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    return request.execute()

def update_dns_record(new_ip):
    """Updates the Cloud DNS A-record to point to the new IP address."""
    # Ensure domain ends with a period for Cloud DNS API
    record_name = f"{DOMAIN_NAME}." if not DOMAIN_NAME.endswith('.') else DOMAIN_NAME
    
    logger.info(f"Checking existing DNS record sets for {record_name}...")
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
            
    # If the record already points to the correct IP, skip update
    if old_ip == new_ip:
        logger.info(f"DNS record for {record_name} already matches new IP {new_ip}. No update needed.")
        return
        
    change_body = {}
    additions = [
        {
            "name": record_name,
            "type": "A",
            "ttl": 60,  # 60s TTL
            "rrdatas": [new_ip]
        }
    ]
    deletions = []
    
    if existing_record:
        deletions.append(existing_record)
        
    change_body["additions"] = additions
    if deletions:
        change_body["deletions"] = deletions
        
    logger.info(f"Updating DNS for {record_name}: changing from {old_ip} to {new_ip}")
    request = dns.changes().create(
        project=PROJECT_ID,
        managedZone=DNS_ZONE_NAME,
        body=change_body
    )
    request.execute()
    logger.info("DNS record successfully updated.")
