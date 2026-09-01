"""Gate DELIVERED-FORM — the descriptor layer must measure the hull the
ladder floats, and the SAC contract must hold feature by feature.

THE MEASURED INCIDENT (2026-09-01, the end-to-end integration audit).
`Hull.form_coefficients` carried a SECOND copy of the sectional area — the
bare outer-envelope quadratic `A = K*yc*(c1*d - c2*m*yc) + d*d*f` — and a
SECOND copy of the waterplane, `yw = 2*y_wl`. Neither knew about the tunnel
notch (Phase 4), the split hole (Phase 4B) or the topside knuckle chain
(Phase 3's design-waterline vertex and Phase 5's second chine), all three of
which `_immersed_batch` — the integral the ladder actually floats on — had
honoured since the day they landed. MEASURED on a 16 x 4 x 0.75 m hull at
Cp 0.72:

    feature   V reported   V delivered   Cm reported   Awp vs the ladder
    split       31.04 m3      28.86 m3     1.1514          +6.33%
    tunnel      29.03 m3      28.86 m3     0.8353          +0.03%
    ch2         28.87 m3      29.42 m3     0.8353          -6.19%

A midship-section coefficient of **1.151** is geometrically impossible — no
section bounded by B and T can exceed B*T — and every one of those numbers is
published by `formcheck.form_descriptors` into the morphology critic, the
certification and the design report. This is the project's own recurring
defect, A NUMBER DECLARED TWICE, sitting in the descriptor layer.

The fix is single-sourcing, not a second correction: `geometry.
immersed_arguments` is now the ONE construction of the five control points,
the knuckle chain, the notch and the hole, and both `Hull` and
`form_coefficients` read it.

THE SECOND FINDING, and it is deliberately NOT fixed here. Every feature
folds its area change into the section solve's target, so the delivered SAC
is the commanded one to machine precision — except the second chine, whose
knuckle redirects the topside leg BELOW it outboard by a wedge the solve's
target does not carry. That drift is now MEASURED and REPORTED
(`Hull.sac_deviation`) instead of silent, and `ch2_*` stays out of every
production draw stream until the wedge is folded in. See the gate ledger row
`Gate SAC-CH2`.
"""

from __future__ import annotations

import numpy as np
import pytest

from navalai import grammar
from navalai.geometry import GeometryError, Hull

# a plausible 16 x 4 m inland cruiser — the brief this project actually has
BASE = {"LWL": 16.0, "BWL": 4.0, "T": 0.75, "D": 1.60, "Cp": 0.72,
        "lcb": -1.0, "x_mb": 0.52, "r_transom": 0.55, "beta_mid": 6.0,
        "beta_bow": 22.0, "beta_len": 0.30, "roundness": 0.35,
        "rocker": 0.06, "forefoot": 0.10, "flare": 6.0, "sheer_rise": 0.10}

FEATURES = {
    "base": {},
    "dwl": dict(dwl=0.8, cwp_x=0.05, rb_transom=0.55, rb_stem=0.25),
    "tunnel": dict(tun_w=0.35, tun_crown=0.35, tun_len=0.30),
    "split": dict(split_w=0.45, split_len=0.35),
    "rho_x": dict(rho_len=0.35, rho_bow=0.15),
    "ch2": dict(ch2_y=0.10, ch2_z=0.55),
}

#: Feature sets whose section solve carries the area change, so the delivered
#: SAC is the commanded one. `ch2` and `dwl` are deliberately absent, for two
#: DIFFERENT reasons — see `test_the_second_chine_declares_its_sac_drift` and
#: `test_a_designed_waterline_that_contradicts_the_sac_is_measured`.
SAC_EXACT = ("base", "tunnel", "split", "rho_x")

#: 401-station `form_coefficients` against 41-station `hydro_arrays`: a
#: TRAPEZOID RESOLUTION difference, not a model difference. MEASURED at
#: 0.039% on the base hull before this gate existed and unchanged by it, so
#: the bar is ~3x that and refuses anything structural.
STATION_RESOLUTION_TOL = 0.0015


def _genome(**over) -> np.ndarray:
    g = dict(grammar.POST_HOC_DEFAULTS)
    g.update(BASE)
    g.update(over)
    return grammar.vector(g)


def _ladder(h: Hull):
    """(volume, waterplane area) exactly as `hydrostatics.solve` integrates
    them — the reference this gate holds the descriptors against."""
    from navalai.geometry import open_waterline_halfbreadth
    x = np.asarray(h.x)
    a, b, _zc = h.hydro_arrays(0.0)
    vol = 2.0 * float(np.trapezoid(a, x))
    awp = 2.0 * float(np.trapezoid(open_waterline_halfbreadth(b, h.y_split),
                                   x))
    return vol, awp


