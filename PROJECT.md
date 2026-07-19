# HandoffBench Research Contract

## Thesis

Multi-agent handoff is a state-transfer boundary. Reliability depends on whether
the receiving agent obtains and correctly uses the task-critical state required
for its next action, not only on whether the system routes to the right agent.

## Intended contributions

1. A benchmark with controlled handoff boundaries and hidden, typed gold state.
2. Deterministic state- and workflow-level metrics plus a failure taxonomy.
3. A comparison of full history, free-form summary, structured payload, and an
   executable handoff capsule.
4. Evidence about fidelity, task success, safety-relevant errors, and context
   cost across domains, stressors, and multiple model families.

## Non-goals

- Generic long-term memory or stale-memory retrieval.
- Tool or provider routing in isolation.
- Vector retrieval or artifact-reuse systems.
- Claims of real-world safety certification.

## Evidence policy

- No fabricated citations, model outputs, measurements, or significance tests.
- Dataset generation and evaluation versions are recorded.
- Main metrics are programmatic; model-based judging is supplementary.
- Every headline claim must map to a checked result artifact.
- Synthetic tasks are explicitly described as synthetic-but-executable.

## Completion gate

The project is paper-ready only when the benchmark and harness are reproducible,
the main and ablation experiments have auditable outputs, the statistical and
failure analyses are complete, and the AAAI source compiles without format
errors.
