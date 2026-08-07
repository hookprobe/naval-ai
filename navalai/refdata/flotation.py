"""Tier F reference data — buoyancy, foam and the swamped criteria.

Transcribed from `BuildPlan2-FullVessel.md` §1.3 and §1.4.

THE ONE THING TO UNDERSTAND BEFORE USING ANY NUMBER HERE: 33 CFR 183 subparts
F/G/H DOES NOT GOVERN OUR BOATS. It applies to monohulls under 20 ft and
excludes sailboats, canoes and inflatables. Our products are 4-14 m. What the
plan adopts is its CALCULATION METHOD, which is public, verified in detail,
and the industry-standard engineering core — and then declares the result an
assessment aid, exactly as `navalai/rules/` does. `SCOPE_IS_NOT_OURS` below
exists so nobody reads a passing Tier F as a regulatory pass.

THE MATH IS SHORT AND THE PROVENANCE IS THE HARD PART.

    F = Fb + Fp + Fc

with each material contributing by its submerged factor K = (SG - 1) / SG.
That formula is exact arithmetic, so `submerged_factor()` computes it rather
than storing more numbers; only the K values the plan states are stored, and
`tests/test_refdata.py` checks the two of them whose SG is also stated close
against the formula. Aluminium and steel are stored as K ALONE because the
plan gives no SG for them, and back-solving 1/(1-K) would manufacture a
specific gravity (8.33 for steel, against a real ~7.85) that reads as data.

WHY PLYWOOD MATTERS TO THIS PROJECT SPECIFICALLY. Fir plywood's K is NEGATIVE
(-0.81): it floats, so it carries itself and some of the outfit. GRP's is
+0.33, so a GRP hull needs foam merely to lift its own shell. The developable
plywood grammar this platform is built on is therefore already halfway to an
unsinkable SKU, which is §1.4's finding and the reason Tier F is cheap for us
and expensive for a GRP builder.

FOAM IS THE PLACE WHERE VENDOR DATA AND FIELD DATA DISAGREE, and the plan
records both. 2 lb PU is only 95-98% closed-cell; new absorption is ~0.1
lb/ft3 but moored boats waterlog over years and foam absorbs spilled gasoline.
So the buoyancy figure is stored as sourced AND a derate policy is stored
beside it, and neither is allowed to quietly become the other.
"""

from __future__ import annotations

from . import Absent, RefValue

# ---------------------------------------------------------------- provenance

_USCG = ("USCG Flotation Handbook / 33 CFR 183.105-183.230, method verified in "
         "detail; via BuildPlan2-FullVessel.md §1.3")
_USCG_114 = ("33 CFR 183.114 (durability), via BuildPlan2-FullVessel.md §1.3")
_FIELD = ("Vendor + practitioner evidence, both verified in the research "
          "sweep; BuildPlan2-FullVessel.md §1.3 'foam honesty'")
_ETAP = ("Etap 21i flooded trial, verified; BuildPlan2-FullVessel.md §1.3 — "
         "adopted as the SKU acceptance criterion in §3 (Gate V2.6)")
_POLICY = ("BuildPlan2-FullVessel.md §1.3/§4 design policy — OURS, adopted in "
           "response to the field evidence; no standard sets it")

# ---------------------------------------------------------------- the scope

SCOPE_IS_NOT_OURS = RefValue(
    6.096, "m", _USCG, "approx",
    "20 ft. 33 CFR 183 subparts F/G/H apply to monohulls BELOW this length "
    "and exclude sailboats, canoes and inflatables. Our SKUs are 4-14 m, so "
    "the regulation does not govern them; we adopt its method only, and the "
    "output is an assessment aid.")

# ------------------------------------------------- material submerged factors


def submerged_factor(sg: float) -> float:
    """K = (SG - 1) / SG — the fraction of its own weight a submerged material
    must be supported by, negative when the material floats.

    Computed, never tabulated, because a table of a two-term formula is a
    second declaration of the same number (CLAUDE.md's recurring defect).
    """
    if sg <= 0:
        raise ValueError(f"specific gravity must be positive, got {sg}")
    return (sg - 1.0) / sg


