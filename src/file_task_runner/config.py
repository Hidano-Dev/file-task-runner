"""Load task definitions from the built-in and user task folders."""

from __future__ import annotations

import os
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "file-task-runner"
HOME_ENV = "FILE_TASK_RUNNER_HOME"

PAUSE_MODES = ("always", "on_error", "never")
OS_NAMES = ("windows", "macos")
# Task names become CLI arguments and shortcut arguments, so keep them shell-safe.
TASK_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
# Names that would be shadowed by subcommands in `runner <task> ...`.
RESERVED_NAMES = frozenset({"run", "list", "install", "uninstall", "open-config"})
ALLOWED_KEYS = frozenset({"cmd", "script", "output", "stdout", "ext", "os", "pause", "description"})


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Task:
    name: str
    source: Path
    cmd: tuple[str, ...] | None = None
    script: Path | None = None
    output: tuple[str, ...] = ()
    stdout: str | None = None
    ext: frozenset[str] | None = None
    os: frozenset[str] | None = None
    pause: str = "always"
    description: str = ""

    @property
    def label(self) -> str:
        return self.description or self.name

    def supports(self, os_name: str) -> bool:
        return self.os is None or os_name in self.os

    def accepts(self, path: Path) -> bool:
        return self.ext is None or path.suffix.lower() in self.ext


def current_os() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return sys.platform


def config_home() -> Path:
    override = os.environ.get(HOME_ENV)
    if override:
        return Path(override)
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME


def user_tasks_dir() -> Path:
    return config_home() / "tasks"


def builtin_tasks_dir() -> Path:
    return Path(__file__).parent / "builtin_tasks"


def load_tasks(dirs: list[Path] | None = None) -> dict[str, Task]:
    """Load all tasks. Later folders override tasks of the same name in earlier ones."""
    if dirs is None:
        dirs = [builtin_tasks_dir(), user_tasks_dir()]
    tasks: dict[str, Task] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for toml_path in sorted(d.glob("*.toml")):
            for task in load_file(toml_path):
                tasks[task.name] = task
    return tasks


def load_file(path: Path) -> list[Task]:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e
    return [_parse_task(name, body, path) for name, body in data.items()]


def _parse_task(name: str, body: object, source: Path) -> Task:
    where = f"{source}: [{name}]"
    if not isinstance(body, dict):
        raise ConfigError(f"{where}: must be a table")
    if not TASK_NAME_RE.match(name):
        raise ConfigError(f"{where}: task name may only contain letters, digits, '_', '.', '-'")
    if name in RESERVED_NAMES:
        raise ConfigError(f"{where}: '{name}' is reserved for a subcommand")
    unknown = set(body) - ALLOWED_KEYS
    if unknown:
        raise ConfigError(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")

    cmd = body.get("cmd")
    script = body.get("script")
    if (cmd is None) == (script is None):
        raise ConfigError(f"{where}: specify exactly one of 'cmd' or 'script'")
    if cmd is not None and not _is_str_list(cmd, allow_empty=False):
        raise ConfigError(f"{where}: 'cmd' must be a non-empty array of strings")
    if script is not None and not isinstance(script, str):
        raise ConfigError(f"{where}: 'script' must be a string")

    output = body.get("output", [])
    if isinstance(output, str):
        output = [output]
    if not _is_str_list(output):
        raise ConfigError(f"{where}: 'output' must be a string or an array of strings")

    stdout = body.get("stdout")
    if stdout is not None and not isinstance(stdout, str):
        raise ConfigError(f"{where}: 'stdout' must be a string")

    ext = body.get("ext")
    if ext is not None:
        if not _is_str_list(ext, allow_empty=False):
            raise ConfigError(f"{where}: 'ext' must be a non-empty array of strings")
        ext = frozenset(e.lower() if e.startswith(".") else "." + e.lower() for e in ext)

    os_list = body.get("os")
    if os_list is not None:
        if not _is_str_list(os_list, allow_empty=False) or not set(os_list) <= set(OS_NAMES):
            raise ConfigError(f"{where}: 'os' must be an array of {', '.join(OS_NAMES)}")
        os_list = frozenset(os_list)

    pause = body.get("pause", "always")
    if pause not in PAUSE_MODES:
        raise ConfigError(f"{where}: 'pause' must be one of {', '.join(PAUSE_MODES)}")

    description = body.get("description", "")
    if not isinstance(description, str):
        raise ConfigError(f"{where}: 'description' must be a string")

    return Task(
        name=name,
        source=source,
        cmd=tuple(cmd) if cmd is not None else None,
        script=(source.parent / script) if script is not None else None,
        output=tuple(output),
        stdout=stdout,
        ext=ext,
        os=os_list,
        pause=pause,
        description=description,
    )


def _is_str_list(value: object, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(v, str) for v in value)
    )
