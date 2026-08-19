#!/usr/bin/env python3
"""Diagnose the external tools and runtime needed by pdf-to-md."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def executable_file(path: Path) -> bool:
    return path.is_file() and (os.name == "nt" or os.access(path, os.X_OK))


def find_command(cmd: str) -> str | None:
    candidate = Path(sys.executable).parent / cmd
    if executable_file(candidate):
        return str(candidate)
    resolved = shutil.which(cmd)
    return resolved if resolved and executable_file(Path(resolved)) else None


def resolve_cmd(cmd: str, override: str | None) -> str | None:
    if override:
        path = Path(override).expanduser().resolve()
        return str(path) if executable_file(path) else None
    return find_command(cmd)


def launcher_interpreter(command: str) -> str | None:
    try:
        first_line = Path(command).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return None
    if first_line.startswith("#!"):
        parts = first_line[2:].strip().split()
        if not parts:
            return None
        if Path(parts[0]).name == "env" and len(parts) > 1:
            interpreter = shutil.which(parts[1])
        else:
            interpreter = parts[0]
        return interpreter if interpreter and Path(interpreter).is_file() else None
    return None


def package_version_from_command(command: str, package: str) -> str | None:
    interpreter = launcher_interpreter(command)
    if not interpreter:
        return None
    probe = (
        "import importlib.metadata; "
        f"print(importlib.metadata.version({package!r}))"
    )
    try:
        result = subprocess.run(
            [interpreter, "-c", probe],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    version = result.stdout.strip()
    return version or None


def launcher_details(command: str, package: str) -> dict[str, str | None]:
    interpreter = launcher_interpreter(command)
    if not interpreter:
        return {}
    probe = (
        "import importlib.metadata, json, platform, sys; "
        f"package = {package!r}; "
        "\ntry: version = importlib.metadata.version(package)\n"
        "except importlib.metadata.PackageNotFoundError: version = None\n"
        "print(json.dumps({'python': sys.executable, 'python_version': platform.python_version(), 'version': version}))"
    )
    try:
        result = subprocess.run(
            [interpreter, "-c", probe],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def probe_command(command: str, package: str) -> dict[str, Any]:
    path = str(Path(command).resolve())
    report: dict[str, Any] = {"path": path, "available": True, "version": "unprobed"}
    details = launcher_details(command, package)
    report.update({key: value for key, value in details.items() if value is not None})
    package_version_value = details.get("version")
    if package_version_value:
        report["version"] = package_version_value
        report["probe"] = "launcher interpreter metadata"
        return report
    try:
        result = subprocess.run(
            [command, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        report["probe"] = "--version timed out; executable retained"
        return report
    except OSError as exc:
        report["available"] = False
        report["error"] = str(exc)
        return report
    output = (result.stdout or result.stderr).strip()
    if output:
        report["version"] = output.splitlines()[0][:500]
        report["probe"] = "--version"
    else:
        report["probe"] = f"--version returned {result.returncode}; executable retained"
    return report


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def writable_target(path: Path) -> dict[str, Any]:
    expanded = path.expanduser().resolve()
    if expanded.exists():
        return {
            "path": str(expanded),
            "exists": True,
            "directory": expanded.is_dir(),
            "writable": os.access(expanded, os.W_OK),
        }

    parent = expanded.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    return {
        "path": str(expanded),
        "exists": False,
        "directory": False,
        "writable_parent": os.access(parent, os.W_OK),
        "checked_parent": str(parent),
    }


def model_cache_locations() -> dict[str, str]:
    return {
        "huggingface": os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface")),
        "torch": os.environ.get("TORCH_HOME", str(Path.home() / ".cache" / "torch")),
        "docling": os.environ.get("DOCLING_ARTIFACTS_PATH", str(Path.home() / ".cache" / "docling")),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    commands: dict[str, dict[str, Any]] = {}
    for name, command, override in (
        ("nougat", "nougat", args.nougat_cmd),
        ("docling", "docling", args.docling_cmd),
        ("pandoc", "pandoc", args.pandoc_cmd),
    ):
        resolved = resolve_cmd(command, override)
        if resolved is None:
            commands[name] = {"available": False, "required": name != "pandoc", "command": command}
        else:
            commands[name] = {
                **probe_command(resolved, "nougat-ocr" if name == "nougat" else "docling"),
                "required": name != "pandoc",
                "command": command,
            }

    required_missing = [name for name in ("nougat", "docling") if not commands[name].get("available")]
    output = writable_target(args.output_dir) if args.output_dir else None
    output_ok = output is None or (
        (output.get("directory") and output.get("writable"))
        if output.get("exists")
        else output.get("writable_parent", False)
    )
    return {
        "runtime": {
            "python": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "commands": commands,
        "packages_in_checker_environment": {
            name: package_version(name)
            for name in ("nougat-ocr", "docling", "torch", "numpy", "transformers")
        },
        "output": output,
        "model_cache_locations": model_cache_locations(),
        "required_missing": required_missing,
        "ok": not required_missing and output_ok,
    }


def print_human(report: dict[str, Any]) -> None:
    runtime = report["runtime"]
    print(f"Python: {runtime['python']} ({runtime['python_version']})")
    print(f"Platform: {runtime['platform']} [{runtime['machine']}]")
    for name, details in report["commands"].items():
        if details.get("available"):
            print(f"{name}: {details['path']} — {details.get('version', 'unknown')}")
        elif details.get("required"):
            print(f"{name}: MISSING ({details.get('command', name)})")
        else:
            print(f"{name}: not installed (optional)")
    if report.get("output"):
        output = report["output"]
        writable = output.get("writable", output.get("writable_parent", False))
        print(f"Output: {output['path']} — {'writable' if writable else 'not writable'}")
    print("Model caches:")
    for name, path in report["model_cache_locations"].items():
        print(f"  {name}: {path}")
    if report["ok"]:
        print("OK: required pdf-to-md dependencies are available.")
    else:
        print("ERROR: one or more required checks failed.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose pdf-to-md dependencies and runtime paths.")
    parser.add_argument("--nougat-cmd", help="Path to the Nougat executable")
    parser.add_argument("--docling-cmd", help="Path to the Docling executable")
    parser.add_argument("--pandoc-cmd", help="Path to the optional Pandoc executable")
    parser.add_argument("--output-dir", type=Path, help="Output directory to check")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
