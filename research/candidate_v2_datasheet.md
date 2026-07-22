# HandoffBench Candidate v2 Datasheet

**Status:** synthetic candidate data; unannotated, unadjudicated, unsealed, and
not a frozen test split. This datasheet records repository-static facts only. It
does not report human validation, model evaluation, benchmark results, or fitness
for confirmatory use. The human annotation protocol is **not yet executed**.

## Motivation and intended research use

HandoffBench studies whether task-critical state survives a transfer of control
between specialized agents. Candidate v2 is an authoring pool for constructing a
future benchmark split after independent annotation, adjudication, leakage review,
overlap analysis, and sealing. It supports research on extraction, transport, and
utilization of boundary state; it is not evidence that any transfer method works.

## Composition

The repository currently contains 200 synthetic candidate families, 40 in each
of five domains:

| Domain | Candidate families | Candidate file |
|---|---:|---|
| travel | 40 | `data/tasks/candidate/travel_commerce.json` |
| commerce | 40 | `data/tasks/candidate/travel_commerce.json` |
| procurement | 40 | `data/tasks/candidate/procurement_it.json` |
| IT support | 40 | `data/tasks/candidate/procurement_it.json` |
| scheduling | 40 | `data/tasks/candidate/scheduling.json` |

Each candidate has a unique `template_family` and auditable workflow-automaton
identity. A record packages an evaluator-facing `Episode`, authenticated upstream
trace, controlled stressors, deterministic mock tools/user replies, and an
agent-visible public action contract. These are authoring records: evaluator
fields must never be placed in target-agent prompts or annotator packets.

The primary stressor vocabulary is `long_distractor`, `user_revision`,
`conflicting_evidence`, `missing_authority`, `multi_step_evidence`, and
`irreversible_action`. Static tests check presence and composition; they do not
establish human-perceived difficulty.

## Creation process

1. Authors specify an independent family blueprint: roles, boundary, causal trace,
   public alternatives, authority/epistemic stressor, legal sequence, and first
   user-impacting or irreversible action.
2. Deterministic generators instantiate concrete synthetic dates, money, status,
   scope, option attributes, opaque IDs, mock transitions, and seeded enum order.
3. Schema and static tests check unique IDs/keys, provenance references, action
   argument grounding, exact oracle execution, public-catalog alternatives,
   automaton hashes, placeholder absence, and shallow positional leakage.
4. A separate packet builder removes evaluator-only labels. Candidate packets—not
   source records—are the inputs to blinded annotation.
5. Independent human annotation, adjudication, rejection/regeneration, overlap
   audits, and sealing are future gates. None is implied by successful generation.

No language model was required to generate or validate the execution assets
described in this datasheet. Static oracle execution is deterministic code, not a
model result.

## Boundary-state ontology

Primary semantic claims use mutually exclusive operational roles:

- `goal`: terminal outcome requested by the user;
- `constraint`: user-supplied restriction on acceptable outcomes;
- `verified_fact`: authenticated business proposition established by a tool or
  other authoritative event;
- `unresolved_slot`: missing descriptive parameter or identity value;
- `consent`: scoped user authorization, confirmation, or acceptance;
- `policy_check`: organization-controlled approval, clearance, or adjudication;
- `commitment`: authenticated promise/initiation/completion, only when explicitly
  present in the source trace;
- `risk`: an independent trace-evidenced hazard, never a mechanical copy of an
  unresolved slot.

Executable preconditions belong in public `ActionRule.when` contracts and are not
duplicated into primary state F1. Tool-call execution metadata belongs in traces
for workflow metrics and does not compete with `verified_fact`. A claim belongs in
gold only when a counterfactual mutation can change a legal action or terminal
success. Candidate source labels are proposals until humans independently
reconstruct and adjudicate them.

## Sources, authorship, and licensing

All scenarios, entities, traces, mock tool outputs, policies, and values are
synthetic project-authored materials. They are not copied customer records,
transactions, medical records, support logs, or personal communications. Domain
patterns are generic workflow abstractions rather than representations of a named
company's private policy.

Project-authored synthetic benchmark data and annotation records are licensed
under CC BY 4.0; project-authored software is Apache-2.0. The manuscript, AAAI
author kit, model weights, and third-party materials remain outside those
grants. See the top-level license and third-party notice files before
redistribution.

## Personal data, safety, and risks

No real person is intentionally represented. Emails use reserved example-style
values and IDs are opaque synthetic identifiers. Nevertheless, free-text edits by
future annotators can accidentally introduce personal data; annotators must use
participant codes and must not paste real customer, credential, passport, payment,
health, or employment information. Coordinators must review exports for PII and
secrets before any release.

Tasks include payments, identity checks, accessibility, travel documents,
account actions, and other consequential workflows. They simplify real policies
and must not be used as operational guidance. Incorrect agents may appear to
authorize charges, account changes, refunds, or travel actions inside the mock
environment; this is simulated behavior only.

## Known limitations and leakage risks

- Public action names such as `ask_user`, `request_authority`, and
  `commit_resolution` can reveal action class or ordering. This is known
  action-name leakage even when opaque option position is balanced. It requires
  explicit human audit and stronger renamed-action controls before freezing.
- Synthetic phrasing and deterministic generators may introduce lexical or
  structural regularities. Current static positional checks do not rule out richer
  catalog-only, family-recognition, or predicate leakage.
- Forty families per domain is not evidence of real-world coverage. Domain
  policies are intentionally simplified and may omit jurisdictional variation.
- The proposed ontology and source labels have not yet been validated by human
  agreement. Candidate rejection is expected and must be reported.
- Static oracle success proves simulator consistency only; it is not an experiment
  result and does not establish task determinacy under human interpretation.

## Prohibited and out-of-scope uses

Do not use candidate v2 for production decisions, purchases, refunds, access
control, identity verification, medical/legal/financial advice, employee
assessment, surveillance, or decisions about real people. Do not market it as a
frozen benchmark, report candidate model scores as confirmatory results, train on
or publish hidden evaluator fields intended for a future split, or attempt to
reidentify annotators. Model inspection of a candidate makes that item development
data and disqualifies it from a future confirmatory split.

## Maintenance and versioning

Candidate versions are mutable authoring pools. Any semantic edit must update the
generator version, regenerate derived JSON/packets, rerun static tests, and create
new assignment assets. Existing annotation responses and manifests are immutable;
never overwrite them. Rejected candidates retain rejection reason and are replaced
before model evaluation. A future frozen release requires content/protocol hashes,
agreement and adjudication artifacts, overlap reports, rejected-task accounting,
and a non-overwritable sealed manifest.

Candidate v2 now has 200 label-free `candidate_packets_v2` packets and two blank,
independently ordered `assignments_v2` files with null responses. Blank response
skeletons and an unlocked lock-manifest template are execution scaffolding only:
they provide no human annotation or agreement evidence. `candidate_packets_v1`
and `assignments_v1` remain historical 120-task assets and must not be mixed into
the v2 execution or cited as v2 coverage.
