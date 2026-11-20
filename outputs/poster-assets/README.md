# Print-ready poster assets

Four measured-data figures and a newly drawn BPMN diagram of the **planned** pipeline. The application-energy plot is supplied as its own figure. No new benchmarks were run for these assets.

## Files to use in the poster

Use **PDF or SVG** in the poster layout whenever possible: they are vectors and remain sharp when scaled. The PDFs contain embedded TrueType fonts; SVG text is converted to vector outlines so a print shop does not need the same installed fonts. Python source and CSV data are included for changing labels, colors or layout.

All full-resolution PNGs are **600 DPI at their native physical size**. The small images in `previews/` are for on-screen review only.

| Asset | Native size | Full PNG pixels | Formats |
|---|---|---|---|
| 01 Application energy distribution | 304.8 × 223.5 mm | 7200 × 5280 | PDF, SVG, PNG |
| 02 Node energy distribution | 304.8 × 223.5 mm | 7200 × 5280 | PDF, SVG, PNG |
| 03 Energy cost | 304.8 × 223.5 mm | 7200 × 5280 | PDF, SVG, PNG |
| 04 Stability versus duration | 304.8 × 223.5 mm | 7200 × 5280 | PDF, SVG, PNG |
| Planned pipeline | 609.6 × 254.0 mm | 14400 × 6000 | PDF, SVG, PNG, editable BPMN |

For an A0 poster (841 × 1189 mm), the graphs work well as roughly 28–36 cm-wide panels. The pipeline works best across the poster width. Even the pipeline PNG retains about 308 effective DPI if stretched to the full 1189 mm width of landscape A0; the vector version avoids resolution limits altogether. Final text size still depends on placement scale. Do not use chat screenshots or the preview images as print masters.

`all_poster_assets.pdf` combines the five vector PDFs into a convenient review booklet; its pages retain the figures' native sizes. This is an asset collection, not a completed A0 poster layout.

## Scientific meaning

- **Application distribution:** all eight baseline repetitions per duration, centered on their own duration mean. This is estimated CPU-package energy attributed to Online Boutique pods by Kepler. It is not an independently measured pod energy sensor. The application plot uses one point color and omits the block color scale, CV labels and explanatory captions. The y-axis is 100 × (run energy − mean energy at the same duration) / that mean. Box = quartiles, line = median, whiskers = observed min/max; there is no fitted normal/violin distribution.
- **Node distribution:** the same runs using total CPU-package energy. The generator shared the measured host. These are not whole-server wall-power measurements.
- **Energy cost:** all observed package-energy totals, mean and one run SD. Longer windows complete more work under fixed concurrency; this is not a fixed-work efficiency experiment. Warm-up/guard energy is excluded.
- **Stability:** CV and approximate percentile-bootstrap 95% intervals, n=8 per duration. The non-monotonic pattern is a finding from one pilot session; no minimum reliable duration or actual regression-detection performance was established.

The reported results use the original 32-run baseline campaign and are unchanged. `data/` includes the source CSVs. Figures intentionally label attribution and uncertainty. `CAPTIONS.md` provides suggested poster captions.

## BPMN design

`pipeline/planned_pipeline.bpmn` is a BPMN 2.0 XML model with diagram interchange/layout, intended for editing in a BPMN modeler such as bpmn.io or Camunda Modeler. It is marked `isExecutable=false`: it documents the proposed workflow and does not deploy or run a CI/CD pipeline.

The flow adapts the reference workflow's build/deploy → parallel load/telemetry → join → collect/analyze structure, adding the research controls specified in the research protocol:

1. Manual dispatch; record configuration, environment and pipeline timing.
2. Build the requested revision(s) and publish pinned images to a versioned local registry.
3. Execute the randomized variant × duration × repetition plan **sequentially**, avoiding overlapping trials on the measured node.
4. Deploy/check readiness and smoke-test each pinned variant; take quiet references; run external Locust and telemetry capture concurrently; retain the loaded guard and align the analysis cutoffs.
5. Validate metrics, requests and trial quality. A failure signals `INVALID_TRIAL`, interrupting the trial subprocess and producing diagnostics rather than a statistical regression verdict.
6. Aggregate A/A and actual A/B results; report CV, detection and false alarms; publish artifacts, pipeline timings and job status. Pass/fail/inconclusive interpretation belongs to the eventual predeclared decision policy.

The diagram shows a conservative quiet reference before and after each trial; cadence and duration are a proposed design choice. If the final experiment measures quiet windows only at block boundaries, update that part of the model to match. Warm-up/guard durations, n and workload parameters are configuration inputs, not fixed numbers baked into the diagram. Build/registry/CI integration and controlled A/B variants are planned work; the current implementation is the local pilot.

BPMN conventions: solid control-flow arrows; dotted artifact associations; `+` diamonds for parallel split/join; three horizontal bars for sequential multi-instance repetition; an interrupting error boundary event for trial-quality failures. The raw data object and versioned registry follow the data-artifact idea in the user's reference image.

Notation sources: [OMG BPMN 2.0.2 schemas](https://www.omg.org/spec/BPMN/machine-readable), [parallel gateways](https://docs.camunda.io/docs/components/modeler/bpmn/parallel-gateways/), [multi-instance activities](https://docs.camunda.io/docs/components/modeler/bpmn/multi-instance/). The validation report records schema and file checks.

## Regenerate

Install `source/requirements.txt` in a Python environment (the assets were generated with Python 3.13). The scripts use Matplotlib, NumPy and pandas. Run with the workspace Python environment already used for the experiments:

```sh
python source/create_graphs.py
python source/create_pipeline.py
```

`source/validate_assets.py` additionally needs Pillow, pypdf and lxml. It checks PNG resolution, vector PDF/SVG content, font embedding, BPMN schema/graph structure and data consistency. Official schemas used for validation are in `source/bpmn-schema/`.

The Python scripts are the source for the supplied print artwork. Editing only the BPMN model does not automatically rewrite the supplied PDF/SVG; export again from the modeler, or update and regenerate the Python artwork for matching styling.
