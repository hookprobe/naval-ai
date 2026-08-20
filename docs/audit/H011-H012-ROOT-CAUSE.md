# h011 / h012 — the chain walked, and the invariant that did NOT break

**Question asked.** `data/gate2u-16gene-mesh.json` (N=25, seed 0, scale 1.0,
speed 2.57, LTS, np=10) and `data/gate2u-16gene-solve.json` (18 rows, hulls
0-17) both record the same two deterministic failures: **h011** — 13 wrongly
oriented faces, max skewness 247.226, non-orthogonality 90.488 — and **h012** —
12 wrongly oriented faces, skew 9.946, non-orthogonality 98.332. Both refused
at rung 0 (the derived layer count, `LAYER_BACKOFF=0`). The operator's
directive: trace backwards genome → sections → curves → surfaces →
tessellation → STL → mesh, find the FIRST mathematical invariant that breaks,
and exclude the invalid region by construction rather than repairing bad
geometry.

**Answer, stated first.** *No invariant breaks anywhere upstream of the volume
mesh.* Every step of the chain was measured on the reproduced hulls and on all
23 that meshed. The section solve is clean, the edge curves are clean, the
surface is fold-free, self-intersection-free, watertight and outward-wound, and
the tessellation of h011/h012 is **better** than that of several hulls that
meshed. A family of **83 geometric descriptors** was scored against the mesh
outcome with the repository's own permutation instrument
(`stl_forensics.family_wise_p`, 20 000 permutations): **best family-wise
p = 0.601**. Nothing separates the two failures from the 23 passers.

The first thing that is different about h011/h012 is a property of the
**volume mesh snappyHexMesh built at rung 0**, not a property of the hull the
grammar emitted. There is therefore **no admissible-region boundary to derive**
from this evidence, and this document does not invent one.

Two by-products of the investigation are real findings in their own right and
are recorded in §7: the `stl_sha256` identity receipt is **not portable across
machines**, and the concurrent ~161-station `hull_to_stl` rebuild **would not
fix h011/h012** (measured, §6).

---

## 0. Reproduction, and the one thing that did NOT reproduce

Everything below was run against a pinned snapshot of the campaign commit
`168ea82` ("mac: 2U mesh-half complete"), extracted read-only to `/tmp` with
`git archive`, so that concurrent edits to the working tree could not
contaminate the measurement.

**The genome reproduces exactly.** `sample_valid(25, MissionSpec(), seed=0)`
returns the same population from the pinned tree and from the working tree
(`np.array_equal` → True), and all 25 LWLs match the per-hull `lwl` recorded
in both campaign JSONs to the recorded 3 decimals:

| hull | 0 | 1 | 2 | … | 11 | 12 | … | 24 |
|---|---|---|---|---|---|---|---|---|
| recorded `lwl` | 10.687 | 14.734 | 17.829 | … | **17.876** | **12.842** | … | 11.663 |
| regenerated | 10.687 | 14.734 | 17.829 | … | **17.876** | **12.842** | … | 11.663 |

**The STL sha256 does NOT reproduce, and I am saying so loudly.** Regenerating
`hull_to_stl(Hull(x), …, nx=600, nz=120)` on this box gives, for the three
hulls tested (0, 11, 12), hashes that differ from every recorded one:

```
hull  0   mine 1a39a297e5206cc7…   recorded a7292e7ed3b1f3f4…   MISMATCH
hull 11   mine c41ed14799370594…   recorded a4f40b868a4ee2ca…   MISMATCH
hull 12   mine 8310986a90338ac7…   recorded 934e9651505a73dd…   MISMATCH
```

The mismatch is **not** a code drift. Every function on the STL path —
`_stations`, `_keel`, `_deadrise`, `_fillet_coeffs`, `sample_section`,
`_resample`, `Hull.__post_init__`, `chine_row`, `_section_at_rows`,
`closed_mesh`, `hull_to_stl`, `_tris_to_ascii_stl`, `stl_resolution` — is
byte-identical between `168ea82` and today's tree once docstrings and comments
are stripped (the only difference anywhere is an added finiteness guard in
`sac_exponents`, which is value-preserving for finite input). `nx=600, nz=120`
is confirmed against a real case receipt (`runs/zba_h11/case.info`:
`stl_nx_shipped=600`, `stl_nz_shipped=120`).

The mismatch is a **platform** difference, and the ascii-STL hash is
measurably too fragile to survive one. Measured on h011's shipped
triangulation (288 956 triangles, 3 467 472 printed numbers at `%.6e`), the
count of numbers sitting within a relative distance ε of a rounding boundary
in the 7th significant digit:

| ε (relative) | 1e-16 | 1e-15 | 1e-14 | 1e-13 | **1e-12** | 1e-11 | 1e-10 | 1e-9 |
|---|---|---|---|---|---|---|---|---|
| numbers that would flip a digit | 0 | 0 | 0 | 0 | **13** | 47 | 444 | 4 408 |

