"""Gate 2R — the defects a reference KCS case and an exact triplet exposed.

Motivating incidents, all measured 2026-08-05/06 against the Wolf Dynamics KCS
and KCS_Dynamic reference cases and against analytically exact Richardson
triplets. Each test below names the number that was wrong.

None of these needs OpenFOAM: they check what the generator WRITES and what the
post-processor COMPUTES, which is where every one of the defects lived.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from navalai import grammar
from navalai.cfd import case as C
from navalai.cfd.post import gci, stl_submerged_properties, stl_waterplane_properties
from navalai.geometry import Hull


def _mid_hull() -> Hull:
    return Hull(grammar.vector({n: 0.5 * (lo + hi)
                                for n, _u, lo, hi, _d in grammar.PARAMS}))


def _write_box_stl(path: Path, lx=4.0, ly=2.0, z0=-3.0, z1=2.0) -> None:
    """A closed box, outward normals, so every integral has a closed form.

    ASCII, because `post._read_stl_tris` is an ASCII reader — writing binary
    here produced a UnicodeDecodeError that a `except ValueError` upstream
    then swallowed, which is its own small lesson about broad excepts.
    """
    x0, x1, y0, y1 = 0.0, lx, -ly / 2, ly / 2
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (1, 2, 6, 5), (0, 4, 7, 3)]
    tris = []
    for a, b, c, d in quads:
        tris += [(v[a], v[b], v[c]), (v[a], v[c], v[d])]
    out = ["solid box"]
    for t in tris:
        n = np.cross(np.subtract(t[1], t[0]), np.subtract(t[2], t[0]))
        n = n / (np.linalg.norm(n) or 1.0)
        out.append(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        out.append("    outer loop")
        for p in t:
            out.append(f"      vertex {p[0]:.6e} {p[1]:.6e} {p[2]:.6e}")
        out += ["    endloop", "  endfacet"]
    out.append("endsolid box")
    path.write_text("\n".join(out) + "\n")


# --------------------------------------------------------------------------
# The 2x that disabled the cross-check built to catch a 2x
# --------------------------------------------------------------------------

def test_forceCoeffs_Aref_is_the_area_the_patch_actually_covers(tmp_path):
    """MEASURED on runs/kcs_sym at t=13.7063: forceCoeffs reported Cd 2.2158e-3
    while force.dat gives 4.4316e-3 — EXACTLY 2x — because Aref was the
    full-hull wetted area while the patch is half the hull on a symmetric case.
    gate2m.py was right; forceCoeffs was silently wrong on every symmetric run,
    which is precisely the failure the independent coefficient exists to catch.
    """
    hull = _mid_hull()
    full = tmp_path / "full"
    half = tmp_path / "half"
    C.write_resistance_case(hull, 2.0, full, end_time=1.0, np_procs=1,
                            symmetric=False)
    C.write_resistance_case(hull, 2.0, half, end_time=1.0, np_procs=1,
                            symmetric=True)

    def _aref(d: Path) -> float:
        for line in (d / "system" / "controlDict").read_text().splitlines():
            if "Aref" in line:
                return float(line.split("Aref")[1].split(";")[0])
        raise AssertionError("no Aref in controlDict")

    # rel 1e-6, because controlDict writes Aref with %.6f — the tolerance is
    # the dict's own precision, not slack in the assertion.
    assert _aref(half) == pytest.approx(0.5 * _aref(full), rel=1e-6)


# --------------------------------------------------------------------------
# The boundary condition that killed runs/kcs_free on timestep 1
# --------------------------------------------------------------------------

def test_a_moving_hull_gets_movingWallVelocity_and_a_fixed_one_does_not(tmp_path):
    """noSlip pins the face velocity in the ABSOLUTE frame and omits the
    mesh-motion flux, so a sinking hull has a spurious mass flux through its
    own surface. runs/kcs_free died at t=0.0012 with the alpha solver at its
    1000-iteration ceiling and alpha in [-81402, +39618]. The reference uses
    movingWallVelocity on the hull; we now do too, but only when it moves.
    """
    hull = _mid_hull()
    fixed, free = tmp_path / "fixed", tmp_path / "free"
    C.write_resistance_case(hull, 2.0, fixed, end_time=1.0, np_procs=1)
    motion = C.sixdof_properties(1000.0, (5.0, 0.0, -0.2), 1.0, 2.5, 2.5,
                                 lwl=10.0, awp_m2=20.0, symmetric=False)
    C.write_resistance_case(hull, 2.0, free, end_time=1.0, np_procs=1,
                            free_motion=motion)

    assert "noSlip" in (fixed / "0.orig" / "U").read_text()
    assert "movingWallVelocity" not in (fixed / "0.orig" / "U").read_text()
    free_u = (free / "0.orig" / "U").read_text()
    assert "movingWallVelocity" in free_u
    assert "noSlip" not in free_u


def test_surface_tension_is_zero_and_the_fluid_constants_have_one_home(tmp_path):
    # sigma*kappa*grad(alpha) on ~15:1 interface cells sitting on refineMesh
    # hanging nodes is a spurious-current source and nothing else at model
    # scale. The reference uses 0.0. rho was ALSO declared five times in
    # case.py before this; the template now formats the constants in.
    hull = _mid_hull()
    d = tmp_path / "c"
    C.write_resistance_case(hull, 2.0, d, end_time=1.0, np_procs=1)
    tp = (d / "constant" / "transportProperties").read_text()
    assert "sigma 0;" in tp or "sigma 0.0;" in tp
    assert f"{C._RHO_WATER:.6g}" in tp and f"{C._NU_WATER:.6g}" in tp


def test_inlet_eddy_viscosity_is_a_boundary_layer_scale_not_a_ship_scale(tmp_path):
    """MEASURED against the reference (k 7.233e-4, omega 60.78 => nu_t/nu 11.9):
    ours was 1968 — 165x — because the turbulent length scale was 1% of Lwl
    (72.8 mm) rather than 1% of the boundary layer (~0.8 mm), and omega 1.35/s
    barely decayed before the hull. Excess freestream nu_t thickens the
    boundary layer and RAISES skin friction, the direction our C_T error
    already points.
    """
    hull = _mid_hull()
    d = tmp_path / "c"
    C.write_resistance_case(hull, 2.0, d, end_time=1.0, np_procs=1)

    def _internal(field: str) -> float:
        for line in (d / "0.orig" / field).read_text().splitlines():
            if line.startswith("internalField"):
                return float(line.split()[-1].rstrip(";"))
        raise AssertionError(field)

    k, w = _internal("k"), _internal("omega")
    nut_over_nu = (k / w) / C._NU_WATER
    assert nut_over_nu < 100.0, (
        f"inlet nu_t/nu = {nut_over_nu:.0f}; the reference achieves ~12 and "
        f"ours was 1968")


# --------------------------------------------------------------------------
# GCI: uncertainty must never be understated, whatever the observed order
# --------------------------------------------------------------------------

@pytest.mark.parametrize("p_true", [0.1, 0.3, 0.5, 0.99, 2.0, 3.0, 6.0])
def test_gci_is_never_anti_conservative(p_true):
    """The old clamp raised a below-first-order p UP to 0.5, which SHRINKS the
    reported band because GCI ~ 1/(r^p - 1). MEASURED on an exact triplet at
    r=sqrt(2), p_true=0.1: analytic 6.392%, reported 1.191% — understated
    5.37x, exactly the direction that lets a barely-converging triplet claim
    the <=2.5% bar.
    """
    r = math.sqrt(2.0)
    f_exact, coeff = 3.711e-3, 2.0e-4
    hf = 1.0
    ff = f_exact + coeff * hf ** p_true
    fm = f_exact + coeff * (hf * r) ** p_true
    fc = f_exact + coeff * (hf * r * r) ** p_true
    rep = gci(fc, fm, ff, r)
    analytic = 100.0 * 1.25 * abs(fm - ff) / ff / (r ** p_true - 1.0)
    assert rep.gci_fine_pct >= analytic * 0.999, (
        f"GCI {rep.gci_fine_pct:.3f}% understates the Fs=1.25 value "
        f"{analytic:.3f}% at p={p_true}")
    if p_true < 1.0:
        assert "Fs=3.0" in rep.method


# --------------------------------------------------------------------------
# Waterplane properties, and the pitch stiffness that was 3.96x too high
# --------------------------------------------------------------------------

def test_waterplane_properties_are_exact_on_a_box(tmp_path):
    stl = tmp_path / "box.stl"
    _write_box_stl(stl, lx=4.0, ly=2.0, z0=-3.0, z1=2.0)
    wp = stl_waterplane_properties(stl, 0.0)
    assert wp["awp_m2"] == pytest.approx(8.0, rel=1e-9)      # 4 x 2
    assert wp["lcf"] == pytest.approx(2.0, rel=1e-9)         # midships
    assert wp["i_l_m4"] == pytest.approx(2.0 * 4.0 ** 3 / 12.0, rel=1e-9)
    sub = stl_submerged_properties(stl, 0.0)
    assert sub["volume_m3"] == pytest.approx(24.0, rel=1e-9)


def test_pitch_stiffness_uses_the_real_second_moment():
    """Awp*(L/2)^2 treats the waterplane as two point areas at the ends. On
    KCS it gives 771030 N.m/rad against a true rho*g*I_L of 194539 — 3.96x too
    stiff — which put the pitch damper at zeta 0.597 instead of the intended
    0.30 and roughly doubled settling time on a multi-day run.
    """
    lwl, awp = 10.0, 20.0
    i_l_true = 20.0 * 10.0 ** 3 / 12.0 / 10.0   # a plausible slender I_L
    common = dict(mass_kg=1000.0, cog=(5.0, 0.0, -0.2), k_roll=1.0,
                  k_pitch=2.5, k_yaw=2.5, lwl=lwl, awp_m2=awp,
                  symmetric=False)
    approx = C.sixdof_properties(**common)
    exact = C.sixdof_properties(**common, i_l_m4=i_l_true)
    # the approximation's implied I_L is awp*(L/2)^2 = 500 vs 166.7 here
    assert approx["c_ang"] > exact["c_ang"]
    ratio = (awp * (0.5 * lwl) ** 2) / i_l_true
    assert approx["c_ang"] / exact["c_ang"] == pytest.approx(
        math.sqrt(ratio), rel=1e-6)


def test_symmetric_halving_still_holds_for_mass_and_inertia():
    # Independently confirmed by the reference, which halves 1649 kg to 824.5
    # for its own half-domain. Regression guard: this is load-bearing.
    kw = dict(mass_kg=1000.0, cog=(5.0, 0.0, -0.2), k_roll=1.0, k_pitch=2.5,
              k_yaw=2.5, lwl=10.0, awp_m2=20.0, i_l_m4=166.7)
    full = C.sixdof_properties(**kw, symmetric=False)
    half = C.sixdof_properties(**kw, symmetric=True)
    assert half["mass"] == pytest.approx(0.5 * full["mass"])
    assert half["iyy"] == pytest.approx(0.5 * full["iyy"])
    # omega_n must be INVARIANT: halving mass and waterplane together leaves
    # the natural frequency alone, which is why the halving is safe.
    assert half["c_lin"] == pytest.approx(0.5 * full["c_lin"], rel=1e-9)


def test_missing_kg_warns_rather_than_quietly_answering_another_ship(tmp_path):
    # MEASURED on KCS: defaulting VCG to VCB gives KG-above-keel 0.187 m
    # against the published 0.2303 — 19% low — and KG is the lever that sets
    # trim. It is legitimate as a neutral default; it is not legitimate silent.
    stl = tmp_path / "box.stl"
    _write_box_stl(stl)
    with pytest.warns(UserWarning, match="VCB"):
        C.motion_from_geometry(stl, lwl=4.0, symmetric=False)


# ==========================================================================
# THE 2026-08-06 ADVERSARIAL RE-AUDIT — ten defects, each with its
# reproduction. Same rule as above: every number in a comment was produced by
# running the code as it stood. The common shape: a second copy of something
# that already had one home, and the copy was the careless one.
# ==========================================================================

import importlib.util
import json
import re

_ROOT = Path(__file__).parents[1]


def _gate2m():
    """Import scripts/gate2m.py as a module (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location(
        "gate2m_under_test", _ROOT / "scripts" / "gate2m.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _kcs_box_stl(path: Path):
    """A closed box hull at KCS proportions — the layer checks are speed- and
    length-sensitive, so the stand-in geometry has to be the right size."""
    _write_box_stl(path, lx=7.2786, ly=1.0, z0=-0.35, z1=0.15)
    return path


def _info(case: Path) -> dict:
    out = {}
    for line in (case / "case.info").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith(("#", "NOTE", "run:",
                                                         "Gate")):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# --------------------------------------------------------------------------
# FIX 1 — the second GCI, which was the one that printed PASS/FAIL
# --------------------------------------------------------------------------

def test_gate2m_has_no_gci_of_its_own():
    """scripts/gate2m.py defined `gci()` beside navalai.cfd.post.gci, and the
    copy was missing every safety rule the library version carries. It is
    deleted; the gate delegates."""
    src = (_ROOT / "scripts" / "gate2m.py").read_text()
    assert "\ndef gci(" not in src, (
        "gate2m.py has re-grown its own GCI. There is one Roache GCI in this "
        "repository and it lives in navalai/cfd/post.py.")
    assert "from navalai.cfd import post" in src


def test_a_diverging_triplet_can_never_read_as_converged():
    """THE ONE THAT MATTERED. MEASURED on fine 3.700e-3, medium 4.100e-3,
    coarse 4.300e-3 — monotone but DIVERGING under refinement — the old local
    gci() returned p = -2.000 and gci_fine_pct = **-27.027%**, and the gate's
    test was the bare `gci <= 5.0`, which is TRUE of -27.027. Gate 2M printed
    `VERDICT: PASS` and exited 0 on a family that was getting worse.

    After: 1855.435% via post.gci, and `gci_is_converged` refuses a negative or
    non-finite uncertainty outright.
    """
    g = _gate2m()
    rep = g.gci_report(3.700e-3, 4.100e-3, 4.300e-3, 2.0 ** 0.5)
    assert rep["gci_fine_pct"] == pytest.approx(1855.435, rel=1e-4)
    assert not g.gci_is_converged(rep["gci_fine_pct"])
    # the exact values that used to slip through, tested as values
    for bad in (-27.027, -1e-12, float("nan"), float("inf")):
        assert not g.gci_is_converged(bad), f"{bad} must never read as converged"
    assert g.gci_is_converged(4.9) and not g.gci_is_converged(5.1)


def test_a_sub_first_order_triplet_is_not_flattered():
    """The `p < 1 -> Fs = 3.0` fallback was absent from the local copy.
    MEASURED on an analytically exact triplet with p_true = 0.3 at r = sqrt(2):
    gate2m reported 3.280% where post.gci reports 7.872% — a 2.4x
    UNDERSTATEMENT, in the direction that lets a sub-first-order family clear
    the 5% bar. 3.280 passes; 7.872 does not, and that is the point."""
    g = _gate2m()
    r, f_ex, e = 2.0 ** 0.5, 3.711e-3, 1e-4
    trip = [f_ex + e * r ** (0.3 * k) for k in (0, 1, 2)]
    rep = g.gci_report(*trip, r)
    assert rep["p"] == pytest.approx(0.3, abs=1e-6)
    assert rep["gci_fine_pct"] == pytest.approx(7.8719, rel=1e-3)
    assert not g.gci_is_converged(rep["gci_fine_pct"])
    assert "Fs=3.0" in rep["method"]      # the reader must see WHICH rule fired


def test_richardson_extrapolates_toward_the_limit_not_away_from_it():
    """SIGN. The local copy computed `f_ext = f1 + e12/(r**p - 1)` with
    `e12 = f2 - f1`. On an exact p=2 triplet built around f_exact = 3.711e-3 it
    returned 3.911e-3 — off by +2 x the fine grid's own error, i.e. it moved
    away from the limit by exactly what it should have moved toward it."""
    g = _gate2m()
    r, f_ex, e = 2.0 ** 0.5, 3.711e-3, 1e-4
    trip = [f_ex + e * r ** (2.0 * k) for k in (0, 1, 2)]
    rep = g.gci_report(*trip, r)
    assert rep["f_extrapolated"] == pytest.approx(f_ex, rel=1e-9)
    assert rep["f_extrapolated"] < trip[0], "must extrapolate PAST the fine grid"
    # and it agrees with the library, because it IS the library
    assert rep["gci_fine_pct"] == pytest.approx(
        gci(trip[2], trip[1], trip[0], r).gci_fine_pct)


# --------------------------------------------------------------------------
# FIX 2 — "the wall model is held fixed across the triplet" was not true
# --------------------------------------------------------------------------

def test_a_generated_triplet_freezes_the_whole_wall_model(tmp_path):
    """case.info has always claimed "first-layer thickness is held constant
    across the GCI triplet, so the GCI bounds OUTER-flow discretisation, not
    the wall model". The THICKNESS was constant; the LAYER COUNT was not,
    because n_layers_to_bridge reads the hull cell, which scales with nx.
    MEASURED on a scale 1 / sqrt2 / 2 symmetric KCS triplet: n_layers 7 / 6 / 5,
    prism stack 12.9*t1 -> 9.9*t1 -> 7.4*t1. The observed order p was absorbing
    two refinements at once — the one thing the note says it does not."""
    stl = _kcs_box_stl(tmp_path / "hull.stl")
    # unpinned: the defect, still reachable, and asserted so the reproduction
    # does not quietly disappear
    free = [C.layer_spec(7.2786, 2.196, s)["n_layers"]
            for s in (1.0, 2 ** 0.5, 2.0)]
    assert len(set(free)) > 1, (
        "n_layers no longer varies with scale; if that is now true by "
        "construction this test's premise has changed, not been fixed")

    pinned = C.layer_spec(7.2786, 2.196, 2.0)["n_layers"]   # finest is binding
    infos = []
    for name, s in (("coarse", 1.0), ("medium", 2 ** 0.5), ("fine", 2.0)):
        C.write_resistance_case_from_stl(
            stl, 7.2786, 2.196, tmp_path / name, end_time=5.0, scale=s,
            np_procs=2, symmetric=True, n_layers=pinned)
        infos.append(_info(tmp_path / name))
    assert len({i["n_layers"] for i in infos}) == 1, [i["n_layers"] for i in infos]
    assert len({i["first_layer_m"] for i in infos}) == 1
    assert len({i["cells_bg"] for i in infos}) == 3, "and it is still a family"


def test_the_pinned_stack_must_fit_the_finest_grids_cell(tmp_path):
    """FORCED BY MEASUREMENT, not chosen. A fixed first layer and a fixed count
    give a stack of fixed HEIGHT while the hull cell halves under refinement.
    MEASURED on KCS at base 57: pinning the COARSE grid's 7 layers gives a
    34.2 mm stack against the fine grid's 17.96 mm hull cell — ratio 1.90 —
    and the generator refuses above 1.2 because that configuration killed
    interFoam with deltaT collapsing to 1e-23. So the ANCHOR IS THE FINEST
    GRID, and make_case.py takes max(scales), not scale 1.0."""
    stl = _kcs_box_stl(tmp_path / "hull.stl")
    coarse_n = C.layer_spec(7.2786, 2.196, 1.0)["n_layers"]
    with pytest.raises(ValueError, match="does not FIT"):
        C.write_resistance_case_from_stl(
            stl, 7.2786, 2.196, tmp_path / "fine", end_time=5.0, scale=2.0,
            np_procs=2, symmetric=True, n_layers=coarse_n)
    src = (_ROOT / "scripts" / "make_case.py").read_text()
    assert "max(s for _n, s in ordered)" in src, (
        "the triplet must pin n_layers at the FINEST scale; anchoring at 1.0 "
        "makes the fine grid unbuildable")


# --------------------------------------------------------------------------
# FIX 4 — a half domain that was not half of anything
# --------------------------------------------------------------------------

def _bg_counts(scale: float, symmetric: bool) -> tuple[int, int, int]:
    nx = max(int(round(C._NX_BASE * scale)), 20)
    ny_half = max(int(round(nx * C._NY_PER_NX_HALF)), 6)
    nz = max(int(round(nx * C._NZ_PER_NX)), 4)
    return nx, ny_half if symmetric else 2 * ny_half, nz


@pytest.mark.parametrize("symmetric", [True, False])
def test_the_refinement_family_is_uniform_in_both_domain_modes(symmetric):
    """MEASURED before: `ny = round((1.5 if symmetric else 3.0)*lwl/dx_bg)` is
    a second, independent rounding of a HALF-SIZE number in the symmetric case,
    so the symmetric triplet's two refinement steps disagreed by 0.85% against
    the full domain's 0.47% — and CLAUDE.md recorded 0.47% while recommending
    --symmetric. ny also came out ODD in the full domain (36/51/72), so the
    "half" domain was not half of it but a third mesh.

    AFTER, at base 57 with ny = nx/3 (nx is a multiple of 3 at every member of
    the family, so the division is exact): 0.03% in BOTH modes.
    """
    cells = [math.prod(_bg_counts(s, symmetric))
             for s in (1.0, 2 ** 0.5, 2.0)]
    r12, r23 = (cells[1] / cells[0]) ** (1 / 3), (cells[2] / cells[1]) ** (1 / 3)
    spread = abs(r23 - r12) / max(r12, r23)
    assert spread < 1e-3, f"r12={r12:.4f} r23={r23:.4f} spread={100*spread:.2f}%"
    assert r12 == pytest.approx(2 ** 0.5, rel=0.01)


def test_a_symmetric_case_is_exactly_half_of_the_full_one():
    """It was not. At scale sqrt(2) the full domain took ny = 51 (odd) while
    the symmetric one took 25 — 38000 cells against half of 77520 = 38760. The
    two modes were different discretisations wearing the same scale number, so
    a figure measured on one did not describe the other."""
    for s in (1.0, 2 ** 0.5, 2.0, 0.5):
        half, full = _bg_counts(s, True), _bg_counts(s, False)
        assert full[1] == 2 * half[1]
        assert math.prod(full) == 2 * math.prod(half)


def test_the_tank_half_width_is_declared_once():
    """`y_half = 1.5 * lwl` was computed and NEVER READ, while 1.5 appeared
    again in the blockMesh y0/y1 entries and again inside the ny expression —
    and it is the third that decides the refinement family."""
    src = (_ROOT / "navalai" / "cfd" / "case.py").read_text()
    assert "y_half = 1.5 * lwl" not in src
    assert src.count("1.5 * lwl") == 0, "the half width is _DOMAIN_HALF_WIDTH_L"


# --------------------------------------------------------------------------
# FIX 6 — a case that could not be regenerated into what was asked for
# --------------------------------------------------------------------------

def test_regenerating_a_free_case_as_fixed_leaves_nothing_moving(tmp_path):
    """MEASURED: `_write_case_dicts` wrote dynamicMeshDict and
    pointDisplacement when `free_motion` and NEVER removed them, so
    regenerating a case FIXED on top of a previously FREE one left a case that
    still sinks and trims while `free_motion=False` sits in its own case.info.
    The existing test could not see it: it generates into a fresh tmp_path,
    which is the one situation where the stale file cannot exist."""
    stl = _kcs_box_stl(tmp_path / "hull.stl")
    out = tmp_path / "case"
    motion = {"mass": 1000.0, "cog_x": 3.0, "cog_y": 0.0, "cog_z": -0.1,
              "ixx": 100.0, "iyy": 3000.0, "izz": 3000.0,
              "inner": 0.4, "outer": 1.2, "c_lin": 500.0, "c_ang": 5000.0}
    C.write_resistance_case_from_stl(stl, 7.2786, 2.196, out, 5.0, 1.0, 2,
                                     symmetric=True, free_motion=motion,
                                     lts=False)
    assert (out / "constant" / "dynamicMeshDict").exists()
    assert (out / "0.orig" / "pointDisplacement").exists()

    C.write_resistance_case_from_stl(stl, 7.2786, 2.196, out, 5.0, 1.0, 2,
                                     symmetric=True, free_motion=None,
                                     lts=False)
    assert not (out / "constant" / "dynamicMeshDict").exists(), (
        "interFoam reads dynamicMeshDict if it is there — this case still moves")
    assert not (out / "0.orig" / "pointDisplacement").exists()
    assert not (out / "0" / "pointDisplacement").exists()


def test_correctphi_and_boxtoface_belong_to_moving_cases_only(tmp_path):
    """Both were written UNCONDITIONALLY, so any regenerated FIXED case was no
    longer the configuration that produced the recorded Gate 2M numbers.
    correctPhi adds a pcorr solve at startup and flips the order in which
    alpha's and U's boundary conditions are evaluated; the setFields boxToFace
    entry exists only because that flipped order divides by the outlet's water
    area. The comments in the file said as much, and the code ignored them."""
    stl = _kcs_box_stl(tmp_path / "hull.stl")
    motion = {"mass": 1000.0, "cog_x": 3.0, "cog_y": 0.0, "cog_z": -0.1,
              "ixx": 100.0, "iyy": 3000.0, "izz": 3000.0,
              "inner": 0.4, "outer": 1.2, "c_lin": 500.0, "c_ang": 5000.0}
    for mo, want in ((motion, True), (None, False)):
        out = tmp_path / f"case_{want}"
        C.write_resistance_case_from_stl(stl, 7.2786, 2.196, out, 5.0, 1.0, 2,
                                         symmetric=True, free_motion=mo,
                                         lts=False)
        fv = (out / "system" / "fvSolution").read_text()
        sf = (out / "system" / "setFieldsDict").read_text()
        assert ("correctPhi yes;" in fv) is want
        assert ("boxToFace" in sf) is want
        # the boxToCell that puts water in the tank is NOT conditional
        assert "boxToCell" in sf


# --------------------------------------------------------------------------
# FIX 7 — "FLUID PROPERTIES, ONCE" was false when it was written
# --------------------------------------------------------------------------

def _code_lines(path: Path) -> str:
    """Source with comment lines and docstring prose dropped.

    Same scanner shape as tests/test_limits_single_source.py: the comments
    QUOTE the banned digits on purpose (that is how the incident stays
    readable), so scanning raw text would fail on the explanation.
    """
    out, in_doc = [], False
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc or stripped.startswith("#") or stripped.startswith("//"):
            continue
        out.append(line.split("  #")[0])
    return "\n".join(out)


@pytest.mark.parametrize("literal,home", [
    ("998.8", "_RHO_WATER"),
    ("9.81", "_G"),
    ("1.09e-6", "_NU_WATER"),
])
def test_a_fluid_property_appears_exactly_once_in_case_py(literal, home):
    """The module comment claimed "every template and helper below formats them
    in rather than retyping them". RE-MEASURED 2026-08-06, it was false in
    EIGHT places: rho 998.8 at motion_from_geometry's default and hardcoded in
    BOTH forces function objects; nu 1.09e-6 at first_layer_thickness's
    default; g 9.81 in the GRAVITY template (a plain string, so it could not
    format anything), in the deep-water half-wavelength and in the wavelength
    receipt. A claim of single-sourcing is worse than no claim, because it
    stops the next reader looking. This is the limits.py grep, for fluids."""
    src = _code_lines(_ROOT / "navalai" / "cfd" / "case.py")
    hits = [ln for ln in src.splitlines()
            if re.search(rf"(?<![\d.]){re.escape(literal)}(?![\d])", ln)]
    assert len(hits) == 1, (
        f"{literal} appears {len(hits)} time(s) outside comments; it has one "
        f"home, {home}, and everything else formats it in:\n  "
        + "\n  ".join(h.strip() for h in hits))
    assert home in hits[0], f"the one occurrence must be {home}'s definition"


# --------------------------------------------------------------------------
# FIX 8 — Gate 2M judged any directory against KRISO tank data
# --------------------------------------------------------------------------

def test_gate2m_refuses_a_hull_that_was_never_in_the_kriso_tank(tmp_path, capsys):
    """REPRODUCED: `python scripts/gate2m.py runs/wigley` printed

        Gate 2M — KCS resistance, Fn 0.26, U 2.196 m/s, Lpp 7.2786 m
          wigley ... C_T 5.9010e-03  E%D -59.0

    for a Wigley parabolic hull at Lwl 10.0 m and 2.971 m/s. Every figure on
    that line except C_T belonged to a different ship, and the -59.0 is
    arithmetic without meaning. Identity comes from the STL hash that case.info
    records and data/benchmark_geom/CHECKSUMS.json pins."""
    g = _gate2m()
    (tmp_path / "system").mkdir()
    (tmp_path / "case.info").write_text(
        "speed_ms=2.971\nlwl=10.0\nstl_sha256=deadbeef\n")
    assert g.benchmark_of(tmp_path) is None
    with pytest.raises(SystemExit) as exc:
        g.main.__globals__["sys"].argv = ["gate2m", str(tmp_path)]
        g.main()
    assert "not a KCS case" in str(exc.value)

    kcs_sha = json.loads(
        (_ROOT / "data/benchmark_geom/CHECKSUMS.json").read_text()
    )["kcs.stl"]["sha256"]
    (tmp_path / "case.info").write_text(f"stl_sha256={kcs_sha}\n")
    assert g.benchmark_of(tmp_path) == "kcs"


def test_a_generated_case_says_which_ship_it_is(tmp_path):
    """The receipt the refusal above reads. An unrecognised hull records
    `benchmark=unknown`, which is the honest answer and is not `kcs`."""
    stl = _kcs_box_stl(tmp_path / "hull.stl")
    C.write_resistance_case_from_stl(stl, 7.2786, 2.196, tmp_path / "c",
                                     5.0, 1.0, 2, symmetric=True)
    assert _info(tmp_path / "c")["benchmark"] == "unknown"


# --------------------------------------------------------------------------
# FIX 5 — the runner's guards
# --------------------------------------------------------------------------

def test_the_runner_never_tolerates_a_failed_setfields():
    """`setFields ... || true`. setFields is what puts water in the tank:
    0.orig/alpha.water is uniform 0 and every cell below z=0 is filled by the
    boxToCell entry. If it fails the solve runs to completion in PURE AIR and
    writes a complete, plausible, meaningless force history."""
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    assert "setFields > log.setFields 2>&1 || true" not in src
    assert re.search(r"setFields > log\.setFields 2>&1 \|\| \{", src)


def test_checkmesh_has_a_fatal_bar_calibrated_between_two_measurements():
    """checkMesh ran with `|| true` and the only consequence was a NOTE, so a
    mesh with degenerate cells went straight into a multi-hour solve.

    The bars are not round numbers chosen for comfort:
      zero-volume cells   -> fatal at 1  (every mesh that solved had 0; the
                             ones that died had 72988, 20 and 14)
      wrongly-oriented    -> fatal at 5.  It was 10, INTERPOLATED between the
                             only two points then known (5 solves, 73 dies).
                             MEASURED 2026-08-06 on runs/val_coarse — symmetric
                             KCS, nx 57, n_layers 7, i.e. exactly what
                             make_case.py derives for this hull — the mesh came
                             out with 10 incorrectly-oriented faces, PASSED
                             this guard by one face, and interFoam died at
                             t=0.0072 with deltaT 1.2e-3 -> 2.5e-26, Courant
                             max still 9-12 and alpha.water at 1503.95. The
                             interpolated bar sat on the wrong side of the gap
                             it was interpolating across.
      max skewness        -> fatal at 20, checkMesh's OWN boundary-face limit.
                             MEASURED: 6.32 / 8.68 / 8.93 / 9.64 on meshes that
                             solve (KCS n=3, wigley n=10, KCS n=5, kcs_gci2)
                             against 42.94 on the one that died.
    """
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    assert '_MQ_ZEROVOL" -gt 0' in src, "zero-volume cells must be fatal at 1"
    assert '_MQ_WRONGOR" -gt 5' in src, (
        "the wrongly-oriented bar must be 5: 10 is MEASURED to pass a mesh "
        "that dies at t=0.0072 (runs/val_coarse, n_layers=7)")
    assert '_MQ_SKEWBAD" = "1"' in src, "max skewness needs a fatal bar too"
    assert "--force" in src and 'FORCE" = "1"' in src


def test_the_layer_receipt_reads_the_achieved_table_not_the_spec_columns():
    """snappy prints TWO `hull ...` tables with DIFFERENT columns — the 5-field
    layer SPEC before extrusion and the 6-field ACHIEVED result after it. The
    receipt matched `/^hull +[0-9]/` and kept `tail -1`, so it printed column 4
    of the achieved table under the label of column 4 of the spec table.

    MEASURED on runs/val_coarse: it reported `first 5.68 m` — a first-layer
    thickness of 5.68 METRES on a 7.28 m hull, against the 2.648 mm the case
    asked for. 5.68 is not a thickness at all; it is the achieved MEAN LAYER
    COUNT. This is the same class of defect as the one the surrounding block
    exists to fix (a table whose meaning was assumed rather than read), so the
    tables are told apart by field count, which a new table cannot silently
    re-point.
    """
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    assert "NF==5" in src and "NF==6" in src, (
        "spec and achieved tables must be distinguished by field count")
    assert not re.search(r"/\^hull \+\[0-9\]/ \{print \"requested", src), (
        "the old position-based parse mislabelled the achieved layer count "
        "as a first-layer thickness in metres")
    assert "_mq_record layers_achieved" in src, (
        "the achieved count belongs in case.info, written through the "
        "de-duplicating recorder")


def test_the_runner_reports_how_many_checkmesh_checks_failed():
    """`grep -c 'Failed' log.checkMesh` counts LINES, and checkMesh writes one
    line — "Failed 3 mesh checks." — so a mesh failing three checks was
    announced as "flagged 1 check(s)". MEASURED on runs/val_coarse: 3 failures
    (non-orthogonality, face pyramids, skewness) reported as 1."""
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    assert "grep -c 'Failed' log.checkMesh" not in src
    assert re.search(r"Failed \[0-9\]\+ mesh check", src)


def test_the_campaign_aborts_on_a_divergence_instead_of_re_meshing_it():
    """run_campaign.sh treated EVERY non-zero exit as "interrupted, will
    resume", which is right for this Mac's thermal naps and wrong for a
    divergence. MEASURED on runs/val_coarse: interFoam died at t=0.0072, no
    checkpoint was ever written, and the loop re-meshed and re-died with a
    120 s cool-down between attempts — ~100 minutes of re-running an unsolvable
    mesh, ending in a WARNING phrased as though the machine had napped.

    A nap always leaves a LATER checkpoint than the attempt started from; a
    divergence leaves the same one. So no progress twice in a row is fatal."""
    src = (_ROOT / "scripts" / "run_campaign.sh").read_text()
    assert "STALL" in src, "the campaign needs a no-progress counter"
    assert re.search(r'STALL" -ge 2', src)
    assert "exit 4" in src, "a divergence must be distinguishable from a nap"
    assert src.index("STALL=0") < src.index("for attempt"), (
        "the stall counter must reset per grid, or one grid's crash "
        "condemns the next")


def test_the_concurrency_guard_runs_before_anything_is_destroyed():
    """MEASURED positions in the old file: the guard sat AFTER
    `rm -rf constant/polyMesh processor*`, after the whole mesh build, after
    the resume early-exit (so in the resuming mode — the mode this
    thermal-sleeping machine actually runs in — it never fired at all), and
    BEFORE the MESH_ONLY exit, so the 2-minute mesh sweeps CLAUDE.md
    recommends running alongside a solve were refused and run_campaign.sh
    retried exit 3 up to 20 times. And `pgrep -f "interFoam -parallel"` misses
    the serial path entirely."""
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    guard = src.index("solve_running()")
    for code in ("rm -rf processor*",
                 "rm -rf constant/polyMesh constant/extendedFeatureEdgeMesh",
                 'say "RESUMING from t=$RESUME_FROM',
                 "blockMesh > log.blockMesh"):
        assert guard < src.index(code), f"the guard must precede: {code}"
    assert '[ "${MESH_ONLY:-0}" != "1" ] && solve_running' in src
    assert "pgrep -x interFoam" in src, "serial interFoam must be matched too"
    # a looser `pgrep -f interFoam` would match `tail -f .../log.interFoam`,
    # which CLAUDE.md tells people to run while a solve is in progress
    assert 'pgrep -f "interFoam"' not in src


# --------------------------------------------------------------------------
# FIX 9 — the ledger entry pointed at a directory that no longer exists
# --------------------------------------------------------------------------

def test_the_gate2m_ledger_entry_points_at_something_real():
    """`measured_on: "runs/kcs (the only SETTLED grid in the repository)"` with
    watermark -79.8. RE-CHECKED: runs/kcs DOES NOT EXIST, and the entry's own
    `verify` command returns exit 2 (NO RESULT) while printing a sixth
    circulating figure, -93.0 from an unsettled coarse grid. That is gap J1
    recreated inside the fix for J1, so the watermark is now explicitly NOT a
    number and the deletion is recorded."""
    entry = json.loads((_ROOT / "data/gate-ledger.json").read_text())["Gate 2M"]
    for field in ("measured_on", "verify", "watermark"):
        assert "runs/kcs " not in f"{entry[field]} " or "DELETED" in str(entry[field])
    referenced = re.findall(r"runs/[A-Za-z0-9_]+", str(entry["verify"]))
    for ref in referenced:
        assert (_ROOT / ref).exists(), (
            f"the ledger's verify command names {ref}, which does not exist — "
            f"a verify that cannot run is not a verification")
    assert not isinstance(entry["watermark"], (int, float)), (
        "no settled measurement exists, so there is no watermark to state; "
        "inventing one is the failure this ledger exists to prevent")
    assert "DELETED" in entry["measured_on"]


# --------------------------------------------------------------------------
# FIX 10 — two small numbers that were not what the file said
# --------------------------------------------------------------------------

def test_the_scatter_band_claims_only_the_groups_it_transcribes():
    """The docstring said "13 independent CFD groups" and the table comment
    said "13 groups"; SUBMITTED_CT_FINEST holds SEVEN entries, and the band is
    min/max over exactly those seven. The evidence was attributed to nearly
    twice what anyone can check in the file."""
    import benchmarks.kcs as K
    n = len(K.SUBMITTED_CT_FINEST)
    assert n == 7
    # The docstring is the claim a reader takes away; the comment in the table
    # is allowed to QUOTE the old wording, because that is how the incident
    # stays readable (same rule as tests/test_limits_single_source.py).
    assert "13 independent CFD groups" not in K.__doc__
    assert str(n) in K.__doc__, "the docstring must state the number it has"
    lo, hi = K.scatter_band()
    assert (lo, hi) == (min(K.SUBMITTED_CT_FINEST.values()),
                        max(K.SUBMITTED_CT_FINEST.values()))


def test_the_displacement_check_matches_the_file_it_describes():
    """benchmarks/kcs.py recorded -0.09% (1.6474 m^3) while
    data/benchmark_geom/CHECKSUMS.json recorded -0.267% (1.644484 m^3) from
    re-running stl_submerged_properties on the committed recipe's actual
    output. One measurement, two numbers, and the 0.18% gap was hidden by a
    rel=0.01 comparison. The reproducible one wins."""
    import benchmarks.kcs as K
    acc = json.loads(
        (_ROOT / "data/benchmark_geom/CHECKSUMS.json").read_text()
    )["kcs.stl"]["acceptance"]
    assert K.GEOMETRY_CHECK["measured_submerged_m3"] == acc["measured_m3"]
    assert K.GEOMETRY_CHECK["displacement_error_pct"] == acc["error_pct"]
    err = ((K.GEOMETRY_CHECK["measured_submerged_m3"]
            - K.GEOMETRY_CHECK["displacement_m3"])
           / K.GEOMETRY_CHECK["displacement_m3"] * 100.0)
    assert err == pytest.approx(K.GEOMETRY_CHECK["displacement_error_pct"],
                                abs=0.005)


def test_every_committed_benchmark_geometry_can_be_IDENTIFIED():
    """`benchmark_of_sha` says CHECKSUMS.json 'pins the hash of every benchmark
    geometry'. It pinned exactly one.

    MEASURED 2026-08-06: `gate2m.py runs/wigley` printed "identified as: None"
    — the case's stl_sha256 matches the COMMITTED data/benchmark_geom/wigley.stl
    byte for byte, and the file simply was not in the record. The refusal still
    fired, because None is not "kcs", so the defect was invisible in the
    outcome. It fired because the hull was UNIDENTIFIABLE rather than because
    it was identified as a different ship, and the next benchmark added would
    have inherited the same silence.

    So the claim is enforced: every benchmark STL that is committed must be
    nameable from its bytes alone.
    """
    import hashlib
    from navalai.cfd.case import benchmark_of_sha
    geom = _ROOT / "data" / "benchmark_geom"
    record = json.loads((geom / "CHECKSUMS.json").read_text())
    # Every STL PRESENT must be nameable. kcs.stl is gitignored and so is
    # absent on most machines, which is fine — it is checked where it exists.
    # wigley.stl is committed, so this test always has at least one subject.
    present = sorted(geom.glob("*.stl"))
    assert present, "no benchmark STL found to check"
    for stl in present:
        sha = hashlib.sha256(stl.read_bytes()).hexdigest()
        assert stl.name in record, (
            f"{stl.name} is committed but absent from CHECKSUMS.json, so "
            f"gate2m identifies a case built on it as None")
        assert record[stl.name]["sha256"] == sha, f"{stl.name} sha drifted"
        assert benchmark_of_sha(sha) == stl.stem.lower()


def test_the_wigley_acceptance_value_is_the_closed_form_one():
    """Wigley is ANALYTIC: its displacement is 4LBT/9 exactly, so the record's
    published value must be that expression evaluated, not a transcription.
    This is the one benchmark where the acceptance number cannot drift from a
    document, and pinning it keeps the kcs.stl style (a measured value beside
    a published one) honest for the easy case too."""
    acc = json.loads(
        (_ROOT / "data/benchmark_geom/CHECKSUMS.json").read_text()
    )["wigley.stl"]["acceptance"]
    L, B, T = 10.0, 1.0, 0.625
    assert acc["published_m3"] == pytest.approx(4 * L * B * T / 9, rel=1e-12)
    err = 100.0 * (acc["measured_m3"] - acc["published_m3"]) / acc["published_m3"]
    assert err == pytest.approx(acc["error_pct"], abs=0.002)
    assert abs(err) < acc["tolerance_pct"]


# --------------------------------------------------------------------------
# The mesh-quality guard's FIRST real subject, and what it taught
# --------------------------------------------------------------------------

def _skew_guard_from_the_script() -> tuple[str, float]:
    """The awk program and the skewness bar, READ OUT OF run-case.sh.

    Extracted rather than restated so this test cannot pass against a copy of
    the guard while the shipped one rots — the whole point of rule 3 (a number
    lives in one place), applied to a test.
    """
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    m = re.search(r"_MQ_SKEW=\$\(_mq_num '([^']+)'", src)
    assert m, "could not find the skewness parse in run-case.sh"
    bar = re.search(r"s\+0 > ([0-9.]+)\) \? 1 : 0", src)
    assert bar, "could not find the skewness bar in run-case.sh"
    return m.group(1), float(bar.group(1))


def _run_skew_guard(tmp_path, checkmesh_text: str) -> str:
    """Return the guard's value for a given log.checkMesh, or 'UNPARSED'."""
    import subprocess
    prog, _bar = _skew_guard_from_the_script()
    log = tmp_path / "log.checkMesh"
    log.write_text(checkmesh_text)
    script = (
        '_mq_num() { local v; v=$(awk "$1" log.checkMesh | tail -1); '
        'case "$v" in \'\'|*[!0-9.eE+-]*) echo "UNPARSED";; *) echo "$v";; '
        'esac; }\n_mq_num "$1"\n')
    out = subprocess.run(["bash", "-c", script, "bash", prog],
                         cwd=tmp_path, capture_output=True, text=True)
    return out.stdout.strip()


# The line checkMesh actually wrote for runs/val_coarse, character for
# character — `***` prefix, trailing clause and all.
_VAL_COARSE_SKEW_LINE = (
    " ***Max skewness = 42.9417, 23 highly skew faces detected which may "
    "impair the quality of the results")


def test_the_skewness_guard_refuses_the_mesh_that_actually_died(tmp_path):
    """The guard shipped on 2026-08-06 and runs/val_coarse was the first mesh
    that should have tripped it: symmetric KCS, nx 57, the DERIVED n_layers=7,
    max skewness 42.9417, and interFoam died at t=0.0072 with deltaT 1.2e-3 ->
    2.5e-26 while Courant max stayed 9-12 and alpha.water reached 1503.95.

    The failure this guards against is not the arithmetic — 42.9 > 20 is not
    hard — it is the guard never RECEIVING the number. checkMesh prefixes the
    line with `***` only when it fails, so a parse that reads a fixed field
    index reads a different token depending on whether the mesh is good, and a
    parse that then falls back to `${VAR:-0}` reports the mesh it could not
    measure as perfect. Both halves are asserted here.
    """
    prog, bar = _skew_guard_from_the_script()
    assert bar == 20.0, "checkMesh's own boundary-face skewness limit"
    v = _run_skew_guard(tmp_path, _VAL_COARSE_SKEW_LINE + "\n")
    assert v == "42.9417", f"guard read {v!r} from the line that killed the run"
    assert float(v) > bar, "42.9417 must be refused"

    # ... and the same parse must still read a PASSING line, which carries no
    # `***` prefix and a different trailing token.
    ok = _run_skew_guard(tmp_path, "    Max skewness = 3.21 OK.\n")
    assert ok == "3.21" and float(ok) <= bar

    # runs/val_coarse5 — the same hull at n_layers=5, which MESHES CLEAN.
    good = _run_skew_guard(
        tmp_path, " ***Max skewness = 8.93076, 18 highly skew faces detected\n")
    assert good == "8.93076" and float(good) <= bar


@pytest.mark.parametrize("text,why", [
    ("Checking geometry...\nMesh OK.\n", "no skewness line at all"),
    (" ***Max skewness = nan, 4 highly skew faces\n", "a non-numeric value"),
    ("", "an empty log"),
])
def test_an_unmeasured_metric_is_refused_not_assumed_perfect(tmp_path, text, why):
    """`${_MQ_SKEW:-0}` converts "I could not measure this" into "this is
    perfect", and 0 passes every bar. It is the same failure class as the
    snappy layer table that reported the REQUESTED spec as the achieved one and
    let weeks of solves run on a mesh with no prism layers: in both cases the
    absence of evidence was rendered as evidence of absence.

    A guard with no evidence must refuse. checkMesh's wording is not
    contractual, so this is not hypothetical.
    """
    assert _run_skew_guard(tmp_path, text) == "UNPARSED", why
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    assert 'if [ "$_MQ_SKEW" = "UNPARSED" ]; then\n  _MQ_SKEWBAD=1' in src, (
        "an unparsed skewness must set the fatal flag directly, not fall "
        "through to a numeric comparison against a default")


def test_case_info_receipts_are_rewritten_not_appended():
    """MEASURED on runs/val_coarse: three mesh builds (a MESH_ONLY sweep and
    two campaign attempts) left checkmesh_wrong_oriented_faces=10 in case.info
    THREE TIMES, and runs/val_coarse5 carried two copies of every checkmesh
    line. Readers of case.info split on '=' and take one — which one depends on
    whether they scan forwards or build a dict — so a receipt from a superseded
    mesh can outlive the mesh that produced it."""
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    assert "_mq_record()" in src
    for key in ("checkmesh_zero_volume_cells", "checkmesh_wrong_oriented_faces",
                "checkmesh_max_skewness", "layers_achieved"):
        assert f'echo "{key}=' not in src, (
            f"{key} must go through _mq_record, which drops the previous line")
    assert src.index("_mq_record()") < src.index("_mq_record layers_achieved")
