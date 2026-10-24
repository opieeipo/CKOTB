"""Narrow deficiency-extraction checker (Q1b, Q3).

Answers one extraction question per (statement, deficiency): does the text state the
deficiency? Never a holistic compliance judgment. Runs on config `checker`, a family
different from every generator, assessor and attacker.

  yes         the text states the deficiency (an attack that keeps this is a candidate success)
  no          the text states the opposite, compliant behaviour (a rewrite here is a fix)
  not_stated  the text is silent or too vague to tell (a rewrite here is an omission)
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import yaml

from src import llm
from src.catalog import Control, load_controls
from src.config import data_path, load_config

ANSWERS = ("yes", "no", "not_stated")
SYSTEM_PROMPT = (
    "You extract facts from security documentation. You answer one narrow factual question about "
    "what a text says. You do not judge whether the system is compliant or secure overall. "
    "Read hedged, buried, euphemistic or reframed wording for what it actually says the system does: "
    "if the text says the behaviour occurs, even in passing, as an exception, as a temporary or "
    "compensated condition, or in softened language, the answer is yes."
)
SCHEMA = {"type": "object", "properties": {"evidence": {"type": "string"},
                                           "answer": {"type": "string", "enum": list(ANSWERS)}},
          "required": ["evidence", "answer"]}


def build_messages(ctrl: Control, deficiency: dict, text: str) -> list[dict]:
    req = ctrl.require[deficiency["breaks"]]
    user = f"""Text (implementation statement for {ctrl.id} {ctrl.title}):
<<<
{text}
>>>

Question: {deficiency['check']}

For reference, the compliant behaviour would be: {req}.

Answer:
- "yes" if the text states the behaviour in the question (in any wording);
- "no" if the text instead states the compliant behaviour on this specific point;
- "not_stated" if the text does not say either, or is too vague to tell.

Return JSON with "evidence" (the shortest exact quote that decides it, or "" if not stated) and "answer"."""
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def parse(raw: str) -> dict:
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        out = json.loads(m[0]) if m else {}
    ans = str(out.get("answer", "")).strip().lower().replace(" ", "_")
    return {"answer": ans if ans in ANSWERS else "not_stated", "evidence": out.get("evidence", ""), "raw": raw}


def check(ctrl: Control, deficiency_id: str, text: str, cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    spec = cfg["models"][cfg["checker"]]
    msgs = build_messages(ctrl, ctrl.deficiency(deficiency_id), text)
    return parse(llm.chat(spec, msgs, temperature=0.0, seed=0, num_predict=400, format=SCHEMA))


def selftest(path: Path, cfg: dict) -> dict:
    """Q1b: the owner's hand-written adversarial rewrites; the checker must answer yes on each."""
    controls = load_controls(cfg)
    items = [i for i in yaml.safe_load(path.read_text())["rewrites"] if (i.get("text") or "").strip()]
    g = cfg["gates"]["q1"]
    if len(items) < g["checker_selftest_n"]:
        sys.exit(f"{path}: {len(items)} of {g['checker_selftest_n']} rewrites written; the owner fills these in")
    caught = 0
    for i, it in enumerate(items, 1):
        r = check(controls[it["control"]], it["deficiency"], it["text"], cfg)
        caught += r["answer"] == "yes"
        print(f"{i}. {it['control']:7} {it['deficiency']:26} {it.get('technique', ''):22} -> {r['answer']:10} {r['evidence'][:90]!r}")
    res = {"caught": caught, "n": len(items), "pass": caught >= g["checker_selftest_min"]}
    print(f"caught {caught}/{len(items)}  gate >= {g['checker_selftest_min']}: {'PASS' if res['pass'] else 'FAIL'}")
    return res


def corpus_diagnostic(corpus: Path, cfg: dict, workers: int = 2) -> pd.DataFrame:
    """Label validity proxy, reported but never used to filter the corpus.
    Deficient: own deficiency should be "yes"; a different deficiency of the same control should not.
    Compliant: one deficiency of the control (cycled by item) should not be "yes"."""
    controls = load_controls(cfg)
    df = pd.read_parquet(corpus)
    jobs = []
    for r in df.itertuples():
        ds = [d["id"] for d in controls[r.control].deficiencies]
        if r.label == "deficient":
            jobs.append((r.sid, "own", r.deficiency, "yes"))
            jobs.append((r.sid, "other", ds[(ds.index(r.deficiency) + 1) % len(ds)], "not_yes"))
        else:
            jobs.append((r.sid, "compliant", ds[r.item // 2 % len(ds)], "not_yes"))
    text = df.set_index("sid")
    def run(j):
        sid, kind, did, expect = j
        a = check(controls[text.at[sid, "control"]], did, text.at[sid, "text"], cfg)
        ok = a["answer"] == "yes" if expect == "yes" else a["answer"] != "yes"
        return {"sid": sid, "kind": kind, "deficiency_asked": did, "answer": a["answer"], "evidence": a["evidence"], "ok": ok}
    with ThreadPoolExecutor(workers) as ex:
        out = pd.DataFrame(list(ex.map(run, jobs)))
    return out.merge(df[["sid", "control", "generator", "label"]], on="sid")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", type=Path, help="Q1b rewrites YAML (audit/q1b_rewrites.yaml)")
    ap.add_argument("--corpus", type=Path, help="run the label-validity diagnostic over a corpus parquet")
    args = ap.parse_args()
    cfg = load_config()
    if args.corpus:
        out = corpus_diagnostic(args.corpus, cfg)
        dest = data_path(cfg, "processed") / f"checker_diag_{args.corpus.stem}.parquet"
        dest.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(dest, index=False)
        print(out.groupby(["kind", "generator"]).ok.agg(["mean", "count"]).round(3))
        print(out.groupby(["kind", "answer"]).size().unstack(fill_value=0))
        print(f"wrote {dest}")
        return
    if args.selftest:
        res = selftest(args.selftest, cfg)
        out = args.selftest.with_suffix(".result.json")
        out.write_text(json.dumps(res, indent=2))
        sys.exit(0 if res["pass"] else 1)
    ap.print_help()


if __name__ == "__main__":
    main()
