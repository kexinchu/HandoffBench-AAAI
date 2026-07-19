# HandoffBench confirmatory analysis contract v3

Status: final pre-freeze amendment dated 2026-07-18. No candidate/test model
output has been generated or inspected. Versions 1 and 2 remain archived. This
version supersedes v2 because the second planned development model and the
implementation audit completed after v2 was written. It must be sealed with the
adjudicated split before any confirmatory call.

## Amendment record

Across six development families and two model families, the legacy EHC minus
Structured effect is -6.25 percentage points, family-clustered 95% CI
[-22.9, 12.5]. In the matched 2x2x2 development factorial (384 ITT cells), the
strict-success effects are typing +2.60 pp [0.52, 4.69], provenance -6.77 pp
[-15.63, 2.60], advisory checks +6.77 pp [3.65, 9.38], and
provenance-by-checks -4.69 pp [-10.42, -0.52]. All 48 source-identity blocks
pass. These are development diagnostics over only six independent families.

The additional model does **not** change the v2 confirmatory family, sample
size, endpoints, stopping rule, or directional decision rule. It reinforces the
decision not to claim all-on EHC superiority and preserves the possibility that
provenance is null or harmful. This amendment also records that mixed models are
optional post-confirmatory diagnostics, not confirmatory evidence.

## Population and immutable execution unit

- 200 independently authored task families, 40 in each of travel, commerce,
  procurement, enterprise IT, and scheduling, conditional on blind double
  annotation, agreement measurement, adjudication, rejection/replacement,
  overlap/leakage remediation, and sealing before model calls.
- Two fixed model families: Qwen2.5-14B-Instruct and
  Ministral-3-14B-Instruct-2512, at the exact snapshots in the sealed model
  manifest; seeds 101 and 202.
- Task family is the independent inference unit. Model and seed rows are repeated
  measures nested within family.
- Every scheduled task--model--seed--condition row is intent-to-treat. Provider,
  schema, parse, or accounting failures remain with zero strict success and state
  credit; raw calls and costs remain in the release.

## Conditions and estimands

The representation experiment is typing (free-form envelope versus typed atoms)
x provenance (absent versus trace-linked) x checks (absent versus executable),
all advisory. Each task--model--seed block creates one immutable source artifact
and reuses it across all eight cells. A block is invalid if source output,
prompt, schema, usage, evidence, generation budget, or seed differs across cells.

Full History and Gold Oracle are required controls. Free Summary, Structured,
and all-on EHC remain reported legacy views where scheduled. Enforced all-on EHC
is a separate secondary intervention and is never pooled with advisory factorial
effects.

The primary endpoint is deterministic strict end-to-end success. Secondary
endpoints are first-probe unweighted field-macro state F1, episode-level critical
errors, oracle-conditional handoff-induced regression (HIR), input/output tokens,
calls, and explicit validator cost.

## Confirmatory family and decision rules

There are exactly two confirmatory tests:

1. Structured minus Gold Oracle strict success, paired within
   task--model--seed, estimates whether generated transfer induces boundary
   regression.
2. The advisory-check high-minus-low factorial main effect on strict success,
   averaged over typing and provenance within the same blocks.

Both use two-sided family-cluster percentile-bootstrap 95% intervals and
two-sided p-values adjusted together by Holm. The directional checks prediction
is supported only if its Holm-adjusted two-sided result excludes zero in the
positive direction. Exact paired McNemar tests are unclustered sensitivity
analyses and cannot override clustered inference.

Typing, provenance, every interaction, EHC versus Structured, enforcement,
category/domain/model slices, and failure taxonomies are secondary or
exploratory. Null and harmful findings remain reportable. No subgroup or endpoint
may be promoted after test inspection.

## Diagnostic association

The association between first-probe state errors and HIR may be summarized after
the confirmatory tables. Optional mixed diagnostic models may include family and
model intercepts, but they are not part of the confirmatory evidence or
multiplicity family. They are reported only with convergence diagnostics and a
predeclared simpler fallback; omission cannot change either primary conclusion.

## Sample size, stopping, and contamination

The archived fixed-seed simulation gives estimated power .847 for a +10 pp paired
effect and .691 for +8 pp at N=200 and ICC .10. These are design assumptions.
The accepted family count cannot change in response to significance. Candidate
tasks may be rejected only from blind human evidence before sealing, never from
model behavior. Any candidate model call, material task repair after sealing,
snapshot drift, missing scheduled cell, or unmanifested retry invalidates the
affected confirmatory execution and routes it outside the analysis root.

## Release contract

Release the sealed task/protocol/config/model/prompt/schema hashes; anonymized
independent annotations; agreement and adjudication artifacts; rejected-task
counts and reasons; all scheduled raw calls and ITT failures; explicit accounting;
and deterministic table-generation code. Development and invalid runs are
excluded by manifest rather than manual selection. The manuscript must label all
pre-seal results as development-only and must not imply human validation before
the corresponding locked artifacts exist.
