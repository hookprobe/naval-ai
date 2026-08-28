"""Gate RHO-X: the bilge radius varies along the length.

Phase 3's named remainder (audit table: "Section = knuckle list, rho(x),
multi-chine | 5 fixed control points, ONE GLOBAL rho"). Real hulls do not
carry one bilge shape stem to stern — the reference corpus holds
`round_bilge` and `hard_chine` as SEPARATE families precisely because a
hull that transitions had to pick one. Two post-hoc genes (`rho_bow`,
`rho_len`) carry the warp, on the flare warp's law so this kernel has one
shape of "a thing that changes toward the bow" rather than three.
"""

from __future__ import annotations

import numpy as np
import pytest

from navalai import grammar
from navalai.geometry import Hull, _fillet_coeffs, _roundness_x
from navalai.reference import REFERENCE_HULL

WARP = dict(roundness=0.0, rho_bow=0.9, rho_len=0.45)


def test_rho_len_zero_is_bit_identical():
    h0 = Hull(grammar.vector(REFERENCE_HULL))
    h1 = Hull(grammar.vector(dict(REFERENCE_HULL, rho_len=0.0, rho_bow=0.7)))
    for attr in ("y_chine", "z_chine", "y_wl", "y_sheer", "roundness_x"):
        assert np.array_equal(getattr(h0, attr), getattr(h1, attr)), attr
    assert np.array_equal(h0.section(20), h1.section(20))
    assert h0.wetted_surface(0.0) == h1.wetted_surface(0.0)
    for wl in (-0.1, 0.0, 0.12):
        for a, b in zip(h0.hydro_arrays(wl), h1.hydro_arrays(wl)):
            assert np.array_equal(a, b)


def test_the_warp_law_is_the_flare_laws_shape():
    p = dict(REFERENCE_HULL, **WARP)
    L = p["LWL"]
    x = np.linspace(0.0, L, 41)
    rho = _roundness_x(p, x)
    aft = x <= L - WARP["rho_len"] * L
    assert np.allclose(rho[aft], WARP["roundness"]), "the warp leaks aft"
    assert rho[-1] == pytest.approx(WARP["rho_bow"])
    # monotone and quadratic forward of the break, never outside [0, 1]
    fwd = rho[~aft]
    assert np.all(np.diff(fwd) >= -1e-12)
    assert float(rho.min()) >= 0.0 and float(rho.max()) <= 1.0


def test_a_hull_may_be_hard_aft_and_round_forward():
    """The shape the corpus has two family names for and the kernel had
    none: a chine bottom running into a rounded entry."""
    h = Hull(grammar.vector(dict(REFERENCE_HULL, **WARP)))
    assert float(h.roundness_x[0]) == pytest.approx(0.0)
    assert float(h.roundness_x[-1]) == pytest.approx(0.9)
    # the CONTROL POINTS carry it: a square bilge aft, a filleted one fwd
    K, P0, C, P2, S = h._controls()
    assert np.allclose(P0[0], C[0]) and np.allclose(P2[0], C[0]), (
        "the aft station is not a hard chine")
    assert not np.allclose(P0[-2], C[-2]), "the bow station is not filleted"


def test_the_area_coefficients_are_per_station():
    """`section_area` closed form must read the LOCAL fillet, or the
    algebra describes a section the hull does not have."""
    h = Hull(grammar.vector(dict(REFERENCE_HULL, **WARP)))
    c1_aft, c2_aft = _fillet_coeffs(float(h.roundness_x[0]))
    c1_bow, c2_bow = _fillet_coeffs(float(h.roundness_x[-2]))
    assert (c1_aft, c2_aft) != (c1_bow, c2_bow)
    # and the delivered SAC is still the contract at every station
    a, _b, _z = h.hydro_arrays(0.0)
    assert np.allclose(2.0 * a, h.A_sac, atol=1e-9)


def test_the_arity_event_is_lawful():
    assert grammar.N_PARAMS == 36
    for gname in ("rho_bow", "rho_len"):
        assert gname in grammar.POST_HOC_DEFAULTS
        i = grammar.NAMES.index(gname)
        assert grammar.DRAW_LOW[i] == grammar.DRAW_HIGH[i] == 0.0
    x36 = grammar.vector(REFERENCE_HULL)
    assert np.array_equal(grammar.pad_genome(x36[:34]), x36)


def test_the_ladder_runs_a_warped_bilge_hull_end_to_end():
    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec
    ev = evaluate(grammar.vector(dict(REFERENCE_HULL, **WARP)), MissionSpec())
    assert ev.tier == "L1" and ev.hydro is not None and ev.gm_m is not None
