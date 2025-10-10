from typing import List, Optional
import xml.etree.ElementTree as ET

from app.models.schemas import DEFAULT_SPEED_KMH, Delivery, Intersection, RoadSegment, Map

class XMLParser:
    # simple class-level counter to generate unique delivery IDs (D1, D2, ...)
    _id_counter = 0

    @classmethod
    def generate_id(cls) -> str:
        """Return a new unique delivery id like 'D1', 'D2', ..."""
        cls._id_counter += 1
        return f"D{cls._id_counter}"
    
    @staticmethod
    def parse_deliveries(xml_text: str) -> List[Delivery]:
        """Parse deliveries from an XML string and return a list of Delivery objects.

        Note: this function returns Delivery instances constructed with the
        attributes parsed from XML. Depending on the project's Delivery type,
        pickup_addr and delivery_addr may be strings (IDs) or Intersection
        objects. This function preserves the raw attribute value (string).
        """
        root: ET.Element = ET.fromstring(xml_text)

        # Grab hourDeparture from <entrepot ... heureDepart="...">
        entrepot: Optional[ET.Element] = root.find('entrepot')
        hour_departure: Optional[str] = (
            entrepot.get('heureDepart') if entrepot is not None else None
        )

        deliveries: List[Delivery] = []
        for delivery_elem in root.findall('livraison'):
            pickup_service_s = int(delivery_elem.get('dureeEnlevement', 0) or 0)
            delivery_service_s = int(delivery_elem.get('dureeLivraison', 0) or 0)

            delivery_data = {
                'id': XMLParser.generate_id(),  # keep your ID generator
                'delivery_addr': delivery_elem.get('adresseLivraison'),
                'pickup_addr': delivery_elem.get('adresseEnlevement'),
                'pickup_service_s': pickup_service_s,
                'delivery_service_s': delivery_service_s,
                'hour_departure': hour_departure,
            }
            delivery = Delivery(**delivery_data)
            deliveries.append(delivery)

        return deliveries
    
    @staticmethod
    def parse_map(xml_text: str) -> Map:
        """Parse a map XML and return a Map object.

        This function constructs Intersections and RoadSegments from XML.
        Note: currently it builds Intersections as a list and RoadSegments
        with start/end set to the raw node id strings. Upstream code may
        expect Intersection objects; adapt as needed.
        """
        root: ET.Element = ET.fromstring(xml_text)

        # --- 1) Intersections ---
        intersections: List[Intersection] = []
        inter_by_id: dict = {}
        for node_elem in root.findall('noeud'):
            node_id = node_elem.get('id')
            if node_id is None:
                raise ValueError('noeud element missing id attribute')
            lat_attr = node_elem.get('latitude')
            lon_attr = node_elem.get('longitude')
            latitude = float(lat_attr) if lat_attr is not None else 0.0
            longitude = float(lon_attr) if lon_attr is not None else 0.0

            node = Intersection(
                id=node_id,
                latitude=latitude,
                longitude=longitude,
            )
            intersections.append(node)
            inter_by_id[str(node_id)] = node

        road_segments: List[RoadSegment] = []
        for edge_elem in root.findall('troncon'):
            origine = edge_elem.get('origine')
            destination = edge_elem.get('destination')
            if origine is None or destination is None:
                raise ValueError('troncon element missing origine or destination attribute')

            longueur_attr = edge_elem.get('longueur')
            length_m = float(longueur_attr) if longueur_attr is not None else 0.0
            # compute travel time in seconds from length and default speed (km/h)
            travel_time_s = int(round(length_m / (DEFAULT_SPEED_KMH * 1000 / 3600))) if DEFAULT_SPEED_KMH != 0 else 0
            street_name = edge_elem.get('nomRue') or ''

            # map start/end ids to Intersection objects (raise if missing)
            try:
                start_inter = inter_by_id[str(origine)]
                end_inter = inter_by_id[str(destination)]
            except KeyError:
                raise ValueError(f'troncon references unknown node: {origine} or {destination}')

            road_seg = RoadSegment(
                start=start_inter,
                end=end_inter,
                length_m=length_m,
                travel_time_s=travel_time_s,
                street_name=street_name,
            )
            road_segments.append(road_seg)

        return Map(intersections, road_segments)

