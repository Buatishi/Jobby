from typing import Literal

from app.services.ai_gateway.base import AIProvider
from app.services.ai_gateway.claude import ClaudeProvider
from app.services.ai_gateway.deepseek import DeepSeekProvider
from app.services.ai_gateway.errors import PremiumRequiredError
from app.services.ai_gateway.openai_embeddings import OpenAIEmbeddingsProvider

TaskType = Literal[
    "cv_parsing",
    "match_reasoning",
    "reality_gap",
    "interview_kit",
    "cv_optimization",
]
UserTier = Literal["free", "premium"]


class AIGateway:
    def __init__(
        self,
        deepseek: AIProvider | None = None,
        claude: AIProvider | None = None,
        embeddings: OpenAIEmbeddingsProvider | None = None,
    ) -> None:
        self.deepseek = deepseek or DeepSeekProvider()
        self.claude = claude or ClaudeProvider()
        self.embeddings = embeddings or OpenAIEmbeddingsProvider()

    def select_provider(self, task_type: TaskType, user_tier: UserTier) -> AIProvider:
        if task_type == "cv_parsing":
            return self.deepseek

        if task_type in {"cv_optimization", "interview_kit"}:
            if user_tier != "premium":
                raise PremiumRequiredError(task_type)
            return self.claude

        if task_type in {"match_reasoning", "reality_gap"}:
            return self.claude if user_tier == "premium" else self.deepseek

        raise ValueError(f"Unsupported task_type: {task_type}")

    async def generate(
        self,
        task_type: TaskType,
        user_tier: UserTier,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        provider = self.select_provider(task_type, user_tier)
        return await provider.generate(prompt, system, json_mode)

    async def embed(self, text: str) -> list[float]:
        return await self.embeddings.embed(text)


__all__ = [
    "AIGateway",
    "ClaudeProvider",
    "DeepSeekProvider",
    "OpenAIEmbeddingsProvider",
    "PremiumRequiredError",
]
