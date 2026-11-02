"""El reporte ATS se calcula una vez y después se lee (Decisión 33).

Antes cada apertura rehacía todo: pedía las keywords a la IA (y salían distintas cada
vez), pedía los vectores a OpenAI y gastaba una de las 5 consultas diarias del plan
gratuito. Ahora el último reporte de cada puesto se guarda, con sus keywords, y vale
mientras no cambie el CV principal.
"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api.v1.ats import _build_ats_report
from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from app.services.ats_analyzer.keyword_matcher import analyze_keywords
from app.services.ats_analyzer.report_store import (
    ATS_REPORT_VERSION,
    cv_fingerprint,
)
from tests.fakes import FakeRedis, FakeSupabase, FakeTableQuery

KEYWORDS = ["Python", "GraphQL", "REST APIs"]
# Lo que guarda la lectura de un CV sin problemas de formato.
NO_FORMAT_PROBLEMS = {
    "has_tables": False,
    "multi_column": False,
    "has_images": False,
    "headers": [],
}


class KeywordGateway:
    """Cuenta cada pedido a la IA y a los vectores; no sale a la red."""

    def __init__(self, answers: list[list[str]] | None = None) -> None:
        self.answers = answers or [KEYWORDS]
        self.generate_calls = 0
        self.embed_batches: list[list[str]] = []

    async def generate(
        self,
        _task_type: str,
        _user_tier: str,
        _prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        answer = self.answers[min(self.generate_calls, len(self.answers) - 1)]
        self.generate_calls += 1
        return json.dumps({"keywords": answer})

    def _vector(self, text: str) -> list[float]:
        # Lo que habla de APIs se parece entre sí; GraphQL y el resto no se parecen a
        # nada del CV.
        if "api" in text.lower():
            return [1.0, 0.0, 0.0]
        return [0.0, 1.0, 0.0] if text == "GraphQL" else [0.0, 0.0, 1.0]

    async def embed(self, text: str) -> list[float]:
        return self._vector(text)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        self.embed_batches.append(list(texts))
        return [self._vector(text) for text in texts]


async def _free_user() -> CurrentUser:
    return CurrentUser(id="user-1", supabase_uid="auth-user-1", email="p@example.com")


def _cv_document(document_id: str = "doc-1", *, primary: bool = True) -> dict[str, Any]:
    return {
        "id": document_id,
        "user_id": "user-1",
        "profile_id": "profile-1",
        "type": "cv",
        "is_primary": primary,
        "parsed_data": {
            "skills": [{"name": "Python"}, {"name": "Diseño de APIs"}],
            "experiences": [{"title": "Backend dev", "description": "Built services"}],
            "format_flags": {**NO_FORMAT_PROBLEMS},
        },
    }


def _job(job_id: str = "job-1") -> dict[str, Any]:
    return {
        "id": job_id,
        "user_id": "user-1",
        "job_title": "Backend Engineer",
        "tech_stack": ["Python"],
        "required_skills": ["GraphQL"],
        "raw_text": "Buscamos backend con Python, GraphQL y REST APIs",
    }


def _world(jobs: int = 1) -> FakeSupabase:
    supabase = FakeSupabase()
    supabase.tables["job_descriptions"].extend(
        _job(f"job-{n}") for n in range(1, jobs + 1)
    )
    supabase.tables["uploaded_documents"].append(_cv_document())
    return supabase


@pytest.fixture()
def gateway(monkeypatch: pytest.MonkeyPatch) -> KeywordGateway:
    fake = KeywordGateway()
    monkeypatch.setattr(
        "app.services.ats_analyzer.keyword_matcher.AIGateway", lambda: fake
    )
    return fake


def _serve(supabase: FakeSupabase) -> None:
    async def fake_client() -> FakeSupabase:
        return supabase

    app.dependency_overrides[get_current_user] = _free_user
    app.dependency_overrides[get_supabase_client] = fake_client


def _queries_spent(redis: FakeRedis) -> int:
    return sum(
        int(value)
        for key, value in redis.values.items()
        if key.startswith("rate:ats:user-1:")
    )


def _open(client: TestClient, job_id: str = "job-1") -> Any:
    return client.get(f"/api/v1/ats/{job_id}")


def test_the_first_opening_calculates_and_saves_the_report(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    supabase = _world()
    _serve(supabase)

    response = _open(client)

    assert response.status_code == 200
    body = response.json()
    # Python literal (1) + REST APIs por significado (0,5) + GraphQL faltante, de 3:
    # 50 de contenido, que valen 45 sobre 90, y el formato sin avisos suma 10.
    assert body["ats_score"] == 55
    assert body["format_points"] == 10
    assert {m["keyword"]: m["status"] for m in body["keyword_matches"]} == {
        "GraphQL": "missing",
        "Python": "literal",
        "REST APIs": "semantic",
    }
    assert gateway.generate_calls == 1
    assert _queries_spent(fake_redis) == 1

    [saved] = supabase.tables["ats_reports"]
    assert saved["job_id"] == "job-1"
    assert saved["user_id"] == "user-1"
    assert saved["cv_document_id"] == "doc-1"
    assert saved["ats_score"] == 55
    assert saved["keyword_matches"] == body["keyword_matches"]
    # El puesto no se toca: el reporte vive en su propia tabla.
    assert "ats_keywords" not in supabase.tables["job_descriptions"][0]


def test_opening_a_calculated_report_again_is_a_read_and_costs_nothing(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    _serve(_world())
    first = _open(client)
    batches_after_first = len(gateway.embed_batches)

    again = [_open(client) for _ in range(3)]

    assert [r.status_code for r in again] == [200, 200, 200]
    assert all(r.json() == first.json() for r in again)
    # Ni la IA ni los vectores: una lectura de la base.
    assert gateway.generate_calls == 1
    assert len(gateway.embed_batches) == batches_after_first
    # Cuatro aperturas, una sola consulta gastada.
    assert _queries_spent(fake_redis) == 1


def test_changing_the_primary_cv_invalidates_the_report_but_not_the_keywords(
    client: TestClient, fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    # La IA daría otras keywords si se la volviera a consultar: no debe consultarse.
    fake = KeywordGateway([KEYWORDS, ["Rust", "Go"]])
    monkeypatch.setattr(
        "app.services.ats_analyzer.keyword_matcher.AIGateway", lambda: fake
    )
    supabase = _world()
    _serve(supabase)
    first = _open(client)

    # La persona sube otro CV y lo marca como principal.
    supabase.tables["uploaded_documents"][0]["is_primary"] = False
    other = _cv_document("doc-2")
    other["parsed_data"]["skills"].append({"name": "GraphQL"})
    supabase.tables["uploaded_documents"].append(other)
    second = _open(client)

    assert second.status_code == 200
    assert fake.generate_calls == 1
    assert [m["keyword"] for m in second.json()["keyword_matches"]] == [
        m["keyword"] for m in first.json()["keyword_matches"]
    ]
    # Con GraphQL en el nuevo CV el puntaje sube: se recalculó.
    assert second.json()["ats_score"] > first.json()["ats_score"]
    assert _queries_spent(fake_redis) == 2
    [saved] = supabase.tables["ats_reports"]
    assert saved["cv_document_id"] == "doc-2"


def test_a_cv_read_again_with_new_data_invalidates_the_report(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    """Releer el mismo documento cambia `parsed_data` sin cambiar `updated_at`."""
    supabase = _world()
    _serve(supabase)
    first = _open(client)

    supabase.tables["uploaded_documents"][0]["parsed_data"]["skills"].append(
        {"name": "GraphQL"}
    )
    second = _open(client)

    assert second.json()["ats_score"] > first.json()["ats_score"]
    assert _queries_spent(fake_redis) == 2
    assert gateway.generate_calls == 1


def test_a_report_from_an_older_algorithm_is_not_reused(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    supabase = _world()
    _serve(supabase)
    _open(client)

    supabase.tables["ats_reports"][0]["report_version"] = 0
    response = _open(client)

    assert response.status_code == 200
    assert _queries_spent(fake_redis) == 2
    assert supabase.tables["ats_reports"][0]["report_version"] >= 1
    # Se rehace el reporte, no las keywords del puesto.
    assert gateway.generate_calls == 1


def test_a_corrupt_saved_report_is_recalculated_instead_of_failing(
    client: TestClient, gateway: KeywordGateway
) -> None:
    supabase = _world()
    _serve(supabase)
    _open(client)

    supabase.tables["ats_reports"][0]["keyword_matches"] = "no es una lista"
    response = _open(client)

    assert response.status_code == 200
    assert response.json()["ats_score"] == 55


def test_a_job_that_already_existed_gets_its_keywords_the_first_time_it_is_opened(
    client: TestClient, gateway: KeywordGateway
) -> None:
    """Los puestos anteriores a la migración no tienen nada guardado."""
    supabase = _world()
    _serve(supabase)
    assert supabase.tables["ats_reports"] == []

    _open(client)

    [saved] = supabase.tables["ats_reports"]
    assert [m["keyword"] for m in saved["keyword_matches"]] == sorted(KEYWORDS)
    assert gateway.generate_calls == 1

    # Desde entonces el puesto las tiene: un recálculo no vuelve a la IA.
    supabase.tables["uploaded_documents"][0]["parsed_data"]["skills"].append(
        {"name": "GraphQL"}
    )
    _open(client)
    assert gateway.generate_calls == 1


def test_a_job_with_saved_keywords_never_asks_the_ai_for_other_keywords(
    client: TestClient, gateway: KeywordGateway
) -> None:
    supabase = _world()
    # El último reporte es de un CV que ya no es el principal: no se sirve, pero sus
    # keywords son las del puesto.
    supabase.tables["ats_reports"].append(
        {
            "job_id": "job-1",
            "user_id": "user-1",
            "cv_document_id": "old-doc",
            "cv_fingerprint": "otra",
            "report_version": 1,
            "ats_score": 10,
            "keyword_matches": [
                {"keyword": "Python", "status": "missing", "matched_text": None},
                {"keyword": "GraphQL", "status": "missing", "matched_text": None},
            ],
            "format_issues": [],
        }
    )
    _serve(supabase)

    response = _open(client)

    assert [m["keyword"] for m in response.json()["keyword_matches"]] == [
        "Python",
        "GraphQL",
    ]
    # No se piden otras palabras: solo una clasificación barata (obligatoria o deseable)
    # porque ese reporte es de antes de guardar la prioridad.
    assert gateway.generate_calls == 1


def test_the_eleventh_new_report_of_the_day_is_blocked_on_the_free_plan(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    supabase = _world(jobs=11)
    _serve(supabase)

    statuses = [_open(client, f"job-{n}").status_code for n in range(1, 11)]
    blocked = _open(client, "job-11")

    assert statuses == [200] * 10
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["code"] == "ATS_RATE_LIMIT_EXCEEDED"
    assert body["error"] == "Límite diario de ATS alcanzado"
    assert body["details"]["limit"] == 10
    assert "reset_at" in body["details"]
    # Lo ya calculado se sigue leyendo aunque el cupo del día se agotó.
    assert _open(client, "job-1").status_code == 200
    assert len(supabase.tables["ats_reports"]) == 10


def test_a_stale_report_is_not_served_once_the_limit_is_spent(
    client: TestClient, gateway: KeywordGateway
) -> None:
    supabase = _world(jobs=10)
    _serve(supabase)
    for n in range(1, 11):
        assert _open(client, f"job-{n}").status_code == 200

    supabase.tables["uploaded_documents"][0]["parsed_data"]["skills"].append(
        {"name": "GraphQL"}
    )
    response = _open(client, "job-1")

    assert response.status_code == 429
    assert response.json()["code"] == "ATS_RATE_LIMIT_EXCEEDED"


def test_without_a_primary_cv_nothing_is_spent_or_saved(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    supabase = _world()
    supabase.tables["uploaded_documents"].clear()
    _serve(supabase)

    response = _open(client)

    assert response.status_code == 404
    assert response.json()["code"] == "PRIMARY_CV_NOT_FOUND"
    assert _queries_spent(fake_redis) == 0
    assert supabase.tables["ats_reports"] == []


class _MissingSchemaQuery(FakeTableQuery):
    """La base sin la migración 031: la tabla no existe."""

    async def execute(self) -> Any:
        if self.table_name == "ats_reports":
            raise APIError(
                {
                    "message": "Could not find the table 'public.ats_reports'",
                    "code": "PGRST205",
                    "hint": None,
                    "details": None,
                }
            )
        return await super().execute()


class _SupabaseWithoutMigration(FakeSupabase):
    def table(self, table_name: str) -> FakeTableQuery:
        return _MissingSchemaQuery(self, table_name)


def test_before_the_migration_is_applied_the_report_works_as_it_always_did(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    supabase = _SupabaseWithoutMigration()
    supabase.tables["job_descriptions"].append(_job())
    supabase.tables["uploaded_documents"].append(_cv_document())
    _serve(supabase)

    first = _open(client)
    second = _open(client)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["ats_score"] == 55
    # Sin dónde guardar nada se calcula cada vez y se gasta una consulta, como antes.
    assert gateway.generate_calls == 2
    assert _queries_spent(fake_redis) == 2


def test_the_optimizer_reads_the_saved_report_and_the_report_it_leaves_is_free(
    client: TestClient,
    gateway: KeywordGateway,
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_optimize(*_args: object, **_kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr("app.api.v1.ats.optimize_cv_sections", fake_optimize)
    _serve(_world(jobs=2))
    seen = _open(client, "job-1")

    optimized = client.post("/api/v1/ats/optimize", json={"job_id": "job-1"})

    assert optimized.status_code == 200
    # Parte del mismo puntaje que la persona vio, sin volver a la IA.
    assert optimized.json()["ats_score_before"] == seen.json()["ats_score"]
    assert gateway.generate_calls == 1

    # Optimizar un puesto nuevo calcula su reporte (el optimizador tiene su propio
    # cupo) y lo deja guardado: abrirlo después no gasta la consulta diaria del ATS.
    spent = _queries_spent(fake_redis)
    client.post("/api/v1/ats/optimize", json={"job_id": "job-2"})
    _open(client, "job-2")
    assert _queries_spent(fake_redis) == spent


def test_only_keywords_the_report_marks_missing_reach_the_optimizer_as_declared(
    client: TestClient,
    gateway: KeywordGateway,
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, Any] = {}

    async def fake_optimize(*_args: object, **kwargs: object) -> list[object]:
        received.update(kwargs)
        return []

    monkeypatch.setattr("app.api.v1.ats.optimize_cv_sections", fake_optimize)
    _serve(_world())
    _open(client)

    # «Python» ya figura en el CV y «Kubernetes» no es del puesto: solo «GraphQL»,
    # que el reporte da por faltante, llega como declarada.
    response = client.post(
        "/api/v1/ats/optimize",
        json={
            "job_id": "job-1",
            "confirmed_keywords": ["graphql", "Python", "Kubernetes"],
        },
    )

    assert response.status_code == 200
    assert received["declared"] == ["GraphQL"]


def test_optimizing_without_declaring_anything_sends_no_declared_keywords(
    client: TestClient,
    gateway: KeywordGateway,
    fake_redis: FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, Any] = {}

    async def fake_optimize(*_args: object, **kwargs: object) -> list[object]:
        received.update(kwargs)
        return []

    monkeypatch.setattr("app.api.v1.ats.optimize_cv_sections", fake_optimize)
    _serve(_world())
    _open(client)

    response = client.post("/api/v1/ats/optimize", json={"job_id": "job-1"})

    assert response.status_code == 200
    assert received["declared"] == []


def test_the_score_after_counts_the_format_of_the_downloadable_cv(
    client: TestClient,
    gateway: KeywordGateway,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_optimize(*_args: object, **_kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr("app.api.v1.ats.optimize_cv_sections", fake_optimize)
    supabase = _world()
    supabase.tables["uploaded_documents"][0]["parsed_data"]["format_flags"] = {
        **NO_FORMAT_PROBLEMS,
        "multi_column": True,
        "has_images": True,
    }
    _serve(supabase)
    seen = _open(client).json()

    body = client.post("/api/v1/ats/optimize", json={"job_id": "job-1"}).json()

    # El archivo subido deja 3 de los 10 puntos de formato (columnas e imágenes):
    # 45 + 3. El descargable es de una columna, sin imágenes ni tablas: 45 + 10. El
    # contenido no cambió, así que la diferencia es solo el formato.
    assert seen["format_points"] == 3
    assert body["ats_score_before"] == seen["ats_score"] == 48
    assert body["format_points_after"] == 10
    assert body["ats_score_after"] == 55


def test_when_the_format_was_not_evaluated_the_score_after_leaves_it_out_too(
    client: TestClient,
    gateway: KeywordGateway,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_optimize(*_args: object, **_kwargs: object) -> list[object]:
        return []

    monkeypatch.setattr("app.api.v1.ats.optimize_cv_sections", fake_optimize)
    supabase = _world()
    del supabase.tables["uploaded_documents"][0]["parsed_data"]["format_flags"]
    _serve(supabase)
    seen = _open(client).json()

    body = client.post("/api/v1/ats/optimize", json={"job_id": "job-1"}).json()

    # Antes y después se comparan sin formato: si no, el «después» ganaría 10 puntos que
    # el «antes» nunca tuvo.
    assert seen["format_points"] is None
    assert body["format_points_after"] is None
    assert body["ats_score_before"] == body["ats_score_after"] == 50


def test_a_report_saved_before_the_format_counted_is_recalculated(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    """La versión 5 puntuaba sin formato: su número ya no es el de hoy (Decisión 42)."""
    supabase = _world()
    _serve(supabase)
    _open(client)

    supabase.tables["ats_reports"][0]["report_version"] = 5
    supabase.tables["ats_reports"][0]["ats_score"] = 50
    response = _open(client)

    assert ATS_REPORT_VERSION >= 6
    assert response.json()["ats_score"] == 55
    assert supabase.tables["ats_reports"][0]["report_version"] == ATS_REPORT_VERSION
    # Rehacerlo cuenta una consulta del tope diario, como cualquier cambio de versión.
    assert _queries_spent(fake_redis) == 2


def test_a_report_saved_before_the_format_check_existed_is_recalculated(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    """La versión 1 es la de antes de leer el formato del PDF (Decisión 34)."""
    supabase = _world()
    _serve(supabase)
    _open(client)

    supabase.tables["ats_reports"][0]["report_version"] = 1
    response = _open(client)

    assert response.status_code == 200
    assert ATS_REPORT_VERSION > 1
    assert supabase.tables["ats_reports"][0]["report_version"] == ATS_REPORT_VERSION
    assert _queries_spent(fake_redis) == 2
    # Se rehace el reporte, no las keywords del puesto.
    assert gateway.generate_calls == 1


def test_a_report_saved_with_non_skill_keywords_is_recalculated_without_them(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    """La versión 2 guardaba «Junior» o «Buenos Aires» como si fueran habilidades
    (Decisión 35): al rehacer el reporte se filtran, sin pedirle otras a la IA."""
    supabase = _world()
    _serve(supabase)
    _open(client)

    saved = supabase.tables["ats_reports"][0]
    saved["report_version"] = 2
    saved["keyword_matches"] = [
        {"keyword": word, "status": "missing", "matched_text": None}
        for word in ["Python", "GraphQL", "Junior", "Buenos Aires", "Full time"]
    ]
    response = _open(client)

    assert response.status_code == 200
    assert [item["keyword"] for item in response.json()["keyword_matches"]] == [
        "Python",
        "GraphQL",
    ]
    assert supabase.tables["ats_reports"][0]["report_version"] == ATS_REPORT_VERSION
    assert ATS_REPORT_VERSION > 2
    # La extracción de la primera apertura y la clasificación de la segunda.
    assert gateway.generate_calls == 2


def test_the_format_problems_are_listed_and_take_their_points_off_the_ten(
    client: TestClient, gateway: KeywordGateway
) -> None:
    supabase = _world()
    _serve(supabase)
    clean = _open(client).json()

    supabase.tables["uploaded_documents"][0]["parsed_data"]["format_flags"] = {
        **NO_FORMAT_PROBLEMS,
        "multi_column": True,
        "has_images": True,
        "headers": ["Perfil académico"],
    }
    flagged = _open(client).json()

    assert clean["format_issues"] == []
    assert clean["format_evaluated"] is True
    assert {issue["code"]: issue["penalty"] for issue in flagged["format_issues"]} == {
        "MULTI_COLUMN": 4,
        "IMAGES": 3,
        "NON_STANDARD_HEADERS": 0,
    }
    assert flagged["format_evaluated"] is True
    # Columnas −4 e imágenes −3 dejan 3 de los 10 puntos de formato (Decisión 42); los
    # títulos poco habituales se avisan sin restar. Contenido 50: 45 + 10 sin avisos
    # contra 45 + 3 con ellos.
    assert clean["format_points"] == 10
    assert flagged["format_points"] == 3
    assert clean["ats_score"] == 55
    assert flagged["ats_score"] == 48


def test_a_cv_read_before_the_format_check_is_reported_as_not_evaluated(
    client: TestClient, gateway: KeywordGateway
) -> None:
    supabase = _world()
    del supabase.tables["uploaded_documents"][0]["parsed_data"]["format_flags"]
    _serve(supabase)

    response = _open(client)

    body = response.json()
    assert body["format_evaluated"] is False
    # Sin banderas no hay qué puntuar: el formato no entra, ni suma ni resta, y el
    # contenido vale los 100 (Decisión 42).
    assert body["format_issues"] == []
    assert body["format_points"] is None
    assert body["ats_score"] == 50


def test_the_saved_report_remembers_whether_the_format_was_evaluated(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    supabase = _world()
    del supabase.tables["uploaded_documents"][0]["parsed_data"]["format_flags"]
    _serve(supabase)

    first = _open(client).json()
    second = _open(client).json()

    assert second == first
    assert second["format_evaluated"] is False
    # Releerlo del guardado no gasta la consulta diaria.
    assert _queries_spent(fake_redis) == 1


def test_reading_the_same_cv_again_with_the_format_check_recalculates_the_report(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    """Volver a subir/leer el CV es la forma de pasar de «no evaluado» a evaluado."""
    supabase = _world()
    parsed_data = supabase.tables["uploaded_documents"][0]["parsed_data"]
    del parsed_data["format_flags"]
    _serve(supabase)
    before = _open(client).json()

    parsed_data["format_flags"] = {**NO_FORMAT_PROBLEMS, "has_tables": True}
    after = _open(client).json()

    assert before["format_evaluated"] is False
    assert after["format_evaluated"] is True
    assert [issue["code"] for issue in after["format_issues"]] == ["TABLES"]
    # Antes el formato no contaba (50 de contenido sobre 100); ahora las tablas dejan 7
    # de los 10 puntos: 45 + 7.
    assert before["format_points"] is None
    assert after["format_points"] == 7
    assert before["ats_score"] == 50
    assert after["ats_score"] == 52
    assert _queries_spent(fake_redis) == 2


# --- requisitos del puesto (Decisión 42) --------------------------------------------


def _world_with_requirements() -> FakeSupabase:
    supabase = _world()
    supabase.tables["job_descriptions"][0].update(
        {
            "required_seniority": "Senior",
            "required_education": "Bachelor's degree",
            "required_languages": ["English"],
        }
    )
    parsed = supabase.tables["uploaded_documents"][0]["parsed_data"]
    parsed["experiences"] = [
        {
            "title": "Backend dev",
            "company": "Acme",
            "started_at": "2025-01",
            "ended_at": "2025-06",
            "description": "Built services",
        }
    ]
    parsed["educations"] = [
        {"institution": "UTN", "field_of_study": "Licenciatura en Sistemas"}
    ]
    parsed["languages"] = [{"name": "English", "level": "advanced"}]
    return supabase


def test_the_report_carries_the_requirements_and_scores_with_them(
    client: TestClient, gateway: KeywordGateway
) -> None:
    supabase = _world_with_requirements()
    _serve(supabase)

    body = _open(client).json()

    by_key = {item["key"]: item for item in body["requirements"]}
    assert list(by_key) == ["experience", "education", "language:english"]
    assert by_key["experience"]["actual"] == "6 meses"
    assert by_key["experience"]["estimated"] is True
    assert by_key["experience"]["ratio"] == pytest.approx(0.1)
    assert by_key["education"]["status"] == "met"
    assert by_key["language:english"]["status"] == "met"
    # Contenido: skills 60 × 0,5 + años 20 × 0,1 + formación 10 + idioma 10 = 52 de
    # 100, que valen 46,8 sobre 90, más 10 de formato sin avisos = 57.
    assert body["ats_score"] == 57
    [saved] = supabase.tables["ats_reports"]
    assert saved["ats_score"] == 57
    # Los requisitos no se guardan: salen del perfil de cada vez.
    assert "requirements" not in saved


def test_a_report_for_a_posting_that_asks_nothing_has_no_requirements(
    client: TestClient, gateway: KeywordGateway
) -> None:
    _serve(_world())

    body = _open(client).json()

    assert body["requirements"] == []
    assert body["ats_score"] == 55


def test_a_saved_report_reads_the_profile_again_without_spending_a_query(
    client: TestClient, gateway: KeywordGateway, fake_redis: FakeRedis
) -> None:
    supabase = _world_with_requirements()
    supabase.tables["uploaded_documents"][0]["parsed_data"]["languages"] = []
    _serve(supabase)
    first = _open(client).json()

    supabase.tables["languages"].append(
        {"profile_id": "profile-1", "name": "Inglés", "proficiency": "advanced"}
    )
    second = _open(client).json()

    english = {item["key"]: item for item in first["requirements"]}["language:english"]
    assert english["status"] == "unmet"
    english = {item["key"]: item for item in second["requirements"]}["language:english"]
    assert english["status"] == "met"
    assert second["ats_score"] > first["ats_score"]
    assert gateway.generate_calls == 1
    assert _queries_spent(fake_redis) == 1


def test_the_linkedin_pdf_adds_the_roles_it_lists(
    client: TestClient, gateway: KeywordGateway
) -> None:
    supabase = _world_with_requirements()
    supabase.tables["uploaded_documents"].append(
        {
            "id": "linkedin-1",
            "user_id": "user-1",
            "profile_id": "profile-1",
            "type": "linkedin",
            "is_primary": False,
            "status": "done",
            "created_at": "2026-10-22T00:00:00+00:00",
            "parsed_data": {
                "experiences": [
                    {
                        "title": "Python Developer",
                        "company": "Paogi",
                        "started_at": "2025-07",
                        "ended_at": "2025-12",
                    }
                ]
            },
        }
    )
    _serve(supabase)

    body = _open(client).json()

    experience = {item["key"]: item for item in body["requirements"]}["experience"]
    # Enero a junio del CV y julio a diciembre de LinkedIn: un año entero.
    assert experience["actual"] == "1 año"
    assert "Paogi — Python Developer: 6 meses" in experience["detail"]


def test_a_failure_evaluating_the_requirements_keeps_the_report_with_the_skills_only(
    client: TestClient, gateway: KeywordGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("falló la evaluación")

    monkeypatch.setattr("app.api.v1.ats.evaluate_requirements", explode)
    _serve(_world_with_requirements())

    response = _open(client)

    assert response.status_code == 200
    assert response.json()["requirements"] == []
    assert response.json()["ats_score"] == 55


def test_a_saved_report_whose_requirements_fail_shows_the_score_of_the_skills(
    client: TestClient, gateway: KeywordGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    supabase = _world_with_requirements()
    _serve(supabase)
    _open(client)
    # El puntaje guardado puede venir de una versión anterior de la fórmula.
    supabase.tables["ats_reports"][0]["ats_score"] = 3

    def explode(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("falló la evaluación")

    monkeypatch.setattr("app.api.v1.ats.evaluate_requirements", explode)

    body = _open(client).json()

    assert body["requirements"] == []
    assert body["ats_score"] == 55


def test_a_report_saved_before_the_change_is_recomputed_without_the_language(
    client: TestClient, fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = KeywordGateway([["Rust"]])
    monkeypatch.setattr(
        "app.services.ats_analyzer.keyword_matcher.AIGateway", lambda: fake
    )
    supabase = _world()
    _serve(supabase)
    # Un reporte de la versión anterior, con «English» entre las palabras clave.
    supabase.tables["ats_reports"].append(
        {
            "job_id": "job-1",
            "user_id": "user-1",
            "cv_document_id": "doc-1",
            "cv_fingerprint": cv_fingerprint(supabase.tables["uploaded_documents"][0]),
            "report_version": ATS_REPORT_VERSION - 1,
            "ats_score": 33,
            "keyword_matches": [
                {"keyword": "Python", "status": "literal", "matched_text": "Python"},
                {"keyword": "English", "status": "missing", "matched_text": None},
            ],
            "format_issues": [],
            "computed_at": "2026-10-31T00:00:00+00:00",
        }
    )

    body = _open(client).json()

    assert [item["keyword"] for item in body["keyword_matches"]] == ["Python"]
    # Se recalcula con las keywords guardadas: la IA solo clasifica cuáles son
    # deseables.
    assert fake.generate_calls == 1
    assert _queries_spent(fake_redis) == 1
    assert supabase.tables["ats_reports"][0]["report_version"] == ATS_REPORT_VERSION


def _priority_gateway(monkeypatch: pytest.MonkeyPatch) -> KeywordGateway:
    fake = KeywordGateway(
        [
            [
                {"name": "Python", "priority": "required"},
                {"name": "GraphQL", "priority": "required"},
                {"name": "REST APIs", "priority": "nice"},
            ]
        ]
    )
    monkeypatch.setattr(
        "app.services.ats_analyzer.keyword_matcher.AIGateway", lambda: fake
    )
    return fake


def test_the_report_saves_which_keywords_the_posting_calls_nice_to_have(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _priority_gateway(monkeypatch)
    supabase = _world()
    _serve(supabase)

    body = _open(client).json()

    assert {m["keyword"]: m["priority"] for m in body["keyword_matches"]} == {
        "GraphQL": "required",
        "Python": "required",
        "REST APIs": "nice",
    }
    [saved] = supabase.tables["ats_reports"]
    assert {m["keyword"]: m["priority"] for m in saved["keyword_matches"]} == {
        "GraphQL": "required",
        "Python": "required",
        "REST APIs": "nice",
    }
    assert fake.generate_calls == 1


def test_a_nice_to_have_keyword_weighs_half_in_the_score(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _priority_gateway(monkeypatch)
    _serve(_world())

    body = _open(client).json()

    # Python literal (1) y REST APIs por significado (0,5, deseable: peso 0,5) contra
    # GraphQL faltante (1): (1 + 0,5 × 0,5) / (1 + 1 + 0,5) = 0,5 -> 45 + 10 de formato.
    assert body["ats_score"] == 55


def test_a_report_saved_with_priorities_is_read_without_asking_the_ai_again(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fake_redis: FakeRedis
) -> None:
    fake = _priority_gateway(monkeypatch)
    supabase = _world()
    _serve(supabase)
    first = _open(client).json()
    # Cambia el CV principal: se rehace con las palabras y las prioridades guardadas.
    supabase.tables["uploaded_documents"][0]["parsed_data"]["skills"].append(
        {"name": "GraphQL"}
    )

    second = _open(client).json()

    assert fake.generate_calls == 1
    assert {m["keyword"]: m["priority"] for m in second["keyword_matches"]} == {
        m["keyword"]: m["priority"] for m in first["keyword_matches"]
    }


def test_a_report_without_priorities_gets_them_classified_once(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class ClassifyingGateway(KeywordGateway):
        async def generate(self, *args: Any, **kwargs: Any) -> str:
            self.generate_calls += 1
            return json.dumps({"nice": ["REST APIs", "Algo que no está"]})

    fake = ClassifyingGateway()
    monkeypatch.setattr(
        "app.services.ats_analyzer.keyword_matcher.AIGateway", lambda: fake
    )
    supabase = _world()
    _serve(supabase)
    supabase.tables["ats_reports"].append(
        {
            "job_id": "job-1",
            "user_id": "user-1",
            "cv_document_id": "old-doc",
            "cv_fingerprint": "otra",
            "report_version": 3,
            "ats_score": 10,
            "keyword_matches": [
                {"keyword": "Python", "status": "missing", "matched_text": None},
                {"keyword": "REST APIs", "status": "missing", "matched_text": None},
            ],
            "format_issues": [],
        }
    )

    body = _open(client).json()

    assert {m["keyword"]: m["priority"] for m in body["keyword_matches"]} == {
        "Python": "required",
        "REST APIs": "nice",
    }
    assert fake.generate_calls == 1
    # Lo siguiente es una lectura: la prioridad ya quedó guardada.
    _open(client)
    assert fake.generate_calls == 1


# --- unidades -------------------------------------------------------------------------


def test_the_fingerprint_follows_the_content_not_the_key_order() -> None:
    first = {"parsed_data": {"skills": [{"name": "Python"}], "format_flags": {}}}
    reordered = {"parsed_data": {"format_flags": {}, "skills": [{"name": "Python"}]}}
    changed = {"parsed_data": {"skills": [{"name": "Rust"}], "format_flags": {}}}

    assert cv_fingerprint(first) == cv_fingerprint(reordered)
    assert cv_fingerprint(first) != cv_fingerprint(changed)
    assert cv_fingerprint({"parsed_data": None}) != cv_fingerprint(first)


@pytest.mark.asyncio
async def test_given_keywords_are_used_without_asking_the_ai() -> None:
    fake = KeywordGateway([["otra", "cosa"]])
    job = {"required_skills": ["Rust"]}

    result = await analyze_keywords(
        job,
        _cv_document(),
        gateway=fake,  # type: ignore[arg-type]
        keywords=["Python", "GraphQL"],
    )

    assert fake.generate_calls == 0
    assert result.keywords == ["Python", "GraphQL"]


async def _baseline(known: dict[str, list[float]] | None) -> tuple[Any, KeywordGateway]:
    fake = KeywordGateway()

    async def loader() -> dict[str, list[float]]:
        return known or {}

    result = await analyze_keywords(
        {},
        _cv_document(),
        gateway=fake,  # type: ignore[arg-type]
        keywords=KEYWORDS,
        saved_vectors=loader if known is not None else None,
    )
    return result, fake


@pytest.mark.asyncio
async def test_saved_vectors_are_not_asked_again_and_the_result_is_the_same() -> None:
    without, plain = await _baseline(None)
    with_known, reusing = await _baseline({"Diseño de APIs": [1.0, 0.0, 0.0]})

    assert with_known.matches == without.matches
    # Sin lo guardado, el lote de términos del CV lleva la skill; con lo guardado, no.
    assert "Diseño de APIs" in plain.embed_batches[1]
    assert all("Diseño de APIs" not in batch for batch in reusing.embed_batches)
    # Lo que no tiene vector guardado (experiencia, otras skills) sigue yendo al lote.
    assert "Built services" in reusing.embed_batches[1]


@pytest.mark.asyncio
async def test_with_a_saved_vector_for_every_term_only_keywords_are_embedded() -> None:
    cv = _cv_document()
    cv["parsed_data"]["experiences"] = []
    fake = KeywordGateway()

    async def loader() -> dict[str, list[float]]:
        return {"Python": [0.0, 0.0, 1.0], "Diseño de APIs": [1.0, 0.0, 0.0]}

    result = await analyze_keywords(
        {},
        cv,
        gateway=fake,  # type: ignore[arg-type]
        keywords=KEYWORDS,
        saved_vectors=loader,
    )

    assert len(fake.embed_batches) == 1
    assert {m.keyword: m.status for m in result.matches}["REST APIs"] == "semantic"


@pytest.mark.asyncio
async def test_a_saved_vector_of_another_size_is_ignored() -> None:
    result, fake = await _baseline({"Diseño de APIs": [1.0]})

    assert "Diseño de APIs" in fake.embed_batches[1]
    assert {m.keyword: m.status for m in result.matches}["REST APIs"] == "semantic"


@pytest.mark.asyncio
async def test_the_report_reuses_the_vectors_stored_with_the_profile_skills(
    gateway: KeywordGateway,
) -> None:
    supabase = _world()
    supabase.tables["skills"].extend(
        [
            # PostgREST devuelve el vector como texto.
            {
                "profile_id": "profile-1",
                "name": "Diseño de APIs",
                "embedding": "[1.0,0.0,0.0]",
            },
            # Una skill cargada a mano no tiene vector: se pide como siempre.
            {"profile_id": "profile-1", "name": "Python", "embedding": None},
            {
                "profile_id": "profile-2",
                "name": "Built services",
                "embedding": "[0.0,0.0,1.0]",
            },
        ]
    )

    report = await _build_ats_report(
        "job-1", supabase.tables["job_descriptions"][0], _cv_document(), supabase
    )

    assert report.ats_score == 55
    assert all("Diseño de APIs" not in batch for batch in gateway.embed_batches)
    # Los vectores de otro perfil no se usan.
    assert "Built services" in gateway.embed_batches[1]
    assert "Python" in gateway.embed_batches[1]
