"""Gate tests for `navalai/blender` — the bars are MEASURED numbers, and the
date beside each one says which geometry kernel measured it.

THE MOTIVATING INCIDENT, in two halves.

(1) A prior session reported "Blender is not installed", inferred it from an
    empty `which blender`, and started down a `pip install bpy` path. Blender
    5.2.0 LTS was installed the whole time at
    `/Applications/Blender.app/Contents/MacOS/Blender` — and, MEASURED
    2026-08-12, it is on PATH as well, via a Homebrew cask wrapper at
    `/opt/homebrew/bin/blender`. Both the original claim and the correction
    that followed it were wrong about the state, which is why
    `test_blender_is_detected_by_the_binary_and_never_by_the_path` fences the
    RULE (detection does not consult PATH) rather than the state.

(2) The owner proposed a voxel Remesh at `voxel_size = 0.05` before export.
    MEASURED on hulls 4/8/14 at the shipped 600x120 triangulation, the chine
    dihedral 5 mm off the knuckle goes from 53.5 / 69.4 / 72.0 deg to
    0.0 / 0.0 / 0.0 — a 50 mm voxel rounds away the feature commit bbf1a47 had
    just fixed to 1e-9 m — while the max deviation from the analytic surface
    rises from a 0.01-3.03 mm band to 23.6-57.6 mm in EVERY x/L bin, and
    `surfaceFeatureExtract` at the pipeline's own `includedAngle 150` goes from
    6-7 feature points and 0 internal edges to 489-524 and 123-156.

    `test_a_005_voxel_remesh_destroys_the_chine` feeds the guard the VERBATIM
    configuration it must reject (docs/LESSONS.md defect class 3: a test
    showing a guard accepts a good case proves nothing about rejection). If a
    future change makes voxel remesh safe on this path, this test fails and
    the finding gets re-measured rather than quietly inherited.

WHAT THE 2026-08-13 GEOMETRY-KERNEL REBUILD (plates P1/P2) DID TO THIS FILE.

The genome went 15 -> 16 parameters (`p_bow` and `p_stern` dropped; `Cp`,
`lcb` and `roundness` added), so `sample_valid(25, MissionSpec(), seed=0)[14]`
is a DIFFERENT BOAT and every hull-specific number above was measured on a
hull that no longer exists. Two consequences, and neither is a relaxation:

  * THE STAGE A DEVIATION TABLE IS VOID AS A CALIBRATION, and the staleness is
    declared by a PROBE on `grammar.N_PARAMS` (`stage_a_table_is_transferable`
    below) rather than by prose, on the same discipline as
    `navalai/admissibility.py::calibration_is_current`. It un-asserts itself
    if the genome ever goes back. What replaces it as the ruler's live fence
    is a CONVERGENCE statement no genome can stale.
  * THE CHINE TESTS ARE PINNED TO `roundness = 0`, not relaxed. "A voxel
    remesh destroys the chine" is a claim about a hull that HAS a chine, and
    plate P2's `roundness` replaces the knuckle with a quadratic-Bezier
    fillet. Index 14 now draws roundness 0.327, so its bilge is radiused and
    there is no knuckle to destroy — MEASURED, its dihedral 5 mm off the
    bilge is 0.53 deg on the CORRECT triangulation. At `roundness = 0` the
    kernel is bit-identical to the pre-rebuild one, so the bar is exactly as
    hard as it was. The hard-chine case is also the one the SKUs are
    (docs/LESSONS.md: KCS shares no chine physics with them).

AND ONE BAR MOVED BECAUSE THE RULER WAS WRONG, not because the mesh was.
`analytic_probe_points` walked the section as three points, keel -> chine ->
sheer, so on a radiused bilge it probed the pre-P2 polyline and scored the
FILLET as a mesh error: 28.9-43.6 mm in every bin on a triangulation that is
right to 0.7-3.0 mm. The fix is in `navalai/blender/metrics.py`, which is
where the measurement is recorded; `test_the_probe_cloud_is_the_old_polyline_
at_roundness_zero` fences that it changed nothing for a hard chine.

Tests that INVOKE Blender carry `requires_blender` and skip where the binary
is absent — fortress001 has no `/Applications`. The mark used to sit on the
module, which skipped the deviation-ruler tests too, and those never touched
Blender: they measure `navalai/blender/metrics.py` against `mesh_of_hull`, so
they now run everywhere. A skip is not a pass; `docs/research/BLENDER.md`
carries the recorded numbers, so an absent binary loses the fence, not the
record.
"""

