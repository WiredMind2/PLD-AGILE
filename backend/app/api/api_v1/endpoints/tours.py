from typing import List
from fastapi import APIRouter, HTTPException

from app.models.schemas import Tour
from app.services import TSPService
from app.core import state

router = APIRouter(prefix="/tours")


@router.post("/compute/{courier_id}", tags=["Tours"], summary="Compute tour for courier")
def compute_tour(courier_id: str):
    """Compute the best tour for a specific courier (returns tours computed -- currently the service computes for all couriers)."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')

    try:
        svc = TSPService()
        tours = svc.compute_tours()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return tours


@router.post("/compute", tags=["Tours"], summary="Compute tours for all couriers")
def compute_all_tours():
    """Trigger the TSP service to compute tours for all registered couriers."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')

    try:
        svc = TSPService()
        tours = svc.compute_tours()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return tours


@router.get("/", response_model=List[Tour], tags=["Tours"], summary="List computed tours")
def list_tours():
    """Return the list of computed tours saved in server state."""
    return state.list_tours()


@router.get("/{courier_id}", response_model=List[Tour], tags=["Tours"], summary="Get tours for courier")
def get_tour(courier_id: str):
    """Return computed tours for a single courier id."""
    tours = state.list_tours()
    if filtered := [t for t in tours if t.courier == courier_id]:
        return filtered
    raise HTTPException(status_code=404, detail='No tour found for courier')


@router.post("/save", tags=["Tours"], summary="Save tours")
def save_tours():
    """Persist tours to disk (acknowledgement)."""
    # For now persist tours is just an acknowledgment
    return {"detail": "tours saved"}