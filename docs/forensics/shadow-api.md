# Forensics — shadow pipelines + API/CLI + live-map skeleton (§15/§23)
HEAD 3527a59. Full tables in agent record.

## Shadow verdicts
- mission→genome: THREE generators (NSGA-II, GMM/PPCA pool, latent/agents)
  but ONE evaluator behind all; pipeline.Pipeline + pareto_front_latent
  UNWIRED; agents.run_plm + hull_ast test-only (docs-labelled).
- genome→hydrostatics: NO unlabelled shadow (every out-of-ladder solve is
  a declared cross-check or research).
- geometry→resistance: clean; ONE authority; certify.speed_curve verified
  to consume ev state; holtrop.total zero production callers (and
  reconcile_gaps CHECKS that).
- geometry→STL: canonical hull_to_stl/closed_mesh + labelled cross-checks;
  export.py STEP/IGES guarded but UNWIRED to any CLI.
- mass: **G7 fix dead on the wire** — CFDManifest.free_motion has only
  test callers; make_case.py --free-motion REQUIRES --stl →
  motion_from_geometry is the ONLY reachable free-motion path for
  imported AND genome hulls alike.
- certification: certify canonical; **admissibility.screen (SAFE/
  DANGEROUS) is never consulted by the case writer** — the screen and the
  thing it screens are disconnected halves.
- policy/estrin: governance executes only in tests (confirmed).

## API/CLI
Production: navalai.gates, navalai.design_report, ui/server (all POST
routes end in evaluate(); /eval does NOT bypass grammar), make_case.py
(bypasses manifest — B6), post_gci/gate2m/reconcile_gaps/mesh_robustness/
make_baseline/fetch_benchmark_geom. demo_mission.py = LEGACY-leaning demo
(predates certify, never emits the canonical verdict). demo_apse =
research. **.githooks silently DISABLED on this box: core.hooksPath
points at /Users/robobostes/... — re-run install-hooks.sh.**
UI lane is monohull-only in practice (no VesselConfig decoder on HTTP; a
vessel dict would 400). docs/BUILD-PLAN.md:612 still presents run_plm +
Pipeline as system entries (both test-only).

## Live-map skeleton (call evidence)
USER → {design_report CLI | ui/server HTTP | make_case CFD} →
parse_mission → grammar (vector/check) ← {sample_valid | pareto_front |
make_generator} → evaluate (THE ladder) → {optimize | pool cut} →
certify (+formcheck/gz/buildability/speed/loading) → manifest
(**DANGLING NODE** — tests-only; live CFD lane = make_case → cfd.case →
hull_to_stl + motion_from_geometry) → gates.
Off-map: pipeline, arrangement, waves, dynamics, agents, hull_ast,
latent, surrogate+flywheel (script/tests), export, policy, estrin,
review, evidence+extrapolate, planner/fidelity/similitude, mesh_repair,
blender (macOS-bound), admissibility (standalone), db.Provenance (no
live entrypoint passes it).
