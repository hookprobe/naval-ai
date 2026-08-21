"""Design DNA — the owner's policy, and the honest label on it.

BuildPlan 3 §2.2, verbatim: *"Sustainability policy (allowed propulsion, banned
fuels, material palette, minimum recyclability) rides the same compiler — but
it is important to be honest that these are **preference constraints, not
safety constraints**. They are recorded with `basis='policy'` and can be
relaxed by the owner of the constitution; the legal envelope and the physics
floors cannot."*

So every constant in this module carries `basis='policy'`, and
`tests/test_policy.py` asserts that — a preference that has drifted into
`basis='directive'` is a preference wearing a law's badge, which is the precise
failure this vocabulary exists to prevent.

TWO KINDS OF FIELD, AND ONLY ONE OF THEM CAN BE A RATCHET
---------------------------------------------------------
1. **Ceilings and palettes** (`max_hull_length_m`, `max_draft_m`,
   `allowed_propulsion`, `material_palette`, `min_solar_fraction`). These bound
   a quantity `limits.py` says nothing about. They compile into the parameter
   box and into the `policy_dna` constraint row.

2. **`floors`** — a tightening of a limit that `limits.py` ALREADY owns. This
   is the dangerous one, and it is the one Gate V3.0(b) is about. A value here
   may only move the bar in the strict direction; the compiler reads the
   current value out of `limits.py` through `getattr` and refuses at compile
   time otherwise. Nothing in this package restates a `limits.py` number, so
   there is no second home for one to drift in.

WHAT THE LENGTH CEILING IS MEASURED AGAINST, STATED PLAINLY
-----------------------------------------------------------
The RCD speaks of HULL LENGTH (LH). This platform's grammar has no LH: it is
parameterised on waterline length, and `rules.iso12217.hull_length_m` already
reads LWL where the standard says LH. That approximation is OPTIMISTIC, because
LH >= LWL always — a hull at LWL 11.9 m may be a 12.4 m boat with its overhangs
and sit outside the self-certifiable envelope while every gate is green.

`lh_over_lwl` is the owner's declared allowance for that, and its default is
1.0 — i.e. exactly today's behaviour, exactly today's numbers, and the
limitation visible in the constitution rather than buried in an assumption. It
is not a fudge factor to be tuned: a real LH needs a geometry model of the stem
and transom overhangs, which is owed work and is recorded as such.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .base import PolicyError, PolicyValue

_OWNER = ("owner constitution (BuildPlan 3 §2.2 design DNA) — a PREFERENCE the "
          "owner of this constitution may relax; not law, not physics")


# The construction methods this platform knows how to reason about, and the
# one thing that follows from each. SHEET_DEVELOPABLE is the CNC-kit product:
# the shell is cut flat and bent, so it must be a DEVELOPABLE surface and a
# radiused bilge is not one — `unroll.hull_panels` refuses `roundness != 0`
# by name. MOULDED takes no position on curvature.
SHEET_DEVELOPABLE = "sheet-developable"
MOULDED = "moulded"
CONSTRUCTION_METHODS = (SHEET_DEVELOPABLE, MOULDED)


def owner(value, unit: str, what: str, note: str = "") -> PolicyValue:
    """A `basis='policy'` constant, with the owner-decision provenance attached.

    A helper rather than four dozen literal `PolicyValue(...)` calls, so that
    the sentence "this is a preference, not a safety bar" is written once and
    cannot be omitted from row 37 of a table.
    """
    return PolicyValue(value, unit, f"{_OWNER}: {what}", "policy", note)


@dataclass(frozen=True)
class DesignDNA:
    """Owner policy: ceilings, palettes, and ratchets on `limits.py`.

    Every field is a `PolicyValue` or None. None means "this constitution takes
    no position", which is different from a permissive number — a ceiling of
    1e9 would occupy a constraint row and read as satisfied forever, and this
    codebase has already shipped one of those (`evaluate`'s `list` row, -2.000
    across 800 evaluations).
    """

    name: str
    max_hull_length_m: PolicyValue | None = None
    max_draft_m: PolicyValue | None = None
    min_solar_fraction: PolicyValue | None = None
    lh_over_lwl: PolicyValue | None = None
    allowed_propulsion: PolicyValue | None = None
    forbidden_propulsion: PolicyValue | None = None
    material_palette: PolicyValue | None = None
    # The construction METHOD, which is a separate owner position from the
    # material palette and is NOT inferable from it. MEASURED 2026-08-21: the
    # reference palette is "sheet goods the platform can derive from its own
    # geometry" AND it contains epoxy + glass-cloth, from which a compound-
    # curved shell can perfectly well be moulded. So a palette does not decide
    # whether the SHELL is developable; only the builder does. Declaring it
    # here keeps one home for the fact instead of inferring it from a set of
    # material strings that happens to read the right way today.
    construction: PolicyValue | None = None
    # limits.py attribute name -> the tightened value. Checked at COMPILE time
    # against the live value in `limits.py`; see `compiler.RATCHETS`.
    floors: Mapping[str, PolicyValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise PolicyError("a design DNA with no name cannot be cited in a "
                              "release; name it")
        for f in self.__dataclass_fields__:
            if f in ("name", "floors"):
                continue
            v = getattr(self, f)
            if v is None:
                continue
            if not isinstance(v, PolicyValue):
                raise PolicyError(
                    f"DesignDNA.{f} is a bare {type(v).__name__} "
                    f"({v!r}). Gate V3.0(a): every policy constant carries "
                    f"source + basis, no bare numbers.")
            if v.basis != "policy":
                raise PolicyError(
                    f"DesignDNA.{f} carries basis {v.basis!r}. Owner "
                    f"preferences are basis='policy' — a preference wearing "
                    f"'directive' or 'regulation' claims the force of law it "
                    f"does not have (BuildPlan 3 §2.2).")
        if self.construction is not None:
            if str(self.construction.value) not in CONSTRUCTION_METHODS:
                raise PolicyError(
                    f"DesignDNA.construction is "
                    f"{self.construction.value!r}; this platform knows "
                    f"{list(CONSTRUCTION_METHODS)}. An unrecognised method "
                    f"would silently take NO position on shell curvature, "
                    f"which is the permissive answer -- so it is refused "
                    f"rather than defaulted.")
        for k, v in dict(self.floors).items():
            if not isinstance(v, PolicyValue):
                raise PolicyError(
                    f"DesignDNA.floors[{k!r}] is a bare "
                    f"{type(v).__name__} ({v!r}); it must carry source + basis")
            if v.basis != "policy":
                raise PolicyError(
                    f"DesignDNA.floors[{k!r}] carries basis {v.basis!r}; a "
                    f"tightening of a `limits.py` bar is an owner decision and "
                    f"is basis='policy'")

    def requires_developable_shell(self) -> bool:
        """Must the hull shell be cuttable from flat sheet?

        The ONE derived consequence of `construction`. A constitution that
        takes no position returns False -- which is today's behaviour for every
        ungoverned run, and is why adopting this field changes no number for a
        constitution that does not set it.
        """
        if self.construction is None:
            return False
        return str(self.construction.value) == SHEET_DEVELOPABLE

    def lh_from_lwl(self, lwl_m: float) -> float:
        """Hull length as this constitution models it from waterline length.

        Exactly `lwl_m` when the owner declares no allowance, which is why
        adopting a constitution with no `lh_over_lwl` changes no number that
        `rules.iso12217.hull_length_m` would have produced.
        """
        r = 1.0 if self.lh_over_lwl is None else float(self.lh_over_lwl.value)
        return float(lwl_m) * r


# --------------------------------------------------------------------------
# The reference SKU. PLM.md §2 lists the Solar Liveaboard (6 t, Danube/Black
# Sea, category C/D, sharp-chine 9-14 m) as the reference product, and
# BuildPlan 3 §5 adds *Kit-Line v3* — "the self-certifiable envelope
# (LH < 12 m, category C/D) delivered as a CNC kit. It is a CONFIGURATION, not
# a fork: same grammar, same ladder, one policy profile, one delivery mode."
#
# Note what the two sentences do to each other: the Solar Liveaboard's declared
# grammar subspace is 9-14 m, and 14 m is on the wrong side of Art. 20(1)(b)'s
# 12 m break for a category C boat. BuildPlan 3 §0 makes exactly this point
# about a "maximum length 24 m" constitution — "a constitution that walks the
# platform into third-party assessment on its first project. The number is
# 12 m." Kit-Line v3 is that correction, written down.
# --------------------------------------------------------------------------

KIT_LINE_V3 = DesignDNA(
    name="Kit-Line v3 (self-certifiable envelope, CNC plywood kit)",
    # 11.9 and not 12.0: Art. 20(1)(b)(i) reads "to LESS THAN 12 m", so 12.00 m
    # is already in the notified-body row. A ceiling AT the break has no margin
    # for the LH model this platform does not have (see `lh_over_lwl`).
    max_hull_length_m=owner(
        11.9, "m",
        "stay strictly inside the RCD Art. 20(1)(b)(i) category C Module A "
        "cell, which ends at 'less than 12 m', with 0.1 m of margin for the "
        "hull-length model this platform does not yet have",
        note="The 12 m figure itself is the Directive's (legal.MODULE_A_"
             "LENGTH_BREAK_M); this 11.9 is the owner's setback from it."),
    max_draft_m=owner(
        1.10, "m",
        "Danube and Black Sea coastal operation with canal and marina access; "
        "the mission preset PLM.md §2 records for the Solar Liveaboard"),
    min_solar_fraction=owner(
        0.60, "-",
        "at least 60% of the daily energy demand at the cruise plan comes from "
        "the array, so 'solar' is a measured fraction rather than a label",
        note="BuildPlan 3 §1.4's anchor is the Silent 62 crossing the Atlantic "
             "on ~5500 L of fuel while battery-powered for 72% of the journey. "
             "A fraction is the honest form of this claim; 'unlimited "
             "autonomy' is not."),
    lh_over_lwl=owner(
        1.0, "-",
        "no hull-length model exists — the grammar is parameterised on LWL and "
        "rules.iso12217.hull_length_m already reads LWL where ISO says LH",
        note="1.0 is TODAY'S BEHAVIOUR, declared rather than assumed. It is "
             "optimistic: LH >= LWL always. Raising it is an owner decision "
             "and tightens the box; the real fix is a stem/transom overhang "
             "model, which is owed."),
    allowed_propulsion=owner(
        frozenset({"electric-inboard", "electric-pod", "electric-outboard"}),
        "",
        "electric propulsion only — the product line exists to be charged from "
        "its own array"),
    forbidden_propulsion=owner(
        frozenset({"diesel-inboard", "petrol-outboard", "diesel-outboard",
                   "hybrid-diesel"}),
        "",
        "no combustion propulsion in this product line"),
    material_palette=owner(
        frozenset({"marine-plywood-okoume", "epoxy", "glass-cloth",
                   "stainless-316", "aluminium-5083"}),
        "",
        "the CNC kit path of BuildPlan 3 §2.5 — sheet goods the platform can "
        "derive from its own geometry, plus the fasteners and adhesives that "
        "join them"),
    construction=owner(
        SHEET_DEVELOPABLE, "",
        "the CNC kit path builds the shell from flat plywood: it is cut, "
        "bent and stitched, never laid into a mould",
        note="MEASURED 2026-08-21 and this is why the field exists. The "
             "product reframed to plywood-only buildable boats, and that "
             "reframe reached the BENCHMARK (Gate 2M demoted to solver "
             "verification) but never reached the SEARCH SPACE. 60 hulls "
             "drawn from the flagship mission: roundness > 0 on 60 of 60, "
             "median 0.541, and `unroll.hull_panels` refused 60 of 60. The "
             "ladder validated a design space that is 100% unbuildable in "
             "the one material this product is made of."),
    floors={},
)


__all__ = ["DesignDNA", "KIT_LINE_V3", "owner", "MOULDED",
           "SHEET_DEVELOPABLE", "CONSTRUCTION_METHODS"]
