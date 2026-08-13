from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

from app.api.v1.router import api_router

if settings.APP_ENV == "development":
    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
else:
    origins = [
        origin.strip()
        for origin in settings.ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]

app = FastAPI(
    title="AIShield Security API",
    description="Backend API for Anomaly Detection & Threat Monitoring",
    version="1.0.0"
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "AIShield Engine",
        "version": "1.0.0"
    }

