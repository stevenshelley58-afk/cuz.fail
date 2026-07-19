"""Lawful public source fetching helpers for V3 source ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from urllib.parse import ParseResult, urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
import httpx


USER_AGENT = "LotFile-Core/0.1 lawful-public-source-fetcher"
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
    content: bytes
    sha256: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class SourceTextExtraction:
    text: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class CandidateSourceLink:
    url: str
    label: str
    source_type: str


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
        extraction = extract_source_text_with_metadata(
            response.content,
            content_type=content_type,
            final_url=str(response.url),
        )
        text = sanitize_source_text(extraction.text)
        if not text.strip():
            raise ValueError("source fetch produced no parseable text")
        digest = sha256(response.content).hexdigest()
        candidate_links = _candidate_links_for_response(
            response.content,
            content_type=content_type,
            final_url=str(response.url),
        )
        return PublicSourceFetch(
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            text=text,
            content=response.content,
            sha256=digest,
            metadata={
                "http_status": response.status_code,
                "content_type": content_type,
                "final_url": str(response.url),
                "raw_sha256": digest,
                "robots_allowed": True,
                "parser": "draftcheck.sources.public_fetch.v0",
                **extraction.metadata,
                "candidate_links": [
                    {
                        "url": link.url,
                        "label": link.label,
                        "source_type": link.source_type,
                    }
                    for link in candidate_links
                ],
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
    return extract_source_text_with_metadata(
        content,
        content_type=content_type,
        final_url=final_url,
    ).text


def extract_source_text_with_metadata(
    content: bytes,
    *,
    content_type: str,
    final_url: str,
) -> SourceTextExtraction:
    lowered_type = content_type.lower()
    lowered_url = final_url.lower()
    if "pdf" in lowered_type or lowered_url.endswith(".pdf"):
        return _extract_pdf_text_with_metadata(content)
    if (
        "wordprocessingml" in lowered_type
        or lowered_url.endswith(".docx")
        or ("-docx" in lowered_url and content[:2] == b"PK")
        or (content[:2] == b"PK" and _zip_has_docx_document(content))
    ):
        return _extract_docx_text_with_metadata(content)
    if "html" in lowered_type or lowered_url.endswith((".html", ".htm", "/")):
        return SourceTextExtraction(
            text=_extract_html_text(content, final_url=final_url),
            metadata={
                "extraction": {
                    "content_kind": "html",
                    "method": "beautifulsoup_text",
                },
                "parse_quality": {
                    "status": "text_extracted",
                },
            },
        )
    text = content.decode("utf-8", errors="ignore").strip()
    return SourceTextExtraction(
        text=text,
        metadata={
            "extraction": {
                "content_kind": "text",
                "method": "utf8_decode",
            },
            "parse_quality": {
                "status": "text_extracted" if text else "no_parseable_text",
            },
        },
    )


def _zip_has_docx_document(content: bytes) -> bool:
    import zipfile
    from io import BytesIO as _BytesIO

    try:
        with zipfile.ZipFile(_BytesIO(content)) as archive:
            return "word/document.xml" in archive.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def _extract_docx_text_with_metadata(content: bytes) -> SourceTextExtraction:
    """Extract paragraph text from a DOCX file using only the standard library."""

    import xml.etree.ElementTree as ElementTree
    import zipfile
    from io import BytesIO as _BytesIO

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    try:
        with zipfile.ZipFile(_BytesIO(content)) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ValueError("docx archive has no word/document.xml")
            root = ElementTree.fromstring(archive.read("word/document.xml"))
            for paragraph in root.iter(f"{namespace}p"):
                runs: list[str] = []
                for node in paragraph.iter():
                    if node.tag == f"{namespace}t" and node.text:
                        runs.append(node.text)
                    elif node.tag in (f"{namespace}tab",):
                        runs.append("\t")
                    elif node.tag in (f"{namespace}br", f"{namespace}cr"):
                        runs.append("\n")
                text = "".join(runs).strip()
                if text:
                    paragraphs.append(text)
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError, OSError) as exc:
        return SourceTextExtraction(
            text="",
            metadata={
                "extraction": {
                    "content_kind": "docx",
                    "method": "stdlib_zip_xml",
                    "error": str(exc),
                },
                "parse_quality": {
                    "status": "no_parseable_text",
                },
            },
        )
    text = "\n\n".join(paragraphs).strip()
    return SourceTextExtraction(
        text=text,
        metadata={
            "extraction": {
                "content_kind": "docx",
                "method": "stdlib_zip_xml",
                "paragraph_count": len(paragraphs),
            },
            "parse_quality": {
                "status": "text_extracted" if text else "no_parseable_text",
                "text_char_count": len(text),
            },
        },
    )


def sanitize_source_text(text: str) -> str:
    """Remove characters PostgreSQL cannot store in text columns."""

    return text.replace("\x00", "")


def extract_candidate_links(final_url: str, html: bytes | str) -> tuple[CandidateSourceLink, ...]:
    text = html.decode("utf-8", errors="ignore") if isinstance(html, bytes) else html
    soup = BeautifulSoup(text, "html.parser")
    return tuple(_candidate_links(soup, final_url=final_url))


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
        rendered_links = [
            f"{link.label}: {link.url}" if link.label else link.url for link in links[:80]
        ]
        parts.append("Candidate public source links:\n" + "\n".join(rendered_links))
    return "\n\n".join(parts).strip()


def _candidate_links_for_response(
    content: bytes,
    *,
    content_type: str,
    final_url: str,
) -> tuple[CandidateSourceLink, ...]:
    lowered_type = content_type.lower()
    lowered_url = final_url.lower()
    if "html" not in lowered_type and not lowered_url.endswith((".html", ".htm", "/")):
        return ()
    return extract_candidate_links(final_url, content)


def _extract_pdf_text(content: bytes) -> str:
    return _extract_pdf_text_with_metadata(content).text


def extract_pdf_text_with_pymupdf(content: bytes) -> SourceTextExtraction:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - optional repair dependency in pyproject
        raise ValueError("PyMuPDF repair parser is unavailable") from exc
    document = fitz.open(stream=content, filetype="pdf")
    try:
        pages = [page.get_text("text") or "" for page in document]
    finally:
        document.close()
    normalized_pages = [page.strip() for page in pages]
    text_pages = [page for page in normalized_pages if page]
    text = "\n\n".join(text_pages)
    page_count = len(normalized_pages)
    pages_with_text = len(text_pages)
    text_char_count = len(text)
    text_word_count = len(text.split())
    text_coverage_ratio = round(pages_with_text / page_count, 4) if page_count else 0.0
    return SourceTextExtraction(
        text=text,
        metadata={
            "extraction": {
                "content_kind": "pdf",
                "method": "pymupdf_text_layer",
            },
            "parse_quality": {
                "status": _pdf_parse_quality_status(
                    page_count=page_count,
                    pages_with_text=pages_with_text,
                    text_char_count=text_char_count,
                    text_coverage_ratio=text_coverage_ratio,
                ),
                "page_count": page_count,
                "pages_with_text": pages_with_text,
                "text_char_count": text_char_count,
                "text_word_count": text_word_count,
                "text_coverage_ratio": text_coverage_ratio,
            },
        },
    )


def extract_pdf_text_with_ocr(
    content: bytes,
    *,
    max_pages: int = 30,
    dpi: int = 200,
) -> SourceTextExtraction:
    try:
        import fitz
        from PIL import Image
        import pytesseract
    except ImportError as exc:  # pragma: no cover - optional repair dependency in pyproject
        raise ValueError("OCR repair parser is unavailable") from exc
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1 for OCR repair")
    if dpi < 100:
        raise ValueError("dpi must be at least 100 for OCR repair")
    document = fitz.open(stream=content, filetype="pdf")
    try:
        page_count = len(document)
        pages_to_process = min(page_count, max_pages)
        scale = dpi / 72
        matrix = fitz.Matrix(scale, scale)
        text_pages: list[str] = []
        for page_index in range(pages_to_process):
            page = document[page_index]
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png")))
            page_text = pytesseract.image_to_string(image, lang="eng").strip()
            if page_text:
                text_pages.append(page_text)
    finally:
        document.close()
    text = "\n\n".join(text_pages)
    pages_with_text = len(text_pages)
    text_char_count = len(text)
    text_word_count = len(text.split())
    text_coverage_ratio = round(pages_with_text / page_count, 4) if page_count else 0.0
    partial = pages_to_process < page_count
    status_value = (
        "partial_ocr_review"
        if partial
        else _pdf_parse_quality_status(
            page_count=page_count,
            pages_with_text=pages_with_text,
            text_char_count=text_char_count,
            text_coverage_ratio=text_coverage_ratio,
        )
    )
    return SourceTextExtraction(
        text=text,
        metadata={
            "extraction": {
                "content_kind": "pdf",
                "method": "pymupdf_render_tesseract_ocr",
                "dpi": dpi,
                "max_pages": max_pages,
                "pages_processed": pages_to_process,
                "partial": partial,
            },
            "parse_quality": {
                "status": status_value,
                "page_count": page_count,
                "pages_processed": pages_to_process,
                "pages_with_text": pages_with_text,
                "text_char_count": text_char_count,
                "text_word_count": text_word_count,
                "text_coverage_ratio": text_coverage_ratio,
            },
        },
    )


def _extract_pdf_text_with_metadata(content: bytes) -> SourceTextExtraction:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is locked in pyproject
        raise ValueError("PDF parser is unavailable") from exc
    try:
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # noqa: BLE001 - malformed public PDFs should fall back, not block
        fallback = extract_pdf_text_with_pymupdf(content)
        fallback.metadata["extraction"] = {
            **dict(fallback.metadata.get("extraction", {})),
            "fallback_from": "pypdf_text_layer",
            "fallback_reason": str(exc)[:500],
        }
        return fallback
    normalized_pages = [page.strip() for page in pages]
    text_pages = [page for page in normalized_pages if page]
    text = "\n\n".join(text_pages)
    page_count = len(normalized_pages)
    pages_with_text = len(text_pages)
    text_char_count = len(text)
    text_word_count = len(text.split())
    text_coverage_ratio = round(pages_with_text / page_count, 4) if page_count else 0.0
    return SourceTextExtraction(
        text=text,
        metadata={
            "extraction": {
                "content_kind": "pdf",
                "method": "pypdf_text_layer",
            },
            "parse_quality": {
                "status": _pdf_parse_quality_status(
                    page_count=page_count,
                    pages_with_text=pages_with_text,
                    text_char_count=text_char_count,
                    text_coverage_ratio=text_coverage_ratio,
                ),
                "page_count": page_count,
                "pages_with_text": pages_with_text,
                "text_char_count": text_char_count,
                "text_word_count": text_word_count,
                "text_coverage_ratio": text_coverage_ratio,
            },
        },
    )


def _pdf_parse_quality_status(
    *,
    page_count: int,
    pages_with_text: int,
    text_char_count: int,
    text_coverage_ratio: float,
) -> str:
    if text_char_count == 0 or pages_with_text == 0:
        return "no_parseable_text"
    if page_count > 1 and pages_with_text <= 1:
        return "low_signal_review"
    if text_char_count < 1000:
        return "low_signal_review"
    if page_count >= 4 and text_coverage_ratio < 0.25:
        return "low_signal_review"
    return "text_layer_extracted"


def _is_low_signal_cockburn_source_link(url: str, source_type: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host.endswith("cockburn.wa.gov.au"):
        return False
    if source_type != "source_document":
        return False
    normalized_path = parsed.path.lower().rstrip("/")
    if normalized_path == "/building-planning-and-roads/town-planning-and-development":
        return True
    return normalized_path.startswith("/building-planning-and-roads/")


def _candidate_links(soup: BeautifulSoup, *, final_url: str) -> list[CandidateSourceLink]:
    parsed_base = urlparse(final_url)
    candidates: list[CandidateSourceLink] = []
    seen_urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith(("mailto:", "tel:", "#")):
            continue
        absolute = urldefrag(urljoin(final_url, href))[0]
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not _host_allowed(parsed_base, parsed):
            continue
        lowered = absolute.lower()
        if any(term in lowered for term in RESTRICTED_TERMS):
            continue
        label = " ".join(anchor.get_text(" ", strip=True).split())
        if not _looks_like_source_link(lowered, label.lower()):
            continue
        source_type = infer_source_type(absolute, label)
        if _is_low_signal_cockburn_source_link(absolute, source_type):
            continue
        if absolute in seen_urls:
            continue
        seen_urls.add(absolute)
        candidates.append(
            CandidateSourceLink(
                url=absolute,
                label=label or _label_from_url(absolute),
                source_type=source_type,
            )
        )
    return candidates


def infer_source_type(url: str, label: str = "") -> str:
    haystack = f"{url} {label}".lower().replace("_", "-")
    is_tps = _has_tps_token(haystack)
    if "standards.org.au" in haystack or "standards australia" in haystack:
        return "standard_metadata"
    if (
        "scheme-map" in haystack
        or "map-" in haystack
        or " map " in f" {haystack} "
        or (is_tps and "map" in haystack)
    ):
        return "scheme_map"
    if "local-development-plan" in haystack or "ldp" in haystack:
        return "local_development_plan"
    if "structure-plan" in haystack or "structure plan" in haystack:
        return "structure_plan"
    if (
        "local-planning-scheme" in haystack
        or "town-planning-scheme" in haystack
        or "scheme-text" in haystack
        or "schemetext" in haystack
        or is_tps
    ):
        return "local_planning_scheme"
    if (
        "local-planning-polic" in haystack
        or "local planning polic" in haystack
        or _has_lpp_token(haystack)
    ):
        return "local_planning_policy"
    if "planning-strategy" in haystack or "local planning strategy" in haystack:
        return "local_planning_strategy"
    if (
        "planning-advice" in haystack
        or "building-advice" in haystack
        or "information-sheet" in haystack
        or "planning information" in haystack
        or ("checklist" in haystack and "planning" in haystack)
    ):
        return "planning_guidance"
    if "r-code" in haystack or "rcode" in haystack or "residential-design-code" in haystack:
        return "r_code"
    return "source_document"


def _looks_like_source_link(url: str, label: str) -> bool:
    haystack = f"{url} {label}".lower().replace("_", "-")
    if any(
        term in haystack
        for term in (
            "local-planning",
            "planning-scheme",
            "scheme-text",
            "schemetext",
            "structure-plan",
            "local-development-plan",
            "local development plan",
            "planning-strategy",
            "local planning strategy",
            "local-planning-polic",
            "local planning polic",
            "planning advice",
            "planning-advice",
            "r-code",
            "rcode",
            "residential-design-code",
        )
    ):
        return True
    if _has_lpp_token(haystack):
        return True
    if _has_tps_token(haystack) and ("map" in haystack or "scheme" in haystack):
        return True
    return bool(
        (haystack.endswith((".pdf", ".doc", ".docx")) or ".pdf" in haystack)
        and any(term in haystack for term in ("planning", "scheme", "map", "r-code", "rcode"))
    )


def _has_tps_token(haystack: str) -> bool:
    normalized = (
        haystack.replace("/", "-")
        .replace(".", "-")
        .replace("(", "-")
        .replace(")", "-")
        .replace("%20", "-")
    )
    return any(token == "tps" or (token.startswith("tps") and token[3:].isdigit()) for token in normalized.split("-"))


def _has_lpp_token(haystack: str) -> bool:
    normalized = (
        haystack.replace("/", "-")
        .replace(".", "-")
        .replace("(", "-")
        .replace(")", "-")
        .replace("%20", "-")
    )
    return any(token == "lpp" or (token.startswith("lpp") and token[3:].isdigit()) for token in normalized.split("-"))


def _host_allowed(parsed_base: ParseResult, parsed_candidate: ParseResult) -> bool:
    base_host = (parsed_base.hostname or "").lower()
    candidate_host = (parsed_candidate.hostname or "").lower()
    if not base_host or not candidate_host:
        return False
    if candidate_host == base_host:
        return True
    # WA Government and City of Cockburn pages sometimes point between official
    # planning hosts. Keep discovery narrow to public government domains.
    official_hosts = (
        "wa.gov.au",
        "planning.wa.gov.au",
        "cockburn.wa.gov.au",
    )
    return any(base_host.endswith(host) for host in official_hosts) and any(
        candidate_host.endswith(host) for host in official_hosts
    )


def _label_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/").split("/")[-1]
    cleaned = path.replace("-", " ").replace("_", " ").replace("%20", " ").strip()
    return cleaned or url


def _assert_lawful_public_url(url: str, *, licence_notes: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("only absolute public HTTP(S) URLs can be fetched")
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        raise ValueError("private/local URLs cannot be fetched as source material")
    lowered = f"{url} {licence_notes}".lower()
    if any(term in lowered for term in RESTRICTED_TERMS):
        raise ValueError("restricted source URL or licence notes require automated validation")
    if "standards.org.au" in lowered or "standards australia" in lowered:
        raise ValueError("Standards Australia full text is metadata-only unless lawfully supplied")
