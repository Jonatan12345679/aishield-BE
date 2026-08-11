from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AIShield API"

    DEBUG: bool = True

    DATABASE_URL: str = (
        "postgresql://aishield:aishield123@localhost:5432/aishield_db"
    )

    # Model ONNX Privacy Detection
    MODEL_PRIVACY_DETECTION_PATH: str = (
        "./ml/privacy-detection-model/weights/best.onnx"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()