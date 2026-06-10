import os
import time
from googleapiclient import discovery

# Read configuration from environment variables
PROJECT_ID = os.environ.get('PROJECT_ID')
ZONE = os.environ.get('ZONE')
INSTANCE_NAME = os.environ.get('INSTANCE_NAME')
DNS_ZONE_NAME = os.environ.get('DNS_ZONE_NAME')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME')

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
