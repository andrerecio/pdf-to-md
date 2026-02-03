# Workflow

1. Run `~/.venvs/jupyter/bin/python scripts/check_deps.py` to confirm Nougat-OCR and Docling are available.
   - If using dedicated venvs, pass `--nougat-cmd /path/to/nougat` and `--docling-cmd /path/to/docling`.
2. Run `~/.venvs/jupyter/bin/python scripts/extract_pdf_to_md.py <pdf> --output-dir outputs`.
   - Add `--nougat-cmd` and `--docling-cmd` when CLIs are not on PATH.
   - `--nougat-args` defaults to `"-m 0.1.0-base"`; override it to change the model.
   - `--docling-args` lets you pass flags like `--device cpu --page-batch-size 1` (useful for macOS or RT-DETR padding errors). Use `--pipeline legacy` only as a fallback; it can reduce figure extraction.
   - Use `--merge-only` to reuse existing `text.mmd` and `figures.md` without re-running OCR/Docling (the PDF itself does not need to exist; its stem is used to locate outputs).
   - Add `--normalize-math` if you want `\(...\)` and `\[...\]` converted to `$...$` and `$$...$$`.
   - Add `--inline-figures` to use Docling Markdown as the base so figures remain inline.
   - Add `--title`, `--author`, and `--date` to inject YAML metadata for Pandoc.
   - Expect Nougat to run up to 60+ minutes; configure any orchestrator timeout to at least 60 minutes. If invoking via an agent and no timeout is specified, ask the user which timeout to use (recommend 60+ minutes).
   - If you run it directly in your terminal, you don’t need to do anything — it will run until completion.
   - If you run it via an agent/automation runner, that runner may have its own timeout. In that case:
     - In this Codex CLI chat: if you ask me to run it, I’ll set the tool timeout to ≥ 60 minutes (e.g., 3,600,000 ms).
     - In Cursor / task runners / scripts: set the command timeout to 60+ minutes (or disable timeouts).
     - Avoid wrapping with a short `timeout` command; or set it to at least 3600 seconds.
3. The script runs Nougat first (base model by default) to extract text/math/tables, then runs Docling to extract figures and footnotes.
4. `combined.md` is based on the Nougat Markdown with Docling figure blocks appended at the end under a `## Figures` section. Docling footnotes are inserted inline as Markdown footnotes; any unplaced footnotes are listed under `## Footnotes (Unplaced)` at the end.
   - If `--inline-figures` is set, `combined.md` starts from Docling Markdown (figures inline) and then inserts Nougat formulas/tables by alignment. Docling footnotes remain as-is in this mode.
5. If `--normalize-math` is set, the script converts `\\[ ... \\]` to `$$ ... $$` and `\\( ... \\)` to `$ ... $`.
6. Review `outputs/<stem>/combined.md` and the figures directory.
7. Optional LaTeX conversion:
   - One-shot: re-run extraction with `--to-latex` (optionally `--pandoc-cmd`); this post-processes LaTeX to move figures/tables inline and add `\caption{}`.
   - `~/.venvs/jupyter/bin/python scripts/prepare_md_for_latex.py outputs/<stem>/combined.md`
   - `pandoc outputs/<stem>/combined_for_tex.md -s --from markdown+tex_math_dollars+tex_math_single_backslash -o outputs/<stem>/combined.tex`

## Portability (install once per machine)
Option A: Copy

1. `git clone <your-repo-url> ~/dev/pdf-to-md-skill`
2. `mkdir -p $CODEX_HOME/skills`
3. `cp -R ~/dev/pdf-to-md-skill $CODEX_HOME/skills/pdf-to-md`

Option B: Symlink (keeps updates in sync)

1. `git clone <your-repo-url> ~/dev/pdf-to-md-skill`
2. `mkdir -p $CODEX_HOME/skills`
3. `ln -s ~/dev/pdf-to-md-skill $CODEX_HOME/skills/pdf-to-md`

## Notes
- Figures are appended at the end by default. Use `--inline-figures` to keep them inline; manual reordering is no longer required.
- If Docling outputs base64 images, the script decodes them to `figures/` and rewrites Markdown paths unless `--keep-base64` is set.
- GPU acceleration can significantly reduce runtime for both tools; CPU-only runs are supported but slower.
- If Nougat crashes on macOS with OpenMP shared-memory errors, run with `KMP_SHM_DISABLE=1 OMP_NUM_THREADS=1`.
