"""Acquisition engine: download every manifest row's document.

Used two ways:
  - imported by pipeline.py (streaming parallel mode — preferred)
  - CLI sweep: python scripts/acquire_all.py [--ids PC-001,PC-002] [--limit N]

For each row with status=pending and a canonical_url:
  1. URL ends .pdf            -> download to corpus/docs/{id}/source.pdf
  2. landing/collection page  -> resolve best PDF link (up to 2 hops), download
  3. JS-render symptoms       -> playwright fallback (rendered DOM + browser download)
  4. write corpus/docs/{id}/meta.json
404/410 after retries -> caller marks status=blocked.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from corpus_lib import (
    REPORTS_ROOT,
    USER_AGENT,
    append_report,
    doc_dir,
    log,
    normalize_name,
    read_manifest,
    sha256_bytes,
    sha256_file,
    today,
    update_row,
    utcnow,
    write_manifest,
)

ACQ_REPORT = REPORTS_ROOT / "acquisition_report.json"

JS_SYMPTOMS = (
    "enable javascript",
    "javascript is required",
    "you need to enable javascript",
    "window.__nuxt__",
    "window.__next_data__",
)

STOP_TOKENS = {"the", "of", "and", "for", "a", "an", "no", "wa", "city", "town", "shire"}


def looks_like_pdf(content: bytes, mime: str) -> bool:
    return content[:5] == b"%PDF-" or "pdf" in mime.lower()


def js_render_symptoms(html: str) -> bool:
    low = html.lower()
    if any(s in low for s in JS_SYMPTOMS):
        return True
    text = re.sub(r"<script.*?</script>", "", low, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return len(text.strip()) < 600


def name_tokens(name: str) -> set[str]:
    return {t for t in normalize_name(name).split() if t not in STOP_TOKENS and len(t) > 2}


def score_link(href: str, text: str, tokens: set[str]) -> float:
    score = 0.0
    href_low = href.lower()
    if re.search(r"\.pdf($|\?)", href_low):
        score += 4
    if any(k in href_low for k in ("/media/", "/download", "/files/", "getmedia", "documents")):
        score += 1
    link_tokens = name_tokens(text) | name_tokens(href_low.rsplit("/", 1)[-1].replace("-", " ").replace("_", " "))
    overlap = tokens & link_tokens
    score += 1.5 * len(overlap)
    if "volume" in text.lower():
        score += 0.5
    return score


def find_candidate_links(html: str, base_url: str, instrument_name: str) -> list[tuple[float, str, str, bool]]:
    """Return [(score, abs_url, text, is_pdf)] sorted best-first."""
    soup = BeautifulSoup(html, "lxml")
    tokens = name_tokens(instrument_name)
    seen: set[str] = set()
    out: list[tuple[float, str, str, bool]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        abs_url = urljoin(base_url, href)
        if abs_url in seen:
            continue
        seen.add(abs_url)
        text = " ".join(a.get_text(" ", strip=True).split())
        is_pdf = bool(re.search(r"\.pdf($|\?)", abs_url.lower()))
        s = score_link(abs_url, text, tokens)
        if s > 0:
            out.append((s, abs_url, text, is_pdf))
    out.sort(key=lambda t: -t[0])
    return out


async def http_get(client: httpx.AsyncClient, url: str, attempts: int = 2) -> httpx.Response:
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            resp = await client.get(url)
            if resp.status_code in (429, 502, 503) and i + 1 < attempts:
                await asyncio.sleep(3.0 * (i + 1))
                continue
            return resp
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last_exc = exc
            await asyncio.sleep(2.0 * (i + 1))
    raise last_exc  # type: ignore[misc]


def _playwright_render(url: str) -> tuple[str, str, int]:
    from fetch_js import fetch_rendered

    return fetch_rendered(url)


def _playwright_download(url: str, out_path: Path) -> tuple[int, str, str]:
    from fetch_js import fetch_binary

    return fetch_binary(url, out_path)


def save_document(row_id: str, content: bytes, mime: str) -> tuple[Path, str, str]:
    """Write content to docs/{id}/source.{pdf|html}; returns (path, hash, note)."""
    is_pdf = looks_like_pdf(content, mime)
    target = doc_dir(row_id) / ("source.pdf" if is_pdf else "source.html")
    new_hash = sha256_bytes(content)
    note = ""
    if target.exists():
        if sha256_file(target) == new_hash:
            return target, new_hash, "unchanged (hash match, not rewritten)"
        note = "content changed since previous fetch; overwritten"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target, new_hash, note


async def acquire_row(client: httpx.AsyncClient, row: dict) -> dict:
    """Acquire one manifest row. Returns a result dict; never raises."""
    row_id = row["id"]
    url = (row.get("canonical_url") or "").strip()
    result: dict = {"id": row_id, "url": url, "ok": False, "fetched_at": utcnow()}
    if not url:
        result["error"] = "blank canonical_url"
        return result
    try:
        resp = await http_get(client, url)
        mime = resp.headers.get("content-type", "")
        final_url = str(resp.url)
        if resp.status_code in (404, 410):
            result.update(error=f"dead URL (HTTP {resp.status_code})", http_status=resp.status_code, dead=True)
            return result
        body = resp.content
        used_playwright = False

        # Bot-wall / JS shell on an expected-PDF or landing page -> playwright render
        if resp.status_code >= 400 or (not looks_like_pdf(body, mime) and js_render_symptoms(body.decode("utf-8", "replace"))):
            html, final_url, status = await asyncio.to_thread(_playwright_render, url)
            used_playwright = True
            if status in (404, 410):
                result.update(error=f"dead URL (HTTP {status}, playwright)", http_status=status, dead=True)
                return result
            body, mime = html.encode("utf-8"), "text/html"
            resp_status = status or resp.status_code
        else:
            resp_status = resp.status_code

        # Landing page -> resolve PDF link, up to 2 hops
        hops = 0
        while not looks_like_pdf(body, mime) and hops < 2:
            html_text = body.decode("utf-8", "replace")
            candidates = find_candidate_links(html_text, final_url, row["instrument_name"])
            if not candidates:
                break
            _, best_url, _, best_is_pdf = candidates[0]
            if best_url.rstrip("/") == final_url.rstrip("/"):
                break
            if best_is_pdf:
                pdf_resp = await http_get(client, best_url)
                if pdf_resp.status_code < 400 and looks_like_pdf(pdf_resp.content, pdf_resp.headers.get("content-type", "")):
                    body, mime = pdf_resp.content, pdf_resp.headers.get("content-type", "application/pdf")
                    final_url, resp_status = str(pdf_resp.url), pdf_resp.status_code
                    break
                # PDF link rejected plain HTTP -> browser download
                target = doc_dir(row_id) / "source.pdf"
                status, _, dl_mime = await asyncio.to_thread(_playwright_download, best_url, target)
                used_playwright = True
                if status < 400 and looks_like_pdf(target.read_bytes()[:8], dl_mime):
                    body, mime, final_url, resp_status = target.read_bytes(), dl_mime or "application/pdf", best_url, status
                    break
                break
            # best link is another HTML page (publication page) -> follow one hop
            hop_resp = await http_get(client, best_url)
            if hop_resp.status_code >= 400:
                break
            body, mime = hop_resp.content, hop_resp.headers.get("content-type", "")
            final_url, resp_status = str(hop_resp.url), hop_resp.status_code
            hops += 1

        # empty/truncated body with a PDF mime -> server gated plain HTTP; browser retry
        if len(body) < 1000:
            target = doc_dir(row_id) / "source.pdf"
            status, _, dl_mime = await asyncio.to_thread(_playwright_download, final_url, target)
            used_playwright = True
            if status < 400 and target.stat().st_size >= 1000:
                body, mime, resp_status = target.read_bytes(), dl_mime or "application/pdf", status
            else:
                result["error"] = f"empty body from {final_url[:90]} (HTTP {resp_status}, browser retry HTTP {status})"
                return result

        if not looks_like_pdf(body, mime) and row.get("category") not in ("HTML", "metadata"):
            # keep HTML if that's all the source offers, but flag it
            result["note_extra"] = "no PDF resolved; saved page HTML"

        path, content_hash, note = save_document(row_id, body, mime)
        meta = {
            "url": url,
            "fetched_at": result["fetched_at"],
            "http_status": resp_status,
            "content_hash": content_hash,
            "mime_type": "application/pdf" if path.suffix == ".pdf" else (mime.split(";")[0] or "text/html"),
            "final_url": final_url,
            "used_playwright": used_playwright,
            "bytes": path.stat().st_size,
        }
        (doc_dir(row_id) / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        result.update(ok=True, path=str(path), hash=content_hash, http_status=resp_status,
                      final_url=final_url, mime=meta["mime_type"], note=note)
        return result
    except Exception as exc:  # noqa: BLE001 — must never kill the sweep
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        follow_redirects=True,
        timeout=httpx.Timeout(60.0, connect=20.0),
        limits=httpx.Limits(max_connections=8, max_keepalive_connections=8),
    )


async def _cli_sweep(ids: list[str] | None, limit: int | None) -> None:
    rows = read_manifest()
    todo = [r for r in rows if r["status"] == "pending" and r.get("canonical_url", "").strip()]
    if ids:
        todo = [r for r in todo if r["id"] in ids]
    if limit:
        todo = todo[:limit]
    log(f"acquiring {len(todo)} rows")
    sem = asyncio.Semaphore(4)
    async with make_client() as client:
        async def run(row: dict) -> dict:
            async with sem:
                res = await acquire_row(client, row)
                append_report(ACQ_REPORT, res)
                if res.get("ok"):
                    update_row(rows, row["id"], status="acquired", last_checked_at=today(),
                               notes=(row.get("notes", "") + " | " + res.get("note", "")).strip(" |"))
                elif res.get("dead"):
                    update_row(rows, row["id"], status="blocked", last_checked_at=today(),
                               notes=f"dead URL: {res.get('error')} {row.get('canonical_url')}")
                write_manifest(rows)
                log(f"{row['id']}: {'OK' if res.get('ok') else res.get('error')}")
                return res

        await asyncio.gather(*(run(r) for r in todo))


if __name__ == "__main__":
    arg_ids = None
    arg_limit = None
    if "--ids" in sys.argv:
        arg_ids = sys.argv[sys.argv.index("--ids") + 1].split(",")
    if "--limit" in sys.argv:
        arg_limit = int(sys.argv[sys.argv.index("--limit") + 1])
    asyncio.run(_cli_sweep(arg_ids, arg_limit))
