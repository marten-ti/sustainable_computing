# Poster text and references

## Suggested title

**Longer Tests, Better Measurements?**

*A preliminary study of energy variability across benchmark durations*

## Motivation

As software energy efficiency gains attention, energy regression testing (ERT) offers a way to detect unintended increases in energy consumption within CI/CD pipelines [1]. Our goal is to detect small regressions reliably while keeping false alarms low. However, variability in execution conditions and energy measurements can obscure these changes [2]. Longer benchmarks may improve precision, but also increase pipeline latency, resource use and testing energy. We investigate benchmark duration to inform an economical testing strategy.

## Research questions

**RQ1:** How does benchmark duration affect the reliability of detecting energy regressions in CI/CD pipelines?

**H1:** Increasing benchmark duration reduces relative variability in energy measurements and improves regression detection, while increasing execution time and testing energy consumption.

**RQ2:** Which combination of benchmark duration and number of repetitions minimizes testing cost while achieving reliable energy regression detection?

Reliable means at least 80% detection for a specified regression size with at most 5% false alarms. Cost includes total execution time and energy, including warm-up and other testing overhead. These are research targets, not established results.

## Source of energy data

Kepler CPU-package energy counters, collected by Prometheus every five seconds.

Node-level energy and estimated energy attributed to Online Boutique pods.

## Metrics

Energy/run (J), across-run SD and CV, and energy/request (J/request).

Request failure rate (%), p95 response time (ms), and total test execution time (s).

## Preliminary results

We evaluated four benchmark durations—15, 30, 60 and 120 seconds—with eight repetitions each, yielding 32 runs. Each used three concurrent simulated users without think-time pauses. Duration order was randomized within each repetition block. Across measured windows, 562,888 HTTP operations completed with zero failures.

Longer benchmarks did not consistently reduce relative variability. Application-attributed energy had its lowest CV at 60 seconds (0.54%), compared with 0.74%, 1.08% and 0.68% at 15, 30 and 120 seconds. Mean energy per run increased approximately proportionally with duration. The data do not establish a minimum reliable duration or actual regression detection rates.

Next, we will test longer durations and more repetitions to assess whether variability eventually decreases consistently, and whether any stability gains justify the additional time and energy cost.

## Conclusion

Detecting unintended increases in software energy consumption supports integrating energy efficiency into continuous integration [1]. Our preliminary measurements show that longer benchmarks consume more time and energy without consistently improving measurement stability. Further experiments are needed to identify when additional testing provides sufficient benefit to justify its cost.

## Graph caption

Each dot is one run's attributed application CPU-package energy, expressed as percentage deviation from the mean at the same duration. Boxes show the middle 50% and median; whiskers span the observed range. Dashed zero denotes the mean. Application attribution is estimated rather than independently metered.

## References

[1] B. Danglot, J.-R. Falleri and R. Rouvoy. *Can We Spot Energy Regressions using Developers Tests?* 2021 preprint. https://arxiv.org/abs/2108.05691

[2] L. Ardito, R. Coppola, M. Morisio and M. Torchiano. *Methodological Guidelines for Measuring Energy Consumption of Software Applications.* Scientific Programming, 2019, article 5284645. https://doi.org/10.1155/2019/5284645

[3] Google Cloud. *Online Boutique / microservices-demo.* Application revision `5f4ccc7d1c4312c72e97cba777c4f6a586026e59`. https://github.com/GoogleCloudPlatform/microservices-demo

[4] Kepler. *Metrics documentation.* Consult the recorded metric configuration and software version when reproducing this study. https://sustainable-computing.io/kepler/design/metrics/

Use numbered citations in poster text and a compact reference list. A QR code may link to this repository for methods, data and the full bibliography.
