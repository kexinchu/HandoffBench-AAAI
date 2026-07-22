# Release scope and licensing decision record

The repository now uses Apache-2.0 for project-authored software and CC BY 4.0
for project-authored synthetic benchmark data and released evaluation outputs.
The authoritative terms and scope exclusions are `LICENSE`, `DATA_LICENSE.md`,
`NOTICE`, and `THIRD_PARTY_NOTICES.md`. This document is a release-scope guide,
not a replacement for those terms.

Applied release partition:

| Material | License family | Notes |
| --- | --- | --- |
| Project-authored Python code and scripts | Apache-2.0 | Includes an explicit patent grant. |
| Project-authored synthetic tasks, labels, and aggregate/raw results | CC BY 4.0 | Requires attribution and indication of changes. |
| Manuscript source and PDF | Publication-specific terms | Excluded from the code/data grants. |
| AAAI author kit and other third-party materials | Original upstream terms | Do not relicense or imply ownership. |
| Model weights and providers | Upstream terms | This project does not redistribute model weights. |

Before public release, owners should still confirm all contributor and
institutional rights, preserve the included notices, update the repository
README if scope changes, and publish a versioned raw-record archive. Third-party
terms remain upstream; the project grants no rights in model weights or names.
