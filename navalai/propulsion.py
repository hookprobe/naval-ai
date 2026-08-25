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

#: Usable prop diameter as a fraction of the water column at the prop
#: station: tip clearance to the hull above (>= 15% D, per the tunnel
#: configurations in `galati-romania.pdf`, JMSE 10:1523) plus grounding
#: margin below.
PROP_IMMERSION_FRACTION = 0.70

#: The prop works this fraction of LWL forward of the transom. Far enough
#: forward for a shaft angle under 12 deg to a motor above the WL; far
#: enough aft to clear the run's rise.
PROP_STATION_FRAC = 0.12

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


def prop_immersion_m(hull, wl: float) -> float:
    """Water column available to the disc at the prop station, >= 0."""
    return max(0.0, float(wl) - _keel_z_at(hull, PROP_STATION_FRAC))


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
    tunnel_recess_m: float
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


ROW_MOTOR = "motor_power"
ROW_PROP = "prop_space"
ROWS = (ROW_MOTOR, ROW_PROP)


def assess(hull, ev, spec) -> PropulsionReport:
    """The full report, from a FINISHED evaluation. Reader, not a tier."""
    wl = float(ev.wl)
    speed_ms = float(ev.energy.speed)
    imm = prop_immersion_m(hull, wl)
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
        tunnel_recess_m=float(getattr(spec, "prop_tunnel_recess_m", 0.0) or 0.0),
        prop_immersion_m=imm,
        d_prop_min_m=min_prop_diameter_m(thrust,
                                         int(getattr(spec, "n_props", 1) or 1)),
        d_prop_max_m=max_prop_diameter_m(
            imm, float(getattr(spec, "prop_tunnel_recess_m", 0.0) or 0.0),
            float(getattr(spec, "prop_max_below_keel_m", 0.0) or 0.0)),
        transom_immersion_m=tr_imm,
        transom_fn=transom_froude(speed_ms, tr_imm),
        transom_fn_clean_bar=TRANSOM_FN_CLEAN,
        chine_span_frac=wetted_chine_span_frac(hull, wl),
        bilge_keel_min_span_frac=BILGE_KEEL_MIN_SPAN_FRAC,
        alpha_e_deg=pitch_entry_report(hull, wl)[0],
        forefoot_drop_frac=pitch_entry_report(hull, wl)[1],
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
    recess = float(getattr(spec, "prop_tunnel_recess_m", 0.0) or 0.0)
    rated = float(spec.motor_kw) * MOTOR_CONTINUOUS_FRACTION
    g[ROW_MOTOR] = demand_kw / rated - 1.0 if rated > 0 else float("inf")
    if g[ROW_MOTOR] > 0:
        why[ROW_MOTOR] = (
            f"cruise demand {demand_kw:.1f} kW exceeds the continuous "
            f"rating {rated:.1f} kW ({MOTOR_CONTINUOUS_FRACTION:.0%} of the "
            f"declared {spec.motor_kw:.0f} kW motor)")
    imm = prop_immersion_m(hull, wl)
    below = float(getattr(spec, "prop_max_below_keel_m", 0.0) or 0.0)
    d_min = min_prop_diameter_m(thrust_n, n_props)
    d_max = max_prop_diameter_m(imm, recess, below)
    g[ROW_PROP] = (d_min / d_max - 1.0) if d_max > 1e-9 else float("inf")
    if g[ROW_PROP] > 0:
        why[ROW_PROP] = (
            f"the thrust needs a {d_min:.2f} m disc ({n_props} prop(s) at "
            f"<= {PROP_DISC_LOADING_MAX_PA:.0f} Pa loading) but the stern "
            f"offers {d_max:.2f} m ({imm:.2f} m immersion + {recess:.2f} m "
            f"tunnel recess + {below:.2f} m below-keel hang); add props, "
            f"recess a tunnel, allow hang below the keel, or deepen the "
            f"stern")
    return g, why
