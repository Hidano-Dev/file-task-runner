"""Write the SHA-256 of a file in sha256sum format (`<hash> *<name>`), verifiable with `sha256sum -c`.

Usage: sha256.py <input> <output>
"""

import hashlib
import sys
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    line = f"{sha256_of(src)} *{src.name}"
    dst.write_text(line + "\n", encoding="utf-8", newline="\n")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
