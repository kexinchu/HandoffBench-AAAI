# Candidate v2 construct-validity static audit

Status: **candidate / unsealed / no model calls / no candidate edits**. This audit reports what repository mechanics can establish and what remains for independent humans.

## Findings

- Provenance field-path leaves exist for 200/200 tasks; source types match their events for 200/200.
- Required action arguments are present in authenticated traces for 200/200 tasks; 0 have a mechanically secret argument.
- The authored gold sequence is legal under action guards for 200/200 tasks. Only 137/200 have a unique legal terminal sequence when the evaluator predicate is withheld.
- 195/200 gold paths contain a public user-impacting action; public `user_impacting` names equal evaluator irreversible names for 199/200.
- Only 305/990 proposed claims have a direct syntactic counterfactual witness (guard-key reference or exact action-argument value). The remainder are not thereby invalid, but their minimal causal relevance is **not statically established** and must be reconstructed by annotators.
- 69/200 candidates share a normalized action-graph hash with development data. A normalized hash collision means the action-name/guard topology matches at least one development episode after identifier normalization. It is neither proof of semantic duplication nor evidence of independence; all 69 require human workflow review.

## By domain

| Domain | n | claims | syntactic witnesses | unique legal sequence | user-impacting | topology overlap |
|---|---:|---:|---:|---:|---:|---:|
| commerce | 40 | 223 | 77 | 35 | 40 | 24 |
| it | 40 | 176 | 40 | 5 | 38 | 0 |
| procurement | 40 | 189 | 40 | 17 | 37 | 0 |
| scheduling | 40 | 160 | 80 | 40 | 40 | 24 |
| travel | 40 | 242 | 68 | 40 | 40 | 21 |

## Category and epistemic semantics

- `commitment/known`: 2
- `consent/known`: 7
- `consent/unknown`: 59
- `constraint/contradicted`: 2
- `constraint/known`: 107
- `goal/known`: 200
- `policy_check/contradicted`: 3
- `policy_check/known`: 47
- `policy_check/unknown`: 12
- `unresolved_slot/contradicted`: 7
- `unresolved_slot/known`: 26
- `unresolved_slot/unknown`: 47
- `verified_fact/known`: 469
- `verified_fact/unknown`: 2

Mechanical semantic flags: 9. Unknown/contradicted claims are checked for null values; known consent is checked for Boolean scope decisions; commitments require authenticated provenance. These are review flags, not automatic invalidity judgments (e.g., a scoped consent may legitimately use a typed object). Passing shape checks does not substitute for human entailment or authority review.

- `cand_commerce_008` / `duplicate_capture`: `open_or_contradicted_value_not_null`
- `cand_commerce_008` / `pending_authorization`: `open_or_contradicted_value_not_null`
- `cand_commerce_033` / `closure_consent`: `known_consent_not_boolean`
- `cand_procurement_007` / `cancel_authorized`: `known_consent_not_boolean`
- `cand_procurement_011` / `requester_agreement`: `known_consent_not_boolean`
- `cand_procurement_019` / `owner_acceptance`: `known_consent_not_boolean`
- `cand_it_010` / `owner_approval`: `known_consent_not_boolean`
- `cand_it_014` / `work_wipe_consent`: `known_consent_not_boolean`
- `cand_it_036` / `manager_approval`: `known_consent_not_boolean`

## Construct-validity decision

The pool passes provenance existence, source-type, argument-grounding, and authored-path executability checks. It does **not** yet establish claim-level counterfactual minimality or uniqueness of the legal policy. Multiple clarification/authority actions often commute, while the terminal predicate selects one arbitrary order. Human annotators must reject or generalize tasks whose public contract admits multiple equally legal sequences, independently justify every claim, audit consent scope and authority precedence, and review all normalized topology overlaps before sealing. No agreement or frozen-test claim is warranted.
