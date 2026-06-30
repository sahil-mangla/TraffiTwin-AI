import os
import asyncio
import logging
from typing import Optional
from google import genai
from google.genai.errors import APIError

logger = logging.getLogger(__name__)

class GeminiService:
    """
    Asynchronous Gemini API service using google-genai SDK.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash", timeout: float = 5.0):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.timeout = timeout
        self.client = None

        if not self.api_key:
            logger.warning("GEMINI_API_KEY environment variable not set. GeminiService will run in offline fallback mode.")
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize google-genai Client: {e}")

    async def enrich_report(self, incident: dict, deterministic_report: str) -> str:
        if not self.client:
            raise ValueError("Gemini client is not initialized (missing API key or initialization failure)")

        prompt = (
            "You are an expert traffic operations analyst.\n\n"
            "Rewrite the provided deterministic incident report for a smart-city traffic operations center.\n\n"
            "Requirements:\n"
            "* Preserve all numerical values exactly.\n"
            "* Never invent statistics.\n"
            "* Never hallucinate.\n"
            "* Use concise operational language.\n"
            "* Maximum 120 words.\n"
            "* Maintain factual faithfulness.\n\n"
            f"Structured Incident:\n{incident}\n\n"
            f"Base Report:\n{deterministic_report}"
        )

        try:
            # Enforce strict 5 second timeout on the async API request
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt
                ),
                timeout=self.timeout
            )
            if response and response.text:
                return response.text.strip()
            raise ValueError("Gemini API returned an empty text response")
        except asyncio.TimeoutError as e:
            logger.error("Gemini API request timed out.")
            raise e
        except APIError as e:
            logger.error(f"Gemini APIError: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini API: {e}")
            raise e
