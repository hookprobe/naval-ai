"""ES-TRIN — European Standard for inland navigation vessels, as checkers.

Gate 6 asks for "ES-TRIN as executable checkers", and gap G7 recorded ZERO
CODE against it while `PLM.md` listed the Solar Liveaboard (Danube) SKU as
demo green. A Danube liveaboard is an inland-waterway craft; ES-TRIN is the
technical standard that governs inland-waterway craft in the EU, referenced by
Directive (EU) 2016/1629. Not having it was not a documentation gap.

WHAT THIS MODULE DOES, AND THE ORDER IT DOES IT IN
-------------------------------------------------
1. ES-SCOPE decides whether the Directive — and therefore ES-TRIN — governs
   this craft at all. It is FIRST and it can end the assessment, because the
   most likely honest answer for a 4-20 m hull is "out of scope", and a bar
   from a standard that does not apply is not information. (Same shape as the
   ISO 12217-1 scope guard next door, gap G8, and as `gate2m.py` printing
   KCS's EFD figure over a Wigley hull.)
2. For a craft IN scope, the two Chapter 4 articles this repository can
   actually measure — safety clearance and freeboard.
3. ES-COV, which FAILS for any in-scope craft, listing the ES-TRIN chapters
   that are not implemented. An in-scope craft must not be able to read a
   green report as compliance with a 578-page standard of which we implement
   two articles.

   THE COUNT WAS WRONG IN THREE DIFFERENT WAYS AT ONCE, MEASURED 2026-08-13,
   and every one of them overstated coverage:
     - this docstring said "eighteen";
     - `UNIMPLEMENTED_CHAPTERS` held SEVENTEEN entries;
     - and the tuple stopped at Chapter 20, which silently asserted that
       ES-TRIN HAS twenty chapters. It has THIRTY-THREE. Chapters 21-33
       (push-tow craft, floating equipment, worksite craft, traditional
       craft, sea-going vessels, RECREATIONAL CRAFT, container carriers,
       craft over 110 m, high-speed vessels, ... ) were not merely
       unimplemented, they were not on the list of things we admit to not
       implementing.
   ES-COV's whole job is an honest refusal, and it was reporting 1 of 18
   against a true 2 articles of 33 chapters — coverage overstated by ~40%.
   `TOTAL_CHAPTERS` is now derived from the table of contents of the edition
   named below, read directly, and the denominator is asserted in the tests.

4. ES-REC, which records that ES-TRIN Art. 26.01 DOES NOT APPLY CHAPTER 4 TO
   RECREATIONAL CRAFT. This is the sharpest finding in the module and it
   points at the module itself: the two bars implemented here are the two
   bars most likely not to govern the craft this project builds. See the
   ES-REC section in `assess` for the verbatim clause list.

PROVENANCE
----------
Scope thresholds: Directive (EU) 2016/1629, Article 2(1), consolidated text at
`eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02016L1629-20240101`.

Numeric bars and definitions: ES-TRIN edition **2023/1**, published free by
CESNI (`cesni.eu`), read directly. Articles 1.01(4.2), 1.01(4.4), 1.01(4.16),
4.01(1) and 4.02 are transcribed below with their own wording quoted in the
docstrings, so a reviewer can check the transcription without re-deriving the
mechanics. The Art. 2(1) scope test is decided on ES-TRIN's own L, B and T —
HULL dimensions, not waterline ones; `hull_length_m` and `hull_breadth_m` are
the single place each is measured, and the section above them records the
20 m craft that escaped the standard entirely when they were not.

BASIS IS STILL 'approx', AND THAT IS NOT A CONTRADICTION. `review.basis_for`
returns 'standard' only for rule ids a named reviewer has confirmed against the
text on a recorded date. Nobody has reviewed these; the author transcribed
them. `basis` records WHO CHECKED, not how confident the author feels, and
promoting a rule by editing the review record from the same change that
introduced it would make Gate 6R self-certifying. The edition is named above
precisely so that review is cheap when someone qualified does it.

DISCLAIMER (honesty rule 5) is unchanged: ASSESSMENT AID, NOT CERTIFICATION.
An ES-TRIN certificate comes from an inspection body, not from this file.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:                      # avoid the evaluate <-> rules cycle
    from ..evaluate import Evaluation
    from ..geometry import Hull

from . import RuleFinding
from .review import basis_for

# ---------------------------------------------------------------- provenance

_DIR_2016_1629 = "Directive (EU) 2016/1629 Art. 2(1) (consolidated 2024-01-01)"
_ESTRIN = "ES-TRIN edition 2023/1 (CESNI, published free at cesni.eu)"

# RE-VERIFIED 2026-08-13 against the 2025/1 text (`ES_TRIN_2025_signed_en.pdf`,
# 578 pages, CESNI, free). Articles 4.01 and 4.02 are UNCHANGED between 2023/1
# and 2025/1 — every bar and coefficient transcribed here was re-read clause by
# clause in the newer edition. The edition string above still names 2023/1
# because that is the text the ORIGINAL transcription was made from and
# `basis_for` records who checked what; this constant records the recheck
# separately rather than silently promoting the citation.
_ESTRIN_2025 = "ES-TRIN edition 2025/1 (CESNI, published free at cesni.eu)"

# ------------------------------------------------------------------- scope

# Directive (EU) 2016/1629 Art. 2(1): the Directive applies to "vessels having
# a length (L) of 20 metres or more" and to "vessels for which the product of
# length (L), breadth (B) and draught (T) is a volume of 100 cubic metres or
# more". Either limb brings a craft in; both are checked.
SCOPE_LENGTH_M = 20.0
SCOPE_LBT_VOLUME_M3 = 100.0

# L, B AND T IN THAT TEST ARE HULL DIMENSIONS, NOT WATERLINE ONES, AND THE
# DIFFERENCE DECIDED THE SCOPE CALL. Art. 2(1) uses the definitions of
# Art. 3, which are ES-TRIN's: "length (L)" is the MAXIMUM LENGTH OF THE HULL
# excluding rudder and bowsprit (ES-TRIN Art. 1.01(4.16)), and "breadth (B)"
# is the MAXIMUM BREADTH OF THE HULL measured to the outer edge of the shell
# plating. ES-TRIN names the waterline pair separately (L_WL, B_WL) precisely
# because they are not these.
#
# MEASURED 2026-08-07, and this is why the module emitted a scope finding and
# nothing else: a 20.0 m grammar hull floats with `hydro.lwl_eff` = 19.00 m and
# a chine half-breadth of 1.60 m, so reading L and B off the waterline gave
# L 19.00 m < 20 m and L.B.T 22.7 m3 < 100 m3 — OUT OF SCOPE, no Chapter 4
# findings, and no coverage refusal. On the hull dimensions the same craft is
# L 20.00 m, B 3.67 m, T 0.37 m: IN SCOPE by the length limb.
#
# The direction of that error is the point. Next door in `iso12217.py` the same
# substitution is deliberate and safe, because there being ruled out of scope
# means getting NO verdict. Here it means being told a craft the Directive
# governs is "a recreational craft under the RCD instead" and never being told
# an inspection body is required — an understated L or B silently DELETES the
# assessment. So ES-TRIN's own measurands are used, and `hull_length_m` /
# `hull_breadth_m` below are the single place either is computed.

# ES-TRIN Art. 4.01(1): "The safety clearance shall be at least 300 mm."
SAFETY_CLEARANCE_MIN_M = 0.300

# ES-TRIN Art. 4.02(1): "The freeboard of vessels with a continuous deck,
# without sheer and superstructures, shall be 150 mm."
FREEBOARD_BASE_MM = 150.0

# Art. 4.02(5) caps on the ACTUAL sheer that may be credited: forward sheer
# "shall not be taken to be more than 1000 mm", aft sheer "may not be taken to
# be more than 500 mm".
SHEER_FWD_CAP_MM = 1000.0
SHEER_AFT_CAP_MM = 500.0

# Art. 4.02(5): "However, coefficient r will not be taken to be more than 1."
# Art. 4.02(6): if beta_a.Se_a exceeds beta_v.Se_v, the AFT term is clamped to
# the forward one. Art. 4.02(7): "In view of the reductions referred to in (2)
# to (6) the freeboard shall be not less than 0 mm."
#
# ALL THREE WERE MISSING, AND ALL THREE OMISSIONS ERRED THE UNSAFE WAY.
# Each clause CAPS a reduction, and `F = 150 - (Se_v + Se_a)/15` subtracts that
# reduction, so dropping a cap makes the REQUIRED freeboard smaller and the
# check easier to pass. That is the opposite direction from the alpha = 0
# simplification documented in `required_freeboard_mm`, which the docstring
# correctly calls conservative — so the file contained one omission that erred
# safe, described at length, and three that erred unsafe, not mentioned.
SHEER_R_CAP = 1.0
FREEBOARD_FLOOR_MM = 0.0

# ES-TRIN 2025/1 has THIRTY-THREE chapters. Read from the table of contents of
# `downloads/standards/ES_TRIN_2025_signed_en.pdf`, not remembered.
TOTAL_CHAPTERS = 33

# The ONE article pair we implement, so that coverage is stated as a fraction
# of something real. Chapter 4 itself is only PARTIALLY implemented: 4.01(2)
# (the 500 mm bar for openings that cannot be closed weathertight), 4.01(3)
# and 4.02(8) (inspection-body discretion to demand more), 4.02(9) (salinity),
# 4.03/4.04 (draught marks and scales) and 4.05 (zone 4 derogations) are not.
IMPLEMENTED_ARTICLES = ("4.01(1) safety clearance", "4.02 freeboard")

# What we do not implement. Transcribed from the ES-TRIN 2025/1 table of
# contents so the refusal names real chapters rather than gesturing. Chapter 1
# (general provisions) is EXCLUDED because its definitions ARE used — 1.01(4.2),
# (4.4) and (4.16) are what `hull_length_m` and `hull_breadth_m` implement — and
# Chapter 4 is excluded because it is the chapter we partially implement. Every
# other chapter of the standard is here.
UNIMPLEMENTED_CHAPTERS = (
    "2 procedure",
    "3 shipbuilding requirements", "5 manoeuvrability", "6 steering system",
    "7 wheelhouse", "8 engine design", "9 emission of gaseous and particulate "
    "pollutants", "10 electrical equipment and installations",
    "11 electric propulsion systems", "12 electronic equipment and systems",
    "13 equipment", "14 safety at work stations", "15 accommodation",
    "16 fuel-fired heating, cooking and refrigerating equipment",
    "17 liquefied gas installations", "18 on-board sewage treatment plants",
    "19 passenger vessels", "20 passenger sailing vessels",
    "21 craft forming part of a push-tow or side-by-side formation",
    "22 floating equipment", "23 worksite craft", "24 traditional craft",
    "25 sea-going vessels", "26 recreational craft",
    "27 vessels carrying containers", "28 craft longer than 110 m",
    "29 high-speed vessels",
    "30 craft with propulsion or auxiliary systems using fuels with a "
    "flashpoint <= 55 C", "31 vessels sailing with minimum crew",
    "32 transitional provisions for craft on the Rhine (Zone R)",
    "33 transitional provisions for craft on Zone 1, 2, 3 and 4 waterways",
)


def hull_length_m(hull: "Hull") -> float:
    """L [m] — ES-TRIN Art. 1.01(4.16), maximum length of the hull.

    The station grid spans the hull from transom to stem, so its x extent IS
    the hull length. It is >= `hydro.lwl_eff`, which is the immersed length at
    the floating draught and is the wrong measurand for Art. 2(1).

    DELIBERATELY NOT SHARED WITH `iso12217.hull_length_m`, which takes an
    Evaluation and returns the WATERLINE length as a documented understatement
    of L_H. Two functions because they are two quantities; sharing the name
    would be the one-number-two-places defect wearing a helpful disguise.

    Neither rudder nor bowsprit is modelled, so the exclusion Art. 1.01(4.16)
    makes is already satisfied by construction.
    """
    xs = np.asarray(hull.x, dtype=float)
    return float(xs.max() - xs.min())


def hull_breadth_m(hull: "Hull") -> float:
    """B [m] — ES-TRIN Art. 1.01, maximum breadth of the hull.

    The definition measures "to the outer edge of the shell plating", i.e. the
    widest point anywhere on the hull, not the widest point at the waterline
    (that is B_WL, a separate ES-TRIN definition). On a flared grammar hull the
    sheer is wider than the chine, so BOTH offset lines are taken into account
    and the larger wins. Half-breadths are stored, hence the factor 2.

    Shell-plating thickness is not modelled, so this is the moulded breadth and
    it UNDERSTATES B by two plate thicknesses (~10 mm on a 3.7 m beam). That
    errs towards out-of-scope, which is the unsafe direction here, so it is
    recorded in the scope finding's note rather than left implicit.
    """
    return 2.0 * float(max(np.max(np.asarray(hull.y_sheer, dtype=float)),
                           np.max(np.asarray(hull.y_chine, dtype=float))))


def _scope_volume(length_m: float, beam_m: float, draught_m: float) -> float:
    return length_m * beam_m * draught_m


def in_scope(length_m: float, beam_m: float, draught_m: float) -> bool:
    """Directive (EU) 2016/1629 Art. 2(1), both limbs."""
    return (length_m >= SCOPE_LENGTH_M
            or _scope_volume(length_m, beam_m, draught_m) >= SCOPE_LBT_VOLUME_M3)


def required_freeboard_mm(hull: "Hull") -> tuple[float, dict]:
    """ES-TRIN Art. 4.02 required freeboard [mm], and the terms that built it.

    Art. 4.02(1) sets 150 mm for a craft "with a continuous deck, without
    sheer and superstructures". Every hull this grammar emits HAS sheer (the
    `sheer_rise` parameter) and has no superstructure, so Art. 4.02(2) applies
    with the superstructure terms at zero:

        F = 150 (1 - a) - (b_v Se_v + b_a Se_a) / 15   [mm]

    with a = 0 (Art. 4.02(3): a is the summed effective superstructure length
    over L, and no superstructure is modelled) and therefore b_v = b_a = 1
    (Art. 4.02(4): b = 1 - 3 le / L).

    Se = S p (Art. 4.02(5)), S being the ACTUAL sheer in mm capped at 1000 mm
    forward and 500 mm aft, and p = 4x/L where x is "the abscissa, measured
    from the extremity, of the point where the sheer is 0.25 S". x is found on
    the hull's own sheer line rather than assumed parabolic, so the result
    follows whatever profile the geometry produced.

    THE SUPERSTRUCTURE TERM IS ZERO BECAUSE WE MODEL NO SUPERSTRUCTURE, NOT
    BECAUSE IT IS NEGLIGIBLE. a > 0 RAISES the credit for superstructures and
    lowers required freeboard, so omitting it is conservative — the direction a
    missing term has to err in. A craft with a deckhouse would be assessed too
    strictly here, and that is recorded in the finding's note.
    """
    zs = np.asarray(hull.z_sheer, dtype=float)
    xs = np.asarray(hull.x, dtype=float)
    lwl = float(xs[-1] - xs[0])
    base = float(zs.min())
    i_low = int(np.argmin(zs))

    def _sheer(seg_x: np.ndarray, seg_z: np.ndarray, cap: float,
               from_end: str) -> tuple[float, float]:
        """(S [mm], Se [mm]) for one end. Empty or flat segment -> no sheer.

        Walks INBOARD from the extremity and interpolates the station where
        the sheer has fallen to 0.25 S. Interpolated rather than snapped to a
        station because `x` is a length in the formula, and rounding it to the
        station spacing would make the answer a function of `n_stations`.
        """
        if seg_x.size < 2:
            return 0.0, 0.0
        rise_mm = (seg_z - base) * 1e3
        s_raw = float(rise_mm.max())
        if s_raw <= 0.0:
            return 0.0, 0.0
        s = min(s_raw, cap)
        target = 0.25 * s_raw
        # order from the extremity inboard
        xx = seg_x[::-1] if from_end == "fwd" else seg_x
        rr = rise_mm[::-1] if from_end == "fwd" else rise_mm
        end_x = float(xx[0])
        x_abs = abs(float(xx[-1]) - end_x)      # sheer never falls that far
        for k in range(1, len(rr)):
            if rr[k] <= target:
                r0, r1 = float(rr[k - 1]), float(rr[k])
                f = 0.0 if abs(r0 - r1) < 1e-12 else (r0 - target) / (r0 - r1)
                xc = float(xx[k - 1]) + f * (float(xx[k]) - float(xx[k - 1]))
                x_abs = abs(xc - end_x)
                break
        # Art. 4.02(5) closes with "However, coefficient r will not be taken to
        # be more than 1." Uncapped, a sheer line that reaches 0.25 S beyond
        # L/4 from the extremity yields r > 1, inflating Se and so DEFLATING
        # the required freeboard. The cap is the standard's, not a guard.
        p = min(4.0 * x_abs / max(lwl, 1e-9), SHEER_R_CAP)
        return s, s * p

    s_v, se_v = _sheer(xs[i_low:], zs[i_low:], SHEER_FWD_CAP_MM, "fwd")
    s_a, se_a = _sheer(xs[:i_low + 1], zs[:i_low + 1], SHEER_AFT_CAP_MM, "aft")

    # Art. 4.02(6): "If beta_a . Se_a is greater than beta_v . Se_v, the value
    # of beta_v . Se_v will be taken as being the value for beta_a . Se_a."
    # beta_v = beta_a = 1 here (Art. 4.02(4) with no superstructure), so the
    # clause reduces to clamping the aft contribution to the forward one. A
    # stern-heavy sheer cannot buy more freeboard credit than the bow earns.
    se_a_eff = min(se_a, se_v)

    f_raw = FREEBOARD_BASE_MM - (se_v + se_a_eff) / 15.0
    # Art. 4.02(7): "In view of the reductions referred to in (2) to (6) the
    # freeboard shall be not less than 0 mm."
    #
    # THIS CLAUSE CANNOT FIRE WHILE alpha = 0, and saying so is the point.
    # Art. 4.02(5) caps the actual sheers at 1000 mm forward and 500 mm aft and
    # caps r at 1, so the reduction cannot exceed (1000 + 500)/15 = 100 mm
    # against the 150 mm base: F >= 50 mm, always. The floor becomes reachable
    # only when a superstructure shrinks the base through 150(1 - alpha), which
    # this project does not model yet. It is transcribed now anyway, because a
    # clause added only on the day it first bites is a clause nobody reviews.
    f = max(f_raw, FREEBOARD_FLOOR_MM)
    return f, {"S_v_mm": s_v, "Se_v_mm": se_v, "S_a_mm": s_a,
               "Se_a_mm": se_a, "Se_a_capped_mm": se_a_eff,
               "F_before_floor_mm": f_raw, "alpha": 0.0}


def assess(ev: "Evaluation", hull: "Hull") -> list[RuleFinding]:
    """ES-TRIN findings for one evaluated hull. Scope first, always.

    `hull` is passed rather than rebuilt from `ev.params` so that the sheer
    line the freeboard formula reads is the SAME geometry the hydrostatics
    floated — the two-copies defect this project keeps finding, applied to a
    shape instead of a number.
    """
    out: list[RuleFinding] = []

    # ---- ES-SCOPE ------------------------------------------------------
    # An unmeasurable scope test is fatal, not a pass: if we cannot say whether
    # the standard applies, we cannot say anything.
    if ev.hydro is None:
        out.append(RuleFinding(
            "ES-SCOPE", f"{_DIR_2016_1629}", basis_for("ES-SCOPE"), False,
            float("nan"), SCOPE_LBT_VOLUME_M3, "m3",
            "no floatation state — L, B and T are unknown, so whether "
            "ES-TRIN governs this craft is UNDECIDABLE"))
        return out

    length = hull_length_m(hull)
    beam = hull_breadth_m(hull)
    draught = float(ev.hydro.draft)
    vals = (length, beam, draught)
    if not all(math.isfinite(v) and v > 0.0 for v in vals):
        out.append(RuleFinding(
            "ES-SCOPE", f"{_DIR_2016_1629}", basis_for("ES-SCOPE"), False,
            float("nan"), SCOPE_LBT_VOLUME_M3, "m3",
            f"L/B/T not all finite and positive ({length}, {beam}, "
            f"{draught}) — scope UNDECIDABLE"))
        return out

    vol = _scope_volume(length, beam, draught)
    if not in_scope(length, beam, draught):
        out.append(RuleFinding(
            "ES-SCOPE", f"{_DIR_2016_1629}", basis_for("ES-SCOPE"), True,
            vol, SCOPE_LBT_VOLUME_M3, "m3",
            f"OUT OF SCOPE: L {length:.2f} m < {SCOPE_LENGTH_M:.0f} m and "
            f"L.B.T {vol:.1f} m3 < {SCOPE_LBT_VOLUME_M3:.0f} m3, so Directive "
            f"(EU) 2016/1629 — and with it ES-TRIN — does not govern this "
            f"craft. It is a recreational craft under the RCD instead. No "
            f"ES-TRIN bar is applied. (L and B are the HULL dimensions per "
            f"ES-TRIN Art. 1.01, not the waterline ones; B is moulded, so it "
            f"understates the shell-plating breadth by ~two plate "
            f"thicknesses. A craft within a few per cent of either threshold "
            f"is a case for the inspection body, not for this file.)"))
        return out

    out.append(RuleFinding(
        "ES-SCOPE", f"{_DIR_2016_1629}", basis_for("ES-SCOPE"), True,
        vol, SCOPE_LBT_VOLUME_M3, "m3",
        f"IN SCOPE: L {length:.2f} m, B {beam:.2f} m, T {draught:.2f} m "
        f"(L.B.T {vol:.1f} m3), on the hull dimensions of ES-TRIN Art. 1.01. "
        f"ES-TRIN applies and an inspection body's certificate is required. "
        f"The findings below are an ASSESSMENT AID, never certification."))

    # ---- ES-SAFE, Art. 4.01(1) -----------------------------------------
    # 1.01(4.2) defines safety clearance as the distance from the plane of
    # maximum draught to the parallel plane through "the lowest point above
    # which the craft is no longer deemed to be watertight". We model no
    # openings, so that point is the sheer line, and the measurand is the same
    # `freeboard_min` that ES-FB below uses for a DIFFERENT definition. That
    # is a limitation of the model, not of the standard: declaring real
    # openings separates the two, and the note says so.
    clearance = float(ev.hydro.freeboard_min)
    out.append(RuleFinding(
        "ES-SAFE", f"{_ESTRIN} Art. 4.01(1) (safety clearance >= 300 mm)",
        basis_for("ES-SAFE"), clearance >= SAFETY_CLEARANCE_MIN_M,
        clearance, SAFETY_CLEARANCE_MIN_M, "m",
        "lowest non-watertight point assumed at the sheer line because no "
        "openings are modelled; a real hatch or window lowers it. Art. "
        "4.01(2) raises the bar to 500 mm for openings that cannot be closed "
        "spray-proof and weathertight — not applied, as no openings exist to "
        "classify."))

    # ---- ES-FB, Art. 4.02 ----------------------------------------------
    f_req_mm, terms = required_freeboard_mm(hull)
    f_req_m = f_req_mm / 1e3
    out.append(RuleFinding(
        "ES-FB", f"{_ESTRIN} Art. 4.02 (freeboard, sheer-corrected)",
        basis_for("ES-FB"), clearance >= f_req_m, clearance, f_req_m, "m",
        f"Art. 4.02(2) with alpha=0 (no superstructure modelled, which is "
        f"CONSERVATIVE — a superstructure would reduce the requirement): "
        f"S_v {terms['S_v_mm']:.0f} mm -> Se_v {terms['Se_v_mm']:.0f} mm, "
        f"S_a {terms['S_a_mm']:.0f} mm -> Se_a {terms['Se_a_mm']:.0f} mm, "
        f"F = 150 - (Se_v + Se_a)/15 = {f_req_mm:.0f} mm. Freeboard per "
        f"1.01(4.4) is to the lowest point of the gunwale; the sheer line is "
        f"used."))

    # ---- ES-REC, Art. 26.01: the two bars above may not govern -----------
    # READ DIRECTLY from ES-TRIN 2025/1 p.191-192 on 2026-08-13. Art. 26.01(1)
    # applies to recreational craft only "the following requirements", and the
    # list is: parts of Ch. 3, 5, 6, 7, 8; all of Ch. 9; part of Ch. 10, 13;
    # all of Ch. 16, 17; part of Ch. 21. CHAPTER 4 IS NOT IN IT. Art. 26.01(2)
    # is narrower still — for a recreational craft subject to Directive
    # 2013/53/EU (the RCD, i.e. exactly this project's SKUs) "only the
    # following requirements apply": 6.08, part of Ch. 7, 8, 13, and Ch. 16,
    # 17. Chapter 4 is absent from that list too.
    #
    # So ES-SAFE and ES-FB — the ONLY two numeric bars this module computes —
    # are very likely not the bars that govern the craft we build. This module
    # cannot decide it, because craft TYPE is not modelled: `MissionSpec` has
    # no recreational/commercial flag, and inferring one from the hull would be
    # inventing a fact. It is therefore REPORTED, not silently applied and not
    # silently dropped. Deleting the two findings on this basis would be the
    # worse error in the same family as the L/B measurand above: an
    # understatement that DELETES the assessment.
    out.append(RuleFinding(
        "ES-REC", f"{_ESTRIN_2025} Art. 26.01 (application of Part II to "
                  f"recreational craft)",
        basis_for("ES-REC"), False, float("nan"), 4.0, "chapter",
        "UNDECIDABLE, AND IT DECIDES WHETHER THE TWO BARS ABOVE APPLY. "
        "Art. 26.01(1) lists the Part II requirements a recreational craft "
        "must meet and CHAPTER 4 IS NOT AMONG THEM; Art. 26.01(2), for a "
        "recreational craft subject to Directive 2013/53/EU, is narrower "
        "still and also omits Chapter 4. Craft type is not modelled here, so "
        "whether ES-SAFE and ES-FB govern this hull CANNOT BE ANSWERED. If "
        "the craft is recreational they are informative only, and the "
        "governing set is Art. 26.01's — none of which is implemented. An "
        "inspection body decides this, not this file."))

    # ---- ES-COV: the refusal -------------------------------------------
    # FAILS, always, for an in-scope craft. Two articles of thirty-three
    # chapters is not an assessment, and a report that passed every finding it
    # happened to implement would read as compliance.
    out.append(RuleFinding(
        "ES-COV", f"{_ESTRIN} (coverage of the standard)",
        basis_for("ES-COV"), False, 1.0, float(TOTAL_CHAPTERS), "chapters",
        f"IN SCOPE AND NOT ASSESSED. {len(UNIMPLEMENTED_CHAPTERS)} of "
        f"{TOTAL_CHAPTERS} chapters are wholly unimplemented. Chapter 1 is "
        f"used for definitions only. Chapter 4 is PARTIALLY implemented — "
        + ", ".join(IMPLEMENTED_ARTICLES)
        + " — while 4.01(2), 4.01(3), 4.02(8), 4.02(9), 4.03, 4.04 and 4.05 "
          "are not. Not implemented at all: "
        + "; ".join(f"Ch. {c}" for c in UNIMPLEMENTED_CHAPTERS)
        + ". This craft requires an inspection body under Directive (EU) "
          "2016/1629; nothing here substitutes for one."))
    return out
