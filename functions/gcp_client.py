import socket
import urllib.request
import json
from googleapiclient import discovery
from config import (
    PROJECT_ID,
    ZONE,
    INSTANCE_NAME,
    DNS_ZONE_NAME,
    DOMAIN_NAME,
    BACKUPS_BUCKET,
    INSTANCE_ID,
    DNS_PROVIDER,
    DNS_API_TOKEN,
    CLOUDFLARE_ZONE_ID,
    logger
)

# Build client services
# cache_discovery=False prevents file-locking warnings in read-only environments
compute = discovery.build('compute', 'v1', cache_discovery=False)
dns = discovery.build('dns', 'v1', cache_discovery=False)
logging_service = discovery.build('logging', 'v2', cache_discovery=False)
storage_service = discovery.build('storage', 'v1', cache_discovery=False)


import time

_instance_cache = None
_instance_cache_time = 0
CACHE_TTL = 10 # seconds

def get_cached_instance():
    """Retrieves the GCE instance, caching the result for a short TTL to prevent redundant API calls within the same request cycle."""
    global _instance_cache, _instance_cache_time
    if time.time() - _instance_cache_time < CACHE_TTL and _instance_cache:
        return _instance_cache
        
    logger.info(f"Fetching GCE instance details for {INSTANCE_NAME}...")
    request = compute.instances().get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
    _instance_cache = request.execute()
    _instance_cache_time = time.time()
    return _instance_cache

def invalidate_instance_cache():
    """Invalidates the instance cache, useful after a metadata update."""
    global _instance_cache_time
    _instance_cache_time = 0

