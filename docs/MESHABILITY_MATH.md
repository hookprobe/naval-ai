# MESHABILITY MATH — the admissible design space, derived and enforced

**Directive (2026-08-18):** geometry → mathematical feasibility → meshability →
CFD, instead of discovering bad geometry after expensive meshing/solving. Every
genome admitted into the CFD pipeline must carry a mathematically justified
high probability of a valid, manifold, meshable hull and a numerically stable
case — *without* loosening any solver tolerance, hiding any failure, or making
the pipeline more tolerant.

Status labels used throughout: **MEASURED** (a labelled outcome backs the
number, named), **DERIVED** (computed from the pipeline's own constants;
moves when they move), **PROVISIONAL** (a stated judgement awaiting a named
measurement). Every claim below carries one.

---

## A. Root cause

The pipeline discovered bad geometry late for three reasons, each measured:

1. **The meshability screen was predicting with a dead formula.**
   `admissibility.sheer_collapse_cells` recomputed the sheer as
   `ys = yc + (zs − zc)·tan(flare)` — the **pre-P1 kernel's** law with the
   *unenveloped* flare. The rebuilt kernel (plates P1/P2) envelopes the flare
   into the stem and **refuses** a negative sheer at L0
   (`geometry._stations`: *"tumblehome closes the sheer past the
   centreline"*). MEASURED on the 16-gene seed-0 batch: the stale formula
   refused 5 of 25 hulls whose *delivered* interior sheer half-breadth is
   0.06–0.37 m — healthy decks, refused by a second copy of a formula the
   kernel no longer contains (LESSONS defect class 2, with the copy voting).

2. **The writer's refusal set conflated two mechanisms.** DANGEROUS is
   documented to mean *"expect a checkMesh refusal at the DERIVED layer
   count"* — and MEASURED (backoff campaign 2026-08-11), every hull the
   draft bar refused meshed cleanly at a lower layer count. Since the
   layer-backoff ladder became canonical in `run-case.sh` (metal-proven
   2026-08-18: case a, derived n=6 FATAL with 16 wrongly-oriented faces →
   ladder → n=5 CLEAN, unattended), a rung-0-refusal prediction has a
   deterministic recovery — yet the C-18 guard refused *all* DANGEROUS at
   the writer. Together with (1), the screen refused 10 of the current 25
   seed-0 hulls, of which **5 were phantoms and ~4 more were
   ladder-recoverable**.

3. **The solvability criterion was the wrong mathematics.** MEASURED (the
   Mac's paired dataset, 2026-08-18, `docs/audit/STATUS.md`): checkMesh's
   `zero-volume / wrong-oriented / skewness` are **indistinguishable** across
   solved and diverged runs, while the local flow time scale
   τ = V_cell/(A_max·U) separates solved (7.8e-6..2.1e-5 s) from diverged
   (4.356e-18 s) by **twelve orders of magnitude**. "0 zero-volume cells" is
   the wrong bar: a 1e-20 m³ cell is not zero and not solvable. (The
   enforcement — a live abort at 1e-12 s — landed in `run-case.sh`
   2026-08-18, orchestrator's commit `2ab0581`; this report supplies the
   pre-mesh end of the same chain.)

So the architecture change is not "add a validator": it is (i) retire the
stale copy, (ii) split every meshability refusal by its **mechanism** —
*cell-scale* (no layer count can fix it → refuse at the writer) vs
*layer-scale* (the ladder's own domain → predict, warn, let the runner
recover) — and (iii) carry the τ receipt from design intent to live abort.

---

## B. Mathematical model — the admissible-space inequalities

Coordinates and symbols follow `navalai/grammar.py` / `navalai/geometry.py`:
x=0 transom → x=LWL stem; z=0 at the DWL; y = starboard half-breadth;
d(x)=−z_keel(x); β(x) deadrise; φ flare; m=tanβ, f=tanφ·env(x); K=1−mf;
(c₁,c₂)=(2−ρ²/3, 1−ρ²/3) from roundness ρ; a(x)=A(x)/A_mid the SAC ordinate.

### B.1 The genome (16 genes): role and failure modes

| gene | role | L0 constraint(s) that govern it | invalid-geometry mode it can drive |
|---|---|---|---|
| LWL, BWL, T, D | absolute box | sourced/derived bounds; L/B, B/T role-banded; freeboard abs/rel | box floors derived so no content-free bound binds first |
| Cp, lcb | **design targets** (inputs since P1) | `sac.target`: (Cp,lcb) must be reachable with SAC exponents in [−6, 8] | unreachable target — refused, never approximated |
| x_mb, r_transom | SAC shape | participate in `sac.target`, `section.solve` | aft-starved/fwd-starved area curves |
| beta_mid, beta_bow, beta_len | bottom panel | `deadrise.order`; `panel.twist` ≤ 14 °/m (max, not mean) | unbuildable twist; steep-β sections that cannot hold A |
| roundness ρ | bilge fillet | (none at L0 — case-dependent, see C.4) | sub-cell fillet radius (r_min ∝ ρ) |
| rocker, forefoot | keel profile | subsumed by bounds (gap E4); enter `section.solve` via d(x) | shallow-end sections asked for more area than d²/tanβ |
| flare | topside | `section.solve` (flare consumes half-beam; tumblehome closes sheer) | negative-sheer collapse — now a **refusal**, not a clamp |
| sheer_rise | deck | enters tumblehome check via z_s | — |

### B.2 Section-law feasibility (L0, case-independent) — all pre-existing, verified

For every x on the 1921-station probe (grid contains the 41/241/481-station
consumer grids exactly):

1. **SAC reachability** — S(p_f,p_a)=Cp·L and M/S = L(½+lcb/100) must have a
   solution with p_f,p_a ∈ [−6, 8]. Monotone-bracketed bisection; failure ⇒
   `sac.target`. *(MEASURED mechanism: plate P1; refusal, never clamp.)*
2. **Section area capacity** — the chine solve's discriminant
   (K·c₁·d)² − 4K·c₂·m·(A − d²f) ≥ 0, i.e. roughly **A ≤ d²/tanβ** at ρ=0
   (chine at the waterline). Failure ⇒ `section.solve`.
3. **Flare capacity** — at the max-area station yc_mid = (½B − d·f)/K > 0,
   i.e. **½·BWL > T·tanφ**; and per-station A ≥ d²f (the flare alone may not
   enclose more area than the target). Failure ⇒ `section.solve`.
4. **Sheer positivity** — delivered **ys ≥ 0 everywhere** (tumblehome may
   not close the deck past the centreline). Failure ⇒ `section.solve`.
   *This is the inequality that made the screen's V2 a stale copy.*
5. **Chine submergence** — **max_x z_chine ≤ 0**: the DWL point must lie on
   the topside run or the closed-form area law does not describe the hull.
6. **Developability** — max_x |dβ_chine/dx| ≤ 14 °/m (local max; the mean
   under-read 12.2% of the box, gap E6).
7. Bounds, role-banded L/B & B/T, freeboard (abs + 4.5% LWL), deadrise
   ordering — as shipped.

**Verdict on new L0 inequalities: none added.** Every CFD-pathological class
found in this investigation is *case-dependent* (it compares a feature to the
cell size the (speed, scale) case derives); hard-coding a case into L0 would
recreate the two-copies defect at the architectural level. The
geometric-infeasibility class is already closed at L0 by 1–7 — MEASURED: on
10,000 uniform-in-box genomes every refusal carries a named clause from this
list (§G attribution) and no L0-passer failed to build a `Hull`.

### B.3 C0/C1 structure the mesher sees (verified, diagnostic)

The kernel is piecewise about x_mb, 0.3L, 0.7L and the warp start. Keel and
deadrise joints are **C1** (quadratic blends with zero end-slope); the SAC is
C0 with a slope break at x_mb ⇒ the chine/sheer plan-forms carry a tangent
break there (MEASURED 12.3° on the reference hull, closed form matches to 6
sig figs). Its predictive power against mesh failure is **MEASURED AUC 0.500**
(chance) — kept DIAGNOSTIC (`xmb_tangent_break_deg`), forbidden to vote. The
same for the stem cusp (`bow_bluntness_cells`, AUC 0.500) and the STL's
41-station crease pattern (`max_facet_turn_deg`, AUC 0.673).

---

## C. Meshability model — dimensionless ratios, with calibration status

The case derives its cell: `cell = (4.5·LWL/round(57·scale))/2⁵` (level-5
hull cell; DERIVED, imported from `cfd/case.py`, never restated). Every ratio
below is *feature/cell*, so it moves with the pipeline's own derivation
(fenced by `test_the_same_hull_is_admissible_when_the_cell_shrinks_with_scale`).

**The rescue axis** (new, `Metric.ladder_rescuable`): a refusal is either
*layer-scale* (mechanism moves with n_layers ⇒ run-case.sh's canonical ladder
is its measured recovery, ~1.9 rungs mean) or *cell-scale* (no rung exists ⇒
`Report.refused_no_rescue` ⇒ the case writer refuses). UNMEASURED is always
fatal (defect class 1).

| metric | inequality (DANGEROUS when violated) | rescuable | status |
|---|---|---|---|
| `draft_over_hull_cell` | draft/cell ≥ fs_band/cell (=14.19 @ scale 1) | **yes** | DERIVED bar; MEASURED 4/4 rung-0 failures below it, 0/6 meshed below it (15-gene labels, void for transfer); MEASURED rescue: all of them meshed on the ladder |
| `min_interior_sheer_halfwidth_cells` (**successor of retired** `sheer_collapse_cells`) | min ys(interior)/cell ≥ 1 | **no** | DERIVED (the bar *is* the cell); refuses, by construction, all three hulls the retired bar was validated on (they delivered literal 0-width ridges); MEASURED on current batch: 1/25 fires (hull 18, 0.35c), 0 phantoms |
| `min_bottom_panel_width_cells` | min yc(interior)/cell ≥ 1 | no | DERIVED; unexercised by labels; 11/200 manifold |
| `min_topside_panel_height_cells` | min (z_s−z_c)/cell ≥ 1 | no | DERIVED; never fired |
| `transom_half_beam_cells` | yc(0)/cell ≥ 1 | no | DERIVED; 7/200 manifold |
| `transom_immersion_cells` | −z_keel(0)/cell ≥ 1 | no | DERIVED; never fired |
| `stack_over_min_radius` | stack·κ_max < 1 away from the four C1 breaks (prism normals must not cross) | **yes** (stack ∝ layer count: floor-3 stack = 3.6·t1 vs 12.9·t1 at n=7) | DERIVED (pure geometry) |
| `bilge_min_radius_cells` (**new**, the 16th gene's own mode) | reported only — see below | (no rung) | **DIAGNOSTIC** — zero labels exist |
| `intended_min_cell_flow_time_scale_s` (**new**) | reported only — see D/F | — | DIAGNOSTIC receipt with MEASURED anchors |

### C.4 The bilge-fillet radius (new derivation)

The fillet is the quadratic Bezier (P0, C, P2) with P0 = C+ρ(K−C),
P2 = C+ρ(W−C). With a = ρ(C−K), b = ρ(W−C), the cross terms cancel and

  κ(s) = |a×b| / (2·|(1−s)a + sb|³),  so  **r_min = 2·d_min³/|a×b|**,

d_min = closest approach of segment a→b to the origin. r_min is **linear in
ρ**: the gene walks continuously from a crease (r=0) to a resolvable round.
Pre-registered trouble window: **stl_row < r_min < cell** — the STL renders
the fillet as smooth (no feature edge for snappy to snap) while the cell
cannot resolve the curvature. Below stl_row the tessellation degrades it to
the hard chine the pipeline already meshes; above the cell it is ordinary
resolvable curvature. MEASURED distribution (16-gene seed-0 batch): the
window holds 2–3 of 25 hulls; the naive `0 < r < cell` band holds ~half the
batch — which is exactly why this metric is **DIAGNOSTIC, forbidden to
vote**: *no round-bilge hull has ever been meshed* (case a is hard-chine;
every labelled campaign is 15-gene), and an unvalidated bar refusing half
the manifold is the V6-first-draft defect. Promotion path: §H.

### C.5 What the corpus can and cannot calibrate

The seven `data/gate2u-*.json` corpora carry mesh metrics per row but the
genome era changed 15→16, so **hull-index→geometry labels are void**
(`CALIBRATION_GENOME_N_PARAMS`); re-fitting geometric bars against them would
be calibrating against nothing. What remains valid and is used here:
row-internal facts (partial-stack ⇒ folded cells; the ladder's rescue
statistics; the paired solve outcomes behind τ). The first 16-gene campaign
(STATUS.md decision (c), `screen_verdict` on every row + the
screen-vs-rung-0 confusion table) is the re-calibration instrument — already
wired by the orchestrator in `scripts/mesh_robustness.py`.

---

## D. The y+ / first-layer model — verified

`first_layer_thickness(U, L, y+_target)`:
Cf = 0.075/(log₁₀Re − 2)² (ITTC-1957, one home: `resistance.ittc57_cf`,
called with the case fluid's ν) → u_τ = U·√(Cf/2) → **t₁ = 2·y+·ν/u_τ**
(cell *centre* at y+, so the cell is twice it). Verified consistent with the
case templates: `nutkWallFunction`/`kqRWallFunction`/`omegaWallFunction` on
`"hull.*"`, valid in the log layer; target y+=100 (MEASURED: y+ 30 put
min-y+ in the buffer layer; 100 lands low-friction regions ≈47). Layer count
n bridges t₁ to the local cell at expansion 1.2, capped at the MEASURED
`_MAX_LAYERS=7`, floored at 3, with build-time guards both ways
(stack/cell ≤ 1.2 fatal; last/cell ≥ 0.12 warned). ITTC-57 is a correlation
line (carries a form allowance over pure flat-plate); at y+ targeting this
is a ≤ ~10% effect on t₁ — inside the ladder's own ±1-layer granularity.
Nothing changed here; the derivation is right.

**The τ chain (design → mesh → solve), the report's numeric spine:**

- intended: τ_int = min(0.25·t₁, fs_dz)/U ≈ **2.3e-4 s** at the design point
  (DERIVED; now a screen receipt, `intended_min_cell_flow_time_scale_s`);
- healthy solved meshes: min τ (runtime, local U) = **7.8e-6..2.1e-5 s**
  (MEASURED, 7 runs);
- measured divergence: **4.356e-18 s** (MEASURED, h18 — checkMesh-blind);
- live abort bar: **1e-12 s** (`run-case.sh`, orchestrator, 2026-08-18;
  ~5.9 orders below the solved floor, ~5.6 above the divergence).

The ~1.5-order gap between intended (1e-4) and achieved-healthy (1e-5) is
squeezed layers + local-U spikes; the further 7 orders to the bar is the
margin *accidental* cells must consume before a solve can die — which is
precisely what the cell-scale feature bars exist to prevent.

---

## E. Mutation / parameterization model

**What is already invariant (keep):** Cp and LCB are *inputs* solved by
`sac_exponents` (plate P1) — the single biggest reject-after-generate class
was removed by re-parameterization, the exact pattern the directive asks
for. The DWL is a first-class curve; the section law is closed-form.

**What stays reject-based, and why:** (i) L0's `section.solve` couples 9
genes through a quadratic discriminant along x — an explicit invariant
parameterization would invert the section law globally (a different genome,
not a constraint), while the 1921-station probe refuses in ~5 ms with a
named station; (ii) all cell-relative bars are properties of a *(hull,
speed, scale) case*, not of a genome — baking them into sampling would
hard-code a case into the grammar and narrow Gate 2U-A's protected raw
denominator. The admissible space is therefore **L0(x) ∧
refused_no_rescue(x; U, scale) = ∅**, enforced at the last case-independent
and first case-dependent gates respectively.

**Sampler consequence (spec, not wired):** the CFD candidate lane
(`certify.cfd_candidate` → `make_case`) should draw from
`L0 ∧ screen-admissible` — a row filter at selection time, never inside
`grammar.sample`/`sample_valid` (2U-A protection). MEASURED cost of the
filter: 5.5% of L0-passers (writer-refusal rate on the manifold), i.e. a
~1.06× draw overhead.

---

## F. Failure taxonomy → which gate catches each

| failure class (classify() bucket) | mechanism | caught by, now |
|---|---|---|
| `generation` / GeometryError | section law cannot deliver | **L0** (sac.target, section.solve, chine.submerged, panel.twist) |
| sub-cell feature → snap/castellation slivers | feature < cell | **screen, refused_no_rescue → writer refuses** (V2', V3–V5) |
| `checkmesh-wrong-oriented` / `-zero-volume` / `-skewness` at rung 0 | partial layer stacks (MEASURED on the baseline corpus: dirty rows carry the larger request−achieved gap, median 4.66 vs 3.63 layers, and lower coverage, 51.9% vs 61.5%), keel-in-band | **screen predicts (DANGEROUS, rescuable) → run-case.sh ladder recovers**. MEASURED at scale: `data/gate2u-n74-mesh.json`, 74 hulls with the ladder = **74/74 meshed (100%)**, attempts {1: 65, 2: 5, 3: 3, 4: 1}, mean 1.19 — the mesh path is empirically deterministic inside the ladder on that manifold (15-gene era; the mechanism, not the labels, is what transfers) |
| ladder-exhausted (old hull 4 class) | unknown — screen called it SAFE | **run-case.sh checkMesh bars** (0 zeroVol / ≤5 wrongOri / ≤20 skew) — no pre-mesh predictor exists; honest residual |
| `solver-diverged` / τ-collapse (h2/h18 class) | accidental cell with τ ≪ healthy; checkMesh-blind | **run-case.sh early abort** at τ < 1e-12 s within ~10 iterations (orchestrator, landed) + reclassification |
| mislabelled timeouts | divergence read as timeout | reclassification (orchestrator, landed) |

---

## G. Expected CPU savings (design point: 25-hull campaign economics)

MEASURED unit costs: screen ~10 ms (chine) / ~210–275 ms (round, this box);
mesh ~74–80 s; LTS solve ~27 min; h18-class divergence burned 2700 s.

- L0 at 4–6 ms/genome refuses 93.25% of the uniform box before any geometry
  work (10k run, seed 42).
- The writer refusal (5.5% of L0-passers) saves a guaranteed-wasted
  mesh+ladder walk: ≈ 80–300 s each for ~0.2 s of screen.
- The rescuable-DANGEROUS path costs extra *mesh* rungs (measured mean 1.19
  attempts over the 74-hull ladder corpus, 100% meshed) but never a wasted
  solve — unchanged from the canonical runner.
- The τ early abort converts a 2700 s divergence into a ≤ ~60 s verdict
  (~45× on that class); the pre-solve receipt makes the margin visible for
  free.
- Net on a 25-hull campaign shaped like seed-0: ~2 writer refusals × ~5 min
  saved + ~1 divergence × 45 min saved ≈ **~1 h saved per 25 hulls**, plus
  the phantom-refusal recovery: 5 hulls/25 that C-18 would have silently
  dropped from the science now run.

---

## H. Validation plan — the one-random-admissible-mesh Mac test

The math must be right, not lucky; one admissible draw, one deterministic
path, receipts at every stage:

```bash
# on fortress001 (no OpenFOAM):
python -c "
import numpy as np
from navalai.evaluate import sample_valid; from navalai.mission import MissionSpec
from navalai.admissibility import screen; from navalai.geometry import Hull
from navalai.cfd.case import write_resistance_case
rng = np.random.default_rng()          # ANY seed — admissibility, not luck
X, _ = sample_valid(8, MissionSpec(), seed=int(rng.integers(1<<30)))
for i, x in enumerate(X):
    r = screen(Hull(x), speed=2.57, scale=1.0)
    print(i, r.verdict.name, r.refused_by, r.refused_no_rescue)
# pick the FIRST hull with refused_no_rescue == () — rescuable-DANGEROUS is
# ADMISSIBLE (that is the point); write the case:
write_resistance_case(Hull(x_pick), 2.57, 'runs/admissible-one', end_time=2.0,
                      symmetric=True)   # LTS defaults; np as measured optimum
"
# on the Mac (OpenFOAM):
openfoam navalai/cfd/run-case.sh runs/admissible-one 10
```

**Receipts that prove the math** (all in `case.info` + logs, no judgement):
1. `admissibility_verdict=…`, `admissibility_no_rescue=none` — the screen
   admitted it and says why.
2. Mesh passes the unchanged checkMesh bars, at rung 0 **or** via
   `layer_backoff_attempt_*` receipts — either way unattended (the
   deterministic path includes the ladder by design).
3. First ~10 LTS iterations print `Flow time scale min/max` ≥ 1e-12 s (no
   early abort) — at iteration 1 the field is ≈ uniform inlet, so this IS
   the pre-solve geometric τ; record its value beside the screen's
   `intended_min_cell_flow_time_scale_s` receipt (**this measurement
   converts the intended-vs-achieved τ gap from PROVISIONAL to MEASURED**).
4. Solve runs to its LTS budget with drift inside the existing 5% bar; no
   FATAL, no watchdog kill.

Failure of any receipt is a *finding against a named bar*, not a retry:
which metric admitted it, at what value, against what outcome.

**Promotion measurements owed after the first 16-gene campaign** (decision
(c) wiring already in `mesh_robustness.py`): re-score `draft_over_hull_cell`
against rung-0 outcomes (the confusion table), score the
`bilge_min_radius_cells` pre-registered window (promote to voting only if it
separates), and re-pin the census bands if `evaluate()` drifts.

---

## SPEC — changes owed in files this investigation may not touch

*(orchestrator owns `run-case.sh` + `scripts/mesh_robustness.py`; items 1–3
of the 2026-08-18 filing are LANDED: early abort @1e-12 s, reclassification,
screen-verdict rows.)* Remaining, from this derivation:

1. **run-case.sh, first-iterations τ receipt:** record the *first* printed
   `Flow time scale min` (≈ geometric τ at uniform inlet U) as
   `min_flow_time_scale_geom=` in case.info, beside the abort-path value —
   it is the calibration datum §H.3 consumes, and it costs one awk.
2. **mesh_robustness rows:** carry `refused_no_rescue` (not just
   `screen_verdict`) so the confusion table can separate "predicted rung-0"
   from "predicted unmeshable" — two different claims to score.
3. **No change to the classify() τ bar is requested**: the runner's 1e-12
   live-abort bar and the harness's post-hoc taxonomy serve different
   consumers; the runner's is the enforcing one.

## Retirements (explicit)

- `admissibility.sheer_collapse_cells` — retired 2026-08-18 (stale pre-P1
  second copy; 5/25 phantom refusals). Successor:
  `min_interior_sheer_halfwidth_cells` (delivered surface; refuses all three
  labelled hulls the retired bar was validated on, by construction).
- The writer's all-DANGEROUS refusal — superseded by `refused_no_rescue`
  (mechanism-split; rescuable predictions are warned + recorded, and the
  canonical ladder is their measured deterministic path). No numeric bar
  moved; the bars' *values* are byte-identical.
