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
from types import SimpleNamespace

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
    # R-GM is basis='approx' since 2026-08-12: ISO 12217-1:2015 contains NO
    # absolute metacentric requirement (a regex sweep of all 86 pages returns
    # zero hits), so the GM floor is ours. It stays as an L1 feasibility bar
    # but must be DECLARED unreviewed — a report claiming no unreviewed bases
    # while carrying it would imply ISO backing for a number ISO does not have,
    # which is the exact defect this test was written to prevent.
    assert report(findings)["unreviewed_bases"] == ["R-GM"]


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

    Two articles of thirty-three chapters is not an assessment. ES-COV fails
    unconditionally for an in-scope craft so that a report full of green
    Chapter 4 findings cannot be read as compliance with a 578-page standard.

    THE DENOMINATOR WAS WRONG THREE WAYS AT ONCE, MEASURED 2026-08-13, all of
    them flattering: the module docstring said "eighteen", the tuple held
    SEVENTEEN entries, and it stopped at Chapter 20 — silently asserting that
    ES-TRIN has twenty chapters. Read from the table of contents of
    `downloads/standards/ES_TRIN_2025_signed_en.pdf`, it has THIRTY-THREE.
    Chapters 21-33 were not merely unimplemented, they were absent from the
    list of things the module admits to not implementing, so the one finding
    whose entire job is an honest refusal overstated coverage by ~40%.
    """
    assert estrin.in_scope(20.0, 3.0, 1.0), "the length limb"
    assert estrin.in_scope(19.0, 6.0, 1.0), "the L.B.T limb (114 m3)"
    assert not estrin.in_scope(12.0, 3.0, 0.8)

    x = _hull_of(20.0)
    ev = evaluate(x, MissionSpec(displacement_target_kg=12000))
    findings = estrin.assess(ev, Hull(x))
    ids = [f.rule_id for f in findings]
    assert ids == ["ES-SCOPE", "ES-SAFE", "ES-FB", "ES-REC", "ES-COV"], ids
    cov = findings[-1]
    assert not cov.passed, (
        "an in-scope craft was reported without a coverage refusal — two "
        "articles of 33 chapters read as an ES-TRIN assessment")
    assert not report(findings)["pass"]

    # the denominator is the standard's real chapter count, not the length of
    # whatever list we happen to maintain
    assert estrin.TOTAL_CHAPTERS == 33
    assert cov.required == float(estrin.TOTAL_CHAPTERS)
    # 33 chapters, minus Ch. 1 (definitions, USED) and Ch. 4 (partly done)
    assert len(estrin.UNIMPLEMENTED_CHAPTERS) == estrin.TOTAL_CHAPTERS - 2
    for chapter in ("3 shipbuilding", "15 accommodation",
                    "26 recreational craft", "29 high-speed vessels"):
        assert any(chapter in c for c in estrin.UNIMPLEMENTED_CHAPTERS), chapter
    # the chapters that used to fall off the end are named in the note itself
    assert "Ch. 33" in cov.note and "Ch. 26" in cov.note


def test_es_trin_says_chapter_4_may_not_govern_a_recreational_craft():
    """ES-TRIN Art. 26.01, READ DIRECTLY from the 2025/1 text p.191-192.

    This is the sharpest finding the EU regulatory audit produced and it points
    at this module. Art. 26.01(1) applies to recreational craft only "the
    following requirements" — parts of Ch. 3, 5, 6, 7, 8; all of Ch. 9; parts
    of Ch. 10 and 13; all of Ch. 16 and 17; part of Ch. 21 — AND CHAPTER 4 IS
    NOT AMONG THEM. Art. 26.01(2), for a recreational craft subject to
    Directive 2013/53/EU (the RCD, i.e. exactly this project's SKUs), is
    narrower still and also omits Chapter 4.

    So ES-SAFE and ES-FB, the only two numeric bars this module computes, are
    very likely not the bars that govern the craft we build. Craft TYPE is not
    modelled — `MissionSpec` has no recreational/commercial flag — so the
    module cannot decide it and must not pretend either way. It REPORTS.

    Deleting the two findings on this basis would be the worse error, and it
    is the same shape as the L, B measurand incident recorded in estrin.py: an
    understatement that silently DELETES an assessment is how a craft the
    Directive governs gets told it is out of scope.
    """
    x = _hull_of(20.0)
    ev = evaluate(x, MissionSpec(displacement_target_kg=12000))
    rec = [f for f in estrin.assess(ev, Hull(x)) if f.rule_id == "ES-REC"]
    assert len(rec) == 1, "an in-scope craft got no Art. 26.01 finding"
    r = rec[0]
    assert not r.passed, (
        "Art. 26.01 is UNDECIDABLE here, and undecidable is not a pass — a "
        "green ES-REC would assert Chapter 4 governs, which the standard "
        "does not say")
    assert math.isnan(r.measured), (
        "an undecidable finding must not report a value")
    assert "26.01" in r.clause and "2025/1" in r.clause
    assert "UNDECIDABLE" in r.note and "recreational" in r.note.lower()
    # and the two bars it casts doubt on are still COMPUTED, not dropped
    ids = [f.rule_id for f in estrin.assess(ev, Hull(x))]
    assert "ES-SAFE" in ids and "ES-FB" in ids


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


def test_art_4_02_caps_every_reduction_it_is_supposed_to_cap():
    """ES-TRIN Art. 4.02(5), (6) and (7), MISSING until 2026-08-13.

    All three clauses CAP a reduction, and `F = 150 - (Se_v + Se_a)/15`
    subtracts that reduction, so every omission made the REQUIRED freeboard
    smaller and the check easier to pass. That is the unsafe direction, and it
    sat next to a long docstring correctly explaining that the alpha = 0
    simplification errs the SAFE way — one omission that erred safe, described
    at length, and three that erred unsafe, unmentioned.

    Verbatim, from ES-TRIN 2025/1 p.18-19 (Articles re-read clause by clause,
    unchanged from 2023/1):
      (5) "However, coefficient r will not be taken to be more than 1."
      (6) "If beta_a . Se_a is greater than beta_v . Se_v, the value of
           beta_v . Se_v will be taken as being the value for beta_a . Se_a."
      (7) "In view of the reductions referred to in (2) to (6) the freeboard
           shall be not less than 0 mm."

    THE CLAUSES ARE INERT ON THE HULLS THIS GRAMMAR ACTUALLY EMITS, AND THAT
    IS SAID OUT LOUD RATHER THAN LEFT FOR SOMEONE TO DISCOVER. MEASURED over
    sheer_rise 0.0-1.2 on a 20 m hull: r lands at 0.90, never above 1; the aft
    sheer is structurally 0 because the sheer minimum sits at the transom, so
    the aft segment is a single point; and F stays at 90-150 mm. So this is
    NOT a fix to a live wrong number on the shipped configuration — it is a
    transcription completed. The guards are exercised below on synthetic sheer
    profiles precisely because the product cannot reach them, which is the
    only honest way to show a guard fires at all.
    """
    L, n = 20.0, 41
    x = np.linspace(0.0, L, n)

    def _stub(z):                        # required_freeboard_mm reads only these
        return SimpleNamespace(x=x, z_sheer=np.asarray(z, dtype=float))

    # (5) a sheer that falls to 0.25 S far inboard drives r above 1
    slow = np.clip((x - L * 0.45) / (L * 0.55), 0.0, 1.0) ** 0.35
    _, t5 = estrin.required_freeboard_mm(_stub(slow))
    assert t5["Se_v_mm"] / t5["S_v_mm"] == pytest.approx(estrin.SHEER_R_CAP)
    assert t5["Se_v_mm"] <= estrin.SHEER_FWD_CAP_MM * estrin.SHEER_R_CAP

    # (6) a stern-heavy sheer cannot buy more credit than the bow earns
    mid = n // 2
    z6 = np.concatenate([np.linspace(0.50, 0.0, mid),
                         np.linspace(0.0, 0.05, n - mid)])
    f6, t6 = estrin.required_freeboard_mm(_stub(z6))
    assert t6["S_a_mm"] == pytest.approx(estrin.SHEER_AFT_CAP_MM)
    assert t6["Se_a_mm"] == pytest.approx(500.0)
    assert t6["Se_a_capped_mm"] == pytest.approx(t6["Se_v_mm"])
    # and the cap is worth 30 mm of required freeboard on this profile
    f_uncapped = estrin.FREEBOARD_BASE_MM - (t6["Se_v_mm"] + t6["Se_a_mm"]) / 15.0
    assert f6 - f_uncapped == pytest.approx(30.0, abs=0.5), (
        "Art. 4.02(6) must raise the requirement; measured 113.3 -> 143.3 mm")

    # (7) THE FLOOR IS UNREACHABLE WHILE alpha = 0, AND THAT IS A PROOF, NOT A
    # GAP. Art. 4.02(5) caps the ACTUAL sheers at 1000 mm forward and 500 mm
    # aft, and r at 1, so Se_v <= 1000 and Se_a <= 500. The largest possible
    # reduction is therefore (1000 + 500)/15 = 100 mm against a 150 mm base:
    #
    #     F_min = 150 - 100 = 50 mm  >  0
    #
    # (An earlier draft of this test asserted 16.7 mm by pairing the 1000 mm
    # forward cap with itself through clause (6). Clause (6) clamps the aft
    # term DOWNWARD to the forward one; it can never raise it past the 500 mm
    # cap that (5) already applied. The measurement caught it.)
    #
    # The floor can only bite once a superstructure shrinks the base through
    # 150(1 - alpha), which this project does not model. It is implemented
    # anyway because alpha is the next term to land, and a clause transcribed
    # only when it first bites is a clause nobody checks.
    z7 = np.concatenate([np.linspace(3.0, 0.0, mid),
                         np.linspace(0.0, 3.0, n - mid)])
    f7, t7 = estrin.required_freeboard_mm(_stub(z7))
    assert t7["Se_v_mm"] == pytest.approx(estrin.SHEER_FWD_CAP_MM)
    assert t7["Se_a_capped_mm"] == pytest.approx(estrin.SHEER_AFT_CAP_MM)
    assert f7 > estrin.FREEBOARD_FLOOR_MM
    assert f7 == pytest.approx(
        estrin.FREEBOARD_BASE_MM
        - (estrin.SHEER_FWD_CAP_MM + estrin.SHEER_AFT_CAP_MM) / 15.0)
    assert f7 == pytest.approx(50.0, abs=0.01), (
        "the analytic minimum of F at alpha = 0; if this moves, one of the "
        "caps above stopped binding")


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
    bow sheer must remove AREA, never produce a violation of its own.

    FIXTURE CORRECTED 2026-08-07 — LWL 10.0 m -> 6.0 m, and this is a change to
    the TEST, not to the rule. THE TEST WAS WRONG AND THE CODE WAS RIGHT.
    It used `mid_params()` (LWL 10.0 m, D 1.55, x_mb 0.55) and asserted that a
    0.5 sheer rise excludes deck there. MEASURED: on that hull the steepest
    deck panel is 18.51 deg (closed form
    `atan(2*sheer*D / (LWL*(1-x_mb)))` = 19.01 deg), against ISO's 25 deg
    bound — a 775 mm rise spread over 4.5 m of deck is a 19 deg ramp, so
    NOTHING is excluded and 0.0 is the correct answer. Asserting `x_steep >
    0.0` there asked the checker to exclude deck that is inside the standard's
    scope; satisfying it would have meant lowering a standard's number.

    The limb is live code, it just does not bind on a 10 m hull. MEASURED at
    the grammar's sheer_rise ceiling (0.5), mid parameters otherwise:

        LWL 4.0 -> 39.94 deg  ·  5.0 -> 33.81  ·  6.0 -> 29.17  ·  7.0 -> 25.57
        LWL 7.2 -> 24.94 deg (keeps all)       ·  10.0 -> 18.51 (keeps all)

    so it fires below ~7.2 m — inside the 4-7 m Dayboat SKU, which is the
    product this scope rule is load-bearing for. At LWL 6.0 the exclusion is
    0.3292 m2 and the counting area falls 13.2475 -> 12.9936 m2.

    RE-MEASURED 2026-08-13 ON THE PLATE-P1/P2 KERNEL. **The slope table above
    did not move by a hundredth of a degree** — the deck's longitudinal slope
    is a closed form in `sheer_rise`, `D`, `LWL` and `x_mb`, and the rebuild
    changed none of them — so the FINDING (the limb is live and binds below
    ~7.2 m, inside the Dayboat SKU) is untouched. What moved is the AREAS, and
    only because the hull is narrower: the counted deck at LWL 6.0 went
    16.6465 -> 13.2475 m2 and the exclusion 0.3706 -> 0.3292 m2. Nothing here
    is a bar; ISO's 25 deg is the bar and it is not in this file.
    """
    flat = _hull_of(6.0)
    flat[grammar.NAMES.index("sheer_rise")] = 0.0
    steep = flat.copy()
    steep[grammar.NAMES.index("sheer_rise")] = 0.5

    c_flat, x_flat = ergonomics.working_deck_area_m2(Hull(flat))
    c_steep, x_steep = ergonomics.working_deck_area_m2(Hull(steep))
    assert ergonomics.deck_panel_slope_deg(Hull(steep)).max() > float(
        ergonomics.WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG.value), (
        "the fixture no longer has a panel past the scope bound, so the rest "
        "of this test proves nothing — re-measure before relaxing it")
    # the flat-hull control: a deck with no slope anywhere must lose EXACTLY
    # nothing, or the exclusion is firing on something other than slope
    assert x_flat == pytest.approx(0.0, abs=1e-9)
    assert c_flat == pytest.approx(13.2475, abs=1e-3)
    assert x_steep == pytest.approx(0.3292, abs=1e-3), (
        "a 0.5 sheer rise on a 6 m hull excluded no deck at all")
    assert c_steep == pytest.approx(12.9936, abs=1e-3)
    assert c_steep < c_flat
    # and it is an exclusion, not a finding
    assert ergonomics.assess(Hull(steep), crew=2)[0].rule_id == "E-DECK"

    # the other half of "scope rule, not a bar": on a hull where nothing is
    # steep enough to exclude, the answer is 0.0 excluded — not a violation
    tall = _hull_of(10.0)
    tall[grammar.NAMES.index("sheer_rise")] = 0.5
    _c10, x10 = ergonomics.working_deck_area_m2(Hull(tall))
    assert x10 == pytest.approx(0.0, abs=1e-9), (
        "18.51 deg is inside ISO's 25 deg working-deck scope bound")
    assert ergonomics.assess(Hull(tall), crew=2)[0].passed


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
    from the mission rather than a constant in this module.

    FIXTURE CORRECTED 2026-08-07 — and again the TEST was wrong twice over
    while the code was right, so both defects are recorded rather than papered
    over. It asserted `not req.check(ev)` for 40 persons on `mid_params()`:

      (1) THE CREW NEVER REACHED 40. MEASURED:
          `replace(MissionSpec(crew=2), crew=40).crew == 12`, because
          `mission.FIELD_RANGES["crew"]` was (1, 12) and
          `MissionSpec.__post_init__` clamps. The row under test graded a
          12-person boat; 40 survived only as the note "crew 40 outside
          [1, 12]; clamped to 12". FIXED IN THE CONTRACT, not here — the
          ceiling is now 250, justified against ES-TRIN scope in
          `mission.FIELD_RANGES`. A clamp still happens and is still NOTED
          (5000 clamps to 250 and says so); the LLM-seam rule is that an
          out-of-range value is clamped and RECORDED, never accepted silently.
      (2) EVEN UNCLAMPED, 40 PERSONS GENUINELY PASS ON THAT HULL, AND THAT IS
          THE CORRECT ANSWER. MEASURED: the mid hull (LWL 10.0 m) has
          27.862 m2 of working deck against 40 x 0.30 = 12.00 m2. The row
          first fails there at 93 persons. Asserting a fail at 40 asked the
          bar to refuse a boat that passes it.

    So the fixture moves to a hull where the requirement can actually bind.
    MEASURED working deck vs 40 x 0.30 = 12.00 m2 required, RE-MEASURED
    2026-08-13 on the plate-P1/P2 kernel (the hull is narrower for the same
    LWL, so every area fell and the pass/fail boundary moved out from ~4.4 m to
    ~5.45 m; the ROW is unchanged and so is the 0.30 m2/person figure it
    divides by):

        LWL 4.0 ->  8.850 m2 FAIL   4.2 ->  9.292 FAIL   4.3 ->  9.513 FAIL
        LWL 5.0 -> 11.062 m2 FAIL   5.4 -> 11.947 FAIL   5.5 -> 12.168 PASS
        LWL 6.0 -> 13.275 m2 PASS  10.0 -> 22.124 PASS

    BEFORE, on the pre-rebuild kernel: 11.145 / 11.702 / 11.981 FAIL at
    4.0 / 4.2 / 4.3 and 12.538 / 13.931 / 27.862 PASS at 4.5 / 5.0 / 10.0.

    NECESSARY CONDITION ONLY. Every number above counts the whole deck plan
    with no console, cabin, side deck or Z1 boundary removed, so a PASS here
    does not mean the crew fit — only a FAIL is decisive. The stronger bar
    needs the deck model of BuildPlan 2 V2.1-V2.3, which is unbuilt. Do NOT
    make this row fail sooner by shrinking the 0.30 m2/person figure: it
    derives from `refdata.ergonomics.SEAT_MIN_MM` (400 x 750 mm incl. foot
    space) and has exactly one home.
    """
    m = MissionSpec(crew=2, displacement_target_kg=1200)
    names = [r.name for r in requirements_from_mission(m)]
    assert "crew-fits-on-deck" in names

    crowded = replace(m, crew=40)
    assert crowded.crew == 40, (
        "the contract clamped the crew away before the row could see it — "
        "FIELD_RANGES['crew'] must admit the count this test is about")
    req = next(r for r in requirements_from_mission(crowded)
               if r.name == "crew-fits-on-deck")

    # binds: 40 x 0.30 = 12.00 m2 against 9.29 m2 of deck on a 4.2 m hull
    # (11.702 m2 before the kernel rebuild — the row bound then and binds now,
    # by a wider margin)
    small = evaluate(_hull_of(4.2), crowded)
    assert ergonomics.working_deck_area_m2(Hull(small.params))[0] == \
        pytest.approx(9.292, abs=1e-3)
    assert not req.check(small), "40 people fit on a 9.29 m2 deck?"
    assert "40 persons" in req.detail(small)
    assert "NECESSARY CONDITION ONLY" in req.detail(small)

    # and it can fail in the OTHER direction too, or it is not a bar but a
    # constant: the same 40 persons on the 10 m mid hull genuinely fit
    big = evaluate(mid_params(), crowded)
    assert ergonomics.working_deck_area_m2(Hull(big.params))[0] == \
        pytest.approx(22.124, abs=1e-3)
    assert req.check(big), (
        "40 x 0.30 = 12.00 m2 on 22.12 m2 of deck must PASS — a row that "
        "cannot pass is not a requirement")


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


def test_the_drone_payload_is_a_real_mission_field_S11():
    """Consolidation directive §11: PayloadSpec is first-class — its mass
    enters the POSITIONED model (moving LCG), its continuous draw enters
    the hotel load (moving the energy balance), an uncrewed mission's
    crew-provision default is zeroed WITH A NOTE, and the whole thing
    round-trips through JSON. Same hull kernel, no drone geometry engine.
    """
    from navalai.evaluate import evaluate
    from navalai.mission import (Manning, MissionSpec, PayloadSpec,
                                 VesselConfig)
    from navalai.reference import reference_params

    base = MissionSpec(vessel=VesselConfig(manning=Manning.UNCREWED))
    loaded = MissionSpec(
        vessel=VesselConfig(manning=Manning.UNCREWED),
        payload=PayloadSpec(mass_kg=300.0, power_w=200.0, x_frac_lwl=0.40,
                            z_frac_depth=0.55, endurance_h=72.0))
    # the crewed provision is zeroed for BOTH (untouched default), recorded
    assert base.energy.payload_kg == 0.0
    assert "uncrewed" in base.notes
    e0 = evaluate(reference_params(), base)
    e1 = evaluate(reference_params(), loaded)
    # the payload is a POSITIONED item, not a silent scalar
    item = {i.id: i for i in e1.masses.items}["mission_payload"]
    assert item.mass_kg == 300.0
    assert "declared position" in item.source
    assert item.x_m == pytest.approx(0.40 * 10.0)
    # it MOVES the boat: LCG shifts toward the declared station
    assert e1.masses.lcg_m < e0.masses.lcg_m
    # and DRAINS the day: 200 W continuous = 4.8 kWh/day off the balance
    assert e0.energy.net_kwh_day - e1.energy.net_kwh_day == pytest.approx(
        4.8, rel=0.05)
    # a payload with NO declared position says so on the item
    e2 = evaluate(reference_params(),
                  MissionSpec(payload=PayloadSpec(mass_kg=100.0)))
    item2 = {i.id: i for i in e2.masses.items}["mission_payload"]
    assert "DEFAULTED" in item2.source
    # round trip
    m2 = MissionSpec.from_json(loaded.to_json())
    assert m2.payload == loaded.payload
    # declared-not-assessed: an explicit refusal to fabricate
    assert loaded.payload.sea_state is None
    with pytest.raises(ValueError, match="finite non-negative"):
        PayloadSpec(mass_kg=-5.0)


def test_one_rule_one_mldc_C04():
    """Forensics B1/C-04: the stock sheet was selected from the MISSION
    TARGET while R-TBM was assessed at the FLOATED displacement — whenever
    the budget exceeded the target the rule failed by construction
    (measured: a 0.02 mm sliver on the 5 m case). Selection is now a fixed
    point on the boat's ACTUAL loaded displacement, so selection and
    assessment read the same boat and R-TBM cannot fail on the split."""
    from navalai import formcheck
    from navalai.evaluate import evaluate
    from navalai.rules.iso12215 import select_stock_thickness_m

    case = {c.key: c for c in formcheck.CASES}["a"]
    ev = evaluate(case.params, case.mission)
    assert ev.hydro is not None
    # the budget exceeds the declared target on this case — the exact
    # regime that used to split the two mLDCs
    assert ev.hydro.disp_kg > case.mission.displacement_target_kg
    # the selected sheet is the fixed point of the FLOATED displacement
    assert ev.ply_thickness_m == select_stock_thickness_m(ev.hydro.disp_kg)
    # and the rule no longer fails on the selection/assessment split
    assert not any("R-TBM" in v for v in ev.violations), ev.violations
