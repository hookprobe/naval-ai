# STL — is the surface handed to snappyHexMesh what separates the hulls that mesh from the ones that do not?

**Measured 2026-08-12. Correlation study only. No file in the CFD pipeline, the
hull grammar, `navalai/gates.py` or `data/` was changed by the pass that wrote
this.** New code is `navalai/stl_forensics.py` and `tests/test_stl_forensics.py`;
everything below is computed from them plus the five recorded Gate 2U campaign
JSONs, read only.

**The answer is NO, and it is the third mechanism this project has proposed for
the same failure and then refuted with its own data.** `docs/research/LAYERS.md`
§2 scored 29 geometry quantities (31 in its correction family) and the best
reached AUC 0.842 at family-wise p = 0.21. This pass scored 37 STL metrics and the best reaches **AUC 0.806 at
family-wise p = 0.207** against the strict labelling and **AUC 0.175 at
family-wise p = 0.279** against the operational one. Neither clears correction.
The study was then re-run against a concurrent change to the surface itself
(§7.1) and the verdict is unchanged: **six best-of-37 results across two arms
and three labellings, none below p = 0.05.** The hypothesis under test —
*"mesh failures correlate with STL quality rather than with hull shape"* — is
**not supported**.

---

## 0 · The five lines

1. **The lead reproduces exactly**, and it is real: `hull_to_stl` at its default
   `nx=80, nz=16` gives **5244 triangles on every hull** — hull 4 at 72.8 m³ and
   hull 8 at 24.3 m³ included — all watertight, outward, 0 open edges, 0 winding
   conflicts. §2.1.
2. **But the pipeline does not use that triangulation, and the one it does use
   is also constant** — 288956 triangles on 24 of 25 hulls — for a stronger
   reason: `stl_resolution` asks for the *same integer* (811) on every hull and
   the 600 ceiling binds on all of them. §2.2.
3. **A size-dependent resolution deficit is therefore impossible by
   construction.** The longitudinal facet length is **0.676683 hull cells on
   every hull, to six decimal places, at any LWL** — the entire mesh generator is
   scale-invariant in LWL except for the prism stack. The observed correlation
   between LWL and the coarse-facet fraction is **negative** (Spearman −0.74),
   i.e. the *opposite* of the hypothesis, and it is a shape effect wearing a size
   effect's clothes. §2.3.
4. **The STL has real defects, and they are the same on every hull.** 0.50% of
   the triangles — the deck lid, the transom cap and the stem cap — span the
   full beam in a single quad and are **60 to 214 hull cells long**; every hull
   carries 480–1414 near-degenerate slivers with a minimum angle of 0.13–0.59°;
   and the effective longitudinal resolution is **10.133 hull cells**, not the
   0.677 the triangle count suggests, because `closed_mesh` interpolates
   linearly between 41 stations. §2.4–2.6. **Zero self-intersections on all
   25 hulls** at the shipped resolution. §2.7.
5. **None of it separates the failures**, on either arm. Full ranked table with
   corrected p-values in §3, robustness arm in §7.1. The specific size-deficit
   test in §3.2. The precondition the brief set for specifying a
   uniform-vs-adaptive experiment — *"first establish whether uniform
   tessellation is the discriminator"* — **is not met, so that experiment is not
   specified here.** §6.

---

## 1 · Configuration, said out loud

docs/LESSONS.md defect class 6 is a defect measured at a configuration the
product never runs, and this study exists because the lead that motivated it was
measured at one.

| | the DEFAULT | the SHIPPED case |
|---|---|---|
| where | `hull_to_stl(hull, path)` with no `nx`/`nz` | `write_resistance_case` → `stl_resolution(lwl, 0.5·bg_dx/2⁵)` |
| nx × nz | 80 × 16 | **600 × 120** |
| triangles (arm A, below) | **5244** | **288956** |
| used by | `tests/`, ad-hoc scripts | `scripts/mesh_robustness.py:523`, i.e. **every Gate 2U campaign row** |

Everything scored in §3 is measured at the SHIPPED triangulation. The default is
carried alongside as three extra family members (`default_*`) so the lead can be
checked at the configuration it was taken at.

The rest of the configuration: seed-0 batch, `sample_valid(25, MissionSpec(),
seed=0)`, speed 2.57 m/s, scale 1.0, full-width (non-symmetric) domain,
`_HULL_REFINE` (4, 5) so the surface snaps at level 5, `_NX_BASE` 57. Hull cell
is `admissibility._pipeline_scales(...)["cell"]`, imported rather than restated.
The labels are the recorded mesh outcomes; **nothing here was re-meshed** and no
OpenFOAM was run.

**Which `closed_mesh`, and this matters — see §7.1.** Two arms, on two versions
of `Hull.closed_mesh`, both measured on this machine on 2026-08-12:

| arm | `navalai/geometry.py` | sha256 (12) | what it is |
|---|---|---|---|
| **A** | `1059c79` = `0e53331` | `57e13ea3d5f2` | the surface the cap-7 campaign was meshed from |
| **B** | `bbf1a47` | `9d4349362ae1` | the CHINE ON A GRID ROW change, landed mid-study |

**Arm A is primary and every number in §2–§5 is arm A**, for one reason: the
outcome labels come from meshes built on arm A's surface, and scoring arm B's
metrics against arm A's labels asks a metric to predict what happened to a
different hull. Arm B exists to answer whether the conclusion survives the
change, and §7.1 reports that it does.

