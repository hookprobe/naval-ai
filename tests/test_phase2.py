"""Gate 2 (this-machine scope): Capytaine wired correctly (Hulme hemisphere
anchor), hull BEM runs with convergence sweep, CFD case generation deterministic."""

import math
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from navalai.cfd.case import write_resistance_case
from navalai.geometry import Hull
from navalai.seakeeping import (convergence_sweep, heave_coeffs,
                                hemisphere_added_mass_lowfreq)
from tests.test_phase0 import mid_params

# C-30: the importorskip was MODULE-level, so a box without capytaine
# skipped all 18 tests — 15 of which (every case-generation test below the
# first three) never touch the BEM stack: seakeeping's capytaine imports
# are function-level by design. The skip now lives in exactly the three
# tests that call into the BEM, and the case-generation gate runs
# everywhere.


# THESE TESTS INSPECT BLOCK STRUCTURE AND NEVER SOLVE (2026-08-20).
# `write_resistance_case` refuses a scale whose background z-bands collapse to
# a single cell, because a one-cell WAVE band is not a coarse free surface —
# it is no free surface, and a run on it would be decoration. That guard is
# right for a case somebody intends to solve and wrong for these, which write
# tiny cases at scale 0.5 purely to check where the waterline lands, whether
# the background cell is near-isotropic and what the motion dicts contain.
# Refusing them would be judging a configuration by a bar belonging to a
# different use — the trap CLAUDE.md names. So they DECLARE that they will
# not solve, by name, and `case.info` records `collapsed_z_bands` on every
# case written that way.

def test_hemisphere_hulme_anchor():
    pytest.importorskip("capytaine")
    """Hulme (1982): heave added mass of a floating hemisphere at omega->0 is
    0.8310 x displaced mass. Coarse-mesh tolerance 6%."""
    ratio = hemisphere_added_mass_lowfreq(n_theta=20, n_phi=40, omega=0.15)
    assert ratio == pytest.approx(0.8310, rel=0.06), f"got {ratio:.4f}"


def test_hull_heave_coeffs_physical():
    pytest.importorskip("capytaine")
    h = Hull(mid_params())
    omegas = np.array([0.8, 1.5, 2.5])
    am, dp, nb = heave_coeffs(h, omegas, nx=24, nz=6)
    assert nb > 200
    assert (am > 0).all()            # heave added mass positive
    assert (dp >= -1e-6).all()       # radiation damping non-negative


def test_convergence_sweep_reports_uncertainty():
    pytest.importorskip("capytaine")
    h = Hull(mid_params())
    vals, panels, rel = convergence_sweep(h, omega=1.2,
                                          levels=((16, 4), (24, 6), (32, 8)))
    assert panels[2] > panels[0]
    assert rel < 0.25, f"mesh far from convergence: {vals}"


