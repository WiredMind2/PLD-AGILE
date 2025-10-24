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
    """Register a new courier (id, name)."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')
    state.add_courier(courier)
    return courier


@router.delete("/{courier_id}", tags=["Couriers"], summary="Delete courier", description="Remove a courier by id.")
def delete_courier(courier_id: str):
    """Remove a courier by id."""
    ok = state.remove_courier(courier_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Courier not found')
    return {"detail": "deleted"}
