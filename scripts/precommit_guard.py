"""Repository hygiene guard for staged files.

This hook blocks large files, private runtime artifacts, and obvious secrets
before they enter Git. It is intentionally conservative for PR0/PR1, where the
workspace contains many untracked runtime artifacts.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


MAX_BYTES = 5 * 1024 * 1024
FORBIDDEN_PREFIXES = (
    ".storage/",
    ".venv/",
    ".vercel/",
    ".codex/",
    "build/",
    "backups/",
    "data/corpus/",
    "node_modules/",
    "web/node_modules/",
    "web/dist/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".codegraph/",
)
FORBIDDEN_SUFFIXES = (
    ".db",
    ".db-wal",
    ".db-shm",
    ".sqlite",
    ".sqlite-wal",
    ".sqlite-shm",
)
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\b(openai|anthropic|github|stripe|vercel|supabase)[_-]?(api[_-]?)?key\b\s*[:=]\s*['\"][^'\"\s]{16,}['\"]"),
    re.compile(r"(?i)\b(secret|password|token)\b\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{16,}['\"]"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
)


def staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def normalise(path: str) -> str:
    normalised = path.replace(os.sep, "/")
    while normalised.startswith("./"):
        normalised = normalised[2:]
    return normalised.lstrip("/")


def looks_binary(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return b"\0" in handle.read(4096)
    except OSError:
        return True


def scan_secret(path: Path) -> str | None:
    if looks_binary(path):
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None


def check_file(path_text: str) -> list[str]:
    path_key = normalise(path_text)
    path = Path(path_text)
    errors: list[str] = []

    if path_key == ".env" or (path_key.startswith(".env.") and path_key != ".env.example"):
        errors.append(f"{path_key}: forbidden environment file path")

    if path_key.startswith(FORBIDDEN_PREFIXES) or path_key.endswith(FORBIDDEN_SUFFIXES):
        errors.append(f"{path_key}: forbidden runtime/private artifact path")

    if path.exists() and path.is_file():
        size = path.stat().st_size
        if size > MAX_BYTES:
            errors.append(f"{path_key}: {size} bytes exceeds 5 MB guard")
        if size <= MAX_BYTES and path_key != ".env.example":
            secret = scan_secret(path)
            if secret:
                errors.append(f"{path_key}: potential secret matched {secret}")

    return errors


def main(argv: list[str]) -> int:
    files = argv[1:] or staged_files()
    errors: list[str] = []
    for file_name in files:
        errors.extend(check_file(file_name))

    if errors:
        print("precommit_guard failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("precommit_guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
