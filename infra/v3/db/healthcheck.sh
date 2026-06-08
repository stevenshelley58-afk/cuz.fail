#!/bin/sh
set -eu

pg_isready -U "${POSTGRES_USER:-draftcheck}" -d "${POSTGRES_DB:-draftcheck}"

extension_count="$(
  psql \
    -U "${POSTGRES_USER:-draftcheck}" \
    -d "${POSTGRES_DB:-draftcheck}" \
    -tAc "SELECT count(*) FROM pg_extension WHERE extname IN ('postgis', 'vector');" |
    tr -d '[:space:]'
)"

test "$extension_count" = "2"
