#!/usr/bin/env python3

import json
import re
import sys
import os
import time
from dataclasses import dataclass, asdict
from typing import Any, Iterable
from dotenv import load_dotenv

from playwright.sync_api import Page, Response, TimeoutError, sync_playwright

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://app.menza.ai")
EMAIL = os.getenv("MENZA_EMAIL")
PASSWORD = os.getenv("MENZA_PASSWORD")
OUTPUT = os.getenv("OUTPUT_FILE", "dashboard_titles.json")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

DEBUG = False

if not EMAIL or not PASSWORD:
    raise RuntimeError("Missing MENZA_EMAIL or MENZA_PASSWORD environment variables.")

# BASE_URL = "https://app.menza.ai"
# EMAIL = "test123@menza.ai"
# PASSWORD = "menzatest"
# OUTPUT = "dashboard_titles.json"
# HEADLESS = False
# DEBUG = True


COMMON_NON_DASHBOARD_TERMS = {
    "dashboard", "dashboards","home", "settings", "billing", "logout", "log out",
    "sign out", "help", "support", "search", "new", "create", "edit", "delete",
    "upgrade", "workspace", "workspaces", "members", "team", "account", "profile",
    "back", "next", "previous", "filters", "templates", "view all", "all dashboards",
    "continue", "use another method", "sign in with your password",
}

TITLE_KEYS = {"title", "name", "dashboardTitle", "dashboardName", "displayName", "label"}
LIST_KEYS = {"dashboards", "items", "results", "data", "nodes"}

CANDIDATE_ROUTES = [
    "/",
    "/dashboards",
    "/dashboard",
    "/app",
    "/app/dashboards",
    "/home",
]


@dataclass
class DashboardRecord:
    title: str
    source: str
    page_url: str | None = None


def debug(*args: Any) -> None:
    if DEBUG:
        print("[debug]", *args, file=sys.stderr)


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" -\n\t")


def plausible_title(value: str) -> bool:
    value = normalize_title(value)
    if not value:
        return False
    low = value.lower()
    if low in COMMON_NON_DASHBOARD_TERMS:
        return False
    if len(value) < 3 or len(value) > 120:
        return False
    if re.fullmatch(r"[\W_]+", value):
        return False
    if re.fullmatch(r"\d+", value):
        return False
    bad_patterns = [
        r"^(sign in|log in|email|password)$",
        r"^(open|close|cancel|save|submit)$",
    ]
    return not any(re.search(p, low) for p in bad_patterns)


def dedupe_records(records: Iterable[DashboardRecord]) -> list[DashboardRecord]:
    seen: set[str] = set()
    out: list[DashboardRecord] = []
    for rec in records:
        key = rec.title.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return sorted(out, key=lambda r: r.title.casefold())


def first_visible(page: Page, selectors: list[tuple[str, str]], timeout_ms: int = 2000):
    for kind, value in selectors:
        try:
            if kind == "css":
                loc = page.locator(value).first
            elif kind == "role_button_exact":
                loc = page.get_by_role("button", name=value, exact=True).first
            elif kind == "role_button":
                loc = page.get_by_role("button", name=value).first
            elif kind == "role_link_exact":
                loc = page.get_by_role("link", name=value, exact=True).first
            elif kind == "role_link":
                loc = page.get_by_role("link", name=value).first
            elif kind == "text":
                loc = page.get_by_text(value, exact=True).first
            else:
                continue

            count = loc.count()
            debug("checking selector:", kind, value, "count=", count)

            if count > 0 and loc.is_visible(timeout=timeout_ms):
                debug("matched selector:", kind, value)
                return loc
        except Exception as e:
            debug("selector failed:", kind, value, e)

    return None


def click_first(page: Page, selectors: list[tuple[str, str]], timeout_ms: int = 2000) -> bool:
    loc = first_visible(page, selectors, timeout_ms=timeout_ms)
    if not loc:
        return False
    try:
        loc.click(timeout=timeout_ms)
        return True
    except Exception as e:
        debug("click failed:", e)
        return False


def fill_first(page: Page, selectors: list[tuple[str, str]], value: str, timeout_ms: int = 3000) -> bool:
    loc = first_visible(page, selectors, timeout_ms=timeout_ms)
    if not loc:
        return False
    try:
        loc.fill(value, timeout=timeout_ms)
        return True
    except Exception as e:
        debug("fill failed:", e)
        return False


