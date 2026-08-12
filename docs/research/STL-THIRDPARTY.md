# STL-THIRDPARTY — the exported hulls, judged by libraries that are not ours

**Measured 2026-08-12** on the 25 STLs exported to `~/Documents/naval-ai-stl`,
verified **25/25 sha256-identical** to `hull_to_stl(Hull(sample_valid(25,
MissionSpec(), seed=0)[0][i]))` regenerated from **ref `1059c79`** — the
geometry the gate-2U cap-7 campaign meshed.

**That export directory was DELETED partway through this session, by something
other than this analysis.** Every number below was re-derived afterwards from a
freshly regenerated set and reproduces exactly, which is the only reason the
document stands: an artefact outside the repository that nobody can rebuild is
gap N6's shape (prose citing a run directory `clean-runs.sh --purge` had
removed). Reproduce, rebuilding the STLs from the ref if they are absent:

    source ~/.venvs/naval/bin/activate
    python scripts/stl_thirdparty_check.py \
        --stl-dir /tmp/stl_regen --regen-ref 1059c79 --profile 4,14,8

`--regen-ref` regenerates from a GIT REF, never from the working tree: while
this was measured a concurrent agent held an uncommitted change to
`Hull.closed_mesh`, and the working-tree identity check flipped from 25/25 to
0/25 mid-session because of it.

This document records what THIRD-PARTY tools say. `docs/research/STL.md` is the
other half — our own metrics, written concurrently and independently. Neither
restates the other's numbers.

**Libraries, as installed into `~/.venvs/naval` for this work** (nothing was
already present; `pip install trimesh networkx rtree pymeshlab open3d` pulled
these plus their transitive dependencies, and no pre-existing package version
changed):

| library | version |
|---|---|
| trimesh | 5.0.0 |
| PyMeshLab | 2025.7.post1 |
| Open3D | 0.19.0 |
| scipy | 1.18.0 (already present) |

---

## 0. THE SHORT VERSION

1. **There are no self-intersections.** Not one, on any of the 25 hulls.
   Open3D reports 30 pairs across 10 hulls; PyMeshLab reports zero; the
   disagreement was settled by measuring the true triangle-triangle distance of
   every reported pair, and they are **116–233 mm apart**. Open3D's predicate
   false-positives on near-coplanar facet pairs, which is exactly what a
   near-developable flat panel is made of. **The self-intersection hypothesis
   for "odd corners" is REFUTED.**
2. **Nor is there any other topological defect.** Three independent
   implementations agree with ours: watertight, edge- and vertex-manifold,
   consistently wound, one component, genus 0, Euler characteristic 2, zero
   duplicate faces, zero unreferenced vertices, zero degenerate faces. Volumes
   agree with our `signed_volume` to **0.0000%** on all 25.
3. **What the owner is seeing at the bow is REAL GEOMETRY, faithfully
   triangulated.** The stem taper `y_sheer = ys·w**0.15` has a vertical tangent
   at `w → 0`, so the hull genuinely opens to **0.2–23.0 CFD cells of
   half-breadth within ONE mesh cell of the stem** (median 6.46), an entrance
   half-angle at the sheer of up to **83.6°** (median 68.4°), and a
   facet-to-facet fold of **115°–179°** in the last 2% of LWL against
   **1.6°–48.6°** at midship. The STL is not adding a corner. The hull has one.
4. **A second, separate defect: the sheer clamp.** `np.maximum(ys, 0.0)` in
   `station_geometry` puts the DECK EDGE ON THE CENTRELINE wherever negative
   flare drives the raw sheer half-breadth below zero. It fires on 4 of 25
   hulls, and on **hull 23 over 21.5% of the length** — including an 18.1%
   stretch of the AFTER body that has nothing to do with the bow.
