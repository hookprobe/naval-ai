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
- Waterline sits on a cell FACE **structurally**: blockMesh splits at z=0.
  (Now FOUR z-blocks — deep / hull / wave / air — with the two middle ones
  ungraded and EQUAL at 0.09 Lwl; see the root-cause section below.) The old "nz multiple of 3" rule held only for the 1.5L/0.75L
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
- ~~Free-surface z-grading makes ~20:1 cells ... inherent, not a bug.~~
  **SUPERSEDED 2026-08-05.** It was not inherent: it was the 38:1 background
  cell (root-cause section below). Removing the free-surface box did not fix it
  because the box was never the cause. Layer coverage is now ~100% at n=3.
  Judging y+ by the yPlus function object rather than checkMesh still stands.
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
- ~~Layer count trades against insertion: n=3 → 50.3% ... n=15 → 11.2%.~~
  **SUPERSEDED 2026-08-05.** Those coverages were measured on the anisotropic
  background and on single-pass snappy. With a near-cubic background and layers
  added in their OWN pass after refinement, the KCS hull patch takes 3 of 3
  layers over all 22881 faces. Coverage still wins over stack depth, so n=3
  stays — but not because deeper stacks fail to insert.
- **Deep layer stacks do not just fail to insert — they KILL the solve.**
  Measured on the OLD anisotropic background; re-measure before trusting the
  envelope, since the mechanism (folded cells) was the aspect ratio:

      config            cells   layer%  medY+  in-band%  zeroVol  solve
      (2,3) y+30  n3   306655    47.0    2477     6.1%       0    runs
      (3,4) y+150 n7   341342    11.5      -        -        0    dies t=8e-4
      (3,4) y+200 n6   341398    13.1      -        -        0    dies t=8e-4
      (4,5) y+200 n4   465251    30.0      -        -       20    dies

  So n>=6 collapses coverage AND crashes interFoam on the first timestep, and
  hull refinement level 5 reintroduces zero-volume cells even on the good
  NAPA geometry. The usable envelope is narrow: refinement (2,3)-(3,4) and
  n<=3.
  NOTE: these sweeps solve only 4 s, so in-band% is LOWER than a settled run
  (the same baseline reads 6.1% at 4 s and 16.3% at 20 s). Compare configs
  against each other, not against the gate.
- First-layer thickness AND layer count are held CONSTANT across the triplet,
  so the GCI bounds OUTER-flow discretisation with the wall model fixed. Say
  so. (Until 2026-08-06 only the thickness was — see the n_layers note below.
  The count is now pinned by `make_case.py --triplet` at the FINEST scale.)
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

## THE ROOT CAUSE, and the fix (MEASURED 2026-08-05 — supersedes all of the
## snappy-tuning lore above)

**snappyHexMesh refines ISOTROPICALLY. Our background cell was 38:1.** That one
sentence explains every meshing failure this project has had.

`hexRef8` halves all three edges at once, so a cell's ASPECT RATIO is preserved
at every refinement level while its height shrinks in absolute terms:

    background  606 x 910 x 16 mm   = 38:1
    level 2     151 x 228 x  4.0 mm = 38:1
    level 5      19 x  28 x  0.5 mm = 38:1

Snap displacement scales with the LONG edge (~57 mm), so moving a node a few
millimetres moved it SEVERAL CELL HEIGHTS and folded the cell inside out. It
predicts everything we could not explain:
- (2,3) clean, (3,4) fails, (4,5) fails worse — refinement makes it WORSE
- `addLayers false` gives a byte-identical broken mesh (the defect is in
  castellation/snapping, not layers)
- snap `tolerance` has no effect — it too scales with the long edge
- the geometry checks out clean, because the geometry was never the problem

DTCHull starts from the same 42:1 background and refines **x,y only**, reaching
0.66:1 BEFORE snappy snaps. Same conclusion, reached from the other side.

**The fix, as implemented (do NOT re-derive this):**
1. blockMesh derives `dz` from `dx` -> background is near-cubic (1.85:1).
2. snappy pass 1: castellate + snap, **addLayers false**. Cubic cells snap fine.
3. `topoSet` + `refineMesh directions (normal)` — z ONLY — in the free-surface
   band, hull shielded by `surfaceToCell`. This is where interface thinness
   comes from; it sidesteps hexRef8 entirely.
4. snappy pass 2: **layers only**, on the z-refined mesh.

MEASURED on KCS after the fix — all three levels clean, where (3,4) and (4,5)
were previously unusable:

    refine   hull mm    cells  zeroVol  wrongOri   skew  layer%
    (2,3)      75.9   164635        0         0    4.67    66.0
    (3,4)      37.9   177436        0         0    5.69    76.4
    (4,5)      19.0   230265        0         0    5.74    75.4

