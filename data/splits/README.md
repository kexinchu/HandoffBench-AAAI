# Confirmatory split manifests

`confirmatory_v3.1.sealed.json` is the active immutable HandoffBench freeze.
It binds the 200-task dataset, final human agreement, static audit, protocol and
implementation files, design matrix, and the provider-aware model snapshot
manifest.

`confirmatory_v3.sealed.json` is retained as an unsuccessful sealing attempt.
Its subsequent preflight exposed a tooling mismatch: preflight required a
provider field that the snapshot-manifest generator did not yet emit. No task or
model output changed. The generator was corrected, the current snapshot was
rehash-verified, and a new non-overwriting v3.1 seal was created. The v3.1
agreement records this supersession explicitly.

The active configuration keeps `execution_authorized: false`; a sealed dataset
does not itself authorize confirmatory model calls.
