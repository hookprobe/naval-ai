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
    fillet. Index 14 now draws roundness 0.324, so its bilge is radiused and
    there is no knuckle to destroy — RE-MEASURED 2026-08-20 on the hull it
    draws today, its dihedral 5 mm off the bilge is 0.08 deg on the CORRECT
    triangulation (it was recorded as 0.53 on the phantom hull, see the
    2026-08-20 section below). At `roundness = 0` the
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

WHAT 2026-08-20 FOUND, AND IT IS THE SAME DEFECT ONE LEVEL UP.

`stage_a_table_is_transferable()` was written to stop a published table from
silently outliving the hull it describes. It asks `grammar.N_PARAMS`. MEASURED
2026-08-20, THAT PROBE CANNOT SEE THE CHANGE THAT ACTUALLY INVALIDATED THE
TABLE: commit f18fcba moved the parameter BOX (LWL [4.0, 20.0] -> [2.5, 24.0]
on RCD 2013/53/EU Art. 3(2)) and re-banded L/B and B/T, which changes which
draws survive `sample_valid`'s feasibility filter — so
`sample_valid(25, MissionSpec(), seed=0)[14]` became a different boat while
`N_PARAMS` stayed 16 and the probe stayed silent:

    gene        2026-08-13 baseline    drawn 2026-08-20
    LWL              13.705 m               17.9671 m
    Cp                0.562                  0.6693
    lcb              +0.272 %Lwl            -0.3503 %Lwl
    roundness         0.3271                 0.3237

Two tests then failed reading like mesh regressions and were neither: bin 0 of
the deviation table read 2.86 mm against a pinned 7.09 (a FALL, which is what
made it obvious that better/worse was the wrong question — the boats are not
comparable), and the knuckle reference returned 66.90 deg against a pinned
84.906 under a message that said it had REFUSED a hard chine. It had not
refused anything; it returned the right angle for a different hull.

AND THE PINNED NUMBERS DESCRIBE A TREE THAT NEVER EXISTED ON `master`. They
landed in commit ff621b8, whose own `grammar.N_PARAMS` is **15** — so
`stage_a_table_is_transferable()` was TRUE there, `SHIPPED_MAX_MM` was on the
unreachable branch, and it was never executed once before f18fcba flipped the
probe. Replayed with `git archive` over every commit that touches
`grammar.py`, `evaluate.py` or `mission.py` since, hull 14 reads LWL 11.67 m
at 15 params before f18fcba and 17.9671 m at 16 params from f18fcba onward.
There is no commit on `master` at which it was 13.705 m.

So the fence is now the BOAT and not the genome length: `SHIPPED_HULL` records
the seven genes that name it and the `hull14` fixture refuses a re-draw BY NAME,
which is the failure this file could not previously produce.

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
from navalai.stl_forensics import edge_table, load_stl, mesh_of_hull

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

#: RE-MEASURED 2026-08-20 on the hull `sample_valid(25, MissionSpec(),
#: seed=0)[14]` ACTUALLY DRAWS TODAY (`SHIPPED_HULL` below), same call, same
#: index, same 600x120 triangulation, same fillet-aware probe cloud. This is a
#: NEW BASELINE FOR A NEW HULL, not a loosened old one — the row it replaces
#: was measured on a 13.705 m boat that no commit on `master` ever drew (see
#: the module docstring), so the two are not comparable term by term and no
#: attempt is made to pretend they are.
#:
#: Raw, before rounding to the two decimals the table carries:
#:     2.8559 0.8653 0.8701 0.3963 0.5343 8.0056 2.8469 1.5656 1.8754 46.8136
SHIPPED_MAX_MM = [2.86, 0.87, 0.87, 0.40, 0.53, 8.01, 2.85, 1.57, 1.88, 46.81]

