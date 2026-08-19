# pdf-to-md

Convert a research PDF into structured Markdown using Nougat-OCR for text, equations, and tables, plus Docling for figures and footnotes.

```bash
python scripts/extract_pdf_to_md.py input.pdf --output-dir outputs
```

The merged result is written to `outputs/<pdf-name>/combined.md`.
