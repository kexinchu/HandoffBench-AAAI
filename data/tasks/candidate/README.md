# Candidate confirmatory tasks — not frozen

These 200 tasks are generated candidates, not a test split. No model evaluation
may be run on them until all gates below pass. Any task inspected through model
outputs becomes development data and must be replaced before freezing.

Required gates:

1. Two blinded annotators independently reconstruct gold claims and legal action
   sequences; a third person adjudicates disagreements.
2. Every task passes schema, provenance, exact-oracle, argument-grounding,
   catalog permutation, shallow leakage, ontology, and mutation audits.
3. Task-family, entity-pool, lexical, and workflow-automaton overlap with all
   development data is measured and resolved.
4. Rejected or materially edited tasks are regenerated before any model call.
5. The final task file and protocol files are sealed with `freeze_split.py`; the
   manifest is never overwritten.

After the locked agreement artifact has been assigned an external unique seal
ID, the multi-file sealing command is:

```bash
python scripts/freeze_split.py --seal \
  --candidate-files data/tasks/candidate/travel_commerce.json \
                    data/tasks/candidate/procurement_it.json \
                    data/tasks/candidate/scheduling.json \
  --config configs/confirmatory_v2.yaml \
  --agreement annotations/confirmatory_v2/agreement.json \
  --seal-id <locked-unique-id> --sealed-at <UTC-ISO-8601> \
  --output data/splits/confirmatory_v2.sealed.json
```

The command refuses overwrite and binds every candidate file, accepted task,
agreement artifact, preregistration v3, protocol schema, confirmatory design,
model design, and model snapshot manifest. Do not run it until the preceding
human and overlap gates are complete. A successful seal still does not authorize
execution; the independent fail-closed preflight must also pass.

Current files contain 40 candidates per domain. Their generator versions and
tests deliberately retain the word `candidate` to prevent accidental claims of
confirmatory evidence.

See `research/candidate_v2_datasheet.md` for composition, provenance, limitations,
licensing status, risks, and prohibited uses. See
`research/candidate_v2_annotation_execution_guide.md` for the planned packet-to-CSV
workflow. The existing `candidate_packets_v1` and `assignments_v1` contain only
120 tasks and do not establish annotation coverage for this 200-task candidate
version.
