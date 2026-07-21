# HandoffBench confirmatory execution amendment v3.4

Status: prospective execution amendment recorded on 2026-07-21 before any v3.4
provider call. This amendment governs infrastructure recovery only. It does not
change the sealed population, model snapshots, prompts, generation parameters,
seeds, conditions, endpoints, estimands, multiplicity family, or decision rules
in `research/preregistration_v3.md`.

## Reason for the amendment

The v3.3 Qwen service was externally terminated during execution. The objective
timeline is recorded in `research/confirmatory_v3.3_execution_disposition.json`.
The interruption produced six EngineCore HTTP 500 errors followed by 1,670
connection-refused records, with six truncated responses at the failure
boundary. Although all 4,400 scheduled Qwen keys were written, presence of a row
is not evidence of a healthy model call. The v3.3 analyzer mechanically treated
these infrastructure records as ordinary intent-to-treat zeros and produced an
aggregate file before this disposition was written. Those aggregates are
invalid and must not be cited, used in the paper, or used to modify this plan.

The invalidation decision is based on provider errors and independently logged
process termination, not on condition-level outcomes or effect estimates.

## Locked replacement rule

The entire v3.3 Qwen model arm is excluded, including its 2,645 rows marked
`ok`. No v3.3 Qwen source artifact, successful row, failed row, summary, or
analysis value may be copied, resumed, or imported. The replacement executes
the original complete product:

```
200 tasks x 2 seeds x 11 conditions = 4,400 Qwen rows
```

The replacement uses a new output root that must not exist when execution
starts. A non-empty root closes preflight. Any interruption of v3.4 invalidates
that attempt; continuation or row-level retry is forbidden and would require a
new prospective execution seal and another fresh root.

The completed v3.3 Ministral arm is retained byte-for-byte and is not rerun
after aggregate inspection. Final analysis may combine only the retained 4,400
Ministral rows bound by the disposition record with the new 4,400-row v3.4
Qwen arm. It must reject the original v3.3 Qwen directory and any duplicate,
foreign, resumed, missing, or infrastructure-failure row.

## Infrastructure isolation and acceptance gates

The Qwen server is restricted to the sealed GPU UUID in the v3.4 config and is
started under an exclusive advisory lock. Before startup, the selected GPU and
port must be unused. During execution, a watchdog records the GPU process set
and endpoint health; a competing GPU process, service restart, missing endpoint,
HTTP 5xx, EngineCore failure, OOM, timeout, connection reset, or connection
refusal invalidates the entire v3.4 attempt.

Before analysis, the following must all hold:

1. the v3.4 ledger reports 4,400 scheduled, 4,400 written, and zero resumed;
2. the 4,400 schedule keys are unique and exactly match the sealed Qwen arm;
3. the dataset, model, prompt, schema, generation, design, and RunConfig hashes
   match the v3.4 seal;
4. the provider identity is `qwen2.5-14b` throughout and the infrastructure
   audit contains no prohibited event;
5. model/schema/parse failures remain immutable ITT rows, but no provider or
   infrastructure failure is present; and
6. combined analysis receives exactly the retained Ministral directory and the
   replacement Qwen directory, producing 8,800 unique rows.

This amendment is prospective relative to every replacement call but is not
represented as having preceded the mechanically generated, invalid v3.3
aggregate. That chronology is preserved for auditability.
