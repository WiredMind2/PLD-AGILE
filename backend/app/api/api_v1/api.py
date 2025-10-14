from fastapi import APIRouter
from app.api.api_v1.endpoints import map, requests, couriers, tours, state, deliveries

api_router = APIRouter()

api_router.include_router(map.router)
api_router.include_router(requests.router)
api_router.include_router(couriers.router)
api_router.include_router(tours.router)
api_router.include_router(state.router)
api_router.include_router(deliveries.router)