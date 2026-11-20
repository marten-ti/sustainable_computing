# Suggested poster captions

**01 — Application energy attribution.** Eight baseline repetitions per duration, using three concurrent Locust shoppers without think-time pauses. Each point is the CPU-package energy attributed by Kepler to Online Boutique pods, expressed as deviation from its duration's mean. Points use one color; the simplified artwork omits block coloring and CV labels. Boxes show quartiles and median; whiskers span the observed range. Attribution is estimated, not independently metered application energy.

**02 — Node CPU-package energy distribution.** The same 32 runs, using package-energy counter deltas instead of workload attribution. The generator and monitoring shared the node. The tight 15-second distribution was observed with only three native energy samples per window and requires independent validation.

**03 — Measured energy cost.** CPU-package energy over the measured windows, with all eight observations per duration and mean ± one run SD. Extending the window from 15 to 120 seconds consumed 8.01 times as much measured energy. Longer windows also completed more requests; warm-up, guard and CI/CD deployment costs are excluded.

**04 — Stability versus duration.** Across-run energy CV for node package energy and estimated application attribution, with approximate bootstrap 95% intervals. Variability did not decline monotonically with duration in this pilot. The sample does not establish a shortest reliable regression-detection duration.

**Planned BPMN pipeline.** Proposed manually triggered workflow for versioned builds, controlled deployment, sequential randomized trials, parallel external load generation and telemetry capture, quality validation, A/A and A/B comparison, and artifact publication. Quiet references and measurement cutoffs are explicit. Build/CI integration and actual regression variants are future work; the diagram is a design, not a record of an implemented pipeline.
