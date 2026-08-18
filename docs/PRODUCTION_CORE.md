# PRODUCTION CORE — the files a human must understand (§30)

The complete production execution path (see LIVE_SYSTEM_MAP.md) is
defined by these files. Everything else is TEST / GATE / RESEARCH /
EXPERIMENT / HISTORICAL per the map's classification table.

## Core (the design path)
- navalai/mission.py         (MissionSpec, VesselConfig, PayloadSpec, targets)
- navalai/grammar.py         (the 16-gene parameterisation + L0 gate)
- navalai/limits.py          (sourced bands/floors — the constants of judgment)
- navalai/constants.py       (physical constants, one home)
- navalai/formlib.py         (form families, sourced ranges)
- navalai/geometry.py        (the kernel: stations, section law, SAC, fairness)
- navalai/hydrostatics.py    (solve family, trim equilibrium, GZ, multihull terms)
- navalai/weights.py         (MassItem/aggregate — the positioned mass model)
- navalai/energy.py          (weight buckets, energy report)
- navalai/resistance.py      (Michell + ITTC-57 + interference; validity flags)
- navalai/holtrop.py         (envelope guard + reference model)
- navalai/rules/{__init__,iso12215,iso12217,review}.py
- navalai/evaluate.py        (THE ladder)
- navalai/optimize.py        (NSGA-II selection)
- navalai/generative.py + navalai/latent.py (the UI candidate pool)
- navalai/formcheck.py       (descriptors + deterministic cases)
- navalai/buildability.py + navalai/engineer.py + navalai/unroll.py + navalai/export.py
- navalai/certify.py         (verdicts + cfd_candidate)
- navalai/design_report.py   (the CLI face)
- navalai/seakeeping.py      (L2 promotion)
- navalai/db.py              (provenance)

## Core (the CFD-prep lane)
- navalai/cfd/case.py        (case writer, STL, motion)
- navalai/cfd/post.py        (readers/GCI)
- navalai/cfd/manifest.py    (the one vessel description — being wired, C-06)
- navalai/cfd/run-case.sh    (bounded solver runner)
- navalai/mesh_repair.py, navalai/stl_forensics.py, navalai/admissibility.py
- scripts/make_case.py, scripts/post_gci.py, scripts/gate2m.py,
  scripts/mesh_robustness.py, scripts/run_campaign.sh

## Core (governance/ops)
- navalai/gates.py, data/gate-ledger.json, data/baselines.json
- scripts/reconcile_gaps.py, scripts/make_baseline.py,
  scripts/fetch_benchmark_geom.py, scripts/install-hooks.sh, .githooks/
- ui/server.py + ui/index.html
- benchmarks/{wigley,kcs,holtrop_cases}.py
