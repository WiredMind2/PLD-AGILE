"""
Tests for the /api/v1/couriers endpoint
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core import state
from app.models.schemas import Courrier, Map, Intersection

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
        ],
        road_segments=[],
        couriers=[],
        deliveries=[],
        adjacency_list={},
    )
    state.set_map(test_map)
    return test_map


def test_list_couriers_empty(setup_map):
    """Test GET /couriers/ returns empty list initially"""
    response = client.get("/api/v1/couriers/")
    
    assert response.status_code == 200
    assert response.json() == []


def test_add_courier_success(setup_map):
    """Test POST /couriers/ successfully adds a courier"""
    courier_data = {
        "id": "c1",
        "name": "Test Courier"
    }
    
    response = client.post("/api/v1/couriers/", json=courier_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "c1"
    assert data["name"] == "Test Courier"
    
    # Verify courier was added
    couriers = state.list_couriers()
    assert len(couriers) == 1
    assert couriers[0].id == "c1"


def test_add_courier_no_map():
    """Test POST /couriers/ fails when no map loaded"""
    state.clear_map()
    
    courier_data = {
        "id": "c1",
        "name": "Test Courier"
    }
    
    response = client.post("/api/v1/couriers/", json=courier_data)
    
    assert response.status_code == 400
    assert "No map loaded" in response.json()["detail"]


def test_add_multiple_couriers(setup_map):
    """Test adding multiple couriers"""
    couriers_data = [
        {"id": "c1", "name": "Courier 1"},
        {"id": "c2", "name": "Courier 2"},
        {"id": "c3", "name": "Courier 3"},
    ]
    
    for courier_data in couriers_data:
        response = client.post("/api/v1/couriers/", json=courier_data)
        assert response.status_code == 200
    
    # Verify all couriers were added
    response = client.get("/api/v1/couriers/")
    assert response.status_code == 200
    couriers = response.json()
    assert len(couriers) == 3
    assert set(c["id"] for c in couriers) == {"c1", "c2", "c3"}


def test_delete_courier_success(setup_map):
    """Test DELETE /couriers/{courier_id} successfully deletes a courier"""
    # Add a courier first
    courier = Courrier(id="c1", name="Test Courier")
    state.add_courier(courier)
    
    response = client.delete("/api/v1/couriers/c1")
    
    assert response.status_code == 200
    assert "deleted" in response.json()["detail"]
    
    # Verify courier was deleted
    couriers = state.list_couriers()
    assert len(couriers) == 0


def test_delete_courier_not_found(setup_map):
    """Test DELETE /couriers/{courier_id} with non-existent ID"""
    response = client.delete("/api/v1/couriers/nonexistent")
    
    assert response.status_code == 404
    assert "Courier not found" in response.json()["detail"]


def test_delete_courier_from_multiple(setup_map):
    """Test deleting one courier when multiple exist"""
    # Add multiple couriers
    for i in range(3):
        courier = Courrier(id=f"c{i+1}", name=f"Courier {i+1}")
        state.add_courier(courier)
    
    # Delete one
    response = client.delete("/api/v1/couriers/c2")
    assert response.status_code == 200
    
    # Verify only the correct one was deleted
    couriers = state.list_couriers()
    assert len(couriers) == 2
    assert set(c.id for c in couriers) == {"c1", "c3"}


def test_add_courier_with_special_characters(setup_map):
    """Test adding courier with special characters in name"""
    courier_data = {
        "id": "c1",
        "name": "Courier Jean-François #1 (Priority)"
    }
    
    response = client.post("/api/v1/couriers/", json=courier_data)
    
    assert response.status_code == 200
    assert response.json()["name"] == courier_data["name"]


def test_courier_persistence_across_requests(setup_map):
    """Test that couriers persist across multiple API calls"""
    # Add courier
    courier_data = {"id": "c1", "name": "Test Courier"}
    client.post("/api/v1/couriers/", json=courier_data)
    
    # Get couriers multiple times
    for _ in range(3):
        response = client.get("/api/v1/couriers/")
        assert response.status_code == 200
        couriers = response.json()
        assert len(couriers) == 1
        assert couriers[0]["id"] == "c1"
