#!/usr/bin/env python3
"""Benchmark one or more complete pdf-to-md runs and emit JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover - Windows has no resource module.
    resource = None  # type: ignore[assignment]

from extract_pdf_to_md import safe_stem, sha256_file


def directory_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def peak_children_mb(before: int | None, after: int | None) -> float | None:
    if before is None or after is None:
        return None
    if after <= before:
        return None
    value = after - before
    if sys.platform == "darwin":
        return round(value / (1024 * 1024), 3)
    return round(value * 1024 / (1024 * 1024), 3)


def output_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark complete pdf-to-md runs.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--profile", choices=("fast", "quality"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--nougat-cmd", required=True)
    parser.add_argument("--docling-cmd", required=True)
    parser.add_argument("--image-mode", choices=("referenced", "embedded"), default="referenced")
    parser.add_argument("--figure-placement", choices=("appended", "inline"), default="appended")
    parser.add_argument("--runs", type=int, default=1, help="Number of identical runs to execute.")
    parser.add_argument("--resume", action="store_true", help="Pass --resume to every run.")
    parser.add_argument("--parallel-stages", action="store_true")
    parser.add_argument("--normalize-math", action="store_true")
    parser.add_argument("--nougat-arg", action="append", default=[])
    parser.add_argument("--docling-arg", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")
    pdf = args.pdf.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    script = Path(__file__).with_name("extract_pdf_to_md.py")
    artifact_stem = safe_stem(pdf)
    job_dir = output_dir / f"{artifact_stem}-{sha256_file(pdf)[:12]}"
    merged_output = job_dir / f"{artifact_stem}.md"
    command = [
        sys.executable,
        str(script),
        str(pdf),
        "--profile",
        args.profile,
        "--output-dir",
        str(output_dir),
        "--nougat-cmd",
        args.nougat_cmd,
        "--docling-cmd",
        args.docling_cmd,
        "--image-mode",
        args.image_mode,
        "--figure-placement",
        args.figure_placement,
    ]
    if args.resume:
        command.append("--resume")
    if args.parallel_stages:
        command.append("--parallel-stages")
    if args.normalize_math:
        command.append("--normalize-math")
    for value in args.nougat_arg:
        command.extend(["--nougat-arg", value])
    for value in args.docling_arg:
        command.extend(["--docling-arg", value])

    records: list[dict[str, Any]] = []
    for run_number in range(1, args.runs + 1):
        before_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss if resource else None
        started = time.perf_counter()
        subprocess.run(command, check=True)
        elapsed = time.perf_counter() - started
        after_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss if resource else None

        timings: dict[str, Any] = {}
        timings_path = job_dir / "timings.json"
        if timings_path.is_file():
            timings = json.loads(timings_path.read_text(encoding="utf-8"))
        records.append(
            {
                "run": run_number,
                "wall_seconds": round(elapsed, 3),
                "peak_children_mb": peak_children_mb(before_rss, after_rss),
                "job_dir_bytes": directory_bytes(job_dir),
                "output_bytes": merged_output.stat().st_size,
                "output_sha256": output_digest(merged_output),
                "stage_timings": timings.get("stages", {}),
                "merge_seconds": timings.get("merge_seconds"),
                "figure_decode_seconds": timings.get("figure_decode_seconds"),
                "ocr_audit_seconds": timings.get("ocr_audit_seconds"),
                "cache_requested": args.resume,
            }
        )

    print(
        json.dumps(
            {
                "pdf": str(pdf),
                "profile": args.profile,
                "image_mode": args.image_mode,
                "figure_placement": args.figure_placement,
                "parallel_stages": args.parallel_stages,
                "runs": records,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