**A companion document was written independently and concurrently:
`docs/research/STL-THIRDPARTY.md`** (commit `b91bbf3`) judges the same 25 STLs
with trimesh, PyMeshLab and Open3D at the DEFAULT `nx=80` triangulation. This document is our
own metrics at the SHIPPED `nx=600` triangulation. Neither restates the other's
numbers, and the two configurations are different — a ratio quoted there against
the level-4 cell at `LWL/79` and a ratio quoted here against the level-5 cell at
`LWL/599` are both correct and are not the same quantity.

---

## 2 · Phase 1 — what the mesher is actually handed

### 2.1 The lead, reproduced

Four hulls through `hull_to_stl` + `stl_watertight_report` at the default:

| hull | triangles | signed volume m³ | watertight | outward | open/non-manifold | winding conflicts |
|---:|---:|---:|:--|:--|---:|---:|
| 4 | 5244 | 72.8 | True | True | 0 | 0 |
| 14 | 5244 | 66.1 | True | True | 0 | 0 |
| 8 | 5244 | 24.3 | True | True | 0 | 0 |
| 3 | 5244 | 47.6 | True | True | 0 | 0 |

Reproduced to the digit. Over the full 25 the default count is 5244 on 24 hulls
and 5214 on one, and the shipped count is 288956 on 24 and 288718 on hull 23 —
the only variation anywhere is a handful of stem quads that self-filter by area. **The constancy is real and it is
not evidence of a defect** — see §2.2 for why it is arithmetically forced, and
§3.2 for what it can and cannot cause.

**The "two that fail are the two largest" reading does not survive the other 21
hulls.** By enclosed volume hull 4 ranks **7th** of 25 and hull 14 **10th**;
hulls 18, 16, 19, 2, 23 and 10 are all larger and four of them mesh clean. By
LWL — which is the quantity the tessellation actually scales with — hull 4 is
the **second shortest hull in the batch** at 8.94 m, shorter than both hulls
quoted as solving. AUC of enclosed volume against the runner bar is **0.693**,
family-wise p ≈ 1.0. A four-point ordering is not a trend.

### 2.2 Why the triangle count is constant, and why that is arithmetic

```
bg_dx       = _DOMAIN_LENGTH_L · LWL / _NX_BASE       = 4.5·LWL/57
target_edge = 0.5 · bg_dx / 2**_HULL_REFINE[1]        = 0.5·(4.5·LWL/57)/32
nx          = round(LWL / target_edge)                = round(57·32/2.25) = 811   ← no LWL
            → clamped to 600 for every hull
```

`target_edge` is itself proportional to LWL, so LWL cancels: `stl_resolution`
requests **811 for a 6.8 m hull and 811 for an 18.7 m hull**, and the `min(...,
600)` ceiling binds on both. `tests/test_stl_forensics.py::
test_stl_resolution_is_clamped_for_every_hull_in_the_batch` fences this across
the batch's measured LWL range.

Two consequences, and they point in opposite directions:

- **The clamp means the code's own stated requirement is not met, uniformly.**
  `stl_resolution`'s docstring says *"The STL must be FINER than the cells that
  snap to it"* and asks for half a level-5 cell. It gets `LWL/599` instead:
  **0.676683 cells** against a request of exactly 0.5, i.e. every hull's STL is
  **1.353× coarser than the pipeline asked for**. This is a receipt-level finding — the
  gap between intent and delivery is worth recording — and it is **identical on
  all 25 hulls**, so it cannot explain why 6 of them fail.
- **A size-dependent deficit is impossible.** `LWL/599` divided by
  `4.5·LWL/57/32` has no LWL in it (`np.linspace(0, LWL, 600)` gives 599
  intervals). Measured at LWL 6.836, 12.320 and 18.702 the ratio is 0.676683 to
  six decimals in all three cases.

### 2.3 The measured deficit does vary — and it varies the wrong way

The x-facet ratio is fixed, but the *median over all edges* is not, because the
z-edges are `girth/120` and girth is a shape quantity. Measured over the 25:

| | Spearman ρ vs LWL | p |
|---|---:|---:|
| `edge_median_over_cell` | **−0.545** | 0.0048 |
| `frac_tris_coarser_than_cell` | **−0.740** | 2.4e−5 |

Both **negative**: in this batch the *shorter* hulls carry the coarser
tessellation relative to their cell. The hypothesis as stated — *"relative
tessellation density falls with hull size"* — is refuted in **direction**, not
merely in significance. And the correlation is not causal in LWL either: LWL
cancels exactly in the x-direction, so what is being measured is that the short
hulls in this particular batch happen to have deep, beamy sections.

### 2.4 The full 25 at the shipped triangulation

`e_*/cell` are edge lengths in level-5 hull cells. `tris>1 cell` is the fraction
of triangles whose longest edge exceeds one hull cell. `degen` is triangles with
a minimum angle below 1°. `jump` is the angle between adjacent face normals.
`self-X` is self-intersecting triangle pairs. `cap7` is the recorded outcome at
the shipped `_MAX_LAYERS` = 7, judged by the bar `run-case.sh` enforces
(0 zero-volume, ≤5 wrongly-oriented, 0 ≤ skew ≤ 20); *strict X* marks hulls that
pass that bar but carry a non-zero wrongly-oriented count.

