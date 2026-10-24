# CKOTB (Cool Kids on the Block)

> **Status:** pre-registered 2026-10-24, not started. Gates are fixed below and in
> `config.yaml` before any corpus is generated or any model is scored. Numbers this
> spike produces are go/no-go signals, not paper results.

Feasibility spike for an ML paper: **can an optimized adversary get a deficient
NIST SP 800-53 control implementation approved by an ML-based compliance assessor,
while the deficiency is still plainly described in the text?**

Agencies and cloud vendors are starting to use LLMs to review System Security Plan
(SSP) implementation statements and to automate assessment for continuous ATO. If
those assessors can be steered by how a narrative is written rather than what it
says, automated RMF assessment has an adversarial weakness that nobody is measuring.

This is a **spike**. It answers go/no-go fast. The code is written to be reusable
toward the real submission, but nothing here is the final model or attack.

Predecessor: [CVE_RMF_Bridging](https://github.com/opieeipo/CVE_RMF_Bridging)
(closed no-go). Its lesson carries over: test the cheapest thing that could kill the
idea first, and design splits so a model can't pass by memorizing an artifact.

---

## Research question and threat model

**Target.** A compliance assessor that reads one implementation statement for one
control and returns *compliant* or *not compliant* (with a score where available).
Two kinds are tested:
- a **fine-tuned classifier** (DeBERTa-v3 class), white-box;
- a **prompted LLM assessor** given the control text and its 800-53A assessment
  objectives, black-box.

**Adversary.** Whoever writes the SSP (system owner, ISSO, vendor) and wants a
deficient implementation approved without fixing it.
- *White-box:* scores or gradients of the fine-tuned assessor.
- *Black-box:* query access to the prompted assessor's decision, with a query budget.
- The adversary may rewrite the statement freely, but **may not remove or fix the
  deficiency.**

**Success** (one attacked statement): the assessor says *compliant* **and** an
independent checker confirms the injected deficiency is still explicitly stated.

**Two failure modes that are not successes, reported separately:**
- *Fix:* the rewrite makes the implementation compliant (no attack, just a fix).
- *Omission:* the rewrite deletes or blurs the deficiency until it is "not stated".
  Omission is realistic (vague narratives are common) and is reported as its own
  finding, but it does not count toward attack success.

**Why this is ML research, not prompt engineering.** The target is a learned model,
the attack is an optimization procedure with a defined threat model, and the novel
part is the constraint: standard adversarial NLP preserves meaning in general; this
attack must preserve one specific, checkable fact (the deficiency). Defenses
(adversarial training, detection) close the loop in the full project.

---

## The questions this spike must answer

Answer in order. Stop at the first failure. Time estimates assume the pace of the
predecessor spike; the parts that don't compress are the owner's hand audits and
attack runtime.

| | Question | Est. elapsed | Kill point |
|---|---|---|---|
| Q0 | Is it already done? | ~30 min | yes |
| Q1 | Can we build ground truth? (incl. early checker test) | ~2 h | yes |
| Q2 | Does the assessor learn compliance, not generator style? | ~3 h | **yes, most likely** |
| Q3 | Does optimization beat a naive rewrite, under the constraint? | ~6 h | no (any outcome is a finding) |
| Q4 | Do attacks transfer from open to closed assessors? | ~7 h | descriptive only |

Worst case: about three hours lost. Full spike: about one working day, with 2-3
hours of owner audit time.

### Q0: prior art

Targeted search (arXiv, ACL Anthology, Google Scholar, USENIX/IEEE S&P/CCS
proceedings) for adversarial attacks on LLM compliance, audit or policy assessors,
and on LLM-as-judge evasion where a specific factual property must survive.

- **Kill:** published attacks on compliance or audit assessors with an equivalent
  preserved-deficiency constraint.
- **Not a kill:** generic LLM-judge or jailbreak attacks. Those are related work.
- Output: `docs/lit_review.md` + `docs/literature.bib`. A systematic database search
  is still required before any submission.

### Q1: ground truth

1. Pick the control set (draft below): controls whose requirements are crisp and
   checkable, with organization-defined parameters fixed from the FedRAMP Moderate
   baseline where it defines them.
2. Write a **deficiency catalog**: 3-5 specific, injectable, checkable facts per
   control.
3. Generate compliant and deficient statements with **at least two generator model
   families**, seeded from FedRAMP / OSCAL template language and varied in length,
   style and level of detail.
4. **Early checker test (Q1b):** the owner hand-writes 5-6 adversarial-style
   rewrites of deficient statements (hedged, buried, euphemized, compensating-control
   framing). The extraction checker must still find the deficiency in each.
   If it can't, Q3 can never be trusted: stop and redesign the checker.
5. Owner hand-audits 100 random statements against their injected labels.

**Gate Q1:** >= 2,000 statements; >= 90% of the audited sample matches its label;
checker catches the deficiency in >= 5 of 6 hand-written rewrites.

### Q2: is the assessor real?

The analog of the predecessor's vendor-grouped split, and the most likely killer.

- Fine-tune the classifier (free Colab T4, minutes). Configure the prompted assessor.
- Evaluate on three splits: random, **held-out controls**, **held-out generator**
  (train on one generator family, test on the other).

**Gate Q2:** fine-tuned assessor macro-F1 >= 0.85 on the held-out-generator split,
and the prompted assessor >= 0.85 on the full test set.
**Fail** means the assessor detects generator style, not compliance. Fix the corpus
before anything else.

### Q3: attacks under the constraint

Attacked set: deficient statements the assessor correctly flags (attacking misses
inflates success).

| Method | Target | Access |
|---|---|---|
| Paraphrase baseline (no adversarial objective) | both | none |
| TextFooler / BERT-Attack (TextAttack) | fine-tuned | white/grey-box |
| PAIR-style iterative LLM attacker | prompted | black-box, budget 20 queries |

Every attacked output goes through the checker (deficiency still stated?) and, for
the checker gate, an owner audit of 50 adversarial outputs.

**Gates Q3:**
- checker agrees with the owner on >= 90% of the 50 audited adversarial outputs
  (otherwise Q3 numbers are void);
- attack success rate >= 30% on at least one target;
- attack success rate >= 15 points above the paraphrase baseline on that target.

**Reading the outcome:**
- pass: adversarial ML paper;
- near-zero success: assessors are robust, a real negative result;
- paraphrase already succeeds: assessors are brittle without optimization, a
  measurement finding, not ML;
- success only via fix or omission: no attack result (omission rate still reported).

### Q4: transfer (no gate)

Do statements optimized against the fine-tuned or open assessor also fool the
prompted closed one? Report transfer rate.

---

## Draft control set and deficiency catalog

Parameters come from the FedRAMP Moderate baseline where defined, otherwise fixed in
`config.yaml`. To be finalized in Q1.

| Control | Example injectable deficiencies |
|---|---|
| AC-2 Account Management | no periodic account review; inactive accounts not disabled |
| AC-7 Unsuccessful Logon Attempts | no lockout; threshold looser than parameter |
| IA-2(1) MFA, Privileged Accounts | MFA not required for privileged accounts |
| IA-5 Authenticator Management | default credentials not changed; password reuse allowed |
| AU-11 Audit Record Retention | retention shorter than parameter |
| SC-8 Transmission Confidentiality | legacy TLS permitted; internal traffic unencrypted |
| SC-28 Protection at Rest | backups or a data store not encrypted |
| CM-7 Least Functionality | unnecessary services or ports enabled, no review |
| SI-2 Flaw Remediation | patch timeline longer than parameter |
| RA-5 Vulnerability Monitoring | scan frequency lower than parameter; no authenticated scans |
| CP-9 System Backup | backups not tested; no offsite copy |

---

## Design principles

**Cache every model call.** LLM calls are the slow, costly part, the way the network
pull was in the predecessor. Every generation, assessor, attacker and checker call is
keyed by a hash of (model, prompt, parameters) and cached to disk. Re-running an
experiment never re-queries a model it has already queried.

**Version the corpus.** Each statement records its control, label, injected
deficiency, generator model, seed template and prompt hash. Splits are defined on
those fields, so the held-out-generator and held-out-control splits are exact.

**The checker is narrow and independent.** It answers an extraction question
("Does this text state that MFA is required for privileged accounts? yes / no /
not stated"), never a holistic compliance judgment, and it runs on a different model
family from both the assessor and the attacker.

**Sample first, scale later.** Every stage takes `--limit`. Prove the wiring on two
controls before generating the full corpus.

---

## Data sources (all public)

| Source | Gives you | Notes |
|---|---|---|
| NIST SP 800-53 Rev. 5 OSCAL catalog (usnistgov/oscal-content) | control text, parameters, 800-53A assessment objectives | assessor rubric and generation context |
| FedRAMP OSCAL baselines and SSP templates (GSA/fedramp-automation) | Moderate baseline parameter values, SSP structure and example language | generation seeds; real SSPs are scarce publicly |
| Generated corpus (this repo) | labeled compliant / deficient statements | synthetic by necessity; held-out-generator split controls for artifacts |

---

## Layout

```
.
+-- README.md
+-- pyproject.toml
+-- config.yaml               # controls, parameters, models, splits, gates
+-- data/
|   +-- raw/                  # OSCAL catalog + FedRAMP baseline. gitignored.
|   +-- cache/                # hashed model-call cache. gitignored.
|   +-- corpus/               # generated statements, Parquet, versioned
|   +-- processed/            # splits, scores, attack outputs
+-- src/
|   +-- pull.py               # OSCAL + FedRAMP -> data/raw/
|   +-- catalog.py            # controls, parameters, deficiency catalog
|   +-- llm.py                # provider wrapper with hashed disk cache
|   +-- generate.py           # corpus generation (Q1)
|   +-- checker.py            # narrow deficiency-extraction checker (Q1b, Q3)
|   +-- assessors.py          # fine-tuned + prompted assessors (Q2)
|   +-- attacks.py            # paraphrase, TextAttack, PAIR-style (Q3)
|   +-- evaluate.py           # metrics, splits, transfer (Q2-Q4)
|   +-- gates.py              # pre-registered go/no-go checks
+-- audit/                    # owner hand-audit sheets and results
+-- notebooks/
|   +-- 01_corpus.ipynb       # Q1: label audit, corpus stats
|   +-- 02_assessor.ipynb     # Q2: split performance
|   +-- 03_attacks.ipynb      # Q3/Q4: success, fix, omission, transfer
+-- docs/
|   +-- lit_review.md         # Q0
|   +-- literature.bib
|   +-- spike_findings.md     # go/no-go write-up
+-- scripts/
    +-- run_spike.sh          # end-to-end: sample (default) or `full`
    +-- update_progress.py    # recompute this README's progress bars
```

---

## Run order

```bash
pip install -e .

python -m src.pull                                   # OSCAL catalog + FedRAMP baseline
python -m src.generate --controls AC-7,AU-11 --limit 200   # wiring check, two controls
python -m src.checker --selftest audit/q1b_rewrites.yaml   # Q1b early checker test
python -m src.generate                               # full corpus
python -m src.gates q1                               # after the owner audit is recorded

python -m src.assessors --train && python -m src.evaluate --q2
python -m src.gates q2

python -m src.attacks --all && python -m src.evaluate --q3 --q4
python -m src.gates q3
```

---

## config.yaml (gates, pre-registered)

```yaml
controls: [AC-2, AC-7, IA-2(1), IA-5, AU-11, SC-8, SC-28, CM-7, SI-2, RA-5, CP-9]
parameters_from: fedramp_moderate
generators: [family_a, family_b]      # two different model families, fixed in Q1
assessors:
  finetuned: deberta-v3-base
  prompted: closed_llm                # given control text + 800-53A objectives
checker: family_c                     # differs from assessor and attacker families
splits: [random, held_out_controls, held_out_generator]
attacks:
  paraphrase: {}
  textattack: [textfooler, bert_attack]
  pair: {query_budget: 20}
gates:
  q1: {min_statements: 2000, min_audit_agreement: 0.90, audit_n: 100,
       checker_selftest_min: 5, checker_selftest_n: 6}
  q2: {min_f1_held_out_generator: 0.85, min_f1_prompted: 0.85}
  q3: {min_checker_agreement: 0.90, checker_audit_n: 50,
       min_attack_success: 0.30, min_gain_over_paraphrase: 0.15}
seed: 0
```

---

## Metrics

- **Clean performance:** macro-F1 per split; per-control F1.
- **Attack success rate (ASR):** attacked statements flipped to *compliant* with the
  deficiency still stated, over attacked statements (correctly flagged deficient).
- **Fix rate** and **omission rate:** rewrites that removed or blurred the deficiency.
- **Query cost:** mean assessor queries per success (black-box).
- **Transfer rate:** success on the prompted assessor of statements optimized
  against the fine-tuned one.
- **Checker validity:** agreement with owner audit, on clean and adversarial text.

---

## Ethics and dual use

This attacks compliance automation, so findings are written for defenders: the
deliverable is the vulnerability and its mitigation, not a toolkit for passing
assessments. The corpus is synthetic and describes no real system. Optimized
adversarial statements are released only as aggregate examples, not as a
ready-to-use set per control.

---

## What this spike is NOT

- Not the final attack or defense. TextAttack and PAIR-style loops are for go/no-go;
  GCG-style gradient attacks and defenses come after the gate.
- Not paper results. These numbers decide whether to write, not what to claim.
- Not a full corpus until the two-control wiring check passes.

---

## Project Progress

**Overall: 23%** (7 of 30 tasks) -- see [TODO](#todo) for details

```
Phase 0 - Setup                   ████████████████████ 100% (5/5) ✓
Phase 1 - Q0 prior art            ░░░░░░░░░░░░░░░░░░░░   0% (0/3)
Phase 2 - Q1 ground truth         ██████░░░░░░░░░░░░░░  29% (2/7)
Phase 3 - Q2 assessor             ░░░░░░░░░░░░░░░░░░░░   0% (0/5)
Phase 4 - Q3 attacks              ░░░░░░░░░░░░░░░░░░░░   0% (0/6)
Phase 5 - Q4 transfer + go/no-go  ░░░░░░░░░░░░░░░░░░░░   0% (0/4)
```

*Last updated: 2026-10-24*

---

## TODO

### Phase 0 - Setup

- [x] Scaffold `src/`, `notebooks/`, `scripts/`, `data/`, `audit/` and ignore rules
- [x] MIT license
- [x] `pyproject.toml` with pinned dependencies
- [x] `config.yaml` with pre-registered gates (above)
- [x] `src/llm.py` provider wrapper with hashed disk cache

### Phase 1 - Q0 prior art

- [ ] Targeted search: adversarial attacks on LLM compliance / audit assessors
- [ ] `docs/lit_review.md` and `docs/literature.bib`
- [ ] Q0 decision: proceed, narrow, or kill

### Phase 2 - Q1 ground truth

- [x] Pull OSCAL 800-53 Rev. 5 catalog and FedRAMP Moderate baseline
- [x] Finalize control set, parameters and deficiency catalog
- [ ] Two-control wiring check (`--limit 200`)
- [ ] Q1b: owner writes 6 adversarial rewrites; checker self-test
- [ ] Full corpus generation across two generator families
- [ ] Owner audit of 100 random statements
- [ ] Q1 decision against gates

### Phase 3 - Q2 assessor

- [ ] Fine-tune DeBERTa-v3 assessor
- [ ] Prompted assessor with control text + 800-53A objectives
- [ ] Random, held-out-control and held-out-generator splits
- [ ] `02_assessor.ipynb`: per-split and per-control performance
- [ ] Q2 decision against gates

### Phase 4 - Q3 attacks

- [ ] Paraphrase baseline
- [ ] TextFooler / BERT-Attack against the fine-tuned assessor
- [ ] PAIR-style attacker against the prompted assessor (budget 20)
- [ ] Checker pass over all outputs; success / fix / omission accounting
- [ ] Owner audit of 50 adversarial outputs (checker validity)
- [ ] Q3 decision against gates

### Phase 5 - Q4 transfer + go/no-go

- [ ] Transfer from fine-tuned to prompted assessor
- [ ] `03_attacks.ipynb`: success, fix, omission, transfer, query cost
- [ ] `docs/spike_findings.md` against the pre-registered gates
- [ ] Go/no-go on the paper (owner's decision)

## License

Code is released under the MIT License. NIST and FedRAMP source material is subject
to its publishers' terms.

