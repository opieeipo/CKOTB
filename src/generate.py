"""Corpus generation (Q1).

Every (control, label, deficiency, style) draw is sent identically to each generator
family, so the held-out-generator split differs only in the model that wrote the text.
Deficient statements state every requirement but one; the broken one is replaced by the
injected fact, stated plainly as how the system works (never flagged as a gap).
"""

import argparse
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from src import llm
from src.catalog import Control, load_controls
from src.config import data_path, load_config

LENGTHS = {"short": "60-110 words", "medium": "130-220 words", "long": "250-380 words"}
FORMATS = {
    "appendix_a": "FedRAMP SSP Appendix A layout: one block per control part, each starting with "
                  "'Part a:', 'Part b:' etc., matching the control's lettered parts",
    "narrative": "one or two continuous prose paragraphs, no part labels",
    "role_led": "start with the responsible roles, then describe the solution as prose; may use a short bulleted list",
}
VOICES = {
    "csp": "third person, referring to the provider as 'the CSP' and the system by name",
    "system": "third person, with the system name as the subject ('<System> enforces ...')",
    "we": "first person plural ('We ...'), as some providers write",
}
ENVIRONMENTS = [
    "a SaaS application hosted in AWS GovCloud (US)",
    "a PaaS offering hosted in Azure Government",
    "a hybrid system with an on-premises data center and a commercial cloud tenant",
    "a SaaS application on Google Cloud Assured Workloads",
    "a containerized platform on Kubernetes in a FedRAMP-authorized IaaS",
]
ORIGINATIONS = ["service provider system specific", "service provider hybrid (corporate and system specific)",
                "partly inherited from the underlying FedRAMP-authorized IaaS"]
DETAIL = {
    "high": "name specific products, tools and configuration settings",
    "medium": "name some tools but stay at the process level",
    "low": "use generic policy and procedure language with few tool names",
}
SYSTEMS = ["Atlas Case Management", "Beacon Analytics", "Cedar Grants Portal", "Delta Records Cloud",
           "Ember HR Suite", "Falcon Field Ops", "Granite Payments Hub", "Harbor Document Exchange",
           "Iris Benefits Platform", "Juniper Learning Cloud", "Keystone Permits", "Lumen Telehealth"]

SYSTEM_PROMPT = (
    "You write control implementation statements for FedRAMP Moderate System Security Plans. "
    "You write exactly what you are told the implementation does, in the style requested. "
    "Output only the implementation statement text: no title, no preamble, no notes, no markdown headings."
)


