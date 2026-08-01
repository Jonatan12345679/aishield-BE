from fastapi import FastAPI

app = FastAPI(
    title="AIShield Security API",
    description="Backend API for Anomaly Detection & Threat Monitoring",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "AIShield Engine",
        "version": "1.0.0"
    }