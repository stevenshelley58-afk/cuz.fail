#!/bin/bash
# Auto-follow-up script: runs WP5 -> WP7 -> WP8 after WP6 completes
set -euo pipefail

COMPOSE_DIR="/srv/draftcheck/app/infra/v3"
LOG="/srv/draftcheck/app/reports/followup.log"

echo "=== Follow-up pipeline waiting for WP6 $(date -Iseconds) ===" | tee -a "$LOG"

# Wait for WP6 parallel extraction to finish
while pgrep -f "wp6_parallel.sh" > /dev/null; do
    echo "WP6 still running... $(date -Iseconds)" | tee -a "$LOG"
    sleep 60
done

echo "=== WP6 complete. Starting WP5 -> WP7 -> WP8 ===" | tee -a "$LOG"

cd "$COMPOSE_DIR"

# WP5: Citation closure
echo "=== WP5: Citation closure ===" | tee -a "$LOG"
sudo docker compose exec -T api python scripts/wp5_citations.py \
    --report "/app/reports/citation_closure.json" \
    2>&1 | tee -a "$LOG"

API_CONTAINER=$(sudo docker compose ps -q api)
sudo docker cp "$API_CONTAINER:/app/reports/citation_closure.json" "/srv/draftcheck/app/reports/citation_closure.json" 2>/dev/null || true

# WP7: Conflict sweep
echo "=== WP7: Conflict sweep ===" | tee -a "$LOG"
sudo docker compose exec -T api python scripts/wp7_conflict_sweep.py \
    --report "/app/reports/conflict_sweep.json" \
    2>&1 | tee -a "$LOG"

sudo docker cp "$API_CONTAINER:/app/reports/conflict_sweep.json" "/srv/draftcheck/app/reports/conflict_sweep.json" 2>/dev/null || true

# WP8: Adversarial round 1
echo "=== WP8: Adversarial round 1 ===" | tee -a "$LOG"
sudo docker compose exec -T api python scripts/adversarial_review.py \
    re-extract --round 1 \
    --report "/app/reports/adversarial_reextract_r1.json" \
    2>&1 | tee -a "$LOG"

sudo docker cp "$API_CONTAINER:/app/reports/adversarial_reextract_r1.json" "/srv/draftcheck/app/reports/adversarial_reextract_r1.json" 2>/dev/null || true

echo "=== Follow-up pipeline complete $(date -Iseconds) ===" | tee -a "$LOG"

# Final state
cd "$COMPOSE_DIR"
sudo docker compose exec -T db psql -U draftcheck -c "
SELECT lifecycle_status, COUNT(*) FROM rules GROUP BY lifecycle_status;
" | tee -a "$LOG"

sudo docker compose exec -T db psql -U draftcheck -c "
SELECT COUNT(*) FROM adversarial_findings;
" | tee -a "$LOG"
