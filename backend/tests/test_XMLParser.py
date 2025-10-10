import pytest
from pathlib import Path
from app.services.XMLParser import XMLParser
from app.models.schemas import DEFAULT_SPEED_KMH

project_root = Path(__file__).resolve().parents[2]
file_path_plan = project_root / "fichiersXMLPickupDelivery" / "petitPlan.xml"
file_path_deliveries = project_root / "fichiersXMLPickupDelivery" / "demandeMoyen5.xml"


@pytest.fixture(autouse=True)
def reset_id_counter():
    XMLParser._id_counter = 0


def test_generate_id_increments():
    # autouse fixture resets the counter; don't call it directly.
    assert XMLParser.generate_id() == "D1"
    assert XMLParser.generate_id() == "D2"
    assert XMLParser.generate_id() == "D3"


def test_parse_deliveries_parses_correctly(tmp_path: Path):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
  <entrepot heureDepart="08:30"/>
  <livraison adresseLivraison="A1" adresseEnlevement="P1" dureeEnlevement="10" dureeLivraison="20"/>
  <livraison adresseLivraison="A2" adresseEnlevement="P2" dureeEnlevement="5" dureeLivraison="15"/>
</root>
"""
    p = tmp_path / "deliveries.xml"
    p.write_text(xml, encoding="utf-8")

    deliveries = XMLParser.parse_deliveries(str(p))
    # two deliveries
    assert len(deliveries) == 2

    d1, d2 = deliveries
    # check types/attributes expected by the parser-created objects
    assert getattr(d1, "id") == "D1"
    assert getattr(d1, "delivery_addr") == "A1"
    assert getattr(d1, "pickup_addr") == "P1"
    assert getattr(d1, "pickup_service_s") == 10
    assert getattr(d1, "delivery_service_s") == 20
    assert getattr(d1, "hour_departure") == "08:30"

    assert getattr(d2, "id") == "D2"
    assert getattr(d2, "delivery_addr") == "A2"
    assert getattr(d2, "pickup_addr") == "P2"
    assert getattr(d2, "pickup_service_s") == 5
    assert getattr(d2, "delivery_service_s") == 15
    assert getattr(d2, "hour_departure") == "08:30"


def test_parse_map_parses_nodes_and_troncons(tmp_path: Path):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<carte>
  <noeud id="N1" latitude="48.8566" longitude="2.3522"/>
  <noeud id="N2" latitude="45.7640" longitude="4.8357"/>
  <troncon origine="N1" destination="N2" longueur="1200" nomRue="Rue de Test"/>
</carte>
"""
    p = tmp_path / "map.xml"
    p.write_text(xml, encoding="utf-8")

    mp = XMLParser.parse_map(str(p))

    # Map should contain intersections and road segments
    intersections = getattr(mp, "intersections", None)
    road_segments = getattr(mp, "road_segments", None)
    # fallback: the Map implementation in project may expose attributes differently; try common names
    if intersections is None:
        intersections = mp[0] if isinstance(mp, (list, tuple)) else getattr(mp, "intersections", [])
    if road_segments is None:
        road_segments = mp[1] if isinstance(mp, (list, tuple)) else getattr(mp, "road_segments", [])

    assert len(intersections) == 2
    ids = {getattr(n, "id") for n in intersections}
    assert ids == {"N1", "N2"}

    # one road segment
    assert len(road_segments) == 1
    seg = road_segments[0]
    # support either Intersection objects or raw node-id strings
    start_obj = getattr(seg, "start")
    end_obj = getattr(seg, "end")
    start_id = getattr(start_obj, 'id', start_obj)
    end_id = getattr(end_obj, 'id', end_obj)
    assert start_id == "N1"
    assert end_id == "N2"
    assert pytest.approx(getattr(seg, "length_m")) == 1200.0

    expected_travel_time = 1200.0 / (DEFAULT_SPEED_KMH * 1000.0 / 3600.0)
    assert pytest.approx(getattr(seg, "travel_time_s"), rel=1e-6) == expected_travel_time
    assert getattr(seg, "street_name") == "Rue de Test"


def test_parse_from_real_file(tmp_path: Path):
    # the autouse fixture already resets the counter for the test; if we need to
    # ensure it here, reset directly on the class rather than calling the fixture
    XMLParser._id_counter = 0
    deliveries = XMLParser.parse_deliveries(str(file_path_deliveries))
    assert len(deliveries) == 5  # assuming the test XML has 5 deliveries

    mp = XMLParser.parse_map(str(file_path_plan))
    intersections = getattr(mp, "intersections", None)
    road_segments = getattr(mp, "road_segments", None)
    if intersections is None:
        intersections = mp[0] if isinstance(mp, (list, tuple)) else getattr(mp, "intersections", [])
    if road_segments is None:
        road_segments = mp[1] if isinstance(mp, (list, tuple)) else getattr(mp, "road_segments", [])

    assert len(intersections) > 0
    assert len(road_segments) > 0