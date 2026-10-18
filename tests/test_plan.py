from pathlib import Path

import pytest

from file_task_runner.config import Task
from file_task_runner.plan import build_jobs
from file_task_runner.template import TemplateError, path_values, render


def task(**kwargs) -> Task:
    return Task(name="t", source=Path("t.toml"), **kwargs)


def test_placeholders(tmp_path):
    path = tmp_path / "clip.final.mov"
    values = path_values(path)
    assert render("{path}|{dir}|{name}|{stem}|{ext}|{{x}}", values) == (
        f"{path}|{tmp_path}|clip.final.mov|clip.final|.mov|{{x}}"
    )


def test_unknown_placeholder():
    with pytest.raises(TemplateError):
        render("{nope}", {})


def test_outputs_are_normalized_and_rendered_into_cmd(tmp_path):
    src = tmp_path / "a.mov"
    t = task(cmd=("ffmpeg", "-i", "{path}", "{output}", "{output[1]}"),
             output=("{dir}/{stem}.mp4", "{dir}/sub/{stem}.wav"))
    (job,) = build_jobs(t, [src])
    assert job.outputs == [tmp_path / "a.mp4", tmp_path / "sub" / "a.wav"]
    assert job.argv("py") == ["ffmpeg", "-i", str(src), str(tmp_path / "a.mp4"), str(tmp_path / "sub" / "a.wav")]


def test_output_placeholder_without_output_declared(tmp_path):
    (job,) = build_jobs(task(cmd=("x", "{output}")), [tmp_path / "a.txt"])
    with pytest.raises(TemplateError):
        job.argv("py")


def test_script_argv(tmp_path):
    src = tmp_path / "a.docx"
    t = task(script=tmp_path / "s.py", output=("{dir}/{stem}.md",))
    (job,) = build_jobs(t, [src])
    assert job.argv("py") == ["py", str(tmp_path / "s.py"), str(src), str(tmp_path / "a.md")]


def test_output_same_as_input_is_an_error(tmp_path):
    t = task(cmd=("x",), output=("{dir}/{stem}.MP4",))
    (job,) = build_jobs(t, [tmp_path / "a.mp4"])
    if Path("A") == Path("a"):  # case-insensitive file systems (Windows)
        assert job.error
    t = task(cmd=("x",), output=("{path}",))
    (job,) = build_jobs(t, [tmp_path / "a.mp4"])
    assert job.error


def test_bad_output_template_is_a_job_error(tmp_path):
    (job,) = build_jobs(task(cmd=("x",), output=("{oops}",)), [tmp_path / "a"])
    assert "oops" in job.error
