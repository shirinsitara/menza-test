# Menza Dashboard Scraper

## Terminal Instructions

### 1. Setup
```bash
python setup.py
```
Installs dependencies, creates the virtual environment, and writes the `.env` file with correct settings (including `HEADLESS=true` forced).

### 2. Run manually
```bash
.venv/bin/python menzatest.py
```
On Windows:
```bash
.venv\Scripts\python.exe menzatest.py
```

### 3. Setup regular updates via a scheduled job
```bash
python setup_cronjob.py
```
- **Mac/Linux**: installs a crontab entry (hourly by default)
- **Windows**: installs a Windows Task Scheduler job

Overlapping runs are prevented automatically (`flock` on Mac/Linux, `MultipleInstancesPolicy=IgnoreNew` on Windows).

---

## Tradeoffs

- UI selectors can still break if the authentication flow changes significantly
- Network inspection improves resilience, but depends on dashboard data being exposed in JSON responses
- The script favors robustness and readability over minimalism
- `HEADLESS` is always forced to `true` in the `.env` to ensure compatibility with scheduled/headless environments
- For ease of test run, values of email and password are hardcoded into the `.env` file during setup.

---

## Conversation with AI

1. Reviewing Playwright script structure
2. Debugging cron failures caused by `HEADLESS=false` in `.env`
3. Creating cross-platform `setup.py` and `setup_cronjob.py` to replace bash scripts
4. Checking submission completeness
