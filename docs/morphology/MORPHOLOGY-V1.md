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
