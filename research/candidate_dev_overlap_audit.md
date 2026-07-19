# Candidate-vs-development overlap audit

Static audit only: no model was called, no candidate was modified, and this report does not seal a split.

- Candidate tasks: 200 across 3 files.
- Development tasks: 54 across 2 files.
- Lexical rule: Jaccard over normalized trace-content token bigrams; flag at Jaccard ≥ 0.80.
- Normalization: lowercase; replace dates, numeric/opaque-ID-like tokens; remove trace/task/boundary IDs.

## Exact/structural collisions

| Signal | Candidate tasks flagged | Pair groups |
|---|---:|---:|
| family_id | 0 | 0 |
| entity_pool | 0 | 0 |
| generator_seed | 0 | 0 |
| exact_trace_hash | 0 | 0 |
| normalized_trace_hash | 0 | 0 |
| exact_action_graph_hash | 0 | 0 |
| normalized_action_graph_hash | 69 | 552 |

## Lexical near duplicates

Pairs above threshold: 0.

| Candidate | Development | Jaccard |
|---|---|---:|

## Highest lexical similarities (including below threshold)

| Candidate | Development | Jaccard |
|---|---|---:|
| cand_scheduling_004 | dev_scheduling_26 | 0.167 |
| cand_scheduling_004 | dev_scheduling_28 | 0.050 |
| cand_scheduling_005 | cf_travel_03_denied | 0.050 |
| cand_scheduling_005 | cf_travel_03_granted | 0.050 |
| cand_scheduling_005 | cf_travel_03_unknown | 0.050 |
| cand_scheduling_005 | dev_travel_03 | 0.050 |
| cand_scheduling_006 | dev_scheduling_26 | 0.050 |
| cand_scheduling_006 | dev_scheduling_28 | 0.050 |
| cand_scheduling_007 | dev_scheduling_26 | 0.048 |
| cand_scheduling_007 | dev_scheduling_28 | 0.048 |
| cand_scheduling_009 | dev_scheduling_26 | 0.048 |
| cand_scheduling_009 | dev_scheduling_28 | 0.048 |
| cand_scheduling_010 | dev_commerce_10 | 0.048 |
| cand_scheduling_012 | dev_scheduling_26 | 0.048 |
| cand_scheduling_012 | dev_scheduling_28 | 0.048 |
| cand_scheduling_016 | dev_scheduling_26 | 0.048 |
| cand_scheduling_016 | dev_scheduling_28 | 0.048 |
| cand_scheduling_017 | dev_scheduling_26 | 0.048 |
| cand_scheduling_017 | dev_scheduling_28 | 0.048 |
| cand_scheduling_019 | dev_scheduling_26 | 0.048 |
| cand_scheduling_019 | dev_scheduling_28 | 0.048 |
| cand_scheduling_023 | dev_scheduling_26 | 0.048 |
| cand_scheduling_023 | dev_scheduling_28 | 0.048 |
| cand_scheduling_024 | dev_scheduling_26 | 0.048 |
| cand_scheduling_024 | dev_scheduling_28 | 0.048 |

## Limitations

- lexical similarity does not establish semantic or automaton equivalence
- normalization can over-collapse common schema vocabulary
- different wording can hide equivalent workflow logic
