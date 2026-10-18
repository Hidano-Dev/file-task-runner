import plistlib
from pathlib import Path

from file_task_runner.config import Task
from file_task_runner.integrations import macos, read_manifest, safe_filename, windows

TASK = Task(name="convert2mp4", source=Path("t.toml"), cmd=("x",), description='To: "mp4"')


def test_safe_filename():
    assert safe_filename('To: "mp4"') == "To_ _mp4_"
    assert safe_filename("...") == "task"


def test_windows_shortcut_spec(tmp_path):
    spec = windows.shortcut_spec(TASK, tmp_path)
    assert spec["lnk"] == str(tmp_path / "To_ _mp4_.lnk")
    assert spec["args"] == "-m file_task_runner run convert2mp4"


def test_macos_install_and_uninstall(home, tmp_path, monkeypatch):
    monkeypatch.setattr(macos, "services_dir", lambda: tmp_path / "Services")
    (bundle,) = macos.install([TASK])
    assert bundle == tmp_path / "Services" / "To_ _mp4_.workflow"
    with (bundle / "Contents" / "document.wflow").open("rb") as f:
        wflow = plistlib.load(f)
    script = wflow["actions"][0]["action"]["ActionParameters"]["COMMAND_STRING"]
    assert "-m file_task_runner run convert2mp4" in script
    assert 'open -a Terminal "$f"' in script
    assert wflow["workflowMetaData"]["workflowTypeIdentifier"] == "com.apple.Automator.servicesMenu"
    with (bundle / "Contents" / "Info.plist").open("rb") as f:
        assert plistlib.load(f)["NSServices"][0]["NSMenuItem"]["default"] == 'To: "mp4"'
    assert read_manifest(macos.KIND) == [bundle]

    assert macos.uninstall() == [bundle]
    assert not bundle.exists()
    assert read_manifest(macos.KIND) == []


def test_macos_install_does_not_touch_foreign_workflows(home, tmp_path, monkeypatch):
    monkeypatch.setattr(macos, "services_dir", lambda: tmp_path / "Services")
    foreign = tmp_path / "Services" / "To_ _mp4_.workflow"
    foreign.mkdir(parents=True)
    assert macos.install([TASK]) == []
    assert foreign.exists()
