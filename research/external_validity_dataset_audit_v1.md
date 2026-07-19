# External-Validity Dataset and Benchmark Audit v1

**Audit date:** 2026-07-18
**Scope:** primary-source review of existing stateful enterprise/tool-workflow datasets that could be adapted to a fixed handoff boundary. Sources are restricted to original papers, official repositories, and official dataset cards. No dataset was downloaded or inspected with a model. This is a research and engineering audit, not legal advice.

## Executive recommendation

Do **not** replace the 200 synthetic candidates with an external benchmark. Add a separately labeled **external-validity adapter slice** whose unit remains a fixed predecessor trace, a cut point, evaluator-private boundary state, and a receiver continuation. The best near-term choices are:

1. **ToolSandbox (best technical pilot):** select 20--30 scenarios with state dependencies or insufficient information, cut at an existing state snapshot, and derive gold claims from the snapshot plus scenario milestones. It has the cleanest state observability and low PII risk, and its license expressly permits modification and redistribution. Its weakness is that it is another synthetic environment rather than enterprise data.
2. **τ²-bench telecom only (best customer-service external slice):** adapt 20--30 telecom tasks, avoiding airline and retail because those domains collide heavily with HandoffBench's travel and commerce candidates. The MIT license is clear and the dual-control policy/tool/user design provides meaningful unknowns, permissions, and pending actions. Gold boundary claims require a new human audit; task rewards are not themselves atomic boundary gold.
3. **CRMArena-Pro B2B sales/lead workflows (best enterprise-semantic slice, conditional):** use only if the project accepts CC BY-NC 4.0 and noncommercial redistribution. Its synthetic Salesforce records, personas, interactive tasks, and exact answers offer genuine enterprise semantics not present in the current pool. Prefer lead qualification and sales/account state; exclude customer-service/refund cases that duplicate commerce candidates.

Use **WebArena-Verified** or **WorkArena++** as a later adapter-only robustness study, not as the first slice. Their browser/UI complexity makes it hard to distinguish handoff-state loss from perception/navigation failure. Do not incorporate **AppWorld protected content** in plaintext, and do not directly redistribute **WebLINX** or derivatives without a separate rights/PII review.

## Decision matrix

Ratings: High/Medium/Low refer to suitability for this project, not benchmark quality.

| Source | Workflow/state realism | License and redistribution | PII / third-party-content risk | Atomic boundary-gold feasibility | Candidate contamination risk | Recommendation |
|---|---|---|---|---|---|---|
| ToolSandbox | Stateful simulated phone tools; full state snapshot at each turn | Apple source license expressly permits use, modification, and redistribution; preserve notice and audit separately licensed subcomponents | **Low:** authored databases; still scan contacts/messages before release | **High:** snapshot diffs, tool visibility, milestones, and scenario state support deterministic claims | **Low--Medium:** reminders/messages overlap weakly with scheduling, but environment/action ontology is distinct | **Tier A: implement pilot** |
| τ²-bench telecom | Stateful policy/tool/user interaction; dual control | **MIT** repository, including software and associated documentation; pin version because grading fixes can change comparability | **Low--Medium:** simulated records, but confirm every domain asset and generated transcript before redistribution | **Medium--High:** hidden user goal, DB state, policy, tools, and reward basis are available; minimality/consent still need double annotation | **Low** for telecom; **High** for airline/retail | **Tier A: telecom adapter** |
| CRMArena-Pro | Synthetic Salesforce org with interconnected enterprise objects, personas, interactive B2B/B2C tasks | Dataset and repository are **CC BY-NC 4.0**; adaptations may be shared only for noncommercial purposes with attribution/change notices | **Low--Medium:** synthetic enterprise records, but schemas include CRM-like personal fields; run PII scanner and never connect to a real org | **Medium:** answers and records identify decision state, but many tasks are QA/analytics rather than executable transition paths | **Medium** for sales; **High** for customer service/commerce | **Tier B: conditional enterprise slice** |
| WorkArena / WorkArena++ | ServiceNow knowledge-work tasks and compositional workflows | Code is **Apache-2.0**, but benchmark instances are gated and require accepting separate access terms; code license does not establish redistribution rights for instance images/data | **Low--Medium** if only official synthetic instance data; operational credentials and instance dumps must never be released | **Medium:** task configs/evaluators can define terminal state, but atomic evidence at a cut needs UI/database instrumentation | **Medium--High** for IT, procurement, scheduling | **Tier B: adapter-only after terms review** |
| WebArena-Verified | Self-hosted realistic websites; 812 human-audited tasks; deterministic offline network-trace scoring | Repository/dataset are **Apache-2.0**; environment images and upstream site data still require per-asset NOTICE/license review | **Medium:** self-hosted sample data reduces user PII, but GitLab/Reddit/maps/Wikipedia content can carry usernames or third-party rights | **Medium--Low:** a trace cut is easy; reconstructing minimal semantic state across DOM/network/database layers is expensive | **High** for shopping and GitLab-like IT; lower for map/Wikipedia but weaker enterprise fit | **Tier B/C: robustness study** |
| AppWorld | Controllable simulated apps/people, database setup, task solution and evaluation programs | Public code is Apache-2.0; protected task/app content is Apache-2.0 **plus encrypted-redistribution requirement** for it and derivatives | **Low** for fictional people, subject to scanning; **high release-process risk** from protected-content rule | **High** locally because setup and evaluators expose state; test setup/solutions are intentionally hidden | **Medium:** broad apps include commerce, scheduling, and communications | **Adapter-only; no plaintext derivative release** |
| WebLINX | Real human--assistant web-navigation dialogues and demonstrations | Data are **CC BY-NC-SA 4.0**, derivatives inherit SA and additional third-party terms; research/fair-use compliance is left to the user | **High:** real websites, conversations, screenshots/HTML, and third-party sources require privacy and rights review | **Low--Medium:** observed next action is available, but world state, policy authority, and unique terminal predicate are generally absent | **Unknown/High:** public real-web traces are widely exposed and semantic overlap is hard to audit | **Do not merge; metadata-only feasibility study** |