5. **No third-party metric separates the meshing failures.** Best AUC 0.847
   (`slivers_lt5deg`), raw p = 0.0050, **Holm-adjusted p = 0.24 over a family of
   48** — not significant, and consistent with the 0.842 / p = 0.21 already on
   record for 29 of our own metrics. **Said plainly: this is a null result.**
6. **But a null result here does not exculpate the taper**, and §5 explains why
   at length: the taper is in EVERY hull the grammar emits, so it has no
   contrast group and scores at chance by construction. It has to be tested by
   INTERVENTION. §6 costs that intervention.

---

## 1. THE BOW — reported first, because that is where the owner says it is

### 1.1 The stem is a vertical tangent, and the mesh is telling the truth

`station_geometry` closes the topside with

    y_sheer = max(ys, 0) * max(w, 0) ** 0.15

whose derivative in `w` is `0.15·w**-0.85` — **unbounded as breadth goes to
zero**. `w` itself vanishes linearly at `x = L`, so `dy_sheer/dx → ∞` at the
stem. The consequence is not subtle and it is not a triangulation artefact:

| hull | LWL m | dx_mesh m | y_sheer one cell aft of stem | in CFD hull cells | entrance half-angle at the sheer | as a fraction of y_sheer at 0.85 L |
|---:|---:|---:|---:|---:|---:|---:|
| **4** | 8.942 | 0.113 | **1.016 m** | **23.03** | **83.64°** | 0.490 |
| **14** | 11.670 | 0.148 | 0.467 m | 8.11 | 72.45° | 0.263 |
| **8** | 12.320 | 0.156 | 0.161 m | 2.65 | 45.89° | 0.165 |
| median of 25 | — | — | — | **6.46** | **68.4°** | 0.298 |
| range of 25 | — | — | — | 0.00 – 23.03 | 0.00° – 83.64° | 0.000 – 0.527 |

The zero ends of both ranges are hull 23, whose sheer is clamped to the
centreline at the stem (§4) — a different defect, not a gentle bow.

Hull 4 opens to just over a metre of half-breadth in 113 mm of length. That is
a **blunt bow**, and an 83.6° entrance half-angle at the sheer is what "very odd
corner" looks like to the eye in a slicer. The surface is doing what the
equation says.

**The absolute-vs-relative question, settled.** The hypothesis that "all three
hulls carry 5244 triangles despite volumes spanning 24.3–72.8 m³, so the larger
hulls have a proportionally coarser stem" is **refuted by construction**:
`hull_to_stl` samples `nx = 80` points over `[0, LWL]` and the CFD hull cell is
`4.5·LWL / _NX_BASE / 2**4`, so BOTH scale linearly with LWL and their ratio is
**`dx_mesh / hull_cell = 2.565` on every one of the 25 hulls, to three
decimals.** Bow resolution relative to the mesh is scale-invariant. What varies
between hulls is the SHAPE — `p_bow` above all — not the sampling.

### 1.2 The fold, localised

Adjacent-normal (dihedral) angle, measured **across transverse edges only** —
the chine, keel and deck edge are designed hard edges carrying 85–115° at every
station, and including them buries the signal (the first version of this
analysis did include them, and its "spike extent" threshold came out at 330°, a
bar nothing bounded by 180° can cross):

| hull | max fold in last 2% LWL | max fold at midship (0.40–0.60) | ratio | spike extent (% LWL, above 2× its own midship max) |
|---:|---:|---:|---:|---:|
| 4 | 130.4° | 4.2° | 30.9× | 8.0% |
| 14 | 138.3° | 48.6° | 2.8× | 2.0% |
| 8 | 150.0° | 21.5° | 7.0× | 2.0% |
| range of 25 | 115.3° – 179.0° | 1.6° – 48.6° | 2.8× – 72.7× | 2.0% – 36.0% |

