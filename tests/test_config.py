import pytest

from conftest import write
from file_task_runner.config import ConfigError, builtin_tasks_dir, load_file, load_tasks


def test_builtin_tasks_load_and_scripts_exist():
    tasks = load_tasks([builtin_tasks_dir()])
    assert {"convert2mp4", "convert2mp3", "check_image_size", "docx2md"} <= set(tasks)
    for task in tasks.values():
        if task.script is not None:
            assert task.script.is_file(), task.name


def test_user_tasks_override_builtin(tmp_path):
    a = write(tmp_path / "a" / "tasks.toml", '[t]\ncmd = ["one"]\n[u]\ncmd = ["u"]\n')
    b = write(tmp_path / "b" / "mine.toml", '[t]\ncmd = ["two"]\n')
    tasks = load_tasks([a.parent, b.parent])
    assert tasks["t"].cmd == ("two",)
    assert tasks["u"].cmd == ("u",)


def test_missing_folder_is_ignored(tmp_path):
    assert load_tasks([tmp_path / "nope"]) == {}


def test_parse_fields(tmp_path):
    path = write(tmp_path / "t.toml", """
[t]
script = "s.py"
output = "{dir}/{stem}.x"
ext = ["PNG", ".Jpg"]
os = ["windows"]
pause = "on_error"
description = "Desc"
""")
    (task,) = load_file(path)
    assert task.script == tmp_path / "s.py"
    assert task.output == ("{dir}/{stem}.x",)
    assert task.ext == {".png", ".jpg"}
    assert task.supports("windows") and not task.supports("macos")
    assert task.pause == "on_error"
    assert task.label == "Desc"


@pytest.mark.parametrize("body", [
    'cmd = ["a"]\nscript = "b.py"',
    'output = "x"',
    'cmd = []',
    'cmd = ["a"]\npause = "sometimes"',
    'cmd = ["a"]\nos = ["linux"]',
    'cmd = ["a"]\ntypo = 1',
])
def test_invalid_task(tmp_path, body):
    path = write(tmp_path / "t.toml", f"[t]\n{body}\n")
    with pytest.raises(ConfigError):
        load_file(path)


@pytest.mark.parametrize("name", ["list", "has space", "日本語"])
def test_invalid_task_name(tmp_path, name):
    path = write(tmp_path / "t.toml", f'["{name}"]\ncmd = ["a"]\n')
    with pytest.raises(ConfigError):
        load_file(path)


def test_toml_syntax_error(tmp_path):
    path = write(tmp_path / "t.toml", "[t\n")
    with pytest.raises(ConfigError):
        load_file(path)
