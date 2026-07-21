# Confirmatory v3.4.1 pre-call startup correction

The tagged v3.4 Qwen replacement seal was exercised on 2026-07-21. The isolated
launcher exited before loading the model, creating the confirmatory output root,
or making any candidate-model call. The local vLLM build attempted to parse the
UUID-valued `CUDA_VISIBLE_DEVICES` string as an integer and raised
`ValueError: invalid literal for int()` during import-time CUDA capability
detection. The startup log had SHA-256
`9edc3b3682816a856b57e1a2f78a8c560aaf4cef448ebe03f8a1603246174596`.

Version v3.4.1 prospectively corrects only the runtime selector from the sealed
GPU UUID string to physical device index `1`. At correction time, `nvidia-smi`
mapped index 1 to the same sealed UUID
`GPU-474505f8-4b3d-0ba7-65de-8014425baee0`. The watchdog continues to identify
and monitor the device by that UUID. The model snapshot, served identity, port,
vLLM arguments, dataset, prompts, generation parameters, seeds, conditions,
RunConfig hashes, required 4,400 rows, estimands, and analysis rules are
unchanged.

The failed startup made zero candidate calls and produced no raw run. The v3.4.1
attempt therefore uses a new attempt ID and fresh output root. It remains
non-resumable: if any raw output is created and the attempt does not pass all
infrastructure gates, a later retry requires another prospective seal.
