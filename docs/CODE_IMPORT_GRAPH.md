# Forensics — import graph + reachability (§6/§7), HEAD 3527a59

AST-level static analysis of all 70 navalai modules + consumers in tests/
(57), scripts/ (24), ui/. Full classification table in the agent record;
summary + verdicts here.

## Classification summary
- CORE (production-reachable): geometry(fan-in 27), grammar(21), limits(16),
  constants(10), evaluate(12-in/17-out), mission, energy, formlib, weights,
  db, holtrop, resistance, hydrostatics, seakeeping, optimize, certify,
  formcheck, buildability, engineer, unroll, export, rules{,iso12215,
  iso12217,review}, cfd{,case,post}, mesh_repair, stl_forensics,
  admissibility, generative, latent.
- SUPPORT: reference, translate(via orphaned agents!), pipeline(sole prod
  importer = gaps), gaps, flywheel, surrogate, fidelity, similitude,
  refdata*, rules.ergonomics.
- GATE-SUPPORT: gates, cfd.manifest(tests only!), rules.estrin(tests
  only!), blender* (subprocess payloads by design).
- CLI: design_report (ZERO importers incl. tests).
- RESEARCH (docstring-declared): experiments, dynamics, waves, planner,
  extrapolate, evidence(0-in/0-out isolated).
- EXPERIMENTAL: agents, hull_ast (only prod importer = agents), arrangement,
  policy subtree.
- **DEAD/LEGACY: NONE.** Every fan-in-0 module is a documented CLI, a
  gated suite subject, a subprocess payload, or declared research.

## Cycles: 5 SCCs, all runtime-safe (deferred-import convention throughout;
iso12217→evaluate is TYPE_CHECKING-only, commented).

## Sharpest findings
- **F1 estrin never runs in production.** rules/__init__ imports ZERO
  submodules; evaluate wires iso12215+iso12217 but NOT estrin; sole
  importer = test_gapfix_product.py:34. mission.py:50 + translate.py:244
  comments claim otherwise — true only inside Gate 6P.
- **F2 CFDManifest is not on the case-writing path.** fan-in 0; consumed
  only by Gates 2R/VM; all 8 case-writing scripts import cfd.case
  directly, none route through manifest_from_evaluation.
- **F3 design_report has zero importers including tests** — certify() is
  gated; the CLI/report formatting layer is untested.
- **F4 waves↔seakeeping wiring doesn't exist** (seakeeping docstring
  claims waves owns the seaway; nothing imports waves in production).
- **F5 policy/governance kernel unwired** (compiler promises rows into
  CONSTRAINT_NAMES; no production importer).
- **F6 100% of tests/ files are gate-registered** (0 unowned suites).
- **F7 two unrelated `Genome` classes** (latent.py:23 8-D vs pipeline.py:64
  lifecycle) — name collision, not alias.
- **F8 no import-only compat aliases.**
- **F9 extrapolate.ittc78_from_model: zero callers anywhere.**
- **F10 the agentic island**: agents→{hull_ast,translate,...} hangs off a
  single test import (test_stageC.py:9) — the only production path into
  hull_ast and translate.
