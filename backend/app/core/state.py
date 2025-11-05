import contextlib
from typing import Optional, List, Dict, Any
from threading import Lock
import os
import pickle
import re
from datetime import datetime, timezone
try:
    from app.models.schemas import Map, Delivery, Tour
except Exception:
    from models.schemas import Map, Delivery, Tour


_lock = Lock()
_current_map: Optional[Map] = None
_tours: List[Tour] = []

_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
os.makedirs(_data_dir, exist_ok=True)
_saved_dir = os.path.join(_data_dir, 'saved_tours')
os.makedirs(_saved_dir, exist_ok=True)


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
    return [] if _current_map is None else _current_map.deliveries


def add_delivery(delivery: Delivery) -> None:
    if _current_map is None:
        raise RuntimeError('No map loaded')

    _current_map.add_delivery(delivery)


def remove_delivery(delivery_id: str) -> bool:
    if _current_map is None:
        return False

    for i, delivery in enumerate(_current_map.deliveries):
        if delivery.id == delivery_id:
            del _current_map.deliveries[i]
            return True

    return False


def update_delivery(delivery_id: str, **kwargs) -> bool:
    if _current_map is None:
        return False

    for delivery in _current_map.deliveries:
        if delivery.id == delivery_id:
            for k, v in kwargs.items():
                with contextlib.suppress(Exception):
                    setattr(delivery, k, v)
            return True

    return False


def list_couriers() -> List[str]:
    return [] if _current_map is None else _current_map.couriers


def add_courier(c: str) -> None:
    if _current_map is None:
        raise RuntimeError('No map loaded')

    _current_map.add_courier(c)


def remove_courier(courier_id: str) -> bool:
    if _current_map is None:
        return False

    for i, courier in enumerate(_current_map.couriers):
        if courier == courier_id:
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


def clear_state() -> None:
    """Clear current map and tours from memory."""
    global _current_map, _tours
    with _lock:
        _current_map = None
        _tours = []


# ---------------------- Named snapshots (Saved Tours) ----------------------

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _sanitize_name(name: str) -> str:
    """Make a filesystem-safe name."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Empty name not allowed")
    safe = _SAFE_NAME_RE.sub("_", name)
    return safe[:128]


def save_snapshot(name: str) -> Dict[str, Any]:
    """Save the current map and tours into a named snapshot."""
    with _lock:
        if _current_map is None:
            raise RuntimeError("No map loaded")

        safe = _sanitize_name(name)
        path = os.path.join(_saved_dir, f"{safe}.pkl")
        
        # If snapshot already exists, overwrite it (tests expect overwrite behavior)
        # (Previously this raised an error.)
        
        payload = {
            "saved_at": datetime.now(timezone.utc),
            "name": safe,
            "map": _current_map,
            "tours": list(_tours),
        }
        with open(path, 'wb') as f:
            pickle.dump(payload, f)

        stat = os.stat(path)
        return {
            "name": safe,
            "saved_at": payload["saved_at"].strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            "size_bytes": stat.st_size,
        }


def list_snapshots() -> List[Dict[str, Any]]:
    """List saved snapshots with metadata."""
    entries: List[Dict[str, Any]] = []
    for fname in sorted(os.listdir(_saved_dir)):
        if not fname.endswith('.pkl'):
            continue
        fpath = os.path.join(_saved_dir, fname)
        try:
            with open(fpath, 'rb') as f:
                payload = pickle.load(f)
            name = payload.get('name') or os.path.splitext(fname)[0]
            saved_at = payload.get('saved_at')
            if isinstance(saved_at, datetime):
                saved_str = saved_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            else:
                saved_str = str(saved_at)
            stat = os.stat(fpath)
            entries.append({
                "name": name,
                "saved_at": saved_str,
                "size_bytes": stat.st_size,
            })
        except Exception:
            # skip unreadable/legacy file
            continue
    # most recent first
    entries.sort(key=lambda e: e.get('saved_at') or '', reverse=True)
    return entries


def load_snapshot(name: str) -> None:
    """Load a named snapshot into memory (map + tours)."""
    global _current_map, _tours
    safe = _sanitize_name(name)
    path = os.path.join(_saved_dir, f"{safe}.pkl")
    if not os.path.isfile(path):
        raise FileNotFoundError("Snapshot not found")
    with _lock:
        with open(path, 'rb') as f:
            payload = pickle.load(f)
        _current_map = payload.get('map')
        _tours = payload.get('tours') or []

def delete_snapshot(name: str) -> None:
    """Delete a named snapshot from disk."""
    safe = _sanitize_name(name)
    path = os.path.join(_saved_dir, f"{safe}.pkl")
    if not os.path.isfile(path):
        raise FileNotFoundError("Snapshot not found")
    os.remove(path)