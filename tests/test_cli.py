import sys

import pytest

from conftest import python_cmd, toml_str, write
from file_task_runner import cli

COPY = "import sys, shutil; shutil.copy(sys.argv[1], sys.argv[2])"
FAIL_ON_B = "import sys; sys.exit(1 if sys.argv[1].endswith('b.txt') else 0)"


def run(*args: str) -> int:
    return cli.main([*args, "--no-pause"])


def add_task(home, body: str) -> None:
    write(home / "tasks" / "test.toml", body)


def test_runs_each_file_and_writes_outputs(home, tmp_path, capsys):
    add_task(home, f'[copy]\ncmd = {python_cmd(COPY)}\noutput = "{{dir}}/out/{{stem}}.bak"\next = [".txt"]\n')
    write(tmp_path / "in" / "a.txt", "A")
    write(tmp_path / "in" / "sub" / "b.txt", "B")
    write(tmp_path / "in" / "c.png")
    assert run("copy", str(tmp_path / "in")) == 0
    assert (tmp_path / "in" / "out" / "a.bak").read_text() == "A"
    assert (tmp_path / "in" / "sub" / "out" / "b.bak").read_text() == "B"
    assert "ignored by ext 1" in capsys.readouterr().out


def test_failures_are_listed_and_exit_code_is_1(home, tmp_path, capsys):
    add_task(home, f'[t]\ncmd = [{toml_str(sys.executable)}, "-c", "{FAIL_ON_B}", "{{path}}"]\n')
    write(tmp_path / "a.txt")
    write(tmp_path / "b.txt")
    assert run("t", str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "failed 1" in out and "b.txt  (exit code 1)" in out


def test_stdout_is_saved_to_file(home, tmp_path):
    add_task(home, f'[t]\ncmd = [{toml_str(sys.executable)}, "-c", "print(42)"]\nstdout = "{{dir}}/{{stem}}.out"\n')
    write(tmp_path / "a.txt")
    assert run("t", str(tmp_path / "a.txt")) == 0
    assert (tmp_path / "a.out").read_text().strip() == "42"


def test_failed_command_removes_partial_stdout_file(home, tmp_path):
    add_task(home, f'[t]\ncmd = [{toml_str(sys.executable)}, "-c", "print(1); raise SystemExit(3)"]\nstdout = "{{dir}}/{{stem}}.out"\n')
    write(tmp_path / "a.txt")
    assert run("t", str(tmp_path / "a.txt")) == 1
    assert not (tmp_path / "a.out").exists()


@pytest.mark.parametrize("on_exists, expected_old, expected_new", [
    ("overwrite", "NEW", None),
    ("skip", "OLD", None),
    ("rename", "OLD", "NEW"),
])
def test_on_exists(home, tmp_path, on_exists, expected_old, expected_new):
    add_task(home, f'[copy]\ncmd = {python_cmd(COPY)}\noutput = "{{dir}}/{{stem}}.bak"\n')
    write(tmp_path / "a.txt", "NEW")
    write(tmp_path / "a.bak", "OLD")
    assert run("copy", str(tmp_path / "a.txt"), "--on-exists", on_exists) == 0
    assert (tmp_path / "a.bak").read_text() == expected_old
    renamed = tmp_path / "a (1).bak"
    assert (renamed.read_text() if renamed.exists() else None) == expected_new


def test_cancel_runs_nothing(home, tmp_path):
    add_task(home, f'[copy]\ncmd = {python_cmd(COPY)}\noutput = "{{dir}}/{{stem}}.bak"\n')
    write(tmp_path / "a.txt", "NEW")
    write(tmp_path / "b.txt", "NEW")
    write(tmp_path / "a.bak", "OLD")
    assert run("copy", str(tmp_path / "a.txt"), str(tmp_path / "b.txt"), "--on-exists", "cancel") == 1
    assert (tmp_path / "a.bak").read_text() == "OLD"
    assert not (tmp_path / "b.bak").exists()


def test_unknown_task_and_command_not_found(home, tmp_path, capsys):
    add_task(home, '[t]\ncmd = ["definitely-not-a-command-ftr"]\n')
    write(tmp_path / "a.txt")
    assert run("nope", str(tmp_path)) == 2
    assert run("t", str(tmp_path)) == 1
    assert "command not found" in capsys.readouterr().out


def test_os_restricted_task(home, tmp_path, monkeypatch):
    add_task(home, '[t]\ncmd = ["x"]\nos = ["macos"]\n')
    monkeypatch.setattr(cli, "current_os", lambda: "windows")
    assert run("t", str(tmp_path)) == 2


def test_missing_path_is_an_error(home, tmp_path):
    add_task(home, f'[t]\ncmd = [{toml_str(sys.executable)}, "-c", ""]\n')
    assert run("t", str(tmp_path / "missing.txt")) == 1


def test_pause_modes(home, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cli.executor, "wait_for_enter", lambda: calls.append(1))
    add_task(home, f'[ok]\ncmd = [{toml_str(sys.executable)}, "-c", ""]\npause = "on_error"\n'
                   f'[always]\ncmd = [{toml_str(sys.executable)}, "-c", ""]\n')
    write(tmp_path / "a.txt")
    cli.main(["ok", str(tmp_path)])
    assert calls == []
    cli.main(["always", str(tmp_path)])
    assert calls == [1]


def test_list(home, capsys):
    assert cli.main(["list"]) == 0
    assert "convert2mp4" in capsys.readouterr().out


def test_builtin_sha256(home, tmp_path):
    import hashlib

    src = write(tmp_path / "日本語.bin", "data")
    assert run("sha256", str(src)) == 0
    expected = f"{hashlib.sha256(b'data').hexdigest()} *日本語.bin\n"
    assert (tmp_path / "日本語.sha256").read_text(encoding="utf-8") == expected


def test_script_task_runs_builtin_docx2md(home, tmp_path):
    import zipfile

    docx = tmp_path / "a.docx"
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    xml = (f'<w:document {w}><w:body>'
           '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Title</w:t></w:r></w:p>'
           '<w:p><w:pPr><w:numPr/></w:pPr><w:r><w:t>item</w:t></w:r><w:r><w:t> 一</w:t></w:r></w:p>'
           '<w:p><w:r><w:t>body</w:t></w:r></w:p>'
           '</w:body></w:document>')
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("word/document.xml", xml)
    assert run("docx2md", str(docx)) == 0
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "# Title\n- item 一\nbody\n"