from __future__ import annotations

import math
import os

import numpy as np
import pytest

from navalai import grammar
from navalai.blender.metrics import (analytic_probe_points,
                                     chine_dihedral_measured, deviation_by_xl,
                                     mesh_to_analytic_mm)
from navalai.blender.run import BLENDER_BIN, build_via_blender, have_blender
from navalai.blender.spec import shipped_resolution
from navalai.evaluate import sample_valid
from navalai.geometry import Hull, station_geometry
from navalai.mission import MissionSpec
from navalai.stl_forensics import load_stl, mesh_of_hull

requires_blender = pytest.mark.skipif(
    not have_blender(),
    reason=f"no Blender binary at {BLENDER_BIN} (this is the Mac simulation "
           "node's tool; a skip here is not a pass — see "
           "docs/research/BLENDER.md for the recorded measurements)")

#: THE GENOME THE STAGE A TABLE WAS MEASURED ON. Not a version string — the
#: parameter COUNT, because that is what decides whether "hull 14 of
#: `sample_valid(25, MissionSpec(), seed=0)`" names the same boat.
#:
#: Same constant, same reasoning and same discipline as
#: `navalai.admissibility.CALIBRATION_GENOME_N_PARAMS`, which is 15 for the
#: labelled Gate 2U campaign. It is deliberately NOT imported from there: that
#: one records when an OpenFOAM campaign's LABELS went stale, this one records
#: when a published deviation table did, and tying them together would make a
#: future session's decision about one silently decide the other.
STAGE_A_GENOME_N_PARAMS = 15

#: Commit bbf1a47's published post-fix row for hull 14, max analytic-to-mesh
#: deviation in mm by x/L bin at the shipped 600x120. VOID on the current
#: genome; see `stage_a_table_is_transferable`.
STAGE_A_MAX_MM = [0.01, 0.11, 0.36, 0.83, 1.36, 23.53, 1.29, 2.62, 3.03,
                  102.92]

#: RE-MEASURED 2026-08-13 at commit c7b7c4b on the 16-parameter genome, same
#: call, same index, same 600x120 triangulation, with the fillet-aware probe
#: cloud. This is a NEW BASELINE for a NEW HULL, not a loosened old one — the
#: two rows are not comparable term by term and no attempt is made to pretend
#: they are.
SHIPPED_MAX_MM = [7.09, 0.66, 1.07, 0.79, 2.53, 33.95, 2.04, 1.40, 2.11, 3.04]

#: x/L bins dominated by the two KNOWN longitudinal defects, excluded wherever
#: a statement is made about "the rest of the hull": 0.55 is the x_mb station,
#: where a(x)'s two branches meet with a tangent break, and 0.95 is the stem
#: taper. Under the old kernel the same two indices were excluded for the same
#: reason (a plan-form knuckle at x_mb, a `w**0.15` taper at the stem).
PLAIN_BINS = [i for i in range(10) if i not in (5, 9)]


def stage_a_table_is_transferable() -> bool:
    """Does `STAGE_A_MAX_MM` still describe the hull this file builds?

    A probe, not a belief, and keyed on `grammar.N_PARAMS` rather than on a
    hand-maintained flag so nobody can declare the table current by editing a
    string. `navalai/admissibility.py::calibration_is_current` is the pattern.
    """
    return grammar.N_PARAMS == STAGE_A_GENOME_N_PARAMS


