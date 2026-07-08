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
