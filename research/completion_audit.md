# Goal completion audit

Audit updated: 2026-07-22. The requested endpoint is an AAAI-27-format paper
with evidence strong enough for an approximately 4/5 review. Agent annotation,
replacement, final audit, dataset sealing, confirmatory execution, infrastructure
audit, and formal analysis are complete. The remaining work is submission-level
paper, checklist, release auditing, and human validity review; a review score
cannot be guaranteed.

| Requirement derived from the brief | Authoritative evidence | Status |
|---|---|---|
| Benchmark isolates state transfer at an agent handoff | Task schema, fixed boundaries, deterministic simulators, sealed 200-family split | Complete for dataset construction |
| Gold boundary state is independently credible | Locked agent double annotations, two agreement reports, disagreement-only agent adjudications, blind validity review, composite agreement artifact | Procedurally complete; no recruited-human validation |
| Invalid original tasks are replaced without outcome inspection | Original adjudication rejected 24 tasks; blind review rejected 39 agreement-only static-risk tasks; 63 new families were generated and double-annotated before model calls | Complete; zero candidate-model calls |
| Replacement labels and validity are resolved | Replacement agreement and adjudication artifacts: 63/63 double-annotated, 47 criticality disagreements adjudicated, 0 replacements rejected | Complete |
| Required baselines and matched mechanism intervention exist | Full History, Free Summary, Structured, Gold Oracle, EHC, and 2×2×2 code/raw development runs | Implemented and development-tested |
| Judge-free state/workflow metrics and failure decomposition | Evaluator, simulator, primary-claim scorer, HIR, and confirmatory analyzer | Complete; formal population estimates generated |
| More than one model family | Versioned Qwen2.5-14B and Ministral-3-14B snapshot manifest | Complete; 4,400 ITT rows per model |
| Final population is balanced and immutable | `data/splits/confirmatory_v3.1.sealed.json`: 200 independent families, 40 in each of five domains | Complete |
| No test leakage or post-outcome task repair | Zero-call attestation, static final audit, leakage/overlap audit, task hashes, canonical dataset hash, immutable seal | Complete; dataset remained byte-identical and post-seal repair remains prohibited |
| Adequate construct validity | All final tasks pass public unique-terminal-sequence, grounding, provenance, impact, and exact-oracle hard checks | Hard gates pass; synthetic/ecological limitations remain |
| Novelty survives closest-work comparison | Primary-source audit including Handoff Debt, PACT, AgentAsk, EntCollabBench, NeuroState, and ProvenanceGuard | Current scoped claim is defensible; recheck at submission |
| Reproducible statistical analysis | Preregistration, ITT/fail-closed analyzer, family bootstrap, Holm, McNemar sensitivity, input hashes, and immutable run ledgers | Complete; 10,000-draw formal artifacts and provenance manifest generated |
| Confirmatory evidence answers the research questions | Sealed 200-family × 2-model × 2-seed × 11-condition cube and generated tables | Complete: 8,800/8,800 ITT cells; both preregistered tests reported |
| AAAI-27 format compliance | `paper/main.pdf`, official 2027 author kit, and format audit | Current anonymous draft passes mechanical checks and the 7/9-page rule; checklist is separate |
| Reviewer-level completeness | Final paper containing confirmatory estimates, uncertainty, null/harmful outcomes, and updated review | In progress: confirmatory results integrated; final format/checklist/reviewer audit remains |

## Agent-annotation and replacement record

The original 200 tasks were independently annotated by two isolated LLM-agent
roles. Across 990 proposed
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

The 63 newly generated replacement families were independently double-annotated
under the same role-isolation protocol. The annotation agents agreed exactly on
all 63 action sequences and on claim identity,
category, status, typed value, and provenance for all 299 claims. Criticality
agreement was 252/299 (0.8428; $\kappa=0.6932$), producing 47 disagreement entries.
All 47 were adjudicated and no replacement was rejected. The composite population
is 137 retained originals plus 63 replacements, balanced at 40 families per
domain. The sealed composite agreement artifact inaccurately calls these
decisions human annotations. `research/annotation_provenance_correction_v1`
corrects that metadata without changing sealed bytes. The exact annotation
model/runtime was not recorded, so a separately documented human audit remains
required before claiming human-grounded gold labels.

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

## Confirmatory execution and result record

The final analysis combines the intact 4,400-row Ministral arm from v3.3 with a
prospectively sealed, fresh 4,400-row Qwen v3.4.1 full-arm replacement. The
earlier Qwen arm was invalidated after external service termination; none of its
rows were reused. The replacement ledger records 4,400 written and zero resumed
rows, while the infrastructure audit found zero provider infrastructure errors.

The two preregistered confirmatory tests both pass Holm correction. Structured
strict success was 71.625% versus 91.125% for Gold Oracle, an effect of -19.50
percentage points (family-bootstrap 95% CI [-23.625, -15.375];
Holm-adjusted p approximately 0.00010). Advisory checks improved strict success
by 3.625 points on average (95% CI [1.906, 5.438]; Holm-adjusted p approximately
0.00010). Secondary typing, provenance, interaction, endpoint, and subgroup
estimates remain outside the confirmatory multiplicity family.

## Remaining order of operations

1. Rebuild the manuscript and checklist, enforce the AAAI main-text page limit,
   and resolve all warnings or paper-to-artifact test failures.
2. Complete an independent post-results reviewer audit, including claim strength,
   model/domain heterogeneity, limitations, and related-work positioning.
3. Reconcile the reproducibility checklist with recorded hardware/software
   details and final AAAI-27 submission instructions.
4. Decide release licenses and archive immutable raw runs separately from Git;
   do not infer an open license from repository visibility.
5. Obtain and lock an independent recruited-human audit (without outcome-driven
   task repair) or explicitly accept agent-annotated construct validity as a
   major limitation.