@pytest.fixture(scope="module")
def hull14():
    """Index 14 of the seed-0 batch, AS DRAWN: roundness 0.327, a round bilge.

    MEASURED 2026-08-13: Lwl 13.705 m, Cp 0.562, lcb +0.272 %Lwl,
    roundness 0.3271. It is the subject of every deviation measurement here.
    """
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    return Hull(X[14])


@pytest.fixture(scope="module")
def hull14_hard_chine():
    """The same genome with `roundness` set to 0 — a HARD CHINE.

    The chine tests need a hull that has one. Every other gene is index 14's,
    so this is the nearest live analogue of the boat Stage A measured, and at
    roundness 0 `geometry.sample_section` is the pre-rebuild three-point
    section bit for bit (fenced at 1e-12 by `tests/test_geometry_kernel.py`).

    `grammar.check` is asserted here rather than assumed: zeroing a gene moves
    the section-area solve (the fillet's area coefficients c1, c2 go to 2, 1),
    so the chine half-breadth moves, and a fixture that quietly built an
    infeasible hull would put every number below outside the design space.
    """
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    x = np.asarray(X[14], dtype=float).copy()
    x[grammar.NAMES.index("roundness")] = 0.0
    rep = grammar.check(x)
    assert rep.ok, f"the hard-chine reference hull is not L0-feasible: {rep.violations}"
    return Hull(x)


def _blender_pair(hull, tmp_path_factory, tag):
    """(grid, voxel) surfaces for `hull`: the shipped rebuild and the owner's
    proposal, at the SHIPPED triangulation both times."""
    nx, nz = shipped_resolution(hull)
    d = tmp_path_factory.mktemp(tag)
    rg = build_via_blender(hull, d / "grid.stl", nx, nz)
    rv = build_via_blender(hull, d / "voxel.stl", nx, nz, voxel=0.05)
    return ((nx, nz, rg) + load_stl(d / "grid.stl"),
            (rv,) + load_stl(d / "voxel.stl"))


@pytest.fixture(scope="module")
def round_bilge_pair(hull14, tmp_path_factory):
    """hull 14's two surfaces: the shipped rebuild and the voxel remesh.

    ONE fixture producing BOTH, because two fixtures each calling
    `_blender_pair` would invoke Blender four times for two surfaces — and a
    second Blender run is a second surface, not a second reading of the same
    one.
    """
    return _blender_pair(hull14, tmp_path_factory, "blender")


@pytest.fixture(scope="module")
def blender_grid(round_bilge_pair):
    """hull 14 rebuilt through Blender at the SHIPPED 600x120 resolution."""
    return round_bilge_pair[0]


@pytest.fixture(scope="module")
def blender_voxel(round_bilge_pair):
    """The owner's proposal, VERBATIM: the same surface, Remesh VOXEL 0.05 m."""
    return round_bilge_pair[1]


@pytest.fixture(scope="module")
def hard_chine_pair(hull14_hard_chine, tmp_path_factory):
    """The same two surfaces for the HARD-CHINE hull: (grid, voxel)."""
    return _blender_pair(hull14_hard_chine, tmp_path_factory, "blender_hc")


@requires_blender
def test_blender_is_detected_by_the_binary_and_never_by_the_path():
    """Detection must not consult PATH, whatever PATH happens to say.

    MEASURED 2026-08-12: `/Applications/Blender.app/Contents/MacOS/Blender
    --version` reports `Blender 5.2.0 LTS, build date 2026-07-14`, and
    `shutil.which("blender")` on this node returns
    `/opt/homebrew/bin/blender` — a Homebrew cask wrapper symlinked at 15:36
    the same day. Both resolve to the same build.

    So the prior session's "Blender is not installed" was wrong, AND the
    correction that said "there is no PATH symlink, that is all" was also
    wrong. The durable rule survives both: `have_blender()` asks the
    filesystem about an exact binary, so it gives the same answer whether or
    not a wrapper exists and whether or not the caller's PATH includes
    `/opt/homebrew/bin`. This test asserts the INDEPENDENCE, not the state —
    asserting the state is what made the first two claims perishable.
    """
    import shutil

    from navalai.blender.run import blender_version, have_blender
    assert have_blender()
    assert blender_version().startswith("Blender ")

    saved = os.environ.get("PATH", "")
    try:
        os.environ["PATH"] = ""
        assert shutil.which("blender") is None
        assert have_blender(), (
            "have_blender() consulted PATH; it must ask the filesystem about "
            "BLENDER_BIN so an empty PATH cannot read as an absent program")
        assert blender_version().startswith("Blender ")
    finally:
        os.environ["PATH"] = saved


