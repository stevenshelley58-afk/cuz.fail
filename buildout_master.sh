#!/bin/bash
# Master DB build-out orchestration script
# Runs sequentially: WP6 -> WP5 -> WP7 -> WP8

set -euo pipefail

LOG="/srv/draftcheck/app/reports/buildout_master.log"
APP_DIR="/srv/draftcheck/app"
COMPOSE_DIR="/srv/draftcheck/app/infra/v3"
REPORTS="/srv/draftcheck/app/reports"
APP_REPORTS="/app/reports"

echo "=== DB Build-Out Master Run $(date -Iseconds) ===" | tee -a "$LOG"

# Function to copy report from container to host
copy_report() {
    local container_report="$1"
    local host_report="$2"
    API_CONTAINER=$(cd "$COMPOSE_DIR" && sudo docker compose ps -q api)
    sudo docker cp "$API_CONTAINER:$container_report" "$host_report" 2>/dev/null || true
}

# WP6: Extraction on uncovered clauses
echo "=== WP6: Starting extraction on uncovered rule-bearing clauses ===" | tee -a "$LOG"
cd "$COMPOSE_DIR"
sudo docker compose exec -T api python scripts/wp6_extract.py \
    --workers 4 \
    --report "$APP_REPORTS/wp6_extraction.json" \
    2>&1 | tee -a "$LOG"

copy_report "$APP_REPORTS/wp6_extraction.json" "$REPORTS/wp6_extraction.json"

# Check how many rule-bearing clauses now have rules
cd "$COMPOSE_DIR"
sudo docker compose exec -T db psql -U draftcheck -c "
SELECT COUNT(*) FROM clauses c 
WHERE disposition = 'rule_bearing' 
AND NOT EXISTS (SELECT 1 FROM rules r WHERE r.clause_id = c.id);
" | tee -a "$LOG"

# WP5: Citation closure on newly acquired versions
echo "=== WP5: Re-running citation closure ===" | tee -a "$LOG"
cd "$COMPOSE_DIR"
sudo docker compose exec -T api python scripts/wp5_citations.py \
    --report "$APP_REPORTS/citation_closure.json" \
    2>&1 | tee -a "$LOG"

copy_report "$APP_REPORTS/citation_closure.json" "$REPORTS/citation_closure.json"

# WP7: Conflict sweep
echo "=== WP7: Re-running conflict sweep ===" | tee -a "$LOG"
cd "$COMPOSE_DIR"
sudo docker compose exec -T api python scripts/wp7_conflict_sweep.py \
    --report "$APP_REPORTS/conflict_sweep.json" \
    2>&1 | tee -a "$LOG"

copy_report "$APP_REPORTS/conflict_sweep.json" "$REPORTS/conflict_sweep.json"

# WP8: Adversarial round 1
echo "=== WP8: Launching adversarial round 1 ===" | tee -a "$LOG"
cd "$COMPOSE_DIR"
sudo docker compose exec -T api python scripts/adversarial_review.py \
    re-extract --round 1 \
    --report "$APP_REPORTS/adversarial_reextract_r1.json" \
    2>&1 | tee -a "$LOG"

copy_report "$APP_REPORTS/adversarial_reextract_r1.json" "$REPORTS/adversarial_reextract_r1.json"

echo "=== Build-out complete $(date -Iseconds) ===" | tee -a "$LOG"

# Final state checks
cd "$COMPOSE_DIR"
sudo docker compose exec -T db psql -U draftcheck -c "
SELECT status, COUNT(*) FROM target_manifest GROUP BY status ORDER BY status;
" | tee -a "$LOG"

cd "$COMPOSE_DIR"
sudo docker compose exec -T db psql -U draftcheck -c "
SELECT lifecycle_status, COUNT(*) FROM rules GROUP BY lifecycle_status ORDER BY lifecycle_status;
" | tee -a "$LOG"

cd "$COMPOSE_DIR"
sudo docker compose exec -T db psql -U draftcheck -c "
SELECT COUNT(*) FROM adversarial_findings;
" | tee -a "$LOG"
