from __future__ import annotations
try:
    # Prefer pydantic dataclass when available (keeps validation), but
    # fallback to stdlib dataclasses so tests run without pydantic installed.
    from pydantic.dataclasses import dataclass, Field
except Exception:  # pragma: no cover - fallback for environments without pydantic
    from dataclasses import dataclass, field as Field

from typing import Dict, List, Tuple, Optional
from datetime import time


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
    street_name: str

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
    deliveries: List[Delivery] = Field(default_factory=list)
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
    intersections: List[Intersection] = Field(default_factory=list)
    road_segments: List[RoadSegment] = Field(default_factory=list)
    couriers: List[Courrier] = Field(default_factory=list)
    deliveries: List[Delivery] = Field(default_factory=list)
    adjacency_list: Dict[str, List[Tuple[Intersection, RoadSegment]]] = Field(default_factory=dict)

    # ----------------- Méthodes de construction -----------------
    def add_intersection(self, intersection: Intersection) -> None:
        # Support both list and dict storage for intersections. If stored as
        # a dict, set by id; if stored as a list, append or replace existing.
        if isinstance(self.intersections, dict):
            self.intersections[intersection.id] = intersection
        else:
            # Replace existing intersection with same id if present
            for i, ins in enumerate(self.intersections):
                if getattr(ins, 'id', None) == intersection.id:
                    self.intersections[i] = intersection
                    return
            self.intersections.append(intersection)

    def add_road_segment(self, segment: RoadSegment) -> None:
        self.road_segments.append(segment)

    def add_delivery(self, delivery: Delivery) -> None:
        self.deliveries.append(delivery)

    def add_courier(self, courier: Courrier) -> None:
        self.couriers.append(courier)

    def build_adjacency(self) -> None:
        """Construit la liste d’adjacence orientée (origine -> destination)."""
        self.adjacency_list.clear()
        for seg in self.road_segments:
            # Resolve start/end to ids and intersections
            origin_id = getattr(seg.start, 'id', None) if seg.start is not None else None
            dest_id = getattr(seg.end, 'id', None) if seg.end is not None else None
            if origin_id is None or dest_id is None:
                continue

            # find destination intersection object
            dst = None
            if isinstance(self.intersections, dict):
                dst = self.intersections.get(dest_id)
            else:
                for ins in self.intersections:
                    if getattr(ins, 'id', None) == dest_id:
                        dst = ins
                        break
            if dst is None:
                continue

            self.adjacency_list.setdefault(origin_id, []).append((dst, seg))
