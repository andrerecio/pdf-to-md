#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import binascii
import mimetypes
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

IMAGE_RE = re.compile(
    # Docling may emit an unescaped absolute path containing spaces.  Accept
    # the complete Markdown target here so it can be made durable before its
    # staging directory is removed.
    r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^\n]*)\)(?=\s*$)",
    re.MULTILINE,
)


def _extension_for(path: Path, content_type: str | None = None) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff", "svg"}:
        return "jpg" if suffix == "jpeg" else suffix
    if content_type:
        guessed = content_type.split("/", 1)[-1].split(";", 1)[0].lower()
        if guessed == "jpeg":
            return "jpg"
        if guessed.isalnum():
            return guessed
    return "png"


def _decode_data_uri(target: str) -> tuple[bytes, str] | None:
    match = re.fullmatch(
        r"data:image/(?P<fmt>[a-zA-Z0-9.+-]+);base64,(?P<b64>[A-Za-z0-9+/=\s]+)",
        target,
        flags=re.DOTALL,
    )
    if not match:
        return None
    b64 = re.sub(r"\s+", "", match.group("b64"))
    try:
        data = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        return None
    return data, _extension_for(Path("."), f"image/{match.group('fmt')}")


def _clean_target(target: str) -> str:
    return unquote(target.strip().strip("<>").split("#", 1)[0])


