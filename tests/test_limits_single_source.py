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
    # The exact statement the audit made: 15 mm is compliant below 845 kg and
    # nowhere else. This is a REGRESSION guard on the crossover, not a bar to
    # be moved — if the rule's coefficients change, this number moves with it.
    assert required_thickness_mm(845.0) <= limits.PLY_THICKNESS_M * 1e3
    assert required_thickness_mm(850.0) > limits.PLY_THICKNESS_M * 1e3


@pytest.mark.parametrize("mldc_kg", [800, 1500, 3000, 6000, 12000, 20000])
def test_derived_sheet_always_satisfies_the_rule_that_derived_it(mldc_kg):
    # The whole point of deriving rather than declaring: there is no input for
    # which the sheet we build with fails the rule we build to.
    t_m = select_stock_thickness_m(mldc_kg)
    assert t_m * 1e3 >= required_thickness_mm(mldc_kg)
    assert t_m in limits.STOCK_PLY_THICKNESS_M, "must be a sheet you can buy"


def test_derived_sheet_is_the_THINNEST_stock_that_works():
    # Rounding up to stock must not quietly over-build: the sheet below the
    # selected one has to be genuinely insufficient.
    for mldc in (1500, 6000, 12000):
        t = select_stock_thickness_m(mldc)
        thinner = [s for s in limits.STOCK_PLY_THICKNESS_M if s < t]
        if thinner:
            assert max(thinner) * 1e3 < required_thickness_mm(mldc)


def test_an_unbuildable_panel_is_a_finding_not_a_rounding():
    # Refusing beats silently returning the thickest sheet: a panel the stock
    # range cannot satisfy is exactly the case a builder must be told about.
    with pytest.raises(ValueError, match="do not round the requirement down"):
        select_stock_thickness_m(6000.0, span_mm=1400.0)


def test_the_ladder_reports_the_sheet_it_actually_built_with():
    # honesty rule 1: the thickness that fed the mass model and the bend limit
    # is the one the rules tier is handed. Before this it was neither.
    from navalai import grammar
    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec

    m = MissionSpec(displacement_target_kg=6000.0)
    ev = evaluate(grammar.vector({n: 0.5 * (lo + hi) for n, _u, lo, hi, _d
                                  in grammar.PARAMS}), m)
    assert ev.ply_thickness_m == select_stock_thickness_m(
        m.displacement_target_kg)
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
    assert old == pytest.approx(48.927, abs=0.01)
    assert shell_in_budget == pytest.approx(51.616, abs=0.01)
    assert abs(shell_in_budget - old) / old > 0.05, (
        "the ladder is back on the 1.6 factor (or the hull moved) — "
        f"budget shell {shell_in_budget:.3f} m^2 vs literal {old:.3f} m^2")

    # ...and the ratio the literal stood in for is a SHAPE, not a constant.
    X = grammar.sample(200, np.random.default_rng(3))
    ratios = [shell_area_m2(geometry.Hull(r)) / geometry.Hull(r).wetted_surface(0.0)
              for r in X]
    assert min(ratios) < 1.35 and max(ratios) > 3.0, (
        f"ratio spread {min(ratios):.3f}-{max(ratios):.3f}")
