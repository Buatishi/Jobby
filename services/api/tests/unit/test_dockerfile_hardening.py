"""El contenedor de la API no corre como root (Decisión 28)."""

from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[2] / "Dockerfile"


def _instructions() -> list[str]:
    text = DOCKERFILE.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    return [line for line in lines if line and not line.startswith("#")]


def test_the_image_drops_root_before_starting_the_api() -> None:
    instructions = _instructions()
    users = [line for line in instructions if line.upper().startswith("USER ")]
    start = next(i for i, line in enumerate(instructions) if line.startswith("CMD "))

    assert users, "falta la instrucción USER: el contenedor correría como root"
    assert users[-1].split()[1] not in {"root", "0"}
    # El último USER tiene que quedar antes del comando de inicio, no después.
    assert instructions.index(users[-1]) < start


def test_system_packages_are_installed_without_recommends() -> None:
    install = [line for line in _instructions() if "apt-get install" in line]

    assert install
    assert all("--no-install-recommends" in line for line in install)
