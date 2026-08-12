from fastapi import FastAPI
from app.api.v1.router import api_router
from app.api.v1.endpoints.detection import router as detection_router

app = FastAPI(
    title="AIShield Security API",
    description="Backend API for Anomaly Detection & Threat Monitoring",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "AIShield Engine",
        "version": "1.0.0"
    }

app.include_router(
    detection_router,
    prefix="/api/v1",
    tags=["Privacy Detection"]
)