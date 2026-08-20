"""Gate L2 — a numeric literal is CATEGORISED, and a fenced one has one home.

MOTIVATING INCIDENT (2026-08-20, commit 99c02e2). `navalai/contract.py` carried

    f"Re {speed_ms * lwl_m / 1.09e-6:.3g} "

for the entire life of that line while `tests/test_limits_single_source.py`
listed `"1.09e-6"` among the constants it hunts. It never fired: the scan
required `"=" in stripped`, so it only ever saw ASSIGNMENTS, and a physical
constant used inside an EXPRESSION was invisible to the fence built to find
restated physical constants. Gap J1's shape — a fence with a hole in itself.

The same-day fix dropped the `"="`. That closed the hole with a string-level
patch, and a string-level patch cannot see `float("998.8")`, cannot see
`1.0900e-6`, and cannot tell `1026.0` in an expression from `1026.0` in prose.
`navalai/constpolicy.py` replaces it with `ast`, and this file is its proof.

TWO DIRECTIONS, because a fence that merely passes proves nothing
(docs/LESSONS.md defect class 3):

  * it FIRES on a crafted offender in each of seventeen syntactic positions, and
    on the historical `contract.py` line VERBATIM;
  * it stays SILENT on legitimate mathematics — 2, 0.5, exponents, 100.0 for a
    percentage, 1e-9 tolerances and 1000.0 — because the goal is not to ban
    numbers.

AND it must not be WEAKER than the fence it replaces: every spelling the
string-level scan hunted is asserted to be in the watch set, by value.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from navalai import constpolicy as cp

_ROOT = pathlib.Path(__file__).resolve().parents[1]


# ==========================================================================
# THE FENCE ITSELF


def test_no_module_restates_a_physical_constant_in_any_position():
    """The live fence, over `navalai/`, `scripts/` and `ui/`.

    MEASURED 2026-08-20 at 0 findings over 100 files with 11 watched values.
    `tests/` is out of scope on purpose: a test asserting `rho == 1025.0` is a
    PIN, which is the mechanism that catches the constant moving, not a
    restatement of it.
    """
    findings = cp.scan_tree()
    assert not findings, (
        "a physical constant is declared outside navalai/constants.py:\n  "
        + cp.report(findings))


def test_the_LIVE_TREE_SCAN_fails_on_a_planted_offender(tmp_path):
    """`test_no_module_restates_...` above is green. Green proves nothing on
    its own (docs/LESSONS.md defect class 3), so the SAME entry point —
    `scan_tree`, walking a directory, resolving homes, applying the allowlist
    — is pointed at a tree that does offend and must report it.

    The tree is built in `tmp_path` rather than by editing a file in the
    repository, because other agents hold uncommitted work here and a fence
    that plants a defect in a shared tree is a worse idea than the defect.
    """
    pkg = tmp_path / "navalai"
    pkg.mkdir()
    (pkg / "constants.py").write_text((_ROOT / cp.CONSTANTS_FILE).read_text())
    (pkg / "planted.py").write_text(
        '"""A receipt. The viscosity is 1.09e-6, quoted here on purpose."""\n'
        "\n"
        "\n"
        "def receipt(speed_ms, lwl_m):\n"
        "    # and quoted again in a comment: 1.09e-6\n"
        '    return f"Re {speed_ms * lwl_m / 1.09e-6:.3g}"\n')

    findings = cp.scan_tree(root=tmp_path, subdirs=("navalai",))
    assert len(findings) == 1, cp.report(findings)
    f = findings[0]
    assert f.path == "navalai/planted.py"
    assert f.line == 6, "the docstring and the comment are not code"
    assert f.watched.home == "navalai.constants.NU_FRESH_20C"
    src = (pkg / "planted.py").read_text().splitlines()[f.line - 1]
    assert src[f.col:f.col + 7] == "1.09e-6"


def test_the_allowlist_is_empty_and_every_entry_would_name_an_owner():
    """An allowlist that is a bare set of paths is where defects go to be
    forgotten. This one is data with an owner and a reason per row, and it is
    currently EMPTY — so the day a row is added it appears in a diff rather
    than being absorbed into a widened predicate.
    """
    assert cp.ALLOWLIST == ()
    for a in cp.ALLOWLIST:                       # pragma: no cover - empty today
        assert a.owner and a.reason and a.path_suffix


# ==========================================================================
# DIRECTION 1 — IT FIRES. One case per syntactic position.
#
# The `2.6` case is the operator's own literal and it is caught through
# `Watched.also`, a spelling a HUMAN declared. Roundings are never INFERRED:
# 1026.0 rounded to two significant digits is 1000.0, and 1000.0 was MEASURED
# at 86 non-docstring occurrences in this tree, so an inferring fence would
# report 86 findings and zero defects.

_BAR = cp.Watched(2.61, "navalai.limits.DEMO_BAR", cp.Category.THRESHOLD,
                  spelling="2.61", also=(2.6,))

_POSITIONS = {
    "plain assignment":       ("X = 2.61\n", "assignment"),
    "binary expression":      ("X = 2.6 + Y\n", "binary expression"),
    "call argument":          ("foo(2.61)\n", "call argument"),
    "list element":           ("X = [2.61, Y]\n", "list element"),
    "dict value":             ('X = {"limit": 2.61}\n', "dict entry"),
    "nested call argument":   ("X = f(Y, 2.61)\n", "call argument"),
    "comprehension":          ("X = [v * 2.61 for v in vs]\n", "binary expression"),
    "conditional":            ("X = 2.61 if flag else Y\n", "conditional expression"),
    "default argument":       ("def g(a, b=2.61):\n    return a + b\n",
                               "default argument"),
    "nested helper":          ("def outer():\n"
                               "    def inner():\n"
                               "        return 2.61\n"
                               "    return inner\n", "return value"),
    "f-string expression":    ('X = f"{y / 2.61:.3g}"\n', "binary expression"),
    "keyword argument":       ("foo(limit=2.61)\n", "keyword argument"),
    "class attribute":        ("class C:\n    limit = 2.61\n", "assignment"),
    "augmented assignment":   ("X += 2.61\n", "augmented assignment"),
    "comparison":             ("if y > 2.61:\n    pass\n", "comparison"),
    "lambda body":            ("h = lambda z: z * 2.61\n", "binary expression"),
    "inside a string":        ('X = float("2.61")\n', "string literal"),
}


@pytest.mark.parametrize("name", sorted(_POSITIONS))
def test_a_forbidden_constant_is_caught_in_every_syntactic_position(name):
    src, position = _POSITIONS[name]
    findings = cp.scan_source(src, "crafted.py", (_BAR,))
    assert len(findings) == 1, f"{name}: expected 1 finding, got {findings}"
    f = findings[0]
    assert f.watched is _BAR
    assert f.position == position, f"{name}: reported position {f.position!r}"
    # file:line:col, and the column must point INTO the offending line
    assert f.path == "crafted.py"
    assert 1 <= f.line <= len(src.splitlines())
    assert f.col >= 0
    assert str(f).startswith(f"crafted.py:{f.line}:{f.col}: ")
    assert "navalai.limits.DEMO_BAR" in str(f)


def test_the_reported_line_and_column_land_on_the_literal():
    """`file:line:col` is only useful if it points at the number.

    Checked against the raw source text rather than trusted — the same rule
    that a truncating summariser broke on 2026-08-20 (LESSONS.md: check the
    artefact, not the summary of it).
    """
    src = ("def outer():\n"
           "    def inner(a, b=2.61):\n"
           "        return a + b\n")
    f, = cp.scan_source(src, "crafted.py", (_BAR,))
    line = src.splitlines()[f.line - 1]
    assert line[f.col:f.col + 4] == "2.61", repr(line[f.col:])


def test_the_historical_contract_line_fires_VERBATIM():
    """The exact text of the incident, and the exact predicate that missed it.

    `git show 99c02e2^:navalai/contract.py` line 438. A guard that was never
    made to fire on the input it must reject is not a guard.
    """
    offending = '            f"Re {speed_ms * lwl_m / 1.09e-6:.3g} "'
    src = "def receipt(speed_ms, lwl_m):\n    return (\n" + offending + "\n    )\n"

    # the PRE-2026-08-20 string predicate, reproduced: it required "=", and
    # this line has none, so it returned False on the defect it was hunting.
    stripped = offending.split("#")[0]
    assert not ("1.09e-6" in stripped and "=" in stripped
                and "import" not in stripped), (
        "the historical predicate is being reproduced wrongly — it must MISS "
        "this line, which is the whole point of the incident")

    findings = cp.scan_source(src, "navalai/contract.py")
    assert len(findings) == 1, findings
    assert findings[0].value == pytest.approx(1.09e-6)
    assert findings[0].watched.home == "navalai.constants.NU_FRESH_20C"
    assert findings[0].position == "binary expression"


def test_the_float_string_hole_the_ast_alone_would_have_opened():
    """Dropping to the AST would have LOST the one thing the string scan did
    for free: a constant smuggled through a string. Put back deliberately, and
    proven, rather than assumed.
    """
    f, = cp.scan_source('RHO = float("998.8")\n', "crafted.py")
    assert f.in_string and f.watched.home == "navalai.constants.RHO_FRESH_20C"


def test_a_string_match_is_bounded_and_not_a_bare_substring():
    """`"999.0" in "1999.0"` is True, and so is `"9.81" in "19.812"`. A match
    that is not the thing it claims to have matched is LESSONS.md defect
    class 1 — the same shape as `grep -c 'Failed'` counting lines. Measured at
    zero either way in this tree, so this is a fence built before it was
    needed rather than after a false finding.
    """
    assert not cp.scan_source('X = "1999.0 kg over 19.812 m"\n', "crafted.py")
    assert not cp.scan_source('X = "11026.0"\n', "crafted.py")
    f, = cp.scan_source('X = "rho is 1026.0 kg/m3"\n', "crafted.py")
    assert f.watched.home == "navalai.constants.RHO_SEA_15C_ITTC"


def test_a_respelt_constant_is_still_the_same_constant():
    """The string fence matched DIGITS; this one matches VALUES. `0.00000109`
    and `1.09E-6` are the same viscosity and the old scan saw neither.
    """
    for spelling in ("0.00000109", "1.09E-6", "1.090e-6", "109e-8"):
        findings = cp.scan_source(f"X = {spelling}\n", "crafted.py")
        assert len(findings) == 1, f"{spelling}: {findings}"
        assert findings[0].watched.home == "navalai.constants.NU_FRESH_20C"


# ==========================================================================
# DIRECTION 2 — IT STAYS SILENT. The goal is not to ban numbers.

_LEGITIMATE = """
import math

