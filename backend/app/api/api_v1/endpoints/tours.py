from typing import List
from fastapi import APIRouter, HTTPException

from app.models.schemas import Tour
from app.services import TSPService
from app.core import state

router = APIRouter(prefix="/tours")


@router.post("/compute/{courier_id}")
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


@router.post("/compute")
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


@router.get("/", response_model=List[Tour])
def list_tours():
    return state.list_tours()


@router.get("/{courier_id}", response_model=List[Tour])
def get_tour(courier_id: str):
    tours = state.list_tours()
    filtered = [t for t in tours if getattr(t.courier, 'id', None) == courier_id]
    if not filtered:
        raise HTTPException(status_code=404, detail='No tour found for courier')
    return filtered


@router.post("/save")
def save_tours():
    # For now persist tours is just an acknowledgment
    return {"detail": "tours saved"}