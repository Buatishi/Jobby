import httpx
import pytest

from app.services.ai_gateway import AIGateway
from app.services.ai_gateway.errors import (
    PremiumRequiredError,
    ProviderUnavailableError,
)
from app.services.ai_gateway.openai_embeddings import (
    OPENAI_EMBEDDINGS_URL,
    OpenAIEmbeddingsProvider,
)


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

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _text in texts]


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


def test_openai_embeddings_api_key_is_normalized() -> None:
    provider = OpenAIEmbeddingsProvider(' "sk-test" ')

    assert provider.api_key == "sk-test"


@pytest.mark.asyncio
async def test_openai_embeddings_unauthorized_returns_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status_code = 401

        def raise_for_status(self) -> None:
            request = httpx.Request("POST", OPENAI_EMBEDDINGS_URL)
            response = httpx.Response(401, request=request)
            raise httpx.HTTPStatusError(
                "unauthorized",
                request=request,
                response=response,
            )

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.ai_gateway.openai_embeddings.httpx.AsyncClient",
        FakeClient,
    )

    provider = OpenAIEmbeddingsProvider("bad-key")

    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.embed("Python")

    assert "OPENAI_API_KEY" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openai_embeddings_batches_multiple_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "data": [
                    {"index": 0, "embedding": [0.1] * 1536},
                    {"index": 1, "embedding": [0.2] * 1536},
                ]
            }

    class FakeClient:
        posted_payloads: list[dict[str, object]] = []

        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> FakeResponse:
            self.posted_payloads.append(kwargs["json"])  # type: ignore[arg-type]
            return FakeResponse()

    monkeypatch.setattr(
        "app.services.ai_gateway.openai_embeddings.httpx.AsyncClient",
        FakeClient,
    )

    provider = OpenAIEmbeddingsProvider("sk-test")
    result = await provider.embed_many(["Python", "FastAPI"])

    assert result == [[0.1] * 1536, [0.2] * 1536]
    assert FakeClient.posted_payloads[0]["input"] == ["Python", "FastAPI"]
