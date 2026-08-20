"""h011 / h012 — the regression that pins what the root-cause hunt PROVED.

FULL WRITE-UP: `docs/audit/H011-H012-ROOT-CAUSE.md`.

THE INCIDENT. `data/gate2u-16gene-mesh.json` (N=25, seed 0, scale 1.0, speed
2.57, LTS, np=10) and `data/gate2u-16gene-solve.json` (18 rows, hulls 0-17)
record the same two deterministic rung-0 refusals: **h011** (13 wrongly
oriented faces, max skewness 247.226, non-orthogonality 90.488) and **h012**
(12 wrongly oriented faces, skew 9.946, non-orthogonality 98.332). The
operator's directive was to walk genome -> sections -> curves -> surfaces ->
tessellation -> STL -> mesh and find the FIRST mathematical invariant that
breaks, so the invalid region could be excluded BY CONSTRUCTION.

THE RESULT, AND WHY THIS FILE IS SHAPED THE WAY IT IS. **No invariant breaks
upstream of the volume mesh.** The section solve is strictly feasible on both
hulls, the edge curves do not cross, the surface is fold-free,
self-intersection-free, watertight and outward-wound, and the tessellation of
both failures is BETTER than that of hulls that meshed. An 83-descriptor
family scored with this repository's own permutation instrument
(`stl_forensics.family_wise_p`, 20 000 permutations) returns a best
family-wise p of **0.601**: nothing separates.

So there is no admissible-region boundary to pin, and inventing a threshold to
make a story work is what `docs/LESSONS.md` forbids. What CAN be pinned, and
is pinned here, is the negative half — every invariant that was checked and
HELD, plus the measured refusal of the best-looking candidate criterion, so
that a later session cannot promote it by mistake.

The campaign outcomes are TRANSCRIBED as constants rather than read from the
JSON, following `tests/test_admissibility.py`'s doctrine: a gate test whose
verdict changes when an artefact grows is not a gate test.

COST. `sample_valid(25, ...)` is ~11 s and is module-scoped; the surface checks
run at a reduced 161x32 triangulation (the shipped case is 600x120) because
every invariant asserted here is topological or sign-based and therefore
resolution-independent. Where a magnitude is compared, it is compared as an
ORDERING between hulls at one stated triangulation, never as an absolute bar.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest

from navalai import grammar
from navalai.admissibility import _pipeline_scales
from navalai.cfd.case import (_tris_to_ascii_stl, hull_to_stl,
                              stl_watertight_report)
from navalai.evaluate import sample_valid
from navalai.geometry import (FEASIBILITY_PROBE_STATIONS, Hull, _stations,
                              section_probe)
from navalai.mission import MissionSpec
from navalai.stl_forensics import mesh_of_hull, validate_stl

SPEED = 2.57
SCALE = 1.0
N_HULLS = 25

# The two rung-0 refusals, and the batch they came from.
FAILED = (11, 12)

# MEASURED, `data/gate2u-16gene-mesh.json` (committed by 168ea82): the 23 hulls
# that meshed unattended at the derived layer count, and the 2 that did not.
MESHED = tuple(i for i in range(N_HULLS) if i not in FAILED)

# MEASURED, same file: the recorded waterline length per hull, to the 3 decimals
# the artefact carries. This is the ONLY identity of the campaign population
# that reproduces across machines — see `test_the_ascii_stl_hash_is_not_a_
# portable_identity` for the one that does not.
RECORDED_LWL = (
    10.687, 14.734, 17.829, 14.821, 15.541, 16.964, 12.767, 20.037, 11.309,
    8.729, 11.097, 17.876, 12.842, 7.908, 17.967, 22.686, 11.559, 11.801,
    13.046, 8.919, 8.355, 5.997, 12.448, 20.494, 11.663,
)

# The triangulation these checks run at. The shipped case is 600x120
# (`stl_resolution` at scale 1.0, the [80, 600] clamp binding on every hull);
# this is a quarter of it in each direction so the suite stays under a minute.
# Stated, not assumed — docs/LESSONS.md defect class 6.
NX, NZ = 161, 32


@pytest.fixture(scope="module")
def population() -> np.ndarray:
    X, _ = sample_valid(N_HULLS, MissionSpec(), seed=0)
    return np.asarray(X, dtype=float)


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return np.divide(v, np.where(n > 1e-300, n, 1.0))


def _shell_grid(h: Hull, nx: int, nz: int) -> np.ndarray:
    """`closed_mesh`'s own starboard station grid, (nx, nz+1, 3)."""
    xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
    jc = h.chine_row(nz)
    S = np.zeros((nx, nz + 1, 3))
    for k, xv in enumerate(xs):
        S[k, :, 1:] = h._section_at_rows(float(xv), jc, nz - jc)
        S[k, :, 0] = xv
    return S


