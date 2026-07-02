#!/bin/bash
# WP6 extraction loop: run wp6_extract.py for each source version with uncovered rule-bearing clauses
set -euo pipefail

COMPOSE_DIR="/srv/draftcheck/app/infra/v3"
LOG="/srv/draftcheck/app/reports/wp6_extraction_loop.log"

echo "=== WP6 Extraction Loop $(date -Iseconds) ===" | tee -a "$LOG"

cd "$COMPOSE_DIR"

# Get all source version IDs with uncovered rule-bearing clauses
IDS=$(sudo docker compose exec -T db psql -U draftcheck -t -A -F" " -c "
SELECT DISTINCT sv.id
FROM source_versions sv
JOIN clauses c ON c.source_version_id = sv.id
WHERE c.disposition = 'rule_bearing'
AND NOT EXISTS (SELECT 1 FROM rules r WHERE r.clause_id = c.id)
ORDER BY sv.id;
")

TOTAL=$(echo "$IDS" | wc -w)
COUNT=0

for SV_ID in $IDS; do
    COUNT=$((COUNT + 1))
    echo "[$COUNT/$TOTAL] Extracting source_version $SV_ID" | tee -a "$LOG"
    
    sudo docker compose exec -T api python scripts/wp6_extract.py \
        --source-version "$SV_ID" \
        --workers 2 \
        --report "/app/reports/wp6_${SV_ID}.json" \
        2>&1 | tee -a "$LOG"
    
    # Copy report from container to host
    API_CONTAINER=$(sudo docker compose ps -q api)
    sudo docker cp "$API_CONTAINER:/app/reports/wp6_${SV_ID}.json" "/srv/draftcheck/app/reports/wp6_${SV_ID}.json" 2>/dev/null || true
    
    # Sleep briefly to avoid rate limiting
    sleep 2
done

echo "=== WP6 Extraction Loop Complete $(date -Iseconds) ===" | tee -a "$LOG"

# Final state check
cd "$COMPOSE_DIR"
sudo docker compose exec -T db psql -U draftcheck -c "
SELECT COUNT(*) FROM clauses c 
WHERE disposition = 'rule_bearing' 
AND NOT EXISTS (SELECT 1 FROM rules r WHERE r.clause_id = c.id);
" | tee -a "$LOG"
