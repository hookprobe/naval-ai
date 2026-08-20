"""Gate R2 — a limit is declared ONCE, and a scantling is DERIVED, not declared.

Motivating incident (audit 2026-08-05). `limits.py` was created after the GM
floor was found in four places at two different values. The audit then found the
same defect class still live in eleven more:

  - `PLY_THICKNESS_M` (15 mm) fed the structural mass and the bend-radius limit
    while `rules.iso12215` independently derived 18.24 mm for the same 6 t boat.
    The two never met, because the only caller that compared them —
    `scripts/demo_mission.py` — hand-passed a FOURTH number, `provided_mm=20.0`,
    which was the only value that made R-TBM pass. Measured: 15 mm satisfies the
    rule only below mLDC 845 kg, i.e. for no product line in PLM.md.
  - the scantling span was a bare `400.0` default while `engineer.py` built
    bulkheads 1.4 m apart with no frames between them. At 1.4 m the same rule
    wants 63.8 mm of plywood.
  - `CREW_MASS_KG` existed only in the rules tier, so 12 crew put 1020 kg on the
    rail for the heel check while the boat floated at the 2-crew displacement.
  - `translate.py` kept a private `0.25` freeboard floor in the same file that
    correctly imported `gm_floor` — the fix, one constant short.

The rule this file enforces: a number that means the same thing in two places
must BE the same object, and a number a standard can compute must be computed.
"""

from __future__ import annotations

import pathlib

import pytest

from navalai import limits
from navalai.rules.iso12215 import (DEFAULT_SPAN_MM, required_thickness_mm,
                                    select_stock_thickness_m)

_ROOT = pathlib.Path(__file__).parents[1]

# (literal, where it may legitimately appear). A limit's own definition site is
# the one place the digits are allowed to exist.
_BANNED = (
    "80.0 * 0.015",        # the bend limit, re-derived inline
    "provided_mm=20.0",    # the demo's magic sheet
    "span_mm: float = 400.0",   # the scantling span, re-declared
)


def _code_lines(path: pathlib.Path) -> str:
    """Source with comment lines and docstring prose dropped.

    The register and the module docstrings QUOTE the banned literals on
    purpose — that is how the incident stays readable. Scanning raw text made
    this test fail on its own explanation, which is a scanner bug, not a
    finding. Only executable lines are searched.
    """
    out = []
    in_doc = False
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc or stripped.startswith("#"):
            continue
        out.append(line.split("  #")[0])
    return "\n".join(out)


def _sources() -> list[pathlib.Path]:
    out = []
    for sub in ("navalai", "scripts", "ui"):
        out += [p for p in _ROOT.joinpath(sub).rglob("*.py")
                if "__pycache__" not in p.parts]
    return out


def test_no_module_redeclares_a_limit():
    offenders = []
    for path in _sources():
        src = _code_lines(path)
        for literal in _BANNED:
            if literal in src:
                offenders.append(f"{path.relative_to(_ROOT)}: {literal!r}")
    assert not offenders, (
        "a limit is declared twice — import it from navalai.limits instead:\n  "
        + "\n  ".join(offenders))


def test_crew_mass_and_frame_spacing_have_exactly_one_home():
    # Both were previously private to a single module. If either reappears as a
    # literal outside limits.py, the two consumers can drift apart again.
    from navalai.rules import iso12215, iso12217

    assert iso12217.CREW_MASS_KG is limits.CREW_MASS_KG
    assert DEFAULT_SPAN_MM == pytest.approx(limits.FRAME_SPACING_M * 1e3)
    assert "85.0" not in iso12217.__doc__ if iso12217.__doc__ else True
    assert iso12215.DEFAULT_SPAN_MM == DEFAULT_SPAN_MM


