# Tooling notes

## Tested constraints

The repository keeps separate pinned constraints:

- requirements/nougat.txt
- requirements/docling.txt

They are tested with CPython 3.12. Accelerator-specific PyTorch wheels may
need to replace the CPU/MPS-compatible lines in those files.

## External interfaces

Nougat is invoked with a PDF, model/profile arguments, --markdown, and an
output directory. The runner validates exactly one .mmd artifact and uses it
as the canonical prose, heading, equation, and table body.

Docling is invoked with Markdown output, an image export mode, and an output
directory. Referenced image mode is preferred; embedded mode remains a fallback.
Before its staging directory is removed, every local image is resolved and
copied into durable `docling_assets/`; final links are relative and use the
canonical `figures/figure-NNN.ext` form. Missing or outside-root assets are
reported as validation errors.

Pandoc is optional and required only for --to-latex. It is run from the hashed
job directory with the job directory, `figures/`, and `docling_assets/` as
resource paths. The LaTeX preparation preflight rejects unresolved local
assets, absolute or `.staging/` paths, formula placeholders, and raw Unicode
unsupported by the documented pdfLaTeX route. Compile a successful output with
`latexmk -pdf -halt-on-error -file-line-error combined.tex` from that job
directory.

## Hardware

CPU is the portable baseline. The fast profile uses the small Nougat model and
small page batches. The quality profile uses the base model. Docling device,
thread, page-batch, and profiling settings can be passed with repeatable
--docling-arg options, for example --docling-arg=--profiling and
--docling-arg=--save-profiling.

Model artifacts are downloaded lazily by the external tools. Use check_deps.py
to print the runtime and cache locations before starting a long conversion.

Review `merge_report.json` after every run. It is the authoritative summary of
figure placement (including inline fallbacks), footnote reconstruction, asset
resolution, and Markdown/LaTeX preflight validation. A merge can be rebuilt
from valid cached stages with `--resume` or `--merge-only` without rerunning
OCR.
