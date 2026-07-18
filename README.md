# HandoffBench Agent Brief

## One-Line Goal

We want to quickly develop an AAAI-27 submission around **HandoffBench: Evaluating State Transfer in Multi-Agent LLM Workflows**.

The core thesis is:

> Multi-agent LLM handoff is not only a routing problem. It is a state-transfer problem. When control moves from one agent to another, task-critical state can be lost, distorted, or hallucinated, causing downstream failures even when each individual agent is capable.

## Background

Modern agent frameworks increasingly support multi-agent workflows where one agent delegates control to another. Examples include:

- OpenAI Agents SDK handoffs and multi-agent orchestration.
- LangChain multi-agent handoffs.
- Microsoft Agent Framework handoff orchestration.

These systems often treat handoff as an engineering primitive: agent A decides that agent B should take over, and the system passes a transcript, summary, tool payload, or structured input. However, there is not yet a clear benchmark that isolates whether the handoff preserved the right task state.

This project should focus on **handoff fidelity**:

- Did the downstream agent receive the user goal correctly?
- Did it preserve verified facts from previous tool calls?
- Did it know which slots remain unresolved?
- Did it avoid inventing user consent or commitments?
- Did it avoid repeating expensive or unsafe tool calls?
- Did it respect preconditions before irreversible actions?

## Important Non-Overlap Constraints

Avoid drifting into these existing or prior idea families:

- Do not make this a stale tool-memory paper.
- Do not make this about old memory interfering with new tasks.
- Do not make this a Safe Reuse Witness / artifact reuse paper.
- Do not make this a pgvector / filtered ANN / SQLens / ANNS retrieval paper.
- Do not make this a generic agent memory paper.
- Do not make this only a tool routing or provider routing paper.

This paper should be about **state transfer across multi-agent handoff boundaries**.

## Target Paper Shape

Working title:

**HandoffBench: Evaluating State Transfer in Multi-Agent LLM Workflows**

Possible stronger framing:

**State Is the Interface: Evaluating Handoff Fidelity in Multi-Agent LLM Workflows**

Expected contribution package:

1. **Benchmark**
   - Create HandoffBench: a benchmark of stateful multi-agent workflows with forced or natural handoff points.
   - Each task contains a gold state specification for the handoff boundary.

2. **Metrics**
   - Measure handoff state recall.
   - Measure handoff state precision.
   - Measure hallucinated commitments.
   - Measure missed preconditions.
   - Measure duplicated tool calls.
   - Measure handoff-induced task regression.
   - Measure final task success.
   - Optionally measure cost/context length.

3. **Baseline Comparison**
   - Full transcript handoff.
   - Free-form summary handoff.
   - Framework-style structured payload handoff.
   - Shared memory handoff, if simple to implement.
   - Proposed typed handoff capsule.

4. **Method**
   - Propose an **Executable Handoff Capsule**: a typed, minimal, provenance-aware transfer artifact.
   - The capsule should expose only task-critical state needed by the next agent.
   - It should be checkable against the conversation and tool trace.

## Research Questions

The project should answer:

1. How often do common handoff mechanisms lose or distort task-critical state?
2. Which state categories are most vulnerable during handoff?
3. Does a typed handoff capsule improve downstream task success and state fidelity?
4. Can capsule-based handoff match full-history handoff with lower context cost and better auditability?
5. Are state-transfer failures different from ordinary planning, memory, or tool-use failures?

## Benchmark Design

Start with 30-50 pilot tasks, then scale to 80-150 if time allows.

Each task should have:

- A user-facing scenario.
- Two or three specialized agents.
- A controlled handoff point.
- A set of tools or mocked APIs.
- A hidden gold state at the handoff boundary.
- A final success condition.

Recommended domains:

- Travel booking or itinerary repair.
- Customer support refund/exchange.
- Shopping or procurement.
- Healthcare-style appointment scheduling without medical advice.
- Enterprise IT support.

Recommended agent roles:

- Intake agent: collects user intent, constraints, identity, and unresolved fields.
- Tool/policy agent: checks inventory, rules, policies, eligibility, or records.
- Resolution agent: performs final action or gives final answer.

