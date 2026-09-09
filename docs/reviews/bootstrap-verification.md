# Initial milestone verification loop

Authority: PROJECT_BRIEF.md and ADR 0001. Owner: J. Myers.
Risk: financial logic; offline research only, no production approval.

Before implementation, the blocking rubric is: correct known log-beta and hedge
units; reject future/asynchronous inputs; no gap/session/halt/contract bridging;
transparent insufficient-information and inference status; deterministic
source/plan/code evidence; template lint, strict types, tests and wheel pass.

Ceilings: four evidence-changing implementation/verification passes, 60 minutes
for this milestone, local synthetic fixtures only, no paid data or live compute.
Stop after the gate passes or a data/domain dependency prevents further useful
verification. Do not repeat unchanged tests to fill an iteration quota.

Planned evidence: analytic examples and adversarial boundary tests; full template
gate; CLI replay plus package smoke test; review of the final diff and unresolved
risks. Record completed evidence below. Raw market validation and release approval
are outside this milestone and must not be inferred from synthetic success.

## Completed evidence — 2026-09-09

- `make check`: Ruff lint/format and strict Pyright passed; 50 unittest tests passed,
  including 16 new domain tests. Scalar closed-form OLS/HC3 checks do not call the
  production regression implementation to construct their expected values.
- Adversarial cases: missing/rejected endpoint chains, future quote and calibration
  availability, session/halt changes, duplicate bars, mixed strike/expiry/side/
  underlying identity, malformed CSV, insufficient variation, unit leverage, exact
  fits, both beta signs and factor-100 hedge units.
- Evidence verification: deterministic repeat runs, overwrite refusal including
  direct publication to an existing path, safe malformed-input error envelope.
- `make build`: wheel and source distribution built. An isolated wheel installation
  ran the real console entry point outside the checkout and produced the same
  artifact bytes as the locked development environment.
- Synthetic replay: 120 rows, 112 pairs, four sessions; beta -1.9940007020636596
  versus generating coefficient -2 with deterministic noise. HC3 remains explicitly
  unvalidated under dependence; no market coverage or economic claim follows.
- Artifact SHA-256: `4f0152f76b1c7510ef816ce7f48b80ff828027580bbdc4226d7f977b8e935be4`.
  Local outputs: build/spot-vol-example.json and build/spot-vol-timed.json (ignored).
  Both use revision label local-bootstrap and exact per-module source hashes.
- Timed locked replay: 1.68 seconds wall time on this Mac, Python 3.12.11, NumPy
  2.5.3, Polars 1.44.2, Statsmodels 0.15.0. This meets the local small-fixture check;
  dependency installation/cold environment setup and large inputs were not benchmarked.
- `make audit`: no known vulnerabilities/adverse project statuses in 18 runtime
  packages; dependency license policy passed. Queries required network access.

## Findings and dispositions

- Fixed before gate: strict NumPy typing at the centered sum-of-squares calculation;
  malformed Polars CSV errors now map to safe boundary errors; whitespace-only IDs
  fail validation; atomic artifact publication uses an exclusive hard link rather
  than the template utility's replacing rename.
- Reviewed: CSV CRLF and archived Markdown hard breaks are intentional. Git attributes
  preserve archived bytes and recognize these whitespace conventions. Archive hashes
  remain identical to source; historical experiment code is excluded from current
  lint/type gates and was not rerun.
- Remaining: feed choice, IV/calibration truth, financial information sufficiency,
  dependence-aware uncertainty, chronology/economic holdouts, full-size performance,
  filesystem portability/crash durability and GVV integration require later work.
  Current local hard-link publication is exclusive and flushes file contents; it
  does not promise directory fsync durability or support every network filesystem.
- This is the implementing agent's bounded verification, not independent domain
  approval. No live eligibility change, release tag, deployment or remote publication.
