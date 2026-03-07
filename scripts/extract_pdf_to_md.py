#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import shlex
from dataclasses import dataclass
from pathlib import Path
from bisect import bisect_right
from difflib import SequenceMatcher

from parse_docling_figures import decode_docling_markdown
from prepare_md_for_latex import fix_fences


def find_command(cmd: str) -> str | None:
    bin_dir = Path(sys.executable).parent
    candidate = bin_dir / cmd
    if candidate.exists():
        return str(candidate)
    return shutil.which(cmd)


def require_command(cmd: str, override: str | None) -> str:
    if override:
        path = Path(override).expanduser()
        if not path.exists():
            print(f"Missing required command at path: {path}", file=sys.stderr)
            raise SystemExit(1)
        return str(path)

    resolved = find_command(cmd)
    if resolved is None:
        print(f"Missing required command: {cmd}", file=sys.stderr)
        raise SystemExit(1)
    return resolved


def run_cmd(cmd: list[str], stdout_path: Path) -> None:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as handle:
        subprocess.run(cmd, check=True, stdout=handle)


def run_nougat(
    nougat_cmd: str,
    pdf_path: Path,
    text_md: Path,
    job_dir: Path,
    nougat_args: list[str],
) -> None:
    run_cmd([nougat_cmd, *nougat_args, str(pdf_path)], text_md)
    if text_md.exists() and text_md.stat().st_size > 0:
        return

    tmp_out = job_dir / "nougat_out"
    tmp_out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [nougat_cmd, *nougat_args, str(pdf_path), "--markdown", "--out", str(tmp_out)],
        check=True,
    )
    mmd_files = list(tmp_out.glob("*.mmd"))
    if not mmd_files:
        raise RuntimeError("Nougat did not produce a .mmd output file.")

    text_md.write_text(mmd_files[0].read_text(encoding="utf-8"), encoding="utf-8")


def run_docling(
    docling_cmd: str,
    pdf_path: Path,
    figures_md: Path,
    job_dir: Path,
    docling_args: list[str],
) -> None:
    docling_out = job_dir / "docling_out"
    docling_out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            docling_cmd,
            *docling_args,
            "--to",
            "md",
            "--image-export-mode",
            "embedded",
            "--output",
            str(docling_out),
            str(pdf_path),
        ],
        check=True,
    )
    md_files = list(docling_out.glob("*.md"))
    if not md_files:
        raise RuntimeError("Docling did not produce a .md output file.")
    figures_md.write_text(md_files[0].read_text(encoding="utf-8"), encoding="utf-8")


FORMULA_RE = re.compile(
    r"\$\$.*?\$\$"
    r"|\\\[.*?\\\]"
    r"|\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?)\}.*?\\end\{\1\}"
    r"|\\\(.*?\\\)"
    r"|(?<!\$)\$(?!\$)[^\n]+?(?<!\$)\$(?!\$)",
    re.DOTALL,
)

FENCED_RE = re.compile(r"```.*?```", re.DOTALL)
TRIPLE_QUOTE_RE = re.compile(r"'''[\\s\\S]*?'''", re.DOTALL)
VERBATIM_RE = re.compile(r"\\begin\{verbatim\}.*?\\end\{verbatim\}", re.DOTALL)
TABULAR_RE = re.compile(r"\\begin\{tabular\}.*?\\end\{tabular\}", re.DOTALL)

STRUCTURED_RE = re.compile(
    r"\$\$|\\\[|\\\(|\\begin\{|```|'''|\\begin\{tabular\}",
    re.DOTALL,
)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
CAPTION_RE = re.compile(r"^(fig(?:ure)?\.?)\b", re.IGNORECASE)
TABLE_RE = re.compile(r"^(table\.?)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s")
FIGURE_CAP_RE = re.compile(r"^Figure\s+\d+:\s+(.+)$")
TABLE_CAP_RE = re.compile(r"^Table\s+\d+:\s+(.+)$")
FOOTNOTE_START_RE = re.compile(r"^(?P<num>\d+)[\).]?\s+(?P<body>.+)")


@dataclass
class Token:
    type: str
    text: str
    start: int
    end: int
    inline: bool = False


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < s_end and end > s_start for s_start, s_end in spans)


