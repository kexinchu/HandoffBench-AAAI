# v3.4.1 runtime environment snapshot

Recorded: 2026-07-22, after confirmatory completion, on the execution host.
This is a post-run host snapshot, not a substitute for a container image or a
complete retained-arm environment log.

- Qwen replacement GPU UUID:
  `GPU-474505f8-4b3d-0ba7-65de-8014425baee0`
- GPU mapping at snapshot: NVIDIA RTX A6000, 49,140 MiB; physical device 1.
- Host CPU: Intel Xeon Gold 6338 @ 2.00 GHz, 64 logical CPUs.
- Host RAM: 1.0 TiB.
- Operating system: Ubuntu 22.04.5 LTS.
- Python: 3.13.12.
- PyTorch: 2.10.0+cu128.
- vLLM: 0.19.1.
- Transformers: 5.12.1.

The sealed Qwen serving arguments are in `configs/confirmatory_v3.4.1.yaml`:
host `127.0.0.1`, port `8101`, GPU-memory utilization `.72`, max model length
8,192, max concurrent sequences 8, eager enforcement, and vLLM generation
configuration. Experiment generation used temperature `.7`, maximum output
1,600 tokens, maximum four receiver turns, and seeds 101 and 202.

The retained Ministral arm has a sealed model snapshot, serving arguments,
ledger, and raw-tree hash, but not an equivalently complete run-time package
version snapshot. Reproducibility claims therefore remain partial for computing
infrastructure.