@requires_blender
def test_the_blender_rebuild_is_the_same_surface_as_closed_mesh(hull14,
                                                                blender_grid):
    """Blender is a LOSSLESS CONTAINER for this grid, to float32.

    Combinatorially identical: a bijective vertex map and every triangle of
    `closed_mesh` present in the Blender STL. The only difference is
    coordinate precision — Blender stores mesh coordinates in SINGLE
    precision, MEASURED at 9.67e-07 m worst case on an 11.67 m hull.

    This is the arm that makes the rest of the comparison meaningful: without
    it, a deviation difference could be the container rather than the modifier.
    """
    from scipy.spatial import cKDTree
    nx, nz, rec, Vb, Tb = blender_grid
    Va, Ta = mesh_of_hull(hull14, nx, nz)

    assert len(Tb) == len(Ta)
    assert rec["watertight"] if "watertight" in rec else True
    assert rec["n_open_edges"] == 0
    assert rec["n_non_manifold_edges"] == 0

    d, m = cKDTree(Va).query(Vb)
    assert d.max() < 2e-6, f"coordinate round trip {d.max():.3e} m"
    assert len(set(m.tolist())) == len(Vb), "vertex map is not bijective"
    ka = set(map(tuple, np.sort(Ta, axis=1).tolist()))
    kb = set(map(tuple, np.sort(m[Tb], axis=1).tolist()))
    assert ka == kb, f"{len(ka - kb)} triangles differ from closed_mesh"


def test_the_deviation_table_of_the_shipped_triangulation(hull14):
    """The ruler's regression baseline, and a PROBE that says which table.

    Commit bbf1a47 published hull 14's post-fix row by x/L bin, in mm:

        0.05  0.15  0.25  0.35  0.45  0.55  0.65  0.75  0.85  0.95
        0.01  0.11  0.36  0.83  1.36 23.53  1.29  2.62  3.03 102.92

    THAT TABLE IS VOID ON THIS GENOME AND IS NOT RELAXED TO FIT — it is
    switched out by `stage_a_table_is_transferable()`, which asks
    `grammar.N_PARAMS`. Plates P1/P2 took the genome 15 -> 16, so index 14 of
    the same call is a different boat and there is no arithmetic that carries
    the row across. Re-tuning the old numbers until they passed would be
    calibrating against nothing, which is worse than an honest re-measurement.

    RE-MEASURED 2026-08-13 on the current hull (Lwl 13.705 m, roundness
    0.3271), same 600x120 triangulation, in mm:

        bin        0.05  0.15  0.25  0.35  0.45  0.55  0.65  0.75  0.85  0.95
        Stage A    0.01  0.11  0.36  0.83  1.36 23.53  1.29  2.62  3.03 102.92
        today      7.09  0.66  1.07  0.79  2.53 33.95  2.04  1.40  2.11   3.04

    Two of those movements are mechanisms worth stating, because both look
    like regressions and neither is:

      * 0.95 falls 102.92 -> 3.04. The old kernel closed the DECK at the stem
        with a `w**0.15` envelope whose x-derivative is unbounded there; plate
        P1 deleted it and closes the deck through the flare envelope, which
        goes to zero with a(x). The stem is simply a much gentler curve now.
      * 0.05 rises 0.01 -> 7.09, and it is NOT a section-sampling error.
        MEASURED at x/L 0.0105 the whole topside reads a CONSTANT 7.09 mm, and
        a constant offset across a straight run is a parallel line, i.e. an
        error in x. `closed_mesh` interpolates the station arrays LINEARLY
        between `Hull`'s 41 stations, and bin 0 is where the rocker's
        quadratic and the SAC's aft branch put the most x-curvature. Holding
        nx=600/nz=120 fixed and raising `n_stations` 41 -> 321 takes the
        plain-bin max 7.09 -> 2.04, which is the attribution.

    The 0.55 bin is the x_mb tangent break and its value depends on whether a
    probe lands exactly on x_mb, which is why `analytic_probe_points` inserts
    it; the tolerance below is loose enough for that and nothing else.
    """
    stale = stage_a_table_is_transferable()
    want = STAGE_A_MAX_MM if stale else SHIPPED_MAX_MM
    src = "Stage A" if stale else "the 2026-08-13 re-measured baseline"
    nx, nz = shipped_resolution(hull14)
    V, T = mesh_of_hull(hull14, nx, nz)
    got = deviation_by_xl(hull14, V, T)["max_mm"]
    for i, (g, w) in enumerate(zip(got, want)):
        assert abs(g - w) <= max(0.05, 0.02 * w), (
            f"bin {i} ({(i + 0.5) / 10:.2f}): {g:.2f} mm against {src}'s "
            f"{w:.2f} mm")


