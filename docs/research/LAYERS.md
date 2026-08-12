# LAYERS — is the prism-layer count a per-hull quantity, and can it be derived?

**Measured 2026-08-12. Investigation only; no code, test or data file was
changed by the pass that wrote this.** Everything below is computed from
`data/gate2u-cap3-mesh.json`, `data/gate2u-cap5-mesh.json`,
`data/gate2u-cap7-mesh.json`, `data/gate2u-campaign-baseline.json` and
`data/gate2u-campaign-backoff-mesh.json`, plus `navalai.admissibility.screen()`
and `navalai.cfd.case.layer_spec()` re-run on the same genomes
(`sample_valid(25, MissionSpec(), seed=0)`, speed 2.57 m/s, scale 1.0, LTS,
full-width domain). Hull LWLs reproduce the campaign rows' `lwl` field to
3 decimal places, so the genomes are the same hulls.

**Configuration, said out loud (docs/LESSONS.md defect class 6):** every mesh
result quoted here is **coarse, scale 1.0, non-symmetric, mesh-only**, judged by
the bars `run-case.sh` enforces — **0 zero-volume cells, ≤5 wrongly-oriented
faces, 0 ≤ max skewness ≤ 20**. That is called the **runner bar** below. The
campaign JSON also carries a stricter `meshed` flag (0 zero-volume AND 0
wrongly-oriented); where the two disagree it is stated. Nothing here is about
the solve.

---

## 0 · The question, and the answer in four lines

The project owner asked: a fixed `_MAX_LAYERS` (3, then 10, now 7) cannot fit
every hull; the 25 test hulls differ in size and shape and are being judged with
one ruler — should the layer count be derived per hull from its own geometry?

1. **The diagnosis is right, and stronger than stated.** There is no single
   layer count that meshes this batch. Hull 10 meshes at n=8 and fails at 7 and
   10; hull 12 meshes at n=6 and fails at 7, 8 and 10. Their admissible sets are
   **disjoint**, so no common ruler exists inside the counts actually tested.
2. **The proposed remedy — derive n from the hull's geometry — is refuted by
   the same data.** For a FIXED hull the mesh outcome is not monotone in n, and
   it is not even unimodal: three of the twelve hulls tested at three or more
   counts have a **hole** in the middle of their admissible set (hull 3 fails at
   5 between passes at 3 and 7; hull 5 fails at 7 between passes at 5 and 8;
   hull 8 fails at 6 between passes at 4 and 7). A rule that emits one number
   per hull cannot reproduce a map that oscillates in its own argument.
3. **Nothing measured here separates the hulls that fail from the ones that
   pass.** Twenty-nine geometric quantities were tested. The best,
   `transom_half_beam_cells`, reaches AUC 0.842 against the runner bar and does
   **not** survive correction for having looked at 31 of them
   (family-wise permutation p = 0.21).
4. **So the count is per-hull, and it must be MEASURED per hull, not derived.**
   The correct object is a **dense two-sided search** with the rung recorded as
   part of the result — not a formula, and not a cap. Specification in §7.

---

## 1 · The 25 hulls, size and shape, with what the pipeline derives for each

`hull_cell` is the level-`_HULL_REFINE[1]` cell the surface actually snaps to
(`admissibility._pipeline_scales`); `t1` is `first_layer_thickness(2.57, LWL,
100)`; `stack` is the n=7 prism stack; `n_ideal` is `n_layers_to_bridge` BEFORE
`_MAX_LAYERS` clips it. `cap7` is the verdict at the shipped configuration.

