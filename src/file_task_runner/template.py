"""Placeholder substitution for task templates."""

from __future__ import annotations

import os
from pathlib import Path


class TemplateError(Exception):
    pass


class Outputs(list):
    """`{output}` formats as the first output; `{output[1]}` picks others."""

    def __format__(self, spec: str) -> str:
        if not self:
            raise TemplateError("{output} is used but the task declares no 'output'")
        return format(self[0], spec)


def path_values(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "dir": str(path.parent),
        "name": path.name,
        "stem": path.stem,
        "ext": path.suffix,
    }


def render(template: str, values: dict[str, object]) -> str:
    try:
        return template.format_map(values)
    except KeyError as e:
        raise TemplateError(f"unknown placeholder {{{e.args[0]}}} in {template!r}") from e
    except (IndexError, ValueError, AttributeError) as e:
        raise TemplateError(f"invalid template {template!r}: {e}") from e


def render_path(template: str, values: dict[str, object]) -> Path:
    # Templates are written with '/', so normalize to the native separator.
    return Path(os.path.normpath(render(template, values)))
