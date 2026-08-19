#!/usr/bin/env python3
"""Create isolated Nougat and Docling environments on macOS, Linux, or Windows."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = {
    "nougat": ROOT / "requirements" / "nougat.txt",
    "docling": ROOT / "requirements" / "docling.txt",
}


def executable_name(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def environment_python(path: Path) -> Path:
    return path / ("Scripts" if os.name == "nt" else "bin") / executable_name("python")


def environment_command(path: Path, name: str) -> Path:
    return path / ("Scripts" if os.name == "nt" else "bin") / executable_name(name)


def run(command: list[str], dry_run: bool = False) -> None:
    print("$ " + " ".join(str(part) for part in command))
    if not dry_run:
        subprocess.run(command, check=True)


def short_python_request(python_request: str) -> str:
    parts = python_request.removeprefix("python").split(".")
    return ".".join(parts[:2])


def python_matches_request(command: str, python_request: str) -> bool:
    requested = short_python_request(python_request)
    probe = [command]
    if os.name == "nt" and Path(command).stem.lower() == "py":
        probe.append(f"-{requested}")
    probe.extend(["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"])
    try:
        result = subprocess.run(
            probe,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == requested


def fallback_python(python_request: str) -> str:
    candidates = [
        "python3.12" if os.name != "nt" else "py",
        "python3",
        "python",
    ]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved and python_matches_request(resolved, python_request):
            return resolved
    if python_matches_request(sys.executable, python_request):
        return sys.executable
    raise RuntimeError(
        f"Could not find Python {python_request}. Install it or install uv, then rerun bootstrap_runtime.py."
    )


def create_environment(path: Path, python_request: str, uv: str | None, dry_run: bool) -> Path:
    interpreter = environment_python(path)
    if interpreter.exists():
        if not dry_run and not python_matches_request(str(interpreter), python_request):
            raise RuntimeError(
                f"Existing environment {path} does not use Python {python_request}; "
                "choose a new --runtime-dir or recreate it explicitly."
            )
        return interpreter
    path.parent.mkdir(parents=True, exist_ok=True)
    if uv:
        run([uv, "venv", "--python", python_request, str(path)], dry_run=dry_run)
    else:
        base_python = fallback_python(python_request)
        command = [base_python]
        if os.name == "nt" and Path(base_python).stem.lower() == "py":
            command.append(f"-{short_python_request(python_request)}")
        command.extend(["-m", "venv", str(path)])
        run(command, dry_run=dry_run)
    return interpreter


def install_requirements(
    interpreter: Path,
    requirements: Path,
    uv: str | None,
    dry_run: bool,
) -> None:
    if uv:
        run([uv, "pip", "install", "--python", str(interpreter), "-r", str(requirements)], dry_run=dry_run)
    else:
        run([str(interpreter), "-m", "pip", "install", "--upgrade", "pip"], dry_run=dry_run)
        run([str(interpreter), "-m", "pip", "install", "-r", str(requirements)], dry_run=dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision isolated Nougat and Docling environments.")
    parser.add_argument("--runtime-dir", type=Path, default=ROOT / ".runtime", help="Environment root directory")
    parser.add_argument("--python", default="3.12", help="Python request passed to uv or venv")
    parser.add_argument("--no-install", action="store_true", help="Create environments but do not install packages")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them")
    args = parser.parse_args()

    uv = shutil.which("uv")
    if uv:
        print(f"Using uv: {uv}")
    else:
        print("uv not found; falling back to venv + pip.")

    runtime_dir = args.runtime_dir.expanduser().resolve()
    for name, requirements in REQUIREMENTS.items():
        env_dir = runtime_dir / name
        interpreter = create_environment(env_dir, args.python, uv, args.dry_run)
        if not args.no_install:
            install_requirements(interpreter, requirements, uv, args.dry_run)

    print("\nRuntime paths:")
    print(f"  NOUGAT_CMD={environment_command(runtime_dir / 'nougat', 'nougat')}")
    print(f"  DOCLING_CMD={environment_command(runtime_dir / 'docling', 'docling')}")
    print(f"  RUNNER_PYTHON={sys.executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
