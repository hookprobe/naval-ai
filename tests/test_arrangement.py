"""Gate V2.1 — the arrangement grammar, its AST, and L0-A.

BuildPlan2-FullVessel.md §3, verbatim: *"V2.1 — Arrangement grammar + AST.
Spaces, deck zones, adjacency vocabulary, masses; flat vector bridge for
solvers; L0-A algebraic feasibility (overlap, envelope, min dims) < 10 ms.
Gate V2.1: the Solar-Liveaboard reference layout (hand-authored) round-trips
and passes L0-A; violations report reasons."*

WHY THIS FILE IS MOSTLY NEGATIVE CONTROLS
-----------------------------------------
`navalai/arrangement.py` was written and never executed. Running
`reference_layout()` for the first time raised `ValueError`, and four more
defects surfaced behind it — a foredeck 0.000 m wide, a coachroof interpolated
into a step that exists nowhere, search bounds that excluded the fixture, and
an envelope rule that measured a box at its floor while three spaces stood out
through the side of the coachroof. Each is recorded at the test that catches
it. That is the ordinary outcome of unrun code and is not the interesting part.

The interesting part is that a gate which cannot fail is not a gate, and this
project has already shipped one: `scripts/gate2m.py` printed `VERDICT: PASS`
with a GCI of **-27.027%** because `gci <= 5.0` is true of a negative number.
An arrangement checker is wide open to the same failure — every one of L0-A's
twelve rules is a comparison that a sign error, a wrong array reduction or an
empty loop turns into a permanent pass, and the reference layout passing tells
you nothing about which. So each rule here is driven from BOTH sides: the
reference layout satisfies it, and a deliberately broken layout is shown to
trip THAT rule, naming THAT space.

'Violations report reasons' is likewise tested as a bar, not as a hope. A
`Violation` must name the subject and the rule, and where its bar came out of
`refdata` it must carry the document and the basis — the property whose
absence made `gate2m.py`'s verdict unusable.
"""

from __future__ import annotations

import dataclasses
import math
import pathlib
import time

import numpy as np
import pytest

from navalai import arrangement as A
from navalai import energy, weights
from navalai.geometry import Hull
from navalai.refdata import RefValue
from navalai.refdata import ergonomics as E

_ROOT = pathlib.Path(__file__).parents[1]


# --------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def hull() -> Hull:
    return Hull(A.reference_hull_params())


@pytest.fixture(scope="module")
def env(hull: Hull) -> A.Envelope:
    return A.Envelope.from_hull(hull, trunk=A.reference_trunk(hull))


@pytest.fixture(scope="module")
def ref(hull: Hull) -> A.Arrangement:
    """The hand-authored Solar-Liveaboard layout — Gate V2.1's fixture.

    Module-scoped and treated as IMMUTABLE by every test below. `Arrangement`,
    `Space`, `DeckZone`, `Box` and `PlanBox` are all frozen dataclasses, so a
    test that wants a broken variant has to build one with
    `dataclasses.replace` and cannot corrupt the fixture for the next test.
    """
    return A.reference_layout(hull)


def _with_space(arr: A.Arrangement, sid: str, **kw) -> A.Arrangement:
    """`arr` with one space replaced — the negative controls' only mutator."""
    spaces = tuple(dataclasses.replace(s, **kw) if s.id == sid else s
                   for s in arr.spaces)
    assert any(s.id == sid for s in arr.spaces), f"no space {sid!r} to break"
    return dataclasses.replace(arr, spaces=spaces)


def _with_deck(arr: A.Arrangement, did: str, **kw) -> A.Arrangement:
    decks = tuple(dataclasses.replace(d, **kw) if d.id == did else d
                  for d in arr.deck_zones)
    assert any(d.id == did for d in arr.deck_zones), f"no deck zone {did!r}"
    return dataclasses.replace(arr, deck_zones=decks)


def _rules(rep: A.ArrangementReport) -> set[str]:
    return {v.rule for v in rep.violations}


# ============================================================ the gate bar
#
# Three clauses, in the order BuildPlan2 §3 writes them: round-trips, passes
# L0-A (under 10 ms), violations report reasons.


def test_the_reference_layout_is_the_boat_plm_describes(ref, env):
    """PLM.md §2: Solar Liveaboard — 6 t, 9-14 m, Danube/Black Sea, cat C/D.

    The composition is asserted, not just the pass, because every negative
    control below reaches into this layout by space id: if a rename or a
    refactor quietly emptied it, `check_l0a` would return ok on nothing at all
    and eleven tests would go green together.
    """
    assert 9.0 <= env.lwl <= 14.0, "outside the Solar Liveaboard's length band"
    assert ref.category in ("C", "D"), "PLM.md §2 puts this SKU at cat C/D"
    assert ref.category == A.REFERENCE_CATEGORY

    assert {s.id for s in ref.spaces} == {
        "machinery", "berth.aft", "head", "galley", "nav", "saloon",
        "berth.fwd", "stowage.fwd"}
    # Every function in BuildPlan2 §2's vocabulary is exercised. A reference
    # layout that skipped one would leave that row of MIN_DIMS unexecuted.
    assert {s.function for s in ref.spaces} == set(A.Function)

    assert {d.id for d in ref.deck_zones} == {
        "cockpit", "sidedeck.stbd", "sidedeck.port", "foredeck"}
    assert {d.zone for d in ref.deck_zones} == set(A.Zone), \
        "Z1/Z2/Z3 are the ISO 15085 zone system; all three are laid out"

    # Masses are declared, positioned and uncertain — honesty rule 1.
    assert all(s.mass_kg > 0 and s.sigma_kg > 0 for s in ref.spaces)
    # ... and they are the interior, not the whole boat: this is the bucket
    # `supersede_outfit` replaces, so it must be the same order of magnitude.
    total = sum(s.mass_kg for s in ref.spaces)
    assert 300.0 < total < 1500.0, f"interior fit-out {total:.0f} kg"


def test_the_reference_layout_round_trips_through_the_flat_vector(ref):
    """Gate clause 1. AST -> flat vector -> AST, unchanged.

    The vector is the interface V2.3's CP+GA solver will consume, so 'unchanged'
    has to mean the WHOLE node and not just the coordinates: a bridge that
    dropped a function tag, an adjacency preference or a mass would still round-
    trip its own floats perfectly while handing the optimiser a different boat.
    Frozen dataclasses give `==` structural semantics, so comparing the tuples
    compares every field.
    """
    v = ref.to_vector()
    assert v.shape == (ref.n_slots,)
    assert v.dtype == np.float64
    assert ref.n_slots == 6 * len(ref.spaces) + 4 * len(ref.deck_zones) == 64
    assert len(ref.slot_names()) == ref.n_slots
    assert len(set(ref.slot_names())) == ref.n_slots, "slot names must be unique"

    back = A.Arrangement.from_vector(v, ref)

    assert back.spaces == ref.spaces
    assert back.deck_zones == ref.deck_zones
    assert back.category == ref.category
    # `Envelope` is eq=False: the round trip must hand the SAME object through,
    # not rebuild an equal-looking one off a hull it was never given.
    assert back.envelope is ref.envelope
    assert np.array_equal(back.to_vector(), v)

    # Bit-exact, not approximately: a float that survives a round trip with a
    # rounding step in it will drift once the solver iterates.
    for a, b in zip(back.spaces, ref.spaces):
        assert a.box.to_slots() == b.box.to_slots()


