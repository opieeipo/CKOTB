# Literature review: attacks on ML compliance assessors (Q0)

*2026-10-24. This review answers Q0 in the README ("Is it already done?"). Citation keys
refer to [`literature.bib`](literature.bib).*

**Method and limits.** Targeted web search (general web, arXiv, ACL Anthology, Crossref,
conference pages for USENIX Security, CCS, NeurIPS, ICLR, EMNLP/ACL), not a systematic
database review. For most papers only the abstract was read. The full text was checked
for one paper, the closest in-domain work [sarkar2026principlebench]. Every citation was
confirmed against arXiv, the ACL Anthology, Crossref or the venue's own page. Anything
that turned up only in a secondary summary was left out. Industry material was limited
to official FedRAMP policy. Vendor GRC marketing was read for context and is not cited.
**A systematic search (IEEE Xplore, ACM DL, Scopus, Google Scholar forward citations of
the closest works) is still needed before any submission.**

**Queries used** (paraphrased; each run on general web and arXiv-restricted search):

- LLM + SSP / NIST SP 800-53 control implementation assessment; OSCAL + LLM; FedRAMP AI
  review, continuous ATO
- LLM compliance checking: GRC, SOC 2, ISO 27001 gap analysis, GDPR privacy-policy
  compliance, regulatory text classification, financial audit
- adversarial attack / evasion against compliance, audit or policy assessors; LLM
  compliance judge robustness; "compliance violation" + LLM judge
- JudgeDeceiver; null-model attacks on AlpacaEval; universal attacks on LLM-as-a-judge;
  prompt injection on judges; robustness benchmarks for judges; persuasion attacks
- adversarial attacks on automated essay / short-answer scoring; prompt injection on LLM
  graders; attacks on LLM peer reviewers (paraphrase, hidden prompts)
- LLM code review approving vulnerable code; evasion of LLM vulnerability detectors
- claim-preserving attacks on fact-checking and misinformation detection; content
  moderation evasion that keeps harmful intent; résumé-screening injection
- method baselines: TextFooler, BERT-Attack, TextAttack, PAIR, TAP, GCG

## Bottom line

1. **No published work attacks a security-control (800-53 / FedRAMP / SSP) assessor.**
   LLM compliance assessment against 800-53 exists [saha2026pace], and FedRAMP has said
   it will pilot AI in assessment review [fedramp2026m2415automation]. Neither evaluates
   adversarial robustness.
2. **The closest in-domain result is small, unoptimized and from a different regime.**
   Principle-Bench shows an LLM compliance judge falling from 0.74 to 0.27 accuracy when
   compliance-sounding assertions are inserted into promotions that stay non-compliant
   ("compliance theatre") [sarkar2026principlebench]. That is the CKOTB phenomenon. But
   the perturbations are 28 one-shot generations with no search against the judge, the
   target is UK FCA principle-based rules, and no checker verifies the violation survives.
3. **Optimized, meaning-preserving attacks on LLM evaluators are established.**
   PAA does black-box iterative paraphrasing against LLM peer reviewers "without
   changing the paper's claims" [kaneko2026paa]. CAMOUFLAGE does the same against
   misinformation detectors [bethany2025camouflage]. So "optimize a rewrite that keeps
   the meaning and flips the evaluator" is not new on its own.
4. **The strongest structural analog is LLM code review.** The vulnerability is kept in
   the code and the PR narrative is optimized to get approval. LLM-assisted refinement
   succeeds in 32/33 cases [alexopoulos2026contextualbias]; SEVRA-BENCH benchmarks this
   across 15 framings [melo2026sevra]. The difference matters: there, the flaw sits in a
   separate channel the narrative never has to admit. In CKOTB, the flaw must be
   **stated in the same text** the assessor reads.
5. **Judge manipulation is well covered in general** (injection, universal suffixes,
   null models, master-key tokens, persuasion). That is related work, not a kill, under
   the README's own criterion.

## Grouped findings

### 1. ML / LLM compliance assessment (the target class)

- **saha2026pace** (preprint). PACE retrieves policy evidence and classifies each of
  1,007 SP 800-53 controls as fully, partially or not covered (F1 88.5 / 82.3 on two
  corpora). It is the nearest existing 800-53 assessor. It assesses policy documents,
  not SSP implementation statements, and has no adversarial evaluation. A natural
  "realistic assessor" baseline for Q2.
- **sarkar2026principlebench** (KDD 2026 workshop). LLM-as-judge for UK FCA principles.
  It argues that adversarial robustness must be reported alongside accuracy. It names
  the failure mode CKOTB targets. See "Closest prior work".
