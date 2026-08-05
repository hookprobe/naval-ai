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