def test_the_deviation_ruler_converges_to_the_analytic_surface(hull14):
    """THE RULER'S LIVE FENCE, and it is the one no genome can stale.

    A published table for one hull dies with that hull. What does not is the
    statement the metric exists to make: refine the triangulation toward the
    analytic surface and the deviation must go to zero. A ruler with a FLOOR
    is measuring a shape difference rather than a mesh error, and that is
    exactly the defect this test was written for.

    MEASURED 2026-08-13 on hull 14 (roundness 0.327). `n_stations` is refined
    with (nx, nz) because `closed_mesh` interpolates linearly in x between
    `Hull`'s stations, so leaving it at 41 caps the achievable deviation:

        n_stations   nx   nz   overall max   plain-bin max   rms
                41   75   15        38.385          27.749   4.1769
                81  150   30        23.883          14.650   1.5850
               161  300   60         6.366           4.667   0.3295
               321  600  120         5.592           2.040   0.1325

    31.5x on the rms over a 4x refinement, monotone, with no floor.

    WHAT THIS CAUGHT, and why it is here rather than being an elaboration:
    `analytic_probe_points` used to walk the section keel -> chine -> sheer as
    STRAIGHT SEGMENTS, which is the pre-plate-P2 three-point section. On this
    hull's radiused bilge that cloud lies inside the hull by the depth of the
    fillet, and the ruler read 28.9 / 34.7 / 37.1 / 37.2 / 35.0 / 43.6 / 34.9
    / 34.9 / 30.8 / 21.7 mm — a flat ~35 mm floor, on a triangulation that is
    right. Run against the old probe cloud, this test fails at the first
    assertion, because the fillet does not care how finely you mesh it.
    """
    family = ((41, 75, 15), (81, 150, 30), (161, 300, 60), (321, 600, 120))
    rms = []
    for ns, nx, nz in family:
        h = Hull(np.asarray(hull14.params, dtype=float), n_stations=ns)
        V, T = mesh_of_hull(h, nx, nz)
        rms.append(deviation_by_xl(h, V, T)["rms_mm"])

    assert rms[0] > 1.0, (
        f"the coarsest member reads {rms[0]:.3f} mm rms — a ruler that cannot "
        "see the error in a 75x15 triangulation of a 13.7 m hull is not "
        "measuring the mesh")
    for a, b in zip(rms, rms[1:]):
        assert b < a, f"deviation rose on refinement: {rms}"
    assert rms[0] / rms[-1] > 10.0, (
        f"rms fell only {rms[0] / rms[-1]:.1f}x over the family ({rms}); a "
        "ruler with a floor is measuring a shape difference, not a mesh error "
        "— see analytic_probe_points")


