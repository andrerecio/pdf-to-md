#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Sync the pdf-to-md skill into Cursor.

Usage:
  sync_cursor_skill.sh [--src PATH] [--dest PATH]
  sync_cursor_skill.sh --project /path/to/project

Options:
  --src PATH      Source skill directory (default: ~/Documents/GitHub/skills/pdf-to-md)
  --dest PATH     Destination skill directory (default: ~/.cursor/skills/pdf-to-md)
  --project PATH  Sync into a project-local .cursor/skills directory
  -h, --help      Show this help
USAGE
}

SRC_DEFAULT="$HOME/Documents/GitHub/skills/pdf-to-md"
DEST_DEFAULT="$HOME/.cursor/skills/pdf-to-md"
SRC="$SRC_DEFAULT"
DEST="$DEST_DEFAULT"
PROJECT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src)
      SRC="$2"
      shift 2
      ;;
    --dest)
      DEST="$2"
      shift 2
      ;;
    --project)
      PROJECT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -n "$PROJECT" ]]; then
  DEST="$PROJECT/.cursor/skills/pdf-to-md"
fi

if [[ ! -d "$SRC" ]]; then
  echo "Source skill directory not found: $SRC" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"

# Avoid syncing bulky or transient folders/files.
RSYNC_EXCLUDES=(
  --exclude ".git/"
  --exclude ".DS_Store"
  --exclude ".tmp.driveupload/"
  --exclude "venvs/"
  --exclude ".venv/"
  --exclude "venv/"
  --exclude "outputs/"
  --exclude "dist/"
  --exclude "*.skill"
  --exclude "__pycache__/"
  --exclude ".pytest_cache/"
)

rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$SRC"/ "$DEST"/

echo "Synced pdf-to-md skill to: $DEST"
