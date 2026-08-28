"""Gate MULTI-CHINE — the two body plans this grammar could not draw.

THE DEFECT, and it is a capability gap rather than a bug.
`docs/audit/geometry-representation.md` reads "multi-chine NO", and
`docs/BUILD-PLAN.md` PV-4 names what that costs: the kernel reaches TWO
of the five standard body plans, and the two it misses are the
double-chine forms. Multi-chine is the PLYWOOD answer to a round bilge,
which is why the same row also calls it the honest replacement for the
`roundness = 0` pin that sheet-built typologies currently carry — that
pin is a stopgap correct for the unroller we have, not a principle.

THE CONSTRUCTION, and why it is a LIST rather than a third branch. The
section was keel -> C (turn of bilge, filleted by rho) -> [W at the
design waterline when dwl > 0] -> sheer. Phase 3 added W as a hand-written
special case in four places. A second breakpoint at a height nobody
pinned to z = 0 would have made each of those an eight-case clip, and two
branches that must agree is this codebase's recurring defect. So the
topside is a KNUCKLE LIST walked by one loop, and the cases it replaces
are recovered as its members:

    k = 0   legacy round-bilge / single chine
    k = 1   the waterline knuckle, OR a second chine alone
    k = 2   both, ordered by height

The loop reproduces the branches it replaced expression for expression,
which is why the pre-Phase-5 fences still hold at exactly 0.0 rather than
at a tolerance. These tests hold that, and hold the append law.
"""

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate, sample_valid
from navalai.geometry import Hull, _immersed, _immersed_batch
from navalai.mission import MissionSpec

CHINE = {"ch2_y": 0.10, "ch2_z": 0.55}


def _base():
    X, _ = sample_valid(1, MissionSpec(), seed=5)
    return np.asarray(X, float)[0]


def _with(**kw):
    g = grammar.named(_base()).copy()
    g.update(kw)
    return grammar.vector(g)


def test_the_arity_event_is_lawful():
    """ch2_y = 0 must be a proven no-op, and pinned in the DRAW box."""
    assert grammar.N_PARAMS == 36
    for gname in ("ch2_z", "ch2_y"):
        assert gname in grammar.POST_HOC_DEFAULTS
        assert grammar.POST_HOC_DEFAULTS[gname] == 0.0
        i = grammar.NAMES.index(gname)
        assert grammar.DRAW_LOW[i] == grammar.DRAW_HIGH[i] == 0.0, (
            "a random un-designed breakpoint on the topside is not a hull "
            "anyone asked for, and pinning it is what keeps every seeded "
            "stream bit-identical across the arity event")
    x36 = _base()
    assert np.array_equal(grammar.pad_genome(x36[:34]), x36)


def test_zero_offset_is_not_a_second_chine_at_all():
    """The gate is ch2_y, not ch2_z — the CODE PATH must not change.

    At zero offset the vertex would lie exactly on the line it interrupts,
    so it is not a chine. A hull that took the multi-chine path to arrive
    at the same numbers would still be a different hull as far as this
    project's fences are concerned — the same discipline dwl, the tunnel
    and the split were each held to.
    """
    for z in (0.0, 0.3, 0.9):
        h = Hull(_with(ch2_z=z, ch2_y=0.0))
        assert not h.has_second_chine
        assert h._topside_chain() is None, (
            f"ch2_z={z} built a topside chain with no offset — ch2_z is "
            f"unreachable code while ch2_y is 0 and must stay that way")


def test_the_second_chine_is_an_exact_vertex_of_the_sampled_section():
    """A mesh that misses a knuckle is a different hull.

    MEASURED before this landed: the nearest sample sat 0.273 m from the
    second chine on a 41-station hull, because a uniform arc-length walk
    passes a breakpoint rather than landing on it. The waterline knuckle
    paid for the same lesson at 0.455 m.
    """
    h = Hull(_with(**CHINE))
    assert h.has_second_chine
    for i in (5, 20, 35):
        sec = h.section(i)
        V = np.array([h.y_ch2[i], h.z_ch2[i]])
        assert float(np.min(np.linalg.norm(sec - V, axis=1))) == 0.0, (
            f"station {i}: the second chine is not a vertex of the "
            f"sampled section")


def test_the_batch_clip_is_the_scalar_clip_at_every_chain_length():
    """k = 0, 1 and 2 — the batch stays the loop, element for element."""
    for kw in ({}, dict(dwl=0.6), CHINE, dict(dwl=0.6, **CHINE)):
        h = Hull(_with(**kw))
        ch = h._topside_chain()
        K, P0, C, P2, S = h._controls()
        for wl in (-0.2, -0.05, 0.0, 0.08, 5.0):
            ab, bb, zb = _immersed_batch(K, P0, C, P2, S, wl, chain=ch)
            for i in range(0, h.n_stations, 7):
                a, b, z = _immersed(K[i], P0[i], C[i], P2[i], S[i], wl,
                                    chain=None if ch is None else ch[i])
                assert (a, b, z) == (ab[i], bb[i], zb[i]), (
                    f"{kw} station {i} at wl {wl}: the batch and the "
                    f"definition disagree")


def test_the_chain_is_ordered_by_height_not_by_construction_order():
    """A chain that does not climb makes leg_cut extrapolate off a leg."""
    h = Hull(_with(dwl=0.6, **CHINE))
    ch = h._topside_chain()
    assert ch is not None and ch.shape[1] == 2
    assert np.all(np.diff(ch[:, :, 1], axis=1) >= 0.0), (
        "the topside chain is not ascending in z at every station; the "
        "clip walks it assuming it climbs, and an out-of-order pair "
        "returns a half-breadth that is not on the hull")


def test_a_second_chine_changes_the_surface_and_survives_the_ladder():
    """It must be a real geometric change, and a floatable one."""
    plain, chined = Hull(_base()), Hull(_with(**CHINE))
    assert chined.wetted_surface(0.0) > plain.wetted_surface(0.0), (
        "a chine standing outboard of the topside line adds girth; if the "
        "wetted surface did not move, the vertex is not in the surface")
    for x in (_base(), _with(**CHINE), _with(dwl=0.6, **CHINE)):
        ev = evaluate(x, MissionSpec())
        assert ev.tier == "L1" and ev.hydro is not None


def test_a_chine_above_the_waterline_leaves_the_hydrostatics_alone():
    """The physics check that says the vertex is in the right place.

    At ch2_z 0.55 the chine sits well above the floated waterline, so the
    IMMERSED half-section cannot know about it. A displacement that moved
    would mean the vertex had been inserted below the water it is drawn
    above — and this is exactly the kind of error a sampled-polygon
    integral hides and a closed form cannot.
    """
    plain, chined = Hull(_base()), Hull(_with(**CHINE))
    wl = float(evaluate(_base(), MissionSpec()).wl)
    zc = float(np.min(chined.z_ch2))
    if zc <= wl:
        pytest.skip(f"the chine is immersed at this float ({zc:.3f} <= "
                    f"{wl:.3f}); this test is about the dry case")
    a0, b0, z0 = plain.hydro_arrays(wl)
    a1, b1, z1 = chined.hydro_arrays(wl)
    assert np.allclose(a0, a1, atol=0.0, rtol=0.0), (
        "a DRY second chine moved the immersed area — the vertex was "
        "inserted below the waterline it is drawn above")
    assert np.allclose(b0, b1, atol=0.0, rtol=0.0)