#: THE BOAT ITSELF, because the genome LENGTH is not the boat.
#:
#: MEASURED 2026-08-20 from `grammar.named(sample_valid(25, MissionSpec(),
#: seed=0)[14])`. Every number in this file is a measurement ON THIS HULL, and
#: `hull14` asserts the drawn genome still is it. `STAGE_A_GENOME_N_PARAMS`
#: stays as well, and the two are not redundant: the parameter count says
#: whether the Stage A table can even be indexed, this says whether the boat
#: under the current count is still the one that was measured. f18fcba changed
#: the second without touching the first, which is precisely the case a
#: count-only probe cannot report.
SHIPPED_HULL = {"LWL": 17.9671, "BWL": 3.4891, "T": 1.0167, "D": 2.4965,
                "Cp": 0.6693, "lcb": -0.3503, "roundness": 0.3237}

#: The hull the pinned numbers this file used to carry were measured on. Kept
#: as the VERBATIM input `hull_identity_drift` must reject, because a fence
#: that has only ever been shown to accept proves nothing about refusal
#: (docs/LESSONS.md defect class 3).
PHANTOM_HULL_2026_08_13 = {"LWL": 13.705, "Cp": 0.562, "lcb": 0.272,
                           "roundness": 0.3271}


def hull_identity_drift(params) -> dict:
    """{gene: |drawn - recorded|} over the genes that NAME the reference hull.

    Absolute, not relative: every gene in `SHIPPED_HULL` is O(1)..O(20) and is
    recorded to four decimals, so a drift above `HULL_IDENTITY_TOL` is a
    re-draw and not a rounding difference. A re-draw moves these by whole
    units — LWL moved 4.26 m — so there is no calibration ambiguity in the bar.
    """
    p = grammar.named(np.asarray(params, dtype=float))
    return {k: abs(float(p[k]) - v) for k, v in SHIPPED_HULL.items()}


