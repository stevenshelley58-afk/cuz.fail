"""WP-D deterministic rule-key clustering scaffold.

Reads distinct ``rule_candidates.rule_key`` values, groups lightweight spelling
variants, and writes a JSON report plus a CSV canonical-key map. Heavy
clustering packages are intentionally optional; this first pass always has a
deterministic fallback and does not require new dependencies.

Run inside the api container:
    python /app/scripts/wp6_cluster_keys.py --report /app/reports/key_clusters.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, "/app/src")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402


DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "key_clusters.json"
DEFAULT_MAP_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "extraction" / "key_canonical_map.csv"

TOKEN_ALIASES = {
    "pct": "percent",
    "percentage": "percent",
    # NB: do NOT alias bare "per" / "cent" to "percent" — in planning rule_keys
    # "per" almost always means "per dwelling / per storey" (e.g.
    # parking_bays_per_dwelling), not a percentage.  Aliasing it corrupts those
    # canonical keys.  Only explicit pct/percentage map to percent.
    "metre": "m",
    "metres": "m",
    "meter": "m",
    "meters": "m",
    "maximum": "max",
    "minimum": "min",
    "setbacks": "setback",
    "requirements": "requirement",
}
DROP_TOKENS = {"rule", "rules", "req"}


@dataclass(frozen=True)
class KeyCluster:
    cluster_id: str
    normalized_key: str
    canonical_rule_key: str
    rule_keys: tuple[str, ...]
    total_candidates: int


# A normalized key with at least this many candidates is treated as an
# "established" concept.  If embedding clustering ever lands two established keys
# in the SAME cluster (e.g. primary_street_setback + rear_setback), that is an
# over-merge that would collapse a distinct check — surfaced as an anchor
# collision in the report for the WP-D spot-check gate.
ANCHOR_MIN_CANDIDATES = 20
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# The 11 hand-written seed-check canonical keys (mirrors
# draftcheck.checks.registry.SEED_CANONICAL_RULE_KEYS values).  These are DISTINCT
# regulated concepts that must never be merged into one another, even when their
# strings embed close ("wall_height" vs "boundary_wall_length" share "wall").
# They are forced anchors regardless of candidate count.
SEED_CANONICAL_KEYS = frozenset({
    "primary_street_setback", "rear_setback", "side_setback", "secondary_street_setback",
    "site_cover", "open_space", "garage_width", "garage_dominance",
    "boundary_wall_length", "building_height", "wall_height",
})


def database_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def optional_cluster_backend() -> dict[str, bool]:
    availability: dict[str, bool] = {}
    for module_name in ("sentence_transformers", "hdbscan"):
        try:
            __import__(module_name)
        except ImportError:
            availability[module_name] = False
        else:
            availability[module_name] = True
    return availability


def normalize_rule_key(value: str | None) -> str:
    raw = (value or "").casefold().strip()
    raw = raw.replace("&", " and ")
    tokens = re.findall(r"[a-z0-9]+", raw)
    normalized: list[str] = []
    for token in tokens:
        token = TOKEN_ALIASES.get(token, token)
        if token in DROP_TOKENS:
            continue
        if token.endswith("s") and len(token) > 4 and not re.fullmatch(r"r\d+s?", token):
            token = token[:-1]
        if normalized and normalized[-1] == token:
            continue
        normalized.append(token)
    return "_".join(normalized)


def canonical_from_normalized(normalized_key: str) -> str:
    return normalized_key[:160]


def cluster_rule_keys(rows: list[dict[str, Any]]) -> list[KeyCluster]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        normalized_key = normalize_rule_key(str(row["rule_key"]))
        if normalized_key:
            grouped[normalized_key].append(row)

    clusters: list[KeyCluster] = []
    for idx, normalized_key in enumerate(sorted(grouped), start=1):
        members = sorted(grouped[normalized_key], key=lambda row: str(row["rule_key"]).casefold())
        clusters.append(
            KeyCluster(
                cluster_id=f"key-{idx:05d}",
                normalized_key=normalized_key,
                canonical_rule_key=canonical_from_normalized(normalized_key),
                rule_keys=tuple(str(row["rule_key"]) for row in members),
                total_candidates=sum(int(row.get("candidate_count") or 0) for row in members),
            )
        )
    return clusters


def _representative_canonical(members: list[dict[str, Any]]) -> tuple[str, str]:
    """Pick (normalized_key, canonical) for an embedding cluster.

    Canonical = the normalized form of the member with the most candidates
    (tiebreaker: shortest normalized key).  So a cluster that contains the big
    established ``site_area`` variant canonicalises to ``site_area`` and pulls the
    long-tail ``r40_grouped_dwelling_site_area_min`` orphans into it.
    """
    def _rank(row: dict[str, Any]) -> tuple[int, int]:
        norm = normalize_rule_key(str(row["rule_key"]))
        return (int(row.get("candidate_count") or 0), -len(norm))

    rep = max(members, key=_rank)
    norm = normalize_rule_key(str(rep["rule_key"])) or str(rep["rule_key"])
    return norm, norm[:160]


def embed_cluster_rule_keys(
    rows: list[dict[str, Any]],
    *,
    model_name: str = EMBED_MODEL,
    min_cluster_size: int = 2,
    min_samples: int = 1,
    cluster_selection_epsilon: float = 0.0,
) -> list[KeyCluster]:
    """Semantic clustering of rule_keys via sentence-transformers + HDBSCAN.

    Requires the optional ``sentence_transformers`` and ``hdbscan`` backends; the
    caller is responsible for checking availability first.  Normalised keys are
    embedded (L2-normalised, so euclidean distance is monotonic with cosine) and
    clustered; HDBSCAN noise points (label ``-1``) each become their own singleton
    cluster so nothing is silently dropped.  Output matches the deterministic
    path's ``KeyCluster`` shape, so the report/CSV/apply contract is unchanged.
    """
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415
    import hdbscan  # noqa: PLC0415

    texts = [normalize_rule_key(str(row["rule_key"])) or str(row["rule_key"]) for row in rows]
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_epsilon=cluster_selection_epsilon,
    )
    labels = clusterer.fit_predict(embeddings)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    singleton_seq = 0
    for row, label in zip(rows, labels, strict=True):
        if int(label) < 0:
            singleton_seq += 1
            grouped[f"noise-{singleton_seq}"].append(row)
        else:
            grouped[f"hdb-{int(label)}"].append(row)

    clusters: list[KeyCluster] = []
    # Deterministic ordering: by representative canonical, then size.
    ordered = sorted(
        grouped.items(),
        key=lambda kv: (_representative_canonical(kv[1])[1], -len(kv[1])),
    )
    for idx, (_label, members) in enumerate(ordered, start=1):
        members_sorted = sorted(members, key=lambda row: str(row["rule_key"]).casefold())
        normalized_key, canonical = _representative_canonical(members_sorted)
        clusters.append(
            KeyCluster(
                cluster_id=f"key-{idx:05d}",
                normalized_key=normalized_key,
                canonical_rule_key=canonical,
                rule_keys=tuple(str(row["rule_key"]) for row in members_sorted),
                total_candidates=sum(int(row.get("candidate_count") or 0) for row in members_sorted),
            )
        )
    return clusters


def anchor_set(
    rows: list[dict[str, Any]],
    *,
    min_candidates: int = ANCHOR_MIN_CANDIDATES,
) -> set[str]:
    """Distinct normalized keys that are DISTINCT regulated concepts.

    = the seed-check canonicals (always) PLUS any key whose summed candidate count
    is >= ``min_candidates``.  Used both to flag and to GUARD over-merges.
    """
    by_norm_count: dict[str, int] = defaultdict(int)
    for row in rows:
        norm = normalize_rule_key(str(row["rule_key"]))
        if norm:
            by_norm_count[norm] += int(row.get("candidate_count") or 0)
    established = {k for k, n in by_norm_count.items() if n >= min_candidates}
    return established | set(SEED_CANONICAL_KEYS)


def _candidate_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["rule_key"])] = int(row.get("candidate_count") or 0)
    return counts


def guard_seed_collisions(
    clusters: list[KeyCluster],
    rows: list[dict[str, Any]],
    anchors: set[str],
) -> list[KeyCluster]:
    """Revert any cluster that merged 2+ distinct anchor concepts to deterministic.

    Embedding clustering pulls long-tail orphans into established checks (good), but
    occasionally merges two DISTINCT anchors whose strings embed close
    (``wall_height`` into ``boundary_wall_length``).  Such a cluster is split back
    into per-normalized-key deterministic clusters, so the good merges survive while
    the bad one is undone.  Idempotent and deterministic (re-id'd by canonical).
    """
    counts = _candidate_counts(rows)
    kept: list[KeyCluster] = []
    for cluster in clusters:
        present = {norm for rk in cluster.rule_keys if (norm := normalize_rule_key(rk)) in anchors}
        if len(present) < 2:
            kept.append(cluster)
            continue
        # Over-merge: regroup this cluster's members by deterministic normalized key.
        sub: dict[str, list[str]] = defaultdict(list)
        for rk in cluster.rule_keys:
            sub[normalize_rule_key(rk) or rk].append(rk)
        for norm, rks in sub.items():
            kept.append(KeyCluster(
                cluster_id="tmp",
                normalized_key=norm,
                canonical_rule_key=norm[:160],
                rule_keys=tuple(sorted(rks, key=str.casefold)),
                total_candidates=sum(counts.get(rk, 0) for rk in rks),
            ))
    # Re-id deterministically by canonical then size.
    kept.sort(key=lambda c: (c.canonical_rule_key, -len(c.rule_keys)))
    return [
        KeyCluster(
            cluster_id=f"key-{idx:05d}",
            normalized_key=c.normalized_key,
            canonical_rule_key=c.canonical_rule_key,
            rule_keys=c.rule_keys,
            total_candidates=c.total_candidates,
        )
        for idx, c in enumerate(kept, start=1)
    ]


# Qualifier tokens that distinguish a variant from its parent concept (R-code,
# min/max/avg).  A member is a safe variant of a target when the target's tokens
# are a subset of the member's tokens (member = target + qualifiers).
# Includes bare numeric fragments because normalisation splits decimal R-codes
# (R2.5 -> tokens "r2" + "5"); the trailing digit is part of the density code.
_QUALIFIER_RE = re.compile(r"^(r\d+(_\d+)?|sl|ac\d*|\d+)$")


def _tokens(normalized_key: str) -> set[str]:
    return set(normalized_key.split("_")) if normalized_key else set()


def is_variant_of(member_norm: str, target_norm: str) -> bool:
    """True when ``member`` is ``target`` plus R-code/min/max qualifiers only.

    Subset direction is deliberate and conservative: it absorbs ``r20_min_frontage``
    into ``min_frontage`` and ``site_cover_max_r30`` into ``site_cover``, but NEVER
    ``driveway_length_min`` into ``driveway_width`` (width ∉ member) or
    ``maximum_lot_area`` into ``min_lot_area_per_dwelling`` (per/dwelling ∉ member).
    """
    if member_norm == target_norm:
        return True
    mt, tt = _tokens(member_norm), _tokens(target_norm)
    if not tt or not tt <= mt:
        return False
    # Extra tokens in the member must all be qualifiers (R-code / min / max / avg).
    extra = mt - tt
    return all(_QUALIFIER_RE.match(tok) or tok in {"min", "max", "avg"} for tok in extra)


def established_targets(conn: Connection, *, min_approved: int = 5) -> set[str]:
    """Canonical keys that ARE real check buckets: >= min_approved approved rules
    (in the rules table) or a seed canonical, minus the non-rule denylist tokens."""
    deny = (
        "none", "penalty", "fine", "interest_rate", "development_area_number",
        "clause_number", "table_number", "figure_number", "density_code",
        "density_recode", "residential_density", "fee", "quorum",
        "other_facility_requirement", "vote", "levy",
    )
    rows = conn.execute(
        text(
            """
            SELECT canonical_rule_key
            FROM rules
            WHERE lifecycle_status = 'approved' AND canonical_rule_key IS NOT NULL
            GROUP BY canonical_rule_key
            HAVING count(*) >= :n
            """
        ),
        {"n": min_approved},
    )
    targets = {str(r[0]) for r in rows} | set(SEED_CANONICAL_KEYS)
    return {t for t in targets if not any(tok in t for tok in deny)}


def absorb_into_established(
    clusters: list[KeyCluster],
    rows: list[dict[str, Any]],
    targets: set[str],
) -> list[KeyCluster]:
    """Keep ONLY clean variant-absorptions into established check buckets.

    For each embedding cluster: if its canonical is an established target, keep the
    members that are genuine variants of it (``is_variant_of``) and revert the rest
    to their own deterministic key; if the canonical is NOT a target (a long-tail
    merge that would mint a junk check), revert the whole cluster to deterministic.
    The result = deterministic clustering PLUS safe orphan-absorption, with no new
    junk checks and no cross-dimension/operator merges.
    """
    counts = _candidate_counts(rows)
    kept: list[KeyCluster] = []

    def _emit(norm: str, rks: list[str]) -> None:
        kept.append(KeyCluster(
            cluster_id="tmp",
            normalized_key=norm,
            canonical_rule_key=norm[:160],
            rule_keys=tuple(sorted(rks, key=str.casefold)),
            total_candidates=sum(counts.get(rk, 0) for rk in rks),
        ))

    for cluster in clusters:
        canon = cluster.canonical_rule_key
        if len(cluster.rule_keys) == 1:
            kept.append(cluster)
            continue
        if canon in targets:
            absorbed = [rk for rk in cluster.rule_keys if is_variant_of(normalize_rule_key(rk), canon)]
            reverted = [rk for rk in cluster.rule_keys if rk not in absorbed]
            if absorbed:
                kept.append(KeyCluster(
                    cluster_id="tmp", normalized_key=canon, canonical_rule_key=canon[:160],
                    rule_keys=tuple(sorted(absorbed, key=str.casefold)),
                    total_candidates=sum(counts.get(rk, 0) for rk in absorbed),
                ))
            for rk in reverted:
                _emit(normalize_rule_key(rk) or rk, [rk])
        else:
            for rk in cluster.rule_keys:
                _emit(normalize_rule_key(rk) or rk, [rk])

    kept.sort(key=lambda c: (c.canonical_rule_key, -len(c.rule_keys)))
    return [
        KeyCluster(
            cluster_id=f"key-{idx:05d}",
            normalized_key=c.normalized_key,
            canonical_rule_key=c.canonical_rule_key,
            rule_keys=c.rule_keys,
            total_candidates=c.total_candidates,
        )
        for idx, c in enumerate(kept, start=1)
    ]


def anchor_collisions(
    clusters: list[KeyCluster],
    rows: list[dict[str, Any]],
    *,
    min_candidates: int = ANCHOR_MIN_CANDIDATES,
) -> list[dict[str, Any]]:
    """Clusters that merged 2+ DISTINCT anchor concepts — the WP-D over-merge flag."""
    anchors = anchor_set(rows, min_candidates=min_candidates)
    collisions: list[dict[str, Any]] = []
    for cluster in clusters:
        present = sorted({
            norm for rk in cluster.rule_keys
            if (norm := normalize_rule_key(rk)) in anchors
        })
        if len(present) >= 2:
            collisions.append({
                "canonical_rule_key": cluster.canonical_rule_key,
                "merged_anchors": present,
                "total_candidates": cluster.total_candidates,
            })
    return collisions


def load_rule_keys(conn: Connection) -> list[dict[str, Any]]:
    result = conn.execute(
        text(
            """
            SELECT rule_key, count(*) AS candidate_count
            FROM rule_candidates
            WHERE rule_key IS NOT NULL AND btrim(rule_key) <> ''
            GROUP BY rule_key
            ORDER BY rule_key
            """
        )
    )
    return [dict(row._mapping) for row in result]


def write_report(
    path: Path,
    clusters: list[KeyCluster],
    backend: dict[str, bool],
    *,
    mode: str = "deterministic_rule_key_scaffold",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "wp": "WP-D",
        "mode": mode,
        "optional_backends_available": backend,
        "summary": {
            "clusters": len(clusters),
            "rule_keys": sum(len(cluster.rule_keys) for cluster in clusters),
            "variant_clusters": sum(1 for cluster in clusters if len(cluster.rule_keys) > 1),
            "candidate_rows": sum(cluster.total_candidates for cluster in clusters),
        },
        "clusters": [
            {
                "cluster_id": cluster.cluster_id,
                "normalized_key": cluster.normalized_key,
                "canonical_rule_key": cluster.canonical_rule_key,
                "rule_keys": list(cluster.rule_keys),
                "total_candidates": cluster.total_candidates,
            }
            for cluster in clusters
        ],
        "notes": [
            "canonical_rule_key values are deterministic normalizations of rule_key variants."
            if mode.startswith("deterministic")
            else "canonical_rule_key chosen as the highest-candidate member of each embedding cluster.",
        ],
    }
    if extra:
        report.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _top_merges(clusters: list[KeyCluster], limit: int = 20) -> list[dict[str, Any]]:
    """The biggest multi-key clusters — the WP-D top-N spot-check material."""
    multi = [c for c in clusters if len(c.rule_keys) > 1]
    multi.sort(key=lambda c: (c.total_candidates, len(c.rule_keys)), reverse=True)
    return [
        {
            "canonical_rule_key": c.canonical_rule_key,
            "n_members": len(c.rule_keys),
            "total_candidates": c.total_candidates,
            "members": list(c.rule_keys)[:40],
        }
        for c in multi[:limit]
    ]


def write_map(path: Path, clusters: list[KeyCluster]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rule_key",
                "canonical_rule_key",
                "normalized_key",
                "cluster_id",
                "cluster_size",
            ],
        )
        writer.writeheader()
        rows = 0
        for cluster in clusters:
            for rule_key in cluster.rule_keys:
                writer.writerow(
                    {
                        "rule_key": rule_key,
                        "canonical_rule_key": cluster.canonical_rule_key,
                        "normalized_key": cluster.normalized_key,
                        "cluster_id": cluster.cluster_id,
                        "cluster_size": len(cluster.rule_keys),
                    }
                )
                rows += 1
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--map-output", default=str(DEFAULT_MAP_OUTPUT))
    parser.add_argument(
        "--embed",
        action="store_true",
        help="use sentence-transformers + HDBSCAN semantic clustering "
        "(requires the optional backends; falls back is NOT silent).",
    )
    parser.add_argument("--model", default=EMBED_MODEL)
    parser.add_argument("--min-cluster-size", type=int, default=2)
    parser.add_argument("--min-samples", type=int, default=1)
    parser.add_argument("--cluster-selection-epsilon", type=float, default=0.0)
    parser.add_argument(
        "--absorb-established",
        action="store_true",
        help="SAFE production mode: keep only clean variant-absorptions into existing "
        "check buckets; revert long-tail merges to deterministic (no junk checks).",
    )
    args = parser.parse_args()

    engine = create_engine(database_url())
    with engine.begin() as conn:
        rows = load_rule_keys(conn)
        targets = established_targets(conn) if (args.embed and args.absorb_established) else set()

    backend = optional_cluster_backend()
    extra: dict[str, Any] | None = None
    if args.embed:
        missing = [name for name, ok in backend.items() if not ok]
        if missing:
            raise SystemExit(
                f"--embed requires optional backends not installed: {', '.join(missing)}"
            )
        raw_clusters = embed_cluster_rule_keys(
            rows,
            model_name=args.model,
            min_cluster_size=args.min_cluster_size,
            min_samples=args.min_samples,
            cluster_selection_epsilon=args.cluster_selection_epsilon,
        )
        # Guard: undo over-merges that collapse 2+ distinct anchor/seed concepts
        # (e.g. wall_height into boundary_wall_length), keeping the good merges.
        anchors = anchor_set(rows)
        pre_collisions = anchor_collisions(raw_clusters, rows)
        clusters = guard_seed_collisions(raw_clusters, rows, anchors)
        if args.absorb_established:
            clusters = absorb_into_established(clusters, rows, targets)
        collisions = anchor_collisions(clusters, rows)
        mode = "embedding_hdbscan_absorb" if args.absorb_established else "embedding_hdbscan"
        extra = {
            # WP-D gate material: review these BEFORE applying the map.
            "collisions_before_guard": pre_collisions,
            "collisions_reverted_by_guard": len(pre_collisions),
            "anchor_collisions": collisions,
            "anchor_collision_count": len(collisions),
            "absorb_established": args.absorb_established,
            "established_targets": len(targets),
            "top_merges": _top_merges(clusters),
            "params": {
                "model": args.model,
                "min_cluster_size": args.min_cluster_size,
                "min_samples": args.min_samples,
                "cluster_selection_epsilon": args.cluster_selection_epsilon,
            },
        }
    else:
        clusters = cluster_rule_keys(rows)
        mode = "deterministic_rule_key_scaffold"

    report = write_report(Path(args.report), clusters, backend, mode=mode, extra=extra)
    map_rows = write_map(Path(args.map_output), clusters)
    report["map_output"] = str(Path(args.map_output))
    report["summary"]["map_rows"] = map_rows
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Keep stdout compact; the full report (incl. all clusters) is on disk.
    summary_view = {k: report[k] for k in ("mode", "summary") if k in report}
    if extra:
        summary_view["collisions_reverted_by_guard"] = report.get("collisions_reverted_by_guard")
        summary_view["collisions_before_guard"] = report.get("collisions_before_guard")
        summary_view["anchor_collision_count"] = report.get("anchor_collision_count")
        summary_view["top_merges"] = report.get("top_merges")
    print(json.dumps(summary_view, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
