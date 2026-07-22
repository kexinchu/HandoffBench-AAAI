# HandoffBench

HandoffBench is a research codebase for measuring whether task-critical state
survives a transfer of control between LLM agents. It fixes an authenticated
upstream trace and handoff boundary, then evaluates alternative receiver views
with deterministic state probes, tool simulators, and terminal predicates.

The accompanying manuscript is **State Is the Interface: Evaluating Handoff
Fidelity in Multi-Agent LLM Workflows**.

> Research status: the synthetic 200-family split was independently
> agent-annotated, adjudicated, statically audited, and sealed
> before candidate-model evaluation. The project-local, pre-execution-sealed
> 8,800-cell confirmatory
> matrix and v3.4.1 replacement audit are complete. Formal results distinguish
> the two Holm-controlled confirmatory tests from unadjusted secondary analyses.

## What is implemented

- Typed atomic boundary state with epistemic status and trace provenance.
- Deterministic task loading, schema validation, mock tools, policy guards, and
  exact terminal predicates.
- Full History, Free Summary, Structured Payload, Gold Oracle, and Executable
  Handoff Capsule views.
- A matched `2 x 2 x 2` representation factorial over typing, provenance, and
  advisory executable checks.
- State precision/recall/F1, strict task success, critical-error accounting,
  handoff-induced regression, cost accounting, family bootstrap intervals,
  Holm correction, and McNemar sensitivity analyses.
- Blind annotation packets, independent assignments, response locking,
  agreement analysis, disagreement-only adjudication, and fail-closed sealing.
- An AAAI-27 anonymous manuscript and conservative reproducibility-checklist
  draft.

## Repository layout

```text
configs/     Development and confirmatory design manifests
data/        Schemas, development tasks, candidates, and blind annotation assets
paper/       AAAI-27 manuscript source and author-kit files
research/    Preregistration, audits, protocols, and development reports
scripts/     Dataset, experiment, annotation, analysis, and build entry points
src/         Installable handoffbench Python package
tests/       Unit, integrity, fail-closed, and paper-to-artifact tests
outputs/     Small aggregate development results used by the manuscript
```

Raw model traces and third-party paper PDFs are intentionally excluded from the
Git repository. Aggregate development and confirmatory artifacts include their
input provenance; `make anonymous-supplement` packages the immutable raw runs as
a separate, audited submission artifact.

## Installation

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,analysis]'
```

Run the full offline verification suite:

```bash
make submission
```

This checks the Python environment, runs all tests, rebuilds the table-source
manifest, compiles the AAAI paper and standalone checklist, and rejects undefined
references, LaTeX warnings, and overfull boxes. It makes no provider or model
call.

For a test-only run:

```bash
PYTHONPATH=src python -m pytest
```

## Reproducing development analyses

The paper's current numerical results are development diagnostics over six
independent counterfactual workflow families and two model families. Relevant
machine-readable aggregates are:

- `outputs/cf_combined_v2_qwen_ministral/counterfactual_analysis.json`
- `outputs/factorial_cf_v2_qwen14b/factorial_analysis.json`
- `outputs/factorial_cf_v3_ministral3_14b/factorial_analysis.json`
- `outputs/factorial_cf_v4_qwen_ministral/factorial_analysis.json`

To combine immutable factorial run directories when raw runs are available:

```bash
PYTHONPATH=src python scripts/analyze_factorial.py \
  outputs/factorial_cf_v2_qwen14b \
  outputs/factorial_cf_v3_ministral3_14b \
  --output outputs/factorial_cf_v4_qwen_ministral/factorial_analysis.json
