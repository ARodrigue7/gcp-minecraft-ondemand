import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server_config import get_server_config, save_server_config, DEFAULT_CONFIG

@patch('server_config.storage_service')
@patch('server_config.get_cached_instance')
def test_get_server_config_default(mock_instance, mock_storage):
    mock_instance.return_value = {"machineType": "zones/us-central1-a/machineTypes/e2-medium"}
    mock_storage.objects().get_media().execute.side_effect = Exception("Not found")
    
    cfg = get_server_config()
    assert cfg["type"] == "paper"
    assert cfg["machine_type"] == "e2-medium"
    assert cfg["idle_timeout_seconds"] == 600

@patch('server_config.storage_service')
@patch('server_config.get_cached_instance')
def test_get_server_config_from_gcs(mock_instance, mock_storage):
    mock_instance.return_value = {"machineType": "zones/us-central1-a/machineTypes/e2-standard-2"}
    mock_storage.objects().get_media().execute.return_value = json.dumps({
        "type": "modrinth",
        "modpack_id": "cobblemon",
        "machine_type": "e2-standard-2",
        "idle_timeout_seconds": 1200
    }).encode('utf-8')
    
    cfg = get_server_config()
    assert cfg["type"] == "modrinth"
    assert cfg["modpack_id"] == "cobblemon"
    assert cfg["machine_type"] == "e2-standard-2"
    assert cfg["idle_timeout_seconds"] == 1200

@patch('server_config.compute')
@patch('server_config.storage_service')
@patch('server_config.get_cached_instance')
def test_save_server_config_success_with_resize(mock_instance, mock_storage, mock_compute):
    mock_instance.return_value = {
        "status": "TERMINATED",
        "machineType": "zones/us-central1-a/machineTypes/e2-medium"
    }
    mock_storage.objects().get_media().execute.side_effect = Exception("Not found")
    
    payload = {
        "type": "fabric",
        "machine_type": "e2-standard-2",
        "idle_timeout_seconds": 900
    }
    
    updated = save_server_config(payload)
    assert updated["type"] == "fabric"
    assert updated["machine_type"] == "e2-standard-2"
    assert updated["idle_timeout_seconds"] == 900
    
    # Verify setMachineType was called because VM was TERMINATED
    mock_compute.instances().setMachineType.assert_called_once()
    mock_storage.objects().insert.assert_called_once()

def test_save_server_config_invalid_type():
    with pytest.raises(ValueError, match="Invalid server type"):
        save_server_config({"type": "invalid-engine"})

def test_save_server_config_invalid_machine():
    with pytest.raises(ValueError, match="Invalid machine type"):
        save_server_config({"machine_type": "invalid-machine-tier"})
