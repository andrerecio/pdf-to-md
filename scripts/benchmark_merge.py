#!/usr/bin/env python3
"""Benchmark the pure-Python merge stage on an existing output directory."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from extract_pdf_to_md import merge_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark pdf-to-md Markdown merging.")
    parser.add_argument("job_dir", type=Path, help="A generated hashed output directory")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--placement", choices=("appended", "inline"), default="appended")
    parser.add_argument("--normalize-math", action="store_true")
    args = parser.parse_args()

    job_dir = args.job_dir.expanduser().resolve()
    nougat = (job_dir / "nougat.mmd").read_text(encoding="utf-8")
    docling = (job_dir / "docling_decoded.md").read_text(encoding="utf-8")
    timings: list[float] = []
    output_size = 0
    for _ in range(max(1, args.iterations)):
        started = time.perf_counter()
        merged = merge_outputs(nougat, docling, args.placement, args.normalize_math)
        timings.append(time.perf_counter() - started)
        output_size = len(merged.encode("utf-8"))

    result = {
        "job_dir": str(job_dir),
        "placement": args.placement,
        "iterations": len(timings),
        "min_seconds": round(min(timings), 6),
        "mean_seconds": round(sum(timings) / len(timings), 6),
        "output_bytes": output_size,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