def _quad_normals(S: np.ndarray):
    a, b = S[:-1, :-1], S[:-1, 1:]
    c, d = S[1:, 1:], S[1:, :-1]
    return (_unit(np.cross(b - a, c - a)), _unit(np.cross(c - a, d - a)),
            0.25 * (a + b + c + d))


# --------------------------------------------------------------------------
# STEP 0 — the population reproduces, and one identity does not
# --------------------------------------------------------------------------


def test_the_campaign_population_reproduces_from_the_seed(population):
    """seed 0 redraws the same 25 hulls, to the precision the record carries.

    This is what makes every other assertion in this file a statement about
    the hulls the campaign meshed rather than about lookalikes.
    """
    got = [round(float(Hull(population[i]).x[-1]), 3) for i in range(N_HULLS)]
    assert got == list(RECORDED_LWL)


def test_the_ascii_stl_hash_is_not_a_portable_identity(population, tmp_path):
    """`stl_sha256` cannot certify geometry ACROSS machines, and here is why.

    MEASURED during the h011/h012 hunt: regenerating hulls 0, 11 and 12 with a
    byte-identical emitter (every function on the STL path is unchanged since
    the campaign commit) reproduced NONE of the recorded hashes on x86-64
    Linux, while the campaign ran on the Mac.

    The mechanism is this formatter. `_tris_to_ascii_stl` prints `%.6e`, i.e.
    seven significant digits; over h011's shipped 288 956 triangles (3 467 472
    printed numbers) THIRTEEN of them sit within 1e-12 RELATIVE of a rounding
    boundary in that seventh digit. So a cross-platform arithmetic difference
    at the 1e-12 level — FMA contraction, a different libm, a different BLAS —
    rewrites the file and therefore the hash while moving no geometry a mesher
    can see.

    The pin: a relative perturbation of 1e-9 — eleven orders below the hull
    cell, four below single precision, geometrically meaningless — changes the
    hash. A receipt that cannot survive that is a SAME-MACHINE identity, and
    reading a mismatch as "different hull" is a misattribution.
    """
    h = Hull(population[FAILED[0]])
    V, T = h.closed_mesh(nx=NX, nz=NZ)
    a = hashlib.sha256(_tris_to_ascii_stl(V, T)).hexdigest()
    b = hashlib.sha256(_tris_to_ascii_stl(V * (1.0 + 1e-9), T)).hexdigest()
    assert a != b, (
        "the ascii-STL hash survived a 1e-9 relative perturbation of every "
        "vertex — if the formatter has been made robust, the portability "
        "finding in docs/audit/H011-H012-ROOT-CAUSE.md §0 needs re-measuring "
        "rather than this assertion needs deleting")


# --------------------------------------------------------------------------
# STEP 1 — the section solve: strictly feasible on BOTH failures
# --------------------------------------------------------------------------


