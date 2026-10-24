"""Controls, parameters and the deficiency catalog.

Joins the NIST OSCAL catalog (statement + 800-53A assessment objectives), the FedRAMP
Moderate baseline workbook (parameter values + FedRAMP requirements) and
src/deficiencies.yaml into one Control record per control in config.yaml.
"""

import json
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import openpyxl
import yaml

from src.config import data_path, load_config

DEFICIENCIES = Path(__file__).with_name("deficiencies.yaml")
INSERT = re.compile(r"\{\{\s*insert:\s*param,\s*([\w.\-]+)\s*\}\}")


@dataclass
class Control:
    id: str                      # README form, e.g. IA-2(1)
    title: str
    statement: str               # NIST control text, parameters shown as [Assignment: ...]
    objectives: str              # 800-53A assessment objectives
    fedramp: str                 # FedRAMP Moderate parameter values and requirements
    params: dict
    require: list[str]
    deficiencies: list[dict] = field(default_factory=list)

    def deficiency(self, did: str) -> dict:
        return next(d for d in self.deficiencies if d["id"] == did)


def oscal_id(cid: str) -> str:
    """AC-2 -> ac-2, IA-2(1) -> ia-2.1"""
    m = re.fullmatch(r"([A-Z]{2})-(\d+)(?:\((\d+)\))?", cid)
    return f"{m[1].lower()}-{m[2]}" + (f".{m[3]}" if m[3] else "")


def _walk(controls):
    for c in controls:
        yield c
        yield from _walk(c.get("controls", []))


def _param_text(p: dict) -> str:
    if "select" in p:
        how = p["select"].get("how-many", "one")
        return f"[Selection ({how.replace('-', ' ')}): {'; '.join(p['select'].get('choice', []))}]"
    return f"[Assignment: {p.get('label', p['id'])}]"


def _render(part: dict, params: dict, depth: int = 0) -> list[str]:
    label = next((pr["value"] for pr in part.get("props", []) if pr["name"] == "label"), "")
    prose = _resolve(part.get("prose", ""), params)
    lines = [("  " * depth + f"{label} {prose}").rstrip()] if (label or prose) else []
    for sub in part.get("parts", []):
        lines += _render(sub, params, depth + (1 if (label or prose) else 0))
    return lines


def _resolve(text: str, params: dict) -> str:
    """Parameter text can itself contain inserts (selection choices), so resolve to a fixed point."""
    for _ in range(5):
        new = INSERT.sub(lambda m: params.get(m[1], m[1]), text)
        if new == text:
            break
        text = new
    return text


@cache
def _oscal(raw: Path) -> dict:
    cat = json.loads((raw / "NIST_SP-800-53_rev5_catalog.json").read_text())["catalog"]
    return {c["id"]: c for g in cat["groups"] for c in _walk(g["controls"])}


@cache
def _fedramp(raw: Path) -> dict:
    ws = openpyxl.load_workbook(raw / "FedRAMP_Security_Controls_Baseline.xlsx", read_only=True)["Moderate Baseline"]
    out = {}
    for r in ws.iter_rows(min_row=3, values_only=True):
        if r[2]:
            out[r[2].replace(" ", "")] = "\n".join(s.strip() for s in (r[6], r[7]) if s and str(s).strip())
    return out


def load_controls(cfg: dict | None = None) -> dict[str, Control]:
    cfg = cfg or load_config()
    raw = data_path(cfg, "raw")
    oscal, fedramp = _oscal(raw), _fedramp(raw)
    defs = yaml.safe_load(DEFICIENCIES.read_text())
    out = {}
    for cid in cfg["controls"]:
        c = oscal[oscal_id(cid)]
        params = {p["id"]: _param_text(p) for p in c.get("params", [])}
        parts = {p["name"]: p for p in c["parts"]}
        d = defs[cid]
        out[cid] = Control(
            id=cid,
            title=c["title"],
            statement="\n".join(_render(parts["statement"], params)),
            objectives="\n".join(_render(parts["assessment-objective"], params)),
            fedramp=fedramp.get(cid, ""),
            params={k: v["value"] for k, v in d["params"].items()},
            require=d["require"],
            deficiencies=d["deficiencies"],
        )
    return out


if __name__ == "__main__":
    for c in load_controls().values():
        print(f"{c.id:8} {c.title[:40]:40} {len(c.deficiencies)} deficiencies, {len(c.require)} requirements")
    c = load_controls()["AC-7"]
    print("\n" + c.statement + "\n---\n" + c.objectives + "\n---\n" + c.fedramp)
