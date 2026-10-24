"""Metrics, splits and transfer (Q2-Q4). Reads predictions from data/processed/, writes q<n>_metrics.json."""

import argparse
import json

import pandas as pd
from sklearn.metrics import f1_score

from src.config import data_path, load_config


def macro_f1(df: pd.DataFrame) -> float:
    return float(f1_score(df["label"], df["pred"], average="macro", labels=["compliant", "deficient"],
                          zero_division=0))


def q2(cfg: dict) -> dict:
    proc = data_path(cfg, "processed")
    ft = pd.concat([pd.read_parquet(p) for p in sorted(proc.glob("q2_finetuned_*.parquet"))], ignore_index=True)
    out = {"finetuned": {}, "per_control": {}}
    for split, g in ft.groupby("split"):
        out["finetuned"][split] = {"macro_f1": macro_f1(g), "n": len(g),
                                   "by_generator": {k: macro_f1(v) for k, v in g.groupby("generator")}}
        out["per_control"][split] = {k: macro_f1(v) for k, v in g.groupby("control")}
    hog = [v["macro_f1"] for k, v in out["finetuned"].items() if k.startswith("held_out_generator")]
    out["f1_held_out_generator"] = min(hog) if hog else float("nan")

    pp = proc / "q2_prompted_random.parquet"
    if pp.exists():
        p = pd.read_parquet(pp)
        out["prompted"] = {"macro_f1": macro_f1(p), "n": len(p),
                           "by_generator": {k: macro_f1(v) for k, v in p.groupby("generator")},
                           "by_control": {k: macro_f1(v) for k, v in p.groupby("control")},
                           "false_compliant_rate": float(((p.label == "deficient") & (p.pred == "compliant")).sum()
                                                         / max((p.label == "deficient").sum(), 1))}
        out["f1_prompted"] = out["prompted"]["macro_f1"]
    else:
        out["f1_prompted"] = float("nan")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--q2", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    proc = data_path(cfg, "processed")
    if args.q2:
        m = q2(cfg)
        (proc / "q2_metrics.json").write_text(json.dumps(m, indent=2))
        print(json.dumps({k: v for k, v in m.items() if k != "per_control"}, indent=2))


if __name__ == "__main__":
    main()