## Primary-source findings

### 1. ToolSandbox

The [official repository](https://github.com/apple/ToolSandbox) defines an execution context containing tools, dialogue history, world state, and a snapshot at every turn. World state covers settings, contacts, messages, and reminders, and evaluation supports intermediate/final milestones over arbitrary trajectories. This makes a boundary adapter unusually direct: choose a pre-action snapshot, expose the prior trace to a source role, and derive candidate gold claims from state deltas, visibility, unmet milestone predicates, and user-provided facts.

The [official license](https://raw.githubusercontent.com/apple/ToolSandbox/main/LICENSE) permits use, reproduction, modification, and redistribution with notice preservation and trademark restrictions; it also warns that subcomponents have separate notices. Before reuse, create a component-level attribution manifest from `ACKNOWLEDGEMENTS` rather than treating the entire tree as a standard permissive license.

**Gold construction:** high feasibility, but do not equate every database cell with task-critical state. For each cut, mechanically enumerate changed/query-relevant state, then have two humans independently select the minimal claims whose removal changes a legal next action or milestone. A snapshot-derived claim is trace-grounded; a scenario milestone provides relevance evidence.

**Contamination:** do not use reminder-creation or calendar-like scenarios that resemble current scheduling families. Prefer cellular/Wi-Fi state dependencies, contact disambiguation, messaging with insufficient information, and canonicalization. Run the same normalized action-graph and lexical audit against all current development/candidate families.

### 2. τ²-bench

The [official repository](https://github.com/sierra-research/tau2-bench) describes policies, tools, tasks and optional user tools across airline, retail, telecom and other domains. The dual-control design is particularly valuable for handoffs: the predecessor may have learned facts from tools or the simulated user while authority or an action remains with the receiver. The repository is [MIT licensed](https://raw.githubusercontent.com/sierra-research/tau2-bench/main/LICENSE). It also records versioned grading changes, so any adapter must pin a release/commit and store upstream task hashes.

**Gold construction:** cut only after at least one authenticated tool/user event and before a consequential action. Candidate claims can be proposed from the database state, hidden user goal, policy preconditions, prior tool results and unresolved user-controlled fields. The original success reward is terminal evidence, not proof that the proposed boundary state is minimal or unique; HandoffBench's human protocol remains necessary.

**Contamination:** exclude airline and retail from the external slice. They are near-direct semantic matches to current travel cancellation/rebooking, refunds, order changes, loyalty and shipping families, and τ-bench already informs this project's related work. Telecom provides a distinct action vocabulary and operational state. Do not inspect τ² tasks until the current 200-family split is sealed, or explicitly mark the external slice as post hoc and separate from confirmation.

### 3. CRMArena and CRMArena-Pro

The [official repository](https://github.com/SalesforceAIResearch/CRMArena) covers Salesforce-based CRM evaluation; the official [CRMArena](https://huggingface.co/datasets/Salesforce/CRMArena) and [CRMArena-Pro](https://huggingface.co/datasets/Salesforce/CRMArenaPro) cards declare **CC BY-NC 4.0**. CRMArena-Pro exposes B2B/B2C and interactive splits, personas, 22 task types, answers and metadata over synthetic enterprise data. The official project describes a research-only/noncommercial use posture.

**License consequence:** an AAAI research artifact can plausibly use and redistribute an attributed noncommercial adaptation, but it cannot be presented as unrestricted commercial-use benchmark data. Mark every derivative, retain attribution and license links, state changes, and separate it from any more permissively licensed core artifact. Obtain institutional confirmation before release.

**Gold construction:** lead qualification is the strongest fit because records and recent discussions support atomic Budget/Authority/Need/Timeline claims and a clear decision. Other promising tasks concern account/sales state and confidentiality. Avoid tasks scored only by fuzzy free-text answers and tasks requiring broad aggregation: they lack a compact handoff boundary. Instrument a fixed record/query trace and ensure the receiver's legal action set is deterministic.

**PII:** data are described as synthetic, but CRM schemas naturally contain names, emails, call transcripts and customer attributes. Run field-level PII detection, preserve fictional-identity documentation, and prohibit connections to any real Salesforce org. Synthetic PII-like strings are not privacy violations by themselves but should be labeled to prevent mistaken operational use.

### 4. WorkArena / WorkArena++

The [official WorkArena repository](https://github.com/ServiceNow/WorkArena) targets common knowledge-work tasks on ServiceNow; WorkArena++ adds compositional workflows. Repository code is [Apache-2.0](https://raw.githubusercontent.com/ServiceNow/WorkArena/main/LICENSE), but execution requires access to the gated `WorkArena-Instances` repository and acceptance of its terms. Therefore, Apache-2.0 for code must not be cited as permission to redistribute instance images, credentials, database dumps, or derived task content.

**Gold construction:** use task configuration plus evaluator/database queries to identify relevant records at a deterministic cut. The most valuable cases would cross roles—for example intake to fulfiller, incident triage to resolver, or request review to approver. However, browser perception and navigation can swamp the transfer effect. The receiver should consume a normalized tool/API interface or a replayed authenticated trace, not a live visual UI, for the primary handoff comparison.

**Contamination:** ServiceNow incidents, approvals, catalog requests and schedules collide with current IT/procurement/scheduling domains. Treat WorkArena as external replication, never as additional “independent” HandoffBench families, and audit semantic/template overlap manually.

### 5. WebArena-Verified

The [official repository](https://github.com/ServiceNow/webarena-verified) provides 812 manually audited tasks, deterministic type-aware evaluation, and offline network-trace replay under [Apache-2.0](https://raw.githubusercontent.com/ServiceNow/webarena-verified/main/LICENSE). This is a strong source for reproducible endpoints and human-verified task correctness.

Its weakness for HandoffBench is construct alignment. A midpoint browser trace contains large DOM/network state, while the required handoff state may be a small set of facts and permissions not explicitly labeled. Shopping and GitLab tasks also overlap strongly with existing commerce and IT families. If used, sample only tasks with a unique mutating endpoint, cut immediately before the mutation, derive state from authenticated network responses, and publish performance both with and without UI observations.

Audit every Docker image and upstream dataset separately. Apache licensing of the wrapper does not automatically resolve rights in Wikipedia, maps, images, usernames, or other bundled content.

### 6. AppWorld

The [official repository](https://github.com/StonyBrookNLP/appworld) provides controllable applications, people, database setup, solutions and executable evaluators. It is technically attractive because a handoff can be inserted between API calls and the gold can be reconstructed from setup/evaluation programs.

However, its public and protected portions use different terms. Protected task/app/API content is encrypted and licensed under Apache-2.0 with an additional requirement that public redistribution of it **or derivatives** remain encrypted. The authors explicitly request that protected content not be posted as plaintext. Therefore HandoffBench must not copy task text, API schemas, solutions, evaluator-derived claims or adapted traces into a public plaintext dataset. A lawful engineering pattern is an adapter that users run locally after separately installing AppWorld; outputs must be checked against the protected-content rule.

### 7. WebLINX

The official [dataset card](https://huggingface.co/datasets/McGill-NLP/WebLINX) describes real-world website navigation with multi-turn dialogue and 79,777 rows. Its data license is **CC BY-NC-SA 4.0**, with additional acknowledgement that third-party-source terms may apply and that users are responsible for lawful/fair-use compliance. The [official repository](https://github.com/mcgill-nlp/weblinx) is Apache-2.0, but explicitly says the dataset has separate terms.

WebLINX is useful as evidence that handoff performance should eventually be tested on human-generated traces. It is a poor source for immediate conversion: real conversations/HTML/screenshots can contain personal identifiers or copyrighted content; the next recorded action is not a unique legal action; and there is no evaluator-private minimal semantic state. The safe first study is metadata-only sampling (site category, trace length, action types) followed by institutional privacy review. Do not redistribute raw or derived examples in HandoffBench v1.

## Boundary-adaptation protocol

For any selected source, use the following gate before creating a task:

1. **Pin provenance:** record upstream repository, release/commit, task ID, file hashes, license, NOTICE and any gated terms.
2. **Choose a causal cut:** at least one authenticated event precedes the cut and at least one nontrivial legal decision follows it. Avoid arbitrary 50% trace cuts.
3. **Separate upstream content:** keep the external task in its own namespace and split. Never count it among the 200 candidate families or use it to replace rejected confirmatory items after seeing outcomes.
4. **Propose boundary state mechanically:** use snapshot diffs, policy guards, hidden user goal, prior tool results and terminal predicates. Record which mechanism witnesses every proposed claim.
5. **Validate independently:** two humans reconstruct the state and legal continuation without seeing proposed labels. Reject non-unique, UI-dependent, secret-argument or evaluator-leaking cases.
6. **Minimize disclosure:** release IDs, adapters and derived statistics when source terms permit; avoid copying protected task text or real user content. Run secrets/PII scanning and manual review.
7. **Measure contamination:** compare family semantics, normalized trace/action graphs, tool/action names, policy phrases and terminal predicates against candidate and development sets. Report exact and human-reviewed overlaps.
8. **Report separately:** label results “external adapter slice,” give per-source estimates, and do not pool them with the synthetic confirmatory estimand unless sampling and weighting were preregistered.

## Contamination controls specific to the current project

The current candidate pool already covers travel, commerce, procurement, enterprise IT and scheduling. Therefore:

- **Embargo τ² airline/retail, WorkArena catalog/incident/approval tasks, WebArena shopping, and AppWorld commerce/calendar tasks** until the 200 candidates are sealed. Viewing their task internals now risks converting them into development material.
- Prefer **telecom network/account state**, **CRM lead/account qualification**, and **ToolSandbox device/contact/message state** because their world schemas and action vocabularies are least represented in the current pool.
- For every imported source, maintain a `source_task_id -> external_family_id` map that is evaluator-private; never describe adapted upstream test content in prompts, papers, or examples beyond the source license.
- Add source-membership as a reporting stratum. External validity is not demonstrated by pooling many near-duplicate source tasks.
- Evaluate modern model contamination separately: AppWorld encrypts protected content specifically to reduce training leakage, while τ²/WebArena/ToolSandbox task definitions are public and may already be in model pretraining. Report source publication date and public exposure; do not call model familiarity “dataset leakage” without evidence.

## Minimum viable external-validity study

After the core confirmatory split is sealed—not before:

1. Select **24 ToolSandbox** scenarios from distinct templates and **24 τ² telecom** tasks, with no model inspection.
2. Create one causal handoff cut per source task and produce label-free packets.
3. Run the existing double-annotation/adjudication protocol; target at least 20 accepted families/source rather than silently relaxing criteria.
4. Compare Structured, Full History and Gold Oracle first. Run the factorial only if the adapter can guarantee identical upstream evidence and matched serialization across cells.
5. Report source-specific agreement, Structured--Oracle regression, reverse flips, task cost and failure taxonomy. Do not use these results to amend the primary synthetic hypotheses.
6. Add CRMArena-Pro only after license approval and only as a separately licensed B2B sales slice.

This two-source study would materially strengthen ecological diversity while preserving causal control. It would not justify claims about production handoffs or real private enterprise data, but it would directly answer the strongest current external-validity objection: whether HandoffBench's evaluator and transfer estimand survive outside its project-authored five-domain world.

## Final go/no-go

- **GO now:** write adapters and annotation specifications for ToolSandbox and τ² telecom using only public metadata and pinned source identifiers; do not inspect candidate task contents until the core split is sealed.
- **CONDITIONAL GO:** CRMArena-Pro B2B after CC BY-NC approval; WorkArena/WebArena-Verified as adapter-only secondary studies after asset/instance-rights review.
- **NO-GO for direct inclusion:** AppWorld protected plaintext derivatives and WebLINX raw/derived real-user content.
- **NO-GO methodologically:** mixing external tasks into the current 200, replacing rejected items after outcome inspection, or calling upstream terminal answers “gold boundary state” without independent reconstruction and minimality validation.
