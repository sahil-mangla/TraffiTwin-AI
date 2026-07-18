import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    data_dir: str = Field(default="datasets/raw", validation_alias="DATA_DIR")
    model_path: str = Field(default="backend/models/checkpoints/lightgbm_baseline.pkl", validation_alias="MODEL_PATH")
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    allowed_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
        validation_alias="ALLOWED_ORIGINS"
    )

    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]

settings = Settings()
