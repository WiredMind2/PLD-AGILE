"""
Tests for error handlers
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core import state

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear state before each test."""
    state.clear_map()
    yield
    state.clear_map()


def test_http_exception_handler_404():
    """Test that HTTPException returns proper error format"""
    # Try to get a map when none is loaded
    response = client.get("/api/v1/map/")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "detail" in data
    assert data["error"] == "http_exception"


def test_http_exception_handler_400():
    """Test that HTTPException 400 returns proper error format"""
    # Try to add a request without a map
    request_data = {
        "pickup_addr": "1",
        "delivery_addr": "2",
        "pickup_service_s": 300,
        "delivery_service_s": 600
    }
    
    response = client.post("/api/v1/requests/", json=request_data)
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "detail" in data
    assert data["error"] == "http_exception"


def test_validation_exception_handler():
    """Test that validation errors return proper error format"""
    # Send invalid data to an endpoint that expects specific types
    invalid_request = {
        "pickup_addr": "1",
        "delivery_addr": "2",
        "pickup_service_s": "not_a_number",  # Should be int
        "delivery_service_s": "not_a_number"  # Should be int
    }
    
    response = client.post("/api/v1/requests/", json=invalid_request)
    
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"] == "validation_error"


def test_error_response_structure():
    """Test that error responses have consistent structure"""
    response = client.get("/api/v1/map/")
    
    assert response.status_code == 404
    data = response.json()
    
    # Check structure
    assert isinstance(data, dict)
    assert "error" in data
    assert "detail" in data
    assert "status_code" in data
    assert data["status_code"] == 404