```

The analyzer rejects duplicate scheduled cells and audits that all eight cells
within each task/model/seed block reuse the same source artifact, prompt, schema,
and logical usage record.

## Sealed split and confirmatory execution

Every original candidate was independently double-annotated from a label-free
packet and locked before comparison. Disagreement-only adjudication rejected 24
tasks. A separate blind validity review rejected another 39 agreement-only tasks
with static sequence or terminal-semantics risks. All 63 exclusions were replaced
by newly generated families and independently double-annotated again. The second
round produced 47 criticality disagreements, all adjudicated, with zero rejected
replacements. The final split therefore contains 137 retained originals and 63
replacements, with 40 families in each of five domains.

Authoritative sealed artifacts are:

- `data/splits/confirmatory_v3.1.sealed.json`
- `annotations/confirmatory_v3/agreement.final.v2.json`
- `annotations/confirmatory_v3/final_audit.ready.json`
- `research/confirmatory_v3_leakage_overlap_audit.{json,md}`

Annotation provenance correction:

- `research/annotation_provenance_correction_v1.{json,md}`

The A/B labels and disagreement adjudication were produced by isolated LLM-agent
roles, not recruited human annotators. The original sealed agreement artifact's
“Human annotations” wording is incorrect and is retained only to preserve its
hash. Agreement statistics must not be described as human validation; a new,
separately documented human audit is still required for that claim.

The seal ID is `hb-v3.1-9671bf1ff2d5-20260721`; the sealed-manifest SHA-256 is
`d2b11edb4e39041fe246706d45b4b36302921813b49d5040fe39f35a88130804`,
and the canonical-dataset SHA-256 bound by that manifest is
`9671bf1ff2d507e31a62069bbd655b83f53803aeee3a5b5908da7b8d9d892a93`.

The original v3.3 Qwen arm was invalidated after an externally documented
service termination. A prospective v3.4.1 seal required a full fresh Qwen arm:
all 4,400 rows were newly written, none were resumed, and no old Qwen row enters
the analysis. The intact 4,400-row Ministral arm was retained. Independent
infrastructure and provenance audits passed, yielding the complete 8,800-cell
ITT matrix. The matrix includes 178 non-OK model-output/schema/parse rows
(2.02%), all retained with zero success and state credit; the infrastructure
audit separately found zero provider infrastructure errors.

Formal aggregate artifacts are:

- `outputs/confirmatory_v3.4.1/analysis_v3.4.1/confirmatory_results.json`
- `outputs/confirmatory_v3.4.1/analysis_v3.4.1/main_tables.tex`
- `outputs/confirmatory_v3.4.1/analysis_v3.4.1/provenance_manifest.public.json`
- `research/confirmatory_v3.4.1_execution_audit.md`
- `outputs/confirmatory_v3.4.1/post_confirmatory_v1/exploratory_subgroup_results.json`
- `outputs/confirmatory_v3.4.1/post_confirmatory_v1/provenance_manifest.json`

The tracked provenance file is a deterministic anonymous derivative with
repo-relative paths; its `source_private_manifest_sha256` binds the unmodified
private sealed manifest. Generate it with
`scripts/sanitize_confirmatory_provenance.py`; do not submit the private
absolute-path manifest for anonymous review.

`main_tables.tex` preserves the sealed analyzer's three-decimal presentation,
which renders the approximately $10^{-4}$ adjusted p-values as `0.000`. This is
rounding, not a zero p-value; the manuscript reports `$p<.001$`, and the exact
floating-point values remain in `confirmatory_results.json`. Its legacy HIR
caption says “oracle-conditional”; the recorded 21.75\% is the oracle-gated
joint incidence over all scheduled pairs, as defined by the sealed indicator,
not a conditional probability.

The two prespecified, pre-execution-sealed confirmatory results are:

- Structured versus Gold Oracle strict success: 71.6\% versus 91.1\%, a
  $-19.50$ percentage-point effect (family-bootstrap 95\% CI
  $[-23.63,-15.38]$; Holm-adjusted $p<.001$).
- Advisory executable checks: $+3.63$ percentage points on average (95\% CI
  $[1.91,5.44]$; Holm-adjusted $p<.001$).

Typing, provenance, interactions, endpoints, and model/domain slices remain
secondary or exploratory; their nominal intervals must not be presented as
confirmatory evidence. The separately versioned post-confirmatory subgroup
artifact shows that the pooled checks gain is heterogeneous across the two
models and carries no multiplicity-adjusted inference.

To verify the current execution seal before analysis:

```bash
PYTHONPATH=src python scripts/preflight_confirmatory.py \
  --config configs/confirmatory_v3.4.1.yaml
```

To regenerate the formal aggregates from separately archived raw runs:

```bash
PYTHONPATH=src python scripts/analyze_confirmatory.py \
  --sealed-manifest data/splits/confirmatory_v3.4.1.execution.sealed.json \
  --raw-run-dir outputs/confirmatory_v3/ministral3-14b-2512/runs \
  --raw-run-dir outputs/confirmatory_v3.4.1/qwen2.5-14b/runs \
  --output-dir outputs/confirmatory_v3.4.1/analysis_v3.4.1 \
  --bootstrap-draws 10000
```

## Paper

The current anonymous draft is available at `paper/main.pdf`. Its development
and confirmatory claims are audited in:

- `research/reviewer_audit_v3.md`
- `research/reviewer_audit_v4.md`
- `research/completion_audit.md`
- `research/aaai27_format_audit.md`
- `research/paper_code_consistency_audit.md`
- `research/non_ok_descriptive_audit_v1.md`

The official AAAI-27 limit is seven pages of non-reference content and nine
pages total, with pages 8--9 reserved for references. The reproducibility
checklist is a separate upload; `paper/ReproducibilityChecklist_draft.pdf` is
built independently. AAAI-27 also requires reproducibility materials at
submission time. Build and mechanically audit the complete anonymous Code and
Data Supplement with:

```bash
make anonymous-supplement
```

The ignored build artifact under `build/anonymous_supplement/` contains the 200
frozen tasks, 8,800 sealed raw runs, analysis code, public provenance, release
documentation, and per-member hashes. It excludes Git metadata, remotes,
private absolute-path manifests, credentials, service logs, and model weights.
Upload this artifact with the submission rather than relying on a
post-acceptance release promise. Verify the three upload artifacts against
`release/SUBMISSION_ARTIFACTS.sha256` before and after upload.

## Data and release cautions

All project-authored tasks are synthetic and unsuitable for operational, legal,
medical, financial, employment, or other decisions about real people. Evaluator
gold state must never be placed in model prompts. The sealed split must not be
repaired or filtered after confirmatory outcomes are observed.

Project-authored software is licensed under Apache-2.0 (`LICENSE`).
Project-authored synthetic tasks, annotations, and released evaluation records
are licensed under CC BY 4.0 (`DATA_LICENSE.md`). The manuscript, AAAI author
kit, model weights, trademarks, and other third-party materials are excluded
from those grants; see `NOTICE`, `THIRD_PARTY_NOTICES.md`, and
`release/RELEASE_SCOPE.md`.

The project records an informal author spot-check in
`research/human_spot_check_record_v1.md`. Because its sample IDs, size, rubric,
and blinding have not yet been recorded, it is not cited as independent human
validation and does not change the frozen dataset.