def test_the_probe_cloud_is_the_old_polyline_at_roundness_zero(
        hull14_hard_chine):
    """The fillet-aware probe cloud changed NOTHING for a hard chine.

    `analytic_probe_points` now samples `geometry.sample_section` instead of
    walking keel -> chine -> sheer in straight steps. That is a fix for a
    radiused bilge, and it must not move a single hard-chine number in
    `docs/research/BLENDER.md`: at `roundness == 0` the shape function IS the
    two-segment linear interpolation, so the two clouds have to agree to
    round-off. Asserted at 1e-12, which is the same bar
    `tests/test_geometry_kernel.py` holds the shape function itself to.

    docs/LESSONS.md, "agents that refused": a refactor claimed to be a no-op
    on one branch is a claim, and this is the measurement of it.
    """
    nx, nt = 201, 21
    h = hull14_hard_chine
    L = float(h.x[-1])
    xs = np.unique(np.concatenate([np.linspace(0.0, L, nx),
                                   [grammar.named(h.params)["x_mb"] * L]]))
    zk, yc, zc, ys, zs = station_geometry(h.params, xs)
    legs = []
    for t in np.linspace(0.0, 1.0, nt):                 # keel -> chine
        legs.append(np.stack([xs, yc * t, zk + (zc - zk) * t], axis=1))
    for t in np.linspace(0.0, 1.0, nt)[1:]:             # chine -> sheer
        legs.append(np.stack([xs, yc + (ys - yc) * t, zc + (zs - zc) * t],
                             axis=1))
    old = np.vstack(legs)
    new = analytic_probe_points(h, nx, nt)

    assert new.shape == old.shape
    a = old[np.lexsort(old.T)]
    b = new[np.lexsort(new.T)]
    assert np.abs(a - b).max() < 1e-12, (
        f"the probe cloud moved by {np.abs(a - b).max():.3e} m on a hard "
        "chine; sample_section's roundness-0 branch is supposed to be the old "
        "linear interpolation bit for bit")


