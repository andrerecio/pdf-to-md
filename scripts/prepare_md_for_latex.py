#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote


IMAGE_TARGET_RE = re.compile(r"!\[[^\]]*\]\((?P<target>[^\n]*)\)(?=\s*$)", re.MULTILINE)
FORMULA_PLACEHOLDER_RE = re.compile(r"<!--\s*formula-(?:not-decoded|missing)\s*-->")
# Pandoc's default pdfLaTeX template/inputenc route handles these ordinary
# Western typography characters.  Keep this deliberately narrow: accepting a
# Unicode punctuation *category* would also admit scripts whose punctuation is
# emitted raw and fails pdfLaTeX.
PDFTEX_SAFE_WESTERN_PUNCTUATION = frozenset("“”‘’‚‛„‟«»‹›–—―…·  ")


def unsupported_pdftex_unicode(text: str) -> list[str]:
    """Find raw symbols that pdfLaTeX cannot safely infer from Markdown."""

    # URLs and verbatim code are not prose/math input to pdfLaTeX in the same
    # way, so avoid treating their escaped or internationalized content as a
    # document glyph.
    inspectable = re.sub(r"```.*?```|`[^`]*`|https?://\S+", "", text, flags=re.DOTALL)
    unsupported: list[str] = []
    for char in inspectable:
        if ord(char) <= 127:
            continue
        name = unicodedata.name(char, "")
        category = unicodedata.category(char)
        is_latin_text = (
            "LATIN" in name
            or category.startswith("M")
            or char in PDFTEX_SAFE_WESTERN_PUNCTUATION
        )
        is_raw_math = (
            "GREEK" in name
            or "COPTIC" in name
            or category == "Sm"
            or 0x2100 <= ord(char) <= 0x22FF
            or 0x27C0 <= ord(char) <= 0x2BFF
            or 0x1D400 <= ord(char) <= 0x1D7FF
        )
        if is_raw_math or not is_latin_text:
            unsupported.append(char)
    return sorted(set(unsupported))


def validate_latex_input(text: str, base_dir: Path | None = None) -> list[str]:
    """Return static pdfLaTeX blockers before Pandoc emits a broken document."""

    errors: list[str] = []
    if FORMULA_PLACEHOLDER_RE.search(text):
        errors.append("unresolved formula placeholder")
    if ".staging/" in text or "/.staging/" in text:
        errors.append("staging path reference")
    raw_unicode = unsupported_pdftex_unicode(text)
    if raw_unicode:
        errors.append(
            "raw Unicode math/symbol glyphs are unsupported by the pdfLaTeX route: "
            + " ".join(raw_unicode)
        )
    for match in IMAGE_TARGET_RE.finditer(text):
        target = unquote(match.group("target").strip().strip("<>").split("#", 1)[0])
        if not target or target.startswith(("data:", "http://", "https://", "//")):
            continue
        path = Path(target)
        if path.is_absolute():
            errors.append(f"absolute local image path: {target}")
            continue
        if base_dir is not None:
            candidate = (base_dir / path).resolve()
            try:
                candidate.relative_to(base_dir.resolve())
            except ValueError:
                errors.append(f"local image outside artifact directory: {target}")
                continue
            if not candidate.is_file():
                errors.append(f"unresolved local image: {target}")
    return errors


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
    errors = validate_latex_input(fixed, input_md.parent)
    if errors:
        print("Cannot prepare pdfLaTeX input: " + "; ".join(errors), file=sys.stderr)
        return 1
    output_md.write_text(fixed, encoding="utf-8")
    print(f"Wrote cleaned Markdown to {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
