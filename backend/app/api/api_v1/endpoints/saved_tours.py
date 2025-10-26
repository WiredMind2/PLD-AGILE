from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from app.core import state

router = APIRouter(prefix="/saved_tours", tags=["Saved Tours"])


@router.get("/", summary="List saved tours", description="List named saved snapshots (map + tours).")
def list_saved_tours() -> List[Dict[str, Any]]:
    return state.list_snapshots()


@router.post("/save", summary="Save current state as named snapshot")
def save_current_as_named(payload: Dict[str, Any]):
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name'")
    try:
        meta = state.save_snapshot(str(name))
        return {"detail": "saved", **meta}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/load", summary="Load a named snapshot into memory")
def load_named_snapshot(payload: Dict[str, Any]):
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name'")
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
    
@router.delete("/delete", summary="Delete a named snapshot")
def delete_named_snapshot(payload: Dict[str, Any]):
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name'")
    try:
        state.delete_snapshot(str(name))
        return {"detail": "deleted"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
