"""OS integrations. Each module exposes `install(tasks) -> list[Path]` and `uninstall() -> list[Path]`.

Created items are recorded in a manifest so uninstall only removes what install made.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import config_home

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def safe_filename(name: str) -> str:
    return _INVALID_FILENAME_CHARS.sub("_", name).strip(" .") or "task"


def _manifest_path(kind: str) -> Path:
    return config_home() / f"installed-{kind}.json"


def read_manifest(kind: str) -> list[Path]:
    try:
        data = json.loads(_manifest_path(kind).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return [Path(p) for p in data]


def write_manifest(kind: str, paths: list[Path]) -> None:
    path = _manifest_path(kind)
    if not paths:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([str(p) for p in paths], ensure_ascii=False, indent=2), encoding="utf-8")
