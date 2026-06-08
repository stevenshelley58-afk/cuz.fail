from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import yaml


STRONG_PHRASES = {
    "accessory dwelling",
    "ancillary dwelling",
    "application checklist",
    "application for development approval",
    "bal assessment",
    "bal report",
    "building and planning",
    "building application",
    "building approval",
    "building permit",
    "bushfire attack level",
    "bushfire management plan",
    "bushfire prone",
    "carport",
    "crossover",
    "deck",
    "deemed to comply",
    "demolition",
    "development application",
    "development approval",
    "development assessment",
    "dwelling addition",
    "fence",
    "fencing",
    "heritage",
    "land use",
    "local planning policy",
    "local planning scheme",
    "local planning strategy",
    "outbuilding",
    "patio",
    "planning and building",
    "planning application",
    "planning policy",
    "planning scheme",
    "planning strategy",
    "r code",
    "r codes",
    "residential application checklist",
    "residential dwelling",
    "retaining wall",
    "scheme amendment",
    "setback",
    "short stay",
    "signage",
    "spa",
    "stormwater",
    "structure plan",
    "subdivision",
    "swimming pool",
    "verandah",
    "zoning",
}

MEDIUM_PHRASES = {
    "application",
    "approval",
    "building",
    "bushfire",
    "checklist",
    "development",
    "dwelling",
    "form",
    "permit",
    "planning",
    "policy",
    "residential",
    "scheme",
    "strategy",
}

DROP_TITLE_PHRASES = {
    "annual report",
    "aquatic centre",
    "budget",
    "bulldust",
    "cat complaint",
    "code of conduct",
    "community bus",
    "community directory",
    "complaint form",
    "complaints register",
    "corporate business plan",
    "council meeting",
    "council plan",
    "councillor",
    "customer service",
    "daip",
    "defibrillator",
    "disability access",
    "dog complaint",
    "elected member",
    "election",
    "electoral",
    "emergency contacts",
    "employee code",
    "events planning",
    "facility hire",
    "fees and charges",
    "fitness",
    "foi",
    "freedom of information",
    "gift",
    "gym",
    "health financial",
    "home care",
    "newsletter",
    "notifiable gifts",
    "pest control",
    "petition",
    "pet ownership",
    "phone book",
    "public health",
    "rates",
    "recovery plan",
    "register councillor",
    "register electoral",
    "risk committee",
    "sporting",
    "strategic community plan",
    "tourism",
    "tourist",
    "training report",
    "travel register",
    "volunteer",
    "waste",
    "weed",
}

GENERIC_TITLES = {
    "application",
    "application form",
    "checklist",
    "click here",
    "download",
    "download the latest edition",
    "form",
    "here",
    "read more",
}


@dataclass(frozen=True)
class RowContext:
    row: dict[str, Any]
    batch_name: str
    batch_root: Path
    row_number: int


@dataclass(frozen=True)
class Decision:
    keep: bool
    score: int
    reason: str
    matches: list[str]
    source_type: str


def main() -> None:
    args = _parse_args()
    input_root = Path(args.input_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()

    contexts = list(_iter_inventory_rows(input_root))
    councils = _load_manifest_councils(manifest_path)
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    stats = _initial_council_stats(councils)
    reason_counts: Counter[str] = Counter()
    source_type_counts: Counter[str] = Counter()

    for context in contexts:
        row = dict(context.row)
        council_key = _council_key(row)
        stats[council_key]["crawled_rows"] += 1
        parsed_text = _read_parsed_text(row, context.batch_root)
        decision = _assess_row(row, parsed_text, min_text_chars=args.min_text_chars)

        if decision.keep:
            filtered = _build_filtered_row(row, context, output_root, decision)
            kept.append(filtered)
            stats[council_key]["kept_documents"] += 1
            stats[council_key]["kept_titles"].append(filtered.get("title") or "")
            source_type_counts[decision.source_type] += 1
        else:
            row["filter_score"] = decision.score
            row["filter_reason"] = decision.reason
            row["filter_matches"] = decision.matches
            row["discovery_batch"] = context.batch_name
            dropped.append(row)
            stats[council_key]["dropped_documents"] += 1
            reason_counts[decision.reason] += 1

    kept.sort(key=lambda item: (_clean(item.get("authority")), _clean(item.get("title"))))
    dropped.sort(key=lambda item: (_clean(item.get("authority")), _clean(item.get("title"))))

    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_root / "source_inventory.jsonl", kept)
    _write_jsonl(reports_dir / "dropped_inventory.jsonl", dropped)
    _write_coverage_csv(reports_dir / "council_coverage_matrix.csv", councils, stats)
    _write_drop_reasons_csv(reports_dir / "drop_reasons.csv", reason_counts)
    _write_summary(
        reports_dir / "filter_summary.md",
        input_root=input_root,
        output_root=output_root,
        manifest_path=manifest_path,
        total_rows=len(contexts),
        kept_count=len(kept),
        dropped_count=len(dropped),
        council_count=len(councils),
        councils_with_kept=sum(1 for item in stats.values() if item["kept_documents"]),
        reason_counts=reason_counts,
        source_type_counts=source_type_counts,
    )

    print(
        json.dumps(
            {
                "input_rows": len(contexts),
                "kept": len(kept),
                "dropped": len(dropped),
                "councils": len(councils),
                "councils_with_kept": sum(
                    1 for item in stats.values() if item["kept_documents"]
                ),
                "output_inventory": str(output_root / "source_inventory.jsonl"),
                "coverage_report": str(reports_dir / "council_coverage_matrix.csv"),
            },
            indent=2,
        )
    )


