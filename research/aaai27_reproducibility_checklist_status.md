# AAAI-27 reproducibility checklist draft status

The official AuthorKit checklist was copied without changing its questions into
`paper/ReproducibilityChecklist_draft.tex`; only response placeholders in the
question section were replaced. AAAI-27 requires this checklist as a separate
upload, so the standalone PDF is intentionally not appended to `main.pdf`.

The conservative `no` or `partial` answers are intentional. Independent
LLM-agent double annotation, disagreement-only agent adjudication, blind validity review,
replacement, final audit, sealing, confirmatory execution, and formal analysis
are complete. The sealed population contains 200 families (40 per domain), and
the final analysis contains all 8,800 scheduled ITT cells. However:

- Apache-2.0 now covers project-authored software and CC BY 4.0 covers
  project-authored synthetic data and released evaluation records. The
  manuscript, AAAI author kit, model weights, and third-party materials are
  explicitly excluded from those grants.
- A deterministic anonymous Code and Data Supplement has been built and audited
  with all 8,800 raw records. It must still be uploaded by the authors at
  submission; its existence in a local ignored build directory is not itself a
  completed OpenReview upload.
- The annotation agents' exact underlying model/runtime identity was not
  recorded, and no recruited-human audit exists; the checklist and paper cannot
  claim human-grounded annotation reproducibility.
- The v3.4.1 Qwen host has a post-run hardware/software snapshot, but the
  retained Ministral arm lacks an equivalently complete package-version record;
  computing infrastructure is therefore `partial`.
- Code is in the repository, not literally embedded in a paper appendix.
- Development settings and selection rationale are documented, but not every
  tried parameter value is enumerated in the paper.
- The paper is empirical rather than theoretical; conditional theory questions
  are marked `NA` because they do not apply.

The significance-testing response is now `yes`: the paper identifies its two
confirmatory tests, uses family-clustered inference, applies Holm correction,
and keeps unadjusted secondary estimates outside that family. Other responses
may be upgraded only when the corresponding artifact and paper disclosure
actually exist. Licensed-release questions may now be answered `yes`; completed
execution does not by itself justify upgrading infrastructure, code-appendix,
or hyperparameter answers.

## Offline rebuild

From the repository root, using the project Python environment:

```bash
make submission
```

This runs tests, records environment/package versions and hashes, reconstructs a
machine-readable manifest of manuscript sources, builds the paper and standalone
checklist, and audits the PDF log. It performs no provider or model call and does
not modify raw output directories. Generated audit records are written under
`build/reproducibility/`.
The default interpreter is `python`; override it with
`PYTHON=/path/to/project/python` when needed. The build first checks Python and
dependency minimum versions and fails with an actionable message if the wrong
environment is active.

Build the separate anonymous supplement with `make anonymous-supplement`. Its
manifest hashes every archive member and its auditor rejects Git metadata,
identity-bearing paths/remotes, unsafe paths, missing raw roots, and hash drift.
