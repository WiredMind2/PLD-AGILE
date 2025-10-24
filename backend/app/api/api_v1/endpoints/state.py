from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException

from app.core import state
from app.core.config import settings

router = APIRouter(prefix="/state")


@router.get("/", tags=["State"], summary="Get server state")
def get_state():
    """Return a snapshot of server state including map, couriers, deliveries and tours."""
    mp = state.get_map()
    tours = state.list_tours()
    return {
        "map": mp,
        "couriers": mp.couriers if mp else [],
        "deliveries": mp.deliveries if mp else [],
        "tours": tours,
    }

@router.delete("/clear_state", tags=["State"], summary="Clear server state")
def clear_state():
    """Clear current map, couriers, deliveries and tours from server memory."""
    state.clear_state()
    return {"detail": "state cleared"}

@router.post("/save", tags=["State"], summary="Save current state")
def save_state(payload: Optional[Dict[str, Any]] = None):
    """Save current state as a named snapshot."""
    payload = payload or {}
    name = payload.get("name", "default")
    try:
        meta = state.save_snapshot(str(name))
        return {"detail": "saved", **meta}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/load", tags=["State"], summary="Load saved state")
def load_state(payload: Optional[Dict[str, Any]] = None):
    """Load a named snapshot into memory."""
    payload = payload or {}
    name = payload.get("name", "default")
    try:
        state.load_snapshot(str(name))
        # Return current state for convenience
        mp = state.get_map()
        tours = state.list_tours()
        return {
            "detail": "loaded",
            "state": {
                "map": mp,
                "couriers": mp.couriers if mp else [],
                "deliveries": mp.deliveries if mp else [],
                "tours": tours,
            },
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/get_travel_speed', tags=["State"], summary="Get travel speed", description="Return the current travel speed setting.")
def get_travel_speed():
    speed = settings.TRAVEL_SPEED
    return {"travel_speed": speed}
