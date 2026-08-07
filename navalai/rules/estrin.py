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
3. ES-COV, which FAILS for any in-scope craft, listing the eighteen ES-TRIN
   chapters that are not implemented. An in-scope craft must not be able to
   read a green report as compliance with a 558-page standard of which we
   implement one chapter.

PROVENANCE
----------
Scope thresholds: Directive (EU) 2016/1629, Article 2(1), consolidated text at
`eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02016L1629-20240101`.

Numeric bars and definitions: ES-TRIN edition **2023/1**, published free by
CESNI (`cesni.eu`), read directly. Articles 1.01(4.2), 1.01(4.4), 4.01(1) and
4.02 are transcribed below with their own wording quoted in the docstrings, so
a reviewer can check the transcription without re-deriving the mechanics.

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

# ------------------------------------------------------------------- scope

# Directive (EU) 2016/1629 Art. 2(1): the Directive applies to "vessels having
# a length (L) of 20 metres or more" and to "vessels for which the product of
# length (L), breadth (B) and draught (T) is a volume of 100 cubic metres or
# more". Either limb brings a craft in; both are checked.
SCOPE_LENGTH_M = 20.0
SCOPE_LBT_VOLUME_M3 = 100.0

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

# What we do not implement. Transcribed from the ES-TRIN 2023/1 table of
# contents so the refusal names real chapters rather than gesturing.
UNIMPLEMENTED_CHAPTERS = (
    "3 shipbuilding requirements", "5 manoeuvrability", "6 steering system",
    "7 wheelhouse", "8 engine design", "9 emission of gaseous and particulate "
    "pollutants", "10 electrical equipment and installations",
    "11 electric vessel propulsion", "12 electronic equipment and systems",
    "13 equipment", "14 safety at work stations", "15 accommodation",
    "16 fuel-fired heating, cooking and refrigerating equipment",
    "17 liquefied gas installations", "18 on-board sewage treatment plants",
    "19 passenger vessels", "20 passenger sailing vessels",
)


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
        p = 4.0 * x_abs / max(lwl, 1e-9)
        return s, s * p

    s_v, se_v = _sheer(xs[i_low:], zs[i_low:], SHEER_FWD_CAP_MM, "fwd")
    s_a, se_a = _sheer(xs[:i_low + 1], zs[:i_low + 1], SHEER_AFT_CAP_MM, "aft")
    f = FREEBOARD_BASE_MM - (se_v + se_a) / 15.0
    return f, {"S_v_mm": s_v, "Se_v_mm": se_v, "S_a_mm": s_a,
               "Se_a_mm": se_a, "alpha": 0.0}


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

    lwl = float(ev.hydro.lwl_eff)
    beam = 2.0 * float(np.max(hull.y_chine))
    draught = float(ev.hydro.draft)
    vals = (lwl, beam, draught)
    if not all(math.isfinite(v) and v > 0.0 for v in vals):
        out.append(RuleFinding(
            "ES-SCOPE", f"{_DIR_2016_1629}", basis_for("ES-SCOPE"), False,
            float("nan"), SCOPE_LBT_VOLUME_M3, "m3",
            f"L/B/T not all finite and positive ({lwl}, {beam}, {draught}) — "
            f"scope UNDECIDABLE"))
        return out

    vol = _scope_volume(lwl, beam, draught)
    if not in_scope(lwl, beam, draught):
        out.append(RuleFinding(
            "ES-SCOPE", f"{_DIR_2016_1629}", basis_for("ES-SCOPE"), True,
            vol, SCOPE_LBT_VOLUME_M3, "m3",
            f"OUT OF SCOPE: L {lwl:.2f} m < {SCOPE_LENGTH_M:.0f} m and "
            f"L.B.T {vol:.1f} m3 < {SCOPE_LBT_VOLUME_M3:.0f} m3, so Directive "
            f"(EU) 2016/1629 — and with it ES-TRIN — does not govern this "
            f"craft. It is a recreational craft under the RCD instead. No "
            f"ES-TRIN bar is applied. (L is the waterline length; ES-TRIN "
            f"1.01(4.16) defines L as maximum HULL length, which is longer, "
            f"so a craft close to either threshold should be re-checked "
            f"against a real L_H.)"))
        return out

    out.append(RuleFinding(
        "ES-SCOPE", f"{_DIR_2016_1629}", basis_for("ES-SCOPE"), True,
        vol, SCOPE_LBT_VOLUME_M3, "m3",
        f"IN SCOPE: L {lwl:.2f} m, B {beam:.2f} m, T {draught:.2f} m "
        f"(L.B.T {vol:.1f} m3). ES-TRIN applies and an inspection body's "
        f"certificate is required."))

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

    # ---- ES-COV: the refusal -------------------------------------------
    # FAILS, always, for an in-scope craft. One chapter of twenty is not an
    # assessment, and a report that passed every finding it happened to
    # implement would read as compliance.
    out.append(RuleFinding(
        "ES-COV", f"{_ESTRIN} (coverage of the standard)",
        basis_for("ES-COV"), False, 1.0, float(len(UNIMPLEMENTED_CHAPTERS) + 1),
        "chapters",
        "IN SCOPE AND NOT ASSESSED. Only Chapter 4 (safety clearance, "
        "freeboard) is implemented. Not implemented: "
        + "; ".join(f"Ch. {c}" for c in UNIMPLEMENTED_CHAPTERS)
        + ". This craft requires an inspection body under Directive (EU) "
          "2016/1629; nothing here substitutes for one."))
    return out
