import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project info
    PROJECT_NAME: str = "PLD-AGILE Backend"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "FastAPI backend for PLD-AGILE project"
    
    # API
    API_V1_STR: str = "/api/v1"
    
    # CORS
    ALLOWED_HOSTS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True


    TRAVEL_SPEED: float = 15.0  # Default travel speed in km/h


settings = Settings()