def test_cfd_case_generation_deterministic(tmp_path):
    h = Hull(mid_params())
    meta1 = write_resistance_case(h, 2.5, tmp_path / "a")
    meta2 = write_resistance_case(h, 2.5, tmp_path / "b")
    assert meta1["stl_sha256"] == meta2["stl_sha256"]
    # a COMPLETE runnable case: mesh, schemes, fields, physics, decomposition
    for rel in ("system/controlDict", "system/blockMeshDict",
                "system/snappyHexMeshDict", "system/fvSchemes",
                "system/fvSolution", "system/decomposeParDict",
                "system/setFieldsDict", "system/surfaceFeatureExtractDict",
                "constant/transportProperties", "constant/turbulenceProperties",
                "constant/g", "0/U", "0/p_rgh", "0/alpha.water", "0/k",
                "0/omega", "0/nut"):
        assert (tmp_path / "a" / rel).exists(), rel
    assert "Gate 2M" in (tmp_path / "a" / "case.info").read_text()
    # CFD hull must be a closed manifold (Mac smoke run found 198 open edges
    # on the wetted-only shell) with outward windings and plausible volume
    from navalai.cfd.case import stl_watertight_report
    rep = stl_watertight_report(tmp_path / "a" / "constant" / "triSurface" / "hull.stl")
    assert rep["watertight"], rep
    assert 10.0 < rep["signed_volume"] < 60.0
    # v2606 mandatory addLayers entries present
    snappy = (tmp_path / "a" / "system" / "snappyHexMeshDict").read_text()
    for key in ("maxFaceThicknessRatio", "maxThicknessToMedialRatio",
                "minMedialAxisAngle", "nBufferCellsNoExtrude", "nLayerIter"):
        assert key in snappy, key
    # v2606 also demands meshQualityControls/relaxed once layer addition
    # reaches nRelaxedIter: without it snappy dies with a FATAL IO ERROR
    # ("Entry 'relaxed' not found") AFTER building the mesh. Hidden while
    # nSurfaceLayers was 3; it surfaced the moment the near-wall fix asked
    # for 6 layers, killing the sweep mid-run.
    assert "relaxed" in snappy, "meshQualityControls/relaxed missing"
    relaxed = snappy.split("relaxed", 1)[1]
    for key in ("maxNonOrtho", "maxBoundarySkewness", "minTwist"):
        assert key in relaxed, f"relaxed block missing {key}"
    # inlet alpha must be height-stratified (air-injection drain bug, smoke #2)
    alpha = (tmp_path / "a" / "0" / "alpha.water").read_text()
    assert "exprFixedValue" in alpha and "pos().z()" in alpha
    # GCI triplet scaling actually changes the background mesh
    m_fine = write_resistance_case(h, 2.5, tmp_path / "c", scale=2.0)
    assert m_fine["bg_cells"] > 6 * meta1["bg_cells"]


def test_free_surface_is_resolved_and_refinement_is_systematic(tmp_path):
    """Mac GCI incident (2026-08-04): the own-hull triplet reported p=nan and
    GCI 58.5% (oscillatory) even after the waterline-alignment fix. Two causes,
    both measured: refinementRegions was EMPTY, so the wave field ran at
    5.1/7.1/10.2 cells per wavelength against the >=20 standard with a
    background cell 0.63-1.25 m tall against ~0.1 m waves; and snapping nz to a
    multiple of 3 gave z-refinement ratios of 1.333 and 1.5, so the three grids
    were never a refinement family (effective r = 1.297 then 1.368).
    """
    h = Hull(mid_params())
    metas = {n: write_resistance_case(h, 2.57, tmp_path / n, scale=s, allow_collapsed_bands=True)
             for n, s in (("coarse", 1.0), ("medium", 2 ** 0.5), ("fine", 2.0))}

    for name, m in metas.items():
        # the bar the wave field failed by 4x before the fix
        assert m["cells_per_wavelength"] >= 20.0, (name, m)
        snappy = (tmp_path / name / "system" / "snappyHexMeshDict").read_text()
        assert "freeSurface" in snappy, f"{name}: no free-surface refinement"
        assert "refinementRegions {}" not in snappy, f"{name}: empty regions"

    # systematic refinement: a CONSISTENT r, close to the sqrt(2) claimed
    r12 = (metas["medium"]["bg_cells"] / metas["coarse"]["bg_cells"]) ** (1 / 3)
    r23 = (metas["fine"]["bg_cells"] / metas["medium"]["bg_cells"]) ** (1 / 3)
    assert abs(r12 - 2 ** 0.5) < 0.03, r12
    assert abs(r23 - 2 ** 0.5) < 0.03, r23
    assert abs(r12 - r23) / max(r12, r23) < 0.02, (r12, r23)


