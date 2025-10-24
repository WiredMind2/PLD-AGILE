from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.api_v1.api import api_router
# from app.utils.TSP.Astar import Astar  # Module not found - commented out


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("🚀 FastAPI server starting up...")
    yield
    # Shutdown logic
    print("🛑 FastAPI server shutting down...")


# OpenAPI tags metadata to provide richer docs grouping
tags_metadata = [
    {"name": "Map", "description": "Upload and inspect city maps (XML)."},
    {"name": "Requests", "description": "Create, list and delete delivery requests (single or batch via XML)."},
    {"name": "Deliveries", "description": "Alternative endpoint for bulk delivery uploads (matches frontend client usage)."},
    {"name": "Couriers", "description": "Manage couriers (add, list, remove)."},
    {"name": "Tours", "description": "Compute delivery tours using the TSP service and list saved tours."},
    {"name": "State", "description": "Inspect and persist the server-side application state (map, deliveries, tours)."},
]


# Create FastAPI app with lifespan events and OpenAPI metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={"name": "WiredMind2", "email": "support@example.com"},
    license_info={"name": "MIT"},
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.VERSION}


if __name__ == "__main__":
    # Test de la classe Astar - commented out as Astar module doesn't exist
    # astar = Astar(0.5)
    # result = astar.print_for_test()

    print("\n=== Démarrage du serveur FastAPI ===")
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )