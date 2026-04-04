#!/usr/bin/env bash

set -e

echo "🔧 Setting up Menza project..."

# Detect python
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
  echo "❌ Python3 is required but not installed."
  exit 1
fi

# Create venv if not exists
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment..."
  $PYTHON_CMD -m venv .venv
fi

# Activate venv
echo "⚡ Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install playwright python-dotenv

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
  echo "📝 Creating .env file..."
  cat <<EOF > .env
BASE_URL=https://app.menza.ai
MENZA_EMAIL=test123@menza.ai
MENZA_PASSWORD=menzatest
OUTPUT_FILE=dashboard_titles.json
HEADLESS=true
EOF
fi

echo ""
echo "✅ Setup complete!"
echo "👉 Run your script with:"
echo "To run the program enter: source .venv/bin/activate && python menzatest.py"
