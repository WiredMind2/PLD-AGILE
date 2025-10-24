from fastapi import APIRouter, HTTPException

from app.core import state

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
