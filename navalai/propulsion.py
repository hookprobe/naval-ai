"""Propulsion integration: the drive system as a DESIGN-STAGE quantity.

WHY THIS MODULE EXISTS, in the project's own words. The held houseboat16 study
recorded: "15 kW IS NOT EXPRESSIBLE -- there is no motor-power field anywhere
in this codebase -- so declaring 15 kW would be silently dropped and NOTHING
would check it." And the owner found the consequence by eye before any tool
found it by measurement: houseboat19 "looks ok for a paddle boat not for a
motor boat". MEASURED on that hull (2026-08-25): stern immersion 0.33 m,
transom Froude 1.42 at the governed 5 kn and 1.99 at 7 kn against ~2.5 for
clean ventilation, and no check anywhere that a propeller of any diameter
could be fed the power the mission needs. The research record behind every
bar in this file is `docs/research/PROPULSION-INTEGRATION.md`; the headline
source is arXiv 2602.14907 -- hulls optimised WITHOUT the propulsion system
in the loop come out inferior (>8% resistance left on the table).

HOW IT INTEGRATES, and the two contracts it honours:

1. **The reader contract** (Gate V3.0's shape, borrowed deliberately).
   `rows_for(hull, ev, spec)` is a READER of a finished evaluation: it
   computes no hydrostatics and rewrites no field. Its two rows are
   PERMANENT members of `evaluate.CONSTRAINT_NAMES` -- not appended behind
   a flag -- because the owner's product definition (2026-08-25, stated
   twice) is that every NavalAI boat carries an electric motor and solar
   panels: "naval-ai only designs boats with motors." `EnergySpec.motor_kw`
   therefore has a DEFAULT (the original brief's 15 kW), never a None.

2. **A row must be able to fail.** Both rows here are live trade-offs,
   demonstrated on real hulls in `tests/test_propulsion.py`: houseboat19
   with one un-tunnelled prop VIOLATES `prop_space` (D_min 0.42 m against
   0.23 m of usable disc) and the twin-tunnel arrangement the assessment
   drew is exactly what satisfies it. An always-satisfied row occupying an
   NSGA-II dimension is a defect this repo has already shipped once; these
   are not that.

Quantities the ladder does not (yet) measure -- transom ventilation, roll
damping span, pitch entry -- are REPORT fields on `PropulsionReport`, not
constraint rows: an assessment aid, exactly as the rules tier is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .constants import G_STANDARD

# ---------------------------------------------------------------------------
# The bars. Each lives HERE and only here (the number-declared-twice fence in
# tests/test_limits_single_source.py is the enforcement); each names its
# source, because a bar with no provenance is a preference.
# ---------------------------------------------------------------------------

#: Fraction of the installed electric power the CRUISE demand may occupy.
#: Continuous-rating practice for small-craft electric drives: the motor
#: cruises at <= 80% so thermal headroom and station-keeping reserve exist.
MOTOR_CONTINUOUS_FRACTION = 0.80

#: Propeller disc loading (thrust / disc area) above which an unducted
#: small-craft propeller's open-water efficiency has fallen out of the
#: 0.5-0.6 band the flat `EnergySpec.prop_efficiency = 0.55` assumes
#: (Radojcic, Kalajdzic & Simic, "Power Prediction Modeling of Conventional
#: High-Speed Craft", in-tree). Above this bar the 0.55 is a lie, so the
#: design must grow the disc, split it (n_props), or recess a tunnel.
PROP_DISC_LOADING_MAX_PA = 8000.0

#: Tip clearance to the hull above the disc, as a fraction of D: >= 15%,
#: per the tunnel configurations in `galati-romania.pdf` (JMSE 10:1523).
#: Below it the blade-passage pressure pulse couples into the plating —
#: noise and vibration first, cavitation erosion second. P6 makes this an
#: explicitly NAMED bar instead of a number folded silently into the
#: usable-column fraction.
TIP_CLEARANCE_FRACTION = 0.15

#: Grounding / debris margin between the disc and the keel line below.
GROUNDING_MARGIN_FRACTION = 0.15

#: Usable prop diameter as a fraction of the water column at the prop
#: station — DERIVED from the two margins above, never retyped (the value
#: is 0.70, exactly what this constant read before the margins were named).
PROP_IMMERSION_FRACTION = 1.0 - TIP_CLEARANCE_FRACTION - GROUNDING_MARGIN_FRACTION

#: The prop works this fraction of LWL forward of the transom. Far enough
#: forward for a shaft angle under 12 deg to a motor above the WL; far
#: enough aft to clear the run's rise. (SHAFT/TUNNEL station; other
#: architectures override — see DRIVE_LAWS.)
PROP_STATION_FRAC = 0.12

#: THE WAKE-DEFICIT LAYER, and the depth that clears it. MEASURED on the
#: hookprobe campaign (v1, v2 and v3 at 8 kn, three independent hulls,
#: docs/research/HOOKPROBE-CFD-CAMPAIGN.md inflow tables): at 0.2 m below
#: the static waterline the tunnel inflow carries a 16-30% deficit
#: (0.70-0.84 of boat speed); at 0.4 m it arrives at 99-107%. The rule
#: "put the prop axis in the deep layer" is the strongest measured
#: feature-to-flow link in this tree — it REPEATED on all three hulls and
#: survived the v2 fin-TE taper — and until 2026-08-28 it existed only as
#: prose inside a DriveLaw note, where nothing could read it.
#:
#: NONDIMENSIONALISED BY LWL, and the assumption is stated because it is
#: an assumption: the campaign hull is 11.8 m on the waterline, so 0.4 m
#: is 0.0339 Lwl. Scaling a near-surface wake by length is a geometric
#: similarity argument, not a measured scaling law — nobody has run this
#: at a second length. It is therefore a REPORT, never a constraint row:
#: an unmeasured quantity occupying an NSGA-II dimension is a defect this
#: repository has already shipped once.
WAKE_REFERENCE_LWL_M = 11.8
WAKE_DEFICIT_DEPTH_M = 0.20        # 0.70-0.84 U0 here
WAKE_CLEAN_DEPTH_M = 0.40          # 99-107% U0 here
WAKE_CLEAN_DEPTH_FRAC_LWL = WAKE_CLEAN_DEPTH_M / WAKE_REFERENCE_LWL_M


# ---------------------------------------------------------------------------
# Drive architecture (P6, 2026-08-27). The audit's H chain: the propulsion
# rows judged every hull as a conventional shaft drive, so an outboard
# transom-hung leg was charged for a tunnel it cannot have and a protected
# tunnel drive was CREDITED with a below-keel hang it must not take — the
# naval-ai-concept's central protected prop exists precisely to put nothing
# below the keel line. WHERE the disc works and WHICH levers can buy it
# room are properties of the drive, not of the hull, so they live in one
# enum-keyed table and both `assess` and `rows_for` read it. `shaft`
# reproduces the pre-P6 behaviour bit-identically (station 0.12, both
# levers live), which is what keeps every recorded evaluation standing.
# ---------------------------------------------------------------------------

from enum import Enum


class DriveArchitecture(Enum):
    SHAFT = "shaft"          # conventional shaft behind a skeg
    OUTBOARD = "outboard"    # transom-hung leg
    POD = "pod"              # under-hull pod / saildrive
    TUNNEL = "tunnel"        # recessed tunnel, protected prop


@dataclass(frozen=True)
class DriveLaw:
    station_frac: float      # where the disc works, as LWL frac fwd of transom
    allows_recess: bool      # may a tunnel recess buy diameter?
    allows_below_keel: bool  # may the disc hang below the keel line?
    note: str
    #: Has the wake-deficit layer been MEASURED for this stern? Only the
    #: tunnel stern has (hookprobe v1-v3). False means the depth report
    #: is withheld rather than guessed: a transom-hung leg and a pod sit
    #: in different flow, and asserting a tunnel measurement over them is
    #: the "defect measured at a configuration the product never runs"
    #: failure, run backwards.
    wake_anchored: bool = False


DRIVE_LAWS: dict[DriveArchitecture, DriveLaw] = {
    DriveArchitecture.SHAFT: DriveLaw(
        station_frac=PROP_STATION_FRAC, allows_recess=True,
        allows_below_keel=True,
        note="shaft angle <= 12 deg; skeg protects the hang"),
    DriveArchitecture.OUTBOARD: DriveLaw(
        station_frac=0.02, allows_recess=False, allows_below_keel=True,
        note="transom-hung: the leg sets immersion at the transom and no "
             "tunnel exists to recess"),
    DriveArchitecture.POD: DriveLaw(
        station_frac=0.20, allows_recess=False, allows_below_keel=True,
        note="pod/saildrive: the pod IS the hang; a tunnel would defeat "
             "its pulling flow"),
    DriveArchitecture.TUNNEL: DriveLaw(
        station_frac=PROP_STATION_FRAC, allows_recess=True,
        allows_below_keel=False,
        note="protected prop: NOTHING below the keel line — the recess is "
             "the only lever (the naval-ai-concept configuration). "
             "MEASURED inflow receipt (hookprobe v1-v3 @ 8 kn, "
             "docs/research/HOOKPROBE-CFD-CAMPAIGN.md): the tunnel stays "
             "WET (>=0.98 water) and the deep layer arrives at 99-107% of "
             "boat speed at 0.4 m below the static WL, >=0.5 prop "
             "diameters behind the keel tail; the near-surface layer "
             "carries a fin/hull wake deficit (0.70-0.84 U0). Configuration"
             "-specific numbers, not a general bar — but the DESIGN rule "
             "they support is general: put the prop axis in the deep "
             "layer, not under the surface deficit",
        wake_anchored=True),
}


def drive_law(spec) -> tuple[DriveArchitecture, DriveLaw]:
    """The architecture a spec declares, defaulting to SHAFT.

    An UNKNOWN drive string is refused, not defaulted: a spec that says
    'waterjet' and silently gets shaft rows would be measured against the
    wrong stern — the fail-open pattern the mesh receipts taught us about.
    """
    raw = str(getattr(spec, "drive", "shaft") or "shaft").lower()
    try:
        arch = DriveArchitecture(raw)
    except ValueError:
        raise ValueError(
            f"unknown drive architecture {raw!r}; known: "
            f"{[a.value for a in DriveArchitecture]}") from None
    return arch, DRIVE_LAWS[arch]

#: Transom Froude number Fn_T = V / sqrt(g * transom immersion) above which
#: the transom runs cleanly ventilated; below ~2.0 it drags its dead-water
#: eddy. Reported, never a hard row: an immersed transom at displacement
#: speed is a legitimate design choice that costs drag, not an invalid one.
TRANSOM_FN_CLEAN = 2.5

#: Fraction of LWL of SUBMERGED chine needed to mount bilge keels that
#: meaningfully damp roll at 5-7 kn (where active fins, with lift ~ V^2, do
#: nothing). Report field: comfort, not safety.
BILGE_KEEL_MIN_SPAN_FRAC = 0.30

#: PMSM + controller + mount, pack level. Used by mass accounting when a
#: motor is declared; nothing else may restate it.
MOTOR_KG_PER_KW = 3.0


# ---------------------------------------------------------------------------
# Geometry readers. Each takes the FLOATED state (hull + waterline), because
# a propeller does not care about the design draft, only the water it is in.
# ---------------------------------------------------------------------------

def _lwl(hull) -> float:
    """The hull's own station extent — `Hull` carries x, not an lwl field."""
    return float(hull.x[-1] - hull.x[0])


