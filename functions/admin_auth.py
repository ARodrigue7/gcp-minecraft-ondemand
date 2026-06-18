import hmac
from config import ADMIN_PASSCODE, logger

def check_admin_auth(request):
    """Verifies the admin passcode in the request headers (Authorization: Bearer <passcode>).
    
    Args:
        request (functions_framework.Request): The HTTP request object.
        
    Returns:
        bool: True if authorized, False otherwise.
    """
    if not ADMIN_PASSCODE:
        logger.error("ADMIN_PASSCODE environment variable is not configured. Admin requests will fail.")
        return False
        
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        logger.warning("Missing Authorization header in admin request.")
        return False
        
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        token = auth_header
        
    return hmac.compare_digest(token, ADMIN_PASSCODE)
