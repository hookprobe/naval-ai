"""OpenFOAM resistance-case generator (interFoam free-surface, snappyHexMesh).

Deterministic: same hull + same settings -> byte-identical case directory,
so the case dir hash goes into provenance. Runner: cfd/run-case.sh.
GATE STATUS: METAL-GATED — requires a machine with OpenFOAM (.com or .org
2306+); this box has none, so Gate 3 (KCS/JBC calibration) stays RED here.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

from ..geometry import Hull

# Total z-expansion across each block (coarsest cell / finest cell). Held
# FIXED while cell counts scale, which is what makes the refinement
# systematic: every cell dimension then shrinks like 1/scale together. Fixing
# the per-cell ratio instead would shrink the interface cell exponentially in
# n and the three grids would not be a refinement family at all.
_Z_EXPANSION = 20.0

# Free-surface refinement slab, as multiples of LWL (hull occupies x in [0,L]).
# Refining the whole tank buys nothing for hull forces and costs the run:
# every refined cell is paid for at every one of the ~13k timesteps that
# maxAlphaCo sets. The slab covers the hull and the near wake, where the
# pressure field that makes the drag actually lives.
_FS_BOX = dict(x0=-1.6, x1=1.3, y=0.7, z=0.05)

# Target y+ for the wall functions (build plan: y+ ~ 30, SJTU KCS pipeline).
# MEASURED before this was computed rather than assumed: 3 relative-sized
# layers gave y+ min 42 / avg 7491 / max 60017 on the hull -- one to three
# orders of magnitude outside where nutkWallFunction is valid. Skin friction
# is most of this hull's drag at Fn 0.26, so that is not a rounding error.
_TARGET_YPLUS = 30.0
_LAYER_EXPANSION = 1.3

# Layers snappy will actually INSERT on this hull, measured (coarse grid,
# absolute first-layer thickness held at y+ 30):
#   n=3 -> 50.3%   n=5 -> 36.5%   n=8 -> 26.2%   n=15 -> 11.2%
# and loosening nLayerIter/nRelaxedIter changed nothing. A layer that is not
# inserted controls no y+ at all, so coverage wins over stack depth: the ideal
# bridging depth is still computed, and case.info records both so the gap is
# visible rather than silently absorbed.
_MAX_LAYERS = 3


def first_layer_thickness(speed: float, lwl: float, target_yplus: float,
                          nu: float = 1.09e-6) -> float:
    """Absolute first-layer THICKNESS [m] that lands the first cell centre at
    `target_yplus`, via the ITTC-1957 flat-plate friction line.

    y+ = u_tau * y / nu with y the cell CENTRE, so the cell is twice that.
    """
    re = speed * lwl / nu
    cf = 0.075 / (math.log10(re) - 2.0) ** 2
    u_tau = speed * math.sqrt(cf / 2.0)
    return 2.0 * target_yplus * nu / u_tau


def n_layers_to_bridge(t1: float, cell: float, expansion: float) -> int:
    """Layers needed for a stack of first-thickness `t1` to reach `cell`.

    A stack that stops far short leaves a large size jump at its top, which is
    where snappy gives up and coverage collapses.
    """
    if t1 <= 0 or cell <= t1:
        return 3
    n = math.log(1.0 + (cell / t1) * (expansion - 1.0)) / math.log(expansion)
    return int(max(3, min(20, round(n))))


def _interface_dz(height: float, n: int, expansion: float) -> float:
    """Height of the cell touching the waterline in a graded block.

    Cells form a geometric series summing to `height`, with the largest/
    smallest ratio equal to `expansion`; the interface cell is the smallest.
    """
    if n < 2:
        return height
    q = expansion ** (1.0 / (n - 1))
    return height * (q - 1.0) / (q ** n - 1.0)   # smallest term of the series

CONTROL_DICT = """FoamFile {{ version 2.0; format ascii; class dictionary; object controlDict; }}
application     interFoam;
startFrom       startTime;  startTime 0;
stopAt          endTime;    endTime {end_time};
deltaT          {dt};
writeControl    adjustableRunTime;  writeInterval {write_int};
purgeWrite      3;
// maxAlphaCo 5 smears the interface: the alpha equation carries the wave, so
// it gets the tighter limit even though momentum tolerates Co>1. Measured
// cost of the limit: at maxAlphaCo 1 it, not the cell count, sets dt (0.0031 s
// -> ~4.9 h for the coarse grid alone, days for the fine). 2 is the compromise
// MULESCorr's semi-implicit alpha solve supports; interface sharpness is
// checked in the render rather than assumed.
adjustTimeStep  yes;  maxCo 5;  maxAlphaCo 2;  maxDeltaT 0.1;
functions {{
  forces {{
    type forces; libs (forces); patches (hull);
    rho rhoInf; rhoInf 998.8; CofR (0 0 0);
    writeControl timeStep; writeInterval 10;
  }}
  // The build plan specifies wall functions at y+ ~ 30 (SJTU KCS pipeline).
  // Nothing measured it before, so the layer stack was unverified: y+ in the
  // buffer layer (5-30) is where wall functions are least valid and skin
  // friction — most of this hull's drag — goes quietly wrong.
  yPlus {{
    type yPlus; libs (fieldFunctionObjects);
    writeControl writeTime;
  }}
}}
"""

# TWO blocks stacked in z, split exactly at the waterline z=0. The split is a
# block boundary, so a mesh FACE lies on z=0 BY CONSTRUCTION for any cell count
# — this replaces the old "nz must be a multiple of 3" snapping, which forced
# z-refinement ratios of 1.333 and 1.5 and so broke the r=sqrt(2) systematic
# refinement that GCI requires (measured: p=nan, GCI 58.5%, oscillatory).
# Both blocks grade toward the interface (G_WATER<1 shrinks upward, G_AIR>1
# expands upward), buying a thin free-surface cell without paying for it
# through the full tank depth.
BLOCKMESH = """FoamFile {{ version 2.0; format ascii; class dictionary; object blockMeshDict; }}
scale 1;
vertices (
  ({x0} {y0} {z0}) ({x1} {y0} {z0}) ({x1} {y1} {z0}) ({x0} {y1} {z0})
  ({x0} {y0} 0)    ({x1} {y0} 0)    ({x1} {y1} 0)    ({x0} {y1} 0)
  ({x0} {y0} {z1}) ({x1} {y0} {z1}) ({x1} {y1} {z1}) ({x0} {y1} {z1})
);
blocks (
  hex (0 1 2 3 4 5 6 7)     ({nx} {ny} {nzw}) simpleGrading (1 1 {g_water})
  hex (4 5 6 7 8 9 10 11)   ({nx} {ny} {nza}) simpleGrading (1 1 {g_air})
);
boundary (
  inlet      {{ type patch; faces ((1 2 6 5) (5 6 10 9)); }}
  outlet     {{ type patch; faces ((0 4 7 3) (4 8 11 7)); }}
  atmosphere {{ type patch; faces ((8 9 10 11)); }}
  bottom     {{ type wall;  faces ((0 3 2 1)); }}
  side1      {{ type wall;  faces ((0 1 5 4) (4 5 9 8)); }}
  side2      {{ type wall;  faces ((3 7 6 2) (7 11 10 6)); }}
);
"""

FV_SCHEMES = """FoamFile { version 2.0; format ascii; class dictionary; object fvSchemes; }
ddtSchemes      { default Euler; }
gradSchemes     { default Gauss linear; }
divSchemes {
  div(rhoPhi,U)     Gauss linearUpwind grad(U);
  div(phi,alpha)    Gauss vanLeer;
  div(phirb,alpha)  Gauss linear;
  div(phi,k)        Gauss upwind;
  div(phi,omega)    Gauss upwind;
  div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
wallDist        { method meshWave; }
"""

FV_SOLUTION = """FoamFile { version 2.0; format ascii; class dictionary; object fvSolution; }
solvers {
  "alpha.water.*" {
    nAlphaCorr 2; nAlphaSubCycles 1; cAlpha 1;
    MULESCorr yes; nLimiterIter 3; alphaApplyPrevCorr yes;
    solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0;
  }
  "pcorr.*" { solver PCG; preconditioner DIC; tolerance 1e-5; relTol 0; }
  p_rgh { solver GAMG; smoother DIC; tolerance 1e-7; relTol 0.01; }
  p_rghFinal { $p_rgh; relTol 0; }
  "(U|k|omega).*" { solver smoothSolver; smoother symGaussSeidel;
                    tolerance 1e-7; relTol 0.1; nSweeps 1; }
}
PIMPLE {
  // nOuterCorrectors 1 is PISO: valid only at Co<1. Running maxCo 5 in PISO
  // mode leaves the pressure-velocity coupling unconverged within the step.
  momentumPredictor no; nOuterCorrectors 2; nCorrectors 3;
  nNonOrthogonalCorrectors 0;
}
relaxationFactors { equations { ".*" 1; } }
"""

DECOMPOSE = """FoamFile {{ version 2.0; format ascii; class dictionary; object decomposeParDict; }}
numberOfSubdomains {np};
method scotch;
"""

SURFACE_FEATURES = """FoamFile { version 2.0; format ascii; class dictionary; object surfaceFeatureExtractDict; }
hull.stl {
  extractionMethod extractFromSurface;
  extractFromSurfaceCoeffs { includedAngle 150; }
  writeObj no;
}
"""

SET_FIELDS = """FoamFile { version 2.0; format ascii; class dictionary; object setFieldsDict; }
defaultFieldValues ( volScalarFieldValue alpha.water 0 );
regions (
  boxToCell { box (-1e6 -1e6 -1e6) (1e6 1e6 0);
              fieldValues ( volScalarFieldValue alpha.water 1 ); }
);
"""

TRANSPORT = """FoamFile { version 2.0; format ascii; class dictionary; object transportProperties; }
phases (water air);
water { transportModel Newtonian; nu 1.09e-06; rho 998.8; }
air   { transportModel Newtonian; nu 1.48e-05; rho 1.2; }
sigma 0.07;
"""

GRAVITY = """FoamFile { version 2.0; format ascii; class uniformDimensionedVectorField; object g; }
dimensions [0 1 -2 0 0 0 0];
value (0 0 -9.81);
"""

TURBULENCE = """FoamFile { version 2.0; format ascii; class dictionary; object turbulenceProperties; }
simulationType RAS;
RAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }
"""

FIELD_U = """FoamFile {{ version 2.0; format ascii; class volVectorField; object U; }}
dimensions [0 1 -1 0 0 0 0];
internalField uniform (-{u} 0 0);
boundaryField {{
  inlet      {{ type fixedValue; value uniform (-{u} 0 0); }}
  outlet     {{ type outletPhaseMeanVelocity; alpha alpha.water;
               Umean {u}; value uniform (-{u} 0 0); }}
  atmosphere {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}
  bottom     {{ type slip; }}
  side1      {{ type slip; }}
  side2      {{ type slip; }}
  hull       {{ type noSlip; }}
}}
"""

FIELD_P_RGH = """FoamFile { version 2.0; format ascii; class volScalarField; object p_rgh; }
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 0;
boundaryField {
  inlet      { type fixedFluxPressure; value uniform 0; }
  outlet     { type zeroGradient; }
  atmosphere { type totalPressure; p0 uniform 0; }
  bottom     { type fixedFluxPressure; value uniform 0; }
  side1      { type fixedFluxPressure; value uniform 0; }
  side2      { type fixedFluxPressure; value uniform 0; }
  hull       { type fixedFluxPressure; value uniform 0; }
}
"""

FIELD_ALPHA = """FoamFile { version 2.0; format ascii; class volScalarField; object alpha.water; }
dimensions [0 0 0 0 0 0 0];
internalField uniform 0;
boundaryField {
  // inlet MUST inject stratified water/air: an inletOutlet with inletValue
  // $internalField (= uniform 0) injects AIR below the waterline and drains
  // the tank (first Mac smoke run: phase fraction 0.667 -> 0.486 over 5 s)
  inlet      { type exprFixedValue; value uniform 0;
               valueExpr "(pos().z() < 0) ? 1 : 0"; }
  outlet     { type variableHeightFlowRate; lowerBound 0.0; upperBound 1.0;
               value uniform 0; }
  atmosphere { type inletOutlet; inletValue uniform 0; value uniform 0; }
  bottom     { type zeroGradient; }
  side1      { type zeroGradient; }
  side2      { type zeroGradient; }
  hull       { type zeroGradient; }
}
"""

FIELD_K = """FoamFile {{ version 2.0; format ascii; class volScalarField; object k; }}
dimensions [0 2 -2 0 0 0 0];
internalField uniform {k_in};
boundaryField {{
  inlet      {{ type fixedValue; value uniform {k_in}; }}
  outlet     {{ type inletOutlet; inletValue uniform {k_in}; value uniform {k_in}; }}
  atmosphere {{ type inletOutlet; inletValue uniform {k_in}; value uniform {k_in}; }}
  bottom     {{ type slip; }}
  side1      {{ type slip; }}
  side2      {{ type slip; }}
  hull       {{ type kqRWallFunction; value uniform {k_in}; }}
}}
"""

FIELD_OMEGA = """FoamFile {{ version 2.0; format ascii; class volScalarField; object omega; }}
dimensions [0 0 -1 0 0 0 0];
internalField uniform {w_in};
boundaryField {{
  inlet      {{ type fixedValue; value uniform {w_in}; }}
  outlet     {{ type inletOutlet; inletValue uniform {w_in}; value uniform {w_in}; }}
  atmosphere {{ type inletOutlet; inletValue uniform {w_in}; value uniform {w_in}; }}
  bottom     {{ type slip; }}
  side1      {{ type slip; }}
  side2      {{ type slip; }}
  hull       {{ type omegaWallFunction; value uniform {w_in}; }}
}}
"""

FIELD_NUT = """FoamFile { version 2.0; format ascii; class volScalarField; object nut; }
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField {
  inlet      { type calculated; value uniform 0; }
  outlet     { type calculated; value uniform 0; }
  atmosphere { type calculated; value uniform 0; }
  bottom     { type calculated; value uniform 0; }
  side1      { type calculated; value uniform 0; }
  side2      { type calculated; value uniform 0; }
  hull       { type nutkWallFunction; value uniform 0; }
}
"""

SNAPPY_STUB = """FoamFile {{ version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }}
castellatedMesh true; snap true; addLayers true;
geometry {{
  hull.stl {{ type triSurfaceMesh; name hull; }}
  // free-surface slab: without it the wave field is unresolved. The bare
  // background cell at the interface is ~{fs_dz_bg:.3f} m tall against waves
  // ~0.1 m high, so the Kelvin pattern washed out entirely (measured: 5-10
  // cells per wavelength vs the >=20 standard) and the drag rode on whatever
  // the hull-local refinement happened to catch.
  freeSurface {{ type searchableBox; min ({fs_x0} {fs_y0} {fs_z0});
                                     max ({fs_x1} {fs_y1} {fs_z1}); }}
}}
castellatedMeshControls {{
  maxLocalCells 2000000; maxGlobalCells 8000000; minRefinementCells 10;
  nCellsBetweenLevels 3;
  features ( {{ file "hull.eMesh"; level 3; }} );
  refinementSurfaces {{ hull {{ level (2 3); }} }}
  refinementRegions {{ freeSurface {{ mode inside; levels ((1e15 {fs_level})); }} }}
  locationInMesh ({loc_x} 0.0 {loc_z});
  allowFreeStandingZoneFaces true; resolveFeatureAngle 30;
}}
snapControls {{ nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; }}
addLayersControls {{
  // ABSOLUTE sizing: y+ is a physical quantity, so the near-wall cell is set
  // in metres from the ITTC friction line, not as a fraction of whatever cell
  // snappy happened to leave there. relativeSizes true is what produced
  // y+ ~ 7500. Held CONSTANT across the GCI triplet so all three grids sit in
  // the wall-function's valid band -- the GCI then bounds OUTER-flow
  // discretisation with the near-wall treatment fixed, which is the honest
  // reading of it and is stated in case.info.
  relativeSizes false; layers {{ hull {{ nSurfaceLayers {n_layers}; }} }}
  expansionRatio {layer_expansion}; firstLayerThickness {first_layer:.6e};
  minThickness {min_thickness:.6e}; nGrow 0;
  featureAngle 60; slipFeatureAngle 30;
  nRelaxIter 5; nSmoothSurfaceNormals 1; nSmoothNormals 3; nSmoothThickness 10;
  // Loosened from 0.5/0.3: free-surface grading makes the cells at the
  // waterline ~20:1 anisotropic, and layer insertion refuses there. Measured
  // hull coverage 43.9% -> 46.3%; the remainder is reported by the yPlus
  // function object rather than assumed adequate.
  maxFaceThicknessRatio 0.8; maxThicknessToMedialRatio 0.6;
  minMedialAxisAngle 90; nBufferCellsNoExtrude 0; nLayerIter 50;
  nRelaxedIter 20;
}}
meshQualityControls {{ maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4;
  maxConcave 80; minVol 1e-13; minTetQuality 1e-15; minArea -1; minTwist 0.02;
  minDeterminant 0.001; minFaceWeight 0.05; minVolRatio 0.01; minTriangleTwist -1;
  nSmoothScale 4; errorReduction 0.75; }}
