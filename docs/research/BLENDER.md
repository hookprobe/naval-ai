# BLENDER — what was measured on 2026-08-12

A record of measurements, not a status. Nothing in this document says Blender
is integrated, and nothing here is consumed by a gate except
`tests/test_blender_hull.py`, which fences the two findings that would be
expensive to re-learn.

**The headline is NEGATIVE and it is the point of the exercise.** On the hull
path, Blender-native generation is not closer to the analytic hull than the
current path — at best it is bit-for-bit the same surface, and every modifier
tried moves it away. The specific proposal measured, a voxel Remesh at
`voxel_size = 0.05`, **destroys the chine** that commit bbf1a47 had just made
exact to 1e-9 m. It must not ship on the hull path.

Two things Blender *does* do that the current tree cannot: it renders the hull
in Cycles from the STL the pipeline already writes (measured, working, 99.3 s),
and it is a lossless container for the existing grid, which is what makes a
manual-edit workflow conceivable. Neither improves a number.

---

## 0. The environment, and two claims about it that were both wrong

| | |
|---|---|
| Binary | `/Applications/Blender.app/Contents/MacOS/Blender` |
| Version | **Blender 5.2.0 LTS**, build date 2026-07-14, hash `fbe6228777e7` |
| Embedded Python | **3.13.13**, numpy **2.3.4** |
| Project venv | cp312 — so `import navalai` inside Blender is impossible |
| Render device | Cycles on **Metal**, `Apple M5 Pro (GPU - 16 cores)` |
| Bundled add-ons | 13 |

A prior session reported "Blender is not installed", inferred from an empty
`which blender`, and began a `pip install bpy`. **The brief that corrected it
said "there is no PATH symlink; that is all", and that was also wrong.**
MEASURED: `shutil.which("blender")` returns `/opt/homebrew/bin/blender`, a
Homebrew cask wrapper symlinked 2026-08-12 15:36, resolving to the same 5.2.0
LTS build. Both accounts of the state were false within a day of each other,
which is why `navalai.blender.run.have_blender()` asks the filesystem about an
exact binary and `tests/test_blender_hull.py` asserts that it gives the same
answer with `PATH` emptied — the rule, not the state.

Nothing was installed for this work. `pip install bpy` was not run.

### The split, and why it is forced

Blender's embedded CPython is 3.13 and the venv is 3.12, so the package is two
halves across a process boundary (`navalai/blender/__init__.py` states the
contract):

- **venv side** — `spec.py` serialises the hull cage to JSON, `metrics.py`
  measures a triangulation against the analytic hull, `run.py` invokes the
  binary.
- **Blender side** — `build_hull.py` and `render_hull.py` import only
  `bpy`/`bmesh`/`addon_utils`/stdlib.

Blender's unit system is set to `METRIC` with `scale_length = 1.0` explicitly
in every script rather than inherited from a startup file. Everything on the
wire is metres.

---

## 1. What the baseline actually is — the brief called it "the CadQuery STL"

It is not. `navalai/cfd/case.py::hull_to_stl` triangulates `Hull.closed_mesh`
directly in numpy and writes ascii STL itself. `cadquery` appears in this
repository **only** in `navalai/export.py`, for STEP and IGES. No STL on the
CFD path has ever been through OpenCascade. The comparison available is
"Blender vs the analytic triangulation", and that is what was measured.

All measurements are at the **SHIPPED** resolution — what
`write_resistance_case` writes for each hull via `stl_resolution`, which clamps
all three to **600 x 120** (288818–288890 triangles). Hulls are 4 / 8 / 14 of
`sample_valid(25, MissionSpec(), seed=0)`, Lwl 8.942 / 12.320 / 11.670 m,
`chine_row` 33 / 69 / 60.

### The ruler, validated before use

