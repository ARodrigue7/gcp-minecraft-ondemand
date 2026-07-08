import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import gcp_client

@patch('gcp_client.get_cached_instance')
def test_get_instance_status_and_ip(mock_get_cached_instance):
    """Test get_instance_status_and_ip correctly parses status and IP."""
    mock_instance = {
        'status': 'RUNNING',
        'networkInterfaces': [
            {
                'accessConfigs': [
                    {'natIP': '1.2.3.4'}
                ]
            }
        ]
    }
    mock_get_cached_instance.return_value = mock_instance
    
    status, ip = gcp_client.get_instance_status_and_ip()
    assert status == 'RUNNING'
    assert ip == '1.2.3.4'

@patch('gcp_client.get_cached_instance')
def test_get_instance_status_and_ip_no_ip(mock_get_cached_instance):
    """Test get_instance_status_and_ip when IP is not available."""
    mock_instance = {
        'status': 'TERMINATED',
        'networkInterfaces': []
    }
    mock_get_cached_instance.return_value = mock_instance
    
    status, ip = gcp_client.get_instance_status_and_ip()
    assert status == 'TERMINATED'
    assert ip is None