|  h | LWL m | cell mm | tris | e_med/cell | e_p95/cell | e_max/cell | tris>1 cell | aspect max | min angle | degen | jump max | jump med | feat edges | featL/LWL | self-X | cap7 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--|
| 0 | 15.02 | 37.0 | 288956 | 0.681 | 2.23 | 107 | 12.2% | 92 | 0.36° | 1382 | 144° | 0.007° | 2876 | 5.02 | 0 | ok |
| 1 | 10.47 | 25.8 | 288956 | 0.718 | 1.17 | 104 | 28.3% | 89 | 0.37° | 640 | 164° | 0.010° | 2906 | 5.14 | 0 | ok |
| 2 | 10.80 | 26.7 | 288956 | 0.952 | 3.11 | 233 | 97.0% | 199 | 0.17° | 1408 | 129° | 0.020° | 2825 | 5.62 | 0 | ok |
| 3 | 9.51 | 23.5 | 288956 | 0.759 | 1.89 | 192 | 64.5% | 164 | 0.20° | 1410 | 133° | 0.021° | 2793 | 5.23 | 0 | ok |
| 4 | 8.94 | 22.1 | 288956 | 1.134 | 4.31 | 214 | 99.4% | 180 | 0.18° | 1414 | 146° | 0.008° | 2653 | 5.67 | 0 | **FAIL, no rung** |
| 5 | 6.84 | 16.9 | 288956 | 1.160 | 1.73 | 169 | 100.0% | 144 | 0.23° | 1394 | 129° | 0.005° | 3076 | 7.16 | 0 | FAIL |
| 6 | 14.15 | 34.9 | 288956 | 0.695 | 1.60 | 140 | 19.1% | 119 | 0.28° | 986 | 141° | 0.019° | 2990 | 5.27 | 0 | ok |
| 7 | 15.23 | 37.6 | 288956 | 0.687 | 0.89 | 113 | 5.3% | 96 | 0.34° | 1406 | 165° | 0.020° | 2929 | 4.96 | 0 | ok |
| 8 | 12.32 | 30.4 | 288956 | 0.713 | 1.25 | 119 | 28.5% | 140 | 0.24° | 1320 | 150° | 0.011° | 3498 | 5.87 | 0 | ok |
| 9 | 9.78 | 24.1 | 288956 | 0.727 | 1.91 | 179 | 40.1% | 153 | 0.22° | 1388 | 129° | 0.013° | 3467 | 6.40 | 0 | ok (strict X) |
| 10 | 16.20 | 40.0 | 288956 | 0.696 | 1.71 | 121 | 21.0% | 104 | 0.32° | 750 | 146° | 0.008° | 3051 | 5.28 | 0 | FAIL |
| 11 | 9.99 | 24.7 | 288956 | 0.690 | 3.82 | 136 | 19.5% | 117 | 0.28° | 1366 | 129° | 0.010° | 2931 | 5.35 | 0 | ok |
| 12 | 13.63 | 33.6 | 288956 | 0.710 | 2.14 | 144 | 25.8% | 249 | 0.13° | 1326 | 142° | 0.011° | 3102 | 5.59 | 0 | FAIL |
| 13 | 9.96 | 24.6 | 288956 | 0.682 | 1.48 | 98 | 32.9% | 84 | 0.40° | 1336 | 143° | 0.007° | 3403 | 6.00 | 0 | ok |
| 14 | 11.67 | 28.8 | 288956 | 0.684 | 1.49 | 170 | 17.7% | 165 | 0.20° | 1408 | 138° | 0.008° | 3018 | 5.89 | 0 | **FAIL, no rung** |
| 15 | 13.08 | 32.3 | 288956 | 0.701 | 0.95 | 135 | 7.1% | 116 | 0.29° | 1016 | 162° | 0.025° | 2837 | 4.88 | 0 | ok |
| 16 | 12.18 | 30.0 | 288956 | 0.775 | 2.92 | 177 | 94.9% | 151 | 0.22° | 1408 | 157° | 0.019° | 2921 | 5.72 | 0 | ok (strict X) |
| 17 | 13.60 | 33.6 | 288956 | 0.700 | 1.18 | 66 | 21.3% | 57 | 0.59° | 1242 | 165° | 0.003° | 2957 | 5.25 | 0 | ok |
| 18 | 17.29 | 42.7 | 288956 | 0.681 | 0.94 | 85 | 5.6% | 97 | 0.34° | 1266 | 163° | 0.007° | 2818 | 4.84 | 0 | FAIL |
| 19 | 11.97 | 29.5 | 288956 | 0.873 | 1.18 | 164 | 99.2% | 140 | 0.24° | 1414 | 160° | 0.015° | 2920 | 5.71 | 0 | ok (strict X) |
| 20 | 12.64 | 31.2 | 288956 | 0.683 | 1.26 | 77 | 12.2% | 66 | 0.51° | 812 | 164° | 0.018° | 3262 | 5.41 | 0 | ok |
| 21 | 15.64 | 38.6 | 288956 | 0.683 | 1.43 | 100 | 12.9% | 85 | 0.39° | 1162 | 157° | 0.015° | 3346 | 5.63 | 0 | ok |
| 22 | 15.73 | 38.8 | 288956 | 0.740 | 1.60 | 150 | 18.0% | 128 | 0.26° | 650 | 144° | 0.014° | 3155 | 5.35 | 0 | ok |
| 23 | 18.70 | 46.1 | 288718 | 0.695 | 1.03 | 93 | 13.3% | 94 | 0.35° | 480 | 180° | 0.013° | 2796 | 4.75 | 0 | ok |
| 24 | 14.62 | 36.1 | 288956 | 0.680 | 1.23 | 93 | 9.8% | 154 | 0.22° | 1328 | 164° | 0.011° | 2820 | 4.73 | 0 | ok |

