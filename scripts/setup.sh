#!/usr/bin/env bash
# First-time local setup: virtual environment, dependencies and a .env template.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Legal Intelligence Agent: local setup"

if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -r frontend/requirements.txt -r requirements-dev.txt -q
echo "Dependencies installed."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Fill in provider keys and database settings."
fi

# System libraries required for PDF rasterisation and OCR
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get install -y poppler-utils libmagic1 tesseract-ocr -q \
    || echo "Could not install system packages; install poppler-utils, libmagic1 and tesseract-ocr manually."
elif command -v brew >/dev/null 2>&1; then
  brew install poppler libmagic tesseract \
    || echo "Could not install system packages; install poppler, libmagic and tesseract manually."
else
  echo "Install poppler, libmagic and tesseract manually for PDF processing."
fi

cat <<'MSG'

Next steps:
  1. Edit .env (provider keys, ZILLIZ_CLOUD_*, DATABASE_URL).
  2. Apply migrations:  source venv/bin/activate && alembic upgrade head
  3. Start the stack:   bash scripts/dev.sh
MSG
