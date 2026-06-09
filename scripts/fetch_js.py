"""Playwright-based fetcher for JS-rendered pages (and bot-walled downloads).

Usage:
  python scripts/fetch_js.py <url>                # print rendered HTML
  python scripts/fetch_js.py <url> --pdf out.pdf  # download a file via browser context
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from corpus_lib import USER_AGENT


def fetch_rendered(url: str, timeout_ms: int = 45000) -> tuple[str, str, int]:
    """Return (html, final_url, status) after JS rendering."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, ignore_https_errors=True)
        page = context.new_page()
        response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass  # networkidle is best-effort; DOM content is enough
        html = page.content()
        final_url = page.url
        status = response.status if response else 0
        browser.close()
    return html, final_url, status


def fetch_binary(url: str, out_path: Path, timeout_ms: int = 90000) -> tuple[int, str, str]:
    """Download a binary (PDF) through a browser context. Returns (status, final_url, mime)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, ignore_https_errors=True)
        response = context.request.get(url, timeout=timeout_ms)
        status = response.status
        mime = response.headers.get("content-type", "")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.body())
        browser.close()
    return status, url, mime


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    target = sys.argv[1]
    if "--pdf" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--pdf") + 1])
        status, final, mime = fetch_binary(target, out)
        print(f"status={status} mime={mime} -> {out}")
    else:
        html, final, status = fetch_rendered(target)
        print(html)
        print(f"\n<!-- status={status} final_url={final} -->", file=sys.stderr)