def test_a_moved_vector_moves_exactly_the_slot_it_names(ref):
    """The other half of the bridge: the vector has to be WRITEABLE.

    A round trip alone is satisfied by `from_vector` ignoring `x` entirely and
    returning the template — which would pass clause 1 of the gate and give the
    solver a no-op. So perturb one slot and require that one coordinate, and
    only that one, moved.
    """
    v = ref.to_vector()
    names = ref.slot_names()
    i = names.index("galley.x1")
    v2 = v.copy()
    v2[i] += 0.25

    moved = A.Arrangement.from_vector(v2, ref)
    assert moved.to_vector()[i] == pytest.approx(v[i] + 0.25)
    assert np.array_equal(np.delete(moved.to_vector(), i), np.delete(v, i))

    g = next(s for s in moved.spaces if s.id == "galley")
    g0 = next(s for s in ref.spaces if s.id == "galley")
    assert g.box.x1 == pytest.approx(g0.box.x1 + 0.25)
    # Everything that is NOT a coordinate rides on the template. A solver that
    # could turn a head into a berth by rounding a float would be able to
    # satisfy the ergonomics tier by relabelling.
    assert g.function is g0.function and g.tags == g0.tags
    assert g.adjacency == g0.adjacency and g.mass_kg == g0.mass_kg


def test_from_vector_refuses_a_vector_of_the_wrong_length(ref):
    """A silent truncation would leave half the layout at template values."""
    with pytest.raises(ValueError, match="slots"):
        A.Arrangement.from_vector(ref.to_vector()[:-1], ref)
    with pytest.raises(ValueError, match="slots"):
        A.Arrangement.from_vector(np.zeros(ref.n_slots + 1), ref)


def test_the_reference_layout_passes_l0a(ref):
    """Gate clause 2. No violations, and the report says so both ways."""
    rep = A.check_l0a(ref)
    assert rep.violations == (), "\n".join(rep.messages)
    assert rep.ok is True
    assert rep.messages == ()
    assert rep.subjects() == ()


def test_l0a_runs_inside_the_ten_millisecond_budget(ref):
    """Gate clause 2's number. MEASURED, not assumed.

    BuildPlan2 §3 budgets *"L0-A algebraic feasibility (overlap, envelope, min
    dims) < 10 ms"*, and the budget is the whole reason L0-A exists as a
    separate tier: V2.3's NSGA-II will call it once per candidate layout, so a
    checker at 100 ms turns a 1-minute generation budget into 10 minutes.

    What is timed is `check_l0a` on a built AST. Extracting the `Envelope` from
    the hull is NOT timed and must not be: it is a per-HULL cost the solver pays
    once and then holds fixed while it moves boxes, which is exactly why
    `from_vector` hands the template's envelope straight through. Its cost is
    measured and reported below anyway, so nobody has to guess at it.

    MEASURED 2026-08-07, this Mac (M5, 24 GB), 8 spaces + 4 deck zones:
    median **0.44 ms**, i.e. 23x under the bar. (It was 0.21 ms before the
    envelope-Y rule was made to evaluate a box at its ceiling as well as its
    floor — the cost of that fix is one extra half-breadth column per space,
    and it is worth stating that a correctness fix doubled this number and
    still left a factor of 23.) The median is the statistic asserted: a single
    worst-case sample on a shared machine measures the scheduler.
    """
    A.check_l0a(ref)                       # warm the numpy paths

    n = 200
    samples = []
    for _ in range(n):
        t0 = time.perf_counter()
        A.check_l0a(ref)
        samples.append((time.perf_counter() - t0) * 1e3)
    med = float(np.median(samples))
    best = min(samples)

    assert med < 10.0, f"L0-A median {med:.3f} ms exceeds the 10 ms budget"
    assert best < 10.0, f"L0-A best-case {best:.3f} ms exceeds the budget"
    # A regression guard with room in it: the reference layout measures 0.21 ms
    # and this fires well before the gate does, so a 10x slowdown is caught as
    # a slowdown rather than absorbed silently into the headroom.
    assert med < 2.0, f"L0-A median {med:.3f} ms — 10x its measured cost"


def test_the_envelope_extraction_cost_is_a_per_hull_cost_and_is_stated(hull):
    """The number the timing test deliberately excludes, measured out loud.

    MEASURED: ~5 ms to build the envelope (two passes over a 41 x 41
    half-breadth table, because `reference_trunk` builds a bare envelope of its
    own to size the coachroof against). It is an order of magnitude over the
    L0-A check, which is precisely why it must not sit inside the solver's
    inner loop — and why `Arrangement.from_vector` passes the envelope through
    by identity instead of rebuilding it.
    """
    t0 = time.perf_counter()
    A.Envelope.from_hull(hull, trunk=A.reference_trunk(hull))
    ms = (time.perf_counter() - t0) * 1e3
    assert ms < 500.0, f"envelope extraction {ms:.1f} ms"


# ================================================== clause 3: NEGATIVE CONTROLS
#
# A gate that cannot fail is not a gate. Each test below breaks the reference
# layout in ONE way and requires (a) that L0-A refuses it, (b) that the rule it
# names is the rule that was broken, and (c) that the subject it names is the
# space that was broken. (b) and (c) together are 'violations report reasons':
# an `ok=False` with no row, or a row that blames the wrong space, is the
# boolean-with-no-reason this project keeps calling out.


def test_two_overlapping_spaces_are_refused_and_both_are_named(ref):
    """Negative control 1 — overlap.

    The quarter berth is moved across the centreline into the head. Nothing
    else changes: same function, same length, same masses.
    """
    head = next(s for s in ref.spaces if s.id == "head").box
    clash = A.Box(head.x0 + 0.10, head.x1 + 0.10, head.y0 - 0.10, head.y1 - 0.10,
                  head.z0, head.z0 + 0.95)
    bad = _with_space(ref, "berth.aft", box=clash)

    rep = A.check_l0a(bad)
    assert not rep.ok
    hits = rep.by_rule(A.R_OVERLAP)
    assert len(hits) == 1, rep.messages
    v = hits[0]
    assert "berth.aft" in v.subject and "head" in v.subject
    # The shared volume is REPORTED, so a solver can rank two infeasible
    # layouts instead of only knowing that both are infeasible.
    assert v.measured is not None and v.measured > 0.0
    assert v.required == 0.0
    assert "share" in v.detail


def test_touching_spaces_are_not_overlapping_spaces(ref):
    """The other side of the same rule, and the reason it has a tolerance.

    Two spaces that share a bulkhead have EQUAL coordinates on that face. If
    the overlap test used `>= 0` instead of `> tol`, every bulkhead in the boat
    would be an overlap and no arrangement could ever pass — the failure mode
    that makes a gate get quietly softened later.
    """
    aft = next(s for s in ref.spaces if s.id == "berth.aft").box
    flush = A.Box(aft.x1, aft.x1 + 0.60, aft.y0, aft.y1, aft.z0, aft.z1)
    assert not aft.overlaps(flush, A.TOUCH_TOL_M)
    assert not flush.overlaps(aft, A.TOUCH_TOL_M)
    # ... and half a millimetre of interpenetration is still touching, while
    # two millimetres is not. TOUCH_TOL_M is 1 mm.
    assert not aft.overlaps(dataclasses.replace(flush, x0=aft.x1 - 5e-4),
                            A.TOUCH_TOL_M)
    assert aft.overlaps(dataclasses.replace(flush, x0=aft.x1 - 2e-3),
                        A.TOUCH_TOL_M)


