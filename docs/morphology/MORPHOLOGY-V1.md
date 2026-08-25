# Hull Morphology System — V1 specification and failure analysis

**Measured 2026-08-23.** Code: `navalai/morphology.py`,
`navalai/morphology_families.py`. Baseline: `navalai/` at HEAD (16 genes); an
earlier unvalidated kernel change is parked at
`docs/morphology/PENDING-r_stem-barge-genes.patch` and is NOT in effect.

> **The premise.** A numerically valid object is not necessarily a valid boat
> hull. `evaluate` answers *is this legal, and does it float*. Nothing answered
> *does this look like a boat*. This document is the first half of the answer:
> what to measure, and what the measurements currently say.

---

## 0. THE HEADLINE MEASUREMENT

Descriptors computed on 58 published hulls and on L0-valid random genomes from
this grammar (`scripts/build_morphology_corpus.py --compare`):

| descriptor | REAL p5 | REAL median | REAL p95 | GENERATED p5 | GEN median | GEN p95 |
|---|---|---|---|---|---|---|
| beam carried at >= 90% | 0.317 | **0.390** | 0.877 | 0.073 | **0.171** | 0.341 |
| waterline convexity | 0.840 | **1.000** | 1.000 | 0.195 | **0.512** | 0.951 |
| beam at transom / max | 0.568 | **0.687** | 1.000 | 0.151 | **0.413** | 0.832 |
| plan waist | 0.000 | **0.000** | 0.000 | — | — | — |

> **89-92% of L0-VALID generated hulls are morphologically implausible.
> 0 of 58 published hulls are.**

Passing the L0 algebraic gate therefore says almost nothing about whether the
object is a boat. The grammar's valid space and the real-hull manifold barely
overlap, and until now nothing measured the difference.

Fenced by `tests/test_morphology.py`. That test is a REGRESSION DETECTOR, not a
target: when the generator is fixed it should fail, and the fix is to lower the
bar and record the new number.

---

## 1. Current morphology failure analysis

On 2026-08-23 the system generated, validated and certified a 16 m liveaboard
that passed displacement, Cp, Cb, LCB, GM, freeboard, scantlings, all eight
constraint rows, seven of seven rule findings and the arrangement gate — and
which was, in the STL, **a rectangular plank**. Four successive hulls were
delivered before anyone rendered one; the defect was found by a human opening
the file. **No gate in this repository reads shape.**

`Hull.alpha_e_deg()` — the half-angle of entrance, the single most direct
bluffness measure — is computed by the kernel and read by **no constraint row,
no rule and no badge**. A 36.1° entry passed everything silently. It cost
3.3 kW at 7 kn and 0.8 kn of top speed, both measured.

### 1.1 The gene box excludes the published hulls it claims to model

Against Table 1 of De Luca & Pensa 2017 (nine hard-chine planing series,
`downloads/hull-examples/research-gate/SSN.pdf` p. 206):

| descriptor | published span | NavalAI gene | series excluded |
|---|---|---|---|
| transom area ratio A_T/A_X | 0.10 – 1.00 | `r_transom` (0.05, **0.50**) | **6 of 9** |
| deadrise at 50% LWL | 13.0° – 37.4° | `beta_mid` (0.0, **25.0**) | **4 of 9** |
| deadrise at 75% LWL | 19.2° – 53.0° | `beta_bow` (2.0, **50.0**) | 1 of 9 |
| L/B | 1.95 – 6.25 | `L_OVER_B_BAND` (**2.2**, 8.5) | 2 of 9 below floor |

### 1.2 The deadrise LAW is the wrong shape, not merely the wrong bound

Published practice prescribes deadrise at **three stations** — transom, 50%
LWL, 75% LWL — rising monotonically forward. NavalAI warps **one quadratic**
from `beta_mid` to `beta_bow` over the forward `beta_len`, and `beta_len` is
capped at 0.60. **The warp can therefore never reach the transom**: transom
deadrise is always exactly `beta_mid`. A three-point prescription cannot in
general be met by this law at any setting.

### 1.3 Independent confirmation from Gate E5

E5 round-trips 53 published hulls through the kernel. Scalar particulars return
almost exactly — but those are *pinned by the fitter*, so they measure the
fitter, not the kernel. The shape residual is the honest number:

- **median RMS 8.92%** of half-beam, worst **16.60%**, points to **35.4%**
- **79% of the error is below the waterline** — the hydrodynamically live part
- best fit is `wigley` (3.30%), which *is* a closed-form parabola; worst is
  `series60` (16.60%), an actual ship
- **26 of 53 hulls do not fit inside the parameter box at all** (`lcb` beyond
  ±3%, `Cp` below 0.525)

