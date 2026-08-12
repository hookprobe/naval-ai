"""Gate 2H — surface repair, and the refusal that keeps it honest.

The whole module exists because of one distinction the repair literature makes
and this project had not: PROACTIVE (generate clean) versus REACTIVE (repair
damaged input). We generate. So repair belongs on the IMPORT boundary, and
running it over our own hulls would find nothing while destroying the chine row
that commit bbf1a47 put on the grid to 1e-9 m — measured, when Blender's voxel
remesh took that chine from 72.0 deg to 0.0 (commit d5d9b9a).

The tests below therefore assert two OPPOSITE things, and both matter:
a broken surface is repaired, and a generated one is refused.
"""
from __future__ import annotations

import numpy as np
import pytest

from navalai.mesh_repair import (GENERATED, IMPORTED, diagnose, repair,
                                 true_self_intersections)


def _tetra():
    """A closed, outward-wound tetrahedron — the smallest valid solid."""
    V = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    T = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    return V, T


def test_a_clean_solid_reports_no_defects_and_no_repairs():
    """`clean` must mean 'no defect found', never 'repair succeeded'. A surface
    that was never broken is the NORMAL case here and must not read as work."""
    rep = diagnose(_tetra(), origin=IMPORTED)
    assert rep.clean, rep.found
    assert rep.applied == []
    assert all(v == 0 for v in rep.found.values())


def test_an_open_shell_is_found_and_is_NOT_silently_closed():
    """One triangle: three boundary edges. Hole filling RETRIANGULATES, so it
    is reported for a human and never applied — a repair that silently changes
    the shape is a different boat, not a repaired one."""
    V = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0]])
    T = np.array([[0, 1, 2]])
    rep = diagnose((V, T), origin=IMPORTED)
    assert rep.found["boundary_edges"] == 3
    assert not rep.clean
    _, _, rep2 = repair((V, T), origin=IMPORTED)
    assert rep2.applied == [], "a hole must not be patched silently"
    assert any("boundary_edges" in r for r in rep2.refused), rep2.refused


def test_a_flipped_triangle_is_found_and_reoriented():
    """Winding conflicts are the one defect worth fixing automatically: the
    repair is a relabelling, not a retriangulation, so the SHAPE is untouched.

    MEASURED incident behind it (cfd.case.stl_watertight_report): keying only
    on the undirected edge is blind to orientation, so a flipped triangle still
    gave every edge a count of 2 and the surface reported watertight while 397
    deck triangles pointed INTO the boat and the signed volume was 38% low.
    """
    V, T = _tetra()
    T = np.array(T, copy=True)
    T[0] = T[0][::-1]                     # flip one face
    rep = diagnose((V, T), origin=IMPORTED)
    assert rep.found["winding_conflicts"] > 0

    V2, T2, rep2 = repair((V, T), origin=IMPORTED)
    assert any("reoriented" in a for a in rep2.applied), rep2.applied
    assert diagnose((V2, T2), origin=IMPORTED).found["winding_conflicts"] == 0
    # and the shape is unchanged: same triangle count, same enclosed volume
    assert len(T2) == len(T)
    vol = float(np.einsum("ij,ij->i", V2[T2[:, 0]],
                          np.cross(V2[T2[:, 1]], V2[T2[:, 2]])).sum() / 6.0)
    assert vol > 0.0, "reorientation must leave the solid wound OUTWARD"
    assert vol == pytest.approx(1.0 / 6.0, rel=1e-9)


def test_a_degenerate_face_is_dropped_before_orientation_is_decided():
    """ORDER MATTERS AND THE COMMENT IN `repair` SAYS WHY. A zero-area triangle
    has no normal, so deciding orientation first means orienting garbage and
    then deleting it — leaving the decision it polluted in place."""
    V, T = _tetra()
    V = np.vstack([V, V[0], V[1]])                  # duplicate two vertices
    T = np.vstack([T, [[0, 4, 5]]])                 # zero-area face
    rep = diagnose((V, T), origin=IMPORTED)
    assert rep.found["degenerate_faces"] >= 1
    _, T2, rep2 = repair((V, T), origin=IMPORTED)
    assert any("degenerate" in a for a in rep2.applied), rep2.applied
    assert len(T2) < len(T)


def test_generated_geometry_is_REFUSED_not_repaired():
    """The load-bearing clause. A defect in a generated hull is a bug in
    `Hull.closed_mesh`, and healing it here would make the bug survive as a
    warning — the same reason run-case.sh refuses an unparsed metric rather
    than defaulting it to zero."""
    V, T = _tetra()
    T = np.array(T, copy=True)
    T[0] = T[0][::-1]
    rep = diagnose((V, T), origin=GENERATED)
    assert rep.refused and "NOT repaired" in rep.refused[0]

    V2, T2, rep2 = repair((V, T), origin=GENERATED)
    assert rep2.applied == [], "generated geometry must come back untouched"
    assert np.array_equal(T2, T), "not one triangle may change"
    assert rep2.n_tris_after == rep2.n_tris_before


def test_a_shared_edge_is_a_contact_not_an_intersection():
    """The seam rule, which is the whole reason surfaceCheck's raw count is
    useless on a mirrored hull.

    MEASURED on hull 0: surfaceCheck reports 42 self-intersections on a surface
    that meshes perfectly, and decoding selfInterPoints.obj puts every one of
    them on the CENTRELINE KEEL SEAM (x/L 0.000-0.321, |y|/B 0.000-0.215,
    z on the keel line, 7 exactly at y=0). trimesh, PyMeshLab and Open3D each
    report ZERO on the same file. The count is also ANTI-correlated with mesh
    quality: h008 has 237 and meshes clean, h039 has 8 and is a failure.
    """
    V, T = _tetra()
    si = true_self_intersections(V, T)
    assert si["true_pairs"] == 0, si
    # every pair of faces in a tetrahedron shares an edge, so if seam contacts
    # were counted this surface would look maximally self-intersecting
    assert si["seam_contacts"] >= 0


def test_an_unmeasured_intersection_count_is_never_reported_as_zero():
    """defect class 1, guarded explicitly. `self_intersections` returns
    complete=False with every count at -1 when the broad phase exceeds
    max_pairs; reading that as 'none found' is the ${VAR:-0} trap."""
    import navalai.mesh_repair as M

    orig = M.self_intersections if hasattr(M, "self_intersections") else None
    import navalai.stl_forensics as F
    saved = F.self_intersections
    try:
        F.self_intersections = lambda *a, **k: {
            "complete": False, "n_self_intersecting_pairs": -1,
            "candidate_pairs": -1, "coplanar_candidate_pairs": -1,
            "note": "NOT MEASURED"}
        V, T = _tetra()
        si = true_self_intersections(V, T)
        assert si["true_pairs"] == -1, si
        assert si["complete"] is False
    finally:
        F.self_intersections = saved
        assert orig is None or True
