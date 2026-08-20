"""Numeric-literal POLICY — CATEGORISE literals, do not ban them.

THE MOTIVATING INCIDENT (2026-08-20, commit 99c02e2). `navalai/contract.py`
built a receipt as

    f"Re {speed_ms * lwl_m / 1.09e-6:.3g} "

with the kinematic viscosity typed inline. `tests/test_limits_single_source.py`
had listed ``"1.09e-6"`` among the constants it hunts for the ENTIRE life of
that line, and never fired: the scan required ``"=" in stripped``, so it only
ever saw ASSIGNMENTS. A physical constant used inside an EXPRESSION was
invisible to the fence built to find restated physical constants.

The same-day fix dropped the ``"="`` requirement. That is a STRING-LEVEL patch
to a STRUCTURAL problem, and it is fragile in both directions: it cannot see
``float("998.8")`` or ``1.0900e-6``, and it happily matches ``1026.0`` inside
``x[1026.0:]`` or inside prose. This module replaces it with `ast` analysis.

WHAT THIS MODULE IS NOT
-----------------------
It is NOT a ban on numbers. Most numeric literals in this codebase are correct
and must stay literal. The policy sorts a literal into one of five categories
and only two of them are fenced:

  * `Category.MATHEMATICAL` — 2, 0.5, 3, an exponent of 2.0/3.0, 100.0 for a
    percentage, 1e-9 for a tolerance. ALWAYS ALLOWED, everywhere, with no
    registration. There is no "one home" for the number two.
  * `Category.PHYSICAL` — g, rho, nu. FENCED. One home: `navalai/constants.py`.
  * `Category.CONFIGURATION` — a grid count, a port, a default plot width.
    Allowed where declared; not fenced by value (see the 1000.0 measurement
    below, which is why fencing them by value is impossible).
  * `Category.EMPIRICAL` — a measured watermark (a drag coefficient, a mesh
    quality figure). Allowed in COMMENTS and DOCSTRINGS, which is where this
    repository records measurements; a live code literal carrying one belongs
    in the ledger or in a named constant.
  * `Category.THRESHOLD` — an arbitrary engineering bar (a GM floor, a
    freeboard floor, a bend-radius ratio). FENCED when registered. One home:
    `navalai/limits.py`.

Comments never reach the AST at all, and DOCSTRINGS are skipped explicitly, so
the module that EXPLAINS an incident may keep quoting its digits. That is the
same charter `tests/test_limits_single_source._code_lines` had; it is now
enforced by the parser instead of by `str.startswith("#")`.

THIS MODULE HOLDS NO COPIES OF ANY VALUE IT FENCES
--------------------------------------------------
`physical_watch()` PARSES `navalai/constants.py` and takes the value, the name
and the SOURCE SPELLING from the assignment itself. Retyping ``9.80665`` here
would be this repository's signature defect committed by the fence built to
prevent it. `test_constpolicy.py` asserts the parsed set equals the IMPORTED
module attribute by attribute.

WHICH PHYSICAL CONSTANTS CAN BE FENCED BY VALUE — AND THE ONE THAT CANNOT
-------------------------------------------------------------------------
A value is only fenceable by value if seeing those digits anywhere else is, by
itself, evidence of a restatement. `is_distinctive()` is that test: four or
more significant digits, OR a magnitude at least five decades from unity and
not a bare power of ten.

MEASURED 2026-08-20 across `navalai/`, `scripts/` and `ui/` (excluding
`constants.py`), counting non-docstring numeric literals:

    1000.0  (RHO_FRESH)       86 occurrences  -> NOT fenceable
    999.0   (RHO_FRESH_15C)    0 occurrences
    9.81    (G_OPENFOAM)       0 occurrences

(Re-run today the count reads 87, and the extra one is this file's own prose
inside `UNFENCEABLE` below. Said out loud rather than rounded away, because a
count quoted without its scope is how a measurement starts drifting.)

`RHO_FRESH` is 1000.0, and 1000.0 is also mm-per-metre, kg-per-tonne and
W-per-kW. Fencing it by value would produce 86 findings, none of them the
defect. It is therefore explicitly OPTED OUT, by name, with that number
recorded — an unfenceable constant declared out loud beats a fence quietly
tuned until it passes. `G_OPENFOAM` (9.81) and `RHO_FRESH_15C` (999.0) fall
below the distinctiveness bar too, but measure ZERO occurrences, so they are
explicitly OPTED IN.

ROUNDED SPELLINGS ARE DECLARED, NEVER INFERRED
-----------------------------------------------
A laundered second copy of a constant is usually a ROUNDING of it, and this
repository already carries a pair: `NU_SEA_15C` 1.18831e-6 and
`NU_SEA_HOLTROP` 1.1883e-6. Both are separate NAMES in `constants.py`, so
reflection covers them. Inferring roundings instead would be a disaster with a
measurement behind it: 1026.0 rounded to two significant digits is 1000.0, and
1000.0 occurs 86 times. `Watched.also` therefore holds spellings a HUMAN
declared, and `physical_watch()` declares none.
"""

