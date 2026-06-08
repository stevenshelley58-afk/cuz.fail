from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pypdf import PdfReader


WALGA_DIRECTORY_URL = (
    "https://walga.asn.au/getmedia/85eb5241-c2ae-4e79-a305-089ecb89e5d7/"
    "The-Western-Australian-Local-Government-Directory.pdf"
)


def main() -> None:
    args = _parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    councils = extract_councils(pdf_path)
    if len(councils) < args.min_councils:
        raise SystemExit(f"Expected at least {args.min_councils} councils, extracted {len(councils)}")

    manifest = {"sources": [_manifest_entry(council) for council in councils]}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    print(f"Wrote {len(councils)} council anchors to {output_path}")


def extract_councils(pdf_path: Path) -> list[dict[str, str]]:
    reader = PdfReader(str(pdf_path))
    quick_reference = "\n".join(reader.pages[index].extract_text() or "" for index in range(4, 7))
    lines = [_clean_pdf_text(line) for line in quick_reference.splitlines()]

    councils: list[dict[str, str]] = []
    pending = ""
    for line in lines:
        if not line or line.lower().startswith("type council"):
            continue
        if _starts_council_line(line):
            if pending:
                _append_council(councils, pending)
            pending = line
        elif pending:
            pending = f"{pending} {line}"
        if pending and _url_from_line(pending):
            _append_council(councils, pending)
            pending = ""
    if pending:
        _append_council(councils, pending)

    deduped: dict[str, dict[str, str]] = {}
    for council in councils:
        deduped[council["name"]] = council
    return sorted(deduped.values(), key=lambda item: item["name"])


def _append_council(councils: list[dict[str, str]], line: str) -> None:
    url = _url_from_line(line)
    name = _name_from_line(line)
    if not url or not name:
        return
    councils.append({"name": name, "url": url})


def _clean_pdf_text(value: str) -> str:
    cleaned = " ".join(value.split())
    replacements = {
        "T own": "Town",
        "T am": "Tam",
        "T o": "To",
        "T ray": "Tray",
        "T hree": "Three",
        "T amb": "Tamb",
        "V alley": "Valley",
        "Y algoo": "Yalgoo",
        "Y ork": "York",
        " wa.gov": ".wa.gov",
        ". wa.gov": ".wa.gov",
        " gov.au": "gov.au",
        " .au": ".au",
        " .cx": ".cx",
        "www .": "www.",
        "http://": "http://",
        "https://": "https://",
    }
    for before, after in replacements.items():
        cleaned = cleaned.replace(before, after)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = re.sub(r"\.\s+", ".", cleaned)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    return cleaned


def _starts_council_line(line: str) -> bool:
    return bool(re.match(r"^(City|Shire|Town) of ", line))


def _url_from_line(line: str) -> str | None:
    match = re.search(r"(https?://[A-Za-z0-9./:_-]+|www\.[A-Za-z0-9./:_-]+)", line)
    if not match:
        return None
    url = match.group(1).rstrip(".,;")
    if url.startswith("www."):
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _name_from_line(line: str) -> str | None:
    match = re.match(r"^((?:City|Shire|Town) of .+?)\s+\(08\)", line)
    if not match:
        return None
    name = " ".join(match.group(1).split())
    name = name.replace(" - ", "-")
    return name


def _manifest_entry(council: dict[str, str]) -> dict[str, object]:
    return {
        "title": f"{council['name']} official website source anchor",
        "jurisdiction": "WA",
        "authority": council["name"],
        "local_government": _short_council_name(council["name"]),
        "source_type": "local_planning_policy",
        "canonical_url": council["url"],
        "licence_notes": (
            "Official council website from WALGA Local Government Directory 2026. "
            "Discover only public planning/building documents; verify licence and currency before use. "
            f"Directory source: {WALGA_DIRECTORY_URL}"
        ),
        "access_type": "public",
        "scrape_allowed": True,
        "version_label": "walga-directory-2026-anchor",
    }


def _short_council_name(name: str) -> str:
    return re.sub(r"^(City|Shire|Town) of ", "", name).strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build WA council source manifest from WALGA PDF.")
    parser.add_argument("--pdf", default="data/seed/walga-local-government-directory-2026.pdf")
    parser.add_argument("--output", default="data/seed/wa_council_source_manifest.yaml")
    parser.add_argument("--min-councils", type=int, default=130)
    return parser.parse_args()


if __name__ == "__main__":
    main()
