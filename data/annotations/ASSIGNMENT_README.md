# Candidate double-annotation assignments

Generate blank assignments from the blinded candidate packets with:

```bash
PYTHONPATH=src python3.13 scripts/generate_annotation_assignments.py \
  --packet-dir data/annotations/candidate_packets_v1 \
  --output-dir data/annotations/assignments_v1 \
  --seed 20270117
```

The output contains two annotator-specific files. Both cover every packet once,
but use independently randomized orders and unrelated opaque assignment IDs.
`response` is deliberately `null`: generation performs no annotation. Annotators
receive only their own assignment file, the referenced candidate packets, the
blank annotation template, and the annotation protocol. They must not exchange
files or inspect model outputs, candidate source files, evaluator code, or another
annotator's responses.

The manifest preassigns no adjudication work. After both independent responses
are locked, a coordinator computes exact disagreements and creates a separate
third-person queue containing only those task IDs. The adjudicator must never be
used as a routine third labeler or see agreement-only tasks. Running the generator
against an existing output directory fails rather than overwriting responses or
previous assignments.

These files are candidate-stage execution assets. Creating them does not annotate,
accept, freeze, seal, or promote any task.