def test_a_space_larger_than_the_envelope_is_refused_on_each_axis(ref, env):
    """Negative control 2 — outside the envelope, one limb at a time.

    Three separate rules, because 'does not fit' has three different physical
    meanings and a solver that is told only 'infeasible' cannot tell a box that
    is too long from one that is too wide.
    """
    saloon = next(s for s in ref.spaces if s.id == "saloon").box

    # (a) past the stem.
    rep = A.check_l0a(_with_space(
        ref, "saloon", box=dataclasses.replace(saloon, x1=env.lwl + 1.5)))
    hits = rep.by_rule(A.R_ENVELOPE_X)
    assert [v.subject for v in hits] == ["saloon"], rep.messages
    assert hits[0].measured == pytest.approx(1.5)

    # (b) wider than the hull at its own floor level. The saloon is already the
    # full interior beam, so 0.5 m a side is unambiguous.
    rep = A.check_l0a(_with_space(
        ref, "saloon",
        box=dataclasses.replace(saloon, y0=saloon.y0 - 0.5, y1=saloon.y1 + 0.5)))
    hits = rep.by_rule(A.R_ENVELOPE_Y)
    assert [v.subject for v in hits] == ["saloon"], rep.messages
    assert hits[0].measured > hits[0].required

    # (c) through the coachroof, and (d) through the bottom.
    rep = A.check_l0a(_with_space(
        ref, "saloon", box=dataclasses.replace(saloon, z1=saloon.z1 + 0.5)))
    hits = rep.by_rule(A.R_ENVELOPE_Z)
    assert [v.subject for v in hits] == ["saloon"], rep.messages
    assert "overhead" in hits[0].detail

    rep = A.check_l0a(_with_space(
        ref, "saloon", box=dataclasses.replace(saloon, z0=env.sole_z - 0.30)))
    hits = rep.by_rule(A.R_ENVELOPE_Z)
    assert [v.subject for v in hits] == ["saloon"], rep.messages
    assert "sole" in hits[0].detail
    assert hits[0].required == pytest.approx(env.sole_z)


def test_a_space_below_its_minimum_dimension_is_refused_and_the_bar_is_cited(ref):
    """Negative control 3 — min dims, and the flip is on the right dimension.

    The quarter berth is shortened from 2.10 m to 1.90 m against the 1 980 mm
    absolute floor. The violation must name the berth, the rule, the measured
    length, the bar AND the document the bar came from — that last part is what
    makes the row re-derivable instead of merely true.
    """
    aft = next(s for s in ref.spaces if s.id == "berth.aft").box
    assert aft.plan_long == pytest.approx(2.10)

    short = dataclasses.replace(aft, x1=aft.x0 + 1.90)
    rep = A.check_l0a(_with_space(ref, "berth.aft", box=short))
    hits = rep.by_rule(A.R_MIN_DIMS)
    assert [v.subject for v in hits] == ["berth.aft"], rep.messages

    v = hits[0]
    assert v.measured == pytest.approx(1.90)
    assert v.required == pytest.approx(E.BERTH_LENGTH_MIN_MM.value / 1e3)
    assert v.source == E.BERTH_LENGTH_MIN_MM.source
    assert v.basis == E.BERTH_LENGTH_MIN_MM.basis
    assert "berth" in v.detail and "1980 mm floor" in v.detail
    assert v.source in str(v) and "basis=" in str(v)


def test_the_min_dim_verdict_flips_within_two_millimetres_of_the_floor(ref):
    """The bar is a BAR, not a vibe.

    At exactly the floor the berth passes; two millimetres under it fails. A
    checker with a fat tolerance would pass a berth 50 mm short and nobody
    would find out until V2.2 asked the same question with a different
    tolerance and disagreed.
    """
    aft = next(s for s in ref.spaces if s.id == "berth.aft").box
    floor = A.min_dims_m(A.Function.BERTH)["plan_long"]
    assert floor == pytest.approx(1.980)

    at = dataclasses.replace(aft, x1=aft.x0 + floor)
    under = dataclasses.replace(aft, x1=aft.x0 + floor - 2e-3)
    assert A.check_l0a(_with_space(ref, "berth.aft", box=at)).by_rule(
        A.R_MIN_DIMS) == ()
    assert A.check_l0a(_with_space(ref, "berth.aft", box=under)).by_rule(
        A.R_MIN_DIMS) != ()


def test_a_degenerate_box_is_refused_before_anything_else_is_measured(ref):
    """Negative control 4 — a zero-extent box.

    It gets its own rule and short-circuits, because every other limb of L0-A
    would otherwise report on a box with no volume: a 0 x 0 x 0 space is inside
    the envelope, overlaps nothing, and would be reported as fitting.
    """
    aft = next(s for s in ref.spaces if s.id == "berth.aft").box
    rep = A.check_l0a(_with_space(
        ref, "berth.aft", box=dataclasses.replace(aft, y1=aft.y0)))
    hits = rep.by_rule(A.R_DEGENERATE)
    assert [v.subject for v in hits] == ["berth.aft"], rep.messages
    assert "non-positive" in hits[0].detail
    # ... and NOT also reported as too small on a dimension it does not have.
    assert rep.by_rule(A.R_MIN_DIMS) == ()


# ------------------------------------------------------ deck-side controls


def test_a_side_deck_below_the_iso_floor_is_refused_and_the_floor_is_the_categorys(ref, env):
    """Negative control 5 — the ISO 15085:2003 side-deck width, by category.

    This is the one L0-A rule whose bar comes from a STANDARD rather than from
    marine practice, and it is why `Arrangement` carries a design category at
    all: C and D differ by 20 mm. The SAME 110 mm side deck is refused at cat C
    (120 mm floor) and accepted at cat D (100 mm) — so the test proves the
    category is read, not merely stored.
    """
    narrow = A.PlanBox(env.trunk.x0, env.trunk.x1,
                       env.trunk.half_width, env.trunk.half_width + 0.110)
    bad = _with_deck(ref, "sidedeck.stbd", plan=narrow)

    rep_c = A.check_l0a(dataclasses.replace(bad, category="C"))
    hits = rep_c.by_rule(A.R_DECK_MIN_WIDTH)
    assert [v.subject for v in hits] == ["sidedeck.stbd"], rep_c.messages
    v = hits[0]
    assert v.measured == pytest.approx(0.110)
    assert v.required == pytest.approx(E.SIDE_DECK_WIDTH_MIN_MM["C"].value / 1e3)
    assert v.source == E.SIDE_DECK_WIDTH_MIN_MM["C"].source
    assert v.basis == "standard-2003", "an ISO clause, not marine practice"
    assert "design category C" in v.detail

    rep_d = A.check_l0a(dataclasses.replace(bad, category="D"))
    assert rep_d.by_rule(A.R_DECK_MIN_WIDTH) == (), rep_d.messages

    # And the reference layout is not passing by accident: its side decks are
    # 250 mm, twice the cat-C floor. They are the boat's only margin here —
    # coachroof half-width is the deck half-breadth MINUS this, and the
    # coachroof is the whole standing-headroom volume, so widening the side
    # deck narrows the saloon by the same millimetre.
    stbd = next(d for d in ref.deck_zones if d.id == "sidedeck.stbd")
    assert stbd.plan.plan_short == pytest.approx(0.25, abs=1e-9)
    assert stbd.plan.plan_short > 2 * A.deck_min_width_m(
        A.DeckKind.SIDE_DECK, "C")[0] - 1e-9


def test_a_barrier_below_the_low_barrier_floor_is_refused(ref):
    """Negative control 6 — a DECLARED barrier against the 2003 numeric floor.

    `None` means 'no barrier declared' and is deliberately not a failure: WHICH
    zones require one lives in the 2024 equipment lists, which are paywalled
    and recorded absent. What L0-A can check is a barrier that exists and is
    too short, and that check must not be reachable by leaving the field out.
    """
    rep = A.check_l0a(_with_deck(ref, "cockpit", barrier_height_mm=300.0))
    hits = rep.by_rule(A.R_BARRIER)
    assert [v.subject for v in hits] == ["cockpit"], rep.messages
    assert hits[0].required == pytest.approx(
        E.BARRIER_LOW_MIN_MM.value / 1e3)
    assert hits[0].basis == "standard-2003"

    # Absent is not zero: no barrier declared is silent, not a violation.
    quiet = A.check_l0a(_with_deck(ref, "cockpit", barrier_height_mm=None))
    assert quiet.by_rule(A.R_BARRIER) == ()
    assert quiet.ok
    # Zero IS a declaration, and it is a declaration of a barrier that fails.
    assert A.check_l0a(
        _with_deck(ref, "cockpit", barrier_height_mm=0.0)).by_rule(
            A.R_BARRIER) != ()


