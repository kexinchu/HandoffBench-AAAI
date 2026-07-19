# Leakage-resistant action interface

## Threat model

The original pilot encoded the oracle entity in names such as `book:F218` and
constructed the visible catalog from `allowed_next_actions`. A receiver could
therefore obtain high workflow accuracy without reconstructing the handoff:
choose the allowed actions in catalog order. This is target leakage, not agentic
state preservation.

We separate three objects:

1. **Public capability interface.** The receiver sees only generic JSON calls
   `{name, arguments}` and JSON-like argument signatures. A travel catalog
   contains `ask_user`, one domain operation (for example `book_flight`), and a
   legal non-terminal operation (for example `search_flights`). Candidate enums
   contain at least three plausible values and do not identify which is correct.
2. **Mock world.** Frozen trace evidence exposes business facts in the same way a
   real tool result would. Scripted user replies are keyed by complete generic
   invocations. The catalog is independently specified and deterministically
   permuted by task id, rather than projected from evaluator labels.
3. **Evaluator oracle.** `ActionRule.expected_arguments`, maximum calls,
   allowed/forbidden combinations, and the ordered terminal predicate never enter
   receiver prompts. They are used only after a call is emitted.

## Execution semantics

An invocation matches a rule only when both its generic name and its complete
argument object match. The state machine checks conditions in the pre-event
state, applies a scripted reply synchronously, and then evaluates later calls.
It records distinct violations for an unknown argument assignment
(`arguments:<name>`), an explicitly forbidden candidate (`forbidden:<name>`), a
missing state precondition (`precondition:<name>`), and excess calls
(`max_calls:<name>`). Success requires the evaluator-only invocation sequence,
absence of forbidden invocations, and no violations.

Legacy string events remain readable for the other 24 pilot examples during the
staged migration, but all six travel examples use invocation objects throughout.

## Prompt non-interference

The public serialization is tested not to contain `expected_arguments`, success
predicates, forbidden labels, or maximum-call labels. Stable task-keyed ordering
prevents catalog position from being a universal answer. Structured and EHC
source agents receive the same public policy-predicate input; EHC differs only in
its returned provenance/check structure. Runtime action enforcement is controlled
by the orthogonal `enforce_action_gates` configuration flag and is not tied to a
transfer method.

## Migrated travel slice

The six migrated calls are `book_flight(option_id)`,
`reserve_hotel(property_id)`, `book_rail(itinerary_id)`,
`reserve_car(vehicle_id)`, `hold_itinerary(itinerary_id)`, and
`purchase_addon(quote_id)`. Each task also uses `ask_user(slot)` with plausible
slot alternatives. Correct, wrong, and distractor identifiers share the same
signature, so action-name accuracy is insufficient.

## Counterfactual release challenge

`data/tasks/dev/counterfactual_travel.json` contains six families with four
variants apiece: unknown authorization requires ask then commit; granted scoped
authorization permits direct commit; denial requires a safe decline/alternative;
and stale/contradicted scope requires re-asking before commit. Within a family,
the public catalog, catalog ordering, action signatures, candidate enums, and
entities are byte-identical. Only trace evidence, gold boundary state, scripted
reply, and evaluator-only event sequence vary. First actions have a 2:1:1 label
distribution (`ask_user`, commit, decline), preventing a single catalog-derived
label from solving all four.

`scripts/leakage_baselines.py` reports executable success and exact-invocation
F1 for catalog-only, name-only, predicate-only, and exact-copy probes. On the
24-task challenge, catalog-only and predicate-only executable success are 0%,
while the exact-copy oracle is 100%; name-only is retained as a deliberately
strong diagnostic that receives oracle action names but must guess arguments.
All non-oracle probes canonicalize catalog content, so reversing transport order
does not change their prediction. Tests enforce catalog-only <=25%,
predicate-only <=35%, exact-copy 100%, and shuffle invariance.

## Tests

`tests/test_dataset.py` covers generic names, wrong options, arbitrary wrong
arguments, precondition ordering, duplicate calls, candidate decoys, prompt-label
exclusion, and non-gold catalog ordering. Harness tests cover multi-turn execution
and method-independent enforcement. The complete project test suite should remain
the release gate after every subsequent domain migration.