Recommended handoff points:

- After user constraints are collected.
- After tool evidence is obtained.
- Before an irreversible or user-impacting action.

## Gold Handoff State Schema

Each handoff boundary should include gold labels such as:

```json
{
  "user_goal": "...",
  "verified_facts": [],
  "unresolved_slots": [],
  "tool_results": [],
  "policy_checks": [],
  "consent_status": "...",
  "commitments": [],
  "risk_flags": [],
  "next_step_preconditions": []
}
```

The downstream agent should be evaluated on whether it preserves and uses these fields correctly.

## Proposed Method: Executable Handoff Capsule

The capsule is not just a summary. It is a typed transfer object.

Suggested capsule fields:

```json
{
  "handoff_id": "...",
  "source_agent": "...",
  "target_agent": "...",
  "task_state": {
    "user_goal": "...",
    "constraints": [],
    "verified_facts": [],
    "open_questions": [],
    "tool_evidence": [],
    "policy_status": [],
    "consent": {
      "required": true,
      "obtained": false,
      "scope": null
    },
    "commitments": [],
    "blocked_actions": [],
    "next_step": "..."
  },
  "provenance": [
    {
      "field": "...",
      "source": "user_message | tool_call | policy_check",
      "trace_id": "..."
    }
  ],
  "checks": [
    {
      "condition": "...",
      "status": "satisfied | missing | contradicted"
    }
  ]
}
```

The key idea: the receiving agent should not infer critical state from an informal summary. It should receive a typed state artifact whose fields can be checked against trace evidence.

## Baselines

Implement these conditions:

1. **Full History**
   - Target agent receives the entire conversation and tool trace.
   - Strong baseline, but expensive and may leak irrelevant state.

2. **Free Summary**
   - Source agent writes a natural-language handoff summary.
   - Common in practice, likely lossy.

3. **Structured Payload**
   - Source agent fills a simple JSON schema without provenance/checks.
   - Tests whether typing alone helps.

4. **Executable Capsule**
   - Typed state plus provenance and precondition checks.
   - Main proposed method.

Optional:

5. **Shared Memory**
   - Agents read/write a shared scratchpad or memory store.
   - Use only if easy; avoid turning the paper into a generic memory paper.

## Evaluation Metrics

State-level metrics:

- **State Recall**: fraction of required gold state fields preserved.
- **State Precision**: fraction of transferred fields that are correct.
- **Contradiction Rate**: rate of fields that conflict with earlier evidence.
- **Hallucinated Commitment Rate**: downstream agent believes the user agreed to something they did not agree to.
- **Missed Precondition Rate**: downstream agent proceeds despite missing required information or consent.

Workflow-level metrics:

- **Final Task Success**.
- **Handoff-Induced Regression**: task fails only after handoff despite sufficient upstream evidence.
- **Duplicate Tool-Call Rate**.
- **Unnecessary User Re-Ask Rate**.
- **Context Tokens / Cost**.

Reliability metrics:

- **Pass@1 / Pass@k**.
- **Cross-run Consistency**.
- **Failure Category Distribution**.

## Failure Taxonomy

Build a compact taxonomy to make the paper feel scientific rather than just infrastructural.

Suggested categories:

- Goal loss: downstream agent misunderstands the user objective.
- Constraint loss: downstream agent drops date, budget, preference, policy, or eligibility constraints.
- Evidence loss: downstream agent ignores verified tool results.
- Evidence mutation: downstream agent changes a tool result during handoff.
- Open-slot loss: downstream agent treats unresolved information as resolved.
- Consent hallucination: downstream agent assumes approval that was never given.
- Commitment hallucination: downstream agent invents a promise or completed action.
- Precondition skip: downstream agent proceeds before required checks.
- Redundant action: downstream agent repeats a tool call or user question unnecessarily.
- Role confusion: downstream agent performs an action outside its assigned scope.

## Related Work To Investigate

Primary sources to read first:

- OpenAI Agents SDK handoff documentation.
- OpenAI multi-agent orchestration documentation.
- LangChain multi-agent handoff documentation.
- Microsoft Agent Framework handoff orchestration.
- AgentBench.
- MultiAgentBench.
- STATE-Bench.
- LEGOMem.

