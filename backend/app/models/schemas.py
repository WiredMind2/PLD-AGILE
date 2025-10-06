from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import time
import xml.etree.ElementTree as ET


DEFAULT_SPEED_KMH: float = 15.0
DEFAULT_START_TIME: time = time(hour=8, minute=0)

# ---------- Modèle CARTE (reseau) ----------

@dataclass
class Intersection:
    id: str           # ex: "25175791"
    latitude: float
    longitude: float


@dataclass
class DeliveryRequest:
    pickup_addr: str          # adresseEnlevement (string, id noeud)
    delivery_addr: str        # adresseLivraison (string, id noeud)
    pickup_service_s: int     # dureeEnlevement (secondes)
    delivery_service_s: int   # dureeLivraison (secondes)


@dataclass
class Courrier:
    id: str                   # ex: "C1"
    current_location: Intersection
    name : str
    phone_number : str

@dataclass
class RoadSegment:
    start: Intersection
    end: Intersection
    length_m: float           # longueur (metres)
    travel_time_s: int        # tempsTrajet (secondes)
    steet_name: str

    def calculate_time(self) -> int:
        """Calculate travel time based on speed (in km/h)."""
        return int(self.length_m / (DEFAULT_SPEED_KMH*1000/3600))


@dataclass
class Delivery:
    id: str                   # ex: "D1"
    pickup_addr: Intersection
    delivery_addr: Intersection
    pickup_service_s: int     # dureeEnlevement (secondes)
    delivery_service_s: int   # dureeLivraison (secondes)
    courier: Optional[Courrier] = None  # Courrier assigned to this delivery, if any
    hour_departure : Optional[time] = None

    

@dataclass
class Tour: 
    courier: Courrier
    deliveries: List[Delivery] = field(default_factory=list)
    total_travel_time_s: int = 0
    total_service_time_s: int = 0
    total_distance_m: float = 0.0
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    def add_delivery(self, delivery: Delivery):
        self.deliveries.append(delivery)
        self.total_service_time_s += delivery.pickup_service_s + delivery.delivery_service_s + delivery.calculate_time()
        if delivery.courier == self.courier:
            self.total_travel_time_s += delivery.pickup_service_s + delivery.delivery_service_s + delivery.calculate_time()
        # Note: total_distance_m should be updated based on actual route calculation


@dataclass
class Map:
    intersections: Dict[str, Intersection] = field(default_factory=dict)  # key: intersection id
    road_segments: List[RoadSegment] = field(default_factory=list)
    couriers: List[Courrier] = field(default_factory=list)
    adjacency_list: Dict[str, List[Tuple[Intersection, RoadSegment]]] = field(default_factory=dict)

    def add_intersection(self, intersection: Intersection):
        self.intersections[intersection.id] = intersection

    def add_road_segment(self, segment: RoadSegment):
        self.road_segments.append(segment)

    def add_delivery(self, delivery: Delivery):
        self.deliveries.append(delivery)

    def add_courier(self, courier: Courrier):
        self.couriers.append(courier)