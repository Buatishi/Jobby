"""La pista del dashboard sobre LinkedIn y Reality Gap.

Decía «Conectá tu LinkedIn para mejorar tu Reality Gap (+18 pts)» con el número escrito
a mano: eran los puntos de completitud del perfil (12 del PDF y 6 del enlace), no del
Reality Gap, y se mostraba entero aunque la persona ya tuviera uno de los dos. Reality
Gap compara con el PDF de LinkedIn; el enlace solo suma al porcentaje del perfil.
"""

import pytest

from app.api.v1.dashboard import _missing_tip
from app.services.profile_completeness import WEIGHTS
from tests.fakes import FakeSupabase


def _document(doc_type: str, *, status: str = "done", is_primary: bool = False) -> dict:
    return {
        "id": f"doc-{doc_type}-{status}",
        "user_id": "user-1",
        "profile_id": "profile-1",
        "type": doc_type,
        "status": status,
        "is_primary": is_primary,
    }


def _world(*documents: dict) -> tuple[FakeSupabase, dict]:
    supabase = FakeSupabase()
    supabase.tables["uploaded_documents"].extend(documents)
    return supabase, supabase.tables["master_profiles"][0]


@pytest.mark.asyncio
async def test_without_the_linkedin_pdf_it_asks_for_the_pdf_with_the_real_points() -> (
    None
):
    supabase, profile = _world(_document("cv", is_primary=True))

    tip = await _missing_tip(supabase, "user-1", profile)

    assert tip is not None
    assert "PDF de tu LinkedIn" in tip
    assert "Reality Gap" in tip
    assert f"+{WEIGHTS['linkedin_document']} pts" in tip
    assert "18" not in tip


@pytest.mark.asyncio
async def test_a_linkedin_pdf_that_failed_to_read_is_asked_for_again() -> None:
    supabase, profile = _world(
        _document("cv", is_primary=True),
        _document("linkedin", status="failed"),
    )

    tip = await _missing_tip(supabase, "user-1", profile)

    assert tip is not None
    assert "PDF de tu LinkedIn" in tip


@pytest.mark.asyncio
async def test_with_the_pdf_but_no_link_it_asks_for_the_link_with_its_own_points() -> (
    None
):
    supabase, profile = _world(
        _document("cv", is_primary=True),
        _document("linkedin"),
    )

    tip = await _missing_tip(supabase, "user-1", profile)

    assert tip is not None
    assert "enlace" in tip
    assert f"+{WEIGHTS['linkedin_url']} pts" in tip
    assert "Reality Gap" not in tip


@pytest.mark.asyncio
async def test_without_a_cv_the_cv_comes_first() -> None:
    supabase, profile = _world(_document("linkedin"))

    tip = await _missing_tip(supabase, "user-1", profile)

    assert tip == "Subí tu CV para empezar a recibir análisis."


@pytest.mark.asyncio
async def test_with_both_linkedin_pieces_it_moves_on_to_the_next_gap() -> None:
    supabase, profile = _world(
        _document("cv", is_primary=True),
        _document("linkedin"),
    )
    profile["linkedin_url"] = "https://www.linkedin.com/in/persona"

    tip = await _missing_tip(supabase, "user-1", profile)

    assert tip is not None
    assert "LinkedIn" not in tip
