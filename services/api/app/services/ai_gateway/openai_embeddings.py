from typing import Any

import httpx

from app.config import settings
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.services.ai_gateway.retry import retry_with_backoff

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


class OpenAIEmbeddingsProvider:
    name = "openai_embeddings"
    model = "text-embedding-3-small"
    dimensions = 1536

    def __init__(self, api_key: str | None = None) -> None:
        raw_api_key = api_key if api_key is not None else settings.openai_api_key
        self.api_key = raw_api_key.strip().strip('"').strip("'")

    async def embed(self, text: str) -> list[float]:
        async def operation() -> list[float]:
            return await self._embed_once(text)

        return await retry_with_backoff(operation, delays=(30.0, 30.0))

    async def _embed_once(self, text: str) -> list[float]:
        if not self.api_key:
            raise ProviderUnavailableError(self.name, "Missing OPENAI_API_KEY.")

        payload = {
            "model": self.model,
            "input": text,
            "dimensions": self.dimensions,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENAI_EMBEDDINGS_URL,
                json=payload,
                headers=headers,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code == 401:
                    raise ProviderUnavailableError(
                        self.name,
                        "OpenAI rechazo la API key configurada. "
                        "Revisa OPENAI_API_KEY en Render.",
                    ) from exc
                raise ProviderUnavailableError(
                    self.name,
                    f"OpenAI embeddings devolvio HTTP {status_code}.",
                ) from exc
            data: dict[str, Any] = response.json()

        embeddings = data.get("data")
        if not isinstance(embeddings, list) or not embeddings:
            raise ProviderUnavailableError(self.name, "OpenAI returned no embeddings.")

        vector = embeddings[0].get("embedding")
        if not isinstance(vector, list) or len(vector) != self.dimensions:
            raise ProviderUnavailableError(
                self.name,
                "OpenAI returned an invalid embedding dimension.",
            )

        return [float(value) for value in vector]
