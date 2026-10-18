"""Print image size with a per-extension color; sizes over 2048 are shown in red.

Usage: check_image_size.py <image>
"""

import subprocess
import sys
from pathlib import Path

from file_task_runner.colors import RED, color, hash_value

LIMIT = 2048

EXT_COLORS = {
    ".png": "96",
    ".tga": "95",
    ".jpg": "93",
    ".jpeg": "93",
    ".bmp": "94",
    ".psd": "35",
    ".exr": "92",
    ".tif": "33",
    ".tiff": "33",
    ".hdr": "36",
    ".dds": "34",
    ".webp": "32",
}


def ext_color(ext: str) -> str:
    if ext.lower() in EXT_COLORS:
        return EXT_COLORS[ext.lower()]
    return str(91 + hash_value(ext[1:], "abcdefghijklmnopqrstuvwxyz0123456789") % 6)


def probe_size(path: Path) -> tuple[int, int] | None:
    result = subprocess.run(
        ["ffprobe", "-hide_banner", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", "-i", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        w, h = result.stdout.strip().splitlines()[0].split("x")[:2]
        return int(w), int(h)
    except (IndexError, ValueError):
        return None


def main() -> int:
    path = Path(sys.argv[1])
    size = probe_size(path)
    if size is None:
        print(f'ERROR: Could not read "{path.name}"')
        return 1
    w, h = size
    prefix = color(f"[{path.suffix[1:]}]", ext_color(path.suffix))
    label = f"{path.name}_{w}x{h}"
    if w > LIMIT or h > LIMIT:
        label = color(label, RED)
    print(f"{prefix} {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
