from pathlib import Path
import pytest
from app.services.XMLParser import XMLParser
from app.models.schemas import DEFAULT_SPEED_KMH, Delivery
import tempfile
import os
from app.models.schemas import Intersection, RoadSegment, Map

project_root = Path(__file__).resolve().parents[2]
file_path_plan = project_root / "fichiersXMLPickupDelivery" / "petitPlan.xml"
file_path_deliveries = project_root / "fichiersXMLPickupDelivery" / "demandeMoyen5.xml"

@pytest.fixture(autouse=True)
def reset_id_counter():
    # Reset the class-level counter before each test
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

    deliveries = XMLParser.parse_deliveries(p.read_text(encoding="utf-8"))
    # two deliveries
def test_parse_deliveries_basic():
    xml = """
    <root>
        <entrepot heureDepart="08:00:00"/>
        <livraison adresseLivraison="123" adresseEnlevement="456" dureeEnlevement="60" dureeLivraison="120"/>
        <livraison adresseLivraison="789" adresseEnlevement="012" dureeEnlevement="30" dureeLivraison="45"/>
    </root>
    """
    deliveries = XMLParser.parse_deliveries(xml)
    assert len(deliveries) == 2
    assert deliveries[0].id == "D1"
    assert deliveries[0].delivery_addr == "123"
    assert deliveries[0].pickup_addr == "456"
    assert deliveries[0].pickup_service_s == 60
    assert deliveries[0].delivery_service_s == 120
    assert deliveries[0].hour_departure == "08:00:00"
    assert deliveries[1].id == "D2"
    assert deliveries[1].delivery_addr == "789"
    assert deliveries[1].pickup_addr == "012"
    assert deliveries[1].pickup_service_s == 30
    assert deliveries[1].delivery_service_s == 45
    assert deliveries[1].hour_departure == "08:00:00"

def test_parse_deliveries_missing_entrepot():
    xml = """
    <root>
        <livraison adresseLivraison="1" adresseEnlevement="2" dureeEnlevement="10" dureeLivraison="20"/>
    </root>
    """
    deliveries = XMLParser.parse_deliveries(xml)
    assert len(deliveries) == 1
    assert deliveries[0].hour_departure is None

def test_parse_deliveries_missing_optional_fields():
    xml = """
    <root>
        <entrepot heureDepart="09:30:00"/>
        <livraison adresseLivraison="100" adresseEnlevement="200"/>
    </root>
    """
    deliveries = XMLParser.parse_deliveries(xml)
    assert len(deliveries) == 1
    assert deliveries[0].pickup_service_s == 0
    assert deliveries[0].delivery_service_s == 0
    assert deliveries[0].hour_departure == "09:30:00"

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

    mp = XMLParser.parse_map(p.read_text(encoding="utf-8"))

    # Map should contain intersections and road segments
    intersections = getattr(mp, "_0", None) if hasattr(mp, "_0") else getattr(mp, "intersections", None)
    road_segments = getattr(mp, "_1", None) if hasattr(mp, "_1") else getattr(mp, "road_segments", None)
    # fallback: the Map implementation in project may expose attributes differently; try common names
    if intersections is None:
        # try attribute names used in simple dataclass tuple-like Map(...)
        intersections = mp[0] if isinstance(mp, (list, tuple)) else getattr(mp, "intersections", [])
    if road_segments is None:
        road_segments = mp[1] if isinstance(mp, (list, tuple)) else getattr(mp, "road_segments", [])

    assert len(intersections) == 2
    ids = {getattr(n, "id") for n in intersections}
    assert ids == {"N1", "N2"}

    # one road segment
    assert len(road_segments) == 1
    seg = road_segments[0]
    # start/end are Intersection objects
    start_obj = getattr(seg, "start")
    end_obj = getattr(seg, "end")
    # support either Intersection objects or raw node-id strings
    start_id = getattr(start_obj, 'id', start_obj)
    end_id = getattr(end_obj, 'id', end_obj)
    assert start_id == "N1"
    assert end_id == "N2"
    assert pytest.approx(getattr(seg, "length_m")) == 1200.0

    expected_travel_time = 1200.0 / (DEFAULT_SPEED_KMH * 1000.0 / 3600.0)
    assert pytest.approx(getattr(seg, "travel_time_s"), rel=1e-6) == expected_travel_time
    assert getattr(seg, "street_name") == "Rue de Test"


def test_parse_from_real_file(tmp_path: Path):
    deliveries = XMLParser.parse_deliveries(Path(file_path_deliveries).read_text(encoding="utf-8"))
    assert len(deliveries) == 5  # assuming the test XML has 5 deliveries

    mp = XMLParser.parse_map(Path(file_path_plan).read_text(encoding="utf-8"))
    print(mp)
    intersections = getattr(mp, "_0", None) if hasattr(mp, "_0") else getattr(mp, "intersections", None)
    road_segments = getattr(mp, "_1", None) if hasattr(mp, "_1") else getattr(mp, "road_segments", None)
    if intersections is None:
        intersections = mp[0] if isinstance(mp, (list, tuple)) else getattr(mp, "intersections", [])
    if road_segments is None:
        road_segments = mp[1] if isinstance(mp, (list, tuple)) else getattr(mp, "road_segments", [])

    assert len(intersections) > 0
    assert len(road_segments) > 0