`_HULL_REFINE` is now (4, 5). Full KCS mesh: 637k cells, hull patch fully
layered (3 of 3 layers, near-wall 0.795 mm against a 0.706 mm target) where
coverage used to be 32%. checkMesh: 4 open cells, 5 wrongly-oriented faces,
77 skew — down from 72988 zero-volume cells.

### The ORDER of steps 2-4 is forced from both sides — do not reorder

- refineMesh must come AFTER snapping, or snappy sees anisotropic cells again.
- refineMesh must come BEFORE layers. MEASURED with the rounds last: the min
  z edge went 1.3e-4 -> 3.8e-5 -> **1.1e-5 m** over three rounds and checkMesh
  found **72988 zero-volume cells**. An 11 micron cell inside a 0.7 mm boundary
  layer is a DESTROYED boundary layer, not a fine one.

### New gotchas from landing it

- **There is no `tan3`.** The refineMesh direction enum is `(tan1 tan2 normal)`;
  `normal` = tan1 ^ tan2 = +z. Asking for tan3 is FATAL.
- **run-case.sh used to SWALLOW that error** and solve anyway — a full 75 s run
  executed on an unrefined free surface. A refinement the case asked for that
  silently did not happen is a WRONG mesh, not a degraded one. Now fatal.
- **refineMesh does not maintain snappy's octree bookkeeping.** It updates
  `constant/polyMesh` but leaves `0/cellLevel` sized for the pre-refinement
  mesh, and decomposePar dies with "Size 230265 is not equal to the expected
  length 920407". Both `0/` and `constant/polyMesh` copies are dropped before
  the layer pass; layers use absolute thicknesses so they do not need levels.
- **Isotropy fights the GCI family.** Deriving nz from dx directly, round(1.08)
  and round(1.53) collapse to the same integer, so nz froze across
  coarse/medium and measured r fell to 1.376 against the sqrt(2) the triplet
  claims. Fix the near-cubic count once at scale 1 and SCALE it: r was then
  1.4175 / 1.4109, spread 0.47% — **on the FULL domain, which nothing runs.**
