#!/usr/bin/env bash
# End-to-end spike. Usage: scripts/run_spike.sh [sample|full]   (default: two-control wiring sample)
# The sample run proves the wiring only; gate numbers come from `full`.
# Owner steps (Q1b rewrites, Q1 label audit, Q3 adversarial audit) pause the pipeline at their gates.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="python"
[ -x .venv/bin/python ] && PY=".venv/bin/python"
MODE="${1:-sample}"

$PY -m src.pull
if [ "$MODE" != "full" ]; then
  $PY -m src.generate --controls AC-7,AU-11 --limit 200
  $PY -m src.checker --corpus data/corpus/corpus_sample.parquet
  exit 0
fi

$PY -m src.checker --selftest audit/q1b_rewrites.yaml     # Q1b: stops here until the owner writes rewrites
$PY -m src.generate
$PY -m src.checker --corpus data/corpus/corpus_v1.parquet
$PY -m src.generate --audit-sheet
$PY -m src.gates q1                                       # needs the owner's audit/q1_label_audit.csv

$PY -m src.assessors --train --prompted && $PY -m src.evaluate --q2
$PY -m src.gates q2

$PY -m src.attacks --all && $PY -m src.evaluate --q3 --q4
$PY -m src.gates q3