def _iter_inventory_rows(input_root: Path) -> list[RowContext]:
    inventory_paths = sorted(input_root.glob("*/source_inventory.jsonl"))
    rows: list[RowContext] = []
    for inventory_path in inventory_paths:
        batch_root = inventory_path.parent
        for row_number, raw_line in enumerate(
            inventory_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            if isinstance(row, dict):
                rows.append(
                    RowContext(
                        row=row,
                        batch_name=batch_root.name,
                        batch_root=batch_root,
                        row_number=row_number,
                    )
                )
    return rows


def _assess_row(
    row: dict[str, Any],
    parsed_text: str | None,
    min_text_chars: int,
) -> Decision:
    if row.get("robots_allowed") is False:
        return Decision(False, 0, "robots_disallowed", [], _classify_source_type(row, ""))
    if _clean(row.get("access_type")).lower() not in {"public", "open"}:
        return Decision(False, 0, "restricted_access", [], _classify_source_type(row, ""))

    parse_status = _clean(row.get("parse_status")).lower() or "ok"
    if parse_status not in {"ok", "partial"}:
        return Decision(False, 0, f"parse_status_{parse_status}", [], _classify_source_type(row, ""))
    if not parsed_text or len(parsed_text.strip()) < min_text_chars:
        return Decision(False, 0, "missing_or_short_parsed_text", [], _classify_source_type(row, ""))

    title = _best_title(row)
    title_url = _normalized(
        " ".join(
            [
                title,
                _clean(row.get("canonical_url")),
                _clean(row.get("retrieved_url")),
                _clean(row.get("raw_path")),
                _clean(row.get("parsed_path")),
            ]
        )
    )
    text = _normalized(parsed_text[:30000])

    title_strong = sorted(phrase for phrase in STRONG_PHRASES if phrase in title_url)
    title_medium = sorted(phrase for phrase in MEDIUM_PHRASES if phrase in title_url)
    text_strong = sorted(phrase for phrase in STRONG_PHRASES if phrase in text)
    text_medium = sorted(phrase for phrase in MEDIUM_PHRASES if phrase in text)
    title_drop = sorted(phrase for phrase in DROP_TITLE_PHRASES if phrase in title_url)

    score = 0
    score += len(title_strong) * 16
    score += len(title_medium) * 5
    score += min(len(text_strong), 8) * 7
    score += min(len(text_medium), 8) * 2

    if title_drop and not title_strong:
        return Decision(
            False,
            score,
            f"irrelevant_title:{title_drop[0]}",
            title_strong + title_medium + text_strong[:4],
            _classify_source_type(row, title_url),
        )

    keep = (
        bool(title_strong)
        or (score >= 18 and len(title_medium) >= 2)
        or (score >= 22 and len(title_medium) >= 1 and len(text_strong) >= 2)
    )
    reason = "planning_building_relevance" if keep else "low_relevance_score"
    matches = sorted(set(title_strong + title_medium + text_strong[:8] + text_medium[:4]))
    return Decision(keep, score, reason, matches, _classify_source_type(row, title_url))


def _build_filtered_row(
    row: dict[str, Any],
    context: RowContext,
    output_root: Path,
    decision: Decision,
) -> dict[str, Any]:
    filtered = dict(row)
    title = _display_title(row)
    filtered["title"] = title
    filtered["source_type"] = decision.source_type
    filtered["filter_score"] = decision.score
    filtered["filter_reason"] = decision.reason
    filtered["filter_matches"] = decision.matches
    filtered["discovery_batch"] = context.batch_name
    filtered["discovery_row_number"] = context.row_number
    filtered["notes"] = _append_note(
        _clean(row.get("notes")),
        (
            "Filtered into WA council planning/building corpus by automated relevance "
            "rules; human review is required before relying on currency or applicability."
        ),
    )

    row_id = _row_id(row)
    raw_path = _resolve_row_path(row.get("raw_path"), context.batch_root)
    parsed_path = _resolve_row_path(row.get("parsed_path"), context.batch_root)
    copied_raw = _copy_file(raw_path, output_root, "raw", f"{context.batch_name}-{row_id}")
    copied_parsed = _copy_file(
        parsed_path,
        output_root,
        "parsed",
        f"{context.batch_name}-{row_id}",
    )
    if copied_raw:
        filtered["raw_path"] = copied_raw
    if copied_parsed:
        filtered["parsed_path"] = copied_parsed
    return filtered


def _classify_source_type(row: dict[str, Any], normalized_title_url: str) -> str:
    value = normalized_title_url or _normalized(
        " ".join(
            [
                _best_title(row),
                _clean(row.get("canonical_url")),
                _clean(row.get("raw_path")),
            ]
        )
    )
    if "local planning scheme" in value or "planning scheme" in value:
        return "local_planning_scheme"
    if "local planning strategy" in value or "planning strategy" in value:
        return "local_planning_strategy"
    if "local planning policy" in value or "planning policy" in value:
        return "local_planning_policy"
    if any(term in value for term in ["building permit", "building application", "building approval"]):
        return "building_guidance"
    if any(term in value for term in ["bushfire", "bal report", "bal assessment"]):
        return "bushfire_guidance"
    if any(term in value for term in ["application", "checklist", "form", "development approval"]):
        return "council_application_guidance"
    return _clean(row.get("source_type")) or "local_planning_policy"


def _load_manifest_councils(manifest_path: Path) -> dict[str, dict[str, Any]]:
    parsed = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    sources = parsed.get("sources", parsed if isinstance(parsed, list) else [])
    councils: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        local_government = _clean(source.get("local_government"))
        authority = _clean(source.get("authority"))
        key = local_government or authority
        if not key:
            continue
        councils[key] = {
            "local_government": local_government,
            "authority": authority,
            "website": _clean(source.get("canonical_url")),
        }
    return councils


def _initial_council_stats(councils: dict[str, dict[str, Any]]) -> defaultdict[str, dict[str, Any]]:
    stats: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "crawled_rows": 0,
            "kept_documents": 0,
            "dropped_documents": 0,
            "kept_titles": [],
        }
    )
    for council in councils:
        stats[council]
    return stats


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def _write_coverage_csv(
    path: Path,
    councils: dict[str, dict[str, Any]],
    stats: defaultdict[str, dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "local_government",
                "authority",
                "website",
                "crawled_rows",
                "kept_documents",
                "dropped_documents",
                "status",
                "kept_titles",
            ],
        )
        writer.writeheader()
        for key in sorted(councils):
            council = councils[key]
            item = stats[key]
            if item["kept_documents"]:
                status = "kept_planning_building_documents"
            elif item["crawled_rows"]:
                status = "crawled_no_kept_planning_building_documents"
            else:
                status = "no_public_documents_discovered_by_bounded_crawl"
            writer.writerow(
                {
                    "local_government": council["local_government"],
                    "authority": council["authority"],
                    "website": council["website"],
                    "crawled_rows": item["crawled_rows"],
                    "kept_documents": item["kept_documents"],
                    "dropped_documents": item["dropped_documents"],
                    "status": status,
                    "kept_titles": "; ".join(item["kept_titles"][:8]),
                }
            )