def test_waterline_sits_on_a_block_face_for_any_cell_count(tmp_path):
    """The z=0 split is a blockMesh BLOCK BOUNDARY, so a mesh face lies on the
    waterline by construction. This replaces the 'nz must be a multiple of 3'
    rule, which held only for the specific 1.5L/0.75L domain and put the
    medium grid's interface mid-cell (nz=25) -- doubling its drag.

    The stack is now FOUR blocks (deep / hull band / wave band / air), after
    the DTCHull reference: the two middle bands are UNIFORM so the keel is as
    well resolved in z as the waterline. The single graded block it replaced
    left the keel coarse. z=0 is the boundary between the hull and wave bands.
    """
    h = Hull(mid_params())
    # deliberately awkward scales: none of these would give a "nice" cell count
    for i, s in enumerate((1.0, 2 ** 0.5, 2.0, 1.234, 0.777)):
        meta = write_resistance_case(h, 2.57, tmp_path / f"s{i}", scale=s, allow_collapsed_bands=True)
        text = (tmp_path / f"s{i}" / "system" / "blockMeshDict").read_text()
        assert text.count("hex (") == 4, "expected the 4-band z stack"
        # a vertex ring sits exactly on z=0, whatever the cell counts
        assert re.search(r"\(-?[\d.]+ -?[\d.]+ 0\)", text), text[:400]
        # and the two middle bands are UNIFORM (grading 1 1 1), which is what
        # makes the keel region resolved rather than graded away
        assert text.count("simpleGrading (1 1 1)") == 2, text[:600]
        assert meta["tank_depth"] > 0


def test_case_keeps_pristine_initial_fields_for_re_meshing(tmp_path):
    """Measured 2026-08-05: re-running the pipeline in a used case directory
    killed snappyHexMesh with an FPE in markFeatureCellLevel (exit 132) on a
    case that had meshed cleanly minutes earlier. Cause: setFields rewrites
    0/alpha.water as a full non-uniform field sized for the SNAPPED mesh
    (1.67 MB vs 817 B pristine), so the next blockMesh+snappy saw a field with
    the wrong cell count. 0.orig is the restore point; run-case.sh copies it
    back before every re-mesh.
    """
    h = Hull(mid_params())
    write_resistance_case(h, 2.57, tmp_path / "c", scale=1.0)
    case = tmp_path / "c"

    fields = ("U", "p_rgh", "alpha.water", "k", "omega", "nut")
    for f in fields:
        assert (case / "0.orig" / f).exists(), f"0.orig missing {f}"
        assert (case / "0" / f).exists(), f"0 missing {f}"
        assert (case / "0.orig" / f).read_text() == (case / "0" / f).read_text()

    # initial alpha must be UNIFORM: that is what makes it mesh-independent
    alpha = (case / "0.orig" / "alpha.water").read_text()
    assert "internalField   uniform 0" in alpha or \
           "internalField uniform 0" in alpha, alpha[:200]

    # simulate what setFields does, then confirm 0.orig is still the clean copy
    (case / "0" / "alpha.water").write_text("CLOBBERED BY setFields\n" * 500)
    assert (case / "0.orig" / "alpha.water").read_text() == alpha
    # and that restoring is a plain copy (what run-case.sh performs)
    shutil.rmtree(case / "0")
    shutil.copytree(case / "0.orig", case / "0")
    assert (case / "0" / "alpha.water").read_text() == alpha

    runner = (Path(__file__).resolve().parents[1] /
              "navalai" / "cfd" / "run-case.sh").read_text()
    assert "0.orig" in runner, "runner must restore pristine fields"