def get_instance_status_and_ip():
    """Retrieves the current status and public IP address of the VM instance."""
    instance = get_cached_instance()
    status = instance.get('status')
    
    ip = None
    network_interfaces = instance.get('networkInterfaces', [])
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
    """Updates either Google Cloud DNS, Cloudflare, DuckDNS, or Dynu to point to the new IP address."""
    provider = DNS_PROVIDER.lower()
    
    if provider == 'none':
        logger.info("DNS provider is 'none'. Skipping dynamic DNS update.")
        return

    elif provider == 'google':
        # Ensure domain ends with a period for Cloud DNS API
        record_name = f"{DOMAIN_NAME}." if not DOMAIN_NAME.endswith('.') else DOMAIN_NAME
        
        logger.info(f"Checking existing Google Cloud DNS record sets for {record_name}...")
        try:
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
                logger.info(f"Google DNS record for {record_name} already matches new IP {new_ip}. No update needed.")
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
                
            logger.info(f"Updating Google DNS for {record_name}: changing from {old_ip} to {new_ip}")
            request = dns.changes().create(
                project=PROJECT_ID,
                managedZone=DNS_ZONE_NAME,
                body=change_body
            )
            request.execute()
            logger.info("Google DNS record successfully updated.")
        except Exception as e:
            logger.error(f"Failed to update Google Cloud DNS: {e}")
            raise e

    elif provider == 'cloudflare':
        headers = {
            "Authorization": f"Bearer {DNS_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # 1. Fetch existing A record to get record_id and check current IP
        url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records?name={DOMAIN_NAME}&type=A"
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            records = res_data.get("result", [])
            record_id = None
            old_ip = None
            if records:
                record_id = records[0].get("id")
                old_ip = records[0].get("content")
                
            if old_ip == new_ip:
                logger.info(f"Cloudflare DNS record for {DOMAIN_NAME} already matches IP {new_ip}. No update needed.")
                return
                
            body = {
                "type": "A",
                "name": DOMAIN_NAME,
                "content": new_ip,
                "ttl": 60,
                "proxied": False
            }
            data = json.dumps(body).encode('utf-8')
            
            if record_id:
                # Update existing record
                logger.info(f"Updating existing Cloudflare record {record_id} to IP {new_ip}...")
                update_url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records/{record_id}"
                req = urllib.request.Request(update_url, data=data, headers=headers, method="PUT")
            else:
                # Create new record
                logger.info(f"Creating new Cloudflare record with IP {new_ip}...")
                create_url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
                req = urllib.request.Request(create_url, data=data, headers=headers, method="POST")
                
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                if res_data.get("success"):
                    logger.info(f"Cloudflare DNS record updated successfully to {new_ip}.")
                else:
                    logger.error(f"Cloudflare API returned error: {res_data}")
                    raise Exception("Cloudflare API error.")
        except Exception as e:
            logger.error(f"Failed to update Cloudflare DNS: {e}")
            raise e

    elif provider == 'duckdns':
        subdomain = DOMAIN_NAME.split('.')[0]
        url = f"https://www.duckdns.org/update?domains={subdomain}&token={DNS_API_TOKEN}&ip={new_ip}"
        logger.info(f"Updating DuckDNS domain '{DOMAIN_NAME}' (subdomain: '{subdomain}') to {new_ip}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'GCP-Minecraft-On-Demand-Updater'})
            with urllib.request.urlopen(req) as response:
                res = response.read().decode('utf-8').strip()
                if res == "OK":
                    logger.info(f"DuckDNS domain '{DOMAIN_NAME}' updated successfully to {new_ip}.")
                else:
                    raise Exception(f"DuckDNS update returned status: {res}")
        except Exception as e:
            logger.error(f"Failed to update DuckDNS: {e}")
            raise e

    elif provider == 'dynu':
        url = f"https://api.dynu.com/nic/update?hostname={DOMAIN_NAME}&password={DNS_API_TOKEN}&myip={new_ip}"
        logger.info(f"Updating Dynu domain '{DOMAIN_NAME}' to {new_ip}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'GCP-Minecraft-On-Demand-Updater'})
            with urllib.request.urlopen(req) as response:
                res = response.read().decode('utf-8').strip()
                if res.startswith("good") or res.startswith("nochg"):
                    logger.info(f"Dynu domain '{DOMAIN_NAME}' updated successfully to {new_ip} (status: {res}).")
                else:
                    raise Exception(f"Dynu update returned status: {res}")
        except Exception as e:
            logger.error(f"Failed to update Dynu DNS: {e}")
            raise e

    else:
        logger.error(f"Unsupported DNS provider configuration: '{DNS_PROVIDER}'")

def is_minecraft_ready(ip, port=25565, timeout=1.0):
    """Checks if the Minecraft server is actually listening on the given IP and port."""
    if not ip:
        logger.warning("No IP provided to check Minecraft status.")
        return False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        s.shutdown(socket.SHUT_RDWR)
        logger.info(f"Minecraft server is ready on {ip}:{port}.")
        return True
    except Exception:
        logger.debug(f"Minecraft server not yet listening on {ip}:{port}.")
        return False
    finally:
        s.close()

def get_backups_list():
    """Retrieves version history of rolling_backup.tar.gz from GCS."""
    if not BACKUPS_BUCKET:
        logger.warning("BACKUPS_BUCKET environment variable is not set. Cannot list backups.")
        return []
    try:
        logger.info(f"Listing backups in GCS bucket: {BACKUPS_BUCKET}...")
        res = storage_service.objects().list(bucket=BACKUPS_BUCKET, versions=True).execute()
        items = res.get('items', [])
        
        backups = []
        for item in items:
            if item.get('name') == 'rolling_backup.tar.gz':
                gen = item.get('generation')
                size = int(item.get('size', 0))
                updated = item.get('timeCreated')
                backups.append({
                    "generation": gen,
                    "size": size,
                    "timeCreated": updated
                })
        
        backups.sort(key=lambda x: x['timeCreated'], reverse=True)
        logger.info(f"Successfully retrieved {len(backups)} backups.")
        return backups[:5]
    except Exception as e:
        logger.error(f"Error listing backups from GCS: {e}")
        return []

def download_backup_file(generation):
    """Downloads a specific generation of rolling_backup.tar.gz from GCS and returns it."""
    if not BACKUPS_BUCKET:
        logger.error("BACKUPS_BUCKET environment variable is not configured.")
        return ("Backups bucket is not configured", 400, {})
    try:
        logger.info(f"Downloading generation {generation} of rolling_backup.tar.gz from {BACKUPS_BUCKET}...")
        url = f"https://storage.googleapis.com/storage/v1/b/{BACKUPS_BUCKET}/o/rolling_backup.tar.gz?alt=media&generation={generation}"
        
        token_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
        req = urllib.request.Request(token_url, headers={"Metadata-Flavor": "Google"})
        try:
            with urllib.request.urlopen(req) as response:
                token_data = json.loads(response.read().decode('utf-8'))
                access_token = token_data['access_token']
        except Exception as token_err:
            logger.error(f"Failed to fetch metadata auth token: {token_err}")
            raise Exception("Failed to authorize GCS download via metadata token.")
        
        file_req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(file_req) as file_resp:
            file_content = file_resp.read()
            
        custom_headers = {
            'Content-Type': 'application/x-gzip',
            'Content-Disposition': f'attachment; filename="minecraft_backup_{generation}.tar.gz"'
        }
        logger.info(f"Successfully downloaded backup generation {generation}.")
        return (file_content, 200, custom_headers)
    except Exception as e:
        logger.error(f"Error downloading backup from GCS: {e}")
        return (f"Failed to download backup: {str(e)}", 500, {})

def get_minecraft_logs():
    """Retrieves recent Minecraft container log entries from Cloud Logging."""
    if not PROJECT_ID or not INSTANCE_ID:
        logger.warning("PROJECT_ID or INSTANCE_ID config missing. Cannot fetch logs.")
        return [{"timestamp": "", "message": "Logging parameters are not configured."}]
    try:
        logger.info(f"Fetching logs for instance {INSTANCE_ID} from Cloud Logging...")
        log_filter = (
            f'resource.type="gce_instance" '
            f'AND resource.labels.instance_id="{INSTANCE_ID}" '
            f'AND (log_name="projects/{PROJECT_ID}/logs/gcplogs-docker-driver" '
            f'OR log_name="projects/{PROJECT_ID}/logs/cos")'
        )
        
        body = {
            "resourceNames": [f"projects/{PROJECT_ID}"],
            "filter": log_filter,
            "orderBy": "timestamp desc",
            "pageSize": 50
        }
        
        res = logging_service.entries().list(body=body).execute()
        entries = res.get('entries', [])
        
        logs = []
        for entry in entries:
            text = entry.get('textPayload', '')
            if not text and 'jsonPayload' in entry:
                text = entry['jsonPayload'].get('message', '')
            
            if text:
                timestamp = entry.get('timestamp')
                logs.append({
                    "timestamp": timestamp,
                    "message": text.strip()
                })
        
        logs.reverse()
        logger.info(f"Retrieved {len(logs)} log entries.")
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs from Cloud Logging: {e}")
        return [{"timestamp": "", "message": f"Error loading logs: {e}"}]

