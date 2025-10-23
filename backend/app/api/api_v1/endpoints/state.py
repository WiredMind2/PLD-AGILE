from fastapi import APIRouter, HTTPException

from app.core import state

router = APIRouter(prefix="/state")


@router.get("/", tags=["State"], summary="Get server state", description="Return a snapshot of server state including map, couriers, deliveries and tours.")
def get_state():
    mp = state.get_map()
    tours = state.list_tours()
    return {
        "map": mp,
        "couriers": mp.couriers if mp else [],
        "deliveries": mp.deliveries if mp else [],
        "tours": tours,
    }

@router.delete("/clear_state", tags=["State"], summary="Clear server state", description="Clear current map, couriers, deliveries and tours from server memory.")
def clear_state():
    state.clear_state()
    return {"detail": "state cleared"}
