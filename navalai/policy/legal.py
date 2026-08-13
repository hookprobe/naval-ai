"""The legal box, machine-checkable: RCD Art. 20 routing and the AI Act coupling.

ASSESSMENT AID. This module routes conformity-assessment work and cites the
clause that routed it. It is NOT legal advice and NOT a compliance claim, and
it answers no question that requires a lawyer — see `AiActConsequence`, where
the one such question is recorded as OPEN and left open.

WHAT THIS ENCODES, AND WHERE IT CAME FROM
-----------------------------------------
Directive 2013/53/EU (recreational craft and personal watercraft),
CELEX 32013L0053. Article 20(1) is a table, not a sentence: it fixes the
available conformity-assessment modules per DESIGN CATEGORY and per HULL-LENGTH
BAND, and only some of those cells contain Module A (internal production
control = self-certification, no notified body).

    category      hull length      Module A available?
    A, B          2.5 - <12 m      no   (A1, B+C/D/E/F, G, H)   Art. 20(1)(a)(i)
    A, B          12 - 24 m        no   (B+C/D/E/F, G, H)       Art. 20(1)(a)(ii)
    C             2.5 - <12 m      YES, but only where the harmonised standards
                                   relating to points 3.2 and 3.3 of Part A of
                                   Annex I (stability/freeboard and
                                   buoyancy/flotation) are complied with;
                                   otherwise A1/B+/G/H          Art. 20(1)(b)(i)
    C             12 - 24 m        no   (B+C/D/E/F, G, H)       Art. 20(1)(b)(ii)
    D             2.5 - 24 m       YES, unconditionally         Art. 20(1)(c)

WHERE THIS TABLE DISAGREES WITH BuildPlan3 §0, AND WHY THE TABLE WINS
---------------------------------------------------------------------
`BuildPlan3-MissionToOrder.md` §0 summarises Art. 20 as "**Categories A and B,
and anything 12-24 m**, require a notified body". That is correct for
categories A, B and C and WRONG for category D: Art. 20(1)(c) gives category D
the whole 2.5-24 m band on Module A, with no length break at 12 m.

CLAUDE.md's first rule for deciding what is true is "a measurement beats a
document, and a document beats an intention", and the primary text is the
measurement here. So `ART_20` encodes the Directive and `DISCREPANCIES` records
the disagreement rather than silently resolving it — a summary that has been
quietly corrected is indistinguishable from one that was never checked.

The correction does NOT weaken §0's headline result. §0's self-certifiable
envelope (LH < 12 m AND category in {C, D} AND harmonised standards applied) is
a strict SUBSET of the Module A cells above, so it remains a SUFFICIENT
condition for "no notified body". It is simply not a NECESSARY one, and the
platform should not tell a category D builder at 15 m that they need a notified
body when Art. 20(1)(c) says they do not. Over-routing is still routing wrongly.

THE COUPLING THAT NO PHYSICS GATE CAN SEE
-----------------------------------------
Regulation (EU) 2024/1689 (AI Act) Art. 6(1) makes an AI system high-risk only
where BOTH:
  (a) it is a safety component of — or is — a product covered by the Union
      harmonisation legislation listed in Annex I, AND
  (b) that product is required to undergo a THIRD-PARTY conformity assessment
      with a view to being placed on the market or put into service.
Annex I Section A item 3 is Directive 2013/53/EU.

So the module routing above decides (b) for us: route to a notified body and
Art. 6(1)(b) is satisfied; stay in Module A, or stay outside the Directive
under Art. 2(2)(a)(vii), and it is not. Condition (a) is a legal judgement
about what this platform IS, and it is not ours to make — see
`SAFETY_COMPONENT_QUESTION`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..limits import RCD_HULL_LENGTH_SCOPE_M
from ..rules import DISCLAIMER as _RULES_DISCLAIMER
from .base import PolicyError, PolicyRefusal, PolicyValue

# Composed, not retyped. The rules tier already ships the sentence that keeps an
# assessment aid from reading as a certificate; governance needs the same
# sentence plus one clause about legal advice, and a second independent copy of
# the first half would drift the way the GM floor did.
DISCLAIMER = (
    f"{_RULES_DISCLAIMER}. Conformity-module routing cites clauses and routes "
    f"work; it is NOT legal advice and NOT a compliance claim.")

_RCD = ("Directive 2013/53/EU on recreational craft and personal watercraft, "
        "CELEX 32013L0053")
_AI_ACT = "Regulation (EU) 2024/1689 (Artificial Intelligence Act)"

# --------------------------------------------------------------- the clauses

# The Directive applies to 'recreational craft', defined by hull length. Outside
# this band the RCD is not the instrument that governs the craft, and this
# module REFUSES to route rather than picking one of three modes because one of
# three had to be returned.
# The tuple moved to `limits.py` on 2026-08-14 and is IMPORTED here. It was
# declared once, correctly, in this file — and then `grammar.PARAMS` needed the
# same band as its LWL box, and the ladder may never import `navalai.policy`.
# So the number went DOWN to the module both layers may see, rather than being
# retyped in the one that could not reach it.
RCD_SCOPE_LENGTH_M = PolicyValue(
    RCD_HULL_LENGTH_SCOPE_M, "m",
    f"{_RCD}, Art. 3(2) — 'recreational craft' means any watercraft intended "
    f"for sport and leisure purposes of hull length from 2,5 m to 24 m",
    "directive")

# The length at which categories A, B and C leave the Module A / A1 band. It is
# NOT a general 12 m rule: category D crosses it untouched (Art. 20(1)(c)).
MODULE_A_LENGTH_BREAK_M = PolicyValue(
    12.0, "m",
    f"{_RCD}, Art. 20(1)(a)(i)/(ii) and 20(1)(b)(i)/(ii) — the hull length at "
    f"which categories A, B and C move from the 2.5-<12 m row to the 12-24 m "
    f"row, and the 12-24 m row contains no Module A cell",
    "directive")

OWN_USE_EMBARGO_YEARS = PolicyValue(
    5.0, "year",
    f"{_RCD}, Art. 2(2)(a)(vii) — watercraft built for own use are outside the "
    f"Directive 'provided that they are not subsequently placed on the Union "
    f"market during a period of five years from the putting into service of "
    f"the watercraft'",
    "directive")

OWN_USE_RESALE_CLAUSE = PolicyValue(
    True, "",
    f"{_RCD}, Art. 19(4) — 'Any person placing on the market a watercraft "
    f"built for own use before the end of the five-year period referred to in "
    f"point (vii) of point (a) of Article 2(2) shall apply the procedure "
    f"referred to in Article 23 before placing the product on the market'; "
    f"Art. 23 -> Annex V (Module PCA), under which the person 'shall lodge an "
    f"application for a post-construction assessment of the product with a "
    f"notified body'",
    "directive",
    note="So the own-use route is out of scope only while it stays own use, "
         "and a sale inside five years acquires a notified body after the "
         "boat is built — the most expensive moment to acquire one.")

HARMONISED_STANDARDS_CLAUSE = PolicyValue(
    True, "",
    f"{_RCD}, Art. 20(1)(b)(i) — category C craft of hull length 2.5 to <12 m "
    f"may use Module A only 'where the harmonised standards relating to points "
    f"3.2 and 3.3 of Part A of Annex I are complied with' (3.2 stability and "
    f"freeboard, 3.3 buoyancy and flotation); where they are not, the "
    f"available modules start at A1",
    "directive")

AI_ACT_ANNEX_I_ITEM = PolicyValue(
    3, "",
    f"{_AI_ACT}, Annex I Section A item 3 — Directive 2013/53/EU is item 3 of "
    f"the Union harmonisation legislation listed in Annex I",
    "regulation")

AI_ACT_HIGH_RISK_TEST = PolicyValue(
    ("annex_i_product", "third_party_conformity_assessment"), "",
    f"{_AI_ACT}, Art. 6(1) — an AI system is high-risk where BOTH (a) it is "
    f"intended to be used as a safety component of, or is itself, a product "
    f"covered by Annex I, AND (b) that product is required to undergo a "
    f"third-party conformity assessment with a view to being placed on the "
    f"market or put into service",
    "regulation")

# THE QUESTION THIS TOOL DOES NOT ANSWER. BuildPlan 3 §0 and §4 risk 3, and it
# is stated in the return value of every route so a caller cannot read the
# AI Act consequence without reading the caveat attached to it.
SAFETY_COMPONENT_QUESTION = (
    "OPEN, AND WE DO NOT ANSWER IT: whether a generative design tool is 'a "
    "safety component of' — or 'is' — the craft, i.e. whether AI Act "
    "Art. 6(1)(a) is satisfied at all, is a legal judgement this platform is "
    "not qualified to make. Only limb (b), which follows mechanically from the "
    "RCD module routing, is decided here. `high_risk` is therefore None and "
    "never True or False.")

DISCREPANCIES = (
    "BuildPlan3-MissionToOrder.md §0 states that 'Categories A and B, and "
    "anything 12-24 m, require a notified body'. Art. 20(1)(c) gives category "
    "D the whole 2.5-24 m band on Module A with no break at 12 m, so the "
    "summary is correct for A, B and C and wrong for D. ART_20 below follows "
    "the Directive. §0's self-certifiable envelope (LH < 12 m, category C or "
    "D, harmonised standards applied) is a strict subset of the Module A cells "
    "and so remains SUFFICIENT for 'no notified body'; it is not necessary.",
)

# ------------------------------------------------------------- the Art. 20 table


@dataclass(frozen=True)
class Art20Row:
    """One cell of Article 20(1): a category, a length band, an answer.

    `band` is [lo, hi) in metres of HULL LENGTH, so 12.0 belongs to the upper
    row — Art. 20(1)(b)(i) reads 'from 2,5 m to less than 12 m' and (ii) reads
    'from 12 m to 24 m'. A boat of exactly 12.00 m is in the 12-24 band.
    """

    category: str
    band: tuple[float, float]
    module_a: bool                 # is internal production control available?
    needs_harmonised: bool         # ... only if the harmonised standards apply
    article: str

    def covers(self, category: str, lh_m: float) -> bool:
        return (category == self.category
                and self.band[0] <= lh_m < self.band[1])


_BREAK = float(MODULE_A_LENGTH_BREAK_M.value)
_LO, _HI = RCD_SCOPE_LENGTH_M.value

ART_20: tuple[Art20Row, ...] = (
    Art20Row("A", (_LO, _BREAK), False, False, "RCD Art. 20(1)(a)(i)"),
    Art20Row("A", (_BREAK, _HI), False, False, "RCD Art. 20(1)(a)(ii)"),
    Art20Row("B", (_LO, _BREAK), False, False, "RCD Art. 20(1)(a)(i)"),
    Art20Row("B", (_BREAK, _HI), False, False, "RCD Art. 20(1)(a)(ii)"),
    Art20Row("C", (_LO, _BREAK), True, True, "RCD Art. 20(1)(b)(i)"),
    Art20Row("C", (_BREAK, _HI), False, False, "RCD Art. 20(1)(b)(ii)"),
    Art20Row("D", (_LO, _HI), True, False, "RCD Art. 20(1)(c)"),
)

# The three delivery modes, as BuildPlan 3 §3 names them. Strings rather than an
# Enum because they are written into the evidence graph and served over HTTP,
# and a value that survives a JSON round trip unchanged is one fewer thing to
# get wrong at the seam.
OWN_USE_KIT = "own_use_kit"
MODULE_A_SELF_CERTIFIED = "module_a_self_certified"
NOTIFIED_BODY_REQUIRED = "notified_body_required"
DELIVERY_MODES = (OWN_USE_KIT, MODULE_A_SELF_CERTIFIED, NOTIFIED_BODY_REQUIRED)

# What the craft is FOR. Not a preference: it decides whether the Directive
# applies at all (Art. 2(2)(a)(vii)).
OWN_USE = "own_use"
PLACED_ON_MARKET = "placed_on_market"
INTENTS = (OWN_USE, PLACED_ON_MARKET)


@dataclass(frozen=True)
class AiActConsequence:
    """AI Act Art. 6(1) as far as we are entitled to take it.

    `high_risk` is ALWAYS None. That is not an omission and not a default: limb
    (a) is open (see `SAFETY_COMPONENT_QUESTION`), so a boolean here would be
    an answer to a question we have refused to answer. `tests/test_policy.py`
    pins it.
    """

    third_party_assessment_required: bool          # limb (b), decided
    high_risk: None                                # limbs (a) AND (b), refused
    article: str
    annex_i_item: int
    safety_component_question: str
    note: str


@dataclass(frozen=True)
class DeliveryRoute:
    """Where a craft's conformity work goes, and the clause that sent it there."""

    mode: str
    article: str
    rationale: str
    ai_act: AiActConsequence
    conditions: tuple[str, ...] = ()
    hull_length_m: float = 0.0
    design_category: str = ""
    disclaimer: str = DISCLAIMER

    @property
    def needs_notified_body(self) -> bool:
        return self.mode == NOTIFIED_BODY_REQUIRED

    def as_dict(self) -> dict:
        return {
            "mode": self.mode, "article": self.article,
            "rationale": self.rationale, "conditions": list(self.conditions),
            "hull_length_m": self.hull_length_m,
            "design_category": self.design_category,
            "ai_act": {
                "third_party_assessment_required":
                    self.ai_act.third_party_assessment_required,
                "high_risk": self.ai_act.high_risk,
                "article": self.ai_act.article,
                "annex_i_item": self.ai_act.annex_i_item,
                "safety_component_question":
                    self.ai_act.safety_component_question,
                "note": self.ai_act.note,
            },
            "disclaimer": self.disclaimer,
        }


