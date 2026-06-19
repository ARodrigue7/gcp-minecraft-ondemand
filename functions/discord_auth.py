import hmac
import hashlib
from config import WHITELIST_SECRET, logger

def generate_signature(username):
    """Generates a secure HMAC-SHA256 signature for a username.
    
    Args:
        username (str): Minecraft username to sign.
        
    Returns:
        str: Hexadecimal signature string.
    """
    if not WHITELIST_SECRET:
        logger.error("WHITELIST_SECRET is not configured.")
        raise ValueError("WHITELIST_SECRET is not configured.")
        
    if not username:
        raise ValueError("Username cannot be empty for signature generation.")
        
    return hmac.new(
        WHITELIST_SECRET.encode('utf-8'),
        username.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
