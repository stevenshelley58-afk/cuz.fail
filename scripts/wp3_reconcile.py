"""WP3 step 3 — reconcile every source_documents row to a target_manifest row.

Reads reports/wp3/docs_fresh.csv + manifest_fresh.csv + aliases_fresh.csv (dumped from
production), matches by canonical_url, then exact title/alias; unmatched docs get a new
manifest row built from the doc's own metadata (status=acquired, FK set).
Emits reports/wp3/batch7_reconcile.sql (idempotent).
"""
from __future__ import annotations

import csv
import re
import uuid
from pathlib import Path

WP3 = Path(__file__).resolve().parent.parent / "reports" / "wp3"
NS = uuid.UUID("7b1e5a52-4f2c-4cf7-9e83-0c8f2a3d6e91")

CATEGORY_BY_SOURCE_TYPE = {
    "local_planning_scheme": "local_planning_scheme",
    "structure_plan": "structure_plan",
    "scheme_map": "scheme_map",
    "local_planning_policy": "local_planning_policy",
    "local_planning_strategy": "local_planning_strategy",
    "local_development_plan": "local_development_plan",
    "planning_guidance": "council_page",
    "source_document": "council_page",
    "index_page": "index_page",
}

SPLITTERS = [
    " Find out", " Access information", " Access the full", " Access approved", " Access ",
    " Learn about", " Learn ", " Read information", " View information", " View the",
    " Information on", " The City received", " Mobile phone carriers", " The Minister for Planning",
    " Department of Planning, Lands and Heritage Regulations",
]

# doc id → manifest natural key (instrument_name, issuing_authority), for matches the
# generic passes cannot make. LPP 5.23 web page → the LPP 5.23 manifest row.
SPECIAL = {
    "b2273a40-7898-5cbf-95fc-b2518d55389d": (
        "City of Cockburn LPP 5.23 - Tree Protection", "City of Cockburn"),
}


def q(s: str | None) -> str:
    if s is None or s == "":
        return "NULL"
    return "'" + s.replace("'", "''") + "'"


def clean_title(t: str) -> str:
    t = re.sub(r"\s*\(PDF, [^)]+\)\s*", " ", t).strip()
    cut = len(t)
    for s in SPLITTERS:
        i = t.find(s)
        if i > 0:
            cut = min(cut, i)
    t = t[:cut].strip().rstrip(".,-–")
    return t[:500]


def main() -> None:
    docs = list(csv.DictReader(open(WP3 / "docs_fresh.csv", encoding="utf-8")))
    manifest = list(csv.DictReader(open(WP3 / "manifest_fresh.csv", encoding="utf-8")))
    aliases = list(csv.DictReader(open(WP3 / "aliases_fresh.csv", encoding="utf-8")))

    by_url = {m["canonical_url"]: m for m in manifest if m["canonical_url"]}
    by_name = {(m["instrument_name"].casefold(), m["issuing_authority"]): m for m in manifest}
    by_name_any = {}
    for m in manifest:
        by_name_any.setdefault(m["instrument_name"].casefold(), m)
    alias_map = {a["alias_text"].casefold(): a["canonical_manifest_id"] for a in aliases}
    mid_by_id = {m["id"]: m for m in manifest}
    by_key = {(m["instrument_name"], m["issuing_authority"]): m for m in manifest}

    out = ["BEGIN;"]
    used_names: dict[tuple[str, str], str] = {}
    matched = created = 0

    for d in docs:
        doc_id = d["id"]
        title = d["title"]
        auth = d["authority"]
        url = d["canonical_url"]
        target = None

        if doc_id in SPECIAL:
            target = by_key.get(SPECIAL[doc_id])
        if target is None and url and url in by_url:
            target = by_url[url]
        if target is None:
            ct = clean_title(title).casefold()
            target = by_name.get((ct, auth)) or by_name_any.get(ct)
            if target is None and ct in alias_map:
                target = mid_by_id.get(alias_map[ct])

        if target is not None:
            matched += 1
            status_sql = "'acquired'"
            out.append(
                f"UPDATE target_manifest SET status = {status_sql}, source_document_id = '{doc_id}', "
                f"last_checked_at = now(), updated_at = now() WHERE id = '{target['id']}' "
                f"AND (source_document_id IS NULL OR source_document_id = '{doc_id}');"
            )
            # alias: record the doc title as an alternative name if it differs
            ct = clean_title(title)
            if ct.casefold() != target["instrument_name"].casefold() and len(ct) > 3:
                aid = uuid.uuid5(NS, f"alias|{ct}|exact")
                out.append(
                    f"INSERT INTO instrument_aliases (id, alias_text, canonical_manifest_id, match_kind, "
                    f"created_at, updated_at) VALUES ('{aid}', {q(ct)}, '{target['id']}', 'exact', now(), now()) "
                    f"ON CONFLICT DO NOTHING;"
                )
            continue

        # No match → create manifest row from the doc's own metadata
        created += 1
        name = clean_title(title)
        key = (name.casefold(), auth)
        if key in used_names:
            # disambiguate colliding cleaned names with the URL tail
            tail = (url or doc_id).rstrip("/").rsplit("/", 1)[-1][:60]
            name = f"{name} [{tail}]"[:500]
            key = (name.casefold(), auth)
        used_names[key] = doc_id
        cat = CATEGORY_BY_SOURCE_TYPE.get(d["source_type"], "council_page")
        note = "Created from existing source_documents row during WP3 reconciliation (no index match)"
        if cat in ("council_page", "index_page"):
            note += "; navigation/administrative page, not an instrument (see CORPUS_SCOPE.md)"
        mid = uuid.uuid5(NS, f"manifest|{name}|{auth}")
        out.append(
            f"INSERT INTO target_manifest (id, instrument_name, category, issuing_authority, "
            f"canonical_url, status, source_document_id, notes, last_checked_at, created_at, updated_at) "
            f"VALUES ('{mid}', {q(name)}, {q(cat)}, {q(auth)}, {q(url)}, 'acquired', '{doc_id}', "
            f"{q(note)}, now(), now(), now()) "
            f"ON CONFLICT (instrument_name, issuing_authority) DO UPDATE SET "
            f"status = 'acquired', source_document_id = EXCLUDED.source_document_id, updated_at = now();"
        )
        if name.casefold() != title.casefold():
            aid = uuid.uuid5(NS, f"alias|{title[:500]}|exact")
            out.append(
                f"INSERT INTO instrument_aliases (id, alias_text, canonical_manifest_id, match_kind, "
                f"created_at, updated_at) VALUES ('{aid}', {q(title[:500])}, '{mid}', 'exact', now(), now()) "
                f"ON CONFLICT DO NOTHING;"
            )

    out.append("COMMIT;")
    (WP3 / "batch7_reconcile.sql").write_text("\n".join(out), encoding="utf-8")
    print(f"docs={len(docs)} matched_existing={matched} created={created}")


if __name__ == "__main__":
    main()
