from typing import List, Tuple
import xml.etree.ElementTree as ET

from traitlets import Dict
from backend.app.models.schemas import DEFAULT_SPEED_KMH, Delivery, Intersection,RoadSegment,Map

class XMLParser:
    # simple class-level counter to generate unique delivery IDs (D1, D2, ...)
    _id_counter = 0

    @classmethod
    def generate_id(cls) -> str:
        """Return a new unique delivery id like 'D1', 'D2', ..."""
        cls._id_counter += 1
        return f"D{cls._id_counter}"
    
    @staticmethod           
    def parse_deliveries(xml_text):
        root = ET.fromstring(xml_text)

        # Grab hourDeparture from <entrepot ... heureDepart="...">
        entrepot = root.find('entrepot')
        hour_departure = entrepot.get('heureDepart') if entrepot is not None else None

        deliveries = []
        for delivery_elem in root.findall('livraison'):
            delivery_data = {
                'id': XMLParser.generate_id(),  # keep your ID generator
                'delivery_addr': delivery_elem.get('adresseLivraison'),
                'pickup_addr': delivery_elem.get('adresseEnlevement'),
                'pickup_service_s': int(delivery_elem.get('dureeEnlevement', 0)),
                'delivery_service_s': int(delivery_elem.get('dureeLivraison', 0)),
                'hour_departure': hour_departure
            }
            delivery = Delivery(**delivery_data)
            deliveries.append(delivery)

        return deliveries
    
    @staticmethod
    def parse_map(xml_text):
        root = ET.fromstring(xml_text)
        # --- 1) Intersections ---
        intersections: List[Intersection] = []
        for node_elem in root.findall('noeud'):
            node = Intersection(
                id=node_elem.get('id'),
                latitude=float(node_elem.get('latitude')),
                longitude=float(node_elem.get('longitude'))
            )
            intersections.append(node)
        
        RoadSegments: List[RoadSegment] = []
        for edge_elem in root.findall('troncon'):   
            RoadSeg = RoadSegment(
                start = edge_elem.get('origine'),
                end = edge_elem.get('destination'),
                length_m = float(edge_elem.get('longueur')),
                travel_time_s = float(edge_elem.get('longueur')) / (DEFAULT_SPEED_KMH * 1000 / 3600),
                street_name = edge_elem.get('nomRue')
            )
            RoadSegments.append(RoadSeg)
        return Map(intersections, RoadSegments)

