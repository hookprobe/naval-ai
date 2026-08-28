"""FORM LIBRARY — the hull shapes that exist, what regime each serves, and
which of them are candidates for this product line.

WHY THIS FILE EXISTS. Before 2026-08-13 the whole of this project's memory of
hull form was `hull_ast.Typology`: two members, `SHARP_CHINE` and `PRAM`, with
`TYPOLOGY_RULES` banding three grammar parameters between them. A generator
that knows two shapes cannot be said to have chosen one. The twelve reference
drawings in `downloads/hull-examples/` describe roughly forty, across six
groups, and `docs/research/HULL-FORM-RULES.md` turned six of them into a rule
set in prose. This module is the machine-readable half of that record: the
families themselves, as data.

THE FRAMING, and it is the owner's: **water is a medium like air, and a hull
must be streamlined in it.** Fine entry, smooth pressure recovery, no abrupt
curvature change. Every `efficiency` sentence below is written to that test —
what does this form do to the flow that makes it cheap to push — and not to
"what is this form for".

WHAT THIS FILE IS NOT.

- It is not geometry. It imports nothing from `geometry.py` or `grammar.py`
  and constructs no hull. The dependency runs the other way: a future policy
  or sampler reads a family from here and sets its own bounds.
- It is not a status source, and it holds no measurement it is the only home
  of. The two numbers below that were MEASURED in this tree
  (`_S_OVER_L_BEST_FN030`, `_S_OVER_L_WORST_FN030`) are quoted with the symbol
  that owns them, exactly as `docs/research/HULL-FORM-RULES.md` R4 quotes them.
- It is NOT a menu of forty options. A library that implies every drawn form
  is reachable would send NSGA-II hunting deep-V deadrise on a solar boat, so
  `candidacy` is a REQUIRED field with a REQUIRED reason, and 25 of the 31
  families are `EXCLUDED` with the reason attached.

PROVENANCE IS THE POINT. Every band carries a `Basis` and a `source`, because a
band with an invented provenance is worse than no band — it is the
number-declared-twice defect with the second copy laundered into a citation. The
vocabulary extends `navalai/rules/review.py`'s, whose unreviewed value is
`'approx'` and which exists for the same reason: so nothing can claim an
authority it does not have. Most bands here are `APPROX`. That is the honest
answer and it is recorded rather than dressed up.

    python -m navalai.formlib          # print the library

Sources, by file (all under `downloads/hull-examples/`):

    hull-example-000.png  "NAVALAI - HULL TYPE REFERENCE LIBRARY", ~40 forms in
                          4 groups, each with a speed band in knots, plus a
                          typical-dimension table and a midship-section strip.
    hull-example-001.png  symmetric catamaran / trimaran / planing; `L/B_h > 12`
    hull-example-002.png  axe-bow wave-piercer; SWATH
    hull-example-003.png  classic displacement / semi-displacement / planing
    hull-example-004.png  "Solar-Electric Displacement Cruiser" (monohull)
    hull-example-005.png  "Solar-Electric Slender Catamaran Cruiser"
    hull-example-006.png  "Solar-Electric Stabilized Trimaran Cruiser"
    hull-example-007.png  panga/dory, stepped planing, cathedral/tunnel
    hull-example-008.png  "12m x 4m High-Efficiency Solar Catamaran"
    hull-example-009.png  "16m x 4.5m Long-Range Solar Catamaran"
    hull-designs.png      "HULL DESIGN EXPLORER", ~40 forms in 6 groups
    hull-designs-gemini.png  14 forms, profile + half-breadth + waterline

THE DRAWINGS CARRY ERRORS AND THEY ARE NOT INHERITED. Recorded in full in
`docs/research/HULL-FORM-RULES.md`; the four that reach a number in this file:

 1. "High Cp, Low Fn" is BACKWARDS. Cp rises with Fn. `CP_VS_FN` below is the
    monotone rule; the printed label is discarded. COUNTED 2026-08-13 by
    reading all twelve sheets: the block appears on **seven** — 001, 002, 003,
    005, 006, 008, 009 — and not on five, which is what this docstring claimed
    until the sheets were counted rather than remembered. Every one of the
    seven also duplicates the last word ("Wave-making dominant dominant"),
    which is what identifies it as one block pasted seven times.
 2. `L/B_h > 12` on 001 has leader lines pointing at demihull DEPTH and
    SEPARATION. The rule is real, the arrows are not.
 3. The SWATH panel's "Dynamic lift dominant" is copy-pasted from the planing
    panel. Same string reappears on 006 under "FINE MAIN HULL ENTRY" and on
    007 under the cathedral hull. `swath` is `Regime.DISPLACEMENT` here.
    Note the three placements are not equally wrong: on 002's SWATH it
    CONTRADICTS the "Submerged Buoyancy" heading directly above it, and on
    006 it contradicts the "Fn 0.2 - 0.35" in that sheet's own title block —
    but 007's cathedral hull really does plane, so there the block is
    duplicated rather than false. Only the first two are refuted here.
 4. "(7-12 knots, Fn 0.2 - 0.35)" heads four drawings and the two halves
    describe different boats. See `knots_to_fn` and `_SPEED_LABEL_CONFLICT`.
    (004 prints "Fn 0.2 - 0.35"; 005, 006, 008 and 009 all print "Fn 2 - 0.35",
    dropping the "0." — the band adopted is the one 004 spells out.)
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Mapping

# Only for the knots<->Froude helper. No project physics is imported: this
# module must stay readable while the geometry kernel is being rewritten, and
# `g` is not a hull-form datum.
from .constants import G_STANDARD as _G
_KNOT_MS = 0.514444


# --------------------------------------------------------------------------
# provenance


class Basis(enum.Enum):
    """WHERE A BAND CAME FROM, carried with the band so it cannot be laundered.

    SERIES    a published systematic series, and the CITATION IS ALREADY IN
              THIS TREE. `source` names the file and the symbol that carries
              it. This is the strongest basis available here and exactly one
              envelope qualifies (see `_NPL_*`).
    MEASURED  measured in this repository. `source` names the symbol or script
              that owns the number; this module quotes, it does not restate.
    DRAWING   read off one of the twelve reference drawings. `source` names the
              file and the label. A drawing is an illustration, not a
              dimensioned lines plan — see the four errors in the module
              docstring.

              A DRAWING BAND MUST QUOTE A NUMBER THE SHEET ACTUALLY PRINTS.
              MEASURED 2026-08-13: two bands claimed DRAWING off labels that
              are WORDS — 007's "Low L/B" became [2.5, 4.0] and its "constant
              deep-V deadrise" became [18, 26] with the edges borrowed from a
              different sheet. A qualitative label is real evidence about the
              DIRECTION and none at all about the EDGES, so both are now
              APPROX. This is the number-declared-twice defect with the second
              copy laundered into a citation, and it is the specific way this
              file was most likely to rot. `test_formlib.py` fences it: a
              DRAWING source that admits no number was printed is refused.
    LITERATURE
              a published paper, report or open dataset THAT WAS OPENED AND
              READ, with the citation carried in the `source` string and in
              full in `docs/research/HULL-FORM-RULES.md` §7.10. Added
              2026-08-13, when that section sourced the first bands in this
              module that came from outside the drawings.

              IT IS DELIBERATELY A RUNG BELOW `SERIES`, and the distinction is
              not pedantry: `SERIES` means the tree ALREADY carries the
              citation (`resistance.py`'s anchor block), so a reader can find
              it without leaving the repository. `LITERATURE` means one
              document was read on one day by one session. The strongest band
              here — the Southampton catamaran demihull envelope — is
              LITERATURE and is worse than that again: `eprints.soton.ac.uk`
              refused every fetch, so it is quoted from a SECONDARY source
              (Petersson 2020 Table 3) and the `source` string says so.
              A basis that hides that is a laundered citation.
    APPROX    engineering practice with NO anchor in this tree. Same word, same
              meaning as `navalai.rules.review.basis_for`'s unreviewed value.
              It is a band to aim at, never a bar to fail on.
    """

    SERIES = "series"
    MEASURED = "measured"
    LITERATURE = "literature"
    DRAWING = "drawing"
    APPROX = "approx"


@dataclass(frozen=True)
class Band:
    """A closed interval with its provenance attached.

    `low < high` STRICTLY. A degenerate band is refused rather than accepted
    as "a very precise band": this repo's signature defect is an unmeasurable
    value scored as a passing one (LESSONS.md #1), and `Band(x, x)` is how a
    single remembered figure gets promoted to a range nobody measured. A form
    whose value is genuinely a point gets no band — see `Absent`, below, which
    is what "not stated for this family" looks like.
    """

    low: float
    high: float
    basis: Basis
    source: str

    def __post_init__(self) -> None:
        for name, v in (("low", self.low), ("high", self.high)):
            if not math.isfinite(v):
                raise ValueError(f"Band.{name} is not finite: {v!r}")
        if not self.low < self.high:
            raise ValueError(
                f"Band is not ordered: low {self.low!r} >= high {self.high!r}. "
                f"A band must be an interval; a point value has no band.")
        if not isinstance(self.basis, Basis):
            raise TypeError(f"Band.basis must be a Basis, got {self.basis!r}")
        if not self.source or not self.source.strip():
            raise ValueError(
                "Band.source is empty. A band with no stated provenance is "
                "worse than no band — it reads as authority it does not have.")

    def contains(self, v: float) -> bool:
        return self.low <= v <= self.high

    def overlaps(self, other: "Band") -> bool:
        return self.low <= other.high and other.low <= self.high

    def within(self, other: "Band") -> bool:
        return other.low <= self.low and self.high <= other.high

    def __str__(self) -> str:
        return f"[{self.low:g}, {self.high:g}] ({self.basis.value})"


# The absence of a band is expressed by the key not being present in
# `FormFamily.proportions`. There is deliberately no sentinel value: a
# placeholder band of (0, 0) or (-1, -1) is the `${VAR:-0}` defect, and it is
# the one this module is most likely to grow if a later editor feels the table
# looks ragged. IT IS MEANT TO LOOK RAGGED. Most forms here have three or four
# honest bands and no more.
PROPORTION_KEYS = (
    "l_over_b",       # waterline length / waterline beam, PER HULL
    "b_over_t",       # waterline beam / draft, PER HULL
    "cp",             # prismatic coefficient
    "cb",             # block coefficient
    "deadrise_deg",   # midship deadrise
    "alpha_e_deg",    # half-angle of entrance (chord basis; see R6)
)

# Every family must carry at least these. `fn` is a field of its own because a
# form family without a speed regime is not a form family — it is a shape.
REQUIRED_PROPORTIONS = ("l_over_b",)


# --------------------------------------------------------------------------
# taxonomy


class Topology(enum.Enum):
    """How many hulls, and how they carry the vessel.

    Kept SEPARATE from `Regime` because the drawings conflate them and the
    result is a fifty-item flat list in which "deep-V" and "catamaran" and
    "bulbous bow" appear as peers. They are not peers: one is a section law,
    one is a topology, one is a local bow treatment. Flattening them is what
    makes a library imply that all forty are alternatives.
    """

    MONOHULL = "monohull"
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    QUADRIMARAN = "quadrimaran"
    SMALL_WATERPLANE = "small-waterplane"
    SUPPORTED = "supported"      # lift comes from something that is not buoyancy


class Regime(enum.Enum):
    """What carries the weight at the design speed."""

    DISPLACEMENT = "displacement"
    SEMI_DISPLACEMENT = "semi-displacement"
    PLANING = "planing"


class Candidacy(enum.Enum):
    """Whether this family may be proposed for THIS product line.

    The mission is `MISSION` below: a solar-electric displacement catamaran,
    ~12 m demihull, Fn 0.2-0.3. The verdict is a required field with a required
    reason because the cost of getting it wrong is asymmetric — an optimiser
    that may reach a stepped planing hull will spend evaluations there, and
    every one of them is wasted.
    """

    TARGET = "target"        # this IS the mission's form
    CANDIDATE = "candidate"  # a real alternative for the mission
    ADJACENT = "adjacent"    # not the form, but specific rules transfer
    EXCLUDED = "excluded"    # do not propose; the reason is on the row


class Expressible(enum.Enum):
    """Can `grammar.py` + `geometry.py` reach a hull of this family AT ALL?

    Answered against commit 173cd00 by `docs/research/HULL-FORM-RULES.md`,
    which names the file and line for each. The geometry kernel is being
    rewritten as this is written, so `missing` names the SHAPE of what is
    absent ("a section whose shape varies with x"), not a line number that a
    rebuild will invalidate.
    """

    YES = "yes"
    PARTIAL = "partial"
    NO = "no"


# --------------------------------------------------------------------------
# the two speed/coefficient rules everything else is checked against


def knots_to_fn(knots: float, lwl_m: float) -> float:
    """Froude number from a speed in knots and a waterline length in metres."""
    if not (lwl_m > 0.0):
        raise ValueError(f"lwl_m must be positive, got {lwl_m!r}")
    return knots * _KNOT_MS / math.sqrt(_G * lwl_m)


def fn_to_knots(fn: float, lwl_m: float) -> float:
    if not (lwl_m > 0.0):
        raise ValueError(f"lwl_m must be positive, got {lwl_m!r}")
    return fn * math.sqrt(_G * lwl_m) / _KNOT_MS


# MEASURED HERE 2026-08-13, and it is a contradiction inside the drawings'
# own title blocks. Four sheets (004, 005, 006, 008, 009) are headed
# "(7-12 knots, Fn 0.2 - 0.35)". On the 12 m waterline that 008 draws,
# 7 kn is Fn 0.332 and 12 kn is Fn 0.569 — so the knots say semi-displacement
# and the Froude numbers say displacement, and Fn 0.569 is above
# `resistance.FN_MICHELL_MAX` (0.45), where this project's own ladder marks
# the wave model invalid and the regime "planing". On the 16 m waterline of
# 009 the same knots give Fn 0.287-0.493.
#
# The mission stated for this work is Fn 0.2-0.3, which on 12 m is 4.2-6.3 kn.
# It agrees with the Froude half of the label and NOT with the knots half.
# Recorded because the difference is not academic: at Fn 0.57 none of the
# displacement rules in this file apply, and the whole library would be the
# wrong library.
_SPEED_LABEL_CONFLICT = (
    "drawings 004/005/006/008/009 head '7-12 knots, Fn 0.2-0.35'; on a 12 m "
    "waterline 7-12 kn is Fn 0.332-0.569, on 16 m it is Fn 0.287-0.493. The "
    "Fn half of the label is adopted, the knots half is discarded.")


# THE MONOTONE Cp RULE (R5). The drawings print "High Cp, Low Fn" on five
# panels and it is backwards: fine ends at low speed, full ends at high speed,
# so Cp RISES with Fn. This table is the rule that replaces the label.
#
# BASIS IS `APPROX` FOR EVERY ROW AND THAT IS THE WHOLE TRUTH ABOUT IT. There
# is no Cp series in this tree. It is used below only as an OVERLAP test — a
# family whose Cp band does not even touch the practice envelope over its own
# Froude band has a typo or a copied label — and never as a bar on a hull.
CP_VS_FN: tuple[tuple[Band, Band], ...] = (
    (Band(0.00, 0.20, Basis.APPROX, "regime bookkeeping"),
     Band(0.52, 0.62, Basis.APPROX, "displacement practice; no anchor in tree")),
    (Band(0.20, 0.30, Basis.APPROX, "regime bookkeeping"),
     Band(0.55, 0.72, Basis.APPROX,
          "displacement practice 0.55-0.65, widened to 0.72 because slender "
          "round-bilge demihulls of the NPL type run near 0.69 at this Fn "
          "(HULL-FORM-RULES R5). No anchor in tree.")),
    (Band(0.30, 0.40, Basis.APPROX, "regime bookkeeping"),
     Band(0.60, 0.76, Basis.APPROX, "semi-displacement practice; no anchor")),
    (Band(0.40, 0.55, Basis.APPROX, "regime bookkeeping"),
     Band(0.65, 0.82, Basis.APPROX, "transitional practice; no anchor")),
    (Band(0.55, 3.00, Basis.APPROX, "regime bookkeeping"),
     Band(0.68, 0.95, Basis.APPROX, "planing practice; no anchor")),
)


def cp_envelope(fn: Band) -> Band:
    """The union of `CP_VS_FN` rows whose Froude band overlaps `fn`."""
    lo = min(cp.low for row_fn, cp in CP_VS_FN if row_fn.overlaps(fn))
    hi = max(cp.high for row_fn, cp in CP_VS_FN if row_fn.overlaps(fn))
    return Band(lo, hi, Basis.APPROX,
                f"CP_VS_FN union over Fn {fn.low:g}-{fn.high:g}")


# Which Froude band each regime may claim. Deliberately OVERLAPPING at the
# edges: a semi-displacement form at Fn 0.38 and a displacement form at Fn 0.38
# are both real, and forcing a hard cut would make the gate refuse honest rows.
# The upper displacement edge is 0.45 because that is `resistance.FN_MICHELL_MAX`
# — the point where this project's own wave model already declares itself
# invalid — and not a number chosen for this table.
REGIME_FN: Mapping[Regime, Band] = {
    Regime.DISPLACEMENT: Band(0.0, 0.45, Basis.APPROX,
                              "upper edge = resistance.FN_MICHELL_MAX"),
    # The semi-displacement ceiling is 1.00 and NOT 0.70, and the reason is a
    # real distinction rather than slack: a very slender multihull demihull
    # runs at Fn 0.8-1.0 WITHOUT planing, because its beam-to-length ratio
    # never lets dynamic lift take over. `wave_piercing_cat_demihull` and
    # `high_speed_trimaran` sit there. Cutting the band at 0.70 would have
    # forced those two rows to claim `PLANING`, which is the exact error the
    # drawings already make on their SWATH and cathedral panels.
    Regime.SEMI_DISPLACEMENT: Band(0.30, 1.00, Basis.APPROX,
                                   "transitional regime, practice; the "
                                   "ceiling covers non-planing slender "
                                   "multihulls"),
    Regime.PLANING: Band(0.50, 3.00, Basis.APPROX,
                         "dynamic lift dominant, practice"),
}


# --------------------------------------------------------------------------
# THE ONE DIMENSIONED TABLE IN THE WHOLE SET

# `hull-example-000.png` carries a panel headed "TYPICAL HULL DIMENSION RANGES"
# with five rows and four numeric columns. Apart from the two labelled solar
# catamarans (008, 009), it is the ONLY place in twelve sheets where a
# proportion is printed as a number rather than as an adjective, so it is
# transcribed here verbatim and is genuine `Basis.DRAWING` material.
#
# IT IS NOT A PER-HULL TABLE, and that is why these bands are kept OUT of
# `FormFamily.proportions`, whose `l_over_b` and `b_over_t` are defined PER
# DEMIHULL. The "Beam" column for the catamaran row is the OVERALL beam — the
# same `B_oa` that 001, 005, 008 and 009 dimension across both hulls — so
# dividing LWL by it would produce a number that is not any family's L/B and
# that would then look like a reading off a drawing. Recorded as what it is.
#
#   type -> (LWL m, beam m, draft m, speed kn), each as (low, high)
DRAWN_DIMENSION_RANGES: Mapping[str, Mapping[str, Band]] = {
    "small monohull": {
        "lwl_m": Band(5.0, 15.0, Basis.DRAWING, "000 dimension table"),
        "beam_m": Band(1.5, 4.0, Basis.DRAWING, "000 dimension table"),
        "draft_m": Band(0.4, 1.5, Basis.DRAWING, "000 dimension table"),
        "speed_kn": Band(5.0, 12.0, Basis.DRAWING, "000 dimension table"),
    },
    "large monohull": {
        "lwl_m": Band(15.0, 25.0, Basis.DRAWING, "000 dimension table"),
        "beam_m": Band(3.0, 6.0, Basis.DRAWING, "000 dimension table"),
        "draft_m": Band(0.8, 2.0, Basis.DRAWING, "000 dimension table"),
        "speed_kn": Band(6.0, 15.0, Basis.DRAWING, "000 dimension table"),
    },
    "catamaran": {
        "lwl_m": Band(6.0, 25.0, Basis.DRAWING, "000 dimension table"),
        # OVERALL beam, across both demihulls — not a demihull beam.
        "beam_m": Band(3.0, 10.0, Basis.DRAWING, "000 dimension table, B_oa"),
        "draft_m": Band(0.4, 1.5, Basis.DRAWING, "000 dimension table"),
        "speed_kn": Band(6.0, 20.0, Basis.DRAWING, "000 dimension table"),
    },
    "trimaran": {
        "lwl_m": Band(8.0, 30.0, Basis.DRAWING, "000 dimension table"),
        "beam_m": Band(4.0, 16.0, Basis.DRAWING, "000 dimension table, B_oa"),
        "draft_m": Band(0.4, 2.0, Basis.DRAWING, "000 dimension table"),
        "speed_kn": Band(8.0, 20.0, Basis.DRAWING, "000 dimension table"),
    },
    # The "special forms" row prints "Varies" for beam and draft. An adjective
    # is not a band and it is NOT converted into one — the two keys are absent,
    # which is this module's way of saying "not stated" (see PROPORTION_KEYS).
    "special forms": {
        "lwl_m": Band(5.0, 30.0, Basis.DRAWING, "000 dimension table"),
        "speed_kn": Band(6.0, 20.0, Basis.DRAWING, "000 dimension table"),
    },
}


# --------------------------------------------------------------------------
# sources that are STRONGER than a drawing, quoted with the symbol that owns them

# The ONE published series envelope this tree carries. It is a CITATION block,
# not data: `navalai/resistance.py` says so in terms ("NOTHING BELOW IS IN THIS
# REPOSITORY. No data file, no transcribed table, no digitised curve"). So
# `Basis.SERIES` here means "a named series whose envelope this tree records",
# which is a rung above practice and still below a measurement.
_NPL_SRC = ("Bailey (1976) NPL round-bilge series, envelope as quoted in "
            "navalai/resistance.py's catamaran-anchor citation block")
_NPL_FN = Band(0.30, 1.20, Basis.SERIES, _NPL_SRC)
_NPL_L_OVER_B = Band(3.33, 7.50, Basis.SERIES, _NPL_SRC)
_NPL_B_OVER_T = Band(1.75, 10.77, Basis.SERIES, _NPL_SRC)

# THE FINDING THAT FALLS OUT OF THAT ENVELOPE, and it is worth stating where
# somebody will read it: the target demihull is L/B 15.0, and 15.0 is OUTSIDE
# `_NPL_L_OVER_B` (3.33-7.50) — comfortably outside, by a factor of two on the
# upper edge. The only published series envelope in this tree does not contain
# the hull this project is being built to design, and `_NPL_FN` starts at 0.30
# while the mission ends there. So the target family's bands below are DRAWING
# and APPROX by necessity, not by laziness. The Southampton catamaran series
# (Molland, Wellicome & Couser 1996), already named in `resistance.py` as the
# transcription to do first, is the anchor that would change that.
_NPL_EXCLUDES_TARGET = (
    "target demihull L/B 15.0 lies outside the NPL envelope [3.33, 7.50] and "
    "the mission's Fn 0.2-0.3 lies below the NPL floor of 0.30")


# --------------------------------------------------------------------------
# THE LITERATURE, opened 2026-08-13. Cited in full in
# `docs/research/HULL-FORM-RULES.md` §7.10; the argument for each band is the
# §7 subsection named in the source string. This module carries the BANDS and
# that document carries the ARGUMENT — neither restates the other.

# The anchor this file's own NPL comment said "would change that". It does.
#
# THE CAVEAT IS PART OF THE CITATION AND MUST NOT BE DROPPED: Molland,
# Wellicome & Couser's Ship Science Report 71 could NOT be opened —
# `eprints.soton.ac.uk` returned 401/403 on every route tried — so this
# envelope is quoted from Petersson (2020) Table 3, which tabulates it. A
# second, partial transcription (models 4b/5b/6b, via a student-essay site
# quoting Wellicome et al. 1995) AGREES on Cp 0.693, Cb 0.397 and LCB -6.4%L,
# which is why it is trusted at all. Opening Report 71 is the highest-value
# follow-up named in §7.10.
_SOTON_SRC = (
    "Southampton catamaran series (Molland, Wellicome & Couser, Ship Science "
    "Report 71, 1994) DEMIHULL envelope, as tabulated in Petersson (2020) "
    "UPTEC F 20024 Table 3 — SECONDARY, the report itself refused every fetch; "
    "see HULL-FORM-RULES.md §7.4 and §7.10")
_SOTON_FN = Band(0.20, 1.00, Basis.LITERATURE, _SOTON_SRC)
_SOTON_L_OVER_B = Band(7.00, 15.10, Basis.LITERATURE, _SOTON_SRC)
_SOTON_B_OVER_T = Band(1.50, 2.50, Basis.LITERATURE, _SOTON_SRC)
_SOTON_L_OVER_VOL13 = Band(6.30, 9.50, Basis.LITERATURE, _SOTON_SRC)

# THE FINDING, and it is the one this section was written to produce: the
# target demihull is L/B 15.0, and 15.0 IS INSIDE `_SOTON_L_OVER_B`. The
# published-series verdict that excluded this project's own hull was a
# MONOHULL series being asked a catamaran question. Both statements are kept —
# NPL still excludes it, Southampton still contains it — because they are
# about different families and averaging them would be the defect this module
# exists to prevent.
_SOTON_CONTAINS_TARGET = (
    "target demihull L/B 15.0 lies INSIDE the Southampton catamaran DEMIHULL "
    "envelope [7.00, 15.10] and the mission's Fn 0.2-0.3 lies inside its "
    "[0.20, 1.00] — the first published series envelope found that contains "
    "this mission's own hull. Its B/T is the other way: the target's 0.8/0.6 "
    "= 1.33 is BELOW the series' [1.50, 2.50], so the slenderness is sourced "
    "and the draft is not")

# The monohull series that reaches the same slenderness from the other side.
_S64_SRC = (
    "DTMB Series 64 (Yeh, 1965), round-bilge high-speed displacement, as "
    "tabulated in Petersson (2020) UPTEC F 20024 Table 3 — SECONDARY; see "
    "HULL-FORM-RULES.md §7.4")
_S64_L_OVER_B = Band(8.45, 18.26, Basis.LITERATURE, _S64_SRC)
_S64_FN = Band(0.06, 1.50, Basis.LITERATURE, _S64_SRC)

# ---------------------------------------------------------------------------
# THE PUBLIC NAMES `grammar.py` IMPORTS. They are the SAME OBJECTS as the
# citation blocks above — `is`, not `==` — and `tests/test_formlib.py` asserts
# the identity, because the alternative was `grammar.py` restating "15.10" as a
# literal beside a comment saying where it came from. That is precisely the
# number-declared-twice defect with the second copy laundered into a citation,
# which is the failure mode `Basis.DRAWING`'s docstring already fences inside
# this module and which this module cannot fence from OUTSIDE itself.
#
# The private `_SOTON_*` spellings stay as the DEFINITIONS because
# `test_a_SECONDARY_quotation_must_SAY_it_is_secondary` sweeps module-level
# bands by that prefix, and an alias inherits the source string it guards.
#
# WHY 2026-08-14. `grammar.check` refused this project's own target demihull
# (12.0 x 0.8 m, L/B 15.00) on `L_OVER_B_BAND`'s ceiling of 8.5 — a correct
# MONOHULL band applied to an object that is not a monohull. The band did not
# move; it acquired a second, sourced row for the demihull case, and this is
# where that row's numbers live.
SOTON_DEMIHULL_L_OVER_B = _SOTON_L_OVER_B
SOTON_DEMIHULL_B_OVER_T = _SOTON_B_OVER_T
SOTON_DEMIHULL_FN = _SOTON_FN

# EXPOSED, AND DELIBERATELY NOT USED AS A BAND EDGE. DTMB Series 64 reaches
# L/B 18.26 and is the reason to believe the drawings' L/B 15-18 demihulls are
# ordinary practice rather than an illustrator's exaggeration — but it is a
# MONOHULL series, and adopting a monohull ceiling for a demihull is the same
# category error as the monohull ceiling that refused the target hull, pointed
# the other way. It corroborates; it does not band.
S64_MONOHULL_L_OVER_B = _S64_L_OVER_B

# The one MEASURED entrance angle found on a named, optimised hull. It is a
# POINT, not a band, so it is deliberately NOT a `Band` — `Band(x, x)` is
# refused by this module and a point dressed as an interval is worse than a
# point. Quoted by the round-bilge semi-displacement family as a note.
_FDS5_SRC = (
    "MARIN Fast Displacement Ship parent form FDS-5, tabulated in Petersson "
    "(2020) UPTEC F 20024 Table 4: L/B 8, B/T 4, Cp 0.626, Cb 0.396, "
    "LCB -5.11 %Lwl, LCF -8.68 %Lwl, L/vol^(1/3) 8.68, series Fn 0.14-1.30")
_FDS5_ALPHA_E_DEG = 11.0

# Blount & McGrath (2009) is the only CROSS-SERIES comparison opened, and the
# only source that measured a RESISTANCE consequence of the entrance angle
# rather than reporting a series' fixed value.
_BLOUNT_SRC = (
    "Blount & McGrath (2009), 'Resistance Characteristics of Semi-Displacement "
    "Mega Yacht Hull Forms', Trans RINA 151 B2 / IJSCT, "
    "DOI 10.3940/rina.ijsct.2009.b2.95; see HULL-FORM-RULES.md §7.1 S1")
# i_e <= 8 deg is the FLAT part of the R/W curve for slender round-bilge hulls
# at L/vol^(1/3) 8.0-9.6, Fn 0.4-0.8; 8-11 deg costs ~0.01 in R/W at Fn
# 0.5-0.6. There is NO measured lower bound: the paper reports 3.7 deg with no
# effect at all, so the band below is one-sided in fact and its low edge is a
# floor of expression, not a finding. Said here because §7.9 item 3 records
# that this project has been auditing against a 7 deg floor with no source.
_BLOUNT_ALPHA_E_FLAT = Band(3.70, 8.00, Basis.LITERATURE,
                            f"{_BLOUNT_SRC} — the range over which i_e showed "
                            f"NO effect on R/W; the 3.70 edge is the finest "
                            f"hull measured, NOT a floor")

# Transom immersion, three series, three constants. See §7.8.2. Recorded
# because `holtrop.particulars_from_floated` hardcodes the immersed transom to
# ZERO for craft this size, and a hull at A_T/A_M ~ 0.4 modelled at 0 is not
# being modelled.
_TRANSOM_SRC = (
    "A_T/A_M held near-constant by three series: MARIN 0.31, DTMB Series 64 "
    "0.40, NPL 0.52, per Petersson (2020) UPTEC F 20024 §6.1/6.2/6.4; see "
    "HULL-FORM-RULES.md §7.8.2")
_TRANSOM_AREA_RATIO = Band(0.31, 0.52, Basis.LITERATURE, _TRANSOM_SRC)

# The entry-length fractions the chord-angle floor below is evaluated at, all
# from series that FIX them: Taylor 0.50, Series 64 0.60, NPL 0.60, and
# Blount & McGrath's own guidance 0.50 (Fn 0.3-0.4) rising to 0.55 (to 0.54).
_LE_OVER_L_SRC = (
    "L_E/L fixed by series: Taylor 0.50, DTMB Series 64 0.60, NPL 0.60 "
    "(Blount & McGrath 2009 Appendix A); design guidance 0.50 at Fn 0.3-0.4 "
    "rising to 0.55 to Fn 0.54 (ibid. §3.4); see HULL-FORM-RULES.md §7.8.2")
_LE_OVER_L = Band(0.50, 0.60, Basis.LITERATURE, _LE_OVER_L_SRC)

# Measured IN THIS TREE. Quoted, never restated: the numbers are owned by
# `resistance.catamaran_interference` and the assertions in
# `tests/test_phase1.py`, and `docs/research/HULL-FORM-RULES.md` R4 quotes the
# same two figures from the same place.
_S_OVER_L_SRC = ("measured on a Wigley demihull at Fn 0.30 by "
                 "resistance.catamaran_interference; owned by "
                 "tests/test_phase1.py, quoted here")
_S_OVER_L_BEST_FN030 = 0.4450     # destructive interference optimum
_S_OVER_L_WORST_FN030 = 0.1500    # constructive interference worst case


def alpha_e_chord_floor_deg(l_over_b: float, le_over_l: float) -> float:
    """The entry half-angle a waterline CANNOT be finer than, at this L/B.

    THE POINT OF THIS FUNCTION, and it is the most useful thing in this module
    for the α_e problem: **α_e is not a free variable.** For a waterline whose
    entry runs `le_over_l * L` from the stem to the maximum-beam station, the
    CHORD half-angle between them is

        atan( (B/2) / L_E ) = atan( (L/B)^-1 / (2 * le_over_l) )

    which depends on NOTHING but L/B and the entry-length fraction. It is
    arithmetic, not a source, and it is a FLOOR: a real convex waterline's
    tangent at the stem sits above it. Calibration, n = 1 and treated as such:
    FDS-5 is L/B 8 with a MEASURED i_e of 11 deg (`_FDS5_ALPHA_E_DEG`) against
    a chord floor here of ~5.9 deg at L_E/L 0.60, i.e. tangent ~ 2x chord.

    WHY IT MATTERS HERE. `scripts/hull_form_audit.py` measures a median α_e of
    ~32 deg over the sampled population, and the monohull grammar's L/B floor
    is ~2.2. At L/B 2.2-3.0 this floor ALONE is 19-26 deg, so most of that
    median is the L/B box, not the bow shape. The ordering that falls out —
    move the L/B ceiling first, then ask whether α_e needs a constraint row of
    its own — is `docs/research/HULL-FORM-RULES.md` §7.7, which is the one home
    of the argument. An α_e row imposed at fixed L/B would be two constraint
    rows measuring one degree of freedom, which is this project's
    number-declared-twice defect in its subtlest form.

    Evaluate at `_LE_OVER_L`'s edges (0.50, 0.60) for the published fractions.

    Raises on a non-physical argument rather than returning a plausible number:
    an unmeasurable value scored as a passing one is LESSONS.md #1.
    """
    if not l_over_b > 0.0:
        raise ValueError(f"l_over_b must be positive, got {l_over_b}")
    if not 0.0 < le_over_l < 1.0:
        raise ValueError(
            f"le_over_l is a fraction of Lwl in (0, 1), got {le_over_l}")
    return math.degrees(math.atan(1.0 / (l_over_b * 2.0 * le_over_l)))


# --------------------------------------------------------------------------
# the family record


@dataclass(frozen=True)
class FormFamily:
    """One whole-hull form. Not a bow treatment and not a lift device — those
    are `Feature`s, below, and keeping them apart is the point of the split."""

    key: str
    name: str
    topology: Topology
    regime: Regime
    fn: Band
    efficiency: str            # ONE sentence, in flow terms
    candidacy: Candidacy
    candidacy_reason: str
    expressible: Expressible
    missing: tuple[str, ...]   # what the grammar cannot say about THIS family
    drawings: tuple[str, ...]
    proportions: Mapping[str, Band] = field(default_factory=dict)
    ast_typology: str | None = None   # `hull_ast.Typology` member name, if any
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key or not self.key.islower():
            raise ValueError(f"family key must be lower-case: {self.key!r}")
        if not self.efficiency.strip():
            raise ValueError(f"{self.key}: efficiency sentence is empty")
        if not self.candidacy_reason.strip():
            raise ValueError(
                f"{self.key}: candidacy {self.candidacy.value} with no reason. "
                f"An unreasoned exclusion is indistinguishable from an "
                f"oversight, and an unreasoned inclusion is worse.")
        if not self.drawings:
            raise ValueError(f"{self.key}: names no source drawing")
        unknown = set(self.proportions) - set(PROPORTION_KEYS)
        if unknown:
            raise ValueError(f"{self.key}: unknown proportion(s) {sorted(unknown)}")
        for k in REQUIRED_PROPORTIONS:
            if k not in self.proportions:
                raise ValueError(f"{self.key}: missing required proportion {k!r}")
        if (self.expressible is Expressible.YES) != (not self.missing):
            raise ValueError(
                f"{self.key}: expressible={self.expressible.value} with "
                f"{len(self.missing)} missing item(s). YES means the list is "
                f"empty and a non-empty list means it is not YES — the two "
                f"are one statement and they may not disagree.")

    def band(self, key: str) -> Band | None:
        return self.proportions.get(key)


@dataclass(frozen=True)
class Feature:
    """A LOCAL treatment applied to a hull of some family — a bow shape, a lift
    device, an appendage, a cross-structure member.

    Separated from `FormFamily` because these have no L/B and no Cp of their
    own, and because the drawings list them as if they were alternative hulls.
    `parameterised_by` says what a grammar would need in order to say it; that
    is the entry `docs/research/HULL-FORM-RULES.md` §3 turns into work.
    """

    key: str
    name: str
    effect: str                # what it does to the flow
    candidacy: Candidacy
    candidacy_reason: str
    expressible: Expressible
    parameterised_by: str      # the shape of the parameter that would express it
    drawings: tuple[str, ...]
    applies_to: tuple[str, ...] = ()   # family keys

    def __post_init__(self) -> None:
        for name, v in (("effect", self.effect),
                        ("candidacy_reason", self.candidacy_reason),
                        ("parameterised_by", self.parameterised_by)):
            if not v.strip():
                raise ValueError(f"{self.key}: {name} is empty")
        if not self.drawings:
            raise ValueError(f"{self.key}: names no source drawing")


# --------------------------------------------------------------------------
# the mission this library is filtered against


@dataclass(frozen=True)
class Mission:
    """The design point the `candidacy` column is answered against.

    Stated here and NOT read from `grammar.py` or a constitution, because this
    module must stay importable while the geometry kernel is rewritten. If a
    policy ever compiles a different mission, the right move is a second
    `Mission` and a re-verdict, not an edit to this one — a candidacy verdict
    is only meaningful next to the mission that produced it.
    """

    name: str
    topology: Topology
    regime: Regime
    fn: Band
    hull_lwl_m: float
    hull_bwl_m: float
    hull_draft_m: float

    @property
    def l_over_b(self) -> float:
        return self.hull_lwl_m / self.hull_bwl_m

    @property
    def b_over_t(self) -> float:
        return self.hull_bwl_m / self.hull_draft_m


MISSION = Mission(
    name="solar-electric displacement catamaran",
    topology=Topology.CATAMARAN,
    regime=Regime.DISPLACEMENT,
    fn=Band(0.20, 0.30, Basis.APPROX,
            "mission statement; agrees with the Fn half of the drawings' "
            "title blocks and not with the knots half (see "
            "_SPEED_LABEL_CONFLICT)"),
    hull_lwl_m=12.0,
    hull_bwl_m=0.8,
    hull_draft_m=0.6,
)


# --------------------------------------------------------------------------
# THE LIBRARY
#
# Ordered by group, as the drawings order them. Read the `candidacy` column
# first: 25 of the 31 are EXCLUDED and the reason is on the row. 24 until
# 2026-08-28, when `wedge_multichine` moved CANDIDATE -> EXCLUDED: Phase 5
# landed the multi-chine section law that row was waiting on, which dissolved
# its candidacy argument rather than confirming it (the argument was
# BUILDABILITY, which is never a candidacy argument here). (This comment
# said "30" until the tuple was counted rather than remembered; `main()` prints
# the live count, and `test_formlib.py` now asserts the two agree.)


def _b(low, high, basis, source):
    return Band(low, high, basis, source)


_D000 = "hull-example-000.png"
_D001 = "hull-example-001.png"
_D002 = "hull-example-002.png"
_D003 = "hull-example-003.png"
_D004 = "hull-example-004.png"
_D005 = "hull-example-005.png"
_D006 = "hull-example-006.png"
_D007 = "hull-example-007.png"
_D008 = "hull-example-008.png"
_D009 = "hull-example-009.png"
_DEXP = "hull-designs.png"
_DGEM = "hull-designs-gemini.png"

# The section law the whole grammar is built on, said once so the rows can
# point at it. RE-AUDITED 2026-08-14 against the shipped P1/P2 kernel: the
# section is now keel / bilge / sheer with a quadratic-Bezier BILGE FILLET
# driven by the `roundness` gene (closed-form area; roundness == 0 reproduces
# the legacy chine bit-for-bit) — so "round bilge" is EXPRESSIBLE and the
# marker that claimed otherwise is gone (it described a kernel two rebuilds
# old; the registry saying a shipped capability was impossible is audit
# finding G0-P0). Likewise `total_resistance(..., separation=)` carries
# demihull spacing into the production wave-interference term, so the
# separation marker's premise is dead. What genuinely remains inexpressible
# is stated below, in present-tense truth.
# RE-VERDICTED 2026-08-28, twice, and NARROWED to present-tense truth
# (PLM section 3 step 7). Two of the three clauses this marker used to
# carry are now false and were measured false, not argued away:
#   * "`roundness` is a single scalar applied at every station" — RETIRED
#     by rho(x) (genes rho_bow/rho_len, Gate RHO-X): the bilge warps along
#     the hull, so a U-forward / V-aft family IS drawable.
#   * "multi-chine transitions cannot be built" — RETIRED by Phase 5 /
#     BUILD-PLAN PV-4 (genes ch2_z/ch2_y, Gate MULTI-CHINE): the topside
#     is a knuckle LIST and a second chine is an exact vertex of the
#     sampled section.
# What genuinely remains is the FLARE half and the deadrise warp, and the
# marker now says only that. A stale marker is worse than no marker: it
# keeps a family reading Expressible.NO after the capability shipped,
# which is the 2026-08-11 defect (four documents asserting work was
# outstanding that was already done) wearing a registry's clothes.
_M_SECTION = ("a section whose FLARE varies with x: `flare` is a single "
              "scalar applied at every station and deadrise warp is "
              "forward-only, so a family needing per-station flare control "
              "(NPL-style varying sections) cannot be built. The bilge "
              "radius and the chine COUNT are no longer part of this: "
              "rho(x) warps the one and the Phase-5 knuckle list adds the "
              "other")
_M_SECOND_HULL = ("a second hull as GEOMETRY: hull count and separation live "
                  "in mission.VesselConfig and the physics evaluates n "
                  "IDENTICAL translated demihulls (interference + "
                  "parallel-axis stability terms), but the genome carries "
                  "one moulded surface — no distinct demihull form, no "
                  "cross-structure, no bridge deck")
_M_WET_DECK = ("a wet deck: no clearance parameter, so "
               "resistance.wet_deck_clearance_g has nothing to score")
_M_FLARE = ("flare that vanishes forward INDEPENDENTLY of section area: the "
            "LAW varies along the length now (flare/flare_bow/flare_len, "
            "2026-08-24), but delivered flare is scaled by the area curve "
            "a(x) pending the independent design-waterline B(x) — full "
            "decoupling was implemented 2026-08-26 and MEASURED to collapse "
            "plan convexity 0.5 -> 0.32, so the taper stays; at r_stem = 0 "
            "the stem is a point and flare there is moot")
_M_STEM = ("stem rake, bow overhang or a counter stern: LOA == LWL by "
           "construction")
# _M_AFT_DEADRISE RETIRED 2026-08-27: the Gate 0E5C-CAP re-fit its text
# demanded has RUN (scripts/e5_chine_warp.py against the five-gene law).
# Measured: the aft warp hits the transom station of every published warped
# series to the decimal, the deepv reconstruction delivers 14/24/27 deg
# (tests/test_hull_kb.py), and the three planing rows that cited this
# marker dropped it — their remaining gap is _M_APPENDAGE (pads, strakes,
# steps), which is real. The FORWARD warp's reach is the open limit now,
# and it is the warp survey's finding, not a formlib marker.
_M_APPENDAGE = ("appendages, steps, strakes, bulbs or foils: absent from "
                "geometry.py entirely")
_M_ASYMMETRIC = ("an asymmetric section: every section is symmetric about the "
                 "hull centreline, and catamaran_interference assumes two "
                 "identical demihulls")
# SUPERSEDED IN HALF ON 2026-08-14, and the half that survived is the half
# that has a SOURCE behind its refusal.
#
# It used to read: "a demihull at L/B > 8.5: grammar.check's L_OVER_B_BAND
# refuses it, and B_OVER_T_BAND's floor of 1.8 refuses B/T 1.33". The L/B
# clause is GONE — `grammar.PROPORTION_BANDS[HullRole.DEMIHULL]` now carries
# `SOTON_DEMIHULL_L_OVER_B`'s 15.10 ceiling, so L/B 15.00 is expressible and
# the mission's slenderness is no longer a grammar limitation.
#
# The B/T clause STAYS, and it is not a code limitation at all: the target's
# 0.8/0.6 = 1.33 is below the Southampton series' own floor of 1.50, so there
# is no published demihull at that draft to band against. That is a MISSING
# SOURCE, and it is recorded as such rather than dissolved by widening a bar to
# fit the target — which is the one move this file exists to prevent.
_M_LB_BAND = ("a demihull at B/T < 1.50: below the Southampton catamaran "
              "demihull series' own floor, so grammar refuses it as OUT OF "
              "SOURCED RANGE. The target's 0.8/0.6 = 1.33 is 11% under it. "
              "This is missing EVIDENCE, not a missing feature — the "
              "slenderness (L/B 15.10) became expressible on 2026-08-14")
_M_SUBMERGED = ("a submerged buoyant body with a piercing strut: the hull is "
                "one surface from keel to sheer")

FAMILIES: tuple[FormFamily, ...] = (

    # ---------------------------------------------------------------- 1. monohull, displacement
    FormFamily(
        key="slender_displacement",
        name="Slender displacement monohull",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.10, 0.35, Basis.APPROX, "displacement practice"),
        efficiency=(
            "A long, narrow body spreads the same volume over a longer "
            "pressure signature, so the bow and stern wave systems are weaker "
            "and the wave-making component collapses."),
        candidacy=Candidacy.ADJACENT,
        candidacy_reason=(
            "the mission's demihull IS this form; it is ADJACENT rather than "
            "TARGET only because the topology is a catamaran and a demihull "
            "is not a monohull — its slenderness and fine-entry rules "
            "transfer whole"),
        expressible=Expressible.PARTIAL,
        missing=(_M_LB_BAND,),
        drawings=(_D000, _DEXP, _D004),
        proportions={
            "l_over_b": _b(6.0, 12.0, Basis.APPROX,
                           "practice for a long-range displacement monohull; "
                           "no anchor in tree"),
            "b_over_t": _b(2.0, 4.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.55, 0.65, Basis.APPROX, "CP_VS_FN displacement row"),
            "cb": _b(0.35, 0.50, Basis.APPROX, "practice; no anchor"),
            "alpha_e_deg": _b(7.0, 12.0, Basis.APPROX,
                              "fine-entry practice; 004 draws '< 12 deg'"),
        },
        notes=("000 gives its speed band as 5-10 kn and calls it 'best for "
               "5-10 kn'; 'long range efficiency' on hull-designs.png",),
    ),
    FormFamily(
        key="moderate_displacement",
        name="Moderate displacement monohull",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.15, 0.35, Basis.APPROX, "displacement practice"),
        efficiency=(
            "Trades some slenderness for interior volume; the ends stay fine "
            "enough that flow reattaches without separation, so the penalty "
            "is wetted area rather than wave-making."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "a beamier monohull buys volume the mission does not need and "
            "costs the wave-making advantage that is the entire reason a "
            "solar boat can move on 6-8 kWp"),
        expressible=Expressible.YES,
        missing=(),
        drawings=(_D000, _DEXP),
        proportions={
            "l_over_b": _b(4.0, 6.5, Basis.APPROX, "practice; no anchor"),
            "b_over_t": _b(2.5, 5.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.58, 0.66, Basis.APPROX, "CP_VS_FN displacement row"),
            "cb": _b(0.42, 0.55, Basis.APPROX, "practice; no anchor"),
        },
    ),
    FormFamily(
        key="full_displacement",
        name="Full displacement monohull",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.10, 0.30, Basis.APPROX, "displacement practice"),
        efficiency=(
            "Maximum volume per metre of length; efficient only where the "
            "speed is low enough that wave-making has not yet become the "
            "dominant term, which is why its ceiling is the lowest here."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "'high volume / payload' is not the mission's objective; at Fn "
            "0.3 a full body is squarely in the wave-making-dominant region "
            "and pays for the volume in propulsive power that solar cannot "
            "supply"),
        expressible=Expressible.YES,
        missing=(),
        drawings=(_D000, _DEXP),
        proportions={
            "l_over_b": _b(3.0, 5.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.60, 0.72, Basis.APPROX, "CP_VS_FN displacement row"),
            "cb": _b(0.50, 0.65, Basis.APPROX, "practice; no anchor"),
        },
    ),
    FormFamily(
        key="round_bilge_displacement",
        name="Round-bilge displacement monohull",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.10, 0.40, Basis.APPROX,
              "practice; the NPL series covers Fn 0.30-1.20 of this range"),
        efficiency=(
            "A curved bilge is the shortest girth for a given section area "
            "and has no crease to shed a vortex, so it carries the least "
            "wetted surface and the smoothest pressure recovery of any "
            "displacement section — this is the streamlined body, in water."),
        candidacy=Candidacy.ADJACENT,
        candidacy_reason=(
            "the mission's demihull section IS a round bilge (004 'ROUND-BILGE "
            "SECTION: MINIMIZES WETTED SURFACE AREA', 003, gemini panel 4); "
            "ADJACENT rather than TARGET because the topology is a catamaran"),
        expressible=Expressible.NO,
        missing=(_M_SECTION,),
        drawings=(_D000, _D003, _D004, _DEXP, _DGEM),
        proportions={
            "l_over_b": _NPL_L_OVER_B,
            "b_over_t": _NPL_B_OVER_T,
            "cp": _b(0.55, 0.70, Basis.APPROX,
                     "CP_VS_FN, widened for NPL-type slender forms"),
            "alpha_e_deg": _b(7.0, 14.0, Basis.APPROX,
                              "fine-entry practice; no anchor"),
        },
        notes=(f"the NPL bands are the only SERIES basis in this file; "
               f"{_NPL_EXCLUDES_TARGET}",),
    ),
    FormFamily(
        key="hard_chine_displacement",
        name="Hard-chine displacement monohull",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.10, 0.40, Basis.APPROX, "practice"),
        efficiency=(
            "Buildable from flat sheet and stiff for its weight; the chine "
            "crease costs a little separation drag at displacement speed and "
            "buys nothing back until the flow can separate cleanly off it."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "it is the ONLY form the current grammar can build, and that is a "
            "fact about the code rather than an argument for the hull: at Fn "
            "0.2-0.3 a chine is a drag penalty with no compensating dynamic "
            "lift or spray separation to earn it back"),
        expressible=Expressible.YES,
        missing=(),
        drawings=(_D000, _DEXP),
        ast_typology="SHARP_CHINE",
        proportions={
            "l_over_b": _b(2.2, 8.5, Basis.MEASURED,
                           "grammar.L_OVER_B_BAND, the band the L0 gate "
                           "actually enforces"),
            "b_over_t": _b(1.8, 12.0, Basis.MEASURED, "grammar.B_OVER_T_BAND"),
            # 25.0 -> 38.0 on 2026-08-26, WITH the grammar bound it cites:
            # the beta_mid ceiling widened to admit the published deep-V
            # canon (Keuning 1993 at 30 deg, Naples NSS to 37.4).
            # tests/test_formlib.py::test_the_deadrise_bound_is_not_declared_twice
            # is the fence that caught this copy the same day.
            "deadrise_deg": _b(0.0, 38.0, Basis.MEASURED,
                               "grammar.PARAMS beta_mid bounds"),
            "cp": _b(0.55, 0.70, Basis.APPROX, "CP_VS_FN; no anchor"),
        },
        notes=("000: 'good initial stability, efficient at lower speeds, "
               "5-12 kn'. This is the family `hull_ast.Typology.SHARP_CHINE` "
               "already names.",),
    ),
    FormFamily(
        key="pram_dory",
        name="Pram / dory / panga",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.10, 0.40, Basis.APPROX, "practice"),
        efficiency=(
            "A shallow, rockered flat-ish bottom with a full bow carries "
            "payload on very little draft; the blunt entry makes it a "
            "high-payload rather than a low-drag form."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "a full bow is the opposite of the fine entrance every solar "
            "drawing calls for; 007 sells it on 'high payload-to-power ratio', "
            "which is a different objective from low power at fixed payload"),
        expressible=Expressible.PARTIAL,
        missing=(_M_STEM,),
        drawings=(_D007, _DEXP),
        ast_typology="PRAM",
        proportions={
            "l_over_b": _b(3.0, 5.5, Basis.APPROX, "practice; no anchor"),
            "deadrise_deg": _b(0.0, 12.0, Basis.APPROX,
                               "near-flat bottom; hull_ast PRAM bounds "
                               "beta_bow at <= 25 deg"),
            "cp": _b(0.58, 0.72, Basis.APPROX, "full ends; no anchor"),
        },
        notes=("007 labels it 'Efficient Low-Drag Entry' AND 'High "
               "Payload-to-Power Ratio' on the same panel while drawing a full "
               "bow with pronounced rocker; the two claims are in tension and "
               "the drawn shape is the payload one",),
    ),
    FormFamily(
        key="wave_piercing_monohull",
        name="Wave-piercing monohull",
        topology=Topology.MONOHULL,
        regime=Regime.SEMI_DISPLACEMENT,
        fn=_b(0.35, 0.70, Basis.APPROX, "practice; 000 gives 8-20 kn"),
        efficiency=(
            "A long fine forebody with little reserve buoyancy forward passes "
            "through a wave crest instead of lifting over it, so added "
            "resistance in a seaway stays low — a seakeeping economy, not a "
            "calm-water one."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "the economy it buys is added resistance in waves at high Fn; at "
            "Fn 0.2-0.3 in coastal service it costs reserve buoyancy forward "
            "and returns nothing"),
        expressible=Expressible.NO,
        missing=(_M_FLARE,),
        drawings=(_D000, _DGEM),
        proportions={
            "l_over_b": _b(7.0, 12.0, Basis.APPROX, "practice; no anchor"),
            "alpha_e_deg": _b(5.0, 10.0, Basis.APPROX,
                              "wave-piercer practice; no anchor"),
            "cp": _b(0.62, 0.75, Basis.APPROX, "CP_VS_FN semi-displacement"),
        },
    ),
    FormFamily(
        key="axe_bow",
        name="Axe-bow wave-piercing monohull (Ulstein-style)",
        topology=Topology.MONOHULL,
        regime=Regime.SEMI_DISPLACEMENT,
        fn=_b(0.35, 0.80, Basis.APPROX, "fast offshore practice"),
        efficiency=(
            "Zero flare volume forward and a deep vertical stem move the "
            "pitch axis aft and stop the bow being driven up by a wave, which "
            "removes the slam and the speed loss rather than the calm-water "
            "drag."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "a seakeeping trade for a fast offshore ship; at Fn 0.2-0.3 it "
            "buys nothing and costs reserve buoyancy forward. Its panel on "
            "002 also carries the reversed 'High Cp, Low Fn' label directly "
            "above 'Very Low prismatic coefficient entry'"),
        expressible=Expressible.NO,
        missing=(_M_FLARE, _M_SECTION),
        drawings=(_D002, _D000, _DEXP, _DGEM),
        proportions={
            "l_over_b": _b(6.0, 11.0, Basis.APPROX, "practice; no anchor"),
            "alpha_e_deg": _b(4.0, 9.0, Basis.APPROX,
                              "002 'Slender Entrance'; no number drawn"),
            "cp": _b(0.62, 0.78, Basis.APPROX, "CP_VS_FN semi-displacement"),
        },
    ),

    # ---------------------------------------------------------------- 2. monohull, semi-displacement
    FormFamily(
        key="semi_displacement_chine_aft",
        name="Semi-displacement, round forward / hard chines aft",
        topology=Topology.MONOHULL,
        regime=Regime.SEMI_DISPLACEMENT,
        fn=_b(0.35, 0.65, Basis.APPROX, "transitional practice"),
        efficiency=(
            "Round sections forward keep the entry fair while chines aft give "
            "the flow a clean line to separate from, so the stern stops "
            "sucking down as speed rises and the transition to lift is smooth."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "the SKU never reaches the transitional regime this form exists "
            "for; its ONE transferable idea — that section type may vary "
            "along the length — is recorded as a grammar gap, not as a "
            "candidate hull"),
        expressible=Expressible.NO,
        missing=(_M_SECTION,),
        drawings=(_D003, _DGEM),
        proportions={
            "l_over_b": _b(3.5, 6.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.62, 0.72, Basis.APPROX, "003 'Moderate Cp'"),
            "deadrise_deg": _b(10.0, 18.0, Basis.APPROX, "practice; no anchor"),
        },
    ),
    FormFamily(
        key="wedge_multichine",
        name="Wedge / multi-chine",
        topology=Topology.MONOHULL,
        regime=Regime.SEMI_DISPLACEMENT,
        fn=_b(0.30, 0.65, Basis.APPROX, "practice; 000 gives 6-15 kn"),
        efficiency=(
            "Several chines approximate a round bilge in flat sheet, so the "
            "girth and the separation penalty both fall while the hull stays "
            "developable and buildable."),
        # RE-VERDICTED 2026-08-28, CANDIDATE -> EXCLUDED, and the reason is
        # that the row's own argument expired in the best possible way.
        # It was a CANDIDATE because the multi-chine section law was the
        # buildable approximation to the round bilge — i.e. on
        # BUILDABILITY, which this library's own rule says is never a
        # candidacy argument. Phase 5 landed that law (Gate MULTI-CHINE)
        # and thereby dissolved the argument: a knuckle list is a section
        # law available to EVERY family, not a property that distinguishes
        # this one. What is left of the row is the planing wedge, and a
        # wedge is excluded on exactly the grounds every other planing
        # device is.
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "THE VERDICT ATTACHES TO THE MULTI-CHINE SECTION LAW AND NOT TO "
            "THE PLANING WEDGE, and the two are one panel only because 000 "
            "draws them as one. The section law LANDED on 2026-08-28 (Phase "
            "5 / PV-4, genes ch2_z/ch2_y, Gate MULTI-CHINE) and is now "
            "available to every family, so it no longer distinguishes this "
            "one — and it never was a candidacy argument, because 'it is "
            "what we can build' is not one. What remains is the wedge: a "
            "flat lifting surface aft is a planing device and is EXCLUDED "
            "on the same grounds as every other one"),
        # RE-VERDICTED 2026-08-28: NO -> YES. This row's own
        # candidacy_reason named the blocker exactly — "reachable by the
        # same grammar change (more section points)" — and that change
        # landed as Phase 5 / PV-4 (Gate MULTI-CHINE). The section law is
        # no longer what stops this family; nothing is. The WEDGE half
        # stays excluded on planing grounds, which is a candidacy verdict
        # and not an expressibility one, and the two must not be confused.
        expressible=Expressible.YES,
        missing=(),
        drawings=(_D000, _DEXP),
        proportions={
            "l_over_b": _b(3.0, 8.0, Basis.APPROX, "practice; no anchor"),
            "deadrise_deg": _b(8.0, 20.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.58, 0.72, Basis.APPROX, "CP_VS_FN; no anchor"),
        },
        notes=("000 sells it on 'reduced slamming / good rough water "
               "performance'; the reason it is kept open here is the WETTED "
               "SURFACE argument, not the slamming one",
               "THE TWO SHEETS DISAGREE ABOUT ITS REGIME. 000 files "
               "'WEDGE / MULTI-CHINE' under 'MONOHULLS - DISPLACEMENT & "
               "SEMI-DISPLACEMENT' at 6-15 kn; hull-designs.png files 'WEDGE "
               "HULL - Stability + lift' under 'MONOHULLS - PLANING'. Both are "
               "right about a different object, which is the evidence that the "
               "panel names two forms. This row follows 000, because the "
               "MULTI-CHINE half is the half the mission can use",),
    ),

    # ---------------------------------------------------------------- 3. monohull, planing
    FormFamily(
        key="deep_v_planing",
        name="Deep-V planing (24 deg deadrise)",
        topology=Topology.MONOHULL,
        regime=Regime.PLANING,
        fn=_b(0.70, 2.00, Basis.APPROX, "planing practice"),
        efficiency=(
            "Not efficient — deadrise is bought to soften impact, and a deep "
            "V carries the highest induced drag of any planing bottom; it is "
            "the rough-water end of a lift-dominated trade."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "dynamic lift is irrelevant below Fn ~0.5. Applying a 24 deg "
            "deadrise to a solar demihull is the single most likely wrong "
            "answer this library exists to prevent"),
        expressible=Expressible.PARTIAL,
        missing=(_M_APPENDAGE,),
        drawings=(_DGEM, _DEXP, _D001, _D003),
        proportions={
            "l_over_b": _b(2.5, 4.5, Basis.APPROX, "practice; no anchor"),
            "deadrise_deg": _b(20.0, 26.0, Basis.DRAWING,
                               "hull-designs-gemini.png panel 1, "
                               "'DEEP-V HULL (24 DEADRISE)'"),
            "cp": _b(0.70, 0.90, Basis.APPROX, "CP_VS_FN planing row"),
        },
    ),
    FormFamily(
        key="modified_v_planing",
        name="Modified-V planing (18 deg deadrise, variable)",
        topology=Topology.MONOHULL,
        regime=Regime.PLANING,
        fn=_b(0.60, 1.60, Basis.APPROX, "planing practice"),
        efficiency=(
            "Warping the bottom from a deep forward deadrise to a flatter aft "
            "one puts the sharp sections where the impact is and the flat "
            "lifting surface where the load is, which is the cheapest planing "
            "compromise."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "same regime argument as deep-V. Noted only because the VARIABLE "
            "DEADRISE law it needs is the one thing the current grammar "
            "already does well (beta_mid/beta_bow/beta_len)"),
        expressible=Expressible.PARTIAL,
        missing=(_M_APPENDAGE,),
        drawings=(_DGEM, _DEXP),
        proportions={
            "l_over_b": _b(2.5, 5.0, Basis.APPROX, "practice; no anchor"),
            "deadrise_deg": _b(14.0, 20.0, Basis.DRAWING,
                               "hull-designs-gemini.png panel 2, "
                               "'MODIFIED-V HULL (18 DEADRISE)'"),
            "cp": _b(0.68, 0.88, Basis.APPROX, "CP_VS_FN planing row"),
        },
    ),
    FormFamily(
        key="shallow_v_pad",
        name="Shallow-V / pad hull",
        topology=Topology.MONOHULL,
        regime=Regime.PLANING,
        fn=_b(0.60, 2.00, Basis.APPROX, "planing practice"),
        efficiency=(
            "A flat lifting surface has the best lift-to-drag of any planing "
            "bottom and the worst ride; a pad concentrates the load on a "
            "narrow strip to cut wetted area further at top speed."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason="a lift device on a hull that never planes",
        expressible=Expressible.PARTIAL,
        missing=(_M_APPENDAGE,),
        drawings=(_DEXP,),
        proportions={
            "l_over_b": _b(2.5, 5.0, Basis.APPROX, "practice; no anchor"),
            "deadrise_deg": _b(0.0, 12.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.70, 0.95, Basis.APPROX, "CP_VS_FN planing row"),
        },
    ),
    FormFamily(
        key="stepped_planing",
        name="Stepped planing hull",
        topology=Topology.MONOHULL,
        regime=Regime.PLANING,
        fn=_b(0.80, 2.00, Basis.APPROX, "planing practice"),
        efficiency=(
            "A transverse step ventilates the bottom so the hull rides on two "
            "short wetted patches instead of one long one; the saving is "
            "wetted area and it exists only while the step stays ventilated."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "a step works by ventilating a PLANING surface. There is no "
            "planing surface at Fn 0.2-0.3, so a step would be a flooded "
            "cavity and a drag source"),
        expressible=Expressible.NO,
        missing=(_M_APPENDAGE, _M_SECTION),
        drawings=(_D007, _DGEM, _DEXP),
        proportions={
            "l_over_b": _b(3.0, 5.5, Basis.APPROX, "practice; no anchor"),
            # Same correction as `cathedral_tunnel`: 007 says "Constant deep-V
            # deadrise" and prints no angle. The band was borrowed from the
            # deep-V panel on a DIFFERENT sheet, which makes it practice, not
            # a reading.
            "deadrise_deg": _b(18.0, 26.0, Basis.APPROX,
                               "007 says 'constant deep-V deadrise' and prints "
                               "no angle; edges borrowed from the deep-V panel "
                               "on hull-designs-gemini.png, i.e. practice"),
            "cp": _b(0.72, 0.95, Basis.APPROX, "CP_VS_FN planing row"),
        },
    ),
    FormFamily(
        key="cathedral_tunnel",
        name="Cathedral / tri-hedral tunnel hull",
        topology=Topology.MONOHULL,
        regime=Regime.PLANING,
        fn=_b(0.60, 2.00, Basis.APPROX, "planing practice"),
        efficiency=(
            "Two outboard sponsons trap air under a central tunnel, adding "
            "aerodynamic lift and a very wide static waterplane; efficient in "
            "stability per metre, not in drag."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "the tunnel's lift is AERODYNAMIC and needs planing speed; at 6 kn "
            "it is a wetted cavity. 007's panel also carries the copy-pasted "
            "'Low L/B, High Fn, Dynamic lift dominant' block"),
        expressible=Expressible.NO,
        missing=(_M_SECTION, _M_SECOND_HULL),
        drawings=(_D007, _D000, _DEXP),
        proportions={
            # WAS `Basis.DRAWING` until 2026-08-13, and that was provenance
            # inflation of exactly the kind this module's docstring warns
            # about: 007 states "Low L/B" IN WORDS and prints no number, so a
            # numeric interval of 2.5-4.0 cannot have come off the sheet. The
            # words are still evidence — they are why the band is low — but the
            # EDGES are practice, so the basis is the practice one.
            "l_over_b": _b(2.5, 4.0, Basis.APPROX,
                           "practice for a cathedral hull; 007 says 'Low L/B' "
                           "in words and prints no number, so the direction is "
                           "drawn and the edges are not"),
            "cp": _b(0.70, 0.92, Basis.APPROX, "CP_VS_FN planing row"),
        },
    ),

    # ---------------------------------------------------------------- 4. catamaran
    FormFamily(
        key="slender_symmetric_cat_demihull",
        name="Slender symmetric catamaran demihull",
        topology=Topology.CATAMARAN,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.15, 0.40, Basis.DRAWING,
              "004/005/008/009 print 'Fn 0.2 - 0.35'; widened at both ends to "
              "cover the mission's 0.20-0.30 with margin. The '7-12 knots' on "
              "the same title blocks is NOT used (see _SPEED_LABEL_CONFLICT)"),
        efficiency=(
            "THE MISSION'S FORM. An extremely slender round-bilge demihull "
            "makes almost no wave of its own, and two of them can be spaced "
            "so that each hull's wave system cancels the other's — the only "
            "form here whose efficiency comes from the ARRANGEMENT as well as "
            "the shape."),
        candidacy=Candidacy.TARGET,
        candidacy_reason=(
            "this is what the mission is: a solar-electric displacement "
            "catamaran at Fn 0.2-0.3, drawn five times in this set "
            "(001, 004, 005, 008, 009) and dimensioned twice"),
        expressible=Expressible.NO,
        missing=(_M_SECOND_HULL, _M_WET_DECK, _M_LB_BAND),
        drawings=(_D001, _D004, _D005, _D008, _D009, _D000, _DEXP, _DGEM),
        proportions={
            "l_over_b": _b(12.0, 18.0, Basis.DRAWING,
                           "001 'L/B_h > 12'; 008 states 15.3 on a 12 m hull "
                           "and 009 states 17.8 on a 16 m hull"),
            "b_over_t": _b(1.2, 2.0, Basis.APPROX,
                           "a deep narrow demihull; the mission's 0.8/0.6 = "
                           "1.33 sits inside. No anchor in tree, and BELOW "
                           "grammar.B_OVER_T_BAND's floor of 1.8"),
            "cp": _b(0.58, 0.70, Basis.APPROX,
                     "slender round-bilge practice; NPL-type forms run near "
                     "0.69 at this Fn. No anchor in tree"),
            "cb": _b(0.35, 0.50, Basis.APPROX, "practice; no anchor"),
            "alpha_e_deg": _b(6.0, 12.0, Basis.DRAWING,
                              "004 '< 12 deg', 008 '< 10 deg', 009 '< 9 deg'"),
        },
        notes=(
            f"separation: {_S_OVER_L_BEST_FN030} is the destructive optimum "
            f"and {_S_OVER_L_WORST_FN030} the constructive worst at Fn 0.30, "
            f"{_S_OVER_L_SRC}",
            "MEASURED from the drawings' own dimensions: 008 (B_oa 4.0 m, "
            "L/B_h 15.3) implies s/L 0.268 and 009 (B_oa 4.5 m, L/B_h 17.8) "
            "implies s/L 0.225 — BOTH well below the 0.445 optimum this tree "
            "measured, and 009 sits nearer the constructive-interference worst "
            "case than the destructive best. The drawings label this "
            "'HULL SEPARATION (s/L) TUNED FOR MINIMUM RESISTANCE' (005); their "
            "own numbers do not support the label",
            "MEASURED: 008's drawn tunnel clearance of 0.65 m clears the "
            "steady bow-wave rise U^2/2g up to Fn 0.30 (0.540 m) and FAILS at "
            "the Fn 0.35 its own title block claims (0.735 m); 009's 0.8 m "
            "clears Fn 0.30 (0.720 m) and fails Fn 0.35 (0.980 m). Both are "
            "sized for the mission band and not for the label",
            _NPL_EXCLUDES_TARGET,
            _SOTON_CONTAINS_TARGET,
            f"CORROBORATED 2026-08-13 against the published literature, and "
            f"the drawings win: the demihull slenderness 001/008/009 draw "
            f"(>12, 15.3, 17.8) is normal published practice, not an "
            f"illustrator's exaggeration — Southampton demihulls run "
            f"{_SOTON_L_OVER_B} and DTMB Series 64 monohulls "
            f"{_S64_L_OVER_B}. grammar.L_OVER_B_BAND's ceiling of 8.5 "
            f"contained neither, so the refusal of this mission's own hull was "
            f"the CODE's, not the drawings'. CLOSED 2026-08-14: the MONOHULL "
            f"band is UNCHANGED at 8.5 and a DEMIHULL is banded separately, "
            f"with a ceiling of {SOTON_DEMIHULL_L_OVER_B.high:g} taken from "
            f"this envelope itself (grammar.PROPORTION_BANDS). See "
            f"HULL-FORM-RULES.md §7.6",
            f"alpha_e: the drawn ceilings (004 '<12', 008 '<10', 009 '<9') "
            f"are FINER than monohull practice and that is not an error — the "
            f"only cross-series measurement found reports NO effect on R/W "
            f"over {_BLOUNT_ALPHA_E_FLAT}. NOT FOUND, and it is the gap that "
            f"matters most for this family: no peer-reviewed catamaran series "
            f"reporting a demihull entrance angle. See HULL-FORM-RULES.md "
            f"§7.1 S6",
            f"alpha_e is NOT independent of L/B: at this family's slenderness "
            f"the chord floor is "
            f"{alpha_e_chord_floor_deg(15.0, 0.60):.1f}-"
            f"{alpha_e_chord_floor_deg(15.0, 0.50):.1f} deg, comfortably "
            f"finer than 009's drawn '<9'. At the monohull grammar's L/B 2.2 "
            f"floor it is {alpha_e_chord_floor_deg(2.2, 0.60):.1f}-"
            f"{alpha_e_chord_floor_deg(2.2, 0.50):.1f} deg and a 7-12 deg "
            f"band is UNREACHABLE by any bow shape. "
            f"`formlib.alpha_e_chord_floor_deg` owns the arithmetic; "
            f"HULL-FORM-RULES.md §7.7 owns the argument",
        ),
    ),
    FormFamily(
        key="asymmetric_cat_demihull",
        name="Asymmetric catamaran demihull (flat inboard face)",
        topology=Topology.CATAMARAN,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.15, 0.45, Basis.APPROX, "practice"),
        efficiency=(
            "A flat inboard face is claimed to straighten the tunnel flow and "
            "weaken the wave the two hulls make between them; the literature "
            "is mixed and the benefit is spacing-dependent."),
        candidacy=Candidacy.CANDIDATE,
        candidacy_reason=(
            "drawn as an option on 001, as 'INWARD-FACING FLAT SIDES / REDUCED "
            "WAVE INTERFERENCE' on gemini panel 9, and asserted outright by "
            "008 and 009 ('ULTRA-SLENDER ASYMMETRIC DEMI-HULLS'). Kept open "
            "and ranked LOW: getting the spacing right (s/L) delivers most of "
            "the same effect for one parameter instead of a new topology and "
            "a new interference derivation"),
        expressible=Expressible.NO,
        missing=(_M_ASYMMETRIC, _M_SECOND_HULL, _M_LB_BAND),
        drawings=(_D001, _D008, _D009, _D000, _DEXP, _DGEM),
        proportions={
            "l_over_b": _b(12.0, 18.0, Basis.DRAWING,
                           "008 'L/B_h 15.3', 009 'L/B_h 17.8', both labelled "
                           "asymmetric"),
            "cp": _b(0.58, 0.70, Basis.APPROX, "as the symmetric demihull"),
        },
        notes=("008 and 009 label their demihulls ASYMMETRIC while drawing "
               "half-breadth views that are symmetric about each demihull "
               "centreline; the label is not supported by the drawn lines",),
    ),
    FormFamily(
        key="power_cat_demihull",
        name="Power-catamaran demihull",
        topology=Topology.CATAMARAN,
        regime=Regime.SEMI_DISPLACEMENT,
        fn=_b(0.35, 0.70, Basis.APPROX, "practice; 000 gives 10-20 kn"),
        efficiency=(
            "A beamier demihull with more aft buoyancy carries load and "
            "accepts transitional speeds; the wave-cancellation argument "
            "weakens as the hulls fatten."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "the regime is wrong and the direction is wrong — it trades away "
            "exactly the slenderness the solar power budget depends on"),
        expressible=Expressible.NO,
        missing=(_M_SECOND_HULL, _M_WET_DECK),
        drawings=(_D000, _DEXP),
        proportions={
            "l_over_b": _b(7.0, 12.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.62, 0.76, Basis.APPROX, "CP_VS_FN semi-displacement"),
        },
    ),
    FormFamily(
        key="wave_piercing_cat_demihull",
        name="Wave-piercing catamaran demihull",
        topology=Topology.CATAMARAN,
        regime=Regime.SEMI_DISPLACEMENT,
        fn=_b(0.35, 0.80, Basis.APPROX, "practice; 000 gives 10-20 kn"),
        efficiency=(
            "Very slender demihulls with minimal flare forward and a high "
            "cross-structure; the hulls slice the wave and the wet deck stays "
            "clear, so speed loss in a seaway is small."),
        candidacy=Candidacy.ADJACENT,
        candidacy_reason=(
            "its SLENDERNESS and WET-DECK CLEARANCE rules transfer directly "
            "and are two of the mission's own constraints; its BOW does not "
            "pay below Fn ~0.4, so borrow the rules and not the form"),
        expressible=Expressible.NO,
        missing=(_M_SECOND_HULL, _M_WET_DECK, _M_FLARE, _M_LB_BAND),
        drawings=(_D000, _DEXP, _DGEM),
        proportions={
            "l_over_b": _b(12.0, 20.0, Basis.APPROX,
                           "'SLENDER HULLS' on gemini panel 10; no number "
                           "drawn"),
            "cp": _b(0.60, 0.76, Basis.APPROX, "CP_VS_FN; no anchor"),
            "alpha_e_deg": _b(4.0, 9.0, Basis.APPROX, "practice; no anchor"),
        },
    ),
    FormFamily(
        key="tunnel_cat",
        name="Tunnel / planing catamaran",
        topology=Topology.CATAMARAN,
        regime=Regime.PLANING,
        fn=_b(0.60, 2.00, Basis.APPROX, "practice; 000 gives 8-18 kn"),
        efficiency=(
            "Two planing sponsons with an air tunnel between them; lift is "
            "part hydrodynamic and part aerodynamic and the form is fast, not "
            "cheap."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason="a planing catamaran on a hull that never planes",
        expressible=Expressible.NO,
        missing=(_M_SECOND_HULL, _M_SECTION, _M_APPENDAGE),
        drawings=(_D000, _DEXP),
        proportions={
            "l_over_b": _b(3.0, 7.0, Basis.APPROX, "practice; no anchor"),
            "deadrise_deg": _b(10.0, 22.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.70, 0.92, Basis.APPROX, "CP_VS_FN planing row"),
        },
    ),
    FormFamily(
        key="swath",
        name="SWATH / small-waterplane-area twin hull",
        topology=Topology.SMALL_WATERPLANE,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.10, 0.45, Basis.APPROX,
              "SWATH is a DISPLACEMENT form; 002's 'High Fn, dynamic lift "
              "dominant' is copy-pasted from the planing panel and discarded"),
        efficiency=(
            "Buoyancy lives in submerged torpedoes below the wave orbital "
            "motion and only thin struts pierce the surface, so wave "
            "excitation nearly vanishes — paid for with a large wetted area "
            "and almost no reserve stability."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "it buys MOTIONS at the cost of wetted surface and reserve "
            "stability. A solar boat's binding constraints are deck area and "
            "drag, so it pays the price and does not collect the benefit; it "
            "also needs active ride-control fins, i.e. continuous power"),
        expressible=Expressible.NO,
        missing=(_M_SUBMERGED, _M_SECOND_HULL, _M_SECTION),
        drawings=(_D002, _D000, _DEXP, _DGEM),
        proportions={
            "l_over_b": _b(8.0, 16.0, Basis.APPROX,
                           "of the submerged body; no number drawn"),
            "cp": _b(0.60, 0.80, Basis.APPROX,
                     "of the submerged body, which is nearly prismatic; no "
                     "anchor in tree"),
        },
        notes=("002 prints 'Low L/B, High Fn, Dynamic lift dominant' directly "
               "under its own 'Submerged Buoyancy' heading. A SWATH is carried "
               "by buoyancy by definition; the block is the planing panel's",),
    ),

    # ---------------------------------------------------------------- 5. trimaran and beyond
    FormFamily(
        key="stabilized_monohull_trimaran",
        name="Stabilized monohull trimaran (slender main hull + amas)",
        topology=Topology.TRIMARAN,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.15, 0.45, Basis.DRAWING,
              "006 prints 'Fn 0.2 - 0.35'; the '7-12 knots' beside it is "
              "discarded (see _SPEED_LABEL_CONFLICT)"),
        efficiency=(
            "The main hull can be far more slender than any catamaran "
            "demihull because it carries no transverse stability duty — the "
            "amas do that, and they are small enough to be nearly free."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "not the stated topology for this SKU. Recorded because its "
            "argument is the strongest hydrodynamic case in the whole set and "
            "would matter if the topology were ever reopened; 006 also "
            "carries the copy-pasted 'Low L/B, High Fn, Dynamic lift "
            "dominant' block under 'FINE MAIN HULL ENTRY'"),
        expressible=Expressible.NO,
        missing=(_M_SECOND_HULL, _M_LB_BAND),
        drawings=(_D006, _D000, _DEXP, _DGEM),
        proportions={
            "l_over_b": _b(12.0, 25.0, Basis.APPROX,
                           "'EXTREMELY SLENDER MAIN HULL (HIGH L/B_m)' on 006; "
                           "no number drawn"),
            "cp": _b(0.58, 0.72, Basis.APPROX, "practice; no anchor"),
        },
    ),
    FormFamily(
        key="high_speed_trimaran",
        name="High-speed trimaran (long thin hulls)",
        topology=Topology.TRIMARAN,
        regime=Regime.SEMI_DISPLACEMENT,
        fn=_b(0.35, 0.90, Basis.APPROX, "practice; 000 gives 8-20 kn"),
        efficiency=(
            "Three slender hulls spread the displacement over more length "
            "still; wave interference between main hull and amas can be tuned "
            "the way a catamaran's spacing can."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason="not the stated topology, and the wrong regime",
        expressible=Expressible.NO,
        missing=(_M_SECOND_HULL, _M_LB_BAND),
        drawings=(_DGEM, _D000, _DEXP),
        proportions={
            "l_over_b": _b(12.0, 20.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.62, 0.78, Basis.APPROX, "CP_VS_FN semi-displacement"),
        },
    ),
    FormFamily(
        key="quadrimaran",
        name="Quadrimaran (four slender hulls)",
        topology=Topology.QUADRIMARAN,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.15, 0.45, Basis.APPROX,
              "practice; capped at REGIME_FN[DISPLACEMENT]'s ceiling"),
        efficiency=(
            "Four hulls give a very large deck for the displacement and a "
            "four-body interference pattern; wetted surface rises faster than "
            "wave-making falls."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "not the stated topology; four hulls multiply the wetted surface "
            "that already dominates resistance at Fn 0.2-0.3"),
        expressible=Expressible.NO,
        missing=(_M_SECOND_HULL,),
        drawings=(_DGEM,),
        proportions={
            "l_over_b": _b(10.0, 20.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.58, 0.74, Basis.APPROX, "practice; no anchor"),
        },
    ),

    # ---------------------------------------------------------------- 6. special purpose
    FormFamily(
        key="pontoon",
        name="Pontoon",
        topology=Topology.CATAMARAN,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.10, 0.35, Basis.APPROX, "practice; 000 gives 6-12 kn"),
        efficiency=(
            "Two cylindrical tubes: enormous deck area and payload per metre, "
            "a blunt entry and a large wetted surface — simple rather than "
            "streamlined."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "the deck-area argument is genuinely attractive for solar, and "
            "the hydrodynamics refuse it: a constant-section tube has no fine "
            "entry and no pressure recovery, so drag per tonne is high exactly "
            "where the power budget is smallest"),
        expressible=Expressible.NO,
        missing=(_M_SECOND_HULL, _M_SECTION),
        drawings=(_D000, _DEXP),
        proportions={
            "l_over_b": _b(6.0, 14.0, Basis.APPROX, "of one tube; no anchor"),
            "cp": _b(0.75, 0.95, Basis.APPROX,
                     "a near-constant-section tube is nearly prismatic; no "
                     "anchor in tree"),
        },
        notes=("its Cp band is high for a displacement form, and that is the "
               "physical statement, not an error: a prismatic tube has almost "
               "no taper. It is the one row where a high Cp at low Fn is "
               "correct, and it is correct for a reason that also makes the "
               "hull slow",),
    ),
    FormFamily(
        key="semi_submersible",
        name="Semi-submersible",
        topology=Topology.SMALL_WATERPLANE,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.05, 0.30, Basis.APPROX, "practice"),
        efficiency=(
            "Buoyancy below the wave zone on columns; extreme motion "
            "stability and a large wetted surface. A station-keeping form, "
            "not a transit form."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason="same trade as SWATH, further in the same direction",
        expressible=Expressible.NO,
        missing=(_M_SUBMERGED, _M_SECOND_HULL, _M_SECTION),
        drawings=(_DEXP,),
        proportions={
            "l_over_b": _b(2.0, 8.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.60, 0.90, Basis.APPROX, "practice; no anchor"),
        },
    ),
    FormFamily(
        key="air_cushion",
        name="Air cushion / surface-effect",
        topology=Topology.SUPPORTED,
        regime=Regime.PLANING,
        fn=_b(0.60, 3.00, Basis.APPROX, "practice; 000 gives 10-20 kn"),
        efficiency=(
            "An air cushion lifts most of the weight clear of the water and "
            "the drag falls dramatically — but the lift itself is bought with "
            "continuous fan power that never stops."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "continuous lift power on a solar energy budget. The lift fan is "
            "a load that runs whenever the boat moves, and the PV array on "
            "008 is 6-8 kWp for the WHOLE vessel"),
        expressible=Expressible.NO,
        missing=(_M_SECTION, _M_APPENDAGE, _M_SECOND_HULL),
        drawings=(_D000, _DEXP),
        proportions={
            "l_over_b": _b(2.0, 5.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.70, 0.95, Basis.APPROX, "practice; no anchor"),
        },
    ),
    FormFamily(
        key="foil_assisted",
        name="Foil-assisted / hydrofoil",
        topology=Topology.SUPPORTED,
        regime=Regime.PLANING,
        fn=_b(0.50, 3.00, Basis.APPROX, "practice"),
        efficiency=(
            "A foil carries the weight on a small high-aspect surface and "
            "lifts the hull out of its own wave system; the best lift-to-drag "
            "of anything here, ABOVE the take-off speed and not below it."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "foils do not pay their own drag below roughly Fn 0.5, and the "
            "mission ends at 0.3 — below take-off a foil is a permanently "
            "wetted appendage"),
        expressible=Expressible.NO,
        missing=(_M_APPENDAGE,),
        drawings=(_DEXP,),
        proportions={
            "l_over_b": _b(4.0, 12.0, Basis.APPROX,
                           "of the hull the foils carry; no anchor"),
            "cp": _b(0.60, 0.85, Basis.APPROX, "practice; no anchor"),
        },
    ),
    FormFamily(
        key="twin_keel_displacement",
        name="Twin-keel displacement monohull",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.10, 0.35, Basis.APPROX, "practice; 000 gives 6-12 kn"),
        efficiency=(
            "Two bilge keels give directional stability and let the boat dry "
            "out upright; both are handling and shore-side properties, and "
            "both add wetted surface."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "a catamaran already has directional stability from hull "
            "separation, so the keels would add wetted surface for a property "
            "the topology supplies free"),
        expressible=Expressible.NO,
        missing=(_M_APPENDAGE,),
        drawings=(_D000, _DEXP),
        proportions={
            "l_over_b": _b(3.0, 7.0, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.55, 0.68, Basis.APPROX, "CP_VS_FN displacement row"),
        },
    ),
    FormFamily(
        key="transom_stern_displacement",
        name="Transom-stern displacement monohull",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.15, 0.45, Basis.APPROX, "practice; 000 gives 6-15 kn"),
        efficiency=(
            "A clean transom lets the flow leave the hull at one line instead "
            "of being dragged around a rounded counter; efficient when the "
            "transom is dry or only lightly immersed, a drag source when it "
            "is deeply immersed at low speed."),
        candidacy=Candidacy.CANDIDATE,
        candidacy_reason=(
            "the mission's demihull ends in a transom and every solar drawing "
            "in the set calls for one (005 'TRANSOM STERN: CLEAN RELEASE', "
            "009 'DEEP IMMERSED TRANSOM'). It is expressible today via "
            "`r_transom` — but the IMMERSION penalty is modelled nowhere, so "
            "the ladder cannot see the failure mode this row exists to warn "
            "about"),
        expressible=Expressible.PARTIAL,
        missing=("transom immersion drag: Michell's integral has no transom "
                 "term and holtrop.particulars_from_floated hardcodes the "
                 "immersed transom to zero for small craft",),
        drawings=(_D000, _D003, _D005, _D008, _D009, _DEXP),
        proportions={
            "l_over_b": _b(3.0, 12.0, Basis.APPROX,
                           "a stern treatment spans the displacement forms; "
                           "no anchor"),
            "cp": _b(0.55, 0.72, Basis.APPROX, "CP_VS_FN displacement row"),
        },
        notes=("009 explicitly draws a DEEP IMMERSED transom and calls it "
               "'clean flow release at 12 knots'. At the mission's Fn 0.2-0.3 "
               "a deeply immersed transom is a drag penalty, not a release — "
               "the label is right for the knots on the sheet and wrong for "
               "the Froude numbers beside them",),
    ),
    FormFamily(
        key="bulbous_bow_displacement",
        name="Displacement monohull with a wave-cancellation bulb",
        topology=Topology.MONOHULL,
        regime=Regime.DISPLACEMENT,
        fn=_b(0.15, 0.30, Basis.APPROX,
              "gemini panel 5 says 'LARGE VESSEL' and 'OPTIMIZED F_D'"),
        efficiency=(
            "The bulb makes its own wave a half-cycle out of phase with the "
            "stem wave and the two partially cancel; it works only when the "
            "bulb is small compared with the hull and the design speed is "
            "narrow."),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "bulbs pay on large, full, low-Fn ships. On a 12 m demihull at "
            "L/B 15 the bulb's own wave is the same order as the hull's, so "
            "there is nothing to cancel against; "
            "`holtrop.particulars_from_floated` already hardcodes the bulb to "
            "zero for craft this size"),
        expressible=Expressible.NO,
        missing=(_M_APPENDAGE, _M_STEM),
        drawings=(_DGEM, _DEXP),
        proportions={
            "l_over_b": _b(5.0, 8.0, Basis.APPROX,
                           "the large full ships bulbs suit; no anchor"),
            "cb": _b(0.60, 0.85, Basis.APPROX, "practice; no anchor"),
            "cp": _b(0.62, 0.85, Basis.APPROX, "practice; no anchor"),
        },
    ),
)


FEATURES: tuple[Feature, ...] = (
    Feature(
        key="wet_deck_platform",
        name="Wet deck / cross-structure / tunnel arch",
        effect=(
            "spans the demihulls and carries the deck and the PV array; its "
            "UNDERSIDE height sets whether the tunnel flow stays air or "
            "becomes a slam"),
        candidacy=Candidacy.CANDIDATE,
        candidacy_reason=(
            "mandatory for the mission topology, and the quantity that "
            "governs it is already written: `resistance.bow_wave_rise` and "
            "`resistance.wet_deck_clearance_g` exist with zero production "
            "call sites, because there is no clearance to give them"),
        expressible=Expressible.NO,
        parameterised_by="one scalar (wet_deck_m, or wet_deck/BWL) + one "
                         "appended constraint row",
        drawings=(_D001, _D005, _D008, _D009, _DGEM),
        applies_to=("slender_symmetric_cat_demihull",
                    "asymmetric_cat_demihull",
                    "wave_piercing_cat_demihull"),
    ),
    Feature(
        key="hull_separation",
        name="Demihull separation s/L",
        effect=(
            "sets whether the two hulls' wave systems cancel or reinforce; it "
            "is the one arrangement variable with a first-order effect on "
            "resistance"),
        candidacy=Candidacy.CANDIDATE,
        candidacy_reason=(
            "mandatory. `resistance.michell_rw` already accepts `separation` "
            "and `total_resistance` does not pass it, so the ladder that is "
            "meant to design a catamaran currently computes the wave "
            "resistance of one isolated demihull"),
        expressible=Expressible.NO,
        parameterised_by="one scalar (s_over_L) threaded through "
                         "total_resistance into michell_rw",
        drawings=(_D001, _D005, _D008, _D009),
        applies_to=("slender_symmetric_cat_demihull",
                    "asymmetric_cat_demihull", "power_cat_demihull",
                    "wave_piercing_cat_demihull", "pontoon"),
    ),
    Feature(
        key="parallel_midbody",
        name="Parallel midbody",
        effect=(
            "a constant section over the middle of the length raises Cp "
            "without fattening the ends, which is how a slender hull gets "
            "volume without a blunt entry"),
        candidacy=Candidacy.CANDIDATE,
        candidacy_reason=(
            "drawn on every solar sheet (004, 005, 008, 009) and it is the "
            "mechanism behind the Cp band the mission wants. The grammar has "
            "`x_mb` (one max-beam STATION) and no midbody EXTENT, so a hull "
            "can have a peak but not a plateau"),
        # NO -> YES on 2026-08-27: `pmb` landed 2026-08-24 exactly as
        # `parameterised_by` prescribed, and the sac solve was corrected
        # 2026-08-26 to INVERT the flat-topped curve (audit D.4), so the
        # delivered Cp now equals the gene with the span active. MEASURED:
        # the hull-kb cruiser carries pmb 0.12 at convexity 0.927 with a
        # clean critique, and the landed barge carries its beam over 88%.
        expressible=Expressible.YES,
        parameterised_by="`pmb` (grammar 2026-08-24; solve corrected "
                         "2026-08-26)",
        drawings=(_D004, _D005, _D008, _D009),
        applies_to=("slender_symmetric_cat_demihull", "slender_displacement",
                    "round_bilge_displacement"),
    ),
    Feature(
        key="plumb_stem",
        name="Vertical / plumb stem",
        effect="maximises waterline length for a given overall length",
        candidacy=Candidacy.CANDIDATE,
        candidacy_reason=(
            "wanted by the mission and free — but free for the wrong reason: "
            "the grammar cannot make anything ELSE, because LOA == LWL by "
            "construction. It is the only drawn feature that is expressible, "
            "and it is expressible because it is compulsory"),
        expressible=Expressible.YES,
        parameterised_by="already implicit; a stem-rake parameter would be "
                         "needed to express its ALTERNATIVES",
        drawings=(_DGEM, _D004, _D008),
        applies_to=("slender_symmetric_cat_demihull", "axe_bow",
                    "wave_piercing_monohull"),
    ),
    Feature(
        key="u_shaped_bow_section",
        name="U-shaped bow section over a fine waterline",
        effect=(
            "a U section puts volume low and forward without widening the "
            "waterline, so reserve buoyancy is available without spoiling the "
            "entrance angle"),
        candidacy=Candidacy.CANDIDATE,
        candidacy_reason=(
            "004 draws it explicitly ('SECTION A-A (BOW): U-SHAPED') beside "
            "'SECTION B-B (MIDSHIP): SEMI-CIRCULAR' and 'SECTION C-C (STERN): "
            "LOW-VOLUME'. Those three labels are one statement — the section "
            "SHAPE changes along the length — and it is the single deepest "
            "thing the current parametrisation cannot say"),
        expressible=Expressible.NO,
        parameterised_by="a section law that is a function of x whose SHAPE, "
                         "not just whose dimensions, varies",
        drawings=(_D004,),
        applies_to=("slender_symmetric_cat_demihull",
                    "round_bilge_displacement", "slender_displacement"),
    ),
    Feature(
        key="zero_flare_forward",
        name="Zero flare volume forward",
        effect=(
            "removes reserve buoyancy at the bow so it pierces a wave instead "
            "of being lifted by it"),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "a wave-piercer property; the mission wants flare forward for "
            "reserve buoyancy. Listed because the GRAMMAR GAP it exposes is "
            "real for every family: flare is one scalar, applied at every "
            "station, one line below a deadrise law that already varies"),
        # NO -> PARTIAL on 2026-08-27: the three genes landed verbatim
        # (2026-08-24). Delivered flare remains SCALED BY a(x) (see
        # _M_FLARE for the measured reason the scaling stays), so zero
        # flare forward is expressible wherever the bow carries area
        # (r_stem > 0) and exact only in the limit — full independence
        # arrives with the design-waterline B(x).
        expressible=Expressible.PARTIAL,
        parameterised_by="flare / flare_bow / flare_len (landed 2026-08-24), "
                         "delivered through the a(x) envelope",
        drawings=(_D002, _DGEM),
        applies_to=("axe_bow", "wave_piercing_monohull",
                    "wave_piercing_cat_demihull"),
    ),
    Feature(
        key="chine_starting_aft",
        name="Chine that begins partway aft (round forward, chined aft)",
        effect=(
            "gives the forebody a fair round entry and the afterbody a clean "
            "separation line"),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "a semi-displacement device; the mission's demihull wants a round "
            "bilge for its whole length. Recorded because it and the round "
            "bilge are ONE grammar change, not two"),
        expressible=Expressible.NO,
        parameterised_by="a bilge radius r(x) that goes to zero aft — the "
                         "same longitudinal distribution that makes a round "
                         "bilge possible",
        drawings=(_D003,),
        applies_to=("semi_displacement_chine_aft",),
    ),
    Feature(
        key="lifting_strakes",
        name="Lifting strakes",
        effect="deflect spray downward and add dynamic lift while planing",
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason="a planing-lift device; there is no planing surface",
        expressible=Expressible.NO,
        parameterised_by="a new AST node — and for this mission, do not add it",
        drawings=(_D003, _DEXP),
        applies_to=("deep_v_planing", "modified_v_planing"),
    ),
    Feature(
        key="chine_flat",
        name="Chine flat",
        effect="a horizontal strip at the chine to knock down spray and lift",
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason="a planing-lift device; there is no planing surface",
        expressible=Expressible.NO,
        parameterised_by="a new AST node — and for this mission, do not add it",
        drawings=(_D003,),
        applies_to=("deep_v_planing", "modified_v_planing"),
    ),
    Feature(
        key="transverse_step",
        name="Transverse step / ventilation tunnel",
        effect="ventilates the planing bottom to cut wetted area",
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "works only on a ventilated planing surface; at Fn 0.2-0.3 it "
            "would be a flooded cavity"),
        expressible=Expressible.NO,
        parameterised_by="a new AST node — and for this mission, do not add it",
        drawings=(_D007, _DGEM, _DEXP),
        applies_to=("stepped_planing",),
    ),
    Feature(
        key="wave_cancellation_bulb",
        name="Bulbous / wave-cancellation bow",
        effect="makes a wave out of phase with the stem wave so the two cancel",
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "pays on large, full, low-Fn ships; on a 12 m demihull the bulb's "
            "wave is the same order as the hull's"),
        expressible=Expressible.NO,
        parameterised_by="a new AST node (a local forebody volume)",
        drawings=(_DGEM, _DEXP),
        applies_to=("bulbous_bow_displacement",),
    ),
    Feature(
        key="inverted_bow",
        name="Inverted / X / tulip / cutter bow",
        effect=(
            "moves waterline length forward and reserve buoyancy up, so the "
            "bow cuts rather than lifts and the deck stays dry"),
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "EIGHT separately-named panels across two sheets for one idea, all "
            "of them seakeeping trades at speeds the SKU never reaches. "
            "COUNTED 2026-08-13 rather than estimated (the figure here read "
            "'four' until the sheets were counted): 000 draws INVERTED BOW and "
            "TULIP BOW; hull-designs.png draws INVERTED BOW, TULIP HULL, "
            "X-BOW, CUTTER BOW, CAT'S PAW BOW, REVERSE BOW and MORTEK STYLE. "
            "A bow is a LOCAL TREATMENT, and a taxonomy that lists eight of "
            "them as peers of 'catamaran' is the flattening this module's "
            "family/feature split exists to undo"),
        expressible=Expressible.NO,
        parameterised_by="stem rake + a flare distribution; blocked by "
                         "LOA == LWL",
        drawings=(_D000, _DEXP),
        applies_to=("wave_piercing_monohull", "axe_bow"),
    ),
    Feature(
        key="ride_control_fins",
        name="Active ride-control fins",
        effect="actively damp pitch and heave on a low-waterplane platform",
        candidacy=Candidacy.EXCLUDED,
        candidacy_reason=(
            "active control needs continuous power and a seakeeping model "
            "this tree does not have: `seakeeping.py` computes HEAVE only, "
            "with no pitch RAO anywhere"),
        expressible=Expressible.NO,
        parameterised_by="an appendage node plus a pitch RAO to control "
                         "against",
        drawings=(_D002,),
        applies_to=("swath",),
    ),
    Feature(
        key="motor_recess",
        name="Aft-body motor recess",
        effect=(
            "a local cavity in the aft body housing the drive; a topology "
            "change, not a proportion"),
        candidacy=Candidacy.CANDIDATE,
        candidacy_reason=(
            "named by the project owner as a target detail. NO SHEET IN THIS "
            "SET DRAWS A RECESS. The closest thing is 006's 'AFT MAIN HULL "
            "VOLUME: SUPPORTS PROPULSION SYSTEM', and it is the OPPOSITE "
            "shape — added buoyancy aft to carry the drive, not a cavity cut "
            "into the hull for it. So the drive's accommodation is drawn once, "
            "as a volume; the recess is not drawn at all and nothing here is "
            "derived from one"),
        expressible=Expressible.NO,
        parameterised_by="a new AST node: a cavity has no scalar description",
        drawings=(_D006, _D000),
        applies_to=("slender_symmetric_cat_demihull",
                    "stabilized_monohull_trimaran"),
    ),
)


BY_KEY: Mapping[str, FormFamily] = {f.key: f for f in FAMILIES}
FEATURE_BY_KEY: Mapping[str, Feature] = {f.key: f for f in FEATURES}


# --------------------------------------------------------------------------
# queries


def families(candidacy: Candidacy | None = None,
             topology: Topology | None = None,
             regime: Regime | None = None) -> tuple[FormFamily, ...]:
    out = FAMILIES
    if candidacy is not None:
        out = tuple(f for f in out if f.candidacy is candidacy)
    if topology is not None:
        out = tuple(f for f in out if f.topology is topology)
    if regime is not None:
        out = tuple(f for f in out if f.regime is regime)
    return out


def proposable() -> tuple[FormFamily, ...]:
    """Families an optimiser may propose for `MISSION`.

    EXCLUDED is not "unlikely", it is "do not spend an evaluation here". This
    is the function a sampler should call; the full `FAMILIES` tuple is a
    reference library and calling it a menu is the error the docstring at the
    top of this file is about.
    """
    return tuple(f for f in FAMILIES if f.candidacy is not Candidacy.EXCLUDED)


def target() -> FormFamily:
    hits = families(candidacy=Candidacy.TARGET)
    if len(hits) != 1:
        raise ValueError(
            f"expected exactly one TARGET family, found {len(hits)}: "
            f"{[f.key for f in hits]}. A mission with two target forms has "
            f"not chosen one.")
    return hits[0]


def unexpressible() -> Mapping[str, tuple[str, ...]]:
    """family/feature key -> what the grammar cannot say about it.

    The union of the values is the geometry-rebuild backlog, and it is derived
    from the library rather than restated in prose, so a family that becomes
    expressible drops out of it by deleting one tuple entry.
    """
    out: dict[str, tuple[str, ...]] = {}
    for f in FAMILIES:
        if f.missing:
            out[f.key] = f.missing
    for ft in FEATURES:
        if ft.expressible is not Expressible.YES:
            out[ft.key] = (ft.parameterised_by,)
    return out


def drawn_dimension_verdict(row: str, lwl_m: float, beam_m: float,
                            draft_m: float) -> Mapping[str, bool | None]:
    """Does a vessel sit inside `DRAWN_DIMENSION_RANGES[row]`?

    `None` for a column the sheet prints as "Varies" — NOT `True`. An absent
    band is unmeasured, and scoring an unmeasured column as a pass is the
    defect class this whole module is written against (LESSONS.md #1).

    `beam_m` is the OVERALL beam for the multihull rows, because that is what
    the table's column means. Passing a demihull beam here compares two
    different quantities and will read as a spurious failure.
    """
    bands = DRAWN_DIMENSION_RANGES[row]
    out: dict[str, bool | None] = {}
    for key, value in (("lwl_m", lwl_m), ("beam_m", beam_m),
                       ("draft_m", draft_m)):
        band = bands.get(key)
        out[key] = None if band is None else band.contains(value)
    return out


def basis_census() -> Mapping[Basis, int]:
    """How many bands rest on each kind of evidence.

    Printed by `__main__` because the ratio is the honest headline: this is a
    library whose numbers are mostly practice, and a reader who does not know
    that will over-trust it.

    SCOPE IS `FAMILIES` ONLY — deliberately. `DRAWN_DIMENSION_RANGES` is 18
    more `Basis.DRAWING` bands, and folding them in would move the practice
    share from 88% to 78% without a single family band having improved. That
    is provenance inflation by aggregation: the question this census answers
    is "how much of the FAMILY LIBRARY is practice", and a transcribed table
    of overall dimensions is not an answer to it.
    """
    counts = {b: 0 for b in Basis}
    for f in FAMILIES:
        counts[f.fn.basis] += 1
        for band in f.proportions.values():
            counts[band.basis] += 1
    return counts


def _fmt(f: FormFamily) -> str:
    props = "  ".join(f"{k} {f.proportions[k]}"
                      for k in PROPORTION_KEYS if k in f.proportions)
    return (f"{f.candidacy.value.upper():<9} {f.key:<34} "
            f"{f.topology.value:<16} {f.regime.value:<18} "
            f"Fn {f.fn}\n           {props}")


def _alpha_e_floor_table() -> str:
    """The floor at the L/B values this project actually argues about."""
    rows = [
        (2.2, "grammar.L_OVER_B_BAND floor"),
        (3.0, "beamy small monohull"),
        (4.0, ""),
        (6.0, ""),
        (8.5, "grammar.L_OVER_B_BAND CEILING"),
        (12.0, "001 'L/B_h > 12'"),
        (15.0, "THE TARGET DEMIHULL"),
        (15.3, "008 as drawn"),
        (17.8, "009 as drawn"),
    ]
    out = [f"alpha_e CHORD FLOOR (deg) — see formlib.alpha_e_chord_floor_deg",
           f"  L_E/L from {_LE_OVER_L} ({_LE_OVER_L.source})",
           "",
           f"  {'L/B':>6}  {'L_E/L 0.50':>10}  {'L_E/L 0.60':>10}   note"]
    for lb, note in rows:
        lo = alpha_e_chord_floor_deg(lb, _LE_OVER_L.low)
        hi = alpha_e_chord_floor_deg(lb, _LE_OVER_L.high)
        out.append(f"  {lb:>6.1f}  {lo:>10.1f}  {hi:>10.1f}   {note}")
    out += [
        "",
        f"  the drawn ceilings are 12 / 10 / 9 deg (004 / 008 / 009) and the",
        f"  sourced flat band is {_BLOUNT_ALPHA_E_FLAT}",
        f"  calibration (n=1): FDS-5 at L/B 8.0 MEASURES "
        f"{_FDS5_ALPHA_E_DEG:.1f} deg against a floor of "
        f"{alpha_e_chord_floor_deg(8.0, 0.60):.1f} — tangent ~ 2x chord",
    ]
    return "\n".join(out)


def main() -> int:
    import sys
    if "--alpha-e-floor" in sys.argv:
        print(_alpha_e_floor_table())
        return 0
    print(f"MISSION: {MISSION.name}, Fn {MISSION.fn}, demihull "
          f"{MISSION.hull_lwl_m} x {MISSION.hull_bwl_m} x "
          f"{MISSION.hull_draft_m} m "
          f"(L/B {MISSION.l_over_b:.2f}, B/T {MISSION.b_over_t:.2f})")
    print(f"  {fn_to_knots(MISSION.fn.low, MISSION.hull_lwl_m):.2f} - "
          f"{fn_to_knots(MISSION.fn.high, MISSION.hull_lwl_m):.2f} kn")
    print(f"  NOTE: {_SPEED_LABEL_CONFLICT}")
    print()
    print(f"{len(FAMILIES)} families, {len(FEATURES)} features")
    for c in Candidacy:
        n = len(families(candidacy=c))
        nf = len([x for x in FEATURES if x.candidacy is c])
        print(f"  {c.value:<10} {n:>3} families  {nf:>3} features")
    print()
    for f in FAMILIES:
        print(_fmt(f))
    print()
    print("THE MISSION AGAINST THE ONE DIMENSIONED TABLE (000, catamaran row)")
    b_oa = 4.0   # hull-example-008.png, "BEAM OVERALL (B_oa): 4.0m"
    verdict = drawn_dimension_verdict("catamaran", MISSION.hull_lwl_m, b_oa,
                                      MISSION.hull_draft_m)
    for key, ok in verdict.items():
        band = DRAWN_DIMENSION_RANGES["catamaran"].get(key)
        state = "not stated" if ok is None else ("inside" if ok else "OUTSIDE")
        print(f"  {key:<8} {state:<10} against {band}")
    print("  (beam is B_oa from 008, not the demihull beam — the table's "
          "column is the overall one)")
    print()
    print("BAND PROVENANCE (FAMILIES only; see basis_census.__doc__)")
    census = basis_census()
    total = sum(census.values())
    for b, n in census.items():
        print(f"  {b.value:<9} {n:>4}  ({100.0 * n / total:5.1f}%)")
    print(f"  total     {total:>4}")
    # `literature` reads 0 here and that is CORRECT, not a bug: the sourcing
    # pass of 2026-08-13 landed as module-level CITATION BLOCKS (`_SOTON_*`,
    # `_S64_*`, `_BLOUNT_*`, `_TRANSOM_*`, `_LE_OVER_L`), not as family
    # proportions, because no family band was strong enough to be overwritten
    # by a single secondary reading. Said out loud so a zero is not read as
    # "no literature was consulted".
    lit = [n for n, o in sorted(globals().items())
           if isinstance(o, Band) and o.basis is Basis.LITERATURE]
    print(f"  ({len(lit)} LITERATURE bands sit at module scope, outside this "
          f"census: {', '.join(lit)})")
    print("  see docs/research/HULL-FORM-RULES.md §7.10 for what was opened "
          "and what refused")
    print()
    print("WHAT THE GRAMMAR CANNOT SAY (union over the library)")
    for item in sorted({m for ms in unexpressible().values() for m in ms}):
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
