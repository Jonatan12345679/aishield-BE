from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "AIShield API"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql://aishield:aishield123@localhost:5432/aishield_db"
    MODEL_PATH: str = "./ml/model/isolation_forest.pkl"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()