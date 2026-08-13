"""Hull grammar AST + type checker (original plan, Phase 1: 'the grammar
dictates spatial allocation and structural limits before any CAD kernel is
invoked').

The flat 15-parameter vector stays the exchange format (fast, surrogate- and
DB-friendly). This module adds the hierarchy above it:

  HullDesign
    ├─ typology            (SHARP_CHINE | PRAM)  — dispatches its own rules
    ├─ Principal           LWL BWL T D
    ├─ FormTargets         Cp lcb                — the design curves (plate P1)
    ├─ Planform            x_mb r_transom
    ├─ SectionLaw          beta_mid beta_bow beta_len roundness
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
class FormTargets:
    """The design curves' targets — what the hull is ASKED to be (plate P1).

    No node-local rule, and that is the point: `Cp` and `lcb` are bounded by
    `grammar.PARAMS` (which takes those bounds from `limits.py`), banded per
    typology by `TYPOLOGY_RULES`, and refused by `grammar.check`'s
    `sac.target` when the shape family cannot reach them. A fourth opinion
    here would be gap E18's defect with a new node.
    """

    Cp: float
    lcb: float


@dataclass(frozen=True)
class Planform:
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
    roundness: float

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


@dataclass(frozen=True)
class Pin:
    """A typology parameter that is SET, not banded — and the two are different
    KINDS of rule, which is why this is a class and not a degenerate tuple.

    A BAND is a test the sampler is expected to satisfy sometimes: the generator
    proposes, `type_check` accepts or refuses, and a band of finite width has
    finite probability under a continuous sampler. A PIN is an ALLOCATION: the
    typology FIXES the value, so the generator must PROJECT a draw onto it
    (`project`) and `type_check` verifies it EXACTLY. Writing a pin as the band
    `(0.0, 0.0)` would be the same text expressing the opposite intent, and a
    continuous sampler hits a zero-width band with probability zero.

    THIS CLASS EXISTS BECAUSE THE PIPELINE DELIVERED ZERO DESIGNS (2026-08-13).
    `roundness` was banded at `(0.0, 0.15)` for SHARP_CHINE and `(0.0, 0.25)`
    for PRAM with the comment "a chine, not a bilge radius", while
    `unroll.hull_panels` refuses ANY `roundness > 0` — a filleted bilge is
    doubly curved and therefore not developable from flat sheet, which is a fact
    about sheet material and not a limitation of the unroller. The two bands and
    the unroller's admissible set are disjoint except at the single point
    `roundness == 0.0`. MEASURED over 4096 Builder genome draws
    (`sample_valid(80, MissionSpec(), seed=17)` -> `Genome.fit` -> `sample(4096,
    seed=1)`): **4** vectors type-checked as any typology, and NONE of them had
    `roundness == 0`, so every one of them was refused downstream by the
    unroller, by `engineer.assess` and by `admissibility`. The SHARP_CHINE
    clause histogram was roundness 4086, forefoot 2180, Cp 881, beta_bow 315 of
    4096. Projecting the pin instead of testing it takes the same 4096 draws to
    **1594** that type-check (see `tests/test_stageB.py::
    test_a_sheet_built_typology_pins_roundness_and_the_generator_projects_it`).

    `why` is carried on the pin so a refusal can say WHY the value is fixed
    rather than printing a bound. It is the pin's own sentence, not a second
    copy of the unroller's: `unroll.hull_panels` remains the one place that
    refuses a round bilge at the point of cutting, and it is untouched.
    """

    value: float
    why: str

    def holds(self, v: float) -> bool:
        # EXACT. `project` sets exactly this value, and the whole point of a pin
        # is that a hand-written vector at roundness 0.07 is REFUSED and named
        # rather than tolerated. A tolerance here would re-open the gap between
        # what the typology admits and what a sheet can be cut to.
        return float(v) == float(self.value)


# typology -> parameter-subspace allocation + structural limits
# `p_bow` IS GONE FROM THE GENOME (plate P1) AND BOTH RULES THAT USED IT ARE
# RE-EXPRESSED, NOT DROPPED. It was the chine plan-form's forward exponent, and
# both typologies used it as a proxy for how full the ends are — SHARP_CHINE
# demanding a fine entry at (1.8, 4.0), PRAM a full bow at (1.2, 1.8). The
# quantity they were reaching for is now a design target and can be stated
# directly: `Cp` is the prismatic coefficient, so a fine-ended hull is a low
# one and a full-ended hull is a high one, and the bands below are the same
# split of the same axis rather than a new rule.
#
# `roundness` is new and it is the rule these two typologies could never state:
# a SHARP CHINE typology could not previously require a sharp chine, because
# every hull the kernel could draw had one. It can now — and it states it as a
# `Pin`, not a band. BOTH members here are SHEET-BUILT forms and that is what
# licenses the pin: `formlib`'s `hard_chine_displacement` (ast_typology
# SHARP_CHINE) sells the family on being "buildable from flat sheet", and
# `pram_dory` (ast_typology PRAM) is the flat-bottom skiff the unroller exists
# for. A round-bilge hull remains fully expressible in this grammar — `roundness`
# is a free parameter of `grammar.PARAMS` and `geometry` draws the fillet — it is
# simply not one of THESE typologies, and being refused by `unroll.hull_panels`
# with "take this hull to a mould, not a cutter" is the right outcome for it.
_SHEET = ("a radiused bilge is a fillet, the filleted strip is doubly curved, "
          "and a doubly curved strip is not developable from flat sheet; this "
          "typology is sheet-built, so the bilge is a chine or it is a "
          "different typology")

TYPOLOGY_RULES: dict[Typology, dict] = {
    Typology.SHARP_CHINE: {
        "Cp": (0.525, 0.620),       # fine ends demanded
        "roundness": Pin(0.0, _SHEET),   # SET, not banded — see `Pin`
        "forefoot": (0.4, 1.0),     # raked stem
        "beta_bow_min": 12.0,       # warped bottom forward for wave entry
    },
    Typology.PRAM: {
        "Cp": (0.600, 0.710),       # full bow
        "roundness": Pin(0.0, _SHEET),   # SET, not banded — see `Pin`
        "forefoot": (0.0, 0.25),    # near-flat profile forward
        "rocker": (0.0, 0.35),
        "sheer_rise": (0.0, 0.25),
        "beta_bow_max": 25.0,       # pram bottoms stay flat-ish
    },
}


def pins(typology: Typology) -> dict[str, Pin]:
    """The pinned parameters of `typology` — the ONE reader of `TYPOLOGY_RULES`
    that knows what a pin is, so nothing else has to `isinstance`-test a rule."""
    return {k: v for k, v in TYPOLOGY_RULES[typology].items()
            if isinstance(v, Pin)}


def project(x: np.ndarray, typology: Typology) -> np.ndarray:
    """A COPY of `x` with every pinned parameter of `typology` SET to its pin.

    This is the generator-side half of a pin, and it is deliberately not part of
    `type_check`: projection decides what a draw BECOMES, verification decides
    what a vector IS. Nothing else about `x` is touched — a band violation is
    still a band violation after projection, and `project` never widens or
    repairs one.
    """
    y = np.array(x, dtype=float).copy()
    for key, pin in pins(typology).items():
        y[grammar.NAMES.index(key)] = float(pin.value)
    return y


@dataclass(frozen=True)
class HullDesign:
    typology: Typology
    principal: Principal
    targets: FormTargets
    planform: Planform
    sections: SectionLaw
    profile: Profile
    topside: Topside

    # ---- AST <-> flat vector bridge ----

    def to_vector(self) -> np.ndarray:
        d = {}
        for node in (self.principal, self.targets, self.planform,
                     self.sections, self.profile, self.topside):
            for f in fields(node):
                d[f.name] = getattr(node, f.name)
        return grammar.vector(d)

    @staticmethod
    def from_vector(x: np.ndarray, typology: Typology) -> "HullDesign":
        p = grammar.named(x)
        return HullDesign(
            typology,
            Principal(p["LWL"], p["BWL"], p["T"], p["D"]),
            FormTargets(p["Cp"], p["lcb"]),
            Planform(p["x_mb"], p["r_transom"]),
            SectionLaw(p["beta_mid"], p["beta_bow"], p["beta_len"],
                       p["roundness"]),
            Profile(p["rocker"], p["forefoot"]),
            Topside(p["flare"], p["sheer_rise"]),
        )


def type_check(design: HullDesign) -> grammar.GateReport:
    """The grammar compiler front end: node rules -> typology allocation ->
    universal flat constraints. No geometry construction anywhere."""
    v: list[str] = []
    for node in (design.principal, design.targets, design.planform,
                 design.sections, design.profile, design.topside):
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
        if isinstance(bound, Pin):
            # A PIN IS VERIFIED EXACTLY AND THE REFUSAL SAYS IT IS A PIN. Naming
            # a bound here ("outside [0.0, 0.15]") is what let the band and the
            # unroller's admissible set drift apart until the pipeline delivered
            # zero designs; a reader of that message would go looking for a
            # tolerance to widen. The generator is expected to have called
            # `project`, so reaching this line means a hand-written vector.
            if not bound.holds(p[key]):
                v.append(f"typology[{design.typology.value}]: {key} "
                         f"{p[key]:.4f} is PINNED at {bound.value:g} — "
                         f"{bound.why}")
        elif key.endswith("_min"):
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
    """Which typology (if any) type-checks this vector AS WRITTEN? First match
    wins. This is the strict verification question and it does NOT project —
    a generator that wants its draw projected calls `fit_typology`."""
    for t in Typology:
        if type_check(HullDesign.from_vector(x, t)).ok:
            return t
    return None


def fit_typology(x: np.ndarray) -> tuple[Typology, np.ndarray] | None:
    """PROJECT `x` onto each typology's pins in turn; the first that then
    type-checks wins. Returns `(typology, projected vector)`, or None.

    This is the generator's question — "what could this draw BE?" — and it is
    the one the design path must ask. `infer_typology` asks the verifier's
    question, "what IS this vector?", and stays strict: the projected vector
    that comes back from here satisfies `infer_typology` on its own, so nothing
    downstream has to trust that a projection happened.
    """
    for t in Typology:
        y = project(x, t)
        if type_check(HullDesign.from_vector(y, t)).ok:
            return t, y
    return None
