"""Exa-backed document discovery sweep for one council.

Runs a battery of semantic searches (structure plans, LDPs, LPPs, activity
centre plans, scheme text, strategy) against the council's own domain plus
wa.gov.au, then diffs the hits against target_manifest to surface documents we
do NOT yet track. Output feeds seed_council_manifest.py after operator eyeball.

Reads EXA_API_KEY from the environment — never hardcode or commit keys.

Run inside the api container:
    docker exec -e EXA_API_KEY=... draftcheck-wa-v3-api-1 \
        python /app/scripts/wp_discover_docs.py --council "City of Canning" \
        --domains canning.wa.gov.au --out /app/reports/discover_canning.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, "/app/src")

import psycopg  # noqa: E402

EXA_URL = "https://api.exa.ai/search"

QUERY_BATTERY = [
    ("structure_plan", "{c} adopted structure plan document"),
    ("structure_plan", "{c} local structure plan report"),
    ("structure_plan", "{c} activity centre plan"),
    ("structure_plan", "{c} precinct structure plan"),
    ("local_development_plan", "{c} local development plan"),
    ("local_planning_policy", "{c} local planning policy"),
    ("local_planning_scheme", "{c} local planning scheme text"),
    ("local_planning_strategy", "{c} local planning strategy endorsed WAPC"),
]


def db_url() -> str:
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def exa_search(key: str, query: str, domains: list[str], n: int) -> list[dict]:
    body = {
        "query": query,
        "type": "auto",
        "numResults": n,
        "includeDomains": domains,
        "contents": {"highlights": True},
    }
    req = urllib.request.Request(
        EXA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"x-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("results", [])


def norm_url(u: str) -> str:
    u = (u or "").strip().lower()
    u = re.sub(r"[?#].*$", "", u)
    return u.rstrip("/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", required=True)
    ap.add_argument("--domains", required=True, help="comma-separated council domains (wa.gov.au auto-added)")
    ap.add_argument("--max-per-query", type=int, default=15)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    key = os.environ.get("EXA_API_KEY", "")
    if not key:
        print("ERROR: EXA_API_KEY not set", file=sys.stderr)
        return 2
    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    domains.append("wa.gov.au")

    with psycopg.connect(db_url()) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT instrument_name, canonical_url, status FROM target_manifest "
            "WHERE issuing_authority = %s OR instrument_name ILIKE '%%' || %s || '%%'",
            (args.council, args.council.split(" of ")[-1]),
        )
        known = {norm_url(r[1]): (r[0], r[2]) for r in cur.fetchall() if r[1]}

    seen: dict[str, dict] = {}
    total_cost = 0.0
    for category, tmpl in QUERY_BATTERY:
        q = tmpl.format(c=args.council)
        try:
            results = exa_search(key, q, domains, args.max_per_query)
        except Exception as exc:  # noqa: BLE001
            print(f"query failed ({q!r}): {exc}", file=sys.stderr)
            continue
        for r in results:
            u = norm_url(r.get("url", ""))
            if not u or u in seen:
                continue
            seen[u] = {
                "url": r.get("url"),
                "title": (r.get("title") or "").strip(),
                "category_guess": category,
                "highlight": (r.get("highlights") or [""])[0][:240],
                "query": q,
            }
        print(f"  {q!r}: {len(results)} results", flush=True)

    new_candidates, known_hits = [], []
    for u, item in seen.items():
        if u in known:
            known_hits.append({**item, "manifest_name": known[u][0], "manifest_status": known[u][1]})
        else:
            new_candidates.append(item)

    out = {
        "council": args.council,
        "domains": domains,
        "queries": len(QUERY_BATTERY),
        "unique_urls": len(seen),
        "already_in_manifest": len(known_hits),
        "new_candidates": new_candidates,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "new_candidates"}, indent=1))
    print(f"new candidates: {len(new_candidates)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
