# AAAI-27 reproducibility checklist draft status

The official AuthorKit checklist was copied without changing its questions into
`paper/ReproducibilityChecklist_draft.tex`; only response placeholders in the
question section were replaced. It is a draft and must be reconciled with the
AAAI-27 submission portal instructions before submission.

The conservative `no` or `partial` answers are intentional:

- Human annotation, adjudication, overlap remediation, candidate sealing, and
  confirmatory evaluation have not happened.
- The repository currently has no declared research-use license, so public
  release-with-license questions cannot be answered yes.
- Full hardware, memory, operating-system, serving-stack, and package-version
  records for every development run are not present.
- Code is in the repository, not literally embedded in a paper appendix.
- Development settings and selection rationale are documented, but not every
  tried parameter value is enumerated in the paper.
- The paper is empirical rather than theoretical; conditional theory questions
  are marked `NA` because they do not apply.

The draft may be upgraded only when the corresponding artifact actually exists.
In particular, do not change dataset/code licensing, infrastructure, annotation,
or confirmatory-evidence answers based on intent alone.

## Offline rebuild

From the repository root, using the project Python environment:

```bash
make submission
```

This runs tests, records environment/package versions and hashes, reconstructs a
machine-readable manifest of the development table sources, builds the paper and
standalone checklist, and audits the PDF log. It performs no provider or model
call and does not modify raw output directories. Generated audit records are
written under `build/reproducibility/`.
The default interpreter is `python`; override it with
`PYTHON=/path/to/project/python` when needed. The build first checks Python and
dependency minimum versions and fails with an actionable message if the wrong
environment is active.
