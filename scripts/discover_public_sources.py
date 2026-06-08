from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from draftcheck_scraper.source_discovery import DiscoverySettings, discover_manifest_sources


def main() -> None:
    args = _parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest_yaml = manifest_path.read_text(encoding="utf-8")
    output_root = Path(args.output_root).expanduser().resolve() if args.output_root else _default_output_root()
    settings = DiscoverySettings(
        max_depth=args.max_depth,
        max_urls_per_anchor=args.max_urls_per_anchor,
        delay_seconds=args.delay_seconds,
        include_html=args.include_html,
    )
    summary = asyncio.run(discover_manifest_sources(manifest_yaml, output_root, settings))
    print(json.dumps(summary.to_dict(), indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover and parse lawful public source documents into a Hermes-compatible corpus."
    )
    parser.add_argument(
        "--manifest",
        default="data/seed/source_manifest.example.yaml",
        help="Source manifest YAML containing official source anchors.",
    )
    parser.add_argument("--output-root", help="Corpus output root. Defaults to data/corpus/discovery-<timestamp>.")
    parser.add_argument("--max-depth", type=int, default=1, help="Maximum HTML discovery depth from each anchor.")
    parser.add_argument(
        "--max-urls-per-anchor",
        type=int,
        default=25,
        help="Maximum candidate URLs fetched per source anchor.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
        help="Per-host politeness delay between requests.",
    )
    parser.add_argument(
        "--include-html",
        action="store_true",
        help="Also store parsed HTML pages as source rows. By default only document/text responses are stored.",
    )
    return parser.parse_args()


def _default_output_root() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return Path("data") / "corpus" / f"discovery-{stamp}"


if __name__ == "__main__":
    main()
