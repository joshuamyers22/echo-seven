# Echo Seven rename and public publication

Requested by the owner on 2026-09-09. Rename the project to Echo Seven and publish
to the public joshuamyers22/echo-seven repository, retaining dev/bootstrap.

Verification rubric: renamed package imports, CLI entry points, strict template
checks, wheel build and isolated CLI replay; inspect tracked files/history for
credentials and restricted market data. Preserve original research hashes and
statistical behavior. No financial model or live-eligibility changes. Stop when
these checks and the public remote/commit verification pass.

The earlier bootstrap-verification.md is a historical record using the original
spot-vol-beta name and source hashes. Current package imports are echo_seven.
The original archive contains a historical local Downloads path but no credentials
or raw market data. The existing proprietary license remains in effect; public
visibility does not introduce an open-source license.

Local verification completed 2026-09-09: 50 tests pass, strict Pyright and Ruff
pass, renamed wheel/source archive build. The wheel runs the echo-seven console
entry point from an isolated environment outside the checkout. Its numerical
estimates and pairs match the pre-rename replay exactly. Dependency versions and
all 13 archived research hashes are unchanged. Git diff whitespace checks pass.
The publication scan checked 119 unique Git blobs across existing history and
staged changes; no configured secret patterns or restricted data paths were found.
CI now runs for dev/** pushes as well as main; secret scanning remains enabled.
