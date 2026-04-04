# 6. Setup cron job (runs every 2 minutes)
echo "⏰ Setting up cron job..."

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
SCRIPT_PATH="$PROJECT_DIR/menzatest.py"
LOG_PATH="$PROJECT_DIR/cron.log"

CRON_JOB="*/2 * * * * cd $PROJECT_DIR && $PYTHON_PATH $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Avoid duplicate cron entries
(crontab -l 2>/dev/null | grep -v -F "$SCRIPT_PATH"; echo "$CRON_JOB") | crontab -

echo "✅ Cron job installed (runs every 2 minutes)"
echo "📄 Logs will be written to: $LOG_PATH"