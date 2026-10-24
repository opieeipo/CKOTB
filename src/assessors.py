"""Fine-tuned and prompted compliance assessors (Q2).

Both read one implementation statement for one control and return compliant /
not compliant with a score in [0, 1] (probability of compliant).

  finetuned  DeBERTa-v3 classifier, trained per split (white-box target in Q3)
  prompted   LLM given the control text, 800-53A objectives and parameter values (black-box target)
"""

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from src import llm
from src.catalog import Control, load_controls
from src.config import data_path, load_config

# ---------------------------------------------------------------- splits

HELD_OUT_CONTROLS_N = 3


def splits(df: pd.DataFrame, cfg: dict) -> dict[str, tuple[pd.Index, pd.Index]]:
    """{name: (train_idx, test_idx)}. Defined on corpus fields only, so every split is exact.
    The same (control, item) draw written by both generators always lands on one side, so a
    model never sees the facts of a test statement through its other generator's version."""
    rng = random.Random(cfg["seed"])
    draw_key = df["control"] + ":" + df["item"].astype(str)
    keys = sorted(draw_key.unique())
    rng.shuffle(keys)
    test_keys = set(keys[: int(0.2 * len(keys))])
    is_test = draw_key.isin(test_keys)
    out = {"random": (df.index[~is_test], df.index[is_test])}

    held = sorted(rng.sample(sorted(df["control"].unique()), HELD_OUT_CONTROLS_N))
    in_held = df["control"].isin(held)
    out["held_out_controls"] = (df.index[~in_held], df.index[in_held])

    gens = sorted(df["generator"].unique())
    for a, b in [(gens[0], gens[1]), (gens[1], gens[0])]:
        out[f"held_out_generator:{a}->{b}"] = (df.index[df["generator"] == a], df.index[df["generator"] == b])
    return out


# ---------------------------------------------------------------- prompted

PROMPTED_SYSTEM = (
    "You are a FedRAMP 3PAO assessor reviewing System Security Plan control implementation statements. "
    "You decide whether the implementation as described satisfies the control and its assessment "
    "objectives at the stated organization-defined parameter values. A statement that describes any "
    "behaviour that fails an objective or parameter is not compliant."
)
PROMPTED_SCHEMA = {"type": "object",
                   "properties": {"rationale": {"type": "string"},
                                  "decision": {"type": "string", "enum": ["compliant", "not_compliant"]},
                                  "confidence": {"type": "integer", "minimum": 0, "maximum": 100}},
                   "required": ["rationale", "decision", "confidence"]}


def prompted_messages(ctrl: Control, text: str) -> list[dict]:
    params = "\n".join(f"- {k}: {v}" for k, v in ctrl.params.items())
    user = f"""Control {ctrl.id} {ctrl.title}

Control text:
{ctrl.statement}

NIST SP 800-53A assessment objectives:
{ctrl.objectives}

FedRAMP Moderate requirements:
{ctrl.fedramp or '(none beyond the control text)'}

Organization-defined parameter values for this system:
{params}

Implementation statement under review:
<<<
{text}
>>>

Assess the statement. Return JSON with a one-to-three sentence "rationale", "decision"
("compliant" or "not_compliant") and "confidence" (0-100) in that decision."""
    return [{"role": "system", "content": PROMPTED_SYSTEM}, {"role": "user", "content": user}]


def prompted_assess(ctrl: Control, text: str, cfg: dict) -> dict:
    spec = cfg["models"][cfg["assessors"]["prompted"]]
    raw = llm.chat(spec, prompted_messages(ctrl, text), temperature=0.0, seed=0, num_predict=400,
                   format=PROMPTED_SCHEMA)
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        out = {}
    compliant = out.get("decision") == "compliant"
    conf = min(max(int(out.get("confidence", 50) or 50), 0), 100) / 100
    return {"pred": "compliant" if compliant else "deficient",
            "score": conf if compliant else 1 - conf, "rationale": out.get("rationale", ""), "raw": raw}


def run_prompted(df: pd.DataFrame, cfg: dict, workers: int = 2) -> pd.DataFrame:
    controls = load_controls(cfg)
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda r: prompted_assess(controls[r.control], r.text, cfg), df.itertuples()))
    return df[["sid", "control", "generator", "label"]].assign(
        pred=[r["pred"] for r in res], score=[r["score"] for r in res], rationale=[r["rationale"] for r in res])


