import hmac
from config import ADMIN_PASSCODE, logger
from whitelist_manager import get_whitelist_sets

def check_admin_auth(request):
    """Verifies the admin passcode in the request headers (Authorization: Bearer <passcode>)
    AND verifies that the X-Admin-User is currently on the approved player whitelist.
    
    Args:
        request (functions_framework.Request): The HTTP request object.
        
    Returns:
        bool: True if authorized, False otherwise.
    """
    if not ADMIN_PASSCODE:
        logger.error("ADMIN_PASSCODE environment variable is not configured. Admin requests will fail.")
        return False
        
    # 1. Verify Passcode (Admin Password)
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        logger.warning("Missing Authorization header in admin request.")
        return False
        
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        token = auth_header
        
    if not hmac.compare_digest(token, ADMIN_PASSCODE):
        logger.warning("Admin passcode mismatch.")
        return False

    # 2. Verify Whitelisted User
    admin_user = request.headers.get('X-Admin-User')
    if not admin_user:
        logger.warning("Missing X-Admin-User header in admin request.")
        return False

    approved_set, _ = get_whitelist_sets()
    if admin_user.lower() not in approved_set:
        logger.warning(f"Admin request attempted by non-whitelisted user: {admin_user}")
        return False

    return True