def _ai_act(third_party: bool, why: str) -> AiActConsequence:
    return AiActConsequence(
        third_party_assessment_required=third_party,
        high_risk=None,
        article=f"{_AI_ACT}, Art. 6(1)(b)",
        annex_i_item=int(AI_ACT_ANNEX_I_ITEM.value),
        safety_component_question=SAFETY_COMPONENT_QUESTION,
        note=why)


def art_20_row(design_category: str, hull_length_m: float) -> Art20Row:
    """The cell of Art. 20(1) that governs this craft, or refuse.

    A craft outside the RCD's own 2.5-24 m definition of 'recreational craft'
    is not routed by guessing the nearest row. It is REFUSED, naming Art. 3(2),
    because the Directive is not the instrument that governs it and this module
    has read no other instrument.
    """
    cat = str(design_category).upper()
    lh = float(hull_length_m)
    if not (_LO <= lh < _HI or lh == _HI):
        raise PolicyRefusal(
            f"hull length {lh:.2f} m is outside {RCD_SCOPE_LENGTH_M.value} m, "
            f"so this craft is not a 'recreational craft' as {_RCD} Art. 3(2) "
            f"defines one. The RCD is not the instrument that governs it and "
            f"this module has read no other instrument, so it routes nothing. "
            f"{DISCLAIMER}")
    for row in ART_20:
        # The 24.0 upper edge is inclusive ('to 24 m'); `covers` is [lo, hi).
        if row.covers(cat, min(lh, _HI - 1e-12)):
            return row
    raise PolicyRefusal(
        f"design category {design_category!r} is not one of A/B/C/D, so "
        f"Art. 20(1) has no row for it. {DISCLAIMER}")


