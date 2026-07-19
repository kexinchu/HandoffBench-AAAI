# HandoffBench confirmatory analysis contract (v1; superseded pre-test)

This version is retained as an audit trail. It was superseded on 2026-07-18 by
`preregistration_v2.md` after development results triggered the EHC stop/go
rule, and v2 was later superseded by the final pre-freeze
`preregistration_v3.md` after the second development model and implementation
audit completed. No candidate/test model output had been inspected.

This contract is frozen before inspecting test outcomes. The development pilot
may alter prompts, schemas, or task logic; every such change increments the
benchmark version and invalidates previous pilot evidence.

## Claims and endpoints

- C1: common transfer views induce regression after controlling upstream trace,
  target model, tools, budget, and seed. Endpoint: strict success conditional on
  gold-state-oracle success (HIR).
- C2: EHC improves strict success over an information-matched structured payload
  and lowers critical consent/commitment/precondition errors relative to free
  summary.
- C3 is tested only if EHC is non-inferior to full history at a -3 percentage
  point margin and reduces median input tokens by at least 30%.

The primary outcome is strict end-to-end success: all terminal predicates pass
and no forbidden action occurs. Key secondary outcomes are macro state F1,
episode-level critical-error rate, and input tokens.

## Confirmatory contrasts

1. EHC minus structured payload on strict success: target absolute improvement
   at least 8 points with task-family-clustered 95% CI lower bound above zero.
2. EHC versus free summary on critical errors: relative reduction at least 30%
   and absolute reduction at least 5 points.
3. EHC versus full history: one-sided non-inferiority margin -3 points, followed
   by token superiority only if non-inferiority passes.

The first two superiority hypotheses use Holm correction. Binary paired effects
use task-family cluster bootstrap intervals and exact McNemar tests as a
secondary check. Seeds are repeated measurements, not independent tasks.

## Stop/go rules

- Stop before model calls if fewer than 95% of pilot episodes pass evaluator
  mutation and schema tests.
- Do not scale if the development pilot shows neither a 5-point EHC advantage
  over structured payload nor a clear critical-error reduction.
- Do not claim a provenance-aware/executable method contribution if the
  provenance and checks factors show neither a main effect nor their predicted
  stressor interaction.
- Never increase test sample size in response to observed test significance.

## Reporting

Report all methods, models, task families, exclusions, provider failures, prompt
hashes, task hashes, costs, confidence intervals, and negative effects. Tables
are generated from immutable per-run outputs. Exploratory subgroup findings are
labeled as such.
