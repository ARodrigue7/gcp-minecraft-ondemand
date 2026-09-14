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

@patch('main.get_cached_instance')
@patch('main.get_instance_status_and_ip')
@patch('main.update_dns_record')
def test_admin_status_dns_update_error(mock_update_dns, mock_get_status, mock_get_cached_instance):
    """Test get_status_http handles DNS update exceptions at line 134 gracefully."""
    mock_vm = {
        'status': 'RUNNING',
        'networkInterfaces': [{'accessConfigs': [{'natIP': '1.2.3.4'}]}],
        'metadata': {'items': []}
    }
    mock_get_status.return_value = ('RUNNING', '1.2.3.4')
    mock_get_cached_instance.return_value = mock_vm
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

@patch('main.check_admin_auth', return_value=True)
@patch('main.get_server_config', return_value={"type": "fabric", "machine_type": "e2-standard-2"})
def test_admin_get_config(mock_cfg, mock_auth):
    mock_request = MagicMock()
    mock_request.method = 'GET'
    mock_request.args = {'action': 'admin_get_config'}
    
    response, code, _ = main.get_status_http(mock_request)
    assert code == 200
    data = json.loads(response)
    assert data["type"] == "fabric"

@patch('main.check_admin_auth', return_value=True)
@patch('main.save_server_config', return_value={"type": "modrinth", "modpack_id": "cobblemon"})
def test_admin_save_config(mock_save, mock_auth):
    mock_request = MagicMock()
    mock_request.method = 'POST'
    mock_request.args = {'action': 'admin_save_config'}
    mock_request.get_json.return_value = {"type": "modrinth", "modpack_id": "cobblemon"}
    
    response, code, _ = main.get_status_http(mock_request)
    assert code == 200
    data = json.loads(response)
@patch('main.check_admin_auth', return_value=True)
@patch('main.list_mods', return_value=[{"filename": "test.jar", "size": 100, "enabled": True}])
def test_admin_mods_list(mock_list, mock_auth):
    mock_request = MagicMock()
    mock_request.method = 'GET'
    mock_request.args = {'action': 'admin_mods_list', 'folder': 'mods'}
    
    response, code, _ = main.get_status_http(mock_request)
    assert code == 200
    data = json.loads(response)
    assert len(data["mods"]) == 1
    assert data["mods"][0]["filename"] == "test.jar"

@patch('main.check_admin_auth', return_value=True)
@patch('main.create_upload_session', return_value={"upload_url": "https://gcs.upload/123", "filename": "test.jar", "folder": "mods"})
def test_admin_mods_upload_session(mock_session, mock_auth):
    mock_request = MagicMock()
    mock_request.method = 'POST'
    mock_request.args = {'action': 'admin_mods_upload_session'}
    mock_request.get_json.return_value = {"filename": "test.jar", "folder": "mods"}
    
    response, code, _ = main.get_status_http(mock_request)
    assert code == 200
    data = json.loads(response)
    assert data["upload_url"] == "https://gcs.upload/123"

@patch('main.check_admin_auth', return_value=True)
@patch('main.toggle_mod', return_value={"filename": "test.jar.disabled", "enabled": False})
def test_admin_mods_toggle(mock_toggle, mock_auth):
    mock_request = MagicMock()
    mock_request.method = 'POST'
    mock_request.args = {'action': 'admin_mods_toggle'}
    mock_request.get_json.return_value = {"filename": "test.jar", "folder": "mods"}
    
    response, code, _ = main.get_status_http(mock_request)
    assert code == 200
    data = json.loads(response)
    assert data["enabled"] is False

@patch('main.check_admin_auth', return_value=True)
@patch('main.delete_mod', return_value={"deleted": True, "filename": "test.jar"})
def test_admin_mods_delete(mock_del, mock_auth):
    mock_request = MagicMock()
    mock_request.method = 'POST'
    mock_request.args = {'action': 'admin_mods_delete'}
    mock_request.get_json.return_value = {"filename": "test.jar", "folder": "mods"}
    
    response, code, _ = main.get_status_http(mock_request)
    assert code == 200
    data = json.loads(response)
    assert data["deleted"] is True