#: The bar `hull14` holds `hull_identity_drift` to, and both sides of it are
#: MEASURED rather than chosen: `SHIPPED_HULL` is recorded to four decimals so
#: the worst rounding residual against the live draw is 5e-5 (20x below the
#: bar), while the SMALLEST gene movement in the 2026-08-13 -> 2026-08-20
#: re-draw is roundness at 3.4e-3 (3.4x above it) and the largest is LWL at
#: 4.26 m. There is no band in which a re-draw hides.
HULL_IDENTITY_TOL = 1e-3

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

    IT IS NECESSARY AND IT IS NOT SUFFICIENT, MEASURED 2026-08-20. A parameter
    count cannot see a change to the parameter BOX or to the feasibility
    bands, and commit f18fcba changed both — so index 14 became a 17.9671 m
    boat where the tables had been measured on a 13.705 m one, with
    `N_PARAMS` 16 on both sides and this function silent throughout.
    `SHIPPED_HULL` and `hull_identity_drift` are the half that was missing;
    this one still answers the question it was written for, which is whether
    `STAGE_A_MAX_MM` can be indexed at all.
    """
    return grammar.N_PARAMS == STAGE_A_GENOME_N_PARAMS


@pytest.fixture(scope="module")
def hull14():
    """Index 14 of the seed-0 batch, AS DRAWN: roundness 0.324, a round bilge.

    MEASURED 2026-08-20: LWL 17.9671 m, BWL 3.4891 m, T 1.0167 m, D 2.4965 m,
    Cp 0.6693, lcb -0.3503 %Lwl, roundness 0.3237. It is the subject of every
    deviation measurement in this file.

    THE IDENTITY IS ASSERTED HERE, ONCE, AND THAT IS THE POINT. This docstring
    previously read "Lwl 13.705 m, Cp 0.562, lcb +0.272 %Lwl, roundness
    0.3271" and was PROSE, so when the grammar's box moved under it the pinned
    tables failed downstream reading like mesh regressions. A fixture that
    quietly returns a different boat turns every number in the file into a
    comparison between two hulls, which is not a measurement of anything.
    """
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    drift = hull_identity_drift(X[14])
    assert max(drift.values()) <= HULL_IDENTITY_TOL, (
        f"hull 14 HAS BEEN RE-DRAWN: {drift}. Every table in this file was "
        f"measured on {SHIPPED_HULL} (2026-08-20). This has happened before — "
        "commit f18fcba moved the LWL box [4.0, 20.0] -> [2.5, 24.0] and "
        "re-banded L/B and B/T, which changes which draws survive "
        "sample_valid's feasibility filter, and stage_a_table_is_transferable "
        "could not see it because N_PARAMS stayed 16. RE-MEASURE the tables "
        "and record the new hull here; do NOT widen a tolerance, and do not "
        "read a moved number as a mesh regression until the boat matches.")
    return Hull(X[14])


@pytest.fixture(scope="module")
def hull14_hard_chine():
    """The same genome with `roundness` set to 0 — a HARD CHINE.

    The chine tests need a hull that has one. Every other gene is index 14's,
    so this is the nearest live analogue of the boat Stage A measured, and at
    roundness 0 `geometry.sample_section` is the pre-rebuild three-point
    section bit for bit (fenced at 1e-12 by `tests/test_geometry_kernel.py`).

    MEASURED 2026-08-20: LWL 17.9671 m, Cp 0.6693, lcb -0.3503 %Lwl,
    roundness 0.0, and its analytic knuckle dihedral is 66.9041 deg. It
    asserts the genome identity ITSELF rather than leaning on `hull14`:
    `hard_chine_pair` and the probe-cloud test reach this fixture without
    touching that one, so an identity check that lived only there would not
    run for them.

    `grammar.check` is asserted here rather than assumed: zeroing a gene moves
    the section-area solve (the fillet's area coefficients c1, c2 go to 2, 1),
    so the chine half-breadth moves, and a fixture that quietly built an
    infeasible hull would put every number below outside the design space.
    """
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    drift = hull_identity_drift(X[14])
    assert max(drift.values()) <= HULL_IDENTITY_TOL, (
        f"hull 14 HAS BEEN RE-DRAWN: {drift} — see the `hull14` fixture")
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
    # The 2026-08-20 sliver fix (build_hull._triangulate_and_clean) must not
    # reach this path at all: MEASURED 0 degenerate fan triangles at 600x120
    # on both the round bilge and the hard chine, so the triangle-set equality
    # below is a statement about the cage and not about a repair of it.
    assert rec["n_degenerate_faces"] == 0
    assert rec["weld_max_move_m"] == 0.0

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

    RE-BASELINED 2026-08-20, and the row it replaces was for A DIFFERENT BOAT,
    not for a different mesh. `SHIPPED_MAX_MM` had been measured on a hull of
    Lwl 13.705 m / Cp 0.562 / roundness 0.3271; `sample_valid(25,
    MissionSpec(), seed=0)[14]` draws 17.9671 m / 0.6693 / 0.3237 today, and
    no commit on `master` ever drew the first one (module docstring). The
    `hull14` fixture now asserts the identity, so this row can only ever be
    read against the boat it was measured on.

        bin        0.05  0.15  0.25  0.35  0.45  0.55  0.65  0.75  0.85  0.95
        Stage A    0.01  0.11  0.36  0.83  1.36 23.53  1.29  2.62  3.03 102.92
        (phantom)  7.09  0.66  1.07  0.79  2.53 33.95  2.04  1.40  2.11   3.04
        2026-08-20 2.86  0.87  0.87  0.40  0.53  8.01  2.85  1.57  1.88  46.81

    NOTHING IS INFERRED FROM COMPARING THE ROWS TERM BY TERM, and the failure
    that produced this re-baseline is the reason: bin 0 came in at 2.86 mm
    against a pinned 7.09, i.e. the mesh looked to have got BETTER, and a
    session could as easily have "fixed" the code back toward 7.09. Three
    boats, three rows, one comparison each is legitimate — against the
    ANALYTIC surface, which is what the metric measures.

    What IS stated, because it was measured on THIS hull:

      * bin 0 (2.86) is the 41-station linear-in-x interpolation, not a
        triangulation defect. Holding nx=600/nz=120 fixed and raising
        `n_stations`: 41 -> 2.856, 81 -> 0.828, 161 -> 0.504, 321 -> 0.504.
        The same attribution the phantom row carried, re-measured here.
      * bin 9 (46.81, and the overall max at x/L 0.988) is the stem taper,
        which is why 9 is not in `PLAIN_BINS`. It converges: at n_stations 321
        the whole row is 0.50 0.29 0.27 0.29 0.31 0.48 0.35 0.36 0.66 3.98.
        A bin that falls by 12x on refinement is a resolution figure, not a
        shape error, and `test_the_deviation_ruler_converges_to_the_analytic_
        surface` is the fence that says so without pinning a number.

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

    RE-MEASURED 2026-08-20 on the hull hull 14 draws today (LWL 17.9671 m,
    roundness 0.3237). `n_stations` is refined with (nx, nz) because
    `closed_mesh` interpolates linearly in x between `Hull`'s stations, so
    leaving it at 41 caps the achievable deviation:

        n_stations   nx   nz   overall max   plain-bin max   rms
                41   75   15        65.149          33.184   6.6368
                81  150   30        23.040           6.694   1.6895
               161  300   60         6.838           2.452   0.4425
               321  600  120         3.978           0.656   0.1175

    56.5x on the rms over a 4x refinement, monotone, with no floor. (The row
    this replaces read 31.5x on the phantom hull; the STATEMENT — monotone,
    no floor, better than 10x — is what the assertions hold, and it survived
    the boat changing under it, which is exactly why it is the live fence and
    the table is not.)

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

    RE-MEASURED 2026-08-20 on the hard-chine reference hull (index 14's genome
    with `roundness` = 0, LWL 17.9671 m), 600x120, dihedral in deg over the
    offset sweep 0.005 / 0.0125 / 0.025 / 0.05 / 0.10 m:

        analytic (knuckle)   66.90
        blender grid         66.89  66.90  66.90  66.90  66.90
        voxel 0.05            0.00  27.21  38.31  57.32  66.90

    (The row this replaces read 84.91 / 84.90 / 0.00-84.85; that was the
    phantom hull of the module docstring. The SHAPE of both arms is
    unchanged, which is the finding.)

    THE SHAPE OF THE SWEEP IS THE FINDING, and it is exactly what
    `CHINE_OFFSETS_M` was written to expose: a true knuckle is FLAT across the
    sweep, and the remeshed one climbs back toward the true angle as the probe
    walks away from the rounding. Zero degrees at 5 mm is not a rounded chine,
    it is NO chine — both probe points land on the same face — and against
    `surfaceFeatureExtract`'s own 30 deg bar (`includedAngle 150`) the
    remeshed knuckle is not a feature at all until 25 mm off it.

    WHY THIS TEST IS PINNED TO `roundness = 0` RATHER THAN RUN ON INDEX 14 AS
    DRAWN. Index 14 draws roundness 0.3237, so its bilge is a fillet and it
    HAS no knuckle. RE-MEASURED on it 2026-08-20, same 600x120 Blender grid:
    the sweep reads 0.08 / 3.96 / 4.17 / 12.06 / 23.01 deg — 0.08 at 5 mm on
    the surface that is RIGHT. The voxel arm reads 0.00 there, so on that hull
    the treatment and the control are 0.08 deg apart and the test could not
    tell a destroyed chine from a correct round bilge. Running it there would be
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

    RE-MEASURED 2026-08-20 on the hull hull 14 draws today (LWL 17.9671 m,
    roundness 0.3237), same 600x120, same fillet-aware probe cloud, in mm:

        bin      0.05   0.15   0.25   0.35   0.45   0.55   0.65   0.75   0.85   0.95
        grid     2.86   0.87   0.87   0.40   0.53   8.01   2.85   1.57   1.88  46.81
        voxel   36.16  35.31  34.17  34.22  34.81  35.96  41.38  36.54  37.19  69.03

    Every bin is still worse, and the eight that are not dominated by the two
    known longitudinal defects are worse by 12.7x to 86.3x — the separation
    the test is about WIDENED.

    ONE BAR MOVED AND IT IS A TIGHTENING, NOT A RELAXATION. `max(grid over
    PLAIN_BINS)` was < 8.0, calibrated on a 7.09 mm bin 0 that belonged to a
    boat this repository never drew (module docstring). On the hull that IS
    drawn the quantity is 2.856 mm, so the bar goes to 4.0 — the same ~40%
    headroom the previous author left, over a number that was actually
    measured here. The other bar, `min(voxel over PLAIN_BINS) > 20.0`, is
    UNCHANGED and now clears by 14.2 mm instead of 1.6.
    """
    _, _, _, Vg, Tg = blender_grid
    _, Vv, Tv = blender_voxel
    g = deviation_by_xl(hull14, Vg, Tg)["max_mm"]
    v = deviation_by_xl(hull14, Vv, Tv)["max_mm"]
    assert all(vv > gg for vv, gg in zip(v, g)), (
        "voxel remesh is no longer worse in every bin; re-measure")
    assert min(v[i] for i in PLAIN_BINS) > 20.0
    assert max(g[i] for i in PLAIN_BINS) < 4.0


@requires_blender
def test_the_remeshed_surface_wanders_off_the_hull_as_well_as_short_of_it(
        hull14, blender_grid, blender_voxel):
    """Both directions, because one of them is buyable.

    `deviation_by_xl` asks how much of the hull the mesh failed to reach.
    `mesh_to_analytic_mm` asks how far off the hull the mesh went. A remesh
    that inflates outward can score acceptably on the first alone.

    RE-MEASURED 2026-08-20 on the hull hull 14 draws today: rms 20.213 mm for
    the grid against 22.909 mm for the voxel arm (the row this replaces read
    12.936 / 13.816 on the phantom hull). Both clouds are sampled from
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

    AND ON 2026-08-20 IT WAS NOT CLOSED: this test failed `assert 8 == 0`, and
    the eight open edges were REAL — `stl_forensics.edge_table` on the
    exported STL counts the same eight. `build_hull._triangulate_and_clean`
    DELETED any fan triangle under 1e-10 m^2, and the voxel remesher emits two
    mirror-image micro-quads (~5.3e-13 m^2, edges 2.0e-07 and 2.6e-06 m) at
    the transom/deck/sheer corner, x ~ 0, y = +-1.4000001, z = 1.45. Deleting
    a face whose three vertices are DISTINCT leaves its edges bounded by one
    face each; that is a hole, and CLAUDE.md's CFD section records that
    interFoam floods the interior of an open shell.

    The fix collapses the shortest edge of a degenerate triangle instead of
    deleting the face, so the assertions below are joined by the receipt
    fields that prove this test is not vacuous. WITHOUT THEM it would pass on
    a build where the remesher had simply stopped producing slivers, and the
    guard would be unexercised — docs/LESSONS.md defect class 3, in the mild
    direction.

    MEASURED after the fix, on BOTH reference hulls' voxel arms:
    `n_degenerate_faces` 4, `n_degenerate_collapsed` 4, `n_degenerate_kept` 0,
    `n_faces_welded_away` 8, `weld_max_move_m` 2.384185791015625e-07 m (a
    quarter micron, below the 9.4e-07 m single-precision coordinate round trip
    on the same mesh), `n_open_edges` 0, `n_non_manifold_edges` 0. Signed
    volume moves 112.94397334442795 -> 112.94397334438304 m^3, 4e-13 relative.
    """
    rec, _V, _T = blender_voxel
    assert rec["n_open_edges"] == 0
    assert rec["n_non_manifold_edges"] == 0
    assert rec["n_degenerate_faces"] > 0, (
        "the voxel remesh no longer produces a degenerate triangle, so this "
        "test no longer exercises the 2026-08-20 hole — re-measure "
        "build_hull._triangulate_and_clean against a surface that does, or "
        "this assertion is decoration")
    assert rec["n_degenerate_collapsed"] == rec["n_degenerate_faces"]
    assert rec["n_degenerate_kept"] == 0, (
        f"{rec['n_degenerate_kept']} degenerate triangles could not be "
        "collapsed and are still in the surface; that is the honest outcome "
        "for a CAP, but it means a zero-area triangle ships to "
        "surfaceFeatureExtract and it must be looked at")
    assert 0.0 < rec["weld_max_move_m"] < 1e-6, (
        f"the collapse moved a vertex by {rec['weld_max_move_m']:.3e} m; the "
        "operation is supposed to be smaller than the single-precision "
        "coordinate round trip, not a reshaping of the surface")


def test_the_knuckle_reference_refuses_a_radiused_bilge(hull14,
                                                        hull14_hard_chine):
    """An unmeasurable quantity is a refusal, never a number.

    `chine_dihedral_analytic` differences the normals of the two STRAIGHT
    panel legs at the chine control point. Plate P2's fillet replaces that
    corner with a quadratic Bezier whose control legs are those same two
    segments, so the formula keeps returning the angle of a corner the
    surface no longer has.

    RE-MEASURED 2026-08-20 on the hull hull 14 draws today (roundness 0.3237):
    it returns **66.90 deg** while the correct 600x120 triangulation of the
    same hull reads **0.08 deg** 5 mm off the bilge. That is docs/LESSONS.md
    defect class 1 — a quantity that cannot be measured on this hull, scored
    as a measurement — and it would have reported the SHIPPED surface as a
    destroyed chine.

    Both directions, because a rule that only refuses is not a rule: the same
    genome at roundness 0 must still produce the knuckle angle.

    THE HARD-CHINE ARM USED TO PIN 84.906 AND THAT WAS THE WRONG KIND OF
    ASSERTION. It is a magic number for one boat, and when `sample_valid`
    re-drew hull 14 (module docstring) it failed at 66.904 under the message
    "the knuckle reference refused a HARD chine, which it must not" — while
    the reference had refused nothing and had returned the correct angle for
    the hull it was handed. A number that can only ever be right for one draw
    reports a re-draw as a code defect.

    So the arm now asserts the reference against an INDEPENDENT measurement of
    the same angle: `chine_dihedral_measured` reads the dihedral off the
    triangulation's FACE NORMALS, which shares no code with
    `chine_dihedral_analytic`'s difference of the two panel normals. MEASURED
    2026-08-20 on the hard-chine reference hull:

        surface                 analytic   measured (5 mm)   sweep
        mesh_of_hull 120x24      66.9041      66.8943        flat 66.89-66.90
        mesh_of_hull 300x60      66.9041      66.8943        flat 66.89-66.90
        mesh_of_hull 600x120     66.9041      66.8943        flat 66.89-66.90

    0.0098 deg apart and independent of the triangulation, which is what a
    knuckle angle should be. That statement survives any re-draw; 84.906 did
    not survive one.
    """
    assert math.isnan(chine_dihedral_measured(
        hull14, *mesh_of_hull(hull14, 120, 24))["analytic_median_deg"]), (
        "the knuckle reference returned a number for a radiused bilge")
    hc = chine_dihedral_measured(hull14_hard_chine,
                                 *mesh_of_hull(hull14_hard_chine, 120, 24))
    ref = hc["analytic_median_deg"]
    assert math.isfinite(ref), (
        "the knuckle reference refused a HARD chine, which it must not")
    assert ref > 30.0, (
        f"the knuckle reference reads {ref:.3f} deg on a hard chine, below "
        "surfaceFeatureExtract's own 30 deg bar — that is not a knuckle")
    assert ref == pytest.approx(hc["median_deg"], abs=0.05), (
        f"the knuckle reference {ref:.4f} deg disagrees with the same angle "
        f"measured off the triangulation's face normals "
        f"({hc['median_deg']:.4f} deg); one of the two is wrong and the "
        "pinned-constant version of this test could not have told you which")


def test_the_hull_identity_fence_refuses_the_boat_it_was_calibrated_on():
    """THE FENCE THAT WAS MISSING, PROVED IN BOTH DIRECTIONS.

    THE INCIDENT, 2026-08-20. Three tests in this file failed at once and two
    of them were not code defects: the deviation table read bin 0 at 2.86 mm
    against a pinned 7.09, and the knuckle reference returned 66.904 deg
    against a pinned 84.906 under the message "the knuckle reference refused a
    HARD chine, which it must not" — while it had refused nothing. Both
    numbers had been measured on a hull of LWL 13.705 m / Cp 0.562 /
    lcb +0.272 / roundness 0.3271, and `sample_valid(25, MissionSpec(),
    seed=0)[14]` draws 17.9671 / 0.6693 / -0.3503 / 0.3237.

    `stage_a_table_is_transferable()` was supposed to catch exactly this and
    could not: it asks `grammar.N_PARAMS`, and f18fcba changed the parameter
    BOX and the feasibility BANDS while leaving the count at 16. A probe that
    cannot fire on the case it exists for is docs/LESSONS.md defect class 3.

    Both directions, because a fence shown only to accept proves nothing:

      * it accepts the genome the file's tables were measured on, and
      * it REFUSES the phantom hull, fed verbatim from
        `PHANTOM_HULL_2026_08_13` — the exact boat whose numbers stood in this
        file for a week, on a tree that never existed on `master`.
    """
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    drift = hull_identity_drift(X[14])
    assert set(drift) == set(SHIPPED_HULL), "the probe stopped reading a gene"
    assert max(drift.values()) <= HULL_IDENTITY_TOL, (
        f"the reference hull moved: {drift}")

    phantom = np.asarray(X[14], dtype=float).copy()
    for gene, value in PHANTOM_HULL_2026_08_13.items():
        phantom[grammar.NAMES.index(gene)] = value
    d = hull_identity_drift(phantom)
    assert max(d.values()) > HULL_IDENTITY_TOL, (
        "the identity fence ACCEPTS the 2026-08-13 phantom hull, so it would "
        f"not have fired on the re-draw that caused this test to exist: {d}")
    assert d["LWL"] > 4.0, (
        f"LWL drift reads {d['LWL']:.4f} m; the two boats are 4.26 m apart "
        "and a fence that cannot see that is not measuring identity")

    # A one-part-in-1e4 nudge of a single gene must also be refused: the bar
    # is 1e-3 absolute and the recorded values are exact to 5e-5, so there is
    # no band in which a re-draw hides.
    nudged = np.asarray(X[14], dtype=float).copy()
    nudged[grammar.NAMES.index("LWL")] += 0.01
    assert max(hull_identity_drift(nudged).values()) > HULL_IDENTITY_TOL


@requires_blender
def test_the_voxel_stl_on_disk_is_closed_and_not_merely_the_receipt(
        blender_voxel):
    """CHECK THE ARTEFACT, NOT THE SUMMARY OF IT (docs/LESSONS.md, 2026-08-20).

    `test_the_voxel_remesh_stays_closed_and_that_is_not_the_point` reads
    `n_open_edges` out of the Blender receipt, i.e. out of a bmesh built
    inside the same function that made the hole. That is the receipt's own
    account of the receipt's own work, and this repository's most expensive
    defect class is a receipt that lies — a `${VAR:-0}`, a layer table
    printing the REQUESTED spec as the ACHIEVED one, a summariser's `[:88]`.

    So the same question is asked of the STL ON DISK, by the module that owns
    it: `stl_forensics.edge_table` over the exported triangles. MEASURED
    2026-08-20 BEFORE the fix, this arm read 8 open edges on the file, in
    agreement with the receipt — so the receipt was honest that day and the
    hole was real. It is asserted anyway, because the day it disagrees is the
    day the number in the other test stops meaning anything.
    """
    rec, V, T = blender_voxel
    et = edge_table(np.asarray(T, dtype=int))
    n_open = int(np.sum(et["count"] == 1))
    n_nonmanifold = int(np.sum(et["count"] > 2))
    assert n_open == 0, (
        f"the exported STL has {n_open} open edges while the receipt claims "
        f"{rec['n_open_edges']}; an open shell floods its interior in "
        "interFoam (CLAUDE.md) and stl_watertight_report gates it")
    assert n_nonmanifold == 0
    assert n_open == rec["n_open_edges"], (
        f"receipt says {rec['n_open_edges']} open edges, the file has "
        f"{n_open} — one of the two is not describing this surface")
    assert len(T) == rec["n_tris"], (
        f"receipt says {rec['n_tris']} triangles, the file has {len(T)}")
