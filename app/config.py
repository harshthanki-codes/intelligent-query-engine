from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:latest"
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True
    cache_ttl: int = 3600
    log_level: str = "INFO"
    api_title: str = "Intelligent Query & Insight Engine"
    api_version: str = "1.0.0"
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()