from __future__ import annotations

import ast
import enum
import math
import pathlib
import re
from dataclasses import dataclass

_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: The directories this fence governs. `tests/` is deliberately EXCLUDED: a
#: test that asserts ``rho == 1025.0`` is a PIN, which is the opposite of a
#: restatement — it is the mechanism that catches the constant moving. This is
#: the same scope the string-level fence it replaces had.
DEFAULT_ROOTS: tuple[str, ...] = ("navalai", "scripts", "ui")

#: The file that owns the physical constants. A literal here is a definition.
CONSTANTS_FILE = pathlib.Path("navalai") / "constants.py"


class Category(enum.Enum):
    """What KIND of number a literal is. See the module docstring."""

    MATHEMATICAL = "mathematical"
    PHYSICAL = "physical"
    CONFIGURATION = "configuration"
    EMPIRICAL = "empirical"
    THRESHOLD = "threshold"

    @property
    def fenced(self) -> bool:
        """Whether a literal of this category needs a single source."""
        return self in (Category.PHYSICAL, Category.THRESHOLD)


# --------------------------------------------------------------------------
# The distinctiveness policy


def significant_digits(value: float) -> int:
    """Significant digits of the SHORTEST round-tripping spelling of `value`.

    `repr` is used, not a format string: ``f"{9.81:.17g}"`` is
    ``'9.8100000000000005'`` and would score 9.81 as seventeen significant
    digits, which is how a first draft of this predicate concluded that 9.81
    is distinctive. Measured and corrected before it shipped.
    """
    s = repr(abs(float(value)))
    if "e" in s or "E" in s:
        s = s.replace("E", "e").split("e")[0]
    s = s.replace(".", "").lstrip("0")
    return len(s.rstrip("0")) or 1


def is_power_of_ten(value: float) -> bool:
    if value == 0.0:
        return False
    lg = math.log10(abs(float(value)))
    return abs(lg - round(lg)) < 1e-12


def is_distinctive(value: float) -> bool:
    """Can these digits be fenced by VALUE alone?

    Two ways to earn it, and both mean "no mathematical or unit constant looks
    like this":

      * four or more significant digits (998.8, 1026.0, 9.80665, 1.13902e-6);
      * a magnitude at least five decades from unity and not a bare power of
        ten (1.09e-6 has three significant digits, but nothing in this
        codebase is one-point-oh-nine microanything except a viscosity).

    It deliberately REFUSES 0.5, 2, 3, 100.0, 1e-9 and 1000.0.
    """
    v = abs(float(value))
    if v == 0.0:
        return False
    if significant_digits(v) >= 4:
        return True
    return abs(math.log10(v)) >= 5.0 and not is_power_of_ten(v)