writeFlags (scalarLevels); mergeTolerance 1e-6;
"""


def hull_to_stl(hull: Hull, path: Path, nx: int = 80, nz: int = 16) -> str:
    """Write a WATERTIGHT ascii STL (full hull + deck + transom); sha256.

    CFD needs a closed manifold: the earlier wetted-only shell had 198 open
    edges (surfaceFeatureExtract, first Mac smoke run) and let the mesher
    reach the hull interior.
    """
    verts, tris = hull.closed_mesh(nx=nx, nz=nz)
    lines = ["solid hull"]
    for t in tris:
        p = verts[list(t)]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        nn = np.linalg.norm(n)
        n = n / nn if nn > 1e-14 else np.array([0.0, 0.0, 1.0])
        lines.append(f" facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        lines.append("  outer loop")
        for v in p:
            lines.append(f"   vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}")
        lines.append("  endloop")
        lines.append(" endfacet")
    lines.append("endsolid hull")
    data = "\n".join(lines).encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def stl_watertight_report(path: Path) -> dict:
    """Parse an ascii STL and check closed-manifoldness geometrically.

    Every undirected edge of a closed 2-manifold is shared by exactly two
    triangles. Also returns the signed enclosed volume (divergence theorem) —
    meaningful only when windings are consistently outward.
    """
    tris = []
    cur: list = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith("vertex"):
            cur.append(tuple(round(float(v), 6) for v in line.split()[1:4]))
            if len(cur) == 3:
                tris.append(tuple(cur))
                cur = []
    from collections import Counter
    edges: Counter = Counter()
    vol = 0.0
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted(e))] += 1
        va, vb, vc = np.array(a), np.array(b), np.array(c)
        vol += float(np.dot(va, np.cross(vb, vc))) / 6.0
    bad = [e for e, n in edges.items() if n != 2]
    return {"n_tris": len(tris), "open_or_nonmanifold_edges": len(bad),
            "watertight": len(bad) == 0, "signed_volume": vol}


def write_resistance_case_from_stl(stl_path: str | Path, lwl: float,
                                   speed: float, out_dir: str | Path,
                                   end_time: float = 40.0, scale: float = 1.0,
                                   np_procs: int = 8) -> dict:
    """Same case generator, but for EXTERNAL geometry (KCS/JBC calibration).

    The STL must be watertight, in metres, with the free surface at z=0 and
    the hull spanning x in [0, lwl] (translate/scale upstream if needed).
    """
    out = Path(out_dir)
    (out / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    data = Path(stl_path).read_bytes()
    (out / "constant" / "triSurface" / "hull.stl").write_bytes(data)
    stl_sha = hashlib.sha256(data).hexdigest()
    return _write_case_dicts(out, stl_sha, lwl, speed, end_time, scale, np_procs)


def write_resistance_case(hull: Hull, speed: float, out_dir: str | Path,
                          end_time: float = 40.0, scale: float = 1.0,
                          np_procs: int = 8) -> dict:
    """Generate a COMPLETE, runnable interFoam resistance case.

    scale: background-mesh refinement multiplier (1.0 / sqrt(2) steps give
    the GCI triplet). Templates are DTCHull-tutorial-derived; first-run
    tuning on the OpenFOAM machine is expected and normal.
    """
    out = Path(out_dir)
    (out / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    stl_sha = hull_to_stl(hull, out / "constant" / "triSurface" / "hull.stl")
    return _write_case_dicts(out, stl_sha, float(hull.x[-1]), speed,
                             end_time, scale, np_procs)


def _write_case_dicts(out: Path, stl_sha: str, lwl: float, speed: float,
                      end_time: float, scale: float, np_procs: int) -> dict:
    (out / "system").mkdir(parents=True, exist_ok=True)
    # Initial fields live in 0.orig and are COPIED to 0 (the OpenFOAM tutorial
    # convention). setFields rewrites 0/alpha.water as a full non-uniform field
    # sized for the snapped mesh; re-running the pipeline in that directory then
    # hands snappyHexMesh a field with the wrong cell count and it dies with an
    # FPE in markFeatureCellLevel (measured: 1.67 MB alpha.water vs 817 B
    # pristine, snappy exit 132 on a case that had meshed cleanly minutes
    # before). A case directory has to be re-runnable.
    (out / "0.orig").mkdir(parents=True, exist_ok=True)

    # Domain: towing-tank box around the hull (hull x in [0, L]), split at the
    # waterline. Depth 0.6L and air 0.25L replace the old 1.5L/0.75L: the tank
    # only has to be deep-water for the generated wave (lambda/2 = pi*U^2/g,
    # checked below), and the cells that bought 15 m of still water underneath
    # are worth far more spent on the free surface.
    # Deep water is a property of the WAVE, not of the hull: a tank shallower
    # than half a wavelength changes the dispersion relation, so the depth
    # tracks speed rather than sitting at a fixed multiple of LWL. 0.6L is
    # ample at the Fn ~ 0.26 design point; a planing-speed case deepens itself
    # instead of quietly computing shallow-water resistance and calling it
    # deep-water resistance.
    half_lambda = math.pi * speed ** 2 / 9.81
    depth = max(0.6 * lwl, 1.5 * half_lambda)

    dom = dict(x0=-2.5 * lwl, x1=2.0 * lwl, y0=-1.5 * lwl, y1=1.5 * lwl,
               z0=-depth, z1=0.25 * lwl,
               nx=max(int(round(54 * scale)), 20),
               ny=max(int(round(24 * scale)), 10),
               nzw=max(int(round(20 * scale)), 8),
               nza=max(int(round(8 * scale)), 4),
               g_water=1.0 / _Z_EXPANSION, g_air=float(_Z_EXPANSION))
    assert depth >= half_lambda, "deep-water condition violated"

    # Cell height at the interface, both sides — these should match, and they
    # set what the free-surface refinement then divides by 2**fs_level.
    dz_w = _interface_dz(abs(dom["z0"]), dom["nzw"], _Z_EXPANSION)
    dz_a = _interface_dz(dom["z1"], dom["nza"], _Z_EXPANSION)
    fs_level = 2
    fs_dz = max(dz_w, dz_a) / 2 ** fs_level
    dx = (dom["x1"] - dom["x0"]) / dom["nx"] / 2 ** fs_level
    wavelength = 2 * math.pi * speed ** 2 / 9.81
    # near-wall stack sized for the wall functions, bridging to the local
    # hull cell (background dx divided by the hull surface refinement level)
    t1 = first_layer_thickness(speed, lwl, _TARGET_YPLUS)
    hull_cell = (dom["x1"] - dom["x0"]) / dom["nx"] / 2 ** 3
    n_ideal = n_layers_to_bridge(t1, hull_cell, _LAYER_EXPANSION)
    n_layers = min(n_ideal, _MAX_LAYERS)
    dom.update(
        n_layers=n_layers, first_layer=t1, layer_expansion=_LAYER_EXPANSION,
        min_thickness=0.25 * t1,
        fs_level=fs_level, fs_dz_bg=max(dz_w, dz_a),
        # slab thick enough to hold the wave through its whole vertical travel
        fs_x0=_FS_BOX["x0"] * lwl, fs_x1=_FS_BOX["x1"] * lwl,
        fs_y0=-_FS_BOX["y"] * lwl, fs_y1=_FS_BOX["y"] * lwl,
        fs_z0=-_FS_BOX["z"] * lwl, fs_z1=_FS_BOX["z"] * lwl,
        # locationInMesh: in the air, far upstream of the hull. The old
        # (-2.0L, 0.35L) sat ABOVE the new tank roof and off a round multiple
        # of the cell size; both are mesh-generation failures.
        loc_x=-1.97 * lwl, loc_z=0.137 * lwl)

    # turbulence inlet: I = 2%, length scale 1% LWL
    k_in = 1.5 * (0.02 * speed) ** 2 + 1e-8
    w_in = k_in ** 0.5 / (0.09 ** 0.25 * 0.01 * lwl)

    sysd, cons, zero = out / "system", out / "constant", out / "0.orig"
    # Checkpoint ~10 times per run. On a machine that thermal-sleeps mid-run
    # the write interval is what you lose per nap: at 5 s of sim time that was
    # ~1.7 h of fine-grid wall time thrown away each time. purgeWrite 3 keeps
    # the disk bounded regardless.
    write_int = max(end_time / 10.0, 0.5)
    sysd.joinpath("controlDict").write_text(
        CONTROL_DICT.format(end_time=end_time, dt=0.001, write_int=write_int))
    sysd.joinpath("blockMeshDict").write_text(BLOCKMESH.format(**dom))
    sysd.joinpath("snappyHexMeshDict").write_text(SNAPPY_STUB.format(**dom))
    sysd.joinpath("fvSchemes").write_text(FV_SCHEMES)
    sysd.joinpath("fvSolution").write_text(FV_SOLUTION)
    sysd.joinpath("decomposeParDict").write_text(DECOMPOSE.format(np=np_procs))
    sysd.joinpath("surfaceFeatureExtractDict").write_text(SURFACE_FEATURES)
    sysd.joinpath("setFieldsDict").write_text(SET_FIELDS)
    cons.joinpath("transportProperties").write_text(TRANSPORT)
    cons.joinpath("g").write_text(GRAVITY)
    cons.joinpath("turbulenceProperties").write_text(TURBULENCE)
    zero.joinpath("U").write_text(FIELD_U.format(u=speed))
    zero.joinpath("p_rgh").write_text(FIELD_P_RGH)
    zero.joinpath("alpha.water").write_text(FIELD_ALPHA)
    zero.joinpath("k").write_text(FIELD_K.format(k_in=f"{k_in:.3e}"))
    zero.joinpath("omega").write_text(FIELD_OMEGA.format(w_in=f"{w_in:.3e}"))
    zero.joinpath("nut").write_text(FIELD_NUT)

    # working copy: run-case.sh restores this from 0.orig before every re-mesh
    import shutil
    if (out / "0").exists():
        shutil.rmtree(out / "0")
    shutil.copytree(zero, out / "0")

    bg_cells = dom["nx"] * dom["ny"] * (dom["nzw"] + dom["nza"])
    # Resolution receipt: the numbers that decide whether the wave field is
    # actually resolved, recorded per case so a bad triplet is diagnosable
    # from the case dir alone rather than from a post-hoc argument.
    cells_per_wave = wavelength / dx
    (out / "case.info").write_text(
        f"speed_ms={speed}\nlwl={lwl}\nscale={scale}\nstl_sha256={stl_sha}\n"
        f"cells_bg={bg_cells}\n"
        f"wavelength_m={wavelength:.4f}\ntank_depth_m={abs(dom['z0']):.4f}\n"
        f"fs_dz_m={fs_dz:.5f}\nfs_dx_m={dx:.5f}\n"
        f"cells_per_wavelength={cells_per_wave:.1f}\n"
        f"target_yplus={_TARGET_YPLUS}\nfirst_layer_m={t1:.6e}\n"
        f"n_layers={n_layers}\nn_layers_to_fully_bridge={n_ideal}\n"
        "NOTE: layers are capped for insertion success, so the stack does NOT\n"
        "  bridge to the local cell; y+ is controlled on layered faces only.\n"
        "  Check postProcessing/yPlus for what was actually achieved.\n"
        "NOTE: first-layer thickness is held constant across the GCI triplet,\n"
        "  so the GCI bounds OUTER-flow discretisation, not the wall model.\n"
        "run: navalai/cfd/run-case.sh <this-dir> <np>\n"
        "Gate 2M = KCS/JBC resistance within Tokyo-2015 scatter, per-case GCI.\n")
    return {"stl_sha256": stl_sha, "speed": speed, "end_time": end_time,
            "scale": scale, "bg_cells": bg_cells,
            "cells_per_wavelength": cells_per_wave, "fs_dz": fs_dz,
            "wavelength": wavelength, "tank_depth": abs(dom["z0"])}
