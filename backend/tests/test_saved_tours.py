import os
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'fichiersXMLPickupDelivery'))
MAP_FILE = os.path.join(DATA_DIR, 'petitPlan.xml')
REQ_FILE = os.path.join(DATA_DIR, 'demandePetit1.xml')


def test_save_and_load_snapshot(tmp_path):
    # Clear state
    resp = client.delete('/api/v1/state/clear_state')
    assert resp.status_code == 200

    # Upload map
    assert os.path.isfile(MAP_FILE), f"Missing map file: {MAP_FILE}"
    with open(MAP_FILE, 'rb') as f:
        resp = client.post('/api/v1/map', files={'file': ('petitPlan.xml', f, 'application/xml')})
    assert resp.status_code == 200

    # Upload requests
    assert os.path.isfile(REQ_FILE), f"Missing request file: {REQ_FILE}"
    with open(REQ_FILE, 'rb') as f:
        resp = client.post('/api/v1/deliveries', files={'file': ('demandePetit1.xml', f, 'application/xml')})
    assert resp.status_code == 200

    # Compute tours (optional, but ensures tours exist to be saved)
    resp = client.post('/api/v1/tours/compute')
    assert resp.status_code == 200

    # Save snapshot
    resp = client.post('/api/v1/saved_tours/save', json={'name': 'unit-test-snapshot'})
    assert resp.status_code == 200

    # List snapshots
    resp = client.get('/api/v1/saved_tours/')
    assert resp.status_code == 200
    lst = resp.json()
    assert any(item.get('name') == 'unit-test-snapshot' for item in lst)

    # Clear state and then load snapshot
    resp = client.delete('/api/v1/state/clear_state')
    assert resp.status_code == 200

    resp = client.post('/api/v1/saved_tours/load', json={'name': 'unit-test-snapshot'})
    assert resp.status_code == 200
    data = resp.json()
    assert 'state' in data
    st = data['state']
    assert st.get('map') is not None
    # tours may be empty if compute couldn't run fully; we just ensure keys exist
    assert 'deliveries' in st and isinstance(st['deliveries'], list)
    assert 'couriers' in st and isinstance(st['couriers'], list)
