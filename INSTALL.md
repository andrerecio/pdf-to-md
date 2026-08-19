# pdf-to-md installation and portability

This guide provisions the skill without assuming a particular home directory,
shell, editor, or pre-existing Python environment.

## Supported baseline

The tested baseline is CPython 3.12 with two isolated environments:

| Component | Environment | Tested constraint |
| --- | --- | --- |
| Nougat-OCR | runtime/nougat | requirements/nougat.txt |
| Docling | runtime/docling | requirements/docling.txt |
| Runner scripts | any Python 3.12 interpreter | standard library only |
| Pandoc | system executable | optional, LaTeX output only |

Other Python versions are untested until verified; use them only with an
explicit compatibility check.

CPU execution is the portable baseline. CUDA, Apple MPS, and other accelerator
builds may require replacing the PyTorch lines in the corresponding requirements
file with the wheel selected by the official PyTorch installer.

Docling documents support for macOS, Linux, and Windows on x86_64 and arm64:
https://docling-project.github.io/docling/getting_started/installation/.

## Support matrix

| Host | Tested Python baseline | CPU baseline | Optional acceleration | First-run downloads and storage |
| --- | --- | --- | --- | --- |
| macOS x86_64/arm64 | CPython 3.12 | 4 CPU cores; 8 GB RAM minimum, 16 GB recommended for quality | Apple MPS when the installed PyTorch wheel supports it | Nougat model weights plus Docling artifacts; reserve at least 8 GB free, 16 GB recommended |
| Linux x86_64/arm64 | CPython 3.12 | 4 CPU cores; 8 GB RAM minimum, 16 GB recommended for quality | CUDA or other PyTorch-supported accelerator | Same model/artifact caches; CUDA wheels add disk usage |
| Windows x86_64/arm64 | CPython 3.12 | 4 CPU cores; 8 GB RAM minimum, 16 GB recommended for quality | CUDA where the selected PyTorch wheel supports it | Same model/artifact caches; keep the runtime on a local NTFS path |
| WSL2 | CPython 3.12 inside the Linux distribution | Linux CPU baseline | CUDA passthrough when configured by the host | Keep runtime and outputs in the WSL filesystem for better PDF I/O |

RAM and disk values are planning estimates, not hard tool limits. The exact
footprint varies with the Nougat profile, PyTorch wheel, page count, and model
cache contents. CPU remains the compatibility fallback.

## 1. Obtain the skill

Set SKILL_DIR to the directory containing this repository. The path is
deliberately user-defined:

    export SKILL_DIR="/path/to/pdf-to-md"
    cd "$SKILL_DIR"

For a fresh clone:

    git clone https://github.com/ccantore/pdf-to-md.git /path/to/pdf-to-md
    export SKILL_DIR="/path/to/pdf-to-md"

### Codex installation

Use a copy as the portable default. Define CODEX_HOME explicitly when it is
not already set:

    if [ -z "$CODEX_HOME" ]; then CODEX_HOME="$HOME/.codex"; fi
    mkdir -p "$CODEX_HOME/skills/pdf-to-md"
    rsync -a --delete --exclude '.git/' "$SKILL_DIR"/ "$CODEX_HOME/skills/pdf-to-md"/
    test -f "$CODEX_HOME/skills/pdf-to-md/SKILL.md"

If rsync is unavailable, copy the directory contents with a file manager or
cp -R "$SKILL_DIR"/. "$CODEX_HOME/skills/pdf-to-md"/.

On Windows PowerShell:

    $env:SKILL_DIR = "C:\path\to\pdf-to-md"
    $CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
    $Destination = Join-Path $CodexHome "skills\pdf-to-md"
    New-Item -ItemType Directory -Force $Destination | Out-Null
    Copy-Item -Path (Join-Path $env:SKILL_DIR "*") -Destination $Destination -Recurse -Force
    Test-Path (Join-Path $Destination "SKILL.md")

Symlinks are optional and convenient for contributors, but copies are more
reliable across Windows, Cursor, archive extraction, and backup tools.

### Cursor installation

From the repository:

    scripts/sync_cursor_skill.sh

The helper derives its default source from its own location. Use explicit paths
for a different source or project-local installation:

    scripts/sync_cursor_skill.sh --src "$SKILL_DIR" --dest "$HOME/.cursor/skills/pdf-to-md"
    scripts/sync_cursor_skill.sh --src "$SKILL_DIR" --project /path/to/project

