import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai.errors import APIError

from backend.services import gemini_service as gemini_service_module
from backend.services.gemini_service import GeminiService


@pytest.fixture(autouse=True)
def _no_local_gemini_key(monkeypatch):
    """GeminiService falls back to settings.gemini_api_key when api_key=None.
    A developer's local .env may have a real key configured, which would make
    "offline mode" tests silently attempt real network calls. Force it off so
    these tests are deterministic regardless of the local environment."""
    monkeypatch.setattr(gemini_service_module.settings, "gemini_api_key", None)


def _service_with_fake_client():
    """Build a GeminiService without hitting the real google-genai SDK by
    constructing with no api_key (client stays None) and then swapping in a
    fake client — avoids needing real credentials or network access."""
    service = GeminiService(api_key=None)
    service.client = MagicMock()
    return service


def test_no_api_key_means_offline_mode():
    service = GeminiService(api_key=None)
    assert service.client is None


def test_enrich_report_without_client_raises_value_error():
    service = GeminiService(api_key=None)
    with pytest.raises(ValueError):
        asyncio.run(service.enrich_report({"sensor_id": 1}, "base report"))


def test_enrich_report_returns_stripped_text_on_success():
    service = _service_with_fake_client()
    fake_response = MagicMock()
    fake_response.text = "  Enriched operational summary.  "
    service.client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    result = asyncio.run(service.enrich_report({"sensor_id": 1}, "base report"))
    assert result == "Enriched operational summary."


def test_enrich_report_raises_on_empty_response_text():
    service = _service_with_fake_client()
    fake_response = MagicMock()
    fake_response.text = ""
    service.client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    with pytest.raises(ValueError):
        asyncio.run(service.enrich_report({"sensor_id": 1}, "base report"))


def test_enrich_report_raises_on_timeout():
    service = _service_with_fake_client()

    async def _hang(*args, **kwargs):
        await asyncio.sleep(10)

    service.client.aio.models.generate_content = _hang
    service.timeout = 0.05

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(service.enrich_report({"sensor_id": 1}, "base report"))


def test_enrich_report_propagates_api_error():
    service = _service_with_fake_client()
    error = APIError(code=503, response_json={"error": {"message": "unavailable"}})
    service.client.aio.models.generate_content = AsyncMock(side_effect=error)

    with pytest.raises(APIError):
        asyncio.run(service.enrich_report({"sensor_id": 1}, "base report"))
