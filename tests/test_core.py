import json

from src import llm
from src.catalog import load_controls, oscal_id
from src.checker import parse
from src.config import load_config
from src.gates import q1_ground_truth, q3_attacks
from src.generate import draw


def test_oscal_id():
    assert oscal_id("AC-2") == "ac-2"
    assert oscal_id("IA-2(1)") == "ia-2.1"


def test_catalog_complete():
    controls = load_controls()
    assert list(controls) == load_config()["controls"]
    for c in controls.values():
        assert c.statement and c.objectives and "{{" not in c.statement
        assert 3 <= len(c.deficiencies) <= 5
        for d in c.deficiencies:
            assert 0 <= d["breaks"] < len(c.require)
            assert d["check"].startswith("Does the text state")


def test_draw_balanced_and_deterministic():
    c = load_controls()["AC-7"]
    rows = [draw(c, i, 0) for i in range(16)]
    assert sum(r["label"] == "deficient" for r in rows) == 8
    assert {r["deficiency"] for r in rows if r["deficiency"]} == {d["id"] for d in c.deficiencies}
    assert draw(c, 5, 0) == rows[5]
    d = rows[1]
    broken = c.deficiency(d["deficiency"])
    assert d["facts"][broken["breaks"]] == broken["inject"]


def test_cache_roundtrip(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setitem(llm.PROVIDERS, "fake", lambda m, msgs, p: calls.append(1) or "hello")
    spec = {"provider": "fake", "model": "m"}
    msgs = [{"role": "user", "content": "hi"}]
    assert llm.chat(spec, msgs, cache_root=tmp_path) == "hello"
    assert llm.chat(spec, msgs, cache_root=tmp_path) == "hello"
    assert len(calls) == 1
    assert llm.chat(spec, msgs, cache_root=tmp_path, temperature=0.5) == "hello"
    assert len(calls) == 2


def test_checker_parse():
    assert parse(json.dumps({"answer": "Yes", "evidence": "x"}))["answer"] == "yes"
    assert parse('noise {"answer": "not stated", "evidence": ""} tail')["answer"] == "not_stated"
    assert parse("garbage")["answer"] == "not_stated"


def test_gates():
    cfg = load_config()
    assert not q1_ground_truth(2500, None, 6, cfg)["pass"]
    assert q1_ground_truth(2500, 0.95, 5, cfg)["pass"]
    r = q3_attacks(0.95, {"prompted": 0.40}, {"prompted": 0.30}, cfg)
    assert not r["pass"]  # only 10 points over paraphrase
    assert q3_attacks(0.95, {"prompted": 0.40}, {"prompted": 0.20}, cfg)["pass"]