`deviation` throughout = **max distance from a point on the ANALYTIC moulded
surface to the nearest point of the triangulation**, binned into ten x/Lwl bins
reported by their centres. Commit bbf1a47 published hull 14's post-Stage-A row;
`navalai/blender/metrics.py::deviation_by_xl` reproduces it:

```
x/L            0.05  0.15  0.25  0.35  0.45  0.55  0.65  0.75  0.85  0.95
bbf1a47        0.01  0.11  0.36  0.83  1.36 23.53  1.29  2.62  3.03 102.92
this module    0.01  0.11  0.36  0.83  1.37 23.54  1.29  2.62  3.03 102.92
```

The 0.55 bin is the `x_mb` knuckle, whose peak is attained *exactly* at
`x = x_mb * Lwl`. Sampled without landing on it, that bin read **23.50 / 23.07
/ 23.50** at 801 / 2001 / 4001 probe stations — a number that moves with how
finely you sampled is not a measurement, so `analytic_probe_points` inserts
`x_mb` into the abscissae and the bin then reads **23.54 at all three
densities**. The shipped probe is 2001 x 61 = 242121 points.

The chine dihedral metric was cross-checked the same way: the normal jump
across the chine-ROW edges of `closed_mesh` at 600x120 reads a median of
**53.48 / 69.36 / 72.02 deg** on hulls 4/8/14, which is the 53.5 / 69.4 / 72.0
bbf1a47 published.

**Chine sharpness is only answerable at a stated length scale**, so it is a
sweep over absolute offsets from the knuckle (5, 12.5, 25, 50, 100 mm) rather
than one number. This matters: at 5% of the panel girth (~75 mm) a
voxel-remeshed chine still reads 71.7 deg. A true knuckle is flat across the
sweep; a rounded one collapses as the offset approaches the rounding radius.

---

## 2. Blender is a LOSSLESS container for the existing grid

`blender-grid` sends the same `admissibility.surface_grid` points to Blender,
which welds on the exact float tuple, builds quads with `closed_mesh`'s
winding, fan-triangulates and exports STL.

MEASURED on hull 14: **288836 triangles and 144420 vertices, identical to
`closed_mesh`**. Vertex map bijective, **every one of the 288836 triangles
matches**, max coordinate difference **9.67e-07 m** — Blender stores mesh
coordinates in single precision and that is the entire cost. Deviation bins,
mesh-to-analytic RMS and chine dihedral are identical to the current path on
all three hulls, to the printed digits.

Two traps found on the way, both of which produced a *different surface* while
looking like a tessellation detail:

- **`bmesh.ops.triangulate(quad_method="BEAUTY")`** — Blender's default —
  picks the shorter diagonal. These quads are WARPED (a ruled panel between two
  non-parallel section polylines is not planar), so the diagonal is part of the
  shape. `surfaceCheck` self-intersection locations went 166 (current, confined
  to x/L <= 0.042) -> **332, spread over x/L 0.00 to 1.00**.
- **`quad_method="FIXED"` did not fix it**: 23263 of 288836 triangles still
  differed, because bmesh does not guarantee it starts the split at the loop
  vertex the face was built with. `me.polygons` *does* preserve `from_pydata`'s
  loop order (verified directly), so the fan is taken there and the triangle
  set then matches exactly.

`surfaceCheck` and `surfaceFeatureExtract` on the identical surfaces:

| surface | featPts | featEdges | internal | selfX locations |
|---|---|---|---|---|
| hull 4 current | 7 | 2758 | 0 | 3 |
| hull 4 blender-grid | 7 | 2758 | 0 | 36 |
| hull 8 current | 7 | 3287 | 0 | 237 |
| hull 8 blender-grid | 7 | 3287 | 0 | 643 |
| hull 14 current | 6 | 2828 | 0 | 166 |
| hull 14 blender-grid | 6 | 2828 | 0 | 271 |

Feature extraction is **identical**. Self-intersection is not, and the
difference is float32 alone — the triangle sets are the same. Two notes, both
of which belong to `docs/research/STL.md`'s territory and are referenced here
rather than restated:

- The **current** shipped STL is already non-zero by `surfaceCheck` (3 / 237 /
  166), while `stl_forensics.self_intersections` (strict Möller–Trumbore) finds
  **0 pairs** on all of them and commit b91bbf3 records trimesh, PyMeshLab and
  Open3D agreeing at zero. The tools disagree, and **that disagreement predates
  Blender**.
- The count is not stable under coordinate precision. Same 288836 triangles,
  hull 14: **166** (float64, `%.6e`), **142** (float32, `%.6e`), **271**
  (float32, Blender's exporter). All of the current path's are confined to the
  transom cap at x/L <= 0.042; Blender's spread to 24.7% elsewhere.

Blender's ascii STL is **16% smaller** (57.5 vs 68.8 MB on hull 14) — it writes
the shortest round-tripping decimal rather than `hull_to_stl`'s fixed `%.6e`.

On build time the two are NOT measured like for like and the figures are given
with that said: 4.22 s is `mesh_of_hull` alone (the `closed_mesh` Python double
loop plus the weld), and 2.05 s is the Blender subprocess from launch to STL on
disk, EXCLUDING the ~4 MB spec JSON the venv side writes first. Neither number
is a fair total and no speed claim is made from them.

---

## 3. THE VOXEL REMESH AT 0.05 m — the specific claim, refuted

A 0.05 m voxel is 50 mm on hulls of 8.9–12.3 m.

### It does not preserve the chine. It deletes it.

Chine dihedral [deg], median over 400 stations, vs offset from the knuckle:

```
                        0.005  0.0125   0.025    0.05     0.1     analytic
hull 4  current          53.5    53.5    53.5    53.5    53.5        53.5
        voxel 0.05        0.0    10.6    28.4    46.8    53.5
        voxel 0.025       9.4    30.9    43.5    53.5    53.5
hull 8  current           69.4    69.4    69.4    69.4    69.4       69.4
        voxel 0.05         0.0    24.1    38.7    56.6    69.3
        voxel 0.025       14.2    38.1    57.3    69.3    69.4
hull 14 current           72.0    72.0    72.0    72.0    72.0       72.1
        voxel 0.05         0.0     9.9    28.9    60.1    71.8
        voxel 0.025        1.7    33.6    54.7    71.9    72.0
```

**0.0 deg is not a rounded chine, it is no chine**: both probe points land on
the same face. The knuckle has been replaced by a fillet of order the voxel
size. `surfaceFeatureExtract`'s own bar is 30 deg (`includedAngle 150`), so at
every offset up to 25 mm the remeshed chine is **not a feature at all**.

Reducing the voxel to 0.025 m does not rescue it (9.4 / 14.2 / 1.7 deg at
5 mm), and 0.025 m already costs 486412 triangles on hull 4 — 1.7x the current
surface.

### Every x/L bin gets worse

Max analytic-to-mesh deviation [mm]:

```
hull 4          0.05   0.15   0.25   0.35   0.45   0.55   0.65   0.75   0.85   0.95
current         1.06   1.10   1.12   0.35   1.56   0.30   0.82   2.12   2.84 130.70
voxel 0.05     57.59  45.71  45.63  46.38  51.04  37.67  45.07  42.06  45.43 163.97
voxel 0.025    27.53  21.41  21.52  20.77  21.03  22.86  22.98  23.18  24.05 141.99

hull 8          0.05   0.15   0.25   0.35   0.45   0.55   0.65   0.75   0.85   0.95
current         0.50   0.50   0.50   1.12   2.77  53.88   2.31   1.75   1.52  54.93
voxel 0.05     30.56  29.42  22.23  29.19  29.03  64.99  33.31  36.17  33.13  65.61
voxel 0.025    17.16  14.13  13.95  13.80  12.52  59.70  16.39  18.13  16.88  61.38

hull 14         0.05   0.15   0.25   0.35   0.45   0.55   0.65   0.75   0.85   0.95
current         0.01   0.11   0.36   0.83   1.37  23.54   1.29   2.62   3.03 102.92
voxel 0.05     31.15  23.62  26.56  30.26  29.49  40.87  42.82  40.12  39.72 116.34
voxel 0.025    22.58  12.51  17.92  17.37  17.30  38.69  20.86  22.68  21.24 106.79
```

Every bin, every hull, worse. Outside the two bins dominated by the known
longitudinal defects (0.55 = the `x_mb` knuckle, 0.95 = the stem taper), the
current path sits in a **0.01–3.03 mm** band and the 0.05 m voxel in a
**22.2–57.6 mm** band. It also wanders further OFF the hull, not merely short
of it: mesh-to-analytic RMS rises 23.1 -> 32.2 (hull 4), 12.1 -> 15.5 (hull 8),
15.1 -> 22.8 mm (hull 14).

### What the mesher would be handed

`surfaceFeatureExtract` at the pipeline's own `includedAngle 150`, initial
feature set:

| surface | feature points | feature edges | internal edges | `surfaceCheck` selfX |
|---|---|---|---|---|
| hull 4 current | 7 | 2758 | 0 | 3 |
| hull 4 voxel 0.05 | **524** | 1570 | **156** | **1505** |
| hull 4 voxel 0.025 | **1058** | 3147 | **315** | **5416** |
| hull 8 current | 7 | 3287 | 0 | 237 |
| hull 8 voxel 0.05 | **524** | 1659 | **130** | **1866** |
| hull 8 voxel 0.025 | **1066** | 3420 | **266** | **7247** |
| hull 14 current | 6 | 2828 | 0 | 166 |
| hull 14 voxel 0.05 | **489** | 1770 | **123** | **1479** |
| hull 14 voxel 0.025 | **986** | 3569 | **255** | **6437** |

This is the same shape of defect Stage A removed. bbf1a47 recorded the old grid
giving 211 feature points and 71 internal edges on hull 14 and the fix taking
it to 6 and 0; a 0.05 m voxel remesh takes it to **489 and 123** — worse than
the defect that was fixed. Those feature points are handed to snappy as
`hull.eMesh` and refined to `_HULL_REFINE[1]`, i.e. the mesher would spend
level-5 cells resolving staircase artefacts.

`surfaceCheck` self-intersection locations rise to **1479–1866** (voxel 0.05)
and **5416–7247** (voxel 0.025) from the current path's 3–237, and unlike the
current path's they are spread over the whole hull (median x/L 0.66 on hull 14)
rather than confined to the transom.

STATED SO IT IS NOT OVERCLAIMED: `stl_forensics.self_intersections` — the
strict Möller–Trumbore test — finds **0 pairs on the voxel-remeshed surfaces
too**, on all three hulls. So this row is `surfaceCheck` disagreeing with the
strict test in the same direction it already disagrees on the current path
(§2), only much more loudly. The voxel remesh is condemned by the deviation and
the chine, which are unambiguous; the self-intersection row is corroborating
evidence about what the mesher sees, not an independent proof of a broken
surface.

**The remeshed surface IS watertight** — 0 open edges, 0 non-manifold edges,
`surfaceCheck` "Surface is closed" on all three hulls — and it is still the
wrong surface. That is the same lesson `stl_forensics.py` was written around:
four hulls with different mesh outcomes all reported watertight/outward/0 open
edges.

### VERDICT

**Do not put a voxel Remesh on the hull path, at any voxel size measured.** It
buys a smaller file (21.1 vs 68.8 MB on hull 14) by discarding the feature the
hull is defined by.

### Where voxel remesh DOES belong

It is a repair tool for surfaces that need repairing, and — importantly —
`docs/research/STL.md` and commit b91bbf3 establish that **these hulls do not**:
trimesh, PyMeshLab and Open3D each find zero self-intersections on the current
STLs, so a remesh on this path is a fix for a defect measured not to exist. The
IMPORTED third-party path (`scripts/stl_thirdparty_check.py`,
`docs/research/STL-THIRDPARTY.md`) is a different question with different
inputs, and voxel remesh is a plausible tool there. **That was not measured
here, and this document does not claim it.** If it is tried there, the voxel
must be sized against the smallest feature that has to survive — on these
hulls, with a chine, no admissible voxel exists.

---

## 4. Subdivision surfaces — does Catmull-Clark move our points off the hull?

It does. The brief's premise is exactly right: our grid points lie ON the
analytic hull to 1e-12 m, and Catmull-Clark approximates its control cage
rather than interpolating it.

Two cages were measured. **A coarse 41 x 16 cage** (41 = `Hull.n_stations`,
16 = `hull_to_stl`'s default nz), which is a plausible hand-editable control
mesh, and **the shipped 600 x 120 cage**, which isolates subdivision's
non-interpolating property from cage coarseness.

Blender's subdivision honours per-edge creases, so measuring default
Catmull-Clark alone would be a strawman. The `-creased` arms crease every cage
edge whose normal jump exceeds **30 deg** — not a new threshold, but the
pipeline's own `includedAngle 150` — which marks the chine, keel, deck edge and
transom corner automatically.

Max analytic-to-mesh deviation [mm], hull 14:

```
                                     0.05   0.15   0.25   0.35   0.45   0.55   0.65   0.75   0.85   0.95
current                              0.01   0.11   0.36   0.83   1.37  23.54   1.29   2.62   3.03 102.92
subsurf-2, coarse cage             238.48 142.25 142.57 143.85 146.57 165.80 146.89 135.78 115.32 160.63
subsurf-2, coarse cage, creased      1.20   1.20   1.22   1.27   1.91  25.39  11.78  18.03   4.04 104.46
subsurf-1, shipped cage             17.40  14.42  14.42  14.42  14.40  30.98  13.81  12.87  11.39 105.14
subsurf-1, shipped cage, creased     0.13   0.13   0.36   0.83   1.37  23.54   1.29   2.63   3.03 102.92
```

**The direct answer to "how far does subdivision move our points off the
analytic hull":**

- **Without creases, up to 19.07 mm** (hull 4), 17.40 mm (hull 14), 11.80 mm
  (hull 8) — on the shipped cage, at ONE level of subdivision, worst bin
  excluding the two dominated by the known longitudinal defects. And the chine
  drops from 53.5 / 72.0 / 69.4 to **28.0 / 39.9 / 37.8 deg** at a 5 mm offset.
- **With creases at the 30 deg bar, 0.12 mm** on hull 14 (bin 0.05 goes
  0.01 -> 0.13), **1.70 mm** on hull 4 (1.06 -> 2.76), and **unchanged to two
  decimals** on hull 8. The chine is preserved exactly at 72.0 / 53.5 / 69.4
  deg across the whole offset sweep.

So creased Catmull-Clark on the shipped cage is at best *equal* to the current
path and never better — while costing **4x the triangles** (1155588 vs 288836)
and **3.3x the file** (230.3 vs 68.8 MB). There is no accuracy argument for it.

The coarse-cage arm is the more interesting one, and it is not a
recommendation either. Creased subsurf-2 on a 41 x 16 cage gives **42608
triangles and 8.5 MB** — 6.8x fewer triangles and 8x smaller — with a perfect
chine and deviation of 1.20–25.39 mm on hull 14 (against 0.01–23.54) and
19.01–24.52 mm on hull 4 (against 0.30–2.84). That is a legitimate trade for a
*visualisation* asset. Against the current surface bin by bin it is **1.08x to
99.8x worse** (hull 14), 1.08–9.1x (hull 8) and 8.0–74.8x (hull 4), and it has
no place on the CFD path.

Uncreased subdivision is catastrophic on the coarse cage: **115–238 mm**, and
the chine reads 0.0 deg at 5 mm on hulls 4 and 14.

---

## 5. Shape keys and lattices for optimisation — the architectural limit

Not measured, because it cannot be measured into existence, and stating it is
part of the deliverable.

The ladder scores a `Hull` built from a **GENOME**. `hydrostatics`, `weights`,
`arrangement` and `evaluate.CONSTRAINT_NAMES` are all computed from grammar
parameters, and `navalai/policy/` compiles the legal envelope to a parameter
BOX that bounds the NSGA-II search **in that same parameter space**. A free-form
lattice deformation or a shape-key blend produces geometry that is not
describable by `grammar.named(params)`, so:

- `evaluate()` cannot score it — there is no parameter vector to hand it;
- the policy box cannot bound it — a bound on `BWL` says nothing about a
  lattice control point;
- the surrogate cannot be queried on it — it is trained on genome vectors and
  is required to refuse OOD queries.

**Any Blender-side deformation scheme must be re-expressible as genome
parameters**, i.e. it must be a UI over the same numbers `grammar` already
carries. A deformation that is not is not an optimisation variable; it is a
render-time modification, and it must not be exported as the geometry the
ladder validated. This is a constraint on the design, not a defect in Blender.

---

## 6. Manufacturing unfold — the existing unroller, measured, and the add-on
##    that is not there

### `bpy.ops.export_mesh.paper_model` does not exist on this installation

MEASURED: Blender 5.2.0 ships **13** add-ons — `bl_pkg`, `cycles`,
`hydra_storm`, `io_anim_bvh`, `io_curve_svg`, `io_mesh_uv_layout`,
`io_scene_fbx`, `io_scene_gltf2`, `node_wrangler`, `pose_library`, `rigify`,
`ui_translate`, `viewport_vr_preview`. There is **no Paper Model**, and the
`bpy.ops.export_mesh` namespace is **empty**. There is also **no DXF
exporter**: the export operators are `alembic`, `obj`, `ply`, `stl`, `usd`,
plus grease-pencil PDF/SVG. `io_curve_svg` is an *importer*.

So the proposed tool would have to be installed as an extension, and even then
it produces neither of the formats a CNC or laser shop is handed here.
`navalai/unroll.py` already writes **R12 ascii DXF in millimetres** with
`$INSUNITS 4`.

### What the existing unroller measures on hulls 4/8/14

Marine ply 15 mm, `BEND_RADIUS_RATIO` 80 -> **1.20 m minimum cold-bend
radius**; sheet 1.22 x 2.44 m. Rigid, developable-only — which is the reason
the hull is chined with ruled panels in the first place. Nothing here stretches
to fit.

```
 hull          panel       family  ruling_twist        refold      refold  strakes
                                     max  median   edge mm   surface mm
    4    bottom-stbd   constant-x  0.6220  0.0000      36.2        36.2        2
    4    bottom-stbd  developable  0.1157  0.0002       8.5         9.1        2
    4   topside-stbd   constant-x  0.9947  0.1552     961.6       933.6        3
    4   topside-stbd  developable  0.4647  0.0121     718.2       706.0        3
    8    bottom-stbd   constant-x  0.1823  0.0000     102.0       101.5        2
    8    bottom-stbd  developable  0.0311  0.0000      34.0        54.3        2
    8   topside-stbd   constant-x  0.5814  0.2242     176.9       176.1        1
    8   topside-stbd  developable  0.6166  0.0199      48.8        71.0        2
   14    bottom-stbd   constant-x  1.0000  0.0515     751.6       727.4        2
   14    bottom-stbd  developable  0.1107  0.0001     337.7       335.1        6
   14   topside-stbd   constant-x  0.9871  0.3742     414.3       407.2        2
   14   topside-stbd  developable  0.3786  0.0314     147.6       147.4        2
```

Reproduce with `python scripts/blender_unroll_survey.py`.

The developable-ruling fit improves `refold_surface_deviation_mm` on every
panel of every hull (36.2 -> 9.1, 101.5 -> 54.3, 727.4 -> 335.1 on the bottoms;
933.6 -> 706.0, 176.1 -> 71.0, 407.2 -> 147.4 on the topsides), and **it clears
the 5 mm bar on none of them** — the best is 9.1 mm and the worst is 706 mm.
`ruling_twist` medians on the fitted topsides are 0.0121 / 0.0199 / 0.0314,
i.e. non-zero: **these topside panels are not developable**, which
`navalai/unroll.py`'s docstring already records as a property of the grammar
(the `w**0.15` sheer taper and the `x_mb` slope discontinuity), not of the
unroller.

### Conclusion: Blender must NOT own unfolding

1. **A second unroller is this repository's signature defect.** `unroll.py`
   already does triangle development, an LM solve for the ruling pairing, a
   two-sided refold verification, bend-radius strake splitting, MaxRects
   nesting, DXF export and DXF readback, and it is covered by Gates F and 6M.
   That module's docstring records what two developability metrics cost the
   last time: `dev_error_rel`, an O(h^2) chord residual, was the one that
   printed the verdict and it passed a doubly-ruled hyperbolic paraboloid at
   6.5e-4 against a 5e-3 bar.
2. **Paper Model would unfold a TRIANGLE MESH.** The shipped hull STL is
   600 x 120 = ~289000 triangles. The hull's real parts are two developable
   strakes per side, which is what `develop()` targets. Unfolding 289000
   triangles with seams and tabs yields confetti, not boat panels.
3. **The blocking number is not a tooling number.** The refold miss is
   9–706 mm and its causes are recorded in `unroll.py` as grammar properties.
   No flattening tool fixes a surface that is not developable.

**What Blender could add, and the bar it must clear:** visual verification —
showing the nested sheet layout and the refolded panel against the hull, so a
6 mm step at `x_mb` is seen rather than read off a table. That is a viewer, not
a second implementation. If any Blender component is proposed to *own* part of
unfolding, the bar is a measured improvement in `refold_surface_deviation_mm`
on these same hulls, not that the SVG looks plausible.

---

## 7. Rendering

### The hull half works, measured end to end

`navalai/blender/render_hull.py` imports the STL the pipeline already writes,
sets a Cycles scene and renders. MEASURED on hull 14's current STL:

| | |
|---|---|
| triangles | 288836 |
| engine | CYCLES (`engine_after_set`) |
| device | GPU / METAL, Apple M5 Pro 16-core |
| resolution, samples | 960 x 600, 64 |
| wall clock | **99.3 s** |
| PNG | 582562 bytes |
| STL import | 77 ms |

One trap: **the render engine enum is not a capability check on this build.**
`bpy.types.RenderSettings.engine`'s enum lists only `BLENDER_EEVEE`, before and
after `addon_utils.enable("cycles")` succeeds — while
`scene.render.engine = 'CYCLES'` nevertheless works. The receipt records
`engine_after_set`, i.e. what the scene actually held when the render ran, not
what the enum advertised.

No conversion is involved: the STL is already the deliverable format. This half
of the owner's rationale — a photorealistic render of a winning design without
a lossy conversion — is **supported and measured**.

### The free-surface half: Blender is DOWNSTREAM of the step that fails

Blender's importers on this build are `alembic`, `fbx`, `gltf`, `obj`, `ply`,
`stl`, `usd` and svg-curve. **There is no VTK, VTU, VTP or OpenFOAM reader.**
So a Cycles render of the wave field requires a POLYGONAL isosurface produced
upstream — and producing that isosurface from the hanging-node polyhedral mesh
is precisely the step `CLAUDE.md` attributes the failure to.

**Blender cannot take that step over. It sits after it.** The intermediate
would be PLY or OBJ, and something still has to make it.

### What could NOT be measured, said plainly

`CLAUDE.md` records that `render_case.py` "produces noise on any case with
`_REFINE_ROUNDS > 0` ... MergeBlocks, Tetrahedralize and ResampleToImage+mask
were all tried and all failed". `scripts/render_case.py` as committed **uses**
ResampleToImage plus a `vtkValidPointMask` threshold and documents it AS THE
FIX ("an isosurface of a regular grid is exact"). Those two statements cannot
both be current.

**It could not be settled here.** MEASURED 2026-08-12: **no run in `runs/`
carries both `constant/polyMesh` and a usable field.** `clean-runs.sh` trimmed
the mesh out of `kcs_s1`, `kcs`, `kcs_iso` and `gci/*` (ParaView reports
"contains no meshes"), and the 25 `zbf_*` / `stageA_*` directories that still
have a mesh are MESH-ONLY builds from the Gate 2U layer campaign — the
OpenFOAM reader finds **916677 cells and zero arrays** on
`runs/stageA_h4_n7`, because `refineMesh` changed `constant/polyMesh` while the
`0/` fields kept their pre-refinement sizes (the bookkeeping problem
`CLAUDE.md` already records).

`scripts/blender_isosurface_probe.py` is written and refuses correctly: it
exits on a case with no `constant/polyMesh`, and it scores each route by
planarity against a known-exact answer (the setFields step at z = 0 must
contour to the plane z = 0). **It has not produced a result.** Running it needs
a case with a mesh AND a solution, i.e. a fresh solve. Until then, neither the
CLAUDE.md claim nor the code comment should be quoted as current.

---

## 8. Summary table — hull 14, everything at 600 x 120

```
surface                              tris   MB  wtr featE  selfX  maxdev  chine@5mm
current                            288836 68.8    Y  2828    166  102.92       72.0
blender-grid                       288836 57.5    Y  2828    271  102.92       72.0
blender-voxel-0.05                 119472 21.1    Y  1770   1479  116.34        0.0
blender-voxel-0.025                477224 86.1    Y  3569   6437  106.79        1.7
blender-subsurf-2 (coarse cage)     42608  8.5    Y   694      0  238.48        0.0
blender-subsurf-2-creased           42608  8.5    Y   838      0  104.46       72.0
blender-subsurf-1-finecage        1155588230.4    Y  5119      -  105.14       39.9
blender-subsurf-1-finecage-creased1155588230.3    Y  5655      -  102.92       72.0
```

`featE` = `surfaceFeatureExtract` initial feature edges at `includedAngle 150`;
`selfX` = `surfaceCheck -checkSelfIntersection` locations (`-` = not run, the
strict in-repo check is capped at 400000 triangles and reports None rather than
0 above it); `maxdev` = worst bin, which for every non-destroyed surface is the
0.95 stem-taper bin and therefore says more about the grammar than about the
mesh. **Read the per-bin tables, not this column.**

---

## 9. What ships, and what does not

**Ships** (measurement infrastructure only; nothing is wired into the ladder,
`pipeline.py` or the case writer):

- `navalai/blender/` — the split package
- `scripts/blender_compare.py`, `blender_foamcheck.py`,
  `blender_unroll_survey.py`, `blender_isosurface_probe.py`
- `tests/test_blender_hull.py` — 7 tests, ~24 s, skipped where the binary is
  absent

**Does not ship, and why:**

- **Voxel Remesh on the hull path** — destroys the chine (§3).
- **Catmull-Clark on the hull path** — never better than the cage it is given,
  4x the triangles for parity at best (§4).
- **A Blender unroller** — `unroll.py` is better and the blocker is the
  grammar, not the tool (§6).
- **Blender as the CFD renderer** — it cannot read the data and sits after the
  step that fails (§7).

**Open, and owed:**

- The ParaView isosurface question (§7) needs a case with a mesh and a
  solution.
- The imported third-party STL path was NOT measured (§3) and no claim is made
  about it.
