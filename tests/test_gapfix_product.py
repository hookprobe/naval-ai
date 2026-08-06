"""Gate tests for the product-surface gap closures of 2026-08-07.

Rows closed here, from `docs/GAP-REGISTER.md` via `scripts/reconcile_gaps.py`:

  G7   ES-TRIN existed as ZERO CODE while PLM listed the Solar Liveaboard
       (Danube) SKU as demo green.
  G8   ISO 12217-1 was applied to any hull handed to it. The grammar admits
       hulls from 4.0 m and the Dayboat SKU is 4-7 m; -1 governs 6 m and over.
  E15  `grade()` and `translate()` swallowed a BROKEN CHECKER and a FAILED
       DESIGN in the same `except Exception`.
  (plus) `refdata/ergonomics.py`'s ~40 sourced constants had ZERO consumers.

Every guard below is tested TWICE, per PLM §3 step 4: once where it FIRES on a
real defect, and once where the metric it needs is absent or garbled and it
must STILL refuse. An unmeasurable metric is fatal, never a passing default —
that is the rule `gate2m.py` broke by returning GCI = -27% and calling it PASS.
"""

from dataclasses import replace

import math

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate
from navalai.geometry import Hull
from navalai.mission import MissionSpec
from navalai.rules import report
from navalai.rules.iso12217 import (SCOPE_MIN_HULL_LENGTH_M,
                                    assess as stability, hull_length_m)
from navalai.rules import estrin
from navalai.rules import ergonomics
from navalai.translate import (grade, requirements_from_mission, translate)
from tests.test_phase0 import mid_params


def _hull_of(lwl: float) -> np.ndarray:
    x = mid_params().copy()
    x[grammar.NAMES.index("LWL")] = lwl
    return x


# ---------------------------------------------------------------------------
# G8 — ISO 12217-1's scope is part of ISO 12217-1
# ---------------------------------------------------------------------------

def test_a_sub_six_metre_hull_gets_no_12217_1_verdict():
    """G8, the case that motivated it.

    MEASURED before the guard: a 4.5 m grammar hull at category C produced
    FOUR numeric findings — downflooding height, GM floor, offset-load heel,
    category wave context — under a header naming ISO 12217-1, which by its
    own scope clause governs craft of 6 m and over. Four bars from a standard
    that does not cover the boat is not a lenient assessment, it is a wrong
    one, and it looked exactly like a right one.

    The same defect shape as `gate2m.py` printing KCS's EFD C_T for a Wigley
    hull; the fix is the same, an identity check that runs FIRST and returns.
    """
    x = _hull_of(4.5)
    m = MissionSpec(design_category="C", displacement_target_kg=1200)
    ev = evaluate(x, m)
    findings = stability(ev, "C", crew=2, beam_m=2.0)

    ids = [f.rule_id for f in findings]
    assert ids == ["R-SCP"], (
        f"a {ev.hydro.lwl_eff:.2f} m hull was assessed by ISO 12217-1 with "
        f"{ids} — the standard's own scope is 6 m and over")
    assert not findings[0].passed, "the refusal has to FAIL, not pass quietly"
    assert "12217-3" in findings[0].note, (
        "the refusal must name the standard that DOES govern this craft, or "
        "the reader is left with 'no' and no next step")
    assert not report(findings)["pass"]


def test_a_hull_in_scope_is_assessed_exactly_as_before():
    """The guard must not become a fifth finding on every boat.

    A scope test that PASSES is a precondition, not a statement about the
    hull. Emitting it would put an 'approx'-basis row into
    `report()['unreviewed_bases']` for every craft the standard does govern —
    an unreviewed threshold reported where there is no threshold at all.
    """
    ev = evaluate(mid_params(), MissionSpec(design_category="D",
                                            displacement_target_kg=5000))
    findings = stability(ev, "D", crew=2, beam_m=3.0)
    assert [f.rule_id for f in findings] == ["R-CAT", "R-DFH", "R-GM", "R-OLH"]
    assert report(findings)["unreviewed_bases"] == []


