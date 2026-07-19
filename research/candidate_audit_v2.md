# Candidate-pool static audit v2

Audit date: 2026-07-18. Status: **candidate / unsealed / zero model calls**.
These numbers describe pre-annotation construction checks and are not paper
results.

## Composition

- 200 tasks and 200 unique `template_family` values.
- Five domains, exactly 40 tasks each: travel, commerce, procurement,
  enterprise IT, and scheduling.
- Primary stressors: long distractor 38, conflicting evidence 35, irreversible
  action 35, multi-step evidence 32, missing authority 30, and user revision 30.
- Gold categories: 471 verified facts, 200 goals, 109 constraints, 80 unresolved
  slots, 66 consent claims, 62 policy checks, and 2 authenticated commitments.
- 195/200 tasks contain a gold-path user-impacting action; the remaining five
  retain non-trivial evidence and action-selection requirements.

## Deterministic and leakage checks

- Exact gold action sequence succeeds on 200/200 tasks.
- Catalog-only success: 14/200 (7.0%).
- Predicate-only success: 12/200 (6.0%).
- Oracle action names plus enum-first guessing succeed on 69/200 (34.5%; Wilson
  95% CI [28.3%, 41.3%]), versus 13.9% expected under uniform enum guessing.
  This is combined name/interface-ordering leakage, not a pure action-name result.
- Exact-copy oracle success: 200/200 (100%).
- All 129 repository tests pass after expansion. Domain tests additionally
  check unique family/automaton identities, trace grounding, enum-position
  balance, wrong-enum and sequence mutation failure, placeholder removal, and
  absence of sealed/test markers.

## Human-audit boundary

The versioned export contains 200 evaluator-blind packets and a SHA-256 list at
`data/annotations/candidate_packets_v2.sha256`.  Both annotator assignment files
cover all 200 packets in independently shuffled order, bind packet hashes, and
contain null responses.  A third adjudicator has no preassigned tasks and may
see only disagreements after both independent annotations are locked.

The pool cannot be called a frozen test set until independent annotation,
agreement computation, adjudication, rejection/replacement, overlap audits, and
`freeze_split.py` sealing are complete.  No confirmatory model call is allowed
before those steps.
