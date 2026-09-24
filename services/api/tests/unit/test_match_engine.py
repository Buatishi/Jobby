import pytest

from app.services.match_engine import compute_match_score
from app.tasks.matching import run_match
from tests.fakes import FakeSupabase


def _embedding(seed: float) -> list[float]:
    return [seed, 1.0 - seed, 0.5]


def _profile(index: int) -> dict[str, object]:
    seniorities = ["junior", "mid", "senior", "staff", "principal"]
    modalities = ["remote", "hybrid", "onsite"]
    return {
        "id": f"profile-{index}",
        "user_id": f"user-{index}",
        "target_seniority": seniorities[index % len(seniorities)],
        "work_modality": modalities[index % len(modalities)],
        "target_industry": ["software", "saas"] if index % 2 == 0 else ["finance"],
        "inferred_soft_skills": [],
        "embedding": _embedding(0.8 if index % 2 == 0 else 0.2),
    }


def _job(index: int) -> dict[str, object]:
    seniorities = ["junior", "mid", "senior", "staff", "principal"]
    modalities = ["remote", "hybrid", "onsite"]
    tech_stack = ["python", "fastapi"] if index % 2 == 0 else ["java", "spring"]
    return {
        "id": f"job-{index}",
        "user_id": f"user-{index}",
        "job_title": "Backend Engineer",
        "required_seniority": seniorities[index % len(seniorities)],
        "required_modality": modalities[index % len(modalities)],
        "industry": "software" if index % 2 == 0 else "finance",
        "tech_stack": tech_stack,
        "required_skills": tech_stack,
        "soft_skills": ["problem_solving", "communication"],
        "required_education": "bachelor",
        "required_languages": [{"name": "english", "level": "advanced"}],
        "embedding": _embedding(0.8 if index % 2 == 0 else 0.2),
    }


def _seed_golden_dataset(db: FakeSupabase) -> None:
    db.tables["users"] = [
        {
            "id": f"user-{index}",
            "supabase_uid": f"auth-user-{index}",
            "email": f"user{index}@example.com",
            "tier": "free",
        }
        for index in range(10)
    ]
    db.tables["master_profiles"] = [_profile(index) for index in range(10)]
    db.tables["job_descriptions"] = [_job(index) for index in range(10)]

    for index in range(10):
        profile_id = f"profile-{index}"
        uses_python = index % 2 == 0
        primary_skills = ["python", "fastapi"] if uses_python else ["java", "spring"]
        for skill in primary_skills + ["communication"]:
            db.tables["skills"].append(
                {
                    "id": f"skill-{index}-{skill}",
                    "profile_id": profile_id,
                    "name": skill,
                    "category": "technical" if skill != "communication" else "soft",
                    "level": "advanced",
                    "in_cv": True,
                    "confirmed": True,
                    "embedding": _embedding(0.8 if uses_python else 0.2),
                }
            )
        db.tables["educations"].append(
            {
                "id": f"edu-{index}",
                "profile_id": profile_id,
                "institution": "Tech University",
                "field_of_study": "Computer Science",
                "degree_level": "bachelor",
                "is_ongoing": index % 3 == 0,
                "embedding": _embedding(0.8 if uses_python else 0.2),
            }
        )
        db.tables["certifications"].append(
            {
                "id": f"cert-{index}",
                "profile_id": profile_id,
                "name": "Cloud Practitioner",
            }
        )
        db.tables["languages"].append(
            {
                "id": f"lang-{index}",
                "profile_id": profile_id,
                "name": "english",
                "proficiency": "advanced" if index != 3 else "basic",
            }
        )
        db.tables["experiences"].append(
            {
                "id": f"exp-{index}",
                "profile_id": profile_id,
                "company": "Acme",
                "title": "Engineer",
                "description": "Solved incidents and documented platform decisions.",
                "achievements": ["Improved latency by 20%", "Presented results"],
            }
        )
        db.tables["uploaded_documents"].append(
            {
                "id": f"doc-{index}",
                "user_id": f"user-{index}",
                "profile_id": profile_id,
                "type": "cv",
                "is_primary": True,
                "parsed_data": {
                    "skills": [{"name": skill} for skill in primary_skills]
                },
            }
        )


class FakeReasoningGateway:
    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        return (
            "- Buen fit por skills backend.\n"
            "- Agregá React al CV.\n"
            "- Mencioná liderazgo en incidentes."
        )


@pytest.mark.asyncio
async def test_golden_dataset_scores_10_profiles_by_10_jobs() -> None:
    db = FakeSupabase()
    _seed_golden_dataset(db)

    results = []
    for profile_index in range(10):
        for job_index in range(10):
            result = await compute_match_score(
                f"profile-{profile_index}",
                f"job-{job_index}",
                db,
            )
            results.append(result)
            assert 0 <= result.match_score <= 100
            assert result.potential_score >= result.match_score
            assert 0 <= result.representation_score <= 100
            assert result.gap_origin in {"skills", "seniority", "both", "none"}
            assert set(result.score_breakdown["sub_scores"]) == {
                "skills",
                "seniority",
                "education",
                "languages",
                "company",
                "soft",
            }

    same_profile_job = await compute_match_score("profile-0", "job-0", db)
    mismatched_job = await compute_match_score("profile-0", "job-1", db)

    assert same_profile_job.match_score > mismatched_job.match_score
    assert same_profile_job.representation_score == 100
    assert db.tables["master_profiles"][0]["inferred_soft_skills"]
    assert len(results) == 100


@pytest.mark.asyncio
async def test_run_match_persists_full_score_breakdown() -> None:
    db = FakeSupabase()
    _seed_golden_dataset(db)

    match = await run_match(
        "job-0",
        "profile-0",
        "user-0",
        supabase=db,
        gateway=FakeReasoningGateway(),  # type: ignore[arg-type]
    )

    assert match["match_score"] >= 80
    assert match["potential_score"] >= match["match_score"]
    assert match["ai_model_used"] == "deepseek-chat"
    assert match["recommendations"]
    assert db.tables["job_matches"][0]["score_breakdown"]["sub_scores"]["skills"] == 1.0
