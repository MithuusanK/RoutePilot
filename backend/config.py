from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    Supabase PostgreSQL connection settings are loaded from .env file.
    """
    
    # Application
    app_name: str = "RoutePilot API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Supabase Database Connection
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_db_url: str = ""  # Full PostgreSQL connection string
    
    # Database Pool Settings
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    
    # CORS Settings (will be set by .env or use defaults)
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:5174"
    
    # Routing Service (for future Step 2)
    routing_service: str = "osrm"  # Options: osrm, openrouteservice
    osrm_base_url: str = "http://router.project-osrm.org"
    openrouteservice_api_key: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def database_url(self) -> str:
        """Return the Supabase PostgreSQL connection URL"""
        return self.supabase_db_url
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def async_database_url(self) -> str:
        """Return the async PostgreSQL connection URL (for asyncpg)"""
        # Convert postgresql:// to postgresql+asyncpg://
        if self.supabase_db_url.startswith("postgresql://"):
            return self.supabase_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.supabase_db_url


# Global settings instance
settings = Settings()
