---
name: pdf-to-md
description: Extract structured Markdown from one research PDF using Nougat-OCR for the document body and Docling for figures, footnotes, layout, and conservative code-block repair.
---

# Pdf To Md

## Purpose

Use this skill when a PDF must be converted to Markdown while preserving
equations, tables, figure assets, and footnotes. The pipeline runs Nougat and
Docling in isolated environments, then merges their outputs. Nougat is the
canonical source for prose, headings, equations, and tables in the final body.
Docling supplies figures, captions, footnote/layout evidence, and page-ordered
code text. The merger replaces a Nougat code fence only when the surrounding
anchors and printed line-number sequence identify one unique listing.

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
6. Review `<safe-stem>.md`, `figures/`, `merge_report.json`, and the OCR-audit
   report in the generated hashed job directory.

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
    docling_code.json
    docling_assets/
    docling_decoded.md
    figures/
    <safe-stem>.md
    merge_report.json
    ocr_audit.json
    ocr_audit.md
    ocr_audit_review.json
    manifest.json
    timings.json

With `--to-latex`, the directory also contains `<safe-stem>_for_tex.md` and
`<safe-stem>.tex`.

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
- Docling exports Markdown and JSON in the same invocation. The runner derives
  `docling_code.json` from the JSON without code enrichment. Confidently
  aligned numbered listings are reflowed into plain balanced fences across
  consecutive pages; ambiguous or flattened evidence remains Nougat text.
- Every local figure is copied into the job. Normalized Docling Markdown uses
  durable relative links under `docling_assets/`; decoded and final Markdown
  uses canonical links such as `figures/figure-001.png`. No final Markdown may
  contain absolute paths or `.staging/` paths. `docling_assets/` retains the
  normalized Docling assets for cache reuse.
- `--resume` repairs and re-normalizes valid cached Docling output before
  merging. A legacy cached job without `docling_code.json` reruns Docling only.
  `--merge-only` never invokes Docling; when that sidecar is unavailable it
  retains Nougat code and records a warning.
- A post-extraction OCR fidelity audit runs after structural validation by
  default. It uses the PDF text layer and character boxes plus cached Docling
  caption/footnote evidence; it never edits content or starts another OCR
  pass. Use `--skip-ocr-audit` only when the check is intentionally disabled.
- `ocr_audit.json` (audit schema 1) records clear/review-required status,
  per-page coverage, bounded substitutions, confidence, snippets, context, and
  coverage limitations. `ocr_audit.md` is the concise review view, and
  `ocr_audit_review.json` preserves human classifications across merge-only
  reruns.
- `merge_report.json` (merge schema 5) records per-code-block status, page and
  line ranges, replacement counts and fallback reasons, plus figure placement,
  footnote reconstruction, structural validation, and an OCR-audit summary.
  Structural `validation.ok` remains independent of nonfatal audit findings.
- Review every active audit finding against the indicated PDF page or bounding
  box. If the PDF disagrees, repair the source artifact—normally `nougat.mmd`,
  or `docling.md` for an inserted caption/footnote. If it agrees, classify it
  as `source_matches` or `false_positive` with the resolver in
  `scripts/audit_ocr.py`; use `confirmed_extraction_error` for a finding that
  was visually confirmed and repaired. Batch confirmed corrections, then rerun
  with `--merge-only` and the original merge/LaTeX options. Finish when no
  active findings remain, while reporting any `full`, `partial`, or
  `unavailable` coverage limitations.
- Before LaTeX output is written, the runner checks for unresolved local assets,
  staging paths, formula placeholders, and unsupported raw Unicode for the
  documented pdfLaTeX route, including code blocks. Intentional `∆` is covered
  by an explicit pdfLaTeX declaration. Pandoc is run with the job directory and
  its `figures/` and `docling_assets/` directories as resource paths; preserved
  fences become genuine `verbatim` environments.
- --nougat-arg and --docling-arg are repeatable and avoid shell-specific
  argument quoting.

## References

- INSTALL.md: cross-platform installation, runtime provisioning, and updates.
- references/workflow.md: end-to-end usage and recovery.
- references/io-spec.md: output contract and cache semantics.
- references/tooling.md: tested constraints and hardware notes.
