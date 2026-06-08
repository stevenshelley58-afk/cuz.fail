from __future__ import annotations

import asyncio
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urldefrag, urljoin, urlparse

import httpx
import yaml
from bs4 import BeautifulSoup

from draftcheck_document_ai.extraction import extract_text_from_bytes
from draftcheck_scraper.lawful_fetcher import assert_lawful_source, parse_robots_allows


DOCUMENT_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".html",
    ".htm",
)
DOCUMENT_KEYWORDS = (
    "r-code",
    "residential",
    "planning",
    "policy",
    "scheme",
    "bushfire",
    "ncc",
    "building",
    "building-permit",
    "building-application",
    "development-application",
    "development-approval",
    "development",
    "checklist",
    "design-code",
    "form",
    "local-law",
    "local-planning",
    "planning-and-building",
    "planning-application",
    "planning-scheme",
    "scheme-amendment",
    "structure-plan",
)
RESTRICTED_LINK_TERMS = (
    "login",
    "sign-in",
    "signin",
    "captcha",
    "paywall",
    "subscription",
    "cart",
    "checkout",
    "facebook.com",
    "linkedin.com",
    "x.com/intent",
)


@dataclass(frozen=True)
class DiscoverySettings:
    max_depth: int = 1
    max_urls_per_anchor: int = 25
    delay_seconds: float = 1.0
    include_html: bool = False
    user_agent: str = "DraftCheckWA-Core/0.1 lawful-source-discovery"


@dataclass(frozen=True)
class CandidateLink:
    url: str
    label: str
    depth: int = 0


@dataclass(frozen=True)
class DiscoverySummary:
    output_root: str
    anchors_seen: int
    candidates_seen: int
    inventory_rows: int
    parsed_rows: int
    metadata_only_rows: int
    skipped: int
    errors: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _FetchedContent:
    requested_url: str
    final_url: str
    content_type: str
    content: bytes
    status_code: int
    robots_allowed: bool


