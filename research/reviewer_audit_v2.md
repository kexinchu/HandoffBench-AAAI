# HandoffBench AAAI-27 Reviewer Audit v2

**Audit date:** 2026-07-18. **Scope:** current `paper/main.tex`, all included
sections and `paper/main.pdf`; current code, 200 candidate families, development
artifacts, annotation scaffolding, preregistration v2, overlap/leakage audits,
power simulation, model manifests, and confirmatory preflight. The prior audit
remains preserved as `reviewer_audit_latest.md`; this document supersedes its
current-state judgment.

## Bottom-line review score

**Current submission score: 2/5 (Reject).** This is no longer merely an idea:
the paper has a coherent formalism, executable harness, 200 synthetic candidate
families, honest development diagnostics, a pre-test amendment, and unusually
good fail-closed reproducibility scaffolding. However, it is still an
**unfinished benchmark paper**. The 200 items are explicitly unannotated,
unadjudicated, unsealed candidates. There is no human agreement result and no
confirmatory model result. The only empirical model evidence comes from six
development families, and the headline all-on EHC comparison is negative.
AAAI cannot accept a benchmark on the basis of proposed gold labels plus static
simulator consistency.

**Potential after completed human validation and confirmatory execution: 4/5
(Weak Accept), conditional rather than guaranteed.** A 4 requires: a materially
retained, human-validated split near the planned N; reproducible agreement and
adjudication; evidence that Structured loses state/success relative to Oracle;
and a cross-model advisory-check effect or another equally clear diagnostic
finding. If confirmatory effects are null but the benchmark has high agreement
and exposes a robust, useful failure taxonomy, the likely score is 3/5. If the
69 normalized topology overlaps/action-interface leakage survive human review,
or if Gold Oracle itself is unreliable, the score remains 2--3. A 5/5 is
unlikely without stronger external validity (real framework adaptation or
trace-inspired cases) and a less synthetic action interface.

## Evidence ledger: claim by claim

| Paper claim / implication | Current evidence | Reviewer verdict |
|---|---|---|
| HandoffBench targets semantic state transfer at an inter-role boundary, not routing or generic memory. | Formal definition, fixed-boundary records, separate source/receiver roles, transfer views, deterministic runner. | **Supported as a protocol definition.** |
| The candidate pool contains 200 unique families, 40/domain. | Three candidate JSON files, unique IDs/families, domain tests, static audit. | **Supported as repository composition**, not as 200 valid/independent test items. |
| Families are independently authored. | Unique family labels and automaton identities; no exact trace/action-graph collision. | **Partially supported.** Sixty-nine candidates share normalized action topology with development; labels/hashes do not establish semantic independence. |
| Each boundary has a minimal, task-critical gold state. | 990 author-proposed claims, mutation/execution checks, trace grounding. | **Pending construct validation.** Humans have not reconstructed claims, tested uniqueness, or agreed on minimality. Call these proposed labels until adjudication. |
| The ontology captures epistemic and authority-bearing state. | Candidate counts: 200 goals, 471 verified facts, 109 constraints, 80 unresolved slots, 66 consent, 62 policy checks, two authenticated commitments. | **Supported coverage for common fields, uneven for rare fields.** No broad commitment/risk claim is justified from this pool. |
| Evaluator metrics are judge-free and deterministic. | Canonicalization, typed probe, one-to-one matching, simulator and extensive tests. | **Substantially supported technically.** Human validity of exact matching/equivalence remains pending. |
| Source extraction, transport, and receiver utilization can be separated. | First receiver probe, generated artifacts, Gold Oracle, factorial views, sidecars. | **Enabled, not yet demonstrated population-wide.** The manuscript appropriately says “enable,” but no confirmatory decomposition exists. |
| Handoff-induced regression exists. | In development, Gold Oracle 45/48 versus Structured 36/48 and other lower views. | **Development indication only.** Six families/four variants cannot estimate prevalence across five domains. |
| EHC improves on Structured. | Development EHC 33/48 versus Structured 36/48; difference $-6.25$ pp, CI $[-22.9,12.5]$. | **Not supported; observed direction is negative.** The paper now honestly avoids a superiority claim. |
| Provenance improves transfer/safety. | Two-model factorial: provenance success effect $-6.77$ pp; critical errors +0.042; provenance×checks $-4.69$ pp. | **Not supported in development and possibly harmful.** This negative result must remain prominent after confirmatory analysis. |
| Advisory checks improve strict success. | Two-model/six-family factorial: +6.77 pp, family CI $[3.65,9.38]$. | **Promising development signal, not confirmation.** Tasks are consent/authority-heavy and only six families; the amended directional hypothesis is legitimate but risky. |
| Factorial effects isolate typing/provenance/checks. | Matched source-artifact reuse; 24/24 fairness blocks pass in development; protocol describes advisory/enforcement separation. | **Good internal-design evidence**, but only development execution exists. Confirmatory cube is pending. |
| Candidate workflows are not shallowly solvable. | Catalog-only 7%, predicate-only 6%; exact copy 100%. | **Partially supported.** Oracle action names plus enum-first reaches 34.5%, much above uniform-enum expectation; public interface leakage remains material. |
| Candidate and development splits do not overlap. | No family/entity/seed/exact or normalized trace/exact graph collision; no lexical pair at Jaccard ≥.80. | **Cannot claim structural holdout.** There are 69 normalized-topology candidate overlaps (552 pairs); lexical metrics miss semantic paraphrases and can over/under-collapse. |
| 200 families provide adequate power. | Fixed simulation: at ICC .10, N=200 power .691 for 8 pp and .847 for 10 pp. | **Adequate only for effects near 10 pp under assumptions.** Rejection during annotation lowers N; 8-pp effects remain underpowered. |
| Two model families are reproducibly specified. | Qwen2.5-14B-Instruct and Ministral-3-14B-Instruct-2512; per-file hashes, serving args, source revisions; independent rehash passed. | **Strong planning/reproducibility evidence.** It is not confirmatory evaluation. Ministral license is correctly recorded as unknown/null. |
| The benchmark is frozen and confirmatory execution ready. | Preflight verifies 200/40-per-domain but exits 2: seal/agreement absent, execution false. | **Explicitly false/pending.** This is handled honestly in the repository and must remain so in the paper. |

