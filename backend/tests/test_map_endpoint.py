"""
Tests for the /api/v1/map endpoint
"""
import pytest
from fastapi.testclient import TestClient
import io

from main import app
from app.core import state

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear state before each test."""
    state.clear_map()
    yield
    state.clear_map()


def test_get_map_no_map_loaded():
    """Test GET /map/ returns 404 when no map loaded"""
    response = client.get("/api/v1/map/")
    
    assert response.status_code == 404
    assert "No map loaded" in response.json()["detail"]


def test_upload_map_success():
    """Test POST /map/ successfully uploads a valid map"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<reseau>
    <noeud id="1" latitude="45.0" longitude="-93.0"/>
    <noeud id="2" latitude="45.1" longitude="-93.1"/>
    <troncon origine="1" destination="2" longueur="1000.0" nomRue="Street 1"/>
</reseau>
"""
    
    files = {"file": ("map.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/map/", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert "intersections" in data
    assert len(data["intersections"]) == 2


def test_upload_map_empty():
    """Test POST /map/ fails with empty map"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<reseau>
</reseau>
"""
    
    files = {"file": ("map.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/map/", files=files)
    
    assert response.status_code == 400
    # The error message may vary, just check it's a 400 error
    assert "detail" in response.json()


def test_upload_map_invalid_xml():
    """Test POST /map/ fails with invalid XML"""
    xml_content = """<invalid>This is not a valid map</invalid>"""
    
    files = {"file": ("map.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/map/", files=files)
    
    assert response.status_code == 400


def test_get_map_after_upload():
    """Test GET /map/ returns map after upload"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<reseau>
    <noeud id="1" latitude="45.0" longitude="-93.0"/>
    <noeud id="2" latitude="45.1" longitude="-93.1"/>
    <troncon origine="1" destination="2" longueur="1000.0" nomRue="Street 1"/>
</reseau>
"""
    
    files = {"file": ("map.xml", xml_content.encode(), "application/xml")}
    client.post("/api/v1/map/", files=files)
    
    response = client.get("/api/v1/map/")
    
    assert response.status_code == 200
    data = response.json()
    assert "intersections" in data
    assert len(data["intersections"]) == 2


def test_upload_map_overwrites_previous():
    """Test uploading a new map overwrites the previous one"""
    xml1 = """<?xml version="1.0" encoding="UTF-8"?>
<reseau>
    <noeud id="1" latitude="45.0" longitude="-93.0"/>
</reseau>
"""
    
    xml2 = """<?xml version="1.0" encoding="UTF-8"?>
<reseau>
    <noeud id="1" latitude="45.0" longitude="-93.0"/>
    <noeud id="2" latitude="45.1" longitude="-93.1"/>
    <noeud id="3" latitude="45.2" longitude="-93.2"/>
</reseau>
"""
    
    files1 = {"file": ("map1.xml", xml1.encode(), "application/xml")}
    client.post("/api/v1/map/", files=files1)
    
    files2 = {"file": ("map2.xml", xml2.encode(), "application/xml")}
    client.post("/api/v1/map/", files=files2)
    
    response = client.get("/api/v1/map/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["intersections"]) == 3


def test_ack_pair_endpoint():
    """Test GET /map/ack_pair returns nearest nodes"""
    # First upload a map
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<reseau>
    <noeud id="1" latitude="45.0" longitude="-93.0"/>
    <noeud id="2" latitude="45.1" longitude="-93.1"/>
    <noeud id="3" latitude="45.2" longitude="-93.2"/>
</reseau>
"""
    
    files = {"file": ("map.xml", xml_content.encode(), "application/xml")}
    client.post("/api/v1/map/", files=files)
    
    # Test ack_pair
    response = client.get(
        "/api/v1/map/ack_pair",
        params={
            "pickup_lat": 45.05,
            "pickup_lng": -93.05,
            "delivery_lat": 45.15,
            "delivery_lng": -93.15
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "pickup" in data
    assert "delivery" in data