For Windows, copy SKILL_DIR to either
%USERPROFILE%\.cursor\skills\pdf-to-md or
<project>\.cursor\skills\pdf-to-md with File Explorer or
Copy-Item -Recurse -Force.

## 2. Install Nougat and Docling

The recommended path uses uv, which can install Python 3.12 and provision
virtual environments without changing the system Python:

    curl -LsSf https://astral.sh/uv/install.sh | sh
    python3 "$SKILL_DIR/scripts/bootstrap_runtime.py" \
      --runtime-dir "$SKILL_DIR/.runtime" \
      --python 3.12

See the official uv installation documentation for Windows and alternative
installation methods:
https://docs.astral.sh/uv/getting-started/installation/.

PowerShell installer from the official uv documentation:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

The bootstrap script creates:

    <SKILL_DIR>/.runtime/
      nougat/
      docling/

It installs the pinned constraints from requirements/. The environments are
separate because Nougat and Docling have different dependency compatibility
risks.

Without uv, use a Python 3.12 installation and let the script fall back to
venv plus pip:

    python3.12 "$SKILL_DIR/scripts/bootstrap_runtime.py" \
      --runtime-dir "$SKILL_DIR/.runtime"

On Windows, use py -3.12 to run the bootstrap script.

PowerShell equivalent:

    $env:RUNTIME_DIR = Join-Path $env:SKILL_DIR ".runtime"
    py -3.12 (Join-Path $env:SKILL_DIR "scripts\bootstrap_runtime.py") --runtime-dir $env:RUNTIME_DIR

## 3. Verify the installation

POSIX shells:

    RUNNER_PYTHON="python3.12"
    RUNTIME_DIR="$SKILL_DIR/.runtime"
    NOUGAT_CMD="$RUNTIME_DIR/nougat/bin/nougat"
    DOCLING_CMD="$RUNTIME_DIR/docling/bin/docling"
    OUTPUT_DIR="$SKILL_DIR/outputs"

    "$RUNNER_PYTHON" "$SKILL_DIR/scripts/check_deps.py" \
      --nougat-cmd "$NOUGAT_CMD" \
      --docling-cmd "$DOCLING_CMD" \
      --output-dir "$OUTPUT_DIR"

Windows PowerShell:

    $RunnerPython = "py"
    $RuntimeDir = Join-Path $env:SKILL_DIR ".runtime"
    $NougatCmd = Join-Path $RuntimeDir "nougat\Scripts\nougat.exe"
    $DoclingCmd = Join-Path $RuntimeDir "docling\Scripts\docling.exe"
    $OutputDir = Join-Path $env:SKILL_DIR "outputs"
    & $RunnerPython -3.12 (Join-Path $env:SKILL_DIR "scripts\check_deps.py") --nougat-cmd $NougatCmd --docling-cmd $DoclingCmd --output-dir $OutputDir

For automation, add --json to receive a machine-readable diagnostic report.

## Quick start: convert a PDF

Choose a profile explicitly:

    "$RUNNER_PYTHON" "$SKILL_DIR/scripts/extract_pdf_to_md.py" /path/to/paper.pdf \
      --profile fast \
      --output-dir "$OUTPUT_DIR" \
      --nougat-cmd "$NOUGAT_CMD" \
      --docling-cmd "$DOCLING_CMD" \
      --resume

Windows PowerShell:

    $Pdf = "C:\path\to\paper.pdf"
    & $RunnerPython -3.12 (Join-Path $env:SKILL_DIR "scripts\extract_pdf_to_md.py") $Pdf `
      --profile fast --output-dir $OutputDir --nougat-cmd $NougatCmd `
      --docling-cmd $DoclingCmd --resume

Use --profile quality for Nougat's base model. Appended figures are the
default. The first run downloads model artifacts; later runs with --resume
reuse valid external-stage outputs when the PDF, profile, arguments, and tool
versions match. Nougat remains the canonical source for prose, headings,
equations, and tables in both placement modes; Docling contributes figure,
caption, and footnote evidence.

### Complete POSIX workflow template

The following placeholder-based example verifies the runtime, converts one
PDF, reviews the merge report, and compiles the generated LaTeX. Replace every
`/path/to/...` value and set `JOB_DIR` to the hashed job directory printed by
the extraction command.

