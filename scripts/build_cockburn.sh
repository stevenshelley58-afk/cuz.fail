#!/usr/bin/env bash
# One-command Cockburn corpus closure driver.
#
# Runs the full DB build-out to completion for the City of Cockburn pilot scope
# (including statutory instruments: P&D Act, Regulations + deemed provisions,
# Local Planning Scheme + maps, LPPs, SPPs, DC policies, region schemes, NCC).
#
# Designed to run INSIDE the api container, where DATABASE_URL + LLM env are set
# and the working tree is at /app:
#
#   docker exec draftcheck-wa-v3-api-1 bash /app/scripts/build_cockburn.sh
#
# It is idempotent and resumable: every stage skips already-terminal work
# (acquired/blocked rows, reached fixpoints, closed adversarial rounds), so a
# re-run after an interruption picks up where it left off. It never approves a
# rule or mutates a rule value on its own — the operator-gated lifecycle and the
# deterministic validators in the underlying scripts remain the only writers of
# approved state.
#
# Authority: docs/CORPUS_COMPLETENESS_PLAN.md (Phases 2-6) and CLAUDE.md operator
# standing approval. Exit non-zero only if the final --strict gate is still red.
set -uo pipefail

APP="${APP_DIR:-/app}"
PY="${PYTHON:-python}"
REPORTS="${REPORTS_DIR:-$APP/reports}"
SCRIPTS="$APP/scripts"
MAX_ACQUIRE_PASSES="${MAX_ACQUIRE_PASSES:-6}"   # acquire<->citation fixpoint cap
MAX_ADV_ROUNDS="${MAX_ADV_ROUNDS:-8}"           # adversarial round cap

cd "$APP" || { echo "FATAL: cannot cd to $APP"; exit 2; }
mkdir -p "$REPORTS"

say() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
run() { echo "+ $*"; "$@"; }

# json_get <file> <python-expr-on-`d`>  -> prints value or empty on error
json_get() {
  "$PY" - "$1" "$2" <<'PYEOF' 2>/dev/null
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(eval(sys.argv[2]))
except Exception:
    print("")
PYEOF
}

# ---------------------------------------------------------------------------
# Phase 2+3: acquisition <-> citation closure, looped to a joint fixpoint.
# WP5 can surface new `pending` manifest rows (unresolved citations), which WP4
# must then acquire; iterate until a citation pass adds zero new rows.
# ---------------------------------------------------------------------------
say "Phase 2/3: acquisition + citation closure (fixpoint loop)"
for pass in $(seq 1 "$MAX_ACQUIRE_PASSES"); do
  echo ">> fixpoint pass $pass / $MAX_ACQUIRE_PASSES"
  run "$PY" "$SCRIPTS/wp4_acquire.py" --report "$REPORTS/acquisition_report.json"
  run "$PY" "$SCRIPTS/wp5_citation_closure.py" --report "$REPORTS/citation_closure.json"

  fixpoint="$(json_get "$REPORTS/citation_closure.json" "d.get('fixpoint_reached')")"
  new_rows="$(json_get "$REPORTS/citation_closure.json" "sum(r.get('new_manifest_rows',0) for r in d.get('rounds',[])) if isinstance(d.get('rounds'),list) else d.get('new_manifest_rows',0)")"
  echo "   citation fixpoint=$fixpoint new_manifest_rows=$new_rows"
  if [ "$fixpoint" = "True" ] && { [ "$new_rows" = "0" ] || [ -z "$new_rows" ]; }; then
    echo "   acquire/citation joint fixpoint reached on pass $pass"
    break
  fi
done

# ---------------------------------------------------------------------------
# Phase 4: rule atoms proofs (matrix + per-doc acceptance gates).
# ---------------------------------------------------------------------------
say "Phase 4: rule matrix + per-document acceptance gates"
run "$PY" "$SCRIPTS/wp6_rule_matrix.py" \
  --matrix "$REPORTS/rule_matrix.csv" --gaps "$REPORTS/rule_matrix_gaps.json"
run "$PY" "$SCRIPTS/wp6_per_doc_gates.py" --report "$REPORTS/per_doc_gates.json"

gap_count="$(json_get "$REPORTS/rule_matrix_gaps.json" "len(d.get('gaps',d if isinstance(d,list) else []))")"
echo "   rule_matrix MISSING cells: ${gap_count:-unknown} (drain queue = pending-review candidates)"

# ---------------------------------------------------------------------------
# Phase 4b: legal graph (exceptions + cross-instrument edges) + conflict sweep.
# ---------------------------------------------------------------------------
say "Phase 4b: legal graph + conflict sweep"
run "$PY" "$SCRIPTS/wp4b_legal_graph.py" exceptions --report "$REPORTS/legal_graph.json"
run "$PY" "$SCRIPTS/wp4b_legal_graph.py" edges --report "$REPORTS/legal_graph.json"
run "$PY" "$SCRIPTS/conflict_sweep.py" --report "$REPORTS/conflict_sweep.json"

# ---------------------------------------------------------------------------
# Phase 5: adversarial rounds until closure (2 consecutive clean rounds).
# ---------------------------------------------------------------------------
say "Phase 5: adversarial review (rounds until closure)"
for r in $(seq 1 "$MAX_ADV_ROUNDS"); do
  echo ">> adversarial round $r / $MAX_ADV_ROUNDS"
  run "$PY" "$SCRIPTS/adversarial_review.py" re-extract         --round "$r" --report "$REPORTS/adversarial_reextract_r$r.json"
  run "$PY" "$SCRIPTS/adversarial_review.py" prosecute          --round "$r" --report "$REPORTS/adversarial_prosecute_r$r.json"
  run "$PY" "$SCRIPTS/adversarial_review.py" gap-hunt           --round "$r" --report "$REPORTS/adversarial_gaphunt_r$r.json"
  run "$PY" "$SCRIPTS/adversarial_review.py" conflict-prosecute --round "$r" --report "$REPORTS/adversarial_conflict_r$r.json"
  run "$PY" "$SCRIPTS/adversarial_review.py" defend             --round "$r" --report "$REPORTS/adversarial_defend_r$r.json"
  run "$PY" "$SCRIPTS/adversarial_review.py" judge              --round "$r" --report "$REPORTS/adversarial_judge_r$r.json"
  run "$PY" "$SCRIPTS/adversarial_review.py" closure            --report "$REPORTS/adversarial_closure.json"

  closed="$(json_get "$REPORTS/adversarial_closure.json" "d.get('closed', d.get('closure_reached'))")"
  echo "   adversarial closed=$closed"
  if [ "$closed" = "True" ]; then
    echo "   adversarial closure reached after round $r"
    break
  fi
done

# ---------------------------------------------------------------------------
# Final: strict closure gate over the regenerated reports/.
# ---------------------------------------------------------------------------
say "Final: corpus closure gates (strict)"
"$PY" "$SCRIPTS/corpus_gates.py" --strict --json "$REPORTS/corpus_gates.json"
rc=$?

say "Done"
echo "Reports written under $REPORTS/. Commit them and flip the CI corpus-gates job to --strict."
echo "Strict gate exit code: $rc  (0 = Cockburn corpus closed for declared scope)"
exit $rc
