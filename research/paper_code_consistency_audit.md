# Paper-to-code consistency audit

Audit date: 2026-07-21. Scope: active files included by `paper/main.tex`
(`method.tex`, `benchmark.tex`, `evidence.tex`, and `ethics.tex`), their research
draft mirrors, evaluator/runtime code, sealed-v3 annotation/audit artifacts, and
development raw-analysis artifacts. This is a consistency audit, not a
confirmatory-results sign-off.

## Executive verdict

- **One definite paper error was fixed:** the precision equation used undefined
  `m_{ji}` after defining only `m_{ij}`. The text now defines directional gold-
  and prediction-relative overlaps (`r_{ij}`, `p_{ij}`), matching the code, and
  distinguishes weighted micro diagnostics from the unweighted field-macro
  headline. The identical change is in the active paper and research draft.
- Candidate counts, leakage diagnostics, overlap counts, development success
  counts, factorial effects/CIs, power values, ITT denominator, and source-reuse
  count are traceable to repository artifacts; no reported result was changed.
- Human-validation claims now trace to both locked agreement reports, both
  disagreement-only adjudications, the 39-task blind review, composite final
  agreement artifact, final static audit, and v3.1 seal. No confirmatory model
  result is claimed, and the execution config remains unauthorized.
- The four implementation blockers found in the initial audit were subsequently
  resolved: the headline scorer now filters primary claims, exact paired McNemar
  sensitivities are emitted, mixed models are explicitly optional
  post-confirmatory diagnostics, and missing `validator_cost` fails closed.

## Claim-level audit