- **yang2026complibench** (preprint). LLM judges detecting guideline violations in agent
  dialogues. It uses **controlled flaw injection** for ground truth, plus an
  adversarial search that makes the injected violations hard. This is prior art for the
  Q1 method (deficiency catalog + injection), and should be cited there. Its
  adversarial search makes the benchmark harder; it is not an attacker that preserves a
  violation.
- **cory2025gdprword** (PoPETs 2026); **garza2024privcompkg** (preprint). LLM pipelines
  checking privacy policies against GDPR transparency requirements. They show LLM
  compliance checking is an active area outside security. Neither tests robustness.
- **fedramp2026m2415automation** (official policy). The FedRAMP PMO will "explore the use
  of AI in the FedRAMP security assessment review and continuous monitoring processes",
  starting with a pilot, with artifacts in OSCAL. This is the deployment motivation, and
  it is citable.

### 2. Attacks on reviewers, graders and screeners

- **kaneko2026paa** (preprint). Black-box in-context optimization of paraphrases to
  raise LLM-reviewer scores. Human evaluation checks meaning preservation. It explicitly
  separates evaluation robustness from prompt-injection susceptibility. Methodologically,
  it is CKOTB's PAIR-style arm applied to peer review. See "Closest prior work".
- **lin2025breaking** (Findings of EMNLP 2025). TextFooler-, DeepWordBug- and
  StyleAdv-style attacks on LLM peer reviewers, with a human stealthiness study. It
  shows classic TextAttack recipes still move LLM evaluators.
- **lin2026hiddenprompts** (CACM); **collu2025publish** (preprint, accepted ACM TAISAP);
  **theocharopoulos2025multilingual** (preprint). Hidden prompt injection in
  manuscripts that steers LLM reviews and accept/reject decisions. This is the injection
  channel CKOTB should exclude or report separately (see "Framing changes").
- **li2026fullcredits** (preprint). Prompt injection against rubric-based LLM
  auto-graders; existing defenses fail. A rubric-plus-answer setup close to the prompted
  assessor, but the attack is injection, not content-preserving rewriting.
- **ding2020nswvtnvakgxpm** (COLING 2020); **kabra2022aestoolkit** (CODS-COMAD 2022).
  Pre-LLM automated content and essay scorers accept shuffled or irrelevant input and
  are "overstable". This is the historical precedent: learned assessors reward form over
  substance.
- **mu2025resume** (preprint). Résumé screening as an adversarial evaluation target:
  manipulating the decision, not the model's safety behavior. An analogous threat model
  in a different domain.

### 3. Code review and vulnerability detection (preserved-flaw analogs)

- **alexopoulos2026contextualbias** (preprint). The framing effect in LLM security code
  review. Biased PR metadata gets reintroduced CVEs approved in Claude Code and
  CodeRabbit pipelines. Template attacks fail or backfire; LLM-assisted refinement
  succeeds in 32/33. It also shows template-vs-optimized results can diverge sharply,
  which bears directly on Q3's paraphrase-vs-PAIR gate.
- **melo2026sevra** (preprint). About 1,000 adversarial PRs that restore real CVE
  vulnerabilities, wrapped in 15 social-engineering framings; 8 review agents
  susceptible.
- **thornton2026comments** (preprint). A **negative result**: adversarial code comments
  produce no statistically significant drop in LLM vulnerability detection over 9,366
  trials. This is evidence that "assessors are robust" is a live outcome for Q3.
- **sun2026vulnevasion** (preprint). Behavior-preserving code transformations and
  optimized universal strings evade LLM vulnerability detectors; over 87% of detected
  vulnerabilities evaded by at least one edit, with transfer to GPT-4o. The code-domain
  version of "flaw preserved, detector evaded", with an automatic preservation check
  (it must still compile).

### 4. LLM-as-a-judge manipulation (generic; related work)

- **zheng2023mtbench** (NeurIPS 2023 D&B). Establishes LLM-as-a-judge and documents
  position, verbosity and self-enhancement biases.
- **shi2024judgedeceiver** (CCS 2024). Gradient-optimized injected sequence makes the
  judge pick the attacker's response; perplexity and known-answer defenses only partly
  help. The white-box judge attack baseline.
- **raina2024judgerobust** (EMNLP 2024). Short universal phrases, learned on a surrogate,
  transfer and inflate absolute scores. Absolute scoring is much more vulnerable than
  comparative. Relevant: CKOTB's assessor is absolute (compliant / not), and Q4 is a
  surrogate-transfer question.