#: Physical constants fenced DESPITE failing `is_distinctive`, each with the
#: measured occurrence count that makes it safe. See the module docstring.
FORCE_WATCH: dict[str, str] = {
    "G_OPENFOAM": "0 occurrences measured in navalai/, scripts/, ui/ (2026-08-20)",
    "RHO_FRESH_15C": "0 occurrences measured in navalai/, scripts/, ui/ (2026-08-20)",
}

#: Physical constants that CANNOT be fenced by value, with the reason. Kept as
#: data rather than as prose so the next session can re-measure the number
#: instead of re-deriving the argument.
UNFENCEABLE: dict[str, str] = {
    "RHO_FRESH": "1000.0 is also mm/m, kg/t and W/kW — 86 non-docstring "
                 "numeric occurrences measured in navalai/, scripts/, ui/ "
                 "on 2026-08-20 (87 reported, the extra one being this very "
                 "sentence). "
                 "A value fence here would produce 86 findings and zero "
                 "defects. Needs a structural fence (an assignment whose "
                 "target names a density), which does not exist yet.",
}


# --------------------------------------------------------------------------
# What is watched


@dataclass(frozen=True)
class Watched:
    """One number that has exactly one home."""

    value: float
    home: str                       # e.g. "navalai.constants.NU_FRESH_20C"
    category: Category
    spelling: str = ""              # the literal text at the definition site
    also: tuple[float, ...] = ()    # DECLARED alternate spellings, never inferred
    home_file: pathlib.Path | None = None

    def matches(self, value: float) -> bool:
        return float(value) == self.value or float(value) in self.also

    @property
    def spellings(self) -> tuple[str, ...]:
        out = [self.spelling] if self.spelling else []
        out += [repr(self.value)] + [repr(a) for a in self.also]
        # a spelling with an exponent has two conventional forms; a str-literal
        # search must see both, e.g. float("1.09e-6") and float("1.09e-06").
        for s in tuple(out):
            if "e-0" in s:
                out.append(s.replace("e-0", "e-"))
            elif "e-" in s:
                head, _, tail = s.partition("e-")
                if len(tail) == 1:
                    out.append(f"{head}e-0{tail}")
        return tuple(dict.fromkeys(out))