def test_the_platform_sheet_is_only_claimed_where_the_rule_allows_it():
    # The crossover guard, RE-MEASURED 2026-08-19 at the 6R re-shape: the
    # rule's coefficients changed to the ISO 12215-5:2008(E) text (kAR at
    # the measured l=2.5b panel geometry, kDC, kL, the Eq 8 minimum,
    # Table E.2 sigma_d at the sheet's own ply count), and per this
    # test's own charter the number moves with them: at LWL 10 m,
    # category C, 15 mm is compliant to ~5317 kg (was 845 under the
    # flat-floor model, 3424 under the interim l=b conservatism).
    from navalai.rules.iso12215 import n_plies_for_thickness as _n
    _n15 = _n(limits.PLY_THICKNESS_M)
    assert required_thickness_mm(5310.0, 10.0, n_ply=_n15) \
        <= limits.PLY_THICKNESS_M * 1e3
    assert required_thickness_mm(5330.0, 10.0, n_ply=_n15) \
        > limits.PLY_THICKNESS_M * 1e3


@pytest.mark.parametrize("mldc_kg", [800, 1500, 3000, 6000, 12000, 20000])
def test_derived_sheet_always_satisfies_the_rule_that_derived_it(mldc_kg):
    # The whole point of deriving rather than declaring: there is no input for
    # which the sheet we build with fails the rule we build to.
    t_m = select_stock_thickness_m(mldc_kg, 10.0)
    from navalai.rules.iso12215 import n_plies_for_thickness
    assert t_m * 1e3 >= required_thickness_mm(
        mldc_kg, 10.0, n_ply=n_plies_for_thickness(t_m))
    assert t_m in limits.STOCK_PLY_THICKNESS_M, "must be a sheet you can buy"


def test_derived_sheet_is_the_THINNEST_stock_that_works():
    # Rounding up to stock must not quietly over-build: the sheet below the
    # selected one has to be genuinely insufficient.
    for mldc in (1500, 6000, 12000):
        t = select_stock_thickness_m(mldc, 10.0)
        thinner = [s for s in limits.STOCK_PLY_THICKNESS_M if s < t]
        if thinner:
            from navalai.rules.iso12215 import n_plies_for_thickness
            t_thin = max(thinner)
            # judged with the THINNER sheet's own sigma_d — the same
            # self-consistency the selector applies
            assert t_thin * 1e3 < required_thickness_mm(
                mldc, 10.0, n_ply=n_plies_for_thickness(t_thin))


def test_an_unbuildable_panel_is_a_finding_not_a_rounding():
    # Refusing beats silently returning the thickest sheet: a panel the stock
    # range cannot satisfy is exactly the case a builder must be told about.
    with pytest.raises(ValueError, match="do not round the requirement down"):
        select_stock_thickness_m(6000.0, 10.0, span_mm=1400.0)


def test_the_ladder_reports_the_sheet_it_actually_built_with():
    # honesty rule 1: the thickness that fed the mass model and the bend limit
    # is the one the rules tier is handed. Before this it was neither.
    from navalai import grammar
    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec

    m = MissionSpec(displacement_target_kg=6000.0)
    ev = evaluate(grammar.vector({n: 0.5 * (lo + hi) for n, _u, lo, hi, _d
                                  in grammar.PARAMS}), m)
    from navalai import grammar as _g
    _lwl = _g.named(_g.vector({n: 0.5 * (lo + hi) for n, _u, lo, hi, _d
                               in _g.PARAMS}))["LWL"]
    assert ev.ply_thickness_m == select_stock_thickness_m(
        m.displacement_target_kg, float(_lwl))
    assert ev.ply_thickness_m > 0.0


