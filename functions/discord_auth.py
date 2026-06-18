import hmac
import hashlib
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from config import DISCORD_PUBLIC_KEY, WHITELIST_SECRET, logger

def verify_discord_signature(signature, timestamp, body):
    """Verifies that an incoming interaction request is cryptographically signed by Discord.
    
    Args:
        signature (str): The signature hex string from the header.
        timestamp (str): The timestamp from the header.
        body (str): The raw request body string.
        
    Returns:
        bool: True if signature is valid, False otherwise.
    """
    if not DISCORD_PUBLIC_KEY:
        logger.error("DISCORD_PUBLIC_KEY environment variable is not configured.")
        return False
        
    if not signature or not timestamp or not body:
        logger.warning("Missing signature, timestamp, or body for Discord signature verification.")
        return False
        
    try:
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        verify_key.verify(f"{timestamp}{body}".encode('utf-8'), bytes.fromhex(signature))
        logger.info("Discord signature validation succeeded.")
        return True
    except BadSignatureError:
        logger.warning("Discord signature validation failed: Bad Signature.")
        return False
    except Exception as e:
        logger.error(f"Error validating Discord signature: {e}")
        return False

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
