"""Convert a .docx to plain text with Markdown-style headings (#) and list items (-).

Usage: docx2text.py <input.docx> <output>
"""

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def paragraph_text(p: ElementTree.Element) -> str:
    text = "".join(t.text or "" for r in p.iter(f"{W}r") for t in r.findall(f"{W}t"))
    style = p.find(f"{W}pPr/{W}pStyle")
    if style is not None:
        value = style.get(f"{W}val", "")
        for level in (1, 2, 3):
            if f"Heading{level}" in value or value == str(level):
                text = "#" * level + " " + text
                break
    if p.find(f"{W}pPr/{W}numPr") is not None and not text.startswith("#"):
        text = "- " + text
    return text


def convert(docx: Path) -> str:
    with zipfile.ZipFile(docx) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    return "".join(paragraph_text(p) + "\n" for p in root.iter(f"{W}p"))


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        text = convert(src)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as e:
        print(f"ERROR: not a valid docx: {e}")
        return 1
    dst.write_text(text, encoding="utf-8")
    print(f"Converted: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