| Paper claim / object | Implementation or raw evidence | Verdict |
|---|---|---|
| Episode formalism, fixed boundary trace, receiver-only view, deterministic terminal predicate | `models.py`, `runner.py`, and simulator records contain task, trace, boundary, roles, actions, gold state, and terminal checks. | Consistent. The mathematical tuple is a paper abstraction rather than a serialized class. |
| Primary semantic claims exclude executable preconditions and tool-event metadata | `dataset.primary_gold_claims` selects `PRIMARY_CATEGORIES` and excludes derived claims; `pilot_analysis.score_receiver_state` now consumes that projection explicitly. | Consistent; covered by a regression test containing an excluded precondition claim. |
| One-to-one matching within `(category,key)`; duplicate predictions are false positives | `state_metrics.score_state` groups by `(ClaimCategory,key)` and calls `maximum_weight_pairs`; `pilot_analysis` matches field-locally, while overlap is zero across unequal keys, yielding the same effective partition. Its precision denominator retains invalid/duplicate entries. | Consistent. |
| Directional set overlap and weighted recall/precision | `state_metrics._overlap_fraction` is directional; matching maximizes `gold weight × gold-relative overlap + category weight × prediction-relative overlap`. | **Definite paper formula bug fixed.** Previous `m_{ji}` was undefined. |
| Headline transfer fidelity is field-macro state F1 | `pilot_analysis.score_receiver_state`, lines 47–82, computes unweighted per-field precision/recall/F1 and averages populated gold fields. Raw development summaries store `macro_state_f1` from this path. | Consistent after wording fix distinguishing it from weighted micro diagnostics. |
| Strict success and HIR | Simulator supplies deterministic success; `confirmatory_analysis` computes strict success with error rows as zero and HIR only when oracle succeeds and target fails. | Consistent. |
| Representation-only `2×2×2` factorial | `_factor_levels` recognizes exactly typing, provenance, checks, all advisory; transfer rendering changes representation while preserving the source evidence. | Consistent. |
| Source called once and reused across eight cells; immutable hashes audited | Factorial raw runs share `source_hash`; the combined Qwen/Ministral analysis reports 48/48 fairness blocks passed. `confirmatory_analysis._audit_shared_sources` fail-closes on incomplete or unequal blocks. | Consistent and traceable. |
| Checks annotate but do not correct/quarantine; enforcement is separate | Transfer construction evaluates public predicates into statuses; primary factorial conditions end in `advisory`; confirmatory loader rejects non-advisory factorial cells. | Consistent. The separate enforced arm is designed/runtime-supported but not part of the current confirmatory analyzer output. |
| ITT keeps provider/schema/parse failures with zero success/state credit | `confirmatory_analysis._metric` returns zero success and state F1 for non-`ok` rows, and `load_and_validate` requires every scheduled cell. Combined development factorial retained 384 rows, including three errors. | Consistent. Raw calls/usages remain in run JSON. |
| Balanced factorial contrast `2 E[Y ∏x]` | `confirmatory_analysis.analyze` appends `2 * sign * metric` and averages across all balanced rows, including all interactions. | Consistent. |
| Family-cluster percentile bootstrap | `_cluster_ci` resamples family IDs and carries all rows belonging to each selected family. | Consistent for point estimates and CIs. |
| Holm-adjusted confirmatory tests | `_holm` is step-down monotone Holm adjustment; analyzer applies it to Structured-vs-Oracle and checks-main-effect family-level sign-flip p-values. | Consistent. The paper does not currently name sign-flip as the main p-value test; generated output does. |
| Exact McNemar sensitivity analyses | `confirmatory_analysis._exact_mcnemar_p` emits discordant counts and an exact two-sided binomial p-value for Structured-vs-Oracle and matched checks-on/off pairs. | Implemented and tested; correctly labeled sensitivity because repeated rows are clustered. |
| Mixed diagnostic models with family/model intercepts and fallbacks | They are not needed for either confirmatory contrast, interval, or multiplicity decision. | Paper now makes them optional post-confirmatory diagnostics, outside confirmatory evidence and multiplicity. |
| Tokens, calls, and validator cost are secondary endpoints; failure costs retained | Analyzer sums prompt/completion usage and counts raw calls. `validator_cost` must be explicitly present; absence raises `ValueError`. | Implemented fail-closed behavior and regression test. |
| Original human validation: 200 tasks/990 claims, claim F1 .9606, sequence agreement 174/200, category $\kappa=.9449$, criticality $\kappa=.2420$, 739 adjudication entries, 24 task rejects | `data/annotations/execution_v2/agreement_report.v2.json` and `data/annotations/adjudication_v2/adjudication_records.v2.json`. | Traceable; no unsupported agreement statistic is reported. |
| Agreement-only blind review: 39/39 rejects, comprising 34 ambiguous terminal actions, four ambiguous orders, and one unspecified terminal semantic | `data/annotations/blind_validity_review_v2/review.json` and `summary.md`. | Traceable; review scope and label isolation are disclosed. |
| Replacement validation: 63 tasks/299 claims, 47 criticality disagreements, criticality $\kappa=.6932$, zero rejects | `replacement_execution_v3/agreement_report.v1.json` and `replacement_adjudication_v3/adjudication_records.v1.json`. | Traceable; all 47 queued entries were adjudicated. |
| Final composition and seal: 137 retained originals plus 63 replacements, 200 families, five domains × 40, zero candidate-model calls | `annotations/confirmatory_v3/agreement.final.v2.json`, `final_audit.ready.json`, and `data/splits/confirmatory_v3.1.sealed.json`. | Consistent. Seal ID and canonical dataset hash match the manuscript and README. |
| Final static probes: exact oracle 200/200; catalog 14/200; predicate 12/200; oracle-sequence-plus-enum-first 61/200 with Wilson CI | `research/confirmatory_v3_leakage_overlap_audit.{md,json}` and bound final audit. | Traceable. The manuscript does not call the oracle-sequence diagnostic name-only. |
| Development normalized-topology flags: 69 final tasks; zero exact development identity/trace/action-graph or bigram-threshold collisions | `research/confirmatory_v3_leakage_overlap_audit.{md,json}`. | Traceable. The manuscript treats topology as diagnostic and makes no structural-holdout claim. |
| Legacy development results: Full 44/48, Free 23/48, Structured 36/48, EHC 33/48, Oracle 45/48; EHC–Structured −6.25 pp | `research/dev_results_report.md` and the combined two-model development analyses. | Traceable; explicitly development-only. |
| Factorial development: 384 ITT, 381 successful parses, effects +2.60/−6.77/+6.77 pp, provenance×checks −4.69 pp, critical-error +0.042 | `outputs/factorial_cf_v4_qwen_ministral/factorial_analysis.json` gives 384/381/3 and exact effects/CIs. | Traceable; both 24-block source audits pass, and invalid v1 is separately marked and excluded. |
| Power `.441/.633` at N=120 and `.691/.847` at N=200 | `research/power_simulation_v1.{md,json}` and `dev_results_report.md`. | Traceable and correctly labeled simulation/design input. |

## Resolved pre-confirmatory fixes

1. The production headline scorer consumes `primary_gold_claims(record)` and has
   a targeted non-primary-claim regression test.
2. The analyzer emits tested exact paired McNemar sensitivity results.
3. Mixed models are explicitly optional post-confirmatory diagnostics rather
   than an unimplemented confirmatory commitment.
4. Missing validator cost raises an error instead of becoming zero.
5. Double annotation, adjudication, blind review, replacement, final audit, and
   immutable sealing are complete. Confirmatory performance claims remain
   prohibited until the authorized preregistered execution and analysis finish.

## Patch record

The definite notation/metric-description bug and the subsequent blocker fixes
changed:

- `paper/sections/method.tex`
- `research/paper_section_method_draft.tex`
- `src/handoffbench/pilot_analysis.py`
- `src/handoffbench/confirmatory_analysis.py`
- targeted tests in `tests/test_pilot_analysis.py` and
  `tests/test_confirmatory_analysis.py`

No raw run, analysis output, table count, effect estimate, confidence interval,
or experimental result was modified.