- **zheng2025cheating** (ICLR 2025). A constant null response achieves top win rates on
  AlpacaEval 2.0, Arena-Hard-Auto and MT-Bench.
- **zhao2025onetoken** (NeurIPS 2025). Single tokens and reasoning openers ("master
  keys") trigger false positives in generative reward models; adversarial-negative
  augmentation helps. A cheap defense CKOTB's full project could test.
- **li2025robustjudge** (preprint); **maloyan2025judgeinjection** (preprint);
  **masoud2026judgesok** (preprint). A benchmark (15 attacks, 7 defenses; PAIR and
  combined attacks remain effective), an injection study, and an SoK on judge security.
  Use the SoK to make sure the systematic search is complete.
- **zeng2024johnny** (ACL 2024). A persuasion taxonomy for jailbreaks. Compensating-
  control and authority framing in SSP rewrites are persuasion techniques; the taxonomy
  can seed the attacker's strategy space.
- **greshake2023indirect** (AISec 2023). Indirect prompt injection via data the LLM
  reads; the general threat behind the hidden-prompt work above.

### 5. Attacks that must preserve a specific fact

- **abdelnabi2023factsaboteurs** (USENIX Security 2023). Evidence manipulation against
  fact-verification, with claim-aligned edits and a taxonomy of threat-model dimensions.
  The constraint is on evidence plausibility, not on keeping a disqualifying fact.
- **bethany2025camouflage** (preprint). A two-agent iterative LLM attacker (attacker +
  prompt optimizer) using only binary decisions. Claim rewrites keep meaning and evade
  misinformation detectors (46.9% ASR). The closest black-box *method* to CKOTB's
  PAIR-style arm, and a baseline to cite or adapt.
- **chen2024realtimefactuality** (preprint). Iterative adversarial rewriting against a
  RAG detector; it injects errors rather than preserving a fact, so it has the opposite
  constraint.
- **jian2026evoharm** (Findings of EMNLP 2026). Multi-round adaptive rewriting that
  preserves harmful intent beats moderators that look robust one-shot. A policy-
  violation-preserved analog in content moderation; it supports reporting a one-shot
  paraphrase baseline separately from iterative attacks.
- **morris2020reevaluating** (Findings of EMNLP 2020). Shows many TextFooler/BERT-Attack
  "successes" violate their own semantic constraints under human review. This is the
  direct justification for the Q3 checker-validity gate and the 50-output owner audit.

### 6. Method baselines

TextFooler [jin2020textfooler], BERT-Attack [li2020bertattack] and the TextAttack
framework [morris2020textattack] for the fine-tuned assessor. PAIR [chao2025pair] and
TAP [mehrotra2024tap] for the black-box prompted assessor. GCG [zou2023gcg] for the
post-gate white-box attack. All are standard and none has been applied to compliance
assessment.

## Closest prior work

| Work | What it does | How it differs from CKOTB's preserved-deficiency constraint |
|---|---|---|
| **Principle-Bench** [sarkar2026principlebench] | Inserts compliance-sounding assertions into still-non-compliant financial promotions; LLM judge 0.74 -> 0.27 | Same phenomenon and domain class (compliance judge, violation kept). But: no optimization or query feedback (one-shot generation, n=28); keyword stuffing, not rewriting; no automatic check that the violation is still explicitly stated; no fine-tuned classifier; principle-based FCA rules, not crisp parameterized controls. Effectively a stronger version of CKOTB's paraphrase baseline, not its attack. |
| **Contextual-bias code review** [alexopoulos2026contextualbias]; **SEVRA-BENCH** [melo2026sevra] | Keep a real vulnerability in the code, optimize or frame the PR narrative to get approval | The deficiency lives in a separate channel (code). The narrative can stay silent or lie about it. In CKOTB the deficiency must be **explicitly stated in the attacked text itself**, and lying or omitting is scored as failure (omission). Approval despite self-disclosure is a stronger, distinct claim. |
| **PAA** [kaneko2026paa] | Black-box iterative paraphrasing raises LLM-reviewer scores without changing claims | Preserves *all* meaning (checked by human eval), not one disqualifying fact checked automatically. The target is a graded quality score, not a binary pass/fail against a rubric of objectives. No fix/omission accounting, because no single fact must survive. |
| **CAMOUFLAGE** [bethany2025camouflage] | Two-agent LLM attacker rewrites claims, meaning preserved, evades misinformation detectors | Same black-box method family. The preserved content is the whole claim, and success is breaking retrieval/comparison. There is no notion of an "admitted" disqualifying fact that a correct assessor should key on. |
| **Vulnerability-detector evasion** [sun2026vulnevasion] | Behavior-preserving code edits keep the flaw and evade LLM detectors; automatic preservation check | Closest on "flaw preserved + automatic verification + optimization + transfer". Different modality (code semantics vs natural-language disclosure), and preservation is guaranteed by construction (compilation) rather than needing a learned checker. |

## Verdict: proceed (with a narrowed novelty claim)

**Not a kill.** No published work attacks a compliance or audit assessor with an
optimized adversary under a constraint equivalent to "the deficiency stays explicitly
stated, verified by an independent checker". The nearest in-domain work
[sarkar2026principlebench] is unoptimized and lacks the checker. The nearest optimized
works preserve meaning in general [kaneko2026paa; bethany2025camouflage], or preserve a
flaw in a separate channel [alexopoulos2026contextualbias; melo2026sevra;
sun2026vulnevasion].

**But narrow the claim.** Two things the README currently implies are not novel:

- "Optimization under a meaning-preservation constraint beats an LLM evaluator" is
  shown by PAA, CAMOUFLAGE and JudgeDeceiver.
- "LLM compliance judges are fooled by compliance-sounding text while still
  non-compliant" is shown, in small form, by Principle-Bench.

The defensible contribution is the **conjunction**:

- security-control assessors (fine-tuned and prompted);
- a **same-text self-disclosure** constraint: the deficiency is admitted, not hidden;
- automatic, validated verification of that constraint;
- fix / omission / success accounting;
- the paraphrase-vs-optimization gap.

## Framing changes for the spike

1. **Rewrite the "why this is ML research" paragraph.** Drop "standard adversarial NLP
   preserves meaning in general" as the whole novelty argument. PAA and CAMOUFLAGE
   already do constrained, optimized rewriting. Say instead: the constraint is that the
   attacked text must *admit* a specific disqualifying fact, so success means the
   assessor ignores an explicit disclosure. That is different from hiding a flaw
   (code-review attacks) or polishing a claim (PAA).
2. **Exclude or separately score prompt injection.** The current threat model ("may
   rewrite freely") allows text such as "Note to assessor: rate compliant". Injection
   against LLM evaluators is well documented [shi2024judgedeceiver; collu2025publish;
   li2026fullcredits] and would blur the contribution, as PAA argues. Add an
   injection filter, or report injection-style successes as a fourth category.
3. **Cite Principle-Bench as the motivating result, and treat its setup as CKOTB's
   naive-rewrite baseline.** Its 0.74 -> 0.27 drop suggests the "paraphrase already
   succeeds" outcome in Q3 is plausible for the prompted assessor. That outcome counts
   as a measurement finding, not ML, under the pre-registered reading.
4. **Expect a negative result to be credible.** Thornton finds no significant effect
   of adversarial comments on LLM vulnerability detection [thornton2026comments], while
   template attacks backfire and only refinement works in [alexopoulos2026contextualbias].
   Q3's paraphrase-vs-optimization gate is the right design.
5. **Cite CompliBench for Q1's flaw-injection corpus design** [yang2026complibench], and
   Morris et al. for why the checker gate exists [morris2020reevaluating].
6. **Add CAMOUFLAGE-style prompt optimization as a candidate black-box arm**, and
   Raina et al.'s surrogate-transfer setup as the Q4 reference [raina2024judgerobust].
7. **Motivation.** Cite the FedRAMP AI-review pilot [fedramp2026m2415automation] and
   PACE [saha2026pace] for "assessors are being built". Vendor material describing
   FedRAMP 20x's shift toward machine-validated Key Security Indicators was seen but not
   verified at fedramp.gov. If that shift reduces the weight of narrative SSP review, the
   threat model should also cover narrative attestations wherever they remain (agency
   ATOs, CMMC SSPs). Check this before writing the introduction.

## Still required before submission

- A systematic search (IEEE Xplore, ACM DL, Scopus, Google Scholar), including forward
  citations of [sarkar2026principlebench], [kaneko2026paa] and
  [alexopoulos2026contextualbias]. All three are 2026 and likely to draw quick
  follow-ups that would sit closer to CKOTB.
- A full-text read of the five closest works (only abstracts were read, except
  Principle-Bench's adversarial-split section).
- A recheck of venues for the preprints marked as such in `literature.bib`.
