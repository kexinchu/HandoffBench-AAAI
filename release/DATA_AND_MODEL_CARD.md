# HandoffBench data and model card

## Dataset

HandoffBench v3.4.1 is a frozen, synthetic benchmark of 200 independent
multi-agent handoff families across travel, commerce, procurement, IT, and
scheduling. Each task provides an authenticated upstream trace, deterministic
mock-tool world, receiver-facing handoff views, evaluator-only gold state, and
exact workflow predicates. The execution design evaluates two named model
deployments, two seeds, and eleven scheduled conditions, for 8,800 ITT cells.

The task content is synthetic and must not be used for operational decisions or
to infer properties of people. Gold state and evaluator-only rules must not be
exposed to evaluated agents. The benchmark is designed to measure controlled
state-transfer fidelity, not real-world safety, general intelligence, or human
preference alignment.

## Label provenance and validity

The frozen labels were independently produced by two isolated LLM-agent roles
and disagreements were handled by a separate LLM-agent adjudication role. They
are not human annotations. The exact underlying annotation runtime was not
recorded. A project owner performed a partial manual spot audit after sealing;
it did not alter frozen labels or the confirmatory analysis. This supports a
limited face-validity check only and does not establish a recruited-human
agreement study.

## Models and outputs

The confirmatory matrix uses the deployment identifiers and snapshot metadata
bound in `configs/confirmatory_v3_model_snapshots.v3.json`. Raw records may
contain generated text and parser failures. They are supplied for reproducible
analysis, not as a recommended training corpus. The package excludes model
weights, provider credentials, and service logs; model use remains subject to
the relevant upstream terms.

## Known limitations

- The task worlds are templated synthetic simulations.
- The retained model arm lacks a complete contemporaneous package-version log.
- The annotation process lacks recruited-human validation.
- Formal inference is limited to the two pre-execution sealed tests; subgroup
  results are explicitly exploratory.
- The archive reconstructs evaluation aggregates, not generation-time service
  behavior or exact runtime latency.

## Release terms

Project-authored code is Apache-2.0. Project-authored synthetic benchmark data,
annotation records, and released raw or aggregate outputs are CC BY 4.0. See
`LICENSE`, `DATA_LICENSE.md`, `NOTICE`, and `THIRD_PARTY_NOTICES.md` for the
authoritative scope and third-party exclusions.