So a cross-platform arithmetic divergence at ~1e-12 relative — FMA
contraction, a different libm `tan`, a different BLAS in `np.interp`'s
neighbourhood — already flips 13 printed digits and therefore the hash, while
changing no geometry a mesher can see. (The count is linear in ε, so 1e-13
flips one digit with probability ≈ 0.13 per hull, and 1e-11 flips 47.) The
campaign ran on the Mac (every commit is labelled `mac:`); this reproduction
ran on x86-64 Linux, numpy 2.3.5.

**What this costs the investigation:** nothing material. The genome is
bit-identical, the emitter is byte-identical, and a 1e-13-relative difference
cannot turn 0 wrongly-oriented faces into 13. Every measurement below is
therefore about the same hulls the campaign meshed, at a geometric precision
~11 orders finer than the cell. **What it costs the project** is stated in §7.

---

## 1. GENOME — what is distinctive about h011/h012

Sixteen genes, the position of each inside its grammar box, and its rank among
the 25-hull population (rank 1 = smallest, 25 = largest):

| gene | box | h011 | %box | rank | h012 | %box | rank | pop mean |
|---|---|---|---|---|---|---|---|---|
| LWL | 2.5 – 24.0 | 17.876 | 71.5 | 21 | 12.842 | 48.1 | 14 | 13.523 |
| BWL | 0.166 – 6.0 | 3.240 | 52.7 | 12 | 4.680 | 77.4 | 22 | 3.366 |
| T | 0.014 – 2.0 | 0.664 | 32.7 | 6 | 1.345 | 67.0 | 20 | 0.947 |
| D | 0.314 – 3.0 | 2.115 | 67.0 | 7 | 2.041 | 64.3 | 5 | 2.403 |
| Cp | 0.525 – 0.710 | 0.548 | 12.3 | 3 | 0.673 | 79.9 | 23 | 0.619 |
| lcb | −3 – 3 | −0.019 | 49.7 | 20 | −1.730 | 21.2 | 8 | −0.909 |
| x_mb | 0.40 – 0.68 | 0.594 | 69.3 | 20 | 0.554 | 55.2 | 15 | 0.545 |
| r_transom | 0.05 – 0.50 | 0.372 | 71.6 | 20 | 0.239 | 41.9 | 12 | 0.264 |
| beta_mid | 0 – 25 | 3.009 | 12.0 | 3 | 20.333 | 81.3 | 24 | 10.021 |
| beta_bow | 2 – 50 | 37.683 | 74.3 | 21 | **48.412** | **96.7** | **25** | 24.837 |
| beta_len | 0.15 – 0.60 | 0.199 | 10.9 | 2 | 0.522 | 82.6 | 23 | 0.377 |
| roundness | 0 – 1 | 0.797 | 79.7 | 22 | 0.564 | 56.4 | 19 | 0.411 |
| rocker | 0 – 0.6 | 0.396 | 66.1 | 16 | 0.551 | 91.9 | 24 | 0.309 |
| forefoot | 0 – 1 | 0.239 | 23.9 | 8 | 0.110 | 11.0 | 2 | 0.381 |
| flare | −5 – 25 | 12.086 | 57.0 | 13 | 12.382 | 57.9 | 15 | 9.241 |
| sheer_rise | 0 – 0.5 | 0.460 | 92.0 | 22 | 0.447 | 89.3 | 20 | 0.320 |

**Reading.** The two failures are close to *opposites* on the shape genes that
matter most: h011 has the 3rd-lowest midship deadrise (3.0°), the 3rd-lowest
Cp (0.548) and the 2nd-shortest deadrise-warp length; h012 has the 2nd-highest
deadrise (20.3°), the 3rd-highest Cp (0.673) and the 3rd-longest warp. The only
genes on which both sit high are `sheer_rise` (ranks 22 and 20) and `roundness`
(22 and 19) — and hull 7 (`sheer_rise` 0.490, the population maximum) and
hulls 0 and 9 (`roundness` 0.995, the population maximum) all meshed cleanly.
No single gene, and no gene pair, isolates the two. §5 makes that quantitative.

---

## 2. SECTIONS AND CURVES — the section solve is clean on both

Measured at `FEASIBILITY_PROBE_STATIONS = 1921`, the densest grid the L0 gate
uses. `A = K·yc·(c1·d − c2·m·yc) + d²·f` is solved on the stable branch; the
three ways it can refuse are a negative discriminant, a negative `rhs`
(the flare enclosing more than the area curve asked for), and the `ys < 0`
tumblehome refusal.