RATIO = 2
HALF = 0.5
THIRD_POWER = 3


def area(r):
    return math.pi * r ** 2.0


def two_thirds(x):
    return x ** (2.0 / 3.0)


def percent(a, b):
    return 100.0 * a / b


def close(a, b):
    return abs(a - b) < 1e-9


def to_tonnes(kg):
    return kg / 1000.0


def displacement(volume_m3, rho=1000.0):
    # the design fresh-water density is 1000.0 and it is UNFENCEABLE by value
    return volume_m3 * rho


def scale(x):
    return [x * 0.5, x * 2, x * 1.5, x / 3.0, x * 100.0]
"""


def test_legitimate_mathematics_produces_no_finding():
    """Sixteen mathematical and unit constants, none of them registered.

    1000.0 is in here on purpose: it IS `constants.RHO_FRESH`, and the policy
    deliberately refuses to fence it because it is also mm/m, kg/t and W/kW.
    A fence that flagged this file would be unusable, which is the difference
    between a policy and a ban.
    """
    findings = cp.scan_source(_LEGITIMATE, "legit.py")
    assert not findings, cp.report(findings)


def test_the_policy_refuses_to_watch_a_mathematical_constant():
    for v in (2, 3, 0.5, 1.5, 2.0, 100.0, 1000.0, 1e-9, 1e6, 0.25, 10.0, 0.1):
        assert not cp.is_distinctive(v), f"{v!r} would be fenced as physical"


def test_the_policy_does_watch_a_constant_that_can_only_be_one_thing():
    for v in (9.80665, 998.8, 1026.0, 1025.0, 1.13902e-6, 1.18831e-6,
              1.1883e-6, 1.09e-6, 1.14e-6):
        assert cp.is_distinctive(v), f"{v!r} is no longer fenceable"


def test_significant_digits_uses_the_shortest_roundtrip_spelling():
    """The first draft of this predicate used `f"{v:.17g}"`, for which
    `9.81` reads as `'9.8100000000000005'` — SEVENTEEN significant digits —
    and it concluded that 9.81 is distinctive. Measured and corrected before
    it shipped; pinned here so it cannot come back.
    """
    assert cp.significant_digits(9.81) == 3
    assert cp.significant_digits(9.80665) == 6
    assert cp.significant_digits(998.8) == 4
    assert cp.significant_digits(1026.0) == 4
    assert cp.significant_digits(1000.0) == 1
    assert cp.significant_digits(1.09e-6) == 3
    assert cp.significant_digits(1.13902e-6) == 6
    assert cp.significant_digits(0.5) == 1


def test_a_rounding_is_never_INFERRED():
    """1026.0 to two significant digits is 1000.0. If the fence inferred
    roundings it would flag every millimetre conversion in the tree — MEASURED
    at 86 occurrences of 1000.0 in `navalai/`, `scripts/` and `ui/`.
    """
    findings = cp.scan_source("X = 1000.0\nY = 1.1e-6\nZ = 9.8\n", "crafted.py")
    assert not findings, cp.report(findings)


def test_docstrings_and_comments_may_quote_a_measurement():
    """This repository records incidents by QUOTING their digits. A fence that
    fires on its own explanation is a scanner bug, not a finding — the charter
    `test_limits_single_source._code_lines` already had, now enforced by the
    parser instead of by `str.startswith('#')`.
    """
    src = ('"""The viscosity was 1.09e-6 and rho was 998.8."""\n'
           "\n"
           "\n"
           "def f():\n"
           '    """Measured at 9.80665 m/s^2 in 2026."""\n'
           "    return 1  # and g was 9.80665 here too\n")
    assert not cp.scan_source(src, "prose.py"), cp.report(
        cp.scan_source(src, "prose.py"))


def test_a_definition_site_is_not_a_finding():
    """`navalai/constants.py` is the home; the digits are allowed to exist
    there and nowhere else. The exclusion is BY HOME, carried on the Watched
    row, not by a hard-coded filename in the scanner.
    """
    home = _ROOT / cp.CONSTANTS_FILE
    assert not cp.scan_file(home, relative_to=_ROOT)
    # ...and the same text under any other name IS a pile of findings
    findings = cp.scan_source(home.read_text(), "navalai/elsewhere.py")
    assert len(findings) >= len(cp.physical_watch())


# ==========================================================================
# NOT WEAKER THAN THE FENCE IT REPLACES


def test_every_spelling_the_string_fence_hunted_is_still_watched():
    """The literal tuple from `test_limits_single_source`'s S18/C33 scans,
    reproduced here as the compatibility contract. If the AST fence stopped
    watching one of these it would be a SOFTENING, and softening a fence is
    the one move this project forbids outright.
    """
    inherited = ("9.80665", "998.8", "1.09e-6", "1.13902e-6",
                 "1.18831e-6", "1.1883e-6", "1026.0")
    watch = cp.physical_watch()
    for spelling in inherited:
        value = float(spelling)
        assert any(w.matches(value) for w in watch), (
            f"{spelling} was fenced by the string scan and is not watched now")


def test_the_ast_fence_watches_STRICTLY_MORE_than_the_string_fence_did():
    """Three constants the string scan never hunted, each measured at ZERO
    occurrences in the governed tree before being added: 1025.0
    (RHO_SEA_HOLTROP), 1.14e-6 (NU_FRESH_15C_ROUNDED), 9.81 (G_OPENFOAM) and
    999.0 (RHO_FRESH_15C). Adding a watch is only honest when the tree is
    measured clean for it first.
    """
    watch = cp.physical_watch()
    for value in (1025.0, 1.14e-6, 9.81, 999.0):
        assert any(w.matches(value) for w in watch), value


# ==========================================================================
# NO SECOND SOURCE — the fence must not become the defect it fences


def test_the_watch_set_is_PARSED_from_constants_and_matches_the_IMPORTED_module():
    """`physical_watch()` reads `navalai/constants.py` with `ast` rather than
    importing it, because it wants the SOURCE SPELLING as well as the value.
    Two readings of one file are two chances to disagree, so they are compared.
    """
    from navalai import constants

    for w in cp.physical_watch():
        name = w.home.rsplit(".", 1)[1]
        assert hasattr(constants, name), f"{w.home} does not exist"
        assert getattr(constants, name) == w.value, (
            f"{w.home}: parsed {w.value!r}, imported "
            f"{getattr(constants, name)!r}")
        assert float(w.spelling) == w.value


def test_constpolicy_holds_no_copy_of_any_value_it_fences():
    """The fence built to prevent a number being declared twice must not
    declare one. It names constants by NAME (`FORCE_WATCH`, `UNFENCEABLE`) and
    never by digits. Checked with the fence's own scanner, pointed at itself.
    """
    findings = cp.scan_file(_ROOT / "navalai" / "constpolicy.py",
                            relative_to=_ROOT)
    assert not findings, cp.report(findings)


def test_every_unfenceable_constant_says_WHY_and_the_reason_re_measures():
    """`UNFENCEABLE` claims 1000.0 occurs many times. LESSONS.md: verify the
    number before quoting it — so the count is re-derived here from the tree,
    not read out of the comment that asserts it.
    """
    from navalai import constants

    assert set(cp.UNFENCEABLE) == {"RHO_FRESH"}
    for name, reason in cp.UNFENCEABLE.items():
        assert hasattr(constants, name)
        assert len(reason) > 40, f"{name}: a reason, not a shrug"

    rho = cp.Watched(constants.RHO_FRESH, "navalai.constants.RHO_FRESH",
                     cp.Category.PHYSICAL, spelling=repr(constants.RHO_FRESH),
                     home_file=cp.CONSTANTS_FILE)
    hits = cp.scan_tree(watch=(rho,), apply_allowlist=False)
    assert len(hits) > 50, (
        f"RHO_FRESH now occurs {len(hits)} times, not the 87 measured on "
        "2026-08-20 (86 numeric literals plus one prose mention in "
        "constpolicy's own UNFENCEABLE reason) — if it has fallen to zero it "
        "is fenceable and belongs in the watch set")


def test_every_forced_watch_names_the_measurement_that_made_it_safe():
    from navalai import constants

    assert set(cp.FORCE_WATCH) == {"G_OPENFOAM", "RHO_FRESH_15C"}
    for name, why in cp.FORCE_WATCH.items():
        assert hasattr(constants, name)
        assert not cp.is_distinctive(getattr(constants, name)), (
            f"{name} is distinctive now and no longer needs forcing")
        assert "occurrence" in why and "2026-" in why


# ==========================================================================
# THE CATEGORIES ARE LOAD-BEARING, NOT DECORATION


def test_only_two_categories_are_fenced():
    fenced = {c for c in cp.Category if c.fenced}
    assert fenced == {cp.Category.PHYSICAL, cp.Category.THRESHOLD}
    assert not cp.Category.MATHEMATICAL.fenced
    assert not cp.Category.CONFIGURATION.fenced
    assert not cp.Category.EMPIRICAL.fenced


def test_a_threshold_gets_the_same_treatment_as_a_physical_constant():
    """The category changes the HOME named in the message, not the mechanism —
    otherwise `limits.py`'s bars would need a second scanner, which is the
    defect class this whole file exists to fence.
    """
    from navalai import limits

    bend = cp.Watched(limits.BEND_RADIUS_RATIO, "navalai.limits.BEND_RADIUS_RATIO",
                      cp.Category.THRESHOLD, spelling=repr(limits.BEND_RADIUS_RATIO))
    f, = cp.scan_source("t = 80.0 * 0.015\n", "crafted.py", (bend,))
    assert f.watched.category is cp.Category.THRESHOLD
    assert "navalai.limits.BEND_RADIUS_RATIO" in str(f)


# ==========================================================================
# THE SCANNER'S OWN HONESTY


def test_an_unparseable_file_is_an_error_and_never_a_clean_scan():
    """LESSONS.md defect class 1: an unmeasurable value must not score as a
    passing one. `${_MQ_SKEW:-0}` turned "could not measure" into "perfect";
    a swallowed `SyntaxError` would do exactly that here.
    """
    with pytest.raises(SyntaxError):
        cp.scan_source("def broken(:\n", "broken.py")


def test_the_scanner_reaches_every_governed_file():
    files = cp.python_files()
    assert len(files) > 50
    assert any(p.name == "contract.py" for p in files)
    assert any(p.parts[-2] == "scripts" for p in files)
    assert not any("__pycache__" in p.parts for p in files)
    for p in files:                      # every one of them parses
        ast.parse(p.read_text())


def test_tests_are_out_of_scope_by_declaration_not_by_accident():
    """A test that pins `rho == 1025.0` is the mechanism that catches the
    constant moving. MEASURED 2026-08-20: fencing `tests/` would report 54
    findings, every one of them a pin. Recorded so a later session widening
    the scope knows what it is walking into.
    """
    assert "tests" not in cp.DEFAULT_ROOTS
    pins = cp.scan_tree(subdirs=("tests",), apply_allowlist=False)
    assert len(pins) > 20, "the pins have gone — did the tests stop pinning?"
