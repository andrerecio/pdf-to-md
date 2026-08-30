# I/O contract

## Input

The pipeline accepts one local PDF path. The file is hashed before external
processing so identical content gets the same job directory even when the
source path changes.

## Output tree

    outputs/
      <safe-stem>-<sha256-prefix>/
        nougat.mmd
        docling.md
        docling_assets/
        docling_decoded.md
        figures/
          figure-001.png
        combined.md
        merge_report.json
        ocr_audit.json
        ocr_audit.md
        ocr_audit_review.json
        manifest.json
        timings.json
        combined_for_tex.md
        combined.tex

The LaTeX files are optional and appear only when --to-latex is used.

## Semantics

- `nougat.mmd` is the canonical body artifact. Its prose, headings, equations,
  and tables are preserved in `combined.md` for both placement modes.
- `docling.md` is normalized Docling Markdown retained for inspection and
  cache repair. Local references resolve below the sibling `docling_assets/`
  directory; it is not the final prose body.
- `docling_assets/` contains copied Docling assets needed by the normalized
  source. References outside the source/staging root are rejected.
- `docling_decoded.md` rewrites local and embedded image references to the
  canonical `figures/figure-NNN.ext` form.
- `figures/` contains decoded or copied image assets. Each figure is emitted
  once and has a durable relative link.
- `combined.md` is the final merged Markdown. It must contain no absolute local
  paths, `.staging/` paths, unresolved local assets, or formula placeholders.
- `merge_report.json` uses merge schema 4 and records placed/unplaced figure
  counts, fallback reasons, footnote reconstruction, structural asset/path
  validation, an OCR-audit summary, and warnings. Treat structural validation
  failures as conversion failures; OCR findings are nonfatal review prompts.
- `ocr_audit.json` uses audit schema 1. It records `clear` or
  `review_required`, one coverage value (`full`, `partial`, or `unavailable`)
  per PDF page, stable finding IDs/fingerprints, optional PDF character boxes,
  content origin, finding type, confidence, extracted/reference snippets, and
  contextual evidence. `ocr_audit.md` is the human-readable report.
- `ocr_audit_review.json` is a persistent schema-1 resolution ledger. A
  `source_matches` or `false_positive` classification suppresses only the
  same finding fingerprint; a changed PDF or relevant extracted content makes
  the finding active again. Use `scripts/audit_ocr.py resolve` to record a
  classification.
- `manifest.json` records the input hash, profile, external-stage arguments,
  tool versions, runtime, and completed stages. External OCR cache keys are
  independent of merge/normalization settings.
- `timings.json` records external-stage, merge, image-decoding, and
  `ocr_audit_seconds` timings. Audit time does not participate in external
  cache keys.

The default `--figure-placement appended` mode preserves Nougat's body and
adds normalized figure blocks once under `## Figures`. With explicit
`--figure-placement inline`, the merger masks structured Docling content and
uses one monotonic, context-based alignment to choose Nougat paragraph
boundaries. A figure with an ambiguous or low-confidence anchor is emitted
once under `## Unplaced Figures` and a warning is recorded. Docling contributes
figure/caption and footnote evidence only; its prose, formulas, and tables are
not transplanted into the canonical body. Footnote markers and definitions are
reconstructed in both modes, including continuations split by page or figure
blocks.

## Cache rules

`--resume` reuses an external stage only when its manifest cache key matches
and every declared output is present, non-empty, and valid. It then
re-normalizes cached Docling Markdown/assets and rebuilds the merge artifacts.
`--force` recomputes the external stages. Missing or malformed manifests never
authorize reuse.

`--merge-only` targets the existing content-hashed job for the supplied PDF and
performs normalization, figure decoding, footnote reconstruction, merging,
structural validation, and the OCR audit without invoking Nougat or Docling. It
is the supported
repair path after a completed OCR run. A missing or invalid source asset is
reported and may require a Docling rerun; a missing durable asset invalidates
only the affected Docling cache where possible.

External-stage cache keys include the PDF content hash, profile, tool path or
version, and stage arguments. Merge choices such as figure placement, math
normalization, metadata, and LaTeX generation are deliberately excluded so
they can be changed without repeating OCR.
