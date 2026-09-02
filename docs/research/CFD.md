# RESEARCH RECORD — CFD measurements

> **Role: RESEARCH / EVIDENCE.** Dated measurement records for the L3 tier.
> This file holds *what was measured, on which run directory, and what it
> refuted*. It carries **no plan and no gate status** — the plan is
> `docs/BUILD-PLAN.md`, gate status is `python -m navalai.gates` and
> `data/gate-ledger.json`. Where a record was later superseded, the earlier
> record is kept **with the superseding measurement beside it**, because the
> elimination work is the part that cost machine-days.
>
> Operating lore — how to mesh, what dies, what to do on the Mac — lives in
> `CLAUDE.md` and is deliberately not repeated here.
>
> **Run-directory status, checked 2026-08-11** (LESSONS defect class 5: a
> record that cites a deleted directory is not a record):
>
> | run | still on this Mac? |
> |---|---|
> | `runs/kcs_s1` | **YES** — 3.40 flow-throughs, checkpoint intact, resumable |
> | `runs/kcs`, `runs/kcs_sym`, `runs/kcs_iso`, `runs/kcs_free`, `runs/kcs_gci` | present |
> | `runs/val_coarse5`, `runs/seiche_u_half`, `runs/beach`, `runs/wigley`, `runs/lts`, `runs/lowfn`, `runs/val_coarse`, `runs/kcs_gci2` | **DELETED.** §1 and §4 quote them; those numbers cannot be re-derived without re-running |

---

## 1 · 2026-08-06 — "the pressure oscillation is a tank mode, but not the seiche"

**SUPERSEDED as a conclusion by §2. Kept for its method and its refutations,
which stand.** Tool: `scripts/tank_resonance.py`. Gate test:
`tests/test_tank_resonance.py`.

    python scripts/tank_resonance.py runs/val_coarse5 --surface

### The question

`runs/val_coarse5` (symmetric KCS, `_NX_BASE` 57, `--n-layers 5`, 230 725
cells, 19.81 s = 1.33 flow-throughs, mesh clean: 0 zero-volume cells, 0 wrongly
oriented faces, max skewness 8.93, Phase-1 volume constant to 7e-5) split into
two halves that behaved completely differently:

- **Viscous**: steady at 1.22–1.36× ITTC-57 for the whole run. A KCS form
  factor (1+k) of 1.10–1.15 is exactly that band, so the wall model is right.
- **Pressure**: oscillated between 0.27× and 5.92× the expected 20.8 N, and
  passed THROUGH ZERO into thrust. Per-second means: −7.07, −1.51, −29.23,
  −50.30, −59.35, −39.87, −5.78, **+14.42**, −10.53, −47.83, −62.05, −71.83,
  −40.69 N. No real hull drag does that.

The ship-wave period at Fn 0.26 is 2πU/g = 1.41 s, so the ~6 s oscillation was
domain-scale. The hypothesis on record was a **longitudinal seiche**,
T = 2L/√(g h) = 7.75 s for this 32.75 m × 7.28 m tank.

### The verdict recorded at the time

The disturbance was read as a free-surface gravity wave whose WAVELENGTH the
domain selects (~11.5 m, tank mode n=6, λ = 2L/6 = 10.92 m), running upstream
and reflecting off inlet and outlet, seen by the hull **Doppler-shifted**:

    T = λ / ( c(λ) − U )        c from the full dispersion relation

That prediction differs from `2L/√(gh)` in the one way that matters: it MOVES
WITH SPEED.

### The deciding measurement: the same tank at two speeds

`make_case.py` derives tank depth as `max(1.0·Lwl, 1.5·π U²/g)`, and at both
speeds the first term wins — so halving U left the domain **bit-identical**
(L = 32.7537 m, h = 7.2786 m) and changed only the flow. Depth could not be
swept: the generator exposes no depth knob.

| run | U (m/s) | mesh | record | λ measured | T measured | λ/(c−U) | 2L/√(gh) |
|---|---|---|---|---|---|---|---|
| `runs/val_coarse5` | 2.196 | 230 725 cells | 19.79 s | **11.44 m** | **5.53 s** | 5.64 s (−1.9%) | 7.75 s |
| `runs/seiche_u_half` | 1.098 | 102 422 cells | 23.96 s | **11.50 m** | **3.67 s** | 3.66 s (+0.3%) | 7.75 s |

1. **The wavelength did not move.** 11.44 → 11.50 m across a factor of two in
   speed AND two different meshes (background scale 1.0 and 0.7). The DOMAIN
   sets it, not the ship and not the cell size.
2. **The period did move**, by exactly the Doppler shift — 0.3% and 1.9%, with
   no fitted parameter anywhere.
3. **The still-water seiche predicts 7.75 s at both speeds** and matches
   neither: 40% high at full speed, 111% high at half.

