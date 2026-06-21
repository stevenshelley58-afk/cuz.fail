#!/usr/bin/env bash
# WP6 tail launcher: safely adds extra source-version concurrency from the end
# of the uncovered queue while the main ascending launcher is still running.
set -euo pipefail

COMPOSE_DIR="${WP6_COMPOSE_DIR:-/srv/draftcheck/app/infra/v3}"
LOG="${WP6_TAIL_LOG:-/srv/draftcheck/app/reports/wp6_parallel_tail.log}"
MAX_WORKERS="${WP6_TAIL_MAX_WORKERS:-6}"
LIMIT="${WP6_TAIL_LIMIT:-80}"
ORDER="${WP6_TAIL_ORDER:-DESC}"

if ! [[ "$MAX_WORKERS" =~ ^[1-9][0-9]*$ && "$LIMIT" =~ ^[1-9][0-9]*$ ]]; then
    echo "WP6_TAIL_MAX_WORKERS and WP6_TAIL_LIMIT must be positive integers" >&2
    exit 2
fi
if [[ "$ORDER" != "ASC" && "$ORDER" != "DESC" ]]; then
    echo "WP6_TAIL_ORDER must be ASC or DESC" >&2
    exit 2
fi

echo "=== WP6 Tail Extraction Loop $(date -Iseconds) ===" | tee -a "$LOG"
cd "$COMPOSE_DIR"

ACTIVE_IDS="$(ps -ef | sed -n 's/.*--source-version \([0-9a-fA-F-]\{36\}\).*/\1/p' | sort -u | tr '\n' ' ')"

IDS=$(sudo docker compose exec -T db psql -U draftcheck -t -A -F" " -c "
SELECT DISTINCT sv.id
FROM source_versions sv
JOIN clauses c ON c.source_version_id = sv.id
WHERE c.disposition = 'rule_bearing'
  AND NOT EXISTS (
      SELECT 1 FROM rules r WHERE r.clause_id = c.id AND r.metadata_json->>'wp6' = 'true'
  )
ORDER BY sv.id ${ORDER}
LIMIT ${LIMIT};
")

COUNT=0
ACTIVE=0
TOTAL=$(echo "$IDS" | wc -w)

echo "Found $TOTAL tail source versions. Max workers: $MAX_WORKERS" | tee -a "$LOG"

for SV_ID in $IDS; do
    if echo " $ACTIVE_IDS " | grep -q " $SV_ID "; then
        echo "Skipping active source_version $SV_ID" | tee -a "$LOG"
        continue
    fi

    COUNT=$((COUNT + 1))
    while [ "$ACTIVE" -ge "$MAX_WORKERS" ]; do
        sleep 5
        ACTIVE=$(jobs -r | wc -l)
    done

    echo "[$COUNT/$TOTAL] Starting tail extraction for source_version $SV_ID (active: $ACTIVE)" | tee -a "$LOG"
    (
        sudo docker compose exec -T api python scripts/wp6_extract.py \
            --source-version "$SV_ID" \
            --workers 2 \
            --report "/app/reports/wp6_tail_${SV_ID}.json" \
            2>&1 | tee -a "$LOG"

        API_CONTAINER=$(sudo docker compose ps -q api)
        sudo docker cp "$API_CONTAINER:/app/reports/wp6_tail_${SV_ID}.json" \
            "/srv/draftcheck/app/reports/wp6_tail_${SV_ID}.json" 2>/dev/null || true

        echo "[$COUNT/$TOTAL] Completed tail source_version $SV_ID" | tee -a "$LOG"
    ) &

    ACTIVE=$(jobs -r | wc -l)
    sleep 2
done

wait

echo "=== WP6 Tail Extraction Loop Complete $(date -Iseconds) ===" | tee -a "$LOG"