Fitted **freely** to real stations, the kernel's own section family reaches
**0.88%–2.20%**. The section shape is therefore *not* the bottleneck; the
longitudinal laws that choose the section at each station are.

### 1.4 The named pathologies, and what produces them

Deck half-breadth is **solved from immersed sectional area**
(`A = K·yc·(c1·d − c2·m·yc) + d²·f` → solve for `yc`). One curve does two jobs,
so deck width and underwater shape cannot be chosen independently:

- ask for a **wide deck** → Cp must approach 0.92 with full ends → the plan
  becomes a rectangle and the bottom must stay flat. **24 of 24** forefoot /
  rocker combinations were refused; the only buildable shape was the slab.
- ask for a **fine bow** → Cp drops → beam coverage collapses to 22–39% → the
  spearhead.

There is no setting that yields both.

---

## 2. Inventory of existing REAL geometry

Only geometry counts. A paper about a hull is not hull training data.

| source | n | form | status |
|---|---|---|---|
| Delft Systematic Yacht Hull Series | **51** | round-bilge sailing yacht | offsets, `tests/e5_real_hulls/` |
| Series 60 | 1 | full displacement cargo | offsets |
| Wigley parabolic | 1 | closed-form test hull | offsets |
| Fridsma prismatic planing | 5 | hard chine | `tests/e5_hard_chine/`, PUBLISHED_PARAMETRIC |
| KCS container ship | 1 | full displacement | IGES + STL |
| **Naples Systematic Series** | 0 geometry | warped hard chine | **descriptor table only** (§5) |

**Total: 59 hulls, effectively one morphological family plus four singletons.**
Corpus span: Cp 0.500–0.666, Cb 0.327–0.593, L/B 2.73–10.00.

This is the dataset problem, quantified. A network trained here learns Delft
yachts, badly. Ship-D's lesson points the same way: 30,000 parametric hulls
still contain many shapes no architect would recognise. **More random geometry
is not the answer; a validated realistic-hull manifold is.**

## 3. Inventory of the form families

`formlib.FAMILIES` = **31** registered. **3 YES, 6 PARTIAL, 22 NO.**
All three buildable families are MONOHULL / DISPLACEMENT:
`moderate_displacement`, `full_displacement`, `hard_chine_displacement`.

Against the five target families in the brief:

| target | registered | expressible today |
|---|---|---|
| conventional displacement | 3 | **YES** (2 of 3) |
| hard-chine planing | 4 | PARTIAL — the only YES is *displacement*, not planing |
| pontoon | 1 | **NO** |
| catamaran | 6 | **NO** (all) |
| wave-piercing / fine entry | 3 | **NO** (all) |

**One of five.**

## 4. Morphology descriptor specification — IMPLEMENTED

`navalai/morphology.py`. The common currency is `HullOffsets` — a station ×
waterline half-breadth grid — **not** a `Hull`, because a descriptor only a
generated hull can have is a descriptor nothing can calibrate. `from_hull()`
adapts the generator; `load_offsets_csv()` reads a published hull.

`describe()` returns 33 descriptors: longitudinal (SAC peak/centroid, entrance
and run fractions, parallel-body fraction, transom and stem area ratios, bow
and stern taper, SAC smoothness), plan (beam peak, beam carried, transom and
stem beam ratios, waterline convexity, plan waist), transverse (midship and
mean section fullness, deadrise at mid and bow, deadrise range, bottom
flatness), profile (depth variation, sheer rise, rocker, forefoot) and global
(L/B, B/T, D/T, Cp, Cb, Cm). Every one is dimensionless or normalised, because
the corpus spans a 5 m yacht to a 230 m ship.

**Two descriptor bugs were found by calibrating against the teacher**, and both
are the reason calibration is mandatory rather than optional:

- `plan_waist` first measured *taper* instead of *non-monotonicity* and
  reported the reference hull as 61% waisted. A waist is a rise-then-fall
  before maximum beam; it now measures that.
- `beam_at_station` read a station with no published offsets as **beam = 0**.
  dsyhs_49 has 3 such gaps in 41 stations, which put a false pinch in the plan
  and made the detector fire on a perfectly fair Delft yacht. Gaps are now
  interpolated and never counted as narrow.

After both fixes, `plan_waist` is **0.000 on every real hull tested**.

## 5. Published family targets — IMPLEMENTED

`navalai/morphology_families.py` transcribes nine hard-chine planing series
with provenance from SSN.pdf Table 1: L/B, A_T/A_X, deadrise at transom / 50% /
75%, length-displacement ratio, chine breadth ratio. This is what makes §1.1
and §1.2 measurements rather than assertions.

## 6. Canonical rendering specification — SPECIFIED, NOT BUILT

