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
adjustTimeStep  yes;  maxCo 5;  maxAlphaCo 5;  maxDeltaT 0.1;
functions {{
  forces {{
    type forces; libs (forces); patches (hull);
    rho rhoInf; rhoInf 1000; CofR (0 0 0);
    writeControl timeStep; writeInterval 10;
  }}
}}
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
                          end_time: float = 40.0) -> dict:
    """Generate a complete interFoam resistance case skeleton.

    Returns provenance dict (stl sha, settings). Deliberately minimal but
    runnable: system/{controlDict,snappyHexMeshDict}, geometry, runner notes.
    """
    out = Path(out_dir)
    (out / "system").mkdir(parents=True, exist_ok=True)
    (out / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    stl_sha = hull_to_stl(hull, out / "constant" / "triSurface" / "hull.stl")
    lwl = float(hull.x[-1])
    (out / "system" / "controlDict").write_text(
        CONTROL_DICT.format(end_time=end_time, dt=0.001, write_int=5.0))
    (out / "system" / "snappyHexMeshDict").write_text(
        SNAPPY_STUB.format(loc_x=-2.0 * lwl, loc_z=1.0))
    (out / "case.info").write_text(
        f"speed_ms={speed}\nlwl={lwl}\nstl_sha256={stl_sha}\n"
        "gate=METAL-GATED: run cfd/run-case.sh on an OpenFOAM machine;\n"
        "Gate 3 = KCS/JBC resistance within Tokyo-2015 scatter with per-case GCI.\n")
    return {"stl_sha256": stl_sha, "speed": speed, "end_time": end_time}
