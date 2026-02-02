#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def is_prose(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return True
    words = re.findall(r"[A-Za-z]+", stripped)
    if len(words) >= 4 and stripped.endswith((".", ":", "?", "!")):
        return True
    if len(words) >= 6 and not re.search(r"[;=]", stripped):
        return True
    return False


def fix_fences(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    open_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped == "'''":
            stripped = "```"
            line = "```"

        if stripped == "```":
            open_fence = not open_fence
            out.append("```")
            continue

        if open_fence and is_prose(line):
            out.append("```")
            open_fence = False

        out.append(line)

    if open_fence:
        out.append("```")

    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare Markdown for Pandoc LaTeX conversion by fixing unclosed code fences."
    )
    parser.add_argument("input_md", type=Path, help="Path to Markdown file (e.g., combined.md)")
    parser.add_argument("--output-md", type=Path, help="Path to write cleaned Markdown")
    args = parser.parse_args()

    input_md = args.input_md.expanduser().resolve()
    if not input_md.exists():
        print(f"Markdown not found: {input_md}", file=sys.stderr)
        return 1

    output_md = args.output_md
    if output_md is None:
        output_md = input_md.with_name(f"{input_md.stem}_for_tex.md")
    output_md = output_md.expanduser().resolve()

    fixed = fix_fences(input_md.read_text(encoding="utf-8", errors="replace"))
    output_md.write_text(fixed, encoding="utf-8")
    print(f"Wrote cleaned Markdown to {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