# Specific gravities the plan states outright. Only these two.
MATERIAL_SG = {
    "grp_laminate": RefValue(1.50, "-", _USCG, "approx"),
    "fir_plywood": RefValue(0.55, "-", _USCG, "approx"),
}

# K as PRINTED in the plan, to the precision it prints. Kept alongside
# submerged_factor() deliberately: these are the transcribed values, and the
# gate test compares them against the formula rather than replacing them, so a
# transcription error is caught instead of being computed away.
MATERIAL_K = {
    "grp_laminate": RefValue(
        +0.33, "-", _USCG, "approx",
        "Positive: GRP needs foam to carry its own laminate."),
    "fir_plywood": RefValue(
        -0.81, "-", _USCG, "approx",
        "NEGATIVE — inherently buoyant. A plywood boat needs flotation only "
        "for ballast, engine, batteries and outfit."),
    "aluminium": RefValue(
        +0.63, "-", _USCG, "approx",
        "K only. The plan states no SG for aluminium, and 1/(1-K) = 2.70 "
        "would be a back-solved number wearing the same clothes as a "
        "transcribed one."),
    "steel": RefValue(
        +0.88, "-", _USCG, "approx",
        "K only, and note it does NOT round-trip to structural steel's real "
        "SG: 1/(1-0.88) = 8.33 against ~7.85. Stored as printed; do not "
        "derive an SG from it."),
}

POLYSTYRENE_BANNED = RefValue(
    True, "", _USCG_114, "approx",
    "Dissolves in gasoline and is highly flammable, so it cannot meet the "
    "30-day immersion durability rule. Banned from the flotation palette — a "
    "material rule, not a preference.")

# ---------------------------------------------------------------------- foam

FOAM_DENSITY_LB_FT3 = RefValue(
    2.0, "lb/ft^3", _USCG, "approx",
    "The industry reference pour density (~32 kg/m^3).")
FOAM_NET_BUOYANCY_LB_FT3 = RefValue(
    60.3, "lb/ft^3", _USCG, "approx",
    "NET of the foam's own weight and a 5% moisture allowance — i.e. this is "
    "what a cubic foot of 2 lb PU actually lifts, not 62.4 minus nothing.")
FOAM_NET_BUOYANCY_KG_M3 = RefValue(
    966.0, "kg/m^3", _USCG, "approx",
    "The plan's own SI restatement of 60.3 lb/ft^3.")
FOAM_MOISTURE_ALLOWANCE = RefValue(
    0.05, "-", _USCG, "approx",
    "Already included in FOAM_NET_BUOYANCY_*. Do not apply it twice.")
FOAM_CLOSED_CELL_FRACTION = RefValue(
    (0.95, 0.98), "-", _FIELD, "approx",
    "2 lb PU is 95-98% closed-cell, not 100%. This is the mechanism behind "
    "long-term waterlogging.")
FOAM_NEW_ABSORPTION_LB_FT3 = RefValue(
    0.1, "lb/ft^3", _FIELD, "approx",
    "As-new absorption. Moored boats measured far worse over years, which is "
    "why FOAM_AGING_DERATE exists as a separate, policy-basis number.")
FOAM_SPEC_MAX_ABSORPTION_24H = RefValue(
    0.02, "-", _ETAP, "approx",
    "<= 2% per 24 h, the verified Etap closed-cell specification. This is a "
    "PROCUREMENT bar for the unsinkable SKU, not a design allowance.")
FOAM_AGING_DERATE = RefValue(
    -0.15, "-", _POLICY, "approx",
    "Long-term buoyancy is derated 15%. OURS: the plan adopts it in response "
    "to the moored-boat evidence, no standard sets it, and it must never be "
    "presented as a sourced figure.")
FOAM_IS_NEVER_THE_ONLY_DEFENCE = RefValue(
    True, "", _POLICY, "approx",
    "Design law from §1.3: sealed inspectable compartments plus foam "
    "REDUNDANCY. Foam alone is not an acceptable single defence.")

