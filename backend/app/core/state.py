from typing import Optional, List
from threading import Lock
import os
import pickle

try:
    from app.models.schemas import Map, Delivery, Courrier, Tour
except Exception:
    from models.schemas import Map, Delivery, Courrier, Tour


_lock = Lock()
_current_map: Optional[Map] = None
_tours: List[Tour] = []

_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
os.makedirs(_data_dir, exist_ok=True)
_map_file = os.path.join(_data_dir, 'map.pkl')
_tours_file = os.path.join(_data_dir, 'tours.pkl')


def set_map(m: Map) -> None:
    global _current_map
    with _lock:
        _current_map = m


def get_map() -> Optional[Map]:
    return _current_map


def clear_map() -> None:
    global _current_map
    with _lock:
        _current_map = None


def list_deliveries() -> List[Delivery]:
    if _current_map is None:
        return []
    return _current_map.deliveries


def add_delivery(delivery: Delivery) -> None:
    if _current_map is None:
        raise RuntimeError('No map loaded')
    _current_map.add_delivery(delivery)


def remove_delivery(delivery_id: str) -> bool:
    if _current_map is None:
        return False
    for i, d in enumerate(_current_map.deliveries):
        if getattr(d, 'id', None) == delivery_id:
            del _current_map.deliveries[i]
            return True
    return False


def list_couriers() -> List[Courrier]:
    if _current_map is None:
        return []
    return _current_map.couriers


def add_courier(c: Courrier) -> None:
    if _current_map is None:
        raise RuntimeError('No map loaded')
    _current_map.add_courier(c)


def remove_courier(courier_id: str) -> bool:
    if _current_map is None:
        return False
    for i, c in enumerate(_current_map.couriers):
        if getattr(c, 'id', None) == courier_id:
            del _current_map.couriers[i]
            return True
    return False


def save_tour(t: Tour) -> None:
    with _lock:
        _tours.append(t)


def list_tours() -> List[Tour]:
    return list(_tours)


def clear_tours() -> None:
    global _tours
    with _lock:
        _tours = []


def persist_state() -> None:
    """Persist current map and tours to disk."""
    with _lock:
        with open(_map_file, 'wb') as f:
            pickle.dump(_current_map, f)
        with open(_tours_file, 'wb') as f:
            pickle.dump(_tours, f)


def load_state() -> None:
    """Load map and tours from disk if present."""
    global _current_map, _tours
    with _lock:
        try:
            if os.path.isfile(_map_file):
                with open(_map_file, 'rb') as f:
                    _current_map = pickle.load(f)
        except Exception:
            _current_map = None
        try:
            if os.path.isfile(_tours_file):
                with open(_tours_file, 'rb') as f:
                    _tours = pickle.load(f) or []
        except Exception:
            _tours = []