Read the two hulls that fail at every layer count against each other before
reading any statistic: **hull 4 is the second-worst row in the table on almost
every column and hull 14 is unremarkable on all of them.** Hull 14's
`e_med/cell` of 0.684 is the batch's fourth *best*; hull 8, which meshes clean,
sits at 0.713. Whatever hulls 4 and 14 share, it is not visible here.

### 2.5 The 0.50% of the surface that is 200 cells across

`Hull.closed_mesh` builds the shell as `nx-1` × `nz` quads per side, and then
closes it with three patches that are **one quad wide across the whole beam**:

```python
# geometry.py:298  — deck lid, ONE quad spanning port to starboard
quad(S[i, nz], P[i, nz], P[i + 1, nz], S[i + 1, nz])
# geometry.py:301  — transom cap, one quad per z level, full local beam
quad(S[0, j], P[0, j], P[0, j + 1], S[0, j + 1])
# geometry.py:304  — stem cap, same
```

That is exactly `(nx−1)·2 + nz·2 + nz·2 = 1678` triangles of the 289198 the
generator emits, and **1436 survive the area filter on each of the three hulls
measured below — 0.50% of the surface, the same count on all three.** The
structure is the same on every hull the grammar emits; only the count of stem
quads that degenerate to zero area can vary (hull 23 drops 238 more triangles
overall than the rest of the batch, and it was not one of the three measured
patch-by-patch). Measured on the three rendered hulls:

| | centreline-spanning tris | their edge/cell median | max | SHELL-only edge/cell median | shell p95 | shell frac > 1 cell |
|---|---:|---:|---:|---:|---:|---:|
| hull 4 (fails) | 1436 (0.50%) | **191** | 214 | 1.333 | 4.68 | 99.4% |
| hull 8 (clean) | 1436 (0.50%) | **60** | 119 | 0.787 | 1.26 | 28.2% |
| hull 14 (fails) | 1436 (0.50%) | **140** | 170 | 0.854 | 2.03 | 17.3% |

Those three patches are the deck edge, the transom edge and the stem — which
`navalai/cfd/case.py`'s `addLayersControls` comment names as *"exactly the places
a boundary layer must not stop"*. So a mechanism is available: a facet 200 cells
long at a layer termination is a plausible source of a folded prism. **It is a
story, and the data does not carry it**: hull 8, which produces the cleanest mesh
in the batch (skew 2.87, 0 wrongly-oriented), has this structure too, at 60 cells;
hull 2 has it at 233 cells, the batch maximum, and meshes. `edge_max_over_cell`
scores AUC 0.640 / family-wise p 0.998 against the runner bar.

### 2.6 The effective longitudinal resolution is 10.1 cells, not 0.68

`closed_mesh` samples the **41 station polylines** and interpolates linearly in
x between them (`_section_at`), so however many triangles are written the surface
has a crease every `LWL/40` and is exactly ruled in between. In hull cells:

```
station spacing / hull cell = (LWL/40) / (4.5·LWL/57/32) = 10.133   ← again, no LWL
```

**The real feature spacing of the surface is ten hull cells, at every hull size.**
Raising `nx` from 80 to 600 multiplies the triangle count by 55 and does not move
this number at all; it only subdivides the ruled strips. This is stated in
`admissibility.surface_grid`'s docstring and is repeated here because it is the
single most important thing about the surface and it is invisible in the
triangle count. It is also, again, **identical on every hull.**

### 2.7 Self-intersections: measured, and zero

`stl_watertight_report` cannot see a self-intersection by construction — it keys
on undirected edge counts, and a surface passing through itself still gives every
edge exactly two faces. `tests/test_stl_forensics.py::
test_watertight_is_blind_to_a_self_intersection` builds two overlapping tetrahedra
in one solid and asserts both halves: the old report returns watertight True /
outward True / 0 open / 0 conflicts, and `self_intersections` returns a non-zero
count.

**Measured on all 25 hulls at 600×120: zero self-intersecting triangle pairs**,
and on arm B as well (§7.1). `docs/research/STL-THIRDPARTY.md` (commit
`b91bbf3`) reaches the same conclusion independently, at the 80×16 default, with
three third-party implementations; read it there rather than here for what those
libraries say.
`n_self_intersecting_pairs` is therefore constant and unscoreable (AUC nan), and
that is the answer, not a missing answer: self-intersection is not the
discriminator because it does not occur.

The function's blind spot is stated rather than defaulted: a **coplanar** overlap
is not detected by a segment/triangle test, so `coplanar_candidate_pairs` is
returned separately (2.1e5 on hull 4 — the deck lid and the flat panels, all
adjacent and none overlapping), and an over-budget broad phase returns
`complete: False` with a count of **−1**, never 0.

---

## 3 · Phase 2 — the correlation study

37 metrics, scored by AUC against three labellings, with the family-wise
correction `docs/research/LAYERS.md` §2.1 used: permutation of the labels,
20 000 draws, statistic = max |AUC − 0.5| over the whole family. The per-metric
`fwp` column is the probability that the family maximum under the null reaches at
least that metric's deviation, which is the number a reader wants beside a
best-of-37 result.

