from typing import Any

import httpx

from app.config import settings
from app.services.ai_gateway.errors import (
    ProviderQuotaExceededError,
    ProviderUnavailableError,
)
from app.services.ai_gateway.retry import retry_with_backoff

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


def _quota_exhausted(response: httpx.Response) -> bool:
    # OpenAI avisa la falta de saldo con un 429 y el código insufficient_quota; un 429
    # sin ese código es un límite de pedidos por minuto, que sí se arregla esperando.
    try:
        payload = response.json()
    except ValueError:
        return False
    error = payload.get("error") if isinstance(payload, dict) else None
    return isinstance(error, dict) and error.get("code") == "insufficient_quota"


class OpenAIEmbeddingsProvider:
    name = "openai_embeddings"
    model = "text-embedding-3-small"
    dimensions = 1536

    def __init__(self, api_key: str | None = None) -> None:
        raw_api_key = api_key if api_key is not None else settings.openai_api_key
        self.api_key = raw_api_key.strip().strip('"').strip("'")

    def _require_api_key(self) -> None:
        # Sin clave ningún intento puede andar: se falla antes de los reintentos.
        if not self.api_key:
            raise ProviderUnavailableError(self.name, "Missing OPENAI_API_KEY.")

    async def embed(self, text: str) -> list[float]:
        self._require_api_key()

        async def operation() -> list[float]:
            embeddings = await self._embed_many_once([text])
            return embeddings[0]

        return await retry_with_backoff(operation, delays=(30.0, 30.0))

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._require_api_key()

        async def operation() -> list[list[float]]:
            return await self._embed_many_once(texts)

        return await retry_with_backoff(operation, delays=(30.0, 30.0))

    async def _embed_many_once(self, texts: list[str]) -> list[list[float]]:
        payload = {
            "model": self.model,
            "input": texts,
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
                if status_code == 429 and _quota_exhausted(exc.response):
                    raise ProviderQuotaExceededError(
                        self.name,
                        "OpenAI no tiene saldo disponible. "
                        "Carga credito en la cuenta de OpenAI.",
                    ) from exc
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
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise ProviderUnavailableError(self.name, "OpenAI returned no embeddings.")

        ordered_embeddings = sorted(
            embeddings,
            key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0,
        )
        vectors: list[list[float]] = []
        for embedding in ordered_embeddings:
            if not isinstance(embedding, dict):
                raise ProviderUnavailableError(
                    self.name,
                    "OpenAI returned an invalid embedding payload.",
                )
            vector = embedding.get("embedding")
            if not isinstance(vector, list) or len(vector) != self.dimensions:
                raise ProviderUnavailableError(
                    self.name,
                    "OpenAI returned an invalid embedding dimension.",
                )
            vectors.append([float(value) for value in vector])

        return vectors
