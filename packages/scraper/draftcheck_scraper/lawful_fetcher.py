from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


ALLOWED_PUBLIC_HOST_HINTS = (
    ".wa.gov.au",
    ".gov.au",
    "planning.wa.gov.au",
    "legislation.wa.gov.au",
    "dfes.wa.gov.au",
    "abcb.gov.au",
    "ncc.abcb.gov.au",
    "standards.org.au",
)

RESTRICTED_TERMS = ("paywall", "login required", "captcha")


@dataclass(frozen=True)
class FetchResult:
    url: str
    content_type: str
    content: bytes
    status_code: int
    robots_allowed: bool = True


def assert_lawful_source(url: str, licence_notes: str = "", access_type: str = "public") -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public HTTP(S) URLs can be fetched")

    host = parsed.hostname.lower()
    allowed = any(host == hint.removeprefix(".") or host.endswith(hint) for hint in ALLOWED_PUBLIC_HOST_HINTS)
    if not allowed:
        raise ValueError("URL is outside the default public official-source allowlist")

    notes = f"{licence_notes} {access_type}".lower()
    if access_type not in {"public", "unknown"}:
        raise ValueError("Only public sources can be fetched automatically")
    if any(term in notes for term in RESTRICTED_TERMS):
        raise ValueError("Source metadata indicates restricted access")


async def fetch_public_text(url: str, licence_notes: str = "", access_type: str = "public") -> FetchResult:
    return await fetch_public_content(url, licence_notes, access_type)


async def fetch_public_content(
    url: str, licence_notes: str = "", access_type: str = "public"
) -> FetchResult:
    assert_lawful_source(url, licence_notes, access_type)
    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"user-agent": "DraftCheckWA-Core/0.1 lawful-public-source-fetcher"},
        follow_redirects=True,
    ) as client:
        robots_allowed = await robots_allows(client, url)
        if not robots_allowed:
            raise ValueError("robots.txt disallows this URL for automated fetch")
        response = await client.get(url)
    response.raise_for_status()
    return FetchResult(
        url=str(response.url),
        content_type=response.headers.get("content-type", "text/plain"),
        content=response.content,
        status_code=response.status_code,
        robots_allowed=robots_allowed,
    )


async def discover_sitemap_urls(url: str) -> list[str]:
    assert_lawful_source(url)
    parsed = urlparse(url)
    sitemap_url = f"{parsed.scheme}://{parsed.hostname}/sitemap.xml"
    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"user-agent": "DraftCheckWA-Core/0.1 lawful-public-source-fetcher"},
        follow_redirects=True,
    ) as client:
        response = await client.get(sitemap_url)
    if response.status_code >= 400:
        return []
    return [
        loc.strip()
        for loc in response.text.replace("</loc>", "<loc>").split("<loc>")
        if loc.strip().startswith("http")
    ]


async def robots_allows(client: httpx.AsyncClient, url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.hostname}/robots.txt"
    try:
        response = await client.get(robots_url)
    except httpx.HTTPError:
        return True
    if response.status_code >= 400:
        return True
    return parse_robots_allows(response.text, parsed.path or "/")


def parse_robots_allows(robots_text: str, path: str, user_agent: str = "*") -> bool:
    active = False
    rules: list[str] = []
    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            active = value == "*" or value.lower() == user_agent.lower()
            continue
        if active and key == "disallow":
            rules.append(value)
    for rule in rules:
        if rule and path.startswith(rule):
            return False
    return True