def test_two_deck_zones_on_the_same_area_are_refused(ref):
    """Negative control 7 — deck overlap, the plan-view twin of R_OVERLAP."""
    stbd = next(d for d in ref.deck_zones if d.id == "sidedeck.stbd")
    rep = A.check_l0a(_with_deck(ref, "sidedeck.port", plan=stbd.plan))
    hits = rep.by_rule(A.R_DECK_OVERLAP)
    assert len(hits) == 1, rep.messages
    assert "sidedeck.stbd" in hits[0].subject and "sidedeck.port" in hits[0].subject
    # The zone labels are in the row, because two Z2 side decks overlapping and
    # a Z1 cockpit overlapping a Z3 foredeck are different problems.
    assert "side-deck" in hits[0].detail and "Z2" in hits[0].detail


def test_deck_under_the_coachroof_is_not_deck(ref, env):
    """Negative control 8 — R_DECK_TRUNK.

    The trunk is the one part of this model the geometry kernel does not know
    about (the hull grammar emits a flush deck at the sheer), so nothing else
    in the pipeline can catch a deck zone drawn straight through it. The
    cockpit is moved forward under the coachroof, narrow enough to keep clear
    of the side decks so exactly one rule fires.
    """
    t = env.trunk
    under = A.PlanBox(t.x0 + 0.10, t.x0 + 0.90, -0.70, 0.70)
    rep = A.check_l0a(_with_deck(ref, "cockpit", plan=under))
    hits = rep.by_rule(A.R_DECK_TRUNK)
    assert [v.subject for v in hits] == ["cockpit"], rep.messages
    assert "coachroof" in hits[0].detail
    assert rep.by_rule(A.R_DECK_OVERLAP) == (), "control is meant to be isolated"


def test_a_deck_zone_wider_than_the_deck_is_refused(ref):
    """Negative control 9 — R_DECK_PLAN, the deck's own envelope rule."""
    fore = next(d for d in ref.deck_zones if d.id == "foredeck")
    rep = A.check_l0a(_with_deck(
        ref, "foredeck", plan=dataclasses.replace(fore.plan, y0=-3.0, y1=3.0)))
    hits = rep.by_rule(A.R_DECK_PLAN)
    assert [v.subject for v in hits] == ["foredeck"], rep.messages
    assert hits[0].measured == pytest.approx(3.0)


def test_the_deck_outline_closes_at_the_stem_so_a_foredeck_cannot_run_to_it(ref, env):
    """DEFECT (found 2026-08-07, `reference_layout`): the foredeck was authored
    as `PlanBox(trunk.x1, LWL, -y, +y)` with
    `y = min_deck_half_breadth(trunk.x1, LWL)`, and the deck outline CLOSES at
    the stem — `y_sheer(LWL)` is 0 — so the minimum over any run ending there is
    zero and the reference boat's foredeck came out 0.000 m wide.

    L0-A caught it as L0A-DEGENERATE, which is the gate doing its job, and the
    layout was still wrong. Both halves are asserted here: the geometry that
    causes it, and the rule that catches it.
    """
    assert env.min_deck_half_breadth(env.trunk.x1, env.lwl) == pytest.approx(0.0)
    assert float(env.y_sheer[-1]) == pytest.approx(0.0)

    y = env.min_deck_half_breadth(env.trunk.x1, env.lwl)
    rep = A.check_l0a(_with_deck(
        ref, "foredeck",
        plan=A.PlanBox(env.trunk.x1, env.lwl, -y, y)))
    assert [v.subject for v in rep.by_rule(A.R_DEGENERATE)] == ["foredeck"]

    # As shipped, the foredeck stops short of the stem and has real width.
    fore = next(d for d in ref.deck_zones if d.id == "foredeck")
    assert fore.plan.x1 < env.lwl
    assert fore.plan.dy > 0.5


def test_a_mass_with_no_sigma_is_refused_by_the_node_itself(ref):
    """Negative control 10 — R_NODE, honesty rule 1 at the AST.

    'Every quantity carries value, tier and sigma.' A hand-authored fit-out
    mass is an estimate by definition, so a zero sigma on one is a claim of
    exactness nobody can make.

    DEFECT (found 2026-08-07): the check was on spaces only. `Space.validate`
    refused a negative mass; `DeckZone.validate` did not, and `mass_items()`
    emits only items with `mass_kg > 0` — so a negative deck mass passed L0-A
    and was then SILENTLY DROPPED from the weight model. Not a crash: a deck
    zone that the gate called feasible and the one weight model did not
    contain. `DeckZone.validate` now checks the same two limbs a `Space` does,
    which is what makes L0-A the guard the aggregate relies on.
    """
    rep = A.check_l0a(_with_space(ref, "galley", sigma_kg=0.0))
    hits = rep.by_rule(A.R_NODE)
    assert [v.subject for v in hits] == ["galley"], rep.messages
    assert "no sigma" in hits[0].detail

    rep = A.check_l0a(_with_space(ref, "galley", mass_kg=-1.0))
    assert [v.subject for v in rep.by_rule(A.R_NODE)] == ["galley"]

    rep = A.check_l0a(_with_deck(ref, "cockpit", sigma_kg=0.0))
    assert [v.subject for v in rep.by_rule(A.R_NODE)] == ["cockpit"]

    bad_deck = _with_deck(ref, "cockpit", mass_kg=-1.0)
    assert [v.subject for v in A.check_l0a(bad_deck).by_rule(A.R_NODE)] == \
        ["cockpit"]
    # This is the half that made the missing check matter. `mass_items()`
    # emits only `mass_kg > 0`, so the negative deck mass does not raise —
    # it VANISHES, and the aggregate is short one item with nothing to say so.
    assert "deck:cockpit" not in {m.id for m in bad_deck.mass_items()}
    assert "deck:cockpit" in {m.id for m in ref.mass_items()}


# ------------------------------------------- every rule, and every rule fires