@dataclass(frozen=True)
class LegalEnvelope:
    """The legal box the OWNER intends to stay inside, and the router for it.

    This is the half of the constitution that the owner may NOT relax. The
    fields are declarations about the project, not preferences about it:

    `intent`  — own use (Art. 2(2)(a)(vii), outside the Directive) or placed on
                the market (inside it). Changing this changes which law applies,
                so it is a statement of fact and the owner is responsible for it.
    `harmonised_standards_applied` — whether the harmonised standards under
                Annex I Part A points 3.2 and 3.3 are complied with. It decides
                the category C, sub-12 m cell and nothing else (Art. 20(1)(b)(i)).
    `accept_notified_body` — the one genuine choice here: is the project willing
                to engage a notified body? Leaving it False is what makes
                "this design has walked out of the self-certifiable envelope" a
                CONSTRAINT the optimizer can see, rather than a surprise at
                delivery. It never changes the routing; it changes whether the
                routing is acceptable.
    """

    intent: str = PLACED_ON_MARKET
    harmonised_standards_applied: bool = True
    accept_notified_body: bool = False
    allowed_categories: tuple[str, ...] = ("C", "D")

    def __post_init__(self) -> None:
        if self.intent not in INTENTS:
            raise PolicyError(f"intent {self.intent!r} not in {INTENTS}")
        bad = [c for c in self.allowed_categories if c not in "ABCD" or len(c) != 1]
        if bad:
            raise PolicyError(f"allowed_categories {bad} are not RCD categories")
        if not self.allowed_categories:
            raise PolicyError("an envelope that allows no design category "
                              "admits no craft; say which categories apply")

    # ---------------------------------------------------------------- routing

    def route(self, hull_length_m: float, design_category: str) -> DeliveryRoute:
        """Delivery mode + the article that decided it + the AI Act consequence.

        Raises `PolicyRefusal` for a craft the RCD does not define — never a
        mode chosen because a mode had to be returned.
        """
        cat = str(design_category).upper()
        lh = float(hull_length_m)

        if self.intent == OWN_USE:
            # Outside the Directive ENTIRELY, so Art. 20 never runs and no
            # notified body is involved — while it stays own use. The five-year
            # clause is not fine print; it is carried on the route, printed
            # verbatim with its article, and it is the reason the AI Act note
            # below says "for as long as".
            #
            # The scope check still runs first: a 30 m own-use build is outside
            # the RCD for a second, independent reason and we do not get to
            # claim Art. 2(2)(a)(vii) as the one that applies.
            art_20_row(cat, lh)
            return DeliveryRoute(
                mode=OWN_USE_KIT,
                article=str(OWN_USE_EMBARGO_YEARS.source),
                rationale=(
                    f"built for own use, so outside {_RCD} entirely "
                    f"(Art. 2(2)(a)(vii)); no conformity assessment module "
                    f"applies while that remains true"),
                ai_act=_ai_act(
                    False,
                    "No third-party conformity assessment is required under "
                    "the RCD for a craft outside its scope, so AI Act "
                    "Art. 6(1)(b) is not satisfied — FOR AS LONG AS the craft "
                    "stays out of scope. Placing it on the market inside five "
                    "years triggers Art. 19(4) -> Art. 23 -> Annex V, which is "
                    "a notified-body assessment, and limb (b) is then "
                    "satisfied after the boat has been built."),
                conditions=(str(OWN_USE_EMBARGO_YEARS.source),
                            str(OWN_USE_RESALE_CLAUSE.source),
                            str(OWN_USE_RESALE_CLAUSE.note)),
                hull_length_m=lh, design_category=cat)

        row = art_20_row(cat, lh)
        module_a = row.module_a and (self.harmonised_standards_applied
                                     or not row.needs_harmonised)

        if module_a:
            conds: tuple[str, ...] = ()
            if row.needs_harmonised:
                conds = (str(HARMONISED_STANDARDS_CLAUSE.source),)
            return DeliveryRoute(
                mode=MODULE_A_SELF_CERTIFIED,
                article=row.article,
                rationale=(
                    f"category {cat} at hull length {lh:.2f} m falls in "
                    f"{row.article}, whose modules include Module A (internal "
                    f"production control) — no notified body"
                    + (" provided the harmonised standards under Annex I "
                       "Part A points 3.2 and 3.3 are complied with, which "
                       "this constitution declares they are"
                       if row.needs_harmonised else "")),
                ai_act=_ai_act(
                    False,
                    "Module A is internal production control: no third party "
                    "assesses conformity, so AI Act Art. 6(1)(b) is not "
                    "satisfied and the second limb of the high-risk test "
                    "fails. Limb (a) remains open."),
                conditions=conds, hull_length_m=lh, design_category=cat)

        why_not = (
            f"category {cat} at hull length {lh:.2f} m falls in {row.article}, "
            f"whose available modules are A1, B+C/D/E/F, G and H — every one "
            f"of them involves a notified body"
            if row.module_a is False else
            f"category {cat} at hull length {lh:.2f} m could use Module A under "
            f"{row.article}, but only where the harmonised standards under "
            f"Annex I Part A points 3.2 and 3.3 are complied with, and this "
            f"constitution declares they are not; the available modules start "
            f"at A1, which involves a notified body")
        return DeliveryRoute(
            mode=NOTIFIED_BODY_REQUIRED,
            article=row.article,
            rationale=why_not,
            ai_act=_ai_act(
                True,
                "A notified body performs the conformity assessment, so the "
                "product IS required to undergo a third-party conformity "
                "assessment and AI Act Art. 6(1)(b) IS satisfied. Whether the "
                "system is therefore high-risk turns on limb (a), which is "
                "open. Note what has happened in one step: the same design "
                "change acquired a notified body AND an AI Act question at "
                "once — the coupling no physics gate can see."),
            conditions=(str(AI_ACT_HIGH_RISK_TEST.source),),
            hull_length_m=lh, design_category=cat)

    # ------------------------------------------------------------- the margins

    def margins(self, hull_length_m: float,
                design_category: str) -> list[tuple[float, str]]:
        """(margin, reason) pairs for the legal row; margin > 0 is a breach.

        Relative wherever a relative number exists, because NSGA-II needs a
        gradient out of an infeasible region and "you are 1.3 m too long" means
        something different on a 5 m tender than on a 20 m barge. A CATEGORICAL
        breach — a design category the envelope does not admit — has no such
        gradient, and reports `CATEGORICAL_BREACH` rather than an invented one.
        """
        out: list[tuple[float, str]] = []
        cat = str(design_category).upper()
        lh = float(hull_length_m)

        lo, hi = RCD_SCOPE_LENGTH_M.value
        if lh > hi:
            out.append(((lh - hi) / hi,
                        f"hull length {lh:.2f} m is above the RCD's own "
                        f"{hi:.0f} m scope ceiling (Art. 3(2)); this platform "
                        f"has read no instrument that governs it"))
        elif lh < lo:
            out.append(((lo - lh) / lo,
                        f"hull length {lh:.2f} m is below the RCD's "
                        f"{lo:.1f} m scope floor (Art. 3(2))"))

        if cat not in self.allowed_categories:
            out.append((float(CATEGORICAL_BREACH.value),
                        f"design category {cat} is not one of "
                        f"{list(self.allowed_categories)}, which is what this "
                        f"constitution's legal envelope is written for"))

        if out:
            # Out of scope, or a category the envelope never claimed to route.
            # Asking `route()` for a mode here would be asking it to answer a
            # question it has just refused.
            return out

        route = self.route(lh, cat)
        if route.needs_notified_body and not self.accept_notified_body:
            row = art_20_row(cat, lh)
            if row.band[0] >= _BREAK and cat in ("A", "B", "C"):
                # The length is the knob, so give the search the gradient.
                out.append(((lh - _BREAK) / _BREAK,
                            f"{route.rationale}; this constitution has not "
                            f"accepted a notified body, and {_BREAK:.0f} m is "
                            f"the length at which category {cat} leaves the "
                            f"Module A band ({MODULE_A_LENGTH_BREAK_M.source})"))
            else:
                out.append((float(CATEGORICAL_BREACH.value),
                            f"{route.rationale}; this constitution has not "
                            f"accepted a notified body, and no geometric "
                            f"parameter changes that"))
        return out


