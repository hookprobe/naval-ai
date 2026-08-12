"""BuildPlan 2 V2.0 — the reference-data spine.

Gate V2.0's bar, verbatim from `BuildPlan2-FullVessel.md` §3: *"constants
importable, every one carries source+basis, no bare numbers."*

WHY A WRAPPER TYPE AND NOT A MODULE OF FLOATS
---------------------------------------------
CLAUDE.md's design-side invariant is that this codebase's recurring defect is
A NUMBER DECLARED TWICE. The reference-data spine has a second, worse failure
mode available to it: a number declared ONCE, correctly, with no way to tell
afterwards whether it came from a standard, from marine practice, or from
somebody's memory. `navalai/rules/` already answers that with a per-finding
`basis`; this package answers it at the constant.

So every value here is a `RefValue`, and a `RefValue` cannot be constructed
without a non-empty `source` and a `basis` from `BASES`. That is a structural
guarantee, not a convention a test has to police after the fact — although
`tests/test_refdata.py` polices it anyway, because a dict of RefValues can
still be reached into and a bare float left beside it.

THE THREE BASES, AND WHY THERE IS NO FOURTH
-------------------------------------------
BuildPlan 2 §2 fixes the vocabulary at 'standard-2003' | 'approx' |
'purchased', and it is deliberately coarse:

  standard-2003  transcribed from a standard text we can read today. In
                 practice that is ISO 15085:2003, whose numeric clauses the
                 plan's research sweep verified against the text itself.
  approx         a floor we ship while the governing text is paywalled, or a
                 marine-practice number verified at claim level but governed by
                 no standard. NOT a guess: every one still names its source.
  purchased      transcribed from a document in the PURCHASE queue after it was
                 bought and read. Nothing carries this basis yet, and that is
                 the honest state — `PURCHASE_QUEUE` below is what it costs.

A number from the ISO 15085:**2024** preview is therefore 'approx', not
'standard-2003': calling it 'standard-2003' would attribute it to a text that
does not contain it, which is exactly the kind of quiet false provenance the
basis field exists to prevent.

WHAT IS DELIBERATELY ABSENT
---------------------------
`NOT_SOURCED` lists, by name, every quantity BuildPlan 2 §1 refers to that we
could NOT transcribe with a citation — Panero & Zelnik's anthropometric
tables, the 2024 per-zone equipment lists, ABYC's exact inch dimensions, the
percentile stretch factor, USCG's reference-area freeboard rules, ISO 9094's
fire numbers. They are recorded as absent rather than invented at a plausible
value, because a plausible invented number is indistinguishable from a
transcribed one once it is in a module, and the tiers above will divide by it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BASES = ("standard-2003", "approx", "purchased")


@dataclass(frozen=True)
class RefValue:
    """One reference constant, with the provenance that makes it usable.

    `value` may be a scalar, a bool (a policy flag such as "polystyrene is
    banned"), or a tuple (a range or a pair of dimensions). `unit` is "-" for
    dimensionless factors and "" for flags.
    """

    value: Any
    unit: str
    source: str
    basis: str
    note: str = ""
    percentile: str | None = None

    def __post_init__(self) -> None:
        if not str(self.source).strip():
            raise ValueError(
                "a reference constant with no source is a remembered number; "
                "cite it or record it in NOT_SOURCED instead")
        if self.basis not in BASES:
            raise ValueError(f"basis {self.basis!r} not in {BASES}")
        if self.unit is None:
            raise ValueError("unit must be given ('-' dimensionless, '' flag)")


@dataclass(frozen=True)
class Absent:
    """A quantity BuildPlan 2 §1 names that we could NOT source.

    Recorded so a reader can tell "we looked and it is paywalled" from "nobody
    thought of it", and so the PURCHASE queue has a concrete shopping list.
    """

    what: str
    why: str
    unblocked_by: str = ""


# ORDERED BY WHAT EACH PURCHASE UNBLOCKS, AND THE FIRST TWO CLOSE A RED GATE.
#
# MEASURED 2026-08-12: neither of the two standards that Gate 6R is RED for was
# on this queue. `review.edition_defects()` returns exactly
#
#     ISO 12215-5: edition is a placeholder ('edition not recorded — set this')
#     ISO 12217-1: edition is a placeholder ('edition not recorded — set this')
#
# and this tuple listed neither, while docs/research/COMPLIANCE.md §11 listed
# "ISO 12217-1 full text" and not 12215-5. Three lists of what to buy, all
# different, and the one in code — the one a purchaser would run — omitted both
# items that would turn a RED gate green. That is A LIST DECLARED TWICE, the
# defect class this repository keeps paying for, applied to its own procurement.
#
# `test_every_edition_defect_has_a_purchase_row` is the fence.
PURCHASE_QUEUE = (
    "ISO 12217-1:2022 — Small craft, stability and buoyancy assessment and "
    "categorization, Part 1: non-sailing boats of hull length >= 6 m. CLOSES "
    "HALF OF GATE 6R (RED). Needed: the four design-category rows behind "
    "iso12217.CATEGORY_TABLE — downflooding height, GM floor, offset-load heel "
    "angle and the significant wave height each category implies — plus the "
    "crew mass and crowding fraction for the offset-load test (85 kg and 0.4 "
    "are engineering-practice stand-ins) and the scope clause behind R-SCP. "
    "The MECHANICS are exact and tested; only the coefficients are basis='approx'",
    "ISO 12215-5 — Small craft, hull construction and scantlings, Part 5: "
    "design pressures for monohulls, design stresses, scantlings determination. "
    "CLOSES THE OTHER HALF OF GATE 6R (RED). Needed: the displacement-mode "
    "design-pressure coefficients (P_BM = max(10, 2.4*mLDC^0.33 + 20) is the "
    "stand-in), the k2 aspect-ratio table, the kC curvature correction, and the "
    "plywood design bending stress sigma_d (15.0 N/mm^2 for okoume is the "
    "stand-in and it sets scantlings directly)",
    "ISO 12217-2 — sailing craft 6-24 m, including WIND-HEELING criteria. Not "
    "an edition defect (nothing implements it), but it BLOCKS THE WINDWING SKU: "
    "a kite-rigged craft must EXTEND R-SCP rather than bypass it, and the rules "
    "tier must refuse to produce -1 findings for it until this is held",
    "ISO 12215-7 — extends scantling loads to MULTIHULLS; blocks any catamaran "
    "SKU outright",
    "ISO 15085:2024 (2nd ed.) — per-zone equipment lists and 2024 numeric "
    "clauses; the Z1/Z2/Z3 zone STRUCTURE is verified and encoded, the numbers "
    "shipped alongside it are the 2003 floors",
    "ISO 12217-3:2022 — governs craft under 6 m, assigns category C or D",
    "ISO 9094 — fire protection; nothing was captured free, so fire posture "
    "ships with no numbers at all",
    "ABYC H-41 — exact inch dimensions for reboarding, ladders, handholds "
    "(claim-level content is verified; the dimensions are behind membership)",
    "Panero & Zelnik, Human Dimension & Interior Space (1979) — the "
    "percentile-organised anthropometric tables themselves",
    "Larsson & Eliasson, Principles of Yacht Design — supplies "
    "`bilge_depth_mm` (the clearance a sole needs above the inside of the "
    "bottom planking for limber water and structure; without it the "
    "arrangement places the sole on a WIDTH criterion, which is geometric and "
    "honest but is not the rule a builder uses) and, with Panero & Zelnik, "
    "`passage_clear_width_mm`. Both are named by `refdata.absent()`",
)


def constants(module) -> dict[str, RefValue]:
    """Every RefValue a module exposes, keyed by a dotted path.

    Walks into dicts and tuples so that category-keyed tables
    (`SIDE_DECK_WIDTH_MIN_MM["C"]`) are enumerated as
    `SIDE_DECK_WIDTH_MIN_MM.C` rather than missed — the gate test is only
    worth anything if it sees every value, including the nested ones.
    """
    out: dict[str, RefValue] = {}

    def walk(name: str, obj: Any) -> None:
        if isinstance(obj, RefValue):
            out[name] = obj
        elif isinstance(obj, dict):
            for k, v in obj.items():
                walk(f"{name}.{k}", v)
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                walk(f"{name}[{i}]", v)

    for name, obj in vars(module).items():
        if name.startswith("_"):
            continue
        walk(name, obj)
    return out


def all_constants() -> dict[str, RefValue]:
    from . import ergonomics, flotation
    out: dict[str, RefValue] = {}
    for mod in (ergonomics, flotation):
        for k, v in constants(mod).items():
            out[f"{mod.__name__.rsplit('.', 1)[-1]}.{k}"] = v
    return out


def absent() -> dict[str, Absent]:
    from . import ergonomics, flotation
    out: dict[str, Absent] = {}
    for mod in (ergonomics, flotation):
        for a in getattr(mod, "NOT_SOURCED", ()):
            out[f"{mod.__name__.rsplit('.', 1)[-1]}.{a.what}"] = a
    return out


__all__ = ["BASES", "RefValue", "Absent", "PURCHASE_QUEUE", "constants",
           "all_constants", "absent"]
