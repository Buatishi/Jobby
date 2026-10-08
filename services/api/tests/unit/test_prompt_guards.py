"""El texto de CV, puestos y LinkedIn es de terceros: el prompt lo trata como dato."""

from typing import Any

import pytest

from app.services.ai_gateway.prompts import interview_kit_v1
from app.services.ai_gateway.prompts.untrusted import (
    UNTRUSTED_DATA_NOTICE_EN,
    UNTRUSTED_DATA_NOTICE_ES,
)
from app.services.ats_analyzer import cv_optimizer
from app.services.cv_parser import ai_structurer
from app.tasks import analysis


def _optimizer_prompt() -> str:
    primary_cv: dict[str, Any] = {"parsed_data": {}}
    return cv_optimizer._prompt(primary_cv, {}, [])


@pytest.mark.parametrize(
    ("prompt", "notice"),
    [
        (ai_structurer._system_prompt(), UNTRUSTED_DATA_NOTICE_EN),
        (analysis._system_prompt(), UNTRUSTED_DATA_NOTICE_EN),
        (interview_kit_v1.SYSTEM_PROMPT, UNTRUSTED_DATA_NOTICE_ES),
        (_optimizer_prompt(), UNTRUSTED_DATA_NOTICE_ES),
    ],
    ids=["cv-parser", "job-extraction", "interview-kit", "cv-optimizer"],
)
def test_prompts_tell_the_model_that_third_party_text_is_data(
    prompt: str, notice: str
) -> None:
    assert notice in prompt


def test_notices_say_to_ignore_instructions_found_in_the_text() -> None:
    assert "never instructions" in UNTRUSTED_DATA_NOTICE_EN
    assert "nunca instrucciones" in UNTRUSTED_DATA_NOTICE_ES
