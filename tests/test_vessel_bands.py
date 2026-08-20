"""Gate PV-B — A BAND IS A RULE ABOUT AN OBJECT, AND THE OBJECT HAS A TYPE.

THE INCIDENT THIS FILE IS THE FENCE FOR, measured 2026-08-14 at the tip of
`master`. This project's own target — a catamaran with 12.0 m x 0.8 m demihulls
— was refused by `grammar.check` on three clauses before a line of physics ran:

    bound[BWL]: 0.8 outside [1.2, 6.0]
    L/B: 15.00 outside [2.2, 8.5]
    B/T: 1.33 outside [1.8, 12.0]

The narrowest 12 m hull the grammar could express was 1.42 m (L/B 8.45). NONE
OF THOSE BANDS WAS WRONG — a 12 m MONOHULL 0.8 m wide would capsize — and the
fix is therefore not to widen them. They were being applied to the wrong
OBJECT. The same error surfaced three times in one day (this band; the ISO GM
floor rejecting slender hulls; `gate2m.py` printing KCS's EFD figure over a
Wigley hull), which is one missing concept wearing three costumes, not three
bugs.

The tests below are ordered as the argument is, and the FIRST one is the one
that matters most: the monohull bar did not move.

A SECOND, OPPOSITE HOLE IS FENCED HERE TOO, and it is the more dangerous of the
pair. The L/B band was a correct rule REFUSING a safe hull. A GM floor applied
to a catamaran is a monohull criterion the catamaran passes TRIVIALLY while
remaining capsizable — a rule ADMITTING an unassessed one. Blocking a safe boat
costs a design; admitting a dangerous one costs more, so `test_a_multihull_*`
below asserts that a catamaran cannot be signed off on a GM floor.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from navalai import formlib, grammar
from navalai.limits import (MULTIHULL_CRITERION_INPUTS_MISSING,
                            MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG,
                            MULTIHULL_RIGHTING_CRITERIA,
                            MULTIHULL_STABILITY_UNASSESSED, RE_TRANSITION_BAND,
                            HullRole, StabilityCriterion,
                            friction_line_validity, hull_role,
                            min_lwl_for_turbulent_flow_m, stability_criterion)

# The owner's target, as three numbers, in ONE place in this file.
TARGET_LWL_M = 12.0
TARGET_BWL_M = 0.8
TARGET_DRAFT_M = 0.6            # B/T 1.333 — BELOW the sourced floor


def _hull(lwl: float, bwl: float, t: float, d: float | None = None,
          **over: float) -> np.ndarray:
    """A parameter vector that is feasible on every clause except, possibly,
    the proportion clauses this file is about.

    The shape genes are pinned to a known-buildable set rather than to the box
    midpoint, so that a failure here is always about L/B, B/T or a bound and
    never about `panel.twist` wandering when the box moved.
    """
    if d is None:
        d = max(t + 0.30, t + grammar.MIN_FREEBOARD_FRAC_LWL * lwl) + 0.02
    p = dict(LWL=lwl, BWL=bwl, T=t, D=d, Cp=0.575, lcb=0.0, x_mb=0.55,
             r_transom=0.20, beta_mid=8.0, beta_bow=20.0, beta_len=0.35,
             roundness=0.0, rocker=0.05, forefoot=0.30, flare=5.0,
             sheer_rise=0.10)
    p.update(over)
    return grammar.vector(p)


def _clauses(rep: grammar.GateReport) -> set[str]:
    return {v.split(":")[0] for v in rep.violations}


# ===================================================================== 1. the
# ================================================== bar that must NOT have moved

def test_a_12x0p8_m_MONOHULL_IS_STILL_REFUSED_ON_THE_SAME_CLAUSE():
    """THE LOAD-BEARING TEST OF THIS CHANGE.

    Widening a band to make a target fit is the move honesty rule 6 forbids,
    and it is indistinguishable from this change UNLESS the monohull verdict is
    pinned. So: the same dimensions, judged as a monohull, are refused on the
    same clause, and the message still carries the same two numbers.
    """
    rep = grammar.check(_hull(TARGET_LWL_M, TARGET_BWL_M, TARGET_DRAFT_M))
    assert not rep.ok, (
        "a 12.0 x 0.8 m MONOHULL became feasible. The demihull row was "
        "supposed to be a SECOND band, not a wider one.")
    assert "L/B" in _clauses(rep)
    joined = " | ".join(rep.violations)
    assert "L/B 15.00" in joined, joined
    assert "[2.2, 8.5]" in joined, (
        f"the monohull L/B band no longer prints [2.2, 8.5]: {joined}")
    assert "monohull" in joined, (
        "the refusal does not say WHICH object it judged, which is the whole "
        "content of the 2026-08-14 finding")


def test_the_MONOHULL_bands_are_byte_for_byte_what_they_were():
    """A regression fence with the literal values in it ON PURPOSE.

    Everywhere else in this repository a literal beside a symbol is the
    number-declared-twice defect. Here it is the point: these four digits are
    the thing that must not move, and a test that read them from the module it
    is testing would pass no matter what they became.
    """
    assert grammar.L_OVER_B_BAND == (2.2, 8.5)
    assert grammar.B_OVER_T_BAND == (1.8, 12.0)
    assert grammar.PROPORTION_BANDS[HullRole.MONOHULL]["L/B"][0] == (2.2, 8.5)
    assert grammar.PROPORTION_BANDS[HullRole.MONOHULL]["B/T"][0] == (1.8, 12.0)


def test_an_ungoverned_call_is_judged_exactly_as_a_monohull():
    """`check(x)` with no vessel must be the old gate, clause for clause.

    Defaulting the other way would have loosened the bar for every caller in
    the tree at once — `evaluate`, `optimize`, the sampler, the surrogate's
    domain — which is the mirror image of the defect being fixed.
    """
    for lwl, bwl, t in ((12.0, 0.8, 0.6), (12.0, 1.5, 0.5), (8.0, 2.0, 0.4)):
        x = _hull(lwl, bwl, t)
        assert (grammar.check(x).violations
                == grammar.check(x, HullRole.MONOHULL).violations)
    assert hull_role(None) is HullRole.MONOHULL


# ================================================================== 2. the new
# ============================================================== demihull row

def test_the_owners_12x0p8_m_DEMIHULL_IS_ACCEPTED():
    """THE HEADLINE. The slenderness the mission asks for is expressible.

    At a draft the sources support: B/T >= 1.50 means T <= 0.533 m on a 0.8 m
    beam. The 0.6 m draft is a separate finding and has its own test below —
    keeping them apart is the point, because they fail for opposite reasons.
    """
    t = TARGET_BWL_M / formlib.SOTON_DEMIHULL_B_OVER_T.low
    rep = grammar.check(_hull(TARGET_LWL_M, TARGET_BWL_M, t * 0.99),
                        HullRole.DEMIHULL)
    assert rep.ok, f"the target demihull is still refused: {rep.violations}"


def test_the_demihull_bands_are_the_UNION_and_the_union_is_CONTIGUOUS():
    """A band assembled by min/max over two intervals is a lie if they do not
    overlap: the hole between them would be admitted silently. Both unions here
    do overlap (L/B at 7.00-8.50, B/T at 1.80-2.50) and this asserts it, so a
    later edit to either contributor cannot open a gap without failing.
    """
    for name, mono, series, union in (
            ("L/B", grammar.L_OVER_B_BAND, formlib.SOTON_DEMIHULL_L_OVER_B,
             grammar.L_OVER_B_BAND_DEMIHULL),
            ("B/T", grammar.B_OVER_T_BAND, formlib.SOTON_DEMIHULL_B_OVER_T,
             grammar.B_OVER_T_BAND_DEMIHULL)):
        assert mono[0] <= series.high and series.low <= mono[1], (
            f"{name}: the monohull band {mono} and the series envelope "
            f"{series} no longer overlap, so their min/max union {union} "
            f"contains a range NO source covers")
        assert union == (min(mono[0], series.low), max(mono[1], series.high))


def test_the_demihull_ceiling_IS_the_Southampton_number_and_not_a_copy_of_it():
    """`grammar` must IMPORT the band, never restate it.

    A literal 15.10 here beside a comment naming Southampton is this
    repository's signature defect with the second copy laundered into a
    citation — which is exactly what `formlib.Basis.DRAWING`'s docstring
    already fences INSIDE formlib and could not fence from outside it.
    """
    assert (grammar.L_OVER_B_BAND_DEMIHULL[1]
            == formlib.SOTON_DEMIHULL_L_OVER_B.high)
    assert (grammar.B_OVER_T_BAND_DEMIHULL[0]
            == formlib.SOTON_DEMIHULL_B_OVER_T.low)
    # and the public name is the SAME OBJECT as the citation block, so the
    # SECONDARY caveat `tests/test_formlib.py` guards travels with it.
    assert formlib.SOTON_DEMIHULL_L_OVER_B is formlib._SOTON_L_OVER_B
    assert formlib.SOTON_DEMIHULL_B_OVER_T is formlib._SOTON_B_OVER_T
    assert "SECONDARY" in formlib.SOTON_DEMIHULL_L_OVER_B.source


def test_the_demihull_L_over_B_ceiling_is_NOT_DTMB_Series_64s():
    """Series 64 reaches L/B 18.26 and CORROBORATES; it does not band.

    Taking a MONOHULL series' ceiling for a demihull would be the same category
    error as the monohull ceiling that started this, pointed the other way. The
    refusal to use the looser available number is the honest half of the change
    and is fenced so a later session cannot quietly reach for it.
    """
    assert (formlib.S64_MONOHULL_L_OVER_B.high
            > grammar.L_OVER_B_BAND_DEMIHULL[1]), (
        "Series 64 no longer offers a looser ceiling, so this test has lost "
        "its subject — check why before deleting it")
    assert grammar.L_OVER_B_BAND_DEMIHULL[1] != formlib.S64_MONOHULL_L_OVER_B.high


# ============================================== 3. what was REFUSED, and why it
# ============================================== says so out loud

def test_the_targets_own_DRAFT_is_still_refused_and_the_refusal_NAMES_THE_GAP():
    """B/T 1.333 is BELOW the Southampton floor of 1.50.

    THE SOURCES DO NOT SUPPORT THE NUMBER THE OWNER ASKED FOR, so the number is
    not invented. What changes is that the refusal stops pretending a bar
    exists and says the evidence is missing — and it refuses on DRAFT, not on
    slenderness, which is a different sentence from the one that started this.
    """
    rep = grammar.check(_hull(TARGET_LWL_M, TARGET_BWL_M, TARGET_DRAFT_M),
                        HullRole.DEMIHULL)
    assert not rep.ok
    assert _clauses(rep) == {"B/T"}, (
        f"the target demihull should now fail on DRAFT ALONE: {rep.violations}")
    msg = rep.violations[0]
    assert "OUT OF SOURCED RANGE" in msg, msg
    assert "Southampton" in msg, msg
    assert "SECONDARY" in msg, (
        "the refusal quotes the Southampton floor without carrying the caveat "
        "that the report itself could not be opened")
    assert "1.33" in msg and "1.5" in msg, msg


def test_the_sourced_range_note_fires_ONLY_below_a_series_floor():
    """LESSONS.md #3: prove the guard is not always-on.

    A message that appears on every refusal carries no information. Above the
    ceiling, and for a monohull, the ordinary refusal must be the one printed.
    """
    above = grammar.check(_hull(4.0, 3.0, 0.20), HullRole.DEMIHULL)   # B/T 15
    assert "B/T" in _clauses(above)
    assert grammar.OUT_OF_SOURCED_RANGE not in " ".join(above.violations)
    mono = grammar.check(_hull(TARGET_LWL_M, TARGET_BWL_M, TARGET_DRAFT_M))
    assert grammar.OUT_OF_SOURCED_RANGE not in " ".join(mono.violations)


# ================================================================ 4. the box

def test_every_box_edge_is_sourced_or_derived_and_the_floors_cannot_bind_first():
    """THE RULE THE BOX IS SET BY: a bound with no naval-architecture content
    must not refuse a hull that a SOURCED band accepts.

    The BWL floor of 1.2 m did exactly that — it refused the owner's 0.8 m
    demihull before the L/B band got to speak — so the floors are now DERIVED
    from the bands and this asserts the derivation still holds.
    """
    box = {n: (lo, hi) for n, _u, lo, hi, _d in grammar.PARAMS}
    lwl_lo, lwl_hi = box["LWL"]
    # SOURCED: Directive 2013/53/EU Art. 3(2), hull length 2,5 m to 24 m.
    assert (lwl_lo, lwl_hi) == (2.5, 24.0)
    lb_max = max(b["L/B"][0][1] for b in grammar.PROPORTION_BANDS.values())
    bt_max = max(b["B/T"][0][1] for b in grammar.PROPORTION_BANDS.values())
    # the narrowest hull ANY band admits at the shortest length must be inside
    assert box["BWL"][0] <= lwl_lo / lb_max + 1e-12, (
        f"the BWL floor {box['BWL'][0]:.4g} binds before the L/B ceiling "
        f"{lb_max} does at LWL {lwl_lo} m — the 2026-08-14 defect, restored")
    assert box["T"][0] <= box["BWL"][0] / bt_max + 1e-12
    assert box["D"][0] <= box["T"][0] + grammar.MIN_FREEBOARD_ABS_M + 1e-12
    # SOURCED ceilings: the drawn dimension table's largest per-hull figures.
    drawn = formlib.DRAWN_DIMENSION_RANGES["large monohull"]
    assert box["BWL"][1] == drawn["beam_m"].high
    assert box["T"][1] == drawn["draft_m"].high


def test_the_box_admits_the_target_beam_that_it_used_to_refuse():
    """The specific measured refusal, inverted."""
    lo, hi = next((lo, hi) for n, _u, lo, hi, _d in grammar.PARAMS
                  if n == "BWL")
    assert lo <= TARGET_BWL_M <= hi, (
        f"BWL {TARGET_BWL_M} m is outside [{lo}, {hi}] again")
    rep = grammar.check(_hull(TARGET_LWL_M, TARGET_BWL_M, 0.50),
                        HullRole.DEMIHULL)
    assert "bound[BWL]" not in _clauses(rep)


def test_the_widened_box_still_yields_samples_at_a_measured_rate():
    """Widening a box is not free and the cost is recorded, not assumed.

    MEASURED 2026-08-14 over 4000 uniform draws at seed 1: 13.2% passed in the
    old box, 6.7% pass as a monohull and 9.6% as a demihull in the new one.
    `sample()` allows 200 tries per sample, so 6.7% leaves ~13x of headroom.
    The bar here is deliberately far below the measurement — it exists to catch
    a COLLAPSE, not to pin a statistic that legitimately drifts when any other
    clause changes.
    """
    rng = np.random.default_rng(1)
    x = rng.uniform(grammar.LOW, grammar.HIGH, size=(1500, grammar.N_PARAMS))
    rate = sum(grammar.check(row).ok for row in x) / len(x)
    assert rate > 0.02, (
        f"uniform-in-box yield collapsed to {rate:.4f}; `sample()` and "
        f"`evaluate.sample_valid` rejection-sample this box")


# ============================================ 5. WHICH STABILITY CRITERION, and
# ============================================ the one that is refused

def test_topology_selects_the_criterion_and_a_multihull_gets_the_unimplemented_one():
    assert stability_criterion(None) is StabilityCriterion.MONOHULL_GM_FLOOR
    assert stability_criterion(None).implemented
    multi = stability_criterion(HullRole.DEMIHULL)
    assert multi is StabilityCriterion.MULTIHULL_RIGHTING_CURVE
    assert not multi.implemented, (
        "a multihull righting-curve criterion is now claimed as IMPLEMENTED. "
        "If that is true it needs a GZ(phi) curve, a downflooding ANGLE and a "
        "windage area — see limits.MULTIHULL_CRITERION_INPUTS_MISSING — and "
        "this test should be replaced by one that checks the criterion, not "
        "deleted.")


def test_a_multihull_is_REFUSED_a_stability_verdict_not_granted_one():
    """THE SAFETY HALF, and it points the opposite way from the L/B band.

    A catamaran's parallel-axis A_wp*d^2 term makes GM enormous, so it clears
    any GM floor by a wide margin AND CAN STILL CAPSIZE AND STAY INVERTED. The
    ladder must not report `R-GM PASS` for one: an unmeasured quantity scored
    as a passing one is this project's defect class 1, and here it would be a
    green tick on a vessel nobody assessed.

    Built as a hand-made `Evaluation` rather than through `evaluate()`, so this
    test owns none of the multihull hydrostatics landing concurrently in
    `hydrostatics.py` / `evaluate.py`.
    """
    from navalai.rules import report
    from navalai.rules.iso12217 import assess

    class _Hydro:
        freeboard_min = 1.0
        disp_kg = 6000.0
        lwl_eff = 12.0

    class _Ev:
        hydro = _Hydro()
        gm_m = 9.0            # a catamaran GM: vastly over any monohull floor
        hull_lwl_m = 12.0
        vessel: dict = {}

    mono = _Ev()
    mono.vessel = {"n_hulls": 1}
    cat = _Ev()
    cat.vessel = {"n_hulls": 2, "separation_over_lwl": 0.30}

    ids_mono = {f.rule_id for f in assess(mono, "C", 2, 2.0)}
    cat_findings = assess(cat, "C", 2, 4.0)
    ids_cat = {f.rule_id for f in cat_findings}

    assert "R-GM" in ids_mono, "the monohull path lost its GM floor"
    assert "R-GM" not in ids_cat, (
        "a catamaran was handed an R-GM finding. GM is the MONOHULL criterion "
        "and a catamaran passes it trivially while remaining capsizable — "
        "emitting it puts a green tick on the quantity that does not govern")
    assert "R-MHS" in ids_cat
    mhs = next(f for f in cat_findings if f.rule_id == "R-MHS")
    assert mhs.basis == "approx"

    # WHICH R-MHS THIS IS DEPENDS ON MANNING, and that is the 2026-08-19
    # design rather than a loophole. ISO 12217-1 cl 6.6 binds HABITABLE
    # multihulls, so a liveaboard still gets the refusal; a crewed or
    # uncrewed multihull's stability verdict is COMPUTED by the ladder (NZ
    # Part 40A App.1 cl 1.3 under 15 m, cl 1.4 on declared windage above
    # it) and R-MHS is a RECEIPT pointing at it. This fixture declares no
    # manning, so it takes the receipt path.
    #
    # The test used to assert `not mhs.passed` unconditionally, which was
    # correct for the blanket-refusal design it was written against and
    # would now demand a false refusal on a vessel the ladder has actually
    # judged (MEASURED on the 10 m catamaran of test_physical_form case c:
    # cl 1.3 heel 0.77 deg, trim 0.93 deg against an 8 deg bar, passes).
    #
    # WHAT IS FENCED INSTEAD is that a receipt must NAME where the verdict
    # lives. A receipt that passes while pointing nowhere is the silent
    # pass, and MEASURED 2026-08-20 that state was reachable: an 18 m
    # catamaran with no declared windage fell through both clauses and came
    # back with cl13 None, cl14 None and no violation. That hole is closed
    # in navalai/evaluate.py and fenced in test_physical_form.
    if mhs.passed:
        assert "cl13" in mhs.note or "cl14" in mhs.note, (
            "R-MHS passed as a receipt without naming the criterion that "
            "carries the verdict — a pointer to nowhere is a silent pass: "
            + mhs.note)
        assert "not a" in mhs.note or "ladder" in mhs.note
    else:
        assert "RCD 2013/53/EU" in mhs.clause and "6.6" in mhs.clause
        assert MULTIHULL_STABILITY_UNASSESSED in mhs.note
        assert not report(cat_findings)["pass"]
        assert abs(mhs.measured - mhs.required) / abs(mhs.required) == 1.0

    # AND THE HABITABLE PATH MUST STILL REFUSE — the clause that has not
    # been replaced by a computed criterion.
    live = _Ev()
    live.vessel = {"n_hulls": 2, "separation_over_lwl": 0.30,
                   "manning": "liveaboard"}
    live_findings = assess(live, "C", 2, 4.0)
    live_mhs = next(f for f in live_findings if f.rule_id == "R-MHS")
    assert not live_mhs.passed, (
        "a LIVEABOARD multihull is exactly what ISO 12217-1 cl 6.6 binds, "
        "and this tree does not hold cl 6.6.1's governing text — it must "
        "still refuse rather than issue a receipt")
    assert MULTIHULL_STABILITY_UNASSESSED in live_mhs.note


def test_the_multihull_refusal_names_its_missing_evidence_rather_than_gesturing():
    """"Not implemented" is only honest if it says what is missing.

    Three FREE criteria exist and every one of them needs a righting-arm curve
    this ladder does not compute — that distinction (missing COMPUTATION, not
    missing DOCUMENT) is the useful half of the finding and it must survive.
    """
    assert len(MULTIHULL_RIGHTING_CRITERIA) >= 3
    regulators = " | ".join(name for name, _why in MULTIHULL_RIGHTING_CRITERIA)
    for expected in ("MCA Workboat", "NSCV", "Part 40A"):
        assert expected in regulators, f"{expected} vanished from {regulators}"
    for _name, why in MULTIHULL_RIGHTING_CRITERIA:
        assert len(why) > 80, "a criterion recorded without saying what it is"
    assert any("GZ" in m for m in MULTIHULL_CRITERION_INPUTS_MISSING)
    assert "GM" in MULTIHULL_STABILITY_UNASSESSED


def test_a_multihull_offset_load_bar_is_the_STRICTER_of_two_and_it_BITES():
    """The one multihull bar that IS computable from what this ladder has.

    Maritime NZ Part 40A App. 1 cl. 1.3/1.1 caps multihull crowding heel at
    8 deg. At LH = 12 m ISO Table 4 allows 14.82 deg, so this is 1.8x stricter
    on exactly the vessel the product line is built around — i.e. it is a real
    constraint and not a decorative row.
    """
    from navalai.rules.iso12217 import assess, offset_load_heel_limit_deg

    iso_at_12 = offset_load_heel_limit_deg(12.0)
    assert iso_at_12 == pytest.approx(14.82, abs=0.01)
    assert MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG < iso_at_12

    class _Hydro:
        freeboard_min = 1.0
        disp_kg = 6000.0
        lwl_eff = 12.0

    class _Ev:
        hydro = _Hydro()
        gm_m = 9.0
        hull_lwl_m = 12.0
        vessel = {"n_hulls": 2, "separation_over_lwl": 0.30}

    olh = next(f for f in assess(_Ev(), "C", 2, 4.0) if f.rule_id == "R-OLH")
    assert olh.required == MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG
    assert "Maritime NZ" in olh.clause and "ISO 12217-1" in olh.clause


# ================================== 6. widening the box exposes hulls the
# ================================== physics cannot score, and they must be named

def test_a_short_hull_leaves_the_friction_models_regime_and_it_is_MEASURED():
    """WIDENING THE BOX IS ONLY HONEST IF THE LADDER REFUSES WHAT IT CANNOT
    SCORE. `resistance` already does this at the TOP end (`FN_MICHELL_MAX`,
    badge `L1-INVALID`, ranked below `L0`). There was nothing at the bottom.

    MEASURED at `resistance.NU_FRESH_15C` = 1.14e-6 m2/s: a 1.0 m hull at 2 kn
    is Re 9.03e5 — inside the laminar-turbulent transition, where ITTC-57 (a
    FULLY TURBULENT correlation line) is not valid — and at 3 kn it is Fn 0.493,
    already over `FN_MICHELL_MAX`. There is no speed at which both halves of
    `total_resistance` are inside their envelopes. A 12 m hull at 6 kn is
    Fn 0.284 / Re 3.25e7 and is comfortable in both.
    """
    from navalai.resistance import FN_MICHELL_MAX, NU_FRESH_15C

    kn = 0.514444
    def re(lwl, knots):
        return knots * kn * lwl / NU_FRESH_15C
    def fn(lwl, knots):
        return knots * kn / math.sqrt(9.80665 * lwl)

    assert re(1.0, 2.0) == pytest.approx(9.03e5, rel=0.01)
    assert not friction_line_validity(re(1.0, 2.0))[0]
    assert "transition" in friction_line_validity(re(1.0, 2.0))[1]
    assert fn(1.0, 3.0) > FN_MICHELL_MAX          # the other envelope, already on
    assert re(12.0, 6.0) == pytest.approx(3.25e7, rel=0.01)
    assert friction_line_validity(re(12.0, 6.0))[0]
    assert friction_line_validity(re(12.0, 6.0))[1] == ""
    # a non-finite Reynolds number is REFUSED, never scored valid
    for bad in (float("nan"), 0.0, -1.0, None):
        assert not friction_line_validity(bad)[0]
    # and the derived length agrees with the band it came from
    assert (min_lwl_for_turbulent_flow_m(6.0 * kn, NU_FRESH_15C)
            == pytest.approx(RE_TRANSITION_BAND[1] * NU_FRESH_15C / (6.0 * kn)))


def test_the_low_reynolds_refusal_is_NOT_YET_WIRED_INTO_THE_LADDER():
    """RECORDED, NOT FIXED — and this test is the record.

    `limits.friction_line_validity` is the single home of the bar, and NOTHING
    CONSUMES IT YET. `resistance.total_resistance` sets `valid` from the Froude
    number alone, so a 2.5 m hull at 2 kn still comes back `valid=True` and is
    badged `L1` by `evaluate`. Closing it means editing `resistance.py` and
    `evaluate.py`, which on 2026-08-14 were owned by the concurrent multihull
    agent, so it was NOT done rather than done in a collision.

    THIS TEST IS A TRIPWIRE AND IT ASSERTS THE GAP. When the wiring lands it
    will fail, and the correct response is to invert it — assert the refusal —
    not to delete it.
    """
    from navalai import geometry, resistance

    # a gentle warp: on a 2.5 m hull the default 8 -> 20 deg over 0.35 LWL is
    # 22.5 deg/m of panel twist, which `panel.twist` refuses on its own merits.
    x = _hull(2.5, 0.5, 0.15, beta_mid=8.0, beta_bow=10.0, beta_len=0.60)
    assert grammar.check(x).ok, (
        "the 2.5 m probe hull is no longer L0-feasible, so this test is "
        "measuring the wrong thing; re-pick the hull, do not weaken the claim")
    hull = geometry.Hull(x)
    speed = 2.0 * 0.514444
    res = resistance.total_resistance(hull, speed=speed, wetted=2.0, cb=0.45,
                                      beam_wl=0.5, draft=0.15)
    re_num = speed * 2.5 / resistance.NU_FRESH_15C
    assert not friction_line_validity(re_num)[0], (
        f"Re {re_num:.3g} is now inside the ITTC-57 regime, so this probe no "
        f"longer demonstrates the gap")
    assert res.valid, (
        "resistance now refuses a low-Reynolds hull — the gap this tripwire "
        "records is CLOSED. Invert this assertion to assert the refusal, and "
        "record the closure; do not delete the test.")


def test_the_ittc_envelope_has_one_home_C31():
    """resistance carried a SECOND copy of the transition band with a
    DIFFERENT ceiling (3e6 vs limits' 5e6) — two modules answering "is
    ITTC-57 inside its regime?" with different numbers. resistance now
    DERIVES its pair from limits.RE_TRANSITION_BAND; the policies stay
    deliberately different (strict helper vs report-inside-band evaluation)
    and both docstrings say so.
    """
    from navalai import resistance
    from navalai.limits import RE_TRANSITION_BAND

    assert resistance.RE_TRANSITION_ONSET == RE_TRANSITION_BAND[0]
    assert resistance.RE_FULLY_TURBULENT == RE_TRANSITION_BAND[1]


def test_a_multihull_that_reaches_NEITHER_clause_is_UNASSESSED_not_blessed():
    """THE SILENT PASS, MEASURED 2026-08-20 and closed in evaluate.py.

    `evaluate` computed NZ Part 40A App.1 cl 1.3 for a multihull under 15 m
    with <= 50 persons, and cl 1.4 for the bigger class WITH a declared
    windage. A multihull that was neither -- >= 15 m and windage NOT
    declared -- fell through both branches and left the function with

        cl13 None, cl14 None, stability_criterion None, and NO violation

    which reads as a clean bill of health. It is silent precisely because
    everything around it is right: R-GM is deliberately withheld from a
    multihull (GM is the monohull criterion and a catamaran passes it
    trivially while remaining capsizable), and R-MHS is issued as a RECEIPT
    whose note points at "the evaluation's cl13/cl14 receipt". With neither
    computed, that pointer resolved to nothing.

    Same class as the rest of this campaign: a bar that exists and is not
    consulted. The rule is ASSESSED OR REFUSED, NEVER SILENTLY BLESSED.
    """
    import copy
    import sys

    sys.path.insert(0, "tests")
    import test_physical_form as _T

    from navalai import grammar
    from navalai.evaluate import evaluate

    case = _T._case("c")                      # a real catamaran fixture
    idx = {n: i for i, n in enumerate(grammar.NAMES)}

    # scale the WHOLE hull past 15 m so the vector stays self-consistent;
    # moving LWL alone produces a refused genome and proves nothing
    params = case.params.copy()
    k = 18.0 / float(params[idx["LWL"]])
    for name in ("LWL", "BWL", "T", "D"):
        params[idx[name]] *= k

    mission = copy.deepcopy(case.mission)
    assert not mission.windage.declared, "fixture must have NO declared windage"

    ev = evaluate(params, mission)
    vessel = ev.vessel or {}
    assert vessel.get("cl13") is None, "cl 1.3 must not apply at 18 m"
    assert vessel.get("cl14") is None, "cl 1.4 needs a declared windage"

    unassessed = [v for v in ev.violations
                  if "multihull stability" in v and "UNASSESSED" in v]
    assert unassessed, (
        "an 18 m multihull with no declared windage reached NEITHER clause "
        "and was returned without a stability violation — silently blessed. "
        f"violations were: {list(ev.violations)}")

    # and it must read as a REFUSAL TO ANSWER, not as a finding against the
    # design -- those are different claims and conflating them is how "we
    # did not check" becomes "this boat is unsafe"
    note = unassessed[0]
    assert "REFUSAL to answer" in note, note
    assert "declare the windage" in note, (
        "a refusal must say what would make it answerable: " + note)

    # the baseline fixture, unscaled, is genuinely ASSESSED and must not
    # acquire a spurious violation from this guard
    base = evaluate(case.params, copy.deepcopy(case.mission))
    assert (base.vessel or {}).get("cl13") is not None
    assert not [v for v in base.violations if "UNASSESSED" in v]
