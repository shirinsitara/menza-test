#!/usr/bin/env python3
"""
setup.py - Cross-platform setup for Menza scraper (Mac, Linux, Windows)
Run with: python setup.py  OR  python3 setup.py
"""

import os
import sys
import shutil
import subprocess
import platform

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = platform.system() == "Windows"

VENV_DIR = os.path.join(PROJECT_DIR, ".venv")
VENV_PYTHON = (
    os.path.join(VENV_DIR, "Scripts", "python.exe")
    if IS_WINDOWS
    else os.path.join(VENV_DIR, "bin", "python")
)
ENV_FILE = os.path.join(PROJECT_DIR, ".env")


def step(msg: str) -> None:
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def run(cmd: list[str], **kwargs) -> None:
    print(f"  > {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"\nERROR: Command failed: {' '.join(cmd)}")
        sys.exit(result.returncode)


def find_python() -> str:
    """Find a usable Python 3.10+ executable."""
    candidates = ["python3", "python", "py"]
    for cmd in candidates:
        path = shutil.which(cmd)
        if not path:
            continue
        try:
            result = subprocess.run(
                [path, "-c", "import sys; print(sys.version_info[:2])"],
                capture_output=True, text=True
            )
            version = eval(result.stdout.strip())
            if version >= (3, 10):
                print(f"  Found Python {version[0]}.{version[1]} at: {path}")
                return path
        except Exception:
            continue
    print("ERROR: Python 3.10+ is required but was not found.")
    print("Install it from https://www.python.org/downloads/ and try again.")
    sys.exit(1)


def create_venv(python_cmd: str) -> None:
    if os.path.isfile(VENV_PYTHON):
        print("  Virtual environment already exists, skipping.")
        return
    run([python_cmd, "-m", "venv", VENV_DIR])


def install_dependencies() -> None:
    run([VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip"])
    run([VENV_PYTHON, "-m", "pip", "install", "playwright", "python-dotenv"])
    run([VENV_PYTHON, "-m", "playwright", "install", "chromium"])


def write_env_file() -> None:
    """
    Write .env file, always forcing HEADLESS=true.
    Preserves existing EMAIL/PASSWORD if already set.
    """
    existing: dict[str, str] = {}

    if os.path.isfile(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    existing[k.strip()] = v.strip()

    # Always force these values
    existing["BASE_URL"]     = existing.get("BASE_URL", "https://app.menza.ai")
    existing["MENZA_EMAIL"]  = existing.get("MENZA_EMAIL", "test123@menza.ai")
    existing["MENZA_PASSWORD"] = existing.get("MENZA_PASSWORD", "menzatest")
    existing["OUTPUT_FILE"]  = os.path.join(PROJECT_DIR, "dashboard_titles.json")
    existing["HEADLESS"]     = "true"   # always forced
    existing["DEBUG"]        = existing.get("DEBUG", "false")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    print(f"  .env written to: {ENV_FILE}")
    print("  HEADLESS forcibly set to: true")


def main() -> None:
    print("\nSetting up Menza scraper...")
    print(f"Platform : {platform.system()}")
    print(f"Project  : {PROJECT_DIR}")

    step("1/4  Finding Python")
    python_cmd = find_python()

    step("2/4  Creating virtual environment")
    create_venv(python_cmd)

    step("3/4  Installing dependencies")
    install_dependencies()

    step("4/4  Writing .env file")
    write_env_file()

    print("\n" + "="*60)
    print("  Setup complete!")
    print(f"\n  To run manually:")
    if IS_WINDOWS:
        print(f"    {VENV_PYTHON} menzatest.py")
    else:
        print(f"    {VENV_PYTHON} menzatest.py")
    print(f"\n  To install the cron/scheduler job:")
    print(f"    python setup_cronjob.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()