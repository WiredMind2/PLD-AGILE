from pathlib import Path
import pytest

from app.services.XMLParser import XMLParser
from app.models.schemas import DEFAULT_SPEED_KMH, Map, Intersection, RoadSegment


project_root = Path(__file__).resolve().parents[2]
file_path_plan = project_root / "fichiersXMLPickupDelivery" / "petitPlan.xml"
file_path_deliveries = project_root / "fichiersXMLPickupDelivery" / "demandeMoyen5.xml"


@pytest.fixture(autouse=True)
def reset_id_counter():
    XMLParser._id_counter = 0


def test_generate_id_increments():
    assert XMLParser.generate_id() == "D1"
    assert XMLParser.generate_id() == "D2"
    assert XMLParser.generate_id() == "D3"


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


def test_parse_deliveries_missing_entrepot():
    xml = """
    <root>
        <livraison adresseLivraison="1" adresseEnlevement="2" dureeEnlevement="10" dureeLivraison="20"/>
    </root>
    """
    deliveries = XMLParser.parse_deliveries(xml)
    assert len(deliveries) == 1
    assert deliveries[0].hour_departure is None


def test_parse_map_parses_nodes_and_troncons():
    xml = """
    <carte>
      <noeud id="N1" latitude="48.8566" longitude="2.3522"/>
      <noeud id="N2" latitude="45.7640" longitude="4.8357"/>
      <troncon origine="N1" destination="N2" longueur="1200" nomRue="Rue de Test"/>
    </carte>
    """
    m = XMLParser.parse_map(xml)
    assert isinstance(m, Map)
    # intersections may be stored as list of Intersection
    assert len(m.intersections) == 2
    ids = {i.id for i in m.intersections}
    assert ids == {"N1", "N2"}

    assert len(m.road_segments) == 1
    seg = m.road_segments[0]
    # ensure start/end are Intersection objects or at least expose id
    start = getattr(seg, "start")
    end = getattr(seg, "end")
    start_id = getattr(start, "id", start)
    end_id = getattr(end, "id", end)
    assert start_id == "N1"
    assert end_id == "N2"
    assert pytest.approx(getattr(seg, "length_m")) == 1200.0
    expected_travel_time = int(round(1200.0 / (DEFAULT_SPEED_KMH * 1000.0 / 3600.0)))
    assert getattr(seg, "travel_time_s") == expected_travel_time
    assert getattr(seg, "street_name") == "Rue de Test"


def test_parse_map_empty():
    xml = "<root></root>"
    m = XMLParser.parse_map(xml)
    assert isinstance(m, Map)
    assert m.intersections == []
    assert m.road_segments == []


def test_parse_from_real_file():
    # parse known files from repository (if present)
    if not file_path_plan.exists() or not file_path_deliveries.exists():
        pytest.skip("example XML files not present in repo")

    deliveries = XMLParser.parse_deliveries(file_path_deliveries.read_text(encoding="utf-8"))
    assert len(deliveries) >= 1

    m = XMLParser.parse_map(file_path_plan.read_text(encoding="utf-8"))
    assert len(m.intersections) > 0
    assert len(m.road_segments) > 0
