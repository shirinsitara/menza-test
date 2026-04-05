#!/usr/bin/env python3
"""
setup_cronjob.py - Cross-platform scheduler setup for Menza scraper.

  Mac/Linux : installs a crontab entry (with flock on Linux/Mac if available)
  Windows   : installs a Windows Task Scheduler task

Run with: python setup_cronjob.py  OR  python3 setup_cronjob.py
"""

import os
import sys
import platform
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS  = platform.system() == "Windows"
IS_MAC      = platform.system() == "Darwin"

VENV_PYTHON = (
    os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
    if IS_WINDOWS
    else os.path.join(PROJECT_DIR, ".venv", "bin", "python")
)
SCRIPT_PATH = os.path.join(PROJECT_DIR, "menzatest.py")
LOG_PATH    = os.path.join(PROJECT_DIR, "cron.log")
LOCK_FILE   = "/tmp/menza.lock"

# How often to run (change here to adjust everywhere)
INTERVAL_MINUTES = 60   # 1 hour — safe default to avoid bot detection


def step(msg: str) -> None:
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def check_venv() -> None:
    if not os.path.isfile(VENV_PYTHON):
        print("ERROR: Virtual environment not found.")
        print("  Run setup.py first: python setup.py")
        sys.exit(1)


# ------------------------------------------------------------------
# Mac / Linux  — crontab
# ------------------------------------------------------------------

def flock_available() -> bool:
    """flock exists on Linux; not always on Mac (brew install util-linux)."""
    import shutil
    return shutil.which("flock") is not None


def build_cron_command() -> str:
    base = f"cd {PROJECT_DIR} && {VENV_PYTHON} {SCRIPT_PATH} >> {LOG_PATH} 2>&1"
    if flock_available():
        return f"flock -n {LOCK_FILE} bash -c '{base}'"
    else:
        return base


def cron_schedule() -> str:
    if INTERVAL_MINUTES == 60:
        return "0 * * * *"
    return f"*/{INTERVAL_MINUTES} * * * *"


def install_crontab() -> None:
    schedule = cron_schedule()
    command  = build_cron_command()
    cron_line = f"{schedule} {command}"

    # Read existing crontab, strip any old menzatest.py entries
    try:
        existing = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True
        ).stdout
    except Exception:
        existing = ""

    lines = [l for l in existing.splitlines() if "menzatest.py" not in l]
    lines.append(cron_line)
    new_crontab = "\n".join(lines) + "\n"

    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True)
    if proc.returncode != 0:
        print("ERROR: Failed to install crontab.")
        sys.exit(1)

    print(f"  Cron job installed.")
    print(f"  Schedule : {schedule}  ({INTERVAL_MINUTES} min interval)")
    print(f"  Command  : {cron_line}")
    print(f"  Log      : {LOG_PATH}")

    if not flock_available():
        print("\n  WARNING: 'flock' not found — overlapping runs are not prevented.")
        print("  On Mac, install with: brew install util-linux")
        print("  On Linux: sudo apt install util-linux  (usually pre-installed)")


# ------------------------------------------------------------------
# Windows — Task Scheduler
# ------------------------------------------------------------------

TASK_NAME = "MenzaScraper"


def install_task_scheduler() -> None:
    # Delete existing task silently if it exists
    subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True
    )

    # Build the action command
    action = f'"{VENV_PYTHON}" "{SCRIPT_PATH}"'

    # Build XML for the task (gives us full control over settings)
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT{INTERVAL_MINUTES}M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2024-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{VENV_PYTHON}</Command>
      <Arguments>"{SCRIPT_PATH}"</Arguments>
      <WorkingDirectory>{PROJECT_DIR}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    xml_path = os.path.join(PROJECT_DIR, "_task.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(xml)

    result = subprocess.run(
        ["schtasks", "/create", "/tn", TASK_NAME, "/xml", xml_path],
        capture_output=True, text=True
    )

    os.remove(xml_path)

    if result.returncode != 0:
        print("ERROR: Failed to create scheduled task.")
        print(result.stderr)
        sys.exit(1)

    print(f"  Windows Task Scheduler job installed.")
    print(f"  Task name : {TASK_NAME}")
    print(f"  Interval  : every {INTERVAL_MINUTES} minutes")
    print(f"  Note      : MultipleInstancesPolicy=IgnoreNew prevents overlapping runs.")
    print(f"\n  To view:   schtasks /query /tn {TASK_NAME}")
    print(f"  To remove: schtasks /delete /tn {TASK_NAME} /f")
    print(f"\n  NOTE: Logs go to cron.log but you must redirect manually on Windows.")
    print(f"  Consider editing the task in Task Scheduler to add output redirection.")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main() -> None:
    print("\nSetting up Menza scheduler...")
    print(f"Platform : {platform.system()}")
    print(f"Project  : {PROJECT_DIR}")
    print(f"Interval : every {INTERVAL_MINUTES} minutes")

    step("Checking virtual environment")
    check_venv()

    if IS_WINDOWS:
        step("Installing Windows Task Scheduler job")
        install_task_scheduler()
    else:
        step("Installing crontab entry (Mac / Linux)")
        install_crontab()

    print("\n" + "="*60)
    print("  Scheduler setup complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()