# A breach with no continuous knob behind it. Its SIGN is contractual (> 0 is a
# violation, which is what `evaluate.g` means); its MAGNITUDE is not a physical
# quantity and must not be read as one. Declared here once rather than typed as
# a bare 1.0 at the four sites that report a categorical breach.
CATEGORICAL_BREACH = PolicyValue(
    1.0, "-",
    "governance kernel, BuildPlan 3 §2.2 — a categorical breach (wrong design "
    "category, notified body unaccepted) has no geometric gradient; the "
    "constraint vector needs a positive number and this is the declared one",
    "derived",
    note="Sign is contractual, magnitude is not. Do not compare it against a "
         "relative geometric margin as though the two were commensurable.")


__all__ = [
    "DISCLAIMER", "DISCREPANCIES", "RCD_SCOPE_LENGTH_M",
    "MODULE_A_LENGTH_BREAK_M", "OWN_USE_EMBARGO_YEARS", "OWN_USE_RESALE_CLAUSE",
    "HARMONISED_STANDARDS_CLAUSE", "AI_ACT_ANNEX_I_ITEM",
    "AI_ACT_HIGH_RISK_TEST", "SAFETY_COMPONENT_QUESTION", "CATEGORICAL_BREACH",
    "Art20Row", "ART_20", "art_20_row", "AiActConsequence", "DeliveryRoute",
    "LegalEnvelope", "OWN_USE_KIT", "MODULE_A_SELF_CERTIFIED",
    "NOTIFIED_BODY_REQUIRED", "DELIVERY_MODES", "OWN_USE", "PLACED_ON_MARKET",
    "INTENTS",
]
