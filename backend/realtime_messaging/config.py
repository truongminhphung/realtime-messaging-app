import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    jwt_secret: str = os.getenv("JWT_SECRET", "secret-key-here")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = (
        60  # Default expiration time for access tokens
    )
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Optional: Different configs for different environments
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"

    TTL: int = 3600

    SYSTEM_TIMEZONE: str = os.getenv("SYSTEM_TIMEZONE", "asia/ho_chi_minh")


settings = Settings()
