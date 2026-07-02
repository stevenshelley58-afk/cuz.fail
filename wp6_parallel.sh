#!/bin/bash
# WP6 extraction loop - PARALLELIZED version
# Runs N source versions concurrently using background jobs
set -euo pipefail

COMPOSE_DIR="/srv/draftcheck/app/infra/v3"
LOG="/srv/draftcheck/app/reports/wp6_extraction_loop.log"
MAX_WORKERS=6  # Number of concurrent source versions

echo "=== WP6 Parallel Extraction Loop $(date -Iseconds) ===" | tee -a "$LOG"

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
ACTIVE=0

echo "Found $TOTAL source versions to extract. Max workers: $MAX_WORKERS" | tee -a "$LOG"

for SV_ID in $IDS; do
    COUNT=$((COUNT + 1))
    
    # Wait if we've hit max workers
    while [ "$ACTIVE" -ge "$MAX_WORKERS" ]; do
        sleep 5
        ACTIVE=$(jobs -r | wc -l)
    done
    
    echo "[$COUNT/$TOTAL] Starting extraction for source_version $SV_ID (active: $ACTIVE)" | tee -a "$LOG"
    
    # Run extraction in background
    (
        sudo docker compose exec -T api python scripts/wp6_extract.py \
            --source-version "$SV_ID" \
            --workers 2 \
            --report "/app/reports/wp6_${SV_ID}.json" \
            2>&1 | tee -a "$LOG"
        
        # Copy report from container to host
        API_CONTAINER=$(sudo docker compose ps -q api)
        sudo docker cp "$API_CONTAINER:/app/reports/wp6_${SV_ID}.json" "/srv/draftcheck/app/reports/wp6_${SV_ID}.json" 2>/dev/null || true
        
        echo "[$COUNT/$TOTAL] Completed source_version $SV_ID" | tee -a "$LOG"
    ) &
    
    ACTIVE=$(jobs -r | wc -l)
    
    # Brief delay to stagger starts
    sleep 3
done

# Wait for all background jobs to finish
wait

echo "=== WP6 Parallel Extraction Loop Complete $(date -Iseconds) ===" | tee -a "$LOG"

# Final state check
sudo docker compose exec -T db psql -U draftcheck -c "
SELECT COUNT(*) FROM clauses c 
WHERE disposition = 'rule_bearing' 
AND NOT EXISTS (SELECT 1 FROM rules r WHERE r.clause_id = c.id);
" | tee -a "$LOG"
