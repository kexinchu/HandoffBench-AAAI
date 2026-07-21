# Blind construct-validity review: designated candidate-v2 replacements

## Scope and isolation

An independent reviewer examined exactly the 39 designated label-free packets using only `trace_cut` evidence, the public action contract, deterministic tool semantics, scripted transitions, and the three allowed protocol/data guides. The reviewer did not inspect source Episodes, evaluator gold, model or development outputs, remediation/audit queues, A/B annotations, or adjudication results.

The decision rule was conservative: a task is accepted only when public evidence proves one unique minimum legal terminal sequence, every user-impacting argument is visible or deterministically inferable, and terminal success is explicitly supported. Action list order and action names were not treated as gold evidence.

## Result

| Metric | Count |
|---|---:|
| Packets reviewed | 39 |
| ACCEPT | 0 |
| REJECT | 39 |
| Unique legal terminal sequence | 0 |
| Irreversible arguments inferable | 39 |
| Enumerated legal sequence candidates | 124 |

Resolution-code counts:

| Resolution code | Count |
|---|---:|
| `REJECT_AMBIGUOUS_SEQUENCE_ORDER` | 4 |
| `REJECT_AMBIGUOUS_TERMINAL_ACTION` | 34 |
| `REJECT_TERMINAL_SEMANTICS_UNSPECIFIED` | 1 |

The four sequence-order failures have two independent, simultaneously enabled state-repair actions whose scripted updates commute. The 34 terminal-action failures either expose four actions under the same already-satisfied precondition or expose one deterministic slot-closing action followed by three actions under the same precondition; their contracts provide no effects or terminal predicate that distinguishes the continuation. The remaining packet has one precondition-satisfying candidate path, but successful termination can only be inferred from the action name because no public terminal effect or predicate is declared.

All 39 packets expose enough public information to identify the compatible enum argument for user-impacting actions. This does not cure action or terminal ambiguity.

## Integrity and validation

- `review.json` SHA-256: `a86c755a45aa60e3bf8d8a4923893df4bd5557c5f703d85904487b0473880132`
- Ordered input-packet SHA-256-manifest digest: `23c2a0bc0d92dd5f817f56a7d78c567e265a2aaa4ccc820bdaad1a74b51e544d`
- Structural validation: 39 expected task IDs in the designated order, 39 decisions, and 124 sequences.
- Executability validation: every recorded action exists in its packet, every argument is in the public enum, every precondition holds at that step, and every scripted state update was applied before checking the next action.

## Recommendation

Do not use these 39 packets as replacements for sealing. Regenerate them with public, deterministic action effects and an explicit terminal predicate. For multi-slot cases, add a public dependency that fixes the necessary order, or explicitly define order-equivalent sequences as equivalent rather than requiring exact sequence identity.