| hull | meshed | min discriminant | min rhs | stations with `yc = 0` | stations with `ys = 0` | min `yc` (interior) | min `ys` (interior) | `section_probe` |
|---|---|---|---|---|---|---|---|---|
| 4 | yes | 0.003400 | 0 | 1 | 1 | 0.06900 | 0.06328 | ok |
| 5 | yes | 0.006249 | 0 | 1 | 1 | 0.05341 | 0.09997 | ok |
| **11** | **no** | **0.40066** | **0** | **1** | **1** | **0.10707** | **0.14036** | **ok** |
| **12** | **no** | **0.025079** | **0** | **1** | **1** | **0.12035** | **0.16041** | **ok** |
| 18 | yes | 0.61918 | 0 | 1 | 1 | 0.008483 | 0.011264 | ok |
| 21 | yes | 0.028940 | 0 | 1 | 1 | 0.19693 | 0.19331 | ok |
| … all 25 … | | ≥ 0.0034 | 0 | 1 | 1 | ≥ 0.0085 | ≥ 0.0113 | ok |

Every hull in the batch, including both failures:

* the discriminant is **strictly positive at every station** — h011's minimum
  margin (0.401) is 118× hull 4's (0.0034) and hull 4 meshed;
* `rhs ≥ 0` everywhere, touching 0 only at `x = LWL` where `a(x) = 0` by
  construction;
* the `yc ≥ 0` floor and the `ys ≥ 0` clamp bite at **exactly one station each —
  the stem, `x = LWL`** — for all 25 hulls identically. Neither floor bites in
  the interior of any hull. The documented "it bites only where a(x) → 0" is
  measured true here;
* `section_probe` passes at 1921 stations for all 25.

**Edge-curve monotonicity, crossings, and the chine.** Measured at 4001
stations:

* `max z_chine < 0` for all 25 — **the chine never reaches the design
  waterline** on any hull (h011 max −0.352 m, h012 max −0.0606 m);
* `y_sheer ≥ 0` everywhere; the sheer is never clipped in the interior;
* `y_sheer − y_chine` goes negative (tumblehome, the sheer inboard of the
  chine) on hulls **4, 15, 16, 21, 23** — **all five meshed**. Neither failure
  does it (h011 min +0.0332 m, h012 min +0.0399 m);
* half-breadth monotonicity: `y_chine` has 2 turning points on h011 and 2 on
  h012, against 1–2 across the whole population — identical structure;
* the chine sits inside the free-surface refinement band over 92.8 % of h011's
  length and 12.2 % of h012's — but over **100 %** of hulls 4, 5, 6, 8 and 23,
  all of which meshed.

**Nothing in the section solve or the edge curves refuses, clamps, crosses or
degenerates on h011/h012 that does not do the same on hulls that meshed.**

---

## 3. TESSELLATION AND STL — the surface handed to snappy is valid by construction

Emitted exactly as the campaign does: `stl_resolution(lwl, target_edge)` →
`nx = 600, nz = 120` for every hull (the [80, 600] clamp binds on all of them),
`wl = 0`, `trim = 0` (no manifest), 288 956 triangles.

### 3.1 Closure and winding — `case.stl_watertight_report` on the emitted files

```
h011  n_tris 288956  open_or_nonmanifold_edges 0  winding_conflicts 0  watertight True  outward True  signed_volume 74.4927
h012  n_tris 288956  open_or_nonmanifold_edges 0  winding_conflicts 0  watertight True  outward True  signed_volume 67.2166
```

**0 open edges, 0 non-manifold edges, 0 winding conflicts, outward.** There
are no inward-facing triangles in the STL. The 13 and 12 "wrongly oriented
faces" checkMesh reports are **volume-mesh** faces (negative face pyramids in
the cells snappy built), not triangles of the surface.

### 3.2 Folds and orientation, replicating `closed_mesh`'s own loop

Every shell quad `(S[i,j], S[i,j+1], S[i+1,j+1], S[i+1,j])` at 600×120, both
its triangles, all 25 hulls:

