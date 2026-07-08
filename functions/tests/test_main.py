import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import main

@patch('main.get_instance_status_and_ip')
@patch('main.is_minecraft_ready')
def test_get_status_http_get(mock_is_minecraft_ready, mock_get_status):
    """Test standard GET status."""
    mock_get_status.return_value = ('RUNNING', '1.2.3.4')
    mock_is_minecraft_ready.return_value = True
    
    mock_request = MagicMock()
    mock_request.method = 'GET'
    mock_request.args = {}
    mock_request.headers = {}
    
    response, code, headers = main.get_status_http(mock_request)
    
    assert code == 200
    data = json.loads(response)
    assert data['status'] == 'RUNNING'
    assert data['ip'] == '1.2.3.4'

@patch('main.get_instance_status_and_ip')
@patch('main.is_minecraft_ready')
def test_get_status_http_not_ready(mock_is_minecraft_ready, mock_get_status):
    """Test when VM is running but Minecraft isn't ready yet."""
    mock_get_status.return_value = ('RUNNING', '1.2.3.4')
    mock_is_minecraft_ready.return_value = False
    
    mock_request = MagicMock()
    mock_request.method = 'GET'
    mock_request.args = {}
    mock_request.headers = {}
    
    response, code, headers = main.get_status_http(mock_request)
    
    assert code == 200
    data = json.loads(response)
    assert data['status'] == 'STARTING'

@patch('main.get_instance_status_and_ip')
@patch('main.start_instance')
@patch('main.update_dns_record')
def test_start_minecraft_terminated(mock_update_dns, mock_start_instance, mock_get_status):
    """Test start_minecraft triggers startup when VM is terminated."""
    mock_get_status.return_value = ('TERMINATED', None)
    
    mock_event = MagicMock()
    main.start_minecraft(mock_event)
    
    mock_start_instance.assert_called_once()
    mock_update_dns.assert_not_called()

@patch('main.get_instance_status_and_ip')
@patch('main.start_instance')
@patch('main.update_dns_record')
def test_start_minecraft_running(mock_update_dns, mock_start_instance, mock_get_status):
    """Test start_minecraft updates DNS when VM is running and has IP."""
    mock_get_status.return_value = ('RUNNING', '1.2.3.4')
    
    mock_event = MagicMock()
    main.start_minecraft(mock_event)
    
    mock_start_instance.assert_not_called()
    mock_update_dns.assert_called_once_with('1.2.3.4')

@patch('main.compute')
@patch('main.update_dns_record')
def test_admin_status_dns_update_error(mock_update_dns, mock_compute):
    """Test get_status_http handles DNS update exceptions at line 134 gracefully."""
    mock_vm = {
        'status': 'RUNNING',
        'networkInterfaces': [{'accessConfigs': [{'natIP': '1.2.3.4'}]}],
        'metadata': {'items': []}
    }
    mock_compute.instances().get().execute.return_value = mock_vm
    mock_update_dns.side_effect = Exception("DNS Update Failed")
    
    mock_request = MagicMock()
    mock_request.method = 'GET'
    mock_request.args = {'action': 'admin_status'}
    mock_request.headers = {}
    
    with patch('main.check_admin_auth', return_value=True):
        # Should not raise exception, but return 200
        response, code, headers = main.get_status_http(mock_request)
        assert code == 200
        data = json.loads(response)
        assert data['status'] == 'RUNNING'

@patch('main.get_cors_headers')
def test_cors_headers_options(mock_cors):
    """Test that OPTIONS preflight request triggers correct CORS headers."""
    mock_request = MagicMock()
    mock_request.method = 'OPTIONS'
    
    main.get_status_http(mock_request)
    mock_cors.assert_called_once_with(mock_request, for_preflight=True)

def test_get_cors_headers_wildcard():
    """Test get_cors_headers returns wildcard when ALLOWED_ORIGINS is '*'."""
    mock_request = MagicMock()
    mock_request.headers = {'Origin': 'https://example.com'}
    
    with patch.dict(os.environ, {'ALLOWED_ORIGINS': '*'}):
        headers = main.get_cors_headers(mock_request)
        assert headers['Access-Control-Allow-Origin'] == '*'

def test_get_cors_headers_allowed():
    """Test get_cors_headers returns correct origin when match is found."""
    mock_request = MagicMock()
    mock_request.headers = {'Origin': 'https://allowed.com'}
    
    with patch.dict(os.environ, {'ALLOWED_ORIGINS': 'https://allowed.com,https://another.com'}):
        headers = main.get_cors_headers(mock_request)
        assert headers['Access-Control-Allow-Origin'] == 'https://allowed.com'

def test_get_cors_headers_disallowed():
    """Test get_cors_headers falls back to first origin when no match is found."""
    mock_request = MagicMock()
    mock_request.headers = {'Origin': 'https://disallowed.com'}
    
    with patch.dict(os.environ, {'ALLOWED_ORIGINS': 'https://allowed.com,https://another.com'}):
        headers = main.get_cors_headers(mock_request)
        assert headers['Access-Control-Allow-Origin'] == 'https://allowed.com'
