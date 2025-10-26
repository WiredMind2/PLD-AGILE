from typing import List
from fastapi import APIRouter, HTTPException, status, Body

from app.core import state

router = APIRouter(prefix="/couriers")


@router.get("/", response_model=List[str], tags=["Couriers"], summary="List couriers")
def list_couriers():
    """Return the list of couriers currently registered on the map."""
    return state.list_couriers()


@router.post("/", response_model=str, tags=["Couriers"], summary="Add courier")
def add_courier(courier: str = Body(...)):
    """Register a new courier (id, name) if a map is loaded. Raises 400 if no map is loaded."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')
    state.add_courier(courier)
    return courier


@router.delete("/{courier_id}", tags=["Couriers"], summary="Delete courier")
def delete_courier(courier_id: str):
    """Remove a courier with his id. Raises 404 if courier not found."""
    if ok := state.remove_courier(courier_id):
        return {"detail": "deleted"}
    else:
        raise HTTPException(status_code=404, detail='Courier not found')
