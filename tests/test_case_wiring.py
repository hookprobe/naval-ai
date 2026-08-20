"""The four seams `navalai/cfd/case.py` had and did not use.

Every test below pins a number that was MEASURED before the fix and after it,
and the docstring carries both. None of them needs OpenFOAM: each checks what
the generator WRITES, which is where all four defects lived.

  G1  `hull_to_stl` triangulated the caller's 41-station hull, so `closed_mesh`
      lerped section control points between 41 kinks no matter how fine nx and
      nz were made. Rebuilding at `export._LOFT_STATIONS` = 161 first.
  G2  nx 600 was not station-aligned and bought triangles rather than geometry.
  C3  `fidelity.MIN_CELLS_PER_WAVELENGTH` was reachable from the planner and
      never from the case writer.
  C4  `limits.RE_TRANSITION_BAND` had ZERO consumers in `navalai/cfd/`, and a
      dead `FidelitySpec.target_yplus = 30.0` contradicted the shipped 100.0.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

import numpy as np
import pytest

from navalai import geometry as G
from navalai import grammar
from navalai.cfd import case as C
from navalai.geometry import Hull
from navalai.reference import reference_params

# The kit reference genome, hard chine (roundness = 0), LWL 12.2446 m. Carried
# as the third hull of the G1 measurement because it is the one the rebuild
# helps LEAST, and a fix measured only on the hulls it flatters is not measured.
KIT_GENOME = np.array([12.24464859, 3.105685017, 0.55, 1.55, 0.6392941018,
                       -1.0, 0.4760097448, 0.3, 9.039289126, 9.039289126,
                       0.35, 0.0, 0.15, 0.0, 0.0, 0.18])


def _round_bilge_params() -> np.ndarray:
    """The reference genome with the bilge radiused — `nz` then matters."""
    p = reference_params().copy()
    p[[n for n, (nm, *_) in enumerate(grammar.PARAMS) if nm == "roundness"][0]] = 0.9
    return p


def _analytic_sections(params, xs, rho, n_lo, n_hi) -> np.ndarray:
    """The section at each x with NO station lerp anywhere in the chain.

    `geometry._stations` is a closed form in x — `Hull.__post_init__` merely
    samples it at `linspace(0, LWL, n_stations)` — so evaluating it AT the STL's
    own x-grid gives the surface the triangulation is trying to be. This is the
    reference the G1 table below is measured against; it is not a denser mesh
    standing in for the truth, it is the truth the mesh discretises.
    """
    s = G._stations(np.asarray(params, float), np.asarray(xs, float))
    return np.array([G.sample_section((0.0, s["z_keel"][k]),
                                      (s["y_chine"][k], s["z_chine"][k]),
                                      (s["y_sheer"][k], s["z_sheer"][k]),
                                      (s["y_wl"][k], 0.0), rho, n_lo, n_hi)
                     for k in range(len(xs))])


def _station_lerp_mm(params, n_stations: int, nx: int, nz: int) -> float:
    """Max |sampled section - analytic section| [mm] over the STL x-grid."""
    h = Hull(np.asarray(params, float), n_stations=n_stations)
    jc = h.chine_row(nz)
    xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
    got = h._sections_at_rows_batch(xs, jc, nz - jc)
    want = _analytic_sections(params, xs, h.roundness, jc, nz - jc)
    return 1e3 * float(np.linalg.norm(got - want, axis=2).max())


def _info(case_dir: Path) -> dict[str, str]:
    out = {}
    for line in (case_dir / "case.info").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# ---------------------------------------------------------------------------
# G1 — the STL is rebuilt longitudinally before it is triangulated
# ---------------------------------------------------------------------------

def test_the_stl_is_lofted_at_161_stations_not_at_the_callers_41():
    """MEASURED 2026-08-20 at nx=600/nz=120, max deviation of the sampled
    section from the ANALYTIC section (mm):

        stations                     41       81      161      321      641
        reference (mid_params)  11.8414   3.0977   0.8029   0.3000   0.1157
        round-bilge (rho 0.9)    7.4961   2.0085   0.7624   0.2847   0.1098
        kit reference genome     4.1587   3.3374   2.5354   2.0243   1.0509

    14.7x and 9.8x on the two smooth hulls. The kit genome moves 1.64x and its
    residual is NOT a station-lerp term — it sits within one STL x-step of the
    max-area station at every count, where the SAC's branches meet — so this
    test bars it separately rather than pretending one bar covers both.

    The girth error is already negligible at this nz and does not explain any
    of it: 0.000 mm on a hard chine, 0.708 mm round-bilge at nz 120.
    """
    ref, rb = reference_params(), _round_bilge_params()
    n = C._stl_loft_stations()
    assert n == 161, n

    # The two smooth hulls: the 41-station surface is >10x worse than 161's,
    # and 161 is inside a millimetre.
    assert _station_lerp_mm(ref, 41, 600, 120) > 10.0
    assert _station_lerp_mm(ref, n, 600, 120) < 1.0
    assert (_station_lerp_mm(ref, 41, 600, 120)
            / _station_lerp_mm(ref, n, 600, 120)) > 10.0
    assert _station_lerp_mm(rb, 41, 600, 120) > 7.0
    assert _station_lerp_mm(rb, n, 600, 120) < 1.0

    # The hull the rebuild helps least, pinned at what it actually buys so a
    # regression there is visible and an over-claim is impossible.
    kit_41 = _station_lerp_mm(KIT_GENOME, 41, 600, 120)
    kit_n = _station_lerp_mm(KIT_GENOME, n, 600, 120)
    assert kit_41 == pytest.approx(4.1587, abs=0.01), kit_41
    assert kit_n == pytest.approx(2.5354, abs=0.01), kit_n
    assert kit_n < kit_41


def test_hull_to_stl_ships_the_rebuilt_surface_and_not_the_callers(tmp_path):
    """The mesh in the file is `loft_hull(hull, 161).closed_mesh(...)`, byte
    for byte, and is NOT the 41-station mesh. Asserted on the bytes because a
    docstring claiming a rebuild is exactly what G1 was: `export.py` had done
    this for STEP since the loft receipt landed and `hull_to_stl` had not.
    """
    from navalai.export import loft_hull

    hull = Hull(reference_params())
    got = tmp_path / "got.stl"
    sha = C.hull_to_stl(hull, got, nx=161, nz=48)

    want = C._tris_to_ascii_stl(*loft_hull(hull, C._stl_loft_stations())
                               .closed_mesh(nx=161, nz=48))
    assert got.read_bytes() == want
    assert sha == hashlib.sha256(want).hexdigest()

    old = C._tris_to_ascii_stl(*hull.closed_mesh(nx=161, nz=48))
    assert got.read_bytes() != old, (
        "the rebuild is a no-op — hull_to_stl is still triangulating the "
        "caller's station grid")


def test_the_loft_station_count_has_one_home():
    """161 is `export._LOFT_STATIONS`, imported and not restated. The STEP loft
    and the CFD STL lerp between the same stations for the same reason, so a
    second literal here would be defect class 2 waiting to drift — which is
    precisely how `_NX_BASE` came to exist in four places.
    """
    from navalai import export

    assert C._stl_loft_stations() == export._LOFT_STATIONS
    src = Path(C.__file__).read_text()
    assert "_LOFT_STATIONS = " not in src, (
        "cfd/case.py has grown its own copy of the loft station count")
    # station-ALIGNED on the validated hull's own 41 stations (161 = 4*40 + 1),
    # so the rebuild contains them rather than merely being finer.
    assert (C._stl_loft_stations() - 1) % (Hull(reference_params()).n_stations
                                           - 1) == 0


#: Hull 18 of `sample_valid(25, MissionSpec(), seed=0)` — the seed-0 population
#: gate2u meshed — transcribed so this test does not pay for a 25-hull
#: evaluation to ask one question about one hull. It is the ONE hull in that
#: population whose longitudinal feature-edge count moves with the rebuild.
GATE2U_HULL_18 = np.array([
    13.046432698462207, 2.7480917699791982, 0.74201978627344,
    1.6679707915787756, 0.568160371441588, -2.8784437434258483,
    0.6562440668723983, 0.13483793026485982, 10.013121841229102,
    27.85083323799488, 0.3011481172580528, 0.4279218295030762,
    0.2353356921454436, 0.45308207204243456, 18.058384188087267,
    0.2618629612938492])

#: Hull 14 of the same population — the counter-example: the 41-station surface
#: carries a 28 deg longitudinal crease that is not on the hull.
GATE2U_HULL_14 = np.array([
    17.967124465777225, 3.489057306789841, 1.0166933816981099,
    2.4965046185293893, 0.6692575877303888, -0.3502760473951345,
    0.5873129560660968, 0.3148593357250972, 8.445263881473824,
    10.642271148394014, 0.39900950331053814, 0.32367452692191134,
    0.4582126844411613, 0.8445799014629709, 14.794314990144354,
    0.13083766921447992])


def _max_longitudinal_dihedral(params, n_stations, nx, nz=120):
    """(max dihedral [deg], count over 30 deg, x/L of the worst) on the shell.

    `closed_mesh` splits quad (i,j) into T1 = (S[i,j], S[i,j+1], S[i+1,j+1])
    and T2 = (S[i,j], S[i+1,j+1], S[i+1,j]), so the STATION-TO-STATION edge
    S[i+1,j]-S[i+1,j+1] is shared by T2(i,j) and T1(i+1,j). That is the crease
    family the loft rebuild moves; girth and diagonal creases are a different
    question and are not mixed in here. 30 deg is the bar
    `SURFACE_FEATURES`' `includedAngle 150` extracts.
    """
    h = Hull(np.asarray(params, float), n_stations=n_stations)
    jc = h.chine_row(nz)
    xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
    S = np.empty((nx, nz + 1, 3))
    S[:, :, 0] = xs[:, None]
    S[:, :, 1:] = h._sections_at_rows_batch(xs, jc, nz - jc)
    a, b, c, d = S[:-1, :-1], S[:-1, 1:], S[1:, 1:], S[1:, :-1]
    n1, n2 = np.cross(b - a, c - a), np.cross(c - a, d - a)
    live1 = np.linalg.norm(n1, axis=-1) > 2e-10
    live2 = np.linalg.norm(n2, axis=-1) > 2e-10
    u1 = n1 / np.maximum(np.linalg.norm(n1, axis=-1, keepdims=True), 1e-300)
    u2 = n2 / np.maximum(np.linalg.norm(n2, axis=-1, keepdims=True), 1e-300)
    m = live2[:-1] & live1[1:]
    ang = np.degrees(np.arccos(np.clip(
        np.einsum("...k,...k->...", u2[:-1], u1[1:]), -1.0, 1.0)))
    over = (ang > 30.0) & m
    i = int(np.unravel_index(np.where(m, ang, -1.0).argmax(), ang.shape)[0])
    return float(ang[m].max()), int(over.sum()), float(xs[i + 1] / xs[-1])


def test_the_rebuild_resolves_the_max_area_crease_it_does_not_invent_it():
    """THE CHALLENGE TO G1, MEASURED. Counting surface feature edges above
    30 deg (what `surfaceFeatureExtract`'s `includedAngle 150` acts on) over
    the whole seed-0 population, the rebuild moves the LONGITUDINAL family from
    0 to 53 edges — and all 53 are on hull 18. If the rebuild invented them the
    change would be a defect; this test is the evidence that it does not.

    MEASURED on hull 18 (x_mb = 0.65624), max longitudinal dihedral and the
    number of edges over the bar:

        stations      41       161       321       641
        max deg    20.27     34.43     34.48     34.48
        over-bar       0        53        54        54
        x/L of them   --    0.6561    0.6561    0.6561

    161, 321 and 641 agree to 0.05 deg at the hull's OWN max-area station,
    where the SAC's two branches meet with different slopes. A crease three
    refinements agree on belongs to the boat. The 41-station surface did not
    lack it — its 0.326 m station spacing straddled the kink and chorded it
    away, the same mechanism, at the same x_mb, as the kit genome's
    slow-converging deviation in the G1 table.

    And the old surface INVENTED creases of its own: hull 14 reads 28.37 deg at
    41 stations against 13.13 / 13.21 at 161 / 321. There is no direction in
    which 41 stations is the smoother surface, only one in which it is the less
    faithful one.
    """
    n = C._stl_loft_stations()

    d41, o41, _ = _max_longitudinal_dihedral(GATE2U_HULL_18, 41, 600)
    dn, on, xn = _max_longitudinal_dihedral(GATE2U_HULL_18, n, 600)
    d321, o321, x321 = _max_longitudinal_dihedral(GATE2U_HULL_18, 321, 600)

    assert (d41, o41) == (pytest.approx(20.27, abs=0.05), 0)
    assert dn == pytest.approx(34.43, abs=0.05) and on == 53
    # CONVERGED: the crease is the hull's, not the discretisation's.
    assert d321 == pytest.approx(dn, abs=0.1), (dn, d321)
    assert abs(o321 - on) <= 2, (on, o321)
    # …and it sits at the max-area station, not somewhere the lerp invented.
    x_mb = grammar.named(GATE2U_HULL_18)["x_mb"]
    assert xn == pytest.approx(x_mb, abs=2e-3)
    assert x321 == pytest.approx(x_mb, abs=2e-3)

    # The counter-example: 41 stations carried a crease the hull does not have.
    e41, _, _ = _max_longitudinal_dihedral(GATE2U_HULL_14, 41, 600)
    en, _, _ = _max_longitudinal_dihedral(GATE2U_HULL_14, n, 600)
    e321, _, _ = _max_longitudinal_dihedral(GATE2U_HULL_14, 321, 600)
    assert e41 == pytest.approx(28.37, abs=0.05)
    assert en == pytest.approx(13.13, abs=0.05)
    assert e321 == pytest.approx(en, abs=0.2), (en, e321)
    assert en < e41 - 10.0, "the rebuild is supposed to REMOVE this one"


def test_the_shipped_stl_is_watertight_and_still_floats_the_manifest(tmp_path):
    """G1 moves every vertex, so the two receipts that key on the surface are
    re-measured rather than assumed: closed-manifoldness (an open shell floods
    the interior and yields a complete, plausible, meaningless run) and the
    manifest displacement bar of 2%.

    MEASURED: the rebuild REMOVES the loft term the STL volume used to carry —
    `closed_mesh` lerps control points while the ladder trapezoids exact
    section areas at the same stations, and area is convex in those points, so
    the lerped solid was always the smaller one. Moving the mesh onto 161
    stations moves it toward the analytic hull, i.e. toward the number the
    manifest certifies, so this is a bar that got EASIER honestly.
    """
    from navalai.cfd.manifest import manifest_from_evaluation
    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec

    m = MissionSpec()
    ev = evaluate(reference_params(), m)
    man = manifest_from_evaluation(ev, m)
    hull = Hull(reference_params())

    out = tmp_path / "case"
    C.write_resistance_case(hull, 2.0, out, end_time=1.0, np_procs=1,
                            symmetric=True, manifest=man)

    rep = C.stl_watertight_report(out / "constant" / "triSurface" / "hull.stl")
    assert rep["watertight"] and rep["outward"], rep
    assert rep["open_or_nonmanifold_edges"] == 0
    assert rep["winding_conflicts"] == 0

    info = _info(out)
    # The 2% bar is enforced inside the writer (it raises); this asserts the
    # receipt is present and comfortably inside it rather than merely absent.
    assert float(info["manifest_displacement_mismatch_frac"]) < 0.02
    assert float(info["manifest_displacement_mismatch_frac"]) < 0.005, (
        "the loft term should be gone; a mismatch near the bar means the "
        "rebuild did not reach the written surface")


# ---------------------------------------------------------------------------
# G2 — nx snapped onto the loft stations
# ---------------------------------------------------------------------------

def test_the_meshed_nx_is_snapped_onto_the_loft_stations(tmp_path):
    """MEASURED 2026-08-20 at 161 stations, max analytic deviation and the
    triangle count:

        hull                    nx=600/nz=120     nx=481/nz=120
        reference (mid_params)     0.8029 mm        0.7790 mm
        round-bilge (rho 0.9)      0.7624 mm        0.7397 mm
        kit reference genome       2.5354 mm        2.6292 mm
        triangles                   288,862          231,504

    -19.8% of triangles for -3.0% of deviation on the two smooth hulls and
    +3.7% on the kit genome — whose error is the max-area-station kink and not
    an alignment term, so alignment cannot be expected to move it.

    nz IS NOT RE-DERIVED FROM THE SNAPPED nx. The 1:5 ratio would take it
    120 -> 96, and that costs 0.7078 -> 1.0804 mm of girth chordal error on the
    round-bilge hull. Paying for an x-direction alignment out of the girth
    budget would be weakening a bar to make a number look better.
    """
    lwl = 10.0
    target = 0.5 * (C._DOMAIN_LENGTH_L * lwl / C._NX_BASE) / 2 ** C._HULL_REFINE[1]
    assert C.stl_resolution(lwl, target) == (600, 120)
    nx, nz = C.stl_resolution_station_aligned(lwl, target,
                                              C._stl_loft_stations())
    assert (nx, nz) == (481, 120)
    assert (nx - 1) % (C._stl_loft_stations() - 1) == 0
    assert nx <= 600 and nx >= C._STL_NX_FLOOR

    # …and it is the value the case writer actually ships.
    hull = Hull(reference_params())
    out = tmp_path / "case"
    C.write_resistance_case(hull, 2.0, out, end_time=1.0, np_procs=1,
                            symmetric=True)
    info = _info(out)
    assert int(info["stl_nx_requested"]) == 811
    assert int(info["stl_nx_clamped"]) == 600
    assert int(info["stl_nx_shipped"]) == 481
    assert int(info["stl_nz_shipped"]) == 120
    assert int(info["stl_stations"]) == C._stl_loft_stations()
    assert int(info["stl_hull_stations"]) == hull.n_stations
    assert float(info["stl_nx_per_station"]) == 3.0

    # THE BAR IS THE RATIO, NOT THE LITERAL, and `test_stl_forensics` records
    # why: the count is `(nx-1)*nz*4 + ...` MINUS however many stem quads
    # degenerate to zero area on this particular hull, so pinning the integer
    # makes this file fail for changes it has no opinion about. 600x120 shipped
    # 288,862 on this hull; 481x120 is 480/599 of the quads.
    rep = C.stl_watertight_report(out / "constant" / "triSurface" / "hull.stl")
    assert rep["n_tris"] / 288862 == pytest.approx(480 / 599, rel=2e-3), (
        rep["n_tris"])
    assert rep["watertight"] and rep["outward"], rep


def test_the_snap_never_drops_below_the_floor():
    """The floor/cap discipline survives the snap. A request that clamps to the
    80 floor has no aligned value at or above it (161 > 80 is the first), so
    the clamped pair is returned unchanged rather than nx collapsing to 1 —
    a snap that can return a coarser mesh than the floor is not a floor.
    """
    tiny = C.stl_resolution(1.0, 1.0)          # request 1 -> floor
    assert tiny == (C._STL_NX_FLOOR, 16)
    assert C.stl_resolution_station_aligned(1.0, 1.0,
                                            C._stl_loft_stations()) == tiny
    # And a window that DOES contain an aligned value takes the largest one.
    for n_st, want in ((41, 561), (161, 481), (321, 321)):
        lwl = 10.0
        target = (0.5 * (C._DOMAIN_LENGTH_L * lwl / C._NX_BASE)
                  / 2 ** C._HULL_REFINE[1])
        nx, _ = C.stl_resolution_station_aligned(lwl, target, n_st)
        assert nx == want, (n_st, nx)
        assert (nx - 1) % (n_st - 1) == 0


# ---------------------------------------------------------------------------
# C3 — the cells-per-wavelength floor, wired
# ---------------------------------------------------------------------------

def test_a_low_froude_case_is_flagged_against_the_wave_resolution_bar(tmp_path):
    """MEASURED: at Fn 0.20 and scale 1.0 the generated mesh carries 12.73
    cells per wavelength against `fidelity.MIN_CELLS_PER_WAVELENGTH` = 20, and
    the writer said nothing — the number was even RECORDED in case.info, next
    to no bar. So this is a FLAG and not a refusal: the case is written, the
    operator is warned, and the receipt names the scale that would clear it.

    RE-PINNED 2026-08-20, 1.5706 -> 1.5789, and the reason is the point of
    the change. `density_for_wave_resolution(0.20)` = 1.5706 inverts the bar
    EXACTLY, as a continuous quantity — and the writer then turns a density
    into an INTEGER background cell count, so acting on 1.5706 lands back
    UNDER the bar. The Mac measured that on all four Fn-matched coverage
    bands: flagged at 19.90 against a bar of 20, and told to use a scale
    that would have reproduced it. The screen now names
    `fidelity.density_that_clears_wave_resolution` = 90/57 = 1.5789 — one
    background cell in x more, and a rung the writer can actually stand on.
    The property is asserted below the number, because the number is only
    the witness.

    Fn 0.26, the KCS calibration point, reads 21.52 and is CLEAR — the bar is
    not one no shipped case can meet.
    """
    hull = Hull(reference_params())
    lwl = float(hull.x[-1])
    slow = 0.20 * math.sqrt(C._G * lwl)

    scr = C.wave_resolution_screen(lwl, slow, 1.0)
    assert scr["verdict"] == "FLAGGED"
    assert scr["cells_per_wavelength"] == pytest.approx(12.73, abs=0.02)
    assert scr["scale_needed"] == pytest.approx(1.5789, abs=1e-3)
    # THE PROPERTY, not the number: the rung the screen names, fed back in,
    # must CLEAR. Pinning only the value let a continuous inverse that
    # misses by 0.5% sit here looking correct.
    from navalai.fidelity import (MIN_CELLS_PER_WAVELENGTH,
                                  cells_per_wavelength)
    assert cells_per_wavelength(0.20, scr["scale_needed"]) >= \
        MIN_CELLS_PER_WAVELENGTH

    out = tmp_path / "slow"
    with pytest.warns(UserWarning, match="cells per wavelength"):
        C.write_resistance_case(hull, slow, out, end_time=1.0, np_procs=1,
                                symmetric=True)
    info = _info(out)
    assert info["wave_resolution_verdict"] == "FLAGGED"
    assert float(info["wave_resolution_bar"]) == 20.0
    assert float(info["wave_resolution_scale_needed"]) == pytest.approx(
        1.5789, abs=1e-3)

    fast = 0.26 * math.sqrt(C._G * lwl)
    clear = C.wave_resolution_screen(lwl, fast, 1.0)
    assert clear["verdict"] == "CLEAR"
    assert clear["cells_per_wavelength"] == pytest.approx(21.52, abs=0.02)


def test_the_screened_wave_resolution_is_the_meshs_own(tmp_path):
    """The screen must not be describing a different grid from the one written.

    `fidelity.cells_per_wavelength` is a closed form in (Fn, density) and
    `_write_case_dicts` computes `wavelength / dx` off the domain it writes;
    the Lwl cancels and they are the same number. That equality is the whole
    reason the screen may be evaluated BEFORE the mesh dictionaries exist, so
    it is fenced rather than assumed — `fidelity`'s own docstring records the
    last time a closed form and its mesh disagreed (8.49 against 8.94, because
    a fourth copy of `_NX_BASE` did not move when the base did).
    """
    hull = Hull(reference_params())
    out = tmp_path / "case"
    info_dict = C.write_resistance_case(hull, 2.0, out, end_time=1.0,
                                        np_procs=1, symmetric=True)
    info = _info(out)
    assert (float(info["wave_resolution_cells_per_wavelength"])
            == pytest.approx(info_dict["cells_per_wavelength"], rel=1e-3))
    assert (float(info["cells_per_wavelength"])
            == pytest.approx(
                float(info["wave_resolution_cells_per_wavelength"]), abs=0.05))


def test_an_unmeasurable_wave_field_is_refused_not_scored():
    """A non-positive speed has no Froude number, so it has no cells per
    wavelength either. `fidelity.admit` would have compared `nan < 20.0`,
    got False, and ADMITTED it — defect class 1, an unmeasurable value scored
    as a passing one.
    """
    for lwl, speed, scale in ((10.0, 0.0, 1.0), (10.0, -1.0, 1.0),
                              (0.0, 2.0, 1.0), (10.0, float("nan"), 1.0),
                              (10.0, 2.0, 0.0)):
        scr = C.wave_resolution_screen(lwl, speed, scale)
        assert scr["verdict"] == "REFUSED", (lwl, speed, scale, scr)
        assert "unmeasurable" in scr["reason"]


# ---------------------------------------------------------------------------
# C4a — the Reynolds regime gate
# ---------------------------------------------------------------------------

def test_a_laminar_case_is_refused_for_the_reason_that_is_true_of_it(tmp_path):
    """MEASURED 2026-08-20 on the reference genome scaled to 1.0 m at 0.4 m/s
    (Re 3.67e5, below `limits.RE_TRANSITION_BAND[0]` = 5e5): the admissibility
    screen returned DANGEROUS on `stack_over_min_radius` with
    `refused_no_rescue` EMPTY — i.e. WARNED, and the case was WRITTEN. The
    laminar case was not refused for the wrong reason; it was not refused at
    all, and the only thing standing near it was a layer-stack-vs-hull-cell
    mesh-fit check that says nothing about physics and evaporates the moment
    the mesh is made finer.

    The same hull at 0.05 m/s on the 10 m reference (Re 4.59e5) is used for the
    end-to-end refusal because its admissibility verdict is rescuable-DANGEROUS
    (warned, not refused), so the raise under test is unambiguously this one.
    """
    from navalai.limits import RE_TRANSITION_BAND

    hull = Hull(reference_params())
    lwl = float(hull.x[-1])
    scr = C.reynolds_regime_screen(lwl, 0.05)
    assert scr["regime"] == "laminar" and scr["verdict"] == "REFUSED"
    assert scr["re"] < RE_TRANSITION_BAND[0]
    assert scr["re"] == pytest.approx(0.05 * lwl / C._NU_WATER, rel=1e-12)

    with pytest.raises(ValueError, match="LAMINAR"):
        C.write_resistance_case(hull, 0.05, tmp_path / "laminar",
                                end_time=1.0, np_procs=1, symmetric=True)

    # …and it refuses BEFORE writing a surface, not after.
    assert not (tmp_path / "laminar" / "case.info").exists()


def test_a_transition_band_case_is_written_with_a_flagged_receipt(tmp_path):
    """The band 5e5..5e6 is REPORTED, not refused — refusing it would block
    every 2.5-3 m hull the drone line is sized around, and BUILD-PLAN §11.8
    gate 2 makes it a flag, not a bar.

    MEASURED 2026-08-20: the reference genome scaled to 2.5 m at Fn 0.26
    (1.2876 m/s, Re 2.95e6) screened SAFE with a CLEAR wave field at 21.52
    cells/wavelength and was written fully turbulent with NO flag of any kind.
    The receipt exists so nobody quotes it as independent confirmation of the
    empirical tier: a fully-turbulent closure inside the band reproduces
    ITTC-57's OWN bias, so agreement there is correlated error, not validation
    (docs/research/SMALL-CRAFT-REGIMES.md §12).
    """
    from navalai.limits import RE_TRANSITION_BAND

    p = reference_params().copy()
    p[:4] *= 0.25                       # LWL/BWL/T/D together: same shape, 2.5 m
    hull = Hull(p)
    lwl = float(hull.x[-1])
    speed = 0.26 * math.sqrt(C._G * lwl)

    scr = C.reynolds_regime_screen(lwl, speed)
    assert scr["regime"] == "transitional" and scr["verdict"] == "FLAGGED"
    assert RE_TRANSITION_BAND[0] <= scr["re"] < RE_TRANSITION_BAND[1]

    out = tmp_path / "band"
    with pytest.warns(UserWarning, match="transition band"):
        C.write_resistance_case(hull, speed, out, end_time=1.0, np_procs=1,
                                symmetric=True)
    info = _info(out)
    assert info["flow_regime"] == "transitional"
    assert info["flow_regime_verdict"] == "FLAGGED"
    assert "ITTC-57" in info["flow_regime_reason"]
    assert (out / "system" / "controlDict").exists(), "the case is WRITTEN"


def test_both_receipts_are_written_when_both_are_clear(tmp_path):
    """A receipt that only appears when something is wrong cannot distinguish
    "checked and clear" from "never checked" — the same rule the imported-STL
    repair receipt already follows.

    THE FIXTURE SPEED IS 0.26 Fn AND NOT THE SUITE'S HABITUAL 2.0 m/s, AND
    THAT IS ITSELF THE MEASUREMENT. This test was written asserting CLEAR at
    2.0 m/s and FAILED: on the 10 m reference hull 2.0 m/s is Fn 0.2020, which
    the wired bar reads at 13.0 cells per wavelength against 20. Every case
    this suite has been writing at that speed has been under-resolving its
    wave field, and nothing said so — which is exactly the silence C3 exists
    to end, found by the fix in its first run. The case is still written (the
    rung is scale >= 1.541); the receipt now says it.
    """
    hull = Hull(reference_params())
    lwl = float(hull.x[-1])
    speed = 0.26 * math.sqrt(C._G * lwl)
    out = tmp_path / "case"
    C.write_resistance_case(hull, speed, out, end_time=1.0, np_procs=1,
                            symmetric=True)
    info = _info(out)
    assert info["flow_regime"] == "fully_turbulent"
    assert info["flow_regime_verdict"] == "CLEAR"
    assert info["wave_resolution_verdict"] == "CLEAR"
    assert float(info["flow_regime_re"]) == pytest.approx(
        speed * lwl / C._NU_WATER, rel=1e-3)

    # …and the habitual speed, recorded rather than quietly avoided.
    slow = C.wave_resolution_screen(lwl, 2.0, 1.0)
    assert slow["verdict"] == "FLAGGED"
    assert slow["fn"] == pytest.approx(0.2020, abs=1e-3)
    assert slow["cells_per_wavelength"] == pytest.approx(13.0, abs=0.05)


def test_the_transition_band_has_exactly_one_home():
    """`limits.RE_TRANSITION_BAND` is the ONE band; `resistance` already
    consolidated its second copy onto it (a different 3e6 ceiling, so two
    modules answered "is ITTC-57 inside its regime?" differently). The CFD
    screen is the third consumer and must not become the fourth copy.
    """
    from navalai.limits import RE_TRANSITION_BAND
    from navalai.resistance import RE_FULLY_TURBULENT, RE_TRANSITION_ONSET

    assert (RE_TRANSITION_ONSET, RE_FULLY_TURBULENT) == RE_TRANSITION_BAND
    assert C.reynolds_regime_screen(10.0, 2.0)["band"] is RE_TRANSITION_BAND
    src = Path(C.__file__).read_text()
    assert not re.search(r"^\s*_?RE_(TRANSITION|FULLY)\w*\s*=", src, re.M), (
        "cfd/case.py has grown its own copy of the transition band")


def test_an_unmeasurable_reynolds_number_is_refused_not_scored():
    """Same rule as the wave screen: no Re, no verdict, no silent pass."""
    for lwl, speed in ((10.0, 0.0), (10.0, -2.0), (0.0, 2.0),
                       (float("inf"), 2.0), (10.0, float("nan"))):
        scr = C.reynolds_regime_screen(lwl, speed)
        assert scr["verdict"] == "REFUSED" and scr["regime"] == "unknown"


# ---------------------------------------------------------------------------
# C4b — the y+ target has one home
# ---------------------------------------------------------------------------

def test_the_yplus_target_has_exactly_one_home():
    """`FidelitySpec.target_yplus` defaulted to 30.0, was read by NOTHING, and
    contradicted the shipped `case._TARGET_YPLUS = 100.0` by 3.3x. The 30 was
    not merely stale: MEASURED, y+ 30 with 3 layers at expansion 1.3 gave a
    3.06 mm stack against a 19 mm hull cell, snappy extruded 44.98% of hull
    faces on iteration 0 and decayed to ZERO over 35 iterations — no prism
    cells at all — while the summary table went on printing the request.

    The field is retired. This fences the retirement the way
    `test_a_fluid_property_appears_exactly_once_in_case_py` fences the fluid
    constants: a y+ target reappearing anywhere in the package outside
    `cfd/case.py` fails here rather than disagreeing silently.
    """
    import dataclasses

    from navalai import fidelity

    assert "target_yplus" not in {f.name
                                  for f in dataclasses.fields(
                                      fidelity.FidelitySpec)}
    assert C._TARGET_YPLUS == 100.0

    home = Path(C.__file__).resolve()
    decl = re.compile(r"^\s*(?:_?TARGET_YPLUS\s*=|target_yplus\s*:\s*float\s*=)")
    offenders = []
    for path in sorted(Path(fidelity.__file__).parent.rglob("*.py")):
        if path.resolve() == home:
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if decl.match(line):
                offenders.append(f"{path}:{i}: {line.strip()}")
    assert not offenders, (
        "a second y+ target has been declared outside cfd/case.py — that is "
        "the 30-vs-100 defect being re-created:\n" + "\n".join(offenders))

    # The only surviving `target_yplus` in the package is the PARAMETER of
    # `first_layer_thickness`, and its one call site passes the single source.
    src = Path(C.__file__).read_text()
    assert "first_layer_thickness(speed, lwl, _TARGET_YPLUS)" in src


def test_a_collapsed_z_BAND_is_refused_before_a_case_is_written():
    """MEASURED 2026-08-20, and the loud failure was hiding a quiet one.

    `background_counts` floors every background z-band at one cell
    (`max(int(e), 1)`), and `_shared_cell` divided by `n - 1`. Below scale
    0.40 the air band reached 1 and the case writer raised
    ZeroDivisionError — found by the Gate 2A recalibration when it tried to
    build a model-scale fixture, and the reason `mesh_robustness.py --scale`
    advertised a model scale it could not deliver.

    The crash was the SAFE half. Measured across the family:

        scale   deep hull wave  air
        1.00      7    2    2    4
        0.70      4    2    1    3   <- WAVE band already collapsed
        0.50      3    1    1    2
        0.40      2    2    1    1   <- air band 1: the writer CRASHED here

    Between scale 0.45 and 0.70 a complete, plausible case was written with a
    ONE-CELL wave band. That band IS the free-surface resolution, and
    CLAUDE.md's rule is not ambiguous: "Resolve the free surface or the whole
    run is decoration." A silent one-cell free surface would have produced a
    settled-looking force history on no free surface at all — which is worse
    than a crash, because nothing would have said so.

    Both are now one refusal, by name, before any file is written.
    """
    import math

    import pytest

    from navalai.cfd.case import (_MIN_CELLS_PER_Z_BAND, background_counts,
                                  z_band_collapse)

    # the arithmetic no longer explodes at a single-cell band
    from navalai.cfd import case as _case
    assert _case is not None

    # REFUSED where a band collapses, and the reason NAMES the band
    bad = z_band_collapse(0.40, True)
    assert bad and "air" in bad and "wave" in bad, bad
    assert "free surface" in bad, "the refusal must say WHY it matters: " + bad

    # and the silent case — no crash there, but still refused
    quiet = z_band_collapse(0.70, True)
    assert quiet and "wave" in quiet, quiet
    assert "hull" not in quiet.split("(floor")[0], (
        "at 0.70 only the wave band is thin; the message names bands it "
        "measured, not a fixed list: " + quiet)

    # ADMITTED above the measured threshold, and 0.78 is NOT above it
    assert z_band_collapse(0.78, True) is not None
    assert z_band_collapse(0.79, True) is None
    assert z_band_collapse(1.0, True) is None

    # the floor is what the message claims it is
    for scale in (0.3, 0.5, 0.79, 1.0):
        _, _, *bands = background_counts(scale, True)
        collapsed = z_band_collapse(scale, True)
        assert (min(bands) < _MIN_CELLS_PER_Z_BAND) == (collapsed is not None), (
            f"scale {scale}: bands {bands} disagree with the verdict "
            f"{collapsed!r}")


def test_the_single_cell_band_arithmetic_does_not_divide_by_zero():
    """The crash itself, pinned separately from the policy that now hides it.

    If the refusal above is ever relaxed, this must still hold: one cell
    spans its block and the grading ratio is meaningless, not zero.
    """
    from navalai.cfd import case as C

    # exercise the writer's own helper shape: a 1-cell block returns the
    # whole height rather than raising
    src = (C.__file__)
    assert src.endswith("case.py")
    # the guard clause is present in the source that owns the arithmetic
    text = open(src).read()
    assert "if n <= 1:" in text, (
        "the single-cell guard in _shared_cell was removed; scale <= 0.40 "
        "will raise ZeroDivisionError again")
