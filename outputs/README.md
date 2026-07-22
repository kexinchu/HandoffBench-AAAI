# Output provenance

Each experiment directory must contain its resolved configuration, model and
prompt identifiers, task split hash, raw traces, per-task scores, aggregate
statistics, and software revision. Paper tables are generated from these
artifacts rather than manually transcribed.

The versioned confirmatory aggregates are under
`confirmatory_v3.4.1/analysis_v3.4.1/`. `confirmatory_results.json` contains the
formal ITT estimates, `main_tables.tex` is the analyzer-rendered table source,
and `provenance_manifest.public.json` is an anonymous, repo-relative derivative
of the private sealed manifest that hashes all 8,800 raw inputs plus the sealed
data, analysis code, and generated outputs. Raw run trees and service logs remain
excluded from Git and should be distributed as a separate immutable archive.
`confirmatory_v3.4.1/post_confirmatory_v1/` contains explicitly exploratory,
unadjusted model/domain subgroup diagnostics generated without modifying the
sealed confirmatory analyzer.

## Offline stage decomposition

Saved run JSON can be analyzed without changing or rerunning the model protocol:

```bash
PYTHONPATH=src python3.13 scripts/analyze_decomposition.py \
  outputs/METHOD_RUNS outputs/ORACLE_RUNS \
  --task-file data/tasks/dev/counterfactual_travel.json \
  --output outputs/decomposition.json \
  --reconstruct-checked-ehc
```

For `structured_payload` and parseable `ehc` source outputs, the report separates
source-vs-gold extraction fidelity from exact source-to-boundary-receiver
transport retention. Matching is one-to-one, so duplicated receiver claims are
false positives and cannot receive repeated credit. Optional EHC reconstruction
reports checker retention and quarantine plus transport from the checked state.

`free_summary` and `full_history` do not expose directly atomized source state;
their extraction and transport fields are JSON `null` with an explicit NA reason,
never zero. `utilization_ceiling` and `handoff_regret` require a run matched to a
`gold_oracle` by task, model, and seed.
