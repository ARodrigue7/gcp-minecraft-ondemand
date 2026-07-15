import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import templates

def test_get_whitelist_approved_html():
    """Test generating the whitelist approved HTML."""
    html = templates.get_whitelist_approved_html('TestUser')
    assert 'TestUser' in html
    assert 'Whitelist Approved' in html

def test_get_whitelist_denied_html():
    """Test generating the whitelist denied HTML."""
    html = templates.get_whitelist_denied_html('TestUser')
    assert 'TestUser' in html
    assert 'Request Denied' in html