|  h | LWL m | BWL m | T m | B/T | β_mid | β_bow | β_len | x_mb | p_bow | p_stern | r_tr | flare | rocker | forefoot | sheer | cell mm | t1 mm | stack mm | n_ideal | cap7 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--|
|  0 | 15.02 | 3.07 | 0.376 |  8.16 | 13.1 | 16.9 | 0.33 | 0.662 | 2.560 | 5.470 | 0.340 |  12.8 | 0.343 | 0.322 | 0.169 | 37.0 | 2.43 | 31.4 | 11 | clean |
|  1 | 10.47 | 2.15 | 0.318 |  6.77 |  7.5 | 34.3 | 0.37 | 0.502 | 1.759 | 5.722 | 0.100 |   8.2 | 0.377 | 0.927 | 0.477 | 25.8 | 2.36 | 30.5 |  9 | clean |
|  2 | 10.80 | 4.18 | 1.494 |  2.80 | 11.5 | 38.4 | 0.48 | 0.620 | 2.593 | 3.741 | 0.394 |  23.0 | 0.441 | 0.711 | 0.057 | 26.7 | 2.37 | 30.6 |  9 | clean |
|  3 |  9.51 | 3.27 | 1.456 |  2.24 |  6.5 | 13.6 | 0.28 | 0.435 | 3.687 | 2.284 | 0.274 |  19.3 | 0.352 | 0.554 | 0.280 | 23.5 | 2.34 | 30.3 |  9 | clean |
|  4 |  8.94 | 2.50 | 1.322 |  1.89 | 12.8 | 18.5 | 0.49 | 0.451 | 3.986 | 2.717 | 0.836 |  23.8 | 0.487 | 0.668 | 0.463 | 22.1 | 2.33 | 30.1 |  9 | **FAIL** wrong-oriented |
|  5 |  6.84 | 3.06 | 0.282 | 10.87 |  2.2 | 21.0 | 0.54 | 0.656 | 3.646 | 3.467 | 0.728 |  −2.8 | 0.549 | 0.127 | 0.035 | 16.9 | 2.28 | 29.5 |  8 | **FAIL** wrong-oriented |
|  6 | 14.15 | 3.58 | 0.413 |  8.69 |  8.0 | 36.1 | 0.59 | 0.621 | 2.489 | 3.636 | 0.088 |  19.2 | 0.347 | 0.197 | 0.244 | 34.9 | 2.42 | 31.2 | 10 | clean |
|  7 | 15.23 | 2.61 | 1.198 |  2.18 |  2.3 | 20.8 | 0.52 | 0.520 | 1.406 | 3.486 | 0.403 |  23.0 | 0.352 | 0.123 | 0.342 | 37.6 | 2.43 | 31.4 | 11 | clean |
|  8 | 12.32 | 3.42 | 0.573 |  5.97 | 17.4 | 35.4 | 0.22 | 0.588 | 1.747 | 5.865 | 0.505 |   9.3 | 0.505 | 0.487 | 0.129 | 30.4 | 2.39 | 30.9 | 10 | clean |
|  9 |  9.78 | 3.97 | 0.886 |  4.48 | 15.9 | 34.4 | 0.42 | 0.575 | 2.763 | 3.059 | 0.562 |  11.4 | 0.204 | 0.303 | 0.306 | 24.1 | 2.35 | 30.3 |  9 | clean (2 wrong-oriented) |
| 10 | 16.20 | 4.15 | 0.621 |  6.68 | 12.1 | 50.0 | 0.50 | 0.473 | 3.373 | 5.187 | 0.145 |  10.4 | 0.120 | 0.432 | 0.097 | 40.0 | 2.45 | 31.6 | 11 | **FAIL** skewness 151.2 |
| 11 |  9.99 | 3.47 | 0.481 |  7.21 |  5.6 | 15.5 | 0.48 | 0.508 | 3.795 | 3.202 | 0.581 |  −2.5 | 0.398 | 0.660 | 0.291 | 24.7 | 2.35 | 30.4 |  9 | clean |
| 12 | 13.63 | 4.99 | 0.444 | 11.25 |  9.4 | 25.7 | 0.33 | 0.448 | 2.523 | 5.148 | 0.809 |  −4.7 | 0.533 | 0.076 | 0.146 | 33.6 | 2.41 | 31.2 | 10 | **FAIL** 30 zero-volume |
| 13 |  9.96 | 2.21 | 0.732 |  3.03 | 24.9 | 43.2 | 0.44 | 0.593 | 2.939 | 2.131 | 0.721 |   4.8 | 0.045 | 0.379 | 0.285 | 24.6 | 2.35 | 30.4 |  9 | clean |
| 14 | 11.67 | 3.84 | 0.581 |  6.60 |  1.1 | 40.9 | 0.54 | 0.539 | 3.741 | 4.813 | 0.802 |  18.0 | 0.002 | 0.666 | 0.163 | 28.8 | 2.38 | 30.8 | 10 | **FAIL** 4 zero-volume |
| 15 | 13.08 | 2.90 | 0.793 |  3.66 |  0.7 | 18.3 | 0.52 | 0.570 | 1.201 | 3.516 | 0.088 |  20.2 | 0.145 | 0.804 | 0.194 | 32.3 | 2.40 | 31.1 | 10 | clean |
| 16 | 12.18 | 3.59 | 0.517 |  6.94 | 10.8 | 42.6 | 0.57 | 0.431 | 1.943 | 5.721 | 0.731 |  21.1 | 0.012 | 0.236 | 0.175 | 30.0 | 2.39 | 30.9 | 10 | clean (2 wrong-oriented) |
| 17 | 13.60 | 1.91 | 0.676 |  2.83 | 11.7 | 18.2 | 0.16 | 0.527 | 2.155 | 5.158 | 0.901 |   3.6 | 0.187 | 0.756 | 0.384 | 33.6 | 2.41 | 31.2 | 10 | clean |
| 18 | 17.29 | 3.11 | 1.325 |  2.34 |  5.0 |  6.1 | 0.46 | 0.500 | 1.680 | 3.574 | 0.790 |   6.6 | 0.282 | 0.555 | 0.377 | 42.7 | 2.46 | 31.7 | 11 | **FAIL** skewness 71.0 |
| 19 | 11.97 | 2.79 | 0.652 |  4.28 |  4.1 |  6.2 | 0.43 | 0.475 | 2.054 | 4.285 | 0.671 |  20.0 | 0.417 | 0.438 | 0.162 | 29.5 | 2.39 | 30.8 | 10 | clean (4 wrong-oriented) |
| 20 | 12.64 | 1.54 | 0.651 |  2.37 | 24.4 | 39.6 | 0.34 | 0.476 | 2.547 | 2.143 | 0.040 |  14.8 | 0.349 | 0.424 | 0.266 | 31.2 | 2.40 | 31.0 | 10 | clean |
| 21 | 15.64 | 2.45 | 0.840 |  2.92 | 17.5 | 41.7 | 0.43 | 0.502 | 2.725 | 4.356 | 0.182 |  18.5 | 0.418 | 0.003 | 0.004 | 38.6 | 2.44 | 31.5 | 11 | clean |
| 22 | 15.73 | 5.70 | 0.715 |  7.97 | 12.9 | 13.3 | 0.17 | 0.590 | 1.687 | 3.066 | 0.014 |   5.0 | 0.083 | 0.808 | 0.280 | 38.8 | 2.44 | 31.5 | 11 | clean |
| 23 | 18.70 | 4.62 | 0.633 |  7.30 |  8.1 | 17.4 | 0.25 | 0.430 | 1.283 | 4.564 | 0.046 |  −3.1 | 0.394 | 0.968 | 0.380 | 46.1 | 2.47 | 31.9 | 12 | clean |
| 24 | 14.62 | 2.21 | 0.716 |  3.08 |  6.2 | 39.2 | 0.53 | 0.453 | 2.051 | 5.590 | 0.850 |  24.5 | 0.092 | 0.296 | 0.024 | 36.1 | 2.43 | 31.3 | 11 | clean |

Two things fall out of the last four columns before any statistics are done:

- **`t1` and `stack` are effectively constant across the batch — 2.28–2.47 mm
  and 29.5–31.9 mm, a spread of 8%.** `first_layer_thickness` depends on speed
  and LWL only, through `log10(Re)`, which is a very flat function; the LWL
  range 6.8–18.7 m is a factor of 2.7 and moves `t1` by 8%. So the *wall model*
  the generator asks for is already almost hull-independent. Everything that
  varies between hulls varies through `hull_cell`, which is LWL/nx.
- **`n_ideal` therefore tracks LWL and nothing else.** It runs 8–12 and its rank
  correlation with LWL is essentially perfect by construction
  (`n_layers_to_bridge(t1, cell, 1.2)` with `t1` fixed and `cell ∝ LWL`). This
  is the concrete form of the owner's complaint: **the "per-hull" quantity the
  code already computes is a function of LENGTH alone. It knows nothing about
  shape.** `n_ideal` AUC against runner-bar failure: **0.465** — chance.

---

## 2 · What separates the failures from the passes at the shipped cap?

**Nothing that survives the multiple comparisons.** At cap 7 (which is rung 0 of
the shipped code — every one of the 25 hulls derives above 7, so the cap binds
on all of them), six hulls fail the runner bar: **4, 5, 10, 12, 14, 18**. Nine
fail the stricter zero-wrongly-oriented definition: those six plus **9, 16, 19**.

Twenty-nine quantities were scored by AUC against both definitions — the twelve
metrics `admissibility.screen()` already computes (reused, not re-derived), the
fifteen grammar parameters, and the derived `hull_cell`, `t1`, `stack`,
`n_ideal`, `last_layer/hull_cell`, plus four new ones written for this pass.

| quantity | AUC vs runner-bar (6 fail) | AUC vs strict (9 fail) | reading |
|---|---:|---:|---|
| `transom_half_beam_cells` | **0.842** | **0.903** | best; see below |
| `r_transom` | 0.789 | 0.799 | same signal, undivided by cell |
| transom cap perimeter / √area (new) | 0.754 | 0.868 | same signal |
| `min_bottom_panel_width_cells` | 0.746 | 0.743 | **inverted** — failures are WIDER |
| min chine half-breadth / stack (new) | 0.807 | 0.764 | **inverted**, same as above |
| `beta_len` | 0.702 | 0.708 | |
| max transverse facet turn (new) | 0.702 | 0.556 | |
| `p_bow` | 0.746 | 0.674 | |
| `stack_over_hull_cell` | 0.526 | 0.618 | |
| `last_layer_over_hull_cell` | 0.526 | 0.618 | identical — it is a function of LWL |
| `max_facet_turn_deg` (longitudinal) | 0.386 | 0.566 | |
| fraction of quads turning >30° (new) | 0.526 | 0.458 | |
| `stack_over_min_radius` | 0.368 | — | **worse than chance** |
| **`n_ideal` (the derived count)** | **0.465** | 0.417 | **chance** |
| `layers_achieved` | 0.368 | — | **worse than chance**; see §2.2 |
| `bow_bluntness_cells` | 0.386 | — | chance, as already recorded |
| `xmb_tangent_break_deg` | 0.316 | 0.333 | chance, as already recorded |
| fraction of quads turning >85° (new) | — | — | **identically zero on all 25 hulls** |

### 2.1 The transom result, and why it does not warrant a rule

`transom_half_beam_cells` is `y_chine(x=0) / hull_cell`, and because `hull_cell
∝ LWL` with a fixed `nx`, it is *exactly* `r_transom · BWL / LWL` up to a
constant — the two score identical AUCs to three decimals, which is the check
that it is a shape ratio and not a size effect.

Sorted, the six runner-bar failures sit at 66.1, 60.0, 53.4, 47.3, 28.8 (h18)
and 7.5 (h10) cells; the nineteen passes run 1.0 to 40.9. A threshold at 41
cells gives TP 6 / FP 0 / FN 3 / TN 16 against the *strict* definition —
better than the existing screen's TP 6 / FP 0 / FN 6. **Do not build on it.**

- The threshold is FITTED to these 25 points. Under leave-one-out re-fitting it
  degrades to **precision 0.60, recall 0.67 (TP 6, FP 4)** on the strict
  definition, and **precision 0.80, recall 0.67 (TP 4, FP 1)** on the runner
  bar. With six positives those estimates are themselves unstable.
- Correcting for the family of 31 metrics tested, by permutation (20 000 draws,
  statistic = max |AUC − 0.5| over the family): **family-wise p = 0.21** against
  the runner bar — the operational definition. It reaches p = 0.012 against the
  strict definition, which is the definition `run-case.sh` does not enforce.
  One of two labellings clearing correction is not a finding.
- It contains **no mechanism connecting a wide transom to a layer count.** The
  transom cap is a flat patch bounded by a sharp edge on all sides, and it is a
  place layers must terminate — so a longer termination edge is a plausible
  story. But hull 10 fails with the third-*narrowest* transom in the batch
  (7.5 cells), and hulls 24 and 17 pass with `r_transom` 0.850 and 0.901, the
  two fullest transoms there are. A story that the two extreme cases contradict
  is a story, not a mechanism.

### 2.2 Three earlier mechanisms, re-measured and refuted

**Achieved layer count does not discriminate.** Commit 48e190b's message states
*"Every clean result sits at achieved ≥ 4.3; every failure sits below ~3."*
Pooling all five campaign arms, 75 mesh results with a readable
`layers_achieved`:

|  | n | achieved range | median |
|---|---:|---|---:|
| passes runner bar | 50 | 0.53 – 8.13 | 4.87 |
| fails runner bar | 25 | 0.88 – 6.20 | 4.36 |

**11 clean results below 4.3; 21 failures at or above 3.0. AUC 0.369** — i.e.
the failures achieve slightly *fewer* layers, and the distributions overlap
almost entirely. At cap 7 alone the ranges are 4.11–6.33 (clean) against
3.99–6.09 (failed), AUC 0.368. The stated mechanism is refuted on its own data.
(The commit-message figures are reproduced here as measured on 2026-08-12;
a brief handed to this pass quoted "20 clean below 4.3, 18 failures ≥ 3.0",
which does not reproduce under either labelling — 11/21 on the runner bar,
9/24 on the strict flag. The conclusion is the same either way.)