def _broken_layouts(ref: A.Arrangement, env: A.Envelope) -> dict:
    """One deliberately broken layout per L0-A rule id.

    Kept as data so the coverage test below cannot drift away from the
    individual controls: adding a rule to `arrangement.py` and forgetting to
    break it here fails immediately, which is the only way a rule that can
    never fire gets noticed.
    """
    saloon = next(s for s in ref.spaces if s.id == "saloon").box
    aft = next(s for s in ref.spaces if s.id == "berth.aft").box
    head = next(s for s in ref.spaces if s.id == "head").box
    stbd = next(d for d in ref.deck_zones if d.id == "sidedeck.stbd")
    fore = next(d for d in ref.deck_zones if d.id == "foredeck")
    t = env.trunk
    return {
        A.R_DEGENERATE: _with_space(
            ref, "berth.aft", box=dataclasses.replace(aft, y1=aft.y0)),
        A.R_ENVELOPE_X: _with_space(
            ref, "saloon", box=dataclasses.replace(saloon, x1=env.lwl + 1.5)),
        A.R_ENVELOPE_Y: _with_space(
            ref, "saloon",
            box=dataclasses.replace(saloon, y0=saloon.y0 - 0.5,
                                    y1=saloon.y1 + 0.5)),
        A.R_ENVELOPE_Z: _with_space(
            ref, "saloon", box=dataclasses.replace(saloon, z1=saloon.z1 + 0.5)),
        A.R_OVERLAP: _with_space(
            ref, "berth.aft",
            box=A.Box(head.x0 + 0.10, head.x1 + 0.10, head.y0 - 0.10,
                      head.y1 - 0.10, head.z0, head.z0 + 0.95)),
        A.R_MIN_DIMS: _with_space(
            ref, "berth.aft", box=dataclasses.replace(aft, x1=aft.x0 + 1.90)),
        A.R_DECK_PLAN: _with_deck(
            ref, "foredeck",
            plan=dataclasses.replace(fore.plan, y0=-3.0, y1=3.0)),
        A.R_DECK_TRUNK: _with_deck(
            ref, "cockpit",
            plan=A.PlanBox(t.x0 + 0.10, t.x0 + 0.90, -0.70, 0.70)),
        A.R_DECK_OVERLAP: _with_deck(ref, "sidedeck.port", plan=stbd.plan),
        A.R_DECK_MIN_WIDTH: _with_deck(
            ref, "sidedeck.stbd",
            plan=A.PlanBox(t.x0, t.x1, t.half_width, t.half_width + 0.110)),
        A.R_BARRIER: _with_deck(ref, "cockpit", barrier_height_mm=300.0),
        A.R_NODE: _with_space(ref, "galley", sigma_kg=0.0),
    }


def test_every_l0a_rule_can_actually_fire(ref, env):
    """The gate2m lesson, applied to twelve rules instead of one.

    `scripts/gate2m.py` printed PASS on a DIVERGING grid family because
    `gci <= 5.0` is true of -27.027%: the comparison was there, was executed,
    and could not fail. Each of L0-A's rules is one comparison away from the
    same state, and the reference layout passing tells you only that they all
    return nothing on a good boat.

    So: every rule id the module exports must be broken by something here, and
    the layout that breaks it must trip THAT rule.
    """
    exported = {getattr(A, n) for n in A.__all__ if n.startswith("R_")}
    cases = _broken_layouts(ref, env)
    assert set(cases) == exported, (
        "a rule with no negative control: " + str(exported ^ set(cases)))

    for rule, bad in cases.items():
        rep = A.check_l0a(bad)
        assert not rep.ok, f"{rule}: the broken layout passed L0-A"
        assert rule in _rules(rep), (
            f"{rule} did not fire; got {sorted(_rules(rep))}\n"
            + "\n".join(rep.messages))


def test_every_violation_reports_a_reason_and_a_subject(ref, env):
    """Gate clause 3, as a structural property of every row L0-A can emit.

    A `Violation` with an empty subject is `ok=False` with no way back to the
    boat, which is the defect this project has recorded twice: three placement
    tables nobody could tell apart, and a CFD verdict with no path to the
    measurement. Every row must name a rule, a subject and a human sentence,
    and `str()` must contain all three.
    """
    for rule, bad in _broken_layouts(ref, env).items():
        for v in A.check_l0a(bad).violations:
            assert v.rule and v.rule.startswith("L0A-")
            assert v.subject.strip(), f"{rule}: violation with no subject"
            assert len(v.detail.strip()) > 10, f"{rule}: {v.detail!r}"
            assert v.subject in str(v) and v.rule in str(v)
            if v.measured is not None and v.required is not None:
                assert math.isfinite(v.measured) and math.isfinite(v.required)
            # A bar quoted from a document must arrive with the document.
            assert bool(v.source) == bool(v.basis), (
                f"{rule}: source/basis half-declared — {v}")


def test_a_bar_that_came_from_refdata_arrives_with_its_document(ref, env):
    """The three rules whose numbers are transcribed must cite them.

    L0-A's other rules compare against the hull's own geometry, which has no
    document and correctly carries none. These three compare against `refdata`,
    and a violation that printed only 'too small' would be exactly the
    unre-derivable verdict the `basis` field was added to prevent.
    """
    cases = _broken_layouts(ref, env)
    sourced = (A.R_MIN_DIMS, A.R_DECK_MIN_WIDTH, A.R_BARRIER)
    known = {rv.source for rv in _all_refdata_sources()}
    for rule in sourced:
        hits = A.check_l0a(cases[rule]).by_rule(rule)
        assert hits, rule
        for v in hits:
            assert v.source in known, f"{rule}: {v.source!r} is not a refdata source"
            assert v.basis in ("standard-2003", "approx", "purchased")
            assert v.required is not None


def _all_refdata_sources() -> list:
    from navalai.refdata import constants
    return list(constants(E).values())


# ============================================ masses feed the ONE weight model
#
# CLAUDE.md's design-side invariant, audit 2026-08-05: "One weight model.
# `weights.MassItem`/`aggregate` is the positioned truth ... There were three
# placement tables and they disagreed by 0.7 m on payload LCG." A fourth would
# be a regression, and an arrangement module is where a fourth would appear,
# because it is the first thing in the codebase that knows where a berth is.


def test_every_space_mass_is_a_mass_item_and_they_aggregate(ref):
    """Requirement: expressible as a `MassItem`, and it goes through
    `weights.aggregate` — not through a parallel summation of its own."""
    items = ref.mass_items()
    assert all(isinstance(m, weights.MassItem) for m in items)
    assert {m.id for m in items} == (
        {f"space:{s.id}" for s in ref.spaces if s.mass_kg > 0}
        | {f"deck:{d.id}" for d in ref.deck_zones if d.mass_kg > 0})

    for m in items:
        assert m.tier == "E", "arrangement masses are the ergonomics tier"
        assert m.sigma_kg > 0, "honesty rule 1: no bare number"
        assert m.source and m.basis

    agg = weights.aggregate(items)
    assert agg.n_items == len(items)
    assert agg.total_kg == pytest.approx(
        sum(s.mass_kg for s in ref.spaces)
        + sum(d.mass_kg for d in ref.deck_zones))
    # Sigmas combine in quadrature in ONE place, and the aggregate is the
    # place. Recomputing it here would be the defect this file is guarding.
    assert agg.sigma_kg == pytest.approx(
        math.sqrt(sum(m.sigma_kg ** 2 for m in items)))
    assert 0.0 < agg.lcg_m < ref.envelope.lwl


def test_a_spaces_position_is_its_box_and_there_is_no_placement_table(ref):
    """The structural form of 'no second placement table'.

    A `Space`'s LCG is not looked up anywhere: it IS the centroid of the box
    the gate just checked. Assert it exactly (not approximately), and then move
    a space and require the aggregate to move by the amount arithmetic
    predicts. A hidden fraction table would survive the first assertion and
    fail the second.
    """
    for s in ref.spaces:
        cx, cy, cz = s.box.centre
        m = s.mass_item()
        assert (m.x_m, m.y_m, m.z_m) == (cx, cy, cz)

    before = weights.aggregate(ref.mass_items())
    shift = 0.40
    aft = next(s for s in ref.spaces if s.id == "berth.aft")
    moved = _with_space(
        ref, "berth.aft",
        box=dataclasses.replace(aft.box, x0=aft.box.x0 - shift,
                                x1=aft.box.x1 - shift))
    after = weights.aggregate(moved.mass_items())

    expected = before.lcg_m - shift * aft.mass_kg / before.total_kg
    assert after.lcg_m == pytest.approx(expected, abs=1e-12)
    assert after.lcg_m < before.lcg_m, "moving a berth aft must move the LCG aft"

    # The same for the transverse axis: the galley is to port, so widening it
    # to port must move TCG to port. Before `weights.py` there was no TCG at
    # all and a galley to port produced no list whatsoever.
    galley = next(s for s in ref.spaces if s.id == "galley")
    listed = _with_space(
        ref, "galley",
        box=dataclasses.replace(galley.box, y0=galley.box.y0 - 0.20))
    assert weights.aggregate(listed.mass_items()).tcg_m < before.tcg_m


