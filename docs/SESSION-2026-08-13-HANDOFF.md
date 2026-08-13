# Session handoff — 2026-08-13

**THIS FILE CARRIES NO AUTHORITY AND NO STATUS.** Ask `python -m navalai.gates`,
`python scripts/reconcile_gaps.py` and `python -m pytest tests/ -q`. It exists
because a session ended at its context limit with uncommitted work in the tree
and two agents still running, and the next session needs to know what happened.
Delete it once its contents have landed in the artifacts that do own them.

## THE TREE IS UNCOMMITTED AND UNPUSHED. Nothing was committed this session.

Last full suite (second run, random ordering disabled): **1117 passed, 16
skipped, 5 failed**. Two of those five were fixed after that run (see below), so
the expected state is **3 failed, of which 2 are DELIBERATE**.

    open   README gate table stale     <- MECHANICAL. `python -m navalai.gates --readme --write`
    held   Gate 3E tripwire            <- DELIBERATE, see "decisions owed"
    held   A6b support-distance        <- DELIBERATE, bar restored on purpose

## What must happen before a push

1. `python -m navalai.gates --readme --write` — regenerate the gate table. It
   was deliberately NOT committed all session because it reflected other
   agents' uncommitted test counts; committing it early puts the README out of
   step with the committed tree and fails CI.
2. Record the two held reds in `data/gate-ledger.json` with a measured
   watermark, an owner and a `review_by` date, or CI is red with no explanation.
3. Full suite on a QUIET tree. A run taken while agents are editing is
   worthless — one `test_gate_integrity` failure this session was transient and
   passed on re-run.
4. Commit to `master` and push to `master`. One branch. No trailers.

## The typology-pin fix LANDED. The PLM pipeline delivers again.

`TYPOLOGY_RULES` banded `roundness` at (0.0, 0.15) / (0.0, 0.25) while
`unroll.hull_panels`, `engineer.assess` and `admissibility` all refuse any
`roundness > 0`. Disjoint except at one point, and `type_check` is a pure
rejection test, so a continuous sampler hit it with probability zero.

Both typologies were CONFIRMED sheet-built before the decision was applied:
`formlib.hard_chine_displacement` sells SHARP_CHINE on being "buildable from
flat sheet", `pram_dory` is the flat-bottom skiff, and `Typology` has exactly
two members. `navalai/unroll.py` is UNTOUCHED — its refusal was correct.

Implemented in `navalai/hull_ast.py`: a frozen `Pin(value, why)` that cannot be
misread as a band, `pins()`, `project(x, typology)` which sets pins and touches
nothing else, exact-equality verification in `type_check` with a refusal that
says PINNED and why (never "outside [0.0, 0.15]"), and `fit_typology(x)` as the
generator's question. `agents._builder` projects; a draw whose BANDS miss every
typology is forwarded UNPROJECTED so the Validator still rejects it at L0 and
the audit records why. `pipeline.py` and `generative.py` deliberately NOT
changed — projecting inside a checker would be wrong, and the GMM/PPCA samplers
are typology-agnostic (imposing SHARP_CHINE there would forbid the round-bilge
hulls the optimizer is allowed to search).

    4096 Builder draws        before          after
    pass as drawn             4 (none at 0)   0
    pass after projection     --              1594 (38.9%)
                                              SHARP_CHINE 1476, PRAM 118
    run_plm(n_designs=3)      0 delivered     3 delivered

Comparable to the 324/512 (63%) pre-rebuild figure at 39%. Gate test shipped in
`tests/test_stageB.py` with four arms including "roundness 0.07 is still
refused" and "the message says PINNED and does not print a band".

**REMEMBER THIS IS STILL A STOPGAP** — see the multi-chine note below. Pinning
to zero is correct for the unroller we have, not for boatbuilding.

## ONE AGENT WAS STILL RUNNING when the session ended

- **paper read** (`docs/research/HULL-GAN-PAPERS.md` only) — ShipHullGAN and
  the JACIII GAN paper. A first attempt died at the session limit one step
  before writing its file and lost everything; the relaunch was told to write
  incrementally. Check whether that file exists before re-running it.

## `tests/test_end_to_end_flow.py` HAS TWO AUTHORS

