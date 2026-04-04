#!/usr/bin/env bash
set -euo pipefail

echo "Setting up Menza project..."

# Find a usable Python
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
elif command -v py >/dev/null 2>&1; then
  PYTHON_CMD="py"
else
  echo "Error: Python was not found. Install Python 3.10+ and try again."
  exit 1
fi

echo "Using Python command: $PYTHON_CMD"

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  if [ "$PYTHON_CMD" = "py" ]; then
    py -3 -m venv .venv
  else
    "$PYTHON_CMD" -m venv .venv
  fi
fi

# Locate venv python without using activate
if [ -x ".venv/bin/python" ]; then
  VENV_PYTHON=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
  VENV_PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/Scripts/python" ]; then
  VENV_PYTHON=".venv/Scripts/python"
else
  echo "Error: Could not find the virtual environment Python executable."
  echo "Try deleting .venv and running this script again."
  exit 1
fi

echo "Virtual environment python: $VENV_PYTHON"

echo "Upgrading pip..."
"$VENV_PYTHON" -m pip install --upgrade pip

echo "Installing dependencies..."
"$VENV_PYTHON" -m pip install playwright python-dotenv

echo "Installing Playwright browsers..."
"$VENV_PYTHON" -m playwright install

if [ ! -f ".env" ]; then
  echo "Creating .env file..."
  cat > .env <<'EOF'
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
echo "$VENV_PYTHON menzatest.py"