def _keel_z_at(hull, x_frac: float) -> float:
    """Keel depth at a station. `edge_curves` returns (keel, chine, sheer)
    as (n, 3) POINT arrays — x, y, z — not five scalar curves."""
    x = float(hull.x[0]) + float(x_frac) * _lwl(hull)
    keel, _chine, _sheer = hull.edge_curves(np.array([x]))
    return float(keel[0, 2])


def prop_immersion_m(hull, wl: float,
                     station_frac: float = PROP_STATION_FRAC) -> float:
    """Water column available to the disc at the prop station, >= 0.

    The station is the DRIVE's (DRIVE_LAWS), defaulting to the shaft
    station so every existing caller reads the same water it always did."""
    return max(0.0, float(wl) - _keel_z_at(hull, station_frac))


def transom_immersion_m(hull, wl: float) -> float:
    """Transom submergence, >= 0. Zero is a dry (ventilated) transom."""
    return max(0.0, float(wl) - _keel_z_at(hull, 0.02))


def transom_froude(speed_ms: float, immersion_m: float) -> float:
    """Fn_T; +inf for a dry transom, which is the clean case by definition."""
    if immersion_m <= 1e-6:
        return float("inf")
    return float(speed_ms) / math.sqrt(G_STANDARD * immersion_m)


