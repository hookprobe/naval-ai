"""Gate tests for `navalai/blender` — the bars are the numbers MEASURED on
2026-08-12 and recorded in `docs/research/BLENDER.md`.

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

These tests SKIP where the Blender binary is absent — fortress001 has no
`/Applications` — and they say so. A skip is not a pass; `docs/research/
BLENDER.md` carries the numbers, so an absent binary loses the fence, not the
record.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

from navalai.blender.metrics import (chine_dihedral_measured, deviation_by_xl,
                                     mesh_to_analytic_mm)
from navalai.blender.run import BLENDER_BIN, build_via_blender, have_blender
from navalai.blender.spec import shipped_resolution
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import MissionSpec
from navalai.stl_forensics import load_stl, mesh_of_hull

pytestmark = pytest.mark.skipif(
    not have_blender(),
    reason=f"no Blender binary at {BLENDER_BIN} (this is the Mac simulation "
           "node's tool; a skip here is not a pass — see "
           "docs/research/BLENDER.md for the recorded measurements)")


@pytest.fixture(scope="module")
def hull14():
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    return Hull(X[14])


@pytest.fixture(scope="module")
def blender_grid(hull14, tmp_path_factory):
    """hull 14 rebuilt through Blender at the SHIPPED 600x120 resolution."""
    nx, nz = shipped_resolution(hull14)
    d = tmp_path_factory.mktemp("blender")
    rec = build_via_blender(hull14, d / "grid.stl", nx, nz)
    return (nx, nz, rec) + load_stl(d / "grid.stl")


@pytest.fixture(scope="module")
def blender_voxel(hull14, tmp_path_factory):
    """The owner's proposal, VERBATIM: the same surface, Remesh VOXEL 0.05 m."""
    nx, nz = shipped_resolution(hull14)
    d = tmp_path_factory.mktemp("blender_voxel")
    rec = build_via_blender(hull14, d / "voxel.stl", nx, nz, voxel=0.05)
    return (rec,) + load_stl(d / "voxel.stl")


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


def test_the_blender_rebuild_is_the_same_surface_as_closed_mesh(hull14,
                                                                blender_grid):
    """Blender is a LOSSLESS CONTAINER for this grid, to float32.

    Combinatorially identical: 288836 triangles, a bijective vertex map, and
    every triangle of `closed_mesh` present in the Blender STL. The only
    difference is coordinate precision — Blender stores mesh coordinates in
    SINGLE precision, MEASURED at 9.67e-07 m worst case on an 11.67 m hull.

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


def test_the_deviation_metric_still_reproduces_the_stage_a_table(hull14):
    """The ruler has not moved.

    Commit bbf1a47 published hull 14's post-fix max analytic-to-mesh deviation
    by x/L bin, in mm:

        0.05  0.15  0.25  0.35  0.45  0.55  0.65  0.75  0.85  0.95
        0.01  0.11  0.36  0.83  1.36 23.53  1.29  2.62  3.03 102.92

    `deviation_by_xl` must reproduce it, or every comparison in
    `docs/research/BLENDER.md` is against a different ruler than Stage A's.
    The 0.55 bin is the x_mb knuckle and its value depends on whether a probe
    lands exactly on x_mb, which is why `analytic_probe_points` inserts it;
    the tolerance below is loose enough for that and nothing else.
    """
    nx, nz = shipped_resolution(hull14)
    V, T = mesh_of_hull(hull14, nx, nz)
    got = deviation_by_xl(hull14, V, T)["max_mm"]
    want = [0.01, 0.11, 0.36, 0.83, 1.36, 23.53, 1.29, 2.62, 3.03, 102.92]
    for i, (g, w) in enumerate(zip(got, want)):
        assert abs(g - w) <= max(0.05, 0.02 * w), (
            f"bin {i} ({(i + 0.5) / 10:.2f}): {g:.2f} mm against Stage A's "
            f"{w:.2f} mm")


def test_a_005_voxel_remesh_destroys_the_chine(hull14, blender_grid,
                                               blender_voxel):
    """THE GUARD, FED THE INPUT IT MUST REJECT.

    The owner's proposal is `voxel_size = 0.05` on a ~11.7 m hull, i.e. a
    50 mm voxel against a knuckle Stage A had just made exact to 1e-9 m.

    MEASURED 2026-08-12, chine dihedral 5 mm off the knuckle, hulls 4/8/14:

        surface              hull 4   hull 8   hull 14
        current / blender      53.5     69.4      72.0
        voxel 0.05              0.0      0.0       0.0
        voxel 0.025             9.4     14.2       1.7

    Zero degrees is not a rounded chine, it is NO chine: both probe points
    land on the same face. Against `surfaceFeatureExtract`'s own 30 deg bar
    (`includedAngle 150`) the remeshed knuckle is not a feature at all.
    """
    _, _, _, Vg, Tg = blender_grid
    _, Vv, Tv = blender_voxel
    grid = chine_dihedral_measured(hull14, Vg, Tg)
    vox = chine_dihedral_measured(hull14, Vv, Tv)

    assert grid["median_deg"] == pytest.approx(
        grid["analytic_median_deg"], abs=0.5), (
        "the control arm must show the chine INTACT, or this test cannot "
        "distinguish a destroyed chine from a broken measurement")
    assert grid["median_deg"] > 30.0
    assert vox["median_deg"] < 1.0, (
        f"a 0.05 m voxel remesh now preserves the chine at "
        f"{vox['median_deg']:.1f} deg where it measured 0.0 on 2026-08-12 — "
        "re-measure docs/research/BLENDER.md before believing it")


def test_a_005_voxel_remesh_leaves_every_xl_bin_worse(hull14, blender_grid,
                                                      blender_voxel):
    """The deviation cost, in every bin, not only at the chine.

    MEASURED on hull 14: the current path's bins are 0.01 / 0.11 / 0.36 /
    0.83 / 1.37 / 23.54 / 1.29 / 2.62 / 3.03 / 102.92 mm and the voxel arm's
    are 31.15 / 23.62 / 26.56 / 30.26 / 29.49 / 40.87 / 42.82 / 40.12 /
    39.72 / 116.34. Every bin is worse, and the eight that are not dominated
    by the two known longitudinal defects (x_mb at 0.55, the stem taper at
    0.95) are worse by 14x to 3000x.
    """
    _, _, _, Vg, Tg = blender_grid
    _, Vv, Tv = blender_voxel
    g = deviation_by_xl(hull14, Vg, Tg)["max_mm"]
    v = deviation_by_xl(hull14, Vv, Tv)["max_mm"]
    assert all(vv > gg for vv, gg in zip(v, g)), (
        "voxel remesh is no longer worse in every bin; re-measure")
    plain = [i for i in range(10) if i not in (5, 9)]
    assert min(v[i] for i in plain) > 20.0
    assert max(g[i] for i in plain) < 4.0


def test_the_remeshed_surface_wanders_off_the_hull_as_well_as_short_of_it(
        hull14, blender_grid, blender_voxel):
    """Both directions, because one of them is buyable.

    `deviation_by_xl` asks how much of the hull the mesh failed to reach.
    `mesh_to_analytic_mm` asks how far off the hull the mesh went. A remesh
    that inflates outward can score acceptably on the first alone.
    """
    _, _, _, Vg, Tg = blender_grid
    _, Vv, Tv = blender_voxel
    g = mesh_to_analytic_mm(hull14, Vg, Tg)
    v = mesh_to_analytic_mm(hull14, Vv, Tv)
    assert v["rms_mm"] > g["rms_mm"]


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