**`last_layer_over_hull_cell` does not discriminate.** `case.py` warns below
0.12 against OpenFOAM's 0.3 `finalLayerThickness` default. At n=7 the whole
batch sits at 0.080–0.202 against the min-level cell; seven hulls are under the
warn bar (0, 7, 10, 18, 21, 22, 23) and **two of the seven fail** — against a
base rate of 6/25. AUC 0.526. The warn is a *record* that the stack does not
bridge, which is true and worth printing; it is not a predictor of the mesh
outcome and must not be promoted to one.

**Feature-angle density does not fire.** The proposed "feature-angle density
where layers must terminate" was implemented two ways on
`admissibility.surface_grid` at the case's own STL resolution. The fraction of
adjacent quads turning by more than half `_LAYER_FEATURE_ANGLE` (85°) is
**identically 0.00% on all 25 hulls** — the grammar's surface never turns that
far between adjacent facets, so the 170° layer feature angle never terminates
extrusion on the STL's own creases. The fraction turning >30° is 0.71–0.98%
across the batch, AUC 0.526. The maximum *transverse* turn (across the chine)
is 54–91°, AUC 0.702 / 0.556. **What this measures is the longitudinal and
transverse crease pattern of a 41-station lofted surface, not where snappy
actually stops a stack** — the real terminations are at the transom cap edge,
the deck edge and the keel, which are boundaries of the grid rather than
interior facet pairs. A metric of the terminating EDGES (their total length in
cells) is the transom perimeter row above, and it is the transom signal again.

**Curvature vs stack height points the wrong way.** `stack_over_min_radius`,
which is exactly the "local radius of curvature vs stack height" candidate and
is already implemented with the four piecewise breakpoints excluded, scores
**AUC 0.368** — the failures have *less* stack-to-radius than the passes. Its
bar of 1.0 is geometry rather than calibration and it should stay as a guard
against a real self-intersection; it is not the discriminator.

**Medial-axis proximity points the wrong way too.** The relevant version for a
full-width (non-symmetric) case is: port and starboard stacks each `stack` tall
approaching each other across `2·y`. Measured as `min interior chine
half-breadth / stack`, the batch runs 1.00 to 18.0 stacks of clearance and
**AUC is 0.807 in the inverted direction** — the failures have the MOST room.
The narrowest hull in the batch, hull 20 at 1.00 stack of clearance, meshes
clean at n=7 with skew 5.27 and zero wrongly-oriented faces.

---

## 3 · The decisive evidence: the outcome is not monotone in n for a FIXED hull

This is the finding that decides the question, and it is assembled from all five
arms. Rungs the back-off campaign tried and rejected are recovered exactly:
`n_layers_used + 2·(layer_attempts − 1)` reconstructs the starting rung, and the
ladder is documented to break on the first rung passing the runner bar, so every
earlier rung failed it. Each reconstructed start matches the hull's `n_ideal`
capped at 10 (the cap in force for that campaign) on all 16 hulls, which is the
check that the reconstruction is right.

`OK` = passes the runner bar, `X` = fails it, `.` = never run.

|  h | n=3 | n=4 | n=5 | n=6 | n=7 | n=8 | n=9 | n=10 | known-good set | shape |
|---:|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|
|  0 | OK | . | OK | . | OK | OK | . | X  | {3,5,7,8} | interval |
|  1 | X  | . | OK | . | OK | .  | X | .  | {5,7} | interval |
|  2 | OK | . | OK | . | OK | .  | OK | . | {3,5,7,9} | interval |
|  3 | OK | . | **X** | . | OK | . | X | . | {3,7} | **HOLE at 5** |
|  4 | X  | . | X  | . | X  | .  | X | .  | ∅ | nothing passes |
|  5 | OK | . | OK | . | **X** | OK | . | . | {3,5,8} | **HOLE at 7** |
|  6 | OK | . | OK | . | OK | OK | . | X  | {3,5,7,8} | interval |
|  7 | .  | . | X  | . | OK | .  | . | OK | {7,10} | interval |
|  8 | .  | OK | . | **X** | OK | X | . | X | {4,7} | **HOLE at 6** |
|  9 | .  | . | .  | . | OK | .  | OK | . | {7,9} | interval |
| 10 | .  | . | .  | . | X  | OK | . | X  | {8} | isolated |
| 11 | .  | . | .  | . | OK | .  | X | .  | {7} | |
| 12 | .  | . | .  | OK | X | X | . | X  | {6} | isolated |
| 13 | .  | . | .  | . | OK | .  | OK | . | {7,9} | interval |
| 14 | .  | X | .  | X | X  | X  | . | X  | ∅ | nothing passes |
| 15 | .  | . | .  | . | OK | .  | . | OK | {7,10} | interval |
| 16 | .  | . | .  | . | OK | .  | . | X  | {7} | |
| 17 | .  | . | .  | . | OK | .  | . | OK | {7,10} | interval |
| 18 | .  | . | .  | . | **X** | . | . | OK | {10} | isolated |
| 19 | .  | . | .  | . | OK | .  | . | X  | {7} | |
| 20–24 | . | . | . | . | OK | . | . | . | {7} | one rung tested |

Pass rate by fixed count, over the hulls where that count was run:

| n | 3 | 4 | 5 | 6 | **7** | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| passes / tested | 5/7 | 1/2 | 5/8 | 1/3 | **19/25** | 4/7 | 3/7 | 4/12 |
| % | 71 | 50 | 62 | 33 | **76** | 57 | 43 | 33 |

Four consequences, each load-bearing:

