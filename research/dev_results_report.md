# Development-only results report

Date: 2026-07-18. These results are prompt/task-development diagnostics. They
must not be presented as frozen-test or confirmatory evidence.

## Legacy transfer views

The counterfactual travel development set contains six independent workflow
families, each instantiated as unknown/granted/denied/stale variants. All
method comparisons use intent-to-treat denominators and family-clustered
bootstrap intervals.

Across Qwen2.5-14B and Ministral-3-14B (48 scheduled episodes per method), strict
success was 68.8% for EHC, 47.9% for free summary, 91.7% for full history,
75.0% for the matched structured payload, and 93.8% for the gold-state oracle.
EHC minus structured was -6.25 percentage points (family-clustered 95% CI
[-22.9, 12.5]). The unclustered McNemar sensitivity p-value was .5811. This is
a negative development result: it does not support a generic EHC advantage and
triggers the preregistered rule against scaling that method claim unchanged.

The large oracle gap for non-oracle views shows that transfer/utilization
regression exists in these development workflows, but six families cannot
estimate its population prevalence.

## Matched representation factorial

The valid Qwen2.5-14B and Ministral-3-14B runs schedule 48 task--model blocks ×
eight cells = 384 ITT cells (381 provider/parse-successful, three receiver
errors), grouped into six independent families. Each task/model/seed block
physically generated one source artifact and reused it across all eight cells.
The post-run fairness audit passed 48/48 blocks for source raw/output hash,
source prompt, response schema, seed, and source usage.

On strict success, the development main effects (high minus low) were:

| Factor | Effect | Family-clustered 95% CI |
|---|---:|---:|
| Typed serialization | +2.60 pp | [+0.52, +4.69] |
| Trace-linked provenance | -6.77 pp | [-15.63, +2.60] |
| Advisory executable checks | +6.77 pp | [+3.65, +9.38] |

The provenance × checks interaction was -4.69 pp [-10.42, -0.52]. Macro
state-F1 effects were small: typing +0.82 pp, provenance -0.70 pp, and checks
+0.34 pp. Provenance increased mean critical-error counts by 0.042 [0.010,
0.078] in this small development sample. Full combined estimates are in
`outputs/factorial_cf_v4_qwen_ministral/factorial_analysis.json`; the two input
directories and all 384 immutable runs remain listed in that artifact.

These estimates are exploratory because they use only six independent families,
despite spanning two model families.
They motivate a benchmark question---why advisory checks sometimes help while
extra provenance may distract the receiver---rather than a claim that all-on
capsules dominate structured payloads. The invalid predecessor run in
`outputs/factorial_cf_v1_qwen14b` remains marked `INVALID_PROTOCOL.md` and is
excluded from every estimate above.

## Confirmatory design implication

A pre-freeze planning simulation (1,000 replications and 1,000 family-bootstrap
draws per grid cell) indicates that 120 independent families are underpowered
for the originally targeted paired effect. At ICC .10 with two model repeats,
estimated power is .441 for +8 pp and .633 for +10 pp at N=120. At N=200 it is
.691 and .847, respectively. The candidate pool was therefore expanded before
human annotation or any candidate model call. These are design assumptions, not
observed test effects; the complete grid is in `research/power_simulation_v1.*`.