**Every hull folds by more than 115° at the stem.** The spike is confined to the
last 2–8% of LWL on 22 of 25 (hull 5 reaches 36%, hulls 13 and 17 reach 14%).
Note that hull 8 — which meshes and solves — folds *harder* at the stem than
hull 4, which fails at every layer count. **The stem fold is universal; it does
not discriminate.** That is §5's whole point.

Hull 4's profile is a clean monotone ramp into the stem — 2.1° at u = 0.40,
7.6° at 0.78, 20.0° at 0.88, 28.2° at 0.96, **130.4° at 0.98–1.00**. Hull 14 is
noisier, with a second disturbed region at u = 0.58–0.78 (43–49°) that hull 4
does not have.

### 1.3 How far the facets sit from the hull the grammar DEFINES

Two errors compound, and they are different in kind:

- **E1 — the 41-station polyline against the analytic closed form.** `Hull`
  evaluates `station_geometry` at 41 stations and `_section_at` interpolates
  LINEARLY between them, so the surface the mesher sees is already piecewise
  linear at 41 knots. `edge_curves`' own docstring records a cubic spline being
  94.95 mm off on the sheer for this reason; the LINEAR interpolant the mesh
  actually uses is worse.
- **E2 — the 80 mesh samples against that polyline.** `nx = 80` over 40 station
  intervals: `j·40 = i·79` has no solution but the endpoints, so **not one of
  the 39 interior station knots is landed on**. Every kink is straddled and cut.

| hull | E1 sheer max | at u | E2 sheer max | at u | E1/cell | outcome |
|---:|---:|---:|---:|---:|---:|---|
| **4** | **636.5 mm** | 0.997 | 11.5 mm | 0.975 | **14.43** | fails every count |
| 19 | 480.7 mm | 0.997 | 14.7 mm | 0.475 | 8.14 | meshes |
| 16 | 470.6 mm | 0.997 | 13.2 mm | 0.425 | 7.83 | meshes |
| **14** | 241.1 mm | 0.997 | 6.8 mm | 0.550 | 4.19 | fails every count |
| **8** | 69.1 mm | 0.998 | 16.3 mm | 0.600 | 1.14 | meshes and solves |
| 23 | 115.8 mm | **0.430** | **57.0 mm** | 0.425 | 1.27 | meshes |

E1 peaks at **u = 0.989–0.998 on 23 of 25 hulls** — i.e. at the stem, and it is
the `w**0.15` taper being sampled by a uniform x-grid that cannot follow it.
**Hull 4's bow is up to 636 mm — 14.4 CFD hull cells — narrower in the STL than
in the hull the grammar defines.** Hull 4 ranks 1st of 25 on this. Hull 14
ranks 12th; hull 8 ranks 22nd.

E2 is a separate, smaller effect (2.7–57 mm) that peaks at **midbody**, which is
the resampling misalignment above. On hull 10 it reaches 56.5 mm against a
79.9 mm hull cell — comparable to the cell, which is enough to matter.

### 1.4 What is at the odd x-positions on hulls 4 and 14, in metres

**Hull 4** — LWL 8.942 m, `x_mb` 0.451, `p_bow` 3.986 (highest of the 25),
flare +23.75°:

| x (m) | u | what is there |
|---:|---:|---|
| 0.00 | 0.00 | transom cap — a 90° edge by design |
| 4.03 | 0.451 | **x_mb**: plan-form equation switch, dy/dx jumps **7.84°** (chine) / 9.21° (sheer). Dihedral rises only 2.2° → 4.2° here — a real crease, but a mild one on this hull |
| 4.53 | 0.507 | deadrise warp toward the bow begins (C1-continuous; no dihedral response) |
| 6.26 | 0.70 | forefoot keel rise begins (C1-continuous; no dihedral response) |
| 7.33–8.05 | 0.82–0.90 | fold climbs 9.2° → 20.0° — the flare and the taper compounding |
| **8.83–8.94** | **0.98–1.00** | **THE STEM.** 130.4° fold, 1.016 m of half-breadth in 113 mm, 83.64° entrance half-angle, 636 mm of E1 deviation, 1 sliver below 5° |

