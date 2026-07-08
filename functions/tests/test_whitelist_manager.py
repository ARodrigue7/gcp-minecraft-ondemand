import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import whitelist_manager

@patch('whitelist_manager.get_cached_instance')
def test_get_whitelist_states_success(mock_get_cached_instance):
    """Test retrieving whitelist states successfully."""
    mock_instance = {
        'metadata': {
            'items': [
                {'key': 'approved-whitelist', 'value': 'Player1,Player2'},
                {'key': 'pending-whitelist', 'value': 'Player3'}
            ]
        }
    }
    mock_get_cached_instance.return_value = mock_instance
    
    approved, pending = whitelist_manager.get_whitelist_states()
    assert 'Player1' in approved
    assert 'Player2' in approved
    assert 'Player3' in pending
    assert len(approved) == 2
    assert len(pending) == 1

@patch('whitelist_manager.get_cached_instance')
def test_get_whitelist_states_error(mock_get_cached_instance):
    """Test retrieving whitelist states handles API errors."""
    mock_get_cached_instance.side_effect = Exception("API Error")
    
    approved, pending = whitelist_manager.get_whitelist_states()
    assert approved == []
    assert pending == []

@patch('whitelist_manager.invalidate_instance_cache')
@patch('whitelist_manager.compute')
@patch('whitelist_manager.get_cached_instance')
def test_update_whitelist_state(mock_get_cached_instance, mock_compute, mock_invalidate):
    """Test updating whitelist state atomically."""
    mock_instance = {
        'metadata': {
            'fingerprint': 'xyz',
            'items': [
                {'key': 'approved-whitelist', 'value': 'Player1'},
                {'key': 'pending-whitelist', 'value': 'Player2'}
            ]
        }
    }
    mock_get_cached_instance.return_value = mock_instance
    
    mock_set_metadata = MagicMock()
    mock_compute.instances().setMetadata.return_value = mock_set_metadata
    
    whitelist_manager.update_whitelist_state('Player2', 'approve')
    
    mock_compute.instances().setMetadata.assert_called_once()
    mock_set_metadata.execute.assert_called_once()
    mock_invalidate.assert_called_once()
