# Example: quantitative RBC notes

Demonstration conversion of:

Eric Sims, “Business Cycle Facts and the Quantitative Performance of the RBC Model,” Graduate Macro Theory II, University of Notre Dame, Spring 2024.

The source PDF is the file he hosts on his Notre Dame course page:

<https://sites.nd.edu/esims/files/2024/01/notes_rbc_quant_sp2024.pdf>

That URL is linked from [Ph.D. Macro Theory II](https://sites.nd.edu/esims/courses/ph-d-macro-theory-ii/) as the quantitative RBC notes. The file downloaded from that URL on 14 October 2026 has SHA-256

```
b1dcee924317f4ac6643012ae4a29e446dfb280fe1792d8698799ceb7a916d08
```

which is the `input.sha256` recorded in [`manifest.json`](manifest.json). The PDF itself is not in this repository.

This directory is a demonstration conversion only. Eric Sims retains copyright in the notes. Hosting this Markdown does not change that copyright or grant any license to the notes beyond what he already provides by posting the PDF.

The committed files were regenerated from a completed quality-profile extraction with:

```bash
python3 scripts/extract_pdf_to_md.py notes_rbc_quant_sp2024.pdf \
  --profile quality \
  --output-dir outputs \
  --merge-only \
  --normalize-math \
  --nougat-cmd /path/to/nougat
```

`--profile` is required by the CLI. `--merge-only` rebuilds the merge from cached Nougat and Docling output and does not rerun OCR. `--normalize-math` rewrites `\(...\)` and `\[...\]` to `$...$` and `$$...$$`, which GitHub renders. Pass `--nougat-cmd` (or have `nougat` on `PATH`) so the OCR audit can find that environment’s Python; `manifest.json` stores the executable name `nougat`, not a machine path. A first conversion from the PDF uses the same flags without `--merge-only`.

[`notes_rbc_quant_sp2024.md`](notes_rbc_quant_sp2024.md) is the merged Markdown. Figures are in [`figures/`](figures/). [`ocr_audit.md`](ocr_audit.md) is clear: no active findings. Pages 10–12 are `partial` because they are code listings and were not compared as prose or math. Nothing in [`ocr_audit_review.json`](ocr_audit_review.json) was marked resolved.

GitHub renders the dollar-delimited equations. Tables leave Nougat as LaTeX `tabular` environments, so GitHub shows that table source rather than a rendered table. A side-by-side of PDF page 2 and the rendered Markdown is [`preview.png`](preview.png).