def test_an_unreadable_length_refuses_instead_of_assessing():
    """The garbled-metric half. A scope test that cannot be measured must not
    resolve to 'in scope, carry on' — that is the direction that assesses an
    unknown boat by a standard picked at random."""
    ev = evaluate(mid_params(), MissionSpec(displacement_target_kg=5000))
    broken = replace(ev, hull_lwl_m=0.0,
                     hydro=replace(ev.hydro, lwl_eff=float("nan")))
    assert hull_length_m(broken) is None
    findings = stability(broken, "D", crew=2, beam_m=3.0)
    assert [f.rule_id for f in findings] == ["R-SCP"]
    assert not findings[0].passed
    assert math.isnan(findings[0].measured)
    assert "UNDECIDABLE" in findings[0].note


def test_the_scope_bound_is_the_standards_own_and_lives_in_one_place():
    """6.0 m is ISO 12217-1's scope, not a project preference, and it is not
    retyped into the assessment body."""
    assert SCOPE_MIN_HULL_LENGTH_M == 6.0
    src = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "navalai" / "rules" / "iso12217.py").read_text()
    body = src[src.index("def assess("):]
    assert "6.0" not in body, "the scope bound was retyped inside assess()"


# ---------------------------------------------------------------------------
# G7 — ES-TRIN, and the scope call that is most of the answer
# ---------------------------------------------------------------------------

def test_a_small_craft_is_out_of_es_trin_scope_and_is_told_why():
    """Directive (EU) 2016/1629 Art. 2(1): L >= 20 m, or L.B.T >= 100 m3.

    A 12 m grammar hull is neither, so ES-TRIN does not govern it and no
    ES-TRIN bar may be applied to it. That determination IS the deliverable
    for most of this product line — the Danube SKU was listed as demo green
    against a standard nobody had checked applied.
    """
    x = _hull_of(12.0)
    ev = evaluate(x, MissionSpec(displacement_target_kg=5000))
    findings = estrin.assess(ev, Hull(x))
    assert [f.rule_id for f in findings] == ["ES-SCOPE"]
    assert findings[0].passed
    assert "OUT OF SCOPE" in findings[0].note


def test_an_in_scope_craft_is_assessed_and_then_refused():
    """A craft big enough to be governed gets Chapter 4 AND a refusal.

    One chapter of twenty is not an assessment. ES-COV fails unconditionally
    for an in-scope craft so that a report full of green Chapter 4 findings
    cannot be read as compliance with a 558-page standard.
    """
    assert estrin.in_scope(20.0, 3.0, 1.0), "the length limb"
    assert estrin.in_scope(19.0, 6.0, 1.0), "the L.B.T limb (114 m3)"
    assert not estrin.in_scope(12.0, 3.0, 0.8)

    x = _hull_of(20.0)
    ev = evaluate(x, MissionSpec(displacement_target_kg=12000))
    findings = estrin.assess(ev, Hull(x))
    ids = [f.rule_id for f in findings]
    assert ids == ["ES-SCOPE", "ES-SAFE", "ES-FB", "ES-COV"], ids
    cov = findings[-1]
    assert not cov.passed, (
        "an in-scope craft was reported without a coverage refusal — Chapter "
        "4 of 20 read as an ES-TRIN assessment")
    assert not report(findings)["pass"]
    for chapter in ("3 shipbuilding", "15 accommodation"):
        assert any(chapter in c for c in estrin.UNIMPLEMENTED_CHAPTERS)


def test_es_trin_refuses_a_craft_it_cannot_measure():
    """Garbled half: no floatation state means L, B and T are unknown, so
    whether the Directive applies is UNDECIDABLE. Undecidable is not
    out-of-scope, and out-of-scope is the answer that would have let it
    through silently."""
    x = _hull_of(12.0)
    ev = evaluate(x, MissionSpec(displacement_target_kg=5000))
    findings = estrin.assess(replace(ev, hydro=None), Hull(x))
    assert [f.rule_id for f in findings] == ["ES-SCOPE"]
    assert not findings[0].passed
    assert "UNDECIDABLE" in findings[0].note

    nan_state = replace(ev, hydro=replace(ev.hydro, draft=float("nan")))
    bad = estrin.assess(nan_state, Hull(x))
    assert [f.rule_id for f in bad] == ["ES-SCOPE"] and not bad[0].passed


