"""Lawful public source fetching helpers for V3 source ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import httpx


USER_AGENT = "DraftCheckWA-Core/0.1 lawful-public-source-fetcher"
RESTRICTED_TERMS = (
    "login",
    "signin",
    "password",
    "private",
    "cart",
    "checkout",
    "captcha",
)


@dataclass(frozen=True)
class PublicSourceFetch:
    final_url: str
    status_code: int
    content_type: str
    text: str
    sha256: str
    metadata: dict[str, object]


def fetch_public_source(
    url: str,
    *,
    licence_notes: str = "",
    timeout_seconds: float = 20.0,
) -> PublicSourceFetch:
    """Fetch and parse a public source without bypassing access controls."""

    _assert_lawful_public_url(url, licence_notes=licence_notes)
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout_seconds,
        headers={"user-agent": USER_AGENT},
    ) as client:
        if not robots_allows(client, url):
            raise ValueError("robots.txt disallows this URL for automated fetch")
        response = client.get(url)
        if response.status_code in {401, 402, 403}:
            raise ValueError(f"source requires restricted access: HTTP {response.status_code}")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "application/octet-stream")
        text = extract_source_text(
            response.content,
            content_type=content_type,
            final_url=str(response.url),
        )
        if not text.strip():
            raise ValueError("source fetch produced no parseable text")
        digest = sha256(response.content).hexdigest()
        return PublicSourceFetch(
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            text=text,
            sha256=digest,
            metadata={
                "http_status": response.status_code,
                "content_type": content_type,
                "final_url": str(response.url),
                "raw_sha256": digest,
                "robots_allowed": True,
                "parser": "draftcheck.sources.public_fetch.v0",
            },
        )


def robots_allows(client: httpx.Client, url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = client.get(robots_url)
    except httpx.HTTPError:
        return False
    if response.status_code == 404:
        return True
    if response.status_code >= 400:
        return False
    return parse_robots_allows(response.text, parsed.path or "/")


def parse_robots_allows(robots_text: str, path: str) -> bool:
    rules: list[tuple[str, str]] = []
    active = False
    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            active = value in {"*", USER_AGENT}
            continue
        if active and key in {"allow", "disallow"}:
            rules.append((key, value))
    matched: tuple[str, str] | None = None
    for key, value in rules:
        if not value:
            continue
        if path.startswith(value) and (matched is None or len(value) > len(matched[1])):
            matched = (key, value)
    return matched is None or matched[0] == "allow"


def extract_source_text(content: bytes, *, content_type: str, final_url: str) -> str:
    lowered_type = content_type.lower()
    lowered_url = final_url.lower()
    if "pdf" in lowered_type or lowered_url.endswith(".pdf"):
        return _extract_pdf_text(content)
    if "html" in lowered_type or lowered_url.endswith((".html", ".htm", "/")):
        return _extract_html_text(content, final_url=final_url)
    return content.decode("utf-8", errors="ignore").strip()


def _extract_html_text(content: bytes, *, final_url: str) -> str:
    soup = BeautifulSoup(content, "html.parser")
    for node in soup(["script", "style", "noscript", "svg"]):
        node.extract()
    parts: list[str] = []
    title = soup.find("title")
    if title and title.get_text(strip=True):
        parts.append(title.get_text(" ", strip=True))
    for selector in ("h1", "h2", "h3", "p", "li"):
        for node in soup.find_all(selector):
            text = " ".join(node.get_text(" ", strip=True).split())
            if text and text not in parts:
                parts.append(text)
    links = _candidate_links(soup, final_url=final_url)
    if links:
        parts.append("Candidate public source links:\n" + "\n".join(links[:80]))
    return "\n\n".join(parts).strip()


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is locked in pyproject
        raise ValueError("PDF parser is unavailable") from exc
    reader = PdfReader(BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(page.strip() for page in pages if page.strip())


def _candidate_links(soup: BeautifulSoup, *, final_url: str) -> list[str]:
    parsed_base = urlparse(final_url)
    candidates: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(("mailto:", "tel:", "#")):
            continue
        absolute = urljoin(final_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != parsed_base.netloc:
            continue
        lowered = absolute.lower()
        if any(term in lowered for term in RESTRICTED_TERMS):
            continue
        label = " ".join(anchor.get_text(" ", strip=True).split())
        if not _looks_like_source_link(lowered, label.lower()):
            continue
        rendered = f"{label}: {absolute}" if label else absolute
        if rendered not in candidates:
            candidates.append(rendered)
    return candidates


def _looks_like_source_link(url: str, label: str) -> bool:
    haystack = f"{url} {label}"
    return any(
        term in haystack
        for term in (
            "planning",
            "policy",
            "scheme",
            "development",
            "r-code",
            "rcode",
            "residential",
            ".pdf",
            ".doc",
            ".docx",
        )
    )


def _assert_lawful_public_url(url: str, *, licence_notes: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("only absolute public HTTP(S) URLs can be fetched")
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        raise ValueError("private/local URLs cannot be fetched as source material")
    lowered = f"{url} {licence_notes}".lower()
    if any(term in lowered for term in RESTRICTED_TERMS):
        raise ValueError("restricted source URL or licence notes require human review")
    if "standards.org.au" in lowered or "standards australia" in lowered:
        raise ValueError("Standards Australia full text is metadata-only unless lawfully supplied")