def test_the_arrangement_module_declares_no_placement_fractions():
    """The source-level fence, in the shape `test_limits_single_source.py` uses.

    Behavioural tests catch a table that is USED. This catches one that is
    merely present — a `LCG_FRACTION`-style dict sitting in `arrangement.py`
    waiting for a caller, which is how the previous three got in.
    """
    src = _code_lines(_ROOT / "navalai" / "arrangement.py")
    for banned in ("LCG_FRACTION", "VCG_FRACTION", "lcg_m", "vcg_m", "_FRACTION"):
        assert banned not in src, (
            f"{banned!r} in arrangement.py: a centre of gravity is computed by "
            "weights.aggregate from positioned MassItems, never declared here")


def test_the_outfit_bucket_is_superseded_exactly_once(ref, hull):
    """The merge, and the coupling it depends on, both measured.

    `energy.weight_items` places a single 'outfit' lump — 55 kg/m of LWL — at
    0.50 LWL. These spaces ARE that lump, described properly, so keeping both
    adds half a tonne of furniture that is not there and pins its LCG at
    midships. The docstring said so; this asserts it, including that the bucket
    name still exists on the other side of the coupling.
    """
    assert A.SUPERSEDED_WEIGHT_BUCKET in energy.LCG_FRACTION, \
        "supersede_outfit is dropping a bucket energy.py no longer declares"

    hull_items = energy.weight_items(
        lwl=ref.envelope.lwl, depth=1.55, hull_surface=30.0,
        deck_area=hull.deck_area(), spec=energy.EnergySpec(), t_design=0.55)
    assert A.SUPERSEDED_WEIGHT_BUCKET in {m.id for m in hull_items}

    merged = A.supersede_outfit(hull_items, ref)
    assert A.SUPERSEDED_WEIGHT_BUCKET not in {m.id for m in merged}
    assert len(merged) == len(hull_items) - 1 + len(ref.mass_items())

    # Double-counting would show up as the outfit lump's mass surviving.
    lump = next(m for m in hull_items if m.id == A.SUPERSEDED_WEIGHT_BUCKET)
    naive = weights.aggregate(hull_items + ref.mass_items())
    honest = weights.aggregate(merged)
    assert naive.total_kg - honest.total_kg == pytest.approx(lump.mass_kg)
    # ... and the interior now has a real transverse centre instead of none.
    assert weights.aggregate(hull_items).tcg_m == 0.0
    assert honest.tcg_m != 0.0


def _code_lines(path: pathlib.Path) -> str:
    """Source with comment lines and docstring prose dropped.

    Same helper as `test_limits_single_source.py`, and for the same reason: the
    docstrings in `arrangement.py` NAME the defect they prevent, and a scanner
    that failed on a module's own explanation would be a scanner bug.
    """
    out = []
    in_doc = False
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.count('"""') >= 2:
            continue
        if stripped.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc or stripped.startswith("#"):
            continue
        out.append(line.split("  #")[0])
    return "\n".join(out)


# ================================== the bars themselves: sourced or explicitly absent


def test_every_minimum_dimension_is_a_refvalue_or_an_explained_absence():
    """Gate V2.0's rule, enforced where V2.1 consumes it.

    A `MinBox` limb is either a `RefValue` carrying its document, or `None`
    with a sentence saying which document does not contain it. What it may
    never be is a plausible float: an invented constant is indistinguishable
    from a transcribed one the moment it lands in a module, and this table is
    what V2.2's ergonomics tier and V2.3's CP solver will both read.
    """
    assert set(A.MIN_DIMS) == set(A.Function), "a function with no floor row"

    for func, mb in A.MIN_DIMS.items():
        limbs = {"plan_long": mb.plan_long, "plan_short": mb.plan_short,
                 "height": mb.height}
        for name, rv in limbs.items():
            if rv is None:
                continue
            assert isinstance(rv, RefValue), f"{func.value}.{name} is a bare number"
            assert rv.source.strip() and rv.basis in ("standard-2003", "approx",
                                                      "purchased")
            assert rv.unit == "mm"
        if any(rv is None for rv in limbs.values()):
            assert len(mb.why_unbounded.strip()) > 20, (
                f"{func.value}: an unbounded limb with no explanation is "
                "indistinguishable from an oversight")


def test_a_locker_has_no_floor_and_says_which_way_that_cuts(ref):
    """STOWAGE is unbounded on all three limbs, on purpose.

    'A shallow locker is still a locker, and inventing a floor would evict real
    stowage.' The forepeak of the reference boat is 0.30 m wide and is a chain
    locker; a fabricated 560 mm floor would delete it and the boat would carry
    its ground tackle nowhere.
    """
    d = A.min_dims_m(A.Function.STOWAGE)
    assert d == {"plan_long": None, "plan_short": None, "height": None}
    assert A.MIN_DIMS[A.Function.STOWAGE].why_unbounded

    fwd = next(s for s in ref.spaces if s.id == "stowage.fwd")
    assert fwd.box.plan_short < 0.56


def test_the_nav_stations_paired_constant_is_read_on_the_right_axis():
    """`SEAT_MIN_MM` is a (width, depth) PAIR and the two limbs index different
    elements. Swapping them is silent — both are plausible seat dimensions —
    and it would let a 400 mm-deep nav seat through while refusing a 750 mm one.
    """
    w, depth = E.SEAT_MIN_MM.value
    assert (w, depth) == (400, 750)
    d = A.min_dims_m(A.Function.NAV)
    assert d["plan_long"] == pytest.approx(depth / 1e3)
    assert d["plan_short"] == pytest.approx(w / 1e3)
    assert d["plan_long"] > d["plan_short"], "a long floor below a short one"


def test_the_galley_height_floor_is_derived_not_transcribed():
    """Two refdata constants added, never a third constant typed out.

    The recurring defect in this codebase is A NUMBER DECLARED TWICE. 1650 mm
    written down beside a 900 and a 750 is that defect with the arithmetic done
    by hand, and it drifts the first time either operand moves.
    """
    got = A.min_dims_m(A.Function.GALLEY)["height"]
    assert got == pytest.approx(
        (E.GALLEY_HOB_HEIGHT_MM.value + E.GALLEY_CLEARANCE_ABOVE_HOB_MIN_MM.value)
        / 1e3)
    assert got == pytest.approx(1.650)
    rv = A.MIN_DIMS[A.Function.GALLEY].height
    assert "DERIVED" in rv.source, "a derived bar must say it is derived"


def test_the_side_deck_floor_is_the_only_category_dependent_bar():
    """C and D differ by 20 mm; a cockpit's floor does not depend on category.

    And a foredeck gets NO floor, because the ISO side-deck number is about a
    passage between coachroof and toerail, not about open deck — promoting it
    would refuse foredecks that comply.
    """
    for cat in ("A", "B", "C", "D"):
        need, rv = A.deck_min_width_m(A.DeckKind.SIDE_DECK, cat)
        assert need == pytest.approx(E.SIDE_DECK_WIDTH_MIN_MM[cat].value / 1e3)
        assert rv is E.SIDE_DECK_WIDTH_MIN_MM[cat]
    assert A.deck_min_width_m(A.DeckKind.SIDE_DECK, "C")[0] > \
        A.deck_min_width_m(A.DeckKind.SIDE_DECK, "D")[0]

    top, bottom = E.COCKPIT_FOOTWELL_TAPER_MM.value
    need, _ = A.deck_min_width_m(A.DeckKind.COCKPIT, "C")
    assert need == pytest.approx(top / 1e3), \
        "the rectangle has to clear the WIDER of the taper's two widths"
    assert A.deck_min_width_m(A.DeckKind.COCKPIT, "D")[0] == pytest.approx(need)

    assert A.deck_min_width_m(A.DeckKind.FOREDECK, "C") is None
    assert A.deck_min_width_m(A.DeckKind.AFTDECK, "C") is None


