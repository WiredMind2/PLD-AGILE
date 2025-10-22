from typing import List, Any
from fastapi import APIRouter, HTTPException

from app.models.schemas import Tour
from app.services import TSPService
from app.core import state
from app.services import XMLParser

router = APIRouter(prefix="/tours")


@router.post("/compute/{courier_id}", tags=["Tours"], summary="Compute tour for courier", description="Compute the best tour for a specific courier (returns tours computed -- currently the service computes for all couriers).")
def compute_tour(courier_id: str):
    """Compute the best tour for the given courier id."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')
    try:
        svc = TSPService()
        tours = svc.compute_tours()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return tours


@router.post("/compute", tags=["Tours"], summary="Compute tours for all couriers", description="Trigger the TSP service to compute tours for all registered couriers.")
def compute_all_tours():
    """Compute tours for all couriers."""
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')
    try:
        svc = TSPService()
        tours = svc.compute_tours()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return tours


@router.get("/", response_model=List[Tour], tags=["Tours"], summary="List computed tours", description="Return the list of computed tours saved in server state.")
def list_tours():
    return state.list_tours()

@router.get("/{courier_id}", response_model=List[Tour], tags=["Tours"], summary="Get tours for courier", description="Return computed tours for a single courier id.")
def get_tour(courier_id: str):
    tours = state.list_tours()
    filtered = [t for t in tours if getattr(t.courier, 'id', None) == courier_id]
    if not filtered:
        raise HTTPException(status_code=404, detail='No tour found for courier')
    return filtered


# response_model attend une classe
@router.post("/save", tags=["Tours"], summary="Save tours", description="Persist tours to disk (acknowledgement).")
def save_tour(request: Tour):
    mp = state.get_map()
    if mp is None:
        raise HTTPException(status_code=400, detail='No map loaded')
    state.save_tour(request)
    return {"detail": "tours saved"}


    
    