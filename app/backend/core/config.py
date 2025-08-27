from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    duckdb_path: str = "data/warehouse.duckdb"

    class Config:
        env_file = ".env"

settings = Settings()
