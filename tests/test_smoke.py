"""Smoke tests — import + CLI invocability."""
from typer.testing import CliRunner

from granum.cli import app


def test_version_command_succeeds():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "granum" in result.stdout.lower()


def test_doctor_fails_without_env(monkeypatch):
    for key in ["GOOGLE_CLOUD_PROJECT", "PHOENIX_API_KEY", "PHOENIX_COLLECTOR_ENDPOINT"]:
        monkeypatch.delenv(key, raising=False)
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "MISSING" in result.stdout or "MISSING" in result.stderr
