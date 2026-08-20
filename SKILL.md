---
name: pdf-to-md
description: Extract structured Markdown from one research PDF using Nougat-OCR for text, math, and tables and Docling for figures, footnotes, and layout.
---

# Pdf To Md

## Purpose

Use this skill when a PDF must be converted to Markdown while preserving
equations, tables, figure assets, and footnotes. The pipeline runs Nougat and
Docling in isolated environments, then merges their outputs. Nougat is the
canonical source for the final document body: prose, headings, equations, and
tables come from Nougat for both figure-placement modes. Docling supplies
figures, captions, and footnote/layout evidence to the merge step.

## Quick workflow

1. Before asking the user to install anything or proceeding with installation,
   check whether Nougat and Docling are already available. Check commands on
   `PATH` and inspect any dedicated or existing virtual environments, including
   the runtime paths configured for this skill. Validate each discovered
   installation by invoking its executable or environment with a version/help
   or diagnostic command; reuse a working installation instead of provisioning
   a duplicate.
2. Provision the runtime once by following INSTALL.md only for tools that are
   not already installed and usable.
3. Run the diagnostic command and pass explicit tool paths when the tools are
   not on PATH.
4. Choose a required profile:
   - fast uses Nougat small with conservative batch settings.
   - quality uses Nougat base for higher-quality academic extraction.
5. Run extraction with --resume for stage-level caching.
6. Review combined.md, figures/, and merge_report.json in the generated hashed
   job directory.

Example:

    python3 scripts/check_deps.py \
      --nougat-cmd /path/to/runtime/nougat/bin/nougat \
      --docling-cmd /path/to/runtime/docling/bin/docling

    python3 scripts/extract_pdf_to_md.py /path/to/paper.pdf \
      --profile fast \
      --output-dir outputs \
      --nougat-cmd /path/to/runtime/nougat/bin/nougat \
      --docling-cmd /path/to/runtime/docling/bin/docling \
      --resume

Use --profile quality for the base model. Appended figures are the default.
Use --figure-placement inline only when figures should be placed near their
source. Inline placement uses monotonic text anchors and appends an ambiguous
or low-confidence figure under **Unplaced Figures** with a warning in
merge_report.json. Use --force to recompute cached stages, and
--parallel-stages only when the host has enough resources to run both models.
For a shareable, placeholder-based example covering dependency checks,
conversion, report review, and PDF compilation, see the
[complete POSIX workflow template](INSTALL.md#complete-posix-workflow-template).

## Outputs

Each PDF gets a directory named <safe-stem>-<content-hash> containing:

    nougat.mmd
    docling.md
    docling_assets/
    docling_decoded.md
    figures/
    combined.md
    merge_report.json
    manifest.json
    timings.json

Optional LaTeX output is created with --to-latex when Pandoc is installed.

## Important behavior

- Nougat and Docling are invoked once per uncached stage using their output
  directory interfaces. Changing placement, math normalization, metadata, or
  LaTeX generation does not rerun OCR.
- Dependency discovery always precedes installation: check PATH and dedicated
  virtual environments first, and reuse any validated Nougat or Docling
  installation. Do not ask the user to install or create a new environment
  until those checks show that a usable installation is unavailable.
- The manifest records the PDF hash, profile, arguments, tool versions, runtime,
  and completed stages.
- Docling referenced image export is the default. The runner retries with
  embedded images when the installed Docling version cannot export references.
- Every local figure is copied into the job. Normalized Docling Markdown uses
  durable relative links under `docling_assets/`; decoded and final Markdown
  uses canonical links such as `figures/figure-001.png`. No final Markdown may
  contain absolute paths or `.staging/` paths. `docling_assets/` retains the
  normalized Docling assets for cache reuse.
- `--resume` repairs and re-normalizes valid cached Docling output before
  merging. `--merge-only` performs the same merge/asset repair from an existing
  hashed job without invoking Nougat or Docling, so a long OCR run need not be
  repeated.
- `merge_report.json` (merge schema 3) records figure placement, fallback
  warnings, footnote reconstruction, and asset/Markdown validation. Review it
  alongside combined.md when accepting a conversion.
- Before LaTeX output is written, the runner checks for unresolved local assets,
  staging paths, formula placeholders, and unsupported raw Unicode for the
  documented pdfLaTeX route. Pandoc is run with the job directory and its
  `figures/` and `docling_assets/` directories as resource paths.
- --nougat-arg and --docling-arg are repeatable and avoid shell-specific
  argument quoting.

## References

- INSTALL.md: cross-platform installation, runtime provisioning, and updates.
- references/workflow.md: end-to-end usage and recovery.
- references/io-spec.md: output contract and cache semantics.
- references/tooling.md: tested constraints and hardware notes.