def _relative_image_bytes(target: str, source_root: Path) -> tuple[bytes, str] | None:
    clean_target = _clean_target(target)
    if not clean_target or clean_target.startswith(("http://", "https://", "//")):
        return None
    candidate = (source_root / unquote(clean_target)).resolve()
    try:
        candidate.relative_to(source_root.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    content_type, _ = mimetypes.guess_type(candidate.name)
    return candidate.read_bytes(), _extension_for(candidate, content_type)


def _is_external_target(target: str) -> bool:
    return target.startswith(("data:", "http://", "https://", "//"))


def _relative_to(path: Path, root: Path) -> Path | None:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return None


def _cached_asset_candidate(target: str, assets_dir: Path) -> Path | None:
    """Find an old staged asset copied by v2 before its staging directory vanished."""

    name = Path(target).name
    if not name or not assets_dir.is_dir():
        return None
    candidates = [
        path for path in assets_dir.rglob(name)
        if path.is_file() and _relative_to(path, assets_dir) is not None
    ]
    return candidates[0] if len(candidates) == 1 else None


def _strip_durable_prefixes(path: Path) -> Path:
    parts = list(path.parts)
    while parts and parts[0] == "docling_assets":
        parts.pop(0)
    return Path(*parts) if parts else Path()


def _collapse_redundant_asset_tree(assets_dir: Path) -> None:
    """Promote only nested directories created by an older normalizer bug."""

    redundant_root = assets_dir / "docling_assets"
    if not redundant_root.is_dir():
        return
    for source in sorted(redundant_root.rglob("*"), key=lambda path: (len(path.parts), str(path))):
        if not source.is_file():
            continue
        relative = _strip_durable_prefixes(source.relative_to(assets_dir))
        if not relative.parts:
            continue
        destination = assets_dir / relative
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    # Everything under this exact top-level name is a duplicate produced by
    # prefixing an already durable link; source assets live beside it.
    shutil.rmtree(redundant_root)


def normalize_docling_markdown(
    input_md: Path,
    output_md: Path,
    assets_dir: Path,
    staging_root: Path | None,
    *,
    allow_cached_repair: bool = False,
) -> int:
    """Copy local Docling images into durable assets and rewrite their links.

    During extraction every local link must resolve inside ``staging_root``.  The
    optional repair mode supports v2 jobs that copied assets before preserving
    their Markdown links, provided the referenced basename is unambiguous.
    """

    text = input_md.read_text(encoding="utf-8")
    assets_dir.mkdir(parents=True, exist_ok=True)
    # A doubled durable prefix is the exact signature of the earlier
    # normalizer defect.  Do not reinterpret a genuinely exported Docling
    # directory that merely happens to be named ``docling_assets``.
    if allow_cached_repair and "docling_assets/docling_assets/" in text:
        _collapse_redundant_asset_tree(assets_dir)
    copied = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal copied
        raw_target = match.group("target").strip().strip("<>")
        target = _clean_target(raw_target)
        if not target or _is_external_target(target):
            return match.group(0)

        source: Path | None = None
        relative: Path | None = None
        candidate = Path(target)
        durable_relative = _strip_durable_prefixes(candidate) if not candidate.is_absolute() else Path()
        if allow_cached_repair and durable_relative.parts:
            durable_candidate = (assets_dir / durable_relative).resolve()
            safe_relative = _relative_to(durable_candidate, assets_dir)
            if safe_relative is not None and durable_candidate.is_file():
                source, relative = durable_candidate, safe_relative
        if staging_root is not None:
            root = staging_root.resolve()
            candidates = [candidate] if candidate.is_absolute() else [root / candidate, input_md.parent / candidate]
            for possible in candidates:
                possible = possible.resolve()
                rel = _relative_to(possible, root)
                durable_rel = _relative_to(possible, assets_dir)
                if source is None and durable_rel is not None and possible.is_file():
                    source, relative = possible, durable_rel
                    break
                if source is None and rel is not None and possible.is_file():
                    source, relative = possible, rel
                    break
            if source is None and not allow_cached_repair:
                raise ValueError(f"Docling image is missing or outside staging: {raw_target}")
        elif not candidate.is_absolute():
            possible = (input_md.parent / candidate).resolve()
            if possible.is_file():
                source = possible
                relative = _relative_to(possible, assets_dir) or Path(candidate)

        if source is None and allow_cached_repair:
            source = _cached_asset_candidate(target, assets_dir)
            if source is not None:
                relative = _relative_to(source, assets_dir)
        if source is None or relative is None:
            raise ValueError(f"Docling image is missing or outside durable assets: {raw_target}")

        destination = assets_dir / relative
        if source.resolve() != destination.resolve():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1
        durable = f"docling_assets/{relative.as_posix()}"
        return f"![{match.group('alt')}]({durable})"

    output_md.write_text(IMAGE_RE.sub(_replace, text), encoding="utf-8")
    return copied


def prefix_relative_image_links(text: str, prefix: str) -> str:
    """Make raw Docling Markdown links valid from a copied output directory."""

    def _replace(match: re.Match[str]) -> str:
        target = match.group("target").strip().strip("<>")
        if target.startswith(("data:", "http://", "https://", "//", "/", prefix + "/")):
            return match.group(0)
        return f"![{match.group('alt')}]({prefix}/{target})"

    return IMAGE_RE.sub(_replace, text)


def decode_docling_markdown(input_md: Path, output_md: Path, figures_dir: Path) -> int:
    figures_dir.mkdir(parents=True, exist_ok=True)
    text = input_md.read_text(encoding="utf-8")
    count = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal count
        target = match.group("target").strip().strip("<>")
        decoded = _decode_data_uri(target)
        if decoded is None:
            decoded = _relative_image_bytes(target, input_md.parent)
        if decoded is None:
            return match.group(0)
        data, ext = decoded
        count += 1
        filename = f"figure-{count:03d}.{ext}"
        out_path = figures_dir / filename
        out_path.write_bytes(data)
        alt = match.group("alt")
        return f"![{alt}](figures/{filename})"

    new_text = IMAGE_RE.sub(_replace, text)
    output_md.write_text(new_text, encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode Docling base64 images to files and rewrite Markdown.")
    parser.add_argument("input_md", type=Path, help="Path to Docling Markdown output")
    parser.add_argument("output_md", type=Path, help="Path to write rewritten Markdown")
    parser.add_argument("figures_dir", type=Path, help="Directory to write decoded images")
    args = parser.parse_args()

    count = decode_docling_markdown(args.input_md, args.output_md, args.figures_dir)
    print(f"Decoded {count} figures into {args.figures_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