def min_prop_diameter_m(thrust_n: float, n_props: int = 1) -> float:
    """Smallest disc that keeps loading under PROP_DISC_LOADING_MAX_PA."""
    t1 = max(0.0, float(thrust_n)) / max(1, int(n_props))
    return math.sqrt(4.0 * t1 / (math.pi * PROP_DISC_LOADING_MAX_PA))


def max_prop_diameter_m(immersion_m: float, tunnel_recess_m: float = 0.0,
                        below_keel_m: float = 0.0) -> float:
    """Largest disc the stern can swing.

    Three sources of room, all design levers: the water column above the
    keel at the prop station, a tunnel recessed INTO the hull, and — for a
    conventional shaft drive — the hang BELOW the keel line that a skeg
    protects. The first version omitted the third and would have refused
    nearly every ordinary launch afloat (MEASURED on the kit reference hull:
    D_min 0.258 m vs 0.230 m of column — a boat every yard builds daily,
    read as impossible). A row that fires on everything is as dead as one
    that fires on nothing.
    """
    return (PROP_IMMERSION_FRACTION * (max(0.0, immersion_m)
                                       + max(0.0, tunnel_recess_m))
            + max(0.0, below_keel_m))


def prop_axis_depth_m(immersion_m: float,
                      tunnel_recess_m: float = 0.0) -> float:
    """Depth of the disc axis below the static waterline, by CONVENTION.

    The convention, single-sourced here so it cannot be re-derived two
    ways: the disc is centred in the column it is allowed to use, so the
    axis sits at half of (water column at the prop station + any tunnel
    recess). It is a geometric read of the floated surface, tier L0.

    This is deliberately NOT the shallowest admissible axis (tip just
    under the waterline). That reading would report every stern as
    sitting in the deficit layer and a bar that fires on everything is as
    dead as one that fires on nothing — the lesson `max_prop_diameter_m`
    above already paid for.
    """
    return 0.5 * (max(0.0, float(immersion_m))
                  + max(0.0, float(tunnel_recess_m)))


