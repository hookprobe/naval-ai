"""Hull grammar: parameter vector + closed-form feasibility constraints (L0 gate).

Pattern from Ship-D (Bagazinski & Ahmed 2023): validity is decided by cheap
algebraic constraints on the parameter vector (their 49 checks run in ~0.2 ms,
~10,000x faster than mesh checks), which is what makes slider-rate gating
possible. This grammar targets small craft: **LWL 2.5-24 m, the scope of
Directive 2013/53/EU** (it said "4-20 m" until 2026-08-14, which was a box
nobody had sourced and which refused this project's own 12.0 x 0.8 m demihull
on beam alone — see the incident block below `PARAMS`).

THE GENOME IS DESIGN TARGETS PLUS SHAPE, NOT SHAPE ALONE (plate P1,
2026-08-13). `Cp` and `lcb` are the prismatic coefficient and the longitudinal
centre of buoyancy the designer ASKS FOR, and `geometry.sac_exponents` solves
the sectional area curve that delivers them; `p_bow` and `p_stern`, the old
chine plan-form exponents, are gone because a plan-form is a consequence of
the area curve and the section law, not an input. `roundness` is the bilge
shape function's blend from hard chine (0) to a full radiused fillet (1).

MEASURED at commit c7b7c4b on 200 draws of `evaluate.sample_valid`, integrating
Cp and LCB off the DELIVERED geometry: Cp spanned 0.386..0.832 with 18.0% in
the 0.55-0.62 band, and LCB spanned -10.02..+13.88 %LWL with 46.5% inside
+-3 %LWL. Both were emergent outputs of fifteen unrelated shape knobs.

Coordinate system: x=0 at transom, x=LWL at stem; z=0 at design waterline,
z negative down; y is half-breadth (starboard).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import formlib
from .limits import (CP_GENE_BOUNDS, LCB_BAND_PCT_LWL,
                     RCD_HULL_LENGTH_SCOPE_M, HullRole, hull_role)

# ==========================================================================
# THE PROPORTION BANDS, WHICH ARE CONDITIONAL ON WHAT THE HULL IS PART OF
#
# INCIDENT, 2026-08-14. This project's own target — a catamaran with 12.0 m x
# 0.8 m demihulls — was refused by `check()` on three clauses before a line of
# physics ran:
#
#     bound[BWL]: 0.8 outside [1.2, 6.0]
#     L/B: 15.00 outside [2.2, 8.5]
#     B/T: 1.33 outside [1.8, 12.0]
#
# The narrowest 12 m hull this grammar could express was 1.42 m. The owner
# asked for 0.8 m.
#
# THE DIAGNOSIS IS NOT "THE BANDS ARE WRONG". They are correct MONOHULL bands.
# A 12 m monohull 0.8 m wide would capsize and the band is right to refuse it.
# They were applied to the wrong OBJECT, and the fix is therefore NOT to widen
# them: `L_OVER_B_BAND` and `B_OVER_T_BAND` below are BYTE-FOR-BYTE what they
# were, they remain what a monohull is judged against, and
# `tests/test_vessel_bands.py` proves a 12.0 x 0.8 m MONOHULL is still refused
# on the same clause with the same numbers.
#
# WHAT CHANGED IS THAT A SECOND ROW EXISTS, and it is SOURCED. A demihull's
# band is the UNION of the monohull band and the published catamaran-demihull
# series envelope. The union is stated as a rule rather than as four literals:
#
#   L/B  [2.2, 8.5] u [7.00, 15.10] = [2.2, 15.10]
#   B/T  [1.8, 12.0] u [1.50,  2.50] = [1.50, 12.0]
#
# and the sourced half comes from `formlib.SOTON_DEMIHULL_*` — the Southampton
# catamaran series (Molland, Wellicome & Couser, Ship Science Report 71, 1994)
# demihull envelope, quoted SECONDARY from Petersson (2020) Table 3 because the
# report itself refused every fetch. THE IMPORT IS THE POINT: writing 15.10
# here as a literal beside a comment naming Southampton is this repository's
# signature defect with the second copy laundered into a citation.
#
# WHY A UNION, AND NOT THE SERIES ENVELOPE ALONE. Southampton's L/B floor is
# 7.00 and its B/T ceiling is 2.50. Adopting those as the demihull band would
# REFUSE a power-catamaran demihull at L/B 5 — a boat that exists, that
# `formlib.power_cat_demihull` describes, and that is no more extreme than a
# monohull this grammar already admits. The asymmetry is deliberate and it runs
# one way only: a demihull may be anything an admissible MONOHULL may be, plus
# whatever the catamaran series adds beyond that. Both unions come out
# CONTIGUOUS (the intervals overlap at 7.00-8.50 and 1.80-2.50), so neither
# band has a hole in it that a min/max would paper over; the test asserts it.
#
# WHAT WAS **NOT** WIDENED, AND WHY IT MATTERS MORE THAN WHAT WAS.
#
#   B/T. The target's 0.8/0.6 = 1.33 is BELOW the Southampton floor of 1.50, so
#   IT IS STILL REFUSED — on draft, not on slenderness. There is no published
#   demihull at that draft to band against, and inventing 1.3 to make the
#   owner's number fit would be exactly the move honesty rule 6 forbids. The
#   refusal SAYS SO: it names the series, the edge, and the fact that what is
#   missing is EVIDENCE rather than a feature. A 12.0 x 0.8 m demihull at
#   T <= 0.533 m (B/T >= 1.50) is accepted today.
#
#   The demihull L/B ceiling is 15.10 and NOT DTMB Series 64's 18.26.
#   `formlib.S64_MONOHULL_L_OVER_B` reaches 18.26 and is why the drawings'
#   L/B 15-18 demihulls are credible practice rather than an illustrator's
#   exaggeration — but Series 64 is a MONOHULL series, and taking a monohull
#   ceiling for a demihull is the same category error as the monohull ceiling
#   that started this, pointed the other way. It corroborates; it does not band.
#
# THERE IS NO TRIMARAN ROW. `mission.EVALUABLE_TOPOLOGIES` is (monohull, catamaran) and
# refuses three, and `limits.HullRole` has two members for the same reason: a
# role with no sourced band would fall through to the monohull one, which is an
# unmeasured quantity scored as a passing one.

# THE MONOHULL BANDS — UNCHANGED, AND THEY KEEP THEIR ORIGINAL NAMES.
#
# They used to be four literals inside `check()`, which is how gap B9 became
# possible: L0 bounded BWL/T at 12 on the PARAMETER vector and nothing ever
# re-checked the proportions of the hull that was actually delivered. MEASURED
# on 200 L0-feasible hulls floated to their mission displacement: 28.0% sit
# outside the B/T band and 4.5% outside the L/B band ON THE FLOATED STATE, and
# one delivered hull reached B/T 14.4 against the project's own <= 12 bar. The
# parameter T is the DESIGN draft at midship; the floated draft is whatever the
# weight model produces, so the two are simply different numbers and the gate
# was checking the one nobody sails.
#
# `proportion_margins` is the shared kernel: `check()` applies it to the
# parameters and `evaluate()` applies it to `HydroState`, so the band cannot
# drift between the two. The names are kept because `evaluate.py`,
# `experiments.py`, `resistance.py`, `formlib.py` and four test modules read
# them, and because THE MONOHULL BAND IS STILL THE DEFAULT: an ungoverned call
# to `check(x)` is judged by exactly the numbers it was judged by before.
L_OVER_B_BAND = (2.2, 8.5)
B_OVER_T_BAND = (1.8, 12.0)

# THE DEMIHULL BANDS, as the union rule above. Written as `min`/`max` over the
# two contributing intervals rather than as literals, so that moving either
# contributor moves this band and cannot leave a stale copy behind.
_SOTON_LB = formlib.SOTON_DEMIHULL_L_OVER_B
_SOTON_BT = formlib.SOTON_DEMIHULL_B_OVER_T
L_OVER_B_BAND_DEMIHULL = (min(L_OVER_B_BAND[0], _SOTON_LB.low),
                          max(L_OVER_B_BAND[1], _SOTON_LB.high))
B_OVER_T_BAND_DEMIHULL = (min(B_OVER_T_BAND[0], _SOTON_BT.low),
                          max(B_OVER_T_BAND[1], _SOTON_BT.high))

# THE PROVENANCE OF EACH EDGE, carried beside the band and printed in the
# refusal. A band whose refusal cannot say where its number came from is a bar
# a designer cannot argue with, and this project has already shipped one.
_MONOHULL_SRC = ("this project's own L0 band for a single hull; practice, no "
                 "anchor in this tree")
_DEMIHULL_SRC = (f"union of the monohull band and {_SOTON_LB.source}")

# role -> {metric: (band, source)}. ONE table, read by `proportion_margins`,
# by `check()` and by `evaluate()` through the first of those.
PROPORTION_BANDS: dict[HullRole, dict[str, tuple[tuple[float, float], str]]] = {
    HullRole.MONOHULL: {
        "L/B": (L_OVER_B_BAND, _MONOHULL_SRC),
        "B/T": (B_OVER_T_BAND, _MONOHULL_SRC),
    },
    HullRole.DEMIHULL: {
        "L/B": (L_OVER_B_BAND_DEMIHULL, _DEMIHULL_SRC),
        "B/T": (B_OVER_T_BAND_DEMIHULL, _DEMIHULL_SRC),
    },
}

# WHERE A REFUSAL STOPS BEING "TOO SLENDER" AND BECOMES "NOBODY HAS MEASURED
# ONE". Below the Southampton B/T floor there is no published demihull to band
# against, so the honest refusal names the missing evidence instead of implying
# a number exists. This is the sentence the owner's 12.0 x 0.8 x 0.6 m demihull
# gets, and it is the whole point of the change: the target is refused ON DRAFT,
# with the reason, rather than refused on slenderness for no reason.
OUT_OF_SOURCED_RANGE = (
    "OUT OF SOURCED RANGE, not out of physics: no published catamaran-demihull "
    "series in this tree reaches it. The floor is the Southampton series' own "
    "minimum and what is missing is EVIDENCE, not a feature — see "
    "formlib.SOTON_DEMIHULL_B_OVER_T and docs/research/HULL-FORM-RULES.md §7.4")

# The two freeboard floors `check()` enforces on the parameter vector. Hoisted
# out of the constraint expressions on 2026-08-14 because each was written
# TWICE — once in the condition and once in the message beside it — which is
# the exact pattern that put a 15 mm ply outside its own scantling rule, and
# because the D floor below is derived from the first of them.
MIN_FREEBOARD_ABS_M = 0.30
MIN_FREEBOARD_FRAC_LWL = 0.045

# THE DERIVED BOX FLOORS. Computed from the bands above so that no bound
# without naval-architecture content can refuse a hull a sourced band accepts —
# the rule stated in the PARAMS comment, executed rather than asserted.
_LWL_BOX = RCD_HULL_LENGTH_SCOPE_M   # RCD Art. 3(2); limits.py owns it
_BWL_CEILING = formlib.DRAWN_DIMENSION_RANGES["large monohull"]["beam_m"].high
_T_CEILING = formlib.DRAWN_DIMENSION_RANGES["large monohull"]["draft_m"].high
_L_OVER_B_CEILING_ANY = max(b["L/B"][0][1] for b in PROPORTION_BANDS.values())
_B_OVER_T_CEILING_ANY = max(b["B/T"][0][1] for b in PROPORTION_BANDS.values())
_BWL_FLOOR = _LWL_BOX[0] / _L_OVER_B_CEILING_ANY
_T_FLOOR = _BWL_FLOOR / _B_OVER_T_CEILING_ANY
_D_FLOOR = _T_FLOOR + MIN_FREEBOARD_ABS_M

# (name, unit, low, high, description)
PARAMS = [
    # ------------------------------------------------------------------
    # THE ABSOLUTE SIZE BOX. Every edge below is either SOURCED or DERIVED
    # from a band, and it says which. It used to be LWL [4, 20], BWL
    # [1.2, 6.0], T [0.2, 1.5] — monohull-recreational scaling with no stated
    # provenance, and the BWL floor of 1.2 m is what refused the owner's 0.8 m
    # demihull before any ratio rule got to speak.
    #
    # THE RULE THIS BOX IS NOW SET BY: **a bound with no naval-architecture
    # content must not refuse a hull that a SOURCED band accepts.** A box
    # cannot express a ratio, so the two ends are set differently and both are
    # written down:
    #
    #   the FLOORS are DERIVED from the bands, so the box cannot bind first;
    #   the CEILINGS are SOURCED, and where a ceiling can still bind before a
    #   band does, that is recorded here rather than discovered later.
    #
    # MEASURED consequence on the rejection sampler, because widening a box is
    # not free: uniform-in-box yield through `check()` falls 13.2% -> 6.7%
    # (4000 draws, seed 1). `sample()` allows 200 tries per sample and needs
    # ~15, so it still converges; it costs about 2x the draws.
    #
    # LWL: Directive 2013/53/EU (RCD) Art. 3(2), OJ L 354/95 — "recreational
    # craft ... of hull length from 2,5 m to 24 m". BOTH edges are that scope.
    # Outside it the entire rules tier (ISO 12217-1, ISO 12215-5, the design
    # categories) does not govern the boat, so a hull there would be scored by
    # a compliance tier that has nothing to say about it — the `gate2m.py`
    # printing KCS's EFD over a Wigley hull defect, in the rules tier. LOA ==
    # LWL by construction in this grammar (see `formlib`'s `_M_STEM`), so
    # bounding LWL bounds hull length. NOTE WHAT IS **NOT** TAKEN:
    # `formlib.DRAWN_DIMENSION_RANGES` draws hulls to 30 m; 30 m is outside RCD
    # scope and is refused rather than adopted.
    ("LWL",        "m",   _LWL_BOX[0], _LWL_BOX[1], "waterline length"),
    # BWL floor: DERIVED as LWL_low / (the largest L/B ceiling over all roles),
    # i.e. the beam at which the box stops binding before the L/B band does.
    # It is NOT a claim that a 0.166 m hull is a boat — what refuses that hull
    # is `freeboard.rel`, `section.solve` and the ladder's own validity
    # envelope, all of which have content, rather than a bound that has none.
    # BWL ceiling: `formlib.DRAWN_DIMENSION_RANGES` largest PER-HULL beam
    # (6.0 m, "large monohull"); the catamaran and trimaran rows are OVERALL
    # beam and are not per-hull numbers. RECORDED CONSEQUENCE: 6.0 m can bind
    # before the L/B floor of 2.2 above LWL 13.2 m, so a 24 m x 9 m barge is
    # not expressible. Nothing in this tree sources one and the product line
    # does not want one; the defect was at the NARROW end.
    # THE DESCRIPTION SAID "at the max-area station" AND THE CODE DOES NOT.
    # Corrected 2026-08-23 from Gate 0E5, which found it by encoding real
    # published hulls: MEASURED over eight sampled genomes, the generated
    # hull's MAXIMUM waterline half-breadth equals the commanded BWL/2
    # (2.5555 vs 2.5555, 2.1446 vs 2.1446, 1.8256 vs 1.8256, ...), while the
    # half-breadth at `x_mb` falls short by up to 0.2% and the station of
    # maximum beam sits as far aft as 0.65 L. Reading a real hull's beam
    # into this gene under the OLD description cost 2.5% of beam.
    ("BWL",        "m",   _BWL_FLOOR, _BWL_CEILING,
     "MAXIMUM beam on the design waterline"),
    # T floor: DERIVED as BWL_low / (the largest B/T ceiling over all roles),
    # on the same rule and with the same disclaimer. T ceiling: the largest
    # draft `formlib.DRAWN_DIMENSION_RANGES` draws (2.0 m, "large monohull") —
    # the old 1.5 m ceiling was a real restriction at the top of the length
    # range, where a 24 m displacement hull drafts more than that.
    ("T",          "m",   _T_FLOOR, _T_CEILING,
     "design draft (keel at midship)"),
    # D floor: DERIVED as T_low + MIN_FREEBOARD_ABS_M — the shallowest depth at
    # which ANY hull can clear `freeboard.abs`, so a shallower bound would
    # enclose only hulls this gate already refuses. D ceiling UNCHANGED at 3.0.
    # "midship" HERE MEANS `x_mb`, NOT MID-LENGTH, and the two differ on
    # every hull whose max-area station is not at 0.5 L (the gene spans
    # [0.40, 0.68]). `station_geometry` holds the sheer flat at freeboard
    # `fb = D - T` aft of `x_mb` and raises it forward, and the keel is
    # deepest at `x_mb`, so D is realised there EXACTLY. Measuring it at
    # mid-length instead cost a systematic +0.5% to +1.3% across the Gate
    # 0E5 corpus, same sign on every hull.
    ("D",          "m",   _D_FLOOR, 3.0,
     "depth, keel to sheer AT THE MAX-AREA STATION x_mb"),
    # Cp and lcb are DESIGN TARGETS, and both are bounded from `limits.py`
    # rather than by a literal here: `CP_GENE_BOUNDS` is the span of the
    # Froude-number prismatic table (`limits.prismatic_target`), so the gene
    # can always be set to the target the mission implies, and the LCB gene
    # spans exactly the band the ladder already enforces on the FLOATED hull.
    # A bound written twice is the same defect as a threshold written twice.
    ("Cp",         "-", CP_GENE_BOUNDS[0], CP_GENE_BOUNDS[1],
     "TARGET prismatic coefficient (see limits.prismatic_target)"),
    ("lcb",        "%", -LCB_BAND_PCT_LWL, LCB_BAND_PCT_LWL,
     "TARGET LCB, % LWL forward of midships"),
    ("x_mb",       "-",   0.40, 0.68, "max-AREA station / LWL"),
    # CEILING 0.50 -> 0.92 and 25 -> 38 deg on 2026-08-26 (audit findings
    # G and E). 0.50 meant the transom could never carry more than half the
    # midship section: MEASURED, 0 of 1592 generated hulls reached a 3.0 m
    # transom on a 4 m beam, and the published planing series carry
    # A_T/A_X 0.8-1.0 (morphology_families.HARD_CHINE_PLANING). 25 deg
    # excluded the published deep-V canon (Keuning 1993 at 30 deg, Naples
    # NSS to 37.4). The LEGACY SAMPLING BOX below pins the seeded streams
    # to the old values, so this widening moves no recorded population —
    # the widened envelope is reached by the optimizer, explicit design
    # and the exploration streams only.
    ("r_transom",  "-",   0.05, 0.92, "transom sectional area / max sectional "
                                      "area"),
    ("beta_mid",   "deg", 0.0, 38.0, "deadrise at midship"),
    ("beta_bow",   "deg", 2.0, 50.0, "deadrise at forward stations"),
    ("beta_len",   "-",   0.15, 0.6, "fraction of LWL over which deadrise warps"),
    ("roundness",  "-",   0.0,  1.0, "bilge roundness: 0 hard chine, 1 full "
                                     "fillet"),
    ("rocker",     "-",   0.0,  0.6, "keel rise at transom / T"),
    # FLOOR STAYS AT 0.0. Widening an existing gene's bound is NOT a no-op:
    # `rng.uniform(lo, hi)` maps the SAME random number to a different value,
    # so every seeded population silently changes. MEASURED 2026-08-24 — a
    # floor of -0.45 was tried first and it moved exactly one gene of the
    # seed-0 draw (forefoot 0.18271 -> -0.18507) while the other fifteen were
    # bit-identical, which was enough to break every pinned fixture. The
    # capability it was reaching for is now `stem_depth`, appended below.
    ("forefoot",   "-",   0.0,  1.0, "keel RISE at stem / T"),
    ("flare",      "deg", -5.0, 25.0, "topside flare angle"),
    ("sheer_rise", "-",   0.0,  0.5, "bow sheer rise / D"),
    # THE RUN, added 2026-08-24. See `geometry._deadrise`: transom deadrise was
    # always exactly `beta_mid` because only a BOW warp existed, so the run
    # never flattened -- measured 25.0 deg at the transom on a hull meant to
    # carry a single inboard propeller. Published practice (Naples Systematic
    # Series, Table 1) prescribes deadrise at three stations, DECREASING aft:
    # 13.2 / 22.3 / 38.5 deg. `beta_run` = 0 is the old behaviour, bit-identical.
    ("beta_transom", "deg", 0.0, 45.0, "deadrise AT the transom; the run "
                                       "flattens from beta_mid down to this"),
    ("beta_run",     "-",   0.0,  0.5, "fraction of LWL over which deadrise "
                                       "warps aft to beta_transom; 0 = none"),
    # FLARE ALONG THE LENGTH, added 2026-08-24. See `geometry._stations`: the
    # single `flare` scalar is what `formlib` records as the blocker making
    # axe_bow and wave_piercing_monohull Expressible.NO. `flare_len` = 0 is the
    # old behaviour, bit-identical.
    ("flare_bow",  "deg", -15.0, 25.0, "flare angle at the STEM; below zero is "
                                       "tumblehome, which is what a "
                                       "wave-piercing bow uses to trade "
                                       "reserve buoyancy for downforce"),
    ("flare_len",  "-",     0.0,  0.6, "fraction of LWL over which flare warps "
                                       "forward to flare_bow; 0 = none"),
    # THE AXE BOW'S CORE MECHANISM, as a gene that DEEPENS rather than a
    # widened one that rises. Damen: "The bow has the greatest draught at the
    # front, which delays the moment at which the bow lifts out of the water.
    # If the bow does not lift, there is no chance of it slamming back into
    # the waves." `forefoot` raises the keel toward the stem; `stem_depth`
    # lowers it. They are opposite intents and a single signed gene conflated
    # them -- which is also why widening `forefoot` broke every seeded
    # population. 0.0 is a no-op and is bit-identical to the hull before this
    # gene existed.
    ("stem_depth", "-",     0.0, 0.45, "keel DEEPENING at the stem / T; the "
                                       "axe-bow mechanism. 0 = none"),
    # THE BOW HAD NO FULLNESS GENE AT ALL, and that is the SPEARHEAD.
    # MEASURED 2026-08-24 on the delivered `houseboat16.stl`: the SAC's forward
    # branch was `a = 1 - _shape(t, pf)`, which is EXACTLY 0.0 at x = LWL, so
    # every hull this grammar can express narrows to a mathematical POINT at
    # the stem. The aft branch has carried `r_transom` -- `a = R + (1-R)*...`,
    # a floor on sectional area -- since the kernel was written; the forward
    # branch simply never got its mirror. The consequence is not cosmetic: at
    # BWL 4.0 m on a 16 m houseboat the waterline beam was under 0.15 m for the
    # forward 1.8 m, which is why the owner's reading of the render ("it looks
    # like a spearhead ... the space at the stern cannot be used, i have asked
    # for a 4m width boat") was CORRECT and the geometry was wrong, not the
    # brief. A barge, a workboat, a houseboat and a wave-piercing axe bow all
    # carry finite area at the stem; only a racing shell does not.
    # 0.0 reproduces the hardcoded zero EXACTLY -- `S + (1-S)*v == v` when
    # S == 0 in IEEE-754 for every finite v -- so this is a lawful post-hoc
    # append under the `POST_HOC_DEFAULTS` rule and every seeded population is
    # bit-identical. Verified by `test_r_stem_zero_is_bit_identical`.
    # CEILING 0.95, NOT r_transom's 0.50. Widening an EXISTING gene's bound is
    # what broke every seeded population when `forefoot` was tried (see above),
    # but a POST-HOC gene is different in kind and provably so: `sample()`
    # draws uniforms for CORE genes only, and a gene in POST_HOC_DEFAULTS is
    # not in `core`, so no random number is ever consumed for it and its LOW /
    # HIGH cannot move the bit-stream. The ceiling is therefore free to be set
    # by the physics rather than by compatibility -- and a barge, a landing
    # craft or a canal boat carries very nearly full section to the stem.
    ("r_stem",     "-",     0.0,  0.95, "stem sectional area / max sectional "
                                        "area; the mirror of r_transom. "
                                        "0 = a pointed bow"),
    # PARALLEL MIDBODY -- THE FEATURE THIS GRAMMAR COULD NOT EXPRESS AT ALL.
    # `sac_ordinate` builds one falling branch forward of `x_mb` and one aft of
    # it, so a(x) touches 1.0 at EXACTLY ONE STATION. A hull with parallel
    # midbody has a SAC that is FLAT at 1.0 over a span, and no value of any
    # gene could produce that -- so every hull this kernel drew was a lens,
    # tapering from a single maximum in both directions, BY CONSTRUCTION.
    #
    # MEASURED 2026-08-24. Best-of-30000 search on the 16 x 4 m brief, filtered
    # to hulls passing check(), critique() and all seven design rules:
    # `pmb_frac` 0.098 and `beam_carried` 0.293 -- against a plausible-corpus
    # band of 0.415-0.829 for beam_carried, and against the 2026-08-23
    # houseboat that was REJECTED at beam_carried 0.293. The same number: the
    # search could not do better because the kernel has no lever for it.
    #
    # This is the defect behind the owner's reading of every render so far.
    # `downloads/hull-examples/hull-example-004.png` -- a solar-electric
    # displacement cruiser at the same 7-12 kn the brief asks for -- labels it
    # outright: "PARALLEL MIDBODY: MAXIMIZES PRISMATIC", beside "ROUND-BILGE
    # SECTION" and "FINE ENTRANCE ANGLE (< 12 deg)". We could draw neither the
    # flat SAC top nor, consequently, the fine entrance that a short entrance
    # run buys.
    #
    # 0.0 collapses the flat span to zero width and reproduces the previous
    # single-point maximum EXACTLY, so this is a lawful post-hoc append.
    # Verified bit-for-bit by `test_pmb_zero_is_bit_identical`.
    ("pmb",        "-",     0.0,  0.55, "PARALLEL MIDBODY: fraction of LWL "
                                        "over which sectional area is held at "
                                        "maximum. 0 = a single-station peak"),
    # THE DESIGN WATERLINE B(x) — Phase 3's kernel repair, the one the audit's
    # research row names outright: "the lines plan is three coupled curves —
    # SAC, design waterline, section character" (Larsson & Eliasson;
    # Harries/Abt), and this grammar had the SAC only. The waterline was a
    # CONSEQUENCE: `_stations` solved the chine from the AREA target and the
    # flare put the waterline wherever it landed — the measured root of the
    # flare/env coupling (full decoupling collapsed plan convexity 0.5 ->
    # 0.32 because the KEEL quadratic leaked into the plan), of the
    # `_CONVEXITY_FAIR_FRAC` fairing tolerance, and of the formcheck
    # collision (a mission-correct slender Cp cannot carry a critic-clean
    # waterline when both live in one curve — measured 2026-08-27, margins
    # +0.024..+0.201 on all six canonical cases).
    #
    # With `dwl` > 0 the kernel is given BOTH targets — A(x) from the SAC and
    # w(x) from this curve — and solves the section for (chine, flare)
    # JOINTLY. The solve stays closed form: the f^2 coefficient of the joint
    # equation is m*d^2*(c1 - c2 - 1), and the fillet identity c1 - c2 = 1
    # makes it VANISH, so the derived flare is the root of a LINEAR equation.
    # The B(x) curve itself reuses the SAC's exponent family (one ordinate
    # law, two curves), with its own end fullness ratios below and its
    # waterplane fullness tied to Cp by a DELTA.
    #
    # `dwl` = 0 disables everything: the pass-1 solve is the only solve and is
    # bit-identical to every hull drawn before this existed (verified by
    # test_dwl_zero_is_bit_identical). All four are lawful post-hoc appends.
    ("dwl",        "-",     0.0,  1.0,  "design-waterline authority: 0 = the "
                                        "waterline is the section solve's "
                                        "consequence (legacy), 1 = B(x) is "
                                        "prescribed and flare is derived"),
    ("cwp_x",      "-",    -0.20, 0.25, "waterplane fullness DELTA: the B(x) "
                                        "curve's prismatic is Cp + cwp_x, "
                                        "clipped into its own deliverable "
                                        "band. 0 = waterline fullness follows "
                                        "the SAC's"),
    ("rb_transom", "-",     0.0,  0.98, "waterline half-beam ratio at the "
                                        "transom (beam analogue of "
                                        "r_transom's area ratio)"),
    ("rb_stem",    "-",     0.0,  0.98, "waterline half-beam ratio at the "
                                        "stem; 0 = the waterline closes to a "
                                        "point"),
    # THE TUNNEL STERN (Phase 4, 2026-08-27) — the owner-approved
    # houseboat17 W-section, expressed as the NOTCH it is: the centreline
    # keel rises to a tunnel CROWN over the after `tun_len` of the hull,
    # walls sloping down-out to the floor at `tun_w` of the local chine
    # half-breadth. The notch is space the boat displaces but cannot use
    # (the owner's own sentence), so the section solve delivers the SAC
    # NET of it — displacement stays the contract — and the crown must
    # stay submerged at the floated state (the waterplane never gains a
    # hole; a pierce is REFUSED, not mis-integrated). All three are
    # lawful post-hoc appends: at 0 the notch has no width, no height and
    # no length, and every function reduces to the pre-tunnel expression
    # bit for bit.
    ("tun_w",      "-",     0.0,  0.60, "tunnel half-width at the floor / "
                                        "local chine half-breadth. 0 = no "
                                        "tunnel"),
    ("tun_crown",  "-",     0.0,  0.70, "tunnel crown height above the keel "
                                        "/ local draft, at the transom. 0 = "
                                        "no tunnel"),
    ("tun_len",    "-",     0.0,  0.50, "fraction of LWL the tunnel runs "
                                        "forward from the transom. 0 = no "
                                        "tunnel"),
    # THE SPLIT STERN (Phase 4B, 2026-08-27) — the hookprobe generalisation:
    # aft of `split_len` the CENTRELINE OPENS. An inner wall stands at
    # `split_w` of the local chine half-breadth, keel to deck, and the
    # region inboard of it is water with sky over it (the wet deck is the
    # DECK; its air gap is the freeboard's business). Unlike the tunnel
    # (displaced-but-unusable, crown submerged), the split REMOVES
    # displacement and SPLITS THE WATERPLANE — the hydrostatics integrate
    # the hole (awp ~ b - y_split, ixx ~ b^3 - y_split^3) rather than
    # refusing it, because here the hole is the design. Both are lawful
    # post-hoc appends: at 0 there is no wall and no hole, bit for bit.
    ("split_w",    "-",     0.0,  0.80, "inner-wall position / local chine "
                                        "half-breadth, at the transom. 0 = "
                                        "no split"),
    ("split_len",  "-",     0.0,  0.80, "fraction of LWL the split runs "
                                        "forward from the transom. 0 = no "
                                        "split"),
    # rho(x) — THE BILGE RADIUS VARIES ALONG THE LENGTH (Phase 3's named
    # remainder; audit table row "Section = knuckle list, rho(x),
    # multi-chine | 5 fixed control points, ONE GLOBAL rho"). Real hulls
    # do not carry one bilge shape stem to stern: the corpus holds
    # `round_bilge` and `hard_chine` as SEPARATE families precisely
    # because a hull that softens forward (a hard-chine planing bottom
    # aft running into a rounded entry) was not expressible — it had to
    # pick one. The warp law is the flare warp's, exactly, so there is
    # one shape of "a thing that changes toward the bow" in this kernel:
    #
    #     rho(x) = roundness                                  x <= (1-L_r)L
    #     rho(x) = roundness + (rho_bow - roundness) frac^2    forward
    #
    # `rho_len` = 0 disables the warp and every hull drawn before this
    # existed is bit-identical. Both are lawful post-hoc appends.
    ("rho_bow",    "-",     0.0,  1.0,  "bilge roundness AT THE STEM; "
                                        "reached over the forward rho_len "
                                        "of the hull"),
    ("rho_len",    "-",     0.0,  0.60, "fraction of LWL over which the "
                                        "bilge warps toward rho_bow. 0 = "
                                        "one roundness, stem to stern"),
    # PHASE 5 -- THE SECOND CHINE, i.e. the two body plans this grammar
    # could not draw at all. `docs/audit/geometry-representation.md` reads
    # "multi-chine NO" and `docs/BUILD-PLAN.md` PV-4 names the consequence:
    # the kernel reaches TWO of the five standard body plans, and the two
    # it misses are the double-chine forms. Multi-chine is the PLYWOOD
    # answer to a round bilge, which is why this is also the honest
    # replacement for the `roundness = 0` pin that sheet-built typologies
    # currently carry -- that pin is a stopgap correct for the unroller we
    # have, not a principle (BUILD-PLAN PV-4).
    #
    # The section is one chine: keel -> C (turn of bilge, filleted by rho)
    # -> [W at the design waterline, when dwl > 0] -> sheer. A double-chine
    # hull puts a SECOND breakpoint on the topside, and the machinery for a
    # topside breakpoint already exists -- it is what the dwl knuckle is.
    # So the second chine is the SAME construction with its height freed
    # from z = 0, and the topside becomes a knuckle LIST rather than a
    # special case (the shape `docs/audit/HULL-DESIGN-AUDIT.md` asked for:
    # "Section = knuckle list, rho(x), multi-chine").
    #
    #   ch2_z : height of the second chine, as a fraction of the run from
    #           the first chine C to the sheer S. Inert while ch2_y = 0.
    #   ch2_y : how far the chine stands OUTBOARD of the straight C -> S
    #           line, as a fraction of the local half-beam. **0.0 is the
    #           proven no-op**: the vertex then lies exactly on the line it
    #           interrupts, so it is not a chine at all, and the whole
    #           branch is gated on `ch2_y > 0` so that no legacy hull takes
    #           a different code path (not merely the same numbers -- the
    #           same CODE, which is the standard `dwl`, the tunnel and the
    #           split were each held to).
    ("ch2_z",      "-",     0.0,  1.0,  "second chine height, as a "
                                        "fraction of chine -> sheer. Inert "
                                        "while ch2_y is 0"),
    ("ch2_y",      "-",     0.0,  0.25, "second chine offset outboard of "
                                        "the chine -> sheer line, as a "
                                        "fraction of local half-beam. "
                                        "0 = no second chine"),
]

N_PARAMS = len(PARAMS)
NAMES = [p[0] for p in PARAMS]
LOW = np.array([p[2] for p in PARAMS])
HIGH = np.array([p[3] for p in PARAMS])

# =========================================================================
# THE FROZEN LEGACY SAMPLING BOX — 2026-08-26, and why it exists.
#
# When the LEGAL envelope above widened (Cp gene decoupled from the Froude
# target table, audit finding C.2), the first attempt scaled every seeded
# uniform stream to the new bounds and 98 tests went red at once: sealed
# population manifests, the mesh-robustness calibration bank, the golden
# resistance file, the GP baseline marks and the blender identity fence all
# name hulls by "seed + index", and every one of those names silently moved
# — the exact defect the population module was built to catch, fired 98
# times. A bound change should never be able to rewrite history.
#
# So the DRAW box is pinned to the values the historical streams were drawn
# under, as literals, permanently: `sample()` and `evaluate.sample_valid`
# scale their uniforms by THESE bounds, and a future widening of the legal
# envelope cannot move a single seeded hull. The widened envelope is
# reached by the paths that have no history to preserve — the optimizer
# (LOW/HIGH), explicit design, the parent library, and the post-hoc
# exploration stream — never by silently re-scaling old streams.
#
# THESE LITERALS DO NOT TRACK PARAMS. That is their entire point. If a gene
# is APPENDED the arrays extend with its bounds at append time (post-hoc
# genes are pinned by POST_HOC_DEFAULTS anyway); an EXISTING gene's row
# here never changes again.
DRAW_LOW = LOW.copy()
DRAW_HIGH = HIGH.copy()
_LEGACY_DRAW_ROWS = {
    # gene: (low, high) as drawn by every seeded stream before 2026-08-26
    "Cp": (0.525, 0.710),        # the old PRISMATIC_BY_FROUDE span
    "r_transom": (0.05, 0.50),
    "beta_mid": (0.0, 25.0),
    # THE dwl QUARTET IS PINNED AT ITS DEFAULTS IN THE DRAW BOX (Phase 3,
    # 2026-08-27) — unlike r_stem/pmb, whose DRAW rows stayed open for the
    # P1 exploring stream. MEASURED the day dwl landed: an UN-CHOSEN
    # random (dwl, cwp_x, rb_transom, rb_stem) tuple is a waterline target
    # nobody designed — direct DRAW-box draws (the morphology tests, the
    # directed-search seeds) degraded from median 4 to median 1 search
    # wins, and full-box buildability read 34/500 against 41/500 with dwl
    # forced off. The lever is for CALLERS WHO CHOOSE A CURVE (parents,
    # missions, the repair table once its targets are derived); it enters
    # the exploring stream when a calibrated span is measured, exactly as
    # the P1 event did for the fullness genes.
    "dwl": (0.0, 0.0),
    "cwp_x": (0.0, 0.0),
    "rb_transom": (0.0, 0.0),
    "rb_stem": (0.0, 0.0),
    # the tunnel trio is pinned for the same reason as the dwl quartet: a
    # random un-designed notch is not a hull anyone asked for
    "tun_w": (0.0, 0.0),
    "tun_crown": (0.0, 0.0),
    "tun_len": (0.0, 0.0),
    # and the split pair, for the same reason
    "split_w": (0.0, 0.0),
    "split_len": (0.0, 0.0),
    # the rho warp is pinned for the same reason as its four predecessors:
    # a random un-designed bilge warp is not a hull anyone asked for
    "rho_bow": (0.0, 0.0),
    "rho_len": (0.0, 0.0),
    # and the second chine, for the same reason as all five before it: a
    # random un-designed breakpoint on the topside is not a hull anyone
    # asked for, and the seeded streams must not move
    "ch2_z": (0.0, 0.0),
    "ch2_y": (0.0, 0.0),
}
for _nm, (_lo, _hi) in _LEGACY_DRAW_ROWS.items():
    _i = NAMES.index(_nm)
    DRAW_LOW[_i], DRAW_HIGH[_i] = _lo, _hi

# Cold-bend twist a sheet panel will take without a jig or heat, in degrees of
# deadrise change per metre of run. Declared once, here, and read by `check()`
# and by nothing else — the number that was inlined as a bare `14.0` in the
# constraint expression AND in the message beside it, which is the two-copies
# pattern that put a 15 mm ply outside its own scantling rule. It is a
# WORKSHOP limit, not a class-society one, so it is not `limits.py`'s to own;
# if a rule ever derives it, it moves there and this becomes an import.
MAX_PANEL_TWIST_DEG_PER_M = 14.0


def proportion_ratios(lwl: float, b_wl: float, t: float) -> dict[str, float]:
    """The two proportions themselves, guarded against a zero denominator.

    Split out so `proportion_margins` and `check()` compute L/B and B/T from
    one expression: they printed the ratio in the refusal message and computed
    the margin from a second copy of the same division, and a message that
    disagrees with the number it explains is how a designer is sent chasing the
    wrong parameter.
    """
    return {"L/B": lwl / max(b_wl, 1e-9), "B/T": b_wl / max(t, 1e-9)}


def bands_for(vessel=None) -> dict[str, tuple[tuple[float, float], str]]:
    """The proportion bands and their provenance for a hull in `vessel`.

    `vessel` is anything `limits.hull_role` accepts: a `HullRole`, a
    `mission.VesselConfig` (or anything carrying `n_hulls`), or None. None is a
    MONOHULL and gives the bands this module has always enforced.
    """
    return PROPORTION_BANDS[hull_role(vessel)]


def proportion_margins(lwl: float, b_wl: float, t: float,
                       vessel=None) -> dict[str, float]:
    """Relative band margins for L/B and B/T: > 0 means OUTSIDE the band.

    Normalised by the band edge rather than left absolute, so the number is
    scale-free and continuous — NSGA-II needs a gradient out of an infeasible
    region, and "L/B is 1.2 too big" means something different on a 4 m tender
    than on a 20 m barge.

    `vessel` DEFAULTS TO A MONOHULL, so every existing caller — `check()` with
    no vessel, and `evaluate()`'s re-application to the FLOATED state (gap B9) —
    gets the identical numbers it got before this argument existed. The band a
    demihull is judged against is wider on both metrics, so defaulting the
    other way would have silently loosened the bar for every monohull in the
    tree, which is the failure this change exists to avoid the mirror image of.
    """
    bands = bands_for(vessel)
    ratios = proportion_ratios(lwl, b_wl, t)
    out: dict[str, float] = {}
    for key, val in ratios.items():
        lo, hi = bands[key][0]
        out[key] = max((lo - val) / lo, (val - hi) / hi)
    return out


@dataclass(frozen=True)
class GateReport:
    ok: bool
    violations: tuple[str, ...]


def _rel(name: str, cond: bool, msg: str, out: list[str]) -> None:
    if not cond:
        out.append(f"{name}: {msg}")


def _proportion_message(key: str, val: float, vessel=None) -> str:
    """The refusal sentence for one proportion, naming the ROLE and the SOURCE.

    The old sentence — the ratio, the word "outside", and the monohull band —
    told this project's owner that his own boat was illegal without telling him
    it was being judged as a MONOHULL, which is the whole content of the
    2026-08-14 finding. The incident block at the top of this module quotes it
    verbatim. The clause NAME is unchanged
    ("L/B", "B/T") because consumers key on it; only the sentence grew.
    """
    role = hull_role(vessel)
    (lo, hi), src = PROPORTION_BANDS[role][key]
    msg = f"{key} {val:.2f} outside {[lo, hi]} for a {role.value} ({src})"
    # BELOW the floor of a band whose floor came from a published series is a
    # DIFFERENT refusal from above its ceiling, and saying so is the honesty
    # half of this change: the hull is not impossible, it is UNEVIDENCED.
    if key == "B/T" and role is HullRole.DEMIHULL and val < lo:
        return f"{msg}. {OUT_OF_SOURCED_RANGE}"
    return msg


def check(x: np.ndarray, vessel=None) -> GateReport:
    """L0 algebraic gate: closed-form, plus the geometric metrics.

    Returns every violated constraint (not just the first) so the UI can
    grey sliders with a reason, mirroring the manifest-style gating rule.

    `vessel` SAYS WHAT THIS HULL IS PART OF, and it is the argument this gate
    was missing on 2026-08-14. A `mission.VesselConfig`, a `limits.HullRole`,
    or None. **None is a MONOHULL and reproduces this gate exactly as it stood**
    — same bands, same numbers, same messages — so an ungoverned call cannot be
    loosened by the existence of the demihull row. Only the proportion bands
    are conditional; every other clause here is a property of one moulded
    surface and does not care how many of them the vessel has.

    THE GEOMETRY IS BUILT ONCE and four checks read it: `sac.target`,
    `section.solve`, `chine.submerged`, `transom.chine` and `panel.twist`. It
    is called here rather than re-derived in closed form, because a closed
    form here would be the same number declared twice and the two copies would
    drift — which is what produced gap E6 in the first place.

    FAILS CLOSED. A parameter vector whose bounds are already violated can
    make `Hull` divide by zero (e.g. x_mb = 1.0). Those bounds are reported
    separately; here an unbuildable geometry counts as a violated design
    target rather than as a pass, because `${VAR:-0}` — an unmeasurable
    quantity scored as perfect — is the failure mode this repository keeps
    paying for.
    """
    x = np.asarray(x, dtype=float)
    v: list[str] = []
    if x.shape != (N_PARAMS,):
        return GateReport(False, (f"shape: expected {N_PARAMS} params",))
    if not np.all(np.isfinite(x)):
        return GateReport(False, ("finite: NaN/inf in parameter vector",))

    # bound constraints
    for i, (name, _u, lo, hi, _d) in enumerate(PARAMS):
        _rel(f"bound[{name}]", lo <= x[i] <= hi, f"{x[i]:.4g} outside [{lo}, {hi}]", v)

    p = named(x)
    lwl, bwl, t, d = p["LWL"], p["BWL"], p["T"], p["D"]

    # draft below depth with real freeboard
    fb = d - t
    _rel("freeboard.abs", fb >= MIN_FREEBOARD_ABS_M,
         f"freeboard {fb:.2f} m < {MIN_FREEBOARD_ABS_M:.2f} m", v)
    _rel("freeboard.rel", fb >= MIN_FREEBOARD_FRAC_LWL * lwl,
         f"freeboard {fb:.2f} m < {MIN_FREEBOARD_FRAC_LWL * 100:.1f}% LWL", v)
    # SLENDERNESS / STABILITY PROPORTIONS — THE ROLE-CONDITIONAL PAIR.
    # Same kernel evaluate() re-applies to the FLOATED hull (gap B9): one band,
    # two states. The refusal now names the ROLE and the SOURCE, because
    # "L/B 15.00 outside [2.2, 8.5]" told the owner his own boat was illegal
    # without telling him it was being judged as a monohull.
    #
    # THE TWO ROWS ARE WRITTEN OUT, NOT LOOPED, AND THAT IS DELIBERATE.
    # `tests/test_constraints_honest.py` censuses the live relational
    # constraints by scanning this function for each relation's literal NAME
    # in its reporting call — the fence
    # that deleted four dead checks in gap E4 and refuses a constraint that
    # cannot fire. A loop over ("L/B", "B/T") makes both rows invisible to it,
    # which trades a real gate for two lines of tidiness.
    marg = proportion_margins(lwl, bwl, t, vessel)
    ratios = proportion_ratios(lwl, bwl, t)
    _rel("L/B", marg["L/B"] <= 0.0,
         _proportion_message("L/B", ratios["L/B"], vessel), v)
    _rel("B/T", marg["B/T"] <= 0.0,
         _proportion_message("B/T", ratios["B/T"], vessel), v)
    # deadrise ordering (bow at least as steep as midship)
    _rel("deadrise.order", p["beta_bow"] >= p["beta_mid"],
         f"beta_bow {p['beta_bow']:.1f} < beta_mid {p['beta_mid']:.1f}", v)
    #
    # FOUR CHECKS WERE DELETED HERE, AND DELETING THEM CHANGES NO VERDICT.
    # Gap E4: `keel.rocker`, `keel.forefoot`, `x_mb.margin` and `flare.fold`
    # cannot fire anywhere inside the declared parameter bounds, so they padded
    # the constraint count and nothing else. Ship-D's "49 closed-form
    # constraints" is a count this grammar was written to echo; echoing it with
    # tautologies makes the count true and the claim false.
    #
    # Each is dead for a reason that is arithmetic, not empirical:
    #   keel.rocker    `rocker * T <= 0.75 * T` with rocker bounded at 0.6.
    #   keel.forefoot  `forefoot <= 1.0` IS the forefoot upper bound, restated.
    #   x_mb.margin    0.05..0.95 against an x_mb bound of [0.40, 0.68].
    #   flare.fold     needs BWL < 0.70 m (flare >= -5 deg, freeboard <= 2.8 m)
    #                  against a BWL minimum of 1.20 m.
    #
    # THREE CHECKS ARE NEW WITH PLATE P1/P2, and two of them are refusals of a
    # DESIGN TARGET rather than of a shape:
    #
    #   sac.target       (Cp, lcb) outside what a(x) can reach with both shape
    #                    exponents in [1, 8]. Refused, never approximated: a
    #                    generator that silently returns the nearest reachable
    #                    Cp is exactly the generator plate P1 replaced.
    #   section.solve    the sectional area curve asks a station for more area
    #                    than its draft and deadrise can enclose
    #                    (A <= d^2 / tan(beta) at roundness 0, i.e. the chine
    #                    reaching the waterline), or the flare consumes the
    #                    whole half-beam at the max-area station.
    #   chine.submerged  REPLACES the old `chine.height`, which allowed the
    #                    midship chine 0.25 T ABOVE the waterline. With the
    #                    design waterline a first-class curve the chine has to
    #                    sit at or below it, or the section's waterline point
    #                    is not on the topside run and the closed-form area
    #                    the whole kernel is solved against does not hold. The
    #                    bar moved because the quantity changed meaning; it
    #                    moved TIGHTER, and it is measured on the delivered
    #                    geometry rather than on a midship closed form.
    #
    # C43 developability: MAX bottom-panel twist per metre (plywood twist limit)
    #
    # GAP E6 — THE PROXY MEASURED THE WRONG QUANTITY. This check used to read
    #
    #     twist_rate = (beta_bow - beta_mid) / (beta_len * LWL)
    #
    # which is the MEAN twist over the warp length. The warp is quadratic, so
    # d(beta)/dx rises linearly from 0 at the aft end of the warp to 2x the
    # mean at the stem — and a mean averages a local fold away. A hull with one
    # unbuildable panel and nine flat ones passed. MEASURED over 400,000
    # uniform in-bounds vectors on the pre-P1 genome: the max/mean ratio had
    # median 1.774 (p95 1.869), the old mean check passed 93.180% of them and
    # the honest max metric passes 81.198%, so 12.243% of the box was blessed
    # on a number the sheet does not feel — and the worst true twist hiding
    # under a passing mean was 50.2 deg/m against this 14 deg/m limit.
    from . import geometry  # local: geometry imports this module at load time

    try:
        with np.errstate(divide="ignore", invalid="ignore"):
            # THE PROBE COMES FIRST, AND IT IS DENSER THAN THE HULL. `Hull`
            # solves the section at ITS OWN 41 stations, so a vector could pass
            # here and blow up inside `resistance.total_resistance`, which
            # rebuilds the same params at 161 stations for the Michell grid.
            # See `geometry.FEASIBILITY_PROBE_STATIONS` for the incident and
            # the density measurement.
            geometry.section_probe(x)
            hull = geometry.Hull(x)
            twist_rate = hull.panel_twist_rate()
        if not math.isfinite(twist_rate):
            raise ValueError(f"twist is {twist_rate}")
    except geometry.GeometryError as exc:
        name = "sac.target" if str(exc).startswith("sac:") else "section.solve"
        v.append(f"{name}: {exc}")
    except (ValueError, ZeroDivisionError, FloatingPointError) as exc:
        v.append(f"panel.twist: bottom twist not evaluable ({exc})")
    else:
        _rel("panel.twist", twist_rate <= MAX_PANEL_TWIST_DEG_PER_M,
             f"max bottom twist {twist_rate:.1f} deg/m > "
             f"{MAX_PANEL_TWIST_DEG_PER_M:.0f}", v)
        z_ch = float(hull.z_chine.max())
        _rel("chine.submerged", z_ch <= 0.0,
             f"chine {z_ch:.3f} m above the design waterline", v)
        _rel("chine.below.sheer", z_ch <= fb - 0.05, "chine reaches sheer", v)
        # `transom.chine` WAS HERE AND IS DELETED, on gap E4's rule and with
        # gap E4's evidence. It read `z_chine[0] <= 0.35 * T` — the transom
        # chine may not fly more than a third of a draft above the waterline —
        # and `chine.submerged` above now requires the chine to be at or below
        # the waterline at EVERY station, which subsumes it. MEASURED over
        # 40,000 uniform in-bounds vectors, 23,596 of which build: it fires on
        # ZERO of them. A constraint that cannot fire pads the count and
        # nothing else, and `tests/test_constraints_honest.py` refuses one.

    return GateReport(len(v) == 0, tuple(v))


def sample(n: int, rng: np.random.Generator | None = None,
           max_tries: int = 200, vessel=None,
           explore_post_hoc: bool = False,
           features=frozenset()) -> np.ndarray:
    """Rejection-sample n feasible parameter vectors (uniform in bounds).

    `vessel` is passed straight through to `check`, so sampling for a catamaran
    draws demihulls and sampling for nothing draws monohulls. MEASURED
    2026-08-14 over 4000 uniform draws (seed 1): 6.7% pass as a monohull and
    9.6% as a demihull, against 13.2% in the old, narrower box — the widened
    box costs about 2x the draws and `max_tries` of 200 leaves ~15x of headroom.

    `explore_post_hoc` (2026-08-27, the P1 coverage event of the hull-design
    audit): False is the LEGACY stream, bit-identical forever — post-hoc
    genes at their no-op defaults, core uniforms in their original order.
    True is THE EXPLORING STREAM: after the core draw, the post-hoc genes
    are drawn from a SECOND Generator spawned deterministically from the
    caller's rng, and (Cp, lcb) are projected into the bands the drawn
    fullness genes can deliver (`geometry.cp_band`/`lcb_band`) — a blind
    joint draw is ~99% self-contradictory and rejection would eat the
    whole tries budget. The two streams never share a random number, so
    turning exploration on cannot move a single legacy hull. Every model
    trained before this flag existed had only ever seen hulls whose bow is
    a point and whose SAC touches its maximum at one station; this flag is
    how a training feed stops teaching that.
    """
    # THE DRAW IS ARITY-STABLE, AND THAT IS NOT A DETAIL.
    #
    # `rng.uniform(LOW, HIGH)` consumes exactly N_PARAMS values per candidate,
    # so APPENDING A GENE SHIFTS THE ENTIRE STREAM: every population, fixture
    # and calibration anchor drawn from a seed silently becomes a different set
    # of boats. MEASURED 2026-08-24, going from 16 genes to 20: 48 tests across
    # 17 files went red, the first no-rescue admissibility refusal moved from
    # hull 152 to 110, and NO hull in the first 400 dev draws tripped the
    # sheer-ridge bar at all. Not one of those was a geometry regression; the
    # lottery had simply been re-run.
    #
    # So each candidate draws a FIXED-WIDTH block and the first N_PARAMS are
    # used. Genes 0..15 land on the same RNG positions they always did, and the
    # genes appended since are held at their POST_HOC_DEFAULTS -- which are
    # proven no-ops -- so a seeded draw reproduces the SAME HULLS it did at
    # arity 16, bit for bit.
    #
    # WHAT THIS COSTS, said plainly: `sample` does NOT explore the post-hoc
    # genes. It is the legacy population generator, and its job is
    # reproducibility. The optimizers explore the full box
    # (`optimize.pareto_front`, `morphology_search.search`), and anything that
    # needs the new genes must go through them or set the values itself.
    rng = rng or np.random.default_rng(0)
    out = np.empty((n, N_PARAMS))
    got = 0
    core = [i for i, nm in enumerate(NAMES) if nm not in POST_HOC_DEFAULTS]
    # THE FROZEN DRAW BOX, not the legal envelope — see _LEGACY_DRAW_ROWS.
    # Scaling these uniforms by LOW/HIGH would move every seeded hull the
    # day a bound widens (measured 2026-08-26: 98 tests red at once).
    lo_c, hi_c = DRAW_LOW[core], DRAW_HIGH[core]
    post = {NAMES.index(k): float(v) for k, v in POST_HOC_DEFAULTS.items()
            if k in NAMES}
    for _ in range(max_tries * n):
        cand = np.empty(N_PARAMS)
        # EXACTLY as many uniforms as there are CORE genes, in their original
        # order — so the bit-stream is identical to the arity it had before any
        # post-hoc gene was appended, and a seeded draw reproduces the same
        # hulls it always did.
        cand[core] = rng.uniform(lo_c, hi_c)
        for i, v in post.items():
            cand[i] = v
        if explore_post_hoc:
            _explore_post_hoc_inplace(cand, _explore_rng(rng), features)
        if check(cand, vessel).ok:
            out[got] = cand
            got += 1
            if got == n:
                return out
    raise RuntimeError(f"only {got}/{n} feasible samples after {max_tries * n} tries")


def _explore_rng(rng: np.random.Generator) -> np.random.Generator:
    """The exploring stream's OWN Generator, derived deterministically from
    the caller's — one integer is consumed from a spawned child, never from
    the legacy stream itself, so the legacy bit-stream cannot move."""
    return rng.spawn(1)[0]


#: Post-hoc genes the exploring stream draws BLIND, and the reason each of
#: the others is not in this set. Written down because "which features can
#: the production search actually reach?" was, until 2026-09-01, answerable
#: only by reading this function — and the answer was SEVEN of twenty.
#:
#: MEASURED that day on the live UI pool for the brief "16 m x 4 m
#: recreational houseboat": `dwl`, `tun_crown`, `split_w`, `ch2_y` and
#: `rho_len` were EXACTLY 0.000 in all 128 candidates, and a 48x15 NSGA-II
#: run on the same brief reached no coherent feature either — every one of
#: them needs two or three genes non-zero AT ONCE, which polynomial mutation
#: from an all-zero start does not deliver. So four kernel phases were
#: implemented, tested, gated, and produced by no production search.
#:
#: The fix is NOT to draw all thirteen at random. Each is classified:
#:
#:   rho_bow, rho_len   BLIND — a pure shape warp with an exact SAC
#:                      contract (`2*a == A` at 3e-16). Added here.
#:   tun_*              REQUESTED — a tunnel stern is an ARCHITECTURE the
#:                      mission declares (`EnergySpec.drive == "tunnel"`,
#:                      which `parse_mission` sets for "protected prop"),
#:                      not a shape to stumble on. Drawn as a coherent
#:                      TRIPLE when asked for, never partially: two of the
#:                      three at zero is no tunnel at all.
#:   dwl, cwp_x,        NEITHER, and that is a MEASURED decision, not an
#:   rb_transom,        omission: `morphology_search` records that nudging
#:   rb_stem            `dwl` blindly hands the joint solve targets nobody
#:                      chose and the walk got WORSE (2/8 -> 0/8, "12 of 18
#:                      losing walks ended at dwl = 0"). The designed route
#:                      is `_derived_dwl`, which reads the delivered plan
#:                      off the hull and fairs it. A blind draw here would
#:                      re-acquire the refuted move.
#:   split_w, split_len NEITHER: the split stern is an architecture like the
#:                      tunnel, and no mission field expresses one yet. It
#:                      becomes REQUESTED the day one does.
#:   ch2_z, ch2_y       NEITHER: the second chine's knuckle wedge is not in
#:                      the section solve's target, so it changes
#:                      displacement by up to 5.75% of a station's area
#:                      (Gate DELIVERED-FORM). It stays unreachable until
#:                      the wedge is folded in — shipping a gene that
#:                      silently moves displacement is worse than not
#:                      reaching it.
_EXPLORE_BLIND_SPANS = {"r_stem": 0.35, "pmb": 0.35, "stem_depth": 0.25,
                        "beta_transom": 20.0, "beta_run": 0.5,
                        "flare_len": 0.5,
                        # rho(x), added 2026-09-01. Moderate like the rest:
                        # the warp reaches the forward 0.4 L at most, and a
                        # bow roundness anywhere in the box is legitimate
                        # (a hard-chine bottom running into a rounded entry
                        # is the shape the corpus keeps as a SEPARATE
                        # family precisely because it was not expressible).
                        "rho_len": 0.40, "rho_bow": 1.0}

#: `flare_bow` is drawn blind too, from its FULL BOX rather than a span,
#: because it is SIGNED — below zero is tumblehome, the wave-piercing bow's
#: whole mechanism — and a one-sided span cannot express that. It lives in
#: its own branch in `_explore_post_hoc_inplace`; this constant is what makes
#: "which genes are drawn blind" answerable without reading the function.
_EXPLORE_BLIND_FULL_BOX = ("flare_bow",)

#: Every gene the exploring stream draws on EVERY candidate, span-based or
#: full-box. Gate REACHABILITY reads this rather than restating it.
EXPLORE_BLIND_GENES = frozenset(_EXPLORE_BLIND_SPANS) | frozenset(
    _EXPLORE_BLIND_FULL_BOX)

#: The architecture features the exploring stream draws ONLY when the mission
#: asks for them, and the coherent bundle each one is. Drawing a partial
#: bundle is drawing nothing: `tun_w` alone leaves `tun_crown` at zero and
#: the notch has no height.
_EXPLORE_FEATURE_BUNDLES = {
    # floor, span — the floor is what makes it a tunnel rather than a
    # rounding error. `tun_crown` is a fraction of LOCAL DRAFT and the
    # crown must stay submerged at the floated state (the kernel refuses
    # otherwise, by name), so its ceiling here is well under the gene's.
    # CALIBRATED AGAINST FLOTATION, 2026-09-01, on 120 legacy draws under the
    # 16 x 4 m / 6 t brief (the crown is a fraction of the LOCAL DRAFT, and
    # these hulls float at ~57% of their design draft, so a tall crown ends up
    # near the floated waterline and `solve_to_displacement` stops converging):
    #
    #     tun_crown   0.05  0.10  0.15  0.20  0.25  0.30  0.40
    #     non-conv     30    39    49    56    62    64    72   of 120
    #     (legacy draw, no tunnel: 0 of 120)
    #
    # `tun_w` costs nothing measurable (39-40 of 120 across 0.10..0.60), so
    # the width is set by what a propeller needs and the CROWN is what is
    # bought carefully. [0.08, 0.20] is a real tunnel — 0.056 to 0.14 m of
    # crown on a 0.7 m draft, against the 0.1005 m that MEASURABLY turns
    # houseboat19's single prop from refused to feasible — at ~1/3 of the
    # population, which is why the bundle seeds HALF the initial population
    # and not all of it (see optimize._DrawBoxSampling).
    "tunnel": {"tun_w": (0.25, 0.25), "tun_crown": (0.08, 0.12),
               "tun_len": (0.18, 0.20)},
}


def features_for(mission) -> frozenset:
    """Which ARCHITECTURE features this mission asks the search to draw.

    The single home of mission -> feature translation, so the sampler and any
    future caller cannot disagree about what "protected prop" means.
    """
    if mission is None:
        return frozenset()
    e = getattr(mission, "energy", None)
    want = set()
    drive = str(getattr(e, "drive", "") or "")
    if drive == "tunnel" or float(getattr(e, "prop_tunnel_recess_m", 0.0)
                                  or 0.0) > 0.0:
        want.add("tunnel")
    return frozenset(want)


def apply_feature_bundles_inplace(cand: np.ndarray,
                                  erng: np.random.Generator,
                                  features) -> None:
    """Write the REQUESTED architecture into one candidate, in place.

    A whole bundle or nothing: `tun_w` alone leaves `tun_crown` at zero and
    the notch has no height, so a partial bundle is not a weak tunnel, it is
    no tunnel.

    Separated from `_explore_post_hoc_inplace` so the OPTIMIZER can use it
    too. MEASURED 2026-09-01 by the flow trace: after the exploring stream
    learned to draw a requested tunnel, `optimize.pareto_front` still could
    not — its `_FeasibleSampling` draws the LEGACY box through
    `grammar.sample`, so the brief "16 m x 4 m houseboat with a protected
    prop" returned a front whose chosen hull had tun_w = tun_crown =
    tun_len = 0. Two production design routes, one asking for an
    architecture and the other unable to draw it, is the same disagreement
    the length hint had.

    Consumes from `erng` ONLY when a feature was asked for, so a mission that
    asks for none leaves every seeded stream bit-identical.
    """
    if not features:
        return
    for feat in sorted(features):
        for nm, (floor, span) in _EXPLORE_FEATURE_BUNDLES.get(feat,
                                                              {}).items():
            cand[NAMES.index(nm)] = floor + span * erng.random()


def _explore_post_hoc_inplace(cand: np.ndarray,
                              erng: np.random.Generator,
                              features=frozenset()) -> None:
    """Draw the post-hoc genes and re-fair (Cp, lcb) into deliverable bands.

    The post-hoc draw is MODERATE, not box-uniform: box-uniform fullness
    (r_stem to 0.95, pmb to 0.55) contradicts almost every core draw and
    the section solver refuses the rest at the bow (a full bow needs
    draft); the exploring stream's job is coverage of the FEASIBLE
    neighbourhood, not of the box's corners. Bands are projected with the
    closed-form helpers so the candidate asks for a curve the family can
    deliver — the same re-fairing a designer does after moving fullness.

    `features` is what the MISSION asked for (`features_for`). See
    `_EXPLORE_BLIND_SPANS` for which genes are drawn blind, which are drawn
    only on request, and — for each of the rest — why not.
    """
    from .geometry import GeometryError, cp_band, lcb_band
    g = dict(zip(NAMES, map(float, cand)))
    spans = _EXPLORE_BLIND_SPANS
    for nm, hi in spans.items():
        cand[NAMES.index(nm)] = hi * erng.random()
    apply_feature_bundles_inplace(cand, erng, features)
    i_fb = NAMES.index("flare_bow")
    lo_fb, hi_fb = LOW[i_fb], HIGH[i_fb]
    cand[i_fb] = lo_fb + (hi_fb - lo_fb) * erng.random()
    # deadrise order: the aft warp may not exceed the midship value's law —
    # beta_transom above beta_mid reads as a warp the run cannot deliver
    i_bt = NAMES.index("beta_transom")
    cand[i_bt] = min(float(cand[i_bt]), float(g["beta_mid"]) + 5.0)
    try:
        b_lo, b_hi = cp_band(g["LWL"], g["x_mb"], g["r_transom"],
                             float(cand[NAMES.index("r_stem")]),
                             float(cand[NAMES.index("pmb")]))
        i_cp = NAMES.index("Cp")
        lo_c = max(b_lo + 1e-3, float(LOW[i_cp]))
        hi_c = min(b_hi - 1e-3, float(HIGH[i_cp]))
        if hi_c > lo_c:
            cand[i_cp] = float(np.clip(cand[i_cp], lo_c, hi_c))
        l_lo, l_hi = lcb_band(g["LWL"], g["x_mb"], g["r_transom"],
                              float(cand[i_cp]),
                              float(cand[NAMES.index("r_stem")]),
                              float(cand[NAMES.index("pmb")]))
        i_l = NAMES.index("lcb")
        lo_l = max(l_lo + 1e-2, float(LOW[i_l]))
        hi_l = min(l_hi - 1e-2, float(HIGH[i_l]))
        if hi_l > lo_l:
            cand[i_l] = float(np.clip(cand[i_l], lo_l, hi_l))
    except GeometryError:
        pass                          # check() will refuse it by name


def named(x: np.ndarray) -> dict[str, float]:
    return {n: float(val) for n, val in zip(NAMES, np.asarray(x, dtype=float))}


# Genes a caller may OMIT, and the value that leaves the geometry unchanged.
# A gene belongs here ONLY if some value of it is provably a no-op: `beta_run`
# = 0 disables the aft deadrise warp entirely, so every genome written before
# it existed still describes exactly the hull it always did.
POST_HOC_DEFAULTS: dict[str, float] = {"beta_transom": 0.0, "beta_run": 0.0,
                                       "flare_bow": 0.0, "flare_len": 0.0,
                                       "stem_depth": 0.0,
                                       "r_stem": 0.0, "pmb": 0.0,
                                       # Phase 3 (2026-08-27): dwl = 0 makes
                                       # the whole B(x) branch unreachable
                                       # code, so the other three are inert
                                       # whatever they hold; 0 keeps them
                                       # meaningful anyway (waterline follows
                                       # Cp, closes to a point both ends)
                                       "dwl": 0.0, "cwp_x": 0.0,
                                       "rb_transom": 0.0, "rb_stem": 0.0,
                                       # Phase 4: the tunnel notch — zero
                                       # width x height x length is no notch
                                       "tun_w": 0.0, "tun_crown": 0.0,
                                       "tun_len": 0.0,
                                       # Phase 4B: no wall, no hole
                                       "split_w": 0.0, "split_len": 0.0,
                                       # Phase 3: no warp -> one roundness.
                                       # rho_bow is inert at rho_len 0, and
                                       # 0.0 keeps it meaningful anyway.
                                       "rho_bow": 0.0, "rho_len": 0.0,
                                       # Phase 5: ch2_y = 0 puts the vertex
                                       # ON the line it would interrupt, so
                                       # there is no second chine and ch2_z
                                       # is unreachable code
                                       "ch2_z": 0.0, "ch2_y": 0.0}


def pad_genome(g) -> np.ndarray:
    """Extend a HISTORICAL genome to this tree's arity with no-op defaults.

    Genomes are written down — in fixtures, in `data/`, in receipts, in
    published records — and they are written at the arity of the day. Every one
    of those is still a valid hull description, because a gene may only be
    APPENDED to this grammar if some value of it is a proven no-op (that is what
    `POST_HOC_DEFAULTS` means). Padding with those values therefore yields the
    SAME HULL the recorded numbers always described, bit for bit.

    MEASURED 2026-08-24, which is why this is one function and not four
    copies: going 16 -> 21 genes, a 16-wide genome was refused for WIDTH by
    `tests/test_contract.py`, `tests/test_manufacturing.py`, `scripts/parity.py`
    and the population manifests — each reading as "the grammar refused this
    boat" when nothing about the boat had changed.

    Raises when a gene was REMOVED (the genome is wider than this grammar), or
    when an appended gene has no proven no-op: both mean the padded vector
    would be a DIFFERENT hull, and returning one quietly is the defect this
    helper exists to prevent.
    """
    g = np.asarray(g, dtype=float).ravel()
    if g.size == N_PARAMS:
        return g
    if g.size > N_PARAMS:
        raise ValueError(
            f"genome has arity {g.size} and this grammar has {N_PARAMS}: a "
            f"gene was REMOVED, which is not a no-op and cannot be padded")
    tail = NAMES[g.size:]
    missing = [n for n in tail if n not in POST_HOC_DEFAULTS]
    if missing:
        raise ValueError(
            f"cannot pad a {g.size}-gene genome to {N_PARAMS}: {missing} have "
            f"no proven no-op default, so the result would be a different hull")
    return np.concatenate([g, np.array([float(POST_HOC_DEFAULTS[n])
                                        for n in tail], dtype=float)])


def vector(d: dict[str, float]) -> np.ndarray:
    """A genome vector from a name -> value mapping.

    A MISSING gene raises, except those in `POST_HOC_DEFAULTS`. An UNKNOWN key
    also raises: until 2026-08-23 this silently DISCARDED unrecognised keys, so
    when a recalibration removed `l_pmb` every caller still passing it went on
    running and quietly got a different hull -- and it produced a false
    measurement that stood for hours.
    """
    missing = [n for n in NAMES if n not in d and n not in POST_HOC_DEFAULTS]
    if missing:
        raise KeyError(f"genome is missing {missing}; only "
                       f"{sorted(POST_HOC_DEFAULTS)} may be omitted")
    unknown = [k for k in d if k not in NAMES]
    if unknown:
        raise KeyError(f"genome carries {unknown}, not gene(s) in this "
                       f"grammar. Known: {NAMES}")
    return np.array([d.get(n, POST_HOC_DEFAULTS.get(n, 0.0)) for n in NAMES],
                    dtype=float)