Labellings, all derived from the recorded campaign rows by predicate, never
restated (`stl_forensics.campaign_labels`, fenced by
`test_the_cap7_labelling_is_the_six_hulls_stl_md_names`):

- **runner bar (6 positives: 4, 5, 10, 12, 14, 18)** — the bar `run-case.sh`
  actually enforces. This is the operational definition.
- **strict (9 positives: + 9, 16, 19)** — the campaign JSON's `meshed` flag,
  which additionally requires zero wrongly-oriented faces. `run-case.sh` does not
  enforce this.
- **no admissible rung (2 positives: 4, 14)** — fails the runner bar at every
  layer count any campaign tried. Two positives is not a sample; it is scored
  because the brief asked and it is reported with that caveat.

### 3.1 The ranked table

| metric | AUC runner | fw p | AUC strict | fw p | AUC no-rung |
|---|---:|---:|---:|---:|---:|
| `normal_jump_median_deg` | **0.175** | **0.279** | 0.347 | 0.979 | 0.261 |
| `aspect_median` | 0.754 | 0.696 | 0.625 | 0.997 | 0.630 |
| `aspect_max` | 0.746 | 0.746 | 0.792 | 0.273 | 0.913 |
| `min_angle_deg` | 0.254 | 0.746 | 0.208 | 0.273 | 0.087 |
| `aspect_max_transom_decile` | 0.737 | 0.795 | **0.806** | **0.207** | **0.935** |
| `default_aspect_max` | 0.693 | 0.940 | 0.722 | 0.715 | 0.870 |
| `min_angle_p1_deg` | 0.316 | 0.963 | 0.347 | 0.979 | 0.196 |
| `frac_edges_jump_over_60deg` | 0.684 | 0.963 | 0.583 | 1.000 | 0.304 |
| `area_max_over_cell2` | 0.667 | 0.986 | 0.771 | 0.397 | 0.870 |
| `frac_tris_over_4_cells` | 0.654 | 0.992 | 0.628 | 0.995 | 0.870 |
| `feature_edges_transom_decile` | 0.351 | 0.996 | 0.389 | 0.999 | 0.163 |
| `edge_max_over_cell` | 0.640 | 0.998 | 0.764 | 0.442 | 0.891 |
| `aspect_p95` | 0.640 | 0.998 | 0.549 | 1.000 | 0.761 |
| `normal_jump_max_deg` | 0.360 | 0.998 | 0.347 | 0.979 | 0.348 |
| `feature_edge_length_over_lwl` | 0.640 | 0.998 | 0.778 | 0.353 | 0.804 |
| `feature_edge_length_over_cell` | 0.640 | 0.998 | 0.778 | 0.353 | 0.804 |
| `jump_max_bow_decile` | 0.360 | 0.998 | 0.347 | 0.979 | 0.348 |
| `edge_p95_over_cell` | 0.632 | 0.999 | 0.660 | 0.968 | 0.761 |
| `edge_max_m` | 0.623 | 0.999 | 0.708 | 0.782 | 0.783 |
| `normal_jump_p99_deg` | 0.395 | 1.000 | 0.396 | 1.000 | 0.348 |
| `n_degenerate_tris` | 0.601 | 1.000 | 0.743 | 0.582 | 0.924 |
| `frac_degenerate_tris` | 0.601 | 1.000 | 0.743 | 0.582 | 0.924 |
| `frac_tris_coarser_than_cell` | 0.588 | 1.000 | 0.736 | 0.608 | 0.652 |
| `edge_median_over_cell` | 0.561 | 1.000 | 0.701 | 0.837 | 0.609 |
| `area_min_over_cell2` | 0.544 | 1.000 | 0.639 | 0.992 | 0.674 |
| `edge_min_over_cell` | 0.535 | 1.000 | 0.639 | 0.992 | 0.696 |
| `jump_max_transom_decile` | 0.386 | 1.000 | 0.500 | 1.000 | 0.826 |
| `default_edge_median_over_cell` | 0.570 | 1.000 | 0.708 | 0.782 | 0.609 |
| `edge_over_cell_bow_decile` | 0.535 | 1.000 | 0.674 | 0.932 | 0.913 |
| `frac_edges_jump_over_30deg` | 0.474 | 1.000 | 0.521 | 1.000 | 0.304 |
| `n_feature_edges` | 0.474 | 1.000 | 0.521 | 1.000 | 0.304 |
| `lwl` (control) | 0.474 | 1.000 | 0.382 | 0.998 | 0.174 |
| `feature_edges_bow_decile` | 0.526 | 1.000 | 0.722 | 0.715 | 0.391 |
| `feature_edge_x_concentration` | 0.482 | 1.000 | 0.444 | 1.000 | 0.674 |
| `default_n_tris` | 0.526 | 1.000 | 0.531 | 1.000 | 0.522 |
| `stack_over_cell` (control) | 0.526 | 1.000 | 0.618 | 0.998 | 0.826 |
| `aspect_max_bow_decile` | 0.491 | 1.000 | 0.618 | 0.998 | 0.891 |
| `n_zero_area_tris` | — | — | — | — | — |
| `n_self_intersecting_pairs` | — | — | — | — | — |
| `n_duplicate_tris` | — | — | — | — | — |

The last three rows are **constant across the batch** (0 zero-area triangles, 0
self-intersecting pairs, 0 duplicate triangles on all 25) and are therefore not
scoreable. `auc` returns `nan` rather than 0.5 for them, on purpose: *could not
be computed* and *computed, and it is chance* are different answers, and this
repository has already paid for conflating them.

