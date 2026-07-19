import os
from typing import List, Literal
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # "development" | "test" | "production" — production tightens validation
    # below (e.g. rejects the default localhost-only CORS origins). This is a
    # local discriminator only; it does not fetch secrets from anywhere — see
    # docs/SECRETS.md for how production secrets are actually supplied.
    environment: Literal["development", "test", "production"] = Field(
        default="development", validation_alias="ENVIRONMENT"
    )

    data_dir: str = Field(default="datasets/raw", validation_alias="DATA_DIR")
    model_path: str = Field(default="backend/models/checkpoints/lightgbm_baseline.pkl", validation_alias="MODEL_PATH")

    # SecretStr prevents the key from ever appearing in plain text in logs,
    # tracebacks, or a repr() of the settings object — callers must explicitly
    # call .get_secret_value() to use it.
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")

    allowed_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
        validation_alias="ALLOWED_ORIGINS"
    )

    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_production_config(self) -> "Settings":
        if self.environment != "production":
            return self

        localhost_markers = ("localhost", "127.0.0.1")
        if all(any(marker in origin for marker in localhost_markers) for origin in self.allowed_origins):
            raise ValueError(
                "ENVIRONMENT=production requires ALLOWED_ORIGINS to include at least one "
                "non-localhost origin (e.g. your Firebase Hosting URL) — refusing to start "
                "with only the local-development default."
            )

        if not os.path.exists(self.model_path):
            raise ValueError(
                f"ENVIRONMENT=production requires MODEL_PATH to point at an existing file "
                f"(got '{self.model_path}') — a production deployment cannot silently start "
                f"without a reconstruction model."
            )

        return self


settings = Settings()
