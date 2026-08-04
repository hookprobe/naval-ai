# NavalAI — project guide for Claude Code

Autonomous naval-architecture validation AI: mission in natural language →
grammar-constrained hull generation → slider surface with live physics →
tiered validation ladder (L0 algebraic → L1 Michell/hydrostatics → L2
Capytaine BEM → L3 OpenFOAM RANS → R ISO rules) → manufacturing export.
Canonical docs: `NavalArchAI-BuildPlan.md` (research-grounded plan),
`ALIGNMENT.md` (audit vs the original agentic-PLM plan), `README.md`
(gate-status table), `MACBOOK.md` (Mac simulation-node runbook).

## Machine roles

- **fortress001 (Linux)**: development, full test suite, gate ladder.
- **Mac (M5, 24 GB)**: THE SIMULATION NODE — OpenFOAM runs (Gate 2M),
  diffusion/LoRA training. If you are running on macOS, this is you.
- Coordinate via git (github.com/hookprobe/naval-ai, branch master).
  Pull before working; push results. Don't assume the other machine's
  uncommitted state.

## Non-negotiable honesty rules (enforced by tests)

1. Every quantity carries `{value, tier, sigma}` — no bare numbers.
2. Kept designs re-validate up the ladder; surrogates refuse OOD queries.
3. LLMs translate missions and explain; they have NO code path to geometry.
4. Retrained surrogates that degrade the frozen benchmark never deploy.
5. Rules tier output is an ASSESSMENT AID, not certification.
6. Never soften a failing gate threshold to make it pass — a failing gate is
   information. Record measured findings (see ALIGNMENT.md scorecard).

## Working on the Mac (OpenFOAM)

- OpenFOAM v2606 native via openfoam-app. One-shot commands WITHOUT an
  interactive session: `openfoam <command args>` (the launcher execs its
  args) or `openfoam bash -c '...'`. Interactive: bare `openfoam` (bash
  inside, so `#` comments are safe there; in zsh outside they are NOT).
- Campaign flow:
  `python scripts/make_case.py --out runs/<name> [--triplet|--stl X --lwl L] --speed U --np 10`
  → `openfoam navalai/cfd/run-case.sh runs/<name>[/grid] 10`
  → `python scripts/post_gci.py runs/<name>`
  → `scripts/clean-runs.sh` (trim keeps forces+logs; --purge deletes).
- Python env: `source ~/.venvs/naval/bin/activate` (numpy scipy pymoo
  capytaine mujoco cadquery pytest).

## Hard-won CFD gotchas (do not re-learn these)

- Hull STL must be a CLOSED manifold (deck + transom capped);
  `stl_watertight_report` gates it. Open shells flood the interior.
- alpha.water inlet must be height-stratified (`exprFixedValue`,
  z<0 → 1); `inletOutlet $internalField` drains the tank.
- Waterline sits on a cell FACE **structurally**: blockMesh is TWO blocks
  split at z=0. The old "nz multiple of 3" rule held only for the 1.5L/0.75L
  domain and silently broke systematic refinement (see next point).
- **GCI needs a systematically refined FAMILY, not three meshes.** Snapping
  nz to a multiple of 3 gave z-ratios 1.333/1.5 → effective r = 1.297/1.368
  while post_gci assumed sqrt(2): p=nan, GCI 58.5%. post_gci now MEASURES r
  from real cell counts and warns if the two steps disagree >5%.
- **Resolve the free surface or the whole run is decoration.** With
  `refinementRegions {}` the wave field ran at 5-10 cells/wavelength (bar:
  >=20) and the background cell was 0.63-1.25 m against ~0.1 m waves — the
  drag then rode on hull-local refinement and one z-cell tripled it.
  `case.info` records cells_per_wavelength / fs_dz as a receipt.
- **maxAlphaCo sets dt, not the cell count.** At maxAlphaCo 1 the interface
  Courant pins dt≈0.003 s → 4.9 h for the COARSE grid alone, days for fine.
  Running at 2 (MULESCorr semi-implicit) is the compromise; 5 smears.
