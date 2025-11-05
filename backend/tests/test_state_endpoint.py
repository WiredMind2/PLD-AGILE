"""
Tests for the /api/v1/state endpoint
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core import state
from app.models.schemas import Map, Intersection, Delivery

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


def test_get_state_no_map():
    """Test GET /state/ returns empty state when no map loaded"""
    response = client.get("/api/v1/state/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["map"] is None
    assert data["couriers"] == []
    assert data["deliveries"] == []
    assert data["tours"] == []


def test_get_state_with_map(setup_map):
    """Test GET /state/ returns state with map"""
    response = client.get("/api/v1/state/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["map"] is not None
    assert len(data["map"]["intersections"]) == 2


def test_clear_state(setup_map):
    """Test DELETE /state/clear_state clears all state"""
    # Add some data
    delivery = Delivery(
        id="d1",
        pickup_addr="1",
        delivery_addr="2",
        pickup_service_s=300,
        delivery_service_s=600
    )
    state.add_delivery(delivery)
    
    response = client.delete("/api/v1/state/clear_state")
    
    assert response.status_code == 200
    assert "state cleared" in response.json()["detail"]
    
    # Verify state is cleared
    state_response = client.get("/api/v1/state/")
    data = state_response.json()
    assert data["map"] is None
    assert data["couriers"] == []
    assert data["deliveries"] == []


def test_save_state_with_name(setup_map):
    """Test POST /state/save saves state with custom name"""
    response = client.post("/api/v1/state/save", json={"name": "test-snapshot"})
    
    assert response.status_code == 200
    assert "saved" in response.json()["detail"]


def test_save_state_default_name(setup_map):
    """Test POST /state/save saves state with default name"""
    response = client.post("/api/v1/state/save", json={})
    
    assert response.status_code == 200
    assert "saved" in response.json()["detail"]


def test_load_state_nonexistent():
    """Test POST /state/load fails with nonexistent snapshot"""
    response = client.post("/api/v1/state/load", json={"name": "nonexistent-xyz-123"})
    
    assert response.status_code == 404
    assert "Snapshot not found" in response.json()["detail"]


def test_save_and_load_state(setup_map):
    """Test saving and loading state works correctly"""
    # Add some data
    delivery = Delivery(
        id="d1",
        pickup_addr="1",
        delivery_addr="2",
        pickup_service_s=300,
        delivery_service_s=600
    )
    state.add_delivery(delivery)

    # Add a courier
    state.add_courier("c1")

    # Save state
    save_response = client.post("/api/v1/state/save", json={"name": "test-save-load"})
    assert save_response.status_code == 200

    # Clear state
    client.delete("/api/v1/state/clear_state")

    # Load state
    load_response = client.post("/api/v1/state/load", json={"name": "test-save-load"})
    assert load_response.status_code == 200
    assert "loaded" in load_response.json()["detail"]

    # Verify state was restored
    state_response = client.get("/api/v1/state/")
    data = state_response.json()
    assert len(data["couriers"]) == 1
    assert data["couriers"][0] == "c1"


def test_get_travel_speed():
    """Test GET /state/get_travel_speed returns speed setting"""
    response = client.get("/api/v1/state/get_travel_speed")
    
    assert response.status_code == 200
    data = response.json()
    assert "travel_speed" in data
    assert isinstance(data["travel_speed"], (int, float))