def test_the_ladder_and_the_engineer_plank_the_same_boat():
    """Gap C9 — the same defect class as the GM floor, in an AREA.

    `engineer.assess` integrated the shell to the sheer via
    `energy.shell_area_m2`; the L1 weight path in `evaluate()` reached the same
    quantity through a bare `hull.wetted_surface(0.0) * 1.6`. So the module
    that counts plywood and the module that weighs it described two different
    boats, and nothing in the ladder could see the disagreement — a number
    declared twice, with the second copy rounded.

    MEASURED on the reference hull (2026-08-11): wetted(0.0) = 30.579 m^2, so
    the literal gave 48.927 m^2 against a true 51.616 m^2 — ratio **1.6879**,
    the factor short by 5.2%, structure mass 1415.03 kg instead of 1464.58 kg
    (-3.38%). The reference hull is the FLATTERING case: over 200
    grammar-feasible hulls (seed 3) the true ratio runs 1.251-6.702, mean
    2.062, so the literal was wrong by up to 76% of the true area and by
    -15.4% on average, across exactly the box NSGA-II searches.

    The shell area is read back OUT of the shipped weight budget by inverting
    `weight_budget`'s structure term, not re-derived beside it: a test that
    called `shell_area_m2` and compared it to itself would pass on the broken
    ladder. It also asserts the OLD literal is refused (defect class 3 in
    docs/LESSONS.md — a guard that was never made to fire is not a guard).
    """
    import numpy as np

    from navalai import engineer, geometry, grammar
    from navalai.energy import PLY_DENSITY, shell_area_m2
    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec
    from tests.test_phase0 import mid_params

    mldc_kg = 6000.0
    x = mid_params()
    hull = geometry.Hull(x)
    deck = hull.deck_area()
    ev = evaluate(x, MissionSpec(displacement_target_kg=mldc_kg))

    # invert structure = (shell + deck) * t * PLY_DENSITY * 1.35
    shell_in_budget = (ev.weights.structure_kg
                       / (PLY_DENSITY * 1.35 * ev.ply_thickness_m)) - deck
    assert shell_in_budget == pytest.approx(shell_area_m2(hull), rel=1e-9)

    # and it is the SAME boat the engineer planks: panel area = shell + deck
    rep = engineer.assess(hull, mldc_kg=mldc_kg)
    assert rep.panel_area_m2 == pytest.approx(round(shell_in_budget + deck, 1))

    # the defect itself, verbatim: 1.6 * the waterline area is refused
    old = hull.wetted_surface(0.0) * 1.6
    # 48.927 / 51.616 UNTIL 2026-08-13, on the pre-plate-P1 reference hull.
    # Both are properties of THIS hull and the hull was re-solved by the new
    # kernel (`tests/test_phase0.mid_params`), so both moved; the margin
    # between them — which is the whole subject of this test — is 13.9%
    # against the 5% bar below, where it used to be 5.5%. The defect is
    # refused by MORE now, not less.
    assert old == pytest.approx(41.023, abs=0.01)
    assert shell_in_budget == pytest.approx(46.707, abs=0.01)
    assert abs(shell_in_budget - old) / old > 0.05, (
        "the ladder is back on the 1.6 factor (or the hull moved) — "
        f"budget shell {shell_in_budget:.3f} m^2 vs literal {old:.3f} m^2")

    # ...and the ratio the literal stood in for is a SHAPE, not a constant.
    X = grammar.sample(200, np.random.default_rng(3))
    ratios = [shell_area_m2(geometry.Hull(r)) / geometry.Hull(r).wetted_surface(0.0)
              for r in X]
    assert min(ratios) < 1.35 and max(ratios) > 3.0, (
        f"ratio spread {min(ratios):.3f}-{max(ratios):.3f}")


# ===========================================================================
# THE PROPORTION BANDS AND THE SIZE BOX, ADDED 2026-08-14.
#
# The band that refused this project's own 12.0 x 0.8 m demihull was correct
# and correctly declared ONCE — `grammar.L_OVER_B_BAND`. What was declared
# twice was the SOURCED demihull ceiling: `formlib` carries the Southampton
# envelope with its SECONDARY caveat attached, and the obvious way to widen
# the grammar was to type `15.10` into `grammar.py` beside a comment naming
# Molland, Wellicome & Couser. That is this repository's signature defect with
# the second copy laundered into a citation, and `formlib.Basis.DRAWING`'s
# docstring already fences it INSIDE formlib and cannot fence it from outside.
# These are the outside half of that fence.

def test_the_demihull_band_edges_are_IMPORTED_and_not_retyped():
    from navalai import formlib, grammar

    assert (grammar.L_OVER_B_BAND_DEMIHULL[1]
            == formlib.SOTON_DEMIHULL_L_OVER_B.high)
    assert (grammar.B_OVER_T_BAND_DEMIHULL[0]
            == formlib.SOTON_DEMIHULL_B_OVER_T.low)
    # the public name is the citation block ITSELF, so the caveat travels
    assert formlib.SOTON_DEMIHULL_L_OVER_B is formlib._SOTON_L_OVER_B
    assert formlib.SOTON_DEMIHULL_B_OVER_T is formlib._SOTON_B_OVER_T