**Reading it.**

- Against the **operational** labelling the best result in 37 tries is
  `normal_jump_median_deg` at AUC 0.175 — inverted, i.e. the failures have a
  *smoother* median crease — at family-wise p = 0.279. **Not significant.**
- Against the **strict** labelling the best is `aspect_max_transom_decile` at
  0.806, family-wise p = 0.207. **Not significant.**
- The no-rung labelling produces AUCs up to 0.935, and family-wise p = 0.437.
  With two positives, one metric in 37 reaching 0.935 by chance is ordinary.
- **`aspect_max` and `min_angle_deg` are the same metric twice** (a sliver's
  worst angle and its worst aspect are algebraically linked) and they score
  0.746/0.254 and 0.792/0.208 — mirror images, as they must. They are counted
  once each in the family, which makes the correction slightly conservative in
  the right direction.
- **The controls behave.** `lwl` scores 0.474 and `stack_over_cell` 0.526 — both
  chance — which is the check that the family is not simply ranking hull size.

**And this understates the multiplicity.** `docs/research/LAYERS.md` §2 already
spent 31 metrics on the same 25 hulls and the same labels. Taken as the project
has actually run it — two passes, 31 + 37 = 68 metrics, one dataset — the corrected p of
the best result in *either* pass is worse than either table shows. Two
independent metric families have now failed to separate these six hulls.

### 3.2 The specific test the brief asked for

> *"Test specifically whether triangle count being constant at 5244 while LWL
> varies produces a size-dependent resolution deficit, and whether THAT separates
> the failures."*

Three answers, in order:

1. **The count is constant, at both configurations.** 5244 at the default (a
   literal), 288956 at the shipped case (the 600 clamp). §2.1.
2. **It does not produce a size-dependent deficit.** LWL cancels exactly:
   `h_stl,x / h_cell = 0.676683` at every LWL and `station spacing / h_cell =
   10.133` at every LWL, both to six decimals. §2.2, §2.6. What deficit does vary
   varies with SHAPE, and its correlation with LWL is **negative** — the opposite
   direction to the hypothesis. §2.3.
3. **It does not separate the failures.** `edge_median_over_cell` AUC 0.561
   (fw p 1.000), `frac_tris_coarser_than_cell` AUC 0.588 (fw p 1.000),
   `default_edge_median_over_cell` AUC 0.570 (fw p 1.000), `default_n_tris` AUC
   0.526. Hull 4 does sit at the extreme of the coarse-facet metrics (99.4% of
   triangles coarser than a cell, `e_med/cell` 1.134) — but hull 5, which also
   fails, sits at 100%, and hulls 19, 2 and 16 sit at 99.2%, 97.0% and 94.9% and
   **pass the runner bar**, while hull 14 — the *other* hull with no admissible
   rung — sits at 17.7%, in the clean half of the batch.

---

## 4 · Phase 3 — eMesh

`snappyHexMeshDict` refines `hull.eMesh` to level 5, and the eMesh comes from
`surfaceFeatureExtract` with `includedAngle 150`, i.e. **any edge whose two faces'
normals differ by more than 30°**. `stl_forensics.feature_edges` replicates that
rule exactly (fenced both directions by
`test_feature_edges_reproduce_the_case_includedAngle_rule`: a 20° crease extracts
nothing, a 40° crease extracts one edge).

Feature-edge count per hull runs **2653–3498**, and total feature length runs
**4.73–7.16 × LWL**. Neither separates anything: `n_feature_edges` AUC 0.474,
`feature_edge_length_over_lwl` AUC 0.640 (fw p 0.998).

**The x-distribution does show a spike at both ends — on every hull, including
the clean ones, so it is not a smoking gun.** Feature edges per 5%-of-LWL bin:

| hull | transom bin | interior bins (typical) | bow bin | outcome |
|---|---:|---|---:|---|
| 8 | **399** | 149–170 | **299** | clean, skew 2.87 |
| 14 | **361** | 116–150 | **330** | fails at every rung |
| 2 | **361** | 105–145 | **268** | clean |
| 4 | **357** | 103–129 | **216** | fails at every rung |
| 23 | **330** | 90–152 | **244** | clean |

The **largest** transom spike and the **second-largest** bow spike in that set
belong to hull 8, the cleanest mesh in the batch. `feature_edges_transom_decile`
scores AUC 0.351 (inverted; fw p 0.996) and `feature_edges_bow_decile` 0.526.
The spike is structural — the transom cap edge, the deck edge and the stem
convergence are feature edges on any hull this grammar emits — and it carries no
information about the outcome.

One incidental measurement worth recording, because it looks alarming and is not
a finding: the maximum normal jump is **128–180°** on every hull, and hull 23
reaches **179.9°**, i.e. two facets almost exactly back-to-back at the stem where
port and starboard converge. Hull 23 meshes clean. `normal_jump_max_deg` AUC
0.360.

---

## 5 · Phase 4 — the pictures, and what they show

- `docs/research/stl-hull04.png` — hull 4, LWL 8.942 m, fails the runner bar at
  n = 3, 5, 7 and 9.
- `docs/research/stl-hull14.png` — hull 14, LWL 11.670 m, fails at n = 4, 6, 7, 8
  and 10.
- `docs/research/stl-hull08.png` — hull 8, LWL 12.320 m, meshes clean at n = 7
  (skew 2.87, 0 wrongly-oriented, 6.33 layers achieved).

