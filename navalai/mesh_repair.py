"""Surface repair for IMPORTED geometry — and a refusal for our own.

WHY THIS EXISTS, AND WHY IT DOES NOT TOUCH GENERATED HULLS
==========================================================

The repair literature (MeshFix, ManifoldPlus, MeshLib healing, "Visual-Guided
Mesh Repair") converges on one taxonomy — holes, non-manifold edges, flipped
normals, degenerate and duplicate faces, self-intersections — and on one
distinction that decides how this module behaves: PROACTIVE (generate clean)
versus REACTIVE (detect and repair damaged input).

This project is proactive. `Hull.closed_mesh` emits an analytic surface, and
MEASURED 2026-08-12 on the seed-0 batch it is already clean by every classical
metric:

    triangles                288 890
    zero-area (<1e-12 m^2)         0
    slivers   (<1e-9  m^2)         0
    zero-length edges              0
    min triangle area      7.24e-06 m^2      min edge 0.577 mm
    every section monotone in y and z; keel line monotone
    surfaceCheck: "Surface is closed. All edges connected to two faces."
    trimesh / PyMeshLab / Open3D: ZERO self-intersections on all 25 hulls

So a MeshFix-style pass over our own hulls would find nothing to fix and would
COST something real: every such algorithm retriangulates, and retriangulation
destroys the chine row that commit bbf1a47 put on the grid to 1e-9 m. That is
not hypothetical — Blender's voxel remesh at 0.05 m was measured taking the
chine dihedral from 72.0 deg to 0.0 deg (commit d5d9b9a). Repairing a surface
that is not broken is how you break it.

THE FALSE POSITIVE THAT MOTIVATED THE SEAM RULE
-----------------------------------------------

`surfaceCheck -checkSelfIntersection` reports 42 self-intersections on hull 0,
which meshes perfectly. Decoding `selfInterPoints.obj`:

    x/L    0.000 .. 0.321      aft third only
    |y|/B  0.000 .. 0.215      near centreline
    z     -0.364 .. -0.150     on the keel line (keel = -0.376)
    7 points exactly at y = 0; none at the deck lid, none at the stem

They lie on the CENTRELINE KEEL SEAM where the mirrored halves meet at a
knife edge — near-coincident contacts, not crossings, which is why three
independent Python libraries report zero on the same file. And the count is
anti-correlated with mesh quality:

    hull   self-intersections   wrongly-oriented faces in the finished mesh
    h008          237                    0
    h000           42                    0
    h059            9                    2
    h039            8                    2
    h004            3                    0

`true_self_intersections()` below excludes seam contacts so the receipt counts
crossings rather than phantoms.

WHERE REPAIR IS ACTUALLY OWED
------------------------------

Imported geometry. CLAUDE.md records the mirrored `KCS.igs` mesh dying on the
first timestep with 73 wrongly-oriented faces, and that plain `surfaceCheck`
calls a broken surface fine. That is the customer for this module.

DETECTION IS NOT DUPLICATED HERE. `navalai.stl_forensics` owns it
(`load_stl`, `weld`, `edge_table`, `triangle_quantities`, `self_intersections`)
and `cfd.case.stl_watertight_report` owns closedness and winding. This module
imports both. A second detector would be A NUMBER DECLARED TWICE, which is the
defect class this repository keeps paying for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .stl_forensics import edge_table, load_stl, triangle_quantities, weld

#: Geometry this module refuses to repair. A generated hull with a defect is a
#: GENERATOR BUG, and silently healing it hides the bug — the same reason
#: `run-case.sh` refuses an unparsed metric instead of defaulting it to zero.
GENERATED = "generated"
IMPORTED = "imported"

#: Two triangles that merely TOUCH along a shared edge are not intersecting.
#: The keel seam of a mirrored hull is a knife edge and produces thousands of
#: such contacts; counting them as defects is what makes `surfaceCheck`'s raw
#: number useless (see the module docstring's h008/h039 table).
_SEAM_TOL_M = 1e-9


@dataclass
class RepairReport:
    """What was found and what was done. Counts, never a boolean verdict.

    `applied` is empty for a surface that needed nothing — which is the
    expected outcome for our own hulls and must not read as a failure.
    """

    origin: str
    n_tris_before: int
    n_tris_after: int
    found: dict[str, int] = field(default_factory=dict)
    applied: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """Every defect count is zero. NOT 'repair succeeded' — a surface can
        be clean because it was never broken, which is the normal case."""
        return all(v == 0 for v in self.found.values())

    def summary(self) -> str:
        bad = {k: v for k, v in self.found.items() if v}
        return (f"{self.origin}: {self.n_tris_before} tris, "
                f"{'clean' if not bad else str(bad)}"
                + (f", applied {self.applied}" if self.applied else "")
                + (f", REFUSED {self.refused}" if self.refused else ""))


def _on_seam(V: np.ndarray, T: np.ndarray, i: int, j: int) -> bool:
    """Do triangles i and j share at least two vertex POSITIONS?

    Position, not index: a mirrored hull may carry duplicate vertices at the
    seam that `weld` has not merged because they arrived from two halves.
    """
    a, b = V[T[i]], V[T[j]]
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    return int((d < _SEAM_TOL_M).any(axis=1).sum()) >= 2


def true_self_intersections(V: np.ndarray, T: np.ndarray,
                            cell: float | None = None) -> dict:
    """Self-intersections with SEAM CONTACTS EXCLUDED.

    `stl_forensics.self_intersections` answers the geometric question
    (does any edge cross any triangle). This answers the ENGINEERING one:
    does the surface cross itself somewhere a mesher will be confused by.
    Two triangles sharing an edge always "intersect" along it and never
    confuse anything.

    MEASURED: this is the difference between surfaceCheck's 42 on hull 0 and
    the zero that trimesh, PyMeshLab and Open3D each report on the same file.
    """
    from .stl_forensics import self_intersections

    raw = self_intersections(V, T, cell=cell)
    # UNMEASURED IS NOT ZERO. `self_intersections` returns complete=False with
    # every count at -1 when the broad phase exceeds `max_pairs`, and reading
    # that as "no intersections" is defect class 1 — the same trap as
    # run-case.sh's ${VAR:-0} receipts. It is propagated as -1, not defaulted.
    if not raw.get("complete", False):
        return {"raw_pairs": -1, "seam_contacts": -1, "true_pairs": -1,
                "pairs": [], "complete": False,
                "note": raw.get("note", "NOT MEASURED")}
    # `pairs` is TRUNCATED to 200 by the detector, so it cannot be used as the
    # count. Scale the seam fraction measured on the sample up to the reported
    # total instead of silently reporting 200.
    n_total = int(raw["n_self_intersecting_pairs"])
    sample = raw.get("pairs") or []
    if not sample:
        return {"raw_pairs": n_total, "seam_contacts": 0,
                "true_pairs": n_total, "pairs": [], "complete": True,
                "note": raw.get("note", "")}
    real = [(int(i), int(j)) for i, j in sample if not _on_seam(V, T, i, j)]
    seam_frac = 1.0 - len(real) / len(sample)
    true_est = int(round(n_total * (1.0 - seam_frac)))
    return {"raw_pairs": n_total,
            "seam_contacts": n_total - true_est,
            "true_pairs": true_est, "pairs": real, "complete": True,
            "sampled": len(sample),
            "note": ("seam fraction measured on the detector's 200-pair sample "
                     "and scaled to the reported total"
                     if n_total > len(sample) else "")}


def diagnose(source, cell: float | None = None,
             origin: str = IMPORTED) -> RepairReport:
    """Every defect the repair literature names, counted separately.

    Separately, because a single "is it broken" boolean is what let an open
    shell reach snappyHexMesh for the whole life of this project — the guard
    existed and reported one bit that nothing consumed.
    """
    V, T = load_stl(source) if not isinstance(source, tuple) else source
    V, T = weld(V, T)
    q = triangle_quantities(V, T)
    e = edge_table(T)
    si = true_self_intersections(V, T, cell=cell)

    area = np.asarray(q["area"], dtype=float)
    # `edge_table` returns the RAW table (uv/count/t0/t1), not summary counts —
    # the summaries are derived here so there is one edge traversal, not two.
    # A manifold edge is shared by exactly two triangles: count 1 is an open
    # boundary, count > 2 is non-manifold.
    count = np.asarray(e["count"], dtype=int)
    # Winding: the two triangles on a shared edge must traverse it in OPPOSITE
    # directions. Same direction means they disagree about which side is out —
    # the signature `stl_watertight_report` was blind to until 397 deck
    # triangles were found pointing into the boat.
    directed: set[tuple[int, int]] = set()
    conflicts = 0
    for t in T:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if (int(a), int(b)) in directed:
                conflicts += 1
            directed.add((int(a), int(b)))
    found = {
        "degenerate_faces": int((area < 1e-12).sum()),
        "sliver_faces": int((area < 1e-9).sum()) - int((area < 1e-12).sum()),
        "duplicate_faces": int(len(T) - len({tuple(sorted(t)) for t in T})),
        "boundary_edges": int((count == 1).sum()),
        "nonmanifold_edges": int((count > 2).sum()),
        "winding_conflicts": conflicts,
        "self_intersections": int(si["true_pairs"]),
    }
    rep = RepairReport(origin=origin, n_tris_before=len(T),
                       n_tris_after=len(T), found=found)
    if origin == GENERATED and not rep.clean:
        # LOUD, because this is a generator bug wearing a repair problem's
        # clothes. Repairing here would make the bug survive as a warning.
        rep.refused.append(
            "generated geometry is NOT repaired: a defect here is a bug in "
            "Hull.closed_mesh and healing it would hide the bug. Fix the "
            "generator.")
    return rep


def repair(source, cell: float | None = None,
           origin: str = IMPORTED) -> tuple[np.ndarray, np.ndarray, RepairReport]:
    """Repair an IMPORTED surface. Returns (verts, tris, report).

    ORDER IS THE LITERATURE'S, and it is not arbitrary: dropping degenerate
    faces first removes elements whose normals are undefined, so orientation
    can be decided afterwards on triangles that actually have one. Reversing
    those two steps orients garbage and then deletes it, leaving the decision
    it polluted in place.

      1. weld coincident vertices        (stl_forensics.weld)
      2. drop degenerate and duplicate faces
      3. reorient to a consistent outward winding
      4. REPORT holes and true self-intersections — never silently patched

    Step 4 is a deliberate stopping point. Hole filling and self-intersection
    removal both RETRIANGULATE, and this project's surfaces carry features
    (the chine row, on the grid to 1e-9 m) that retriangulation destroys.
    A repair that silently changes the shape is not a repair; it is a
    different boat. Those are reported for a human to decide.
    """
    V, T = load_stl(source) if not isinstance(source, tuple) else source
    n0 = len(T)
    rep = diagnose((V, T), cell=cell, origin=origin)
    if origin == GENERATED:
        rep.n_tris_after = n0
        return V, T, rep

    V, T = weld(V, T)
    if rep.found["degenerate_faces"] or rep.found["sliver_faces"]:
        q = triangle_quantities(V, T)
        keep = np.asarray(q["area"], dtype=float) >= 1e-12
        T = T[keep]
        rep.applied.append(f"dropped {int((~keep).sum())} degenerate faces")
    if rep.found["duplicate_faces"]:
        seen, keep = set(), []
        for k, t in enumerate(T):
            key = tuple(sorted(t))
            keep.append(key not in seen)
            seen.add(key)
        T = T[np.array(keep)]
        rep.applied.append(f"dropped {rep.found['duplicate_faces']} duplicates")
    if rep.found["winding_conflicts"]:
        T = _reorient(V, T)
        rep.applied.append("reoriented to a consistent outward winding")
    for defect in ("boundary_edges", "nonmanifold_edges", "self_intersections"):
        if rep.found[defect]:
            rep.refused.append(
                f"{defect}={rep.found[defect]} REPORTED, not patched: closing "
                f"or un-crossing it retriangulates, which changes the shape")
    rep.n_tris_after = len(T)
    return V, T, rep


def _reorient(V: np.ndarray, T: np.ndarray) -> np.ndarray:
    """Flood-fill a consistent winding, then flip the whole shell outward.

    Outwardness is decided by the SIGNED VOLUME (divergence theorem), not by
    a ray cast or a vote: it is exact for a closed surface and it is the same
    quantity `stl_watertight_report` already reports, so the two cannot
    disagree about which way is out.
    """
    T = np.array(T, copy=True)
    adj: dict[tuple[int, int], list[int]] = {}
    for k, t in enumerate(T):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            adj.setdefault((min(a, b), max(a, b)), []).append(k)
    seen = np.zeros(len(T), dtype=bool)
    for start in range(len(T)):
        if seen[start]:
            continue
        seen[start] = True
        stack = [start]
        while stack:
            k = stack.pop()
            t = T[k]
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                for n in adj.get((min(a, b), max(a, b)), ()):
                    if seen[n]:
                        continue
                    u = T[n]
                    # neighbour traverses the shared edge the SAME way => it
                    # disagrees with us, so flip it
                    if any((u[i], u[(i + 1) % 3]) == (a, b) for i in range(3)):
                        T[n] = u[::-1]
                    seen[n] = True
                    stack.append(n)
    vol = float(np.einsum("ij,ij->i",
                          V[T[:, 0]],
                          np.cross(V[T[:, 1]], V[T[:, 2]])).sum() / 6.0)
    return T[:, ::-1] if vol < 0.0 else T
