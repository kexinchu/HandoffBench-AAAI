# Claim-level collision audit: *Handoff Debt*

Audited source: Dipesh KC and Anjila Budathoki, *Handoff Debt: The
Rediscovery Cost When Coding Agents Take Over Interrupted Tasks*, arXiv:2606.02875v1,
1 June 2026. The local audit copy is `papers/handoff_debt.pdf`; this document
should be rechecked if a later version appears.

## What is already occupied

| Their claim/evidence | Overlap with the initial brief | Consequence |
|---|---|---|
| Formalizes predecessor/successor takeover at a deterministic checkpoint while holding repository state, predecessor trace, and successor fixed | Controlled handoff boundary and matched transfer conditions | Do not claim the first controlled handoff/takeover benchmark or that matched replay is novel |
| Converts 75 SWE-bench Verified tasks into 181 handoff points and 2,172 takeover runs | Benchmark construction with forced handoffs | Novelty cannot be “inserting handoffs into existing tasks” |
| Compares repository only, raw trace, free summary, and structured notes | Full/raw history, summary, structured payload baselines | Do not claim the first comparison of raw, summary, and structured handoffs |
| Structured notes contain deterministic and model-filled fields for changed files, validation evidence, uncertainty, rollback notes, and next action | Typed handoff capsule fields | Typing, boundedness, uncertainty, and auditability language alone are occupied |
| Reports official solve rate, agent events, prompt tokens, matched bootstrap intervals, and McNemar tests | Downstream success, duplicate effort, and context cost | Efficiency/reliability measurement alone is incremental |
| Finds context reduces events/tokens more consistently than solve-rate; notes may omit exact evidence or be over-trusted | Expected HandoffBench qualitative hypothesis | Do not present these observations as new without a different measurable construct |

## Defensible delta and required evidence

| HandoffBench delta | Absent from audited paper | Required experiment/artifact |
|---|---|---|
| Atomic, typed, hidden gold state at the boundary, including epistemic status (`known`, `unknown`, `contradicted`) | Handoff states are three repository-level outcome labels, not a gold semantic interface | Public schema, double annotation, deterministic typed matching, category-level precision/recall/contradiction |
| Policy- and transaction-critical categories: scoped consent, commitments, unresolved slots, and action preconditions | Coding schema has uncertainty/rollback/verification but no consent or executable action authority | Interactive mocked workflows with irreversible actions and explicit CHR/HCR/MPR metrics |
| Extraction → transport → utilization decomposition | Notes are generated and consumed end-to-end; generation and receiver use are not separately identified | Gold-extraction, lossless-transport, gold-state upper-bound, and no-information interventions |
| Provenance pointers validated against authenticated user/tool/policy events | Notes are historical evidence and include evidence text, but no field-level trace binding or integrity score | Trace-linked claims, provenance precision, controlled conflicting-evidence and corrupted-capsule tests |
| Executable precondition checks that can block illegal next actions | The successor is instructed to verify; no machine-executed boundary predicates | Checks-on/off intervention, missed-precondition outcomes, checks × irreversible/missing-consent interaction |
| Factorial mechanism identification beyond structured notes | No typing × provenance × checks factorial ablation | Same-information, approximately equal-token 2×2×2 design across tasks and at least two models |
| Handoff-induced regression conditional on gold-state oracle success | Solve-rate effects do not condition failure attribution on oracle transfer success | Paired oracle control and HIR metric separating transfer failure from ordinary reasoning failure |

## Gate decision

The project remains a conditional GO because the audited version does not expose atomic
gold boundary state, epistemic unknowns, scoped authority, field-level provenance, or
executable preconditions. It also does not decompose note extraction, transport, and
receiver utilization. The project becomes a main-track NO-GO if the proposed method
cannot beat an information-matched structured payload through provenance/check-specific
effects, because the remaining difference would mostly be domain substitution.

Safe positioning sentence:

> Prior takeover evaluation measures whether coding agents can resume and how much
> rediscovery they incur under different context views. We instead measure which
> task-critical semantic claims cross an inter-role control boundary, whether each is
> evidence-supported and action-authorizing, and which transfer errors cause downstream
> policy violations or regression.