Each is six orthographic wireframe panels of the **actual shipped 600×120
triangulation with no decimation** — top, side, front, isometric, then true-scale
zooms on the last and first 7% of the length coloured by `log10(edge / hull
cell)`. `stl_forensics.render_facets` produced them.

**THE PNGs ARE ARM A, AND THEY ARE NO LONGER IN THE REPOSITORY.** They were
rendered at 14:53 on 2026-08-12 and committed at 15:41, but `bbf1a47` — the
chine row — landed at 15:22 BETWEEN those two times. So the images show the
SUPERSEDED surface while sitting in a document whose primary arm is now the
other one, and nothing in the file said so.

They were also 2.7 MB of reproducible binary in git, which is gap J6 exactly:
`.gitignore` already records that `renders/` "held 9 committed PNGs (~2.3 MB)
of CFD output that is reproducible" and gitignores it. `docs/research/` was
simply not covered by that rule. It is now. Regenerate any of them with:

```python
from navalai.admissibility import _pipeline_scales
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import MissionSpec
from navalai.stl_forensics import render_facets
X, _ = sample_valid(25, MissionSpec(), seed=0)
h = Hull(X[4])
render_facets(h, "docs/research/stl-hull04.png", nx=600, nz=120,
              cell=_pipeline_scales(float(h.x[-1]))["cell"], title="hull 4")
```

which renders the CURRENT surface — so a regenerated image can never silently
be a picture of a geometry the code no longer produces.

What they show, and it is worth more than the metric table:

- **The two transom panels are the picture of §2.5.** The deck lid and the
  transom cap render as solid yellow — `log10(edge/cell) ≈ 2`, a hundred hull
  cells across a single facet — bounded on all sides by shell facets at
  `log10 ≈ 0`. The discontinuity is two orders of magnitude and it is at a layer
  termination.
- **The top views show the 41 stations.** The longitudinal creases at `LWL/40`
  are visible as bands in all three hulls; the 600 x-divisions between them are
  not resolvable as separate features because they lie in the ruled interior.
  That is §2.6 as an image.
- **Hull 8 does not look better than hull 4 and 14 where it matters.** Its stem
  panel is if anything more contorted (a plan-form tangent break at x ≈ 7.4 m is
  plainly visible in its top view), and it meshes cleanest. A reader looking for
  the visual difference between the two failures and the success will not find
  one, which is the same conclusion §3 reaches with numbers.

---

## 6 · What this pass does NOT license

**The uniform-vs-adaptive tessellation experiment is not specified here, and
should not be run on the strength of this study.** The brief made it conditional:
*"First establish whether uniform tessellation is the discriminator."* It is not.
Every quantity by which the tessellation is uniform — triangle count, facet
length in cells, station spacing in cells, the deck/transom cap structure — is
**identical or near-identical across all 25 hulls**, and the six that fail are
distributed through the batch on every one of them. An adaptive tessellation
would change a variable that is currently constant and therefore currently
explains nothing; the experiment would be measuring a hypothesis this data has
already declined to support, which is the pattern docs/LESSONS.md records twice.

Two things this pass *does* leave standing, neither of which is a mechanism:

- **The 1.35× clamp gap (§2.2) is a real divergence between what
  `stl_resolution` asks for and what it returns**, and it is not recorded
  anywhere else. It is uniform across hulls, so it cannot be the discriminator,
  but a pipeline whose stated invariant ("the STL must be FINER than the cells
  that snap to it") is violated on every case it has ever run is worth knowing
  about. Any change to it belongs to whoever owns `navalai/cfd/case.py`, with its
  own before/after mesh measurement.
- **The transom/deck-cap facets (§2.5)** are a plausible-sounding mechanism with
  no supporting correlation. Recorded so it is not re-proposed as a new idea.

---

## 7 · Robustness, and what could NOT be verified

### 7.1 The concurrent chine-row change — re-run, and the verdict does not move

While this study was being written, a separate pass put the CHINE on a grid row
in `Hull.closed_mesh` (`Hull.chine_row`, commit `bbf1a47`), so the knuckle is a
mesh edge instead of something the z-sampling chords across. That is a change to
the exact surface this document measures, and it appeared in the working tree
**after** §2–§5's measurement pass had finished. Rather than caveat the result,
the entire study was re-run against it: `navalai/geometry.py`,
`navalai/admissibility.py` and `navalai/cfd/case.py` were sha256-hashed before
and after the run and were **unchanged across it**
(`geometry.py` = `9d4349362ae1`, which is `bbf1a47`'s), so the second arm is a
measurement of one tree, not of a moving one.

What the change does to the surface (arm A = PRE-bbf1a47, arm B = the chine
row, which IS the committed surface — the parenthetical here read
"arm A = committed" until 2026-08-12 and contradicted the sentence three lines
above it, which records the second arm hashing to `bbf1a47`'s `geometry.py`):

| | arm A | arm B |
|---|---|---|
| triangles | 288956 on 24 hulls | 288658–288912, a few dozen fewer per hull |
| max normal jump, range over 25 | 128.6°–179.9° | **93.0°–179.8°** |
| max normal jump, hull 0 / 5 / 10 | 143.7° / 129.1° / 146.1° | **107.4° / 93.0° / 104.3°** |
| feature edges, range | 2653–3498 | 2625–3394 |
| self-intersecting pairs | 0 on all 25 | **0 on all 25** |
| `edge_median_over_cell`, range | 0.680–1.160 | 0.677–1.695 |

The crease is measurably better resolved — the maximum facet-to-facet fold falls
on **every one of the 25 hulls**, by up to 39° — which is the change doing
exactly what its author says it does.

**It does not change this document's conclusion.** Re-scored, same 37 metrics,
same three labellings, same 20 000-draw correction:

| labelling | arm A best | fw p | arm B best | fw p |
|---|---|---:|---|---:|
| runner bar (6 pos) | `normal_jump_median_deg` 0.175 | 0.279 | `normal_jump_median_deg` 0.246 | **0.674** |
| strict (9 pos) | `aspect_max_transom_decile` 0.806 | 0.207 | `default_edge_median_over_cell` 0.840 | **0.083** |
| no rung (2 pos) | `aspect_max_transom_decile` 0.935 | 0.437 | `frac_tris_over_4_cells` 0.957 | 0.382 |

Against the **operational** labelling the best result gets *worse* (fw p 0.279 →
0.674). Against the strict labelling — the one `run-case.sh` does not enforce —
the best reaches fw p 0.083, closer than anything measured in either arm and
**still not significant**, on a metric measured at the 80×16 default rather than
at the shipped triangulation. Two arms, six best-of-37 results, none below 0.05.

### 7.2 What could NOT be verified

- **The solve results for hulls 3, 8, 19 and 22 are not in this tree.** The brief
  cited them; `data/gate2u-cap7-mesh.json` and the other four mesh-only arms
  record `solve_requested: 0.0` and `why: meshed-no-solve-requested` for every
  row, and `data/gate2u-campaign-baseline.json` — the only arm with solve data —
  covers hulls 0–19 and records `why == "ok"` for hulls **7, 9, 13, 15 and 17
  only**; hulls 3, 8 and 19 all carry `solve_attempted: false` and
  `why: checkmesh-wrong-oriented` there, and hull 22 is not in that arm at all
  (it stopped at hull 19). Hull 5's row in the same file is internally
  inconsistent — `why: mesh-build-failed`, `cells: -1`, `max_skewness: -1.0`,
  and yet `solves: true` with `solve_reached: 2000` — so a sixth `solves` flag
  exists in that JSON and is not usable as an outcome. Flagged, not fixed:
  `data/` is not this pass's to edit. Every labelling in §3 is therefore a **mesh** outcome, not a
  solve outcome, and is labelled as such. If solve results for those four hulls
  exist, they are outside the repository and this study has not seen them.
- **No mesh was built and no solver was run by this pass.** Every outcome label
  comes from the recorded JSONs. A metric that separates a *solve* failure could
  not have been detected here.
- **Coplanar self-intersections are not detected** (§2.7). The segment/triangle
  narrow phase is blind to them by construction; `coplanar_candidate_pairs` is
  reported so the blind spot is visible rather than assumed empty.
- **`n = 25` with 6 positives is a small sample and the corrections above are
  honest about it, not generous.** A metric with a true AUC of 0.8 would fail to
  clear this correction most of the time. The correct reading of §3 is *"no
  evidence found"*, not *"proved absent"* — the same reading LAYERS.md §2 earns.
- **The renders are of three hulls, chosen because the brief named them.** They
  are illustrations of measurements made over 25; they are not evidence in
  themselves, and they are **arm A only** — they were produced before the
  chine-row change of §7.1 and have not been regenerated against it.
- **The two arms of §7.1 are not independent evidence.** They are the same 25
  hulls, the same labels and the same metric family measured on two versions of
  one surface. The second arm shows the conclusion is not an artefact of the
  chine chording; it does not double the sample.

---

## 8 · Reproducing this

```
source ~/.venvs/naval/bin/activate
python -m navalai.stl_forensics --n 25 --seed 0 --perm 20000 --json /tmp/stl_study.json
python -m pytest tests/test_stl_forensics.py -q
```

Arm A reproduces at `navalai/geometry.py` as committed at `0e53331`; arm B
(§7.1) at `bbf1a47`, which is where the tree now is. The command is the same —
which version of `closed_mesh` is on disk is the only difference, and it is why
§1 pins it by sha256 rather than by date.

Runtime is ~9 minutes for the 25-hull study (dominated by `closed_mesh` at
600×120 and the self-intersection broad phase, ~16 s per hull) and ~2 s for the
tests. The study writes nothing inside the repository.

**`tests/test_stl_forensics.py` is not yet owned by a gate row**, so
`tests/test_gate_integrity.py::test_every_test_file_is_owned_by_a_gate` fails
until one is added to `navalai/gates.py`. The row this suite wants:

```python
Gate("Gate 2F", "STL forensics: watertight is not valid, and the surface "
     "handed to snappy is measured rather than assumed",
     "tests/test_stl_forensics.py"),
```

`navalai/gates.py` is not this pass's file to edit, so the row is stated rather
than added — the same reason `data/` was left alone in §7.2.

**One other suite is red in this tree and it is not this one's doing:**
`tests/test_cfd_reference_parity.py::test_the_layer_backoff_ladder_descends_by_
two_and_stops_at_three` asserts `layer_backoff_ladder(10) == [8, 6, 4]`, which
was the ladder's behaviour before commit `1059c79` made it two-sided with step 1
(it now returns `[9, 8, 7, 6, 5, 4, 3]`). Full run at `737da23` plus this pass's
files: **877 passed, 5 skipped, 2 failed** — that one and the missing gate row.