- **The 0.47% above described a mesh we do not use.** RE-MEASURED 2026-08-06:
  `ny = round((1.5 if symmetric else 3.0)*lwl/dx_bg)` re-rounds a HALF-SIZE
  number in the symmetric case, so the symmetric family — the one this file
  recommends — came out 18/25/36 with spread **0.85%**, and the full domain's
  ny was ODD (36/51/72), meaning the "half" domain was not half of anything but
  a third mesh. Fixed by `_NX_BASE 54 -> 57` (57/81/114 are ALL multiples of 3,
  so `ny = nx/3` is exact and tracks nx's ratio) and `ny_full = 2*ny_half`:

      base   family        symmetric   full     symmetric == half of full
       54    54/76/108     0.85%       0.47%    NO (38000 vs 77520/2)
       57    57/81/114     0.03%       0.03%    YES

  Cost is measured: (57/54)^3 = **+19% cells** at every grid. Coarse symmetric
  goes 13608 -> 16245 bg cells. Any triplet generated before 2026-08-06
  (including `runs/kcs_gci2`) is at the old base and is not this family.
  The exactness holds only where nx is a multiple of 3, i.e. for
  `--anchor coarse` (57/81/114). MEASURED for `--anchor fine`: 28/40/57,
  spread **1.92%** (it was 1.7% at base 54). `make_case.py --triplet` now
  PRINTS `family: r12 ... r23 ... spread ...` and flags anything over 1%, so
  a non-uniform family is known at generation time rather than after the solve.
- **A GCI triplet must freeze the LAYER COUNT, not just the first layer.**
  case.info claimed the wall model was held fixed; only `first_layer_m` was.
  `n_layers_to_bridge` reads the hull cell, which scales with nx, so a KCS
  triplet ran 7/6/5 layers and the prism stack thinned 12.9*t1 -> 7.4*t1 —
  p was absorbing two refinements. `make_case.py --triplet` now pins n_layers
  once and passes it to every member. It pins at the **FINEST** grid, not at
  scale 1: the stack has a fixed height in metres while the hull cell halves,
  so the coarse grid's 7 layers give a 34.2 mm stack against the fine grid's
  17.96 mm cell (ratio 1.90) and the generator refuses above 1.2.
- The two ungraded core z-bands are EQUAL (0.09 Lwl each). A thin 0.03 band
  divided into the >=2 cells the family needs gave 109 mm cells against 607 mm
  dx — 5.6:1, reintroducing the very anisotropy the fix removes.
- `scripts/run_campaign.sh` now accepts a SINGLE case dir. It used to print
  "skip coarse/medium/fine" then "done" — a successful-looking exit that ran
  nothing.

## What the 2026-08-06 re-audit changed about RUNNING things

- **`gate2m.py` has no GCI of its own.** It carried a second copy beside
  `navalai.cfd.post.gci`, missing every safety rule, and it was the copy that
  printed PASS/FAIL. MEASURED: on a monotone but DIVERGING triplet (fine
  3.700e-3, medium 4.100e-3, coarse 4.300e-3) it returned GCI = **-27.027%**,
  and `gci <= 5.0` is TRUE of a negative number, so the gate printed
  `VERDICT: PASS` and exited 0. It also understated a p=0.3 family by 2.4x
  (3.280% vs 7.872%) and inverted the Richardson sign (3.911e-3 for a triplet
  built around 3.711e-3). It now delegates, PRINTS the `method` string so you
  can see which safety rule fired, and refuses a negative or non-finite GCI.
- **`gate2m.py` refuses a case that is not KCS.** It applied `KCS.EFD` and
  `KCS.scatter_band()` to any directory: `gate2m.py runs/wigley` printed
  `C_T 5.9010e-03, E%D -59.0` for a Wigley hull under a header naming KCS's
  speed and Lpp. Identity comes from `stl_sha256` in case.info matched against
  `data/benchmark_geom/CHECKSUMS.json`; case.info now records `benchmark=`.
- **`run-case.sh` guards, in order.** The concurrency check is now FIRST (it
  used to sit after `rm -rf constant/polyMesh`, after the whole mesh build, and
  after the resume early-exit — so in resuming mode it never fired at all) and
  matches the serial path (`pgrep -x interFoam`). `MESH_ONLY=1` is EXEMPT, so
  2-minute mesh sweeps run alongside a solve. `setFields` is FATAL (it was
  `|| true`; a failure starts the tank as pure air and produces a complete,
  plausible, meaningless force history). checkMesh now has a bar: **0**
  zero-volume cells, **10** incorrectly-oriented faces (calibrated between the
  fixed KCS mesh, 5 faces, which SOLVES, and the mirrored KCS.igs mesh, 73,
  which dies on the first timestep). `--force` / `FORCE=1` overrides.
- **Regenerating a FIXED case over a FREE one no longer leaves it moving.**
  `dynamicMeshDict` and `pointDisplacement` were written and never removed, and
  `correctPhi yes` plus the setFields `boxToFace` block were unconditional — so
  a regenerated fixed case was not the configuration that produced the recorded
  numbers. All four are now gated on `free_motion`.

## Gate 2M: KCS meshes cleanly now; the NUMBER is still owed

The mesh blocker is closed (above). Geometry pipeline and acceptance data were
already done (`benchmarks/kcs.py`, displacement **-0.267%** re-measured on the
committed STL — the -0.09% previously recorded here and in kcs.py was a second
figure for one measurement; EFD Ct 3.711e-3 @ Fn 0.26, **7**-group scatter
3.620-3.733e-3 — the band is min/max over the seven rows transcribed in
`SUBMITTED_CT_FINEST`, not the 13 the docstring used to claim).

Still open: the 75 s (5 flow-through) KCS solve on the fixed mesh, ~16 h at
637k cells on 10 ranks. Run it resumably:

    openfoam scripts/run_campaign.sh runs/kcs_iso 10

Last recorded Ct was 4.283e-3 = **-15.4%** against EFD, on the OLD 306k mesh
with y+ median 2475 and 32% layer coverage. The new mesh addresses all three
contributors, so this number should be re-measured before it is reasoned about.
Then the GCI triplet (scale 1, sqrt2, 2) and `data/baselines.json`.

Geometry notes that remain true: sewing is MANDATORY (`--deflection 0.001
--sew-tol 1e-3`), run `surfaceCheck -checkSelfIntersection` (plain surfaceCheck
calls a broken surface fine), and keep `symmetric=True` with `type symmetry`
(NOT `symmetryPlane`).

Open and recorded (see ALIGNMENT.md): a SECOND benchmark anchor is owed. KCS
shares no chine/transom/spray physics with the SKUs, so Gate 2M passing is not
small-craft validation.

## Design-side invariants (audit 2026-08-05)

The recurring defect in this codebase is A NUMBER DECLARED TWICE. Every one of
these was a real drift found by measurement, not a style preference:

- **Limits live in `navalai/limits.py`.** GM floor, freeboard floor, ply
  thickness, bend-radius ratio, trim/list limits. `optimize.py` and
  `evaluate.py` had private copies and they drifted (GM 0.35 vs 0.45).
- **Constraints come from the ladder.** `evaluate.CONSTRAINT_NAMES` /
  `Evaluation.g` is the ONE inequality vector; NSGA-II consumes it. Add a check
  to `evaluate()` and the optimizer is constrained by it automatically.
- **One weight model.** `weights.MassItem`/`aggregate` is the positioned truth;
  `energy.weight_items` produces it and `dynamics.inertia` consumes it. There
  were three placement tables and they disagreed by 0.7 m on payload LCG.
- **`hydrostatics` owns both metacentres.** `bm_l` uses the parallel axis
  through LCF, not midships.

## WHERE TO PICK UP (end of 2026-08-05 Mac session)

**Gate 2M is now MACHINE-CHECKED, not prose.** `scripts/gate2m.py <case-or-root>`
computes C_T, compares it to the KRISO EFD 3.711e-3 and the Tokyo-2015 scatter
band, runs Roache GCI over a triplet, and prints PASS/FAIL. It REFUSES a verdict
it cannot support: an unsettled grid (drift > 5% over the last fifth) is excluded
and reported, and fewer than three grids gives "C_T comparison only, NO GCI".

    python scripts/gate2m.py runs/kcs_sym        # live, single grid
    python scripts/gate2m.py runs/kcs_gci        # the triplet, when it exists

**Running now:** `runs/kcs_sym` — symmetric, 241,946 cells, 75 s, ~6.1 h,
resumable (`openfoam scripts/run_campaign.sh runs/kcs_sym 10`).

Two cost fixes that were sitting unused and cost 2.6x on every experiment:
- `--symmetric` on make_case.py. The hull IS symmetric, so the full-width domain
  computed a mirror image of itself: 637k cells -> 242k, 16.2 h -> 6.1 h.
- `_FS_BOX["z"]` 0.05 -> 0.025. The fine band was +-0.36 m against a wave field
  of roughly +-0.06 m — six times taller than the physics occupies.

Then, in order:
1. When `runs/kcs_sym` settles, `scripts/gate2m.py` gives the single-grid C_T.
2. Build the triplet (`make_case.py --triplet --symmetric`) for the GCI. Budget
   honestly: medium is ~3x coarse and fine ~8x, so ~3 days on this Mac.
3. **Free sinkage and trim.** KCS Case 2.1 is towed FREE to sink and trim; we
   solve FIXED. We are comparing against a different condition, and it is a
   known part of the error. Needs `rigidBodyMotion` — code, not compute.
4. Gate 2U against the bar it actually claims (`mesh_robustness.py --solve`),
   not the clean-checkMesh proxy, which MEASURED as not predictive in either
   direction: KCS solves with 5 wrongly-oriented faces, and an own-hull mesh
   with a perfect checkMesh is in the same batch.
5. Second anchor (Fridsma hard-chine, or DSYHS). KCS will never validate chine,
   transom or spray physics — Gate 2M green is not small-craft validation.

### Rendering: the free-surface isosurface does NOT work on refineMesh cells

`scripts/render_case.py` produces noise on any case with `_REFINE_ROUNDS > 0`.
Hanging-node cells are POLYHEDRA and ParaView cannot contour them; MergeBlocks,
Tetrahedralize and ResampleToImage+mask were all tried and all failed. The older
`renders/medium-t40-fixed.png` is clean because that mesh had no such cells.

This is COSMETIC. The physics was verified numerically instead, and is sound:
MEASURED on `runs/kcs_iso` at t=7.5 — **2.6 interface cells per column** (a clean
VOF interface is 2-4), 45.4% water / 50.7% air, alpha bounded -6e-5..1, Phase-1
volume constant to 0.005%. Do not re-diagnose the interface from the picture.

Two render bugs that WERE real and are fixed: the hull patch selector is
`/Root/boundary/hull` (NOT `/Root/patch/hull`, which silently yields 0 cells),
and `ColorBy(disp, None)` throws on this ParaView — it was caught and reduced to
a one-line note, so every wave render was produced with NO HULL IN IT. A missing
hull and a broken interface at the hull then look identical, which is exactly the
distinction the picture exists to make. Both now fail loudly.


## Verification

- `python -m pytest tests/ -q` (expect all green, ~3 min) and
  `python -m navalai.gates` before/after non-trivial changes.
- Tests encode the gates; new physics/fixes get a gate test with the
  measured bar and a comment naming the incident that motivated it.
