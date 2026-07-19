# Data layout

- `tasks/`: public task specifications and mocked tool worlds.
- `splits/`: immutable benchmark split manifests.
- `schemas/`: machine-readable task, trace, capsule, and result schemas.

Gold handoff state used for evaluation must not be included in prompts presented
to evaluated agents. Generated artifacts should record their generator version
and pass schema validation before use.

## Development pilot

`tasks/dev/pilot.json` is the labeled 30-task development pilot. It contains six
independent workflow families in each of five domains: travel, commerce,
procurement, IT, and scheduling. A record packages four fields:

- `episode`: evaluator-only labels conforming to `schemas/episode.schema.json`;
- `upstream_trace`: the frozen authenticated trace through `boundary.trace_cut`;
- `stressors`: controlled difficulty factors for stratified reporting; and
- `mock_tool_world`: deterministic initial state, tool responses, and scripted
  user replies.

The whole record is an authoring/evaluation artifact and must never be passed to
an evaluated target agent. Agent-visible views are derived by the runner and
exclude `gold_state`, action rules, scoring fields, and predicate arguments.

Load and audit the pilot with `handoffbench.dataset.load_tasks`, followed by
`validate_dev_pilot`. The loader validates every embedded episode with both the
Pydantic `Episode` model and the Draft 2020-12 JSON Schema, then rejects dangling
provenance, inconsistent trace cuts, undeclared predicate events, unknown
precondition keys, and malformed mock worlds. Terminal predicates use an exact
ordered event sequence and never require an LLM judge.

Every atomic claim's canonical `key` must equal the leaf of at least one cited
`provenance.field_path`. A genuinely derived claim may opt out only by declaring
`normalizer: "derived:<deterministic-rule>"`; an unexplained key/evidence mismatch
is rejected at load time.

## Atomic category routing

Categories are mutually exclusive labels for a claim's operational role at the
boundary. Annotators apply the first matching definition below after splitting
compound statements into atomic claims:

1. `goal`: the terminal outcome requested by the user.
2. `constraint`: a user-supplied restriction on acceptable outcomes.
3. `consent`: a scoped user decision authorizing an action, confirmation, or
   settlement; unknown consent is not an ordinary missing slot.
4. `policy_check`: an organization-controlled approval, clearance, eligibility
   gate, or policy adjudication, including pending/denied status.
5. `unresolved_slot`: a missing descriptive parameter or identity field whose
   value is neither user authorization nor organizational adjudication.
6. `verified_fact`: an authenticated business proposition established by a tool
   or other authoritative source. Tool-call execution metadata (arguments,
   success, volatility, retryability) remains in the trace and is not a competing
   semantic gold claim.
7. `tool_evidence`: reserved by the interchange schema for evidence artifacts,
   but not used for business propositions in this pilot or primary state F1.
8. `commitment`: whether an agent or organization has promised, initiated, or
   completed an action; this must cite an authenticated commitment event.
9. `risk`: a distinct hazard explicitly evidenced in the authenticated trace;
   never synthesize a generic “risk if unresolved” from another claim.
10. `precondition`: represented executablely by `ActionRule.when`, not repeated
    as a gold-state claim in this pilot.

The pilot does not target all schema categories. In particular, it contains no
standalone risk claim and no commitment claim because the original authenticated
traces do not establish independent hazards or explicit promises/denials. Honest
absence is preferable to template signals added for category balance.

Primary state F1 uses `primary_gold_claims`: independent base semantic claims
only. It excludes derived claims, executable preconditions, and tool-execution
metadata. Base claim keys are unique within an episode, preventing the same
semantic identity from receiving multiple category labels or weights.

`execute_events` evaluates each action against the state *before* that action,
enforces forbidden actions and `max_calls`, then applies any synchronous scripted
user reply. Thus an `ask` is legal while its slot is unknown, the mock reply can
change it to `known`, and an irreversible resolution action is legal only after
that transition. Merely emitting the expected action names in order is not
sufficient when a rule is violated.
