# LIVE SYSTEM MAP — what actually executes (forensics, call evidence)

Every node below is a concrete `file::function` proven by import/call
tracing and executed traces (`docs/forensics/e2e-map.md`,
`docs/forensics/shadow-api.md`). Everything NOT on this map is classified
in the table underneath — no hidden fourth category.

```
USER
 ├── CLI    navalai/design_report.py::main         (--mission | --case; the certification report)
 ├── HTTP   ui/server.py::Handler                  (/eval /mission /generate /pareto — every POST ends in evaluate())
 └── CFD    scripts/make_case.py::main             (⚠ bypasses mission/evaluate/manifest today — plan C-06)
        │
MISSION     navalai/mission.py::parse_mission      (rule floor; translate.py = optional-LLM wrapper, degrades to floor)
        │      MissionSpec ── VesselConfig ── PayloadSpec ── EnergySpec
        │      targets: mission.py::design_fn / mission_cp_target / mission_cp_band
        ▼
GENOME      navalai/grammar.py::vector/named/check(vessel=)     ← the one parameterisation + L0 gate
   sources: evaluate.py (incl. morphology's `shape` row since 2026-08-26)::sample_valid │ optimize.py::pareto_front │ generative.py::make_generator
        ▼
EVALUATION  navalai/evaluate.py::evaluate          ← THE ladder (one call, one state)
   inside:  geometry.py::Hull (kernel: _stations/sample_section/SAC)
            hydrostatics.py::solve_to_displacement → solve_equilibrium   (solved trim attitude)
            energy.py::weight_budget/weight_items → weights.py::aggregate (+ mission_payload item)
            resistance.py::total_resistance (Michell+ITTC-57, separation-aware; holtrop = envelope guard only)
            rules/iso12215.py::assess · rules/iso12217.py::assess (+ multihull refusal w/ measured GZ clauses)
   promote: evaluate.py::revalidate → seakeeping.py (L2 BEM) · l3_case_evidence (L3 reads a finished case)
        ▼
SELECTION   optimize.py::pareto_front (NSGA-II, ev.ok-gated) │ ui pool percentile cut
        ▼
CERTIFICATION  navalai/certify.py::certify         (ACCEPT / MARGINAL / REFUSE + cfd_candidate)
   composes: formcheck.py::form_descriptors · hydrostatics.py::gz_curve/multihull_gz_assessment
             buildability.py::shell_complexity · certify.py::speed_curve/loading_matrix
        ▼
CFD MANIFEST  navalai/cfd/manifest.py::manifest_from_evaluation   (⚠ DANGLING at HEAD: tests-only;
              the live CFD lane is make_case → cfd/case.py::write_resistance_case → hull_to_stl
              with motion_from_geometry — plan C-06 reconnects this node)
        ▼
GATES       navalai/gates.py::main (ladder + red ledger)  ·  scripts/reconcile_gaps.py (gap truth)
```

## Everything else, classified (§26 rule — no UNKNOWN left)

| Classification | Modules / files |
|---|---|
| TEST-SUPPORT | tests/ (55 files, 100% gate-owned), navalai/reference.py |
| GATE-SUPPORT | gates.py, cfd/manifest.py (until C-06), rules/estrin.py (until C-23), blender/* (subprocess cross-check, macOS-bound), admissibility.py (until C-18), data/gate-ledger.json, data/baselines.json, tests/formcheck_baseline.json |
| RESEARCH (intentional, docstring-declared) | experiments.py, dynamics.py, waves.py, planner.py, extrapolate.py, evidence.py, fidelity.py, similitude.py (last two also serve tank_resonance), scripts/demo_apse.py, scripts/hull_form_audit.py, scripts/stl_thirdparty_check.py, scripts/blender_*.py, docs/research/** |
| EXPERIMENT | agents.py + hull_ast.py (the Phase-2 agentic island, test-only; the builder now carries the shape-repair stage), policy/ (governance kernel; UI envelope + sweep consult its box — evaluate/certify governed only on request), pipeline.py + latent front (lifecycle FSM / latent search, unwired), arrangement.py (tier-E, awaiting R2.4) |
| HISTORICAL (evidence, keep) | docs/audit/**, docs/forensics/**, the seven gate2u-*.json (quarantined-void calibration), docs/GATE-6R-REVIEW.md, NAVALAI_* audit/plan docs |
| LEGACY (label, don't delete yet) | scripts/demo_mission.py (predates certify; C-27), renders/*.png (tracked-vs-ignored; C-20) |
| DEAD | **none found** — every fan-in-0 module is a CLI, a gated subject, a subprocess payload, or declared research |

## The three dangling wires (the map's whole point)

1. **CFDManifest → case writer** (C-06): the single-truth object exists,
   is gated, and nothing on the live CFD lane consumes it.
2. **admissibility screen → case writer** (C-18): the meshability verdict
   never guards the mesh.
3. **policy / estrin → evaluate** (C-23/24): governance and inland rules
   execute only in tests while docs imply otherwise.
