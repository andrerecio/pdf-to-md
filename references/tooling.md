# Tooling Notes

## Installation (from the Nougat/Docling workflow)
- Nougat-OCR:
  - `uv tool install nougat-ocr --python 3.12 --with transformers==4.38.2`
- Docling:
  - `uv tool install docling --python 3.12`

## Dedicated venvs (recommended)
- Create separate venvs to avoid dependency conflicts:
  - `~/.venvs/jupyter/bin/python -m venv /path/to/venvs/nougat`
  - `~/.venvs/jupyter/bin/python -m venv /path/to/venvs/docling`
- Install Nougat with pinned versions (Nougat venv):
  - `venvs/nougat/bin/python -m pip install "nougat-ocr==0.1.17" "transformers==4.38.2" "tokenizers==0.15.2" "albumentations==1.3.1" "pypdfium2==4.30.0"`
- Install Docling in its own venv:
  - `venvs/docling/bin/python -m pip install docling`
  - If Torch/Docling complains about NumPy 2.x (common on macOS), pin:
    - `venvs/docling/bin/python -m pip install "numpy<2" "opencv-python==4.8.1.78"`

## CLI usage
- Nougat (stdout):
  - `nougat input.pdf > output.mmd`
- Nougat (output directory):
  - `nougat input.pdf --markdown --out /path/to/output_dir`
- Nougat (base model):
  - `nougat -m 0.1.0-base input.pdf --markdown --out /path/to/output_dir`
- Nougat (small model):
  - `nougat -m 0.1.0-small input.pdf --markdown --out /path/to/output_dir`
- Docling:
  - `docling --to md --image-export-mode embedded --output /path/to/output_dir input.pdf`
  - Output will be written as `/path/to/output_dir/<stem>.md`
  - If RT-DETR padding errors appear, retry with:
    - `docling --device cpu --page-batch-size 1 --to md --image-export-mode embedded --output /path/to/output_dir input.pdf`
  - If that still fails, add `--pipeline legacy`, but note this can reduce figure extraction.

## Performance
- Both tools benefit from GPU acceleration, but CPU-only runs are supported.

## Optional: Markdown to LaTeX
- Pandoc:
  - `pandoc combined_for_tex.md -s --from markdown+tex_math_dollars+tex_math_single_backslash -o combined.tex`
- One-shot (uses Pandoc):
  - `~/.venvs/jupyter/bin/python scripts/extract_pdf_to_md.py input.pdf --output-dir outputs --to-latex`
  - Add `--title`, `--author`, and `--date` to inject YAML metadata for Pandoc.

## Inline figures
- To keep figures inline, pass `--inline-figures` to `scripts/extract_pdf_to_md.py`; this uses Docling Markdown as the base and inserts Nougat math/tables by alignment.

## Skill portability (install once per machine)
Option A: Copy

1. `git clone <your-repo-url> ~/dev/pdf-to-md-skill`
2. `mkdir -p $CODEX_HOME/skills`
3. `cp -R ~/dev/pdf-to-md-skill $CODEX_HOME/skills/pdf-to-md`

Option B: Symlink (keeps updates in sync)

1. `git clone <your-repo-url> ~/dev/pdf-to-md-skill`
2. `mkdir -p $CODEX_HOME/skills`
3. `ln -s ~/dev/pdf-to-md-skill $CODEX_HOME/skills/pdf-to-md`
