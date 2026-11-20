# Preliminary study metrics

Eight repetitions per duration; three concurrent users, no think time. These values come from `results/duration_summary.csv`.

| Metric | 15 s | 30 s | 60 s | 120 s |
|---|---:|---:|---:|---:|
| Repetitions | 8 | 8 | 8 | 8 |
| Mean application-attributed energy (J) | 312.70 | 627.86 | 1,253.34 | 2,503.31 |
| Application energy CV (%) | 0.74 | 1.08 | 0.54 | 0.68 |
| Mean node CPU-package energy (J) | 631.42 | 1,268.33 | 2,529.26 | 5,055.00 |
| Node energy SD (J) | 1.31 | 10.89 | 9.87 | 27.97 |
| Node energy CV (%) | 0.21 | 0.86 | 0.39 | 0.55 |
| Mean package power (W) | 42.09 | 42.28 | 42.15 | 42.12 |
| Within-run power SD, averaged (W) | 0.24 | 0.34 | 0.35 | 0.31 |
| Mean throughput (HTTP operations/s) | 313.21 | 313.09 | 312.95 | 312.44 |
| Throughput CV (%) | 0.19 | 0.28 | 0.17 | 0.20 |
| Total HTTP operations | 37,585 | 75,142 | 150,216 | 299,945 |
| Failure rate (%) | 0 | 0 | 0 | 0 |
| Mean of per-run p95 response times (ms) | 12.37 | 12.39 | 12.38 | 12.43 |
| Mean node energy/operation (J) | 0.1344 | 0.1350 | 0.1347 | 0.1348 |
| p95 interval energy/operation proxy (J) | 0.1354 | 0.1367 | 0.1365 | 0.1365 |
| Mean measured duration (s) | 15.0003 | 30.0006 | 60.0004 | 120.0004 |
| Mean elapsed time incl. startup/warm-up/guard (s) | 41.48 | 56.49 | 86.53 | 146.57 |
| Native energy samples in measured window | 3 | 6 | 12 | 24 |

SD is sample standard deviation across repetitions unless marked within-run. CV = 100 × SD / mean. Energy is CPU-package energy, not wall-socket electricity. Application energy is a Kepler attribution estimate. The node includes generator and host overhead.

The p95 interval proxy is the mean of per-run 95th percentiles of approximately five-second energy/operation ratios. It is not individual-request p95 energy. Elapsed time includes startup, warm-up and guard; reported energy excludes those phases, so total pipeline energy overhead has not yet been quantified.

No actual regression variant was tested. Four predefined A/A checks gave zero false alarms; that sample is insufficient to establish a population false-alarm rate below 5%. Conditional sensitivity simulations are not observed detection reliability.
