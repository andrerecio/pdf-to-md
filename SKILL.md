---
name: pdf-to-md
description: Extract structured Markdown from a single research PDF, preserving equations and tables via Nougat-OCR and figures via Docling; use when converting PDFs to Markdown with math, tables, and figure assets or when combining Nougat text with Docling figures.
---

# Pdf To Md

## Overview
Use Nougat-OCR (base model by default) for text, math, tables, and verbatim blocks and Docling for figures + footnotes. By default, figures are appended to the Nougat Markdown and Docling footnotes are inserted inline; use `--inline-figures` to keep figures in their original positions and blend in Nougat math/tables (Docling footnotes are left as-is). Math normalization is optional.

## Workflow
1. Check dependencies: run `~/.venvs/jupyter/bin/python scripts/check_deps.py` (use `--nougat-cmd`/`--docling-cmd` if needed).
2. Extract and merge: run `~/.venvs/jupyter/bin/python scripts/extract_pdf_to_md.py <path/to.pdf>` (use `--nougat-cmd`/`--docling-cmd` if needed; on macOS start with `--docling-args "--device cpu --page-batch-size 1"` and only add `--pipeline legacy` if the standard pipeline fails). Add `--inline-figures` to keep figures inline. Plan for Nougat to run up to 60+ minutes; set any orchestration timeouts to at least 60 minutes. If running via an agent and no timeout was specified, ask the user which timeout to use (recommend 60+ minutes).
   - If you run it directly in your terminal, you don’t need to do anything — it will run until completion.
   - If you run it via an agent/automation runner, that runner may have its own timeout. In that case:
     - In this Codex CLI chat: if you ask me to run it, I’ll set the tool timeout to ≥ 60 minutes (e.g., 3,600,000 ms).
     - In Cursor / task runners / scripts: set the command timeout to 60+ minutes (or disable timeouts).
     - Avoid wrapping with a short `timeout` command; or set it to at least 3600 seconds.
3. Review outputs in `outputs/<pdf-stem>/`.
4. Optional LaTeX conversion:
   - One-shot: add `--to-latex` (optionally `--pandoc-cmd`) to the extract command (moves figures/tables inline and injects `\caption{}` in the LaTeX).
   - Manual: `~/.venvs/jupyter/bin/python scripts/prepare_md_for_latex.py outputs/<stem>/combined.md`
   - Manual: `pandoc outputs/<stem>/combined_for_tex.md -s --from markdown+tex_math_dollars+tex_math_single_backslash -o outputs/<stem>/combined.tex`

## Command example
```bash
~/.venvs/jupyter/bin/python scripts/extract_pdf_to_md.py notes_rbc_quant_sp2024.pdf --output-dir outputs
~/.venvs/jupyter/bin/python scripts/extract_pdf_to_md.py notes_rbc_quant_sp2024.pdf --output-dir outputs --inline-figures
```

## Output layout
- `outputs/<stem>/text.mmd` (Nougat)
- `outputs/<stem>/figures.md` (Docling raw)
- `outputs/<stem>/figures/` (decoded image files)
- `outputs/<stem>/figures_decoded.md`
- `outputs/<stem>/combined.md` (Nougat base text + Docling figures appended; footnotes inserted inline unless `--inline-figures` is used, which keeps Docling footnotes as-is)

## Options
- `--keep-base64` keep Docling base64 images in Markdown (skip decoding).
- `--merge-only` skip Nougat/Docling runs and reuse existing `text.mmd` + `figures.md`.
- `--normalize-math` normalize `\(...\)` to `$...$` and `\[...\]` to `$$...$$`.
- `--inline-figures` use Docling Markdown as the base so figures stay inline; Nougat math/tables are inserted by alignment.
- `--to-latex` generate `combined_for_tex.md` and `combined.tex` via Pandoc.
- `--title` set Pandoc/YAML title metadata.
- `--author` set Pandoc/YAML author metadata.
- `--date` set Pandoc/YAML date metadata.
- `--pandoc-cmd` explicit path to the Pandoc executable (used with `--to-latex`).
- `--nougat-cmd` explicit path to the Nougat executable.
- `--nougat-args` extra arguments passed to the Nougat CLI (defaults to `"-m 0.1.0-base"`).
- `--docling-cmd` explicit path to the Docling executable.
- `--docling-args` extra arguments passed to the Docling CLI (use for `--device`, `--page-batch-size`, `--pipeline`, etc.).

## Troubleshooting
- Docling RT-DETR padding errors (batched image sizes): re-run with `--docling-args "--device cpu --page-batch-size 1"`.
- If Docling still fails, add `--pipeline legacy`, but note this can reduce figure extraction.
- Docling NumPy 2.x/Torch mismatch: in the Docling venv run `pip install "numpy<2" "opencv-python==4.8.1.78"`.
- Nougat OpenMP SHM crash on macOS (e.g., `OMP: Error #179 ... SHM2` followed by SIGABRT): run with `KMP_SHM_DISABLE=1 OMP_NUM_THREADS=1` in the environment.

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
- See `EXPORT_AND_SETUP.md` for Cursor skills installation and sync helper.
