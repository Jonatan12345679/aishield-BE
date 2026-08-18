from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "AIShield API"

    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+psycopg2://aishield:aishield123@postgres:5432/aishield_db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    APP_ENV: str = "development"

    ML_MODEL_PATH: str = "./ml/aishield/model/isolation_forest.pkl"
    ML_SCALER_PATH: str = "ml/aishield/model/scaler.pkl"
    ML_METRICS_PATH: str = "ml/aishield/model/metrics.json"
    ML_FEATURE_COLUMNS_PATH: str = "ml/aishield/model/feature_columns.json"

    ALLOWED_ORIGINS: str = ""

    # Risk threshold buat risk_calculator mapping skor utk level bahaya

    # makin negatif anomaly_score, makin "aneh" datanya
    RISK_THRESHOLD_LOW: float = -0.05
    RISK_THRESHOLD_MEDIUM: float = -0.15
    RISK_THRESHOLD_HIGH: float = -0.25
 
    #  WebSocket (dipakai nanti pas bikin endpoint realtime) 
    WS_BROADCAST_INTERVAL_SEC: float = 1.0
 
    #  CORS, biar frontend Vite bisa akses API ini 
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    MODEL_PRIVACY_DETECTION_KTP_PATH: str
    MODEL_PRIVACY_DETECTION_PLAT_NOMOR_PATH: str
    MODEL_PRIVACY_DETECTION_QR_CODE_PATH: str
    MODEL_PRIVACY_DETECTION_STRUK_PATH: str
    MODEL_PRIVACY_DETECTION_STRUK_AND_KTP_PATH: str

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()