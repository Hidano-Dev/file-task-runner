"""Expand command-line paths into the list of files to process."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Expansion:
    files: list[Path] = field(default_factory=list)
    missing: list[Path] = field(default_factory=list)
    filtered: int = 0


def expand_paths(args: Iterable[str | Path], accepts: Callable[[Path], bool]) -> Expansion:
    """Folders are expanded recursively (sorted); duplicates are dropped, keeping first order."""
    result = Expansion()
    seen: set[Path] = set()
    for arg in args:
        path = Path(arg).absolute()
        if path.is_dir():
            candidates = sorted(p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            candidates = [path]
        else:
            result.missing.append(path)
            continue
        for p in candidates:
            if p in seen:
                continue
            seen.add(p)
            if accepts(p):
                result.files.append(p)
            else:
                result.filtered += 1
    return result