@pytest.mark.parametrize("hull_id", FAILED)
def test_the_section_solve_is_strictly_feasible_on_the_failed_hulls(
        population, hull_id):
    """No refusal, no clamp, no floor — except the two that bite at the stem.

    `_stations` can refuse three ways: a negative discriminant (the requested
    area exceeds what the draft and deadrise can enclose), a negative `rhs`
    (the flare encloses more than the area curve asked for), and the
    tumblehome refusal on a negative sheer. It clamps once, `yc >= 0`, which
    the kernel documents as biting only where a(x) -> 0.

    MEASURED at the 1921-station feasibility grid on all 25 campaign hulls:
    the discriminant is strictly positive everywhere, `rhs` touches zero only
    at x = LWL, and BOTH floors bite at exactly one station — the stem — on
    every hull, failures and passers alike. h011's discriminant margin
    (0.401) is 118x hull 4's (0.0034), and hull 4 meshed.
    """
    x = population[hull_id]
    lwl = float(grammar.named(x)["LWL"])
    t = np.linspace(0.0, lwl, FEASIBILITY_PROBE_STATIONS)
    s = _stations(x, t)

    disc = (s["K"] * s["c1"] * s["d"]) ** 2 - \
        4.0 * s["K"] * s["c2"] * s["m"] * (s["A"] - s["d"] ** 2 * s["f"])
    rhs = s["A"] - s["d"] ** 2 * s["f"]

    assert disc.min() > 0.0, "the section quadratic went singular"
    assert rhs.min() >= -1e-12, "the flare outran the area curve"
    # both floors bite exactly once, and it is the stem
    assert int((s["y_chine"] <= 0.0).sum()) == 1
    assert int((s["y_sheer"] <= 0.0).sum()) == 1
    assert np.argmax(s["y_chine"] <= 0.0) == len(t) - 1
    assert np.argmax(s["y_sheer"] <= 0.0) == len(t) - 1
    # and the dense probe the L0 gate uses raises nothing
    section_probe(x)


@pytest.mark.parametrize("hull_id", FAILED)
def test_the_failed_hulls_edge_curves_do_not_cross(population, hull_id):
    """Chine below the waterline, sheer outboard of the chine, all x.

    Two crossings were hypothesised and both are refuted on these hulls:
    the chine never reaches z = 0 (h011 max -0.352 m, h012 max -0.0606 m), and
    the sheer never falls inboard of the chine. NOTE the direction of the
    evidence: five hulls that DID mesh (4, 15, 16, 21, 23) carry genuine
    tumblehome, `y_sheer < y_chine`, so tumblehome is not the defect either.
    """
    x = population[hull_id]
    lwl = float(grammar.named(x)["LWL"])
    t = np.linspace(0.0, lwl, 4001)
    s = _stations(x, t)
    interior = t < 0.98 * lwl

    assert s["z_chine"].max() < 0.0
    assert s["y_sheer"].min() >= 0.0
    assert (s["y_sheer"] - s["y_chine"])[interior].min() > 0.0
    assert (s["z_sheer"] - s["z_chine"])[interior].min() > 0.0


# --------------------------------------------------------------------------
# STEP 2 — the surface: valid BY CONSTRUCTION, which is what the operator asked
# --------------------------------------------------------------------------


@pytest.mark.parametrize("hull_id", FAILED)
def test_z_is_monotone_along_every_section_so_the_surface_cannot_self_intersect(
        population, hull_id):
    """The invariant that makes self-intersection impossible, not merely absent.

    Along a section the z-coordinate rises monotonically from keel to sheer:
    the bottom leg at +tan(beta), the fillet Bezier whose z control points are
    (zc + rho*(zk - zc), zc, (1 - rho)*zc) and therefore non-decreasing for
    zk <= zc <= 0, and the topside leg to zs > zc. Sections lie at distinct x,
    the caps are planar at the two ends, and the deck lid meets the shell only
    at the unique z where the section reaches its top. Together those forbid a
    self-intersection.

    CORROBORATED numerically: `stl_forensics.self_intersections` reports 0
    intersecting pairs (complete broad phase, ~2e6 candidate pairs) on h011,
    h012 and three controls at 241x48.
    """
    h = Hull(population[hull_id])
    S = _shell_grid(h, NX, NZ)
    dz = np.diff(S[:, :, 2], axis=1)
    assert dz.min() >= 0.0, "z is not monotone along the section"
    assert S[:, :, 1].min() >= 0.0, "the starboard section crossed y = 0"


