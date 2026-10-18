"""macOS Finder Quick Actions (Automator workflows in ~/Library/Services).

The workflow runs a "Run Shell Script" action that writes a temporary `.command` file and
opens it in Terminal.app, so task output and the final summary stay visible.
"""

from __future__ import annotations

import plistlib
import shlex
import shutil
import sys
import uuid
from pathlib import Path

from ..config import Task
from . import read_manifest, safe_filename, write_manifest

KIND = "macos-quickaction"

_SHELL_TEMPLATE = """\
f=$(mktemp "${{TMPDIR:-/tmp}}/file-task-runner.XXXXXX") || exit 1
mv "$f" "$f.command" && f="$f.command"
{{
  echo '#!/bin/bash'
  printf 'rm -f %q\\n' "$f"
  printf '%q ' {python} -m file_task_runner run {task} "$@"
  echo
}} > "$f"
chmod +x "$f"
open -a Terminal "$f"
"""


def services_dir() -> Path:
    return Path.home() / "Library" / "Services"


def shell_script(task: Task, python: str) -> str:
    return _SHELL_TEMPLATE.format(python=shlex.quote(python), task=shlex.quote(task.name))


def info_plist(task: Task) -> dict:
    return {
        "CFBundleName": task.label,
        "NSServices": [
            {
                "NSMenuItem": {"default": task.label},
                "NSMessage": "runWorkflowAsService",
                "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
                "NSSendFileTypes": ["public.item"],
            }
        ],
    }


def document_wflow(task: Task, python: str) -> dict:
    string_list = {"Container": "List", "Types": ["com.apple.cocoa.string"]}
    action = {
        "AMAccepts": {**string_list, "Optional": True},
        "AMActionVersion": "2.0.3",
        "AMApplication": ["Automator"],
        "AMParameterProperties": {
            "COMMAND_STRING": {},
            "CheckedForUserDefaultShell": {},
            "inputMethod": {},
            "shell": {},
            "source": {},
        },
        "AMProvides": string_list,
        "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
        "ActionName": "Run Shell Script",
        "ActionParameters": {
            "COMMAND_STRING": shell_script(task, python),
            "CheckedForUserDefaultShell": True,
            "inputMethod": 1,  # pass input as arguments
            "shell": "/bin/bash",
            "source": "",
        },
        "BundleIdentifier": "com.apple.RunShellScript",
        "CFBundleVersion": "2.0.3",
        "CanShowSelectedItemsWhenRun": False,
        "CanShowWhenRun": True,
        "Category": ["AMCategoryUtilities"],
        "Class Name": "RunShellScriptAction",
        "InputUUID": str(uuid.uuid4()).upper(),
        "OutputUUID": str(uuid.uuid4()).upper(),
        "UUID": str(uuid.uuid4()).upper(),
        "UnlocalizedApplications": ["Automator"],
        "isViewVisible": 1,
    }
    return {
        "AMApplicationBuild": "523",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [{"action": action, "isViewVisible": 1}],
        "connectors": {},
        "workflowMetaData": {
            "applicationBundleIDsByPath": {},
            "applicationPaths": [],
            "inputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "outputTypeIdentifier": "com.apple.Automator.nothing",
            "presentationMode": 15,
            "processesInput": 0,
            "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": 0,
            "useAutomaticInputType": 0,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }


def write_workflow(task: Task, folder: Path, python: str) -> Path:
    bundle = folder / f"{safe_filename(task.label)}.workflow"
    contents = bundle / "Contents"
    contents.mkdir(parents=True, exist_ok=True)
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump(info_plist(task), f)
    with (contents / "document.wflow").open("wb") as f:
        plistlib.dump(document_wflow(task, python), f)
    return bundle


def install(tasks: list[Task]) -> list[Path]:
    uninstall()
    folder = services_dir()
    created = []
    for task in tasks:
        bundle = folder / f"{safe_filename(task.label)}.workflow"
        if bundle.exists():
            print(f"skipped (a workflow not created by runner exists): {bundle}", file=sys.stderr)
            continue
        created.append(write_workflow(task, folder, sys.executable))
    write_manifest(KIND, created)
    return created


def uninstall() -> list[Path]:
    removed = []
    for path in read_manifest(KIND):
        if path.is_dir() and path.suffix == ".workflow":
            shutil.rmtree(path)
            removed.append(path)
    write_manifest(KIND, [])
    return removed
