#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REQUIRED = ["nougat", "docling"]


def find_command(cmd: str) -> str | None:
    bin_dir = Path(sys.executable).parent
    candidate = bin_dir / cmd
    if candidate.exists():
        return str(candidate)
    return shutil.which(cmd)


def resolve_cmd(cmd: str, override: str | None) -> str | None:
    if override:
        path = Path(override).expanduser()
        return str(path) if path.exists() else None
    return find_command(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Nougat and Docling CLI availability.")
    parser.add_argument("--nougat-cmd", help="Path to nougat executable")
    parser.add_argument("--docling-cmd", help="Path to docling executable")
    args = parser.parse_args()

    resolved = {
        "nougat": resolve_cmd("nougat", args.nougat_cmd),
        "docling": resolve_cmd("docling", args.docling_cmd),
    }

    missing = [name for name, path in resolved.items() if path is None]
    if missing:
        joined = ", ".join(missing)
        print(f"Missing required commands: {joined}", file=sys.stderr)
        print("Install Nougat-OCR and Docling, then ensure they are on PATH.", file=sys.stderr)
        return 1

    print("OK: nougat and docling found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