**(a) The cap 10 → 7 change was a net win that also caused specific
regressions, and the ladder cannot undo them.** Hull 18 meshed **clean at
n=10** — 0 zero-volume, 0 wrongly-oriented, skew 6.19, 8.13 layers achieved —
and at n=7 produces **10 wrongly-oriented faces and skew 70.98**. Hull 10 meshes
clean only at n=8 (skew 4.98) and fails at 7 (skew 151.19) and 10 (skew 43.36).
Hull 12's zero-volume cells went **4 at n=10 to 30 at n=7**, and it meshes
cleanly at n=6. Under the shipped configuration rung 0 is 7 and
`layer_backoff_ladder` steps *down* by 2 — so from 7 it can only reach 5 and 3,
and **it can never reach 8, 10 or even 6.** Hulls 10, 12 and 18 each have a
known-good rung that the current ladder is structurally incapable of visiting.

**(b) The step of 2 skips known-good rungs.** Hull 12's only known-good count is
**6**, which a step-2 ladder from an odd start never lands on.

**(c) The admissible set is not an interval.** Three of the twelve hulls tested
at three or more distinct counts have a failure strictly between two passes.
Hull 5 is the sharpest: n=3, n=5 and n=8 all give **0 wrongly-oriented faces and
max skewness 4.53–4.54**, while n=7 gives **182 wrongly-oriented faces and skew
56.80**. Hull 8 is the mirror image: n=4, 6, 8 and 10 all fail the strict flag
(6, 8 and 10 fail the runner bar too) while n=7 is the cleanest mesh it has —
skew 2.87, 6.33 layers achieved. **A single-valued function of hull geometry
cannot generate that map**, because it does not describe a threshold in n at
all.

**(d) No single count works for the batch.** Hull 12 passes only at 6 among the
four counts it was run at; hull 10 passes only at 8 among its three. Those sets
are disjoint. **Within the counts actually tested, the intersection over the 23
rescuable hulls is empty.** (It is not *proven* empty over all n: hulls 10 and
12 have never both been run at 3, 4, 5 or 9. §9 settles that.)

**23 of 25 hulls have at least one known-good rung — 92%,** against 76% at the
best fixed count. Hulls **4** and **14** pass at none of the counts tried (4 at
3/5/7/9, 14 at 4/6/7/8/10) and remain the batch's two genuinely unexplained
hulls; hull 4 was already flagged as such in `docs/BUILD-PLAN.md` §11.6.7.

---

## 4 · The five candidate rules, each judged against §2 and §3

The brief asked for each to be argued from the data rather than asserted.

| candidate | verdict | the argument |
|---|---|---|
| **local radius of curvature vs stack height** | **REJECT as a predictor, KEEP as a guard** | `stack_over_min_radius` already exists; AUC **0.368**, inverted. Its bar of 1.0 is geometry (layer normals cross at s→R) and it correctly refuses nothing here because nothing here is near it (0.005–3.5 was the range measured for §11.6.2). Keeping a geometric impossibility guard is right; calling it a discriminator is not. |
| **feature-angle density at terminations** | **REJECT as measured; the interior-facet form cannot fire** | The fraction of adjacent quads exceeding 85° is **0.0000 on all 25 hulls**. `_LAYER_FEATURE_ANGLE` is 170°, so no interior facet pair in this grammar ever terminates a stack. The terminations that matter are the transom cap edge, deck edge and keel — boundaries, not facet pairs. Measured as edge *length* (transom perimeter / √area) it becomes the transom signal, AUC 0.754/0.868, and inherits that signal's multiplicity problem. |
| **`last_layer_over_hull_cell` vs OpenFOAM's 0.3** | **REJECT as a predictor, KEEP as a receipt** | AUC 0.526. Seven hulls under the 0.12 warn bar, two of them fail, base rate 24%. It is a pure function of LWL at fixed n and therefore cannot carry shape information at all. |
| **minimum panel width** | **REJECT — inverted** | `min_bottom_panel_width_cells` AUC 0.746 with the failures WIDER. Hull 20, the narrowest at 1.00 cell, meshes clean. |
| **medial-axis / opposite-surface proximity** | **REJECT — inverted** | min chine half-breadth / stack: AUC **0.807**, failures have the most clearance (5.8–10.3 stacks) and several clean hulls have the least (1.0, 1.3, 2.0). The mechanism is real in principle for a full-width case and it simply is not binding at this cell size. |

None of the five is buildable as a per-hull `n = f(geometry)`. And §3 says why
that was never the right shape: even a perfect `f` returning one integer cannot
express `{4, 7}` (hull 8) or `{3, 5, 8}` (hull 5).

---

## 5 · The honest constraint, stated prominently

> **This repository has MEASURED that no build-time predictor of layer-induced
> mesh failure exists.** Wigley solves at `stack/hull_cell` **1.084** while KCS
> dies at **0.952** — a thicker relative stack surviving on one hull than kills
> another. `docs/LESSONS.md` records that a build-time cap on that ratio was
> drafted and killed by its own data, and `admissibility.py` refuses to let
> `stack_over_hull_cell` vote for the same reason.

**The proposal in §7 is not a predictor and cannot mispredict KCS or Wigley,
because it makes no prediction.** It meshes, reads checkMesh, and moves. That
is a deliberate structural choice: after §2 and §3, a search is the only
instrument the evidence supports.

Two places where the counter-example still bites and must be honoured:

1. **Anything that *orders* the search is a weak prediction, and it is allowed
   to be wrong** — being wrong costs one 96-second mesh, not a wrong answer.
   The ordering proposed in §7 is justified only by observed hit rate on this
   batch, is stated as such, and must be re-derived when the batch changes.
2. **The `stack_ratio > 1.2` refusal in `write_resistance_case` is a real
   build-time refusal and it is on the KCS/Wigley side of the line.** It is
   justified by a different measurement (a 5-layer 57 mm stack in a 37.9 mm
   cell at Fn 0.10 killing interFoam at t=0.0012) and it is a *fit* check, not
   a quality prediction. It should stay — but §6 shows it is about to become
   the binding constraint on triplets, which nobody has noticed.