def test_no_module_retypes_a_sourced_band_edge_or_a_box_bound():
    """A textual sweep, in the spirit of `_BANNED` above.

    Each literal below is a number that now has exactly one home. The scan
    drops comments and docstrings (see `_code_lines`), so the module that
    EXPLAINS an incident may still quote its digits — only executable lines
    are searched.
    """
    from navalai import formlib, grammar

    banned = (
        # the Southampton demihull ceiling, retyped instead of imported
        ("15.10", "formlib.SOTON_DEMIHULL_L_OVER_B.high"),
        # the RCD scope, retyped instead of read from grammar.PARAMS
        ("(2.5, 24.0)", "grammar.PARAMS' LWL row"),
    )
    offenders = []
    for path in _sources():
        if path.name in ("formlib.py", "grammar.py", "limits.py"):
            continue      # the definition sites: formlib owns the Southampton
            # envelope, limits.py owns the RCD scope tuple, and grammar.py
            # imports both. `policy/legal.py` used to hold the RCD scope and
            # now imports it from limits.py — the ladder may never import
            # `navalai.policy`, so the number had to move DOWN to the module
            # both layers can see rather than be retyped in the grammar.
        src = _code_lines(path)
        for literal, home in banned:
            if literal in src:
                offenders.append(
                    f"{path.relative_to(_ROOT)}: {literal!r} — import {home}")
    assert not offenders, (
        "a sourced band edge was retyped:\n  " + "\n  ".join(offenders))
    # and the definition sites really do hold them
    assert formlib.SOTON_DEMIHULL_L_OVER_B.high == 15.10
    assert [r for r in grammar.PARAMS if r[0] == "LWL"][0][2:4] == (2.5, 24.0)


def test_the_freeboard_floors_check_applies_are_declared_once_each():
    """They were each written TWICE — in the condition and in the message
    beside it — which is the pattern that put a 15 mm ply outside its own
    scantling rule. `check()` now reads both from a symbol, and the D-floor of
    the parameter box is DERIVED from the absolute one, so a divergence would
    silently move the box as well as the bar.
    """
    from navalai import grammar

    assert grammar.MIN_FREEBOARD_ABS_M == 0.30
    assert grammar.MIN_FREEBOARD_FRAC_LWL == 0.045
    d_floor = [r for r in grammar.PARAMS if r[0] == "D"][0][2]
    t_floor = [r for r in grammar.PARAMS if r[0] == "T"][0][2]
    assert d_floor == pytest.approx(t_floor + grammar.MIN_FREEBOARD_ABS_M)
    src = _code_lines(_ROOT / "navalai" / "grammar.py")
    assert "0.045 * lwl" not in src, (
        "the relative freeboard floor is inlined again beside its own symbol")


def test_the_multihull_stability_refusal_has_ONE_home():
    """The sentence a catamaran gets instead of a GM verdict is a THRESHOLD in
    prose: if the rules tier and any report ever phrase it differently, they
    are two claims about one thing. `limits.py` owns it, exactly as it owns the
    GM floor the sentence exists to disown.
    """
    from navalai.rules import iso12217

    assert limits.MULTIHULL_STABILITY_UNASSESSED in iso12217.assess.__doc__ \
        if iso12217.assess.__doc__ else True
    src = _code_lines(_ROOT / "navalai" / "rules" / "iso12217.py")
    assert "MULTIHULL STABILITY IS NOT ASSESSED" not in src, (
        "the refusal text is retyped in the rules tier — import "
        "limits.MULTIHULL_STABILITY_UNASSESSED")
    assert "8.0" not in src.replace("MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG", ""), (
        "the multihull offset-load limit is retyped — import "
        "limits.MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG")


