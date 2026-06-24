import os
import logging

# Configure structured system logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('minecraft-ondemand')

# Read configuration from environment variables
PROJECT_ID = os.environ.get('PROJECT_ID')
ZONE = os.environ.get('ZONE')
INSTANCE_NAME = os.environ.get('INSTANCE_NAME')
DNS_ZONE_NAME = os.environ.get('DNS_ZONE_NAME')
DOMAIN_NAME = os.environ.get('DOMAIN_NAME')
WHITELIST_SECRET = os.environ.get('WHITELIST_SECRET')
FUNCTION_REGION = os.environ.get('FUNCTION_REGION', 'us-central1')
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

# New config variables for Admin Panel, backups, and wakeup control
ADMIN_PASSCODE = os.environ.get('ADMIN_PASSCODE')
WAKEUP_PASSCODE = os.environ.get('WAKEUP_PASSCODE')
BACKUPS_BUCKET = os.environ.get('BACKUPS_BUCKET')
INSTANCE_ID = os.environ.get('INSTANCE_ID')

# Generic Dynamic DNS configurations
DNS_PROVIDER = os.environ.get('DNS_PROVIDER', 'google')
DNS_API_TOKEN = os.environ.get('DNS_API_TOKEN')
CLOUDFLARE_ZONE_ID = os.environ.get('CLOUDFLARE_ZONE_ID')

def validate_config():
    """Validates that all critical configuration variables are loaded.
    Fails fast by raising a ValueError if required config is missing.
    """
    required = {
        'PROJECT_ID': PROJECT_ID,
        'ZONE': ZONE,
        'INSTANCE_NAME': INSTANCE_NAME,
    }
    
    if DNS_PROVIDER == 'google':
        required['DNS_ZONE_NAME'] = DNS_ZONE_NAME
        required['DOMAIN_NAME'] = DOMAIN_NAME
    elif DNS_PROVIDER in ['cloudflare', 'duckdns', 'dynu']:
        required['DOMAIN_NAME'] = DOMAIN_NAME
        required['DNS_API_TOKEN'] = DNS_API_TOKEN
        if DNS_PROVIDER == 'cloudflare':
            required['CLOUDFLARE_ZONE_ID'] = CLOUDFLARE_ZONE_ID
            
    missing = [k for k, v in required.items() if not v]
    if missing:
        msg = f"Missing required configuration environment variables for DNS provider '{DNS_PROVIDER}': {', '.join(missing)}"
        logger.error(msg)
        raise ValueError(msg)
        
    logger.info("Configuration successfully validated.")
    
    # Log warnings for missing optional parameters to help debug
    optional = {
        'ADMIN_PASSCODE': ADMIN_PASSCODE,
        'WAKEUP_PASSCODE': WAKEUP_PASSCODE,
        'BACKUPS_BUCKET': BACKUPS_BUCKET,
        'INSTANCE_ID': INSTANCE_ID,
        'WHITELIST_SECRET': WHITELIST_SECRET,
        'DISCORD_WEBHOOK_URL': DISCORD_WEBHOOK_URL
    }
    missing_opt = [k for k, v in optional.items() if not v]
    if missing_opt:
        logger.warning(f"Optional configuration variables are missing: {', '.join(missing_opt)}")

