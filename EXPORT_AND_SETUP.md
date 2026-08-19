# Export and setup

The authoritative installation and portability guide is
INSTALL.md. It covers Codex copies, Cursor copies, macOS/Linux/Windows setup,
isolated Nougat and Docling environments, verification, updates, and removal.

This file remains as a stable link for older references.

The exported skill keeps the v2 output contract: Nougat is the canonical
prose/equation/table body for appended (default) and explicit inline figure
placement. Local images are copied into the hashed job and referenced with
durable relative paths such as `figures/figure-001.png`; `.staging/` and
absolute local paths must not appear in final Markdown. Inline placement falls
back to a single **Unplaced Figures** section, with the reason recorded in
`merge_report.json`. Review that report for placement, footnote, asset, and
validation status.

Existing OCR caches can be repaired without rerunning either model: invoke the
runner with the same PDF, profile, and output directory plus `--resume`, or
use `--merge-only` when the external stages are already complete. The latter
rebuilds the merge and normalizes cached Docling assets without requiring
Nougat or Docling executables.

## Packaging an archive

If the host application provides a skill packager, run that packager against
the repository directory rather than assuming a particular Codex installation
path. The resulting archive can be extracted into the host's skills directory.
After extraction, verify that the destination directly contains SKILL.md,
references/, and scripts/.

## Runtime provisioning

Use scripts/bootstrap_runtime.py with a user-selected runtime directory.
Do not copy or reuse another machine's virtual environment; virtual
environments contain absolute interpreter paths and platform-specific binaries.
