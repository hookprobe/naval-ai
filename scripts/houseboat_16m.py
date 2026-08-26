"""A 16 m x 4 m electric liveaboard houseboat, generated and VALIDATED.

    python scripts/houseboat_16m.py --out data/exports/houseboat16

THE BRIEF, as received: 16 m x 4 m x 3 m, 3 tonne displacement, 100 kWh
battery, 15 kW motor, 7-12 knots, full liveaboard accommodation (living room,
terrace, bathroom, kitchen).

THREE OF THOSE NUMBERS DO NOT SURVIVE CONTACT WITH THE LADDER, AND THIS SCRIPT
MEASURES IT RATHER THAN ASSERTING IT -- the point of the ladder is that a
refusal is a RESULT.

1. **3 TONNES IS NOT A DISPLACEMENT THIS HULL CAN HAVE.** `grammar.B_OVER_T_BAND`
   is (1.8, 12.0). At BWL 4.0 m that band forces T >= 0.333 m, and a 15.2 m
   waterline at that draft floats 9-13 t depending on Cb. 3000 kg floats at
   T ~= 0.09 m, i.e. B/T ~= 44 -- nearly 4x outside the ceiling. `evaluate`
   re-applies `proportion_margins` to the FLOATED state (gap B9), so this is a
   real violation of the `proportions` row and not merely a design-draft one.
   The repo's own mass model agrees from the other side: `energy.BATT_KG_PER_KWH`
   is 7.5, so the 100 kWh pack ALONE is 750 kg, and `OUTFIT_KG_PER_M` 55 over
   16 m is another 880 kg before any structure exists.

2. **12 KNOTS IS OUTSIDE THE RESISTANCE MODEL, NOT MERELY EXPENSIVE.**
   `resistance.FN_MICHELL_MAX` is 0.45; at LWL 15.2 m that is 10.68 kn. At
   12 kn the Michell integral returns `valid=False`, the badge degrades to
   `L1-INVALID` (which `tier_rank` ranks BELOW L0) and the Wh/NM sigma widens
   to 100% of the answer. The displacement hull speed here is 9.4 kn. 7 kn is
   Fn 0.297 and is the speed the boat actually has.

3. **15 kW IS NOT EXPRESSIBLE.** There is no motor-power field anywhere in this
   codebase -- `EnergySpec` carries `motor_efficiency` and nothing else -- so
   declaring 15 kW would be silently dropped and NOTHING would check it. This
   script therefore checks it EXTERNALLY, against `EnergyReport.prop_power_w`,
   and reports the speed at which the 15 kW is actually exhausted.

So the deliverable is TWO designs:

    AS_ASKED    the brief verbatim -> expected REFUSAL, with the refusing
                constraint named and measured
    CORRECTED   the same 16 x 4 m envelope at a displacement the band admits
                -> validated, certified, exported to STL, and laid out

WHY THE HULL `D` IS 1.55 AND NOT THE 3.0 THE BRIEF SAYS. `grammar.PARAMS`
defines D as "depth, keel to sheer AT THE MAX-AREA STATION" -- the HULL, not
the air draft. The brief's 3 m is overall height, which on a houseboat is hull
depth plus a deckhouse. Modelling 3 m as hull depth would draw a 16 m hull with
a 3 m deep canoe body and no cabin at all. The hull carries 1.55 m and the
remaining ~1.45 m is the trunk/deckhouse, which is where standing headroom
lives and which `arrangement.Trunk` models explicitly. `parse_mission`'s
`_DENY_LENGTH` already refuses to read "3 m height" as a length, so this
reading is the grammar's and not this script's.

WHY THIS RUNS UNGOVERNED. `policy.reference_policy()` compiles the KIT_LINE_V3
constitution, whose `max_hull_length_m` is 11.9 m; it would refuse a 16 m hull
before any physics ran, and it would refuse it for a COMMERCIAL reason (the
RCD Art. 20 Module A break at 12 m) rather than a physical one. A 16 m boat
needs a different constitution, and writing one is a decision for the owner,
not for this script. So `policy=None` throughout, and every number here is
therefore an ENGINEERING result and NOT a compliance verdict.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from navalai import grammar
from navalai.certify import certify
from navalai.cfd.case import hull_to_stl
from navalai.energy import BATT_KG_PER_KWH, EnergySpec, energy_report
from navalai.evaluate import CONSTRAINT_NAMES, evaluate
from navalai.geometry import GeometryError, Hull
from navalai.hydrostatics import solve
from navalai.mission import Manning, MissionSpec, VesselConfig
from navalai.reference import REFERENCE_HULL
from navalai.constants import G_STANDARD, RHO_FRESH
from navalai.resistance import FN_MICHELL_MAX, total_resistance


LOA_M = 16.0
LWL_M = 15.2                # 16.0 LOA less a raked stem and an immersed transom
BWL_M = 4.0
D_HULL_M = 1.55             # keel to sheer; see the module docstring
AIR_HEIGHT_M = 3.0          # the brief's "3 m" = hull depth + deckhouse
TRUNK_HEIGHT_M = AIR_HEIGHT_M - D_HULL_M

BATTERY_KWH = 100.0
MOTOR_KW = 15.0             # NOT expressible in EnergySpec; checked externally
CRUISE_KN = 7.0
DASH_KN = 12.0              # the brief's upper speed; MEASURED, not designed to
CREW = 4

# Clearance held off the interior skin: framing, ceiling battens and the
# linings that `Envelope.from_hull` explicitly does NOT deduct (it takes off
# panel thickness and nothing else).
_Y_MARGIN = 0.06

# The displacement the CORRECTED design is floated to. It is not a round number
# picked to look plausible: it is the lightest whole tonne that puts B/T inside
# `grammar.B_OVER_T_BAND` with margin AND covers the mass model's own fixed
# items (750 kg of battery at BATT_KG_PER_KWH, 880 kg of outfit at
# OUTFIT_KG_PER_M x 16 m, the crew provision, and a 16 x 4 m plywood shell).
CORRECTED_KG = 14_000.0
AS_ASKED_KG = 3_000.0

# The barge-form deltas from the reference liveaboard genome. `REFERENCE_HULL`
# is the ONE home of a genome vector in this tree (CLAUDE.md rule 3), so this
# is expressed as an override of it and not as a fresh transcription.
_BARGE = {
    "LWL": LWL_M,
    "BWL": BWL_M,
    "D": D_HULL_M,
    # A BARGE, AT LAST. Until 2026-08-23 these three lines were impossible:
    # `r_stem` did not exist (the SAC ended at a hardcoded zero, so the bow was
    # always a point), `r_transom` was capped at 0.50 (a full transom was
    # unreachable by construction) and `Cp` was capped at 0.710 by the
    # resistance-optimal table (the full ends of a box reach Cp 0.831 at the
    # LOWEST, so the kernel refused with "Cp 0.7100 unreachable"). Three
    # independent bounds each forbade a houseboat.
    #
    # MEASURED on this 16.0 x 4.0 m hull at 14 t, before and after:
    #
    #                        % of length at    deck      stern    bow
    #                        >= 90% beam       area      beam     beam
    #     before                 39%          43.6 m2    1.96 m   0.00 m
    #     after                  88%          59.4 m2    4.22 m   1.50 m
    #     a 16x4 rectangle      100%          64.0 m2    4.00 m   4.00 m
    #
    # 93% of a rectangle's deck, against 68%. THIS is the boat the brief asked
    # for, and the cost is paid in drag, measured and reported in `main()`.
    # 0.55 AND NOT 0.40, AND THE REASON IS COUNTERINTUITIVE ENOUGH TO RECORD.
    # At r_stem 0.40 the delivered STL had a visibly cut-off bow, and it was
    # not cosmetic: MEASURED half-entrance angle 36.1 deg (a fine bow is under
    # 20) with 1.38 m of beam still on the WATERLINE at the stem — a square
    # end pushing water. Asking for MORE stem area, not less, fixed it: the
    # SAC solver redistributes and the entry becomes a smoother wedge.
    #
    #     r_stem   alpha_e   WL beam at stem   deck m2   kW @ 7 kn   max kn
    #      0.40     36.1 deg      1.38 m        59.4       12.3       7.50
    #      0.55     22.1 deg      2.14 m        59.0        9.0       8.29
    #
    # Same deck area, 27% less power, 0.8 kn more speed. The bluff bow was
    # costing 3.3 kW and nothing in the ladder said so — `Hull.alpha_e_deg`
    # exists and is computed, but NO gate reads it, so a bow this blunt passes
    # L0, L1, all seven rules and certification in silence.
    "r_stem": 0.55,
    "r_transom": 0.92,
    "Cp": 0.92,
    # -2.5 AND NOT -1.5, AND THIS IS THE ONE THAT MADE IT LOOK LIKE A BOAT.
    # Rendering the STL (which nobody had done) showed a WASP WAIST in plan:
    # 4.22 m at the transom, pinching to 3.76 m at 20% of the length, then
    # swelling back to 4.33 m. A hull wider at the transom than at the
    # sections beside it is not a shape anyone draws on purpose. MEASURED as
    # the plan's largest dip below a monotone rise to maximum beam:
    #
    #     lcb      waist     alpha_e   deck m2
    #     -1.5     10.5%     21.9 deg   59.2
    #     -2.5      1.0%     14.8 deg   59.3
    #
    # Same deck area, the waist gone and the entry finer. Moving the target
    # LCB aft lets the SAC fall away smoothly from a nearly full transom
    # instead of dipping and recovering.
    "lcb": -2.5,
    "x_mb": 0.40,
    "beta_mid": 8.0,    # nearly flat bottom: shallow draft and deck area
    "beta_bow": 10.0,
    "beta_len": 0.45,
    "roundness": 0.0,   # HARD CHINE -> the sheet-developable kit path
    "rocker": 0.05,
    "forefoot": 0.10,
    "flare": 6.0,
    # 0.50, not 0.12. The PROFILE view of the rendered STL was a flat slab of
    # constant depth -- 0.186 m of sheer rise over a 16 m hull is invisible,
    # and every reference form in downloads/hull-examples has a sheer sweeping
    # up to the bow. 0.50 gives 0.775 m.
    "sheer_rise": 0.50,
}


def base_genome(T: float) -> dict[str, float]:
    """The 16 x 4 m barge-form liveaboard, parameterised on draft alone.

    Everything except T is held FIXED across the two designs, so the ONLY
    difference between AS_ASKED and CORRECTED is the displacement -- which is
    the question actually being asked.
    """
    return dict(REFERENCE_HULL, **_BARGE, T=T)


class Unreachable(ValueError):
    """The envelope cannot float the asked-for weight AT ALL.

    Distinguished from a constraint violation on purpose: a hull that floats
    but breaks a band is a DESIGN that fails, and a hull the section solver
    will not build is a design that DOES NOT EXIST. The brief's 3 t is the
    second kind, and reporting it as the first would overstate how close it is.
    """


def feasible_draft_floor(rho: float = RHO_FRESH, lo: float = 0.05,
                         hi: float = 1.9) -> float:
    """The shallowest draft at which this 16 x 4 m form BUILDS.

    Below it `geometry._stations` raises -- the SAC demands a forward section
    area that a hull this shallow cannot deliver at any deadrise the genome
    allows. That floor, not the B/T band, is the binding constraint on the
    brief's 3 t, so it is measured rather than assumed.
    """
    def builds(T: float) -> bool:
        try:
            Hull(grammar.vector(base_genome(T)))
            return True
        except GeometryError:
            return False

    if not builds(hi):
        raise RuntimeError(f"the form does not build even at T={hi} m")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if builds(mid):
            hi = mid
        else:
            lo = mid
    return hi


def design_draft_for(target_kg: float, rho: float = RHO_FRESH
                     ) -> tuple[float, float]:
    """Bisect the genome's T so the hull floats at `target_kg` ON ITS DESIGN
    WATERLINE (wl = 0).

    A design stated as a weight has to be inverted through the hydrostatics
    rather than assumed. Raises `Unreachable` when the weight is below what the
    shallowest BUILDABLE member of the family displaces -- which is the brief's
    case, and is a stronger refusal than a violated band.
    """
    def disp(T: float) -> float:
        return float(solve(Hull(grammar.vector(base_genome(T))),
                           rho=rho, wl=0.0).disp_kg)

    lo = feasible_draft_floor(rho)
    hi = 1.9
    d_lo = disp(lo)
    if target_kg < d_lo:
        raise Unreachable(
            f"{target_kg:.0f} kg is below the lightest BUILDABLE member of this "
            f"16.0 x 4.0 m family: T_min = {lo:.3f} m displaces {d_lo:.0f} kg")
    if disp(hi) < target_kg:
        raise Unreachable(f"{target_kg:.0f} kg is beyond the envelope at T={hi} m")
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        if disp(mid) < target_kg:
            lo = mid
        else:
            hi = mid
    T = 0.5 * (lo + hi)
    return T, disp(T)


def make_mission(target_kg: float, name: str) -> MissionSpec:
    """The mission both designs are judged against.

    `waters` carries the literal token "river"/"canal"/"inland" because
    `evaluate` triggers the ES-TRIN inland-vessel checkers on exactly that
    vocabulary (evaluate.py, the C-23 wire); manning is LIVEABOARD because that
    is what selects ISO 12217-1's habitability bars. NEITHER survives prose
    parsing -- `parse_mission` puts the design CATEGORY in `waters` and leaves
    manning CREWED -- so both are set structurally here.
    """
    return MissionSpec(
        name=name,
        lwl_hint_m=LWL_M,
        displacement_target_kg=target_kg,
        cruise_speed_kn=CRUISE_KN,
        design_category="D",                 # sheltered inland waters
        crew=CREW,
        waters="river+canal+inland",
        energy=EnergySpec(battery_kwh=BATTERY_KWH),
        vessel=VesselConfig(manning=Manning.LIVEABOARD),
    )


def power_at(hull: Hull, ev, spec: EnergySpec, knots: float,
             rho: float = RHO_FRESH) -> dict:
    """Electrical power and validity at `knots`, judged against the 15 kW.

    `EnergySpec` HAS NO MOTOR FIELD, so the installed 15 kW cannot be declared
    to the ladder and nothing inside it would ever check the boat can reach the
    asked-for speed. The check is therefore made here, explicitly, against
    `EnergyReport.prop_power_w` -- and the model's OWN validity flag is carried
    out with it, because above `FN_MICHELL_MAX` the number is not just large,
    it is not a number this project stands behind.
    """
    hs = ev.hydro
    v = knots * 0.514444
    res = total_resistance(
        hull, v, wetted=hs.wetted, cb=hs.cb, rho=rho, wl=ev.wl,
        beam_wl=hs.b_wl_max, draft=hs.draft, lwl_eff=hs.lwl_eff)
    rep = energy_report(res.total, v, hull.deck_area(), spec,
                        resistance_sigma_n=res.uncertainty)
    kw = rep.prop_power_w / 1000.0
    return {
        "knots": knots,
        "fn": res.fn,
        "resistance_n": res.total,
        "electrical_kw": kw,
        "model_valid": bool(res.valid),
        "within_15kw": bool(kw <= MOTOR_KW),
        "wh_per_nm": rep.wh_per_nm,
        "range_battery_nm": rep.range_battery_nm,
        "headroom_kw": MOTOR_KW - kw,
    }


def max_speed_on(hull: Hull, ev, spec: EnergySpec, cap_kw: float,
                 rho: float = RHO_FRESH) -> float:
    """The fastest speed the installed `cap_kw` actually reaches.

    Bisected on the electrical power curve, and CLAMPED at the Michell
    validity ceiling: reporting a speed the resistance model does not stand
    behind would be exactly the "confident wrong answer" this repo keeps
    finding in its own history.
    """
    v_max_valid = FN_MICHELL_MAX * math.sqrt(G_STANDARD * ev.hydro.lwl_eff) / 0.514444
    lo, hi = 1.0, v_max_valid
    if power_at(hull, ev, spec, lo, rho)["electrical_kw"] > cap_kw:
        return float("nan")
    if power_at(hull, ev, spec, hi, rho)["electrical_kw"] <= cap_kw:
        return hi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if power_at(hull, ev, spec, mid, rho)["electrical_kw"] <= cap_kw:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def houseboat_layout(hull: Hull, ev) -> "tuple":
    """The brief's accommodation, as an `arrangement` AST the L0-A gate reads.

    The brief asks for living, terrace, bathroom, kitchen. Mapped onto
    `arrangement.Function`, which is the vocabulary the gate actually has:

        living room  -> SALOON        kitchen  -> GALLEY
        bathroom     -> HEAD          cabin    -> BERTH
        terrace      -> DeckKind.AFTDECK   (see the caveat below)

    NOTHING HERE IS A CHOSEN DIMENSION; EVERY ONE IS DERIVED FROM THE HULL OR
    FROM A BAR IN `arrangement`. Three successive L0-A refusals put it that way,
    and each is worth recording because each is a fact about this hull:

    1. A fixed 1.45 m half-breadth for every cabin: refused four times --
       "berth.fwd reaches y=1.450 m ... where 0.671 m half-breadth is
       available". This hull carries beam only amidships (2.00 m half-breadth
       at x = 7.5 m) and narrows to 0.67-0.72 m at both ends, because the SAC
       kernel caps `l_pmb` at 0.30. Boxes now ask the envelope.
    2. Sizing a full-height room at the SOLE's half-breadth: refused for head
       and galley -- their CEILING is inside the deckhouse, which is narrower
       than the hull. A room that reaches `top` is capped by the trunk.
    3. Choosing the trunk width: `min_deck_half_breadth` over the cabin span is
       1.070 m and ISO 15085's side-deck floor (via `deck_min_width_m`, cat D)
       is 0.10 m, so a 1.55 m trunk left a NEGATIVE side deck and L0-A caught
       it as `L0A-DEGENERATE ... dy=-0.540 m`. The trunk half-width is now
       whatever the deck has left after the side deck is paid for.

    ONE double cabin and not two: `min_dims_m(Function.BERTH)` sets a 1.98 m
    floor on the longer plan dimension, and two berths plus head, galley and
    saloon do not fit in the 8.4 m of deckhouse this hull supports. The saloon
    is the second sleeping place, which is what a houseboat actually does.

    THE TERRACE GETS NO DIMENSIONAL BAR, AND THAT IS A REAL GAP, NOT AN
    OVERSIGHT HERE. `deck_min_width_m` returns None for AFTDECK and FOREDECK --
    no source in this tree holds a width floor for open deck -- so the terrace
    is checked for overlap, for staying inside the plan and clear of the trunk,
    and for nothing else. It is reported as unbounded rather than quietly passed.

    `reference_layout()` is NOT reused: it is the hand-authored 10 m
    Solar-Liveaboard and it raises on a hull too bluff to carry its V-berth,
    which is exactly what a 16 m barge bow is.
    """
    from navalai.arrangement import (Arrangement, Box, DeckKind, DeckZone,
                                     DeckZone as _DZ, Envelope, Function,
                                     PlanBox, Space, Trunk, Zone,
                                     deck_min_width_m)

    cab_x0, cab_x1 = 4.0, 12.4          # the deckhouse footprint
    probe = Envelope.from_hull(hull, trunk=Trunk(cab_x0, cab_x1, 1.0,
                                                 TRUNK_HEIGHT_M))
    side_bar = deck_min_width_m(DeckKind.SIDE_DECK, "D")[0]
    deck_half = probe.min_deck_half_breadth(cab_x0, cab_x1)
    trunk_half = deck_half - side_bar - _Y_MARGIN

    trunk = Trunk(x0=cab_x0, x1=cab_x1, half_width=trunk_half,
                  height=TRUNK_HEIGHT_M)
    env = Envelope.from_hull(hull, trunk=trunk)
    sole = env.sole_z
    top = sole + 2.05                    # standing headroom inside the trunk

    def room(sid, func, x0, x1, z0, z1, mass, sigma, in_trunk=True):
        """A space sized by what the hull -- and the deckhouse -- actually offer."""
        y = env.min_half_breadth(x0, x1, z0) - _Y_MARGIN
        if in_trunk:
            y = min(y, trunk_half - _Y_MARGIN)
        y = max(0.30, y)
        return Space(sid, func, Box(x0, x1, -y, y, z0, z1),
                     mass_kg=mass, sigma_kg=sigma)

    spaces = (
        room("machinery.aft", Function.MACHINERY, 1.0, 3.6, sole, sole + 1.10,
             970.0, 97.0, in_trunk=False),
        room("berth.aft", Function.BERTH, 4.0, 6.2, sole, top, 320.0, 32.0),
        room("head", Function.HEAD, 6.2, 7.6, sole, top, 260.0, 26.0),
        room("galley", Function.GALLEY, 7.6, 9.2, sole, top, 430.0, 43.0),
        room("saloon", Function.SALOON, 9.2, 12.4, sole, top, 520.0, 52.0),
        room("stowage.fwd", Function.STOWAGE, 12.8, 14.2, sole, sole + 1.20,
             180.0, 18.0, in_trunk=False),
    )

    def deck(did, kind, zone, x0, x1, y0, y1, mass=0.0, sigma=0.0):
        return DeckZone(did, kind, zone, PlanBox(x0, x1, y0, y1),
                        barrier_height_mm=1000, mass_kg=mass, sigma_kg=sigma)

    aft_half = max(0.25, probe.min_deck_half_breadth(0.6, 3.6) - _Y_MARGIN)
    fwd_half = max(0.25, probe.min_deck_half_breadth(12.8, 14.6) - _Y_MARGIN)
    decks = (
        # THE TERRACE. Aft of the deckhouse, full beam, open.
        deck("terrace.aft", DeckKind.AFTDECK, Zone.Z1, 0.6, 3.6,
             -aft_half, aft_half, mass=140.0, sigma=14.0),
        deck("sidedeck.p", DeckKind.SIDE_DECK, Zone.Z2, cab_x0, cab_x1,
             -deck_half, -trunk_half),
        deck("sidedeck.s", DeckKind.SIDE_DECK, Zone.Z2, cab_x0, cab_x1,
             trunk_half, deck_half),
        deck("foredeck", DeckKind.FOREDECK, Zone.Z3, 12.8, 14.6,
             -fwd_half, fwd_half),
    )
    return Arrangement(envelope=env, spaces=spaces, deck_zones=decks,
                       category="D"), trunk


def _g_table(ev) -> list[dict]:
    """`Evaluation.g` as rows, in the order `CONSTRAINT_NAMES` declares.

    Read from `ev.g_names` and not from the module constant, because a policy
    may APPEND rows and the appended ones are exactly the ones a reader would
    otherwise miss.
    """
    names = ev.g_names or CONSTRAINT_NAMES
    return [{"constraint": n,
             "g": (None if ev.g.get(n) is None else float(ev.g[n])),
             "ok": bool(ev.g.get(n) is not None and ev.g[n] <= 0.0)}
            for n in names]


def main() -> int:
    ap = argparse.ArgumentParser("houseboat_16m")
    ap.add_argument("--out", default="data/exports/houseboat16")
    ap.add_argument("--nx", type=int, default=241,
                    help="STL longitudinal stations; 241 = 1 + 1.5*(161-1) so "
                         "the loft grid divides evenly (see hull_to_stl)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "brief": {
            "loa_m": LOA_M, "beam_m": BWL_M, "height_m": AIR_HEIGHT_M,
            "displacement_kg": AS_ASKED_KG, "battery_kwh": BATTERY_KWH,
            "motor_kw": MOTOR_KW, "speed_kn": [CRUISE_KN, DASH_KN],
            "accommodation": ["living room", "terrace", "bathroom", "kitchen"],
        },
        "governance": "UNGOVERNED (policy=None). reference_policy() caps "
                      "max_hull_length_m at 11.9 m and would refuse 16 m for a "
                      "commercial reason before any physics ran. These are "
                      "ENGINEERING results, NOT a compliance verdict.",
        "bands": {"L_over_B": list(grammar.L_OVER_B_BAND),
                  "B_over_T": list(grammar.B_OVER_T_BAND),
                  "fn_michell_max": FN_MICHELL_MAX},
    }

    # ---- 1. the brief's 3 t, put through the SAME gates ------------------
    #
    # THIS SECTION CHANGED ITS ANSWER ONCE, AND THE FIRST ANSWER IS RECORDED
    # BECAUSE IT WAS WRONG IN AN INSTRUCTIVE WAY. With `l_pmb` at 0.30 the
    # section solver refused every draft below 0.316 m, so 3 t came back
    # "UNREACHABLE -- the lightest BUILDABLE member displaces 7465 kg". That
    # was TRUE OF THAT FORM AND NOT OF THE BRIEF. Taking l_pmb to 0.0 for
    # resistance reasons (see `_BARGE`) also opened the shallow end, and 3 t
    # now builds. The refusal is real either way, but it is a PROPORTION
    # refusal, not an existence one, and reporting the stronger claim would
    # have overstated the case. Ask the gate, not the last run.
    floor_T = feasible_draft_floor()
    floor_disp = float(solve(Hull(grammar.vector(base_genome(floor_T))),
                             rho=RHO_FRESH, wl=0.0).disp_kg)
    as_asked: dict = {"lightest_buildable_kg": floor_disp,
                      "lightest_buildable_draft_m": floor_T,
                      "asked_kg": AS_ASKED_KG}
    try:
        T_a, d_a = design_draft_for(AS_ASKED_KG)
        x_a = grammar.vector(base_genome(T_a))
        rep_a = grammar.check(x_a)
        ev_a = evaluate(x_a, make_mission(AS_ASKED_KG, "16 m at the brief's 3 t"),
                        rho=RHO_FRESH)
        as_asked.update({
            "buildable": True, "draft_m": T_a, "b_over_t": BWL_M / T_a,
            "b_over_t_ceiling": grammar.B_OVER_T_BAND[1],
            "l0_gate_ok": bool(rep_a.ok),
            "l0_violations": [str(v) for v in getattr(rep_a, "violations", ())],
            "evaluation_ok": bool(ev_a.ok),
            "violations": list(ev_a.violations),
            "constraints": _g_table(ev_a),
        })
        print(f"[1] the brief's {AS_ASKED_KG:.0f} kg: BUILDS at T = {T_a:.3f} m, "
              f"B/T = {BWL_M / T_a:.1f} against a ceiling of "
              f"{grammar.B_OVER_T_BAND[1]:.1f}")
        print(f"    L0 gate ok = {rep_a.ok}; ladder ok = {ev_a.ok}")
        for v in list(rep_a.violations)[:6]:
            print(f"      L0: {v}")
        for v in list(ev_a.violations)[:6]:
            print(f"      L1: {v}")
    except Unreachable as e:
        as_asked.update({"buildable": False, "refusal": str(e),
                         "shortfall_factor": floor_disp / AS_ASKED_KG})
        print(f"[1] the brief's {AS_ASKED_KG:.0f} kg: UNREACHABLE -- {e}")
    report["as_asked"] = as_asked

    # ---- 2. the CORRECTED hull --------------------------------------------
    T, disp = design_draft_for(CORRECTED_KG)
    genome = base_genome(T)
    x = grammar.vector(genome)
    hull = Hull(x)
    rep = grammar.check(x)
    print(f"[2] CORRECTED: T = {T:.3f} m, floats {disp:.0f} kg, "
          f"B/T = {BWL_M / T:.2f}; L0 gate ok = {rep.ok}")
    report["corrected_genome"] = genome
    report["l0_gate"] = {"ok": bool(rep.ok),
                         "violations": [str(v) for v in getattr(rep, "violations", ())]}

    mission = make_mission(CORRECTED_KG, "16 m inland electric liveaboard")
    ev = evaluate(x, mission, rho=RHO_FRESH)
    print(f"    ladder: ok = {ev.ok}, tier = {ev.tier}, "
          f"violations = {list(ev.violations)}")
    # THE BOW IS REPORTED BECAUSE NOTHING GATES IT. `Hull.alpha_e_deg` is
    # computed by the kernel and read by NO constraint row, no rule and no
    # badge, so a half-entrance angle of 36.1 deg -- a square end pushing
    # water, measured on this very hull on 2026-08-23 -- passed L0, L1, all
    # seven rules and certification in silence. It cost 3.3 kW at 7 kn and
    # 0.8 kn of top speed. Until there is a gate, it is at least PRINTED.
    _alpha_e = hull.alpha_e_deg()
    report["bow"] = {
        "half_entrance_angle_deg": _alpha_e,
        "waterline_beam_at_stem_m": float(2.0 * hull.y_wl[-1]),
        "gated": False,
        "note": ("alpha_e < 20 deg is a fine entry, > 40 deg is bluff. "
                 "NOTHING IN THE LADDER CHECKS THIS."),
    }
    print(f"    bow: half-entrance angle {_alpha_e:.1f} deg "
          f"({'fine' if _alpha_e < 20 else 'moderate' if _alpha_e < 30 else 'BLUFF'}), "
          f"waterline beam at stem {2.0 * hull.y_wl[-1]:.2f} m -- UNGATED")
    report["corrected"] = {
        "draft_m": T, "displacement_kg": disp, "b_over_t": BWL_M / T,
        "evaluation_ok": bool(ev.ok), "tier": ev.tier,
        "violations": list(ev.violations),
        "constraints": _g_table(ev),
        "gm_m": ev.gm_m, "trim_deg": ev.trim_deg, "list_deg": ev.list_deg,
        "wl_m": ev.wl,
        "hydro": {"draft": ev.hydro.draft, "disp_kg": ev.hydro.disp_kg,
                  "cb": ev.hydro.cb, "cp": ev.hydro.cp, "awp": ev.hydro.awp,
                  "lcb_pct_lwl": ev.hydro.lcb_pct_lwl,
                  "freeboard_min": ev.hydro.freeboard_min,
                  "wetted": ev.hydro.wetted},
        "ply_thickness_m": ev.ply_thickness_m,
        "badges": {k: [v[0], v[1], v[2]] for k, v in (ev.badges or {}).items()},
        "rules": ev.rules,
    }

    # ---- 3. the 15 kW, checked from outside the ladder ---------------------
    speeds = [power_at(hull, ev, mission.energy, kn) for kn in (5.0, CRUISE_KN, 9.0, DASH_KN)]
    v_cap = max_speed_on(hull, ev, mission.energy, MOTOR_KW)
    for s in speeds:
        flag = "" if s["model_valid"] else "  <- OUTSIDE THE MODEL (Fn > 0.45)"
        print(f"    {s['knots']:5.1f} kn  Fn {s['fn']:.3f}  "
              f"{s['electrical_kw']:7.1f} kW electrical  "
              f"{'within' if s['within_15kw'] else 'OVER'} 15 kW{flag}")
    print(f"    max speed on {MOTOR_KW:.0f} kW = {v_cap:.2f} kn")
    report["propulsion"] = {"points": speeds, "max_speed_on_15kw_kn": v_cap,
                            "motor_kw_is_expressible": False,
                            "note": "EnergySpec has no motor-power field; the "
                                    "15 kW is checked here, not by the ladder."}

    # ---- 4. accommodation --------------------------------------------------
    from navalai.arrangement import check_l0a
    arr, trunk = houseboat_layout(hull, ev)
    l0a = check_l0a(arr)
    print(f"[4] L0-A arrangement gate: ok = {l0a.ok}")
    for m in (l0a.messages if not l0a.ok else [])[:12]:
        print(f"      {m}")
    report["arrangement"] = {
        "ok": bool(l0a.ok),
        "violations": [str(m) for m in l0a.messages],
        "trunk": {"x0": trunk.x0, "x1": trunk.x1,
                  "half_width": trunk.half_width, "height": trunk.height},
        "interior_volume_m3": arr.envelope.interior_volume_m3,
        "interior_volume_used_m3": arr.interior_volume_used_m3,
        "deck_area_m2": arr.envelope.deck_area_m2,
        "spaces": [{"id": s.id, "function": s.function.value,
                    "plan_long_m": s.box.plan_long, "plan_short_m": s.box.plan_short,
                    "height_m": s.box.dz, "mass_kg": s.mass_kg}
                   for s in arr.spaces],
        "deck_zones": [{"id": d.id, "kind": d.kind.value, "zone": d.zone.value}
                       for d in arr.deck_zones],
    }

    # ---- 5. certification and geometry ------------------------------------
    cert = certify(x, mission)
    print(f"[5] certification verdict: {cert.verdict}")
    report["certification"] = {
        "verdict": cert.verdict, "genome_sha256": cert.genome_sha256,
        "regime": str(cert.regime), "regime_supported": bool(cert.regime_supported),
        "reasons": list(cert.reasons), "violations": list(cert.violations),
        "assumptions": list(cert.assumptions),
    }

    stl = out / "houseboat16.stl"
    sha = hull_to_stl(hull, stl, nx=a.nx, wl=ev.wl)
    size_mb = stl.stat().st_size / 1e6
    print(f"[6] STL: {stl}  ({size_mb:.1f} MB, sha256 {sha[:16]}...)")
    report["stl"] = {"path": str(stl), "sha256": sha, "megabytes": size_mb,
                     "nx": a.nx, "wl_m": ev.wl}

    (out / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print(f"    report: {out / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