## Novelty and collision analysis

### What is already occupied

1. **Handoff Debt** already establishes deterministic predecessor interruption,
   successor takeover, matched context-view comparison, free versus structured
   notes, solve rate, and rediscovery/token cost. HandoffBench cannot claim the
   first handoff benchmark, takeover protocol, structured handoff, or context
   comparison.
2. **NeuroState-Bench** already motivates explicit probes for latent state and
   commitment integrity. The existence or utility of a state probe is not new.
3. **ProvenanceGuard** already connects traceable evidence for user intent to
   action screening and blocking. Provenance-aware safety and action gating are
   not new by themselves.
4. tau-bench/tau2, ToolSandbox, and stateful enterprise benchmarks already
   provide interactive policies, tools, dynamic state, and deterministic
   terminal evaluation. MultiAgentBench already evaluates multi-agent
   communication. Frameworks already expose history filtering, typed payloads,
   shared state, and handoff tools.

### Defensible novelty if confirmed

The defensible contribution is the **combination and estimand**, not any single
component: evaluator-private atomic boundary state with epistemic/authority
status; field-level fidelity measured before action; paired Gold Oracle
conditioning to localize transfer-induced regression; and a matched
representation factorial that keeps advisory checks separate from enforcement.
This is meaningfully different from coding resumability, within-profile state
drift, or runtime action blocking.

The current collision table is commendably direct, but the Related Work section
is too narrow for a final AAAI paper. It should add a compact second paragraph
covering tau2/ToolSandbox/stateful enterprise benchmarks, multi-agent
communication, and official framework transfer semantics. The paper should not
use a scoped “first” claim unless the literature is rechecked immediately before
submission. The novelty survives only if the final artifact teaches something
beyond “structured JSON and reminders help.”

## Construct-validity concerns

1. **Proposed gold is not yet gold.** Static provenance and oracle execution
   prove consistency with authored labels, not that independent readers recover
   the same task-critical state or legal sequence. Double annotation and
   adjudication are the highest-priority missing evidence.
2. **The probe changes the task.** Every receiver must explicitly reconstruct a
   ten-field state object before acting. This is excellent for measurement but
   may improve/distract reasoning relative to natural handoff systems. The paper
   evaluates probe-conditioned receivers. It should state this and, if feasible,
   include a small action-only sensitivity condition.
3. **Gold Oracle is not perfect reasoning/no-handoff.** It changes the
   representation to canonical state and still depends on receiver competence.
   Oracle-conditional HIR is useful, but it identifies failures relative to this
   intervention, not all causal loss at a production handoff. Reverse flips and
   Oracle failures must be reported.
4. **Action-interface leakage is substantial.** Catalog-only/predicate-only
   baselines are low, but the 34.5% oracle-name+enum-first result shows that enum
   ordering can solve many paths once action class is known. This is not a pure
   name-only baseline and the paper labels it correctly. Human leakage review,
   enum/order randomization, and an action-name sensitivity analysis remain
   necessary.
5. **Structural holdout is unresolved.** Sixty-nine candidates share normalized
   action topology with development. Common ask→authorize→commit graphs may be
   intrinsic to the construct, but then “independent family” must mean semantic
   scenario independence rather than topology independence. Define this before
   adjudication and report retained overlap.
