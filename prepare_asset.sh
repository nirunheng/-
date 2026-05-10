#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 -m pip install --break-system-packages -r "$PROJECT_DIR/requirements-wsl.txt"
PYTHONPATH="$PROJECT_DIR/src" python3 -m pet.prepare_asset \
  --source "$PROJECT_DIR/./image.png" \
  --output-dir "$PROJECT_DIR/assets"
