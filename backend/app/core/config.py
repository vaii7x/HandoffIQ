"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = Field(default="HandoffIQ", description="Application name")
    APP_ENV: str = Field(default="development", description="Environment: development, test, staging, production")
    API_PREFIX: str = Field(default="/api", description="Base prefix for application API routes")
    FRONTEND_ORIGIN: str = Field(default="http://localhost:3000", description="Allowed CORS origin for frontend")

    # Supabase configuration
    SUPABASE_URL: str = Field(
        default="http://localhost:54321",
        description="Supabase project URL"
    )
    SUPABASE_ANON_KEY: str = Field(
        default="placeholder-anon-key",
        description="Supabase client anonymous key"
    )
    SUPABASE_SERVICE_ROLE_KEY: SecretStr = Field(
        default=SecretStr("placeholder-service-role-key"),
        description="Supabase backend service role key - NEVER EXPOSE TO CLIENT"
    )

    # Gemini AI configuration
    GEMINI_API_KEY: SecretStr = Field(
        default=SecretStr("placeholder-gemini-key"),
        description="Gemini API Key - NEVER EXPOSE TO CLIENT"
    )

    # Operational flags
    MOCK_MODE: bool = Field(
        default=True,
        description="Run in mock mode without external API dependencies"
    )

    @property
    def is_production(self) -> bool:
        """Check if environment is production."""
        return self.APP_ENV.lower() == "production"

    def public_safe_dict(self) -> dict:
        """Return non-sensitive configuration values safe for diagnostics."""
        return {
            "app_name": self.APP_NAME,
            "app_env": self.APP_ENV,
            "api_prefix": self.API_PREFIX,
            "mock_mode": self.MOCK_MODE,
        }


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
