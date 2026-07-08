import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import socket

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

@patch('gcp_client.compute')
def test_start_instance(mock_compute):
    """Test starting instance triggers compute start request."""
    mock_start = MagicMock()
    mock_compute.instances().start.return_value = mock_start
    
    gcp_client.start_instance()
    mock_compute.instances().start.assert_called_once()
    mock_start.execute.assert_called_once()

@patch('socket.socket')
def test_is_minecraft_ready_success(mock_socket_class):
    """Test is_minecraft_ready returns True when socket successfully connects."""
    mock_socket = MagicMock()
    mock_socket_class.return_value = mock_socket
    
    result = gcp_client.is_minecraft_ready('1.2.3.4')
    assert result is True
    mock_socket.connect.assert_called_once_with(('1.2.3.4', 25565))

@patch('socket.socket')
def test_is_minecraft_ready_failure(mock_socket_class):
    """Test is_minecraft_ready returns False when socket raises an error."""
    mock_socket = MagicMock()
    mock_socket.connect.side_effect = Exception("Connection refused")
    mock_socket_class.return_value = mock_socket
    
    result = gcp_client.is_minecraft_ready('1.2.3.4')
    assert result is False

def test_is_minecraft_ready_no_ip():
    """Test is_minecraft_ready returns False immediately if IP is empty."""
    assert gcp_client.is_minecraft_ready('') is False

@patch('gcp_client.DNS_PROVIDER', 'none')
def test_update_dns_record_none():
    """Test update_dns_record returns immediately when DNS provider is 'none'."""
    # Should not raise any errors or trigger any requests
    gcp_client.update_dns_record('1.2.3.4')

@patch('gcp_client.DNS_PROVIDER', 'google')
@patch('gcp_client.dns')
def test_update_dns_record_google_no_change(mock_dns):
    """Test Google DNS update skips when IP is already correct."""
    mock_list_request = MagicMock()
    mock_list_request.execute.return_value = {
        'rrsets': [
            {'name': 'my-mc-domain.', 'type': 'A', 'rrdatas': ['1.2.3.4']}
        ]
    }
    mock_dns.resourceRecordSets().list.return_value = mock_list_request
    
    with patch('gcp_client.DOMAIN_NAME', 'my-mc-domain.'):
        gcp_client.update_dns_record('1.2.3.4')
        mock_dns.changes().create.assert_not_called()

@patch('gcp_client.DNS_PROVIDER', 'google')
@patch('gcp_client.dns')
def test_update_dns_record_google_change(mock_dns):
    """Test Google DNS updates record when IP changes."""
    mock_list_request = MagicMock()
    mock_list_request.execute.return_value = {
        'rrsets': [
            {'name': 'my-mc-domain.', 'type': 'A', 'rrdatas': ['9.9.9.9']}
        ]
    }
    mock_dns.resourceRecordSets().list.return_value = mock_list_request
    
    mock_create_request = MagicMock()
    mock_dns.changes().create.return_value = mock_create_request
    
    with patch('gcp_client.DOMAIN_NAME', 'my-mc-domain.'):
        gcp_client.update_dns_record('1.2.3.4')
        mock_dns.changes().create.assert_called_once()
        mock_create_request.execute.assert_called_once()

@patch('gcp_client.DNS_PROVIDER', 'google')
@patch('gcp_client.dns')
def test_update_dns_record_google_error(mock_dns):
    """Test Google DNS list try-except block logs and raises exception."""
    mock_dns.resourceRecordSets().list.side_effect = Exception("API Error")
    
    with patch('gcp_client.DOMAIN_NAME', 'my-mc-domain.'):
        with pytest.raises(Exception):
            gcp_client.update_dns_record('1.2.3.4')

@patch('gcp_client.DNS_PROVIDER', 'cloudflare')
@patch('urllib.request.urlopen')
def test_update_dns_record_cloudflare_success(mock_urlopen):
    """Test Cloudflare DNS update via urllib mock."""
    mock_res_get = MagicMock()
    mock_res_get.read.return_value = b'{"result":[{"id":"rec123","content":"9.9.9.9"}]}'
    
    mock_res_put = MagicMock()
    mock_res_put.read.return_value = b'{"success":true}'
    
    mock_urlopen.side_effect = [
        MagicMock(__enter__=MagicMock(return_value=mock_res_get)),
        MagicMock(__enter__=MagicMock(return_value=mock_res_put))
    ]
    
    gcp_client.update_dns_record('1.2.3.4')
    assert mock_urlopen.call_count == 2

@patch('gcp_client.DNS_PROVIDER', 'duckdns')
@patch('urllib.request.urlopen')
def test_update_dns_record_duckdns_success(mock_urlopen):
    """Test DuckDNS update via urllib mock."""
    mock_res = MagicMock()
    mock_res.read.return_value = b'OK'
    mock_urlopen.return_value.__enter__.return_value = mock_res
    
    gcp_client.update_dns_record('1.2.3.4')
    mock_urlopen.assert_called_once()

@patch('gcp_client.DNS_PROVIDER', 'dynu')
@patch('urllib.request.urlopen')
def test_update_dns_record_dynu_success(mock_urlopen):
    """Test Dynu update via urllib mock."""
    mock_res = MagicMock()
    mock_res.read.return_value = b'good 1.2.3.4'
    mock_urlopen.return_value.__enter__.return_value = mock_res
    
    gcp_client.update_dns_record('1.2.3.4')
    mock_urlopen.assert_called_once()