def test_parse_deliveries_no_livraison():
    xml = """
    <root>
        <entrepot heureDepart="10:00:00"/>
    </root>
    """
    deliveries = XMLParser.parse_deliveries(xml)
    assert deliveries == []
    def test_parse_map_basic():
        xml = """
        <root>
            <noeud id="1" latitude="48.8566" longitude="2.3522"/>
            <noeud id="2" latitude="48.8570" longitude="2.3530"/>
            <troncon origine="1" destination="2" longueur="100" nomRue="Rue A"/>
            <troncon origine="2" destination="1" longueur="150" nomRue="Rue B"/>
        </root>
        """
        m = XMLParser.parse_map(xml)
        assert isinstance(m, Map)
        assert len(m.intersections) == 2
        assert m.intersections[0].id == "1"
        assert m.intersections[0].latitude == 48.8566
        assert m.intersections[0].longitude == 2.3522
        assert m.intersections[1].id == "2"
        assert m.intersections[1].latitude == 48.8570
        assert m.intersections[1].longitude == 2.3530
        assert len(m.road_segments) == 2
        assert m.road_segments[0].start == "1"
        assert m.road_segments[0].end == "2"
        assert m.road_segments[0].length_m == 100.0
        assert m.road_segments[0].street_name == "Rue A"
        # Check travel_time_s calculation
        expected_time_0 = 100 / (DEFAULT_SPEED_KMH * 1000 / 3600)
        assert abs(m.road_segments[0].travel_time_s - expected_time_0) < 1e-6

def test_parse_map_empty():
        xml = "<root></root>"
        m = XMLParser.parse_map(xml)
        assert isinstance(m, Map)
        assert m.intersections == []
        assert m.road_segments == []

def test_parse_map_missing_fields():
        xml = """
        <reseau>
            <noeud id="A" latitude="0.0" longitude="0.0"/>
            <troncon origine="A" destination="B" longueur="50" nomRue="Main St"/>
        </reseau>
        """
        m = XMLParser.parse_map(xml)
        assert len(m.intersections) == 1
        assert m.intersections[0].id == "A"
        assert len(m.road_segments) == 1
        assert m.road_segments[0].start == "A"
        assert m.road_segments[0].end == "B"
        assert m.road_segments[0].length_m == 50.0
        assert m.road_segments[0].street_name == "Main St"

def test_parse_map_non_numeric_longitude_latitude():
        xml = """
        <reseau>
            <noeud id="X" latitude="not_a_float" longitude="2.0"/>
        </reseau>
        """
        with pytest.raises(ValueError):
            XMLParser.parse_map(xml)

def test_parse_map_non_numeric_longueur():
        xml = """
        <reseau>
            <noeud id="1" latitude="1.0" longitude="2.0"/>
            <troncon origine="1" destination="2" longueur="not_a_number" nomRue="Rue C"/>
        </reseau>
        """
        with pytest.raises(ValueError):
            XMLParser.parse_map(xml)
          

def test_parse_map_from_real_datas():
    xml_content = """
    <reseau>
        <noeud id="208769499" latitude="45.760597" longitude="4.87622"/>
        <noeud id="975886496" latitude="45.756874" longitude="4.8574047"/>
        <troncon destination="25175778" longueur="69.979805" nomRue="Rue Danton" origine="25175791"/>
        <troncon destination="2117622723" longueur="136.00636" nomRue="Rue de l'Abondance" origine="25175791"/>
    </reseau>
    """
    m = XMLParser.parse_map(xml_content)
    assert isinstance(m, Map)
    assert len(m.intersections) == 2
    assert len(m.road_segments) == 2    
    assert m.intersections[0].id == "208769499"
    assert m.intersections[0].latitude == 45.760597
    assert m.intersections[0].longitude == 4.87622
    assert m.intersections[1].id == "975886496"
    assert m.intersections[1].latitude == 45.756874
    assert m.intersections[1].longitude == 4.8574047
    assert m.road_segments[0].start == "25175791"
    assert m.road_segments[0].end == "25175778"
    assert m.road_segments[0].length_m == 69.979805
    assert m.road_segments[0].street_name == "Rue Danton"
    expected_time_0 = 69.979805 / (DEFAULT_SPEED_KMH * 1000 / 3600)
    assert abs(m.road_segments[0].travel_time_s - expected_time_0) < 1e-6
    assert m.road_segments[1].start == "25175791"
    assert m.road_segments[1].end == "2117622723"
    assert m.road_segments[1].length_m == 136.00636
    assert m.road_segments[1].street_name == "Rue de l'Abondance"
    expected_time_1 = 136.00636 / (DEFAULT_SPEED_KMH * 1000 / 3600)
    assert abs(m.road_segments[1].travel_time_s - expected_time_1) < 1e-6


