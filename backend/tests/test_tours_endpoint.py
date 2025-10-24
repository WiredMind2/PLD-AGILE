"""
Tests for the /api/v1/tours endpoint
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core import state
from app.models.schemas import (
    Courrier, Delivery, Map, Intersection, RoadSegment, Tour
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear state before each test."""
    state.clear_map()
    yield
    state.clear_map()


@pytest.fixture
def setup_map_with_deliveries():
    """Setup a map with intersections, roads, couriers, and deliveries for testing."""
    # Create intersections
    int1 = Intersection(id="1", latitude=45.0, longitude=-93.0)
    int2 = Intersection(id="2", latitude=45.1, longitude=-93.1)
    int3 = Intersection(id="3", latitude=45.2, longitude=-93.2)
    int4 = Intersection(id="4", latitude=45.3, longitude=-93.3)
    
    test_map = Map(
        intersections=[int1, int2, int3, int4],
        road_segments=[
            RoadSegment(start=int1, end=int2, length_m=1000.0, travel_time_s=240, street_name="Street 1"),
            RoadSegment(start=int2, end=int3, length_m=1500.0, travel_time_s=360, street_name="Street 2"),
            RoadSegment(start=int3, end=int4, length_m=1200.0, travel_time_s=288, street_name="Street 3"),
            RoadSegment(start=int1, end=int3, length_m=2000.0, travel_time_s=480, street_name="Street 4"),
        ],
        couriers=[],
        deliveries=[],
        adjacency_list={},
    )
    state.set_map(test_map)
    
    # Add a courier
    courier = Courrier(id="c1", name="Test Courier")
    state.add_courier(courier)
    
    # Add deliveries
    delivery1 = Delivery(
        id="d1",
        pickup_addr="2",
        delivery_addr="3",
        pickup_service_s=300,
        delivery_service_s=600,
    )
    delivery2 = Delivery(
        id="d2",
        pickup_addr="1",
        delivery_addr="4",
        pickup_service_s=300,
        delivery_service_s=600,
    )
    state.add_delivery(delivery1)
    state.add_delivery(delivery2)
    
    return test_map


def test_list_tours_empty():
    """Test GET /tours/ returns empty list initially"""
    response = client.get("/api/v1/tours/")
    
    assert response.status_code == 200
    assert response.json() == []


def test_compute_tour_no_map():
    """Test POST /tours/compute/{courier_id} fails when no map loaded"""
    state.clear_map()
    
    response = client.post("/api/v1/tours/compute/c1")
    
    assert response.status_code == 400
    assert "No map loaded" in response.json()["detail"]


def test_compute_all_tours_no_map():
    """Test POST /tours/compute fails when no map loaded"""
    state.clear_map()
    
    response = client.post("/api/v1/tours/compute")
    
    assert response.status_code == 400
    assert "No map loaded" in response.json()["detail"]


def test_compute_tour_success(setup_map_with_deliveries):
    """Test POST /tours/compute/{courier_id} successfully computes tours"""
    response = client.post("/api/v1/tours/compute/c1")
    
    assert response.status_code == 200
    tours = response.json()
    assert isinstance(tours, list)


def test_compute_all_tours_success(setup_map_with_deliveries):
    """Test POST /tours/compute successfully computes tours for all couriers"""
    response = client.post("/api/v1/tours/compute")
    
    assert response.status_code == 200
    tours = response.json()
    assert isinstance(tours, list)


def test_list_tours_after_compute(setup_map_with_deliveries):
    """Test that tours are listed after computation"""
    # Compute tours
    compute_response = client.post("/api/v1/tours/compute")
    assert compute_response.status_code == 200
    
    # List tours
    list_response = client.get("/api/v1/tours/")
    assert list_response.status_code == 200
    tours = list_response.json()
    assert isinstance(tours, list)


def test_get_tour_for_courier(setup_map_with_deliveries):
    """Test GET /tours/{courier_id} returns tours for specific courier"""
    # Assign deliveries to courier c1
    mp = state.get_map()
    if mp:
        courier = next((c for c in mp.couriers if c.id == "c1"), None)
        state.update_delivery("d1", courier=courier)
        state.update_delivery("d2", courier=courier)
    
    # Compute tours
    client.post("/api/v1/tours/compute")
    
    # Get tours for specific courier
    response = client.get("/api/v1/tours/c1")
    
    assert response.status_code == 200
    tours = response.json()
    assert isinstance(tours, list)
    # All tours should belong to courier c1
    for tour in tours:
        assert tour["courier"]["id"] == "c1"


def test_get_tour_for_nonexistent_courier(setup_map_with_deliveries):
    """Test GET /tours/{courier_id} fails when courier has no tours"""
    # Add another courier without computing tours
    courier2 = Courrier(id="c2", name="Courier 2")
    state.add_courier(courier2)
    
    response = client.get("/api/v1/tours/c2")
    
    assert response.status_code == 404
    assert "No tour found for courier" in response.json()["detail"]


def test_save_tours(setup_map_with_deliveries):
    """Test POST /tours/save acknowledges save request"""
    response = client.post("/api/v1/tours/save")
    
    assert response.status_code == 200
    assert "tours saved" in response.json()["detail"]


def test_compute_tours_multiple_couriers(setup_map_with_deliveries):
    """Test computing tours with multiple couriers"""
    # Add more couriers
    courier2 = Courrier(id="c2", name="Courier 2")
    courier3 = Courrier(id="c3", name="Courier 3")
    state.add_courier(courier2)
    state.add_courier(courier3)
    
    # Compute tours
    response = client.post("/api/v1/tours/compute")
    
    assert response.status_code == 200
    tours = response.json()
    assert isinstance(tours, list)


def test_compute_tour_with_assigned_deliveries(setup_map_with_deliveries):
    """Test computing tours when deliveries are assigned to courier"""
    # Assign deliveries to courier
    mp = state.get_map()
    if mp:
        courier = next((c for c in mp.couriers if c.id == "c1"), None)
        
        state.update_delivery("d1", courier=courier)
        state.update_delivery("d2", courier=courier)
    
    # Compute tours
    response = client.post("/api/v1/tours/compute/c1")
    
    assert response.status_code == 200
    tours = response.json()
    assert isinstance(tours, list)


def test_tours_persistence(setup_map_with_deliveries):
    """Test that computed tours persist in state"""
    # Compute tours
    client.post("/api/v1/tours/compute")
    
    # Get tours multiple times to ensure persistence
    for _ in range(3):
        response = client.get("/api/v1/tours/")
        assert response.status_code == 200
        tours = response.json()
        assert isinstance(tours, list)


def test_get_tour_empty_courier_id():
    """Test GET /tours/{courier_id} with empty string courier_id"""
    # Setup minimal map
    test_map = Map(
        intersections=[Intersection(id="1", latitude=45.0, longitude=-93.0)],
        road_segments=[],
        couriers=[],
        deliveries=[],
        adjacency_list={},
    )
    state.set_map(test_map)
    
    response = client.get("/api/v1/tours/")
    
    assert response.status_code == 200
    assert response.json() == []