def test_near_wall_spacing_targets_the_wall_function_band(tmp_path):
    """Measured on the Mac (2026-08-04) once a yPlus function object existed:
    3 RELATIVE-sized layers gave hull y+ min 42 / avg 7491 / max 60017, one to
    three orders above the build plan's y+ ~ 30. Wall functions were being
    applied far outside their valid band, and skin friction is most of this
    hull's drag at Fn 0.26 -- so the triplet would have converged on a wrong
    number. First-layer thickness is now absolute, from the ITTC-57 line.
    """
    from navalai.cfd.case import first_layer_thickness

    # ITTC-57 at the reference condition: y+ 30 wants a ~0.7 mm first cell
    t1 = first_layer_thickness(2.57, 10.0, 30.0)
    assert 5e-4 < t1 < 1e-3, t1
    # y+ target and thickness are proportional
    assert first_layer_thickness(2.57, 10.0, 60.0) == pytest.approx(2 * t1,
                                                                    rel=1e-9)
    # faster ship -> thinner first cell (higher u_tau)
    assert first_layer_thickness(5.0, 10.0, 30.0) < t1

    h = Hull(mid_params())
    write_resistance_case(h, 2.57, tmp_path / "y", scale=1.0)
    snappy = (tmp_path / "y" / "system" / "snappyHexMeshDict").read_text()
    assert "relativeSizes false" in snappy, "relative sizing caused y+ ~ 7500"
    assert "firstLayerThickness" in snappy
    m = re.search(r"firstLayerThickness ([\d.e+-]+)", snappy)
    # The generator's target moved 30 -> 100 (see _TARGET_YPLUS). At y+ 30 the
    # requested 0.795 mm first layer against a 19 mm hull cell was a 28:1 jump
    # that snappy's medial-axis solver refused to bridge: extrusion decayed to
    # ZERO and the mesh shipped with no prism layers while the summary table
    # kept printing the requested spec. So this asserts against the GENERATOR's
    # own target, not a hard-coded y+ 30 value, and the wall-model band is
    # checked separately below.
    from navalai.cfd.case import _TARGET_YPLUS
    t_gen = first_layer_thickness(2.57, 10.0, _TARGET_YPLUS)
    assert float(m.group(1)) == pytest.approx(t_gen, rel=1e-3)
    # ...and the target must stay inside the log-layer band the wall functions
    # are valid in. 30 sits at the buffer-layer edge (measured min y+ was 12.8,
    # already below the log layer); 300 is the upper end of the standard band.
    assert 30.0 <= _TARGET_YPLUS <= 300.0

    # the y+ instrumentation itself must be wired, or this regresses unseen
    ctrl = (tmp_path / "y" / "system" / "controlDict").read_text()
    assert "yPlus" in ctrl and "fieldFunctionObjects" in ctrl

    # the wall model is held FIXED across the triplet, so GCI bounds the outer
    # flow: first-layer thickness must NOT vary with grid scale
    coarse = write_resistance_case(h, 2.57, tmp_path / "yc", scale=1.0)
    fine = write_resistance_case(h, 2.57, tmp_path / "yf", scale=2.0)
    def first_layer(p):
        t = (p / "system" / "snappyHexMeshDict").read_text()
        return float(re.search(r"firstLayerThickness ([\d.e+-]+)", t).group(1))
    assert first_layer(tmp_path / "yc") == pytest.approx(
        first_layer(tmp_path / "yf"), rel=1e-9)
    assert coarse["bg_cells"] < fine["bg_cells"]


def test_tank_deepens_with_speed_instead_of_faking_deep_water(tmp_path):
    """Deep water is a property of the wave (lambda/2 = pi*U^2/g), not of LWL.
    A fixed 0.6L tank would be shallow above ~4.3 m/s for this hull and would
    return shallow-water resistance under a deep-water label.
    """
    h = Hull(mid_params())
    for speed in (2.57, 5.0, 7.0):
        m = write_resistance_case(h, speed, tmp_path / f"u{speed}")
        half_lambda = math.pi * speed ** 2 / 9.81
        assert m["tank_depth"] >= half_lambda, (speed, m["tank_depth"])


def _kcs_or_skip():
    stl = Path(__file__).parents[1] / "data/benchmark_geom/kcs.stl"
    if not stl.exists():
        pytest.skip("KCS geometry not generated (see benchmarks/kcs.py recipe)")
    return str(stl)


def _background_cell(case):
    """(dx, dy, dz) of the ungraded core blockMesh cell, in metres."""
    d = (Path(case) / "system/blockMeshDict").read_text()
    body = d[d.index("vertices"):d.index("blocks")]
    verts = [tuple(map(float, m)) for m in re.findall(
        r"\(\s*(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s*\)", body)]
    xs = sorted({v[0] for v in verts})
    ys = sorted({v[1] for v in verts})
    zs = sorted({v[2] for v in verts})
    blocks = re.findall(
        r"hex \([^)]*\)\s*\((\d+)\s+(\d+)\s+(\d+)\)\s*simpleGrading \(([^)]*)\)", d)
    nx, ny, _, _ = blocks[0]
    core = [(int(nz), i) for i, (_, _, nz, g) in enumerate(blocks)
            if [float(v) for v in g.split()] == [1.0, 1.0, 1.0]]
    assert core, "no ungraded core block -- the hull would sit in graded cells"
    dz = min((zs[i + 1] - zs[i]) / nz for nz, i in core)
    return (xs[-1] - xs[0]) / int(nx), (ys[-1] - ys[0]) / int(ny), dz


