# HandoffBench confirmatory analysis contract v2

Status: pre-test amendment dated 2026-07-18. No candidate/test model output was
inspected before this amendment. Version 1 is retained for transparency but is
superseded because development evidence failed its EHC scaling gate. This file
must be sealed together with the final annotated split before confirmatory calls.

## Why the contract changed

On six development families across two models, EHC minus matched Structured was
-4.17 pp with a wide family-clustered interval. In a fair one-model development
factorial, advisory checks were positive, while provenance was not and the
provenance-by-checks interaction was negative. We therefore drop “all-on EHC is
superior” as the paper's method thesis. The confirmatory study targets the
benchmark construct and predeclared mechanism effects, retaining negative
effects rather than tuning the capsule on test.

## Confirmatory population and inference unit

- 200 independently authored task families, 40 in each of five domains, subject
  to double annotation, adjudication, rejection/replacement, overlap audit, and
  sealing before model calls.
- At least two model families. Model and seed observations are repeated measures
  nested within task family, never independent sample units.
- Every scheduled task--model--seed--condition cell is analyzed intent-to-treat.
  Provider/schema/parse failures remain in the denominator with zero strict
  success and state credit; raw calls and costs remain in release artifacts.

## Claims and endpoints

1. **Boundary regression exists.** For each non-oracle view, estimate the rate
   at which the same receiver succeeds with gold boundary state but fails under
   that view. Primary contrast: generated Structured versus Gold Oracle on
   strict success, paired within task/model/seed.
2. **Representation mechanisms have separable effects.** In the matched
   2x2x2 representation factorial, estimate typing, trace-linked provenance,
   advisory-check main effects and all interactions on strict success. The
   prespecified directional hypothesis is positive for advisory checks; typing
   and provenance are two-sided because development effects were uncertain or
   negative.
3. **Field loss predicts downstream regression.** Estimate the association
   between first-probe macro state F1/category errors and oracle-conditional
   regression, with task-family and model intercepts. This is diagnostic, not a
   claim that probe fidelity alone causally determines success.
4. **Legacy views remain descriptive controls.** Full History, Free Summary,
   Structured, all-on Capsule, and Gold Oracle are all reported. EHC versus
   Structured is a two-sided retained comparison; no superiority claim is made
   unless its corrected interval excludes zero in the favorable direction.

Strict end-to-end success is the primary endpoint. Macro state F1, episode-level
critical error, HIR, input/output tokens, calls, and validator cost are secondary.
Advisory representation and enforced action gating are never pooled.

## Tests and multiplicity

- Binary paired effects: family-cluster percentile-bootstrap 95% intervals;
  exact McNemar is a sensitivity analysis only because repeated model/seed rows
  are clustered.
- Continuous/count outcomes: family-cluster bootstrap intervals. Mixed models
  include task-family and model intercepts; convergence failures and fallbacks
  are disclosed.
- Confirmatory family: (i) Structured versus Oracle strict success and (ii)
  advisory-check factorial main effect on strict success. Two-sided p-values are
  Holm-adjusted; the directional checks prediction is supported only when the
  adjusted two-sided interval excludes zero positively.
- All other factor interactions, category/domain/model subgroups, and legacy
  view contrasts are reported with intervals and labeled secondary or
  exploratory. No subgroup is promoted after observing test outcomes.

## Power and stopping

The pre-test simulation grid is archived in `research/power_simulation_v1.*`.
At ICC .10, N=200 gives estimated power .847 for a +10 pp paired effect but only
.691 for +8 pp; null or imprecise results remain publishable benchmark findings.
The sample size cannot change in response to test significance. A task may be
rejected only during blinded human adjudication before sealing, never because of
model performance.

## Release and reporting contract

Release task/split/protocol hashes, anonymized independent annotations,
adjudication and agreement outputs, rejected-task reasons, prompts/schemas,
model snapshots, configuration/software hashes, every scheduled raw run, and
table-generation scripts. Report all models, conditions, denominators, failures,
cost components, intervals, and negative effects. Development and invalid
protocol directories are excluded by explicit manifests rather than by manual
table selection.
