# Frozen-test gold annotation and adjudication protocol

Status: preregistered procedure; **not yet executed**. Candidate tasks cannot be
called frozen test data until this protocol is completed and the resulting
manifest is sealed.

The concrete candidate-v2 packet, CSV, provenance-continuation, locking, and
submission steps are specified in `candidate_v2_annotation_execution_guide.md`.
That guide supplements but does not relax this protocol. Existing v1 packets and
assignments cover 120 historical candidates, not the current 200-task v2 pool.

## Blinding and roles

Two annotators independently review every candidate family. They receive the
authenticated upstream trace, boundary roles, public action contract, and mock
tool semantics, but no model outputs, transfer-method labels, development
results, evaluator gold, or task-family expected sequence. A third person
adjudicates disagreements. Task authors may explain schema mechanics but may not
serve as both independent annotators for a task they authored.

## Independent annotation

For each boundary, each annotator first writes the legal next-action sequence
from the public evidence. They then enumerate the smallest evidence-grounded
claims needed to distinguish that sequence from plausible alternatives. Each
claim receives:

- canonical key, category, epistemic status, typed value, and criticality;
- one or more exact `(trace_id, source_type, field_path)` provenance pointers;
- a binary task-critical judgment and short inclusion rationale;
- whether omission, mutation, or contradiction changes a legal action;
- whether scope/authority is explicit, absent, stale, or contradicted.

Annotators also record whether every irreversible action argument is inferable
from visible evidence, whether at least two public alternatives remain
plausible before reading the state, and whether public catalog order, names,
enums, or predicates reveal the evaluator sequence.

## Mechanical pre-adjudication checks

The annotation export must pass schema validation, unique-key validation,
provenance-leaf validation, exact gold-sequence execution, catalog permutation,
and catalog-only/predicate-only leakage baselines. A task with a secret required
argument, ambiguous terminal predicate, or non-executable oracle is rejected,
not repaired after model evaluation.

## Agreement and adjudication

Before adjudication, report claim-level precision/recall/F1 under one-to-one
matching, category and status agreement, typed-value exact agreement,
provenance-pointer F1, criticality agreement, and exact action-sequence
agreement. Cohen's kappa is reported for category, status, and criticality only
when both annotators use at least two labels; raw agreement and denominators are
always retained. Agreement is clustered by independent task family rather than
counting claims as independent samples.

The adjudicator sees both annotations and the trace, records one resolution code
per disagreement, and may reject the task. No model run may be inspected during
adjudication. Material changes after any confirmatory model call invalidate the
split and require a new versioned freeze.

## Release artifacts

The release includes anonymized independent annotations, adjudication records,
agreement scripts and outputs, rejected-task counts and reasons, final task and
protocol hashes, model/config/prompt hashes, and the sealed split manifest.