async def discover_manifest_sources(
    manifest_yaml: str,
    output_root: str | Path,
    settings: DiscoverySettings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> DiscoverySummary:
    discoverer = PublicSourceDiscoverer(output_root, settings or DiscoverySettings(), transport)
    return await discoverer.discover_manifest(manifest_yaml)


class PublicSourceDiscoverer:
    def __init__(
        self,
        output_root: str | Path,
        settings: DiscoverySettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.output_root = Path(output_root).expanduser().resolve()
        self.settings = settings
        self.transport = transport
        self.raw_dir = self.output_root / "raw"
        self.parsed_dir = self.output_root / "parsed"
        self.reports_dir = self.output_root / "reports"
        self.inventory_rows: list[dict[str, Any]] = []
        self.fetch_log_rows: list[dict[str, Any]] = []
        self.error_rows: list[dict[str, Any]] = []
        self._seen_candidates: set[str] = set()
        self._last_fetch_by_host: dict[str, datetime] = {}
        self._robots_text_by_origin: dict[str, str | None] = {}

    async def discover_manifest(self, manifest_yaml: str) -> DiscoverySummary:
        self._ensure_output_dirs()
        entries = _manifest_entries(manifest_yaml)
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={"user-agent": self.settings.user_agent},
            follow_redirects=True,
            transport=self.transport,
        ) as client:
            for entry in entries:
                await self._discover_anchor(client, entry)
        self._write_outputs()
        return self._summary(len(entries))

    async def _discover_anchor(self, client: httpx.AsyncClient, entry: dict[str, Any]) -> None:
        url = _clean_str(entry.get("canonical_url"))
        if not url:
            self._record_error("missing_canonical_url", None, entry, "Source anchor has no canonical_url")
            return
        if not _as_bool(entry.get("scrape_allowed"), default=True):
            self._record_fetch(url, "skipped", None, False, "scrape_allowed=false")
            return
        if _is_standards_candidate(url, entry):
            self._append_metadata_only_row(entry, url, "Standards Australia metadata only; no full text fetched.")
            return
        try:
            assert_lawful_source(url, _clean_str(entry.get("licence_notes")) or "", _access_type(entry))
        except ValueError as exc:
            self._record_fetch(url, "skipped", None, False, str(exc))
            return

        fetched = await self._fetch(client, url, entry)
        if fetched is None:
            return
        self._seen_candidates.add(fetched.final_url)

        content_text = fetched.content.decode("utf-8", errors="ignore")
        if _is_document_response(fetched.final_url, fetched.content_type):
            self._store_parsed_row(entry, CandidateLink(fetched.final_url, _title_from_entry(entry)), fetched)
            return
        if self.settings.include_html and "html" in fetched.content_type.lower():
            self._store_parsed_row(entry, CandidateLink(fetched.final_url, _title_from_entry(entry)), fetched)

        candidates = extract_candidate_links(fetched.final_url, content_text, depth=1)
        candidates.extend(await self._sitemap_candidates(client, fetched.final_url, entry))
        await self._visit_candidates(client, entry, candidates)

    async def _visit_candidates(
        self,
        client: httpx.AsyncClient,
        entry: dict[str, Any],
        candidates: list[CandidateLink],
    ) -> None:
        queue = candidates[:]
        visited_for_anchor = 0
        while queue and visited_for_anchor < self.settings.max_urls_per_anchor:
            candidate = queue.pop(0)
            if candidate.url in self._seen_candidates:
                continue
            self._seen_candidates.add(candidate.url)
            visited_for_anchor += 1

            if _is_standards_candidate(candidate.url, entry):
                self._append_metadata_only_row(
                    entry,
                    candidate.url,
                    "Standards Australia metadata only; no full text fetched.",
                    candidate.label,
                )
                continue

            if _looks_restricted(candidate.url, candidate.label):
                self._record_fetch(candidate.url, "skipped", None, False, "restricted link terms")
                continue

            try:
                assert_lawful_source(
                    candidate.url,
                    _clean_str(entry.get("licence_notes")) or "",
                    _access_type(entry),
                )
            except ValueError as exc:
                self._record_fetch(candidate.url, "skipped", None, False, str(exc))
                continue

            fetched = await self._fetch(client, candidate.url, entry)
            if fetched is None:
                continue

            is_document = _is_document_response(fetched.final_url, fetched.content_type)
            is_html = "html" in fetched.content_type.lower()
            if is_document or (self.settings.include_html and is_html):
                self._store_parsed_row(entry, candidate, fetched)

            if is_html and candidate.depth < self.settings.max_depth:
                html = fetched.content.decode("utf-8", errors="ignore")
                queue.extend(extract_candidate_links(fetched.final_url, html, depth=candidate.depth + 1))

    async def _fetch(
        self,
        client: httpx.AsyncClient,
        url: str,
        entry: dict[str, Any],
    ) -> _FetchedContent | None:
        await self._respect_delay(url)
        try:
            robots_allowed = await self._robots_allows(client, url)
        except Exception as exc:
            self._record_error("robots_check_failed", url, entry, str(exc))
            robots_allowed = False
        if not robots_allowed:
            self._record_fetch(url, "robots_disallowed", None, False, "robots.txt disallowed automated access")
            return None

        try:
            response = await client.get(url)
        except httpx.HTTPError as exc:
            self._record_error("fetch_failed", url, entry, str(exc))
            return None

        status = "success" if response.status_code < 400 else "http_error"
        self._record_fetch(
            url,
            status,
            response.status_code,
            True,
            None if status == "success" else f"HTTP {response.status_code}",
            str(response.url),
            response.headers.get("content-type", ""),
        )
        if response.status_code >= 400:
            return None
        return _FetchedContent(
            requested_url=url,
            final_url=str(response.url),
            content_type=response.headers.get("content-type", "application/octet-stream"),
            content=response.content,
            status_code=response.status_code,
            robots_allowed=True,
        )

    async def _robots_allows(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.hostname}"
        if origin not in self._robots_text_by_origin:
            robots_url = f"{origin}/robots.txt"
            try:
                response = await client.get(robots_url)
            except httpx.HTTPError:
                self._robots_text_by_origin[origin] = None
            else:
                self._robots_text_by_origin[origin] = (
                    None if response.status_code >= 400 else response.text
                )
        robots_text = self._robots_text_by_origin[origin]
        if not robots_text:
            return True
        return parse_robots_allows(robots_text, parsed.path or "/")

    async def _sitemap_candidates(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        entry: dict[str, Any],
    ) -> list[CandidateLink]:
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.hostname}/sitemap.xml"
        if sitemap_url in self._seen_candidates:
            return []
        try:
            sitemap = await self._fetch(client, sitemap_url, entry)
        except Exception as exc:
            self._record_error("sitemap_failed", sitemap_url, entry, str(exc))
            return []
        if sitemap is None:
            return []
        text = sitemap.content.decode("utf-8", errors="ignore")
        candidates: list[CandidateLink] = []
        for loc in re.findall(r"<loc>\s*([^<]+)\s*</loc>", text, flags=re.IGNORECASE):
            normalized = _normalize_url(base_url, loc)
            if not normalized:
                continue
            label = _title_from_url(normalized)
            if _candidate_score(normalized, label) > 0:
                candidates.append(CandidateLink(normalized, label, depth=1))
        return candidates

    async def _respect_delay(self, url: str) -> None:
        if self.settings.delay_seconds <= 0:
            return
        host = (urlparse(url).hostname or "").lower()
        now = datetime.now(UTC)
        last_fetch = self._last_fetch_by_host.get(host)
        if last_fetch:
            elapsed = (now - last_fetch).total_seconds()
            if elapsed < self.settings.delay_seconds:
                await asyncio.sleep(self.settings.delay_seconds - elapsed)
        self._last_fetch_by_host[host] = datetime.now(UTC)

    def _store_parsed_row(
        self,
        entry: dict[str, Any],
        candidate: CandidateLink,
        fetched: _FetchedContent,
    ) -> None:
        raw_digest = sha256(fetched.content).hexdigest()
        filename = _safe_filename(candidate.label or fetched.final_url, raw_digest, fetched.final_url)
        raw_path = self.raw_dir / filename
        raw_path.write_bytes(fetched.content)

        try:
            text = extract_text_from_bytes(fetched.content, fetched.content_type)
            parse_status = "ok" if text.strip() else "partial"
        except Exception as exc:
            text = ""
            parse_status = "parse_error"
            self._record_error("parse_failed", fetched.final_url, entry, str(exc))
        parsed_path: Path | None = None
        if text.strip():
            parsed_path = self.parsed_dir / f"{Path(filename).stem}.txt"
            parsed_path.write_text(text, encoding="utf-8")

        title = candidate.label or _title_from_text(text) or _title_from_entry(entry)
        row = self._base_inventory_row(entry, fetched.final_url, title)
        row.update(
            {
                "retrieved_url": fetched.final_url,
                "content_type": fetched.content_type,
                "raw_path": _relative_path(raw_path, self.output_root),
                "parsed_path": _relative_path(parsed_path, self.output_root) if parsed_path else None,
                "sha256": raw_digest,
                "retrieved_at": _utc_timestamp(),
                "robots_allowed": fetched.robots_allowed,
                "robots_status": "allowed",
                "access_type": _access_type(entry),
                "parse_status": parse_status,
                "notes": _join_notes(
                    _clean_str(entry.get("licence_notes")),
                    "Discovered from official source anchor; licence and version require human verification before use.",
                ),
            }
        )
        self.inventory_rows.append(row)

    def _append_metadata_only_row(
        self,
        entry: dict[str, Any],
        url: str,
        reason: str,
        title: str | None = None,
    ) -> None:
        row = self._base_inventory_row(entry, url, title or _title_from_entry(entry))
        row.update(
            {
                "retrieved_url": url,
                "content_type": None,
                "raw_path": None,
                "parsed_path": None,
                "sha256": None,
                "retrieved_at": _utc_timestamp(),
                "robots_allowed": True,
                "robots_status": "not_fetched",
                "access_type": _access_type(entry),
                "parse_status": "metadata_only",
                "notes": _join_notes(_clean_str(entry.get("licence_notes")), reason),
            }
        )
        self.inventory_rows.append(row)

    def _base_inventory_row(self, entry: dict[str, Any], url: str, title: str) -> dict[str, Any]:
        source_type = _clean_str(entry.get("source_type")) or "source_document"
        if _is_standards_candidate(url, entry):
            source_type = "standard_metadata"
        return {
            "source_id": _source_id(title, url),
            "title": title,
            "authority": _clean_str(entry.get("authority")) or "Unknown authority",
            "jurisdiction": _clean_str(entry.get("jurisdiction")) or "WA",
            "local_government": _clean_str(entry.get("local_government")),
            "source_type": source_type,
            "canonical_url": url,
            "published_date": _clean_str(entry.get("published_date")),
            "effective_date": _clean_str(entry.get("effective_date")),
            "version_label": _clean_str(entry.get("version_label")),
            "licence_notes": _clean_str(entry.get("licence_notes")) or "",
        }

    def _record_fetch(
        self,
        url: str,
        status: str,
        http_status: int | None,
        robots_allowed: bool,
        error: str | None = None,
        retrieved_url: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.fetch_log_rows.append(
            {
                "url": url,
                "retrieved_url": retrieved_url,
                "status": status,
                "http_status": http_status,
                "robots_allowed": robots_allowed,
                "content_type": content_type,
                "error": error,
                "retrieved_at": _utc_timestamp(),
            }
        )

    def _record_error(
        self,
        error_type: str,
        url: str | None,
        entry: dict[str, Any],
        message: str,
    ) -> None:
        self.error_rows.append(
            {
                "error_type": error_type,
                "url": url,
                "title": _clean_str(entry.get("title")),
                "message": message,
                "created_at": _utc_timestamp(),
            }
        )

    def _ensure_output_dirs(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _write_outputs(self) -> None:
        _write_jsonl(self.output_root / "source_inventory.jsonl", self.inventory_rows)
        _write_jsonl(self.output_root / "fetch_log.jsonl", self.fetch_log_rows)
        _write_jsonl(self.output_root / "errors.jsonl", self.error_rows)
        self._write_reports()

    def _write_reports(self) -> None:
        parsed = [row for row in self.inventory_rows if row.get("parse_status") in {"ok", "partial"}]
        metadata = [row for row in self.inventory_rows if row.get("parse_status") == "metadata_only"]
        skipped = [row for row in self.fetch_log_rows if row.get("status") != "success"]
        summary = [
            "# Source Discovery Summary",
            "",
            f"- Inventory rows: {len(self.inventory_rows)}",
            f"- Parsed rows: {len(parsed)}",
            f"- Metadata-only rows: {len(metadata)}",
            f"- Skipped/blocked fetches: {len(skipped)}",
            f"- Errors: {len(self.error_rows)}",
            "",
            "Rows are discovery outputs only. Human licence/version verification is required before treating any source as submission support.",
        ]
        (self.reports_dir / "source_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

        risk_lines = [
            "# Licensing Risks",
            "",
            "Every discovered row requires human review of licence, access, currency, and supersession status.",
            "",
        ]
        for row in self.inventory_rows:
            risk_lines.append(f"- {row.get('title')}: {row.get('canonical_url')}")
        for row in skipped:
            risk_lines.append(f"- Skipped {row.get('url')}: {row.get('error') or row.get('status')}")
        (self.reports_dir / "licensing_risks.md").write_text("\n".join(risk_lines) + "\n", encoding="utf-8")

        missing_lines = [
            "# Missing Sources",
            "",
            "Use this report to add more official anchors or schedule manual source review.",
            "",
        ]
        if not self.inventory_rows:
            missing_lines.append("- No inventory rows were produced.")
        (self.reports_dir / "missing_sources.md").write_text("\n".join(missing_lines) + "\n", encoding="utf-8")

        with (self.reports_dir / "council_coverage_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["local_government", "parsed_rows", "metadata_only_rows"])
            writer.writeheader()
            coverage: dict[str, dict[str, int]] = {}
            for row in self.inventory_rows:
                key = row.get("local_government") or "state_or_national"
                coverage.setdefault(key, {"parsed_rows": 0, "metadata_only_rows": 0})
                if row.get("parse_status") == "metadata_only":
                    coverage[key]["metadata_only_rows"] += 1
                else:
                    coverage[key]["parsed_rows"] += 1
            for local_government, counts in sorted(coverage.items()):
                writer.writerow({"local_government": local_government, **counts})

    def _summary(self, anchors_seen: int) -> DiscoverySummary:
        parsed_rows = len([row for row in self.inventory_rows if row.get("parse_status") in {"ok", "partial"}])
        metadata_rows = len([row for row in self.inventory_rows if row.get("parse_status") == "metadata_only"])
        skipped = len([row for row in self.fetch_log_rows if row.get("status") != "success"])
        return DiscoverySummary(
            output_root=str(self.output_root),
            anchors_seen=anchors_seen,
            candidates_seen=len(self._seen_candidates),
            inventory_rows=len(self.inventory_rows),
            parsed_rows=parsed_rows,
            metadata_only_rows=metadata_rows,
            skipped=skipped,
            errors=len(self.error_rows),
        )


def extract_candidate_links(base_url: str, html: str, depth: int = 1) -> list[CandidateLink]:
    soup = BeautifulSoup(html, "html.parser")
    scored_by_url: dict[str, tuple[int, int, CandidateLink]] = {}
    for element in soup.find_all("a", href=True):
        label = " ".join(element.get_text(" ", strip=True).split())
        normalized = _normalize_url(base_url, str(element["href"]))
        if not normalized:
            continue
        if _looks_restricted(normalized, label):
            continue
        try:
            assert_lawful_source(normalized)
        except ValueError:
            continue
        score = _candidate_score(normalized, label)
        if score <= 0:
            continue
        candidate = CandidateLink(url=normalized, label=label or _title_from_url(normalized), depth=depth)
        label_length = len(candidate.label)
        existing = scored_by_url.get(normalized)
        if existing is None or (score, label_length) > (existing[0], existing[1]):
            scored_by_url[normalized] = (score, label_length, candidate)
    scored_candidates = list(scored_by_url.values())
    scored_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [candidate for _score, _label_length, candidate in scored_candidates]


def _manifest_entries(manifest_yaml: str) -> list[dict[str, Any]]:
    parsed = yaml.safe_load(manifest_yaml) or {}
    entries = parsed.get("sources", parsed if isinstance(parsed, list) else [])
    if not isinstance(entries, list):
        raise ValueError("Manifest must contain a sources list")
    return [entry for entry in entries if isinstance(entry, dict)]


def _normalize_url(base_url: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    joined = urljoin(base_url, href)
    normalized, _fragment = urldefrag(joined)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return normalized


def _looks_like_document_link(url: str, label: str) -> bool:
    parsed = urlparse(url)
    path = unquote(parsed.path).lower()
    haystack = f"{url.lower()} {path} {label.lower()}"
    if any(path.endswith(ext) for ext in DOCUMENT_EXTENSIONS):
        return True
    return any(keyword in haystack for keyword in DOCUMENT_KEYWORDS)


def _candidate_score(url: str, label: str) -> int:
    parsed = urlparse(url)
    path = unquote(parsed.path).lower()
    haystack = f"{url.lower()} {path} {label.lower()}"
    score = 0
    if "standards.org.au" in haystack or "standards australia" in haystack:
        score += 80
    if any(path.endswith(ext) for ext in DOCUMENT_EXTENSIONS if ext not in {".html", ".htm"}):
        score += 100
    if "pdf" in haystack or "docx" in haystack or "download" in haystack:
        score += 30
    for keyword in DOCUMENT_KEYWORDS:
        if keyword in haystack:
            score += 10
    if path.endswith((".html", ".htm")):
        score -= 20
    return score


def _is_document_response(url: str, content_type: str) -> bool:
    lower_type = content_type.lower()
    lower_path = unquote(urlparse(url).path).lower()
    if "pdf" in lower_type or "wordprocessingml" in lower_type or "msword" in lower_type:
        return True
    if lower_type.startswith("text/") and not lower_type.startswith("text/html"):
        return True
    if any(lower_path.endswith(ext) for ext in DOCUMENT_EXTENSIONS if ext not in {".html", ".htm"}):
        return True
    return False


def _looks_restricted(url: str, label: str) -> bool:
    haystack = f"{url} {label}".lower()
    return any(term in haystack for term in RESTRICTED_LINK_TERMS)


def _is_standards_candidate(url: str, entry: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(part or "")
        for part in [
            url,
            entry.get("title"),
            entry.get("authority"),
            entry.get("source_type"),
        ]
    ).lower()
    return "standards australia" in haystack or "standards.org.au" in haystack


def _safe_filename(label: str, digest: str, url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in DOCUMENT_EXTENSIONS:
        suffix = ".bin"
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:80] or "source"
    return f"{slug}-{digest[:12]}{suffix}"


def _relative_path(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    return path.resolve().relative_to(root.resolve()).as_posix()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows),
        encoding="utf-8",
    )


def _title_from_text(text: str) -> str | None:
    for line in text.splitlines():
        cleaned = " ".join(line.strip().split())
        if 8 <= len(cleaned) <= 160 and any(char.isalpha() for char in cleaned):
            return cleaned
    return None


def _title_from_entry(entry: dict[str, Any]) -> str:
    return _clean_str(entry.get("title")) or "Untitled source"


def _title_from_url(url: str) -> str:
    name = Path(unquote(urlparse(url).path)).stem
    return re.sub(r"[-_]+", " ", name).strip().title() or url


def _source_id(title: str, url: str) -> str:
    digest = sha256(url.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "source"
    return f"{slug}-{digest}"


def _access_type(entry: dict[str, Any]) -> str:
    access_type = (_clean_str(entry.get("access_type")) or "public").lower()
    return "public" if access_type == "open" else access_type


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1", "allowed"}:
            return True
        if normalized in {"false", "no", "n", "0", "disallowed", "blocked"}:
            return False
    return default


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _join_notes(*parts: str | None) -> str:
    return " | ".join(part.strip() for part in parts if part and part.strip())


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