Positioning:

- AgentBench and MultiAgentBench evaluate broad agent or multi-agent capability, but do not isolate handoff-boundary state transfer.
- STATE-Bench evaluates stateful enterprise agents, but the paper should emphasize cross-agent state transfer rather than single-agent state tracking.
- LEGOMem studies procedural memory in multi-agent systems; this project should focus on transfer fidelity at handoff boundaries.
- Framework docs show handoff is real and timely, but they do not provide a benchmark or formal metrics for state-transfer failures.

## Why This Is Viable For AAAI

This idea is viable because:

- Handoff is already a real primitive in deployed agent frameworks.
- Multi-agent LLM systems are increasingly common, but reliability at the handoff boundary is under-measured.
- The benchmark can be built quickly with synthetic-but-realistic workflows and mocked tools.
- The method does not require training a model.
- The paper can show value even if full-history is strong, because capsule handoff can be cheaper, more auditable, and less noisy.
- The contribution can be benchmark-first, which is realistic under a short deadline.

## Main Risk

The biggest risk is that reviewers may see this as an engineering protocol instead of a research contribution.

Mitigation:

- Make the problem definition formal.
- Include gold state labels and deterministic scoring.
- Include a failure taxonomy.
- Show empirical gaps in common handoff mechanisms.
- Show that typed/provenance-aware handoff improves measurable reliability.

## Fast Execution Plan

### Day 1: Literature And Problem Lock

- Read primary framework docs and benchmark papers.
- Write related-work table.
- Lock the benchmark schema and failure taxonomy.
- Draft the paper abstract and intro thesis.

### Day 2: Pilot Dataset

- Create 30-50 tasks across 3 domains.
- Define gold handoff states.
- Implement mocked tools.
- Implement the four handoff conditions.

### Day 3: Evaluation Harness

- Run at least two LLMs if possible.
- Compute state metrics and final success.
- Produce first plots/tables.
- Inspect failures manually.

### Day 4: Scale And Polish

- Scale toward 80-150 tasks if feasible.
- Add stressors:
  - long context,
  - user changes mind,
  - conflicting evidence,
  - missing consent,
  - multi-step tool result,
  - irreversible action.
- Finalize claims.

### Day 5: Paper Draft

- Write intro, benchmark, method, experiments, related work, limitations.
- Keep claims modest and evidence-backed.
- Emphasize benchmark and metrics as the durable contribution.

## Desired Output From The Next Agent

The next agent should produce:

1. A deeper related-work matrix with citations and exact positioning.
2. A refined problem definition and benchmark formalism.
3. A concrete dataset schema.
4. 10-20 fully specified example tasks.
5. An evaluation harness design.
6. A draft abstract and intro outline.
7. A go/no-go assessment for AAAI-27 feasibility.

## Suggested Initial Abstract

Multi-agent LLM systems increasingly decompose tasks through handoffs, where one agent transfers control to another after partial user interaction and tool execution. Current handoff mechanisms often pass raw history, informal summaries, or lightweight payloads, leaving unclear whether task-critical state has been preserved. We introduce HandoffBench, a benchmark for measuring state-transfer fidelity in multi-agent tool-use workflows. HandoffBench inserts controlled handoffs into stateful tasks and evaluates whether downstream agents preserve verified evidence, unresolved constraints, user commitments, tool-derived state, consent status, and required next-step preconditions. We further propose Executable Handoff Capsules, typed transfer artifacts with provenance and checkable preconditions. Experiments compare raw-history, summary, structured-payload, shared-memory, and capsule-based handoffs across task success, state fidelity, hallucinated commitments, unnecessary tool use, and context cost. Our results aim to show that reliable multi-agent coordination requires treating handoff as a first-class state-transfer problem, not merely a routing decision.

## Instruction To The Next Agent

Please do not propose a new unrelated idea. Assume the target idea is HandoffBench. Your job is to pressure-test it, sharpen the novelty, find related work, and turn it into a fast AAAI-ready research plan.


