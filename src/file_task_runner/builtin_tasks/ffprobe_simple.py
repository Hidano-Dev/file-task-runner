"""Print codec, resolution, FPS and audio presence, each value hash-colored.

Output: codec<TAB>WxH<TAB>FPS<TAB>Audio<TAB>file name
(variable-length file name last so the tab-separated columns line up)

Usage: ffprobe_simple.py <video>
"""

import subprocess
import sys
from pathlib import Path

from file_task_runner.colors import GREEN, RED, color, hash_color


def probe(path: Path, stream: str, entries: str) -> str:
    result = subprocess.run(
        ["ffprobe", "-hide_banner", "-v", "error", "-select_streams", stream,
         "-show_entries", f"stream={entries}", "-of", "csv=s=,:p=0", "-i", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    lines = result.stdout.strip().splitlines()
    return lines[-1] if lines else ""


def format_fps(raw: str) -> str:
    """`30000/1001` -> `29.97`, truncated like the old bat."""
    num, _, den = raw.partition("/")
    try:
        n, d = int(num), int(den)
    except ValueError:
        return raw
    if d <= 0:
        return raw
    return f"{n // d}.{(n % d) * 100 // d:02d}"


def main() -> int:
    path = Path(sys.argv[1])
    info = probe(path, "v:0", "codec_name,width,height,r_frame_rate")
    fields = info.split(",")
    if len(fields) < 4:
        print(f'ERROR: Could not read "{path.name}"')
        return 1
    codec, w, h, fps_raw = fields[:4]
    fps = format_fps(fps_raw)
    res = f"{w}x{h}"
    has_audio = bool(probe(path, "a:0", "codec_name"))
    audio = color("Audio", GREEN) if has_audio else color("No Audio", RED)
    print("\t".join([
        color(codec, hash_color(codec)),
        color(res, hash_color(res)),
        color(f"{fps}fps", hash_color(fps)),
        audio,
        path.name,
    ]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
