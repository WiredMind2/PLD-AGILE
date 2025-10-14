from typing import List
from fastapi import APIRouter, HTTPException, status

from app.models.schemas import Courrier
from app.core import state

router = APIRouter(prefix="/couriers")


@router.get("/", response_model=List[Courrier], tags=["Couriers"], summary="List couriers", description="Return the list of couriers currently registered on the map.")
def list_couriers():
    """Return list of couriers."""
    return state.list_couriers()


@router.post("/", response_model=Courrier, tags=["Couriers"], summary="Add courier", description="Register a new courier (id, current_location, name, phone_number).")
def add_courier(courier: Courrier):
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


@router.delete("/{courier_id}", tags=["Couriers"], summary="Delete courier", description="Remove a courier by id.")
def delete_courier(courier_id: str):
    ok = state.remove_courier(courier_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Courier not found')
    return {"detail": "deleted"}