# ---------------------------------------------------------------- fine-tuned

MAX_LEN = 512


def model_input(control: str, title: str, text: str) -> str:
    return f"{control} {title}: {text}"


def _device():
    import torch
    return "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"


class FineTuned:
    """Thin wrapper so attacks.py can query scores and TextAttack can wrap the HF model."""

    def __init__(self, path: Path | str):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForSequenceClassification.from_pretrained(path).to(_device()).eval()
        self.torch = torch

    def scores(self, texts: list[str], batch: int = 16) -> np.ndarray:
        """P(compliant) for each already-formatted model_input string."""
        out = []
        with self.torch.no_grad():
            for i in range(0, len(texts), batch):
                enc = self.tok(texts[i:i + batch], truncation=True, max_length=MAX_LEN, padding=True,
                               return_tensors="pt").to(self.model.device)
                out.append(self.torch.softmax(self.model(**enc).logits.float(), -1)[:, 1].cpu().numpy())
        return np.concatenate(out) if out else np.array([])


def train_finetuned(train: pd.DataFrame, out_dir: Path, cfg: dict, epochs: int = 3, lr: float = 2e-5,
                    batch: int = 8) -> Path:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    torch.manual_seed(cfg["seed"])
    name = cfg["assessors"]["finetuned"]
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForSequenceClassification.from_pretrained(name, num_labels=2).to(_device())
    controls = load_controls(cfg)
    x = [model_input(r.control, controls[r.control].title, r.text) for r in train.itertuples()]
    y = (train["label"] == "compliant").astype(int).to_numpy()
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * -(-len(x) // batch)
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    model.train()
    for ep in range(epochs):
        order = np.random.default_rng(cfg["seed"] + ep).permutation(len(x))
        total = 0.0
        for i in range(0, len(x), batch):
            idx = order[i:i + batch]
            enc = tok([x[j] for j in idx], truncation=True, max_length=MAX_LEN, padding=True,
                      return_tensors="pt").to(model.device)
            loss = model(**enc, labels=torch.tensor(y[idx], device=model.device)).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            total += loss.item() * len(idx)
        print(f"    epoch {ep + 1}/{epochs} loss {total / len(x):.4f}", flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    return out_dir


def predict_finetuned(model_dir: Path, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    controls = load_controls(cfg)
    m = FineTuned(model_dir)
    s = m.scores([model_input(r.control, controls[r.control].title, r.text) for r in df.itertuples()])
    return df[["sid", "control", "generator", "label"]].assign(
        pred=np.where(s >= 0.5, "compliant", "deficient"), score=s)


def model_dir(cfg: dict, split: str) -> Path:
    return data_path(cfg, "processed") / "models" / f"deberta_{split.replace(':', '_').replace('->', '_to_')}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", action="store_true", help="fine-tune one DeBERTa per split and save test predictions")
    ap.add_argument("--prompted", action="store_true", help="run the prompted assessor on the random-split test set")
    ap.add_argument("--splits", help="comma-separated subset of split names")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--corpus", default="corpus_v1.parquet")
    args = ap.parse_args()
    cfg = load_config()
    df = pd.read_parquet(data_path(cfg, "corpus") / args.corpus)
    proc = data_path(cfg, "processed")
    sp = splits(df, cfg)
    names = args.splits.split(",") if args.splits else list(sp)
    if args.train:
        for name in names:
            tr, te = sp[name]
            print(f"[{name}] train {len(tr)} test {len(te)}", flush=True)
            d = train_finetuned(df.loc[tr], model_dir(cfg, name), cfg, epochs=args.epochs)
            predict_finetuned(d, df.loc[te], cfg).assign(split=name).to_parquet(
                proc / f"q2_finetuned_{d.name}.parquet", index=False)
    if args.prompted:
        te = sp["random"][1]
        run_prompted(df.loc[te], cfg).assign(split="random").to_parquet(proc / "q2_prompted_random.parquet", index=False)
        print(f"prompted assessor: {len(te)} statements, cache {llm.stats()}")


if __name__ == "__main__":
    main()