def wait_briefly(page: Page, ms: int = 1500) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=ms)
    except Exception:
        pass
    page.wait_for_timeout(ms)


def sign_in(page: Page, email: str, password: str) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)

    email_filled = fill_first(page, [
        ("css", 'input[type="email"]'),
        ("css", 'input[name*="email" i]'),
        ("css", 'input[placeholder*="email" i]'),
        ("css", 'input[placeholder*="email address" i]'),
        ("css", 'label:has-text("Email") + input'),
    ], email)

    if not email_filled:
        raise RuntimeError("Could not find the email input.")

    clicked_continue = click_first(page, [
        ("role_button_exact", "Continue"),
        ("css", 'button[type="submit"]'),
        ("css", 'input[type="submit"]'),
    ])

    if not clicked_continue:
        raise RuntimeError("Could not find the email Continue button.")

    wait_briefly(page, 2500)
    debug("URL after email continue:", page.url)

    if "accounts.google.com" in page.url:
        raise RuntimeError("Clicked into Google OAuth instead of the email sign-in flow.")

    use_another_method_visible = first_visible(page, [
        ("role_button_exact", "Use another method"),
        ("text", "Use another method"),
    ], timeout_ms=4000)

    if use_another_method_visible:
        if not click_first(page, [
            ("role_button_exact", "Use another method"),
            ("text", "Use another method"),
        ], timeout_ms=4000):
            raise RuntimeError('Found "Use another method" but could not click it.')
        wait_briefly(page, 2000)

    password_method_visible = first_visible(page, [
        ("role_button_exact", "Sign in with your password"),
        ("text", "Sign in with your password"),
    ], timeout_ms=4000)

    if not password_method_visible:
        raise RuntimeError('Could not find "Sign in with your password".')

    if not click_first(page, [
        ("role_button_exact", "Sign in with your password"),
        ("text", "Sign in with your password"),
    ], timeout_ms=4000):
        raise RuntimeError('Found "Sign in with your password" but could not click it.')

    wait_briefly(page, 2000)

    password_filled = fill_first(page, [
        ("css", 'input[type="password"]'),
        ("css", 'input[name*="password" i]'),
        ("css", 'input[placeholder*="password" i]'),
        ("css", 'input[autocomplete="current-password"]'),
        ("css", 'label:has-text("Password") + input'),
    ], password, timeout_ms=4000)

    if not password_filled:
        raise RuntimeError("Could not find the password input after switching methods.")

    clicked_password_continue = click_first(page, [
        ("role_button_exact", "Continue"),
        ("role_button_exact", "Sign in"),
        ("css", 'button[type="submit"]'),
        ("css", 'input[type="submit"]'),
    ], timeout_ms=3000)

    if not clicked_password_continue:
        raise RuntimeError("Could not find the password submit button.")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except TimeoutError:
        debug("Timed out waiting for final networkidle.")

    page.wait_for_timeout(4000)
    debug("Final sign-in URL:", page.url)


def safe_json(response: Response) -> Any | None:
    try:
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type and not response.url.endswith(".json"):
            return None
        return response.json()
    except Exception:
        return None


def walk_for_dashboard_titles(obj: Any, hits: list[str]) -> None:
    if isinstance(obj, dict):
        if any(k in obj for k in TITLE_KEYS):
            title_candidates = [obj.get(k) for k in TITLE_KEYS if isinstance(obj.get(k), str)]
            if any("dashboard" in str(k).lower() for k in obj.keys()):
                for t in title_candidates:
                    if plausible_title(t):
                        hits.append(normalize_title(t))

        for k, v in obj.items():
            kl = str(k).lower()
            if kl in {x.lower() for x in LIST_KEYS} or "dashboard" in kl:
                walk_for_dashboard_titles(v, hits)
            elif isinstance(v, (dict, list)):
                walk_for_dashboard_titles(v, hits)

    elif isinstance(obj, list):
        for item in obj:
            walk_for_dashboard_titles(item, hits)


def attach_network_collector(page: Page, bucket: list[DashboardRecord]) -> None:
    def on_response(response: Response) -> None:
        try:
            parsed = safe_json(response)
            if parsed is None:
                return
            titles: list[str] = []
            walk_for_dashboard_titles(parsed, titles)
            if titles:
                for t in titles:
                    bucket.append(
                        DashboardRecord(
                            title=t,
                            source=f"network:{response.url}",
                            page_url=page.url,
                        )
                    )
        except Exception as exc:
            debug("network collector error:", exc)

    page.on("response", on_response)


