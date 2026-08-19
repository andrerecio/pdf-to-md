# pdf-to-md

Convert a research PDF into structured Markdown using Nougat-OCR for text, equations, and tables, plus Docling for figures and footnotes.

## Use as an AI skill

Install [`SKILL.md`](SKILL.md) as a skill in your preferred AI tool to let it use this repository's PDF-to-Markdown workflow.

## Use from the terminal

You can also run the Python scripts directly from your terminal:

```bash
python scripts/extract_pdf_to_md.py input.pdf --output-dir outputs
```

The merged result is written to `outputs/<pdf-name>/combined.md`.