def build_messages(ctrl: Control, facts: list[str], style: dict) -> list[dict]:
    fact_lines = "\n".join(f"- {f}" for f in facts)
    user = f"""Control {ctrl.id} {ctrl.title}

Control text:
{ctrl.statement}

FedRAMP Moderate parameters and requirements:
{ctrl.fedramp or '(none beyond the control text)'}

Write the "What is the solution and how is it implemented?" statement for {style['system']}, {style['environment']}.
Control origination: {style['origination']}.

The implementation does exactly the following. State every point explicitly and concretely,
as plain fact about how the system works today:
{fact_lines}

Rules:
- Do not add statements about the points above beyond what is listed, and do not contradict any of them.
- Do not label anything as a gap, deficiency, exception, risk, finding, POA&M item, or planned improvement.
- Length: {LENGTHS[style['length']]}.
- Format: {FORMATS[style['format']]}.
- Voice: {VOICES[style['voice']]}.
- Detail: {DETAIL[style['detail']]}."""
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def draw(ctrl: Control, i: int, seed: int) -> dict:
    """One corpus item: label, deficiency and style. Alternates compliant / deficient and cycles deficiencies."""
    rng = random.Random(f"{seed}:{ctrl.id}:{i}")
    deficient = i % 2 == 1
    d = ctrl.deficiencies[(i // 2) % len(ctrl.deficiencies)] if deficient else None
    facts = list(ctrl.require)
    if d:
        facts[d["breaks"]] = d["inject"]
    return {
        "control": ctrl.id, "item": i, "label": "deficient" if deficient else "compliant",
        "deficiency": d["id"] if d else None, "facts": facts,
        "length": rng.choice(list(LENGTHS)), "format": rng.choice(list(FORMATS)),
        "voice": rng.choice(list(VOICES)), "detail": rng.choice(list(DETAIL)),
        "environment": rng.choice(ENVIRONMENTS), "origination": rng.choice(ORIGINATIONS),
        "system": rng.choice(SYSTEMS),
    }


def generate_one(ctrl: Control, row: dict, gen_name: str, spec: dict) -> dict:
    msgs = build_messages(ctrl, row["facts"], row)
    text = llm.chat(spec, msgs, temperature=0.8, seed=row["item"], num_predict=900).strip()
    return {**row, "facts": "\n".join(row["facts"]), "generator": gen_name, "family": spec["family"],
            "model": spec["model"], "seed_template": row["format"], "prompt_hash": llm.prompt_hash(msgs),
            "text": text, "n_words": len(text.split())}


def audit_sheet(corpus: Path, out: Path, n: int, seed: int) -> None:
    """Q1 owner audit: n random statements, blind (the injected label is not on the sheet).
    The owner writes compliant / deficient in owner_label; gates.py joins on sid."""
    df = pd.read_parquet(corpus).sample(n, random_state=seed)
    controls = load_controls()
    sheet = pd.DataFrame({
        "sid": df["sid"], "control": df["control"],
        "requirements": [" | ".join(controls[c].require) for c in df["control"]],
        "text": df["text"], "owner_label": "", "owner_note": "",
    })
    sheet.to_csv(out, index=False)
    print(f"wrote {out}: {n} statements, blind. Fill owner_label with compliant or deficient.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit-sheet", action="store_true", help="write the blind Q1 audit sheet from corpus_v1")
    ap.add_argument("--controls", help="comma-separated subset, e.g. AC-7,AU-11")
    ap.add_argument("--limit", type=int, help="total statements (default: config min_statements, rounded up)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", help="output parquet (default: data/corpus/corpus_v1.parquet, or _sample when limited)")
    args = ap.parse_args()

    cfg = load_config()
    if args.audit_sheet:
        audit_sheet(data_path(cfg, "corpus") / "corpus_v1.parquet", data_path(cfg, "audit") / "q1_label_audit.csv",
                    cfg["gates"]["q1"]["audit_n"], cfg["seed"])
        return
    controls = load_controls(cfg)
    ids = args.controls.split(",") if args.controls else cfg["controls"]
    gens = {g: cfg["models"][g] for g in cfg["generators"]}
    total = args.limit or int(cfg["gates"]["q1"]["min_statements"] * 1.1)
    per = -(-total // (len(ids) * len(gens)))  # per (control, generator)
    rows = [draw(controls[c], i, cfg["seed"]) for c in ids for i in range(per)]
    jobs = [(controls[r["control"]], r, g, s) for g, s in gens.items() for r in rows]
    print(f"{len(jobs)} statements: {len(ids)} controls x {len(gens)} generators x {per}")

    done = []
    with ThreadPoolExecutor(args.workers) as ex:
        for k, out in enumerate(ex.map(lambda j: generate_one(*j), jobs), 1):
            done.append(out)
            if k % 50 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)}  cache {llm.stats()}", flush=True)

    df = pd.DataFrame(done)
    df.insert(0, "sid", [f"{r.control}-{r.generator}-{r.item:04d}" for r in df.itertuples()])
    name = args.out or ("corpus_v1.parquet" if not (args.limit or args.controls) else "corpus_sample.parquet")
    out = Path(name) if args.out else data_path(cfg, "corpus") / name
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"wrote {out} ({len(df)} rows)")
    print(df.groupby(["generator", "label"]).n_words.describe()[["count", "mean", "min", "max"]])


if __name__ == "__main__":
    main()