def extract_markdown_tables(text: str, occupied: list[tuple[int, int]]) -> list[Token]:
    tokens: list[Token] = []
    lines = text.splitlines(keepends=True)
    line_starts: list[int] = []
    pos = 0
    for line in lines:
        line_starts.append(pos)
        pos += len(line)

    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        next_line = lines[i + 1]
        if "|" in line and re.match(r"^\s*\|?[\s:-]+\|[\s:-|]*$", next_line):
            start = line_starts[i]
            j = i + 2
            while j < len(lines) and "|" in lines[j]:
                j += 1
            end = line_starts[j] if j < len(lines) else len(text)
            if not _overlaps(start, end, occupied):
                tokens.append(Token(type="table", text=text[start:end], start=start, end=end))
                occupied.append((start, end))
            i = j
            continue
        i += 1
    return tokens


def extract_tokens(text: str) -> list[Token]:
    tokens: list[Token] = []
    occupied: list[tuple[int, int]] = []

    for regex in (FENCED_RE, TRIPLE_QUOTE_RE, VERBATIM_RE):
        for m in regex.finditer(text):
            tokens.append(Token(type="verbatim", text=m.group(0), start=m.start(), end=m.end()))
            occupied.append((m.start(), m.end()))

    for m in TABULAR_RE.finditer(text):
        tokens.append(Token(type="latex_table", text=m.group(0), start=m.start(), end=m.end()))
        occupied.append((m.start(), m.end()))

    tokens.extend(extract_markdown_tables(text, occupied))

    for m in FORMULA_RE.finditer(text):
        if _overlaps(m.start(), m.end(), occupied):
            continue
        f = m.group(0).strip()
        inline = f.startswith("\\(") or (f.startswith("$") and not f.startswith("$$"))
        tokens.append(Token(type="formula", text=f, start=m.start(), end=m.end(), inline=inline))
        occupied.append((m.start(), m.end()))

    return sorted(tokens, key=lambda t: t.start)


def normalize_display(formula: str) -> str:
    f = formula.strip()
    if f.startswith("\\[") and f.endswith("\\]"):
        inner = f[2:-2].strip()
        return f"$$\n{inner}\n$$"
    return f


def normalize_inline(formula: str) -> str:
    f = formula.strip()
    if f.startswith("\\(") and f.endswith("\\)"):
        inner = f[2:-2].strip()
        return f"${inner}$"
    return f


def format_formula_for_placeholder(token: Token) -> str:
    if token.inline:
        return normalize_inline(token.text)
    return normalize_display(token.text)


def replace_placeholders_with_formulas(content: str, formulas: list[Token]) -> tuple[str, int]:
    marker = "## Formulas (Nougat)"
    if marker in content:
        content = content.split(marker, 1)[0].rstrip() + "\n"

    placeholders = list(re.finditer(r"<!-- formula-not-decoded -->", content))
    if not placeholders:
        return content, 0

    out_parts: list[str] = []
    last_idx = 0
    inserted = 0
    for ph in placeholders:
        out_parts.append(content[last_idx:ph.start()])
        if inserted < len(formulas):
            out_parts.append("\n" + format_formula_for_placeholder(formulas[inserted]) + "\n")
        else:
            out_parts.append("\n<!-- formula-missing -->\n")
        inserted += 1
        last_idx = ph.end()
    out_parts.append(content[last_idx:])
    return "".join(out_parts), inserted


def normalize_bracket_math(text: str) -> str:
    return re.sub(r"\\\[(.*?)\\\]", lambda m: f"$$\n{m.group(1).strip()}\n$$", text, flags=re.DOTALL)


def normalize_inline_math(text: str) -> str:
    return re.sub(r"\\\((.*?)\\\)", lambda m: f"${m.group(1).strip()}$", text, flags=re.DOTALL)