**Hull 14** — LWL 11.670 m, `x_mb` 0.539, `p_bow` 3.741 (3rd highest), flare
+18.02°:

| x (m) | u | what is there |
|---:|---:|---|
| 5.42 | 0.464 | deadrise warp begins |
| 6.29 | 0.539 | **x_mb**: dy/dx jumps **16.22°** (chine) / 19.07° (sheer); dihedral 2.9° |
| 6.77–9.10 | 0.58–0.78 | **a disturbed midbody band hull 4 does not have** — folds of 48.6°, 43.2°, 30.8°, alternating with 11–16°. This is the flare/deadrise-warp interaction across the chine, not the taper |
| 8.17 | 0.70 | forefoot keel rise begins |
| **11.44–11.67** | **0.98–1.00** | **THE STEM.** 138.3° fold, 0.467 m in 148 mm, 72.45° half-angle, 241 mm of E1 deviation |

**The x_mb crease is real but it is not what distinguishes these two hulls.**
It ranges 3.9°–52.8° across the batch, and hulls 4 (7.84°) and 14 (16.22°) rank
**22nd and 19th of 25** — *milder* than hull 8's 34.51°, which meshes and
solves. Whatever is wrong with 4 and 14, x_mb is not it.

---

## 2. THE SELF-INTERSECTION COUNT — the headline, and it is zero

Nothing in this repository tests self-intersection. `stl_watertight_report`
tests edge closure, directed-edge winding and the signed volume, and a surface
can pass all three while intersecting itself. So this was the question worth
asking, and the answer is a clean negative:

| | reported | confirmed |
|---|---:|---:|
| Open3D `get_self_intersecting_triangles` | 30 pairs on 10 hulls | — |
| PyMeshLab `compute_selection_by_self_intersections_per_face` | 0 faces on 25 hulls | — |
| **true triangle-triangle distance, every reported pair** | — | **0** |

The two libraries disagreed, so the disagreement was **adjudicated by
measurement** rather than by preferring one: minimum distance between the two
triangles as a convex QP in barycentric coordinates. Every one of the 30 pairs
is **116–233 mm apart** (median 164 mm). They are pairs of near-coplanar
facets — normal offsets of 1e-8 to 1e-7 m, i.e. `%.6e` ASCII rounding — lying
on the same flat hull panel, 15–23 cm from each other. Open3D flags them; they
cannot possibly intersect.

**This is a false positive caused by the design succeeding.** The grammar emits
"a pair of near-developable ruled panels per side"; consecutive facets on a
developable panel are coplanar; Open3D's triangle-triangle predicate mishandles
the coplanar case. **Do not add Open3D's self-intersection count to any gate.**
PyMeshLab's answer is the correct one and it is zero.

Note also that Open3D's `is_watertight()` reads **False on 10 hulls** in the
table — that is downstream of the same false positive (`is_watertight` = edge
manifold ∧ vertex manifold ∧ **not self-intersecting**). Its edge- and
vertex-manifold predicates read True on all 25.

**Open3D must be handed a vertex-merged mesh or every number is wrong.**
`hull_to_stl` writes one vertex record per triangle corner — 15732 records for
5244 triangles — and before `remove_duplicated_vertices()` Open3D reports
25852 self-intersecting pairs on hull 4 and `is_watertight` False on all 25.
Merging coincident vertices moves no geometry and is not a repair; it is what
every consumer does. (trimesh's `process=True` does it on load; all three
libraries land on exactly **2624 vertices**, which is the structured grid
`80×17` per side less the 96 points shared on the centreplane — the topology is
exactly what `closed_mesh` builds.)

---

## 3. EVERY OTHER TOPOLOGICAL CHECK AGREES WITH OURS

Identical on all 25 hulls, from all four implementations:

| check | value |
|---|---|
| watertight (ours / trimesh / PyMeshLab) | True |
| winding consistent (trimesh) | True |
| `is_volume` (trimesh) | True |
| Euler characteristic | 2 |
| connected components | 1 |
| genus | 0 |
| non-two-manifold edges / vertices (PyMeshLab, Open3D) | 0 / 0 |
| boundary edges, holes | 0, 0 |
| duplicate faces | 0 |
| unreferenced vertices | 0 |
| degenerate faces (area < 1e-10) | 0 |
| **volume, ours vs trimesh** | **0.0000% apart on all 25** |

Two independent implementations of the divergence-theorem volume agreeing to
five decimals is a genuine cross-check of `stl_watertight_report`, and it
passes. **Our checker is correct about everything it checks. It simply does not
check enough** — and the things it does not check turn out, this time, to be
clean too.

Triangle quality is unremarkable in aggregate: minimum angle 0.35°–4.45°,
50–425 triangles below 5° per hull (1–8% of 5244), aspect ratio R/2r median
1.21–1.63 with a p99 of 6.3–21.0. Hull 23 is the outlier — 5214 triangles
rather than 5244 (30 dropped by `closed_mesh`'s own 1e-10 area filter), a
0.354° minimum angle and a 179.0° fold — and §4 says why.

---

## 4. THE SHEER CLAMP — a second defect, and it is not at the bow

    y_sheer = np.maximum(ys, 0.0) * ...          # station_geometry, line 68
    ys = y_chine + (z_sheer - z_chine) * tan(flare)

`flare` may be **negative** (tumblehome). When the tumblehome over the freeboard
exceeds the chine half-breadth, the raw `ys` goes negative and the clamp puts
**the deck edge on the centreline**: the topsides fold together and the deck lid
has zero width. The result is still closed, still manifold, still correctly
wound — and folded. Every check in §3 passes on it.

| hull | flare | clamped over | where |
|---:|---:|---:|---|
| 5 | −2.79° | 0.7% of LWL | u 0.993–1.000 (the stem point only) |
| 11 | −2.46° | 0.5% of LWL | u 0.995–1.000 (stem only) |
| 12 | −4.72° | 1.1% of LWL | u 0.989–1.000 (stem only) |
| **23** | **−3.07°** | **21.5% of LWL** | **u 0.000–0.180 (x 0.00–3.38 m, the AFTER body) and u 0.966–1.000 (x 18.07–18.70 m)** |

Hull 23 is the one to look at in the slicer. Over the aftmost 3.38 m of an
18.70 m boat the deck edge is pinned to the centreline while the chine is not,
so the topside is a wedge closing onto the centreplane — with a raw `ys`
reaching −0.036 m there and −0.177 m forward. This is where hull 23's 0.354°
minimum angle, its 179.0° fold and its 30 dropped triangles come from, and why
its E1 peaks at **u = 0.430** rather than at the stem.

It is worth being explicit: **on hull 23 the largest surface anomaly is in the
after body, not the bow.** If the owner's "odd surfaces" include anything aft,
this is the mechanism.

---

## 5. DOES ANY OF IT SEPARATE THE FAILURES? NO — and here is what that means

Scored against three labels from `data/gate2u-cap7-mesh.json` and
`data/gate2u-campaign-backoff-mesh.json`, AUC with an **exact** two-sided
Mann-Whitney p (the normal approximation is not usable at these counts) and
**Holm-Bonferroni** correction over the whole metric family:

| label | positives | best metric | AUC | p raw | p Holm | verdict |
|---|---|---|---:|---:|---:|---|
| cap-7 runner bar (wo≤5, skew≤20, zeroVol=0) | 6 / 25 — hulls 4, 5, 10, 12, 14, 18 | `aspect_max` | 0.798 | 0.030 | 1.000 | **none significant** |
| cap-7 strict `meshed` | 9 / 25 | `slivers_lt5deg` | **0.847** | **0.0050** | **0.242** | **none significant** |
| backoff: fails at EVERY layer count | 2 / 16 — hulls 4, 14 | `p_bow` | **0.964** | 0.033 | 1.000 | **none significant**, and underpowered — see below |

Family size 48 metrics. Runners-up on the strict label: `min_angle_p01`
(AUC 0.812), `aspect_p99` (0.799), `aspect_max` (0.792) — all raw p < 0.02, all
Holm > 0.45.

**The best third-party result, AUC 0.847 at Holm p = 0.24, is the same answer
already on record for 29 of our own geometry metrics (best AUC 0.842, p = 0.21).
Two independent metric families, two null results. Say it plainly: the STL does
not predict which hulls fail to mesh.**

**On the {4, 14} label the study cannot succeed even in principle.** With 2
positives in 16, the smallest two-sided exact p a PERFECT separator can reach is
`2 / C(16,2) = 0.0167`, and after correction over any family larger than 3
metrics that is not significant. `p_bow` at AUC 0.964 (hulls 4 and 14 rank 1st
and 3rd of 25) is the most suggestive number in this document and it is
**uncorroborable at this sample size**. It is a hypothesis to test, not a
finding. The script prints this ceiling before the ranking so a reader cannot
mistake *underpowered* for *refuted*.

### 5.1 Why the null result does NOT exculpate the taper

An earlier analysis scored the stem-taper defect at AUC 0.500 and it was
reported as refuted. **That reading was wrong, and this document is on record
correcting it**, because the same analysis said why it scored at chance: the
defect is *"a property of the grammar, in EVERY hull it emits"*.

A defect present in all 25 hulls is **invisible to correlation by
construction**. There is no contrast group. AUC 0.500 means "does not separate
failures from passes"; it does not and cannot mean "harmless". A universal
defect can raise the failure rate on every hull and still score exactly at
chance. §1.2 measures precisely this shape: the stem fold exceeds 115° on all 25
hulls, and hull 8 — which meshes and solves cleanly — folds *harder* (150.0°)
than hull 4, which fails at every layer count (130.4°).

The correct inference from §5 is therefore **not** "the geometry is fine". It is
**"correlation over 25 samples cannot answer this question, and an intervention
can."**

---

## 6. THE INTERVENTION, AND WHAT IT COSTS

The experiment a universal defect requires: **replace the taper, regenerate the
SAME 25 genomes, re-mesh with NOTHING ELSE CHANGED, compare against today's
16/25 (strict) and 19/25 (runner bar).** Correlation cannot test it; only this
can.

A geometry change that improves meshing while moving the hydrostatics is a
different boat, not a fix — so the deltas were computed first, with the
PRODUCTION integrator (`hydrostatics.solve` on a Hull whose `y_sheer` array is
substituted in place; nothing is reimplemented, so this cannot drift from the
real hydrostatics).

**The obvious candidates are NOT local, and that is the first result.**
`w**0.15` is applied over the WHOLE length, not just at the stem — at `w = 0.5`
it is already 0.90 and at `w = 0.3` it is 0.83, so the taper narrows the sheer
by 10–17% along most of the hull. Replacing the envelope wholesale therefore
changes the whole boat:

| candidate | max │ΔV│ | max │ΔS_wetted│ | max │ΔLCB│ | max │ΔA_wp│ | max │ΔSAC│ |
|---|---:|---:|---:|---:|---:|
| smoothstep `3w²−2w³` | **12.66%** | 2.31% | **2.55 %LWL** | **22.02%** | 12.93% of A_max |
| cosine `½(1−cos πw)` | **12.60%** | 2.27% | **2.57 %LWL** | **21.94%** | 13.10% of A_max |
| **blend: `w**0.15` where w ≥ 0.25, straightened below** | **2.93%** | **0.50%** | **1.19 %LWL** | **5.22%** | **6.14% of A_max** |

A 12.7% displacement change and a 22% waterplane change are not a fix; they are
a redesign, and every L1 result in the ledger would be invalidated. The **blend**
keeps `w**0.15` exactly wherever `w ≥ 0.25` and straightens only below it, so the
derivative is bounded by `0.25**0.15 / 0.25 = 3.27` instead of unbounded, and the
geometry change is confined to the few percent of LWL where the taper was
actually pathological. Its median disturbance across the 25 hulls is
**│ΔV│ < 0.06%** — 18 of 25 hulls move by less than 0.1% of displacement — with
a worst case of 2.93% on hull 15.

**Recommended experiment, in order:**

1. Change the taper in `station_geometry` in **ONE** place (it is already the
   single definition — `edge_curves` and `__post_init__` both route through it,
   and the docstring says so). Use the blend, not smoothstep.
2. Regenerate the same 25 genomes and re-run `stl_thirdparty_check.py`. The
   prediction is falsifiable and specific: `stem_halfangle_1dx_deg` drops from a
   median of 68.4° to below 30°, `y1dx_over_cell` from a median 6.46 to below
   2, `E1_sheer_max_mm` on hull 4 from 636 mm to under 100 mm, and the last-2%
   fold from 115–179° to under 90°.
3. Re-mesh at the shipped configuration with nothing else changed and compare
   16/25 and 19/25. **State the hydrostatic deltas of §6 alongside the meshing
   rate**, because a rate that improves while the boat moves is two results, not
   one.
4. If the rate does not move, the taper is exonerated *as a meshing cause* by an
   experiment that could have convicted it — which is worth as much as a fix,
   and is the outcome this document expects a reader to be prepared for.

**Independently of the taper**, the sheer clamp of §4 should be made an
admissibility refusal rather than a silent `np.maximum`. A hull whose deck edge
lands on the centreline over 21.5% of its length is not a boat, and nothing
currently notices.

---

## 7. WHAT I COULD NOT VERIFY

- **That any of this causes the meshing failures.** §5 is a null result. The
  strongest signal, `p_bow` at AUC 0.964 on {4, 14}, is uncorroborable at n = 16
  and is a hypothesis for §6, not a finding.
- **What the owner actually saw on screen.** §1 and §4 locate the geometry that
  *would* read as "odd corners and surfaces", but no one has pointed at the same
  pixel twice. The specific claim worth confirming with him is hull 4's stem
  (83.6° entrance half-angle at the sheer) and hull 23's after body
  (x 0.00–3.38 m, deck edge on the centreline).
- **Whether E2's midbody resampling misalignment matters.** It is real —
  `nx = 80` lands on none of the 39 interior station knots — and 2.7–57 mm, but
  no failure has been traced to it. Setting `nx = 81` (or any nx with
  `(nx−1) % 40 == 0`) would land every knot exactly and cost nothing; that is a
  cheap, separate experiment, and it has NOT been run.
- **PyMeshLab's version string.** The module exposes no `__version__`; pip
  reports `2025.7.post1`. The script prints "installed" rather than inventing a
  number.
- **Anything about the working tree's current `closed_mesh`.** A concurrent
  agent held an uncommitted change to it (the chine as a grid row) while this
  was measured. **Every number here is at ref `1059c79`**, which is the geometry
  the cap-7 campaign meshed and the geometry the 25 STLs reproduce from. After
  that change lands, re-run the script: the triangulation changes, and §1.2,
  §1.3 and §3 must be re-measured before they are quoted again.
- **Nothing was repaired, and no repaired STL was produced.** No repairer was
  run even as a demonstration, because there was nothing to repair: zero
  self-intersections, zero non-manifold edges, zero holes, zero degenerate
  faces. Had there been, the rule stands — a repair is measured as a delta
  (volume, wetted area, max surface deviation) and reported, never adopted.
