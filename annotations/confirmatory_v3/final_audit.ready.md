# Confirmatory v3 final static audit

Status: **pass_unsealed**. No model/provider call was made.

## Hard gates

- PASS — `load_and_schema_200`
- PASS — `five_domains_x_40`
- PASS — `task_ids_unique`
- PASS — `families_unique`
- PASS — `exact_oracle_200`
- PASS — `unique_legal_terminal_without_phi_200`
- PASS — `provenance_200`
- PASS — `human_values_grounded_200`
- PASS — `irreversible_arguments_grounded_200`
- PASS — `public_arguments_valid_200`
- PASS — `impact_consistent_200`
- PASS — `gold_terminal_is_irreversible_200`
- PASS — `catalog_permutation_safe_200`
- PASS — `blind_surface_has_no_evaluator_keys`
- PASS — `no_internal_identity_or_trace_collision`
- PASS — `no_dev_identity_exact_or_trace_collision`
- PASS — `exact_copy_oracle_200`

## Recomputed diagnostics

- Tasks/domain counts: 200 / {'commerce': 40, 'it': 40, 'procurement': 40, 'scheduling': 40, 'travel': 40}.
- Unique legal terminal sequence without Phi: 200/200.
- Development normalized-topology flags: 69.
- Development lexical pairs at Jaccard >= .80: 0.
- Internal duplicate groups: `{'task_id': 0, 'family_id': 0, 'entity_pool': 0, 'exact_trace_hash': 0, 'normalized_trace_hash': 0, 'exact_action_graph_hash': 3, 'normalized_action_graph_hash': 5}`.
- Shallow success counts: `{'catalog_only': 14, 'predicate_only': 12, 'name_only': 61, 'exact_copy': 200}`.

Normalized topology, lexical similarity, internal action-graph reuse, and shallow-probe success are reported diagnostics rather than automatic rejection rules. Identity, exact/normalized trace, exact development graph, provenance, grounding, impact, executability, and uniqueness checks are fail-closed hard gates.
