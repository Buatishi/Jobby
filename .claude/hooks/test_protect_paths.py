"""Pruebas del guardia protect_paths.py.

    python -m unittest discover -s .claude/hooks -p "test_*.py" -v
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HOOK = pathlib.Path(__file__).with_name("protect_paths.py")


def run_git(project: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)


class ProtectPathsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.project = pathlib.Path(cls._tmp.name)
        run_git(cls.project, "init", "-q")
        run_git(cls.project, "config", "user.email", "test@example.com")
        run_git(cls.project, "config", "user.name", "test")
        migrations = cls.project / "services" / "api" / "migrations"
        migrations.mkdir(parents=True)
        (migrations / "001_init.sql").write_text("select 1;\n", encoding="utf-8")
        run_git(cls.project, "add", ".")
        run_git(cls.project, "commit", "-q", "-m", "init")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def call(self, file_path: str, key: str = "file_path") -> subprocess.CompletedProcess[str]:
        payload = json.dumps({"tool_name": "Edit", "tool_input": {key: file_path}})
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project)}
        return subprocess.run(
            [sys.executable, str(HOOK)], input=payload, capture_output=True,
            text=True, env=env, cwd=self.project,
        )

    def assert_blocked(self, file_path: str) -> None:
        result = self.call(file_path)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Bloqueado", result.stderr)

    def assert_asks(self, file_path: str) -> None:
        result = self.call(file_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "ask")

    def assert_allowed(self, file_path: str) -> None:
        result = self.call(file_path)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, ""), result.stderr)

    def test_env_files_are_blocked_in_every_spelling(self) -> None:
        for path in (".env", "./.env", "services/api/.env", "apps/web/.env.local",
                     str(self.project / ".env.production"), "services\\api\\.env"):
            with self.subTest(path=path):
                self.assert_blocked(path)

    def test_env_templates_are_allowed(self) -> None:
        for path in (".env.example", "services/api/.env.example"):
            with self.subTest(path=path):
                self.assert_allowed(path)

    def test_tracked_migrations_are_blocked_but_new_ones_are_allowed(self) -> None:
        self.assert_blocked("services/api/migrations/001_init.sql")
        self.assert_blocked(str(self.project / "services" / "api" / "migrations" / "001_init.sql"))
        self.assert_allowed("services/api/migrations/024_nueva.sql")

    def test_git_internals_are_blocked(self) -> None:
        self.assert_blocked(".git/config")

    def test_deployment_and_billing_files_ask_for_confirmation(self) -> None:
        for path in ("render.yaml", ".github/workflows/ci.yml", "services/api/Dockerfile",
                     "services/api/app/services/lemonsqueezy_service.py",
                     "services/api/app/api/v1/webhooks.py"):
            with self.subTest(path=path):
                self.assert_asks(path)

    def test_ordinary_files_and_notebooks_are_allowed(self) -> None:
        self.assert_allowed("apps/web/lib/api/client.ts")
        self.assert_allowed("docs/00-vision.md")
        payload = json.dumps({"tool_input": {"notebook_path": "docs/analisis.ipynb"}})
        result = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True,
                                text=True, cwd=self.project)
        self.assertEqual(result.returncode, 0)

    def test_broken_input_does_not_block_work(self) -> None:
        result = subprocess.run([sys.executable, str(HOOK)], input="no es json", capture_output=True,
                                text=True, cwd=self.project)
        self.assertEqual(result.returncode, 1)
        self.assertIn("error interno", result.stderr)

    def test_missing_path_is_allowed(self) -> None:
        result = subprocess.run([sys.executable, str(HOOK)], input="{}", capture_output=True,
                                text=True, cwd=self.project)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
