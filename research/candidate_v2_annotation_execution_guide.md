# Candidate v2 Annotation Execution Guide

**Procedure status:** planned and not yet executed. This guide supplements
`research/annotation_protocol.md`; the protocol controls if wording conflicts.
Following the steps below creates independent candidate annotations, not frozen
gold. No annotator may inspect model outputs or evaluator-facing candidate JSON.

## 1. Inputs and role separation

Each independent annotator receives only:

1. their own randomized assignment file;
2. the referenced label-free packet containing boundary roles, authenticated
   trace, public action contract, deterministic tool semantics, and scripted
   responses;
3. `data/annotations/annotation_template.csv`; and
4. the annotation protocol and this guide.

Do not provide the other annotator's order/responses, family blueprint, source
`Episode`, `gold_state`, allowed/forbidden labels, expected sequence, success
predicate, scoring weights, model outputs, or development results. Use only the
assigned participant code; do not enter names or contact details in CSV files.

The coordinator may use `research/human_remediation_queue_v2.csv` to schedule
work and identify which generic blind checks need special attention. **Do not
give that coordinator queue or its risk codes to either independent annotator.**
Annotators receive only their ordinary randomized assignment and packet, so
static audit findings cannot become label hints. A separate remediation reviewer
receives only the referenced blind packet and generic operation, never the source
audit, evaluator record, or a proposed answer.

The versioned `candidate_packets_v2` and `assignments_v2` assets cover 200 tasks;
their assignment responses are still null.  Generate annotator-specific working
skeletons without overwriting any directory:

```bash
PYTHONPATH=src python3.13 scripts/prepare_annotation_execution.py \
  --assignments-dir data/annotations/assignments_v2 \
  --output-dir data/annotations/execution_v2_blank
```

Each skeleton contains 200 task records, empty `claims` and
`claim_continuation_rows`, a null `action_sequence`, and `response=null`.  These
are workbooks, not annotations.  `assignments_v1` remains a historical 120-task
asset and must not be mixed into v2.

## 2. Work one packet at a time

Verify the packet filename, internal `task_id`, assignment `packet_sha256`, and
boundary `trace_cut`. Read the trace only through that cut. Treat later scripted
responses as reachable future transitions, not facts already known at the
boundary. Public action `requires` fields are operational contracts, not gold
claim suggestions.

Before writing claims, independently derive the smallest legal next-action
sequence:

1. enumerate at least three public alternatives where available;
2. evaluate each public precondition using authenticated boundary evidence;
3. identify any clarification, consent, or authority transition and its scripted
   state update;
4. write exact action names and JSON arguments in order; and
5. mark the first user-impacting/irreversible action and verify every argument is
   inferable from visible evidence.

If two sequences remain equally legal, an argument is secret, or public semantics
are insufficient, flag the task for rejection. Do not guess and do not consult a
task author for the answer.

## 3. Fill the task-level row

Create exactly one row with `record_type=task`:

- `task_id`, `annotator_id`: assigned values;
- `action_sequence_json`: a valid JSON array such as
  `[{"name":"ask_user_1","arguments":{"key":"fee_consent"}}, ...]`;
- `irreversible_args_inferable`: `true` only if all such arguments have exact
  visible support, otherwise `false` and explain in `notes`;
- `catalog_leakage_flag`: `true` if action name/order, enum position, public
  requirement wording, or another shallow cue reveals the sequence without
  reasoning over trace evidence;
- `notes`: ambiguity/rejection rationale only, with no personal information.

Leave claim/provenance columns empty on the task row. Preserve JSON types: strings
are quoted, booleans are lowercase JSON, and no Python literals are allowed.

## 4. Reconstruct atomic claims

Add one `record_type=claim` row per unique canonical `claim_key`. Split compound
facts. Do not create separate claims for tool metadata or copy a consent/policy
slot into a derived precondition/risk claim.

For every claim fill:

- `category`: apply the ontology in the datasheet and `data/README.md`; user
  authorization is `consent`, organizational authority is `policy_check`, and an
  ordinary missing parameter is `unresolved_slot`;
- `status`: exactly `known`, `unknown`, `contradicted`, or `not_applicable`;
- `value_json`: canonical JSON. Use `null` for unknown, retain both incompatible
  observations in provenance for contradicted status, and never close an unknown
  from the task's future scripted reply;
