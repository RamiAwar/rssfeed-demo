from functools import lru_cache

from pydantic import BaseSettings, PostgresDsn


class Settings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60 * 24 * 7  # 1 week
    REDIS_HOST: str
    REDIS_PORT: int
    POSTGRES_DSN: PostgresDsn

    @property
    def REDIS_DSN(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


@lru_cache
def get_settings() -> Settings:
    """Singleton-like, returns the application settings from environment variables"""
    return Settings()  # type: ignore
