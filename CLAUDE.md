# NavalAI — project guide for Claude Code

Autonomous naval-architecture validation AI: mission in natural language →
grammar-constrained hull generation → slider surface with live physics →
tiered validation ladder (L0 algebraic → L1 Michell/hydrostatics → L2
Capytaine BEM → L3 OpenFOAM RANS → R ISO rules) → manufacturing export.
Canonical docs: `PLM.md` (product-line management: platform law, roles,
lifecycle, roadmap board — READ THIS FIRST), `NavalArchAI-BuildPlan.md`
(research-grounded plan),
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
- **v2606 needs `meshQualityControls/relaxed`** as soon as layer addition
  reaches `nRelaxedIter`, else FATAL IO ERROR "Entry 'relaxed' not found"
  AFTER the mesh is built. Hidden at nSurfaceLayers 3; it appears at 6.
- **`deltaT` collapsing (1e-40) while Courant stays high == a pathological
  CELL, not a numerics problem.** No timestep can fix a cell whose local
  Courant will not fall, so the adaptive controller shrinks dt to underflow
  and interFoam dies with an FPE in the GAMG p_rgh solve. Diagnose by the
  dt/Courant signature.
- **Do NOT use snappy's "illegal faces" count as the predictor** — it is not
  sufficient. MEASURED: coarse finished with 8826 illegal faces and medium
  with 17326, and BOTH solved 25 s cleanly; the configs that died had 11976
  and 22529. What distinguished them was more/thicker layers at higher hull
  refinement, not the raw count. Keeping `relaxed` from loosening the
  volume/twist guards is still right on principle (a dropped layer costs
  accuracy, a degenerate cell costs the run) but it is NOT an established
  cause of these crashes.
- **The STL must be finer than the cells that snap to it.** Default 80x16 gives
  ~112 mm triangles on a 10 m hull — fine against level-3 (104 mm) cells, but
  the limiting surface at level 4-5. `stl_resolution()` now scales it with the
  hull refinement level (capped at 600x120 ~ 144k tris).
- **Core topology (MEASURED — the old "10 performance cores" note was wrong
  in a way that matters).** `sysctl hw.perflevel{0,1}` on this M5 Pro:
  perflevel0 = "Super" ×5, perflevel1 = "Performance" ×10, 15 total. There is
  no efficiency tier to avoid.
- **np=10 is the measured optimum — do not use all 15.** Same 0.4 s slice of
  the medium grid: np=5 → 212.7 s, **np=10 → 127.2 s (1.67×)**, np=15 →
  153.1 s. Oversubscribing all 15 costs ~20%. (A prior guess that the slower
  tier would stall MPI was simply wrong; the benchmark settled it.)
- **This Mac's cooling cannot sustain long runs.** Measured: `pmset -g log`
  showed `Entering Sleep state due to 'Thermal Emergency Sleep'` at
  2026-08-04 23:19, losing a triplet with the fine grid never started.
  `caffeinate` and the lockscreen timeout do NOT prevent this — they address
  IDLE sleep, a different path (`pmset -g` already shows `sleep 0`). Mitigate
  by RESUMABILITY, not by throttling: `scripts/run_campaign.sh <root> 10`
  re-invokes until endTime is reached. Check `pmset -g log | grep -i thermal`
  after any run that ends early.
- Consequences of that, both now handled: `run-case.sh` RESUMES from the
  latest checkpoint instead of re-meshing, and `post.forces_path()` merges the
  extra `postProcessing/forces/<restart-t>/` segment a resume creates —
  reading only `0/` would report the pre-crash fragment as the whole run.
  writeInterval is end_time/10 so a nap costs ~10% of the run, not 20%.

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
## WHERE TO PICK UP (end of 2026-08-04/05 Mac session)

**The blocker is the near-wall mesh, not the outer mesh.** The v2 mesh strategy
works — coarse/medium are now MONOTONIC (-2639.4 → -2469.4 N, 297712 → 834760
cells), unlike v1's oscillation. But `scripts/yplus_wetted.py` showed only
**2.0% of WETTED hull faces are inside 30 ≤ y+ ≤ 300** (median 11431), so the
wall functions are invalid where skin friction is made. Cross-checks agree:
viscous drag is 2.62× the ITTC-57 line, and Ct 2.4e-2 against ~6.7e-3 from L1.

The fine grid was deliberately NOT run: ~3 h to converge onto a wall model
known to be invalid buys a precise wrong number.

Root cause: `refinementSurfaces hull level (2 3)` gives FLAT hull area only
level 2 (~208 mm cells), which a 0.7 mm first layer cannot bridge in 3 layers,
so layers mostly are not inserted. `_HULL_REFINE` and `_TARGET_YPLUS` in
`navalai/cfd/case.py` are now the knobs.

