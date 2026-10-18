"""Command-line entry point: `runner <task> <path...>` and management subcommands."""

from __future__ import annotations

import argparse
import subprocess
import sys

from . import conflicts, executor
from .colors import RED, color
from .config import ConfigError, Task, current_os, load_tasks, user_tasks_dir
from .expand import expand_paths
from .plan import build_jobs

SUBCOMMANDS = ("run", "list", "install", "uninstall", "open-config")
ON_EXISTS = ("ask", conflicts.OVERWRITE, conflicts.RENAME, conflicts.SKIP, conflicts.CANCEL)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # `runner <task> ...` is shorthand for `runner run <task> ...`.
    if argv and argv[0] not in SUBCOMMANDS and not argv[0].startswith("-"):
        argv = ["run", *argv]
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")

    args = _build_parser().parse_args(argv)
    if args.command is None:
        _build_parser().print_help()
        return 2
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runner", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("run", help="run a task on files / folders (also: runner <task> ...)")
    p.add_argument("task")
    p.add_argument("paths", nargs="+")
    p.add_argument("--on-exists", choices=ON_EXISTS, default="ask",
                   help="what to do when output files already exist (default: ask)")
    p.add_argument("--no-pause", action="store_true", help="never wait for Enter at the end")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("list", help="list available tasks")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("install", help="create Send To shortcuts / Quick Actions for all tasks")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("uninstall", help="remove shortcuts / Quick Actions created by install")
    p.set_defaults(func=cmd_uninstall)

    p = sub.add_parser("open-config", help="open the user task folder")
    p.set_defaults(func=cmd_open_config)
    return parser


def _error(message: str) -> None:
    print(color(f"error: {message}", RED), file=sys.stderr)


def _load_or_report() -> dict[str, Task] | None:
    try:
        return load_tasks()
    except ConfigError as e:
        _error(str(e))
        return None


def cmd_run(args: argparse.Namespace) -> int:
    code, pause_mode = _run(args)
    if not args.no_pause and executor.should_pause(pause_mode, code != 0):
        executor.wait_for_enter()
    return code


def _run(args: argparse.Namespace) -> tuple[int, str]:
    """Returns (exit code, pause mode). Setup errors always pause so Send To users can read them."""
    tasks = _load_or_report()
    if tasks is None:
        return 2, "always"
    task = tasks.get(args.task)
    if task is None:
        _error(f"unknown task: {args.task}  (see `runner list`)")
        return 2, "always"
    if not task.supports(current_os()):
        _error(f"task '{task.name}' is not available on {current_os()}")
        return 2, "always"

    expansion = expand_paths(args.paths, task.accepts)
    jobs = build_jobs(task, expansion.files)
    print(f"{task.label}: {len(jobs)} file(s)")

    found = conflicts.find_conflicts(jobs)
    if found:
        choice = args.on_exists
        if choice == "ask":
            choice = conflicts.ask_choice(found)
        if choice == conflicts.CANCEL:
            print("Cancelled.")
            return 1, "never"
        conflicts.apply_choice(jobs, found, choice)

    summary = executor.run_jobs(jobs)
    executor.print_summary(summary, expansion.missing, expansion.filtered)
    failed = summary.has_errors or bool(expansion.missing)
    if summary.interrupted:
        return 130, task.pause
    return (1 if failed else 0), task.pause


def cmd_list(args: argparse.Namespace) -> int:
    tasks = _load_or_report()
    if tasks is None:
        return 2
    os_name = current_os()
    for task in sorted(tasks.values(), key=lambda t: t.name):
        note = "" if task.supports(os_name) else f"  (only {', '.join(sorted(task.os or ()))})"
        desc = f"  - {task.description}" if task.description else ""
        print(f"{task.name}{desc}{note}")
        print(f"    {task.source}")
    print(f"\nUser tasks folder: {user_tasks_dir()}")
    return 0


def _integration():
    os_name = current_os()
    if os_name == "windows":
        from .integrations import windows
        return windows
    if os_name == "macos":
        from .integrations import macos
        return macos
    _error(f"install is not supported on {os_name}")
    return None


def cmd_install(args: argparse.Namespace) -> int:
    integration = _integration()
    tasks = _load_or_report()
    if integration is None or tasks is None:
        return 2
    available = [t for t in tasks.values() if t.supports(current_os())]
    created = integration.install(sorted(available, key=lambda t: t.name))
    for path in created:
        print(f"created: {path}")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    integration = _integration()
    if integration is None:
        return 2
    for path in integration.uninstall():
        print(f"removed: {path}")
    return 0


def cmd_open_config(args: argparse.Namespace) -> int:
    folder = user_tasks_dir()
    folder.mkdir(parents=True, exist_ok=True)
    print(folder)
    if sys.platform == "win32":
        subprocess.run(["explorer", str(folder)])
    elif sys.platform == "darwin":
        subprocess.run(["open", str(folder)])
    return 0
