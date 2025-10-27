import json
import os
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


SIMPLE_MAP_XML = """
<reseau>
  <noeud id="N1" latitude="48.8566" longitude="2.3522" />
  <noeud id="N2" latitude="48.8570" longitude="2.3530" />
  <troncon origine="N1" destination="N2" longueur="100" nomRue="Rue A" />
</reseau>
"""


def test_map_upload_and_get(tmp_path):
    # upload map
    files = {"file": ("map.xml", SIMPLE_MAP_XML, "application/xml")}
    r = client.post("/api/v1/map/", files=files)
    assert r.status_code == 200
    data = r.json()
    assert "intersections" in data

    # get map
    r2 = client.get("/api/v1/map/")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["intersections"]


def test_add_courier_and_request_and_compute():
    # add a courier
    courier = "C1"
    r = client.post("/api/v1/couriers/", json=courier)
    assert r.status_code == 200

    # add a delivery request
    req = {
        "pickup_addr": "N1",
        "delivery_addr": "N2",
        "pickup_service_s": 60,
        "delivery_service_s": 60
    }
    r2 = client.post("/api/v1/requests/", json=req)
    assert r2.status_code == 200
    d = r2.json()
    assert d.get("id") is not None

    # compute tours
    r3 = client.post("/api/v1/tours/compute")
    assert r3.status_code == 200
    tours = r3.json()
    # should be a list (possibly with one tour)
    assert isinstance(tours, list)


def test_state_and_persist_load():
    r = client.get("/api/v1/state/")
    assert r.status_code == 200
    st = r.json()
    assert "map" in st and "deliveries" in st
