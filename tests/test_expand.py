from conftest import write
from file_task_runner.expand import expand_paths


def test_folders_are_expanded_recursively_and_sorted(tmp_path):
    write(tmp_path / "d" / "b.txt")
    write(tmp_path / "d" / "sub" / "a.txt")
    write(tmp_path / "d" / "a.txt")
    result = expand_paths([tmp_path / "d"], lambda p: True)
    assert [p.relative_to(tmp_path / "d").as_posix() for p in result.files] == [
        "a.txt", "b.txt", "sub/a.txt",
    ]


def test_ext_filter_duplicates_and_missing(tmp_path):
    a = write(tmp_path / "a.mov")
    write(tmp_path / "b.txt")
    result = expand_paths([a, tmp_path, tmp_path / "missing.mov"], lambda p: p.suffix == ".mov")
    assert result.files == [a]
    assert result.filtered == 1
    assert result.missing == [tmp_path / "missing.mov"]
