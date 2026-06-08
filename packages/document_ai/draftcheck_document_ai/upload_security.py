from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True)
class ValidatedUpload:
    content: bytes
    content_type: str
    detected_type: str
    byte_size: int


ALLOWED_UPLOAD_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/dxf",
    "text/html",
    "text/plain",
}
_DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_WINDOWS_RESERVED_FILENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def validate_uploaded_document(
    content: bytes,
    *,
    declared_content_type: str,
    filename: str,
    max_bytes: int,
) -> ValidatedUpload:
    if not content:
        raise ValueError("Uploaded document is empty")
    if len(content) > max_bytes:
        raise ValueError(f"Uploaded document exceeds {max_bytes} byte limit")

    detected_type = detect_upload_content_type(content, filename=filename)
    declared_type = _clean_content_type(declared_content_type)
    if detected_type not in ALLOWED_UPLOAD_TYPES:
        raise ValueError("Uploaded document type is not supported")
    if not _declared_type_matches(declared_type, detected_type):
        raise ValueError(
            f"Uploaded document content does not match declared content type {declared_type}"
        )

    return ValidatedUpload(
        content=content,
        content_type=detected_type,
        detected_type=detected_type,
        byte_size=len(content),
    )


def safe_upload_filename(filename: str | None) -> str:
    basename = (filename or "upload.bin").replace("\\", "/").split("/")[-1].strip()
    if basename in {"", ".", ".."}:
        basename = "upload.bin"
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("._ ")
    if not sanitized:
        sanitized = "upload.bin"
    stem = Path(sanitized).stem.upper()
    if stem in _WINDOWS_RESERVED_FILENAMES:
        sanitized = f"upload_{sanitized}"
    return _truncate_filename(sanitized)


def upload_object_key(*, project_id: str, filename: str, content: bytes) -> str:
    digest = sha256(content).hexdigest()
    return f"projects/{project_id}/documents/{digest[:2]}/{digest}/{filename}"


def detect_upload_content_type(content: bytes, *, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if _looks_like_docx(content):
        return _DOCX_TYPE
    if _looks_like_html(content):
        return "text/html"
    if _looks_like_dxf(content, suffix=suffix):
        return "application/dxf"
    if _looks_like_text(content):
        return "text/plain"
    return "application/octet-stream"


def _truncate_filename(filename: str, max_length: int = 120) -> str:
    if len(filename) <= max_length:
        return filename
    path = Path(filename)
    suffix = path.suffix[:20]
    stem_limit = max(1, max_length - len(suffix))
    return f"{path.stem[:stem_limit]}{suffix}"


def _clean_content_type(value: str) -> str:
    return (value or "application/octet-stream").split(";", 1)[0].strip().lower()


def _declared_type_matches(declared_type: str, detected_type: str) -> bool:
    if declared_type in {"", "application/octet-stream"}:
        return True
    if declared_type == detected_type:
        return True
    aliases = {
        "application/x-dxf": "application/dxf",
        "image/vnd.dxf": "application/dxf",
        "text/dxf": "application/dxf",
        "application/xhtml+xml": "text/html",
    }
    return aliases.get(declared_type) == detected_type


def _looks_like_docx(content: bytes) -> bool:
    if not content.startswith(b"PK"):
        return False
    try:
        from io import BytesIO

        with ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
    except (BadZipFile, OSError):
        return False
    return "[Content_Types].xml" in names and any(name.startswith("word/") for name in names)


def _looks_like_html(content: bytes) -> bool:
    sample = content[:2048].lstrip().lower()
    return sample.startswith((b"<!doctype html", b"<html", b"<body")) or b"<html" in sample[:512]


def _looks_like_dxf(content: bytes, *, suffix: str) -> bool:
    if suffix != ".dxf" and b"SECTION" not in content[:4096].upper():
        return False
    text = content[:8192].decode("utf-8", errors="ignore").upper()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if "SECTION" not in lines:
        return False
    return "ENTITIES" in lines or "$INSUNITS" in lines or "HEADER" in lines


def _looks_like_text(content: bytes) -> bool:
    if b"\x00" in content[:4096]:
        return False
    try:
        content.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False