@requires_blender
def test_a_005_voxel_remesh_destroys_the_chine(hull14_hard_chine,
                                               hard_chine_pair):
    """THE GUARD, FED THE INPUT IT MUST REJECT.

    The owner's proposal is `voxel_size = 0.05` on a ~13.7 m hull, i.e. a
    50 mm voxel against a knuckle Stage A had just made exact to 1e-9 m.

    MEASURED 2026-08-12 on the 15-parameter genome, chine dihedral 5 mm off
    the knuckle, hulls 4/8/14:

        surface              hull 4   hull 8   hull 14
        current / blender      53.5     69.4      72.0
        voxel 0.05              0.0      0.0       0.0
        voxel 0.025             9.4     14.2       1.7

    RE-MEASURED 2026-08-13 on the hard-chine reference hull (index 14's genome
    with `roundness` = 0), 600x120, dihedral in deg over the offset sweep
    0.005 / 0.0125 / 0.025 / 0.05 / 0.10 m:

        analytic (knuckle)   84.91
        blender grid         84.90  84.90  84.90  84.90  84.90
        voxel 0.05            0.00  35.39  44.82  66.64  84.85

    THE SHAPE OF THE SWEEP IS THE FINDING, and it is exactly what
    `CHINE_OFFSETS_M` was written to expose: a true knuckle is FLAT across the
    sweep, and the remeshed one climbs back toward the true angle as the probe
    walks away from the rounding. Zero degrees at 5 mm is not a rounded chine,
    it is NO chine — both probe points land on the same face — and against
    `surfaceFeatureExtract`'s own 30 deg bar (`includedAngle 150`) the
    remeshed knuckle is not a feature at all until 25 mm off it.

    WHY THIS TEST IS PINNED TO `roundness = 0` RATHER THAN RUN ON INDEX 14 AS
    DRAWN. Index 14 now draws roundness 0.327, so its bilge is a fillet and it
    HAS no knuckle. MEASURED on it, same 600x120 Blender grid: the sweep reads
    0.53 / 10.95 / 21.03 / 60.94 / 77.54 deg — 0.53 at 5 mm on the surface
    that is RIGHT. The voxel arm reads 0.00 there, so on that hull the
    treatment and the control are 0.53 deg apart and the test could not tell a
    destroyed chine from a correct round bilge. Running it there would be
    docs/LESSONS.md defect class 6: measuring at a configuration that does not
    exhibit the phenomenon. The hard-chine hull is also the SKU case.
    """
    _, _, _, Vg, Tg = hard_chine_pair[0]
    _, Vv, Tv = hard_chine_pair[1]
    grid = chine_dihedral_measured(hull14_hard_chine, Vg, Tg)
    vox = chine_dihedral_measured(hull14_hard_chine, Vv, Tv)

    assert grid["median_deg"] == pytest.approx(
        grid["analytic_median_deg"], abs=0.5), (
        "the control arm must show the chine INTACT, or this test cannot "
        "distinguish a destroyed chine from a broken measurement")
    assert grid["median_deg"] > 30.0
    sweep = grid["sweep_median_deg"]
    assert max(sweep) - min(sweep) < 1.0, (
        f"the control's dihedral sweep is not flat ({sweep}); a knuckle reads "
        "the same angle at every offset, so this hull no longer has one and "
        "the treatment arm below is measuring something else")
    assert vox["median_deg"] < 1.0, (
        f"a 0.05 m voxel remesh now preserves the chine at "
        f"{vox['median_deg']:.1f} deg where it measured 0.0 on 2026-08-12 — "
        "re-measure docs/research/BLENDER.md before believing it")
    vs = vox["sweep_median_deg"]
    assert vs[0] < 1.0 < 30.0 < vs[-1], (
        f"the voxel arm's sweep {vs} no longer has the ROUNDING signature "
        "(flat at the knuckle, recovering far from it); re-measure")


@requires_blender
def test_a_005_voxel_remesh_leaves_every_xl_bin_worse(hull14, blender_grid,
                                                      blender_voxel):
    """The deviation cost, in every bin, not only at the bilge.

    MEASURED 2026-08-12 on the 15-parameter genome, hull 14: the current
    path's bins were 0.01 / 0.11 / 0.36 / 0.83 / 1.37 / 23.54 / 1.29 / 2.62 /
    3.03 / 102.92 mm and the voxel arm's 31.15 / 23.62 / 26.56 / 30.26 /
    29.49 / 40.87 / 42.82 / 40.12 / 39.72 / 116.34.

    RE-MEASURED 2026-08-13 on the current hull 14 (roundness 0.327), same
    600x120, with the fillet-aware probe cloud, in mm:

        bin      0.05   0.15   0.25   0.35   0.45   0.55   0.65   0.75   0.85   0.95
        grid     7.09   0.66   1.07   0.79   2.53  33.95   2.04   1.40   2.11   3.04
        voxel   44.70  24.36  24.14  23.10  21.61  48.42  29.85  30.34  29.29  40.28

    Every bin is still worse, and the eight that are not dominated by the two
    known longitudinal defects are worse by 3x to 37x.

    ONE BAR MOVED AND IT IS NOT A RELAXATION. `max(grid over PLAIN_BINS)` was
    < 4.0 and is now < 8.0, because the quantity it bounds went from 3.03 mm
    to 7.09 mm ON A DIFFERENT HULL under a different kernel. The 7.09 is bin
    0 and it is the 41-station linear-in-x interpolation near the transom, not
    a triangulation defect: holding 600x120 fixed and taking `n_stations`
    41 -> 321 moves it to 2.04 (see
    `test_the_deviation_ruler_converges_to_the_analytic_surface`). The other
    bar, `min(voxel over PLAIN_BINS) > 20.0`, is UNCHANGED and still clears by
    1.6 mm — the separation between the arms did not shrink, and that
    separation is what the test is about.
    """
    _, _, _, Vg, Tg = blender_grid
    _, Vv, Tv = blender_voxel
    g = deviation_by_xl(hull14, Vg, Tg)["max_mm"]
    v = deviation_by_xl(hull14, Vv, Tv)["max_mm"]
    assert all(vv > gg for vv, gg in zip(v, g)), (
        "voxel remesh is no longer worse in every bin; re-measure")
    assert min(v[i] for i in PLAIN_BINS) > 20.0
    assert max(g[i] for i in PLAIN_BINS) < 8.0


