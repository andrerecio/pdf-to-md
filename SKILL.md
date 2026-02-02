---
name: pdf-to-md
description: Extract structured Markdown from a single research PDF, preserving equations and tables via Nougat-OCR and figures via Docling; use when converting PDFs to Markdown with math, tables, and figure assets or when combining Nougat text with Docling figures.
---

# Pdf To Md

## Overview
Use Nougat-OCR (base model by default) for text, math, tables, and verbatim blocks and Docling for figures + footnotes, then append figures and insert footnotes inline in the Nougat Markdown (unplaced footnotes are listed at the end). Math normalization is optional.

## Workflow
1. Check dependencies: run `~/.venvs/jupyter/bin/python scripts/check_deps.py` (use `--nougat-cmd`/`--docling-cmd` if needed).
2. Extract and merge: run `~/.venvs/jupyter/bin/python scripts/extract_pdf_to_md.py <path/to.pdf>` (use `--nougat-cmd`/`--docling-cmd` if needed).
3. Review outputs in `outputs/<pdf-stem>/`.
4. Optional LaTeX conversion:
   - One-shot: add `--to-latex` (optionally `--pandoc-cmd`) to the extract command (moves figures/tables inline and injects `\caption{}` in the LaTeX).
   - Manual: `~/.venvs/jupyter/bin/python scripts/prepare_md_for_latex.py outputs/<stem>/combined.md`
   - Manual: `pandoc outputs/<stem>/combined_for_tex.md -s --from markdown+tex_math_dollars+tex_math_single_backslash -o outputs/<stem>/combined.tex`

## Command example
```bash
~/.venvs/jupyter/bin/python scripts/extract_pdf_to_md.py notes_rbc_quant_sp2024.pdf --output-dir outputs
```

## Output layout
- `outputs/<stem>/text.mmd` (Nougat)
- `outputs/<stem>/figures.md` (Docling raw)
- `outputs/<stem>/figures/` (decoded image files)
- `outputs/<stem>/figures_decoded.md`
- `outputs/<stem>/combined.md` (Nougat base text + Docling figures appended; footnotes inserted inline)

## Options
- `--keep-base64` keep Docling base64 images in Markdown (skip decoding).
- `--merge-only` skip Nougat/Docling runs and reuse existing `text.mmd` + `figures.md`.
- `--normalize-math` normalize `\(...\)` to `$...$` and `\[...\]` to `$$...$$`.
- `--to-latex` generate `combined_for_tex.md` and `combined.tex` via Pandoc.
- `--pandoc-cmd` explicit path to the Pandoc executable (used with `--to-latex`).
- `--nougat-cmd` explicit path to the Nougat executable.
- `--nougat-args` extra arguments passed to the Nougat CLI (defaults to `"-m 0.1.0-base"`).
- `--docling-cmd` explicit path to the Docling executable.

## Portability (install once per machine)
Option A: Copy

1. `git clone <your-repo-url> ~/dev/pdf-to-md-skill`
2. `mkdir -p $CODEX_HOME/skills`
3. `cp -R ~/dev/pdf-to-md-skill $CODEX_HOME/skills/pdf-to-md`

Option B: Symlink (keeps updates in sync)

1. `git clone <your-repo-url> ~/dev/pdf-to-md-skill`
2. `mkdir -p $CODEX_HOME/skills`
3. `ln -s ~/dev/pdf-to-md-skill $CODEX_HOME/skills/pdf-to-md`

## References
- See `references/workflow.md` for detailed pipeline steps and failure modes.
- See `references/tooling.md` for installation and CLI notes.
- See `references/io-spec.md` for I/O contract details.
- See `EXPORT_AND_SETUP.md` for cross-machine install, portability, and venv setup.
