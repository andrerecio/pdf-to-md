#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path

DATA_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(data:image/(?P<fmt>[a-zA-Z0-9.+-]+);base64,(?P<b64>[A-Za-z0-9+/=\s]+)\)",
    re.DOTALL,
)


def decode_docling_markdown(input_md: Path, output_md: Path, figures_dir: Path) -> int:
    figures_dir.mkdir(parents=True, exist_ok=True)
    text = input_md.read_text(encoding="utf-8")
    count = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        fmt = match.group("fmt").lower()
        ext = "jpg" if fmt in {"jpeg", "jpg"} else fmt
        b64 = re.sub(r"\s+", "", match.group("b64"))
        data = base64.b64decode(b64)
        filename = f"figure-{count:03d}.{ext}"
        out_path = figures_dir / filename
        out_path.write_bytes(data)
        alt = match.group("alt")
        return f"![{alt}](figures/{filename})"

    new_text, _ = DATA_RE.subn(_replace, text)
    output_md.write_text(new_text, encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode Docling base64 images to files and rewrite Markdown.")
    parser.add_argument("input_md", type=Path, help="Path to Docling Markdown output")
    parser.add_argument("output_md", type=Path, help="Path to write rewritten Markdown")
    parser.add_argument("figures_dir", type=Path, help="Directory to write decoded images")
    args = parser.parse_args()

    count = decode_docling_markdown(args.input_md, args.output_md, args.figures_dir)
    print(f"Decoded {count} figures into {args.figures_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
