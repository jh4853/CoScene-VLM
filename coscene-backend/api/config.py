"""
Application configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/coscene"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Anthropic API
    anthropic_api_key: str

    # Application
    max_session_cost_usd: float = 5.0
    render_quality_default: str = "preview"
    blender_gpu_enabled: bool = False

    # Agent Configuration
    # Set to False to disable visual context for ablation studies
    enable_input_rendering: bool = True
    # Set to False to disable verification/fix loop for ablation studies
    enable_verification_loop: bool = True
    # Maximum number of fix iterations
    max_verification_attempts: int = 3

    # Development
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
