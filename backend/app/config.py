from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OrganChip Insight API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    data_dir: Path = Path("data")
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    max_upload_mb: int = Field(default=25, ge=1, le=25)
    max_image_pixels: int = Field(default=16_777_216, ge=1, le=16_777_216)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ORGANCHIP_",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_path(self) -> Path:
        return self.data_dir / "organchip.sqlite3"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
