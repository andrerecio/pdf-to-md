# Workflow

## First run

1. Follow INSTALL.md and provision separate Nougat and Docling environments.
2. Run scripts/check_deps.py with explicit executable paths if the environments
   are not activated.
3. Choose --profile fast or --profile quality.
4. Run scripts/extract_pdf_to_md.py with --resume.
5. Review combined.md, figures/, merge_report.json, manifest.json, and
   timings.json.

The default `--figure-placement appended` mode keeps Nougat's complete body
and adds each normalized Docling figure once under `## Figures`. Nougat is
also the body source when `--figure-placement inline` is selected; inline
placement only inserts figure blocks at monotonic Nougat paragraph anchors.
Docling prose, tables, and formulas are never transplanted into the body.

## Repeat runs

--resume reuses a stage only when its PDF hash, profile, arguments, tool path,
and tool version match the manifest. If a stage is missing or stale, only that
stage is rerun. --force invalidates both external stages.

Changing figure placement, math normalization, metadata, or LaTeX options does
not require OCR reruns; rerun the merge command with --resume.

When a job already has valid external stages, use the same PDF, profile, and
output directory with `--merge-only` to rebuild Markdown and repair cached
assets without invoking either OCR tool. `--resume` performs this merge-time
normalization as part of a normal run. Both paths rewrite local Docling image
references to durable relative links and remove stale `.staging/` paths.

For example:

    python3 scripts/extract_pdf_to_md.py /path/to/paper.pdf \
      --profile fast --output-dir outputs \
      --merge-only --figure-placement appended

## Performance guidance

- Use fast for routine conversions and quality for documents where extraction
  fidelity matters more than runtime.
- Referenced Docling images avoid storing large base64 strings in Markdown.
- Keep stages serial unless the machine has enough memory for both models.
- Use --parallel-stages only after measuring the host; GPU memory contention can
  make concurrent execution slower or fail.
- Use timings.json to compare model, merge, and image-decoding costs.
- Use merge_report.json to compare placed and unplaced figures, fallback
  warnings, reconstructed footnotes, and validation failures. A clean report
  contains no unresolved local assets, absolute paths, `.staging/` references,
  or formula placeholders.

## Recovery

- If Docling cannot export referenced images, the runner retries with embedded
  images. You can force the fallback with --image-mode embedded.
- If Nougat emits many [MISSING_PAGE] markers, pass
  --nougat-arg=--no-skipping.
- If a run is interrupted, rerun with --resume. Partial stage directories are
  discarded before a retry and are never treated as valid cache entries.
- If inline matching is ambiguous, the affected figure is emitted once under
  `## Unplaced Figures` and the report explains the fallback; inspect that
  section before accepting the result.
- For LaTeX, use --to-latex. Pandoc runs from the hashed job directory with
  the job, `figures/`, and `docling_assets/` as resource paths. Preflight
  rejects unresolved assets, staging paths, formula placeholders, and raw
  Unicode unsupported by the documented pdfLaTeX route. Compile from that
  directory with:

      latexmk -pdf -halt-on-error -file-line-error combined.tex
