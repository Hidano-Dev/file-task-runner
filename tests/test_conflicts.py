from pathlib import Path

from conftest import write
from file_task_runner import conflicts
from file_task_runner.config import Task
from file_task_runner.plan import build_jobs

TASK = Task(name="t", source=Path("t.toml"), cmd=("x",), output=("{dir}/{stem}.mp4",))


def make_jobs(tmp_path):
    files = [write(tmp_path / "a.mov"), write(tmp_path / "a.avi"), write(tmp_path / "b.mov")]
    write(tmp_path / "b.mp4")
    write(tmp_path / "b (1).mp4")
    return build_jobs(TASK, files)


def test_find_existing_and_duplicate_outputs(tmp_path):
    jobs = make_jobs(tmp_path)
    found = conflicts.find_conflicts(jobs)
    # a.avi also writes a.mp4 (duplicate within the run); b.mp4 already exists.
    assert [(j.path.name, t.name) for j, t in found] == [("a.avi", "a.mp4"), ("b.mov", "b.mp4")]


def test_rename_avoids_existing_and_reserved(tmp_path):
    jobs = make_jobs(tmp_path)
    conflicts.apply_choice(jobs, conflicts.find_conflicts(jobs), conflicts.RENAME)
    assert [j.outputs[0].name for j in jobs] == ["a.mp4", "a (1).mp4", "b (2).mp4"]
    assert conflicts.find_conflicts(jobs) == []


def test_skip_marks_conflicting_jobs(tmp_path):
    jobs = make_jobs(tmp_path)
    conflicts.apply_choice(jobs, conflicts.find_conflicts(jobs), conflicts.SKIP)
    assert [bool(j.skip_reason) for j in jobs] == [False, True, True]


def test_overwrite_changes_nothing(tmp_path):
    jobs = make_jobs(tmp_path)
    conflicts.apply_choice(jobs, conflicts.find_conflicts(jobs), conflicts.OVERWRITE)
    assert [j.outputs[0].name for j in jobs] == ["a.mp4", "a.mp4", "b.mp4"]
    assert not any(j.skip_reason for j in jobs)


def test_ask_choice_retries_until_valid(tmp_path):
    jobs = make_jobs(tmp_path)
    answers = iter(["", "x", "Rename"])
    lines = []
    choice = conflicts.ask_choice(conflicts.find_conflicts(jobs), lambda _: next(answers), lines.append)
    assert choice == conflicts.RENAME
    assert any("b.mp4" in line for line in lines)


def test_ask_choice_eof_cancels(tmp_path):
    def eof(_):
        raise EOFError

    assert conflicts.ask_choice(conflicts.find_conflicts(make_jobs(tmp_path)), eof, lambda _: None) == conflicts.CANCEL