```sh
set -eu

# Project, input, and output paths.
SKILL_DIR="/path/to/pdf-to-md"
PDF_PATH="/path/to/document.pdf"
OUTPUT_ROOT="/path/to/output-directory"

# Executables from the provisioned environments.
RUNNER_PYTHON="/path/to/python3.12"
NOUGAT_CMD="/path/to/nougat/bin/nougat"
DOCLING_CMD="/path/to/docling/bin/docling"
PANDOC_CMD="/path/to/pandoc"
LATEXMK_CMD="/path/to/latexmk"

cd "$SKILL_DIR"

# 1. Verify dependencies.
"$RUNNER_PYTHON" scripts/check_deps.py \
  --nougat-cmd "$NOUGAT_CMD" \
  --docling-cmd "$DOCLING_CMD" \
  --output-dir "$OUTPUT_ROOT"

# 2. Extract, merge, and generate LaTeX. Appended figures are the default.
"$RUNNER_PYTHON" scripts/extract_pdf_to_md.py "$PDF_PATH" \
  --profile quality \
  --output-dir "$OUTPUT_ROOT" \
  --nougat-cmd "$NOUGAT_CMD" \
  --docling-cmd "$DOCLING_CMD" \
  --resume \
  --figure-placement appended \
  --to-latex \
  --pandoc-cmd "$PANDOC_CMD"

# 3. Replace this placeholder with the job directory printed above.
JOB_DIR="$OUTPUT_ROOT/<pdf-stem>-<content-hash>"

# 4. Inspect the machine-readable merge and validation report.
"$RUNNER_PYTHON" -m json.tool "$JOB_DIR/merge_report.json"

# 5. Compile from the job directory so relative figure paths resolve.
cd "$JOB_DIR"
"$LATEXMK_CMD" -pdf \
  -halt-on-error \
  -file-line-error \
  -interaction=nonstopmode \
  combined.tex

printf 'Markdown: %s\n' "$JOB_DIR/combined.md"
printf 'PDF:      %s\n' "$JOB_DIR/combined.pdf"
```

For routine conversions, change `--profile quality` to `--profile fast`.
Use `--force` instead of `--resume` for a fully fresh OCR run into a new or
existing output root. Use `--figure-placement inline` only when source-position
placement is required. If only Markdown is needed, omit `--to-latex`,
`--pandoc-cmd`, the `LATEXMK_CMD` variable, and the compilation step.

Useful options:

    --force                         Recompute both external stages.
    --figure-placement inline       Try source-position figure placement.
    --merge-only                    Rebuild from the existing hashed job cache.
    --image-mode embedded           Use embedded Docling images.
    --keep-base64                   Retain data URIs in docling.md; final outputs still decode figures.
    --parallel-stages               Opt into concurrent Nougat/Docling execution.
    --normalize-math                Normalize bracketed math delimiters.
    --to-latex                      Generate LaTeX with Pandoc.
    --nougat-arg VALUE              Repeat for one additional Nougat argument.
    --docling-arg VALUE             Repeat for one additional Docling argument.

When the value itself starts with a dash, use the equals form, for example
--nougat-arg=--no-skipping.

The current output directory is:

    outputs/<pdf-stem>-<content-hash>/
      nougat.mmd
      docling.md
      docling_assets/
      docling_decoded.md
      figures/
      combined.md
      merge_report.json
      manifest.json
      timings.json
      combined_for_tex.md            optional
      combined.tex                  optional

## Profiles and performance

Use fast for routine conversions: it selects Nougat's small model and
conservative batches and Docling thread settings. Use quality when fidelity
matters more than elapsed time: it selects Nougat's base model and larger
Docling page batches. Both profiles remain CPU-compatible.

Stages run serially by default to avoid competing for memory. Opt into
--parallel-stages only when the host has enough CPU/GPU memory for both tools;
parallel execution can be slower or fail on constrained machines. Use
--resume for content-addressed stage reuse and --force to invalidate both
external stages. A resume also normalizes cached Docling image links and
repairs durable assets when possible. To repair or regenerate only merge
artifacts after OCR has completed, pass --merge-only with the same PDF,
--profile, and --output-dir; this does not invoke Nougat or Docling.

Pass tool-specific settings without shell-quoted argument strings:

    --docling-arg=--device --docling-arg=cpu
    --docling-arg=--num-threads --docling-arg=2
    --docling-arg=--profiling --docling-arg=--save-profiling
    --nougat-arg=--no-skipping

## Output contract