def test_physical_constants_have_one_home_S18():
    """Consolidation directive §18: four densities, three viscosities and
    two gravities were declared across seven modules. They now live ONLY in
    navalai/constants.py; everything else imports. The fence greps for the
    distinctive literals — a re-declaration anywhere else is the
    number-declared-twice defect coming back.
    """
    import pathlib
    import re

    import navalai

    root = pathlib.Path(navalai.__file__).parent
    distinctive = ("9.80665", "998.8", "1.09e-6", "1.13902e-6",
                   "1.18831e-6", "1.1883e-6", "1026.0")
    offenders = []
    for py in root.rglob("*.py"):
        if py.name == "constants.py":
            continue
        text = py.read_text()
        for lit in distinctive:
            for k, line in enumerate(text.splitlines(), 1):
                stripped = line.split("#")[0]
                # THE FENCE HAD A HOLE (2026-08-20). It required "=" in the
                # line, so it only ever saw ASSIGNMENTS -- and a literal used
                # inside an EXPRESSION walked straight through it. MEASURED:
                # contract.py carried `Re {speed_ms * lwl_m / 1.09e-6:.3g}`
                # in an f-string for as long as this fence has existed, and
                # this test passed the whole time. Same shape as gap J1, a
                # fence with a hole in itself.
                if lit in stripped and "import" not in stripped:
                    offenders.append(f"{py.relative_to(root)}:{k}: {line.strip()[:70]}")
    assert not offenders, (
        "physical-constant literals re-declared outside constants.py:\n  "
        + "\n  ".join(offenders))


def test_the_displacement_regime_edge_IS_the_michell_validity_edge_C33():
    """formlib's charter forbids importing project physics, so its 0.45 is
    linked to `resistance.FN_MICHELL_MAX` by COMMENT only ("the upper
    displacement edge is 0.45 because that is resistance.FN_MICHELL_MAX").
    A comment cannot follow a re-measurement. This fence is the executable
    half of that link: if the Michell validity edge ever moves, the regime
    table must move with it — or this test names the divergence.
    """
    from navalai import formlib, resistance

    assert (formlib.REGIME_FN[formlib.Regime.DISPLACEMENT].high
            == resistance.FN_MICHELL_MAX), (
        "formlib.REGIME_FN[DISPLACEMENT].high no longer equals "
        "resistance.FN_MICHELL_MAX — the comment-enforced identity broke")


def test_the_two_freeboard_floors_declare_their_relationship_C33():
    """`grammar.MIN_FREEBOARD_ABS_M` (0.30, the L0 box floor) and
    `limits.FREEBOARD_FLOOR_M` (0.25, the L1 feasibility floor) are two
    floors for one quantity, and their ordering is load-bearing: the L0
    floor must be AT LEAST the L1 floor, or the grammar admits hulls the
    ladder then refuses on freeboard — a refusal the box was supposed to
    make unreachable. The L1 floor stays for non-genome inputs (imported
    STL, hand-built params), which never pass through the box.
    """
    from navalai import grammar, limits

    assert grammar.MIN_FREEBOARD_ABS_M >= limits.FREEBOARD_FLOOR_M, (
        f"L0 box floor {grammar.MIN_FREEBOARD_ABS_M} below the L1 "
        f"feasibility floor {limits.FREEBOARD_FLOOR_M}: the grammar now "
        "admits hulls the ladder refuses on freeboard")


def test_scripts_do_not_redeclare_physical_constants_C33():
    """The S18 fence stops at the package boundary, and the first stray it
    missed was scripts/hull_form_audit.py's own `G = 9.80665`. Same fence,
    scripts/ directory."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "scripts"
    distinctive = ("9.80665", "998.8", "1.09e-6", "1.13902e-6",
                   "1.18831e-6", "1.1883e-6", "1026.0")
    offenders = []
    for py in root.glob("*.py"):
        for k, line in enumerate(py.read_text().splitlines(), 1):
            stripped = line.split("#")[0]
            if ("=" in stripped and "import" not in stripped
                    and "`" not in stripped
                    and any(lit in stripped for lit in distinctive)):
                offenders.append(f"{py.name}:{k}: {line.strip()[:70]}")
    assert not offenders, (
        "physical-constant literals re-declared in scripts/:\n  "
        + "\n  ".join(offenders))
