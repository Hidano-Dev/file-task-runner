import sys
from pathlib import Path

import pytest


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Isolated config home whose tasks/ folder is the user task folder."""
    home = tmp_path / "home"
    (home / "tasks").mkdir(parents=True)
    monkeypatch.setenv("FILE_TASK_RUNNER_HOME", str(home))
    return home


def toml_str(value: str) -> str:
    """Literal TOML string (no escape processing, so Windows paths are safe)."""
    return "'" + value + "'"


def python_cmd(code: str) -> str:
    """A TOML `cmd` array that runs `code` with the current Python."""
    return f"[{toml_str(sys.executable)}, '-c', {toml_str(code)}, '{{path}}', '{{output}}']"


def write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
