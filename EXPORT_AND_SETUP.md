# Pdf-to-md Skill Export and Setup

## 1) Export the skill on the source machine

1. Locate the skill folder:
   - `~/.codex/skills/pdf-to-md`

2. Package the skill into a `.skill` file:
   - `~/.venvs/jupyter/bin/python ~/.codex/skills/.system/skill-creator/scripts/package_skill.py ~/.codex/skills/pdf-to-md ./dist`

3. Copy the generated file to the new machine:
   - `./dist/pdf-to-md.skill`

## 2) Install the skill on the new machine

1. Create a skills directory if it does not exist:
   - `mkdir -p $CODEX_HOME/skills`

2. Unpack the `.skill` file into the skills directory:
   - `unzip pdf-to-md.skill -d $CODEX_HOME/skills/pdf-to-md`

3. Verify the skill folder:
   - `$CODEX_HOME/skills/pdf-to-md/SKILL.md`

## 2b) Install globally from a GitHub repo (recommended)

This keeps the skill versioned and available on the whole machine.

Option A: Copy (simple)

1. Clone your repo anywhere:
   - `git clone <your-repo-url> ~/dev/pdf-to-md-skill`

2. Copy the skill folder into Codex:
   - `mkdir -p $CODEX_HOME/skills`
   - `cp -R ~/dev/pdf-to-md-skill $CODEX_HOME/skills/pdf-to-md`

Option B: Symlink (best for staying in sync)

1. Clone your repo once:
   - `git clone <your-repo-url> ~/dev/pdf-to-md-skill`

2. Symlink into Codex:
   - `mkdir -p $CODEX_HOME/skills`
   - `ln -s ~/dev/pdf-to-md-skill $CODEX_HOME/skills/pdf-to-md`

3. Verify:
   - `$CODEX_HOME/skills/pdf-to-md/SKILL.md`

## 3) Create dedicated venvs (recommended)

Use the same interpreter that was used here:
- `~/.venvs/jupyter/bin/python`

Create two isolated venvs for dependency stability:

- `~/.venvs/jupyter/bin/python -m venv /path/to/venvs/nougat`
- `~/.venvs/jupyter/bin/python -m venv /path/to/venvs/docling`

Upgrade pip in both:

- `/path/to/venvs/nougat/bin/python -m pip install --upgrade pip`
- `/path/to/venvs/docling/bin/python -m pip install --upgrade pip`

## 4) Install Nougat in its venv (pinned versions)

Install the same versions used in this setup:

- `/path/to/venvs/nougat/bin/python -m pip install \
  "nougat-ocr==0.1.17" \
  "transformers==4.38.2" \
  "tokenizers==0.15.2" \
  "albumentations==1.3.1" \
  "pypdfium2==4.30.0" \
  "numpy==1.26.4" \
  "opencv-python-headless==4.8.1.78"`

## 5) Install Docling in its venv

- `/path/to/venvs/docling/bin/python -m pip install docling`

## 6) Run the skill pipeline

1. Check dependencies (explicit CLI paths):
   - `~/.venvs/jupyter/bin/python $CODEX_HOME/skills/pdf-to-md/scripts/check_deps.py \
     --nougat-cmd /path/to/venvs/nougat/bin/nougat \
     --docling-cmd /path/to/venvs/docling/bin/docling`

2. Run extraction:
   - `~/.venvs/jupyter/bin/python $CODEX_HOME/skills/pdf-to-md/scripts/extract_pdf_to_md.py /path/to/file.pdf \
     --output-dir outputs \
     --nougat-cmd /path/to/venvs/nougat/bin/nougat \
     --docling-cmd /path/to/venvs/docling/bin/docling`
   - Optional: add `--normalize-math` to convert `\(...\)`/`\[...\]` to `$...$`/`$$...$$`.
   - Optional: use `--merge-only` to reuse existing `text.mmd` and `figures.md` without re-running Nougat/Docling.

3. Final output:
   - `outputs/<pdf-stem>/combined.md`

## 7) Convert Markdown to LaTeX (optional)

1. Clean up code fences (helps Pandoc render verbatim blocks correctly):
   - `~/.venvs/jupyter/bin/python $CODEX_HOME/skills/pdf-to-md/scripts/prepare_md_for_latex.py outputs/<stem>/combined.md`

2. Convert to LaTeX with Pandoc:
   - `pandoc outputs/<stem>/combined_for_tex.md -s --from markdown+tex_math_dollars+tex_math_single_backslash -o outputs/<stem>/combined.tex`

Or use the one-shot flag (also inlines figures/tables and adds `\caption{}` in LaTeX):
- `~/.venvs/jupyter/bin/python $CODEX_HOME/skills/pdf-to-md/scripts/extract_pdf_to_md.py /path/to/file.pdf \
  --output-dir outputs \
  --to-latex`

## 8) Nougat model selection

Nougat supports `--model` and `--checkpoint`. This skill defaults to the base model (`-m 0.1.0-base`). To use the small model instead, pass `--nougat-args "-m 0.1.0-small"`.

### Option A: Run Nougat directly (ad-hoc)

- `/path/to/venvs/nougat/bin/nougat /path/to/file.pdf -o /tmp/nougat_out -m 0.1.0-base --markdown`

### Option B: Use the base model inside the skill pipeline (wrapper)

Create a tiny wrapper script and point `--nougat-cmd` to it:

```bash
#!/usr/bin/env bash
exec /path/to/venvs/nougat/bin/nougat -m 0.1.0-base "$@"
```

Then:
- `chmod +x /path/to/nougat_base`
- `~/.venvs/jupyter/bin/python $CODEX_HOME/skills/pdf-to-md/scripts/extract_pdf_to_md.py /path/to/file.pdf \
  --output-dir outputs \
  --nougat-cmd /path/to/nougat_base \
  --docling-cmd /path/to/venvs/docling/bin/docling`

### Option C: Pass `--nougat-args` (no wrapper script)

- `~/.venvs/jupyter/bin/python $CODEX_HOME/skills/pdf-to-md/scripts/extract_pdf_to_md.py /path/to/file.pdf \
  --output-dir outputs \
  --nougat-cmd /path/to/venvs/nougat/bin/nougat \
  --nougat-args "-m 0.1.0-base" \
  --docling-cmd /path/to/venvs/docling/bin/docling`

### Option D: Use the small model inside the skill pipeline

- `~/.venvs/jupyter/bin/python $CODEX_HOME/skills/pdf-to-md/scripts/extract_pdf_to_md.py /path/to/file.pdf \
  --output-dir outputs \
  --nougat-cmd /path/to/venvs/nougat/bin/nougat \
  --nougat-args "-m 0.1.0-small" \
  --docling-cmd /path/to/venvs/docling/bin/docling`

## Troubleshooting

- If you see a lot of `[MISSING_PAGE]` in Nougat output, rerun with `--no-skipping` (add it to the wrapper script if using the skill pipeline).
- If the Nougat CLI is not found, re-check `--nougat-cmd` and make sure the venv path is correct.
- If Docling does not produce a Markdown file, confirm you passed `--docling-cmd` and that the output directory is writable.

## Notes

- The skill uses Nougat for text/math/tables and appends Docling figure blocks under a `## Figures` section. Docling footnotes are inserted inline as Markdown footnotes; any unplaced footnotes are appended under `## Footnotes (Unplaced)`.
- Math normalization only happens when `--normalize-math` is used.
- If you prefer base64 images in Markdown, pass `--keep-base64` to the extraction script.
