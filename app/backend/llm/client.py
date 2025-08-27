import os
from typing import Any, Dict

class GeminiClient:
    """Minimal stub client for Gemini API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    def to_sql(self, question: str, filters: Dict[str, Any] | None = None) -> str:
        """Return a naive SQL query for testing purposes."""
        return "SELECT COUNT(*) AS total FROM licencias"

    def summarize(self, text: str) -> str:
        return "Sin resumen disponible"
