"""Gate rows for `navalai/stl_forensics.py`.

THE INCIDENT THIS SUITE NAMES. Four grammar hulls with different mesh outcomes
were handed to `stl_watertight_report` and all four came back identical —
5244 triangles, watertight True, outward True, 0 open/non-manifold edges,
0 winding conflicts — across a 3x range of enclosed volume. That report is
correct and it is blind by construction: it keys on undirected edge counts, so
a surface that passes THROUGH ITSELF still gives every edge exactly two faces.
`test_watertight_is_blind_to_a_self_intersection` builds the smallest surface
that makes the point and asserts BOTH halves of it — the old report passes, the
new one fires.

Every threshold-shaped function here is fed the VERBATIM input it must reject
(docs/LESSONS.md defect class 3: a test showing a guard accepts a good case
proves nothing about rejection), and every "could not measure" path is asserted
to return a REFUSAL rather than a zero (defect class 1).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from navalai import stl_forensics as F
from navalai.cfd.case import hull_to_stl, stl_resolution, stl_watertight_report
from navalai.geometry import Hull

ROOT = Path(__file__).resolve().parents[1]


def _tetra(offset=(0.0, 0.0, 0.0), s=1.0):
    """A closed, manifold, outward-wound tetrahedron: (verts, tris)."""
    v = np.array([[0.0, 0.0, 0.0], [s, 0.0, 0.0], [0.0, s, 0.0], [0.0, 0.0, s]])
    v = v + np.asarray(offset, dtype=float)
    t = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    return v, t


def _write_ascii_stl(path, V, T):
    lines = ["solid t"]
    for tri in T:
        p = V[list(tri)]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        nn = np.linalg.norm(n)
        n = n / nn if nn > 1e-14 else np.array([0.0, 0.0, 1.0])
        lines.append(f" facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        lines.append("  outer loop")
        for q in p:
            lines.append(f"   vertex {q[0]:.6e} {q[1]:.6e} {q[2]:.6e}")
        lines += ["  endloop", " endfacet"]
    lines.append("endsolid t")
    Path(path).write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# The motivating claim: watertight != valid
# ---------------------------------------------------------------------------


def test_watertight_is_blind_to_a_self_intersection(tmp_path):
    """VERBATIM the case the module exists for.

    Two tetrahedra written as ONE solid, overlapping in space. Every undirected
    edge still has exactly two incident triangles and every winding is still
    outward, so `stl_watertight_report` — correctly, within its contract —
    returns watertight True / outward True / 0 open edges / 0 winding
    conflicts. The surface nevertheless passes through itself, which is a mesh
    input snappyHexMesh cannot resolve. The point of the assertion is that BOTH
    statements are true at once.
    """
    va, ta = _tetra((0.0, 0.0, 0.0), 1.0)
    vb, tb = _tetra((0.2, 0.2, 0.2), 1.0)
    V = np.vstack([va, vb])
    T = np.vstack([ta, tb + len(va)])
    stl = tmp_path / "two_tetra.stl"
    _write_ascii_stl(stl, V, T)

    old = stl_watertight_report(stl)
    assert old["watertight"] is True and old["outward"] is True
    assert old["open_or_nonmanifold_edges"] == 0
    assert old["winding_conflicts"] == 0

    Vw, Tw = F.load_stl(stl)
    si = F.self_intersections(Vw, Tw)
    assert si["complete"] is True
    assert si["n_self_intersecting_pairs"] > 0, (
        "the guard did not fire on a surface built to be self-intersecting")


def test_self_intersection_does_not_fire_on_a_clean_closed_surface():
    """Adjacency is not self-intersection. Every pair of faces of a tetrahedron
    shares an edge, and a non-strict segment/triangle test reports all of them.
    """
    V, T = _tetra()
    assert F.self_intersections(V, T)["n_self_intersecting_pairs"] == 0


def test_a_real_hull_stl_is_not_self_intersecting_at_the_shipped_resolution():
    """MEASURED 2026-08-12 on seed-0 hull 4 (the batch's hardest hull, which
    fails checkMesh at every layer count tried): 0 self-intersecting pairs at
    nx=600/nz=120. Recorded as a test so a future geometry change that folds
    the surface through itself is caught, and so the STL.md claim that
    self-intersection is NOT the discriminator has a fence."""
    from navalai.evaluate import sample_valid
    from navalai.mission import MissionSpec
    X, _ = sample_valid(5, MissionSpec(), seed=0)
    V, T = F.mesh_of_hull(Hull(np.asarray(X[4], dtype=float)), 120, 24)
    si = F.self_intersections(V, T)
    assert si["complete"] is True
    assert si["n_self_intersecting_pairs"] == 0


# ---------------------------------------------------------------------------
# An unmeasurable value is a refusal, never a zero
# ---------------------------------------------------------------------------


def test_self_intersection_over_budget_refuses_rather_than_returning_zero():
    """`max_pairs` exceeded must return complete False and -1.

    docs/LESSONS.md defect class 1, in its most expensive disguise: a broad
    phase that quietly truncates and reports 0 intersections is
    `${_MQ_SKEW:-0}` again — failure to measure scored as a perfect result.
    """
    V, T = _tetra()
    si = F.self_intersections(V, T, max_pairs=1)
    assert si["complete"] is False
    assert si["n_self_intersecting_pairs"] == -1
    assert "NOT MEASURED" in si["note"]


def test_over_cell_metrics_are_none_without_a_cell_size():
    """No hull cell given => no `*_over_cell` number, not a zero."""
    V, T = _tetra()
    rep = F.validate_stl((V, T), hull_cell_m=None, lwl=1.0,
                         do_self_intersection=False)
    for k in ("edge_over_cell_median", "edge_over_cell_p95",
              "edge_over_cell_max", "frac_tris_coarser_than_cell"):
        assert rep[k] is None, f"{k} defaulted instead of refusing"
    assert rep["n_self_intersecting_pairs"] is None
    assert rep["self_intersection_complete"] is False


def test_auc_refuses_a_single_class_instead_of_returning_half():
    """"Could not be computed" and "computed, and it is chance" are different
    answers. Returning 0.5 for an empty class would let a metric with no
    positives read as a scored, uninformative metric."""
    assert math.isnan(F.auc(np.arange(5.0), np.zeros(5, dtype=bool)))
    assert math.isnan(F.auc(np.arange(5.0), np.ones(5, dtype=bool)))
    assert F.auc(np.array([0.0, 1.0, 2.0, 3.0]),
                 np.array([False, False, True, True])) == 1.0
    assert F.auc(np.array([3.0, 2.0, 1.0, 0.0]),
                 np.array([False, False, True, True])) == 0.0
    # perfect ties are chance, and that IS 0.5
    assert F.auc(np.ones(4), np.array([True, True, False, False])) == 0.5


# ---------------------------------------------------------------------------
# The measurements themselves
# ---------------------------------------------------------------------------


def test_aspect_ratio_is_one_for_an_equilateral_triangle():
    """The normalisation is load-bearing: longest/(2*inradius) reads
    sqrt(3) = 1.732 on a perfect triangle, so any aspect bar quoted against the
    unnormalised form is wrong by that factor."""
    V = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, math.sqrt(3) / 2, 0.0]])
    q = F.triangle_quantities(V, np.array([[0, 1, 2]]))
    assert q["aspect"][0] == pytest.approx(1.0, abs=1e-9)
    assert q["min_angle_deg"][0] == pytest.approx(60.0, abs=1e-9)
    # a 100:1 sliver is unambiguously worse than any near-isotropic facet
    S = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, 0.005, 0.0]])
    assert F.triangle_quantities(S, np.array([[0, 1, 2]]))["aspect"][0] > 50.0


def test_edge_table_and_normal_jump_on_a_known_dihedral():
    """A roof of two triangles with an exact 40 degree normal jump."""
    a = math.radians(20.0)
    V = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                  [0.0, math.cos(a), math.sin(a)],
                  [0.0, -math.cos(a), math.sin(a)]])
    T = np.array([[0, 1, 2], [0, 3, 1]])
    et = F.edge_table(T)
    assert list(np.sort(et["count"])) == [1, 1, 1, 1, 2]
    ang, _ = F.normal_jumps(V, T, et)
    assert ang[0] == pytest.approx(40.0, abs=1e-6)


def test_feature_edges_reproduce_the_case_includedAngle_rule():
    """`SURFACE_FEATURES` writes `includedAngle 150`, i.e. a 30 degree bar on
    the normal jump. Fed a 20 degree crease it must extract NOTHING; fed 40 it
    must extract exactly one edge. Both directions, because a rule that only
    accepts is not a rule."""
    def roof(deg):
        a = math.radians(deg / 2.0)
        V = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                      [0.0, math.cos(a), math.sin(a)],
                      [0.0, -math.cos(a), math.sin(a)]])
        return V, np.array([[0, 1, 2], [0, 3, 1]])

    lo = F.feature_edges(*roof(20.0), included_angle=150.0)
    hi = F.feature_edges(*roof(40.0), included_angle=150.0)
    assert lo["normal_jump_bar_deg"] == 30.0
    assert lo["n_feature_edges"] == 4      # the four OPEN edges, angle-free
    assert hi["n_feature_edges"] == 5      # the four open edges + the crease
    assert hi["feature_edge_total_length_m"] == pytest.approx(1.0, abs=1e-9)


def test_weld_is_required_because_closed_mesh_emits_loose_vertices():
    """`Hull.closed_mesh`'s `vid()` appends a fresh vertex per triangle corner,
    so its raw output has 3x as many vertices as triangles and NO topology at
    all. Every edge-based metric in this module is meaningless without the
    weld, so the ratio is asserted rather than assumed."""
    from navalai.evaluate import sample_valid
    from navalai.mission import MissionSpec
    X, _ = sample_valid(1, MissionSpec(), seed=0)
    h = Hull(np.asarray(X[0], dtype=float))
    raw_v, raw_t = h.closed_mesh(nx=40, nz=8)
    assert len(raw_v) == 3 * len(raw_t)
    V, T = F.weld(np.asarray(raw_v, float), np.asarray(raw_t, int))
    assert len(V) < len(raw_v)
    et = F.edge_table(T)
    assert int(np.sum(et["count"] == 2)) == len(et["count"]), (
        "the welded hull surface is not closed; every metric downstream of "
        "this assumes it is")


def test_the_file_on_disk_and_the_array_in_memory_are_the_same_surface(tmp_path):
    """`hull_to_stl` writes `%.6e`. The forensics must be measured on what
    OpenFOAM reads, so the parsed file and the in-memory mesh have to agree —
    otherwise a finding is about a float format, not about a hull."""
    from navalai.evaluate import sample_valid
    from navalai.mission import MissionSpec
    X, _ = sample_valid(1, MissionSpec(), seed=0)
    h = Hull(np.asarray(X[0], dtype=float))
    p = tmp_path / "hull.stl"
    hull_to_stl(h, p, nx=60, nz=12)
    Vf, Tf = F.load_stl(p)
    Vm, Tm = F.mesh_of_hull(h, 60, 12)
    assert len(Tf) == len(Tm)
    a = F.validate_stl((Vf, Tf), hull_cell_m=0.02, lwl=float(h.x[-1]),
                       do_self_intersection=False)
    b = F.validate_stl((Vm, Tm), hull_cell_m=0.02, lwl=float(h.x[-1]),
                       do_self_intersection=False)
    for k in ("n_tris", "n_verts", "n_feature_edges", "n_degenerate_tris"):
        assert a[k] == b[k], k
    # 1e-3, not 1e-5, and the slack is the point: `hull_to_stl` writes
    # `%.6e`, so the file on disk is a ROUNDED copy of the array. Measured on
    # this hull the worst-affected metric is `aspect_max`, 9.304995 from the
    # file against 9.305204 in memory (2.2e-5 relative) — the sliver triangles
    # are where seven significant digits bite. It is small, and it is not zero,
    # and a test asserting exact equality would be asserting something false.
    for k in ("edge_median_m", "aspect_max", "normal_jump_max_deg"):
        assert a[k] == pytest.approx(b[k], rel=1e-3), k


# ---------------------------------------------------------------------------
# The claims docs/research/STL.md makes about the PIPELINE
# ---------------------------------------------------------------------------


def test_stl_resolution_is_clamped_for_every_hull_in_the_batch():
    """STL.md's central negative result depends on this and nothing else.

    `stl_resolution` asks for `lwl / target_edge` where `target_edge` is itself
    proportional to LWL, so the request is the SAME INTEGER (811) for every
    hull and the 600 ceiling binds on all of them. The triangulation is
    therefore hull-size-independent by construction, and "relative tessellation
    density falls with hull size" cannot be true at the shipped configuration.
    Asserted across the batch's measured LWL range 6.836 .. 18.702 m.
    """
    from navalai.cfd.case import _DOMAIN_LENGTH_L, _HULL_REFINE, _NX_BASE
    for lwl in (6.836, 8.942, 9.509, 11.670, 12.320, 15.015, 18.702):
        bg_dx = _DOMAIN_LENGTH_L * lwl / _NX_BASE
        assert stl_resolution(lwl, 0.5 * bg_dx / 2 ** _HULL_REFINE[1]) == (600, 120)
    # And the triangle COUNT does not track LWL either, at either resolution.
    #
    # THE BAR IS "DOES NOT TRACK LWL", NOT A LITERAL. It was `== {5244}` for
    # one commit, and that broke within the hour: an unrelated pass put the
    # chine on a grid row and the default count moved to 5234/5236/5238 —
    # correctly, because the count is `(nx-1)*nz*4 + ...` MINUS however many
    # stem quads degenerate to zero area on that particular hull. Pinning the
    # literal would have made this suite fail for a change it has no opinion
    # about, while asserting nothing STL.md relies on.
    # MEASURED 2026-08-12 at ref 0e53331: 5244 on 24 of the 25 seed-0 hulls and
    # 5214 on one, spread 0.57%; at the shipped 600x120, 288956 on 24 and
    # 288718 on one.
    #
    # THE INDEPENDENCE IS NOW EXACT, AND THAT IS WHY THIS TEST WENT RED WITH A
    # NaN. RE-MEASURED 2026-08-13 on the plate P1/P2 kernel: the count is the
    # SAME INTEGER on all eight hulls (5244 at 80x16, 288956 at 600x120) —
    # spread ZERO, not 0.57% — so `spearmanr` was handed a CONSTANT array,
    # returned an undefined `nan` with a `ConstantInputWarning`, and
    # `abs(nan) < 0.9` is False. It failed LOUDLY on a stronger result than the
    # one it was asserting, which is the correct behaviour for an unmeasurable
    # value (docs/LESSONS.md defect class 1) and is why it is handled below
    # rather than papered over with `nan_policy` or a bare `if`.
    #
    # The mechanism is plate P1's stem. At x = LWL the sectional area curve
    # reaches a(x) = 0, so the flare envelope closes with it and the section
    # solve returns y_chine = y_sheer = 0 EXACTLY — MEASURED, on all eight
    # hulls. The stem station therefore collapses onto the centreline for every
    # hull, and the quads that degenerate are always the same ones:
    #
    #     nx    nz   written  delivered  dropped  2*nz+2
    #     40     8      1358       1340       18      18
    #     80    16      5278       5244       34      34
    #    120    24     11758      11708       50      50
    #    200    40     32398      32316       82      82
    #
    # i.e. the whole stem cap (2*nz triangles) plus the two deck slivers at the
    # last station, identically on every hull. The old kernel closed the deck
    # with a separate `w**0.15` taper, so how many quads collapsed depended on
    # the hull — that is where the 5244/5214 split came from. "The count is a
    # function of (nx, nz) and NOT of LWL" is therefore now an IDENTITY, and it
    # is asserted as one.
    from navalai.evaluate import sample_valid
    from navalai.mission import MissionSpec
    X, _ = sample_valid(8, MissionSpec(), seed=0)
    hulls = [Hull(np.asarray(x, float)) for x in X]
    lwls = np.array([float(h.x[-1]) for h in hulls])
    counts = np.array([len(h.closed_mesh(nx=80, nz=16)[1]) for h in hulls])
    assert lwls.max() / lwls.min() > 2.0, "the sample does not span hull sizes"
    assert (counts.max() - counts.min()) / counts.mean() < 0.01, (
        f"triangle count spread {counts.min()}..{counts.max()} exceeds 1%; the "
        "triangulation may have become size-dependent")
    for nx, nz in ((80, 16), (200, 40)):
        got = {len(h.closed_mesh(nx=nx, nz=nz)[1]) for h in hulls}
        want = (nx - 1) * nz * 4 + 4 * nz + 2 * (nx - 1) - (2 * nz + 2)
        assert got == {want}, (
            f"at {nx}x{nz} the batch produced {sorted(got)} triangles against "
            f"the closed form's {want}; the stem no longer degenerates the "
            "same way on every hull, so re-derive the identity above before "
            "trusting STL.md's size-independence claim")
    # The rank correlation is kept as the fallback for the day the counts stop
    # being identical: it must then be COMPUTABLE and small, and a `nan` there
    # would be a refusal to measure, not a pass.
    from scipy.stats import ConstantInputWarning, spearmanr
    if counts.min() == counts.max():
        # `pytest.warns` rather than a filter: scipy SAYING the coefficient is
        # undefined is the evidence this branch rests on, so it is asserted,
        # not suppressed.
        with pytest.warns(ConstantInputWarning):
            rho = spearmanr(lwls, counts).statistic
        assert math.isnan(rho), (
            f"spearmanr returned {rho} on a constant array; the branch above "
            "assumes it is undefined there and the assertion in the other "
            "branch would be the one to keep")
    else:
        rho = spearmanr(lwls, counts).statistic
        assert math.isfinite(rho), (
            "the counts vary but their rank correlation with LWL could not be "
            "computed; an unmeasurable value is not a passing one")
        assert abs(rho) < 0.9, f"triangle count tracks LWL (Spearman {rho:.3f})"


def test_the_stl_encloses_the_volume_the_geometry_kernel_defines():
    """THE STL PATH IS NOT THE STEP PATH, and this is the measurement.

    MOTIVATING INCIDENT, 2026-08-13. Plate P2 made `Hull.section` return 3
    points for a hard chine and 2*SECTION_FILLET_SAMPLES+1 (257) for a
    radiused bilge. `navalai/export.py` read that section POSITIONALLY, lofted
    between the wrong points, and produced a sliver: ladder displacement
    11.1722 m^3 against 0.000650 m^3 exported, **-99.994%**, with the
    exporter's own receipt scoring the sliver against the sliver and printing
    ~0% error.

    The STL path reads the same shape function and could have had the same
    defect, so it is verified rather than assumed. `closed_mesh` asks
    `sample_section` for exactly `nz+1` points with the bilge on
    `chine_row(nz)`, i.e. by CONTRACT rather than by position, and the
    enclosed volume says so. MEASURED 2026-08-13 over the eight seed-0 hulls
    at the shipped 600x120, signed volume of the triangulation against the
    moulded volume integrated independently from the section polygons:

        hull   Lwl m   roundness   analytic m^3   STL m^3    error
           0  17.811       0.981       47.94846   47.95585  +0.0154%
           1   5.993       0.369       19.64787   19.64650  -0.0070%
           2  10.092       0.995       72.80631   72.81984  +0.0186%
           3  13.104       0.127       91.97784   91.99630  +0.0201%
           4   9.776       0.303       30.29420   30.29558  +0.0046%
           5  15.476       0.780       85.63890   85.63507  -0.0045%
           6  15.558       0.265       57.53939   57.54492  +0.0096%
           7  18.830       0.131       83.82109   83.83563  +0.0174%

    Worst 0.0201%, across roundness 0.127 .. 0.995 — the range that would
    expose a positional read, since the section's point COUNT is what changed.
    The residual is the 41-station linear interpolation in x, and it is
    two-signed, which a truncation would not be.

    The bar is 0.5%: four orders inside the failure it is written against and
    an order and a half above the observed worst case, so it refuses a sliver
    and does not fire on the interpolation. It is measured on the ARRAYS;
    `test_the_file_on_disk_and_the_array_in_memory_are_the_same_surface` is
    the arm that carries it to the file OpenFOAM actually meshes, and the two
    were MEASURED to agree here to 1e-5 relative.
    """
    from navalai.evaluate import sample_valid
    from navalai.mission import MissionSpec

    def signed_volume(V, T):
        p0, p1, p2 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        return float(np.sum(np.einsum("ij,ij->i", p0,
                                      np.cross(p1, p2))) / 6.0)

    def moulded_volume(h):
        """2 * int(area enclosed by the section polyline and the centreline)dx.

        Independent of the triangulation: it shoelaces `Hull.section`, the
        shape function itself, at the hull's own stations. Not a second copy
        of the geometry — a second INTEGRATION of the one definition, which is
        the only kind of cross-check that can catch a wrong loft.
        """
        a = np.empty(h.n_stations)
        for i in range(h.n_stations):
            poly = np.vstack([[0.0, h.z_keel[i]], h.section(i),
                              [0.0, h.z_sheer[i]]])
            y, z = poly[:, 0], poly[:, 1]
            a[i] = 0.5 * abs(float(np.dot(y, np.roll(z, -1))
                                   - np.dot(z, np.roll(y, -1))))
        return 2.0 * float(np.trapezoid(a, h.x))

    X, _ = sample_valid(8, MissionSpec(), seed=0)
    roundness = []
    for i, x in enumerate(X):
        h = Hull(np.asarray(x, float))
        roundness.append(h.roundness)
        want = moulded_volume(h)
        V, T = F.mesh_of_hull(h, 600, 120)
        got = signed_volume(V, T)
        assert abs(got - want) / want < 5e-3, (
            f"hull {i}: the 600x120 triangulation encloses {got:.5f} m^3 "
            f"against the section shape function's {want:.5f} m^3 "
            f"({100.0 * (got - want) / want:+.3f}%) — a loft that reads the "
            "section positionally fails here by orders of magnitude, so check "
            "that before adjusting this bar")
        assert got > 0.0, f"hull {i}: the STL is wound INWARD"
    assert min(roundness) < 0.2 and max(roundness) > 0.9, (
        f"the batch's roundness spans {min(roundness):.3f}..{max(roundness):.3f}"
        " and no longer covers both a near-hard chine and a full fillet; the "
        "point-count change is what a positional read trips over")


def test_runner_bar_refuses_the_verbatim_rows_it_must_refuse():
    """The label every AUC in STL.md is computed against, fed the ACTUAL
    recorded campaign rows. Hull 4 at cap 7 (38 wrongly-oriented faces) must be
    a failure; hull 0 at cap 7 (0/0/skew 4.52) must not; and a row whose
    skewness is the -1.0 `mesh_robustness.py` writes when it could not read one
    must be a FAILURE, not a pass (docs/LESSONS.md defect class 1)."""
    rows = json.loads((ROOT / "data" / "gate2u-cap7-mesh.json").read_text())["rows"]
    by = {r["hull"]: r for r in rows}
    assert F.runner_bar_fails(by[4]) is True
    assert F.runner_bar_fails(by[0]) is False
    assert F.runner_bar_fails({"zero_volume_cells": 0, "wrong_oriented": 0,
                               "max_skewness": -1.0}) is True
    base = json.loads(
        (ROOT / "data" / "gate2u-campaign-baseline.json").read_text())["rows"]
    h5 = [r for r in base if r["hull"] == 5][0]
    assert h5["max_skewness"] == -1.0 and F.runner_bar_fails(h5) is True


def test_the_cap7_labelling_is_the_six_hulls_stl_md_names():
    """STL.md and docs/research/LAYERS.md must be talking about the same six
    hulls. Derived from the recorded rows, never restated."""
    lab = F.campaign_labels(ROOT)
    fails = sorted(h for h, v in lab["cap7_fails_runner_bar"].items() if v)
    assert fails == [4, 5, 10, 12, 14, 18]
    strict = sorted(h for h, v in lab["cap7_fails_strict"].items() if v)
    assert strict == [4, 5, 9, 10, 12, 14, 16, 18, 19]
    none_ok = sorted(h for h, v in lab["no_admissible_rung"].items() if v)
    assert none_ok == [4, 14]


def test_family_wise_p_corrects_for_the_size_of_the_family():
    """A best-of-N AUC quoted uncorrected is a finding about N.

    Fed 40 pure-noise metrics on 25 samples with 6 positives, the family
    maximum routinely exceeds AUC 0.80 — so the corrected p of that maximum
    must stay well away from significance, while a metric that separates the
    classes perfectly must still clear it.
    """
    rng = np.random.default_rng(7)
    y = np.zeros(25, dtype=bool)
    y[[4, 5, 10, 12, 14, 18]] = True
    fam = {f"noise{i}": rng.normal(size=25) for i in range(40)}
    res = F.family_wise_p(fam, y, n_perm=2000, seed=1)
    assert res["n_metrics_in_family"] == 40
    assert res["best_family_wise_p"] > 0.05, (
        "40 noise metrics produced a 'significant' best AUC; the correction "
        "is not correcting")
    fam["perfect"] = y.astype(float) + rng.normal(scale=1e-6, size=25)
    res2 = F.family_wise_p(fam, y, n_perm=2000, seed=1)
    assert res2["best_metric"] == "perfect"
    assert res2["best_auc"] == pytest.approx(1.0)
    assert res2["best_family_wise_p"] < 0.01
