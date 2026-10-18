"""Reduce a motion FBX by running motionbuilder/AutoReduction.py in MotionBuilder 2026 (batch).

Usage: motionbuilder_auto_reduction.py <input.fbx> <output.fbx>
"""

import os
import subprocess
import sys
import winreg
from pathlib import Path

MB_VERSION = "2026"
FPS = 30
REDUCTION_SCRIPT = Path(__file__).parent / "motionbuilder" / "AutoReduction.py"


def motionbuilder_exe() -> Path:
    key_path = rf"SOFTWARE\Autodesk\MotionBuilder\{MB_VERSION}"
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
        install_path, _ = winreg.QueryValueEx(key, "InstallPath")
    return Path(install_path) / "bin" / "x64" / "MotionBuilder.exe"


def main() -> int:
    fbx, out = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        exe = motionbuilder_exe()
    except OSError:
        print(f"[ERROR] MotionBuilder {MB_VERSION} InstallPath not found in registry.")
        return 1
    if not exe.is_file():
        print(f"[ERROR] Executable not found: {exe}")
        return 1

    env = dict(
        os.environ,
        MB_AUTOREDUCE_FBX=str(fbx),
        MB_AUTOREDUCE_FPS=str(FPS),
        MB_AUTOREDUCE_OUT=str(out),
    )
    # The runner has already confirmed overwriting; remove it so a stale file is not taken as success.
    out.unlink(missing_ok=True)
    subprocess.run([str(exe), "-batch", str(REDUCTION_SCRIPT)], env=env)
    # MotionBuilder's exit code is not meaningful; judge by the output file.
    if not out.is_file():
        print(f"[ERROR] Output was not created: {out}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
