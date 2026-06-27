import pytest

from app.services.ai_gateway import AIGateway
from app.services.ai_gateway.errors import PremiumRequiredError


class MockProvider:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[str, str | None, bool]] = []

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        self.calls.append((prompt, system, json_mode))
        return self.name


class MockEmbeddingsProvider:
    async def embed(self, _text: str) -> list[float]:
        return [0.1] * 1536


@pytest.mark.asyncio
async def test_cv_parsing_always_uses_deepseek() -> None:
    deepseek = MockProvider("deepseek")
    claude = MockProvider("claude")
    gateway = AIGateway(
        deepseek=deepseek,
        claude=claude,
        embeddings=MockEmbeddingsProvider(),
    )

    result = await gateway.generate("cv_parsing", "premium", "parse cv")

    assert result == "deepseek"
    assert len(deepseek.calls) == 1
    assert claude.calls == []


@pytest.mark.asyncio
async def test_match_reasoning_routes_by_tier() -> None:
    deepseek = MockProvider("deepseek")
    claude = MockProvider("claude")
    gateway = AIGateway(
        deepseek=deepseek,
        claude=claude,
        embeddings=MockEmbeddingsProvider(),
    )

    free_result = await gateway.generate("match_reasoning", "free", "reason")
    premium_result = await gateway.generate("match_reasoning", "premium", "reason")

    assert free_result == "deepseek"
    assert premium_result == "claude"


@pytest.mark.asyncio
async def test_reality_gap_routes_by_tier() -> None:
    deepseek = MockProvider("deepseek")
    claude = MockProvider("claude")
    gateway = AIGateway(
        deepseek=deepseek,
        claude=claude,
        embeddings=MockEmbeddingsProvider(),
    )

    free_result = await gateway.generate("reality_gap", "free", "gap")
    premium_result = await gateway.generate("reality_gap", "premium", "gap")

    assert free_result == "deepseek"
    assert premium_result == "claude"


@pytest.mark.asyncio
async def test_premium_only_tasks_use_claude_for_premium() -> None:
    gateway = AIGateway(
        deepseek=MockProvider("deepseek"),
        claude=MockProvider("claude"),
        embeddings=MockEmbeddingsProvider(),
    )

    assert await gateway.generate("cv_optimization", "premium", "optimize") == "claude"
    assert await gateway.generate("interview_kit", "premium", "kit") == "claude"


@pytest.mark.asyncio
async def test_premium_only_tasks_reject_free_tier() -> None:
    gateway = AIGateway(
        deepseek=MockProvider("deepseek"),
        claude=MockProvider("claude"),
        embeddings=MockEmbeddingsProvider(),
    )

    with pytest.raises(PremiumRequiredError):
        await gateway.generate("cv_optimization", "free", "optimize")

    with pytest.raises(PremiumRequiredError):
        await gateway.generate("interview_kit", "free", "kit")
