# Architecture audit — in-flight recovery map (2026-08-14)

Campaign: deep inspection -> docs/NAVALAI_GEOMETRY_ARCHITECTURE_AUDIT.md ->
docs/NAVALAI_REBUILD_PLAN.md -> incremental execution. NO CFD runs.

## In flight
- 7 read-only inspection agents (domains): geometry/representation,
  grammar/genome/typology, hydrostatics/loading, physics models,
  cfd-prep/timers, optimization/generative, tests/docs/dead-code.
- Full pytest baseline running (result -> docs/audit/pytest-baseline.txt).

## Save protocol
Each agent report is written to docs/audit/<domain>.md and committed+pushed
IMMEDIATELY on arrival. If a session limit kills the run, resume by reading
this directory: whatever is here is done; whatever is missing must be
re-inspected (agent prompts are reconstructable from AUDIT doc section list).

## Arrived so far
(none yet — updated as reports land)
