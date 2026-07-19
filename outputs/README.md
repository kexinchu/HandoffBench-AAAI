# Output provenance

Each experiment directory must contain its resolved configuration, model and
prompt identifiers, task split hash, raw traces, per-task scores, aggregate
statistics, and software revision. Paper tables are generated from these
artifacts rather than manually transcribed.

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
