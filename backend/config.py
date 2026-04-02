from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    OPENWEATHER_API_KEY: str = ""
    TOMTOM_API_KEY: str = ""
    CPCB_API_KEY: str = ""
    CITY_NAME: str = "Delhi"
    CITY_LAT: float = 28.6139
    CITY_LNG: float = 77.2090

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
