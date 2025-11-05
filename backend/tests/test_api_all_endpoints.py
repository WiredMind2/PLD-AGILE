import io
import os
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SIMPLE_MAP_XML = """
<reseau>
  <noeud id="N1" latitude="48.8566" longitude="2.3522" />
  <noeud id="N2" latitude="48.8570" longitude="2.3530" />
  <noeud id="N3" latitude="48.8575" longitude="2.3540" />
  <troncon origine="N1" destination="N2" longueur="100" nomRue="Rue A" />
  <troncon origine="N2" destination="N3" longueur="200" nomRue="Rue B" />
  <troncon origine="N3" destination="N1" longueur="150" nomRue="Rue C" />
</reseau>
"""

SAMPLE_DELIVER_XML = """
<demandeDeLivraisons>
  <livraison adresseEnlevement="N1" adresseLivraison="N2" dureeEnlevement="60" dureeLivraison="120"/>
  <livraison adresseEnlevement="N2" adresseLivraison="N3" dureeEnlevement="30" dureeLivraison="90"/>
</demandeDeLivraisons>
"""


def test_full_api_flow(tmp_path):
    # upload map
    files = {"file": ("map.xml", SIMPLE_MAP_XML, "application/xml")}
    r = client.post("/api/v1/map/", files=files)
    assert r.status_code == 200
    assert r.json().get("intersections")

    # add courier
    courier_id = "C1"
    r = client.post("/api/v1/couriers/", json=courier_id)
    assert r.status_code == 200
    assert r.json() == courier_id

    # add single request via JSON
    req = {
        "pickup_addr": "N1",
        "delivery_addr": "N2",
        "pickup_service_s": 60,
        "delivery_service_s": 60
    }
    r = client.post("/api/v1/requests/", json=req)
    assert r.status_code == 200
    d1 = r.json()
    assert d1.get("id")

    # upload deliveries XML via /deliveries/ endpoint
    files = {"file": ("deliveries.xml", SAMPLE_DELIVER_XML, "application/xml")}
    r = client.post("/api/v1/deliveries/", files=files)
    assert r.status_code == 200
    ds = r.json()
    assert isinstance(ds, list) and len(ds) == 2

    # list requests
    r = client.get("/api/v1/requests/")
    assert r.status_code == 200
    all_requests = r.json()
    assert len(all_requests) >= 3

    # compute tours
    r = client.post("/api/v1/tours/compute")
    assert r.status_code == 200
    tours = r.json()
    assert isinstance(tours, list)

    # get state
    r = client.get("/api/v1/state/")
    assert r.status_code == 200
    st = r.json()
    assert "deliveries" in st and "couriers" in st

    # save and load state
    r = client.post("/api/v1/state/save")
    assert r.status_code == 200
    r = client.post("/api/v1/state/load")
    assert r.status_code == 200
