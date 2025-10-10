from fastapi import APIRouter, HTTPException

from app.core import state

router = APIRouter(prefix="/state")


@router.get("/")
def get_state():
    mp = state.get_map()
    tours = state.list_tours()
    return {
        "map": mp,
        "couriers": mp.couriers if mp else [],
        "deliveries": mp.deliveries if mp else [],
        "tours": tours,
    }


@router.post('/save')
def save_state():
    state.persist_state()
    return {"detail": "state persisted"}


@router.post('/load')
def load_state():
    state.load_state()
    return {"detail": "state loaded"}