def go_to_dashboard_area(page: Page) -> None:
    clicked = click_first(page, [
        ("role_link_exact", "Dashboards"),
        ("role_button_exact", "Dashboards"),
        ("role_link", "Dashboard"),
        ("role_button", "Dashboard"),
    ], timeout_ms=2000)

    if clicked:
        wait_briefly(page, 3000)
        return

    for route in CANDIDATE_ROUTES:
        try:
            url = f"{BASE_URL}{route}"
            debug("trying route:", url)
            page.goto(url, wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(1500)

            if "sign-in" not in page.url.lower():
                return
        except Exception as e:
            debug("route failed:", route, e)


def extract_ui_titles(page: Page) -> list[DashboardRecord]:
    selectors = [
        'main h1',
        'main h2',
        'main h3',
        '[role="main"] h1',
        '[role="main"] h2',
        '[role="main"] h3',
        'a[href*="dashboard"]',
        '[data-testid*="dashboard" i]',
        '[class*="dashboard" i]',
    ]

    records: list[DashboardRecord] = []

    for sel in selectors:
        try:
            loc = page.locator(sel)
            count = min(loc.count(), 200)
            debug("scanning selector:", sel, "count=", count)

            for i in range(count):
                el = loc.nth(i)
                try:
                    if not el.is_visible(timeout=300):
                        continue
                    raw_text = normalize_title(el.inner_text(timeout=500))
                    text = clean_dashboard_card_text(raw_text)
                except Exception:
                    continue

                if not plausible_title(text):
                    continue

                attr_blob = " ".join(filter(None, [
                    el.get_attribute("href") or "",
                    el.get_attribute("data-testid") or "",
                    el.get_attribute("class") or "",
                    el.get_attribute("aria-label") or "",
                ]))

                context = f"{sel} {attr_blob}".lower()

                if "dashboard" in context or sel.startswith("main h") or sel.startswith('[role="main"]'):
                    records.append(DashboardRecord(title=text, source=f"ui:{sel}", page_url=page.url))
        except Exception as e:
            debug("ui scan failed:", sel, e)

    return records


def extract_dashboard_titles(page: Page, network_hits: list[DashboardRecord]) -> list[DashboardRecord]:
    go_to_dashboard_area(page)

    for _ in range(3):
        try:
            page.mouse.wheel(0, 1500)
        except Exception:
            pass
        page.wait_for_timeout(1000)

    click_first(page, [
        ("role_button_exact", "All"),
        ("role_button_exact", "View all"),
        ("role_button_exact", "Show more"),
    ], timeout_ms=1000)

    page.wait_for_timeout(2500)

    ui_hits = extract_ui_titles(page)
    return dedupe_records(network_hits + ui_hits)

def clean_dashboard_card_text(value: str) -> str:
    value = normalize_title(value)

    value = re.sub(
        r"\s+You\s+\d+\s+(minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\s+ago$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    return normalize_title(value)


def save_results(titles: list[str]) -> None:
    payload = {
        "last_updated_epoch": int(time.time()),
        "count": len(titles),
        "dashboard_titles": titles,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        network_hits: list[DashboardRecord] = []
        attach_network_collector(page, network_hits)

        try:
            sign_in(page, EMAIL, PASSWORD)

            results = extract_dashboard_titles(page, network_hits)

            if not results:
                debug("First attempt returned 0 dashboards. Retrying...")
                page.wait_for_timeout(5000)
                go_to_dashboard_area(page)
                page.wait_for_timeout(3000)
                results = extract_dashboard_titles(page, network_hits)

            titles = [r.title for r in results]

            save_results(titles)

            print(json.dumps({
                "last_updated_epoch": int(time.time()),
                "count": len(titles),
                "dashboard_titles": titles,
            }, indent=2, ensure_ascii=False))

            return 0
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        error_payload = {
            "base_url": BASE_URL,
            "fetched_at_epoch": int(time.time()),
            "error": str(e),
        }

        with open("dashboard_titles_errors.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(error_payload, ensure_ascii=False) + "\n")

        print(json.dumps(error_payload, indent=2, ensure_ascii=False), file=sys.stderr)
        raise