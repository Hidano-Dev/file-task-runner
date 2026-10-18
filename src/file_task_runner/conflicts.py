"""Detect existing output files before running and let the user decide what to do."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .plan import Job, path_key

OVERWRITE = "overwrite"
RENAME = "rename"
SKIP = "skip"
CANCEL = "cancel"
CHOICES = {"o": OVERWRITE, "r": RENAME, "s": SKIP, "c": CANCEL}

MAX_LISTED = 20


def find_conflicts(jobs: list[Job]) -> list[tuple[Job, Path]]:
    """Targets that already exist, or that an earlier job in this run will also write."""
    conflicts = []
    seen: set[str] = set()
    for job in jobs:
        if job.error:
            continue
        for target in job.targets:
            key = path_key(target)
            if key in seen or target.exists():
                conflicts.append((job, target))
            seen.add(key)
    return conflicts


def apply_choice(jobs: list[Job], conflicts: list[tuple[Job, Path]], choice: str) -> None:
    if choice == OVERWRITE:
        return
    if choice == SKIP:
        for job, _ in conflicts:
            job.skip_reason = "output already exists"
        return
    if choice == RENAME:
        reserved = {path_key(t) for job in jobs for t in job.targets}
        for job, target in conflicts:
            new = unique_path(target, reserved)
            reserved.add(path_key(new))
            job.replace_target(target, new)
        return
    raise ValueError(f"unsupported choice: {choice}")


def unique_path(path: Path, reserved: set[str]) -> Path:
    """`name.ext` -> `name (1).ext`, `name (2).ext`, ... avoiding existing and reserved paths."""
    n = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists() and path_key(candidate) not in reserved:
            return candidate
        n += 1


def ask_choice(
    conflicts: list[tuple[Job, Path]],
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> str:
    print_fn(f"{len(conflicts)} output file(s) already exist or would be written twice:")
    for _, target in conflicts[:MAX_LISTED]:
        print_fn(f"  {target}")
    if len(conflicts) > MAX_LISTED:
        print_fn(f"  ... and {len(conflicts) - MAX_LISTED} more")
    while True:
        try:
            answer = input_fn("[O]verwrite / [R]ename / [S]kip these / [C]ancel: ")
        except EOFError:
            return CANCEL
        choice = CHOICES.get(answer.strip().lstrip("﻿").lower()[:1])
        if choice:
            return choice
