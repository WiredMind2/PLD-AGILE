"""
Tests for the /api/v1/deliveries endpoint
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core import state
from app.models.schemas import Map, Intersection

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear state before each test."""
    state.clear_map()
    yield
    state.clear_map()


@pytest.fixture
def setup_map():
    """Setup a basic map for testing."""
    test_map = Map(
        intersections=[
            Intersection(id="1", latitude=45.0, longitude=-93.0),
            Intersection(id="2", latitude=45.1, longitude=-93.1),
            Intersection(id="3", latitude=45.2, longitude=-93.2),
        ],
        road_segments=[],
        couriers=[],
        deliveries=[],
        adjacency_list={},
    )
    state.set_map(test_map)
    return test_map


def test_list_deliveries_empty(setup_map):
    """Test GET /deliveries/ returns empty list initially"""
    response = client.get("/api/v1/deliveries/")
    
    assert response.status_code == 200
    assert response.json() == []


def test_upload_deliveries_success(setup_map):
    """Test POST /deliveries/ successfully uploads deliveries"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<livraisons>
    <livraison adresseEnlevement="1" adresseLivraison="2" dureeEnlevement="300" dureeLivraison="600"/>
    <livraison adresseEnlevement="2" adresseLivraison="3" dureeEnlevement="400" dureeLivraison="500"/>
</livraisons>
"""
    
    files = {"file": ("deliveries.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/deliveries/", files=files)
    
    assert response.status_code == 200
    deliveries = response.json()
    assert isinstance(deliveries, list)
    assert len(deliveries) == 2


def test_upload_deliveries_empty():
    """Test POST /deliveries/ fails with empty XML"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<livraisons>
</livraisons>
"""
    
    files = {"file": ("deliveries.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/deliveries/", files=files)
    
    assert response.status_code == 400
    assert "No deliveries parsed" in response.json()["detail"]


def test_upload_deliveries_invalid_xml():
    """Test POST /deliveries/ fails with invalid XML"""
    xml_content = """<invalid>Not a valid deliveries file</invalid>"""
    
    files = {"file": ("deliveries.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/deliveries/", files=files)
    
    assert response.status_code == 400


def test_list_deliveries_after_upload(setup_map):
    """Test GET /deliveries/ returns deliveries after upload"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<livraisons>
    <livraison adresseEnlevement="1" adresseLivraison="2" dureeEnlevement="300" dureeLivraison="600"/>
</livraisons>
"""
    
    files = {"file": ("deliveries.xml", xml_content.encode(), "application/xml")}
    client.post("/api/v1/deliveries/", files=files)
    
    response = client.get("/api/v1/deliveries/")
    
    assert response.status_code == 200
    deliveries = response.json()
    assert len(deliveries) == 1


def test_upload_multiple_deliveries_files(setup_map):
    """Test uploading multiple delivery files adds to existing deliveries"""
    xml1 = """<?xml version="1.0" encoding="UTF-8"?>
<livraisons>
    <livraison adresseEnlevement="1" adresseLivraison="2" dureeEnlevement="300" dureeLivraison="600"/>
</livraisons>
"""
    
    xml2 = """<?xml version="1.0" encoding="UTF-8"?>
<livraisons>
    <livraison adresseEnlevement="2" adresseLivraison="3" dureeEnlevement="400" dureeLivraison="500"/>
</livraisons>
"""
    
    files1 = {"file": ("deliveries1.xml", xml1.encode(), "application/xml")}
    client.post("/api/v1/deliveries/", files=files1)
    
    files2 = {"file": ("deliveries2.xml", xml2.encode(), "application/xml")}
    client.post("/api/v1/deliveries/", files=files2)
    
    response = client.get("/api/v1/deliveries/")
    assert response.status_code == 200
    deliveries = response.json()
    assert len(deliveries) == 2
