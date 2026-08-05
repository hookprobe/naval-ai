# Consultation brief — OpenFOAM near-wall / y+ blocker

Written to be self-contained for an outside reader (human or AI). Everything
below is measured on the machine, not estimated.

## What we are building

Automated ship-resistance CFD: a parametric hull generator emits an STL, a
script writes a complete OpenFOAM `interFoam` case (free-surface RANS,
kOmegaSST with wall functions), and it runs unattended. It must work on
arbitrary generated hulls, not one hand-tuned case.

## The blocker in one sentence

**We cannot get y+ into the wall-function validity band (30–300) on any mesh
configuration that also produces a valid mesh, so skin friction — most of the
drag at our Froude number — is computed outside the model's range of validity.**

## The evidence

Benchmark: KCS containership, model scale 1:31.6, LPP 7.2786 m, Fn 0.260
(U = 2.196 m/s, Re = 1.26e7). Published tank data: C_t = 3.711e-3
(KRISO), 13-group CFD scatter 3.620–3.733e-3.

Our result: **C_t = 9.33e-3, i.e. −151% vs EFD, 2.5× too high.**
Only **16.3% of wetted hull faces** lie in 30 ≤ y+ ≤ 300; median y+ 2475.
On our own (chined, small-craft) hull the same pipeline gives 2.0% in band and
viscous drag 2.62× the ITTC-57 flat-plate line. Both hulls point the same way.

## The mechanism we believe is at work

To land y+ ≈ 30 at this Reynolds number the first cell must be ~0.8 mm. The
local hull cell is 76–152 mm. That is a 100–200× jump, which needs either
(a) ~15 prism layers, or (b) a much finer surface cell.

- (a) fails: snappyHexMesh inserts ~50% of layers at n=3, 26% at n=8, 11% at
  n=15, and at n≥6 interFoam dies on the first timestep. `nLayerIter` /
  `nRelaxedIter` change nothing.
- (b) fails: raising `refinementSurfaces` from (2 3) to (3 4) gives 18
  *incorrectly oriented faces* (negative face pyramids) and interFoam dies at
  t≈8e-4; (4 5) gives zero-volume cells. Verified this is the castellation
  stage, not layers: `addLayers false` produces a byte-identical broken mesh.

Refinement making things *worse* is the strange part. It is the signature of a
sub-cell defect that coarse cells step over — but the surface is clean:
`surfaceCheck -checkSelfIntersection` reports "not self-intersecting", OCC
`BRepCheck_Analyzer` says the shape is valid (one shell, 649 faces), and
displacement matches published to −0.14%.

## What we already ruled out, with measurements

| hypothesis | test | result |
|---|---|---|
| prism layers cause it | `addLayers false` | identical broken mesh |
| STL sliver triangles | vertex weld | merges nothing (slivers are *collinear*, not coincident) |
| mirrored-hull keel seam | switched to half hull + symmetry | skewness 52.2 → 9.5, defect persists |
| self-intersecting STL | fixed sew tolerance + ear-clip capping | surface clean, defect persists |
| bad IGES export | swapped to a NAPA `PTOL=0.002` export | zero-volume 14 → 2, still dies |
| solver startup transient | initial `deltaT` 1e-3 → 1e-5 | still dies at t≈1e-5 |
| free-surface refinement box | removed it | skew 63 → 7, still 7 zero-volume cells |

## The architectural theory we tested and could not land

OpenFOAM's own reference case (`$FOAM_TUTORIALS/multiphase/interFoam/RAS/
DTCHull`) does NOT let snappy refine. It runs **6 rounds of `topoSet` +
`refineMesh` first**, then snappy with `refinementSurfaces level (0 0)` and no
refinement regions. The decisive line is in `refineMeshDict`:

    directions ( tan1 tan2 );      // x and y ONLY, never z

Free-surface ship meshes need **anisotropic** refinement — fine in x,y near the
hull, fine in z only at the waterline, coarse in z at the keel. `refineMesh`
does that directionally. **snappyHexMesh refines isotropically**, so buying x,y
resolution through snappy levels drags z along, and every level boundary is a
hanging-node transition. That single fact would explain all of our symptoms.

We implemented it. The refinement rounds work correctly (429k → 1.716M cells,
exactly 4× per round). snappy then **aborts**:

    Dangling coarse cells refinement iteration 0
    Selected for refinement : 5868 cells (out of 1980981)
    FATAL ERROR: cell 9404 of level 0 uses more than 8 points of equal or
    lower level
    From hexRef8::setRefinement(...) at hexRef8.C:3763

i.e. snappy's `danglingCellRefine` still wants to refine, and `hexRef8` (its
octree engine) cannot refine cells that `refineMesh` created. Setting
`refinementSurfaces level (0 0)`, `features level 0` and `minRefinementCells 0`
did not stop `danglingCellRefine` running.

## The specific questions we would like help with

1. **How do you stop snappyHexMesh refining entirely** so it only snaps and
   adds layers on a mesh pre-refined by `refineMesh`? Is there a switch that
   disables `danglingCellRefine`, or must the pre-refined mesh satisfy some
   `hexRef8` invariant (consistent `cellLevel`/`pointLevel`) that `refineMesh`
   does not write? DTCHull evidently does this successfully — what makes our
   case different?
2. If that path is a dead end, **what is the accepted way to reach y+ 30–300
   on an automatically generated hull** with snappy? Published KCS studies use
   1–6 M cells and report y+ ≈ 30; we cannot reproduce the near-wall mesh they
   imply.
3. Is the aspect ratio the real constraint? Our free-surface cells are ~20:1
   (dx 0.6 m, dz 0.03 m) and DTCHull's are ~40:1, so anisotropy per se seems
   fine — but our failures all appear where a refinement transition meets an
   anisotropic cell.
4. Is there a defensible alternative: accept high y+ and use a wall treatment
   valid there, or correct the friction against ITTC-57 and declare the bias?
   We will not soften the gate, so any correction must be a stated model, not a
   fudge factor.

## Environment

OpenFOAM v2606 (gerlero/openfoam-app, macOS arm64, M5 Pro, 15 cores, 24 GB).
Solver `interFoam`, kOmegaSST, `nutkWallFunction`, maxCo 5 / maxAlphaCo 2,
10 MPI ranks. Geometry via OCP/OpenCascade from IGES.
