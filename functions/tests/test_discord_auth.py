import os
import sys
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import discord_auth

@patch('discord_auth.WHITELIST_SECRET', 'my_super_secret')
def test_generate_signature_success():
    """Test standard signature generation."""
    sig = discord_auth.generate_signature('ArodPlayerLocal')
    assert sig is not None
    assert len(sig) > 0

@patch('discord_auth.WHITELIST_SECRET', 'my_super_secret')
def test_generate_signature_empty_username():
    """Test generating a signature for an empty username string."""
    with pytest.raises(ValueError):
        discord_auth.generate_signature('')

@patch('discord_auth.WHITELIST_SECRET', None)
def test_generate_signature_missing_secret():
    """Test generating a signature when the secret is missing."""
    with pytest.raises(ValueError):
        discord_auth.generate_signature('ArodPlayerLocal')
