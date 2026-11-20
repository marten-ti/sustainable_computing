# Preliminary results — 19 November 2026

32 completed baseline runs, eight per duration, with three concurrent Locust shoppers and no think-time pauses. The fixed-seed workload browsed products, added items to carts and performed mock checkouts. Measured windows total 30 minutes; the campaign took about 44 minutes including loaded warm-up and guard phases. There were **562,888 completed Locust HTTP operations and zero failures**.

| Duration | Mean CPU package energy | Across-run CV |
|---|---:|---:|
| 15 s | 631.4 J | 0.21% |
| 30 s | 1,268.3 J | 0.86% |
| 60 s | 2,529.3 J | 0.39% |
| 120 s | 5,055.0 J | 0.55% |

Longer runs consumed about eight times as much measured energy at 120 seconds versus 15 seconds, without a consistent improvement in CV. Throughput stayed around 313 operations/s and mean package energy was about 0.135 J/operation. These data do not support assuming that longer runs are always more stable. The secondary application-attribution estimate had its lowest CV at 60 seconds (0.54%), so the apparent best duration also depends on the metric; it is not an independent hardware measurement.

The four predefined n=4 baseline-versus-baseline checks produced no false alarms, but four comparisons cannot establish a false-alarm rate below 5%. Conditional models of +5% to +30% energy increases gave 100% detection for n=3 or n=4 per variant at all tested durations. These are saturated planning simulations from the same eight baseline observations, not actual regression experiments. With this exact unpaired permutation test, n=2 cannot reject at 5% because its smallest p-value is 1/6.

**15 seconds is a candidate for independent follow-up, not a validated minimum.** No actual regression variant was tested. Only three energy samples fall inside a 15-second window. The generator shared the measured host, and the application stayed deployed and warm throughout. Node energy includes host/generator overhead; pod energy is an attribution estimate. True per-request energy p95 is unavailable, so reports explicitly use a roughly five-second interval energy/operation proxy.

The controller corrected a cutoff problem found during calibration by holding load constant for an excluded 11-second guard beyond every cutoff. Earlier data remain in calibration_v1 and were excluded before final collection. All final runs passed independent count/timing/energy audits. The application deployment spec was unchanged, all pods and scrape targets were healthy, and Locust stopped after the last run.

See REPORT.md for methods, confidence intervals, limitations and next experiments; figures/report.pdf for charts; results/ for CSVs and raw evidence. No CI/CD pipeline or artificial regression was introduced.
