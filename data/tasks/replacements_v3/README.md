# Replacement v3 evaluator source

Coordinator/evaluator access only. `replacement_candidates.v3.json` contains
gold claims, evaluator action rules, and exact success predicates. It must not
be distributed to annotators A/B.

The 63 records are unsealed replacement candidates (35 IT, 23 procurement,
and 5 commerce), not frozen test data. Rebuild and audit them without model
calls using:

```bash
PYTHONPATH=src python3.13 scripts/generate_replacements_v3.py
PYTHONPATH=src python3.13 scripts/generate_replacements_v3.py --verify-only
```

Only the JSON packets in `data/annotations/replacement_packets_v3/` are the
blind annotator-facing views. The manifest records source and packet-set hashes.
