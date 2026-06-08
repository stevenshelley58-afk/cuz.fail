#!/usr/bin/env bash
set -euo pipefail

pg_isready -U "${POSTGRES_USER:?}" -d "${POSTGRES_DB:?}" >/dev/null

psql \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -v ON_ERROR_STOP=1 \
  -tAc "
    select case
      when exists (select 1 from pg_extension where extname = 'postgis')
       and exists (select 1 from pg_extension where extname = 'vector')
      then 1
      else 0
    end
  " | grep -qx 1
