import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import admin_auth

@patch('admin_auth.ADMIN_PASSCODE', 'secret_passcode')
@patch('admin_auth.get_whitelist_states')
def test_check_admin_auth_success(mock_get_whitelist_states):
    """Test successful authentication."""
    mock_get_whitelist_states.return_value = (['AdminUser'], [])
    
    mock_request = MagicMock()
    mock_request.headers = {
        'Authorization': 'Bearer secret_passcode',
        'X-Admin-User': 'AdminUser'
    }
    
    assert admin_auth.check_admin_auth(mock_request) is True

@patch('admin_auth.ADMIN_PASSCODE', 'secret_passcode')
def test_check_admin_auth_missing_auth_header():
    """Test check_admin_auth fails when Authorization header is missing."""
    mock_request = MagicMock()
    mock_request.headers = {
        'X-Admin-User': 'AdminUser'
    }
    
    assert admin_auth.check_admin_auth(mock_request) is False

@patch('admin_auth.ADMIN_PASSCODE', 'secret_passcode')
def test_check_admin_auth_missing_admin_user_header():
    """Test check_admin_auth fails when X-Admin-User header is missing."""
    mock_request = MagicMock()
    mock_request.headers = {
        'Authorization': 'Bearer secret_passcode'
    }
    
    assert admin_auth.check_admin_auth(mock_request) is False

@patch('admin_auth.ADMIN_PASSCODE', 'secret_passcode')
@patch('admin_auth.get_whitelist_states')
def test_check_admin_auth_not_in_whitelist(mock_get_whitelist_states):
    """Test check_admin_auth fails when the user is not in the approved whitelist."""
    mock_get_whitelist_states.return_value = (['OtherUser'], [])
    
    mock_request = MagicMock()
    mock_request.headers = {
        'Authorization': 'Bearer secret_passcode',
        'X-Admin-User': 'AdminUser'
    }
    
    assert admin_auth.check_admin_auth(mock_request) is False
