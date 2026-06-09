"""Streaming corpus pipeline: parallel acquisition + extraction.

Downloads run on async workers (politeness-limited per host); every document
is handed to a process pool for pdfplumber extraction THE MOMENT it lands,
while remaining downloads continue. The manifest is updated by a single
writer (the event loop) after every state change, so progress is durable
and the run is resumable.

Usage:
  python scripts/pipeline.py                  # everything pending + un-extracted
  python scripts/pipeline.py --priority-only  # just the priority list
  python scripts/pipeline.py --ids A,B,C
  python scripts/pipeline.py --limit 20
"""
from __future__ import annotations

import asyncio
import random
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from urllib.parse import urlparse

from acquire_all import ACQ_REPORT, acquire_row, make_client
from corpus_lib import append_report, log, read_manifest, today, update_row, write_manifest
from extract_text import EXT_REPORT, extract_document

PRIORITY_IDS = [
    "PC-001", "PC-002", "MEL-SCH-001", "MEL-LPP-021", "MEL-LPP-014",
    "MEL-LPP-009", "MEL-SP-001", "FRE-LPP-006", "REG-001", "RS-001",
]

GLOBAL_FETCH_LIMIT = 12
PER_HOST_LIMIT = 4
PLAYWRIGHT_LIMIT = 3
EXTRACT_WORKERS = 8


class Counters:
    def __init__(self) -> None:
        self.acquired = 0
        self.acq_failed = 0
        self.blocked = 0
        self.extracted = 0
        self.ext_failed = 0


async def run_pipeline(ids: list[str] | None, limit: int | None, priority_only: bool) -> Counters:
    rows = read_manifest()
    by_id = {r["id"]: r for r in rows}

    to_acquire = [r for r in rows if r["status"] == "pending" and r.get("canonical_url", "").strip()]
    to_extract_only = [r for r in rows if r["status"] == "acquired"]

    # priority rows first, original manifest order after that
    rank = {pid: i for i, pid in enumerate(PRIORITY_IDS)}
    to_acquire.sort(key=lambda r: rank.get(r["id"], len(rank) + 1))
    if priority_only:
        to_acquire = [r for r in to_acquire if r["id"] in rank]
        to_extract_only = [r for r in to_extract_only if r["id"] in rank]
    if ids:
        wanted = set(ids)
        to_acquire = [r for r in to_acquire if r["id"] in wanted]
        to_extract_only = [r for r in to_extract_only if r["id"] in wanted]
    if limit:
        to_acquire = to_acquire[:limit]

    counters = Counters()
    loop = asyncio.get_running_loop()
    pool = ProcessPoolExecutor(max_workers=EXTRACT_WORKERS)
    global_sem = asyncio.Semaphore(GLOBAL_FETCH_LIMIT)
    host_sems: dict[str, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(PER_HOST_LIMIT))
    extraction_tasks: list[asyncio.Task] = []

    log(f"pipeline start: {len(to_acquire)} to acquire, {len(to_extract_only)} already-acquired to extract")

    async def extract_async(row: dict) -> None:
        res = await loop.run_in_executor(
            pool, extract_document,
            row["id"], row["instrument_name"], row["category"], row["issuing_authority"],
        )
        append_report(EXT_REPORT, res)
        if res.get("ok"):
            counters.extracted += 1
            update_row(rows, row["id"], status="extracted", last_checked_at=today())
            write_manifest(rows)
            log(f"  EXTRACTED {row['id']} ({res['pages']}p, {res['refs']} refs) "
                f"[{counters.extracted} done]")
        else:
            counters.ext_failed += 1
            update_row(rows, row["id"], last_checked_at=today(),
                       notes=(row.get("notes", "") + f" | extract failed: {res.get('error')}").strip(" |"))
            write_manifest(rows)
            log(f"  EXTRACT-FAIL {row['id']}: {res.get('error')}")

    async def acquire_and_stream(client, row: dict) -> None:
        host = urlparse(row["canonical_url"]).netloc
        async with global_sem, host_sems[host]:
            await asyncio.sleep(random.uniform(0.2, 0.8))  # politeness jitter
            res = await acquire_row(client, row)
        append_report(ACQ_REPORT, res)
        if res.get("ok"):
            counters.acquired += 1
            note_bits = [b for b in (res.get("note"), res.get("note_extra")) if b]
            update_row(rows, row["id"], status="acquired", last_checked_at=today(),
                       notes=(row.get("notes", "") + (" | " + "; ".join(note_bits) if note_bits else "")).strip(" |"))
            write_manifest(rows)
            log(f"ACQUIRED {row['id']} <- {res.get('final_url', '')[:90]} [{counters.acquired} done]")
            extraction_tasks.append(asyncio.create_task(extract_async(row)))
        elif res.get("dead"):
            counters.blocked += 1
            update_row(rows, row["id"], status="blocked", last_checked_at=today(),
                       notes=f"dead URL: {res.get('error')} :: {row.get('canonical_url')}")
            write_manifest(rows)
            log(f"BLOCKED {row['id']}: {res.get('error')}")
        else:
            counters.acq_failed += 1
            update_row(rows, row["id"], last_checked_at=today(),
                       notes=(row.get("notes", "") + f" | fetch failed: {res.get('error')}").strip(" |")[:500])
            write_manifest(rows)
            log(f"FAILED {row['id']}: {res.get('error')}")

    try:
        # extraction of already-acquired rows starts immediately, in parallel
        for row in to_extract_only:
            extraction_tasks.append(asyncio.create_task(extract_async(row)))

        async with make_client() as client:
            await asyncio.gather(*(acquire_and_stream(client, r) for r in to_acquire))

        if extraction_tasks:
            await asyncio.gather(*extraction_tasks)
    finally:
        pool.shutdown(wait=True)

    log("pipeline done: "
        f"acquired={counters.acquired} acq_failed={counters.acq_failed} "
        f"blocked={counters.blocked} extracted={counters.extracted} ext_failed={counters.ext_failed}")
    return counters


if __name__ == "__main__":
    arg_ids = None
    arg_limit = None
    if "--ids" in sys.argv:
        arg_ids = sys.argv[sys.argv.index("--ids") + 1].split(",")
    if "--limit" in sys.argv:
        arg_limit = int(sys.argv[sys.argv.index("--limit") + 1])
    asyncio.run(run_pipeline(arg_ids, arg_limit, "--priority-only" in sys.argv))