| quantity | h011 | h012 | population |
|---|---|---|---|
| folded quads (the two triangles' normals in opposite hemispheres) | **0** | **0** | **0 on all 25** |
| inward-facing quads (normal·(centroid − section axis) < 0) | **0** | **0** | **0 on all 25** |
| max quad twist (angle between the two triangles of one quad) | 50.00° | 44.78° | 10.4° … 84.9° |

h011 and h012 sit in the middle of the twist distribution; hulls 3 (84.9°),
21 (84.2°), 8 (81.8°) and 14 (80.1°) are far worse and meshed.

### 3.3 Self-intersection — measured, and provable

`stl_forensics.self_intersections` at 241×48 (`complete: True`, ~2·10⁶
candidate pairs each):

```
h011  n_self_intersecting_pairs 0   h012  0   h000  0   h024  0   h003  0
```

This is not luck; it is a property of the shape function. Along every section
the z-coordinate is **monotone non-decreasing** from keel to sheer: the bottom
leg rises at `+tan(beta)`, the fillet Bezier has z-control points
`(zc + ρ(zk − zc), zc, (1−ρ)zc)` which are non-decreasing for `zk ≤ zc ≤ 0`,
and the topside leg rises to `zs > zc`. Measured over all 25 hulls at 401
stations × 121 girth rows: **min Δz along a section = +0.000e+00 on every hull**
(never negative), and **min y in a section = +0.000e+00** (never negative).
Because sections lie at distinct x, the deck lid meets the shell only at
`z = z_sheer` (the unique z where the section reaches its top) and the caps are
planar at the two ends, the surface **cannot** self-intersect. That invariant
holds — for every hull, failures included.

### 3.4 Triangle shape, and where the worst ones live

Per-region worst facets (starboard shell + deck lid + transom cap + stem cap;
the port side is the mirror). "Region" is `closed_mesh`'s own loop:

| hull | meshed | worst aspect ratio | where | min angle | min area (m²) | where |
|---|---|---|---|---|---|---|
| **11** | **no** | **189.17** | transom cap, girth row 8 | **0.1847°** | 2.828e-05 | transom cap row 1 |
| **12** | **no** | **234.76** | transom cap, girth row 67 | **0.1418°** | 2.920e-05 | stem, i=598, row 0 |
| 24 | yes | **1107.54** | transom cap row 28 | **0.0304°** | 5.740e-06 | stem |
| 3 | yes | 543.94 | transom cap row 28 | 0.0619° | 1.886e-05 | stem |
| 8 | yes | 528.43 | transom cap row 18 | 0.0643° | 2.591e-06 | transom cap |
| 16 | yes | 464.94 | transom cap row 36 | 0.0721° | 4.520e-06 | stem |
| 13 | yes | 459.54 | bottom panel, x/L 0.9983, row 29 | 0.0720° | 1.649e-07 | stem |
| 15 | yes | 445.14 | transom cap row 32 | 0.0755° | 2.150e-05 | stem |
| 5 | yes | 398.70 | bottom panel, x/L 0.9983, row 16 | 0.0830° | 5.878e-07 | stem |

**The worst triangles in this population are not on the failures.** Hull 24's
worst facet is 5.9× more slivered than h011's and 4.7× more than h012's, its
minimum angle is 6× smaller, and it meshed with 0 wrongly-oriented faces and
skew 3.45. Degenerate/near-degenerate facets are dropped identically on every
hull by `closed_mesh`'s own `area > 1e-10` filter: over the starboard shell,
the deck lid and both caps, **145 196 of 145 438 triangles kept and 242
dropped — the same two numbers on all 25 hulls** (the port shell is the exact
mirror; the full STL is 288 956 triangles on every hull).

The worst facets live in the **transom cap** (17 of 25 hulls) or the **deck
lid strip** (6 of 25) or the **last bottom-panel column at the stem**
(2 of 25) — the three places where a flat cap is triangulated across a section
whose girth rows are unevenly spaced. That is a property of the emitter shared
by the whole population, not of h011/h012.

### 3.5 Longitudinal creases (`surfaceFeatureExtract`'s own bar)

`SURFACE_FEATURES` writes `includedAngle 150`, i.e. an edge is a feature when
the normal jump exceeds 30°. Longitudinal normal jumps at 600×120,
41 stations:

| hull | max jump | edges > 30° | | hull | max jump | edges > 30° |
|---|---|---|---|---|---|---|
| **11** | **30.283°** | **1** | | 3 | 45.014° | 25 |
| **12** | **23.558°** | **0** | | 21 | 44.484° | 18 |
| 0 | 8.627° | 0 | | 8 | 44.024° | 20 |
| 23 | 24.618° | 0 | | 10 | 42.348° | 38 |
| 13 | 28.421° | 0 | | 14 | 40.176° | 29 |

h011 has **one** phantom feature edge and h012 has **none**, against 43, 38, 29,
27, 25, 22, 20, 18, 18, 16 on hulls that meshed. The 41-station lerp crease is
therefore *emphatically* not what distinguishes them.

---

## 4. THE MESH — where the 13 faces and the skew 247 actually live

The recorded checkMesh receipts, sorted by non-orthogonality:

| hull | cells | layers achieved / 7 | wrong-oriented (set / pyramid check) | max skew | max non-ortho | failed checks |
|---|---|---|---|---|---|---|
| **12** | 637 964 | 5.73 | **12 / 12** | 9.946 | **98.332** | 3 |
| **11** | 527 105 | 5.73 | **13 / 13** | **247.226** | **90.488** | 3 |
| 14 | 606 598 | 6.46 | 0 / 0 | 2.641 | 74.999 | 0 |
| 9 | 819 674 | 5.71 | 0 / 0 | 6.662 | 74.946 | 1 |
| 2 | 622 439 | 5.89 | 0 / 0 | 2.745 | 74.941 | 0 |
| … 20 more … | | 3.79 – 6.92 | 0 / 0 | 1.93 – 11.97 | 65.9 – 74.6 | 0 – 1 |

Two things are visible and both point at the mesher, not the hull:

1. **The 23 passers pile up exactly against snappy's own quality ceilings** —
   18 of them land in 65.9–70.0 and 5 in 74.0–75.0, i.e. on the
   `maxNonOrtho` targets. The two failures are the only ones **outside** the
   controls (90.5 and 98.3). That is the signature of the quality loop failing
   to repair cells, not of a surface defect: a bad surface would show up in
   §3, and §3 is clean.
2. **The set count and the pyramid-check count agree** (13/13 and 12/12) on
   both failures — the two counts that `mesh_robustness.py` documents as
   routinely disagreeing (128 vs 92 on an earlier hull). A small, exactly
   agreeing count is a handful of cells, not a torn region.

Both failures achieved **5.73 of 7 layers — the same number to 2 dp** — which is
mid-population (3.79 … 6.92). The refusal is not a layer-coverage collapse.

`docs/research/LAYERS.md` and `docs/BUILD-PLAN.md` already record the
mechanism class for exactly this signature on the previous genome: hulls whose
admissible prism-layer set excludes the derived count and includes a lower one
("hull 12 meshes at n=6 and fails at 7, 8 and 10"). The campaign that produced
these two rows pinned `LAYER_BACKOFF=0` by design, so rung 0 is the *only*
rung either hull was offered.

---

## 5. THE INVARIANT — the systematic scan, and its verdict

83 descriptors were computed per hull and scored against the recorded mesh
outcome using the repository's own permutation instrument
(`stl_forensics.family_wise_p`, 20 000 permutations, 2 positives / 23
negatives). The family covers:

* all 16 genes;
* proportions `L/B`, `B/T`, `T/L`, `D/L`, `D/T`;
* placement against the pipeline's own bands: draft/z-core, deck/z-air,
  draft/free-surface box, chine fraction inside the FS box;
* cell-relative feature sizes: `cell/L`, `stack/cell`, `first_layer/cell`,
  girth/cell, min chine / min sheer / min topside / transom half-beam /
  transom immersion in cells;
* curvature: max |dy/dx| and |dz/dx| and max κ×cell and κ×stack on the keel,
  chine and sheer;
* section angles: chine included angle (min/max/transom), keel included angle;
* the bilge fillet: leg lengths in cells, leg-length ratio, min radius;
* all 14 `admissibility.screen` metrics;
* delivered form coefficients, `alpha_e`, `panel_twist_rate`, `fairness`,
  `min_bend_radius/cell`;
* `lwl` as a size control.

### 5.1 Result

```
family size            83
positives              2  (hulls 11, 12)
best metric            min_topside_panel_height_cells   (AUC 0.957)
best family-wise p     0.601
```

**No descriptor separates at any level of significance.** The single best
metric's family-wise p is 0.60; the next twelve are 0.67, 0.93, 0.96, 0.96,
0.96, 0.99, 0.99, 0.99, 0.99, 1.0, 1.0, 1.0.

### 5.2 The best candidate, scored honestly — and refused

`min_topside_panel_height_cells` = min over `x < 0.98·LWL` of
`(z_sheer(x) − z_chine(x)) / cell`. Full ordering (failures in brackets):

```
[12:23.88]  4:25.29  10:35.24  [11:40.88]  14:42.76  15:43.78  18:45.23
 1:45.38   2:45.96   7:46.52  23:52.08  22:57.20   5:59.47  16:67.15
 3:68.25  13:73.80  17:79.22   6:80.14  24:82.68   0:94.05  20:94.51
 9:95.50  21:96.04   8:99.45  19:101.14
```

The tightest single threshold that catches both failures is `≤ 40.8816`
cells — which is **h011's own value to 4 decimals**, the definition of a fitted
threshold — and it drags in hulls 4 and 10, which meshed:

| criterion | corpus | TP | FP | FN | TN |
|---|---|---|---|---|---|
| `min_topside_panel_height_cells ≤ 40.8816` | 25-hull mesh | 2 | **2** (h004, h010) | 0 | 21 |
| `min_topside_panel_height_cells ≤ 40.8816` | 18-row solve (hulls 0–17) | 2 | **2** (h004, h010) | 0 | 14 |
| current screen, rung-0 refusal predicted (DANGEROUS) | 25-hull mesh | 0 | 6 (h004,005,006,008,018,022) | 2 | 17 |
| current screen (as recorded in the solve JSON) | 18-row solve | 0 | 4 (h004,005,006,008) | 2 | 12 |

On raw counts the candidate beats the shipped screen (2/2/0 against 0/6/2).
**It is still refused, for three reasons and they are decisive:**

1. its family-wise p is **0.601** — over 83 looks, a metric this good is what
   chance produces;
2. the threshold is *h011's own value*. Nothing in the pipeline derives 40.88
   cells. The metric's own bar in `admissibility.py` is **1.0 cell** (a
   sub-cell feature), and the shipped hulls sit 24–101 cells above it — the
   metric has, correctly, "never fired". Moving a derived bar by a factor of 41
   to fit two points is precisely the move `docs/LESSONS.md` forbids;
