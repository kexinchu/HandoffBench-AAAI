# Confirmatory v3 leakage and overlap audit

Status: **PASS — diagnostic, with no post-hoc filtering**. This was a read-only
static audit of the 200 confirmatory-v3 tasks. No model output was read, no
provider/model call was made, no task or configuration was changed, and no seal
was generated.

The stored final audit was recomputed in `--verify-only` mode and matched its
versioned JSON. Its status is `pass_unsealed`, and every declared hard gate
passes.

## Decision and threshold policy

The pool passes the leakage/overlap requirements that existed before this
audit. `preregistration_v3.md` and `annotation_protocol.md` require the static
leakage and overlap checks, but they do not specify a numeric rejection cutoff
for the full 200-task pool. The final-audit policy explicitly classifies shallow
probe success, normalized topology overlap, internal action-graph reuse, and
lexical flags as reported diagnostics rather than automatic rejection rules.

No threshold is invented after seeing these values, and no task should be
filtered using them. If a stricter leakage or topology cutoff is desired, it
must be introduced prospectively in a new versioned amendment and audit chain
before model calls.

The only existing numeric baseline thresholds in the repository apply to the
24-task development counterfactual challenge: catalog-only at most 25%,
predicate-only at most 35%, exact-copy exactly 100%, plus transport-order shuffle
invariance. Confirmatory v3's 7%, 6%, and 100% satisfy those values if they are
used as a nonbinding consistency reference. They are not retroactively promoted
to confirmatory-v3 preregistration criteria. No existing numeric threshold covers
the oracle-sequence diagnostic or normalized-topology flags.

PASS therefore means compliance with the existing pre-seal contract. It does
not mean that interface regularity is absent or that structural independence has
been proved.

## Shallow executable baselines

| Stratum | n | Catalog only | Predicate only | Oracle sequence + enum-first |
|---|---:|---:|---:|---:|
| Overall | 200 | 14 (7.0%) | 12 (6.0%) | 61 (30.5%) |
| Commerce | 40 | 5 | 5 | 13 |
| IT | 40 | 0 | 0 | 9 |
| Procurement | 40 | 0 | 0 | 11 |
| Scheduling | 40 | 2 | 0 | 14 |
| Travel | 40 | 7 | 7 | 14 |
| Sequence length 1 | 69 | 14 | 12 | 20 (29.0%) |
| Sequence length 2 | 131 | 0 | 0 | 41 (31.3%) |

Overall Wilson 95% intervals are 4.2%--11.4% for catalog-only,
3.5%--10.2% for predicate-only, and 24.5%--37.2% for oracle sequence plus
enum-first. Exact-copy succeeds on 200/200.

All 12 predicate-only successes are among the 14 catalog-only successes, and
all 14 catalog-only successes are among the 61 oracle-sequence successes. All
three methods succeed only on tasks for which every gold enum argument is at
index zero. Catalog-only and predicate-only success is confined to one-step
tasks.

### Why `name_only` is not name-only

The implementation label `name_only` is a misnomer. The probe reads the
evaluator-only, ordered oracle action-name sequence, including its length, and
only guesses arguments using `enum[0]`, `false`, or `unknown`. The accurate name
is **oracle sequence + enum-first**.

Its 61/200 result cannot establish that a receiver looking only at public action
names solves 30.5% of tasks. It measures the combined advantage of being handed
the correct workflow path and exploiting canonical argument ordering. Uniform
argument guessing expects 32.52/200 successes (16.26%); the observed result has
a Poisson-binomial upper-tail probability of (1.10\times10^{-7}). The contrast
is concentrated in two-step tasks: their observed rate is 31.3% versus a 10.0%
uniform expectation. For one-step tasks, the observed 29.0% is close to the
28.2% uniform expectation.

The existing `research/action_name_leakage_audit_v2.*` files and manuscript text
report 69/200 (34.5%) for the superseded candidate-v2 pool. They must not be
cited as the confirmatory-v3 result. Public v3 reporting must use 61/200 (30.5%)
and the accurate diagnostic name.

## Enum-position audit

| Scope | Enum fields/tasks | Index 0 | Index 1 | Index 2 |
|---|---:|---:|---:|---:|
| All gold enum fields | 377 fields | 185 | 91 | 101 |
| First-action enum fields | 231 fields | 134 | 52 | 45 |
| Terminal-action enum fields | 231 fields | 82 | 71 | 78 |
| Terminal primary argument | 200 tasks | 72 | 61 | 67 |

Terminal primary choices are approximately balanced overall and within each
domain:

| Domain | Index 0 | Index 1 | Index 2 |
|---|---:|---:|---:|
| Commerce | 15 | 11 | 14 |
| IT | 14 | 14 | 12 |
| Procurement | 15 | 10 | 15 |
| Scheduling | 14 | 13 | 13 |
| Travel | 14 | 13 | 13 |

However, first-action fields remain strongly skewed toward index zero, commonly
for clarification or authorization arguments. Among tasks whose terminal
primary argument is at index 0, catalog-only, predicate-only, and oracle-sequence
success are respectively 14/72, 12/72, and 61/72; each count is zero at terminal
indices 1 and 2. Terminal balance therefore does not eliminate whole-path
enum-first leakage.

## Catalog permutation and action positions

Catalog sizes range from three to eight:

| Size | Tasks |
|---:|---:|
| 3 | 37 |
| 4 | 78 |
| 5 | 22 |
| 6 | 24 |
| 7 | 24 |
| 8 | 15 |

The displayed positions of gold actions are:

| Position | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| First action | 34 | 41 | 48 | 42 | 19 | 6 | 7 | 3 |
| Terminal action | 39 | 50 | 52 | 22 | 21 | 6 | 9 | 1 |
| All 331 gold actions | 62 | 73 | 82 | 58 | 33 | 9 | 11 | 3 |

Using the task-size-conditional uniform expectation, descriptive chi-square
tests give (p=.173) for first positions and (p=.152) for all gold positions.
The terminal distribution gives (p=.049). This marginal terminal result is a
post-hoc diagnostic among several position summaries, was not preregistered,
and is not used as a rejection rule.

For 181/200 tasks, the gold name sequence is not an exact prefix of the displayed
catalog. A direct displayed-first-item plus enum-first heuristic succeeds on
4/200. Even a diagnostic additionally given the oracle sequence length and
allowed to emit that many displayed prefix items succeeds on only 8/200.

There is an implementation nuance: `catalog_only` first canonicalizes catalog
content by sorting it, so it is intentionally invariant to displayed transport
order and does not itself measure displayed-position leakage. Likewise, the
hard check named `catalog_permutation_safe` primarily verifies deterministic
reconstruction, public-name coverage, uniqueness, and absence of evaluator
keys; its self-recomputation equality is not a statistical balance test. The
position counts above are the separate balance diagnostic. Overall they support
the narrower claim that no universal first-position answer exists, not a claim
of perfect positional balance.

## Candidate--development overlap

| Signal | Confirmatory tasks flagged |
|---|---:|
| Family ID | 0 |
| Entity pool | 0 |
| Generator seed | 0 |
| Exact trace hash | 0 |
| Normalized trace hash | 0 |
| Exact action-graph hash | 0 |
| Normalized action-graph hash | 69 |
| Lexical bigram Jaccard at least 0.80 | 0 |

All 69 normalized-topology flags are two-step tasks. They are concentrated in
travel (21), commerce (24), and scheduling (24), with none in IT or procurement.
The normalization erases action names, keys, and concrete values, so common
abstract ask/authorize/commit skeletons can collide. This is not evidence of
semantic duplication, but the concentration prevents a claim of complete
structural holdout.

## Internal overlap

There are no duplicate task IDs, family IDs, entity pools, exact traces, or
normalized traces. There are three exact action-graph duplicate groups, covering
six tasks:

- `cand_commerce_015` and `cand_travel_015`
- `cand_commerce_037` and `cand_travel_037`
- `cand_commerce_034` and `cand_travel_034`

Five normalized action-graph groups have sizes 22, 9, 21, 16, and 69. Together
they cover 137 tasks; the remaining 63 tasks are normalized-topology singletons.
The release may accurately state that it has 200 unique family labels and trace
identities. It must not describe them as 200 unique action graphs.

## Required transparent reporting

Before public release:

1. Report 14/200 catalog-only, 12/200 predicate-only, 200/200 exact-copy, and
   61/200 oracle sequence plus enum-first success.
2. Include the domain and sequence-length concentration of shallow successes
   and normalized-topology flags.
3. Describe normalized topology as an abstract-graph diagnostic, not semantic
   identity, and avoid claiming a structural holdout.
4. Replace the candidate-v2 69/200 and 34.5% values currently present in the
   manuscript when discussing confirmatory v3.
5. Do not filter or repair tasks based on these observed diagnostics.

One nonblocking implementation note remains: `freeze_split.py` binds the final
audit byte hash but does not itself assert the final-audit status or every hard
check. The bound audit currently recomputes as PASS; a fail-closed content check
would strengthen future sealing safety without changing tasks or thresholds.