def wake_clean_depth_m(lwl_m: float) -> float:
    """Depth at which the campaign measured clean inflow, scaled by length.

    See WAKE_CLEAN_DEPTH_FRAC_LWL for the measurement and for why the
    length scaling is an assumption rather than a result.
    """
    return WAKE_CLEAN_DEPTH_FRAC_LWL * max(0.0, float(lwl_m))


def axis_clears_wake_deficit(hull, wl: float, law: "DriveLaw",
                             tunnel_recess_m: float = 0.0):
    """Is the prop axis in the deep layer? None when nothing measured it.

    Returns None — not False — for a stern whose wake has never been
    solved. An unmeasured metric reported as a verdict is exactly the
    `${VAR:-0}` failure the CFD receipts taught this project: "I could
    not measure this" must not read as "this is fine", and it must not
    read as "this is broken" either.
    """
    if not getattr(law, "wake_anchored", False):
        return None
    imm = prop_immersion_m(hull, wl, law.station_frac)
    lwl = float(hull.x[-1] - hull.x[0])
    return prop_axis_depth_m(imm, tunnel_recess_m) >= wake_clean_depth_m(lwl)


def wetted_chine_span_frac(hull, wl: float, n: int = 81) -> float:
    """Fraction of LWL where the chine is submerged: bilge-keel real estate.

    The anti-roll device that works at 5-7 kn mounts ON the chine, so the
    span available is a property of the floated geometry -- measured, not
    assumed. (houseboat19: 1.00 -- chine wet stem to stern.)
    """
    x = np.linspace(float(hull.x[0]), float(hull.x[-1]), n)
    _keel, chine, _sheer = hull.edge_curves(x)
    return float(np.mean(chine[:, 2] < wl))