@pytest.mark.parametrize("hull_id", FAILED)
def test_the_failed_hulls_surface_is_fold_free_and_outward(population, hull_id):
    """0 folded quads, 0 inward-facing quads — measured on all 25, pinned on 2.

    A quad is FOLDED when its two triangles' normals sit in opposite
    hemispheres; it is INWARD when the outward normal points back at the
    section's own centreline axis. Both counts are zero for every hull in the
    campaign batch. This is the assertion that says the 13 and 12 "wrongly
    oriented faces" checkMesh reported are cells snappyHexMesh built, not
    triangles this kernel emitted.
    """
    h = Hull(population[hull_id])
    S = _shell_grid(h, NX, NZ)
    n1, n2, cen = _quad_normals(S)

    assert int((np.sum(n1 * n2, axis=-1) < 0.0).sum()) == 0, "folded quad"

    zk = np.interp(cen[..., 0], h.x, h.z_keel)
    zs = np.interp(cen[..., 0], h.x, h.z_sheer)
    axis = np.stack([cen[..., 0], np.zeros_like(zk), 0.5 * (zk + zs)], -1)
    assert int((np.sum(n1 * (cen - axis), axis=-1) < 0.0).sum()) == 0, \
        "a shell quad faces into the hull"


@pytest.mark.parametrize("hull_id", FAILED)
def test_the_failed_hulls_stl_is_watertight_and_outward(population, hull_id,
                                                        tmp_path):
    """The pipeline's own guard, on the two hulls that failed downstream of it.

    `write_resistance_case` refuses a surface this reports open, and it did not
    refuse these two: 0 open-or-non-manifold edges, 0 winding conflicts,
    outward, positive signed volume. The surface handed to snappy was closed.
    """
    h = Hull(population[hull_id])
    path = tmp_path / f"h{hull_id:03d}.stl"
    hull_to_stl(h, path, nx=NX, nz=NZ)
    rep = stl_watertight_report(path)

    assert rep["open_or_nonmanifold_edges"] == 0
    assert rep["winding_conflicts"] == 0
    assert rep["watertight"] is True
    assert rep["outward"] is True
    assert rep["signed_volume"] > 0.0


def test_the_failed_hulls_tessellation_is_not_the_worst_in_the_batch(
        population):
    """The sliver hypothesis, refuted by a hull that meshed.

    Hull 24 meshed with 0 wrongly-oriented faces and skew 3.449 while carrying
    the worst facet in the whole batch. At the shipped 600x120 its aspect ratio
    is 1107.5 against h011's 189.2 and h012's 234.8, and its minimum angle is
    0.0304 deg against 0.185 and 0.142. The ordering is asserted at this
    file's own triangulation rather than the absolute numbers, so the pin
    survives a change of resolution.
    """
    def worst(i):
        r = validate_stl(mesh_of_hull(Hull(population[i]), NX, NZ),
                         do_self_intersection=False)
        return r["aspect_max"], r["min_angle_deg"], r

    a24, ang24, r24 = worst(24)
    for i in FAILED:
        ai, angi, ri = worst(i)
        assert a24 > ai, (
            f"hull 24 (meshed clean) no longer carries a worse facet than "
            f"h{i:03d} (refused): {a24:.4g} vs {ai:.4g}")
        assert ang24 < angi
        assert ri["n_nonmanifold_or_open_edges"] == 0
        assert ri["n_zero_area_tris"] == 0
        assert ri["n_duplicate_tris"] == 0


# --------------------------------------------------------------------------
# STEP 3 — the negative result, pinned so nobody promotes it by mistake
# --------------------------------------------------------------------------


def _min_topside_panel_height_cells(x: np.ndarray) -> float:
    """The best-separating descriptor of the 83 scanned — AUC 0.957, p_fw 0.601.

    min over x < 0.98*LWL of (z_sheer - z_chine) / cell. This is
    `admissibility.screen`'s own `min_topside_panel_height_cells`, recomputed
    here so the test does not depend on the screen's metric list.
    """
    lwl = float(grammar.named(x)["LWL"])
    cell = _pipeline_scales(lwl, SPEED, SCALE)["cell"]
    t = np.linspace(0.0, lwl, 4001)
    s = _stations(x, t)
    return float((s["z_sheer"] - s["z_chine"])[t < 0.98 * lwl].min() / cell)


