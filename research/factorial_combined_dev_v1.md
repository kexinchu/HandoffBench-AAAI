# Two-model matched-factorial development audit

Date: 2026-07-18. Status: **development only; excluded from confirmation**.

Inputs are the immutable raw run trees
`outputs/factorial_cf_v2_qwen14b` and
`outputs/factorial_cf_v3_ministral3_14b`. The machine-readable joint analysis is
`outputs/factorial_cf_v4_qwen_ministral/factorial_analysis.json`.

## Integrity

- Models: Qwen2.5-14B-Instruct and Ministral-3-14B-Instruct-2512.
- Independent task families: 6; counterfactual episodes: 24 per model.
- Scheduled factorial cells: 384; provider/parse successful: 381; ITT errors: 3.
- Shared-source fairness: 48/48 task--model--seed blocks passed. Every eight-cell
  block has one identical source output, source prompt, response schema, and
  logical usage record.

## Strict-success effects

High-minus-low effect coding; percentile intervals resample the six task
families and carry both models and all counterfactual variants together.

| Term | Effect | Family-clustered 95% CI |
|---|---:|---:|
| Typing | +2.60 pp | [+0.52, +4.69] |
| Provenance | -6.77 pp | [-15.63, +2.60] |
| Advisory checks | +6.77 pp | [+3.65, +9.38] |
| Provenance × checks | -4.69 pp | [-10.42, -0.52] |

The remaining strict-success interactions are in the JSON artifact. Provenance
also changes mean critical-error count by +0.042 [0.010, 0.078]. These are
diagnostic signals, not population estimates: model repetitions do not turn six
families into a large independent sample. The results motivate the preregistered
confirmatory checks contrast and require retaining the null/harmful provenance
possibility.
