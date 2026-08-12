from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.detection import router as detection_router

app = FastAPI(
    title="AIShield Security API",
    description="Backend API for Anomaly Detection & Threat Monitoring",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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