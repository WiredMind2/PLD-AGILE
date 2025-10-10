from app.api.api_v1.endpoints import map
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(map.router, prefix="/map")