3. `min_topside` is a **height**, and the two candidates it drags in (h004 at
   25.29 and h010 at 35.24 cells) bracket h011 (40.88) on both sides of the
   distribution. There is no mechanism under which a 41-cell-tall topside panel
   is unmeshable and a 25-cell one is fine.

Every other criterion on the shortlist is worse or equally fitted:

```
FN=0 FP=2   min_topside_panel_height_cells  <= 40.8816     (h011's own value)
FN=0 FP=3   beta_bow                        >= 37.683      (h011's own value)
FN=0 FP=4   sheer_rise                      >= 0.446666    (h012's own value)
FN=0 FP=5   D                               <= 2.11484     (h011's own value)
FN=0 FP=5   fairness                        <= 36.8285     (h011's own value)
FN=0 FP=5   roundness                       >= 0.564472    (h012's own value)
FN=0 FP=6   forefoot                        <= 0.238766    (h011's own value)
FN=0 FP=6   panel_twist_deg_per_m           >= 7.37669     (h012's own value)
```

Every one of them is a threshold pinned to one of the two failures' own
coordinates. **A criterion that does not separate is not a criterion, and this
document does not ship one.**

### 5.3 Mechanisms tested and eliminated by name

Each of these was a specific hypothesis with a mechanism, and each is refuted
by a hull that meshed:

| hypothesis | measurement | refuted by |
|---|---|---|
| the chine crease reaches the free surface / the z-refine transition | `max z_chine < 0` on all 25; chine inside the FS band over 92.8 % (h011) and 12.2 % (h012) of length | hulls 4, 5, 6, 8, 23: **100 %** of length inside the band, all meshed |
| the keel drops out of the uniform z-core band (`T > 0.09·LWL`) | h012 violates (T/L = 0.1047); h011 does not (0.0372) | 8 of the 9 violators meshed (h003 at 0.115, h013 at 0.169, h020 at 0.175) |
| the bilge fillet is sub-cell but STL-smooth (the pre-registered window) | `r_min/cell` = 2.669 (h011), 0.104 (h012) | h005 at 0.002, h004 at 0.012, h001 at 0.139 cells — all meshed |
| the fillet Bezier's control legs are pathologically lopsided | leg ratio 2.57 (h011), 25.18 (h012) | h004 at 39.16, h005 at 22.52 — meshed |
| the prism stack exceeds the local concave radius | `stack_over_min_radius` 0.037 (h011), 0.118 (h012), bar 1.0 | h021 at 0.150, h013 at 0.122 — meshed; nothing in the batch approaches the bar |
| the 41-station lerp makes a phantom knuckle over the 30° feature bar | 1 edge (h011), 0 edges (h012) | h001 43, h010 38, h014 29, h016 27, h003 25 edges — meshed |
| triangle slivers / aspect ratio | 189 and 235 | h024 at 1108, h003 at 544 — meshed |
| self-intersection | 0 pairs, and provably 0 (§3.3) | n/a — nobody in the batch has any |
| tumblehome (`y_sheer < y_chine`) | neither failure has it | h004, h015, h016, h021, h023 do — all meshed |
| a section-solve clamp or refusal | none in the interior of any hull | n/a |

---

## 6. Would the ~161-station `hull_to_stl` rebuild fix h011/h012? — **No.**

*(The change has since LANDED in the working tree: `hull_to_stl` now calls
`loft_hull(hull, _stl_loft_stations())` with `export._LOFT_STATIONS = 161`
before `closed_mesh`. Everything below was measured on that same rebuild.)*

Measured directly: the surface was rebuilt at `n_stations` = 41, 161 and 321
(same `nx=600, nz=120` triangulation) and the two quantities snappy reacts to —
the longitudinal normal jump and how many of those edges clear
`surfaceFeatureExtract`'s 30° bar — were recounted.

