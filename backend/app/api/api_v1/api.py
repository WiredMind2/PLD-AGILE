from backend.app.api.api_v1.endpoints import map
from fastapi import APIRouter

from app.api.api_v1.endpoints import users

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(map.router, prefix="/items", tags=["items"])
api_router.include_router(users.router, prefix="/users", tags=["users"])