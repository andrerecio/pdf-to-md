# Benchmarks

The extraction stages are dominated by model inference, so benchmark both the
external tools and the pure-Python merge/audit stages. Keep a small
representative corpus outside the repository when PDFs are copyrighted.

After a conversion, benchmark the pure-Python merge stage:

    python3 scripts/benchmark_merge.py outputs/<stem>-<hash> --placement appended
    python3 scripts/benchmark_merge.py outputs/<stem>-<hash> --placement inline

`appended` is the default production placement. Both modes use Nougat as the
canonical prose, heading, equation, and table body while allowing uniquely
aligned Docling code replacement; inline mode additionally measures monotonic
figure-anchor work and any append-with-warning fallback.

To benchmark complete runs, use the external-tool harness. It records wall
time, stage timings, merge time, figure-decoding time, OCR-audit time, output
size/hash, job disk usage, and peak child RSS where the host exposes it:

    python3 scripts/benchmark_pipeline.py /path/to/paper.pdf \
      --profile fast \
      --output-dir benchmark-results/fast-cached \
      --nougat-cmd /path/to/runtime/nougat/bin/nougat \
      --docling-cmd /path/to/runtime/docling/bin/docling \
      --runs 2 --resume

The first run above is uncached and the second should report cached stages.
Use separate output roots when comparing variants so their artifacts do not
overwrite one another:

    python3 scripts/benchmark_pipeline.py /path/to/paper.pdf --profile fast \
      --output-dir benchmark-results/embedded-inline \
      --nougat-cmd "$NOUGAT_CMD" --docling-cmd "$DOCLING_CMD" \
      --image-mode embedded --figure-placement inline

Repeat the command for quality, referenced images, appended figures, and
--parallel-stages. Compare output_sha256 values to confirm equivalence before
comparing speed or disk usage. Peak child memory is unavailable on Windows
because the standard library does not expose a portable RSS counter there.

For a cached repair benchmark, first complete a normal run, then measure the
merge-only path with the same PDF and output root:

    python3 scripts/extract_pdf_to_md.py /path/to/paper.pdf \
      --profile fast --output-dir benchmark-results/fast-cached \
      --merge-only --figure-placement appended

Confirm that the repair does not increment either external-stage counter (or
rerun either command), and inspect `merge_report.json` for zero unresolved
assets, absolute paths, `.staging/` references, and formula placeholders.
Inspect `ocr_audit.json` for execution status, per-page coverage, active
findings, and limitations. Record placed/unplaced figure counts,
reconstructed footnotes, audit findings, and warnings alongside wall time and
output hashes. A missing durable asset should invalidate only the affected
Docling cache on `--resume`; report the resulting Docling rerun separately
from the merge and `ocr_audit_seconds` costs.

Compare timings.json and the benchmark output for:

- first run versus --resume;
- fast versus quality profiles;
- referenced versus embedded Docling images;
- appended versus inline figure placement;
- serial versus --parallel-stages execution.
- cached `--resume`/`--merge-only` repair versus a full OCR run;
- successful versus fallback inline figure placement and its warning count;
- successful versus fallback hybrid code replacement and sidecar availability;
- merge-report validation status and final figure asset count;
- OCR-audit coverage, active findings, and `ocr_audit_seconds`.