# ============================================ the envelope, and two more defects


def test_the_trunk_is_a_step_and_is_never_interpolated_across(hull, env):
    """DEFECT (found 2026-08-07, `Envelope.overhead_z`): the coachroof height
    was added to a per-station array and the array was then INTERPOLATED at the
    two ends of a run — smearing a vertical step over one station spacing.

    MEASURED on the reference layout: the head runs 1.35-2.15 m, the coachroof
    starts at 1.30 m, so the head is 50 mm inside the trunk from end to end.
    Interpolating between station 1.25 (no trunk, 1.000 m) and station 1.50
    (trunk, 1.735 m) returned **1.294 m**. The head then reported a height of
    **1619 mm** against the 1905 mm compromise-headroom floor and L0-A FAILED
    the reference layout on an overhead that exists nowhere on the vessel —
    neither the sheer nor the coachroof, but 40% of the way between them.

    The invariant that replaces it: over a run entirely under the trunk, the
    overhead is exactly the bare-hull overhead plus the trunk height; over a
    run that leaves it, the trunk buys nothing at all.
    """
    bare = A.Envelope.from_hull(hull)
    t = env.trunk
    assert t is not None and t.height > 0

    inside = (t.x0 + 0.05, t.x0 + 0.85)
    assert env.overhead_z(*inside) == pytest.approx(
        bare.overhead_z(*inside) + t.height)
    # ... including a run that contains no station at all.
    tiny = (t.x0 + 0.02, t.x0 + 0.06)
    assert env.overhead_z(*tiny) == pytest.approx(
        bare.overhead_z(*tiny) + t.height)

    straddle = (t.x0 - 0.20, t.x0 + 0.80)
    assert env.overhead_z(*straddle) == pytest.approx(
        bare.overhead_z(*straddle)), "a box crossing the edge gets the sheer"

    # The consequence, at the gate: the head clears standing headroom.
    head = next(s for s in A.reference_layout(hull).spaces if s.id == "head")
    assert head.box.dz == pytest.approx(2.060, abs=1e-3)
    assert head.box.dz > A.min_dims_m(A.Function.HEAD)["height"]


def test_the_search_bounds_contain_the_layout_they_are_meant_to_contain(ref, env):
    """DEFECT (found 2026-08-07, `Arrangement.bounds`): the upper z bound was
    `overhead_z(0, LWL)`, which is the LOWEST overhead anywhere — 1.000 m on
    this hull. Four of the reference layout's own spaces have ceilings at
    1.735 m under the coachroof, so the search box excluded the fixture the
    gate is defined by, and V2.3's CP+GA would have been unable to express it.

    `bounds()` bounds the SEARCH, not feasibility (the hull is not a cuboid),
    but a bound a known-good point violates is simply wrong.
    """
    lo, hi = ref.bounds()
    v = ref.to_vector()
    assert lo.shape == hi.shape == v.shape
    assert np.all(hi >= lo)

    bad = [(n, float(x), float(a), float(b))
           for n, x, a, b in zip(ref.slot_names(), v, lo, hi)
           if not (a - 1e-9 <= x <= b + 1e-9)]
    assert bad == [], f"the reference layout is outside its own bounds: {bad}"

    assert env.overhead_max_z > env.overhead_z(0.0, env.lwl), \
        "the highest overhead and the lowest are not the same number here"
    # The highest overhead is NOT sheer_max + trunk height: the sheer peaks at
    # the stem (1.279 m) where the coachroof does not reach, and the coachroof
    # peaks at its own forward end (1.031 + 0.735 = 1.766 m). Two different
    # stations, which is exactly why the profile is built before it is reduced.
    t = env.trunk
    profile = np.where((env.x >= t.x0) & (env.x <= t.x1),
                       env.z_sheer + t.height, env.z_sheer)
    assert env.overhead_max_z == pytest.approx(float(profile.max()))
    assert env.overhead_max_z > float(env.z_sheer.max())


def test_the_envelope_reports_what_it_extracted_and_what_it_assumed(env, hull):
    """The trunk is DECLARED, not measured, and the split is reported.

    The hull grammar emits a flush deck at the sheer, so standing headroom on a
    10 m boat comes from a coachroof this platform does not generate. That is
    an honest gap and it is labelled as one — but only if the assumed volume
    stays separable from the extracted volume, which is what this asserts.
    """
    assert env.trunk_volume_m3 > 0.0
    assert env.interior_volume_m3 > env.trunk_volume_m3
    bare = A.Envelope.from_hull(hull)
    assert bare.trunk_volume_m3 == 0.0
    assert env.interior_volume_m3 == pytest.approx(
        bare.interior_volume_m3 + env.trunk_volume_m3)
    # A fifth of this interior is assumed. Worth saying out loud.
    assert 0.10 < env.trunk_volume_m3 / env.interior_volume_m3 < 0.30

    # The sole is the chine plane at the maximum-beam station — a geometric
    # statement about this grammar, not a number, so it is checked as one.
    i_mb = int(np.argmax(hull.y_chine))
    assert env.sole_z == pytest.approx(float(hull.z_chine[i_mb]))
    assert env.sole_clear_width_m >= E.SOLE_MIN_CLEAR_WIDTH_MM.value / 1e3


def test_the_accommodation_run_is_measured_not_remembered(env):
    """MEASURED 2026-08-07 on the 10 m reference hull: (0.00, 8.50) m.

    The docstring claimed (0.00, 9.20) — 800 mm off the bow — until the module
    was executed for the first time. It is 1.50 m. A measurement beats a
    document; this test is what keeps the document honest from now on.
    """
    x0, x1 = env.accommodation_x
    assert (x0, x1) == pytest.approx((0.0, 8.5), abs=0.02)
    assert env.lwl - x1 == pytest.approx(1.5, abs=0.02)
    # It ends where the sole stops being wide enough to stand on, so the
    # V-berth and the forepeak are forward of it and sit on platforms.
    for sid in ("berth.fwd", "stowage.fwd"):
        s = next(s for s in A.reference_layout().spaces if s.id == sid)
        assert s.box.x1 > x1
        assert s.box.z0 > env.sole_z, "forward of the accommodation, on a platform"


def test_an_envelope_with_no_interior_is_refused_rather_than_reported_empty(hull):
    """The construction guard. It is not one of L0-A's rules and must not be
    counted as one — it cannot fire inside the hull grammar's own parameter
    space — but `Envelope` is public and nothing stops a caller reaching it.

    Driven here by an absurd panel thickness, which is the one input that
    shrinks the interior without leaving the grammar.
    """
    with pytest.raises(ValueError, match="no interior"):
        A.Envelope.from_hull(hull, panel_thickness_m=1.60)