# ---------------------------------------------------------------------------
# Incident (2026-08-05): snappyHexMesh could not refine the hull past level
# (2,3). Level (3,4) produced 3 zero-volume and 49 wrongly-oriented faces,
# (4,5) produced 149 and 938, and checkMesh "Failed 5 mesh checks". Weeks of
# snapControls/addLayers tuning changed nothing, because the cause was not in
# either control set: the BACKGROUND CELL was 606 x 910 x 16 mm, a 38:1 slab.
# snappyHexMesh refines ISOTROPICALLY (hexRef8 halves all three edges), so the
# aspect ratio is PRESERVED at every level while the height shrinks in
# absolute terms. Snap displacement scales with the LONG edge, so a few-mm
# move was several cell-heights and folded the cell inside out.
#
# The fix derives dz from dx so the background is near-cubic; free-surface
# thinness now comes from `refineMesh` in z ONLY, run AFTER snappy, which
# never hands hexRef8 an anisotropic cell to snap. Measured after the fix:
# (2,3)/(3,4)/(4,5) all give 0 zero-volume and 0 wrongly-oriented faces, and
# layer coverage rose from 32% to 75%.
def test_background_cell_is_near_isotropic(tmp_path):
    """EVERY scale in the family, not just scale 1.

    This originally checked scale 1.0 only, and the coarse end broke exactly
    where it was not looking: a floor of 2 on the z-count stopped dz scaling
    with dx, so at scale 0.5 the cell was 1213 x 1213 x 328 mm = 3.7:1 and the
    grid meshed with 128 wrongly-oriented faces and skewness 57 (the fine grid,
    same geometry, gets 5 and 9.6). A GCI family is only a family if every
    member is built the same way.
    """
    from navalai.cfd import case as C

    lwl, speed = 7.2786, 2.196
    for scale in (0.5, 2 ** -0.5, 1.0, 2 ** 0.5, 2.0):
        out = tmp_path / f"iso{scale:.3f}"
        C.write_resistance_case_from_stl(
            _kcs_or_skip(), lwl, speed, out,
            end_time=1.0, scale=scale, np_procs=2,
            allow_collapsed_bands=True)
        dx, dy, dz = _background_cell(out)
        aspect = max(dx, dy, dz) / min(dx, dy, dz)
        assert aspect <= 3.0, (f"scale {scale}: "
            f"cell {dx*1e3:.0f} x {dy*1e3:.0f} x {dz*1e3:.0f} mm = "
            f"{aspect:.1f}:1. snappy refines isotropically, so this ratio "
            f"survives to every level and folds cells during snapping.")


def test_refine_mesh_uses_a_valid_direction():
    # The enum is (tan1 tan2 normal). `tan3` looks obvious and is FATAL:
    # "tan3 is not in enumeration". It cost a full 75 s solve on an unrefined
    # free surface, because run-case.sh swallowed the error (see next test).
    from navalai.cfd import case as C
    directions = re.search(r"directions\s*\(([^)]*)\)", C.REFINE_MESH).group(1)
    for d in directions.split():
        assert d in {"tan1", "tan2", "normal"}, f"invalid refineMesh direction {d!r}"


def test_refine_mesh_failure_is_fatal():
    # A refinement the case ASKED for that silently did not happen is a WRONG
    # mesh, not a degraded one — it must not reach the solver.
    script = (Path(__file__).parents[1] / "navalai/cfd/run-case.sh").read_text()
    loop = script[script.index("refineMesh -dict"):][:200]
    assert "exit 1" in loop, "a failed refineMesh round must abort the run"


