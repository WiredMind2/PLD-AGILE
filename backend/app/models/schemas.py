from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from pydantic.dataclasses import dataclass
from pydantic import Field
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
    # addresses may be represented as node-id strings in some places or
    # full Intersection objects elsewhere. Allow both to make parsing
    # convenient for tests and incremental construction.
    pickup_addr: str | Intersection
    delivery_addr: str | Intersection
    pickup_service_s: int     # dureeEnlevement (secondes)
    delivery_service_s: int   # dureeLivraison (secondes)
    warehouse: Optional[Intersection] = None
    courier: Optional[Courrier] = None  # Courrier assigned to this delivery, if any
    # tests expect the raw hour string like "08:30"; accept str here
    hour_departure : Optional[str] = None
    id: Optional[str] = None  # ex: "D1" (optional when creating a new delivery)


@dataclass
class Tour: 
    courier: Courrier
    deliveries: List[Delivery] = Field(default_factory=list)
    total_travel_time_s: int = 0
    total_service_time_s: int = 0
    total_distance_m: float = 0.0
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    route_intersections: List[str] = Field(default_factory=list)

    def add_delivery(self, delivery: Delivery):
        self.deliveries.append(delivery)
        # service time is pickup + delivery durations
        self.total_service_time_s += delivery.pickup_service_s + delivery.delivery_service_s
        # total_travel_time_s is cumulative travel; deliveries don't contain travel distance here
        if delivery.courier == self.courier:
            self.total_travel_time_s += delivery.pickup_service_s + delivery.delivery_service_s
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
        # intersections is a list; append new intersection
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
        # build a lookup of intersections by id
        inter_by_id = {str(i.id): i for i in self.intersections}
        for seg in self.road_segments:
            # start/end may be Intersection objects or raw ids
            start_id = getattr(seg.start, 'id', seg.start)
            end_id = getattr(seg.end, 'id', seg.end)
            if start_id is None or end_id is None:
                continue
            start_id = str(start_id)
            end_id = str(end_id)
            dst = inter_by_id.get(end_id)
            if dst is None:
                # unknown destination; skip
                continue
            self.adjacency_list.setdefault(start_id, []).append((dst, seg))