- Free-surface z-grading makes ~20:1 cells where the hull pierces the
  waterline ⇒ ~72 skew faces (max ~6) and ~50% prism-layer coverage.
  MEASURED: removing the free-surface box does NOT fix either, so this is
  inherent, not a bug. Judge it by the yPlus function object, not checkMesh.
- **Size the near-wall cell in METRES, never `relativeSizes true`.**
  `first_layer_thickness()` derives it from the ITTC-57 line (0.706 mm at the
  reference condition). Verified: min y+ on the hull is 41.8 ⇒ a 0.985 mm
  first cell, i.e. the target is being hit where layers exist.
- **Do NOT read the patch-average y+ as a quality metric.** The `hull` patch
  includes the DECK and topsides, which sit in AIR. Inverting the numbers:
  avg y+ 7508 ⇒ 177 mm first cell and max 61420 ⇒ 1446 mm — both larger than
  the 104 mm local hull cell, and 1.4 m is the background cell in y. Those are
  dry faces, and they dominate max/average. Only the MIN reflects the wetted,
  layered surface. A wetted-only (alpha.water-masked) y+ is still owed.
- Layer count trades against insertion: MEASURED coverage n=3 → 50.3%,
  n=5 → 36.5%, n=8 → 26.2%, n=15 → 11.2%; nLayerIter/nRelaxedIter change
  nothing. Coverage wins (an uninserted layer controls no y+), so n=3 and the
  stack does NOT bridge to the local cell — `case.info` records both numbers.
- First-layer thickness is held CONSTANT across the triplet, so the GCI
  bounds OUTER-flow discretisation with the wall model fixed. Say so.
- Deep water is a property of the WAVE: tank depth = max(0.6L, 1.5·λ/2),
  λ = 2πU²/g. A fixed depth quietly returns shallow-water resistance.
- Watch `Phase-1 volume fraction` in log.interFoam: it must stay constant.
- post_gci drift column > 5% ⇒ not settled ⇒ extend --end-time, don't trust.
- v2606 requires the full addLayersControls set (maxFaceThicknessRatio etc.).
- Mesh-tuning loop: mesh-only (blockMesh+snappy+checkMesh) is ~2 min while a
  solve is hours — sweep mesh parameters WITHOUT solving.

## Current campaign state (2026-08-04, Mac)

- Full pipeline proven end-to-end on the Mac (mesh+layers+solve+forces+GCI).
- **Own-hull GCI triplet v1 is DEAD — do not use its numbers.** Even after the
  waterline fix it gave p=nan / GCI 58.5% (oscillatory: -1202 / -738 / -1388 N).
  Root causes were measured, not guessed: an unresolved free surface and a
  non-systematic refinement family. Kept at `runs/gci_v1_unresolved/` as
  evidence; `runs/gci/medium_nz25_stale` is the original mid-cell-waterline run.
- v2 case generator (this session) rebuilds the mesh around those two causes:
  two-block waterline split, graded free-surface slab, measured r, y+ reported.
  Coarse mesh 297,712 cells at 20.3 cells/wavelength (v1: 45,606 at 5.1).
- Runtime on 10 performance cores at maxAlphaCo 2, end-time 25 s:
  coarse ~0.5 h, medium ~2 h, fine ~8.5 h (measured rate, not the runbook guess).
- Next milestone: **Gate 2M** — KCS calibration (IGES from t2015.nmri.go.jp,
  model scale 1:31.6, LWL 7.2786 m, Fn 0.26 → 2.196 m/s) via
  `scripts/iges2stl.py` + `make_case.py --stl`. Success = fine-grid Ct inside
  Tokyo-2015 scatter with GCI ≲ 2.5%.
- Then: record L3 results in provenance (tier 'L3') and wire the co-kriging
  L1→L3 correction; parallel tracks: diffusion (PyTorch-MPS), LoRA (mlx-lm).

## Verification

- `python -m pytest tests/ -q` (expect all green, ~3 min) and
  `python -m navalai.gates` before/after non-trivial changes.
- Tests encode the gates; new physics/fixes get a gate test with the
  measured bar and a comment naming the incident that motivated it.