**What could NOT be tested:** the transom metric cannot be evaluated on KCS or
Wigley. `admissibility.screen()` takes a grammar genome, not an STL, and no
equivalent quantity was measured for either benchmark. So the one rule that came
closest in §2 has never been put to this repository's standing counter-example,
and that alone is sufficient reason not to ship it.

---

## 6 · What a per-hull count breaks

### 6.1 The GCI triplet — and it is already broken at a fixed count

CLAUDE.md is right that the wall model must be frozen **across the grids of one
family**, and `make_case.py --triplet` pins `n_layers` at the finest scale for
exactly that reason. A per-hull count does **not** conflict with that: the
search runs once per hull and the winning count is pinned across all three
grids. The rule is "one count per FAMILY", and per-hull is a different axis.

**But the count must be searched at the FINEST grid, not the coarse one**, and
this is not a preference. `hull_cell ∝ 1/nx`, so `stack/hull_cell` doubles from
the coarse grid to the fine grid of a √2 family. MEASURED, at n=7 on a
coarse-anchored triplet:

| grid | scale | hulls whose `stack/hull_cell` exceeds the 1.2 build-time refusal |
|---|---|---|
| coarse | 1.0 | none (range 0.346–0.873) |
| medium | 1.414 | hull 5 (1.241) |
| fine | 2.0 | hulls 3, 4, 5, 9, 11, 13 (1.233–1.747) |

**Six of 25 hulls cannot be given an n=7 triplet at all** — `write_resistance_case`
raises `ValueError` on the fine grid before anything is meshed. That is true of
the SHIPPED fixed cap today; per-hull search does not create it, but it does
make the fix mandatory, because a search that ran at the coarse grid could
select a count the fine grid refuses. **The search must run at the finest scale
of the intended family, or it must be re-verified there and the family refused
as a unit if it fails.** Say which; do not leave it implicit.

### 6.2 Two hulls stop being comparable, and this is the expensive one

The known-good rungs across the 23 rescuable hulls span **3 to 10**. With
`_LAYER_EXPANSION` 1.2 the prism stack is `(1.2ⁿ − 1)/0.2 · t1`, so that range
is **3.64·t1 to 25.96·t1 — a 7.1× spread in stack height** at an essentially
constant `t1` (§1). Hull 12 at n=6 gets 9.93·t1 and hull 10 at n=8 gets
16.50·t1: a 66% difference in where the resolved near-wall region hands over to
the wall function, on two hulls that would then be compared on resistance.

`docs/BUILD-PLAN.md` §11.6.5 already states the principle — *"a hull that meshes
only with layers reduced has not passed the same physics case"* — for back-off
as an exception. **Under per-hull search it is the norm, on every hull, always.**
Concretely:

- Gate 2U is a *mesh-and-converge* gate. Per-hull counts are fine for it,
  provided the rung is reported (§11.6.5 already requires this).
- **Any cross-hull PHYSICS comparison is confounded** — a resistance ranking, a
  surrogate trained on CFD labels, an NSGA-II objective fed by L3. There is no
  common count to re-mesh them at: §3(d) shows the intersection is empty within
  the tested counts. So the honest position is that **CFD labels from a searched
  batch are not mutually comparable and must not be pooled into one training
  set or one ranking** until either a common count is found (§9 tests for one)
  or the wall-model difference is shown to be smaller than the effect being
  ranked. Nothing in the repository currently does this pooling — but §8.1 of
  the plan (the delta engine) and the surrogate flywheel both point at it.

### 6.3 Receipts — three of them are owed, and one existing line becomes false

`case.info` records `n_layers=` and `n_layers_to_fully_bridge=` and nothing
about how the count was chosen. Under search it must additionally record, per
the "an unmeasured metric is REFUSED, never assumed good" rule:

- `n_layers_ideal=` — the uncapped `n_layers_to_bridge` value.
- `n_layers_ladder=` — the full ordered list of counts that will be / were
  attempted, so a reader can tell a first-rung result from a sixth-rung one.
- `n_layers_rung=` — the index of the rung that produced this mesh, and
  `layer_search=on|off`.

And **`case.info`'s "NOTE: first-layer thickness AND layer count are held
constant across the GCI triplet" is written UNCONDITIONALLY today**
(`navalai/cfd/case.py`, the `case.info` template). It is already prose asserting
a property of a *family* on a case that may not belong to one; under per-hull
search on a single case it is simply false. That is docs/LESSONS.md defect class
4 — prose standing in for a verdict — and it should be emitted only when the
caller pinned the count, with the pinning scale named.

### 6.4 The admissibility screen's headline no longer describes the pipeline

This was not in the brief and it is the most urgent thing found.
`navalai/admissibility.py`'s docstring and `docs/BUILD-PLAN.md` §11.6.2 publish
**TP 6, FP 0, FN 6, TN 6 — precision 1.000, recall 0.500, Fisher p = 0.0498**,
measured on `data/gate2u-campaign-baseline.json`, i.e. at rung 0 **when rung 0
meant the derived count under `_MAX_LAYERS` = 10**. Rung 0 now means 7.

Re-scoring the *unchanged* screen against `data/gate2u-cap7-mesh.json`, which is
rung 0 of the shipped code, N = 25:

| labelling | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| published (baseline, cap 10, N=18) | 6 | 0 | 6 | 6 | 1.000 | 0.500 |
| **cap 7 runner bar (N=25)** | **2** | **6** | **4** | **13** | **0.250** | **0.333** |
| cap 7 strict (N=25) | 2 | 6 | 7 | 10 | 0.250 | 0.222 |

