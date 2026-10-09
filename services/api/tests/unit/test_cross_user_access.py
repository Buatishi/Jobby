"""Acceso entre dos personas (IDOR): ninguna ruta con un identificador en la URL entrega
ni cambia el recurso de otra persona.

Dos garantías:

1. Matriz: cada ruta con identificador se pide como persona ajena (debe responder
   404, igual que un recurso inexistente, sin datos ni cambios) y como dueña (control:
   la misma pregunta sí se contesta, así el 404 de la ajena no es un error de la
   propia prueba).
2. Inventario: una ruta nueva sin sesión, o con un identificador en la URL y sin caso
   acá, rompe estas pruebas hasta que alguien decida a conciencia cómo se protege.

Las rutas de tareas (`/tasks/{task_id}`) tienen su propia prueba en
`test_tasks_access.py`, porque su identificador no es una fila sino un texto atado a
su dueña.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase_client
from app.dependencies import get_current_user
from app.main import app
from app.models.auth import CurrentUser
from tests.fakes import FakeRedis, FakeSupabase

# Dato que solo conoce la dueña: si aparece en la respuesta a la ajena, hubo fuga.
SECRET = "DATO-PRIVADO-DE-USER-2"

JOB_ID = "3f1c2a4e-8b7d-4c21-9e5a-1d2f3a4b5c6d"
JOB_WITHOUT_RESULTS_ID = "7b2d9c1e-4a3f-4e8b-9c6d-2f1a0b9c8d7e"

# Ambas son premium: así las rutas premium llegan a la verificación de dueña y un
# 403 por plan no puede esconder una verificación que falte.
INTRUDER = CurrentUser(
    id="user-1",
    supabase_uid="auth-user-1",
    email="intruder@example.com",
    tier="premium",
)
OWNER = CurrentUser(
    id="user-2",
    supabase_uid="auth-user-2",
    email="owner@example.com",
    tier="premium",
)

# Operaciones que responden sin sesión a propósito.
PUBLIC_OPERATIONS = {
    ("GET", "/health"),
    ("GET", "/api/v1/health"),
    # Se autentica por la firma del cuerpo, no por una sesión (ver
    # test_lemonsqueezy_webhooks).
    ("POST", "/api/v1/webhooks/lemonsqueezy"),
}

COVERED_ELSEWHERE = {
    ("GET", "/api/v1/tasks/{task_id}"): "test_tasks_access.py",
    ("GET", "/api/v1/tasks/{task_id}/stream"): "test_tasks_access.py",
}


@dataclass(frozen=True)
class AccessCase:
    method: str
    template: str  # ruta tal como la declara OpenAPI
    path: str  # ruta concreta con el recurso de la dueña
    intruder_code: str
    owner_status: int
    body: dict[str, Any] | None = None
    # Solo cuando la dueña tampoco recibe un éxito: el código distingue su respuesta de
    # la de la persona ajena (en ATS, la dueña no tiene CV primario cargado).
    owner_code: str | None = None

    @property
    def label(self) -> str:
        return f"{self.method} {self.template}"


CASES = [
    AccessCase("GET", "/api/v1/jobs/{job_id}", f"/api/v1/jobs/{JOB_ID}",
               "JOB_NOT_FOUND", 200),
    AccessCase("PATCH", "/api/v1/jobs/{job_id}", f"/api/v1/jobs/{JOB_ID}",
               "JOB_NOT_FOUND", 200, body={"job_title": "Título nuevo"}),
    AccessCase("DELETE", "/api/v1/jobs/{job_id}",
               f"/api/v1/jobs/{JOB_WITHOUT_RESULTS_ID}", "JOB_NOT_FOUND", 204),
    AccessCase("GET", "/api/v1/matches/{match_id}", "/api/v1/matches/match-2",
               "MATCH_NOT_FOUND", 200),
    AccessCase("PATCH", "/api/v1/matches/{match_id}/rating",
               "/api/v1/matches/match-2/rating", "MATCH_NOT_FOUND", 200,
               body={"rating": 1}),
    AccessCase("GET", "/api/v1/interview-kits/{kit_id}", "/api/v1/interview-kits/kit-2",
               "INTERVIEW_KIT_NOT_FOUND", 200),
    AccessCase("PATCH", "/api/v1/interview-kits/{kit_id}/rating",
               "/api/v1/interview-kits/kit-2/rating", "INTERVIEW_KIT_NOT_FOUND", 200,
               body={"rating": 1}),
    AccessCase("POST", "/api/v1/interview-kits/{kit_id}/regenerate",
               "/api/v1/interview-kits/kit-2/regenerate", "INTERVIEW_KIT_NOT_FOUND",
               202),
    AccessCase("GET", "/api/v1/ats/{job_id}", f"/api/v1/ats/{JOB_ID}",
               "JOB_NOT_FOUND", 404, owner_code="PRIMARY_CV_NOT_FOUND"),
    AccessCase("PATCH", "/api/v1/profiles/documents/{document_id}/set-primary",
               "/api/v1/profiles/documents/doc-2/set-primary", "DOCUMENT_NOT_FOUND",
               200),
    AccessCase("DELETE", "/api/v1/profiles/documents/{document_id}",
               "/api/v1/profiles/documents/doc-2", "DOCUMENT_NOT_FOUND", 204),
    # El identificador viaja en el cuerpo y no en la URL, pero es el mismo riesgo.
    AccessCase("POST", "/api/v1/ats/optimize", "/api/v1/ats/optimize",
               "JOB_NOT_FOUND", 404, body={"job_id": JOB_ID},
               owner_code="PRIMARY_CV_NOT_FOUND"),
]


@dataclass
class World:
    supabase: FakeSupabase
    enqueued: list[str]

    def act_as(self, user: CurrentUser) -> None:
        async def current_user() -> CurrentUser:
            return user

        app.dependency_overrides[get_current_user] = current_user


@pytest.fixture()
def world(monkeypatch: pytest.MonkeyPatch) -> World:
    """Datos de user-2 (la dueña); user-1 no tiene nada y es quien intenta entrar."""
    supabase = FakeSupabase()
    supabase.tables["job_descriptions"].extend(
        [
            {
                "id": job_id,
                "user_id": "user-2",
                "raw_text": SECRET,
                "job_title": f"Puesto {SECRET}",
                "company_name": "Globex",
            }
            for job_id in (JOB_ID, JOB_WITHOUT_RESULTS_ID)
        ]
    )
    supabase.tables["job_matches"].append(
        {
            "id": "match-2",
            "user_id": "user-2",
            "profile_id": "profile-2",
            "job_id": JOB_ID,
            "match_score": 70,
            "potential_score": 80,
            "representation_score": 60,
            "gap_origin": "skills",
            "score_breakdown": {"sub_scores": {"skills": 0.7}},
            "recommendations": [
                {"title": SECRET, "description": SECRET, "priority": "high"}
            ],
            "user_rating": None,
            "ai_model_used": "deepseek-chat",
        }
    )
    supabase.tables["interview_kits"].append(
        {
            "id": "kit-2",
            "user_id": "user-2",
            "profile_id": "profile-2",
            "job_id": JOB_ID,
            "match_id": None,
            "title": SECRET,
            "status": "done",
            "prep_notes": {"interviewer_name": SECRET},
        }
    )
    supabase.tables["uploaded_documents"].append(
        {
            "id": "doc-2",
            "user_id": "user-2",
            "profile_id": "profile-2",
            "type": "cv",
            "cv_slot": 1,
            "is_primary": False,
            "storage_path": "user-2/cv.pdf",
            "status": "done",
            "parsed_data": {"summary": SECRET},
        }
    )

    enqueued: list[str] = []

    def fake_enqueue(resource_id: str, _owner_id: str) -> str:
        enqueued.append(resource_id)
        return "task-test"

    monkeypatch.setattr("app.tasks.parsing.enqueue_parse_cv", fake_enqueue)
    monkeypatch.setattr("app.api.v1.interview_kits.enqueue_interview_kit", fake_enqueue)

    async def fake_client() -> FakeSupabase:
        return supabase

    app.dependency_overrides[get_supabase_client] = fake_client
    return World(supabase=supabase, enqueued=enqueued)


def _operations() -> list[tuple[str, str, dict[str, Any]]]:
    """Todas las operaciones de la API tal como las publica OpenAPI."""
    paths: dict[str, dict[str, dict[str, Any]]] = app.openapi()["paths"]
    return [
        (method.upper(), path, operation)
        for path, operations in paths.items()
        for method, operation in operations.items()
    ]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
def test_a_person_cannot_reach_a_resource_of_another(
    client: TestClient, world: World, fake_redis: FakeRedis, case: AccessCase
) -> None:
    tables_before = deepcopy(world.supabase.tables)
    counters_before = dict(fake_redis.values)
    world.act_as(INTRUDER)

    response = client.request(case.method, case.path, json=case.body)

    # Responde igual que un recurso inexistente: no revela que existe.
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == case.intruder_code
    assert set(body) == {"error", "code", "details"}
    assert SECRET not in response.text
    # Ni cambios, ni trabajo encolado, ni consumo de cupo de la persona ajena.
    assert world.supabase.tables == tables_before
    assert world.enqueued == []
    assert fake_redis.values == counters_before


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
def test_the_owner_does_reach_her_own_resource(
    client: TestClient, world: World, case: AccessCase
) -> None:
    """Control: sin esto, el 404 de la ajena podría ser un error de la prueba."""
    world.act_as(OWNER)

    response = client.request(case.method, case.path, json=case.body)

    assert response.status_code == case.owner_status
    if case.owner_code is not None:
        assert response.json()["code"] == case.owner_code
        assert response.json()["code"] != case.intruder_code


def test_every_operation_requires_a_session_except_the_public_ones() -> None:
    without_session = {
        (method, path) for method, path, operation in _operations()
        if not operation.get("security")
    }

    assert without_session == PUBLIC_OPERATIONS


def test_every_operation_with_an_id_in_the_path_has_an_access_case() -> None:
    existing = {(method, path) for method, path, _operation in _operations()}
    with_id = {operation for operation in existing if "{" in operation[1]}
    in_matrix = {(case.method, case.template) for case in CASES}

    missing = with_id - in_matrix - set(COVERED_ELSEWHERE)
    assert not missing, f"Rutas con identificador sin caso de acceso: {sorted(missing)}"
    stale = (in_matrix | set(COVERED_ELSEWHERE)) - existing
    assert not stale, f"Casos de rutas que ya no existen: {sorted(stale)}"