6. **Synthetic severity bias.** 195/200 paths are user-impacting. This supplies
   safety signal but may exaggerate the benefit of explicit checks and limits
   claims about ordinary handoffs. Stratify by authority/severity and retain
   benign informational cases.
7. **Domain realism is limited.** Policies and tools are authored mock worlds;
   forty families/domain are breadth by design, not evidence of production
   representativeness. Healthcare examples are scheduling-only, appropriately,
   but all domains need explicit external-validity limits.
8. **Exact matching is defensible but incomplete.** Canonical typed matching is
   auditable and avoids judge bias, yet humans may express equivalent atomic
   decompositions. Agreement analysis must reveal whether the fixed ontology and
   granularity are stable. Weighted and unweighted metrics should both appear.
9. **Rare categories cannot support broad claims.** Two commitment claims and no
   primary risk emphasis are insufficient for commitment/risk conclusions.
10. **Source fairness requires end-to-end accounting.** Reusing one source
    artifact across eight cells is a strong control, but representation-specific
    serialization, receiver input length, validator computation, and failures
    must all enter cost and fairness tables.

## Statistical review

### Strengths

- Family is correctly treated as the independent unit; model and seed rows are
  nested repeated measures.
- ITT retains provider/parse failures with zero credit and raw cost.
- The amended confirmatory family is small: Structured-vs-Oracle strict success
  and advisory-check factorial effect, Holm adjusted.
- Development negatives are retained; EHC superiority was dropped before test.
- Family-cluster bootstrap and mixed diagnostic models match the dependency
  structure better than row-level tests.

### Remaining risks and required clarifications

- Human rejection/replacement may reduce the planned 200. The final paper must
  report the flow diagram: proposed, double-annotated, rejected, replaced,
  adjudicated, and sealed. Do not silently top up after observing model outcomes.
- Power is only .691 for an 8-pp effect at the central ICC assumption. A null
  checks result may be inconclusive rather than evidence of no mechanism.
- Bootstrap should resample families while preserving domain balance, or provide
  a domain-stratified sensitivity analysis; five equal domains make accidental
  domain imbalance avoidable.
- The factorial scaling convention (`2 E[Y∏x]`) should be stated as the chosen
  product-sign contrast. Readers expecting conventional difference-in-
  differences may use a different factor for higher-order terms; analysis code,
  tables, and prose must use one convention consistently.
- Structured-vs-Oracle combines source extraction/serialization and receiver use;
  it is a valid regression estimand but does not alone identify transport loss.
  The gold-generated and/or lossless-transport decomposition must be reported if
  the paper claims three-stage attribution.
- The planned association between state F1 and regression is observational even
  within the benchmark. Keep the manuscript's “diagnostic, not causal” wording.
- Report paired discordant counts and reverse flips, not only mean success gaps.
  For token/cost outcomes report source, receiver, validator, failed calls, and
  output tokens separately; maximum-token envelopes are not expected cost.

## Reproducibility and artifact review

### Strong current assets

- Deterministic schema validation, canonical matching, simulator, action mutation,
  leakage baselines, resumable atomic artifacts, explicit provider/parse failures,
  seeded generation, prompt/schema/config hashes, and a large passing test suite.
- Reproducible 200-candidate static audits and label-free annotation packets.
- Exact local model manifests: all config/tokenizer/chat-template/weight files,
  byte sizes, SHA-256, directory hashes, source revisions, and serving args.
- Confirmatory config, call envelope, cost-accounting schema, invalid isolation,
  and fail-closed preflight. Current preflight correctly fails due to missing
  seal/agreement and `execution_authorized=false`.
- Invalid protocol and development outputs are visibly separated rather than
  silently deleted.

### Blocking gaps

- No completed human responses, agreement statistics, adjudication records,
  rejection reasons, or sealed manifest.
- No confirmatory raw runs, factorial analysis, main tables, or table-to-artifact
  regeneration path has been exercised end to end.
- The repository still lacks a declared top-level data/code release license;
  the paper correctly warns not to infer one. This must be resolved before
  artifact release. Ministral's unknown local license metadata also requires
  manual source verification before redistribution; weights need not be shipped.
- The current workspace is effectively an untracked first commit (`git status`
  shows the project tree untracked), so no meaningful software revision binds
  artifacts yet. A clean, versioned commit/tag is required before sealing.
- Reproducibility tests cannot substitute for documentation of environment,
  exact dependencies, GPU/runtime versions, latency measurement, and one-command
  table generation.

## Paper and AAAI format review