The measurement is of the FREE SURFACE, not of the forces: `alpha.water × V`
integrated per x-bin over the whole tank at every saved time, then
`eta'(x,t) = A(x) cos(ωt) + B(x) sin(ωt)` fitted after removing the snapshot
mean (which cancels the hull's displaced volume and the steady Kelvin pattern).
Two independent checks confirmed a real gravity wave rather than a numerical
mode: the measured intrinsic phase speed matched the dispersion relation for
the measured wavelength to **+0.9%** and **−0.2%**, and the wavelength was
resolved by **80** free-surface cells on the fine mesh (`fs_dx` 0.14366 m) and
**56** on the coarse one (0.20471 m) — nowhere near the cell size, and the two
counts differ by 1.4× while the measured wavelength differs by 0.5%.

Integrating rather than contouring is deliberate. `scripts/render_case.py`
records that ParaView CANNOT contour this mesh — the z-only `refineMesh` rounds
leave hanging-node polyhedra. A volume integral does not care.

### Why Fn 0.26 was argued to be the worst case

T(λ) = λ/(c−U) has a minimum where `dT/dλ = 0`, i.e. at c = 2U — precisely
where the GROUP velocity c/2 equals U and the wave's energy holds station in
the tank. There,

    λ_block = 8 π U² / g          T_min = 8 π U / g = 4 ship-wave periods

At Fn 0.26 that is λ 12.35 m against a tank mode at 10.92 m: they nearly
coincide. At half speed they are 3.09 m and 10.92 m apart, and the pressure
history correspondingly refused to yield a single period at all (41.7% of the
detrended variance, below the 50% bar).

The curve is also FLAT near its minimum: at Fn 0.26, tank modes n=4..8 predict
5.76 / 5.64 / 5.65 / 5.75 / 5.94 s. **No 19.79 s record separates them**, and
the tool reports the FAMILY, never a mode number.

### What was refuted, and how — this part survives §2

- **Still-water seiche, T = 2L/√(gh) = 7.75 s.** Refuted by the speed sweep (it
  cannot move with U, and the measurement moved 5.53 → 3.67 s), and
  independently by the mode shape: standing score 0.34 and 0.17 where a
  standing wave is 1. *Caveat, stated because it cuts against the argument: a
  tank mode in a CURRENT is not a clean standing wave either — its upstream and
  downstream components share a frequency but not a wavelength — so a low
  standing score refutes the still-water form specifically, not "a tank mode".*
- **Transom ventilation** (the other candidate on record; the KCS transom
  measures 100% wetted where it should ventilate). Refuted: the wave was
  coherent over the ENTIRE tank including 10 m ahead of the bow, its wavelength
  was speed-independent, and it obeyed the free-surface dispersion relation.
  Nothing local to the stern does any of those three.
- **A first, wrong reading of this same data: "the trapped band, λ = 8πU²/g".**
  At Fn 0.26 the measured wavelength (11.44 m) sat 7% from the blocking
  wavelength (12.35 m) and c/U came out 1.94 against a predicted 2.00, which
  looked conclusive. It was a coincidence of the design point: that model
  predicts λ ∝ U², so half speed should have given 3.09 m, and the measurement
  gave 11.50 m. **One speed was not enough to tell the two apart, and the
  second speed cost four minutes of compute.**

### What the record could NOT say

A period needs cycles. Every other run in the repository was checked and every
one of them REFUSED:

| run | record | why no period |
|---|---|---|
| `runs/beach` | 10.38 s, 0.70 flow-throughs | best sinusoid explains 33.1% (bar 50). Its leading candidate at 5.63 s needs 11.3 s of record; an unbounded FFT returns 10.40 s — the record length |
| `runs/wigley` | 9.98 s, 0.66 flow-throughs | 20.2%. Unbounded FFT returns 10.00 s — the record length |
| `runs/lts` | 'time' 10..2000, dt 10 | pseudo-time. Refused outright |
| `runs/lowfn` | — | no `force*.dat` was ever written |
| `runs/val_coarse` | 4 samples | diverged at t = 0.0072 s |
| `runs/kcs_gci2/coarse` | 1.95 s, 0.13 flow-throughs | fits 0.82 s at 65.9%, matches no candidate: UNEXPLAINED |

`runs/beach` is the calibration point for the 50% bar, and it is not academic.
At the old 25% bar the tool returned "seiche n=3, 4.05 s" for it — on the SAME
tank at the SAME speed where 19.79 s of record gives 5.95 s. **A short record
does not find a different mechanism; it finds whatever it is allowed to find.**

### The fix proposed at the time, and why it was not bought

Not solver tuning, not deepening the tank:

1. **Absorb, do not reflect.** The inlet is `fixedValue U` and the outlet
   `outletPhaseMeanVelocity` + `zeroGradient p_rgh`; both are perfectly
   reflecting for gravity waves. A relaxation/damping zone over the last
   1–1.5 Lwl at each end removes the energy. ESI v2606 has **no
   `verticalDamping` fvOption** (that is an OpenFOAM.org facility — checked, not
   present, recorded in `navalai/cfd/case.py`); the options are its
   `waveModels` absorption BC with a `constant/waveProperties`, or an explicit
   momentum sink over a `cellZone`. **This is weeks of work, which is why §2
   mattered so much.**
2. **Or dissipate, the reference's way.** The Wolf Dynamics KCS deck has no
   damping model either — it leaves 2.31 Lpp of run-out coarsening 32× and lets
   numerical dissipation eat the waves. This project pulled the refined wake
   forward to −1.0 Lwl for that reason, leaving 1.5 Lwl of run-out.
3. **Domain sizing, secondary.** This project's domain is 1.5–2.6× smaller than
   the DTCHull reference on every axis (worst in half-width, 0.50, and depth,
   0.39). Lengthening the tank moves the mode wavelengths (2L/n) but does NOT
   remove the mode — the ends still reflect — and it costs cells cubically.
4. **Do not chase it with run length.** The oscillation had not decayed at
   1.33 flow-throughs and had not decayed at 24 s.

### Compute spent

10.5 minutes of machine time, all of it on this Mac at np=10 —
`postProcess -func writeCellVolumes/writeCellCentres` on `runs/val_coarse5`
(~40 s, no re-solve: the fields for t = 4, 6, 8, 14, 16, 18 had survived);
`runs/seiche_u_half` generation + mesh + 9 s of solve (~90 s mesh, 152 s solve,
102 422 cells, `--scale 0.7 --symmetric --transient --n-layers 5`, checkMesh 0
zero-volume, 4 incorrectly-oriented faces against a bar of 5, max skewness 5.69
against a bar of 20); the same case resumed 9 → 24 s (267 s — at 8.90 s the fit
sat at 4.21 s against a scan capped at 4.45 s, i.e. against its own bound, so
24 s was needed before anything could be concluded); `postProcess` on it (~60 s).

Mass was conserved on both runs (Phase-1 0.800306 → 0.800242 on the half-speed
case, 8e-5), alpha stayed bounded, and `pmset -g log | grep -i thermal` was
clean over the session.

Note what `runs/seiche_u_half` was NOT: at U = 1.098 one flow-through is
29.83 s, so 24 s is **0.80 flow-throughs**. It is a period measurement — a
timescale — and a tank mode is excited by the impulsive start rather than by a
settled wake. Nothing in it is a resistance number and `tank_resonance.py`
prints that warning itself.

**The cost lesson, which generalises:** this diagnosis cost 10.5 minutes
because it measured a *period* rather than a drag coefficient, so mesh
resolution barely mattered. The alternative plan was a three-day GCI triplet.

---

## 2 · 2026-08-07 on `runs/kcs_s1` — RE-MEASURED, and it is NOT an oscillation

**This supersedes §1's conclusion and the "3–6× and growing" reading that
preceded it.** First reproducible KCS run in the repository since the one the
ledger records as deleted. Symmetric, `_NX_BASE` 57, `--n-layers 5`,
`--transient`, 230 730 cells, 92.6% layer coverage (4.63 of 5 achieved), 0
zero-volume cells, 0 incorrectly-oriented faces, max skewness 8.93. Mass
conserved: Phase-1 volume fraction 0.80015 flat, alpha bounded [−3.9e-6, 1].
Stopped deliberately at **t = 50.7 s = 3.40 flow-throughs** (a compute budget,
not a failure); the checkpoint is intact and the case resumes.

### The run converges, and it converges to the wrong number

| flow-throughs | E%D vs EFD | drift |
|---|---|---|
| 1.34 | −98.1% | 26.7% |
| 2.22 | −47.0% | 15.2% |
| **3.40** | **−43.5%** | **0.31%** |

Drift has collapsed to **0.31%**, far inside the 5% bar. The transient has
washed out, and C_T has flattened.

**So the remaining error is not a settling problem, and more wall-clock will
not remove it.** That is the finding, and it retires the standing assumption
that Gate 2M is waiting on run length.

### The error is entirely in the pressure component

Decomposed against the ITTC-57 line at Re = 1.402e7 (Cf 2.8312e-3, friction
65.2 N on 9.551 m² of wetted surface):

| component | measured | expected | ratio |
|---|---|---|---|
| **viscous** | 75.6 N | 65.2 N (ITTC-57) | **1.161×** — inside the 1.10–1.15 form-factor band, marginally above |
| **pressure** | 46.9 N | 20.2 N (EFD total − friction) | **2.32× too high** |
| total | 122.5 N | 85.4 N | 1.43× |

**The viscous half is right.** 1.161× ITTC-57 is what a KCS form factor should
give, and it is stable: batch error 1.7%. The wall model, the layer stack and
the near-wall mesh are doing their job — which is exactly what the 2026-08-05
mesh rebuild was for, and this is the first run to confirm it end to end.

**The pressure half is 2.3× too high and it is noisy, not trending:**

    drift_pressure  0.84%      error_pressure  36.1%
    drift_viscous   1.15%      error_viscous    1.7%
    drift_total     0.31%      error_total     36.2%

A 0.8% drift with a 36% batch standard error means the window mean is not
reproducible across its own window while having no trend. **Averaging longer
averages noise.**

### It is NOT a tank mode either

`scripts/tank_resonance.py` on 2 041 samples over 33 s: **the best single
sinusoid explains 0.4% of the detrended signal against a 50% bar — NO RESULT,
there is no coherent oscillation to name.** Every candidate mechanism (seiche
n=1..3, Doppler tank modes n=1..8, blocking minimum, ship transverse wave) had
enough cycles in the record to have been seen.

This **revises** §1 and the earlier R5.5 reading of a ~5 s pressure
oscillation. On this mesh family the pressure signal is broadband, not
periodic. The earlier record was taken on a different family (`_NX_BASE` 54) at
1.33 flow-throughs, where a rising quarter-cycle of anything looks like a
trend — so the two are not in contradiction so much as the older one was
under-sampled.

**A further trap, recorded because it was nearly not seen:** two runs on ONE
domain could not separate λ/3 from the domain half-width, because 1.5 Lwl =
10.918 m and 2L/6 = 10.92 m are the same number in that domain. A
domain-LENGTH sweep is the experiment that would separate them: at fixed U,
2L/n moves with L and the half-width does not.

### What this means for the next experiment

Extending to 5 flow-throughs was necessary and is no longer the blocker. The
candidates are now ordered by evidence rather than by guess:

1. **Free sinkage and trim.** KCS Case 2.1 is towed FREE to sink and trim; this
   run is FIXED. That is a different condition, it acts on the pressure
   component specifically, and it is CODE (`rigidBodyMotion`) rather than
   compute. The single most likely candidate, because the viscous half being
   right localises the error to exactly what sinkage and trim move.
2. **Free-surface resolution.** `cells_per_wavelength` is 21.5, barely over the
   ≥20 bar. The pressure component is the wave component.
3. **Grid.** This is one grid, and the coarse member. The 36% batch error must
   be understood before a triplet means anything — three noisy numbers do not
   make a Richardson extrapolation.

`gate2m.py runs/kcs_s1` correctly returns **NO RESULT, exit 2**. The −43.5% is
recorded here as a diagnosis and is quoted nowhere as a result.

---

## 3 · Hypotheses eliminated at real compute cost — the do-not-re-try list

From the 2026-08-06 gap-closure sweep across six runs (`runs/kcs_iso`,
`runs/kcs_sym`, `runs/kcs`, `runs/beach` and two since deleted). The framing of
that sweep — "3–6× and **grows with time**" — is superseded by §2, which
measures 2.32× with no growth. **The eliminations below are not superseded**,
and each cost machine-hours:

- *insufficient convergence* — no; on that family the error grew with
  convergence, and on the §2 family it is flat with a collapsed drift.
- *missing boundary layer* — fixed; viscous corrected, pressure unchanged.
- *wave reflection off the outlet* — a beach (run-out 0.6 → 1.5 Lwl) and a
  deeper tank (0.6 → 1.0 Lpp) made it WORSE (2.9× → 5.7× at the same t).
- *LTS as a cheap path* — far worse (14.5×). Waves are inherently unsteady, so
  per-cell pseudo-timesteps make propagation speed meaningless. LTS is kept
  only as a flow-field initialiser and can never produce a resistance number.
- *mass leak* — no; Phase-1 volume constant to 0.001%.
- *a tank mode / relaxation zone* — refuted by §2 at 3.40 flow-throughs. A
  relaxation zone would have been weeks of work against a mechanism measured
  not to exist.

The per-run table that framing rested on, kept so the numbers are reviewable:

| run | t | pressure | vs expected (~20.8 N) | viscous | vs ITTC |
|---|---|---|---|---|---|
| kcs_iso | 7.5 s | 41.4 N | 2.9× | 40.9 N | 0.63× |
| kcs_sym | 13.7 s | 36.8 N | 2.6× | 52.8 N | 0.82× |
| kcs | 76 s (settled) | 60.1 N | 4.2× | 93.3 N | 1.44× |
| beach + deep tank | 8–10 s | 84.8 N | 6.0× | 76.0 N | 1.18× |

Every one of those values lies inside the envelope §1 measured, which is how
four samples of one broadband signal read as a trend.

**One candidate from that sweep is still open and is not addressed by §2:**
whether the wave-resistance machinery is systematically wrong, decided by a
Wigley run against Michell.

---

## 4 · The near-wall / y+ blocker brief — SUPERSEDED 2026-08-06, kept for its eliminations

> This brief was written for an outside reader while the blocker was believed
> to be the wall model. **It was not.** The root cause was a **38:1 background
> cell**: `hexRef8` refines ISOTROPICALLY, so every refinement level preserved
> the aspect ratio while shrinking the height, and snap displacement — which
> scales with the LONG edge — moved nodes several cell HEIGHTS and folded cells
> inside out. That single fact explains every failure listed below, including
> the ones the brief calls unexplained: (2,3) clean / (3,4) worse / (4,5) worse
> still, `addLayers false` producing a byte-identical broken mesh, and snap
> `tolerance` having no effect. `CLAUDE.md`'s root-cause section carries the
> four-step fix and its measured result (72 988 zero-volume cells → 4 open
> cells).
>
> **The C_t figure quoted below is one of five that circulated (gap J1) and is
> superseded.** The one measurement lives in `data/gate-ledger.json`.
>
> Kept rather than deleted because the elimination work is real and re-doing it
> would cost machine-days. PLM §3 step 7: superseded material is removed with a
> note, never left ambiguous — this is the note.

### The blocker as it was stated

**We cannot get y+ into the wall-function validity band (30–300) on any mesh
configuration that also produces a valid mesh, so skin friction — most of the
drag at our Froude number — is computed outside the model's range of validity.**

Benchmark: KCS containership, model scale 1:31.6, LPP 7.2786 m, Fn 0.260
(U = 2.196 m/s, Re = 1.26e7). Published tank data: C_t = 3.711e-3 (KRISO),
CFD scatter 3.620–3.733e-3.

Our result at the time: **C_t = 9.33e-3, i.e. −151% vs EFD, 2.5× too high.**
Only **16.3% of wetted hull faces** lay in 30 ≤ y+ ≤ 300; median y+ 2475. On
our own (chined, small-craft) hull the same pipeline gave 2.0% in band and
viscous drag 2.62× the ITTC-57 flat-plate line. Both hulls pointed the same way.

### The mechanism believed at the time

To land y+ ≈ 30 at this Reynolds number the first cell must be ~0.8 mm. The
local hull cell is 76–152 mm — a 100–200× jump, needing either (a) ~15 prism
layers or (b) a much finer surface cell.

- (a) failed: snappyHexMesh inserted ~50% of layers at n=3, 26% at n=8, 11% at
  n=15, and at n≥6 interFoam died on the first timestep. `nLayerIter` /
  `nRelaxedIter` changed nothing.
- (b) failed: raising `refinementSurfaces` from (2 3) to (3 4) gave 18
  incorrectly-oriented faces (negative face pyramids) and interFoam died at
  t≈8e-4; (4 5) gave zero-volume cells. Verified as the castellation stage, not
  layers: `addLayers false` produced a byte-identical broken mesh.

Refinement making things *worse* was the strange part — the signature of a
sub-cell defect that coarse cells step over. But the surface was clean:
`surfaceCheck -checkSelfIntersection` reported "not self-intersecting", OCC
`BRepCheck_Analyzer` said the shape was valid (one shell, 649 faces), and
displacement matched published to −0.14%.

### Ruled out, with measurements

| hypothesis | test | result |
|---|---|---|
| prism layers cause it | `addLayers false` | identical broken mesh |
| STL sliver triangles | vertex weld | merges nothing (slivers are *collinear*, not coincident) |
| mirrored-hull keel seam | switched to half hull + symmetry | skewness 52.2 → 9.5, defect persists |
| self-intersecting STL | fixed sew tolerance + ear-clip capping | surface clean, defect persists |
| bad IGES export | swapped to a NAPA `PTOL=0.002` export | zero-volume 14 → 2, still dies |
| solver startup transient | initial `deltaT` 1e-3 → 1e-5 | still dies at t≈1e-5 |
| free-surface refinement box | removed it | skew 63 → 7, still 7 zero-volume cells |

### The architectural theory, which was right and initially unlandable

OpenFOAM's own reference case (`$FOAM_TUTORIALS/multiphase/interFoam/RAS/
DTCHull`) does NOT let snappy refine. It runs **6 rounds of `topoSet` +
`refineMesh` first**, then snappy with `refinementSurfaces level (0 0)` and no
refinement regions. The decisive line is in `refineMeshDict`:

    directions ( tan1 tan2 );      // x and y ONLY, never z

Free-surface ship meshes need **anisotropic** refinement — fine in x,y near the
hull, fine in z only at the waterline, coarse in z at the keel. `refineMesh`
does that directionally. **snappyHexMesh refines isotropically**, so buying x,y
resolution through snappy levels drags z along, and every level boundary is a
hanging-node transition.

The first implementation failed: the refinement rounds worked (429k → 1.716M
cells, exactly 4× per round) and snappy then aborted with

    FATAL ERROR: cell 9404 of level 0 uses more than 8 points of equal or
    lower level      (hexRef8::setRefinement, hexRef8.C:3763)

i.e. `danglingCellRefine` still wanted to refine, and `hexRef8` cannot refine
cells that `refineMesh` created. **The landed fix inverts the order** —
castellate + snap FIRST on a near-cubic background, then z-only `refineMesh`,
then a layers-only snappy pass — and it is documented in `CLAUDE.md`, including
why the order is forced from both sides.

### The mesh constants do not transfer between hulls

MEASURED 2026-08-06: KCS bridges its 37.9 mm hull cell with 5 layers; Wigley's
52.1 mm cell needs 10, and capping at 5 there reproduces exactly the
last-layer/cell ratio (0.082 vs 0.071) that produced ZERO layers on KCS. The
layer count is therefore DERIVED per hull by `n_layers_to_bridge` and guarded
at both ends. **Any constant tuned on one hull is suspect** — `_HULL_REFINE`,
`_TARGET_YPLUS` and the layer count were all tuned on KCS.

And the derived count is not automatically safe: at `_NX_BASE` 57 the symmetric
KCS coarse case derives **7**, and that mesh passes every build-time check and
then kills interFoam at t = 0.0072 s. The mesh-time gate, not a build-time
predictor, is the mechanism — Wigley survives a *thicker* relative stack
(1.084) than the one that kills KCS (0.952), so no build-time predictor exists.
`CLAUDE.md` carries the sweep and the bars it produced.

---

## 5 · Still owed

- **A wetted-only (alpha.water-masked) y+.** The `hull` patch includes deck and
  topsides, which sit in AIR, so the patch average and maximum are dominated by
  dry faces. Only the MIN currently reflects the wetted, layered surface.
- **A domain-LENGTH sweep** at fixed U, the only experiment that separates a
  tank mode (2L/n, moves with L) from the domain half-width (does not).
- **A Wigley run against Michell**, which is the surviving test of whether the
  wave-resistance machinery is systematically wrong.

---

## 6 · 2026-08-12 — the wave/air blockMesh boundary is a 15.3:1 slab, and hull 4's 38 faces live inside it

**Owner of the question:** Gate 2U mesh robustness. **Configuration:** seed-0
25-hull grammar batch, `--scale 1.0 --speed 2.57`, `n_layers = 7` (the shipped
`_MAX_LAYERS` cap), full-width domain, `MESH_ONLY=1` through
`navalai/cfd/run-case.sh` — no solves. Run directories `runs/zb_*` and
`runs/zba_h*` on this Mac at time of writing.

### The handover, and what it already ruled out

Hull 4 (lwl 8.9417) failed at every prism-layer count. The NURBS agent's Stage
A (`bbf1a47`) put the chine on a row of the grid and removed a ~10 mm deviation
floor, re-meshed hull 4, and measured **38 wrongly-oriented faces before Stage
A and 38 after — not one moved**, with `nonOrtho` 98.9835 and `skew` 10.4659
unchanged. The `wrongOrientedFaces` set decoded to a 26 mm band at fixed z
spanning 44% of Lwl. `data/gate2u-layer-search-mesh.json` shows the same
`38 / 98.9835 / 10.4659` at n = 3, 4, 5, 6, 7, 8 **and** 9 — a defect invariant
to both the geometry and the layer count.

### The mesh arithmetic, which is scale-free

`_Z_EXPANSION = 20.0` was a **total** expansion (`simpleGrading (1 1 20)`, last
cell / first cell, z upward) applied to both graded outer z-blocks. In units of
Lwl — and these are scale-free, so they held on every case this project has
ever meshed:

| block | height | n | cell AT the core band | core band cell | step |
|---|---|---|---|---|---|
| air  | 0.160 L | 4 | 0.005148 L (46.0 mm) | 0.045 L (402.4 mm) | **8.74x finer** |
| deep | 0.910 L | 7 | 0.36923 L (3301 mm)  | 0.045 L (402.4 mm) | **8.20x coarser** |

The air block's grading was the right direction and eight times too strong: the
mesh got *finer* moving away from the free surface and then coarser again. The
first air cell is 705.9 x 705.9 x 46.0 mm — **15.34:1**, and `hexRef8` preserves
aspect ratio at every level, so at hull refinement level 4 it is
44.1 x 44.1 x 2.88 mm, still 15.34:1. That is CLAUDE.md's 2026-08-05 root cause
(snap displacement scales with the LONG edge, so a few-mm move is several cell
HEIGHTS and the cell folds) reintroduced inside a 46 mm horizontal slab that no
hull feature marks. The ratio is a **constant 15.335 for every hull**, because
dx and the first air cell are both proportional to Lwl — which is why it has no
contrast group and could not have been found by comparing hulls.

The deep block's grading was **inverted**: coarsest cell (3.30 m) against the
402 mm core band, finest (165 mm) at the tank floor where nothing happens.

### The decisive experiment: move the boundary and see whether the faces follow

Hull 4, geometry byte-identical (`stl_sha256 3f8c87ae…`), n_layers 7, only the
z-block constants moving. Face coordinates decoded from `wrongOrientedFaces`
via `foamToVTK`.

| config | cells | zeroVol | wrongOri | skew | nonOrtho | face z-range | first air cell |
|---|---|---|---|---|---|---|---|
| `_Z_BANDS` 0.09, `_Z_EXPANSION` 20 | 916677 | 0 | **38** | 10.3992 | 98.9835 | 0.8105 .. 0.8365 | [0.804755, 0.850783] |
| `_Z_BANDS` 0.12, `_Z_EXPANSION` 20 | 843124 | 0 | **14** | 8.6104 | 89.1700 | **1.0774 .. 1.0897** | **[1.073006, 1.110405]** |
| `_Z_BANDS` 0.09, `_Z_EXPANSION` 1  | 1106081 | 0 | **0** | 2.4415 | 69.1067 | — (`Mesh OK`) | — |

**The faces moved with the blockMesh vertex.** The hull did not move; the
defect did. That settles the causal direction: it is located by the mesh, not
by the surface. And flattening the grading removes it entirely — 38 to 0, skew
10.3992 to 2.4415, nonOrtho 98.9835 to 69.1067, and checkMesh prints `Mesh OK`
on a hull that had failed three checks at every layer count.

The `_Z_BANDS` 0.12 arm is reported for its location, not its count: moving the
plane also moves what part of the topside sits at it, so 38 to 14 is not a
dose-response.

### The fix, and the companion change the data REFUSED

`_z_grading()` derives the air block's grading so its first cell equals the
ungraded core cell, bounded by an adjacent-cell ratio of 2.0. At the shipped
proportions (0.160 L over 4 cells against a 0.045 L core) that resolves to
**uniform**: 0.3577 L/8.94 m cells, an 0.889x step and a 1.97:1 first air cell.

Correcting the deep block the same way is the obvious companion change, and
**the batch refuses it**. 25 hulls, n_layers 7, `run-case.sh` bar (0 zero-volume
cells, <= 5 wrongly-oriented faces, <= 20 max skewness):

| configuration | bar | fixed | regressed | cells |
|---|---|---|---|---|
| baseline (`data/gate2u-cap7-mesh.json`) | **19 / 25** | — | — | — |
| both blocks derived | **16 / 25** | 4, 14, 18 | 0, 1, 6, 8, 20, 22 | +12.2% |
| **air block only** | **23 / 25** | 4, 10, 12, 14, 18 | 8 | **-0.2%** |

The controlled triple on hull 0, which is clean at baseline, shows there is no
additive story to tell:

    hull 0   air derived, deep 20.0   619094 cells   0 zeroVol    0 wrongOri  skew  3.17  CLEAN
    hull 0   air 20.0, deep derived   680425 cells   0 zeroVol    0 wrongOri  skew  4.52  CLEAN
    hull 0   BOTH derived             686237 cells  30 zeroVol  324 wrongOri  skew 53.62  REFUSED

Each change alone is clean and the pair is not. The deep block therefore keeps
`_Z_EXPANSION = 20.0` — inverted, wasteful, and **unmeasured as harmful**.

### KCS is untouched, and that is why nobody found this

Symmetric, scale 1, same STL, `MESH_ONLY`:

| n | grading | cells | zeroVol | wrongOri | skew | nonOrtho | layers achieved |
|---|---|---|---|---|---|---|---|
| 3 | fixed 20.0 | 227597 | 0 | 0 | 6.31765 | 73.4805 | 2.93 |
| 3 | derived air | 227597 | 0 | 0 | **6.31765** | **68.2707** | 2.93 |
| 5 | fixed 20.0 | 230725 | 0 | 0 | 8.93076 | 73.4805 | 4.63 |
| 5 | derived air | 230725 | 0 | 0 | **8.93076** | **69.5849** | 4.63 |

Identical cell count, identical zero-volume / wrongly-oriented / skewness,
identical layer coverage; maximum non-orthogonality improves by 4-5 degrees at
both counts. (The `fixed 20.0` rows reproduce CLAUDE.md's recorded KCS meshes
exactly — 227597 / 6.32 / 2.93 and 230725 / 8.93 / 4.63 — so the baseline is
the project's own record, not a re-derivation.)

The reason is one number: **KCS's deck top is z = 0.4021 m and the wave/air
boundary is 0.09 x 7.2786 = 0.6551 m.** No KCS geometry enters the air block at
all, so the benchmark every mesh constant in this file was tuned on is blind to
this defect by construction. CLAUDE.md already says a second anchor is owed;
this is the first measured instance of the benchmark being unable to see a
defect rather than merely not covering the physics.

The background aspect ratio the 2026-08-05 fix depends on is **unchanged**:
`dx / dz_core` is still 1.754 (the two equal 0.09 L core bands are untouched).
What changed is the FIRST AIR CELL's aspect, 15.34:1 -> 1.97:1.

### The sufficient condition was NOT found, and the search is at chance

The brief asked for the condition separating hull 4 from the crossers that mesh
clean. **There is none in the geometry, and the AUCs say so.** Measured over
all 25 hulls against the baseline refusal (zero-volume or > 5 wrongly-oriented
faces at n=7, 5 positives), on features computed from `Hull.closed_mesh` inside
the first air cell:

| feature | AUC |
|---|---|
| surface crosses the plane at all | 0.475 |
| hull triangles in the band | 0.295 |
| surface area in the band / Lwl^2 | 0.575 |
| area-weighted mean \|n_z\| (surface inclination) | 0.475 |
| z travelled per level-5 cell, in cell heights | 0.485 |
| distinct background columns the band footprint covers | 0.385 |
| max \|y\| in the band / Lwl | 0.625 |
| deck height / za | 0.580 |
| Lwl | 0.370 |

Every one is chance at N=25. Two facts explain why, and both are measurements
rather than excuses:

1. **The aspect ratio has no contrast group.** dx and the first air cell are
   both proportional to Lwl, so 15.335:1 is a constant across the entire batch.
   The hazard is identical for every hull; only whether a *snap* lands badly
   inside it varies, and that is not a property of the surface at the plane.
2. **The effect is not confined to hulls that reach the plane.** Hulls 8 and 12
   have their deck tops at 0.654 and 0.908 of za — neither touches the air
   block — and the air grading change flipped **both** of them (12 fixed, 8
   regressed). snappy's refinement propagation and the layer pass reach above
   the deck, so the air block's cell sizes matter to a hull that never enters
   it.

Consistent with `docs/LESSONS.md` and with commit `b5771fb`: a defect present
in every hull has no contrast group, and this one was found by moving the mesh,
not by comparing hulls.

### What is now owed

- **Hull 8 regressed and hull 5 did not recover.** Hull 8 goes 0/0/2.866 ->
  2 zeroVol / 34 wrongOri / 20.350 at n=7; `data/gate2u-layer-search-mesh.json`
  already records hull 8 as knife-edge in n (clean at 4 and 7, REFUSED at 6),
  so the two-sided layer search is the mechanism that should rescue it, and the
  23/25 above is the rung-0-only number. Hull 5 fails either way and its
  skewness intensifies (56.796 -> 3769.28); it is a different defect.
- **The 23/25 is at rung 0.** Re-run `scripts/mesh_robustness.py
  --layer-backoff` on top of this to get the number the ledger should carry.
- **The deep block is still inverted.** It puts a 3.30 m cell against a 402 mm
  core band and 165 mm cells at the tank floor. Correcting it is measured to
  cost more than it buys AT n=7 ON THIS BATCH, which is not the same as it
  being right. It should be re-measured once the layer search is in the loop,
  because six of its regressions may be knife-edge in n rather than caused.

## 3 · 2026-09-02, `runs/kcs_free1` — the FREE sinkage-and-trim run: NO RESULT at 4.02 flow-throughs, and what it measured anyway

The run §2 called for. Symmetric half-domain, 230 388 cells, `n_layers 5`,
`sixDoFRigidBodyMotion` (heave + pitch, KG = 0.2303 m), endTime 60 s =
4.02 flow-throughs, solved in five resumable slices by `scripts/cfd_batch.sh`
(~9 h wall total on 10 ranks). Mass conserved (Phase-1 0.800162 → 0.800098),
alpha in [−3.0e-6, 1], deltaT stable 1.8–2.2e-3 throughout, no thermal sleep.

**`gate2m.py` verdict: NO RESULT — not settled — and that refusal is the
correct reading of this data.** Over the last fifth (t = 48–60 s,
524 samples): total drift 19.1 %, pressure drift 18.7 %, batch errors
39.6 / 40.5 % against the 5 % bar. Every number below is therefore a
WINDOW MEAN OF AN UNSETTLED SIGNAL, recorded for direction, not for use:

    C_T (window mean)   4.5958e-3    E%D −23.8 %   (EFD 3.711e-3)
    sinkage             −12.04 mm    EFD −13.94 mm   drift 39.1 %
    trim                −0.111°      EFD −0.169°     drift 29.9 %

Three things this run DID establish:

1. **The free-motion machinery works end to end** — first production use of
   the `rigidBodyMotion` path: the hull sank and trimmed toward the
   measured attitude (sinkage passed through −10.6 → −31 → −6 → −12 mm), the
   solve stayed stable for 60 s of motion, and the case is reproducible
   from its manifest.
2. **The attitude oscillates with a period the run did not outlast.** The
   heave/pitch transient is still ringing at 4 flow-throughs — sinkage
   drift 39 % in the last fifth. The FIXED case settled at 3.4 FT (§2)
   because nothing was moving; the free case adds a slow decaying 6-DoF
   mode. Longer run needed, or stronger numerical damping — measure,
   don't guess which.
3. **The direction of C_T is toward the measurement, with a wide honest
   band.** The fixed-attitude history read E%D ≈ −80 %; this window mean
   reads −23.8 %. That is CONSISTENT with §2's localisation (the missing
   physics is what sinkage and trim move) — but with a 40 % batch error it
   is a direction, not a delta. Do not quote −23.8 % as a result; it is
   the same class of number as §2's struck-through oscillation readings.

**Next experiment: extend THIS case, not a new one.** `--end-time 90`
(6.0 FT, ≈ +2.5 h wall in one `cfd_batch.sh` slice, resuming from the
t = 57.648 checkpoint) answers whether the 6-DoF mode damps out. If at
6 FT the attitude still rings, the mode needs damping coefficients, not
more hours — and that is a case-setup change with its own budget line.

Operational finding, fixed the same day: a `cfd_batch.sh` `writeNow` stop
re-anchors the adjustableRunTime write grid, so endTime may never receive
a field write; `run_campaign.sh` judged completion by CHECKPOINT time and
declared a false DIVERGENCE on this complete run (re-solving its last
2.35 s twice on the way). Completion now takes max(checkpoint, solver-log
time); the checkpoint remains the resume truth, the log the completion
truth.