def pitch_entry_report(hull, wl: float) -> tuple[float, float]:
    """(half-entrance angle deg, forefoot drop / midship draft).

    The two geometry levers that set pitch EXCITATION: a fine entry excites
    less; a forefoot deeper than midships (the axe mechanism, `stem_depth`)
    resists bow emergence. Damping devices (stern foil) are arrangement
    items, not hull genes, so they are not read here.
    """
    ae = hull.alpha_e_deg
    ae = float(ae() if callable(ae) else ae)
    t_mid = max(1e-6, float(wl) - _keel_z_at(hull, 0.50))
    drop = (float(wl) - _keel_z_at(hull, 0.98)) / t_mid - 1.0
    return ae, float(drop)


# ---------------------------------------------------------------------------
# The report and the rows.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PropulsionReport:
    """Every quantity carries its provenance: geometry rows are tier L0
    (exact reads of the floated surface, sigma 0 by construction); the two
    power-coupled quantities inherit the resistance tier and RELATIVE sigma,
    because thrust here IS the resistance prediction."""
    demand_kw: float           # electric, at the mission cruise point
    demand_tier: str
    demand_rel_sigma: float
    motor_kw: float | None
    n_props: int
    drive: str                 # DriveArchitecture.value the rows were built for
    tunnel_recess_m: float     # AS APPLIED (zeroed when the drive has no tunnel)
    prop_immersion_m: float    # L0
    d_prop_min_m: float        # from thrust; inherits resistance sigma
    d_prop_max_m: float        # L0
    transom_immersion_m: float  # L0
    transom_fn: float          # at cruise speed
    transom_fn_clean_bar: float
    chine_span_frac: float     # L0
    bilge_keel_min_span_frac: float
    alpha_e_deg: float         # L0
    forefoot_drop_frac: float  # L0; positive = deeper than midships (axe)
    #: The wake-deficit reading (audit P2-15). L0 geometry against a
    #: MEASURED depth; `axis_clears_wake_deficit` is None when this stern
    #: has no anchor, and that is an answer, not a gap.
    prop_axis_depth_m: float
    wake_clean_depth_m: float
    axis_clears_wake_deficit: bool | None


ROW_MOTOR = "motor_power"
ROW_PROP = "prop_space"
ROWS = (ROW_MOTOR, ROW_PROP)


def assess(hull, ev, spec) -> PropulsionReport:
    """The full report, from a FINISHED evaluation. Reader, not a tier."""
    wl = float(ev.wl)
    speed_ms = float(ev.energy.speed)
    arch, law = drive_law(spec)
    imm = prop_immersion_m(hull, wl, law.station_frac)
    recess = (float(getattr(spec, "prop_tunnel_recess_m", 0.0) or 0.0)
              if law.allows_recess else 0.0)
    below = (float(getattr(spec, "prop_max_below_keel_m", 0.0) or 0.0)
             if law.allows_below_keel else 0.0)
    tr_imm = transom_immersion_m(hull, wl)
    thrust = float(ev.resistance.total)
    rel_sigma = (float(ev.resistance.uncertainty) / thrust
                 if thrust > 0 else float("inf"))
    return PropulsionReport(
        demand_kw=float(ev.energy.prop_power_w) / 1000.0,
        demand_tier=str(ev.tier),
        demand_rel_sigma=rel_sigma,
        motor_kw=spec.motor_kw,
        n_props=int(getattr(spec, "n_props", 1) or 1),
        drive=arch.value,
        tunnel_recess_m=recess,
        prop_immersion_m=imm,
        d_prop_min_m=min_prop_diameter_m(thrust,
                                         int(getattr(spec, "n_props", 1) or 1)),
        d_prop_max_m=max_prop_diameter_m(imm, recess, below),
        transom_immersion_m=tr_imm,
        transom_fn=transom_froude(speed_ms, tr_imm),
        transom_fn_clean_bar=TRANSOM_FN_CLEAN,
        chine_span_frac=wetted_chine_span_frac(hull, wl),
        bilge_keel_min_span_frac=BILGE_KEEL_MIN_SPAN_FRAC,
        alpha_e_deg=pitch_entry_report(hull, wl)[0],
        forefoot_drop_frac=pitch_entry_report(hull, wl)[1],
        prop_axis_depth_m=prop_axis_depth_m(imm, recess),
        wake_clean_depth_m=wake_clean_depth_m(
            float(hull.x[-1] - hull.x[0])),
        axis_clears_wake_deficit=axis_clears_wake_deficit(
            hull, wl, law, recess),
    )


