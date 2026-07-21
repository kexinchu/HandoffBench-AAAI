# Replacement v3 Disagreement-Only Adjudication

Status: adjudicated subset, unsealed.

- Compared tasks in locked inputs: 63
- Queue coverage: 47/47 entries, exactly once
- Queue-addressed tasks adjudicated: 47
- Agreement-only tasks intentionally not opened: 16
- Rejected tasks: 0
- Adjudicator: `adjudicator_c`

## Resolution counts

- `ACCEPT_A`: 47

## Decision rule

All queued disagreements concern `operation_scope_ref`: both annotators agree on its identity, `constraint` category, known typed value, and provenance. It determines the requested operational scope and terminal validity, whereas a separate `authorization_state` claim carries the authority/safety gate. Therefore all 47 entries resolve to A's `terminal` criticality.

## Source integrity

- Annotator A SHA-256: `f2b8e0c76741c5b2856199369e4eb6f3030f16da0959ac411618d651c913e825`
- Annotator B SHA-256: `036b01dd96125685d19c8554c7b6c3371455d3a1580e90e37cd9bcc1ded55e6b`
- Lock manifest SHA-256: `850194d41103e35cc6c35a0b86a0297e498a84fb78eab3785e6e6f1b769a9ace`
- Disagreement queue SHA-256: `dccbe9e2f8b193fc2eb92029225a0ab8ba1c74abab4bd0655f210b2a22aaeaf6`
