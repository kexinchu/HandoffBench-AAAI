# Receiver-model development gate

Date: 2026-07-18. Scope: four counterfactual **development** tasks under Gold
Oracle transfer, seed 404, at most four receiver turns, and a common 1,600-token
output cap. No candidate task was called.

The gate asks whether a receiver can use perfect boundary state. A model that
fails most oracle episodes would make transfer-view comparisons floor-dominated
and is not admitted to the confirmatory matrix.

| Model | Distinct family | Oracle success | Protocol outcome |
|---|---|---:|---|
| Qwen2.5-14B-Instruct | Qwen | 23/24 on full dev | retained development model |
| Qwen3.5-9B | Qwen | 23/24 on full dev | retained development model; not an independent family |
| Llama-3.1-8B-Instruct | Llama | 2/4 | rejected in earlier gate |
| Mistral-7B-Instruct-v0.3 | Mistral | 0/4 | rejected; state F1 was 1.0 but workflow use failed |
| DeepSeek-R1-Distill-Llama-8B | Llama-derived | 1/4 | rejected; two strict-schema failures |
| Phi-3.5-MoE mixed AutoRound | Phi | 0/4 | rejected; 4/4 JSON outputs truncated at the common cap |
| Ministral-3-14B-Instruct-2512 | Mistral | 4/4 | passed; exact Apache-2.0 snapshot retained for full development evaluation |

The Mistral outcome is a useful construct check: perfect first-probe state does
not imply successful utilization. It is not evidence about benchmark
prevalence. The Phi model is not rescued by increasing only its output budget,
because the confirmatory comparison requires a common post-handoff budget.

Ministral-3-14B is the first installed non-Qwen family to clear the receiver
gate. It was downloaded from the official `mistralai/Ministral-3-14B-Instruct-2512`
Apache-2.0 repository and served in language-model-only mode. The exact local
snapshot and Qwen2.5-14B snapshot remain provisional until their file hashes,
serving arguments, and final condition/config hashes are embedded atomically in
the sealed design. `execution_authorized` remains false; passing a development
gate does not authorize candidate calls.
