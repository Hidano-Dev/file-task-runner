"""Windows Explorer "Send To" shortcuts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ..config import Task
from . import read_manifest, safe_filename, write_manifest

KIND = "windows-sendto"

# Shortcut data is passed through an environment variable to avoid any quoting issues.
_CREATE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject WScript.Shell
foreach ($i in ($env:FTR_SHORTCUTS | ConvertFrom-Json)) {
    $s = $shell.CreateShortcut($i.lnk)
    $s.TargetPath = $i.target
    $s.Arguments = $i.args
    $s.WorkingDirectory = $i.cwd
    $s.Description = $i.desc
    $s.Save()
}
"""


def sendto_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "SendTo"


def shortcut_spec(task: Task, folder: Path) -> dict[str, str]:
    return {
        "lnk": str(folder / f"{safe_filename(task.label)}.lnk"),
        # The venv's python.exe stays valid even when its Scripts folder is not on PATH.
        "target": sys.executable,
        "args": f"-m file_task_runner run {task.name}",
        "cwd": str(Path.home()),
        "desc": f"file-task-runner: {task.label}",
    }


def install(tasks: list[Task]) -> list[Path]:
    uninstall()
    folder = sendto_dir()
    specs = []
    for task in tasks:
        spec = shortcut_spec(task, folder)
        if Path(spec["lnk"]).exists():
            print(f"skipped (a file not created by runner exists): {spec['lnk']}", file=sys.stderr)
            continue
        specs.append(spec)
    if specs:
        env = dict(os.environ, FTR_SHORTCUTS=json.dumps(specs, ensure_ascii=False))
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _CREATE_SCRIPT],
            env=env,
            check=True,
        )
    created = [Path(s["lnk"]) for s in specs]
    write_manifest(KIND, created)
    return created


def uninstall() -> list[Path]:
    removed = []
    for path in read_manifest(KIND):
        if path.exists():
            path.unlink()
            removed.append(path)
    write_manifest(KIND, [])
    return removed
