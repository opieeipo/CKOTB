# CKOTB

- The README is the pre-registered research plan. Gates in the README and `config.yaml` are fixed; do not change them after results come in.
- The "Project Progress" bars are generated from the TODO checklist. Tick a task, then run `python scripts/update_progress.py` in the same change.
- Owner-audit tasks (Q1b rewrites, the 100-statement audit, the 50 adversarial audit) are the owner's; never fill those sheets in.
- Every model call goes through `src/llm.py` (hashed disk cache). Raw and cache data stay local and gitignored.
- Run tests with `.venv/bin/python -m pytest -q tests`.