| hull | meshed | 41: max jump / n>30° | 161: max jump / n>30° | 321: max jump / n>30° |
|---|---|---|---|---|
| **11** | **no** | **30.283° / 1** | **27.272° / 0** | **26.807° / 0** |
| **12** | **no** | **23.558° / 0** | **22.558° / 0** | **22.427° / 0** |
| 1 | yes | 39.215° / 43 | 39.243° / 44 | 39.295° / 43 |
| 10 | yes | 42.348° / 38 | 42.324° / 38 | 42.264° / 37 |
| 18 | yes | 26.956° / **0** | 34.400° / **53** | 34.447° / **53** |
| 3 | yes | 45.014° / 25 | 45.217° / 26 | 45.166° / 25 |

Three findings:

1. **The dominant longitudinal normal jump is not the lerp crease.** Going from
   41 to 321 stations moves `max jump` by less than 1° on 22 of 25 hulls. The
   jump is set by the hull's own plan-form curvature near the stem, which more
   stations resolve rather than remove.
2. **For h012 the change is a null operation** — it already has zero
   over-bar edges at 41 stations. For h011 it removes exactly **one** 30.28°
   edge. Fifteen hulls that meshed carry between 2 and 43 such edges.
3. **The change is not monotonically an improvement.** Hull 18 goes from 0
   over-bar edges at 41 stations to **53** at 161 — refining the loft exposes
   real curvature that the coarse lerp was chording across. Anyone landing the
   161-station rebuild should expect the *feature-edge* population to move on
   hulls that currently mesh, and should re-measure Gate 2U rather than assume
   the rate can only go up.

**Verdict: the ~161-station rebuild would not fix h011 or h012.** It is a
legitimate change for the loft-error term documented in `stl_girth_resolution`
(`A(lerp(p)) ≤ lerp(A(p))`, worst 0.1869 %, does not converge in nz or nx), and
it should be justified on *that* ground. It repairs no defect these two hulls
have, because §3 measured that they have none.

Confirmed after the change landed: `hull_to_stl` through the 161-station loft
still reports h011 and h012 **watertight, outward, 0 open-or-non-manifold
edges, 0 winding conflicts** — the surface was never the problem and is not
the problem now.

**One consequence that must not be missed.** The rebuild changes the surface of
*every* hull, so **every `stl_sha256` in `data/gate2u-16gene-mesh.json` and
`data/gate2u-16gene-solve.json` is now stale by construction**, on top of being
unreproducible across machines (§0). Those two artefacts are the ledger's Gate
2U evidence. Whoever re-measures Gate 2U on the new loft should expect the
feature-edge population to move on hulls that currently mesh (hull 18: 0 → 53
over-bar edges) and should treat the recorded rates as describing a surface
that no longer exists — the exact defect class `mesh_robustness.py`'s
`stl_sha256` field was added to prevent.

---

## 7. What this investigation did establish

1. **The generated geometry IS valid by construction, and that is now
   measured rather than asserted.** Over all 25 hulls: 0 open edges, 0
   non-manifold edges, 0 winding conflicts, outward-wound, 0 folded quads, 0
   inward-facing quads, 0 self-intersecting pairs, z monotone along every
   section (so self-intersection is impossible, not merely absent), the section
   solve strictly feasible everywhere with its two floors biting only at the
   stem. The operator's preferred posture — "generated geometry should be valid
   by construction" — is **already true for this kernel**, and the two failures
   are not counter-examples to it.
2. **The failure is downstream of the surface.** The 13 and 12 wrongly-oriented
   faces are negative face pyramids in snappy's cells; the surface has none.
   The non-orthogonality signature (90.5, 98.3 against a population that piles
   up on the 70/75 quality ceilings) is a quality-loop failure at rung 0.
3. **The `stl_sha256` receipt is not a portable identity.** It changed with
   byte-identical code on a different machine, and the emitter is measurably
   fragile at the ~1e-12 relative level (§0). The receipt is still a
   perfect *same-machine* identity and must be kept; what it cannot do is what
   it is currently used for in cross-machine review — "the record cannot be
   checked against the code, in either direction" is the very defect
   `mesh_robustness.py`'s `stl_sha256` comment was written to close, and it is
   only half-closed.
4. **No admissible-region boundary is derivable from N=2.** Two positives
   cannot support a criterion over an 83-metric family; the best hit's
   family-wise p is 0.601. The measurement that would settle it is the one the
   campaign deliberately did not take: **the layer ladder on these two hulls.**
   If h011 and h012 mesh at n = 6 or 5 with 0 wrongly-oriented faces, the
   mechanism is the derived layer count and the fix is the ladder that is
   already canonical in `run-case.sh` — nothing in the generator changes. If
   they fail at every rung, the class is `no_admissible_rung` and *then* there
   is a geometry question worth another scan, with labels that can carry it.

### 7.1 The one change this evidence does justify — and it is not a bar