nougat.mmd is the canonical body source. docling.md is normalized Docling
Markdown with local assets copied into the sibling docling_assets/ directory;
it is retained for inspection and cache repair, not used as the final prose
body. docling_decoded.md is the merge input after images are copied or decoded
into figures/. combined.md is the final artifact. Every local image reference
in these Markdown artifacts is durable and relative: docling.md uses
docling_assets/..., while docling_decoded.md and combined.md use
figures/figure-001.png. Absolute paths and .staging/ references are invalid.

The default appended mode puts each figure once under ## Figures. Explicit
inline mode anchors figures to Nougat paragraph boundaries using monotonic
context. If an anchor is ambiguous or below the confidence threshold, that
figure is placed once under ## Unplaced Figures and a warning is recorded.
Footnote markers and definitions are reconstructed for both modes. Review
merge_report.json (merge schema 3) for placed/unplaced figures, footnote
status, validation errors, and warnings. manifest.json contains external-stage cache keys and
tool/runtime metadata; timings.json contains stage, merge, and image-decoding
timings. See references/io-spec.md for the complete contract.

## LaTeX output

Install Pandoc using the package manager for the host system or the official
instructions: https://pandoc.org/installing.html. The executable is required
only for --to-latex; a TeX distribution is needed separately only if the
generated .tex file will be compiled.

Run:

    PANDOC_CMD="$(command -v pandoc)"
    "$RUNNER_PYTHON" "$SKILL_DIR/scripts/extract_pdf_to_md.py" /path/to/paper.pdf \
      --profile quality --output-dir "$OUTPUT_DIR" \
      --nougat-cmd "$NOUGAT_CMD" --docling-cmd "$DOCLING_CMD" \
      --resume --to-latex --pandoc-cmd "$PANDOC_CMD"

The runner first prepares combined_for_tex.md, validates image paths and
LaTeX-sensitive content, then writes and postprocesses combined.tex. Pandoc is
run from the hashed job directory with that directory, figures/, and
docling_assets/ available as resource paths. The preparation step fails before
Pandoc when it finds an unresolved local asset, a .staging/ path, a formula
placeholder, or raw Unicode unsupported by the documented pdfLaTeX route.

To compile the generated file, change into the job directory and run:

    cd outputs/<pdf-stem>-<content-hash>
    latexmk -pdf -halt-on-error -file-line-error combined.tex

Treat missing-graphics or input-encoding errors as failures; ordinary
overfull-box warnings can be reviewed separately.

## Updates and removal

Update the skill copy by rerunning the Codex or Cursor copy command. Update the
runtime environments by rerunning:

    python3 "$SKILL_DIR/scripts/bootstrap_runtime.py" --runtime-dir "$SKILL_DIR/.runtime"

To remove the skill, delete only the installed skill directory and, if desired,
the explicitly created .runtime directory. Model caches are separate and can
be retained for another installation.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| nougat or docling missing | Run check_deps.py --json and pass explicit executable paths. |
| Docling image-export failure | Retry with --image-mode embedded; the runner also falls back automatically. |
| Nougat [MISSING_PAGE] output | Add --nougat-arg=--no-skipping. |
| macOS OpenMP crash | Set KMP_SHM_DISABLE=1 and OMP_NUM_THREADS=1 for the run. |
| NumPy/Torch incompatibility | Recreate the affected environment from the pinned requirements or adjust the platform-specific Torch build. |
| Long-running command terminated | Increase the caller's timeout; OCR duration depends on page count and hardware. |
| Missing or unresolved figure | Check merge_report.json, confirm the target exists below figures/ or docling_assets/, and rerun with --resume. If OCR stages are valid, use --merge-only; a missing source asset may require rerunning Docling. |
| Absolute path or .staging/ appears in Markdown | Do not edit the final file by hand. Run --resume or --merge-only to re-normalize cached Docling output, then inspect the validation errors in merge_report.json. |
| LaTeX reports Unicode/input errors | The pdfLaTeX preflight rejects unsupported raw Unicode. Replace or encode the source character, choose a Unicode-capable TeX engine outside this documented route, or fix the upstream Markdown before retrying. |
| LaTeX reports missing graphics | Compile from the job directory with the command above and verify figures/ and docling_assets/ are present; unresolved local paths are a merge/preflight error. |

Nougat is designed for academic documents and performs best on documents
similar to its training data. Review combined.md, the figure directories, and
merge_report.json after every conversion.
