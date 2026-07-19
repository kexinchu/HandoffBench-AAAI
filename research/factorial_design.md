# Fair mechanism-identification design

## Estimand and confounds

The primary mechanism experiment is a representation-only 2x2x2 design:
typing (free-form/typed) x provenance (absent/trace-linked) x checks
(absent/executable). `executable` means that the framework evaluates the public
predicates and serializes the resulting status. It does not mean that the
framework blocks a receiver action. Action enforcement is a separate binary
intervention and is excluded from all representation-effect estimates.

This separation addresses three otherwise fatal confounds in the legacy EHC
comparison: EHC alone receives field-level evidence links, EHC alone receives a
validator that can quarantine claims, and EHC could receive a privileged gate.
The primary table therefore uses advisory enforcement in all eight cells. A
secondary table compares advisory versus enforced execution while holding the
all-on representation cell fixed. We never call the enforced arm an EHC
representation gain.

## Information- and budget-matched protocol

For every task/model/seed block, all eight source agents receive the identical
frozen upstream trace, identical public action predicates, and identical atomic
evidence records. They receive the same state-field vocabulary and no gold
claims, criticality labels, action rules, or evaluator feedback. Provenance-off
cells retain evidence atoms but omit trace bindings; checks-off cells retain the
public predicates as inputs but do not serialize evaluated statuses. Thus a
factor removes a representation capability, not source information.

All cells use the same source and receiver model snapshot, decoding parameters,
maximum output tokens, receiver action schema, tool catalog, maximum turns, and
tool-call budget. We record actual input/output tokens and latency. Prompts use
padded, predeclared envelopes (or an equal-token sensitivity run) so an all-on
cell cannot win merely because it receives a larger generation budget. Typed
and free-form cells expose the same ten semantic field names; free-form cells
render each field as prose inside a fixed envelope, while typed cells render the
same atoms as `{key,status,value}` records.

## Validation and receiver visibility

Every generated artifact is retained unchanged. Validators emit a sidecar audit
for every cell and never silently supply corrected values. For the primary
representation comparison, invalid provenance or checks are marked in the
sidecar and visibly annotated in the received artifact, rather than quarantining
claims only in provenance-on cells. We report both intent-to-transfer results
(raw artifact received) and protocol-valid subsets. A corruption challenge may
measure quarantine/blocking, but belongs to the secondary checkability analysis.

All receivers emit the same evaluation-facing typed state probe before acting;
this probe is not shown to the receiver again and does not repair its handoff.
The simulator, tools, and evaluator are method-blind.

## Cells and legacy labels

Cell IDs are `typing__provenance__checks`; enforcement is appended only to run
IDs. Legacy `free_summary` maps to `free_form__absent__absent`,
`structured_payload` to `typed__absent__absent`, and `ehc` to
`typed__trace_linked__executable`. Full history and gold oracle are controls
outside the factorial. Every legacy combination defaults to `advisory`; setting
`enforce_action_gates=true` creates a separately labelled enforced arm.

The remaining five factorial cells must have explicit serializations and frozen
prompts before test execution. Results from a partial cube cannot support main
effects or interactions.

## Analysis and reporting

Estimate all three main effects, all two-way interactions, and the three-way
interaction with episode-paired inference and task-family clustering. The
pre-specified mechanism probes are provenance x conflicting evidence and checks
x missing consent/irreversible action. Report strict success, state F1, critical
errors, provenance validity, check accuracy, and tokens for every cell. The
enforcement table reports prevented violations and false blocks, plus success;
it is descriptive/secondary and never pooled into the 2x2x2 model.
