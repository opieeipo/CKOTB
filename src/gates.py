"""Pre-registered go/no-go gates (config.yaml `gates`), evaluated mechanically.

Usage: python -m src.gates q1|q2|q3. Each check reads its inputs from data/processed/
and audit/, prints the comparison against the gate and writes data/processed/gate_<q>.json.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from src.config import data_path, load_config


def q1_ground_truth(n_statements: int, audit_agreement: float | None, selftest_caught: int | None, cfg: dict) -> dict:
    g = cfg["gates"]["q1"]
    checks = {
        "min_statements": n_statements >= g["min_statements"],
        "min_audit_agreement": audit_agreement is not None and audit_agreement >= g["min_audit_agreement"],
        "checker_selftest": selftest_caught is not None and selftest_caught >= g["checker_selftest_min"],
    }
    return {"statements": n_statements, "audit_agreement": audit_agreement,
            "selftest_caught": selftest_caught, "checks": checks, "pass": all(checks.values())}


def q2_assessor(f1_held_out_generator: float, f1_prompted: float, cfg: dict) -> dict:
    g = cfg["gates"]["q2"]
    checks = {"finetuned_held_out_generator": f1_held_out_generator >= g["min_f1_held_out_generator"],
              "prompted": f1_prompted >= g["min_f1_prompted"]}
    return {"f1_held_out_generator": f1_held_out_generator, "f1_prompted": f1_prompted,
            "checks": checks, "pass": all(checks.values())}


def q3_attacks(checker_agreement: float | None, asr: dict, asr_paraphrase: dict, cfg: dict) -> dict:
    """asr / asr_paraphrase: attack success rate per target (finetuned, prompted)."""
    g = cfg["gates"]["q3"]
    per_target = {t: {"asr": a, "paraphrase": asr_paraphrase.get(t, 0.0),
                      "pass": a >= g["min_attack_success"] and a - asr_paraphrase.get(t, 0.0) >= g["min_gain_over_paraphrase"]}
                  for t, a in asr.items()}
    valid = checker_agreement is not None and checker_agreement >= g["min_checker_agreement"]
    return {"checker_agreement": checker_agreement, "checker_valid": valid, "targets": per_target,
            "pass": valid and any(t["pass"] for t in per_target.values())}


def _load_q1(cfg: dict) -> dict:
    corpus = data_path(cfg, "corpus") / "corpus_v1.parquet"
    n = len(pd.read_parquet(corpus, columns=["sid"])) if corpus.exists() else 0
    audit = data_path(cfg, "audit")
    agreement = None
    sheet = audit / "q1_label_audit.csv"
    if sheet.exists():
        a = pd.read_csv(sheet)
        a = a[a["owner_label"].notna()].merge(pd.read_parquet(corpus, columns=["sid", "label"]), on="sid")
        if len(a) >= cfg["gates"]["q1"]["audit_n"]:
            agreement = float((a["owner_label"].str.strip().str.lower() == a["label"]).mean())
    selftest = audit / "q1b_rewrites.result.json"
    caught = json.loads(selftest.read_text())["caught"] if selftest.exists() else None
    return q1_ground_truth(n, agreement, caught, cfg)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("gate", choices=["q1", "q2", "q3"])
    args = ap.parse_args()
    cfg = load_config()
    if args.gate == "q1":
        res = _load_q1(cfg)
    else:
        src = data_path(cfg, "processed") / f"{args.gate}_metrics.json"
        if not src.exists():
            sys.exit(f"{src} missing: run src.evaluate --{args.gate} first")
        m = json.loads(src.read_text())
        res = (q2_assessor(m["f1_held_out_generator"], m["f1_prompted"], cfg) if args.gate == "q2"
               else q3_attacks(m.get("checker_agreement"), m["asr"], m["asr_paraphrase"], cfg))
    out = data_path(cfg, "processed") / f"gate_{args.gate}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2, default=str))
    print(yaml.safe_dump(res, sort_keys=False))
    print("GATE", args.gate.upper(), "PASS" if res["pass"] else "FAIL / INCOMPLETE")


if __name__ == "__main__":
    main()
