"""Load config.yaml so every stage reads the same controls, models, paths and gates."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def data_path(cfg: dict, stage: str) -> Path:
    """Resolve a stage directory (raw, cache, corpus, processed, audit) relative to the repo root."""
    return ROOT / cfg["paths"][stage]