`draft_over_hull_cell` refuses hulls 0, 1, 6 and 12; **0, 1 and 6 all mesh
cleanly at n=7** (skew 4.52 / 3.25 / 4.65, zero wrongly-oriented faces each).
`sheer_collapse_cells` refuses 5, 11, 12 and 23; **11 and 23 mesh cleanly.**
The precision of 1.000 is a property of the cap-10 configuration and does not
transfer. `tests/test_admissibility.py::test_the_screen_catches_half_the_failures_and_no_more`
pins the matrix against the stored baseline JSON, so it still passes — the test
is green and the claim it protects no longer describes what ships. That is the
same shape as a receipt outliving the mesh that produced it.

**This is not a reason to re-fit the bars.** Both are `Basis.DERIVED` from
`_FS_BOX`, `_HULL_REFINE` and `_NX_BASE`, and re-fitting a derived bar to a new
outcome set would convert it into exactly the kind of tuned number the module
was built to avoid. The correct response is to **re-state the confusion matrix
at the shipped configuration**, in `admissibility.py` and in §11.6.2, and to
carry both.

**And the pre-registration in §11.6.6 is NOT settled by this.** It predicted
hulls 20 and 23 would fail to mesh **at rung 0 of the cap-10 baseline**, and
that campaign stopped at hull 19 — so neither hull was ever run in the
configuration the prediction was about. Both mesh cleanly at n=7. That is a
different configuration, so per docs/LESSONS.md defect class 6 the prediction is
**neither confirmed nor falsified; it is now unrunnable**, and it should be
recorded that way rather than scored against the cap-7 arm.

### 6.5 The Gate 2U-A watermark is stale

`data/gate-ledger.json` records Gate 2U at **27.8%**, `N=18, _MAX_LAYERS=10 —
the PRE-FIX configuration`, and says so honestly in its own `units` string. The
cap-7 arm is 25 hulls at rung 0 of the shipped code: **19/25 = 76.0% mesh-clean
by the runner bar, 16/25 = 64.0% by the strict flag, and 0% mesh-and-converge
because no solve was requested.** Gate 2U's metric is mesh AND converge, so the
watermark cannot be updated from a mesh-only arm — but the ledger's `units`
string should stop describing a configuration that no longer exists, and the
mesh-only figure belongs in the funnel's `mesh-success` stage (§11.6.4), not in
the watermark.

### 6.6 `derived_n_layers` in the screen is now a constant

The screen reports `derived_n_layers` as a DIAGNOSTIC whose note says it "is
8–10 for essentially every hull the grammar emits". It returns `layer_spec()`'s
capped value, which under `_MAX_LAYERS` = 7 is **7.0 for all 25 hulls** — a
constant, which cannot discriminate anything and whose note is now describing
the uncapped `n_ideal` instead. It should report `n_ideal` (which does vary,
8–12, and scores AUC 0.465) or say which of the two it is.

---

## 7 · What should change — the specification

**Someone else implements this. The files are `navalai/cfd/case.py`,
`scripts/mesh_robustness.py`, `scripts/make_case.py` and a new gate test.**

### 7.1 `_MAX_LAYERS` stops being a quality lever

It is currently the single knob standing in for a per-hull decision, and §3
shows it cannot be. Keep a bound — an absurd stack should still be refused — but
justify it as a **compute and fit** bound (the `stack_ratio > 1.2` refusal is
already the fit half), not as "the largest count measured clean". After a dense
sweep (§9) the largest-clean framing has no meaning: n=7 is the best single
rung on this batch and it is *wrong* for 6 of 25 hulls, two of which are only
correct ABOVE it.

`tests/test_layer_cap.py::test_the_cap_is_the_measured_value_and_moving_it_needs_a_new_measurement`
pins `_MAX_LAYERS == 7` and must be replaced, not deleted — its motivating
incident (the cap moved on an argument instead of a measurement) is still
exactly right, and the replacement test should pin the **search's ordering and
its bounds** against the same standard.

### 7.2 Replace the one-sided step-2 ladder with a dense two-sided search

```
search_order(n_ideal, floor=3) -> list[int]
    candidates = [n for n in range(floor, n_ideal + 1)]
    ordered by |n - n_start| ascending, ties resolved upward
    where n_start is the highest-yield rung MEASURED on the current batch
```

- **step 1, not 2** — hull 12's only known-good count is 6 and a step-2 ladder
  from 7 never visits it.
- **two-sided** — hull 10's is 8 and hull 18's is 10, both ABOVE the shipped
  rung 0; a downward-only ladder cannot reach either.
- **upper bound `n_ideal`, not a global cap** — that is the count at which the
  stack bridges to the local cell, which is the only principled ceiling, and it
  varies 8–12 across the batch. It is a bound on the SEARCH, not a target.
- **lower bound 3** — unchanged, and `test_a_clean_mesh_with_no_boundary_layer_is_not_a_pass`
  must keep guarding it: at cap 3, 14 of 15 "clean" hulls achieved 0.31–2.85
  layers, and a mesh with no prism stack cannot fold one.
- **`n_start` is an ORDERING HINT and it is allowed to be wrong.** On this batch
  it is 7 (19/25). It is a measured hit rate, not a derivation, and it must be
  re-derived from the dense sweep rather than carried forward as a constant.
- **Determinism is a requirement**, per §11.6.5: the order depends on
  `(n_ideal, floor, n_start)` and on nothing else — not wall clock, not machine
  state, not a retry counter.

**Stop condition:** the first rung passing the runner bar. **Report:** the rung
and the full ladder (§6.3).

### 7.3 Projected cost, from the observed matrix

19 hulls pass at the first rung; hulls 5 and 10 at the second (n=8); hull 12 at
the third (7→8→6); hull 18 no later than the sixth (7→8→6→9→5→10, with 8, 6, 9
and 5 untested); hulls 4 and 14 exhaust the ladder. That is **≤48 meshes for 25
hulls, 1.9 rungs/hull**. At the measured mesh-only cost of **96.2 s/hull mean
(median 92.8, range 41–174; the full 25-hull cap-7 arm took 40.1 min)** the
search costs **~77 min for 25 hulls against 40 min for one fixed rung — 1.9×
for 76% → 92%.** State that trade when proposing it; it is not free.