- `main.pdf` is 5 pages on US Letter with the AAAI-27 submission style and
  anonymous author block. No undefined-citation warning was found. The two small
  overfull boxes observed during this audit were subsequently removed without
  manual spacing commands. The current AAAI-27 event page does not state the
  main-content page limit, so the historical AAAI-26 seven-page rule must not be
  treated as authoritative until AAAI-27 publishes submission instructions.
  Under-length is not a strength: decisive human-validation and confirmatory
  results are absent.
- The manuscript now has real primary-source references and an unusually honest
  limitations section. Citation coverage remains narrow; official framework
  semantics and the broader stateful-agent landscape should be cited.
- Abstract wording is still premature for the current artifact. “We introduce
  HandoffBench” is acceptable for a protocol/candidate paper, but “a factorial
  evaluation isolates” reads as completed benchmark evidence. Until confirmatory
  execution, use “we design/pre-register.” “Link field-level fidelity to
  downstream regression” is a planned analysis, not yet a five-domain result.
- Introduction contribution (2), a “three-stage diagnostic decomposition,” is
  only fully defensible after gold extraction/lossless transport/generated
  transfer results. Current Oracle+probe infrastructure enables it but does not
  yet demonstrate all stages.
- Candidate statistics are carefully labeled repository-static and pending
  human validation. Keep that wording. Do not move static 200/200 oracle success
  into a Results claim about agents.
- Development results are appropriately negative and separated, but occupy a
  large fraction of a five-page paper. In the final seven-page version, compress
  them to one small table/paragraph and allocate space to confirmatory main
  results, human agreement, and error decomposition.
- The final paper needs, in the main body: annotation flow/agreement; sealed split
  counts; primary paired effects with CIs/denominators; Oracle failures/reverse
  flips; factorial main effects/interactions; cost; and at least one grounded
  failure example. Supplementary material cannot carry all decisive evidence.

## Shortest critical path to a credible 4/5

This is the minimum path; adding more models or prose before completing it is
lower value.

1. **Execute blinded human annotation now.** Two independent annotators cover all
   200 packets; lock responses; compute claim/value/provenance/category/status/
   sequence agreement; adjudicate; report every rejection and reason. Do not let
   task authors serve as both annotators for their own items.
2. **Resolve leakage/overlap during blinded adjudication.** Review all 69
   normalized-topology overlaps and enum/order leakage flags. Reject or redesign
   ambiguous/secret/shortcut tasks before any candidate model call. Rebuild
   packets and re-annotate any material replacement.
3. **Preserve statistical viability.** Retain or replace enough blinded families
   to stay near 200 and balanced by domain/stressor. Re-run power with the final
   accepted N only as a reporting sensitivity, not a significance-driven sample
   change.
4. **Seal once.** Resolve release/license questions, commit/tag the code, bind
   task/protocol/prompt/model/software hashes, agreement/adjudication outputs and
   split IDs in a non-overwritable manifest. Require preflight to pass; keep
   `execution_authorized=false` until the human/seal review is signed off.
5. **Run the smallest complete confirmatory matrix.** Use the two hashed model
   families, both seeds, eight factorial cells, Full History, Structured/legacy
   mappings, Gold Oracle, and the separate enforced arm exactly as preregistered.
   Do not run a partial cube or tune prompts after inspecting results.
6. **Generate the two confirmatory claims first.** Report Structured-vs-Oracle
   strict-success/HIR with discordant pairs and the advisory-check main effect,
   family-cluster CIs and Holm adjustment. Then report typing/provenance,
   interactions, EHC-vs-Structured (including a negative result), state-error
   association, reverse flips and full cost.
7. **Finish the seven-page evidence story.** Replace planned-tense abstract claims
   with observed, bounded results; add human agreement and main confirmatory
   tables; keep collision positioning and limitations; ensure every number is
   generated from manifest-listed raw artifacts.

### Go/no-go after confirmatory execution

- **Likely 4/5:** high human determinacy/agreement; a substantial
  Structured-vs-Oracle regression gap across both models; advisory checks help
  with corrected uncertainty and acceptable false-block/cost behavior; negative
  provenance/EHC findings are explained and retained; leakage sensitivity does
  not erase results.
- **Likely 3/5:** benchmark validates well but check/provenance mechanisms are
  null or model-specific; contribution becomes a useful diagnostic resource,
  requiring stronger analysis and restrained method framing.
- **Remain 2/5:** low annotation agreement, many rejected/ambiguous tasks,
  Oracle failures dominate, results depend on action naming/enum position, or
  topology-overlap cases drive the effects.

**Final reviewer judgment:** the project is now unusually disciplined and much
closer to an AAAI-quality benchmark than the old audit suggested, but the current
paper still reports preparation rather than the promised study. Human validity
and frozen confirmatory evidence—not more engineering polish—are the remaining
admission ticket.