def yaml_escape(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
    return escaped.replace("\n", " ")


def build_yaml_metadata(title: str | None, author: str | None, date: str | None) -> str:
    items: list[str] = []
    if title:
        items.append(f"title: \"{yaml_escape(title)}\"")
    if author:
        items.append(f"author: \"{yaml_escape(author)}\"")
    if date:
        items.append(f"date: \"{yaml_escape(date)}\"")
    if not items:
        return ""
    return "---\n" + "\n".join(items) + "\n---\n\n"


def extract_figure_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if IMAGE_RE.search(line):
            block_lines: list[str] = []
            caption_candidates: list[str] = []
            prev = i - 1
            while prev >= 0 and not lines[prev].strip():
                prev -= 1
            if prev >= 0:
                prev_text = lines[prev].strip()
                if TABLE_RE.match(prev_text):
                    i = i + 1
                    continue
                if CAPTION_RE.match(prev_text):
                    caption_line = lines[prev].rstrip()
                    block_lines.append(caption_line)
                    caption_candidates.append(caption_line)
            block_lines.append(line.rstrip())
            j = i + 1
            while j < len(lines):
                if IMAGE_RE.search(lines[j]) and lines[j].strip():
                    break
                if HEADING_RE.match(lines[j].strip()):
                    break
                if not lines[j].strip():
                    break
                caption_line = lines[j].rstrip()
                block_lines.append(caption_line)
                caption_candidates.append(caption_line)
                j += 1
            if any(TABLE_RE.match(c.strip()) for c in caption_candidates):
                i = j
                continue
            block = "\n".join(block_lines).strip()
            if block:
                blocks.append(block)
            i = j
            continue
        i += 1
    return blocks


def extract_footnote_defs(text: str) -> dict[str, str]:
    lines = text.splitlines()
    foot_defs: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m = FOOTNOTE_START_RE.match(line.strip())
        if not m:
            i += 1
            continue

        num = m.group("num")
        prev = i - 1
        while prev >= 0 and not lines[prev].strip():
            prev -= 1
        prev_line = lines[prev].rstrip() if prev >= 0 else ""
        prev_match = bool(re.search(rf"(?:\b{re.escape(num)}\b)[\s.]*$", prev_line))

        body = m.group("body").strip()
        block = [body] if body else []
        j = i + 1
        while j < len(lines) and lines[j].strip():
            block.append(lines[j].strip())
            j += 1
        block_text = " ".join(s for s in block if s).strip()

        word_count = len(re.findall(r"[A-Za-z]+", block_text))
        has_url = "http" in block_text or "www." in block_text
        has_period = block_text.count(".") >= 1

        if (prev_match or has_url) and word_count >= 8 and has_period:
            foot_defs.setdefault(num, block_text)

        i = j

    return foot_defs


def extract_footnote_markers(text: str, foot_defs: dict[str, str]) -> dict[str, list[str]]:
    markers: dict[str, list[str]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        m = re.search(r"(.*?)(?:\s|\u00A0)(\d+)\s*$", stripped)
        if not m:
            continue
        num = m.group(2)
        if num not in foot_defs or num in markers:
            continue
        words = re.findall(r"[A-Za-z]+", m.group(1))
        if len(words) < 3:
            continue
        markers[num] = words[-6:]
    return markers


def in_code_fence(text: str, pos: int) -> bool:
    return text[:pos].count("```") % 2 == 1


def line_at(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end]


def find_replacement(text: str, context_words: list[str], num: str) -> tuple[int, int] | None:
    pattern = r"\b" + r"\W+".join(map(re.escape, context_words)) + r"\b"
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        pos = m.end()
        line = line_at(text, pos).lstrip()
        if line.startswith("#"):
            continue
        if in_code_fence(text, pos):
            continue
        tail = text[pos:pos + 10]
        mnum = re.search(rf"\s*{re.escape(num)}(?!\d)", tail)
        if mnum:
            start = pos + mnum.start()
            end = pos + mnum.end()
            return start, end
        while pos < len(text) and text[pos] in ".;,!?":
            pos += 1
        return pos, pos
    return None


def extract_figure_images_from_section(lines: list[str]) -> list[str]:
    images: list[str] = []
    for line in lines:
        if "\\includegraphics" in line or "\\pandocbounded" in line:
            images.append(line)
    return images


def split_caption_text(text: str) -> tuple[str, str]:
    m = re.search(r"([a-z])([A-Z])", text)
    if m:
        idx = m.start(2)
        return text[:idx].rstrip(), text[idx:].lstrip()
    return text.strip(), ""


def split_caption_with_next_line(caption: str, next_line: str) -> tuple[str, str]:
    m = re.match(r"^([A-Z][a-z]+)(\\\(|\\\[|\\$)", next_line.strip())
    if not m:
        return caption, ""
    word = m.group(1)
    remainder = next_line.strip()[len(word):].lstrip()
    return f"{caption} {word}".strip(), remainder


def postprocess_latex(latex_text: str) -> str:
    lines = latex_text.splitlines()

    fig_start = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("\\subsection{Figures}") or line.strip().startswith("\\section{Figures}"):
            fig_start = idx
            break

    figure_images: list[str] = []
    if fig_start is not None:
        fig_end = None
        for idx in range(fig_start + 1, len(lines)):
            if lines[idx].strip().startswith("\\section{") or lines[idx].strip().startswith("\\subsection{"):
                fig_end = idx
                break
            if lines[idx].strip() == "\\end{document}":
                fig_end = idx
                break
        if fig_end is None:
            fig_end = len(lines)
        figure_images = extract_figure_images_from_section(lines[fig_start + 1:fig_end])
        lines = lines[:fig_start] + lines[fig_end:]

    out: list[str] = []
    fig_idx = 0
    i = 0
    in_verbatim = False
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("\\begin{verbatim}"):
            in_verbatim = True
            out.append(line)
            i += 1
            continue
        if in_verbatim:
            out.append(line)
            if line.strip().startswith("\\end{verbatim}"):
                in_verbatim = False
            i += 1
            continue
        fig_match = FIGURE_CAP_RE.match(line.strip())
        if fig_match and fig_idx < len(figure_images):
            caption_full = fig_match.group(1).strip()
            caption, remainder = split_caption_text(caption_full)
            image_line = figure_images[fig_idx]
            fig_idx += 1
            out.append("\\begin{figure}")
            out.append("\\centering")
            out.append(image_line)
            out.append(f"\\caption{{{caption}}}")
            out.append("\\end{figure}")
            if remainder:
                out.append(remainder)
            i += 1
            continue

        if line.strip().startswith("\\begin{table}"):
            table_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("\\end{table}"):
                table_lines.append(lines[i])
                i += 1
            if i < len(lines):
                table_lines.append(lines[i])
                i += 1

            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                cap_match = TABLE_CAP_RE.match(lines[j].strip())
                if cap_match:
                    caption_full = cap_match.group(1).strip()
                    caption, remainder = split_caption_text(caption_full)
                    if not remainder and j + 1 < len(lines):
                        caption, remainder = split_caption_with_next_line(caption, lines[j + 1])
                    for idx in range(len(table_lines) - 1, -1, -1):
                        if table_lines[idx].strip().startswith("\\end{table}"):
                            table_lines.insert(idx, f"\\caption{{{caption}}}")
                            break
                    out.extend(table_lines)
                    if remainder:
                        out.append(remainder)
                    i = j + (2 if remainder else 1)
                    continue
            out.extend(table_lines)
            i = j
            continue

        out.append(line)
        i += 1

    if fig_idx < len(figure_images):
        out.append("\\section*{Figures (Unplaced)}")
        for image_line in figure_images[fig_idx:]:
            out.append("\\begin{figure}")
            out.append("\\centering")
            out.append(image_line)
            out.append("\\caption{Unplaced Figure}")
            out.append("\\end{figure}")

    return "\n".join(out) + "\n"


def mask_spans(text: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return text
    chars = list(text)
    for start, end in spans:
        for i in range(start, end):
            chars[i] = " "
    return "".join(chars)


def word_positions(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"[A-Za-z0-9]+", text)]


def build_word_map(nougat_text: str, docling_text: str, nougat_spans: list[tuple[int, int]], docling_spans: list[tuple[int, int]]) -> tuple[list[tuple[int, int]], list[tuple[int, int]], list[tuple[int, int, int]]]:
    masked_nougat = mask_spans(nougat_text, nougat_spans)
    masked_docling = mask_spans(docling_text, docling_spans)

    nougat_positions = word_positions(masked_nougat)
    docling_positions = word_positions(masked_docling)

    nougat_words = [masked_nougat[s:e].lower() for s, e in nougat_positions]
    docling_words = [masked_docling[s:e].lower() for s, e in docling_positions]

    matcher = SequenceMatcher(None, nougat_words, docling_words, autojunk=False)
    blocks = [(b.a, b.b, b.size) for b in matcher.get_matching_blocks() if b.size > 0]
    return nougat_positions, docling_positions, blocks


def map_word_index(word_idx: int, blocks: list[tuple[int, int, int]]) -> int | None:
    for a, b, size in blocks:
        if a <= word_idx < a + size:
            return b + (word_idx - a)

    prev = None
    next_block = None
    for a, b, size in blocks:
        if a + size <= word_idx:
            if prev is None or a + size > prev[0] + prev[2]:
                prev = (a, b, size)
        elif a > word_idx and next_block is None:
            next_block = (a, b, size)

    if prev is not None:
        return prev[1] + prev[2]
    if next_block is not None:
        return next_block[1]
    return None


def spans_from_regex(text: str, regex: re.Pattern[str]) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in regex.finditer(text)]


def insert_tokens_by_alignment(content: str, tokens: list[Token], source_text: str) -> str:
    if not tokens:
        return content

    # Mask Docling images to avoid huge base64 words
    image_spans = spans_from_regex(content, re.compile(r"!\[[^\]]*\]\([^)]+\)"))

    # Mask structured spans in both source and target
    src_spans = spans_from_regex(source_text, FENCED_RE)
    src_spans += spans_from_regex(source_text, TRIPLE_QUOTE_RE)
    src_spans += spans_from_regex(source_text, VERBATIM_RE)
    src_spans += spans_from_regex(source_text, TABULAR_RE)
    src_spans += spans_from_regex(source_text, FORMULA_RE)

    tgt_spans = image_spans
    tgt_spans += spans_from_regex(content, FENCED_RE)
    tgt_spans += spans_from_regex(content, TRIPLE_QUOTE_RE)
    tgt_spans += spans_from_regex(content, VERBATIM_RE)
    tgt_spans += spans_from_regex(content, TABULAR_RE)
    tgt_spans += spans_from_regex(content, FORMULA_RE)

    nougat_positions, docling_positions, blocks = build_word_map(source_text, content, src_spans, tgt_spans)
    if not nougat_positions or not docling_positions:
        return content

    nougat_starts = [s for s, _ in nougat_positions]
    insertions: list[tuple[int, str]] = []

    table_spans = extract_markdown_tables(content, [])

    def replace_near_table(pos: int, table_text: str) -> bool:
        if not table_spans:
            return False
        nearest = min(table_spans, key=lambda s: abs(s.start - pos))
        if abs(nearest.start - pos) > 400:
            return False
        nonlocal_content[0] = nonlocal_content[0][:nearest.start] + table_text + nonlocal_content[0][nearest.end:]
        return True

    nonlocal_content = [content]

    for token in tokens:
        content = nonlocal_content[0]
        if token.type == "formula":
            if token.inline:
                if token.text in content or normalize_inline(token.text) in content:
                    continue
            else:
                if token.text in content or normalize_display(token.text) in content:
                    continue
        elif token.text in content:
            continue

        word_idx = bisect_right(nougat_starts, token.start) - 1
        if word_idx < 0:
            word_idx = 0

        doc_idx = map_word_index(word_idx, blocks)
        if doc_idx is None or doc_idx >= len(docling_positions):
            continue

        insert_pos = docling_positions[doc_idx][1]
        if _overlaps(insert_pos, insert_pos + 1, tgt_spans):
            continue

        if token.type == "formula":
            if token.inline:
                insert_text = normalize_inline(token.text)
                before = content[insert_pos - 1] if insert_pos > 0 else ""
                after = content[insert_pos] if insert_pos < len(content) else ""
                if before and before.isalnum():
                    insert_text = " " + insert_text
                if after and after.isalnum():
                    insert_text = insert_text + " "
            else:
                insert_text = "\n\n" + normalize_display(token.text) + "\n\n"
        elif token.type == "latex_table":
            insert_text = "\n\n" + token.text.strip() + "\n\n"
        else:
            insert_text = "\n\n" + token.text.strip() + "\n\n"
        if token.type == "latex_table":
            if replace_near_table(insert_pos, insert_text):
                continue
        insertions.append((insert_pos, insert_text))

    content = nonlocal_content[0]
    for pos, insert_text in sorted(insertions, key=lambda x: x[0], reverse=True):
        content = content[:pos] + insert_text + content[pos:]

    return content


def context_words(text: str, start: int, end: int, n: int = 6) -> tuple[list[str], list[str]]:
    before_words = re.findall(r"[A-Za-z0-9]+", text[:start])
    after_words = re.findall(r"[A-Za-z0-9]+", text[end:])
    return before_words[-n:], after_words[:n]


def find_insertion_point(content: str, left_words: list[str], right_words: list[str], start_pos: int) -> int | None:
    if not left_words or not right_words:
        return None
    left_pattern = r"\b" + r"\W+".join(map(re.escape, left_words)) + r"\b"
    right_pattern = r"\b" + r"\W+".join(map(re.escape, right_words)) + r"\b"
    left_match = re.search(left_pattern, content[start_pos:], flags=re.IGNORECASE)
    if not left_match:
        return None
    search_start = start_pos + left_match.end()
    right_match = re.search(right_pattern, content[search_start:], flags=re.IGNORECASE)
    if not right_match:
        return None
    gap = right_match.start()
    if gap > 800:
        return None
    insert_pos = search_start + right_match.start()
    between = content[search_start:insert_pos]
    if STRUCTURED_RE.search(between):
        return None
    return insert_pos


def insert_tokens_by_context(content: str, tokens: list[Token], source_text: str) -> str:
    cursor = 0
    for token in tokens:
        if token.type == "formula":
            if token.inline:
                if token.text in content or normalize_inline(token.text) in content:
                    continue
            else:
                if token.text in content or normalize_display(token.text) in content:
                    continue
        elif token.text in content:
            continue
        left_words, right_words = context_words(source_text, token.start, token.end)
        insert_pos = find_insertion_point(content, left_words, right_words, cursor)
        if insert_pos is None:
            continue
        if token.type == "formula":
            if token.inline:
                insert_text = token.text
                before = content[insert_pos - 1] if insert_pos > 0 else ""
                after = content[insert_pos] if insert_pos < len(content) else ""
                if before and before.isalnum():
                    insert_text = " " + insert_text
                if after and after.isalnum():
                    insert_text = insert_text + " "
            else:
                insert_text = "\n\n" + normalize_display(token.text) + "\n\n"
        else:
            insert_text = "\n\n" + token.text.strip() + "\n\n"
        content = content[:insert_pos] + insert_text + content[insert_pos:]
        cursor = insert_pos + len(insert_text)
    return content


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract Markdown from a single PDF using Nougat-OCR + Docling and merge outputs."
    )
    parser.add_argument("pdf", type=Path, help="Path to a single PDF")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Root output directory")
    parser.add_argument("--nougat-cmd", help="Path to nougat executable")
    parser.add_argument("--docling-cmd", help="Path to docling executable")
    parser.add_argument(
        "--nougat-args",
        default="-m 0.1.0-base",
        help="Extra args passed to nougat (e.g., \"-m 0.1.0-base\").",
    )
    parser.add_argument(
        "--docling-args",
        default="",
        help="Extra args passed to docling (e.g., \"--device cpu --page-batch-size 1\").",
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Reuse existing text.mmd and figures.md; skip Nougat/Docling execution.",
    )
    parser.add_argument(
        "--normalize-math",
        action="store_true",
        help="Normalize \\[...\\] to $$...$$ and \\(...\\) to $...$ in combined.md.",
    )
    parser.add_argument(
        "--inline-figures",
        action="store_true",
        help="Use Docling Markdown as the base so figures stay inline; insert Nougat formulas/tables by alignment.",
    )
    parser.add_argument(
        "--to-latex",
        action="store_true",
        help="Generate combined_for_tex.md and combined.tex via Pandoc.",
    )
    parser.add_argument("--title", help="Title metadata for Pandoc/YAML front matter.")
    parser.add_argument("--author", help="Author metadata for Pandoc/YAML front matter.")
    parser.add_argument("--date", help="Date metadata for Pandoc/YAML front matter.")
    parser.add_argument("--pandoc-cmd", help="Path to pandoc executable")
    parser.add_argument("--keep-base64", action="store_true", help="Keep Docling base64 images in Markdown")
    args = parser.parse_args()

    pdf_path = args.pdf.expanduser().resolve()
    if not args.merge_only and not pdf_path.exists():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    out_root = args.output_dir.expanduser().resolve()
    job_dir = out_root / pdf_path.stem
    job_dir.mkdir(parents=True, exist_ok=True)

    text_md = job_dir / "text.mmd"
    figures_md = job_dir / "figures.md"
    combined_md = job_dir / "combined.md"

    if args.merge_only:
        if not text_md.exists():
            print(f"Missing required file for merge-only: {text_md}", file=sys.stderr)
            return 1
        if not figures_md.exists():
            print(f"Missing required file for merge-only: {figures_md}", file=sys.stderr)
            return 1
    else:
        nougat_cmd = require_command("nougat", args.nougat_cmd)
        docling_cmd = require_command("docling", args.docling_cmd)
        nougat_args = shlex.split(args.nougat_args) if args.nougat_args else []
        docling_args = shlex.split(args.docling_args) if args.docling_args else []

        print("Running Nougat-OCR...", file=sys.stderr)
        run_nougat(nougat_cmd, pdf_path, text_md, job_dir, nougat_args)

        print("Running Docling...", file=sys.stderr)
        run_docling(docling_cmd, pdf_path, figures_md, job_dir, docling_args)

    if args.keep_base64:
        base_path = figures_md
    else:
        figures_dir = job_dir / "figures"
        figures_decoded = job_dir / "figures_decoded.md"
        decode_docling_markdown(figures_md, figures_decoded, figures_dir)
        base_path = figures_decoded

    nougat_text = text_md.read_text(encoding="utf-8")
    figures_text = base_path.read_text(encoding="utf-8")
    if args.inline_figures:
        combined_text = figures_text.rstrip()
        tokens = extract_tokens(nougat_text)
        formula_tokens = [token for token in tokens if token.type == "formula"]
        combined_text, inserted = replace_placeholders_with_formulas(combined_text, formula_tokens)
        if inserted:
            remaining_tokens: list[Token] = []
            consumed = 0
            for token in tokens:
                if token.type == "formula" and consumed < inserted:
                    consumed += 1
                    continue
                remaining_tokens.append(token)
        else:
            remaining_tokens = tokens
        combined_text = insert_tokens_by_alignment(combined_text, remaining_tokens, nougat_text)
        combined_text = insert_tokens_by_context(combined_text, remaining_tokens, nougat_text)
    else:
        figure_blocks = extract_figure_blocks(figures_text)
        footnote_defs = extract_footnote_defs(figures_text)
        footnote_markers = extract_footnote_markers(figures_text, footnote_defs)

        combined_text = nougat_text.rstrip()
        used_footnotes: dict[str, str] = {}
        if footnote_markers:
            insertions: list[tuple[int, int, str, str]] = []
            for num, ctx in footnote_markers.items():
                if f"[^{num}]" in combined_text:
                    used_footnotes[num] = footnote_defs.get(num, "")
                    continue
                loc = find_replacement(combined_text, ctx, num)
                if loc is None:
                    continue
                start, end = loc
                marker = f"[^{num}]"
                if end < len(combined_text) and combined_text[end:end + 1].isalnum():
                    marker += " "
                insertions.append((start, end, marker, num))

            for start, end, marker, num in sorted(insertions, key=lambda x: x[0], reverse=True):
                combined_text = combined_text[:start] + marker + combined_text[end:]
                used_footnotes[num] = footnote_defs.get(num, "")
        if figure_blocks:
            combined_text = combined_text.rstrip() + "\n\n## Figures\n\n" + "\n\n".join(figure_blocks)
        if used_footnotes:
            ordered = sorted(used_footnotes.items(), key=lambda x: int(x[0]))
            defs = [f"[^{num}]: {body}".strip() for num, body in ordered if body]
            if defs:
                combined_text = combined_text.rstrip() + "\n\n" + "\n\n".join(defs)
        if footnote_defs:
            unplaced = [
                footnote_defs[num]
                for num in sorted(footnote_defs, key=lambda x: int(x))
                if num not in used_footnotes
            ]
            if unplaced:
                combined_text = combined_text.rstrip() + "\n\n## Footnotes (Unplaced)\n\n" + "\n\n".join(unplaced)
    if args.normalize_math:
        combined_text = normalize_bracket_math(combined_text)
        combined_text = normalize_inline_math(combined_text)

    metadata_block = build_yaml_metadata(args.title, args.author, args.date)
    if metadata_block:
        combined_text = metadata_block + combined_text.lstrip()

    combined_text = combined_text.rstrip() + "\n"
    combined_md.write_text(combined_text, encoding="utf-8")
    if args.to_latex:
        combined_for_tex = job_dir / "combined_for_tex.md"
        combined_tex = job_dir / "combined.tex"
        cleaned = fix_fences(combined_text)
        combined_for_tex.write_text(cleaned, encoding="utf-8")
        pandoc_cmd = require_command("pandoc", args.pandoc_cmd)
        subprocess.run(
            [
                pandoc_cmd,
                str(combined_for_tex),
                "-s",
                "--from",
                "markdown+tex_math_dollars+tex_math_single_backslash",
                "-o",
                str(combined_tex),
            ],
            check=True,
        )
        latex_text = combined_tex.read_text(encoding="utf-8", errors="replace")
        combined_tex.write_text(postprocess_latex(latex_text), encoding="utf-8")
    print(f"Wrote merged Markdown to {combined_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