- `criticality`: `terminal`, `safety`, `efficiency`, or `context`;
- `task_critical`: whether changing/removing it can alter a legal action or
  terminal success;
- `inclusion_rationale`: the specific counterfactual difference;
- `mutation_changes_action`: `true` only when the proposed mutation changes a
  public rule truth value, action argument, order, or terminal result.

Exclude memorable but noncausal detail. A task may have multiple claims in one
category and must usually have multiple claims overall; never compress goal,
constraint, evidence, and authority into a single prose record.

## 5. Record one or more provenance pointers

The template stores one provenance pointer per row. Put the first pointer on the
`claim` row. For each additional supporting or contradicting pointer, add a
`record_type=provenance` row repeating `task_id`, `annotator_id`, `claim_key`,
`category`, `status`, and `value_json`, then fill:

- exact `trace_id`;
- `source_type` exactly as shown in the event; and
- dot-separated `field_path`, normally `content.<claim_key>`.

The field-path leaf must match `claim_key` unless the annotation format later
adds a preregistered deterministic derivation rule. Cite the authoritative event,
not the packet description or public action catalog. For a contradiction, cite
every conflicting event needed to reproduce the status and explain authority or
unresolved precedence in `notes`.

## 6. Self-check before submission

Confirm all of the following without viewing another annotation:

- one task row and at least one atomic claim row exist for every assigned task;
- claim keys are unique after grouping provenance continuation rows;
- every claim has at least one exact provenance pointer;
- values parse as JSON and status/value combinations are coherent;
- the action sequence uses only public actions with exact inferable arguments;
- simulated clarification/consent/approval updates occur before irreversible use;
- the counterfactual rationale is concrete for every included claim;
- known action-name leakage is flagged rather than silently normalized; and
- no model output, evaluator label, real PII, secret, or other annotator content
  appears in the export.

Mechanical validation failure returns the file to the same annotator for format
repair only. Coordinators must not suggest semantic answers.

## 7. Lock and submit independently

Export UTF-8 CSV with the original header and stable row order. Compute SHA-256
of the completed file and submit it through the coordinator's access-controlled
channel. The coordinator records annotator code, assignment manifest hash,
response hash, receipt time, template version, and packet-set hash, then marks the
response locked. The annotator receives a hash receipt but not the other response.

Never overwrite a locked response. A permitted correction is a new versioned
file with a new hash and documented reason; both versions remain retained. Both
independent responses must be locked before any comparison or disagreement queue
is created.

For JSON skeletons, provenance continuation rows are a drafting convenience.
Before locking, normalize them into the corresponding claim's `provenance` array,
set nonempty `claims` and `action_sequence` for every task, fill the inferability
and leakage decisions, change each task's `response` to `complete`, and set the
top-level status to `completed_unlocked`.  The agreement analyzer deliberately
rejects null responses, empty claims/sequences, and unlocked inputs.

Copy `lock_manifest.template.json` to a new versioned path only after both exports
are complete. Replace both paths, SHA-256 nulls, and `locked_at` nulls; verify
annotator IDs and exact 200-task coverage; then set `locked=true` and status
`locked`. Never modify the completed files after hashing.

## 8. Disagreement-only adjudication

The coordinator compares locked exports with deterministic one-to-one matching
and creates a third-person queue containing only disagreements in claim identity,
category/status/value, provenance, criticality, action sequence, inferability, or
leakage flag. Agreement-only tasks are not assigned to the adjudicator. The third
person sees both locked records and the same packet, records a resolution code or
rejects the candidate, and may not inspect model runs.

Completion of adjudication still does not freeze candidate v2. Agreement reports,
rejections/regeneration, overlap/leakage audits, final schema/oracle checks, version
hashes, licensing decision, and the non-overwritable sealing procedure remain
separate required gates.

Run the disagreement-only preflight with:

```bash
PYTHONPATH=src python3.13 scripts/generate_disagreement_queue.py \
  annotator_a_responses.completed.json annotator_b_responses.completed.json \
  --lock-manifest lock_manifest.locked.json \
  --output disagreement_queue.v2.json
```

The command refuses existing outputs and fails before writing when the manifest
is unlocked, a hash differs, an annotation is blank/incomplete, annotator IDs are
not independent, or double coverage is not exact. It emits only disagreement
records; an empty queue is valid only after the same completed/locked preflight.