Fixed views, identical every time, never an arbitrary camera: **profile, plan,
body plan, design-waterline, transverse sections, longitudinal sections,
isometric.** Written per hull beside its descriptors, and emitted as a
before/after artifact on every geometry change so that a plank cannot pass
review unseen. This is the direct fix for "green numbers, terrible hull".

## 7. Positive corpus — IMPLEMENTED; negative corpus — SPECIFIED

- **Positive**: the 59 real hulls of §2, each with descriptors and canonical
  views.
- **Negative**: pathological hulls this system has actually produced, kept as
  fixtures rather than discarded — the plank, the spearhead, the box, the
  wasp-waist, the 36° bluff bow. These already exist in this session's history
  and are reproducible from recorded genomes.

A critic calibrated only on good examples cannot say what bad looks like.

## 8. Morphology critic — IMPLEMENTED

`navalai.morphology.critique`. Deterministic, no ML. Detects **SPEARHEAD** (excessive forward taper,
low beam carried, extreme LCB, low aft volume), **BOX** (near-constant SAC,
abrupt end termination, low longitudinal curvature), **PLANK** (low vertical
sectional variation, near-zero deadrise range, low depth variation),
**PYRAMID** (monotonic taper in several dimensions at once), plus **WAIST**,
**WAVY-PLAN** and **PROPORTION**. Bands measured on the positive corpus; every
rejection names the descriptor AND both numbers. Runs **before** CFD.

**Verified on the incident**: the 16 m houseboat as shipped returns
`ENGINEERING: PASS / MORPHOLOGY: REJECTED (SPEARHEAD, WAVY-PLAN)` —
`beam_carried` 0.171 against a published p5 of 0.317. That is the gate that was
missing.

Three descriptor bugs were caught by the zero-false-positive rule, and each is
recorded in `tests/test_morphology.py` because each is the same defect class:
an unmeasured quantity being scored instead of refused. `plan_waist` measured
taper rather than non-monotonicity; `beam_at_station` read an absent published
station as beam = 0; and `_safe` returned its DEFAULT for a non-finite
denominator, turning Wigley's missing sheer column into a PLANK verdict on one
of the critic's own teachers.

## 9. Family-specific parameterization — SPECIFIED, NOT BUILT

`formlib` becomes the registry; each family may carry its own parameterization
over a shared substrate. **A pontoon and a SWATH must not be forced through the
grammar that draws a Delft yacht.** The first concrete instance is the
three-point deadrise warp of §1.2, which the current single-quadratic law
cannot represent.

## 10. Self-learning loop and the acceptance test — SPECIFIED, NOT BUILT

`generate → render canonical views → describe → engineering validate →
morphology validate → on reject: classify, record genome, descriptors and
reason → mutate toward the manifold → regenerate`. Every iteration is training
data. Mutation is directed, never blind.

**Acceptance test (first five families):** conventional displacement,
hard-chine planing, pontoon, catamaran, wave-piercing. For each: obtain real
geometry, generate canonical views, extract descriptors, fit the family
parameterization, generate a new hull, and compare **descriptors and views** —
not "does it have the same Cp". Today **one of the five** is expressible at all,
and **geometry exists for two** (displacement, hard chine). Acquiring pontoon,
catamaran and wave-piercing geometry is a prerequisite, not a detail.

---

## The absolute rule

A hull is not good because hydrostatics, stability, CFD, mesh and constraints
pass. It must satisfy **engineering validity AND geometric validity AND
morphological plausibility**, and the system must distinguish **VALID** from
**PLAUSIBLE** in what it reports.

---

## 2026-08-24 — the SPEARHEAD had a cause, and the critic did not catch it

The owner rejected the delivered `houseboat16.stl` on sight: *"it looks like a
spearhead rather than a boat and the space at the stern cannot be used, i have
asked for a 4m width boat"*. That reading was correct and the geometry was
wrong. Three defects, all measured, all now fenced.

### 1. The grammar had no bow-fullness gene at all

`geometry.sac_ordinate` built its forward branch as `a = 1 - _shape(t, pf)`,
which is **exactly 0.0 at x = LWL**. The aft branch has carried `r_transom` —
`a = R + (1-R)·…`, a floor on sectional area — since the kernel was written;
the forward branch simply never got its mirror. So *every hull this grammar
could express* narrowed to a mathematical point at the stem. A barge, a
workboat, a houseboat and an axe bow all carry finite area at the stem; only a
racing shell does not.

MEASURED on the 16 × 4 m houseboat envelope, sheer beam at the stem:

    r_stem   beam @ stem   beam @ 0.95L   beam @ 0.85L
     0.00        0.020 m        0.954 m        2.432 m
     0.15        0.709 m        1.516 m        2.741 m
     0.30        1.454 m        2.110 m        3.055 m
     0.45        2.277 m        2.741 m        3.376 m

