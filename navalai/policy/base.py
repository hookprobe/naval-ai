"""The typed constant every policy statement is made of, and the one error.

WHY THIS IS NOT `refdata.RefValue`
----------------------------------
`navalai/refdata/__init__.py` already answers "where did this number come
from?" with `RefValue{value, unit, source, basis}` and a CLOSED vocabulary,
`BASES = ('standard-2003', 'approx', 'purchased')`. Every member of that
vocabulary is a claim about a TECHNICAL document we transcribed or still owe.

A governance constant has two kinds of provenance that vocabulary cannot
express, and the difference between them is the whole point of BuildPlan 3
§2.2:

  * a clause of law, which the owner may not relax at any price, and
  * the owner's own preference, which the owner may relax tomorrow.

Widening `refdata.BASES` with 'policy' would let a preference wear the same
badge as a transcribed standard number, and the reader of a `RefValue` would
lose the ability to tell "ISO says 0.45" from "we prefer 0.45". So policy
constants carry their own type with their own vocabulary, and the two sets are
DISJOINT on purpose (`tests/test_policy.py` asserts it).

What is NOT duplicated is any number. Nothing in this package restates a value
that `navalai/limits.py` owns; the ratchet reads them through `getattr` at
compile time — see `compiler.RATCHETS`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# 'directive'  transcribed from the text of an EU Directive. Today that is
#              Directive 2013/53/EU (recreational craft), CELEX 32013L0053.
# 'regulation' transcribed from the text of an EU Regulation. Today that is
#              Regulation (EU) 2024/1689 (AI Act).
# 'policy'     the OWNER's preference. Not law, not physics, not a standard.
#              The owner may relax it; the legal envelope and the floors in
#              `limits.py` they may not. BuildPlan 3 §2.2, verbatim: "these are
#              preference constraints, not safety constraints".
# 'derived'    computed here from another PolicyValue or from `limits.py`.
#              Never typed by hand — if you can type the digits, it is not
#              derived.
BASES = ("directive", "regulation", "policy", "derived")

# A source has to identify a document and a clause, not gesture at one. The bar
# is `tests/test_refdata.py`'s (len > 20) applied to this package, so a
# governance constant cannot be cited more loosely than a freeboard number.
MIN_SOURCE_CHARS = 20


class PolicyError(ValueError):
    """A constitution that cannot be compiled.

    Raised at COMPILE TIME, which is the entire mechanism of Gate V3.0(b).
    BuildPlan 3 §2.2, verbatim: "A policy that would loosen any floor in
    `limits.py` is a policy ERROR, rejected when the constitution is compiled —
    not a runtime override, not a warning, not a note."

    A warning would be the wrong shape for a reason this codebase has already
    paid for: `translate.py`'s design-category ratchet exists because an LLM
    returning `{"design_category": "D"}` on an ocean brief relaxed a stability
    bar by 42% and nothing downstream could tell. A policy file is a MORE
    trusted input than an LLM, not a less trusted one, so it gets a harder
    refusal, not a softer one.
    """


class PolicyRefusal(RuntimeError):
    """A routing question this tool is not entitled to answer.

    Distinct from `PolicyError`: the constitution is well-formed, but the craft
    it describes falls outside the text we can read (e.g. outside the RCD's own
    2.5-24 m scope). The honest answer is a refusal naming the clause, never a
    delivery mode chosen because one of three had to be returned.
    """


@dataclass(frozen=True)
class PolicyValue:
    """One governance constant, with the provenance that makes it usable.

    `value` may be a scalar, a bool, a tuple (a band), or a frozenset (a
    palette). `unit` is '-' for dimensionless factors and '' for flags and
    enumerations, matching `refdata.RefValue`'s convention so a reader moving
    between the two packages does not have to learn a second one.
    """

    value: Any
    unit: str
    source: str
    basis: str
    note: str = ""

    def __post_init__(self) -> None:
        if not str(self.source).strip():
            raise PolicyError(
                "a policy constant with no source is a remembered number; cite "
                "the article, the clause or the owner decision that fixed it")
        if len(str(self.source).strip()) < MIN_SOURCE_CHARS:
            raise PolicyError(
                f"source {self.source!r} is {len(str(self.source).strip())} "
                f"characters — it names no document. A governance constant may "
                f"not be cited more loosely than a freeboard number "
                f"(tests/test_refdata.py holds the same bar).")
        if self.basis not in BASES:
            raise PolicyError(f"basis {self.basis!r} not in {BASES}")
        if self.unit is None:
            raise PolicyError("unit must be given ('-' dimensionless, '' flag)")

    def __float__(self) -> float:
        return float(self.value)


def constants(module) -> dict[str, PolicyValue]:
    """Every PolicyValue a module exposes, keyed by a dotted path.

    Walks into dicts, tuples, lists and dataclass instances so that nested
    values — a floor inside a `DesignDNA`, a row inside a table — are
    ENUMERATED rather than missed. Gate V3.0(a) is only worth anything if the
    walk sees every value.

    `refdata.constants` does the same job for `RefValue` and cannot be reused:
    it filters on `isinstance(obj, RefValue)`, so pointing it at this package
    returns an empty dict — which would pass every "all constants carry a
    source" assertion by vacuous truth. That failure mode is why this walker
    exists rather than an import.
    """
    out: dict[str, PolicyValue] = {}
    seen: set[int] = set()

    def walk(name: str, obj: Any) -> None:
        if isinstance(obj, PolicyValue):
            out[name] = obj
            return
        if id(obj) in seen:
            return
        if isinstance(obj, dict):
            seen.add(id(obj))
            for k, v in obj.items():
                walk(f"{name}.{k}", v)
        elif isinstance(obj, (list, tuple, set, frozenset)):
            seen.add(id(obj))
            for i, v in enumerate(sorted(obj, key=repr)
                                 if isinstance(obj, (set, frozenset)) else obj):
                walk(f"{name}[{i}]", v)
        elif hasattr(obj, "__dataclass_fields__") and not isinstance(obj, type):
            seen.add(id(obj))
            for f in obj.__dataclass_fields__:
                walk(f"{name}.{f}", getattr(obj, f))

    for name, obj in vars(module).items():
        if name.startswith("_"):
            continue
        walk(name, obj)
    return out


__all__ = ["BASES", "MIN_SOURCE_CHARS", "PolicyError", "PolicyRefusal",
           "PolicyValue", "constants"]
