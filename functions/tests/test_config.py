import os
import sys
import pytest
from unittest.mock import patch

# Add parent directory to sys.path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def test_validate_config_success():
    """Test validate_config passes when required variables are set."""
    with patch.multiple('config', PROJECT_ID='proj', ZONE='zone', INSTANCE_NAME='inst', DNS_PROVIDER='none'):
        # Should not raise any exception
        config.validate_config()

def test_validate_config_missing_required():
    """Test validate_config raises ValueError when critical variables are missing."""
    with patch.multiple('config', PROJECT_ID='', ZONE='zone', INSTANCE_NAME='inst', DNS_PROVIDER='none'):
        with pytest.raises(ValueError, match="Missing required configuration environment variables"):
            config.validate_config()

def test_validate_config_google_dns_missing():
    """Test Google DNS missing required fields."""
    with patch.multiple('config', PROJECT_ID='proj', ZONE='zone', INSTANCE_NAME='inst', DNS_PROVIDER='google', DNS_ZONE_NAME='', DOMAIN_NAME=''):
        with pytest.raises(ValueError, match="DOMAIN_NAME"):
            config.validate_config()

def test_validate_config_cloudflare_dns_missing():
    """Test Cloudflare DNS missing required fields."""
    with patch.multiple('config', PROJECT_ID='proj', ZONE='zone', INSTANCE_NAME='inst', DNS_PROVIDER='cloudflare', DOMAIN_NAME='', DNS_API_TOKEN='', CLOUDFLARE_ZONE_ID=''):
        with pytest.raises(ValueError, match="CLOUDFLARE_ZONE_ID"):
            config.validate_config()
