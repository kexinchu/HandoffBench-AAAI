# Goal completion audit

Audit date: 2026-07-21. The requested endpoint is an AAAI-27-format paper with
evidence strong enough for an approximately 4/5 review. The human-validation,
replacement, final-audit, and sealing gates are now complete. The endpoint is
still incomplete because the preregistered confirmatory model matrix has not
been authorized or executed.

| Requirement derived from the brief | Authoritative evidence | Status |
|---|---|---|
| Benchmark isolates state transfer at an agent handoff | Task schema, fixed boundaries, deterministic simulators, sealed 200-family split | Complete for dataset construction |
| Gold boundary state is independently credible | Locked double annotations, two agreement reports, disagreement-only adjudications, blind validity review, composite agreement artifact | Complete |
| Invalid original tasks are replaced without outcome inspection | Original adjudication rejected 24 tasks; blind review rejected 39 agreement-only static-risk tasks; 63 new families were generated and double-annotated before model calls | Complete; zero candidate-model calls |
| Replacement labels and validity are resolved | Replacement agreement and adjudication artifacts: 63/63 double-annotated, 47 criticality disagreements adjudicated, 0 replacements rejected | Complete |
| Required baselines and matched mechanism intervention exist | Full History, Free Summary, Structured, Gold Oracle, EHC, and 2×2×2 code/raw development runs | Implemented and development-tested |
| Judge-free state/workflow metrics and failure decomposition | Evaluator, simulator, primary-claim scorer, HIR, and confirmatory analyzer | Implemented; confirmatory population estimates pending |
| More than one model family | Versioned Qwen2.5-14B and Ministral-3-14B snapshot manifest | Design sealed; confirmatory calls not authorized |
| Final population is balanced and immutable | `data/splits/confirmatory_v3.1.sealed.json`: 200 independent families, 40 in each of five domains | Complete |
| No test leakage or post-outcome task repair | Zero-call attestation, static final audit, leakage/overlap audit, task hashes, canonical dataset hash, immutable seal | Pre-execution gate complete; post-seal repair remains prohibited |
| Adequate construct validity | All final tasks pass public unique-terminal-sequence, grounding, provenance, impact, and exact-oracle hard checks | Hard gates pass; synthetic/ecological limitations remain |
| Novelty survives closest-work comparison | Primary-source audit including Handoff Debt, PACT, AgentAsk, EntCollabBench, NeuroState, and ProvenanceGuard | Current scoped claim is defensible; recheck at submission |
| Reproducible statistical analysis | Preregistration, ITT/fail-closed analyzer, family bootstrap, Holm, McNemar sensitivity, and immutable development runs | Implemented; confirmatory artifacts pending |
| Confirmatory evidence answers the research questions | Sealed 200-family × 2-model × 2-seed run cube and generated tables | Missing: `execution_authorized` is false and no confirmatory result exists |
| AAAI-27 format compliance | `paper/main.pdf`, official 2027 author kit, and format audit | Current anonymous draft passes mechanical checks; event-specific page/checklist rules must be rechecked |
| Reviewer-level completeness | Final paper containing confirmatory estimates, uncertainty, null/harmful outcomes, and updated review | Pending confirmatory execution and paper update |

## Human-validation and replacement record

The original 200 tasks were independently annotated twice. Across 990 proposed
claims, claim F1 was 0.9606; exact action-sequence agreement was 174/200 (0.87),
category agreement was 951/990 with Cohen's $\kappa=0.9449$, and criticality
agreement was 478/990 with $\kappa=0.2420$. Status, typed value, and provenance
agreement were each 990/990. The 739-entry disagreement queue was adjudicated
exactly once; 24 tasks were rejected.

A separate reviewer, blind to labels and adjudication, examined 39 agreement-only
tasks flagged by static construct-validity diagnostics and rejected all 39: 34
for ambiguous terminal action, four for ambiguous sequence order, and one for
unspecified terminal semantics. These tasks are distinct from the 24 adjudication
rejections, giving 63 total exclusions.

The 63 newly generated replacement families were independently double-annotated.
The annotators agreed exactly on all 63 action sequences and on claim identity,
category, status, typed value, and provenance for all 299 claims. Criticality
agreement was 252/299 (0.8428; $\kappa=0.6932$), producing 47 disagreement entries.
All 47 were adjudicated and no replacement was rejected. The composite population
is 137 retained originals plus 63 replacements, balanced at 40 families per
domain.

## Final audit and seal

Every named hard check in `annotations/confirmatory_v3/final_audit.ready.json`
passes, including unique public legal terminal sequences, grounded irreversible
arguments, provenance, impact consistency, exact-oracle execution, schema
validity, and absence of exact development identity/trace collisions. The final
agreement artifact attests zero candidate-model calls.

- Seal ID: `hb-v3.1-9671bf1ff2d5-20260721`
- Sealed manifest: `data/splits/confirmatory_v3.1.sealed.json`
- Manifest SHA-256: `d2b11edb4e39041fe246706d45b4b36302921813b49d5040fe39f35a88130804`
- Canonical dataset SHA-256: `9671bf1ff2d507e31a62069bbd655b83f53803aeee3a5b5908da7b8d9d892a93`

The v3 leakage audit reports 14/200 catalog-only, 12/200 predicate-only,
200/200 exact-copy, and 61/200 (30.5%) oracle-sequence-plus-enum-first success.
The last probe is not name-only: it is given the evaluator-side ordered oracle
action sequence. Sixty-nine tasks share a normalized action-graph topology with
development tasks. This normalization erases semantic labels and values, so the
count is a diagnostic rather than proof of duplication; equally, it precludes a
claim of complete structural holdout. Neither diagnostic was used for post-hoc
filtering.

## Remaining order of operations

1. A human verifies the seal, model snapshot hashes, hardware readiness, and the
   static preflight report, then explicitly authorizes execution.
2. Change `execution_authorized` only as the recorded authorization act; never
   use it to bypass a failed annotation, seal, hash, or audit gate.
3. Execute the preregistered matrix without task repair, filtering, optional
   stopping, or access to evaluator gold in model prompts.
4. Generate confirmatory tables and release artifacts, retaining provider/parse
   failures and null or harmful findings under the preregistered ITT analysis.
5. Update the manuscript with confirmatory estimates, repeat independent reviewer
   and AAAI-format audits, and reconcile the checklist with final submission rules.

Until these steps are evidenced, all numerical model-performance findings remain
development-only. Sealing completes the dataset-construction gate; it is not a
confirmatory result and does not by itself complete the paper goal.
