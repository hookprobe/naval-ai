"""Gate TUNNEL: the W-stern — houseboat17's topology, in-genome.

Phase 4A (2026-08-27). The owner-approved houseboat17 stern is a tunnel
NOTCH cut into a monohull's bottom: the centreline keel rises to a crown
over the after `tun_len` of the hull, walls sloping down-out to the floor
at `tun_w` of the local chine half-breadth. Three post-hoc genes express
it (arity 27 -> 30, all no-op at 0).

THE CONTRACTS, each asserted here:
- the notch is displaced-but-unusable space (the owner's own sentence),
  so the section is solved for the SAC PLUS the notch and the delivered
  NET displacement stays the SAC — exactly, because the notch area is
  linear in the chine half-breadth and folds into the section quadratic's
  linear coefficient (and into the dwl joint solve's a0/a1) in closed
  form;
- the crown must stay submerged at any floated state — a crown above the
  waterline puts a hole in the waterplane that vessel_terms does not
  model, and that is REFUSED BY NAME, never mis-integrated;
- the sections carry the crown and the floor as exact vertices, so the
  mesh, the wetted surface and the critic all see the W the hydrostatics
  integrate.
"""

from __future__ import annotations

import numpy as np
import pytest

from navalai import grammar
from navalai.geometry import GeometryError, Hull, _immersed, _immersed_batch
from navalai.reference import REFERENCE_HULL

TUN = dict(tun_w=0.4, tun_crown=0.5, tun_len=0.35)


def test_tunnel_zero_is_bit_identical():
    h0 = Hull(grammar.vector(REFERENCE_HULL))
    h1 = Hull(grammar.vector(dict(REFERENCE_HULL, tun_w=0.0, tun_crown=0.0,
                                  tun_len=0.0)))
    assert np.array_equal(h0.section(20), h1.section(20))
    for wl in (-0.1, 0.0, 0.12):
        for a, b in zip(h0.hydro_arrays(wl), h1.hydro_arrays(wl)):
            assert np.array_equal(a, b)


def test_the_sac_stays_the_net_displacement_contract():
    """Outer minus notch equals the SAC at every station, to the bit —
    the fold is exact algebra, not an iteration. (The immersed integral
    is the HALF-plane; the section closed form is FULL area — the 2x is
    the convention, and the first fold got it wrong by exactly that
    factor, which is why this test compares the doubled integral.)"""
    ht = Hull(grammar.vector(dict(REFERENCE_HULL, **TUN)))
    a, _b, _z = ht.hydro_arrays(0.0)
    assert np.allclose(2.0 * a, ht.A_sac, atol=1e-9)
    # and the plain hull obeys the same identity, unchanged
    h0 = Hull(grammar.vector(REFERENCE_HULL))
    a0, _, _ = h0.hydro_arrays(0.0)
    assert np.allclose(2.0 * a0, h0.A_sac, atol=1e-9)


def test_tunnel_scalar_and_batch_agree_bit_exactly():
    ht = Hull(grammar.vector(dict(REFERENCE_HULL, **TUN)))
    K, P0, C, P2, S = ht._controls()
    N = ht._tunnel_notch()
    assert N is not None
    for wl in (-0.05, 0.0, 0.15):
        ab, bb, zb = _immersed_batch(K, P0, C, P2, S, wl, notch=N)
        for i in range(0, ht.n_stations, 9):
            a, b, z = _immersed(K[i], P0[i], C[i], P2[i], S[i], wl,
                                notch=N[i])
            assert (a, b, z) == (ab[i], bb[i], zb[i]), (wl, i)


def test_a_crown_above_the_waterline_is_refused_by_name():
    """Both integrators, and the design-time guard in _stations."""
    ht = Hull(grammar.vector(dict(REFERENCE_HULL, **TUN)))
    with pytest.raises(GeometryError, match="roof"):
        ht.hydro_arrays(-0.45)          # floats so low the crown pierces
    with pytest.raises(GeometryError, match="submerged|waterline"):
        Hull(grammar.vector(dict(REFERENCE_HULL, tun_w=0.4, tun_crown=0.999,
                                 tun_len=0.35)))


def test_the_sections_carry_the_w_and_the_wetted_surface_counts_the_walls():
    h0 = Hull(grammar.vector(REFERENCE_HULL))
    ht = Hull(grammar.vector(dict(REFERENCE_HULL, **TUN)))
    sec = ht.section(0)                                    # transom
    crown = np.array([0.0, float(ht.z_keel[0] + ht.z_crown[0])])
    floor = np.array([float(ht.y_tun[0]), float(ht.z_keel[0])])
    assert np.allclose(sec[0], crown, atol=1e-12), "section must START at the crown"
    assert any(np.allclose(r, floor, atol=1e-12) for r in sec), "floor vertex lost"
    assert ht.wetted_surface(0.0) > h0.wetted_surface(0.0), (
        "the tunnel walls add wetted area; a tunnel that reduces it is "
        "not being meshed")


def test_the_tunnel_tapers_to_nothing_forward():
    ht = Hull(grammar.vector(dict(REFERENCE_HULL, **TUN)))
    L = ht.x[-1] - ht.x[0]
    fwd = ht.x > 0.35 * L + 1e-9
    assert not ht.z_crown[fwd].any() and not ht.y_tun[fwd].any(), (
        "the notch leaks forward of tun_len")
    assert float(ht.z_crown[0]) > 0.0 and float(ht.y_tun[0]) > 0.0


def test_the_arity_event_is_lawful():
    assert grammar.N_PARAMS == 34      # + split pair, + the rho(x) pair
    for g in ("tun_w", "tun_crown", "tun_len"):
        assert g in grammar.POST_HOC_DEFAULTS
        i = grammar.NAMES.index(g)
        assert grammar.LOW[i] <= grammar.POST_HOC_DEFAULTS[g] <= grammar.HIGH[i]
        # pinned in the DRAW box: an un-designed random notch is not a hull
        # anyone asked for (the dwl quartet's precedent)
        assert grammar.DRAW_LOW[i] == grammar.DRAW_HIGH[i] == 0.0
    x32 = grammar.vector(REFERENCE_HULL)
    assert np.array_equal(grammar.pad_genome(x32[:27]), x32)


def test_the_ladder_runs_a_tunnel_hull_end_to_end():
    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec
    ev = evaluate(grammar.vector(dict(REFERENCE_HULL, **TUN)), MissionSpec())
    assert ev.tier == "L1" and ev.hydro is not None
    # same net SAC as the plain hull -> the same displaced volume at the
    # same waterline, so the tunnel is genuinely priced as lost volume
    h0 = Hull(grammar.vector(REFERENCE_HULL))
    ht = Hull(grammar.vector(dict(REFERENCE_HULL, **TUN)))
    a0 = h0.hydro_arrays(0.0)[0]
    at = ht.hydro_arrays(0.0)[0]
    assert np.allclose(np.trapezoid(a0, h0.x), np.trapezoid(at, ht.x),
                       rtol=1e-9)
