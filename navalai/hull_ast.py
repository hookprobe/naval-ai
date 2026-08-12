"""Hull grammar AST + type checker (original plan, Phase 1: 'the grammar
dictates spatial allocation and structural limits before any CAD kernel is
invoked').

The flat 15-parameter vector stays the exchange format (fast, surrogate- and
DB-friendly). This module adds the hierarchy above it:

  HullDesign
    ├─ typology            (SHARP_CHINE | PRAM)  — dispatches its own rules
    ├─ Principal           LWL BWL T D
    ├─ Planform            p_bow p_stern x_mb r_transom
    ├─ SectionLaw          beta_mid beta_bow beta_len
    ├─ Profile             rocker forefoot
    └─ Topside             flare sheer_rise

Each node validates itself; the typology adds allocation rules on top; the
flat `grammar.check` remains the universal floor. A design type-checks only
if ALL levels pass — before any geometry is constructed.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum

import numpy as np

from . import grammar


class Typology(Enum):
    SHARP_CHINE = "sharp-chine"     # fine entry, warped bottom — coastal ability
    PRAM = "pram"                   # full bow, flat rocker — max volume, calm water


@dataclass(frozen=True)
class Principal:
    LWL: float
    BWL: float
    T: float
    D: float

    def validate(self) -> list[str]:
        v = []
        if not self.LWL > 0 or not self.BWL > 0:
            v.append("principal: non-positive dimensions")
        return v


@dataclass(frozen=True)
class Planform:
    p_bow: float
    p_stern: float
    x_mb: float
    r_transom: float

    def validate(self) -> list[str]:
        v = []
        if self.x_mb < 0.3:
            v.append("planform: max beam too far aft-of-amidships convention")
        return v


@dataclass(frozen=True)
class SectionLaw:
    beta_mid: float
    beta_bow: float
    beta_len: float

    def validate(self) -> list[str]:
        return ["sections: bow deadrise below midship"] if self.beta_bow < self.beta_mid else []


# TWO NODES HAVE NO NODE-LOCAL RULE, AND THEY NOW SAY SO BY NOT HAVING THE
# METHOD (gap E18).
#
# `Profile.validate` and `Topside.validate` both read `return []`
# unconditionally: a guard that cannot fire, which is defect class 3, and worse
# than an absent guard because `type_check`'s loop calls it and gets a clean
# answer back. MEASURED 2026-08-12 over 4000 `grammar.sample` vectors (all 4000
# `grammar.check`-valid): the node layer produced ZERO violations — not just
# these two, ALL FIVE — so nothing in it moved a single verdict. `Planform`'s
# `x_mb < 0.3` cannot fire at all while `PARAMS` bounds x_mb at [0.40, 0.68],
# and `SectionLaw`'s rule is `grammar.check`'s `deadrise.order` a second time.
#
# The rules these two nodes WOULD carry already have homes, and putting them
# here would be a number declared twice: `rocker`, `forefoot` and `sheer_rise`
# are banded per typology by `TYPOLOGY_RULES` below, `rocker` is relationally
# checked by `grammar.check`'s `transom.chine`, and every one of the four is
# bounded by `grammar.PARAMS`. Inventing a node-local threshold to fill the
# slot is how gap E4's four tautological constraints got written.
#
# So `type_check` asks for `validate` and skips a node that does not define it.
# The removal is deliberate and fenced: `tests/test_constraints_honest.py`
# refuses any validator whose body is an unconditional empty return, and the
# fence is aimed at the verbatim text that stood here.
@dataclass(frozen=True)
class Profile:
    rocker: float
    forefoot: float


@dataclass(frozen=True)
class Topside:
    flare: float
    sheer_rise: float


# typology -> parameter-subspace allocation + structural limits
TYPOLOGY_RULES: dict[Typology, dict] = {
    Typology.SHARP_CHINE: {
        "p_bow": (1.8, 4.0),        # fine entry demanded
        "forefoot": (0.4, 1.0),     # raked stem
        "beta_bow_min": 12.0,       # warped bottom forward for wave entry
    },
    Typology.PRAM: {
        "p_bow": (1.2, 1.8),        # full bow
        "forefoot": (0.0, 0.25),    # near-flat profile forward
        "rocker": (0.0, 0.35),
        "sheer_rise": (0.0, 0.25),
        "beta_bow_max": 25.0,       # pram bottoms stay flat-ish
    },
}


@dataclass(frozen=True)
class HullDesign:
    typology: Typology
    principal: Principal
    planform: Planform
    sections: SectionLaw
    profile: Profile
    topside: Topside

    # ---- AST <-> flat vector bridge ----

    def to_vector(self) -> np.ndarray:
        d = {}
        for node in (self.principal, self.planform, self.sections,
                     self.profile, self.topside):
            for f in fields(node):
                d[f.name] = getattr(node, f.name)
        return grammar.vector(d)

    @staticmethod
    def from_vector(x: np.ndarray, typology: Typology) -> "HullDesign":
        p = grammar.named(x)
        return HullDesign(
            typology,
            Principal(p["LWL"], p["BWL"], p["T"], p["D"]),
            Planform(p["p_bow"], p["p_stern"], p["x_mb"], p["r_transom"]),
            SectionLaw(p["beta_mid"], p["beta_bow"], p["beta_len"]),
            Profile(p["rocker"], p["forefoot"]),
            Topside(p["flare"], p["sheer_rise"]),
        )


def type_check(design: HullDesign) -> grammar.GateReport:
    """The grammar compiler front end: node rules -> typology allocation ->
    universal flat constraints. No geometry construction anywhere."""
    v: list[str] = []
    for node in (design.principal, design.planform, design.sections,
                 design.profile, design.topside):
        # A node with no node-local rule does not define `validate` (gap E18);
        # it does NOT define one that returns [] unconditionally. The two look
        # the same from here and are opposite claims: the first says "this
        # node's rules live elsewhere", the second says "this node has rules
        # and they all pass".
        rule = getattr(node, "validate", None)
        if rule is not None:
            v.extend(rule())

    rules = TYPOLOGY_RULES[design.typology]
    p = grammar.named(design.to_vector())
    for key, bound in rules.items():
        if key.endswith("_min"):
            name = key[:-4]
            if p[name] < bound:
                v.append(f"typology[{design.typology.value}]: {name} "
                         f"{p[name]:.2f} < {bound}")
        elif key.endswith("_max"):
            name = key[:-4]
            if p[name] > bound:
                v.append(f"typology[{design.typology.value}]: {name} "
                         f"{p[name]:.2f} > {bound}")
        else:
            lo, hi = bound
            if not (lo <= p[key] <= hi):
                v.append(f"typology[{design.typology.value}]: {key} "
                         f"{p[key]:.2f} outside [{lo}, {hi}]")

    flat = grammar.check(design.to_vector())
    v.extend(flat.violations)
    return grammar.GateReport(len(v) == 0, tuple(v))


def infer_typology(x: np.ndarray) -> Typology | None:
    """Which typology (if any) type-checks this vector? First match wins."""
    for t in Typology:
        if type_check(HullDesign.from_vector(x, t)).ok:
            return t
    return None
