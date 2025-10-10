import pytest

try:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.api_v1.endpoints import items as items_module, users as users_module

    client = TestClient(app)
except Exception:  # pragma: no cover - skip tests when dependencies missing
    pytest.skip("FastAPI or app package not available - skipping API tests", allow_module_level=True)


def setup_function():
    # Reset in-memory fake DBs to default state before each test
    items_module.fake_items_db[:] = [
        items_module.Item(id=1, name="Laptop", description="High-performance laptop", price=999.99, is_active=True),
        items_module.Item(id=2, name="Mouse", description="Wireless mouse", price=29.99, is_active=True),
    ]
    users_module.fake_users_db[:] = [
        users_module.User(id=1, email="admin@example.com", name="Admin User", is_active=True),
        users_module.User(id=2, email="user@example.com", name="Regular User", is_active=True),
    ]


def test_root_and_health():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "version" in data

    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"


def test_get_items_list_and_get_item():
    r = client.get("/api/v1/items/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2

    r = client.get("/api/v1/items/1")
    assert r.status_code == 200
    item = r.json()
    assert item["id"] == 1
    assert item["name"] == "Laptop"


def test_create_update_delete_item():
    # Create
    payload = {"name": "Keyboard", "description": "Mechanical", "price": 79.9, "is_active": True}
    r = client.post("/api/v1/items/", json=payload)
    assert r.status_code == 201
    item = r.json()
    assert item["id"] == 3
    assert item["name"] == "Keyboard"

    # Update
    update_payload = {"description": "Mechanical, RGB", "price": 89.9}
    r = client.put("/api/v1/items/3", json=update_payload)
    assert r.status_code == 200
    updated = r.json()
    assert updated["description"] == "Mechanical, RGB"
    assert updated["price"] == 89.9

    # Delete
    r = client.delete("/api/v1/items/3")
    assert r.status_code == 200
    msg = r.json()
    assert "deleted" in msg["message"]


def test_get_users_list_and_get_user():
    r = client.get("/api/v1/users/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2

    r = client.get("/api/v1/users/1")
    assert r.status_code == 200
    user = r.json()
    assert user["id"] == 1
    assert user["email"] == "admin@example.com"


def test_create_user_and_conflict_and_delete():
    payload = {"email": "new@example.com", "name": "New User", "password": "secret"}
    r = client.post("/api/v1/users/", json=payload)
    assert r.status_code == 201
    user = r.json()
    assert user["id"] == 3
    assert user["email"] == "new@example.com"

    # Try creating with existing email
    r = client.post("/api/v1/users/", json={"email": "new@example.com", "name": "Dup", "password": "x"})
    assert r.status_code == 400

    # Delete the created user
    r = client.delete("/api/v1/users/3")
    assert r.status_code == 200
    msg = r.json()
    assert "deleted" in msg["message"]