def test_the_freeboard_formula_credits_sheer_and_stays_conservative():
    """ES-TRIN Art. 4.02: 150 mm baseline, reduced by the effective sheer.

    Two properties the transcription has to have, both checkable without the
    standard in hand: more sheer can only REDUCE the requirement (that is what
    the minus sign in `F = 150 - (Se_v + Se_a)/15` means), and a hull with no
    sheer at all gets exactly the Art. 4.02(1) baseline.
    """
    flat = mid_params().copy()
    flat[grammar.NAMES.index("sheer_rise")] = 0.0
    f_flat, terms = estrin.required_freeboard_mm(Hull(flat))
    assert terms["S_v_mm"] == 0.0 and terms["S_a_mm"] == 0.0
    assert f_flat == pytest.approx(estrin.FREEBOARD_BASE_MM)

    sheered = flat.copy()
    sheered[grammar.NAMES.index("sheer_rise")] = 0.4
    f_sheer, terms2 = estrin.required_freeboard_mm(Hull(sheered))
    assert terms2["S_v_mm"] > 0.0
    assert f_sheer < f_flat, (
        "sheer must reduce the required freeboard; a sign error here makes "
        "the check stricter for a better boat")
    assert terms2["alpha"] == 0.0, (
        "no superstructure is modelled and alpha must stay 0 — a non-zero "
        "alpha CREDITS a deckhouse that does not exist and lowers the bar")


# ---------------------------------------------------------------------------
# Tier E — the reference-data spine gets a consumer that can say no
# ---------------------------------------------------------------------------

def test_the_working_deck_bar_fires_on_a_crowded_small_boat():
    """`refdata/ergonomics.py` had ~40 sourced constants and ZERO consumers.

    A constant nothing divides by has never been wrong about anything. This is
    the first bar the boat can fail on the people it carries: ISO 15085:2024
    requires the maximum persons to be accommodated in Z1 plus the interior,
    and `SEAT_MIN_MM` (400 x 750 mm incl. foot space) is 0.30 m2 each.
    """
    assert ergonomics.seat_area_m2() == pytest.approx(0.30)
    small = Hull(_hull_of(4.5))
    counting, _excl = ergonomics.working_deck_area_m2(small)

    ok = ergonomics.assess(small, crew=2)[0]
    assert ok.passed, f"2 crew do not fit on {counting:.2f} m2 of deck"

    n_over = int(counting / ergonomics.seat_area_m2()) + 2
    bad = ergonomics.assess(small, crew=n_over)[0]
    assert not bad.passed, (
        f"{n_over} persons x 0.30 m2 fit on {counting:.2f} m2 of working deck "
        f"— the bar cannot fire and is decoration")
    assert "NECESSARY CONDITION ONLY" in bad.note, (
        "the note must say a pass is not 'the crew fit' — the whole deck plan "
        "is counted with no cabin, console or Z1 boundary removed")


def test_an_unreadable_crew_count_refuses_rather_than_defaulting_to_one():
    """Garbled half. The bar scales with the people aboard, so a crew count
    that is not a positive integer makes it UNMEASURABLE. Defaulting to 1 —
    the value that passes on any hull — is the shape of failure PLM §3 names:
    an unmeasurable metric scored as a perfect one."""
    h = Hull(mid_params())
    for crew in (0, -3, None, "two", float("nan")):
        f = ergonomics.assess(h, crew)[0]
        assert not f.passed, f"crew={crew!r} produced a PASS"
        assert math.isnan(f.measured)
        assert "UNMEASURABLE" in f.note