@pytest.mark.parametrize("key", sorted(FEATURES))
def test_form_coefficients_measure_the_hull_the_ladder_floats(key):
    """The defect verbatim: split read 31.04 m3 against a delivered 28.86."""
    h = Hull(_genome(**FEATURES[key]))
    fc = h.form_coefficients()
    vol, awp = _ladder(h)
    assert fc["volume_m3"] == pytest.approx(vol, rel=STATION_RESOLUTION_TOL), (
        f"{key}: form_coefficients reports {fc['volume_m3']:.4f} m3 and the "
        f"ladder floats {vol:.4f} m3. Two answers to one question is this "
        f"repository's recurring defect; the descriptor layer must read "
        f"`immersed_arguments`, not a second algebraic copy.")
    awp_fc = fc["Cwp"] * BASE["BWL"] * BASE["LWL"]
    assert awp_fc == pytest.approx(awp, rel=STATION_RESOLUTION_TOL), (
        f"{key}: Cwp implies a waterplane of {awp_fc:.4f} m2 and the ladder "
        f"integrates {awp:.4f} m2 — the split hole must be subtracted in "
        f"exactly one place (`open_waterline_halfbreadth`).")


@pytest.mark.parametrize("key", sorted(FEATURES))
def test_no_feature_reports_an_impossible_midship_coefficient(key):
    """Cm = A_max / (B*T) > 1 means the reported section does not fit inside
    the box it is measured against. The split hull reported 1.1514."""
    cm = Hull(_genome(**FEATURES[key])).form_coefficients()["Cm"]
    assert 0.0 < cm <= 1.0, (
        f"{key}: Cm = {cm:.4f}. A midship-section coefficient above 1 is not "
        f"a full hull, it is an area measured on a surface the hull does not "
        f"have.")


@pytest.mark.parametrize("key", SAC_EXACT)
def test_the_delivered_sac_is_the_commanded_sac(key):
    """`2 * a == A` at every station, or the feature changed displacement
    behind the designer's back. The tunnel and the split each fold their
    area change into the solve's target (`_stations`' `_tnotch`); this is the
    fence that says so."""
    h = Hull(_genome(**FEATURES[key]))
    dev = h.sac_deviation()
    rel = float(np.max(np.abs(dev) / np.maximum(h.A_sac, 1e-9)))
    assert rel < 1e-9, (
        f"{key}: the delivered sectional area departs from the target by "
        f"{rel:.3e} relative. A feature that silently changes displacement "
        f"is the defect this gate exists for.")


def test_the_second_chine_declares_its_sac_drift():
    """The one feature whose wedge is NOT in the solve's target.

    Not a tolerance being widened: the drift is REPORTED by `sac_deviation`
    and grows linearly with `ch2_y`, which is what makes it a known property
    rather than an unknown. MEASURED 2026-09-01 on this hull:

        ch2_y 0.02 -> 4.60e-03 relative      ch2_y 0.10 -> 2.30e-02
        ch2_y 0.25 (the gene ceiling) -> 5.75e-02

    `ch2_*` is pinned to 0 in `grammar.DRAW_LOW/DRAW_HIGH` and is drawn by no
    production stream, so no shipped hull carries this drift today. Folding
    the wedge into the section solve is the fix; until it lands, this test
    holds the number and the ceiling.
    """
    prev = 0.0
    for ch2_y, want in ((0.02, 4.60e-3), (0.10, 2.30e-2), (0.25, 5.75e-2)):
        h = Hull(_genome(ch2_y=ch2_y, ch2_z=0.55))
        rel = float(np.max(np.abs(h.sac_deviation())
                           / np.maximum(h.A_sac, 1e-9)))
        assert rel == pytest.approx(want, rel=0.02), (
            f"ch2_y {ch2_y}: SAC drift {rel:.3e}, recorded {want:.3e}. If "
            f"this moved because the wedge was folded into the solve, this "
            f"case belongs in SAC_EXACT; if it moved for another reason, "
            f"that is a regression.")
        assert rel > prev, "the drift must grow with the offset that causes it"
        prev = rel
    # and the gene is unreachable from every production draw, which is why
    # the drift is recorded rather than shipped
    for nm in ("ch2_y", "ch2_z"):
        i = grammar.NAMES.index(nm)
        assert grammar.DRAW_LOW[i] == grammar.DRAW_HIGH[i] == 0.0


def test_sac_deviation_is_exactly_zero_without_a_knuckle_chain():
    """The receipt must not invent a deviation on a legacy hull."""
    for key in SAC_EXACT:
        h = Hull(_genome(**FEATURES[key]))
        dev = h.sac_deviation()
        assert np.max(np.abs(dev)) < 1e-12, key


