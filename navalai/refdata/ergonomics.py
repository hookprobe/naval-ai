"""Tier E reference data — accommodation, circulation and deck safety.

Transcribed from `BuildPlan2-FullVessel.md` §1.1 and §1.2, which record a
50-source research sweep with 76 adversarial verification votes (71 upheld,
5 refuted). Nothing here is remembered: every constant names the document the
plan attributes it to, and anything the plan marks paywalled is in
`NOT_SOURCED` rather than filled in at a plausible value.

TWO KINDS OF NUMBER LIVE HERE, AND THEY MUST NOT BE CONFLATED.

  ISO 15085:2003 deck numbers are basis='standard-2003'. The plan states they
  were verified from the standard text itself.

  Accommodation numbers are marine PRACTICE (Perry and marine accommodation
  guidance). No standard governs a berth length. They are verified at claim
  level and ship as basis='approx' — which here means "sourced, but not a
  legal bar", not "guessed".

THE SEA CHANGES THE RULES. §1.1's most useful finding is that land ergonomics
references are not sufficient: stoves need 40 deg of gimbal, sea berths must
be narrow enough to wedge into, footwells taper so feet brace the leeward seat
when heeled, and handholds are a first-class layout element. Those are encoded
below as marine modifiers, not as footnotes, because a layout that satisfies
Panero and fails these is a layout that only works alongside.
"""

from __future__ import annotations

from . import Absent, RefValue

# ---------------------------------------------------------------- provenance

_MARINE = ("Robert Perry + marine accommodation guidance, via "
           "BuildPlan2-FullVessel.md §1.1 (research sweep, verified at claim "
           "level; no standard governs these)")
_ISO15085_2003 = ("ISO 15085:2003, numeric clauses verified from the standard "
                  "text; BuildPlan2-FullVessel.md §1.2")
_ISO15085_2024 = ("ISO/FDIS 15085:2024 preview (iTeh), via "
                  "BuildPlan2-FullVessel.md §1.2 — the full text and the "
                  "per-zone equipment lists are paywalled")
_ABYC_H41 = ("ABYC H-41 (2014), verified at claim level via "
             "BuildPlan2-FullVessel.md §1.2 — exact inch dimensions are "
             "behind membership")

# ------------------------------------------------------------------- berths

BERTH_LENGTH_STANDARD_MM = RefValue(
    2060, "mm", _MARINE, "approx",
    "6 ft 9 in. The standard, not the minimum — see BERTH_LENGTH_MIN_MM.")
BERTH_LENGTH_MIN_MM = RefValue(
    1980, "mm", _MARINE, "approx", "6 ft 6 in absolute floor.")
DOUBLE_BERTH_WIDTH_MIN_MM = RefValue(
    1525, "mm", _MARINE, "approx",
    "Measured AT THE HEAD; a double may still taper toward the foot.")
BERTH_WIDTH_HEAD_MM = RefValue(560, "mm", _MARINE, "approx")
BERTH_WIDTH_FOOT_MM = RefValue(
    380, "mm", _MARINE, "approx",
    "The taper is the point: a parallel-sided berth of this width is not the "
    "same object.")

# Marine modifier. A sea berth is deliberately NARROW so the occupant wedges
# in, which inverts the land intuition that wider is better.
SEA_BERTH_NEEDS_LEE_CLOTH = RefValue(
    True, "", _MARINE, "approx",
    "Lee cloth or lee board required for a berth used at sea; often "
    "convertible single-sea / double-at-anchor.")

# ------------------------------------------------------------------ seating

SETTEE_HEIGHT_MM = RefValue(455, "mm", _MARINE, "approx")
SETTEE_DEPTH_MM = RefValue(455, "mm", _MARINE, "approx", "Sitting upright.")
SETTEE_DEPTH_LOUNGING_MM = RefValue(610, "mm", _MARINE, "approx")
SETTEE_BACKREST_MIN_MM = RefValue(380, "mm", _MARINE, "approx")
SETTEE_WIDTH_PER_PERSON_MM = RefValue(610, "mm", _MARINE, "approx")