def _module_level_numbers(path: pathlib.Path) -> list[tuple[str, float, str]]:
    """(name, value, source spelling) for every module-level numeric constant."""
    src = path.read_text()
    tree = ast.parse(src)
    out: list[tuple[str, float, str]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if not (isinstance(value, ast.Constant)
                and isinstance(value.value, (int, float))
                and not isinstance(value.value, bool)):
            continue
        for t in targets:
            if isinstance(t, ast.Name):
                seg = ast.get_source_segment(src, value) or ""
                out.append((t.id, float(value.value), seg.strip()))
    return out


def physical_watch(root: pathlib.Path | None = None) -> tuple[Watched, ...]:
    """The physical constants that can be fenced by value.

    Derived by PARSING `navalai/constants.py`, so no value, name or spelling is
    copied into this module. `UNFENCEABLE` names are dropped; `FORCE_WATCH`
    names are kept even when `is_distinctive` refuses them.
    """
    root = pathlib.Path(root) if root is not None else _ROOT
    home_file = root / CONSTANTS_FILE
    out = []
    for name, value, spelling in _module_level_numbers(home_file):
        if name.startswith("_") or name in UNFENCEABLE:
            continue
        if not (is_distinctive(value) or name in FORCE_WATCH):
            continue
        out.append(Watched(value=value, home=f"navalai.constants.{name}",
                           category=Category.PHYSICAL, spelling=spelling,
                           home_file=CONSTANTS_FILE))
    return tuple(out)


# --------------------------------------------------------------------------
# Findings


@dataclass(frozen=True)
class Finding:
    """A watched value found in a position where it is a second declaration."""

    path: str
    line: int
    col: int
    value: float
    watched: Watched
    position: str          # the AST context, e.g. "call argument"
    in_string: bool = False

    def __str__(self) -> str:
        where = "inside a string literal" if self.in_string else self.position
        return (f"{self.path}:{self.line}:{self.col}: {self.value!r} "
                f"({where}) — import {self.watched.home}")


@dataclass(frozen=True)
class Allowance:
    """An offender this fence knows about and is NOT responsible for fixing.

    Kept as data with a named owner so it appears in a diff. An allowlist that
    is a bare set of paths is a place defects go to be forgotten.
    """

    path_suffix: str
    value: float
    owner: str
    reason: str

    def covers(self, f: Finding) -> bool:
        return f.path.endswith(self.path_suffix) and float(f.value) == self.value


#: MEASURED EMPTY 2026-08-20: the AST fence over `navalai/`, `scripts/` and
#: `ui/` finds zero offenders, so there is nothing to allow. The list ships
#: anyway, and `test_constpolicy.py` asserts it is empty — so the day one is
#: added, the addition is visible in a diff with an owner attached rather than
#: absorbed into a widened predicate.
ALLOWLIST: tuple[Allowance, ...] = ()


# --------------------------------------------------------------------------
# The scanner


_POSITION = {
    ast.Assign: "assignment",
    ast.AnnAssign: "annotated assignment",
    ast.AugAssign: "augmented assignment",
    ast.BinOp: "binary expression",
    ast.UnaryOp: "unary expression",
    ast.BoolOp: "boolean expression",
    ast.Compare: "comparison",
    ast.Call: "call argument",
    ast.keyword: "keyword argument",
    ast.List: "list element",
    ast.Tuple: "tuple element",
    ast.Set: "set element",
    ast.Dict: "dict entry",
    ast.IfExp: "conditional expression",
    ast.comprehension: "comprehension",
    ast.ListComp: "comprehension",
    ast.DictComp: "comprehension",
    ast.SetComp: "comprehension",
    ast.GeneratorExp: "comprehension",
    ast.Return: "return value",
    ast.arguments: "default argument",
    ast.Subscript: "subscript",
    ast.Slice: "slice bound",
    ast.FormattedValue: "f-string expression",
    ast.JoinedStr: "f-string expression",
    ast.Lambda: "lambda body",
    ast.Starred: "starred element",
    ast.Yield: "yield value",
}


def spelling_in_string(text: str, watched: "Watched") -> bool:
    """Is one of `watched`'s spellings present in `text` as a WHOLE number?

    Bounded on both sides, because a bare substring test reads "999.0" out of
    "1999.0" and "9.81" out of "19.812". That is the same class of error as
    `grep -c 'Failed'` counting lines (LESSONS.md defect class 1): a match that
    is not the thing it claims to have matched. Measured at zero occurrences
    either way in this tree today, so the tightening costs nothing now and
    stops a false finding later.
    """
    for s in watched.spellings:
        if re.search(r"(?<![0-9.])" + re.escape(s) + r"(?![0-9])", text):
            return True
    return False


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """`id()` of every Constant that is a module/class/function docstring.

    Docstrings QUOTE measurements on purpose — that is how an incident stays
    readable — so they are not code and are never scanned.
    """
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def _parents(tree: ast.AST) -> dict[int, ast.AST]:
    out: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            out[id(child)] = node
    return out


def _position_of(node: ast.AST, parents: dict[int, ast.AST]) -> str:
    """The narrowest named AST context containing `node`.

    Walks OUTWARD, not just one step: the literal in ``def g(a, b=2.61)`` sits
    under `ast.arguments`, and the one in ``[v * 2.61 for v in vs]`` sits under
    a `BinOp` inside a `ListComp`. Reporting "binary expression" there is not
    wrong, so the first named ancestor wins and the walk stops.
    """
    cur = parents.get(id(node))
    while cur is not None:
        name = _POSITION.get(type(cur))
        if name is not None:
            return name
        cur = parents.get(id(cur))
    return "module body"


def scan_source(source: str, path: str,
                watch: tuple[Watched, ...] | None = None,
                *, scan_strings: bool = True) -> list[Finding]:
    """Every watched value used as a live literal in `source`.

    Both halves of "live" matter:

      * a NUMERIC literal anywhere in an expression — the incident this module
        exists for was a division inside an f-string, which the string-level
        fence could not see and `ast` reaches like any other BinOp;
      * a watched SPELLING inside a non-docstring STRING literal, which closes
        ``float("998.8")``. The string-level fence caught that by accident;
        dropping to the AST would have lost it, so it is put back deliberately.
    """
    if watch is None:
        watch = physical_watch()
    tree = ast.parse(source, filename=path)
    docs = _docstring_nodes(tree)
    parents = _parents(tree)
    home_here = [w for w in watch
                 if w.home_file is not None and path.endswith(str(w.home_file))]
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or id(node) in docs:
            continue
        value = node.value
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            for w in watch:
                if w in home_here:
                    continue
                if w.matches(value):
                    findings.append(Finding(
                        path=path, line=node.lineno, col=node.col_offset,
                        value=float(value), watched=w,
                        position=_position_of(node, parents)))
        elif scan_strings and isinstance(value, str):
            for w in watch:
                if w in home_here:
                    continue
                if spelling_in_string(value, w):
                    findings.append(Finding(
                        path=path, line=node.lineno, col=node.col_offset,
                        value=w.value, watched=w,
                        position="string literal", in_string=True))
                    break
    findings.sort(key=lambda f: (f.line, f.col, f.watched.home))
    return findings


def scan_file(path: pathlib.Path, watch: tuple[Watched, ...] | None = None,
              *, relative_to: pathlib.Path | None = None,
              **kw) -> list[Finding]:
    path = pathlib.Path(path)
    shown = str(path.relative_to(relative_to)) if relative_to else str(path)
    return scan_source(path.read_text(), shown, watch, **kw)


def python_files(root: pathlib.Path | None = None,
                 subdirs: tuple[str, ...] = DEFAULT_ROOTS) -> list[pathlib.Path]:
    root = pathlib.Path(root) if root is not None else _ROOT
    out: list[pathlib.Path] = []
    for sub in subdirs:
        d = root / sub
        if not d.is_dir():
            continue
        out += [p for p in d.rglob("*.py") if "__pycache__" not in p.parts]
    return sorted(out)


def scan_tree(root: pathlib.Path | None = None,
              subdirs: tuple[str, ...] = DEFAULT_ROOTS,
              watch: tuple[Watched, ...] | None = None,
              *, apply_allowlist: bool = True) -> list[Finding]:
    """Findings across the governed tree, `file:line:col` in every one.

    A file that does not PARSE is a finding of its own, not a silent skip —
    LESSONS.md defect class 1: an unmeasurable metric must never score as a
    passing one. It is raised, because a syntax error in this tree is a
    different emergency.
    """
    root = pathlib.Path(root) if root is not None else _ROOT
    if watch is None:
        watch = physical_watch(root)
    out: list[Finding] = []
    for p in python_files(root, subdirs):
        out += scan_file(p, watch, relative_to=root)
    if apply_allowlist:
        out = [f for f in out
               if not any(a.covers(f) for a in ALLOWLIST)]
    return out


def report(findings: list[Finding]) -> str:
    return "\n  ".join(str(f) for f in findings)


if __name__ == "__main__":  # pragma: no cover - operator convenience
    import sys

    fs = scan_tree()
    for f in fs:
        print(f)
    print(f"{len(fs)} finding(s) over {len(python_files())} files; "
          f"{len(physical_watch())} watched value(s)")
    sys.exit(1 if fs else 0)
