# Forensics — docs-vs-code contradictions (§11), HEAD 3527a59

## STALE-FALSE (doc asserts what code disproves)
1. PLM.md:121-128 §2.0 — "no payload/endurance/sea-state mission" vs
   PayloadSpec + MissionSpec.payload (Gate VM). BIGGEST contradiction.
   (Still-true half: no wake/acoustic/survey objectives.)
2. BUILD-PLAN.md:2234 PV-1 — multihull I_T "does not exist" vs
   hydrostatics parallel-axis + gz_curve + Gate 1M; scheduled under a
   never-created "Gate 11H" (landed as Gate 1M).
3. BUILD-PLAN.md:2235 PV-2 — "no separation in production" vs
   resistance.py:21 + mission.separation_over_lwl.
4. BUILD-PLAN.md:2629-31 — same, dated verification note still standing
   as scheduling basis.
5. BUILD-PLAN.md:998 — "MissionSpec has no wind, no sea state" — half
   false (sea_state declared; wind still true).
6. docs/audit/STATUS.md:107-110 — "Next rungs" lists R2.2/R3.1/R3.2
   which the SAME FILE records DONE (internal self-contradiction).
7. CLAUDE.md:72-73 — "there is no ~/naval-ai" — Mac-scoped absolute,
   false on fortress001.
8. physics-models.md:40 + ARCHITECTURE_AUDIT:246 — seiche claim now
   stale (fixed ed1cf83); dated snapshots.

## STALE-COUNT
9. BUILD-PLAN:519 pop24/gens10 vs ui/server 48/15. 10. ALIGNMENT.md:64
pop24x10 + params(15) — both stale. 11. ui/server.py:291 comment
contradicts line 143 of its own file. 12. Three different pytest
wall-times (CLAUDE 4min/3min vs README 10min), no per-machine note.

## DEAD-COMMAND: none found (every literal command resolves at HEAD;
reconcile_gaps runs clean: 123 rows = 108 closed/12 open/1 needs/2 retired).

## Borderline: BUILD-PLAN §2.2 "MISSION INTELLIGENCE not built" (dated
badge saves it; certify.py now delivers a slice); MACBOOK.md pre-void
claims; GAP-REGISTER frozen-by-design EXCEPT row A2 edited in-place
against Gate SG's own no-edit rule.

## Disproven hunt targets: trim_angle_deg NOT deleted (weights.py:129 —
but see ownership report: zero production callers); README capability
section verified clean; gate-table prose consistent.
