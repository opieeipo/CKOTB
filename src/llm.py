"""Provider wrapper with a hashed disk cache.

Every generation, assessor, attacker and checker call is keyed by
sha256(provider, model, messages, params) and stored as one JSON file under
data/cache/. Re-running an experiment never re-queries a call it has made.
"""

import hashlib
import json
import os
import threading
from pathlib import Path

import requests

from src.config import data_path, load_config

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
_lock = threading.Lock()
_stats = {"hits": 0, "misses": 0}


def cache_key(provider: str, model: str, messages: list[dict], params: dict) -> str:
    blob = json.dumps({"provider": provider, "model": model, "messages": messages, "params": params},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def _cache_file(key: str, root: Path | None = None) -> Path:
    root = root or data_path(load_config(), "cache")
    return root / key[:2] / f"{key}.json"


def _ollama(model: str, messages: list[dict], params: dict) -> str:
    options = {k: v for k, v in params.items() if k != "format"}
    body = {"model": model, "messages": messages, "stream": False, "options": options, "think": False}
    if "format" in params:
        body["format"] = params["format"]
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=600)
    r.raise_for_status()
    return r.json()["message"]["content"]


PROVIDERS = {"ollama": _ollama}


def chat(spec: dict, messages: list[dict], cache_root: Path | None = None, **params) -> str:
    """spec: a config `models` entry ({provider, model}). params: temperature, seed, num_predict, format."""
    params.setdefault("temperature", 0.0)
    params.setdefault("seed", 0)
    key = cache_key(spec["provider"], spec["model"], messages, params)
    path = _cache_file(key, cache_root)
    if path.exists():
        with _lock:
            _stats["hits"] += 1
        return json.loads(path.read_text())["response"]
    response = PROVIDERS[spec["provider"]](spec["model"], messages, params)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_text(json.dumps({"provider": spec["provider"], "model": spec["model"], "params": params,
                               "messages": messages, "response": response}, ensure_ascii=False))
    tmp.rename(path)
    with _lock:
        _stats["misses"] += 1
    return response


def prompt_hash(messages: list[dict]) -> str:
    return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()[:12]


def stats() -> dict:
    return dict(_stats)
