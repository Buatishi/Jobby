from typing import Any

import httpx

from app.config import settings
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.services.ai_gateway.retry import retry_with_backoff

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"


class DeepSeekProvider:
    name = "deepseek"
    model = "deepseek-chat"

    def __init__(self, api_key: str | None = None) -> None:
        raw_api_key = api_key if api_key is not None else settings.deepseek_api_key
        self.api_key = raw_api_key.strip().strip('"').strip("'")

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        async def operation() -> str:
            return await self._generate_once(prompt, system, json_mode)

        return await retry_with_backoff(operation, delays=(30.0, 60.0))

    async def _generate_once(
        self,
        prompt: str,
        system: str | None,
        json_mode: bool,
    ) -> str:
        if not self.api_key:
            raise ProviderUnavailableError(self.name, "Missing DEEPSEEK_API_KEY.")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                DEEPSEEK_CHAT_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        return _extract_openai_compatible_content(data, self.name)


def _extract_openai_compatible_content(data: dict[str, Any], provider: str) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderUnavailableError(provider, "Provider returned no choices.")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ProviderUnavailableError(provider, "Provider returned invalid message.")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ProviderUnavailableError(provider, "Provider returned empty content.")

    return content