def test_the_best_candidate_criterion_does_not_separate(population):
    """THE POINT OF THIS FILE. It looks like a criterion; it is not one.

    Of 83 descriptors scored against the mesh outcome with
    `stl_forensics.family_wise_p` (20 000 permutations, 2 positives), the best
    is `min_topside_panel_height_cells` at AUC 0.957 — and its family-wise
    p is **0.601**. Over 83 looks, that is what chance produces.

    Measured ordering at the shipped triangulation:

        [12:23.88]  4:25.29  10:35.24  [11:40.88]  14:42.76  15:43.78 ...

    The tightest threshold that catches both failures is h011's OWN value, and
    it drags in hulls 4 and 10, which meshed: TP 2 / **FP 2** / FN 0 on the
    25-hull mesh corpus, and TP 2 / **FP 2** / FN 0 on the 18-row solve corpus.
    It beats the shipped screen on raw counts (0 / 6 / 2) and is REFUSED
    anyway, because the metric's derived bar in `admissibility.py` is 1.0 cell
    — a sub-cell feature — and moving a derived bar by a factor of 41 to fit
    two points is exactly the move docs/LESSONS.md forbids.

    This test fails the day someone makes it separate. That would be good news
    and should be read as an invitation to re-measure, not to delete the test.
    """
    v = np.array([_min_topside_panel_height_cells(population[i])
                  for i in range(N_HULLS)])

    # the two failures are NOT the two smallest: at least one hull that meshed
    # sits strictly between them
    lo, hi = sorted(v[list(FAILED)])
    between = [i for i in MESHED if lo < v[i] < hi]
    assert len(between) >= 2, (
        f"hulls that meshed no longer sit inside the failures' band "
        f"({between}) — the separation scan in "
        f"docs/audit/H011-H012-ROOT-CAUSE.md §5 must be re-run before this "
        f"metric is promoted")

    # and therefore no threshold catches both failures without false alarms
    threshold = v[list(FAILED)].max()
    false_alarms = [i for i in MESHED if v[i] <= threshold]
    assert len(false_alarms) >= 2, (
        f"a threshold at {threshold:.4f} cells now catches both failures with "
        f"{len(false_alarms)} false alarm(s); re-score it against the corpus "
        f"before shipping it as a bar")


def test_the_161_station_rebuild_removes_no_defect_these_two_hulls_have(
        population):
    """Question 6, answered by measurement: it would NOT fix h011/h012.

    A concurrent change rebuilds `hull_to_stl` at ~161 stations instead of 41.
    The quantity snappy reacts to is the longitudinal normal jump — an edge
    becomes a `surfaceFeatureExtract` feature at 30 deg
    (`includedAngle 150`) and is then refined and snapped to.

    MEASURED at 600x120 across the batch, station counts 41 / 161 / 321:
    h011 carries ONE over-bar edge at 41 stations (30.283 deg) and none at 161;
    h012 carries NONE at either. Hulls that meshed carry up to 43 (h001), 38
    (h010), 29 (h014), 27 (h016), 25 (h003). Worse, the change is not
    monotone: hull 18 goes 0 -> 53 over-bar edges from 41 to 161 stations,
    because refining the loft exposes curvature the coarse lerp was chording
    across.

    So the rebuild is a legitimate fix for the loft-error term
    (`A(lerp(p)) <= lerp(A(p))`, worst 0.1869%) and must be justified on that
    ground. It repairs no defect these two hulls have.
    """
    def over_bar(i, n_stations):
        h = Hull(population[i], n_stations=n_stations)
        n1, n2, _ = _quad_normals(_shell_grid(h, NX, NZ))
        q = _unit(n1 + n2)
        dot = np.clip(np.sum(q[:-1] * q[1:], axis=-1), -1.0, 1.0)
        return int(np.nansum(np.degrees(np.arccos(dot)) > 30.0))

    for i in FAILED:
        assert over_bar(i, 41) <= 1, (
            f"h{i:03d} carries more than one phantom feature edge at 41 "
            f"stations; the 161-station argument needs re-measuring")
        assert over_bar(i, 161) == 0

    # and hulls that meshed carry far more of them, at both station counts
    for i in (1, 3, 10):
        assert over_bar(i, 41) >= 5
        assert over_bar(i, 161) >= 5