def test_a_v_berth_that_does_not_fit_is_refused_at_construction(hull):
    """DEFECT (found 2026-08-07, `reference_layout`): the first authored layout
    put the V-berth at 0.705-0.915 LWL and `reference_layout()` raised
    'this hull is too fine forward to carry a V-berth' on the very hull it is
    written for. The module had never been executed.

    A berth is a BOX, so its width is the hull's half-breadth at its
    FORWARD-most station, and at 0.915 LWL that is 0.617 m against the 0.8125 m
    a 1525 mm double needs. The refusal itself is correct and is kept: a layout
    that silently produced a 1.2 m 'double' would be worse. What changed is the
    station, to 0.870 LWL, and the test asserts both — that the shipped berth
    clears the double-berth floor, and that the old station still cannot.
    """
    env = A.Envelope.from_hull(hull, trunk=A.reference_trunk(hull))
    want_half = 0.5 * E.DOUBLE_BERTH_WIDTH_MIN_MM.value / 1e3 + 0.05

    L = env.lwl
    assert env.lowest_z_for_half_breadth(0.705 * L, 0.915 * L, want_half) is None
    assert env.min_half_breadth(0.915 * L, 0.915 * L, 0.4) < want_half

    berth = next(s for s in A.reference_layout(hull).spaces if s.id == "berth.fwd")
    assert berth.box.dy >= E.DOUBLE_BERTH_WIDTH_MIN_MM.value / 1e3
    assert berth.box.plan_long >= E.BERTH_LENGTH_MIN_MM.value / 1e3
    # It sits on a platform above the sole, which is geometry and not taste:
    # the forefoot lifts the keel above the sole plane forward.
    assert berth.box.z0 > env.sole_z


# ================================================ adjacency is carried, not gated


def test_adjacency_preferences_are_carried_and_never_checked(ref):
    """BuildPlan2 §1.5: adjacency and separation are ISA's SOFT constraints,
    the objective V2.3's GA optimises. A soft preference enforced as a hard
    gate is a gate nobody can satisfy — the reference layout itself declares
    machinery AVOID saloon while both sit in a 10 m hull.

    So: the preferences exist, they name real nodes, they survive the vector
    bridge, and L0-A has nothing to say about them even when they are
    self-contradictory.
    """
    ids = {s.id for s in ref.spaces} | {d.id for d in ref.deck_zones}
    pairs = [(s.id, other, kind)
             for s in ref.spaces for other, kind in s.adjacency]
    assert pairs, "the reference layout declares no adjacency at all"
    assert {k for _, _, k in pairs} == set(A.Adjacency), \
        "both PREFER and AVOID are exercised"
    for src, other, _ in pairs:
        assert other in ids, f"{src} prefers/avoids {other!r}, which does not exist"
        assert other != src

    # Contradict one outright and L0-A stays silent.
    contradictory = _with_space(
        ref, "galley",
        adjacency=(("saloon", A.Adjacency.PREFER),
                   ("saloon", A.Adjacency.AVOID)))
    assert A.check_l0a(contradictory).ok
    assert not any("adjacen" in v.rule.lower() or "adjacen" in v.detail.lower()
                   for v in A.check_l0a(_broken_layouts(
                       ref, ref.envelope)[A.R_OVERLAP]).violations)


def test_min_dims_m_exposes_exactly_the_numbers_the_gate_applies(env):
    """`min_dims_m` is what a UI, a test or V2.2 will read. If it drifted from
    what `check_l0a` compares against, the interface would advertise one floor
    and the gate would enforce another — the number-declared-twice defect with
    a function call in between.

    Driven by a deliberately absurd 50 mm cube per function, so EVERY floor
    that exists fires and its `required` can be read straight off the row.
    """
    tiny = []
    for i, f in enumerate(A.Function):
        x0 = 1.0 + 0.5 * i
        tiny.append(A.Space(f"tiny.{f.value}", f,
                            A.Box(x0, x0 + 0.05, -0.025, 0.025,
                                  env.sole_z, env.sole_z + 0.05),
                            mass_kg=1.0, sigma_kg=0.2))
    rep = A.check_l0a(A.Arrangement(envelope=env, spaces=tuple(tiny)))

    for f in A.Function:
        want = {v for v in A.min_dims_m(f).values() if v is not None}
        got = {v.required for v in rep.by_rule(A.R_MIN_DIMS)
               if v.subject == f"tiny.{f.value}"}
        assert got == want, (
            f"{f.value}: gate applied {sorted(got)}, table advertises "
            f"{sorted(want)}")


def test_a_space_that_stands_above_the_sheer_is_measured_against_the_coachroof(
        ref, env):
    """DEFECT (found 2026-08-07, `check_l0a` + `Envelope.min_half_breadth`):
    the envelope-Y rule was evaluated at the box FLOOR only, on the argument
    that 'a section's half-breadth is non-decreasing upward, so the bottom of a
    box is always its tightest level'. True of the hull. Not true of the boat.

    Above the sheer this hull has no topsides at all — the grammar emits a
    flush deck — and the only volume up there is the DECLARED coachroof, which
    is narrower than the sheer by a side deck each side. Two things then went
    wrong at once: `geometry._halfbreadth_at` returns the sheer half-breadth
    for any z above the sheer (it extends the topsides upward forever), and the
    check never looked at that level anyway.

    MEASURED on the reference layout, which L0-A PASSED: the saloon, the galley
    and the head all stood 735 mm above the sheer, with half-beams of
    1.399 / 1.248 / 1.128 m against a 0.964 m coachroof. The saloon protruded
    435 mm through the side of the coachroof, each side, over its whole height.
    The gate's own fixture was not a buildable boat, and 'fits in the envelope'
    is one of the three rule families L0-A exists to enforce.
    """
    t = env.trunk
    # The mechanism, stated as a fact about the geometry kernel: above the
    # sheer the hull query does NOT go to zero.
    above = float(env.z_sheer.min()) + 0.30
    assert env.min_half_breadth(3.0, 4.0, above) > 1.0
    assert env.available_half_breadth(3.0, 4.0, above) == pytest.approx(
        t.half_width)
    # ... and outside the coachroof's run there is nothing up there at all.
    assert env.available_half_breadth(t.x1 + 0.5, t.x1 + 1.0,
                                      float(env.z_sheer.max()) + 0.05) == 0.0

    # As shipped, every space fits at its ceiling as well as at its floor.
    for s in ref.spaces:
        assert s.box.half_beam <= env.available_half_breadth(
            s.box.x0, s.box.x1, s.box.z1) + A.TOUCH_TOL_M, s.id

    # The control: widen the saloon back out to the hull's beam and it is
    # refused — at its CEILING, and the row says so.
    saloon = next(s for s in ref.spaces if s.id == "saloon").box
    wide = dataclasses.replace(saloon, y0=-1.399, y1=1.399)
    # It still fits at the floor, which is why the old check passed it.
    assert env.available_half_breadth(saloon.x0, saloon.x1, saloon.z0) > 1.399
    rep = A.check_l0a(_with_space(ref, "saloon", box=wide))
    hits = rep.by_rule(A.R_ENVELOPE_Y)
    assert [v.subject for v in hits] == ["saloon"], rep.messages
    assert "ceiling" in hits[0].detail
    assert hits[0].required == pytest.approx(t.half_width)

    # And a space that keeps the same width but stops BELOW the sheer is fine
    # — the rule is about height, not about width alone.
    short = dataclasses.replace(wide, z1=float(env.z_sheer.min()) - 0.05)
    assert A.check_l0a(_with_space(ref, "saloon", box=short)).by_rule(
        A.R_ENVELOPE_Y) == ()


def test_an_unknown_design_category_is_named_not_defaulted(ref):
    """`Arrangement.category` is a free-form string with a default, so a typo
    reaches the ISO table. It used to raise a bare `KeyError` from six frames
    inside `check_l0a`; it now says which categories exist.

    What it must NOT do is fall back to one. Defaulting would apply cat D's
    100 mm side-deck floor to a cat A boat and pass it — a quiet wrong number
    wearing a standard's name.
    """
    with pytest.raises(ValueError, match="unknown design category"):
        A.deck_min_width_m(A.DeckKind.SIDE_DECK, "Z")
    with pytest.raises(ValueError, match="unknown design category"):
        A.check_l0a(dataclasses.replace(ref, category="c"))