Next steps, in order:
1. Finish the near-wall sweep. It was cut short; PARTIAL result (2 s solves, so
   read these as RELATIVE — the 25 s coarse run gave median 11431 / 2.0%):

       trial                  cells   layer%  t1 mm  wet med y+  in-band%
       (2,3) y+30 n3         297712    50.3   0.706      7163      5.1
       (3,4) y+30 n5         343675    48.6   0.706      3999      8.9

   So raising hull refinement halves median y+ for only +15% cells — right
   direction, nowhere near enough. UNTESTED and most promising: a THICKER
   first layer aimed at the middle of the valid band rather than its edge
   (y+ 100-150 → t1 2.4-3.5 mm) with level (4 5); a short stack bridges a
   small cell far more easily than a 0.7 mm layer bridges a 208 mm one.
   Sweep script: `~/.claude/jobs/*/tmp/wall_sweep.py` (re-create if the job
   dir is gone; it is 5 configs × ~5 min). Adopt the winner into
   `_HULL_REFINE` / `_TARGET_YPLUS` / `_MAX_LAYERS` + a gate test.
   NOTE: `openfoam bash <script>` SEGFAULTS; the launcher execs its args, so
   call `openfoam <script> ...` directly.
2. Re-run the own-hull triplet ONCE with a valid wall treatment:
   `openfoam scripts/run_campaign.sh runs/gci 10` (resumes across thermal naps).
   Then `python scripts/post_gci.py runs/gci` → record `data/baselines.json`.
3. **Gate 2M is otherwise READY.** Acceptance data is in `benchmarks/kcs.py`
   (EFD Ct 3.711e-3 @ Fn 0.26, 13-group scatter 3.620–3.733e-3). Regenerate the
   hull per the recipe in that file (validated to −0.09% on displacement), then
   `make_case.py --stl data/benchmark_geom/kcs.stl --lwl 7.2786 --speed 2.196`.
4. Then: L3 into provenance (tier 'L3') + co-kriging L1→L3; parallel tracks
   diffusion (PyTorch-MPS) and LoRA (mlx-lm), both GPU — OpenFOAM never uses it.

Open and recorded (see ALIGNMENT.md): a SECOND benchmark anchor is owed. KCS
shares no chine/transom/spray physics with the SKUs, so Gate 2M passing is not
small-craft validation.

## Gate 2M: KCS still does NOT mesh cleanly (open)

The acceptance data and geometry pipeline are done (`benchmarks/kcs.py`,
displacement -0.09%). The MESH is not. Every variant tried leaves ~9-10
zero-volume cells and non-orthogonality **141.057 — the identical value every
time**, i.e. one fixed unresolved feature. interFoam dies on the first
timestep.

Ruled OUT by measurement, so do not re-try these:
- prism layers: `addLayers false` gives a byte-identical broken mesh, so the
  defect is in castellation/snapping
- refinement: it gets WORSE, not better — (2,3) 10 zero-vol / 55 wrong-ori,
  (3,4) 9 / 82, (4,5) **149 / 938**. Degrading under refinement is the
  signature of a surface defect that coarse cells step over
- the STL slivers (8 triangles below quality 1e-3): welding merges nothing,
  because they are three nearly COLLINEAR vertices, not coincident ones
- the mirrored-hull keel seam: symmetry removed it (skewness 52.2 -> 9.5)

The live lead is `surfaceCheck -checkSelfIntersection` (run it WITH the flag;
plain surfaceCheck reports the surface as fine):
    sewn at 1e-4          -> 64 self-intersections
    sewn at 1e-3 (raw)    -> NONE, clean
    after my capping      -> 5, at y~0.5095, z -0.009..0.096
So the raw sewn half hull is clean and OUR post-processing breaks it. The
centroid-fan cap was genuinely invalid (a fan only works on a convex loop) and
is now ear-clipping, but 5 intersections remain and their z does NOT match the
cap plane (0.1332) — so the cap is not the whole story. Next: bisect the
remaining post-processing, or cap in OCC before tessellation instead.

Symmetry (`symmetric=True`) is implemented and worth keeping regardless: half
the cells, no mirror seam. Use `type symmetry`, NOT `symmetryPlane` — once the
hull lies on the boundary snappy leaves faces of both orientations and
symmetryPlane refuses.

## Verification

- `python -m pytest tests/ -q` (expect all green, ~3 min) and
  `python -m navalai.gates` before/after non-trivial changes.
- Tests encode the gates; new physics/fixes get a gate test with the
  measured bar and a comment naming the incident that motivated it.