def test_the_slope_rule_excludes_deck_and_does_not_fail_it():
    """`WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG` is recorded in refdata as a
    SCOPE rule — "surfaces steeper than this are excluded from the
    working-deck definition ... which is a scope rule, not a bar". So a steep
    bow sheer must remove AREA, never produce a violation of its own."""
    flat = mid_params().copy()
    flat[grammar.NAMES.index("sheer_rise")] = 0.0
    steep = flat.copy()
    steep[grammar.NAMES.index("sheer_rise")] = 0.5

    c_flat, x_flat = ergonomics.working_deck_area_m2(Hull(flat))
    c_steep, x_steep = ergonomics.working_deck_area_m2(Hull(steep))
    assert x_flat == pytest.approx(0.0, abs=1e-9)
    assert x_steep > 0.0, "a 0.5 sheer rise excluded no deck at all"
    assert c_steep < c_flat
    # and it is an exclusion, not a finding
    assert ergonomics.assess(Hull(steep), crew=2)[0].rule_id == "E-DECK"


def test_a_constant_this_checker_skips_says_why_in_code():
    """The transverse slope limit cannot fire on a flat deck lid, and a check
    that cannot fire is the defect gap E4 deleted four of. It is recorded as
    deliberately not applied rather than silently omitted."""
    na = ergonomics.not_applicable()
    assert "WORKING_DECK_SLOPE_MAX_TRANSVERSE_DEG" in na
    assert "SIDE_DECK_WIDTH_MIN_MM" in na
    assert all(v.strip() for v in na.values())


def test_the_derived_finding_carries_the_weaker_provenance():
    """A number derived from a transcribed standard value and a paywalled
    preview value is a preview-grade number. Reporting the stronger of the two
    is how false provenance gets manufactured one derivation at a time."""
    from navalai.refdata.ergonomics import (
        SEAT_MIN_MM, WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG)
    assert WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG.basis == "standard-2003"
    assert SEAT_MIN_MM.basis == "approx"
    assert ergonomics.weakest_basis(
        SEAT_MIN_MM, WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG) == "approx"
    # and the RuleFinding field stays in the Gate 6R vocabulary, so a rule
    # nobody reviewed still shows up in report()['unreviewed_bases']
    f = ergonomics.assess(Hull(mid_params()), crew=2)[0]
    assert f.basis == "approx"
    assert report([f])["unreviewed_bases"] == ["E-DECK"]


def test_the_mission_contract_now_carries_the_crew_requirement():
    """The checker is WIRED, not merely written. `requirements_from_mission`
    is the contract the agentic loop is graded on, and the crew count comes
    from the mission rather than a constant in this module."""
    m = MissionSpec(crew=2, displacement_target_kg=5000)
    names = [r.name for r in requirements_from_mission(m)]
    assert "crew-fits-on-deck" in names
    crowded = requirements_from_mission(replace(m, crew=40))
    req = next(r for r in crowded if r.name == "crew-fits-on-deck")
    ev = evaluate(mid_params(), m)
    assert not req.check(ev), "40 people fit on this deck?"
    assert "40 persons" in req.detail(ev)


# ---------------------------------------------------------------------------
# E15 — a broken checker is not a failed design
# ---------------------------------------------------------------------------

def test_a_raising_checker_is_reported_as_broken_not_as_a_failing_hull():
    """E15. `except Exception: ok = False` cannot tell "this hull's GM is
    below the category floor" from "the GM checker raised AttributeError
    because `Evaluation` lost a field". Both printed `"pass": false` with a
    plausible detail beside them — a broken TOOL reported as a broken BOAT.
    On a field rename it would have reported every design as failing and the
    optimiser would have followed the lie."""
    m = MissionSpec(displacement_target_kg=5000)
    ev = evaluate(mid_params(), m)
    reqs = requirements_from_mission(m)
    reqs[0] = replace(
        reqs[0], check=lambda _ev: (_ for _ in ()).throw(
            AttributeError("Evaluation has no attribute 'hydro'")))

    rep = grade(ev, reqs)
    row = rep["requirements"][0]
    assert row["state"] == "broken"
    assert row["pass"] is False, (
        "a broken checker must still not count as passing — an unmeasurable "
        "requirement is not a met one")
    assert "checker error: AttributeError" in row["error"]
    assert rep["broken"] == [reqs[0].name]
    assert rep["checkers_ok"] is False
    assert rep["pass"] is False


