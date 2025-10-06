import xml.etree.ElementTree as ET
from backend.app.models.schemas import Delivery, Intersection,RoadSegment,Map

class XMLParser:
    # simple class-level counter to generate unique delivery IDs (D1, D2, ...)
    _id_counter = 0

    @classmethod
    def generate_id(cls) -> str:
        """Return a new unique delivery id like 'D1', 'D2', ..."""
        cls._id_counter += 1
        return f"D{cls._id_counter}"
    
    @staticmethod           
    def parse_pickup_delivery(xml_file_path):
        """
        Parses the XML file and returns a list of PickupDelivery objects.
        """
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        deliveries = []


        for delivery_elem in root.findall('livraison'):
            # Adjust tag names and attributes according to your XML structure and PickupDelivery schema
            delivery_data = {
                'id': XMLParser.generate_id(),
                'delivery_addr': delivery_elem.find('adresseLivraison').text,
                'pickup_addr': delivery_elem.find('adresseEnlevement').text,
                'pickup_service_s': int(delivery_elem.find('dureeEnlevement').text),
                'delivery_service_s': int(delivery_elem.find('dureeLivraison').text),
                'hour_departure': root.attrib.get('heureDepart', None)  # Optional attribute at root level
            }
            delivery = Delivery(**delivery_data)
            deliveries.append(delivery)

        return deliveries
    
    @staticmethod
    def parse_map(xml_file_path):
        """
        Parses the XML file and returns a list of Map objects.
        """
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        intersections = []
        road_segments = []

        for intersection_elem in root.findall('intersection'):
            intersection_data = {
                'id': intersection_elem.get('id'),
                'latitude': float(intersection_elem.get('latitude')),
                'longitude': float(intersection_elem.get('longitude'))
            }
            intersection = Intersection(**intersection_data)
            intersections.append(intersection)

        for road_elem in root.findall('troncon'):
            start_id = road_elem.get('origine')
            end_id = road_elem.get('destination')
            start = next((i for i in intersections if i.id == start_id), None)
            end = next((i for i in intersections if i.id == end_id), None)
            if start and end:
                road_segment_data = {
                    'start': float(road_elem.get('origine')),
                    'end': float(road_elem.get('destination')),
                    'length_m': float(road_elem.get('longueur')),
                    'travel_time_s': int(road_elem.get('tempsTrajet')),
                    'street_name': road_elem.get('nomRue', 'Unnamed Road')
                }
                road_segment = RoadSegment(**road_segment_data)
                road_segments.append(road_segment)

        return Map(intersections=intersections, road_segments=road_segments)

# Example usage:
# deliveries = XMLParser.parse_pickup_delivery('fichierXMLPickupDelivery.xml')
# map_data = XMLParser.parse_map('fichierXMLMap.xml')
