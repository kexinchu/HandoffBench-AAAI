# Annotation provenance correction v1

Correction date: 2026-07-22. Status: **post-seal metadata correction**.

The sealed composite agreement artifact states that “Human annotations were the
only semantic decisions.” That statement is incorrect. The original and
replacement packets were labeled by two isolated LLM-agent roles, with a
separate disagreement-only LLM-agent adjudication role. No recruited human
annotators performed the recorded A/B labels or adjudications.

The exact underlying annotation model and runtime were not recorded in the
locked response artifacts. Consequently, agreement statistics quantify
replication across isolated agent roles; they are not evidence of human
agreement or human-grounded construct validity. Any future claim of human
validation requires a separately documented human audit, including recruitment,
training, consent/IRB disposition, compensation where applicable, protocol, and
locked responses.

This correction changes no task, label, dataset byte, model run, statistical
estimate, or execution/analysis seal. The original sealed artifact is retained
unchanged to preserve hash integrity. The machine-readable correction is
`research/annotation_provenance_correction_v1.json`; manuscripts and current
status documents must cite the corrected provenance rather than repeat the
sealed artifact's inaccurate wording.
