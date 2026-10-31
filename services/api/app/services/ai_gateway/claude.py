import logging
from typing import Any

import httpx

from app.config import settings
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.services.ai_gateway.retry import retry_with_backoff

logger = logging.getLogger("jobmatch.ai")

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


class ClaudeProvider:
    name = "claude"
    model = "claude-sonnet-4-5"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.anthropic_api_key

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        # Sin clave ningún intento puede andar: se falla antes de los reintentos.
        if not self.api_key:
            raise ProviderUnavailableError(self.name, "Missing ANTHROPIC_API_KEY.")

        async def operation() -> str:
            return await self._generate_once(prompt, system, json_mode)

        return await retry_with_backoff(operation, delays=(30.0, 60.0))

    async def _generate_once(
        self,
        prompt: str,
        system: str | None,
        json_mode: bool,
    ) -> str:
        user_prompt = prompt
        if json_mode:
            user_prompt = (
                f"{prompt}\n\nReturn only valid JSON. Do not include markdown."
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                ANTHROPIC_MESSAGES_URL,
                json=payload,
                headers=headers,
            )
            if response.is_error:
                logger.warning(
                    "Anthropic respondió HTTP %s: %s",
                    response.status_code,
                    _api_error_summary(response),
                )
            response.raise_for_status()
            data = response.json()

        return _extract_claude_content(data)


def _api_error_summary(response: httpx.Response) -> str:
    """Tipo y mensaje del error de Anthropic, cortado; nunca el pedido (lleva el CV).

    Un 400 puede ser «saldo insuficiente» o un pedido mal armado, y `raise_for_status`
    solo deja el código: sin esto el log no distingue una causa de la otra.
    """
    try:
        body = response.json()
    except ValueError:
        return "sin cuerpo JSON"
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return "sin detalle"
    return f"{error.get('type')}: {str(error.get('message'))[:200]}"


def _extract_claude_content(data: dict[str, Any]) -> str:
    content = data.get("content")
    if not isinstance(content, list):
        raise ProviderUnavailableError("claude", "Claude returned invalid content.")

    text_parts = [
        block.get("text")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    text = "\n".join(part for part in text_parts if isinstance(part, str)).strip()
    if not text:
        raise ProviderUnavailableError("claude", "Claude returned empty content.")

    return text