# ---------------------------------------------------------------- headroom

HEADROOM_PREFERRED_MM = RefValue(2060, "mm", _MARINE, "approx")
HEADROOM_COMPROMISE_MIN_MM = RefValue(
    1905, "mm", _MARINE, "approx",
    "6 ft 3 in. A compromise floor, explicitly not a target.")

# -------------------------------------------------------------------- head

HEAD_BOWL_TO_DOOR_MIN_MM = RefValue(560, "mm", _MARINE, "approx")
SHOWER_MIN_SQUARE_MM = RefValue(
    610, "mm", _MARINE, "approx", "610 x 610 clear.")

# ------------------------------------------------------------------ galley

GALLEY_HOB_HEIGHT_MM = RefValue(
    900, "mm", _MARINE, "approx",
    "Approximate working height; the plan states it as ~900 mm.")
GALLEY_CLEARANCE_ABOVE_HOB_MIN_MM = RefValue(750, "mm", _MARINE, "approx")
GALLEY_KICK_SPACE_MM = RefValue(75, "mm", _MARINE, "approx")
STOVE_GIMBAL_RANGE_DEG = RefValue(
    40, "deg", _MARINE, "approx",
    "Marine modifier with no land equivalent: total gimbal range a seagoing "
    "stove must have.")

# -------------------------------------------------------- hatches, cockpit

HATCH_CLEAR_MIN_MM = RefValue(460, "mm", _MARINE, "approx")
HATCH_CLEAR_PREFERRED_MM = RefValue(610, "mm", _MARINE, "approx")
COCKPIT_FOOTWELL_TAPER_MM = RefValue(
    (610, 460), "mm", _MARINE, "approx",
    "(top, bottom) width. The taper lets feet brace against the leeward seat "
    "when heeled — a parallel footwell of either width does not.")
HANDHOLDS_ARE_LAYOUT_ELEMENTS = RefValue(
    True, "", _MARINE, "approx",
    "Handholds are placed as a first-class layout element, not fitted after "
    "the joinery. Spacing is not given numerically by any source we hold.")

# ------------------------------------------------- ISO 15085:2003 deck rules

# Minimum side-deck width by design category. The plan records D/C/A+B.
SIDE_DECK_WIDTH_MIN_MM = {
    "D": RefValue(100, "mm", _ISO15085_2003, "standard-2003"),
    "C": RefValue(120, "mm", _ISO15085_2003, "standard-2003"),
    "B": RefValue(150, "mm", _ISO15085_2003, "standard-2003",
                  "A and B share the 150 mm floor."),
    "A": RefValue(150, "mm", _ISO15085_2003, "standard-2003",
                  "A and B share the 150 mm floor."),
}

BARRIER_LOW_MIN_MM = RefValue(450, "mm", _ISO15085_2003, "standard-2003")
BARRIER_HIGH_MIN_MM = RefValue(600, "mm", _ISO15085_2003, "standard-2003")
WORKING_DECK_STEP_MAX_MM = RefValue(
    500, "mm", _ISO15085_2003, "standard-2003",
    "Working-deck continuity: steps and obstacles above this break it.")
STANCHION_TEST_LOAD_N = RefValue(
    280, "N", _ISO15085_2003, "standard-2003", "Applied horizontally.")
STANCHION_MAX_DEFLECTION_MM = RefValue(
    50, "mm", _ISO15085_2003, "standard-2003",
    "Under STANCHION_TEST_LOAD_N.")
WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG = RefValue(
    25, "deg", _ISO15085_2003, "standard-2003",
    "Surfaces steeper than this are excluded from the working-deck "
    "definition — i.e. they do not COUNT, which is a scope rule, not a bar.")
WORKING_DECK_SLOPE_MAX_TRANSVERSE_DEG = RefValue(
    30, "deg", _ISO15085_2003, "standard-2003", "See the longitudinal note.")
