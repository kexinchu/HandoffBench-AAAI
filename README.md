# HandoffBench

HandoffBench is a research codebase for measuring whether task-critical state
survives a transfer of control between LLM agents. It fixes an authenticated
upstream trace and handoff boundary, then evaluates alternative receiver views
with deterministic state probes, tool simulators, and terminal predicates.

The accompanying manuscript is **State Is the Interface: Evaluating Handoff
Fidelity in Multi-Agent LLM Workflows**.

> Research status: the synthetic 200-family confirmatory split is human-validated
> and sealed, and has received zero candidate-model calls. Confirmatory model
> execution has **not** started: `configs/confirmatory_v3.yaml` deliberately sets
> `execution_authorized: false`. Development results must not be described as
> benchmark test results.

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
Git repository. Aggregate development artifacts include their input-directory
provenance; a complete archival release should publish the immutable raw runs as
a separate versioned artifact.

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

## Sealed split and confirmatory gate

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

The seal ID is `hb-v3.1-9671bf1ff2d5-20260721`; the sealed-manifest SHA-256 is
`d2b11edb4e39041fe246706d45b4b36302921813b49d5040fe39f35a88130804`,
and the canonical-dataset SHA-256 bound by that manifest is
`9671bf1ff2d507e31a62069bbd655b83f53803aeee3a5b5908da7b8d9d892a93`.

Run the static confirmatory preflight with:

```bash
PYTHONPATH=src python scripts/preflight_confirmatory.py \
  --config configs/confirmatory_v3.yaml
```

All annotation, audit, seal, dataset, design, and model-snapshot gates pass. The
command intentionally exits nonzero only because execution authorization remains
false. Do not edit `execution_authorized` merely to bypass this final human gate.
No confirmatory result exists yet.

## Paper

The current anonymous draft is available at `paper/main.pdf`. Its development
claims and unresolved limitations are audited in:

- `research/reviewer_audit_v2.md`
- `research/completion_audit.md`
- `research/aaai27_format_audit.md`
- `research/paper_code_consistency_audit.md`

The official AAAI-27 event-specific page limit and checklist submission procedure
must be rechecked before submission; this repository does not infer them from a
previous conference year.

## Data and release cautions

All project-authored tasks are synthetic and unsuitable for operational, legal,
medical, financial, employment, or other decisions about real people. Evaluator
gold state must never be placed in model prompts. The sealed split must not be
repaired or filtered after confirmatory outcomes are observed.

No top-level open-source or data license has yet been selected. Public visibility
does not grant reuse rights; do not infer a license until the project owners add
one. Third-party author-kit files retain their original terms.
