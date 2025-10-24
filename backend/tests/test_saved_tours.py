import os
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core import state

client = TestClient(app)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'fichiersXMLPickupDelivery'))
MAP_FILE = os.path.join(DATA_DIR, 'petitPlan.xml')
REQ_FILE = os.path.join(DATA_DIR, 'demandePetit1.xml')


@pytest.fixture
def setup_state():
    """Fixture to setup a clean state with map and deliveries loaded."""
    # Clear state
    client.delete('/api/v1/state/clear_state')
    
    # Upload map
    with open(MAP_FILE, 'rb') as f:
        resp = client.post('/api/v1/map', files={'file': ('petitPlan.xml', f, 'application/xml')})
    assert resp.status_code == 200
    
    # Upload requests
    with open(REQ_FILE, 'rb') as f:
        resp = client.post('/api/v1/deliveries', files={'file': ('demandePetit1.xml', f, 'application/xml')})
    assert resp.status_code == 200
    
    yield
    
    # Cleanup
    client.delete('/api/v1/state/clear_state')


def test_save_and_load_snapshot(setup_state):
    """Test saving and loading a snapshot with map and tours."""
    # Compute tours to have complete state
    resp = client.post('/api/v1/tours/compute')
    assert resp.status_code == 200

    # Save snapshot
    resp = client.post('/api/v1/saved_tours/save', json={'name': 'unit-test-snapshot'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['detail'] == 'saved'
    assert data['name'] == 'unit-test-snapshot'
    assert 'saved_at' in data
    assert 'size_bytes' in data

    # List snapshots
    resp = client.get('/api/v1/saved_tours/')
    assert resp.status_code == 200
    lst = resp.json()
    assert isinstance(lst, list)
    assert any(item.get('name') == 'unit-test-snapshot' for item in lst)

    # Clear state and then load snapshot
    resp = client.delete('/api/v1/state/clear_state')
    assert resp.status_code == 200

    resp = client.post('/api/v1/saved_tours/load', json={'name': 'unit-test-snapshot'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['detail'] == 'loaded'
    assert 'state' in data
    st = data['state']
    assert st.get('map') is not None
    assert 'deliveries' in st and isinstance(st['deliveries'], list)
    assert 'couriers' in st and isinstance(st['couriers'], list)
    assert 'tours' in st and isinstance(st['tours'], list)


def test_list_snapshots_empty():
    """Test listing snapshots when none exist (or only system ones)."""
    resp = client.get('/api/v1/saved_tours/')
    assert resp.status_code == 200
    lst = resp.json()
    assert isinstance(lst, list)
    # May have some existing snapshots, just verify structure
    for item in lst:
        assert 'name' in item
        assert 'saved_at' in item
        assert 'size_bytes' in item


def test_save_without_name():
    """Test that saving without a name returns 400."""
    resp = client.post('/api/v1/saved_tours/save', json={})
    assert resp.status_code == 400
    assert 'name' in resp.json()['detail'].lower()


def test_save_with_empty_name():
    """Test that saving with empty name returns 400."""
    resp = client.post('/api/v1/saved_tours/save', json={'name': ''})
    assert resp.status_code == 400


def test_save_with_whitespace_name():
    """Test that saving with whitespace-only name returns 400."""
    resp = client.post('/api/v1/saved_tours/save', json={'name': '   '})
    assert resp.status_code == 400


def test_save_without_map_loaded():
    """Test that saving fails when no map is loaded."""
    # Clear state
    client.delete('/api/v1/state/clear_state')
    
    resp = client.post('/api/v1/saved_tours/save', json={'name': 'test-no-map'})
    assert resp.status_code == 400
    assert 'no map' in resp.json()['detail'].lower()


def test_save_with_special_characters_in_name(setup_state):
    """Test that special characters in names are sanitized."""
    special_name = 'test/with\\special:chars*?<>|'
    
    resp = client.post('/api/v1/saved_tours/save', json={'name': special_name})
    assert resp.status_code == 200
    data = resp.json()
    # Name should be sanitized (special chars replaced)
    assert data['name'] != special_name
    assert '/' not in data['name']
    assert '\\' not in data['name']


def test_save_with_very_long_name(setup_state):
    """Test that very long names are truncated."""
    long_name = 'a' * 200  # Very long name
    
    resp = client.post('/api/v1/saved_tours/save', json={'name': long_name})
    assert resp.status_code == 200
    data = resp.json()
    # Name should be truncated to reasonable length
    assert len(data['name']) <= 128


def test_save_overwrite_existing_snapshot(setup_state):
    """Test that saving with same name overwrites existing snapshot."""
    name = 'overwrite-test'
    
    # Save first version
    resp = client.post('/api/v1/saved_tours/save', json={'name': name})
    assert resp.status_code == 200
    first_saved_at = resp.json()['saved_at']
    
    # Save again with same name
    resp = client.post('/api/v1/saved_tours/save', json={'name': name})
    assert resp.status_code == 200
    second_saved_at = resp.json()['saved_at']
    
    # Timestamps should be different
    assert second_saved_at >= first_saved_at


def test_load_without_name():
    """Test that loading without a name returns 400."""
    resp = client.post('/api/v1/saved_tours/load', json={})
    assert resp.status_code == 400
    assert 'name' in resp.json()['detail'].lower()


def test_load_with_empty_name():
    """Test that loading with empty name returns 400."""
    resp = client.post('/api/v1/saved_tours/load', json={'name': ''})
    assert resp.status_code == 400


def test_load_nonexistent_snapshot():
    """Test that loading a non-existent snapshot returns 404."""
    resp = client.post('/api/v1/saved_tours/load', json={'name': 'nonexistent-snapshot-xyz-123'})
    assert resp.status_code == 404
    assert 'not found' in resp.json()['detail'].lower()


def test_load_snapshot_restores_state(setup_state):
    """Test that loading a snapshot correctly restores map, deliveries, and tours."""
    # Compute tours to have a complete state
    resp = client.post('/api/v1/tours/compute')
    assert resp.status_code == 200
    
    # Get current state
    resp = client.get('/api/v1/tours/')
    original_tours = resp.json()
    
    resp = client.get('/api/v1/deliveries/')
    original_deliveries = resp.json()
    
    # Save snapshot
    snapshot_name = 'restore-test'
    resp = client.post('/api/v1/saved_tours/save', json={'name': snapshot_name})
    assert resp.status_code == 200
    
    # Clear state
    resp = client.delete('/api/v1/state/clear_state')
    assert resp.status_code == 200
    
    # Verify state is cleared
    resp = client.get('/api/v1/tours/')
    assert resp.json() == []
    
    # Load snapshot
    resp = client.post('/api/v1/saved_tours/load', json={'name': snapshot_name})
    assert resp.status_code == 200
    loaded_state = resp.json()['state']
    
    # Verify deliveries are restored
    assert len(loaded_state['deliveries']) == len(original_deliveries)
    
    # Verify tours are restored
    assert len(loaded_state['tours']) == len(original_tours)


def test_multiple_snapshots(setup_state):
    """Test creating and managing multiple snapshots."""
    snapshot_names = ['snapshot-1', 'snapshot-2', 'snapshot-3']
    
    # Create multiple snapshots
    for name in snapshot_names:
        resp = client.post('/api/v1/saved_tours/save', json={'name': name})
        assert resp.status_code == 200
    
    # List all snapshots
    resp = client.get('/api/v1/saved_tours/')
    assert resp.status_code == 200
    snapshots = resp.json()
    
    # Verify all created snapshots are in the list
    snapshot_names_in_list = [s['name'] for s in snapshots]
    for name in snapshot_names:
        assert name in snapshot_names_in_list


def test_snapshot_preserves_tours_count(setup_state):
    """Test that saving and loading preserves the number of tours."""
    # Compute tours
    resp = client.post('/api/v1/tours/compute')
    assert resp.status_code == 200
    
    # Get tours count
    resp = client.get('/api/v1/tours/')
    original_tours = resp.json()
    original_count = len(original_tours)
    
    # Save snapshot
    resp = client.post('/api/v1/saved_tours/save', json={'name': 'tours-count-test'})
    assert resp.status_code == 200
    
    # Clear and reload
    client.delete('/api/v1/state/clear_state')
    resp = client.post('/api/v1/saved_tours/load', json={'name': 'tours-count-test'})
    assert resp.status_code == 200
    
    loaded_tours = resp.json()['state']['tours']
    assert len(loaded_tours) == original_count


def test_snapshot_metadata_fields(setup_state):
    """Test that snapshot metadata contains all required fields."""
    # Save snapshot
    resp = client.post('/api/v1/saved_tours/save', json={'name': 'metadata-test'})
    assert resp.status_code == 200
    save_data = resp.json()
    
    # Check save response
    assert 'detail' in save_data
    assert 'name' in save_data
    assert 'saved_at' in save_data
    assert 'size_bytes' in save_data
    assert save_data['size_bytes'] > 0
    
    # Check list response
    resp = client.get('/api/v1/saved_tours/')
    snapshots = resp.json()
    metadata_test = [s for s in snapshots if s['name'] == 'metadata-test']
    assert len(metadata_test) > 0
    
    snapshot = metadata_test[0]
    assert 'name' in snapshot
    assert 'saved_at' in snapshot
    assert 'size_bytes' in snapshot


def test_save_with_null_payload():
    """Test handling of null/None payload."""
    resp = client.post('/api/v1/saved_tours/save', json=None)
    # FastAPI returns 422 for validation errors with null payload
    assert resp.status_code == 422


def test_load_with_null_payload():
    """Test handling of null/None payload for load."""
    resp = client.post('/api/v1/saved_tours/load', json=None)
    # FastAPI returns 422 for validation errors with null payload
    assert resp.status_code == 422


def test_snapshot_ordering():
    """Test that snapshots are ordered by most recent first."""
    # Create snapshots with slight delays
    import time
    
    client.delete('/api/v1/state/clear_state')
    with open(MAP_FILE, 'rb') as f:
        client.post('/api/v1/map', files={'file': ('petitPlan.xml', f, 'application/xml')})
    
    names = ['oldest', 'middle', 'newest']
    for name in names:
        client.post('/api/v1/saved_tours/save', json={'name': name})
        time.sleep(0.1)  # Small delay to ensure different timestamps
    
    # Get list
    resp = client.get('/api/v1/saved_tours/')
    snapshots = resp.json()
    
    # Find our test snapshots
    test_snapshots = [s for s in snapshots if s['name'] in names]
    
    # Verify they are in reverse chronological order
    if len(test_snapshots) == 3:
        # Should be: newest, middle, oldest
        assert test_snapshots[0]['saved_at'] >= test_snapshots[1]['saved_at']
        assert test_snapshots[1]['saved_at'] >= test_snapshots[2]['saved_at']


def test_load_corrupted_snapshot(setup_state, tmp_path):
    """Test handling of corrupted snapshot file."""
    import pickle
    import os
    from app.core import state as state_module
    
    # Save a valid snapshot first
    resp = client.post('/api/v1/saved_tours/save', json={'name': 'valid-snapshot'})
    assert resp.status_code == 200
    
    # Create a corrupted snapshot file by writing invalid pickle data
    # Get the snapshots directory from state module
    saved_dir = state_module._saved_dir
    corrupt_file = os.path.join(saved_dir, 'corrupt-test.pkl')
    
    # Write corrupted data
    with open(corrupt_file, 'wb') as f:
        f.write(b'This is not valid pickle data!!!')
    
    # Try to load the corrupted snapshot
    resp = client.post('/api/v1/saved_tours/load', json={'name': 'corrupt-test'})
    # Should fail with 400 due to pickle error
    assert resp.status_code == 400
    
    # Clean up
    try:
        os.remove(corrupt_file)
    except:
        pass
