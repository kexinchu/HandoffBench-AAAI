# HandoffBench confirmatory power simulation

This is a pre-freeze planning simulation, not experimental evidence. The independent sample
unit is the task family. Model and seed repetitions are averaged within family and never
counted as independent samples.

## Assumptions

- Analysis: paired family-cluster percentile bootstrap.
- Baseline success planning value: 0.550.
- Models per family: 2; seeds per model/family: 1.
- Two-sided alpha: 0.05; RNG seed: 270127.
- ICC: logistic random intercept; residual variance pi^2/3.
- DGP: conditional treatment probability = min(control probability + absolute effect, 1).
- The baseline rate/effect/ICC grid must be justified from development data and locked before test.

## Estimated power

| N families | ICC | Target Δ | Simulated Δ | Discordance | Power | MC SE |
|---:|---:|---:|---:|---:|---:|---:|
| 80 | 0.05 | 0.05 | 0.050 | 0.465 | 0.144 | 0.011 |
| 120 | 0.05 | 0.05 | 0.047 | 0.463 | 0.189 | 0.012 |
| 160 | 0.05 | 0.05 | 0.050 | 0.462 | 0.261 | 0.014 |
| 200 | 0.05 | 0.05 | 0.050 | 0.461 | 0.308 | 0.015 |
| 80 | 0.10 | 0.05 | 0.049 | 0.446 | 0.139 | 0.011 |
| 120 | 0.10 | 0.05 | 0.049 | 0.444 | 0.207 | 0.013 |
| 160 | 0.10 | 0.05 | 0.050 | 0.445 | 0.250 | 0.014 |
| 200 | 0.10 | 0.05 | 0.051 | 0.446 | 0.327 | 0.015 |
| 80 | 0.20 | 0.05 | 0.050 | 0.411 | 0.177 | 0.012 |
| 120 | 0.20 | 0.05 | 0.051 | 0.412 | 0.244 | 0.014 |
| 160 | 0.20 | 0.05 | 0.050 | 0.412 | 0.265 | 0.014 |
| 200 | 0.20 | 0.05 | 0.051 | 0.411 | 0.350 | 0.015 |
| 80 | 0.05 | 0.08 | 0.080 | 0.461 | 0.326 | 0.015 |
| 120 | 0.05 | 0.08 | 0.082 | 0.458 | 0.470 | 0.016 |
| 160 | 0.05 | 0.08 | 0.078 | 0.459 | 0.552 | 0.016 |
| 200 | 0.05 | 0.08 | 0.080 | 0.458 | 0.655 | 0.015 |
| 80 | 0.10 | 0.08 | 0.082 | 0.440 | 0.327 | 0.015 |
| 120 | 0.10 | 0.08 | 0.079 | 0.443 | 0.441 | 0.016 |
| 160 | 0.10 | 0.08 | 0.080 | 0.442 | 0.580 | 0.016 |
| 200 | 0.10 | 0.08 | 0.081 | 0.442 | 0.691 | 0.015 |
| 80 | 0.20 | 0.08 | 0.080 | 0.408 | 0.341 | 0.015 |
| 120 | 0.20 | 0.08 | 0.080 | 0.411 | 0.461 | 0.016 |
| 160 | 0.20 | 0.08 | 0.078 | 0.412 | 0.577 | 0.016 |
| 200 | 0.20 | 0.08 | 0.078 | 0.409 | 0.659 | 0.015 |
| 80 | 0.05 | 0.10 | 0.102 | 0.460 | 0.486 | 0.016 |
| 120 | 0.05 | 0.10 | 0.101 | 0.456 | 0.645 | 0.015 |
| 160 | 0.05 | 0.10 | 0.101 | 0.457 | 0.773 | 0.013 |
| 200 | 0.05 | 0.10 | 0.100 | 0.456 | 0.834 | 0.012 |
| 80 | 0.10 | 0.10 | 0.101 | 0.443 | 0.471 | 0.016 |
| 120 | 0.10 | 0.10 | 0.099 | 0.440 | 0.633 | 0.015 |
| 160 | 0.10 | 0.10 | 0.100 | 0.441 | 0.760 | 0.014 |
| 200 | 0.10 | 0.10 | 0.100 | 0.442 | 0.847 | 0.011 |
| 80 | 0.20 | 0.10 | 0.100 | 0.407 | 0.526 | 0.016 |
| 120 | 0.20 | 0.10 | 0.099 | 0.408 | 0.666 | 0.015 |
| 160 | 0.20 | 0.10 | 0.101 | 0.409 | 0.788 | 0.013 |
| 200 | 0.20 | 0.10 | 0.099 | 0.407 | 0.879 | 0.010 |

## Interpretation constraints

Power depends on the assumed baseline, discordance, effect model, ICC, and model heterogeneity.
Seeds reduce Monte Carlo noise but cannot replace independent families. This simulation does not
authorize optional stopping or sample-size changes after inspecting confirmatory outcomes.
