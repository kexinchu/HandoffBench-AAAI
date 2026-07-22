# Post-results reviewer audit v3

Audit date: 2026-07-22. Scope: the completed 8,800-cell confirmatory study,
updated anonymous manuscript, execution/provenance chain, and AAAI-27 submission
requirements.

## Current verdict

The empirical core is credible and potentially competitive: 200 independent
families, two models, two seeds, a matched representation factorial, judge-free
metrics, a Gold Oracle intervention, family-clustered inference, and transparent
full-arm replacement after infrastructure invalidation. The two preregistered
results are strong and correctly bounded: Structured trails Gold Oracle by 19.50
percentage points, while advisory checks have a pooled +3.625-point effect.

The initial post-results draft rated 2--3/5 because of claim/provenance errors.
This revision fixes or mitigates the following:

- discloses LLM-agent rather than human annotation and records a post-seal
  provenance correction without mutating sealed bytes;
- discloses broader generative-AI assistance in research and writing;
- removes the unsupported headline claim of an empirically demonstrated
  extraction--transport--utilization decomposition;
- calls 21.75% an oracle-gated HIR joint incidence, not a conditional rate;
- reports all 178/8,800 non-OK ITT rows separately from infrastructure errors;
- versions an explicitly exploratory subgroup analysis showing the checks gain
  in Ministral (+7.06 points) but not Qwen (+0.19 points);
- replaces identity-bearing private provenance with a deterministic public
  repo-relative derivative; and
- updates the audit to the official AAAI-27 7/9-page rule and separate-checklist
  requirement.

## Remaining blockers to a 4/5 claim

1. **Human construct validity.** No recruited human produced or independently
   verified the A/B labels; the exact annotation-agent model/runtime was not
   recorded. A frozen, outcome-independent human audit is the highest-value next
   step. It may report discrepancies but must not repair the sealed test set.
2. **Anonymous reproducibility package.** AAAI-27 requires necessary code, data,
   and materials at submission. The project still needs an anonymized Code and
   Data Supplement containing the sealed public derivatives and raw-run archive
   or an acceptable immutable archive, with no `.git`, username paths, remotes,
   logs, or identifying metadata.
3. **Licensing.** No top-level code/data license has been selected; checklist
   release answers must remain `no` until the owners choose compatible terms.
4. **Runtime completeness.** The Qwen arm has a post-run environment snapshot,
   but the retained Ministral arm lacks an equivalent package-version record.
5. **Presentation depth.** The main paper would benefit from one concrete
   task/capsule example and broader foundational related work. A true stage-wise
   failure decomposition should be added only with a versioned diagnostic
   artifact; otherwise the current scoped claim should remain.

## Score guidance

As revised, the work is closer to a defensible 3/5 than the pre-audit draft, but
it should not yet be represented as a 4/5-ready submission. A locked human audit,
an anonymous submission-time reproducibility package, and an explicit licensing
decision are the critical path to a plausible weak accept. No review score can
be guaranteed.
