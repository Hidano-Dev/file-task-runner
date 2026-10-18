"""Run jobs one by one and report the results."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .colors import CYAN, GRAY, GREEN, RED, YELLOW, color
from .plan import Job
from .template import TemplateError

OK = "ok"
FAILED = "failed"
SKIPPED = "skipped"


@dataclass
class Summary:
    ok: list[Job] = field(default_factory=list)
    failed: list[tuple[Job, str]] = field(default_factory=list)
    skipped: list[tuple[Job, str]] = field(default_factory=list)
    not_run: list[Job] = field(default_factory=list)
    interrupted: bool = False

    @property
    def has_errors(self) -> bool:
        return bool(self.failed) or self.interrupted


def run_jobs(jobs: list[Job], print_fn: Callable[[str], None] = print) -> Summary:
    summary = Summary()
    total = len(jobs)
    for i, job in enumerate(jobs, 1):
        print_fn(color(f"[{i}/{total}] {job.path}", CYAN))
        # Child processes write straight to the console; keep our header in front of their output.
        sys.stdout.flush()
        try:
            status, message = run_job(job)
        except KeyboardInterrupt:
            summary.interrupted = True
            summary.failed.append((job, "interrupted"))
            summary.not_run.extend(jobs[i:])
            break
        if status == OK:
            summary.ok.append(job)
        elif status == SKIPPED:
            print_fn(color(f"  skipped: {message}", YELLOW))
            summary.skipped.append((job, message))
        else:
            print_fn(color(f"  failed: {message}", RED))
            summary.failed.append((job, message))
    return summary


def run_job(job: Job) -> tuple[str, str]:
    if job.error:
        return FAILED, job.error
    if job.skip_reason:
        return SKIPPED, job.skip_reason
    try:
        argv = job.argv(sys.executable)
    except TemplateError as e:
        return FAILED, str(e)

    # Resolve through PATH/PATHEXT so `.exe` / `.cmd` shims are found without a shell.
    exe = shutil.which(argv[0])
    if exe is None:
        return FAILED, f"command not found: {argv[0]}"
    argv[0] = exe

    for target in job.targets:
        target.parent.mkdir(parents=True, exist_ok=True)

    try:
        if job.stdout is not None:
            with job.stdout.open("wb") as out:
                code = subprocess.run(argv, stdout=out).returncode
            if code != 0:
                job.stdout.unlink(missing_ok=True)
        else:
            code = subprocess.run(argv).returncode
    except OSError as e:
        return FAILED, str(e)
    if code != 0:
        return FAILED, f"exit code {code}"
    return OK, ""


def print_summary(
    summary: Summary,
    missing: list[Path] = (),
    filtered: int = 0,
    print_fn: Callable[[str], None] = print,
) -> None:
    print_fn("")
    print_fn("=" * 60)
    parts = [color(f"ok {len(summary.ok)}", GREEN)]
    if summary.failed:
        parts.append(color(f"failed {len(summary.failed)}", RED))
    if summary.skipped:
        parts.append(color(f"skipped {len(summary.skipped)}", YELLOW))
    if summary.not_run:
        parts.append(color(f"not run {len(summary.not_run)}", YELLOW))
    if filtered:
        parts.append(color(f"ignored by ext {filtered}", GRAY))
    print_fn("  ".join(parts))
    if summary.interrupted:
        print_fn(color("Interrupted.", RED))
    if summary.failed:
        print_fn(color("Failed:", RED))
        for job, message in summary.failed:
            print_fn(f"  {job.path}  ({message})")
    if missing:
        print_fn(color("Not found:", RED))
        for path in missing:
            print_fn(f"  {path}")


def should_pause(mode: str, has_errors: bool) -> bool:
    return mode == "always" or (mode == "on_error" and has_errors)


def wait_for_enter() -> None:
    try:
        input("Press Enter to close...")
    except (EOFError, KeyboardInterrupt):
        pass
