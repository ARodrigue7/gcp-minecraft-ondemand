import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import discord_webhook

@patch('discord_webhook.DISCORD_WEBHOOK_URL', 'http://fake-webhook')
@patch('discord_webhook.urllib.request.urlopen')
def test_send_discord_webhook_success(mock_urlopen):
    """Test successful Discord webhook transmission."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"id": "123"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    result = discord_webhook.send_discord_webhook('TestUser', 'http://status.url')
    assert result is True
    assert mock_urlopen.call_count == 2

@patch('discord_webhook.DISCORD_WEBHOOK_URL', None)
@patch('discord_webhook.urllib.request.urlopen')
def test_send_discord_webhook_missing_url(mock_urlopen):
    """Test webhook fails gracefully when URL is not configured."""
    result = discord_webhook.send_discord_webhook('TestUser', 'http://status.url')
    assert result is False
    mock_urlopen.assert_not_called()

@patch('discord_webhook.DISCORD_WEBHOOK_URL', 'http://fake-webhook')
@patch('discord_webhook.urllib.request.urlopen')
def test_send_discord_webhook_http_error(mock_urlopen):
    """Test webhook handles HTTP errors gracefully."""
    mock_urlopen.side_effect = Exception("HTTP Error")
    
    result = discord_webhook.send_discord_webhook('TestUser', 'http://status.url')
    assert result is False
    mock_urlopen.assert_called_once()