def rows_for(hull, wl: float, thrust_n: float, prop_power_w: float,
             spec) -> tuple[dict, dict]:
    """The two constraint rows, evaluate()-convention (<= 0 satisfied).

    Takes PRIMITIVES rather than the finished Evaluation because it is called
    FROM the main constraint assembly, where the Evaluation does not exist
    yet -- these rows are first-class citizens of CONSTRAINT_NAMES, not
    post-hoc appendages (owner's product definition, module docstring).

    `motor_power`: the cruise demand must fit inside the CONTINUOUS rating.
    `prop_space` : the disc the thrust needs must fit the water the stern
                   offers (n_props and tunnel recess are the design levers).
    """
    g, why = {}, {}
    demand_kw = float(prop_power_w) / 1000.0
    n_props = int(getattr(spec, "n_props", 1) or 1)
    arch, law = drive_law(spec)
    # a lever the DRIVE does not have contributes NOTHING, whatever the
    # spec declares — an outboard credited with a tunnel recess, or a
    # protected tunnel drive credited with a below-keel hang, is measured
    # against a stern that does not exist (P6; audit H chain)
    recess = (float(getattr(spec, "prop_tunnel_recess_m", 0.0) or 0.0)
              if law.allows_recess else 0.0)
    below = (float(getattr(spec, "prop_max_below_keel_m", 0.0) or 0.0)
             if law.allows_below_keel else 0.0)
    rated = float(spec.motor_kw) * MOTOR_CONTINUOUS_FRACTION
    g[ROW_MOTOR] = demand_kw / rated - 1.0 if rated > 0 else float("inf")
    if g[ROW_MOTOR] > 0:
        why[ROW_MOTOR] = (
            f"cruise demand {demand_kw:.1f} kW exceeds the continuous "
            f"rating {rated:.1f} kW ({MOTOR_CONTINUOUS_FRACTION:.0%} of the "
            f"declared {spec.motor_kw:.0f} kW motor)")
    imm = prop_immersion_m(hull, wl, law.station_frac)
    d_min = min_prop_diameter_m(thrust_n, n_props)
    d_max = max_prop_diameter_m(imm, recess, below)
    g[ROW_PROP] = (d_min / d_max - 1.0) if d_max > 1e-9 else float("inf")
    if g[ROW_PROP] > 0:
        levers = ["add props"]
        if law.allows_recess:
            levers.append("recess a tunnel")
        if law.allows_below_keel:
            levers.append("allow hang below the keel")
        levers.append("deepen the stern")
        why[ROW_PROP] = (
            f"the thrust needs a {d_min:.2f} m disc ({n_props} prop(s) at "
            f"<= {PROP_DISC_LOADING_MAX_PA:.0f} Pa loading) but the "
            f"{arch.value} stern offers {d_max:.2f} m ({imm:.2f} m "
            f"immersion + {recess:.2f} m tunnel recess + {below:.2f} m "
            f"below-keel hang); " + ", ".join(levers))
    return g, why
