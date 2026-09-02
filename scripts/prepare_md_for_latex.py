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
PDFTEX_UNICODE_DECLARATIONS = {
    "∆": r"\ifPDFTeX\DeclareUnicodeCharacter{2206}{\ensuremath{\Delta}}\fi",
}


def pdftex_header_includes(text: str) -> list[str]:
    return [
        declaration
        for char, declaration in PDFTEX_UNICODE_DECLARATIONS.items()
        if char in text
    ]


def unsupported_pdftex_unicode(text: str) -> list[str]:
    """Find raw symbols that pdfLaTeX cannot safely infer from Markdown."""

    # URL glyphs do not enter the document as ordinary text. Fenced and inline
    # code do, so inspect them too and allow only explicitly declared symbols.
    inspectable = re.sub(r"https?://\S+", "", text)
    unsupported: list[str] = []
    for char in inspectable:
        if ord(char) <= 127:
            continue
        if char in PDFTEX_UNICODE_DECLARATIONS:
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
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == "'''":
            stripped = "```"
            line = "```"
        opener = re.match(r"^(`{3,})(?:[^`]*)$", stripped)
        if opener is None:
            out.append(line)
            index += 1
            continue

        marker = opener.group(1)
        closing = next(
            (candidate for candidate in range(index + 1, len(lines)) if lines[candidate].strip() == marker),
            None,
        )
        out.append(line)
        index += 1
        if closing is not None:
            out.extend(lines[index:closing + 1])
            index = closing + 1
            continue

        while index < len(lines):
            candidate = lines[index]
            code_like = bool(
                re.match(r"^\s*(?:\d+\s|[%#]|//|/\*|\*|--)", candidate)
                or re.search(r"[;={}()]", candidate)
            )
            if is_prose(candidate) and not code_like:
                out.append(marker)
                break
            out.append(candidate)
            index += 1
        else:
            out.append(marker)

    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare Markdown for Pandoc LaTeX conversion by fixing unclosed code fences."
    )
    parser.add_argument("input_md", type=Path, help="Path to a merged Markdown file")
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