### 7.4 What must NOT be done

- **Do not narrow the grammar.** §11.6.3's anti-gaming clause covers this and it
  is not weakened by anything here.
- **Do not ship the transom rule.** §2.1.
- **Do not re-fit `draft_over_hull_cell` or `sheer_collapse_cells` to the cap-7
  outcomes.** §6.4. Re-state the matrix; leave the derived bars alone.
- **Do not claim the search is a per-hull DERIVATION.** It is a per-hull
  measurement, and the distinction is the whole content of §5.

---

## 8 · The experiment that settles it

**Complete the (hull × n) matrix.** It is the only experiment that can
distinguish "the admissible set is an interval whose location varies per hull"
(in which case a derived rule could exist, applied as a starting point) from
"the admissible set is a scatter" (in which case only a search can work), and it
is affordable.

| | |
|---|---|
| **hulls** | the same 25, `sample_valid(25, MissionSpec(), seed=0)` — the same genomes, so the 71 cells already measured are reused |
| **varies** | `--n-layers` over the integers **3…10**, one mesh per cell |
| **held** | speed 2.57 m/s, scale 1.0, non-symmetric, LTS, `_HULL_REFINE` (4,5), `_LAYER_EXPANSION` 1.2, `_TARGET_YPLUS` 100, `_LAYER_FEATURE_ANGLE` 170, `_REFINE_ROUNDS`, mesh-only, `--np 1`, `--cap-layers N --layer-backoff 0` so exactly one rung runs per cell |
| **records** | zero-volume, wrongly-oriented, max skewness, `layers_achieved`, `layer_pct`, cells, seconds — the fields `mesh_robustness.py` already writes |
| **cost** | 200 cells − 71 already measured = **129 meshes × 96.2 s ≈ 3.4 h**, unattended, resumable by hull. Add n=11 and n=12 for the six hulls whose `n_ideal` reaches them: +12 meshes, ~19 min |

**What would REFUTE the §7 specification**, stated in advance:

- **If every hull's admissible set turns out to be a contiguous interval** — the
  three observed holes (hulls 3, 5, 8) being reproduction artefacts or
  mis-reconstructed back-off rungs — then a two-sided search is over-engineering
  and a derived starting point plus a one-sided walk would do. *The holes must
  be re-run directly, not inferred:* hull 5 at n=7, hull 8 at n=6 and hull 3 at
  n=5 are three meshes, ~5 min, and they are the highest-value cells in the
  whole grid. Run them first.
- **If some count passes on all 23 rescuable hulls**, the per-hull claim
  collapses and the answer is "the cap was simply set wrong". §3(d) makes this
  unlikely — hulls 10 and 12 would both have to pass at one of 3, 4, 5 or 9,
  and each currently passes at exactly one count out of three or four tried —
  but it is not excluded and this experiment decides it.
- **If `n_start` = 7 is not the highest-yield rung over the completed grid**, the
  ordering in §7.2 is wrong and must be re-derived. It is a hit rate on 25
  points and it is the weakest number in the specification.
- **If a metric in §2 separates the completed grid's per-hull admissible sets**
  — e.g. transom width predicting the *centre* of the admissible set rather than
  pass/fail at one count — then a derived starting point becomes defensible, and
  it must then be tested against KCS and Wigley before it is believed (§5).

**Two cheap side-experiments the grid does not cover, both already owed:**

- **Is the mesh build identical at `--np 1` and `--np 10`?** §11.6.7 lists this
  as unverified, and this document's matrix mixes both (the baseline arm ran
  `--solve 2 --np 10`; the cap and back-off arms ran mesh-only at `--np 1`).
  The mesh build is serial either way, so it should be — one `MESH_ONLY=1`
  re-mesh of hull 7 at both settings, ~4 min, closes it. **Until it is closed,
  every row in §3 that comes from the baseline arm carries this assumption.**
- **Hull 4 and hull 14.** They pass at no count tried. The completed grid will
  say whether they pass at any count at all, and if they do not they become the
  batch's only evidence for a genuinely inadmissible geometry — which is the
  claim §11.6.2a says the data does *not* currently support.

---

## 9 · What this document does NOT establish

- **Any mechanism.** Not one. §2 refutes five candidates and finds no
  replacement. Why n=7 folds 182 faces on hull 5 while n=5 and n=8 fold none is
  unexplained, and nothing here should be read as an explanation.
- **That the back-off reconstruction in §3 is exact.** The rejected rungs are
  inferred from `n_layers_used + 2·(layer_attempts − 1)` and the documented
  break condition, not read from a stored record. Every reconstructed starting
  rung matches the hull's independently computed `n_ideal` capped at 10 (16 of
  16), which is a strong check — but `mesh_robustness.py` does not persist the
  rejected rungs' metrics, so the X marks at those cells carry no numbers. §8's
  grid replaces every inferred cell with a measured one.
- **Anything about the solve.** Every result here is checkMesh. `run-case.sh`'s
  bars are calibrated proxies for solvability (5 wrongly-oriented faces solve,
  10 die, 73 die; skew ≤20 from 6.32/8.68/8.93/9.64 solving and 42.94 dying) and
  a mesh passing them can still diverge — hull 2 did, in the baseline arm.
- **Whether per-hull counts change the physics enough to matter.** §6.2 shows a
  7.1× spread in prism-stack height across the known-good rungs and argues the
  comparison is confounded. **The size of the effect on C_T has not been
  measured**, and it should be, on one hull at two of its own known-good counts,
  before "not comparable" is used to block anything.
- **That the transom association is real.** §2.1. Family-wise p = 0.21 on the
  operational labelling.
- **Anything about symmetric cases or other scales.** Everything here is
  non-symmetric, scale 1.0, speed 2.57. `--symmetric` halves the domain and
  changes `ny`; no layer measurement exists for it.
