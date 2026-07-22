# Anonymous code and data supplement

This archive is an analysis-reproduction package for anonymous AAAI review. It
contains the frozen v3.4.1 execution manifest, the 200 synthetic task records,
all 8,800 sealed raw run records, validation and analysis source, runtime
metadata, and the reported aggregate JSON artifacts. It contains no model
weights and makes no provider call.

The raw records are losslessly nested as `raw_runs.tar.xz` so compression can
share context across JSON files and leave safe upload-size headroom. Their paths
and bytes are unchanged. From the extracted archive root, unpack them with
Python's standard library, install the package dependencies, and run:

```bash
python -m tarfile -e raw_runs.tar.xz .
```

```bash
PYTHONPATH=src python scripts/analyze_confirmatory.py \
  --sealed-manifest data/splits/confirmatory_v3.4.1.execution.anonymous.json \
  --raw-run-dir outputs/confirmatory_v3/ministral3-14b-2512/runs \
  --raw-run-dir outputs/confirmatory_v3.4.1/qwen2.5-14b/runs \
  --output-dir build/recomputed_confirmatory \
  --bootstrap-draws 10000
```

The generated `confirmatory_results.json` must exactly match the released result
SHA-256:

```text
077dd30aae75ff63d4f49594be4419bdc3b6a1df7c63af31e8c3a21a18db2c09
```

Verify it with `sha256sum build/recomputed_confirmatory/confirmatory_results.json`.
Only the separately generated provenance file contains extraction-local paths
and is therefore expected to differ. The archive manifest records SHA-256 values
for every input member. To verify archive integrity before extraction, run
`python scripts/build_anonymous_supplement.py --audit ARCHIVE`.

Local model paths and the private model-snapshot manifest are intentionally
excluded: they are not required to recompute aggregates from sealed raw records,
and would reveal local execution-host details. Deployment identifiers and the
post-run environment snapshot remain available in the supplied public metadata.

The supplied anonymous execution manifest is a mechanically derived
analysis-only view of the byte-exact original seal. It replaces only the
path-bearing `protocol_file_hashes` inventory with an empty map and records the
source seal SHA-256. It is used solely because the original inventory includes
legacy documents with absolute local paths; it does not replace the source seal
or modify its task, design, execution-attempt, or hash-bound raw-run metadata.

The benchmark consists entirely of synthetic task worlds. The frozen A/B labels
and adjudication were produced by isolated LLM-agent roles, not recruited human
annotators. The package therefore supports reproducibility of the reported
evaluation, not a claim of human-grounded label validity.
