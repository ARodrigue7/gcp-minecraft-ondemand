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
DISCORD_PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY')
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def validate_config():
    """Validates that all critical configuration variables are loaded.
    Fails fast by raising a ValueError if required config is missing.
    """
    required = {
        'PROJECT_ID': PROJECT_ID,
        'ZONE': ZONE,
        'INSTANCE_NAME': INSTANCE_NAME,
        'DNS_ZONE_NAME': DNS_ZONE_NAME,
        'DOMAIN_NAME': DOMAIN_NAME
    }
    
    missing = [k for k, v in required.items() if not v]
    if missing:
        msg = f"Missing required configuration environment variables: {', '.join(missing)}"
        logger.error(msg)
        raise ValueError(msg)
        
    logger.info("Configuration successfully validated.")
