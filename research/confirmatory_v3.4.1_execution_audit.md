# Confirmatory v3.4.1 execution and analysis audit

Audit date: 2026-07-22. Status: **PASS**.

This record binds the infrastructure-only completion audit to the formal
confirmatory analysis. It does not replace the sealed manifests, immutable raw
archive, or machine-readable provenance manifest.

## Execution disposition

- Dataset seal: `hb-v3.1-9671bf1ff2d5-20260721`
- Execution seal: `hb-v3.4.1-exec-9671bf1ff2d5-20260721`
- Execution-seal SHA-256:
  `a51d810927620ced84acc800991db55226645d7a234d58737ba4506e50df2b3b`
- Retained Ministral v3.3 arm: 4,400 raw rows.
- Fresh Qwen v3.4.1 replacement arm: 4,400 scheduled, 0 resumed, 4,400
  written.
- Invalidated v3.3 Qwen rows included in analysis: 0.
- Combined ITT population: 8,800 rows, covering 200 task families, 2 models,
  2 seeds, and 11 conditions without duplicate scheduled cells.

The v3.4 attempt failed before model loading or any candidate call because the
local vLLM build rejected a UUID-form `CUDA_VISIBLE_DEVICES`. The prospectively
sealed v3.4.1 correction mapped the same sealed GPU UUID to physical device
index 1; model snapshots, data, prompts, generation settings, analysis contract,
and full-arm replacement rule were unchanged.

The earlier v3.3 Qwen arm remains excluded in full because an external service
termination invalidated that arm. This disposition was based on infrastructure
evidence, not condition outcomes, and no partial retry or successful-row reuse
was allowed.

## Infrastructure audit

- Runner completed normally with `scheduled=4400`, `resumed=0`, and
  `written=4400`.
- Raw inventory contained 4,400 valid JSON files and 4,400 unique
  `(task_id, method, seed)` cells.
- All 6,261 watchdog samples observed the same GPU process and a healthy model
  endpoint; no watchdog violation marker exists.
- Provider infrastructure errors under the sealed audit rule: 0.
- Qwen raw-inventory SHA-256:
  `cc3e62cf3067701f311ec3a480c8ad520e09e68ce92d4d622fe35a57e381c87d`
- Qwen execution-ledger SHA-256:
  `0d5a41a8a06df32d9d92cf33464170e8165ae47ea2c04866c4433a82667e17a7`
- GPU-monitor SHA-256:
  `043184902582a51397a23416f395d4cb6eed3240e7ea9448a7e272b6a0d61912`
- Runner stdout SHA-256:
  `82dadbf1726da2cc4cb280c491c21c350c1f0e20f7b714cb7d55b96fd3385d44`
- Runner stderr SHA-256:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- vLLM log SHA-256:
  `091dc7c79db54ab56e43c9c9ce0aa48fae111a3c9357a79860e7c91fbcca561a`

Three HTTP 400 input-length validations and 81 general error-status rows were
retained under ITT; none matched the sealed definition of a provider
infrastructure error.

## Formal analysis audit

The analysis used family-cluster percentile bootstrap inference with seed 2027
and 10,000 draws. Independent recomputation verified both preregistered effects,
their confidence intervals, sign-flip tests, Holm correction, and provenance
closure across all 8,800 raw hashes.

The combined inventory contains 178 non-OK model-output/schema/parse rows
(2.02%): 97 Ministral and 81 Qwen, comprising 170 `ValueError` and 8
`JSONDecodeError` records. They remain in all formal denominators with zero
success and state credit. This tally is distinct from the infrastructure audit,
which found zero provider infrastructure errors.

- Confirmatory results SHA-256:
  `077dd30aae75ff63d4f49594be4419bdc3b6a1df7c63af31e8c3a21a18db2c09`
- Generated LaTeX tables SHA-256:
  `dd1e58862be1bbedb743c6b4cf3e7382a548e11dfe94f91f4b483b3d5c5e760c`
- Provenance manifest SHA-256:
  `86d0643395e7bf2e04a8971374fe5778587ddfa303cbc89d6ff72d8458cd773e`
- Anonymous repo-relative provenance derivative SHA-256:
  `d2121fbe15682f7ed6e9a57e6de0e3cb05ab4e8bf456a82fd3a5db26c6e8c47e`

The sealed analyzer's generated LaTeX table formats adjusted p-values to three
decimals, so values near `0.00010` appear as `0.000`. This is a presentation
rounding artifact, not a zero p-value. The paper uses `p<.001` and the exact
values in `confirmatory_results.json`; the sealed analyzer was not modified
post-execution. The generated table's “oracle-conditional” HIR caption is also
legacy wording: 21.75% is the oracle-gated joint incidence over all scheduled
pairs, not a conditional probability.

The only confirmatory claims are Structured versus Gold Oracle strict success
and the advisory-check strict-success main effect. Typing, provenance,
interactions, secondary endpoints, legacy conditions, enforcement, and
model/domain slices remain secondary or exploratory.

## Post-confirmatory exploratory subgroup artifact

A separate analysis module, not the sealed confirmatory analyzer, computes
unadjusted model/domain diagnostics over the same validated 8,800 ITT rows. It
uses 10,000 family-bootstrap draws with seed 2027, applies no multiplicity
correction, and is not confirmatory evidence.

- Exploratory subgroup results SHA-256:
  `f2512a7295f381e4943dcc38284a953e0c28d60c57684749abdd1cdc2373c828`
- Exploratory subgroup provenance SHA-256:
  `1289ae3d0820318e99151e57417ff446e1c558efddd27556654aaf5d29d6b2ed`

The checks effect is +7.0625 percentage points for Ministral (95% CI
[3.8125, 10.5]) and +0.1875 for Qwen ([-0.9375, 1.375]); their Qwen-minus-
Ministral difference is -6.875 points ([-10.4375, -3.4375]). These diagnostics
show that the pooled checks result does not replicate in Qwen and must not be
described as universal.
