from fastapi import APIRouter
 
from app.api.v1.endpoints.aishield import dashboard, simulation
from app.api.v1.endpoints.privacy_detection import detection
 
api_router = APIRouter()
 
api_router.include_router(dashboard.router)
api_router.include_router(simulation.router)

api_router.include_router(
    detection.router,
    tags=["Privacy Detection"]
)