**20 mm** is the point bow, and it is what the render showed. `r_stem` is now
the mirror of `r_transom`, appended under `grammar.POST_HOC_DEFAULTS` with
default 0.0. That default is a *proven* no-op, not an approximate one:
`S + (1-S)·v == v` for every finite `v` when `S == 0` in IEEE-754, verified
bit-for-bit over 48 seeded draws by
`test_r_stem_zero_is_bit_identical_to_the_pointed_bow`. Every pinned population
and every E5 residual is unchanged.

### 2. `sac_stem` and `sac_transom` were measuring the sampling grid

This is the `beam_transom` defect (300 of 300 ShipD hulls reading 0.000) in the
curve next door, and it went unnoticed because the 2.5% inset was applied to the
plan and **not** to the area curve.

MEASURED across all 53 published hulls in `tests/e5_real_hulls/`:

    descriptor     before (at the extreme station)   after (2.5% inset)
    sac_stem       53 of 53 read 0.0000              min 0.0058  med 0.0130  max 0.0975
                   min == p5 == med == max           zeros: 0
    sac_transom    1 of 53 read 0.0000               min 0.0000  med 0.0259  max 0.0975

Sectional area is zero at a closed hull's own extremity *by definition*, so at
`x[-1]` this descriptor could only ever return zero — for a barge exactly as for
a spike. A band 0.000 wide cannot discriminate anything, which is why a hull
whose bow was a mathematical point critiqued **`ok=True, score=1.000`**.

Neither key is in `MANIFOLD_KEYS`, so the fix does **not** move the vendored
ShipD bands. Regression: **0 of 53** published hulls change verdict.

### 3. STILL OPEN — the inset is an INDEX, so it is not grid-invariant

`_inset = max(1, round(0.025·(len(b)-1)))`. MEASURED: the published corpus
carries **both 25- and 41-station** files, and `max(1, …)` floors both at index
1 — which is **4.17%** of length on a 25-station hull and **2.5%** on a
41-station one. The descriptor therefore depends on the grid it was sampled on,
which is precisely what a scale-free descriptor must not do.

This is NOT fixed here, deliberately. `beam_transom` **is** in `MANIFOLD_KEYS`,
so correcting it to a true fixed fraction (by interpolation rather than by
index) moves the learned bands and requires regenerating the 30,000-hull ShipD
manifold. That is a measurement, not an edit, and it is owed — recorded here so
it is not rediscovered a third time.

### 4. The BOW is fixed; the STERN is capped by a bound, and that is measured

With `r_stem` landed, the 16 × 4 m brief was re-searched inside the CURRENT
gene box (9000 candidates, `grammar.check` + `morphology.critique`):

    beam            before r_stem   after r_stem   the brief
    at the stem        0.020 m         1.906 m      —
    maximum            —               3.980 m      4.0 m
    at the transom     —               2.161 m      ~3.0 m for a usable terrace

The spearhead is GONE and the 4.0 m envelope is respected. The stern is not,
and the reason is a bound rather than a search failure. MEASURED over 1592
hulls that pass `check()`:

    transom beam >= 3.0 m :    0 of 1592   (median 1.84 m, best 2.38 m)
    max beam     <= 4.0 m : 1152 of 1592

`r_transom` is capped at 0.50 and it is a SECTIONAL AREA ratio, so on a 4 m
boat it caps transom beam near 2.4 m — 60% of maximum beam. A houseboat
terrace, a landing craft ramp and a canal-boat counter all need more, and none
of them are reachable from this box. `Cp` is capped at 0.710 by the
resistance-optimal table for the same reason, and the box ends of a barge reach
Cp 0.83 at the lowest.

**This is NOT fixed here, and the distinction from `r_stem` is the whole point.**
`r_stem` was APPENDED, so its default is a proven no-op and no seeded population
moved. `r_transom` and `Cp` are CORE genes: `sample()` draws a uniform for each,
so widening either ceiling maps the same random number to a different value and
silently re-draws every pinned population, every E5 residual and every fixture —
which is exactly the failure `forefoot`'s floor produced and which the comment
beside `forefoot` in `grammar.py` records. Landing a true barge form is
therefore a SEQUENCED change with a re-measured corpus behind it, not an edit to
two numbers.

The delivered `data/exports/houseboat16/` is the best form the current box
admits: ladder `ok=True` at tier L1, 0 of 8 constraints violated, morphology
`ok=True` score 1.00, manifold 0.958, all seven design rules pass, 14.0 t at
0.392 m draft, GM 1.55 m, 1116 N and 1135 Wh/NM at 7 kn. It is a fair launch
hull. It is not yet a barge, and the render (`lines.png`) shows why: a lens
plan, pointed at both ends, with very little parallel middle body.
