from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from config import DISCORD_PUBLIC_KEY, logger

def verify_discord_signature(signature, timestamp, body):
    """Verifies that an incoming interaction request is cryptographically signed by Discord."""
    if not DISCORD_PUBLIC_KEY:
        logger.error("DISCORD_PUBLIC_KEY environment variable is not configured.")
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
