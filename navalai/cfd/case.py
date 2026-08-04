"""OpenFOAM resistance-case generator (interFoam free-surface, snappyHexMesh).

Deterministic: same hull + same settings -> byte-identical case directory,
so the case dir hash goes into provenance. Runner: cfd/run-case.sh.
GATE STATUS: METAL-GATED — requires a machine with OpenFOAM (.com or .org
2306+); this box has none, so Gate 3 (KCS/JBC calibration) stays RED here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from ..geometry import Hull

CONTROL_DICT = """FoamFile {{ version 2.0; format ascii; class dictionary; object controlDict; }}
application     interFoam;
startFrom       startTime;  startTime 0;
stopAt          endTime;    endTime {end_time};
deltaT          {dt};
writeControl    adjustableRunTime;  writeInterval {write_int};
purgeWrite      3;
adjustTimeStep  yes;  maxCo 5;  maxAlphaCo 5;  maxDeltaT 0.1;
functions {{
  forces {{
    type forces; libs (forces); patches (hull);
    rho rhoInf; rhoInf 998.8; CofR (0 0 0);
    writeControl timeStep; writeInterval 10;
  }}
}}
"""

BLOCKMESH = """FoamFile {{ version 2.0; format ascii; class dictionary; object blockMeshDict; }}
scale 1;
vertices (
  ({x0} {y0} {z0}) ({x1} {y0} {z0}) ({x1} {y1} {z0}) ({x0} {y1} {z0})
  ({x0} {y0} {z1}) ({x1} {y0} {z1}) ({x1} {y1} {z1}) ({x0} {y1} {z1})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1) );
boundary (
  inlet      {{ type patch; faces ((1 2 6 5)); }}
  outlet     {{ type patch; faces ((0 4 7 3)); }}
  atmosphere {{ type patch; faces ((4 5 6 7)); }}
  bottom     {{ type wall;  faces ((0 3 2 1)); }}
  side1      {{ type wall;  faces ((0 1 5 4)); }}
  side2      {{ type wall;  faces ((3 7 6 2)); }}
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
  momentumPredictor no; nOuterCorrectors 1; nCorrectors 3;
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
  writeObj yes;
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
  inlet      { type inletOutlet; inletValue $internalField; value $internalField; }
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
geometry {{ hull.stl {{ type triSurfaceMesh; name hull; }} }}
castellatedMeshControls {{
  maxLocalCells 2000000; maxGlobalCells 8000000; minRefinementCells 10;
  nCellsBetweenLevels 3;
  features ( {{ file "hull.eMesh"; level 3; }} );
  refinementSurfaces {{ hull {{ level (2 3); }} }}
  refinementRegions {{}}
  locationInMesh ({loc_x} 0.0 {loc_z});
  allowFreeStandingZoneFaces true; resolveFeatureAngle 30;
}}
snapControls {{ nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; }}
addLayersControls {{
  relativeSizes true; layers {{ hull {{ nSurfaceLayers 3; }} }}
  expansionRatio 1.25; finalLayerThickness 0.4; minThickness 0.05; nGrow 0;
  featureAngle 60; nRelaxIter 5;
}}
meshQualityControls {{ maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4;
  maxConcave 80; minVol 1e-13; minTetQuality 1e-15; minArea -1; minTwist 0.02;
  minDeterminant 0.001; minFaceWeight 0.05; minVolRatio 0.01; minTriangleTwist -1;
  nSmoothScale 4; errorReduction 0.75; }}
writeFlags (scalarLevels); mergeTolerance 1e-6;
"""


def hull_to_stl(hull: Hull, path: Path, nx: int = 80, nz: int = 20) -> str:
    """Write a binary-ascii STL of the full hull surface; returns sha256."""
    verts, faces = hull.panel_mesh(nx=nx, nz=nz)
    lines = ["solid hull"]
    for f in faces:
        for tri in ((f[0], f[1], f[2]), (f[0], f[2], f[3])):
            p = verts[list(tri)]
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


def write_resistance_case(hull: Hull, speed: float, out_dir: str | Path,
                          end_time: float = 40.0, scale: float = 1.0,
                          np_procs: int = 8) -> dict:
    """Generate a COMPLETE, runnable interFoam resistance case.

    scale: background-mesh refinement multiplier (1.0 / sqrt(2) steps give
    the GCI triplet). Templates are DTCHull-tutorial-derived; first-run
    tuning on the OpenFOAM machine is expected and normal.
    """
    out = Path(out_dir)
    (out / "system").mkdir(parents=True, exist_ok=True)
    (out / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    (out / "0").mkdir(parents=True, exist_ok=True)
    stl_sha = hull_to_stl(hull, out / "constant" / "triSurface" / "hull.stl")
    lwl = float(hull.x[-1])

    # domain: generous towing-tank box around the hull (hull x in [0, L])
    dom = dict(x0=-2.5 * lwl, x1=2.0 * lwl, y0=-1.5 * lwl, y1=1.5 * lwl,
               z0=-1.5 * lwl, z1=0.75 * lwl,
               nx=max(int(54 * scale), 20), ny=max(int(24 * scale), 10),
               nz=max(int(18 * scale), 8))

    # turbulence inlet: I = 2%, length scale 1% LWL
    k_in = 1.5 * (0.02 * speed) ** 2 + 1e-8
    w_in = k_in ** 0.5 / (0.09 ** 0.25 * 0.01 * lwl)

    sysd, cons, zero = out / "system", out / "constant", out / "0"
    sysd.joinpath("controlDict").write_text(
        CONTROL_DICT.format(end_time=end_time, dt=0.001, write_int=5.0))
    sysd.joinpath("blockMeshDict").write_text(BLOCKMESH.format(**dom))
    sysd.joinpath("snappyHexMeshDict").write_text(
        SNAPPY_STUB.format(loc_x=-2.0 * lwl, loc_z=0.35 * lwl))
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

    (out / "case.info").write_text(
        f"speed_ms={speed}\nlwl={lwl}\nscale={scale}\nstl_sha256={stl_sha}\n"
        f"cells_bg={dom['nx'] * dom['ny'] * dom['nz']}\n"
        "run: navalai/cfd/run-case.sh <this-dir> <np>\n"
        "Gate 2M = KCS/JBC resistance within Tokyo-2015 scatter, per-case GCI.\n")
    return {"stl_sha256": stl_sha, "speed": speed, "end_time": end_time,
            "scale": scale, "bg_cells": dom["nx"] * dom["ny"] * dom["nz"]}