One agent's `STL_VOLUME_TOL_PCT` re-measurement block (referencing
`cfd.case._STL_NZ_FILLETED` 48 -> 96) and another's `_validated(...,
sheet_built=True)` projection helper are both uncommitted in that file, in
separate regions. Read it before editing.

## Decisions owed BY THE PROJECT OWNER — none of these were taken

1. **Gate 3E retirement.** The across-seed L1 error bar is **0.1471** against
   Gate 3's **0.15** bar, i.e. the bar is MET. It was HELD, not retired,
   because 1.9% of margin against a measured **1.97x** across-seed spread is a
   draw landing well, not a gate being met, and the tree was moving. Retiring
   it is a THREE-FILE change in one commit: the `data/gate-ledger.json` row,
   the `navalai/gates.py` row, and `tests/test_phase3.py`'s tripwire (whose
   docstring carries the work order). Doing one alone leaves the tree
   asserting two contradictory things.

2. **The flywheel deployment ratchet.** `make_baseline` pins `HARVEST_SEEDS[0]`
   (seed 21) as the deployable entry, and seed 21 flipped from the ensemble
   MINIMUM under the old genome to near the WORST of eight. Against the
   `ens_med * 1.25` threshold it refuses **3 of the 8 seeds the file itself
   certifies as honest** — a 37.5% false-refusal rate, and one of the three is
   the draw it deploys.
   `flywheel.py`'s stated reason for not widening `tol` to `seed_spread` is
   WEAKENED BUT NOT REFUTED, and it is MIXED:

       wh_per_nm   0.1130 x 3.0214 = 0.3415   BELOW the 0.35 floor
       rt          0.1206 x 3.0215 = 0.3643   ABOVE it

   so widening would make the ratchet inert for one quantity of two. Widening a
   tolerance is a bar move; it was left untouched.

3. **`unaccounted` mass at 50.2% of displacement.** Half the boat has no
   declared position. It is handled HONESTLY in `evaluate.py` (declared
   `MassItem`, placed at the aggregate's own centre so it moves no centre it
   has no right to move, carrying a 50% sigma) but `unaccounted_frac` is NOT a
   constraint row — `CONSTRAINT_NAMES` has 8 entries and none is mass balance.
   **MEASURED, AND IT REFUTES THE OBVIOUS HYPOTHESIS:** closing the gap does
   almost nothing to feasibility.

       target 6000 kg   feasible 4/30   median GM 0.278   unaccounted 29.1%
       target 4500 kg   feasible 6/30   median GM 0.302   unaccounted 11.6%
       target 3000 kg   feasible 5/30   median GM 0.283   unaccounted  0.0%

## THE BIGGEST UNRESOLVED FINDING: slender hulls fail a monohull GM floor

Feasibility is **6/40 (15%)**, dominated by `rules tier` (R-GM 12, R-OLH 8).
Median GM is **0.28 m against a 0.45 m floor**, and one sampled design floats at
**GM = -0.33 m**. The hulls are tender BECAUSE THEY ARE SLENDER, which is what
the solar-electric brief asks for.

**These hulls are meant to be DEMIHULLS.** For a multihull, stability is
dominated by separation:

    I_T = sum_j [ I_T,j + A_wp,j * d_j^2 ]

Applying a monohull GM floor to an isolated demihull measures the wrong vessel —
the same error class as `gate2m.py` printing KCS's EFD figure over a Wigley
hull, which this project has already caught once. **The multihull hydrostatics
are the largest single unlock and they do not exist.**

Unexplained and still open: `static list is UNDEFINED` fires on 11-13 of 30
designs. An undefined quantity reaching a constraint vector is defect class 1.

## What the experiment suite MEASURED (`navalai/experiments.py`, Gate 0X)

New this session: `navalai/experiments.py` (1995 lines) + `tests/test_experiments.py`
(44 tests, green). `python -m navalai.experiments` renders the report.

**"Sharper = better" is REFUTED.** R_t span over each lever's full gene range:

    Fn     Cp        lcb       bow/waterline shape
    0.20   19.77%    13.01%    12.39%
    0.30   45.31%    24.32%     9.21%
    0.45   26.35%    16.86%     1.36%

Volume distribution dominates bow shape by 1.6x at Fn 0.20 and **19.4x at
Fn 0.45**. At Fn >= 0.40 the SHARPEST bow is measurably worse than mid-range, by
2.1x and 2.8x the production-to-converged grid shift. At Fn 0.35 the penalty is
BELOW the grid shift and is flagged, not claimed.

**The Michell catamaran phase convention is CORRECT and is sec SQUARED.**
Depth kernel `exp(k0.sec^2(t).z)`, x-phase `exp(i.k0.sec(t).x)`, hence
`k_y = k0.sec^2(t).sin(t)`. Verified three ways: reconstructed factor vs module
5.6e-11; full independent complex superposition vs `michell_rw(separation=s)`
**0.0 relative difference exactly**; theta-average 1.99549 vs 2.0. The
plausible-but-wrong `k0.sec(t).sin(t)` differs by 3.99, so the check has the
resolution to catch it. `s -> infinity` recovers the independent sum to 0.37%.

**Separation is worth up to 60% and NOTHING USES IT.** No single optimum s/L —
it moves with Fn (0.390 at Fn 0.20; **0.300 at Fn 0.25, -25.2%**; 0.430 at
Fn 0.30), and above Fn 0.35 the entire 0.20-0.50 band is CONSTRUCTIVE, peaking
at **+59.7% at Fn 0.40, s/L 0.200**. s/L 0.300 reads 1.441 at Fn 0.40.
**`total_resistance` calls `michell_rw` with NO `separation`**, so every
catamaran this project has evaluated was scored as one isolated demihull.
**Wiring it is the highest-value single change in the tree.**

There is **no experimental anchor for the catamaran term at all** — Insel &
Molland are cited in `resistance.py`, never transcribed. Self-consistency is not
validation.

## The grammar reaches 2 of the 5 standard body plans

From `downloads/hull-examples/research-gate/Body-plans-of-five-equivalent-hull-forms.png`:

    a. Series 62                        EXPRESSIBLE
    b. Deep-V                           EXPRESSIBLE
    c. Double chine with wide transom   CANNOT DRAW (one chine only)
    d. Double chine based on Series 62  CANNOT DRAW
    e. Rounded bilge                    draws, but the unroller refuses it

**Multi-chine does not exist and it is the plywood answer to a round bilge.**
Grammar typologies: `sharp-chine`, `pram`. That is all.

What IS expressible (verified): `beta_mid` 0-25 deg, `beta_bow` 2-50,
`beta_len` 0.15-0.60 (so warped-vee vs monohedron is a real degree of freedom),
`flare` **-5** to +25 (negative = mild tumblehome), `forefoot` 0-1,
`roundness` 0-1.

**A CORRECTION TO THE RECORD:** the claim "a radiused bilge cannot be cut from
flat sheet" is TRUE OF OUR FILLET (a quadratic Bezier whose radius varies
station to station is doubly curved) and FALSE IN GENERAL — a constant-radius
strip is a cylinder, single curvature, and IS developable, which is how
radius-chine metal boats are built. Pinning `roundness = 0` for sheet-built
typologies is a STOPGAP correct for the unroller we have, NOT a principle. The
proper fix is a multi-chine section law.

## Alpha_e: the diagnosis I had wrong all session

alpha_e is NOT independent of L/B. The chord half-angle floor is

    alpha_e_floor = atan( (L/B)^-1 / (2 * L_E/L) )

At the monohull grammar's L/B floor of 2.2 that floor ALONE is **20.7-24.4
deg**, so 7-12 deg is unreachable there by any bow shape. The "1 of 74 in band,
median 31.6 deg" figure I quoted repeatedly was measuring **the L/B box, not the
bows**. Adding an alpha_e constraint now would put two constraint rows on one
degree of freedom. **Move the L/B ceiling first.** `formlib.alpha_e_chord_floor_deg`
is the one home; do not write a second copy.

The "7-12 deg band" is also not a band: the defensible spread is **3.7-21 deg
BY FAMILY** (hard-chine USCG series fixes it at 19.5). And **no source states
its station convention**, so no alpha_e constraint can ship until that is
pinned.

**The L/B cap of 8.5 is REFUTED with sources**: Southampton catamaran demihull
L/B 7-15.1, DTMB Series 64 L/B 8.45-18.26. The 12 x 0.8 m target at L/B 15 sits
INSIDE the Southampton envelope. (Southampton Report 71 refused every fetch, so
that band is SECONDARY via Petersson, and a test enforces the word survives.)
B/T points the other way: target 1.33 is BELOW the series' 1.50-2.50.

## Standards research — four files landed in `docs/research/standards/`

    CLASS-SOCIETIES.md   3089 lines
    ISO-FAMILY.md        2080 lines
    MATERIALS.md         1665 lines
    NATIONAL-CODES.md    2320 lines
    (plus docs/research/EU-REGULATORY.md, committed earlier as 3c68094)

**The trap, and it is the most important line in all of it:** the RCD guide
publishes the dated harmonised editions for free, so typing
`"ISO 12215-5:2019"` into `REVIEW["editions"]` would satisfy the year regex and
**flip Gate 6R GREEN with nobody having read a word of the standard**.

**Corrections that would have cost money, both now in `PURCHASE_QUEUE`:**
- `ISO 12217-1` — the queue said buy **2022**. The harmonised reference is
  EN ISO 12217-1:2017 which CONTAINS **ISO 12217-1:2015**. The EN year is the
  ADOPTION date. The 2022 edition is NOT harmonised. **This also means an
  earlier claim that R-DFH/R-OLH rest on a superseded text is WRONG —
  `review.py` holding 2015 is correct.**
- `ISO 8666` is **TWO** SIS products (EN ISO 8666:2020 1937 SEK + /A11:2021
  687 SEK = 2624 SEK), not one. It is the measurand behind six RCD length
  thresholds, one of them CUBIC.

**Our design pressure formula matches no standard.**
`max(10, 2.4*mLDC^0.33 + 20)` against ISO's `P_bm = P_bm_base * k_AR * k_L`
(beam, L_WL, design category, vertical acceleration n_CG). Not a simplification
— unrelated. Our THICKNESS formula IS ISO equation (39) term for term.

**Free sources that actually deliver numbers:** BV NR546 is the only free
plywood scantling method that exists; the Australian USL Code 5G+5M gives the
only free closed-form design-pressure -> plywood-thickness chain (scanned, no
text layer — extract page images); FPL Wood Handbook + APA for plywood
allowables; MIL-HDBK-17-2F for E-glass dry/wet knock-downs (~0.71 hot/wet);
Zenkert (free at KTH) for sandwich wrinkling.

**FRP, carbon and foam-core sandwich have NO free scantling source in ANY
jurisdiction** — three of our four materials. Offsetting: five jurisdictions
accept a first-principles calculation route, three in binding regulation.
**Reg. 1049/2001 after *Malamud* (C-588/21 P, 5 Mar 2024)**: harmonised
standards are part of EU law and must be released free on request — file it
before spending ~3853 SEK.

**Nobody applies a knock-down factor to carbon** — all three class societies
handle it as admissibility (ABS `T/E >= 0.014`) or minimum thickness, never as
reduced allowable stress.

**A second benchmark anchor candidate appeared:** the **NTUA Series**,
double-chine planing, LOA 4.00-7.00 m, L/B 1.00-4.23, with model-test
resistance/CG-rise/trim. In our size band and chined, unlike KCS. Caveat: it is
a planing series and Michell stops at Fn 0.45.

## ES-TRIN fixes made this session (`navalai/rules/estrin.py`)

- Coverage count was wrong THREE ways at once, all flattering: docstring said
  "eighteen", the tuple held SEVENTEEN, and it stopped at Chapter 20 —
  asserting ES-TRIN has twenty chapters. It has **33** (read from the 2025/1
  table of contents). `ES-COV` now reports 2 articles of 33.
- **New `ES-REC` finding: Art. 26.01 does NOT apply Chapter 4 to recreational
  craft**, and 26.01(2) — for craft under the RCD, i.e. our SKUs — is narrower
  still and also omits it. So the only two numeric bars this module computes
  probably do not govern the boats we build. Reported as UNDECIDABLE because
  craft type is not modelled; NOT silently applied or dropped.
- Art. 4.02(5) `r <= 1`, 4.02(6) aft-credit clamp and 4.02(7) `F >= 0` were all
  MISSING and all three omissions erred the UNSAFE way (each caps a reduction
  that is subtracted from the required freeboard). Now transcribed.
  **They are INERT on the hulls this grammar emits** (r lands at 0.90, aft
  sheer is structurally zero) and 4.02(7) is PROVABLY unreachable while
  alpha = 0 (F >= 50 mm always). Said out loud rather than left to be found.

## Other corrections and fixes made this session

- `hull_to_stl`'s girth default was a fixed `nz=16`, calibrated when every hull
  had a hard chine. Now `stl_girth_resolution(hull)`: 16 chine / **96** fillet.
  (An intermediate value of 48 was chosen on ONE hull with a claimed 3.15x
  margin; on the population that margin was **1.04x**. Same error as the
  original.)
- **The STL/STEP loft under-encloses irreducibly, and the mechanism is
  convexity.** `closed_mesh` integrates the area of the LERPED section
  (`integral A(lerp p)`); `hydrostatics.solve` trapezoids the EXACT areas
  (`integral lerp(A p)`). Area is convex in the control points, so the mesh can
  only ever enclose LESS — which is why every measured error is negative. The
  LADDER is right (within 0.044% of the densely resampled closed form).
- `Hull.n_stations` 41 -> 81 was PROPOSED and **correctly DECLINED**: +51% on
  `evaluate()` (22.14 -> 33.38 ms, and 161 breaks Gate 1's 50 ms bar) to buy an
  export-path fix the ladder does not need. Fixed in the export instead:
  `export._LOFT_STATIONS = 161`, station-aligned.
- `PRODUCTION_GRID` 161x28 -> **241x44** (0.907% -> 0.221% from converged);
  `CONVERGED_GRID` 321x65 -> 481x88.
- Reference hull LCB **-5.36 %LWL (infeasible) -> -1.68 (feasible)**; LCB band
  pass rate 47.3% -> 85%.
- **The PLM network failed SILENTLY**: `_engineer` let a `ValueError` escape
  into `asyncio.gather(return_exceptions=True)`, so the engineer task died on
  the first refused design — 55,500 candidates, 43 validated, **0 delivered**,
  and nothing in the audit saying why.
- **Gap A6b's bar was SOFTENED and has been RESTORED.** The assertion had been
  lowered from `+0.10` to `approx(0.051, abs=0.03)`, which silently closes A6b
  on a bar the code does not meet. It now fails openly at **+0.0513**. Worse,
  A6b's predicate matches the assertion TEXT, never a measurement, so at HEAD —
  where `X[:, 4]` selects zero rows and `GP.fit` dies — it scored A6b CLOSED on
  a test that CANNOT RUN.
- **G6's predicate tested an implementation and reported a regression on an
  improvement.** Re-aimed at the property.
- The gap JOURNAL (`data/evolution/gaps.jsonl`, gitignored) was stale from
  2026-08-11; `--apply` closed 11 rows. **An earlier claim in this session that
  there were "11 regressions" was WRONG — the columns were read backwards.**
- ARD saturation comments quoted a 15-parameter genome. Re-measured and it is
  CONFIGURATION-DEPENDENT: `sample_valid(250, seed=7)` full box gives **3 of
  16** (D, beta_len, sheer_rise); the `beta_mid >= 12` subset gives **6 of 16**.
  `x_mb`, the axis the old comment named, has STOPPED saturating.
- A calibration finding worth keeping: **a model with deliberately DOUBLED
  sigma is twice as well calibrated as production** (0.0557 vs 0.1135). So
  `calibration_error` cannot separate honest from over-hedged, any more than it
  can see the sign of a miscalibration — any test using it as a discriminator
  is weaker than it looks. Relatedly, the grid refinement moved accuracy and
  honesty in OPPOSITE directions: error 0.1523 -> 0.1471 while
  calibration_error 0.0427 -> 0.1135.

## Recorded, not fixed — measured limits

- **`Hull.min_bend_radius()` is ill-posed** and always has been: it halves with
  every doubling of the station count (new kernel 1.777/0.954/0.515/0.277/
  0.148/0.078 at 21->641; OLD kernel 4.184/2.239/... also fails from 81 up). A
  central difference straddling the x_mb tangent break measures the corner
  divided by the step. Bar untouched.
- **`GRID_CONVERGED_TO` is verified on ONE hull.** Population worst is
  **0.673%** against the 0.5% bar (median 0.331%).
- **`resistance.total_resistance` uses `hull.x[-1]`** — the DESIGN LWL — while
  beam and draft come from the floated state. Usually 0%, but **8.11%** on one
  of nine sampled hulls. Pre-existing.
- `navalai/experiments.py` owes `resistance.py` two named constants: the inline
  `0.25 * rw` and `0.10 * cf` are not importable, and `ResistanceResult` has no
  per-component sigmas.

## THE OBJECTIVE IS GAMEABLE ALONG THE LENGTH AXIS (measured, late session)

At FIXED length and FIXED Fn it is NOT gameable: the R_w, R_t and Wh/NM optima
are the same hull and wetted surface spans only ~3% across the feasible box.

At FIXED SPEED WITH LENGTH FREE — which is what the optimiser actually searches,
because `LWL` is gene 0 — the pathology reproduces. Stretching 12 m -> 20 m at
constant displacement:

    R_w              81.5 -> 13.4 N     -84%
    wetted surface                      +69%
    R_f                                 +54%
    R_t                                 +20%
    structural mass                    +111%

**AND THE OBVIOUS FIX IS WRONG.** `optimize.py` ALREADY carries
`build_area = wetted_surface(sheer) + deck_area` as objective 2, and
`energy.weight_budget` derives structural mass as EXACTLY that area times a
constant. So adding a separate "structural mass" objective — which both the
project owner's note and the lead's summary proposed — would be A NUMBER
DECLARED TWICE, this repository's signature defect. The genuinely uncovered
quantity is MANUFACTURING COMPLEXITY: `engineer.assess` computes `panel_count`
and `panel_area_m2`, `grammar` C43 measures panel twist, and none of the three
reaches `F`.

## THE FOUR PAPERS, and two attributions that were WRONG

`docs/research/HULL-GAN-PAPERS.md` (1624 lines) covers all four.

- **`jmse-11-02215.pdf` is ShipGen (Bagazinski & Ahmed, MIT) and it is a
  DIFFUSION model, not a GAN.** A CTGAN appears only as a benchmark it beats
  (0.7% feasibility against diffusion's 99.5%) — so do not build a GAN.
- **The 2.1x / 4.4x / 1.51x figures are SHIPGEN's, not ShipHullGAN's.** Exact,
  Table 4 §4.3.2: wave drag x0.086, total surface area **x2.138**, lower-half
  surface **x4.365**, Gaussian curvature **x1.514**, volume x47.9. The authors
  write "This is not desirable." ShipHullGAN reports no such figures.

**THE LESSON IS SHARPER THAN "ADD WETTED AREA TO THE OBJECTIVE".** Surface area
and curvature were AMONG THE SEVEN OBJECTIVES BEING MINIMISED and still went up.
Including a term is not sufficient. The exposed mechanism is a NORMALISATION
choice: they scaled the wave-drag coefficient by **LOA^2 instead of by wetted
area**, which let the optimiser inflate the boat while the headline coefficient
fell. **Check whether anything in our objective or our reported coefficients is
normalised by a length the optimiser can stretch** — the 12->20 m result above
has exactly that smell.

**CHINE: only ShipGen can draw one** (`Bc` beam at chine, `Beta` deadrise, `Rc`
chine fillet radius as a fraction of `Bc`, repeated at the transom, so deadrise
AND chine radius vary longitudinally — we have one global `roundness` scalar).
**NONE of the four can draw a DOUBLE chine.** The multi-chine work is ours to
invent; no paper hands it over.

**Highest-value adoptable idea, needing no network: area-averaged Gaussian
curvature as a GRADED MANUFACTURING COST.** It turns the `roundness = 0` pin
from a measure-zero binary refusal into a priced continuum without softening the
unroller's bar.

**Distrust two numbers:** ShipGen's R^2 = 0.973 is a TRAINING fit with no test
split, and the two weakest fits (MaxBox 0.784, curvature 0.765) are exactly the
two that later misbehaved. And Ship-D "feasible" means ONLY watertight and
non-self-intersecting — no stability, no performance — so 1-in-150 and 99.5% are
claims about geometric validity, not about good boats.

## OPENFOAM AND WEIGHT DISTRIBUTION ARE COUPLED, AND THE MASS MODEL IS UPSTREAM

`weights.MassAggregate` DOES carry `lcg_m`, `tcg_m`, `vcg_m`, so free sinkage
and trim is structurally reachable. But the `unaccounted` item is 50.2% of
displacement placed at the aggregate's OWN CENTRE, so a free-motion run would
converge to a plausible attitude FOR A DIFFERENTLY-BALLASTED BOAT. `CLAUDE.md`
records the same failure mode from the KCS side: KG existed only in a comment,
the VCB fallback measured 19% low, and KG is the lever that sets trim under tow.
**Fix the mass model before spending compute on free-motion CFD.**

## Environment note

`cryptography` was pip-installed into `~/.venvs/naval` so `pypdf` can open the
AES-encrypted JACIII paper. A fresh clone will not have it and the PDF will look
unreadable rather than encrypted. `pdftoppm`/poppler is NOT installed; the
working route for a scanned or typeset PDF is `pypdf` single-page split then
macOS `qlmanage -t -s 2400` to PNG, then read the image.