def test_stale_octree_levels_are_dropped_before_decompose():
    # snappy leaves cellLevel/pointLevel in 0/ as well as constant/polyMesh;
    # refineMesh -overwrite updates only the latter, so decomposePar died with
    # "Size 230265 is not equal to the expected length 920407".
    script = (Path(__file__).parents[1] / "navalai/cfd/run-case.sh").read_text()
    assert "0/cellLevel" in script and "0/pointLevel" in script
    assert script.index("0/cellLevel") < script.index("decomposePar -force")


def test_mesh_is_froude_similar_at_any_hull_size(tmp_path):
    """The SAME generator must serve a 7 m tank model and a 230 m ship.

    KCS is calibrated at MODEL scale because that is where the tank data is
    (Lpp 7.2786 m, Re 1.26e7), while our own craft are meshed at 1:1. Those are
    only the same validated code path if the mesh is geometrically similar at
    constant Froude number — otherwise the benchmark certifies a mesh nobody
    builds for a real boat.

    MEASURED across a 31.6x size range at Fn 0.26: identical cell counts,
    identical dx/L, identical cells-per-wavelength.

    The near-wall spacing must NOT follow that similarity: y+ is a Reynolds
    phenomenon, so t1/L falls 124x over the same range. A first layer that
    scaled geometrically would be silently wrong at every scale but one.
    """
    import math

    from navalai.cfd import case as C

    stl, ref = _kcs_or_skip(), []
    for k in (1.0, 4.0, 31.6):
        lwl, speed = 7.2786 * k, 2.196 * math.sqrt(k)   # constant Froude
        out = tmp_path / f"k{k}"
        meta = C.write_resistance_case_from_stl(
            stl, lwl, speed, out, end_time=1.0, scale=1.0,
            np_procs=2, symmetric=True)
        dx, dy, dz = _background_cell(out)
        ref.append({
            "cells": meta["bg_cells"],
            "dx_over_L": dx / lwl, "dz_over_L": dz / lwl,
            "cells_per_wavelength": meta["cells_per_wavelength"],
            "t1_over_L": C.first_layer_thickness(
                speed, lwl, C._TARGET_YPLUS) / lwl,
        })

    first = ref[0]
    for r in ref[1:]:
        assert r["cells"] == first["cells"], (r, first)
        assert r["dx_over_L"] == pytest.approx(first["dx_over_L"], rel=1e-9)
        assert r["dz_over_L"] == pytest.approx(first["dz_over_L"], rel=1e-9)
        assert r["cells_per_wavelength"] == pytest.approx(
            first["cells_per_wavelength"], rel=1e-6)

    # ... and the wall spacing follows Reynolds, so it must SHRINK relative to
    # the hull as the hull grows.
    assert ref[-1]["t1_over_L"] < ref[0]["t1_over_L"] / 50


# ---------------------------------------------------------------------------
# Free sinkage and trim (2026-08-05). KCS Case 2.1 is towed FREE to sink and
# trim; solving it fixed answers a different question than the tank measured,
# and is a known part of the C_T error. These check the parts that can be
# silently wrong without the solve ever complaining.
def test_symmetric_case_carries_half_the_mass(tmp_path):
    """The halving must live in the generator, not in the caller's head.

    A symmetric case meshes half the hull and therefore feels half the
    hydrodynamic force. If it carries the FULL mass it accelerates at half the
    right rate and settles at the wrong sinkage. We already shipped a bug that
    was exactly 2x wrong for the mirror-image reason (forces on a half model),
    so this is not hypothetical.
    """
    from navalai.cfd.case import sixdof_properties

    kw = dict(mass_kg=1000.0, cog=(3.0, 0.0, -0.1), k_roll=0.4, k_pitch=1.8,
              k_yaw=1.8, lwl=7.2786, awp_m2=5.9)
    full = sixdof_properties(symmetric=False, **kw)
    half = sixdof_properties(symmetric=True, **kw)
    assert half["mass"] == pytest.approx(0.5 * full["mass"])
    for i in ("ixx", "iyy", "izz"):
        assert half[i] == pytest.approx(0.5 * full[i]), i
    # the centre of mass does NOT move: the half is a mirror of the whole
    assert half["cog_x"] == full["cog_x"] and half["cog_z"] == full["cog_z"]