@requires_blender
def test_the_remeshed_surface_wanders_off_the_hull_as_well_as_short_of_it(
        hull14, blender_grid, blender_voxel):
    """Both directions, because one of them is buyable.

    `deviation_by_xl` asks how much of the hull the mesh failed to reach.
    `mesh_to_analytic_mm` asks how far off the hull the mesh went. A remesh
    that inflates outward can score acceptably on the first alone.

    MEASURED 2026-08-13 on the current hull 14: rms 12.936 mm for the grid
    against 13.816 mm for the voxel arm. Both clouds are now sampled from
    `sample_section`, including the transom cap — with the old straight-leg
    cap, a legitimate transom vertex on a radiused bilge read as a wanderer.
    """
    _, _, _, Vg, Tg = blender_grid
    _, Vv, Tv = blender_voxel
    g = mesh_to_analytic_mm(hull14, Vg, Tg)
    v = mesh_to_analytic_mm(hull14, Vv, Tv)
    assert v["rms_mm"] > g["rms_mm"]


@requires_blender
def test_the_voxel_remesh_stays_closed_and_that_is_not_the_point(
        blender_voxel):
    """Watertightness is NOT the discriminator here, and saying so is the test.

    MEASURED: the voxel remesh IS a closed manifold — `surfaceCheck` reports
    "Surface is closed" on all three hulls — and it is still the wrong
    surface. A closure check cannot see a rounded knuckle or a 40 mm
    deviation, which is the same lesson `navalai/stl_forensics.py` was written
    around: four hulls with different mesh outcomes were all reported
    watertight/outward/0 open edges.
    """
    rec, _V, _T = blender_voxel
    assert rec["n_open_edges"] == 0
    assert rec["n_non_manifold_edges"] == 0


def test_the_knuckle_reference_refuses_a_radiused_bilge(hull14,
                                                        hull14_hard_chine):
    """An unmeasurable quantity is a refusal, never a number.

    `chine_dihedral_analytic` differences the normals of the two STRAIGHT
    panel legs at the chine control point. Plate P2's fillet replaces that
    corner with a quadratic Bezier whose control legs are those same two
    segments, so the formula keeps returning the angle of a corner the
    surface no longer has.

    MEASURED 2026-08-13 on hull 14 (roundness 0.327): it returned **84.90
    deg** while the correct 600x120 triangulation of the same hull reads
    **0.53 deg** 5 mm off the bilge. That is docs/LESSONS.md defect class 1 —
    a quantity that cannot be measured on this hull, scored as a measurement —
    and it would have reported the SHIPPED surface as a destroyed chine.

    Both directions, because a rule that only refuses is not a rule: the same
    genome at roundness 0 must still produce the knuckle angle.
    """
    assert math.isnan(chine_dihedral_measured(
        hull14, *mesh_of_hull(hull14, 120, 24))["analytic_median_deg"]), (
        "the knuckle reference returned a number for a radiused bilge")
    hc = chine_dihedral_measured(hull14_hard_chine,
                                 *mesh_of_hull(hull14_hard_chine, 120, 24))
    assert hc["analytic_median_deg"] == pytest.approx(84.906, abs=0.01), (
        "the knuckle reference refused a HARD chine, which it must not")