# ---------------------------------------------------- swamped pass criteria

SWAMPED_HEEL_MAX_DEG = RefValue(
    10.0, "deg", _USCG, "approx", "Level-flotation criterion, swamped.")
SWAMPED_OFFCENTRE_LOAD_HEEL_MAX_DEG = RefValue(
    30.0, "deg", _USCG, "approx",
    "With the off-centre load applied. A different, looser bar than "
    "SWAMPED_HEEL_MAX_DEG — they are not interchangeable.")

# ------------------------------------------------- 3-D placement constraints

# Flotation is an ARRANGEMENT problem, which is why Tier F sits in BuildPlan 2
# next to the arrangement grammar rather than beside the hydrostatics.
PROPULSION_FLOTATION_WITHIN_OF_TRANSOM_IN = RefValue(
    36, "in", _USCG, "approx",
    "= 0.914 m. Flotation for the propulsion mass must sit within this of the "
    "transom.")
PASSENGER_FLOTATION_WITHIN_OF_SIDES_IN = RefValue(
    6, "in", _USCG, "approx",
    "= 0.152 m. Passenger flotation goes outboard and high, not in the bilge "
    "where it is easy to fit.")

# ------------------------------------------------------------- durability

DURABILITY_IMMERSION_DAYS = RefValue(
    30, "day", _USCG_114, "approx",
    "Immersion in fuel, oil and TSP solution.")
DURABILITY_MAX_BUOYANCY_LOSS = RefValue(
    0.05, "-", _USCG_114, "approx",
    "<= 5% buoyancy loss after DURABILITY_IMMERSION_DAYS.")

# --------------------------------------------- the SKU acceptance criterion

ETAP_MAX_FREEBOARD_LOSS_FRAC_LOA = RefValue(
    0.03, "-", _ETAP, "approx",
    "Fully flooded, freeboard loss below 3% of LOA, and the vessel remains "
    "manoeuvrable. Adopted as the 'unsinkable' acceptance test precisely "
    "because it is measurable — 'always floats' on its own is marketing.")
ETAP_21I_FLOODED_VOLUME_L = RefValue(
    2000, "L", _ETAP, "approx",
    "Approximate flooded volume carried by the double-hull foam on a "
    "21-footer, still sailable about 1 kn slower. The demonstration behind "
    "the criterion above.")

# ------------------------------------------------------------ what is absent

NOT_SOURCED = (
    Absent("reference_area_freeboard_rules",
           "33 CFR 183's level-flotation pass criteria include freeboard rules "
           "stated against a reference area. The plan names them without "
           "reproducing the geometry or the limits, and they cannot be "
           "guessed from the heel angles.",
           "read 33 CFR 183.105-183.230 in full"),
    Absent("uscg_worked_examples",
           "Gate V2.4's bar is 'reproduces the USCG handbook worked examples "
           "exactly, including the plywood -0.81 negative-contribution case'. "
           "No worked example is transcribed anywhere in this repository, so "
           "that gate has no validation set yet — the same defect gap E1 "
           "found when Gate 1's bar named Holtrop-Mennen and nothing "
           "implemented it.",
           "transcribe the handbook examples, as benchmarks/holtrop_cases.py "
           "did for Holtrop"),
    Absent("iso9094_fire_thresholds",
           "ISO 9094 (fire protection) was not captured free at all. No fire "
           "number is transcribed here; fire posture ships with none.",
           "purchase ISO 9094"),
    Absent("fire_retardant_coating_ratings",
           "§1.4 records that fire-retardant epoxy and intumescent coatings "
           "exist for wood, and explicitly sends the specifics to the "
           "purchase/verify list.",
           "vendor data sheets + ISO 9094"),
    Absent("material_sg_aluminium_steel",
           "The plan gives K for aluminium and steel but no SG. See "
           "MATERIAL_K's notes for why one is not back-solved from the other.",
           "a material database with cited densities"),
)
