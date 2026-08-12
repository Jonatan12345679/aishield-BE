from fastapi import APIRouter
 
from app.api.v1.endpoints.aishield import dashboard
 
api_router = APIRouter()
 
api_router.include_router(dashboard.router)