def test_a_raising_detail_no_longer_takes_the_whole_report_down():
    """`detail()` was OUTSIDE the guard, so a formatting lambda that raised
    killed `grade()` with a traceback — from the one part of the function
    nobody would think to suspect."""
    m = MissionSpec(displacement_target_kg=5000)
    ev = evaluate(mid_params(), m)
    reqs = requirements_from_mission(m)
    reqs[1] = replace(reqs[1], detail=lambda _ev: f"{None:.2f}")
    rep = grade(ev, reqs)                      # must not raise
    assert rep["requirements"][1]["state"] == "broken"
    assert "checker error in detail()" in rep["requirements"][1]["detail"]
    assert rep["checkers_ok"] is False


def test_a_healthy_grade_still_says_its_checkers_are_healthy():
    """The negative control: without a broken checker the new fields must not
    fire, or `checkers_ok` is a constant and tells nobody anything."""
    m = MissionSpec(displacement_target_kg=5000)
    rep = grade(evaluate(mid_params(), m), requirements_from_mission(m))
    assert rep["broken"] == [] and rep["checkers_ok"] is True
    assert all(r["state"] == "checked" for r in rep["requirements"])


@pytest.mark.parametrize("llm, expect", [
    (lambda _p: (_ for _ in ()).throw(ConnectionError("no route to model")),
     "checker error: LLM call raised ConnectionError"),
    (lambda _p: "sure! here is your boat:", "unparseable JSON"),
    (lambda _p: "[1, 2, 3]", "returned a list, not an object"),
])
def test_translate_says_which_of_the_three_fallbacks_it_took(llm, expect):
    """The same collapse one layer up. An LLM returning prose, an LLM raising
    ConnectionError and a bug in `sanitize()` produced a silent, identical
    fallback — so a translator broken for a week looked exactly like a user
    typing a mission the model declined to parse.

    The BEHAVIOUR is unchanged and must stay unchanged: never an exception,
    never geometry. Only the notes field learns to say what happened."""
    m = translate("a 6 m dayboat for four people at 8 knots", llm=llm)
    assert isinstance(m, MissionSpec)
    assert expect in m.notes, m.notes


def test_a_broken_sanitiser_is_named_as_ours_not_as_the_models_fault():
    """The fourth branch is OURS. If `sanitize()` raises, the model did its
    job and we did not — a defect to fix, not a mission to translate."""
    import navalai.translate as T
    real = T.sanitize
    try:
        T.sanitize = lambda raw, floor: (_ for _ in ()).throw(
            KeyError("design_category"))
        m = translate("a 6 m dayboat", llm=lambda _p: '{"crew": 2}')
        assert "checker error: sanitize() raised KeyError" in m.notes
    finally:
        T.sanitize = real


# ---------------------------------------------------------------------------
# Dead code cleared for removal by the audit
# ---------------------------------------------------------------------------

def test_the_two_dead_unroll_helpers_stay_gone():
    """`FlatPanel.perimeter` and `_interp_edge` had zero references across
    navalai/, tests/, scripts/ and ui/. `_interp_edge` was also wrong for the
    general case: it lerps between a panel's two developed edges, which is a
    ruling only if the panel is developable."""
    from navalai import unroll
    assert not hasattr(unroll.FlatPanel, "perimeter")
    assert not hasattr(unroll, "_interp_edge")
    src = (__import__("pathlib").Path(unroll.__file__)).read_text()
    # named in the comment recording WHY they went, and nowhere else
    assert "def perimeter" not in src and "def _interp_edge" not in src
