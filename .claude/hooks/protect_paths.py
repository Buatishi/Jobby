"""Guardia de Claude Code (PreToolUse) para Edit, Write y NotebookEdit.

Convierte en control automático lo que hoy solo está escrito en AGENTS.md:

- BLOQUEA editar archivos `.env` (secretos), migraciones ya versionadas y `.git/`.
- PIDE CONFIRMACIÓN antes de tocar `render.yaml`, `.github/workflows/`, la imagen de la API o
  cualquier archivo de LemonSqueezy o webhooks (AGENTS.md, sección 1).

Protocolo: exit 2 con el motivo en stderr bloquea; JSON en stdout con
`permissionDecision: "ask"` pide confirmación; exit 0 sin salida permite.
Si el hook falla por un error propio, sale con 1 (aviso visible, no bloquea el trabajo).
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

ENV_FILE = re.compile(r"(^|/)\.env(\.[^/]+)?$")
ENV_TEMPLATES = (".env.example", ".env.sample", ".env.template")
ASK_PATTERNS = (
    (re.compile(r"(^|/)render\.yaml$"), "render.yaml define el despliegue"),
    (re.compile(r"(^|/)\.github/workflows/"), "los workflows de GitHub definen el pipeline"),
    (re.compile(r"(^|/)services/api/Dockerfile$"), "el Dockerfile define la imagen de producción"),
    (re.compile(r"lemonsqueezy|webhook", re.IGNORECASE), "afecta el cobro real a usuarios premium"),
)


def normalize(raw: str, project: pathlib.Path) -> str:
    path = raw.replace("\\", "/")
    root = str(project).replace("\\", "/").rstrip("/") + "/"
    if path.lower().startswith(root.lower()):
        path = path[len(root):]
    return path[2:] if path.startswith("./") else path


def is_tracked(relative: str, project: pathlib.Path) -> bool:
    done = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=project, capture_output=True, text=True,
    )
    return done.returncode == 0


def decide(relative: str, project: pathlib.Path) -> tuple[str, str] | None:
    """Devuelve ("block" | "ask", motivo) o None si se permite."""
    name = relative.rsplit("/", 1)[-1]
    if ENV_FILE.search(relative) and name not in ENV_TEMPLATES:
        return "block", f"{relative} guarda secretos: los archivos .env no se editan desde Claude Code."
    if relative.startswith(".git/"):
        return "block", "no se edita el interior de .git/."
    if relative.startswith("services/api/migrations/") and is_tracked(relative, project):
        return "block", (
            f"{relative} es una migración ya versionada: no se modifica. "
            "Los cambios de esquema van en una migración nueva."
        )
    for pattern, reason in ASK_PATTERNS:
        if pattern.search(relative):
            return "ask", f"{relative}: {reason}. Confirmá antes de modificarlo."
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        tool_input = payload.get("tool_input", {})
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if not raw:
            return 0
        project = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
        outcome = decide(normalize(raw, project), project)
    except Exception as exc:  # noqa: BLE001 - un fallo del guardia no debe frenar el trabajo
        print(f"protect_paths: error interno ({exc}); no se aplicó la guardia.", file=sys.stderr)
        return 1

    if outcome is None:
        return 0
    verdict, reason = outcome
    if verdict == "block":
        print(f"Bloqueado: {reason}", file=sys.stderr)
        return 2
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
