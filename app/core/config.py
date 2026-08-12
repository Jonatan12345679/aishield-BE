from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "AIShield API"

    DEBUG: bool = True

    DATABASE_URL: str = (
        "postgresql://aishield:aishield123@localhost:5432/aishield_db"
    )

    MODEL_PATH: str = "./ml/model/isolation_forest.pkl"

    MODEL_PRIVACY_DETECTION_KTP_PATH: str

    MODEL_PRIVACY_DETECTION_PLAT_NOMOR_PATH: str

    MODEL_PRIVACY_DETECTION_QR_CODE_PATH: str

    MODEL_PRIVACY_DETECTION_STRUK_PATH: str

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()