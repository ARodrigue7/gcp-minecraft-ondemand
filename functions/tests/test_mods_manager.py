import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mods_manager import list_mods, create_upload_session, toggle_mod, delete_mod, _validate_path

@patch('mods_manager.storage_service')
def test_list_mods_populated(mock_storage):
    mock_storage.objects().list().execute.return_value = {
        "items": [
            {"name": "mods/", "size": "0"},
            {"name": "mods/sodium-0.5.jar", "size": "1048576", "updated": "2026-09-12T00:00:00Z"},
            {"name": "mods/lithium-0.11.jar.disabled", "size": "524288", "updated": "2026-09-12T01:00:00Z"}
        ]
    }
    
    items = list_mods("mods")
    assert len(items) == 2
    
    sodium = next(i for i in items if i["filename"] == "sodium-0.5.jar")
    assert sodium["enabled"] is True
    assert sodium["size"] == 1048576
    
    lithium = next(i for i in items if i["filename"] == "lithium-0.11.jar.disabled")
    assert lithium["enabled"] is False
    assert lithium["size"] == 524288

@patch('mods_manager.storage_service')
def test_list_mods_empty_or_error(mock_storage):
    mock_storage.objects().list().execute.side_effect = Exception("Storage error")
    items = list_mods("mods")
    assert items == []

def test_validate_path_security():
    # Path traversal rejected
    with pytest.raises(ValueError, match="Invalid filename"):
        _validate_path("../../etc/passwd", "mods")
    
    with pytest.raises(ValueError, match="Invalid filename"):
        _validate_path("subdir/test.jar", "mods")
        
    with pytest.raises(ValueError, match="File must be a .jar or .zip"):
        _validate_path("malicious.sh", "mods")
        
    with pytest.raises(ValueError, match="Invalid folder"):
        _validate_path("test.jar", "root")

    assert _validate_path("valid-mod.jar", "mods") == "valid-mod.jar"
    assert _validate_path("valid-plugin.jar.disabled", "plugins") == "valid-plugin.jar.disabled"

@patch('google.auth.default')
@patch('urllib.request.urlopen')
def test_create_upload_session(mock_urlopen, mock_auth):
    mock_creds = MagicMock()
    mock_creds.token = "fake-token"
    mock_auth.return_value = (mock_creds, "test-project")
    
    mock_response = MagicMock()
    mock_response.headers.get.return_value = "https://storage.googleapis.com/upload/session/12345"
    mock_urlopen.return_value.__enter__.return_value = mock_response

    session = create_upload_session("iris-shaders.jar", "mods")
    assert session["upload_url"] == "https://storage.googleapis.com/upload/session/12345"
    assert session["filename"] == "iris-shaders.jar"
    assert session["folder"] == "mods"

@patch('mods_manager.storage_service')
def test_toggle_mod_disable(mock_storage):
    res = toggle_mod("mod.jar", "mods")
    assert res["filename"] == "mod.jar.disabled"
    assert res["enabled"] is False
    mock_storage.objects().copy.assert_called_once()
    mock_storage.objects().delete.assert_called_once()

@patch('mods_manager.storage_service')
def test_toggle_mod_enable(mock_storage):
    res = toggle_mod("mod.jar.disabled", "mods")
    assert res["filename"] == "mod.jar"
    assert res["enabled"] is True
    mock_storage.objects().copy.assert_called_once()
    mock_storage.objects().delete.assert_called_once()

@patch('mods_manager.storage_service')
def test_delete_mod(mock_storage):
    res = delete_mod("mod.jar", "mods")
    assert res["deleted"] is True
    assert res["filename"] == "mod.jar"
    mock_storage.objects().delete.assert_called_once()
