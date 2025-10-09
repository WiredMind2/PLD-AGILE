from pathlib import Path
import pytest
from app.services.XMLParser import XMLParser
from app.models.schemas import DEFAULT_SPEED_KMH, Delivery
import tempfile
import os
from app.models.schemas import Intersection, RoadSegment, Map

@pytest.fixture(autouse=True)
def reset_id_counter():
    # Reset the class-level counter before each test
    XMLParser._id_counter = 0

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


