#!/usr/bin/env bash

set -e

echo "Setting up Menza project..."

PYTHON_CMD="python3"
if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
  PYTHON_CMD="python"
fi

if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
  echo "Error: Python is required but was not found."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_CMD" -m venv .venv
fi

OS="$(uname -s 2>/dev/null || echo Windows)"

if [ -f ".venv/bin/activate" ]; then
  VENV_ACTIVATE=".venv/bin/activate"
  VENV_PYTHON=".venv/bin/python"
elif [ -f ".venv/Scripts/activate" ]; then
  VENV_ACTIVATE=".venv/Scripts/activate"
  VENV_PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/Scripts/activate.bat" ]; then
  VENV_ACTIVATE=".venv/Scripts/activate.bat"
  VENV_PYTHON=".venv/Scripts/python.exe"
else
  echo "Error: Could not find virtual environment activation script."
  exit 1
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1090
source "$VENV_ACTIVATE" 2>/dev/null || true

echo "Upgrading pip..."
"$VENV_PYTHON" -m pip install --upgrade pip

echo "Installing dependencies..."
"$VENV_PYTHON" -m pip install playwright python-dotenv

echo "Installing Playwright browsers..."
"$VENV_PYTHON" -m playwright install

if [ ! -f ".env" ]; then
  echo "Creating .env file..."
  cat <<EOF > .env
BASE_URL=https://app.menza.ai
MENZA_EMAIL=test123@menza.ai
MENZA_PASSWORD=menzatest
OUTPUT_FILE=dashboard_titles.json
HEADLESS=true
EOF
fi

echo ""
echo "Setup complete."
echo "Run the script with:"
echo "\"$VENV_PYTHON\" menzatest.py"