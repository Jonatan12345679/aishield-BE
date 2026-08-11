from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "AIShield API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = (
        "postgresql+psycopg2://aishield:aishield123@postgres:5432/aishield_db"
    )
    DB_ECHO: bool = False  # set True kalau mau lihat query SQL di log (debug only)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Ml model
    ML_MODEL_PATH: str = "ml/aishield/model/isolation_forest.pkl"
    ML_SCALER_PATH: str = "ml/aishield/model/scaler.pkl"
    ML_METRICS_PATH: str = "ml/aishield/model/metrics.json"
    ML_CONTAMINATION: float = 0.12 

    RISK_THRESHOLD_LOW: float = -0.05
    RISK_THRESHOLD_MEDIUM: float = -0.15
    RISK_THRESHOLD_HIGH: float = -0.25

    # WebSocket
    WS_BROADCAST_INTERVAL_SEC: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()