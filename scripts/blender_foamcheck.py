#!/usr/bin/env python
"""Run the REAL OpenFOAM surface tools on every STL a `blender_compare` run
produced, and report what the MESHER would be handed.

    python scripts/blender_foamcheck.py --dir data/blender

Two tools, both at the pipeline's own settings:

  surfaceCheck -checkSelfIntersection <stl>
      The bar `docs/research/STL.md` and commit b91bbf3 use. Reported as the
      tool's own words, not as a re-derivation: trimesh/PyMeshLab/Open3D all
      find ZERO self-intersections on the current hulls (b91bbf3), so a
      DISAGREEMENT here would be the interesting result and it must be able to
      show one.

  surfaceFeatureExtract with `includedAngle 150`
      Copied verbatim from `navalai/cfd/case.py::SURFACE_FEATURES` at runtime
      rather than restated, so this cannot drift from what the case writes.
      What snappy is handed as `hull.eMesh` and refines to `_HULL_REFINE[1]`.

AN UNPARSEABLE RESULT IS A REFUSAL, NOT A ZERO. Every count here is None when
the tool's output could not be read, and `--strict` makes that an exit 1. This
repository has shipped `${VAR:-0}` against a bar of 20 and a `not
ledger_has(...)` that was TRUE when there was no ledger; a missing measurement
must never arrive as a good score (docs/LESSONS.md defect class 1).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

OPENFOAM = "openfoam"


def _run(args: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run([OPENFOAM] + args, cwd=str(cwd), capture_output=True,
                       text=True, timeout=3600)
    return p.returncode, p.stdout + p.stderr


def surface_check(stl: Path) -> dict:
    """`surfaceCheck -checkSelfIntersection`, parsed."""
    rc, out = _run(["surfaceCheck", "-checkSelfIntersection", stl.name],
                   stl.parent)
    res: dict = {"rc": rc, "n_self_intersection_locations": None,
                 "n_illegal_triangles": None, "n_open_edges": None,
                 "n_regions": None, "n_zones": None, "closed": None}
    m = re.search(r"Surface is (\w+)\s*(?:and\s*)?(\w+)?", out)
    if re.search(r"Surface is closed", out):
        res["closed"] = True
    elif re.search(r"Surface is not closed", out):
        res["closed"] = False
    # The tool's own wording, verified against a real run rather than
    # guessed: "Surface is self-intersecting at 166 locations." / "Surface is
    # not self-intersecting". A first pass looked for "Found N intersecting"
    # and matched neither, so every count came back None -- which is what the
    # None default is for.
    m = re.search(r"Surface is self-intersecting at (\d+) location", out)
    if m:
        res["n_self_intersection_locations"] = int(m.group(1))
    elif re.search(r"Surface is not self-intersecting", out):
        res["n_self_intersection_locations"] = 0
    m = re.search(r"Surface has (\d+) illegal triangles", out)
    if m:
        res["n_illegal_triangles"] = int(m.group(1))
    elif re.search(r"Surface has no illegal triangles", out):
        res["n_illegal_triangles"] = 0
    m = re.search(r"Number of zones[^:]*:\s*(\d+)", out)
    if m:
        res["n_zones"] = int(m.group(1))
    m = re.search(r"Number of unconnected parts\s*:\s*(\d+)", out)
    if m:
        res["n_regions"] = int(m.group(1))
    m = re.search(r"boundary edges\s*:\s*(\d+)", out)
    if m:
        res["n_open_edges"] = int(m.group(1))
    res["tail"] = "\n".join(out.splitlines()[-25:])
    return res


def feature_extract(stl: Path, case_dict: str) -> dict:
    """`surfaceFeatureExtract` at the pipeline's includedAngle."""
    with tempfile.TemporaryDirectory() as td:
        case = Path(td)
        (case / "system").mkdir()
        (case / "constant" / "triSurface").mkdir(parents=True)
        shutil.copy(stl, case / "constant" / "triSurface" / "hull.stl")
        (case / "system" / "surfaceFeatureExtractDict").write_text(case_dict)
        (case / "system" / "controlDict").write_text(
            "FoamFile { version 2.0; format ascii; class dictionary; "
            "object controlDict; }\napplication interFoam;\nstartTime 0;\n"
            "endTime 0;\ndeltaT 1;\nwriteInterval 1;\n")
        rc, out = _run(["surfaceFeatureExtract"], case)
        res: dict = {"rc": rc, "n_feature_points": None,
                     "n_feature_edges": None, "n_internal_edges": None,
                     "n_external_edges": None, "n_region_edges": None}
        # THE "INITIAL FEATURE SET" BLOCK, not the final one. The tool prints
        # both, with the same field names and different numbers -- on hull 14's
        # current STL, initial points 6 / final points 2825 -- so a regex over
        # the whole log reads whichever comes first and the two are not
        # comparable. Commit bbf1a47's "211 feature points and 71 internal
        # edges -> 6 and 0" is the INITIAL block, which is also the set written
        # to hull.eMesh, so that is the one parsed here. Same defect shape as
        # the layer table snappy prints twice.
        blk = re.search(r"Initial Feature set:(.*?)Final Feature set:",
                        out, re.S)
        if blk:
            b = blk.group(1)
            for key, pat in (("n_feature_points", r"points\s*:\s*(\d+)"),
                             ("n_feature_edges", r"edges\s*:\s*(\d+)"),
                             ("n_internal_edges", r"internal edges\s*:\s*(\d+)"),
                             ("n_external_edges", r"external edges\s*:\s*(\d+)"),
                             ("n_region_edges", r"region edges\s*:\s*(\d+)")):
                m = re.search(pat, b)
                if m:
                    res[key] = int(m.group(1))
        res["tail"] = "\n".join(out.splitlines()[-30:])
        return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/blender")
    ap.add_argument("--glob", default="*.stl")
    ap.add_argument("--exclude", default=None,
                    help="substring; matching files are SKIPPED and "
                         "named in the output, never silently dropped")
    ap.add_argument("--out", default=None)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    from navalai.cfd.case import SURFACE_FEATURES

    d = Path(a.dir)
    rows = []
    skipped = [s.name for s in sorted(d.glob(a.glob))
               if a.exclude and a.exclude in s.name]
    for s in skipped:
        print(f"SKIPPED (--exclude {a.exclude}): {s}")
    for stl in sorted(d.glob(a.glob)):
        if a.exclude and a.exclude in stl.name:
            continue
        sc = surface_check(stl)
        fe = feature_extract(stl, SURFACE_FEATURES)
        rows.append({"stl": stl.name, "bytes": stl.stat().st_size,
                     "surfaceCheck": sc, "surfaceFeatureExtract": fe})
        print(f"{stl.name:<44} closed={sc['closed']!s:<5} "
              f"selfX={sc['n_self_intersection_locations']} "
              f"illegal={sc['n_illegal_triangles']} "
              f"featPts={fe['n_feature_points']} "
              f"featEdges={fe['n_feature_edges']} "
              f"internal={fe['n_internal_edges']}")
    if a.out:
        Path(a.out).write_text(json.dumps(rows, indent=1))
    if a.strict:
        for r in rows:
            if (r["surfaceCheck"]["n_self_intersection_locations"] is None
                    or r["surfaceFeatureExtract"]["n_feature_points"] is None):
                print(f"UNREADABLE: {r['stl']}")
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
