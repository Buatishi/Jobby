"""Prueba de errores deliberados (consigna 3.7.7): si se rompe una regla, algo falla.

Introduce, de a una, alteraciones en reglas de negocio y corre las pruebas unitarias:
cada alteración tiene que hacer fallar al menos una. El archivo alterado se restaura
siempre, aunque la corrida se interrumpa. Uso, desde services/api:

    poetry run python -m tests.deliberate_bugs

Son las once alteraciones de la prueba del 2026-09-21, que entonces detectó cinco.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DeliberateBug:
    code: str
    rule: str
    path: str
    original: str
    altered: str


BUGS = (
    DeliberateBug(
        "M1",
        "Peso de las habilidades en el MatchScore (0,35 a 0,30)",
        "app/services/match_engine/formula.py",
        'scores["skills"] * 0.35',
        'scores["skills"] * 0.30',
    ),
    DeliberateBug(
        "M2",
        "Perfil mínimo para analizar un puesto (60 % a 50 %)",
        "app/api/v1/jobs.py",
        "if completeness_pct < 60:",
        "if completeness_pct < 50:",
    ),
    DeliberateBug(
        "M3",
        "Puestos por mes del plan gratis (10 a 100)",
        "app/services/rate_limits.py",
        "limit=None if premium else 10,",
        "limit=None if premium else 100,",
    ),
    DeliberateBug(
        "M4",
        "Dueño de una tarea (cualquiera pasa)",
        "app/core/task_ids.py",
        'return bool(owner_id) and task_id.startswith(f"{owner_id}.")',
        "return True",
    ),
    DeliberateBug(
        "M5",
        "Peso de la coincidencia semántica del ATS (0,5 a 1,0)",
        "app/services/ats_analyzer/scoring.py",
        "semantic_hits * 0.5",
        "semantic_hits * 1.0",
    ),
    DeliberateBug(
        "M6",
        "Ruteo de IA por plan (premium usa DeepSeek)",
        "app/services/ai_gateway/__init__.py",
        'return self.claude if user_tier == "premium" else self.deepseek',
        "return self.deepseek",
    ),
    DeliberateBug(
        "M7",
        "Firma del webhook de pagos (cualquiera es válida)",
        "app/services/lemonsqueezy_service.py",
        "return hmac.compare_digest(digest, signature)",
        "return True",
    ),
    DeliberateBug(
        "M8",
        "Plan premium para crear un kit (cualquiera puede)",
        "app/api/v1/interview_kits.py",
        "user_tier = await _fetch_user_tier(supabase, current_user.id)\n"
        '    if user_tier != "premium":\n'
        "        raise _premium_required()\n\n"
        "    profile = await _fetch_profile(supabase, current_user.id)",
        "user_tier = await _fetch_user_tier(supabase, current_user.id)\n\n"
        "    profile = await _fetch_profile(supabase, current_user.id)",
    ),
    DeliberateBug(
        "M9",
        "Perfil completo para generar un kit (100 % a 10 %)",
        "app/api/v1/interview_kits.py",
        'if int(profile.get("completeness_pct") or 0) < 100:',
        'if int(profile.get("completeness_pct") or 0) < 10:',
    ),
    DeliberateBug(
        "M10",
        "Tamaño máximo del PDF (10 MB a 100 MB)",
        "app/services/cv_parser/pdf_extractor.py",
        "MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024",
        "MAX_PDF_SIZE_BYTES = 100 * 1024 * 1024",
    ),
    DeliberateBug(
        "M11",
        "Puertos permitidos en la guarda anti-SSRF (se suma el 22)",
        "app/services/scraper/url_guard.py",
        "_ALLOWED_PORTS = {None, 80, 443}",
        "_ALLOWED_PORTS = {None, 22, 80, 443}",
    ),
)


def _unit_tests_fail() -> bool:
    # Orden fijo y detención en el primer fallo: alcanza con saber si alguna falla.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "not integration",
            "-x",
            "-q",
            "-p",
            "no:randomly",
            "-p",
            "no:cacheprovider",
        ],
        cwd=API_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # 1 es «hubo pruebas que fallaron»; otro código es un problema de la corrida misma.
    if result.returncode not in (0, 1):
        raise RuntimeError(f"pytest terminó con el código {result.returncode}")
    return result.returncode == 1


def _detects(bug: DeliberateBug) -> bool:
    path = API_ROOT / bug.path
    original = path.read_bytes()
    text = original.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    target = bug.original.replace("\n", newline)
    if text.count(target) != 1:
        raise RuntimeError(f"{bug.code}: no se encontró una única vez en {bug.path}")
    try:
        altered = text.replace(target, bug.altered.replace("\n", newline), 1)
        path.write_bytes(altered.encode("utf-8"))
        return _unit_tests_fail()
    finally:
        path.write_bytes(original)


def main() -> int:
    if _unit_tests_fail():
        print("Las pruebas fallan sin alteraciones: primero hay que arreglarlas.")
        return 2

    detected = 0
    for bug in BUGS:
        caught = _detects(bug)
        detected += caught
        result = "detectada" if caught else "NO detectada"
        print(f"{bug.code:>4}  {result:<12}  {bug.rule}")

    print(f"\nDetectadas: {detected} de {len(BUGS)}")
    return 0 if detected == len(BUGS) else 1


if __name__ == "__main__":
    sys.exit(main())
