# Confirmatory v2 execution dry-run contract

This document and its companion config are planning assets only. The final
pre-freeze analysis contract is `research/preregistration_v3.md`; earlier
versions remain historical records. These assets do not
seal the candidate pool and do not authorize any model/provider request.

## Fail-closed preflight

`python scripts/preflight_confirmatory.py --config configs/confirmatory_v2.yaml`
must exit nonzero until all of the following independently exist and validate:

1. the three candidate files contain exactly 200 unique families, 40/domain;
2. a sealed manifest contains the exact task IDs and canonical task hashes;
3. independent human annotation is complete with at least two annotators/task,
   adjudication complete, accepted IDs exactly matching the manifest, and an
   explicit agreement gate pass;
4. every model uses a resolved provider and immutable snapshot ID;
   `configs/confirmatory_v2_model_snapshots.json` must also match every local
   config/tokenizer/chat-template/weight file byte-for-byte and bind serving args;
5. `execution_authorized` is changed only after the sealed artifacts pass
   institutional/project authorization.

The current repository deliberately lacks the sealed manifest/agreement assets
and sets `execution_authorized: false`; therefore current preflight must fail.
Model file hashes are evaluated only after those cheaper gates pass, but any
subsequent byte, file-set, metadata, or serving-argument drift closes preflight.

## Resume and invalid isolation

Each scheduled cell is content-addressed by protocol, sealed-manifest hash,
task hash, exact model snapshot, seed, condition, prompt/schema hashes, and
generation budget. Existing complete artifacts are skipped. Provider/schema/
parse failures are immutable ITT artifacts with zero success/state credit and
are never silently retried into success. A separately authorized missing-call
completion run may create a new attempt ID while preserving the failed attempt.

Artifacts whose manifest, prompt, schema, model snapshot, or protocol hash does
not match the sealed execution go only to `outputs/confirmatory_v2_invalid/`.
Invalid/development directories are excluded by manifest, never by manual table
selection. Summary generation occurs only after workers finish and reads only
manifest-listed artifacts.

## Call and cost envelope

There are 800 task/model/seed blocks. The primary design has eight factorial
and two control receiver runs/block; enforced all-on adds one secondary run.
One matched source artifact is generated/block and reused across the factorial.
This yields 8,800 receiver runs, 800 source generations, 9,600 minimum provider
calls, and 34,000 maximum calls at four receiver turns. These are an envelope,
not a spending estimate. At the configured 1,600-token response cap, the purely
mechanical maximum requested output envelope is 54.4M tokens; it is not an
expected consumption value. Expected input tokens remain unset until frozen
prompts are measured, and monetary cost remains unset until exact model snapshots
and a dated pricing record exist. Actual input/output tokens, failures, and pricing
snapshot are recorded under `confirmatory_cost_accounting.schema.json`; costs
must never be inferred from maximum output tokens alone.
