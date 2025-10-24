"""Additional tests for requests endpoint"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import io
from app.models.schemas import Map, Delivery, Courrier, Intersection
from app.core import state
from main import app

client = TestClient(app)


@pytest.fixture
def setup_map():
    """Setup a test map"""
    map_obj = Map(
        intersections=[
            Intersection(id="1", latitude=45.0, longitude=-93.0),
            Intersection(id="2", latitude=45.1, longitude=-93.1),
        ],
        road_segments=[]
    )
    state.set_map(map_obj)
    yield map_obj
    state.clear_state()


def test_list_requests_endpoint(setup_map):
    """Test GET /requests/ endpoint"""
    # Add some deliveries
    delivery = Delivery(id="d1", pickup_addr="1", delivery_addr="2", pickup_service_s=300, delivery_service_s=600)
    state.add_delivery(delivery)
    
    response = client.get("/api/v1/requests/")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_add_request_endpoint(setup_map):
    """Test POST /requests/ endpoint"""
    request_data = {
        "pickup_addr": "1",
        "delivery_addr": "2",
        "pickup_service_s": 300,
        "delivery_service_s": 600
    }
    
    response = client.post("/api/v1/requests/", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["pickup_addr"] == "1"
    assert data["delivery_addr"] == "2"
    assert "id" in data


def test_add_request_no_map():
    """Test POST /requests/ fails when no map loaded"""
    state.clear_map()
    
    request_data = {
        "pickup_addr": "1",
        "delivery_addr": "2",
        "pickup_service_s": 300,
        "delivery_service_s": 600
    }
    
    response = client.post("/api/v1/requests/", json=request_data)
    
    assert response.status_code == 400
    assert "No map loaded" in response.json()["detail"]


def test_delete_request_endpoint(setup_map):
    """Test DELETE /requests/{delivery_id} endpoint"""
    # Add a delivery first
    delivery = Delivery(id="d1", pickup_addr="1", delivery_addr="2", pickup_service_s=300, delivery_service_s=600)
    state.add_delivery(delivery)
    
    response = client.delete("/api/v1/requests/d1")
    
    assert response.status_code == 200
    assert "deleted" in response.json()["detail"]
    
    # Verify it's deleted
    deliveries = state.list_deliveries()
    assert not any(d.id == "d1" for d in deliveries)


def test_delete_request_not_found(setup_map):
    """Test DELETE /requests/{delivery_id} with non-existent ID"""
    response = client.delete("/api/v1/requests/nonexistent")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_upload_requests_file_endpoint(setup_map):
    """Test POST /requests/upload endpoint"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<livraisons>
    <livraison adresseEnlevement="1" adresseLivraison="2" 
               dureeEnlevement="300" dureeLivraison="600"/>
</livraisons>
"""
    
    files = {"file": ("deliveries.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/requests/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_upload_requests_file_empty(setup_map):
    """Test POST /requests/upload with empty XML"""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<livraisons>
</livraisons>
"""
    
    files = {"file": ("deliveries.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/requests/upload", files=files)
    
    assert response.status_code == 400
    assert "No deliveries parsed" in response.json()["detail"]


def test_upload_requests_file_invalid_xml(setup_map):
    """Test POST /requests/upload with invalid XML"""
    xml_content = "This is not valid XML"
    
    files = {"file": ("deliveries.xml", xml_content.encode(), "application/xml")}
    response = client.post("/api/v1/requests/upload", files=files)
    
    assert response.status_code == 400


def test_assign_courier_to_delivery(setup_map):
    """Test PATCH /requests/{delivery_id}/assign endpoint"""
    # Add a courier
    courier = Courrier(id="c1", name="Test Courier")
    state.add_courier(courier)
    
    # Add a delivery
    delivery = Delivery(id="d1", pickup_addr="1", delivery_addr="2", pickup_service_s=300, delivery_service_s=600)
    state.add_delivery(delivery)
    
    # Assign courier
    response = client.patch("/api/v1/requests/d1/assign", json={"courier_id": "c1"})
    
    assert response.status_code == 200
    assert "assigned" in response.json()["detail"]
    
    # Verify assignment
    deliveries = state.list_deliveries()
    delivery = next((d for d in deliveries if d.id == "d1"), None)
    assert delivery is not None
    assert delivery.courier is not None
    assert delivery.courier.id == "c1"


def test_assign_courier_unassign(setup_map):
    """Test unassigning a courier from delivery"""
    # Add a courier
    courier = Courrier(id="c1", name="Test Courier")
    state.add_courier(courier)
    
    # Add a delivery with courier
    delivery = Delivery(id="d1", pickup_addr="1", delivery_addr="2", pickup_service_s=300, delivery_service_s=600, courier=courier)
    state.add_delivery(delivery)
    
    # Unassign courier
    response = client.patch("/api/v1/requests/d1/assign", json={"courier_id": None})
    
    assert response.status_code == 200
    
    # Verify unassignment
    deliveries = state.list_deliveries()
    delivery = next((d for d in deliveries if d.id == "d1"), None)
    assert delivery is not None
    assert delivery.courier is None


def test_assign_courier_no_map():
    """Test PATCH /requests/{delivery_id}/assign fails when no map"""
    state.clear_map()
    
    response = client.patch("/api/v1/requests/d1/assign", json={"courier_id": "c1"})
    
    assert response.status_code == 400
    assert "No map loaded" in response.json()["detail"]


def test_assign_courier_not_found(setup_map):
    """Test PATCH /requests/{delivery_id}/assign with non-existent courier"""
    # Add a delivery
    delivery = Delivery(id="d1", pickup_addr="1", delivery_addr="2", pickup_service_s=300, delivery_service_s=600)
    state.add_delivery(delivery)
    
    # Try to assign non-existent courier
    response = client.patch("/api/v1/requests/d1/assign", json={"courier_id": "nonexistent"})
    
    assert response.status_code == 404
    assert "Courier not found" in response.json()["detail"]


def test_assign_courier_delivery_not_found(setup_map):
    """Test PATCH /requests/{delivery_id}/assign with non-existent delivery"""
    # Add a courier
    courier = Courrier(id="c1", name="Test Courier")
    state.add_courier(courier)
    
    # Try to assign to non-existent delivery
    response = client.patch("/api/v1/requests/nonexistent/assign", json={"courier_id": "c1"})
    
    assert response.status_code == 404
    assert "Delivery not found" in response.json()["detail"]
