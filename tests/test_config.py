import pytest
from pydantic import ValidationError

from backend.config import Settings


def test_defaults_to_development_and_allows_localhost():
    settings = Settings(_env_file=None)
    assert settings.environment == "development"
    assert "http://localhost:5173" in settings.allowed_origins


def test_gemini_api_key_is_masked_as_secret_str():
    settings = Settings(_env_file=None, GEMINI_API_KEY="super-secret-value")
    assert "super-secret-value" not in str(settings.gemini_api_key)
    assert "super-secret-value" not in repr(settings)
    assert settings.gemini_api_key.get_secret_value() == "super-secret-value"


def test_production_rejects_localhost_only_origins(tmp_path):
    model_path = tmp_path / "model.pkl"
    model_path.write_text("stub")

    with pytest.raises(ValidationError, match="non-localhost origin"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            MODEL_PATH=str(model_path),
            ALLOWED_ORIGINS="http://localhost:5173,http://127.0.0.1:5173",
        )


def test_production_accepts_explicit_non_localhost_origin(tmp_path):
    model_path = tmp_path / "model.pkl"
    model_path.write_text("stub")

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        MODEL_PATH=str(model_path),
        ALLOWED_ORIGINS="https://traffitwin-ai.web.app",
    )
    assert settings.allowed_origins == ["https://traffitwin-ai.web.app"]


def test_production_requires_model_path_to_exist():
    with pytest.raises(ValidationError, match="MODEL_PATH to point at an existing file"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            MODEL_PATH="does/not/exist.pkl",
            ALLOWED_ORIGINS="https://traffitwin-ai.web.app",
        )


def test_development_does_not_require_model_path_to_exist():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        MODEL_PATH="does/not/exist.pkl",
    )
    assert settings.model_path == "does/not/exist.pkl"


def test_invalid_environment_value_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENVIRONMENT="staging")
