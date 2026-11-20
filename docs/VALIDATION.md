# Poster-session validation — 20 November 2026

Validated offline with the existing Python 3.13 research environment:

- Seven measurement checks passed (including interpolation, missing data and counter resets).
- Six statistical checks passed.
- All 32 measured runs passed the saved-data audit: frozen collection-source hashes, request counts/timestamps, energy interval sums, loaded guards and non-overlapping windows.
- Full campaign reanalysis and distribution, active/idle and quiet-reference analyses completed from the included raw data.
- Five PDF/SVG figure masters passed vector/font validation; all print PNGs passed 600-DPI/dimension checks; BPMN passed official schema and structural checks.
- Poster CSVs match the canonical 32-run campaign; 562,888 operations and zero failures confirmed.
- New documentation links and saved checksums passed offline verification.
- A scan for common private-key and credential signatures found no matches.

No new load, deployment, security change or live experiment was performed to prepare this repository. Raw CSVs retain their original CRLF endings; archived original source and generated artifacts retain their original whitespace. No clean-environment dependency installation or live deployment test was performed in this preparation step.