def test_mass_and_lcg_come_from_the_geometry(tmp_path):
    """Not from a published percentage — the two can disagree.

    The KCS STL spans 0..7.7165 m against Lpp 7.2786 (bulb and rudder reach
    past the perpendiculars), so "LCB -1.48% Lpp from midship" cannot even be
    located in this file's coordinates. The hull knows where its own centre of
    buoyancy is; ask it, and let mass = rho * volume so the model floats at its
    own displacement rather than at an asserted one.
    """
    import benchmarks.kcs as KCS
    from navalai.cfd.case import motion_from_geometry
    from navalai.cfd.post import stl_submerged_properties

    stl = _kcs_or_skip()
    props = stl_submerged_properties(stl, 0.0)
    published = KCS.GEOMETRY_CHECK["displacement_m3"]
    assert props["volume_m3"] == pytest.approx(published, rel=0.01), (
        f"submerged volume {props['volume_m3']:.4f} m^3 vs published "
        f"{published:.4f} — geometry pipeline drifted")
    # a symmetric hull must have TCB on the centreline; this catches a mirror
    # or a unit error that displacement alone would not
    assert abs(props["tcb"]) < 1e-3, props["tcb"]

    m = motion_from_geometry(stl, KCS.LPP, symmetric=True, kg_above_keel=0.2303)
    assert m["cog_x"] == pytest.approx(props["lcb"], rel=1e-9)
    assert m["cog_y"] == 0.0
    assert m["mass"] == pytest.approx(0.5 * 998.8 * props["volume_m3"], rel=1e-9)


def test_motion_dict_releases_heave_and_pitch_only(tmp_path):
    """Surge, sway, roll and yaw must stay constrained.

    A hull free in surge accelerates away down the tank; free in roll it falls
    over at the symmetry plane. Sinkage and trim are the two the tank measured.
    """
    import benchmarks.kcs as KCS
    from navalai.cfd import case as C

    stl = _kcs_or_skip()
    motion = C.motion_from_geometry(stl, KCS.LPP, symmetric=True,
                                    kg_above_keel=0.2303)
    out = tmp_path / "free"
    C.write_resistance_case_from_stl(stl, KCS.LPP, KCS.DESIGN_SPEED, out,
                                     end_time=1.0, scale=0.5, np_procs=2,
                                     symmetric=True, free_motion=motion, allow_collapsed_bands=True)

    d = (out / "constant" / "dynamicMeshDict").read_text()
    assert "sixDoFRigidBodyMotion" in d
    assert "line; direction (0 0 1)" in d.replace("\n", " "), "heave not released"
    assert "axis; axis (0 1 0)" in d.replace("\n", " "), "pitch not released"
    # dampers act on velocity, so they vanish at equilibrium and cannot bias
    # the converged answer — but they must be present to survive the release
    assert "linearDamper" in d and "sphericalAngularDamper" in d

    pd = (out / "0.orig" / "pointDisplacement").read_text()
    assert "hull" in pd and "calculated" in pd
    # side1 is a `symmetry` patch here and is handled by setConstraintTypes;
    # declaring it again is a duplicate-entry error at run time
    assert "setConstraintTypes" in pd
    assert "side1" not in pd, "symmetry patch must not be declared explicitly"

    # a moving mesh needs correctPhi or the inherited fluxes violate continuity
    assert "correctPhi yes" in (out / "system" / "fvSolution").read_text()


def test_fixed_case_writes_no_motion_dict(tmp_path):
    from navalai.cfd import case as C
    out = tmp_path / "fixed"
    C.write_resistance_case_from_stl(_kcs_or_skip(), 7.2786, 2.196, out,
                                     end_time=1.0, scale=0.5, np_procs=2,
                                     symmetric=True, allow_collapsed_bands=True)
    assert not (out / "constant" / "dynamicMeshDict").exists()
    assert not (out / "0.orig" / "pointDisplacement").exists()