def _write_drop_reasons_csv(path: Path, reason_counts: Counter[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["reason", "count"])
        writer.writeheader()
        for reason, count in reason_counts.most_common():
            writer.writerow({"reason": reason, "count": count})


def _write_summary(
    path: Path,
    *,
    input_root: Path,
    output_root: Path,
    manifest_path: Path,
    total_rows: int,
    kept_count: int,
    dropped_count: int,
    council_count: int,
    councils_with_kept: int,
    reason_counts: Counter[str],
    source_type_counts: Counter[str],
) -> None:
    lines = [
        "# WA Council Corpus Filter Summary",
        "",
        f"- Input root: {input_root}",
        f"- Output root: {output_root}",
        f"- Council manifest: {manifest_path}",
        f"- Council anchors: {council_count}",
        f"- Raw discovered rows: {total_rows}",
        f"- Kept planning/building rows: {kept_count}",
        f"- Dropped rows: {dropped_count}",
        f"- Councils with at least one kept row: {councils_with_kept}",
        "",
        "## Kept Source Types",
        "",
    ]
    if source_type_counts:
        for source_type, count in source_type_counts.most_common():
            lines.append(f"- {source_type}: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "## Drop Reasons", ""])
    if reason_counts:
        for reason, count in reason_counts.most_common():
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- This is a bounded automated discovery pass from official council website anchors.",
            "- It does not prove that every WA council document has been discovered.",
            "- Retained documents still require human review for currency, licence, supersession, and applicability.",
            "- Paid Australian Standards full text is intentionally outside this corpus.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_parsed_text(row: dict[str, Any], batch_root: Path) -> str | None:
    parsed_path = _resolve_row_path(row.get("parsed_path"), batch_root)
    if parsed_path and parsed_path.is_file():
        return parsed_path.read_text(encoding="utf-8", errors="replace")
    return None


def _resolve_row_path(value: Any, batch_root: Path) -> Path | None:
    path_text = _clean(value)
    if not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        return path
    return batch_root / path


def _copy_file(source: Path | None, output_root: Path, folder: str, prefix: str) -> str | None:
    if not source or not source.is_file():
        return None
    destination_dir = output_root / folder
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / _safe_dest_name(prefix, source.name)
    if not destination.exists() or _file_sha256(destination) != _file_sha256(source):
        shutil.copy2(source, destination)
    return destination.relative_to(output_root).as_posix()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_dest_name(prefix: str, name: str) -> str:
    path = Path(name)
    suffix = path.suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip(".-_")
    stem = stem[:90].strip(".-_") or "source"
    return f"{prefix}-{stem}{suffix}"


def _row_id(row: dict[str, Any]) -> str:
    existing = _clean(row.get("sha256"))
    if existing:
        return existing[:12].lower()
    basis = "|".join(
        [
            _clean(row.get("canonical_url")),
            _clean(row.get("retrieved_url")),
            _clean(row.get("title")),
        ]
    )
    return sha256(basis.encode("utf-8")).hexdigest()[:12]


def _display_title(row: dict[str, Any]) -> str:
    title = _best_title(row)
    authority = _clean(row.get("authority"))
    if not authority or authority.lower() in title.lower():
        return title
    return f"{authority} - {title}"


def _best_title(row: dict[str, Any]) -> str:
    candidates = [
        _clean(row.get("title")),
        _title_from_url(_clean(row.get("canonical_url"))),
        _title_from_url(_clean(row.get("retrieved_url"))),
        _title_from_path(row.get("parsed_path")),
        _title_from_path(row.get("raw_path")),
        _clean(row.get("source_id")),
    ]
    scored = [
        (_title_score(candidate), index, candidate)
        for index, candidate in enumerate(candidates)
        if candidate
    ]
    if not scored:
        return "Untitled council source"
    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return scored[0][2]


def _title_score(title: str) -> int:
    normalized = _normalized(title)
    words = normalized.split()
    score = len(set(words)) * 4 + min(len(title), 120)
    if normalized in GENERIC_TITLES or len(words) < 2:
        score -= 100
    if any(phrase in normalized for phrase in STRONG_PHRASES):
        score += 80
    if any(phrase in normalized for phrase in MEDIUM_PHRASES):
        score += 20
    if any(phrase in normalized for phrase in DROP_TITLE_PHRASES):
        score -= 30
    return score


def _title_from_url(url: str) -> str:
    if not url:
        return ""
    path = Path(unquote(urlparse(url).path)).stem
    return _humanize(path)


def _title_from_path(value: Any) -> str:
    path_text = _clean(value)
    if not path_text:
        return ""
    stem = Path(path_text).stem
    stem = re.sub(r"[-_][0-9a-f]{12}$", "", stem, flags=re.IGNORECASE)
    return _humanize(stem)


def _humanize(value: str) -> str:
    cleaned = unquote(value)
    cleaned = re.sub(r"[_-]+", " ", cleaned)
    cleaned = re.sub(r"\bpdf\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;:_-")
    if not cleaned:
        return ""
    words: list[str] = []
    for word in cleaned.split():
        lower = word.lower()
        if lower in {"bal", "ncc", "r", "wa"}:
            words.append(lower.upper())
        elif lower in {"codes", "code"} and words and words[-1] == "R":
            words[-1] = "R-Codes"
        else:
            words.append(lower.capitalize())
    return " ".join(words)


def _append_note(existing: str, note: str) -> str:
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing} | {note}"


def _council_key(row: dict[str, Any]) -> str:
    return _clean(row.get("local_government")) or _clean(row.get("authority")) or "unknown"


def _normalized(value: str) -> str:
    lowered = value.lower()
    lowered = lowered.replace("r-codes", "r codes").replace("r-code", "r code")
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter WA council crawl output to planning/building-relevant inventory rows."
    )
    parser.add_argument(
        "--input-root",
        default="data/corpus/wa-councils-20260605-batches",
        help="Root containing batch subdirectories with source_inventory.jsonl files.",
    )
    parser.add_argument(
        "--manifest",
        default="data/seed/wa_council_source_manifest.yaml",
        help="WA council source manifest used for coverage reporting.",
    )
    parser.add_argument(
        "--output-root",
        default="data/corpus/wa-councils-20260605-filtered",
        help="Filtered corpus output root.",
    )
    parser.add_argument(
        "--min-text-chars",
        type=int,
        default=160,
        help="Drop parsed documents shorter than this many characters.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
