from typing import List
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import Courrier
from app.core import state

router = APIRouter(prefix="/couriers")


@router.get("/", response_model=List[Courrier], tags=["Couriers"], summary="List couriers")
def list_couriers():
    """Return the list of couriers currently registered on the map."""
    return state.list_couriers()


@router.post("/", response_model=Courrier, tags=["Couriers"], summary="Add courier")
def add_courier(courier: Courrier):
    """Register a new courier (id, name) if a map is loaded. Raises 400 if no map is loaded."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')
    # validate current_location refers to a known intersection id if provided as an id
    inter_ids = {str(i.id) for i in mp.intersections}
    loc = getattr(courier.current_location, 'id', courier.current_location)
    if loc is not None and str(loc) not in inter_ids:
        raise HTTPException(status_code=400, detail=f'Courier current_location {loc} not found on map')
    state.add_courier(courier)
    return courier


@router.delete("/{courier_id}", tags=["Couriers"], summary="Delete courier")
def delete_courier(courier_id: str):
    """Remove a courier with his id. Raises 404 if courier not found."""
    ok = state.remove_courier(courier_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Courier not found')
    return {"detail": "deleted"}