@pytest.mark.parametrize("key", sorted(FEATURES))
def test_section_area_refuses_a_section_its_algebra_cannot_express(key):
    """It returned 1.727 m^2 for a delivered 0.852 m^2 at a split transom —
    a factor of 2.03 under a docstring promising the IMMERSED area. Its value
    is being an INDEPENDENT check of `_immersed`, so it refuses rather than
    delegating (which would delete the second derivation) and rather than
    answering (which is what it used to do)."""
    h = Hull(_genome(**FEATURES[key]))
    featured = key in ("dwl", "tunnel", "split", "ch2")
    if featured:
        with pytest.raises(GeometryError, match="OUTER-ENVELOPE"):
            h.section_area(5)
    else:
        assert h.section_area(5) == pytest.approx(
            h.immersed_section(5, 0.0)[0], abs=1e-12)


def test_a_dry_second_chine_still_moves_the_immersed_area():
    """The proposition `test_multichine` asserts is FALSE, and its test only
    passes because its fixture hull floats below its own turn of bilge.

    A knuckle standing outboard of the chine->sheer line redirects the leg
    BELOW it, so the waterline half-breadth and the immersed area both move
    even when the vertex itself is dry. This is the geometry; the defect was
    a guard that could never fire (docs/LESSONS.md defect class 3).
    """
    plain = Hull(_genome())
    chined = Hull(_genome(ch2_y=0.10, ch2_z=0.55))
    # the vertex is ABOVE the design waterline at every station
    assert float(np.min(chined.z_ch2)) > 0.0
    a0, b0, _ = plain.hydro_arrays(0.0)
    a1, b1, _ = chined.hydro_arrays(0.0)
    assert np.max(np.abs(b1 - b0)) > 1e-3, (
        "a dry knuckle left the waterline exactly where it was — then it is "
        "not standing outboard of the line it interrupts")
    assert np.max(np.abs(a1 - a0)) > 1e-3


def test_a_designed_waterline_that_contradicts_the_sac_is_measured():
    """`rb_stem > 0` with `r_stem = 0` COMMANDS A CONTRADICTION, and the
    kernel silently resolved it in favour of the waterline.

    A station cannot carry finite waterline half-beam and zero sectional
    area at the same time. `r_stem = 0` closes the SAC to a mathematical
    point at the stem; `rb_stem = 0.25` asks the designed waterline for a
    quarter of the maximum half-beam there. The joint solve honours the
    WATERLINE, so the hull delivers area the designer never asked for — and
    `dwl_deviation` could not see it, because it measures the WATERLINE.

    MEASURED 2026-09-01 on the 16 x 4 m hull, and the diagnosis is exact:
    the drift is confined to the last two stations and VANISHES the moment
    the two commands agree.

        rb_stem 0.25, r_stem 0.00   ->  +0.4310% volume, stations [39, 40]
        rb_stem 0.00, r_stem 0.00   ->  -0.0000%, no station
        rb_stem 0.25, r_stem 0.25   ->  -0.0000%, no station

    Not reachable from production today: `morphology_search._derived_dwl`
    reads `rb_stem` OFF the delivered plan (measured 0.0000 on 12 of 12
    sampled genomes, so it never commands the contradiction) and the draw
    box pins `dwl`. This test holds the diagnosis so a future dwl-exploring
    stream cannot re-acquire it silently.
    """
    common = dict(dwl=0.8, cwp_x=0.05, rb_transom=0.55)

    def drift(**over):
        h = Hull(_genome(**common, **over))
        x = np.asarray(h.x)
        return (100.0 * float(np.trapezoid(h.sac_deviation(), x))
                / float(np.trapezoid(np.asarray(h.A_sac), x)))

    contradictory = drift(rb_stem=0.25, r_stem=0.0)
    assert contradictory == pytest.approx(0.4310, rel=0.02), contradictory
    assert abs(drift(rb_stem=0.0, r_stem=0.0)) < 1e-9, (
        "with no stem beam commanded, the designed waterline and the SAC "
        "agree and the delivered area must be the commanded area")
    assert abs(drift(rb_stem=0.25, r_stem=0.25)) < 1e-9, (
        "with the two end ratios AGREEING, the drift must vanish — that is "
        "what proves the drift is the contradiction and not the feature")
    # and the receipt names the stations, so a reader can see where
    h = Hull(_genome(**common, rb_stem=0.25, r_stem=0.0))
    hot = np.flatnonzero(np.abs(h.sac_deviation()) > 1e-9)
    assert hot.tolist() == [39, 40], hot.tolist()