REBOARDING_MEANS_MANDATORY = RefValue(
    True, "", _ISO15085_2003, "standard-2003",
    "Required on every boat. ABYC H-41 agrees and adds 'unassisted'.")

# ------------------------------------------- ISO 15085:2024 zone STRUCTURE

# The 2024 edition supersedes 2003 with risk-based deck zones. The zone SYSTEM
# is verified; the per-zone equipment lists are not, so this table carries the
# access condition and nothing else. Numeric deck floors continue to come from
# the 2003 constants above until the 2024 text is purchased.
DECK_ZONE_ACCESS = {
    "Z1": RefValue(
        None, "kn", _ISO15085_2024, "approx",
        "Access at any time — no speed condition. Structure verified; the "
        "equipment list for this zone is paywalled."),
    "Z2": RefValue(
        4, "kn", _ISO15085_2024, "approx",
        "Access at or below 4 kn."),
    "Z3": RefValue(
        None, "kn", _ISO15085_2024, "approx",
        "Access nearly stationary. The plan gives no numeric speed for "
        "'nearly stationary', so none is invented here."),
}
MAX_PERSONS_MUST_FIT_IN_Z1_PLUS_INTERIOR = RefValue(
    True, "", _ISO15085_2024, "approx",
    "2024 requirement: the craft must seat/accommodate its maximum persons "
    "within Z1 plus the interior.")
SEAT_MIN_MM = RefValue(
    (400, 750), "mm", _ISO15085_2024, "approx",
    "(width, depth) including foot space. From the 2024 preview, so basis is "
    "'approx' and NOT 'standard-2003' — the 2003 text does not contain it.")

# ----------------------------------------------------------- ABYC H-41

REBOARDING_MUST_BE_UNASSISTED = RefValue(
    True, "", _ABYC_H41, "approx",
    "On all boats. Claim-level verified; the dimensional requirements are "
    "behind membership.")
LADDER_AND_GATE_DESIGN_LOAD_N = RefValue(
    1780, "N", _ABYC_H41, "approx",
    "400 lb, for boarding ladders and cockpit gates. The load is verified; "
    "the geometry it is applied to is not (see NOT_SOURCED).")

# ------------------------------------------------------------ what is absent

NOT_SOURCED = (
    Absent("anthropometric_percentile_tables",
           "Panero & Zelnik (1979) is named as the canonical decomposition and "
           "its 5th-95th percentile organisation is verified, but the tables "
           "themselves are not reproduced in any source we hold. No body "
           "dimension is transcribed here.",
           "purchase Panero & Zelnik"),
    Absent("percentile_stretch_factor",
           "The plan's response to 1970s body-size data is a configurable "
           "stretch factor. It states the MECHANISM, not a value, and a "
           "plausible invented multiplier would resize every envelope in "
           "Tier E while looking transcribed.",
           "measurement against a modern anthropometric dataset"),
    Absent("handhold_spacing_mm",
           "Named as a first-class layout element by both the marine-practice "
           "sweep and ABYC H-41; neither yields a spacing we can cite.",
           "purchase ABYC H-41"),
    Absent("abyc_h41_dimensions",
           "Ladder step spacing, immersion depth and handhold clearance are "
           "given in inches behind ABYC membership. Only the 1780 N load and "
           "the unassisted-reboarding requirement are verified.",
           "purchase ABYC H-41"),
    Absent("iso15085_2024_zone_equipment",
           "The Z1/Z2/Z3 structure is verified and encoded; WHICH equipment "
           "each zone requires, and the 2024 numeric clauses that replace the "
           "2003 floors, are paywalled.",
           "purchase ISO 15085:2024"),
    Absent("iso12217_3_thresholds",
           "Governs craft under 6 m and assigns category C or D (the plan "
           "records this as a CORRECTION to an earlier 'D ceiling' claim). "
           "The numeric content is paid text.",
           "purchase ISO 12217-3:2022"),
)
