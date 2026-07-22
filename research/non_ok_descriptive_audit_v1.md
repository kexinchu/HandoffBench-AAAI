# Post-confirmatory non-OK row audit (v1)

Status: **exploratory/descriptive only**. This audit describes the validated v3.4.1 inputs; it does not modify the execution seal, raw runs, sealed confirmatory analyzer, or confirmatory inference.

- Contract: `post_confirmatory_non_ok_audit_v1`
- Seal: `hb-v3.4.1-exec-9671bf1ff2d5-20260721`
- Denominator: 8800 scheduled ITT rows
- Non-OK: 178 (2.02%)
- JSON SHA-256: `554dce91034eac6415272143dc432705572c1a5230ba6ec983483deac29cc85b`

### By model

| Group | Non-OK / total | Rate |
|---|---:|---:|
| ministral3-14b-2512 | 97 / 4400 | 2.20% |
| qwen2.5-14b | 81 / 4400 | 1.84% |

### By condition

| Group | Non-OK / total | Rate |
|---|---:|---:|
| free_form__absent__absent__advisory | 22 / 800 | 2.75% |
| free_form__absent__executable__advisory | 19 / 800 | 2.38% |
| free_form__trace_linked__absent__advisory | 28 / 800 | 3.50% |
| free_form__trace_linked__executable__advisory | 30 / 800 | 3.75% |
| full_history | 10 / 800 | 1.25% |
| gold_oracle | 0 / 800 | 0.00% |
| typed__absent__absent__advisory | 15 / 800 | 1.88% |
| typed__absent__executable__advisory | 13 / 800 | 1.62% |
| typed__trace_linked__absent__advisory | 13 / 800 | 1.62% |
| typed__trace_linked__executable__advisory | 13 / 800 | 1.62% |
| typed__trace_linked__executable__enforced | 15 / 800 | 1.88% |

### By recorded failure stage

| Group | Non-OK / total | Rate |
|---|---:|---:|
| receiver_action_validation | 75 / 75 | 100.00% |
| receiver_output_parse | 8 / 8 | 100.00% |
| receiver_state_validation | 86 / 86 | 100.00% |
| source_transfer_parse | 9 / 9 | 100.00% |

### By recorded error type

| Group | Non-OK / total | Rate |
|---|---:|---:|
| JSONDecodeError | 8 / 8 | 100.00% |
| ValueError | 170 / 170 | 100.00% |

### By typing factor

| Group | Non-OK / total | Rate |
|---|---:|---:|
| free_form | 99 / 3200 | 3.09% |
| not_applicable | 10 / 1600 | 0.62% |
| typed | 69 / 4000 | 1.73% |

### By provenance factor

| Group | Non-OK / total | Rate |
|---|---:|---:|
| absent | 69 / 3200 | 2.16% |
| not_applicable | 10 / 1600 | 0.62% |
| trace_linked | 99 / 4000 | 2.48% |

### By checks factor

| Group | Non-OK / total | Rate |
|---|---:|---:|
| absent | 78 / 3200 | 2.44% |
| executable | 90 / 4000 | 2.25% |
| not_applicable | 10 / 1600 | 0.62% |

### By enforcement factor

| Group | Non-OK / total | Rate |
|---|---:|---:|
| advisory | 153 / 6400 | 2.39% |
| enforced | 15 / 800 | 1.88% |
| not_applicable | 10 / 1600 | 0.62% |

## ITT treatment

Every non-OK row remains in the formal denominator. Under the sealed analyzer, it receives zero strict-success and macro-state-F1 credit; this was independently checked here against all non-OK records. The table is descriptive and has no p-values, confidence intervals, or multiplicity claims.

## Provenance

- Sealed manifest SHA-256: `a51d810927620ced84acc800991db55226645d7a234d58737ba4506e50df2b3b`
- Canonical dataset SHA-256: `9671bf1ff2d507e31a62069bbd655b83f53803aeee3a5b5908da7b8d9d892a93`
- Audit script SHA-256: `f390337e4033a143d85d1e7e55adecd8ed00193a07661eb9034a536fb2ee4c9a`
- Audit module SHA-256: `52d92f1c15853dd2834c5547bf10286aef506db3463ce222eee0d7fe1a5b17ec`
