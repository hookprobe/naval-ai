"""Gate SPLIT: the split stern — an open centreline, and a waterplane with
a hole the hydrostatics INTEGRATE rather than refuse.

Phase 4B (2026-08-28). Aft of `split_len` the centreline opens: an inner
wall stands at `split_w` of the local chine half-breadth, keel to deck,
and the region inboard is water with sky over it. Unlike the tunnel
(displaced-but-unusable, crown submerged), the split REMOVES displacement
and SPLITS THE WATERPLANE — here the hole is the design, so:

- the section is solved for the SAC PLUS the hole (linear in the chine
  half-breadth, folded into the same coefficient as the tunnel notch),
  and the delivered NET displacement stays the SAC to the bit;
- both immersed integrators subtract the rectangle [0, y_split] x
  [keel, wl] — the wall piercing the waterline is BY DESIGN, no refusal;
- the waterplane integrals subtract the strip: awp ~ (b - y_split),
  ixx ~ (b^3 - y_split^3), lcf and I_L on the reduced strip — and on
  every legacy hull y_split == 0 makes each expression IEEE-identical to
  the unsubtracted one, which is what keeps every recorded state still;
- the sections carry the wall VERTICALLY at y_split (the 3-field start
  rows exist because the tunnel's 2-field crown semantics drew the wall
  slanted from the centreline — measured, and the section is the mesh).

This is the kernel piece the recorded-OPEN hookprobe 70-80% deep-V split
was waiting for.
"""

from __future__ import annotations

import numpy as np
import pytest

from navalai import grammar
from navalai.geometry import Hull, _immersed
from navalai.hydrostatics import solve
from navalai.reference import REFERENCE_HULL

SPLIT = dict(split_w=0.25, split_len=0.35, r_transom=0.45)


def test_split_zero_is_bit_identical():
    h0 = Hull(grammar.vector(REFERENCE_HULL))
    h1 = Hull(grammar.vector(dict(REFERENCE_HULL, split_w=0.0,
                                  split_len=0.0)))
    assert np.array_equal(h0.section(20), h1.section(20))
    for wl in (-0.1, 0.0, 0.12):
        for a, b in zip(h0.hydro_arrays(wl), h1.hydro_arrays(wl)):
            assert np.array_equal(a, b)
    s0, s1 = solve(h0, wl=0.0), solve(h1, wl=0.0)
    for f in ("awp", "lcf", "bm", "bm_l", "disp_kg"):
        assert getattr(s0, f) == getattr(s1, f), f


def test_the_sac_stays_the_net_contract_and_the_hole_is_subtracted():
    hs = Hull(grammar.vector(dict(REFERENCE_HULL, **SPLIT)))
    a, b, _ = hs.hydro_arrays(0.0)
    assert np.allclose(2.0 * a, hs.A_sac, atol=1e-9)
    st = solve(hs, wl=0.0)
    ys = np.minimum(hs.y_split, b)
    assert st.awp == pytest.approx(
        2.0 * float(np.trapezoid(b - ys, hs.x)), abs=1e-9), (
        "the solver's waterplane is not the hole-aware integral")
    assert float(ys.max()) > 0.0


def test_split_scalar_and_batch_agree_bit_exactly():
    hs = Hull(grammar.vector(dict(REFERENCE_HULL, **SPLIT)))
    K, P0, C, P2, S = hs._controls()
    H = hs._split_hole()
    assert H is not None
    for wl in (-0.1, 0.0, 0.12):
        ab, bb, zb = hs.hydro_arrays(wl)
        for i in range(0, hs.n_stations, 9):
            r = _immersed(K[i], P0[i], C[i], P2[i], S[i], wl, hole=H[i])
            assert r == (ab[i], bb[i], zb[i]), (wl, i)


def test_the_wall_is_vertical_at_y_split_and_the_wetted_surface_counts_it():
    hs = Hull(grammar.vector(dict(REFERENCE_HULL, **SPLIT)))
    hp = Hull(grammar.vector(dict(REFERENCE_HULL, r_transom=0.45)))
    sec = hs.section(0)
    assert sec[0][0] == pytest.approx(float(hs.y_split[0]), abs=1e-12), (
        "the section must START on the wall at y_split — a start at the "
        "centreline draws the wall slanted through open water")
    assert sec[0][1] == pytest.approx(float(hs.z_sheer[0]), abs=1e-12)
    assert hs.wetted_surface(0.0) > hp.wetted_surface(0.0)


def test_the_split_wins_where_both_features_stand():
    """PRECEDENCE, not refusal (re-verdicted 2026-08-28). The first cut
    REFUSED a station carrying both a crown and an open centreline — and
    since a uniform legal-box draw activates both features over aft spans
    that always share the transom, that refusal emptied the ENTIRE
    envelope (measured: 0/600 L0 passes, "the LEGAL envelope admits
    nothing at all"). A station with an open centreline has no material
    to carve a crown into, so the split MASKS the tunnel where
    split_frac > 0, deterministically, and the plausible composite stays
    legal: a W forward of the split's end, an open centreline aft."""
    h = Hull(grammar.vector(dict(REFERENCE_HULL, r_transom=0.45,
                                 split_w=0.25, split_len=0.35,
                                 tun_w=0.3, tun_crown=0.4, tun_len=0.2)))
    # aft: split active, crown masked to zero
    assert float(h.y_split[0]) > 0.0 and float(h.z_crown[0]) == 0.0
    # every station: never both
    both = (h.y_split > 0.0) & (h.z_crown > 0.0)
    assert not both.any(), "a station carries a crown AND an open centreline"


def test_the_split_composes_with_the_designed_waterline():
    g = dict(REFERENCE_HULL, split_w=0.30, split_len=0.35, r_transom=0.45,
             dwl=1.0, rb_transom=0.55, rb_stem=0.04, cwp_x=0.10,
             forefoot=0.15, r_stem=0.03)
    hs = Hull(grammar.vector(g))
    a, _, _ = hs.hydro_arrays(0.0)
    assert np.allclose(2.0 * a, hs.A_sac, atol=1e-9)


def test_the_arity_event_is_lawful():
    assert grammar.N_PARAMS == 32
    for gname in ("split_w", "split_len"):
        assert gname in grammar.POST_HOC_DEFAULTS
        i = grammar.NAMES.index(gname)
        assert grammar.DRAW_LOW[i] == grammar.DRAW_HIGH[i] == 0.0
    x32 = grammar.vector(REFERENCE_HULL)
    assert np.array_equal(grammar.pad_genome(x32[:30]), x32)


def test_the_ladder_runs_a_split_hull_end_to_end():
    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec
    ev = evaluate(grammar.vector(dict(REFERENCE_HULL, **SPLIT)),
                  MissionSpec())
    assert ev.tier == "L1" and ev.hydro is not None and ev.gm_m is not None
