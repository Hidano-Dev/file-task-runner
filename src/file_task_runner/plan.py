"""Turn a task and its input files into concrete jobs."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .config import Task
from .template import Outputs, TemplateError, path_values, render, render_path


@dataclass
class Job:
    task: Task
    path: Path
    outputs: list[Path] = field(default_factory=list)
    stdout: Path | None = None
    # Set when the job must not run: an error fails it, a skip reason skips it.
    error: str | None = None
    skip_reason: str | None = None

    @property
    def targets(self) -> list[Path]:
        return self.outputs + ([self.stdout] if self.stdout else [])

    def replace_target(self, old: Path, new: Path) -> None:
        self.outputs = [new if p == old else p for p in self.outputs]
        if self.stdout == old:
            self.stdout = new

    def values(self) -> dict[str, object]:
        values = path_values(self.path)
        values["output"] = Outputs(str(p) for p in self.outputs)
        return values

    def argv(self, python: str) -> list[str]:
        if self.task.script is not None:
            return [python, str(self.task.script), str(self.path), *map(str, self.outputs)]
        assert self.task.cmd is not None
        values = self.values()
        return [render(arg, values) for arg in self.task.cmd]


def path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def build_jobs(task: Task, files: list[Path]) -> list[Job]:
    jobs = []
    for path in files:
        job = Job(task=task, path=path)
        values = path_values(path)
        try:
            job.outputs = [render_path(t, values) for t in task.output]
            if task.stdout is not None:
                job.stdout = render_path(task.stdout, values)
        except TemplateError as e:
            job.error = str(e)
        else:
            if any(path_key(t) == path_key(path) for t in job.targets):
                job.error = "output path is the same as the input file"
        jobs.append(job)
    return jobs