Not a grammar clause and not a screen criterion: a **receipt**. `case.info`
should carry a *portable* geometry identity beside the platform-dependent one,
so a hash mismatch can be read as "different machine" or "different loft"
instead of "different hull". `write_resistance_case` already hashes the genome
on the manifest path (`hashlib.sha256(np.asarray(hull.params, …))`); it is not
recorded for generated hulls. The diff belongs in `navalai/cfd/case.py`, which
this investigation may not edit, so it is stated here rather than applied:

```diff
--- a/navalai/cfd/case.py
+++ b/navalai/cfd/case.py
@@ write_resistance_case, in the existing `with (out / "case.info").open("a")` block
         fh.write(f"admissibility_verdict={_adm.verdict.name}\n")
         fh.write("admissibility_refused_by="
                  f"{','.join(_adm.refused_by) or 'none'}\n")
         fh.write("admissibility_no_rescue="
                  f"{','.join(_adm.refused_no_rescue) or 'none'}\n")
+        # THE PORTABLE HALF OF THE IDENTITY. `stl_sha256` above is a
+        # SAME-MACHINE receipt and nothing said so: MEASURED 2026-08-20
+        # (docs/audit/H011-H012-ROOT-CAUSE.md §0), regenerating campaign
+        # hulls 0/11/12 with a byte-identical emitter reproduced NONE of the
+        # recorded hashes on a different box. `_tris_to_ascii_stl` prints
+        # %.6e, and over h011's 3 467 472 printed numbers THIRTEEN sit within
+        # 1e-12 relative of a rounding boundary in the seventh digit — so a
+        # cross-platform arithmetic difference at 1e-12 rewrites the file
+        # while moving no geometry. A reader comparing hashes across machines
+        # cannot tell "different box" from "different hull", which is the
+        # defect `stl_sha256` was added to close, half-closed.
+        #
+        # The genome IS portable: numpy's Generator is bit-reproducible, so
+        # the same seed gives the same vector everywhere, and the loft count
+        # names the surface the vector was turned into. Recorded BESIDE the
+        # file hash, never instead of it — `benchmark_of_sha` matches the
+        # file hash against CHECKSUMS.json and must keep meaning that.
+        fh.write("genome_sha256="
+                 f"{hashlib.sha256(np.asarray(hull.params, dtype=float).tobytes()).hexdigest()}\n")
+        fh.write(f"genome_n_params={len(np.asarray(hull.params))}\n")
+        fh.write(f"stl_loft_stations={_stations}\n")
+        fh.write("  # genome_sha256 + stl_loft_stations + stl_nx/nz identify\n"
+                 "  # the surface ACROSS machines; stl_sha256 identifies the\n"
+                 "  # bytes on THIS one. A mismatch in the first is a\n"
+                 "  # different hull; a mismatch in only the second is a\n"
+                 "  # different box or a different emitter build.\n")
```

`mesh_robustness.py` should carry the same field up into its rows beside
`stl_sha256` (`_case_stl_sha`'s sibling, same `UNRECORDED` sentinel
discipline), so a campaign artefact can be checked against the code that
produced it from a different machine.

---

## 8. Honest uncertainty

* **I could not reproduce the recorded `stl_sha256` for any of the three hulls
  I tested (0, 11, 12).** The evidence that this is a platform effect and not a
  different hull is strong (identical genome, byte-identical emitter, quantified
  hash fragility) but it is *inference*, not proof: it cannot be closed without
  re-running one hull on the Mac. If the Mac reproduces its own hashes and this
  box does not, the inference is confirmed; if the Mac no longer reproduces
  them either, something did change and every conclusion here needs re-checking
  against the surface the campaign actually meshed.
* **All the mesh-side reasoning in §4 is read off recorded checkMesh scalars.**
  No mesh was built for this investigation (no OpenFOAM on this box), so
  "snappy's quality loop failed to repair these cells" is the reading most
  consistent with the numbers, not a measurement. The `wrongOrientedFaces`
  cell set would settle it in one look.
* **N = 2.** Every negative result in §5 is a statement about a 25-hull corpus
  with two positives. A descriptor that separates could exist and be invisible
  at this sample size. What is *not* uncertain is that none of the 83 tried
  does, and that promoting any of them on this evidence would be fitting.
* **The scan is over descriptors I chose.** It is broad (genes, ratios,
  cell-relative sizes, curvature, section angles, fillet geometry, the whole
  screen, delivered coefficients) but it is not exhaustive, and it contains no
  descriptor of the *volume* mesh, which is where §4 locates the difference.

---

## 9. Reproducing this document

Pinned tree: `git archive 168ea82 | tar -x -C <dir>` (read-only; concurrent
working-tree edits do not affect it). Population:
`sample_valid(25, MissionSpec(), seed=0)`. Triangulation: `stl_resolution` →
600 × 120 at scale 1.0. The permanent regression that pins the proved half is
`tests/test_h011_h012_invariant.py`.
