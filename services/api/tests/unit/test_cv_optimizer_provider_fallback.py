"""Si Claude falla, un premium recibe el CV optimizado con el modelo gratis."""

import json
import logging

import httpx
import pytest

from app.models.ats import ATSKeywordMatch
from app.services.ai_gateway.errors import ProviderUnavailableError
from app.services.ats_analyzer.cv_optimizer import optimize_cv_sections

MATCHES = [
    ATSKeywordMatch(keyword="Python", status="literal", matched_text="Python"),
    ATSKeywordMatch(keyword="Kubernetes", status="missing"),
]
PRIMARY_CV = {"parsed_data": {"skills": [{"name": "Python"}, {"name": "SQL"}]}}
JOB = {"job_title": "Backend"}
ANSWER = json.dumps(
    {
        "sections": [
            {
                "section_name": "skills",
                "original_excerpt": "Python, SQL",
                "rewritten_text": "Python y SQL",
                "added_keywords": [],
                "rationale": "Ordena lo que el CV ya dice.",
            }
        ]
    }
)


def _claude_rejects_the_request() -> httpx.HTTPStatusError:
    """Lo que dejó el 500 de producción: Anthropic respondió 400 y nadie lo atajó."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx.HTTPStatusError(
        "Client error '400 Bad Request' for url 'https://api.anthropic.com/v1/messages'",
        request=request,
        response=httpx.Response(400, request=request),
    )


class ScriptedGateway:
    """Responde o falla según el plan, como el AIGateway real según el proveedor."""

    def __init__(self, **by_tier: str | Exception) -> None:
        self.by_tier = by_tier
        self.calls: list[str] = []

    async def generate(
        self,
        _task_type: str,
        user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        self.calls.append(user_tier)
        outcome = self.by_tier[user_tier]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def _optimize(gateway: ScriptedGateway, tier: str) -> list[str]:
    sections = await optimize_cv_sections(
        PRIMARY_CV,
        JOB,
        MATCHES,
        tier,  # type: ignore[arg-type]
        gateway,  # type: ignore[arg-type]
    )
    return [section.rewritten_text for section in sections]


@pytest.mark.asyncio
async def test_a_premium_plan_keeps_claude_when_it_answers() -> None:
    gateway = ScriptedGateway(premium=ANSWER)

    assert await _optimize(gateway, "premium") == ["Python y SQL"]
    assert gateway.calls == ["premium"]


@pytest.mark.asyncio
async def test_a_premium_plan_falls_back_to_the_free_model_when_claude_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    gateway = ScriptedGateway(premium=_claude_rejects_the_request(), free=ANSWER)

    with caplog.at_level(logging.WARNING, logger="jobmatch.ats"):
        assert await _optimize(gateway, "premium") == ["Python y SQL"]

    assert gateway.calls == ["premium", "free"]
    assert "HTTPStatusError" in caplog.text
    assert "premium" in caplog.text


@pytest.mark.asyncio
async def test_a_premium_plan_falls_back_when_claude_returns_broken_json() -> None:
    gateway = ScriptedGateway(premium="esto no es JSON", free=ANSWER)

    assert await _optimize(gateway, "premium") == ["Python y SQL"]
    assert gateway.calls == ["premium", "free"]


@pytest.mark.asyncio
async def test_it_reports_the_ai_as_unavailable_when_no_plan_answers() -> None:
    gateway = ScriptedGateway(
        premium=_claude_rejects_the_request(),
        free=ProviderUnavailableError("deepseek", "Missing DEEPSEEK_API_KEY."),
    )

    with pytest.raises(ProviderUnavailableError):
        await _optimize(gateway, "premium")

    assert gateway.calls == ["premium", "free"]


@pytest.mark.asyncio
async def test_the_free_plan_has_nothing_to_fall_back_to() -> None:
    gateway = ScriptedGateway(
        free=ProviderUnavailableError("deepseek", "Missing DEEPSEEK_API_KEY.")
    )

    with pytest.raises(ProviderUnavailableError):
        await _optimize(gateway, "free")

    assert gateway.calls == ["free"]
