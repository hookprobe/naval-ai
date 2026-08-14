"""L1 hydrostatics: displacement, centres, GM, and the draft solve.

Classic naval-architecture integrals over the station arrays (Simpson via
trapezoid on a fine grid). Everything here is deterministic and O(ms).

MULTIHULL. `solve(hull, ..., vessel=cfg)` puts `cfg.n_hulls` IDENTICAL copies
of `hull` at their own centreplanes and returns the hydrostatics of the WHOLE
vessel. The one piece of physics that is not a multiplication is the transverse
waterplane inertia, which picks up a parallel-axis term:

    I_T = sum_j [ I_T,j + A_wp,j d_j^2 ]     BM = I_T / volume     GM = KB+BM-KG

`d_j` is the transverse distance from demihull j's waterplane centroid to the
vessel centreline (s/2 for a symmetric catamaran). It is why a SLENDER
catamaran has excellent transverse stability without widening a single
demihull, which is exactly what a solar vessel wants — deck and roof area
without wetted beam.

WHICH QUANTITIES ARE THE VESSEL'S AND WHICH ARE ONE DEMIHULL'S. Getting this
wrong is the whole trap, because `cb` divided by an overall beam is a number
with no meaning and `L/B` measured across the tunnel is not the slenderness
Michell's integral assumes.

    VESSEL   volume, disp_kg, awp, i_t, bm, bm_l, wetted
    DEMIHULL b_wl_max, cb, cp, freeboard_min
    SHARED   draft, lcb, lcf, kb, lwl_eff, x_wl_aft  (identical hulls)

`beam_overall_m` and `volume_demi` are PROPERTIES derived from those, not
stored a second time.

A MONOHULL IS THE ONE-HULL CASE, BIT FOR BIT. With `vessel=None` (the default)
`n_hulls` is 1 and `d` is 0.0, and every line below reduces to `1 * v` and
`ixx + awp * 0.0`, which are exact in IEEE-754 — not "within tolerance".
`tests/test_multihull.py::test_the_one_hull_case_is_the_monohull_bit_for_bit`
asserts it field by field with `==`, and against the pre-multihull FORMULAS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .geometry import G, RHO_WATER, Hull


@dataclass(frozen=True)
class HydroState:
    draft: float          # m, waterline used (>=0 means WL at z = T_design - draft shift)
    volume: float         # m^3
    disp_kg: float
    lcb: float            # m from transom
    kb: float             # m above keel (baseline = keel at midship, z=-T)
    bm: float             # m, transverse
    bm_l: float           # m, longitudinal (about the transverse axis at F)
    awp: float            # m^2 waterplane
    lcf: float            # m from transom
    b_wl_max: float       # ONE DEMIHULL's waterline beam, not the vessel's
    # The waterline length the hull ACTUALLY floats at, not the LWL parameter.
    # It was computed inside solve() as a local, used for cb/cp, and thrown
    # away — so the only length available to a caller wanting LCB as a
    # percentage was the design parameter, which is a different number at any
    # floated waterline. Gap B8 needs the floated one: LCB is meaningful only
    # relative to the midpoint of the waterline it was integrated over.
    lwl_eff: float
    # x of the aft end of the immersed waterline. The transom does not sit at
    # x = 0 once rocker lifts it clear, so the midships station is
    # x_wl_aft + lwl_eff/2 and NOT lwl_eff/2 — an error of half the rocker
    # overhang, straight onto the quantity B8 constrains.
    x_wl_aft: float
    cb: float             # block coefficient
    cp: float             # prismatic
    wetted: float         # m^2
    freeboard_min: float  # m
    # --- multihull. Defaults ARE the monohull, so every existing construction
    # of this frozen type keeps working and keeps meaning what it meant.
    n_hulls: int = 1
    separation_m: float = 0.0     # centreplane to centreplane; 0 for a monohull
    # The VESSEL's transverse waterplane second moment [m^4], parallel-axis
    # term included. Stored rather than recomputed by every reader because it
    # is the numerator of `bm` and the two must never be able to disagree; for
    # a monohull it is exactly (2/3) Int b^3 dx, the number this module has
    # always divided by the volume.
    i_t: float = 0.0

    @property
    def volume_demi(self) -> float:
        """Displaced volume of ONE demihull [m^3]. Derived, never stored — the
        recurring defect in this codebase is a number declared twice."""
        return self.volume / self.n_hulls

    @property
    def awp_demi(self) -> float:
        """Waterplane area of ONE demihull [m^2]."""
        return self.awp / self.n_hulls

    @property
    def beam_overall_m(self) -> float:
        """Overall waterline beam of the VESSEL [m]: the demihull centreplanes
        are s apart and each carries b_wl_max/2 outboard, so the extreme
        breadth is s + b_wl_max. Equals `b_wl_max` for a monohull, where
        `separation_m` is 0.0.

        A DERIVED REPORTING QUANTITY, not a constraint: nothing in the ladder
        bounds overall beam today (trailer and lock widths are a product
        question, not a physics one), and an always-satisfied constraint row
        occupying an NSGA-II dimension is a defect this repository has already
        shipped once (gap E4 deleted four of them).
        """
        return self.separation_m + self.b_wl_max

    @property
    def lcb_pct_lwl(self) -> float:
        """LCB relative to midships, as a percentage of the floated waterline
        length. NEGATIVE = aft of midships, the naval-architecture convention.

        Derived here rather than at the call site so the reference station is
        defined once — see `limits.LCB_BAND_PCT_LWL` for the band it is judged
        against and gap B8 for why it is judged at all.
        """
        mid = self.x_wl_aft + 0.5 * self.lwl_eff
        return 100.0 * (self.lcb - mid) / max(self.lwl_eff, 1e-9)


def _waterline_ends(x, a, wet) -> tuple[float, float]:
    """(x_wl_aft, lwl_eff), with the ends INTERPOLATED, not snapped to a station.

    THE BUG THIS REPLACES. `lwl_eff` was the span of WET STATIONS:

        x_wl_aft = float(x[wet].min())
        lwl_eff  = float(x[wet].max() - x[wet].min())

    The waterline does not end at a station; it ends between the last wet one
    and the first dry one. Snapping to the last wet station therefore truncates
    by up to one spacing, and -- this is what makes it a defect rather than
    noise -- it can only ever be too SHORT. The error never averages out over a
    population, so every hull in the batch is biased the same way.

    MEASURED 2026-08-12 on the seed-0 batch, hull 0 at x_mb = 0.5123 (chosen to
    fall BETWEEN stations at the shipped n_stations = 41), against a converged
    reference at n_stations = 2561:

        n_stations     lwl_eff        cb         cp
                41   14.639769  0.370325   0.708813
                81   14.827458  0.365835   0.700272
               161   14.921303  0.363595   0.695983
               641   14.991687  0.361914   0.692767
              1281   15.003417  0.361634   0.692230

    True LWL is 15.0151 m and the station spacing is 0.375379 m, so the shipped
    grid was short by 0.363648 m = 0.969 of ONE station -- an off-by-one-cell
    truncation, converging at observed order p = 1.00. It propagates straight
    into the two coefficients that divide by it: `cb` and `cp` were both
    inflated 2.4% (Richardson-extrapolated cp 0.691693 against 0.708813).

    Volume was never the problem -- it converges to 0.087% over the same range,
    and `awp` to 0.12%. Nor was it the max-beam station: `Am` is CONSTANT at
    0.603408 across 41..1281, which refutes the first explanation offered for
    this (that the coarse grid was missing the true midship section). The error
    is entirely in the LENGTH.

    Found while sweeping x_mb for station-period aliasing. That aliasing is real
    -- a sawtooth of period 1/40 in x_mb that collapses ~60x per station
    doubling -- but it is small (264 ppm on wetted area at n=41) and reaches
    `wh_per_nm` at only ~0.01% above the noise floor. The bias found alongside
    it is 200x larger and has nothing to do with x_mb.
    """
    if not wet.any():
        return 0.0, 1e-9
    idx = np.flatnonzero(wet)
    i0, i1 = int(idx[0]), int(idx[-1])
    # Forward end: a falls from a[i1] to a[i1+1] <= 1e-6. Linear in the section
    # area, so the estimate is exact for a wedge and second-order otherwise.
    x_fwd = float(x[i1])
    if i1 + 1 < len(x):
        da = float(a[i1] - a[i1 + 1])
        if da > 0.0:
            x_fwd += float(x[i1 + 1] - x[i1]) * float(a[i1]) / da
    # Aft end: usually the transom, which is wet AT x[0] -- there is no dry
    # station behind it and the waterline genuinely ends there. Only a hull that
    # runs dry aft of its first station gets an interpolated aft end.
    x_aft = float(x[i0])
    if i0 - 1 >= 0:
        da = float(a[i0] - a[i0 - 1])
        if da > 0.0:
            x_aft -= float(x[i0] - x[i0 - 1]) * float(a[i0]) / da
    return x_aft, max(x_fwd - x_aft, 1e-9)


def moulded_max_beam(hull: Hull) -> float:
    """The widest the moulded surface of ONE hull ever gets [m].

    NOT `HydroState.b_wl_max`, which is the beam at the waterline the hull was
    solved at and moves with the draft. This is the whole surface — chine,
    sheer and design waterline — and it is the right bar for "do two demihulls
    at this spacing touch each other", because two hulls whose sheers overlap
    are one hull with a slot in it whatever their waterline beams do.
    """
    return 2.0 * max(float(hull.y_chine.max()), float(hull.y_sheer.max()),
                     float(hull.y_wl.max()))


def vessel_terms(hull: Hull, vessel=None) -> tuple[int, float, float]:
    """(n_hulls, separation_m, d_m) for a vessel configuration on THIS hull.

    THE ONE HOME of "how many hulls, how far apart, and how far off centreline
    is each one". `solve` calls it, and `evaluate` calls it to hand the same
    separation to `resistance.total_resistance` — if the two derived it
    separately the stability answer and the resistance answer could describe
    different vessels while sharing one `Evaluation`.

    `vessel` is DUCK-TYPED on `.n_hulls` and `.separation_m(lwl)`, the same
    device and for the same reason as `evaluate._apply_policy` duck-types the
    compiled constitution: this module imports `geometry` and nothing else, and
    importing `mission` here would make the hydrostatic kernel depend on the
    front-end contract layer that sits three floors above it.

    `vessel=None` is a monohull and returns `(1, 0.0, 0.0)` exactly, which is
    what makes every arithmetic line in `solve` reduce to what it was.

    REFUSES an intersection. Thin-ship theory and a waterplane integral will
    both happily accept two demihulls that occupy the same water and return a
    number; `resistance._separation_or_raise` already says so in as many words
    for the wave side, and this is the same refusal on the stability side.
    """
    if vessel is None:
        return 1, 0.0, 0.0
    n = int(vessel.n_hulls)
    if n == 1:
        return 1, 0.0, 0.0
    lwl = float(hull.x[-1] - hull.x[0])
    sep = float(vessel.separation_m(lwl))
    beam = moulded_max_beam(hull)
    if sep <= beam:
        raise ValueError(
            f"vessel: demihull spacing {sep:.4f} m is not greater than the "
            f"demihull's own moulded beam {beam:.4f} m, so the {n} hulls at "
            f"y = +-{sep / 2:.4f} m INTERSECT. That is not a narrow catamaran, "
            f"it is one hull with a slot in it — and both the waterplane "
            f"integral and the Michell integral would return a number for it.")
    # Two IDENTICAL demihulls at y = +-s/2, so every |d_j| is s/2 and the
    # parallel-axis term is the same for both. The `sum_j` in the docstring is
    # written out rather than collapsed because a trimaran would not have this
    # symmetry — which is exactly why `mission.EVALUABLE_TOPOLOGIES` refuses
    # one instead of pretending three copies of one genome is a trimaran.
    return n, sep, 0.5 * sep


def solve(hull: Hull, rho: float = RHO_WATER, wl: float = 0.0,
          vessel=None) -> HydroState:
    """Hydrostatics at a given waterline height wl (0 = design WL).

    `vessel` is an optional duck-typed multihull configuration (see
    `vessel_terms`); None is a monohull and is bit-identical to this function's
    behaviour before multihull support existed.
    """
    a, b, zc = hull.hydro_arrays(wl)
    x = hull.x
    n_hulls, separation, d = vessel_terms(hull, vessel)
    # ONE demihull first, then the vessel. Every per-hull integral below is
    # unchanged; what the multihull adds is the n_hulls factor and the one
    # A_wp d^2 term, and nothing else.
    vol_demi = 2.0 * float(np.trapezoid(a, x))
    if vol_demi <= 1e-9:
        raise ValueError("hull has no displacement at this waterline")
    vol = n_hulls * vol_demi
    # lcb, zb, lcf are LENGTHS shared by identical hulls, so they divide by the
    # DEMIHULL integral and not by the vessel total. Dividing lcb by `vol`
    # after it became the vessel volume would have halved it for a catamaran,
    # which is a lever straight onto trim.
    lcb = 2.0 * float(np.trapezoid(a * x, x)) / vol_demi
    # KB: volume-weighted z-centroid, referenced to keel plane z=-T
    zb = 2.0 * float(np.trapezoid(a * zc, x)) / vol_demi
    t_design = -float(hull.z_keel.min())
    kb = zb + t_design
    awp_demi = 2.0 * float(np.trapezoid(b, x))
    awp = n_hulls * awp_demi
    lcf = 2.0 * float(np.trapezoid(b * x, x)) / max(awp_demi, 1e-12)
    ixx_demi = (2.0 / 3.0) * float(np.trapezoid(b**3, x))
    # THE MULTIHULL TERM, AND IT IS THE WHOLE POINT.
    #     I_T = sum_j [ I_T,j + A_wp,j d_j^2 ]
    # The demihull's own inertia about ITS centreplane is ixx_demi; the shift
    # to the vessel centreline is the parallel-axis A_wp d^2. On a slender
    # demihull the second term dwarfs the first — that is why a catamaran can
    # be stiff transversely while every hull in it stays narrow, and why
    # judging a demihull by a monohull GM floor measures the wrong vessel.
    i_t = n_hulls * (ixx_demi + awp_demi * d * d)
    bm = i_t / vol
    # Longitudinal waterplane inertia about the TRANSVERSE axis through the
    # centre of flotation (parallel-axis, so it must use lcf and not midships).
    # Without this there is no GM_L, and without GM_L `weights.trim_angle_deg`
    # has no denominator — which is why the trim check could not exist and an
    # arrangement could move 500 kg aft with no consequence anywhere.
    # Identical hulls side by side share one x-distribution, so both I_L and
    # the volume scale by n_hulls and BM_L is UNCHANGED by adding a demihull.
    # That is correct and worth saying: a catamaran's transverse stiffness is
    # transformed by separation and its longitudinal stiffness is not.
    i_l = n_hulls * 2.0 * float(np.trapezoid(b * (x - lcf) ** 2, x))
    bm_l = i_l / vol
    bmax = 2.0 * float(b.max())          # ONE demihull's waterline beam
    wet = a > 1e-6
    x_wl_aft, lwl_eff = _waterline_ends(x, a, wet)
    # Immersion is measured from the KEEL (z = -t_design) up to the waterline
    # plane (z = wl), so it is wl + t_design. The sign was inverted, which is
    # exact only at wl = 0 — which is why every test passed. MEASURED on the
    # mid hull: at wl = -0.40 the volume collapses to 1.088 m^3 (barely
    # immersed) while draft was reported as 0.95 m, LARGER than the 0.55 m at
    # wl = 0. It propagates: cb = vol/(lwl*bmax*t_mean) was then ~0.11 instead
    # of ~0.34, and evaluate() feeds that cb to form_factor(), so the friction
    # form factor k came out ~0.03 instead of ~0.29 — a large error in
    # frictional resistance at any off-design waterline.
    t_mean = t_design + wl
    # cb AND cp ARE THE DEMIHULL'S, and they must be. Both are consumed by
    # `resistance.form_factor`, which is Watanabe's regression on a hull's own
    # block coefficient and its own B/T; feeding it a vessel volume over a
    # demihull beam would misreport a catamaran's form drag by exactly the hull
    # count. Same reason `bmax` above is one demihull's.
    cb = vol_demi / max(lwl_eff * bmax * t_mean, 1e-12)
    amax = float(a.max()) * 2.0
    cp = vol_demi / max(amax * lwl_eff, 1e-12)
    fb = float((hull.z_sheer - wl).min())
    return HydroState(
        draft=t_mean, volume=vol, disp_kg=rho * vol, lcb=lcb, kb=kb, bm=bm,
        bm_l=bm_l,
        awp=awp, lcf=lcf, b_wl_max=bmax, lwl_eff=lwl_eff, x_wl_aft=x_wl_aft,
        cb=cb, cp=cp,
        wetted=n_hulls * hull.wetted_surface(wl), freeboard_min=fb,
        n_hulls=n_hulls, separation_m=separation, i_t=i_t,
    )


def gm(state: HydroState, kg: float) -> float:
    """Transverse metacentric height. kg measured above keel plane."""
    return state.kb + state.bm - kg


# ---------------------------------------------------------------------------
# THE MULTIHULL STABILITY CRITERION — WHICH DOES NOT EXIST HERE, AND SAYS SO
# ---------------------------------------------------------------------------
#
# THE FAILURE THIS REFUSES TO SHIP. The `A_wp d^2` term above makes a
# catamaran's GM enormous — MEASURED on `tests/test_phase0.mid_params` at the
# 6000 kg mission, 0.6688 m as a monohull and **25.11 m** at s/Lwl 0.40. Every
# GM floor in this repository and in four national codes is between 0.15 m and
# 0.35 m. So the moment the parallel-axis term landed, every catamaran started
# clearing every metacentric bar by two orders of magnitude, and a reader of
# `ev.rules` would see R-GM PASSED and conclude the boat is safe.
#
# IT IS NOT THE SAME QUESTION. A monohull's righting arm rises to a maximum and
# falls to zero at the angle of vanishing stability, and below AVS it
# SELF-RIGHTS, so a GM floor is a fair proxy for "will it come back". A
# catamaran's righting moment PEAKS when the windward hull lifts and collapses
# past it; once over, the vessel is STABLE INVERTED and cannot self-right. That
# is why ISO 12217 addresses INVERSION and ESCAPE for habitable multihulls
# rather than resting on a metacentric floor. GM is nearly irrelevant to
# whether a catamaran capsizes.
#
# WHAT ACTUALLY GOVERNS, and it is FREE, BINDING and CROSS-ATTESTED by two
# independent regulators — transcribed in
# `docs/research/standards/NATIONAL-CODES.md` §8.4 and §4.5:
#
#   NZ Maritime Rules Part 40A, Appendix 1, cl. 1.4 (multihull decked ship):
#     (a) area under the GZ curve >= 0.055 x 30/theta m.rad up to theta, theta
#         the LEAST of the downflooding angle, the angle of maximum GZ, and 30
#         degrees;
#     (b) maximum GZ must occur at a heel of NOT LESS THAN 10 degrees;
#     (c) heel due to steady wind <= 16 degrees, with the wind heel lever
#         h_w = P A Z / (9800 disp_t) metres — P the wind pressure by
#         operating area, A the projected lateral area above the lightest
#         service waterline, Z from the centre of A to half the lightest
#         service draught;
#     (d) a residual-area condition (NOT READ in the research file).
#   AMSA NSCV Part C6A Chapter 5B Table 11 cl. 5B.2 and 5B.4 give the SAME
#   10-degree theta_max floor and the SAME 16-degree combined heel cap.
#   NZ Part 40A App. 1 cl. 1.1 also caps offset-load heel at 8 degrees for a
#   MULTIHULL against 15 for a monohull.
#
# THOSE NUMBERS ARE QUOTED IN THE REFUSAL STRING AND ARE DELIBERATELY NOT
# CONSTANTS. A threshold in code is a threshold something enforces, and nothing
# here enforces these — writing them as `MULTIHULL_THETA_MAX_MIN_DEG = 10.0`
# would put a bar in the tree that no test can fail and that a later reader
# would wire up believing it had been validated. They are prose, with a
# citation, inside a refusal.
#
# WHY THEY CANNOT BE IMPLEMENTED HERE, precisely:
#   * (a) and (b) need a RIGHTING-ARM CURVE at large heel. This module computes
#     UPRIGHT metacentres only — `bm` is the small-angle waterplane inertia and
#     goes wrong the instant a demihull emerges, which for a catamaran is the
#     one angle that matters. There is no heeled-waterplane solve anywhere in
#     this repository.
#   * (c) needs the projected lateral area A above the waterline. The genome
#     carries a hull and no superstructure, and on a solar catamaran the roof
#     and the bridge-deck house ARE the windage. Computing A from the hull
#     profile alone would understate the heeling moment — the flattering
#     direction — which is precisely the defect class this refusal exists for.
#
# So the verdict is a REFUSAL and never a pass. `evaluate` emits it as a
# violation, so a multihull is INFEASIBLE by explicit refusal rather than
# feasible by a criterion that does not apply to it. A failing gate is
# information; an unmeasured quantity scored as passing is defect class 1.
MULTIHULL_CRITERION = (
    "NZ Maritime Rules Part 40A App. 1 cl. 1.4 (a)-(d), cross-attested by AMSA "
    "NSCV C6A ch. 5B Table 11 cl. 5B.2/5B.4 — see "
    "docs/research/standards/NATIONAL-CODES.md §8.4 and §4.5")


def multihull_stability_refusal(state: HydroState, gm_m: float,
                                offset_load_assessed: bool = True
                                ) -> tuple[str, ...]:
    """Why a multihull's GM does not establish that it is safe. Empty for a
    monohull.

    Returns violation strings in `evaluate`'s convention. This is a REFUSAL
    generator, not an assessor: it computes no criterion and returns no margin,
    because the criterion that governs needs a righting-arm curve and a windage
    area that this repository does not have. See the block above.
    """
    if state.n_hulls <= 1:
        return ()
    # The third clause is about a verdict R-OLH gave. It is omitted when
    # ISO 12217-1 was not assessed at all (manning=uncrewed), because a warning
    # that "the bar this ladder applied is a monohull bar" is false when no bar
    # was applied — and a refusal that misdescribes what happened is worse than
    # one clause shorter.
    olh = ((
        f"multihull stability: the offset-load bar this ladder applied is ISO "
        f"12217-1's LENGTH formula for a monohull. NZ Part 40A App. 1 cl. 1.1 "
        f"caps a MULTIHULL at 8 deg against 15 for a monohull, so R-OLH's "
        f"verdict on this hull is a monohull verdict and must not be read as a "
        f"multihull one.",) if offset_load_assessed else ())
    return (
        f"multihull stability: NO CRITERION IS IMPLEMENTED, and GM "
        f"{gm_m:.2f} m does NOT establish that this vessel is safe. The "
        f"parallel-axis A_wp d^2 term makes a {state.n_hulls}-hull vessel at "
        f"{state.separation_m:.2f} m spacing clear every metacentric floor in "
        f"this repository by one to two orders of magnitude, and that is not "
        f"the question. A monohull self-rights below its angle of vanishing "
        f"stability; a catamaran's righting moment PEAKS when the windward "
        f"hull lifts, collapses past that peak, and the vessel is then STABLE "
        f"INVERTED and cannot self-right — which is why ISO 12217 addresses "
        f"inversion and escape for habitable multihulls instead of resting on "
        f"a metacentric floor.",
        f"multihull stability: the criterion that governs is "
        f"{MULTIHULL_CRITERION}: (a) GZ-curve area, (b) maximum GZ at a heel "
        f"of not less than 10 deg, (c) steady-wind heel not over 16 deg on the "
        f"lever h_w = P.A.Z/(9800.disp_t), (d) a residual-area condition. "
        f"Clauses (a) and (b) ARE now computable — the heeled-waterplane "
        f"solve landed 2026-08-14 and yields the righting-arm curve; ask `hydrostatics.multihull_gz_assessment` "
        f"for the measured values — but the criterion still cannot PASS: "
        f"(c) needs the projected lateral area above the waterline, which on "
        f"a solar catamaran is the roof and the bridge-deck house — neither "
        f"is in the genome, and deriving A from the bare hull profile would "
        f"understate the heeling moment, the flattering direction — and "
        f"(d)'s clause body is NOT READ. Two assessed clauses of four is a "
        f"measurement, not a verdict.",
    ) + olh


def gm_long(state: HydroState, kg: float) -> float:
    """Longitudinal metacentric height [m]. kg measured above keel plane.

    Typically ~Lwl in magnitude, i.e. two orders above transverse GM, which is
    exactly why trim is stiff and small LCG errors show up as tenths of a
    degree rather than a capsize.
    """
    return state.kb + state.bm_l - kg


def solve_to_displacement(hull: Hull, target_kg_mass: float,
                          rho: float = RHO_WATER,
                          tol: float = 1e-3,
                          vessel=None) -> tuple[HydroState, float]:
    """Find the waterline at which displacement matches target mass (bisection).

    `vessel` floats the WHOLE vessel to `target_kg_mass`, not each demihull:
    a 6000 kg catamaran puts 3000 kg in each hull and therefore floats higher
    than the same genome as a monohull. That is not a detail — draft is what
    KB, the waterplane beam and every proportion downstream are measured at.

    Returns (state, wl). wl < 0 means floating higher than design WL.
    Raises if the hull cannot carry the mass with positive freeboard, AND if it
    cannot float that lightly, AND if the bisection does not close on `tol`.

    BOTH ENDS OF THE BRACKET ARE VERIFIED NOW (gap E14). Only `z_hi` was, and
    the post-loop line returned `solve(hull, rho, 0.5*(lo+hi))` — the midpoint
    after 80 iterations — with the SAME shape as the converged return, so no
    caller could tell them apart. The mechanism was never the iteration count:
    `z_lo = z_keel.min() * 0.98` is commented "nearly dry" and is not dry.

    MEASURED 2026-08-12 on `tests/test_phase0.mid_params`, exactly reproducing
    the register's figure:

        target kg   returned disp kg      error
              1.0             4.134    +313.4%
             10.0            10.003      +0.0%
            100.0            99.960      -0.0%
           2000.0          1999.393      -0.0%

    The hull still displaces 4.134 kg at `z_lo`, so any target below that
    cannot be bracketed, `hi` walks down to `z_lo`, and the loop hands back a
    waterline whose displacement is four times what was asked for — an
    unconverged answer returned as an answer, which is defect class 1. It is
    now a refusal, symmetric with the "hull swamps" one above it, and it is a
    ValueError because `evaluate()` already catches exactly that and turns it
    into a `floatation: ...` violation string (navalai/evaluate.py:454-460).
    A `converged=` flag on `HydroState` was considered and rejected: a flag
    nobody is forced to read is the same defect with a field added.
    """
    z_lo = float(hull.z_keel.min()) * 0.98          # nearly dry, NOT dry
    z_hi = float(hull.z_sheer.min()) - 0.02          # just below deck edge
    m_hi = solve(hull, rho, z_hi, vessel).disp_kg
    if m_hi < target_kg_mass:
        raise ValueError(
            f"hull swamps: max buoyant mass {m_hi:.0f} kg < target {target_kg_mass:.0f} kg")
    # The LOW end. `solve` raises when the waterline is below the keel, and
    # that is the GOOD case: it means the bracket really does reach zero
    # displacement and any positive target is reachable.
    try:
        m_lo = solve(hull, rho, z_lo, vessel).disp_kg
    except ValueError:
        m_lo = 0.0
    if m_lo > target_kg_mass:
        raise ValueError(
            f"hull floats too high: min buoyant mass {m_lo:.3f} kg at the "
            f"lowest bracketable waterline {z_lo:.4f} m > target "
            f"{target_kg_mass:.3f} kg. The bracket does not contain the "
            f"answer, so bisection cannot find it and the midpoint it would "
            f"return is not a flotation.")
    lo, hi = z_lo, z_hi
    m = float("nan")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        try:
            m = solve(hull, rho, mid, vessel).disp_kg
        except ValueError:
            lo = mid
            continue
        if abs(m - target_kg_mass) < tol * target_kg_mass:
            return solve(hull, rho, mid, vessel), mid
        if m < target_kg_mass:
            lo = mid
        else:
            hi = mid
    raise ValueError(
        f"solve_to_displacement did not converge: {m:.3f} kg against target "
        f"{target_kg_mass:.3f} kg after 80 bisections on [{z_lo:.4f}, "
        f"{z_hi:.4f}] m, still {abs(m - target_kg_mass) / max(target_kg_mass, 1e-9):.1%} "
        f"out against a {tol:.1%} tolerance. The midpoint is not the answer "
        f"and must not be returned as one.")


# ---------------------------------------------------------------------------
# TRIM EQUILIBRIUM (R2.1, audit P0 "no trim equilibrium anywhere").
#
# Every hydrostatic quantity above is computed at a LEVEL waterline; the trim
# ANGLE the ladder reports is `weights.trim_angle_deg`, the small-angle lever
# (LCG-LCB)/GM_L — a linearised ESTIMATE about the level float. That means a
# hull the ladder reports as trimming 1.9 deg has its GM, freeboard, wetted
# surface and proportions all reported for an attitude it does not float at.
# The two functions below solve the actual attitude: the waterline PLANE gains
# a longitudinal tilt, each station is clipped at its own local waterline —
# `Hull.immersed_section(i, wl_i)` was per-station all along — and the
# equilibrium is the (wl0, theta) at which the buoyant mass matches the weight
# AND the centre of buoyancy stands under the centre of gravity.
# ---------------------------------------------------------------------------

def solve_trimmed(hull: Hull, rho: float = RHO_WATER, wl0: float = 0.0,
                  trim_deg: float = 0.0, vessel=None) -> HydroState:
    """Hydrostatics on a TRIMMED waterplane. Positive trim = bow (x = LWL) down.

    `wl0` is the waterline height at midships (x = LWL/2); the local plane is
    z_wl(x) = wl0 + tan(trim) * (x - LWL/2). At trim 0 this reproduces
    `solve(hull, rho, wl0, vessel)` exactly — same integrals, same guards —
    so the level solver remains the special case, not a second code path.

    Transverse quantities (BM, I_T) are still the UPRIGHT waterplane's: this
    solves trim, not heel. A heeled solve (the righting-arm curve) remains
    absent and is said so in the multihull refusal above.
    """
    x = hull.x
    L = float(x[-1] - x[0])
    tanb = math.tan(math.radians(trim_deg))
    wl_x = wl0 + tanb * (x - (x[0] + 0.5 * L))
    n = hull.n_stations
    a = np.empty(n)
    b = np.empty(n)
    zc = np.empty(n)
    for i in range(n):
        a[i], b[i], zc[i] = hull.immersed_section(i, float(wl_x[i]))
    n_hulls, separation, d = vessel_terms(hull, vessel)
    vol_demi = 2.0 * float(np.trapezoid(a, x))
    if vol_demi <= 1e-9:
        raise ValueError("hull has no displacement at this waterline")
    vol = n_hulls * vol_demi
    lcb = 2.0 * float(np.trapezoid(a * x, x)) / vol_demi
    zb = 2.0 * float(np.trapezoid(a * zc, x)) / vol_demi
    t_design = -float(hull.z_keel.min())
    kb = zb + t_design
    awp_demi = 2.0 * float(np.trapezoid(b, x))
    awp = n_hulls * awp_demi
    lcf = 2.0 * float(np.trapezoid(b * x, x)) / max(awp_demi, 1e-12)
    ixx_demi = (2.0 / 3.0) * float(np.trapezoid(b**3, x))
    i_t = n_hulls * (ixx_demi + awp_demi * d * d)
    bm = i_t / vol
    i_l = n_hulls * 2.0 * float(np.trapezoid(b * (x - lcf) ** 2, x))
    bm_l = i_l / vol
    bmax = 2.0 * float(b.max())
    wet = a > 1e-6
    x_wl_aft, lwl_eff = _waterline_ends(x, a, wet)
    # Mean immersion over the wetted length — the trimmed generalisation of
    # `t_design + wl`, which it equals exactly at trim 0 for a fully-wetted
    # hull. cb/cp consume it the same way the level solver's t_mean is
    # consumed: as the mean draft of the floating attitude.
    if wet.any():
        t_mean = t_design + float(np.mean(wl_x[wet]))
    else:
        t_mean = t_design + wl0
    cb = vol_demi / max(lwl_eff * bmax * t_mean, 1e-12)
    amax = float(a.max()) * 2.0
    cp = vol_demi / max(amax * lwl_eff, 1e-12)
    fb = float((hull.z_sheer - wl_x).min())
    return HydroState(
        draft=t_mean, volume=vol, disp_kg=rho * vol, lcb=lcb, kb=kb, bm=bm,
        bm_l=bm_l,
        awp=awp, lcf=lcf, b_wl_max=bmax, lwl_eff=lwl_eff, x_wl_aft=x_wl_aft,
        cb=cb, cp=cp,
        wetted=n_hulls * hull.wetted_surface(wl0), freeboard_min=fb,
        n_hulls=n_hulls, separation_m=separation, i_t=i_t,
    )


def _float_at_trim(hull: Hull, target_kg_mass: float, trim_deg: float,
                   rho: float, vessel, tol: float) -> tuple[HydroState, float]:
    """`solve_to_displacement`'s bisection, on the trimmed plane at one angle."""
    z_lo = float(hull.z_keel.min()) * 0.98
    z_hi = float(hull.z_sheer.min()) - 0.02
    st_hi = solve_trimmed(hull, rho, z_hi, trim_deg, vessel)
    if st_hi.disp_kg < target_kg_mass:
        raise ValueError(
            f"hull swamps at trim {trim_deg:+.2f} deg: max buoyant mass "
            f"{st_hi.disp_kg:.0f} kg < target {target_kg_mass:.0f} kg")
    try:
        m_lo = solve_trimmed(hull, rho, z_lo, trim_deg, vessel).disp_kg
    except ValueError:
        m_lo = 0.0
    if m_lo > target_kg_mass:
        raise ValueError(
            f"hull floats too high at trim {trim_deg:+.2f} deg: min buoyant "
            f"mass {m_lo:.3f} kg > target {target_kg_mass:.3f} kg")
    lo, hi = z_lo, z_hi
    m = float("nan")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        try:
            st = solve_trimmed(hull, rho, mid, trim_deg, vessel)
            m = st.disp_kg
        except ValueError:
            lo = mid
            continue
        if abs(m - target_kg_mass) < tol * target_kg_mass:
            return st, mid
        if m < target_kg_mass:
            lo = mid
        else:
            hi = mid
    raise ValueError(
        f"flotation at trim {trim_deg:+.2f} deg did not converge: {m:.3f} kg "
        f"against target {target_kg_mass:.3f} kg after 80 bisections")


def solve_equilibrium(hull: Hull, target_kg_mass: float, lcg_m: float,
                      rho: float = RHO_WATER, vessel=None,
                      max_trim_deg: float = 6.0, tol: float = 1e-3,
                      warm: tuple[HydroState, float] | None = None
                      ) -> tuple[HydroState, float, float]:
    """The floating ATTITUDE: (state, wl0, trim_deg) with the buoyant mass at
    `target_kg_mass` AND the centre of buoyancy under the centre of gravity.

    Nested bisection: the inner loop floats the hull at a candidate trim
    (`_float_at_trim`), the outer drives lcb(trim) - lcg to zero. lcb moves
    AFT as the bow goes down, so the residual is monotone decreasing in trim
    and a sign change on [-max_trim_deg, +max_trim_deg] brackets the root.

    REFUSES when no bracket exists: a hull whose LCG cannot be stood under
    within ±`max_trim_deg` has no equilibrium this solver may report, and the
    nearest endpoint is not an answer (the same rule
    `solve_to_displacement` applies to its own bracket — gap E14).
    """
    L = max(float(hull.x[-1]), 1.0)
    # NEWTON FAST PATH, MEASURED 2026-08-14 before wiring into evaluate():
    # the nested bisection costs 963 ms against the level float's 80 ms on
    # the reference hull, which would put ~1 s inside every L1 evaluation
    # and ~12 minutes inside one NSGA-II front. Warm-started from the level
    # float and the small-angle lever (the estimate this solver replaces —
    # demoted from answer to initial guess), 2-4 damped Newton iterations
    # on r = (disp - target, lcb - lcg) land inside the same tolerances for
    # ~10 `solve_trimmed` calls. The bisection below remains the
    # AUTHORITATIVE fallback and the only issuer of the no-equilibrium
    # refusal: Newton is never allowed to refuse, only to succeed or hand
    # over.
    try:
        if warm is not None:
            # The caller already floated the hull level (`evaluate` always
            # has); re-solving it here would double the entry cost for
            # nothing.
            st0, wl_l = warm
        else:
            st0, wl_l = solve_to_displacement(hull, target_kg_mass, rho,
                                              tol=tol, vessel=vessel)
        theta0 = math.degrees(math.atan((lcg_m - st0.lcb)
                                        / max(st0.kb + st0.bm_l, 1e-9)))
        z = np.array([wl_l, min(max(theta0, -max_trim_deg), max_trim_deg)])
        h_w, h_t = 1e-4, 1e-3
        for _ in range(8):
            st = solve_trimmed(hull, rho, float(z[0]), float(z[1]), vessel)
            r = np.array([st.disp_kg - target_kg_mass, st.lcb - lcg_m])
            if (abs(r[0]) < tol * target_kg_mass and abs(r[1]) < 1e-4 * L
                    and abs(z[1]) <= max_trim_deg):
                return st, float(z[0]), float(z[1])
            sw = solve_trimmed(hull, rho, float(z[0]) + h_w, float(z[1]),
                               vessel)
            stt = solve_trimmed(hull, rho, float(z[0]), float(z[1]) + h_t,
                                vessel)
            J = np.array([
                [(sw.disp_kg - st.disp_kg) / h_w,
                 (stt.disp_kg - st.disp_kg) / h_t],
                [(sw.lcb - st.lcb) / h_w, (stt.lcb - st.lcb) / h_t]])
            step = np.linalg.solve(J, r)
            if not np.all(np.isfinite(step)):
                break
            # Damping: a Newton step through the sheer or past the trim
            # range is a sign the local model left its region, not a result.
            step[0] = min(max(step[0], -0.2), 0.2)
            step[1] = min(max(step[1], -2.0), 2.0)
            z = z - step
            if abs(z[1]) > max_trim_deg + 1e-9:
                break
    except (ValueError, np.linalg.LinAlgError):
        pass

    def residual(theta: float) -> tuple[float, HydroState, float]:
        st, wl0 = _float_at_trim(hull, target_kg_mass, theta, rho, vessel, tol)
        return st.lcb - lcg_m, st, wl0

    r_lo, st_lo, w_lo = residual(-max_trim_deg)
    r_hi, st_hi, w_hi = residual(+max_trim_deg)
    if r_lo == 0.0:
        return st_lo, w_lo, -max_trim_deg
    if r_hi == 0.0:
        return st_hi, w_hi, +max_trim_deg
    if r_lo * r_hi > 0.0:
        raise ValueError(
            f"no longitudinal equilibrium within ±{max_trim_deg:.1f} deg: "
            f"lcb - lcg spans [{r_hi:+.3f}, {r_lo:+.3f}] m over the full trim "
            f"range, so the centre of buoyancy cannot be stood under the "
            f"centre of gravity at any attitude this solver may report.")
    lo, hi = -max_trim_deg, +max_trim_deg
    # residual is DECREASING in trim (bow down moves lcb aft), so keep the
    # invariant residual(lo) > 0 > residual(hi).
    if r_lo < 0.0:
        lo, hi = hi, lo
    theta = 0.0
    for _ in range(60):
        theta = 0.5 * (lo + hi)
        r, st, wl0 = residual(theta)
        if abs(r) < 1e-4 * max(float(hull.x[-1]), 1.0):
            return st, wl0, theta
        if r > 0.0:
            lo = theta
        else:
            hi = theta
    raise ValueError(
        f"trim equilibrium did not converge: |lcb - lcg| = {abs(r):.5f} m "
        f"after 60 bisections at trim {theta:+.3f} deg — not an answer, and "
        f"not returned as one.")


# ---------------------------------------------------------------------------
# THE RIGHTING-ARM CURVE — GZ(phi) (audit P0 "no GZ(phi) anywhere"; R2.2's
# prerequisite).
#
# Everything above is UPRIGHT hydrostatics: `bm` is the small-angle waterplane
# inertia, and the multihull refusal block says precisely why that is not a
# capsize story ("there is no heeled-waterplane solve anywhere in this
# repository"). This is that solve. Each station's FULL closed section
# (starboard polyline, deck closure at the sheer, port mirror) is clipped
# against the heeled waterplane z = wl0 + tan(phi)*y [+ tan(trim)*(x-mid)],
# the vessel is floated at each heel, and the righting arm is the
# earth-horizontal separation of B and G.
#
# DECLARED ASSUMPTIONS, carried on the result so no consumer can mistake the
# claim (honesty rule 1):
#   * watertight to the SHEER, no superstructure or deckhouse buoyancy — the
#     genome carries a hull and nothing above it, so beyond deck-edge
#     immersion the curve is CONSERVATIVE for a real boat with a cabin and
#     exact for an open one with a sealed deck;
#   * fixed longitudinal attitude (the caller's trim, not re-solved per
#     heel) — free-to-trim coupling is not computed and is said so;
#   * no downflooding openings are declared anywhere in the genome, so the
#     deck-edge immersion angle is reported as the conservative proxy.
# ---------------------------------------------------------------------------

def _station_polygon(hull: Hull, i: int, y_offset: float = 0.0) -> np.ndarray:
    """Full closed section at station i as a CCW (M, 2) polygon of (y, z).

    Starboard keel -> bilge -> sheer from `Hull.section` (the kernel's own
    sampled boundary — no geometry re-transcription), a straight deck edge
    to the port sheer, and the port mirror back down to the keel."""
    half = hull.section(i)
    port = half[::-1].copy()
    port[:, 0] = -port[:, 0]
    poly = np.vstack([half, port[:-1]])
    if y_offset:
        poly = poly.copy()
        poly[:, 0] += y_offset
    return poly


def _clip_below_line(poly: np.ndarray, c: float,
                     m: float) -> tuple[float, float, float]:
    """(area, y_centroid, z_centroid) of the polygon region with
    z <= c + m*y — Sutherland-Hodgman against the half-plane, then the
    shoelace area and centroid. Returns (0, 0, 0) for a dry section."""
    f = poly[:, 1] - (c + m * poly[:, 0])
    if (f >= 0.0).all():
        return 0.0, 0.0, 0.0
    if (f <= 0.0).all():
        kept = poly
    else:
        pts = []
        n = len(poly)
        for k in range(n):
            a, b = poly[k], poly[(k + 1) % n]
            fa, fb = f[k], f[(k + 1) % n]
            if fa <= 0.0:
                pts.append(a)
            if (fa <= 0.0) != (fb <= 0.0):
                t = fa / (fa - fb)
                pts.append(a + t * (b - a))
        kept = np.asarray(pts)
        if len(kept) < 3:
            return 0.0, 0.0, 0.0
    y, z = kept[:, 0], kept[:, 1]
    y1, z1 = np.roll(y, -1), np.roll(z, -1)
    cross = y * z1 - y1 * z
    area2 = cross.sum()
    if abs(area2) < 1e-14:
        return 0.0, 0.0, 0.0
    yc = ((y + y1) * cross).sum() / (3.0 * area2)
    zc = ((z + z1) * cross).sum() / (3.0 * area2)
    return abs(area2) / 2.0, yc, zc


def heeled_displacement(hull: Hull, wl0: float, heel_deg: float,
                        trim_deg: float = 0.0,
                        vessel=None) -> tuple[float, float, float]:
    """(volume, yB, zB) with the waterplane heeled about the x-axis.

    Plane in body coordinates: z = wl0 + tan(heel)*y + tan(trim)*(x - mid).
    Positive heel puts the STARBOARD side (y > 0) deeper. A multihull is the
    same integral over each demihull's polygon offset to ±separation/2 —
    which is exactly the mechanism the upright parallel-axis term
    approximates, now computed instead of linearised: as the windward hull
    emerges the integral loses it, and the righting moment collapses past
    the peak, which no GM can express."""
    x = hull.x
    L = float(x[-1] - x[0])
    mid = float(x[0]) + 0.5 * L
    m_heel = math.tan(math.radians(heel_deg))
    m_trim = math.tan(math.radians(trim_deg))
    n_hulls, _sep, d = vessel_terms(hull, vessel)
    offsets = (0.0,) if n_hulls == 1 else (+d, -d)
    n = hull.n_stations
    a = np.zeros(n)
    my = np.zeros(n)
    mz = np.zeros(n)
    for i in range(n):
        c_i = wl0 + m_trim * (float(x[i]) - mid)
        for off in offsets:
            ai, yi, zi = _clip_below_line(_station_polygon(hull, i, off),
                                          c_i, m_heel)
            a[i] += ai
            my[i] += ai * yi
            mz[i] += ai * zi
    vol = float(np.trapezoid(a, x))
    if vol <= 1e-9:
        return 0.0, 0.0, 0.0
    yb = float(np.trapezoid(my, x)) / vol
    zb = float(np.trapezoid(mz, x)) / vol
    return vol, yb, zb


def _float_at_heel(hull: Hull, target_kg: float, heel_deg: float,
                   trim_deg: float, rho: float, vessel,
                   tol: float = 1e-3) -> tuple[float, float, float, float]:
    """Bisect wl0 until the heeled displacement carries `target_kg`.
    Returns (wl0, volume, yB, zB); raises when the hull cannot carry it."""
    m_heel = abs(math.tan(math.radians(heel_deg)))
    n_hulls, _sep, d = vessel_terms(hull, vessel)
    reach = (float(hull.y_sheer.max()) + (d if n_hulls > 1 else 0.0))
    z_min = float(hull.z_keel.min())
    z_max = float(hull.z_sheer.max())
    lo = z_min - m_heel * reach - 0.05
    hi = z_max + m_heel * reach + 0.05
    v_hi, _, _ = heeled_displacement(hull, hi, heel_deg, trim_deg, vessel)
    if rho * v_hi < target_kg:
        raise ValueError(
            f"hull swamps at heel {heel_deg:+.1f} deg: fully-immersed "
            f"buoyant mass {rho * v_hi:.0f} kg < target {target_kg:.0f} kg")
    target_v = target_kg / rho
    vol = yb = zb = 0.0
    for _ in range(70):
        mid_wl = 0.5 * (lo + hi)
        vol, yb, zb = heeled_displacement(hull, mid_wl, heel_deg, trim_deg,
                                          vessel)
        if abs(vol - target_v) < tol * target_v:
            return mid_wl, vol, yb, zb
        if vol < target_v:
            lo = mid_wl
        else:
            hi = mid_wl
    raise ValueError(
        f"heeled flotation did not converge at {heel_deg:+.1f} deg: "
        f"{rho * vol:.1f} kg against target {target_kg:.1f} kg — not an "
        f"answer, and not returned as one.")


@dataclass(frozen=True)
class GZCurve:
    """The righting-arm curve and what it implies, with its assumptions."""
    heels_deg: tuple[float, ...]
    gz_m: tuple[float, ...]
    gz_max_m: float
    heel_at_gz_max_deg: float
    avs_deg: float | None            # first GZ downcrossing past the peak
    area_to_30_m_rad: float          # integral of GZ dphi, 0..min(30, range)
    deck_edge_deg: float | None      # first heel immersing a sheer point
    assumptions: tuple[str, ...]

    def area_m_rad(self, to_deg: float) -> float:
        """Integral of GZ dphi from 0 to `to_deg` [m.rad], trapezoid on the
        computed grid, clamped to the grid's range."""
        h = np.radians(np.asarray(self.heels_deg))
        g = np.asarray(self.gz_m)
        top = min(math.radians(to_deg), float(h[-1]))
        hh = np.linspace(0.0, top, 121)
        return float(np.trapezoid(np.interp(hh, h, g), hh))


GZ_ASSUMPTIONS = (
    "watertight to the sheer; no superstructure or deckhouse buoyancy (the "
    "genome carries none) — conservative past deck-edge immersion",
    "fixed longitudinal attitude: the caller's trim, not re-solved per heel",
    "no downflooding openings are declared; deck-edge immersion is the "
    "conservative proxy angle",
)


def gz_curve(hull: Hull, disp_kg: float, kg_above_keel: float,
             rho: float = RHO_WATER, vessel=None, trim_deg: float = 0.0,
             tcg_m: float = 0.0,
             heels_deg: tuple[float, ...] | None = None) -> GZCurve:
    """Righting arm GZ(phi) for the vessel floated at each heel.

    GZ = (yB - yG) cos(phi) + (zB - zG) sin(phi) — the earth-horizontal
    separation of the centre of buoyancy from the centre of gravity, in the
    body frame whose z = 0 is the design waterline. Positive GZ restores a
    positive (starboard-down) heel. `kg_above_keel` is the same KG every GM
    in this module consumes; `tcg_m` admits an asymmetric loading.

    VALIDATED (tests/test_gapfix_physics.py): the small-angle slope
    reproduces gm() to a few percent; the wall-sided formula
    GZ = sin(phi) (GM + BM tan^2(phi)/2) is matched in its regime; the
    curve is odd in phi; and a catamaran's curve PEAKS near windward-hull
    emergence and falls — the shape the refusal block above describes and
    upright GM cannot express.
    """
    if heels_deg is None:
        heels_deg = (0.0, 2.0, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0, 25.0,
                     30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0)
    t_design = -float(hull.z_keel.min())
    z_g = kg_above_keel - t_design
    gz = []
    deck_edge = None
    m_trim = math.tan(math.radians(trim_deg))
    x = hull.x
    mid = float(x[0]) + 0.5 * float(x[-1] - x[0])
    n_hulls, _sep, d = vessel_terms(hull, vessel)
    for phi in heels_deg:
        wl0, _vol, yb, zb = _float_at_heel(hull, disp_kg, phi, trim_deg,
                                           rho, vessel)
        c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
        gz.append((yb - tcg_m) * c + (zb - z_g) * s)
        if deck_edge is None and phi > 0.0:
            m_heel = math.tan(math.radians(phi))
            offs = (0.0,) if n_hulls == 1 else (+d, -d)
            for off in offs:
                y_sh = hull.y_sheer + off
                z_wl_at_sheer = (wl0 + m_heel * y_sh
                                 + m_trim * (x - mid))
                if (hull.z_sheer <= z_wl_at_sheer).any():
                    deck_edge = phi
                    break
    gz_arr = np.asarray(gz)
    k_max = int(np.argmax(gz_arr))
    avs = None
    for k in range(k_max, len(gz_arr) - 1):
        if gz_arr[k] > 0.0 >= gz_arr[k + 1]:
            f0, f1 = gz_arr[k], gz_arr[k + 1]
            avs = heels_deg[k] + (heels_deg[k + 1] - heels_deg[k]) * (
                f0 / (f0 - f1))
            break
    curve = GZCurve(tuple(heels_deg), tuple(float(g) for g in gz_arr),
                    float(gz_arr[k_max]), float(heels_deg[k_max]), avs,
                    0.0, deck_edge, GZ_ASSUMPTIONS)
    # area_to_30 needs the finished arrays; frozen dataclass -> replace
    from dataclasses import replace as _replace
    return _replace(curve, area_to_30_m_rad=curve.area_m_rad(30.0))


@dataclass(frozen=True)
class MultihullGZAssessment:
    """NZ Part 40A App. 1 cl. 1.4 assessed AS FAR AS THE TREE CAN — and no
    further. `passes` is None, deliberately not a bool: clauses (c) and (d)
    cannot be assessed (windage is not declared anywhere in the genome or
    the mission; (d)'s text is NOT READ past the paywall), and a criterion
    with unassessed clauses has no pass to report. What this object adds
    over the old blanket refusal is MEASUREMENT: (a) and (b) now carry
    computed values against their sourced bars instead of the sentence
    "none of them is computed here"."""
    curve: GZCurve
    theta_deg: float                 # the three-way minimum of clause (a)
    theta_basis: str
    area_to_theta_m_rad: float       # measured, clause (a) LHS
    area_required_m_rad: float       # 0.055 * 30/theta, clause (a) RHS
    clause_a_satisfied: bool
    heel_at_gz_max_deg: float        # measured, clause (b) LHS
    clause_b_satisfied: bool         # >= 10 deg
    unassessable: tuple[str, ...]
    passes: None = None


def multihull_gz_assessment(hull: Hull, disp_kg: float, kg_above_keel: float,
                            rho: float = RHO_WATER, vessel=None,
                            trim_deg: float = 0.0) -> MultihullGZAssessment:
    """Clauses (a) and (b) of NZ Maritime Rules Part 40A App. 1 cl. 1.4,
    COMPUTED from the righting-arm curve (docs/research/standards/
    NATIONAL-CODES.md §8.4, read verbatim; cross-attested by AMSA NSCV C6A
    ch. 5B Table 11 cl. 5B.2). theta is the clause's own three-way minimum;
    with no downflooding openings declared, the deck-edge immersion angle
    stands in as the CONSERVATIVE proxy for the downflooding angle and the
    basis says so."""
    n_hulls, _sep, _d = vessel_terms(hull, vessel)
    if n_hulls <= 1:
        raise ValueError("multihull_gz_assessment is for n_hulls > 1; a "
                         "monohull is governed by different criteria")
    curve = gz_curve(hull, disp_kg, kg_above_keel, rho, vessel=vessel,
                     trim_deg=trim_deg)
    candidates = {"angle of maximum GZ": curve.heel_at_gz_max_deg,
                  "30 deg": 30.0}
    if curve.deck_edge_deg is not None:
        candidates["deck-edge immersion (downflooding PROXY — no openings "
                   "declared)"] = curve.deck_edge_deg
    theta_basis = min(candidates, key=candidates.get)
    theta = candidates[theta_basis]
    area = curve.area_m_rad(theta)
    area_req = 0.055 * 30.0 / max(theta, 1e-9)
    return MultihullGZAssessment(
        curve=curve, theta_deg=theta, theta_basis=theta_basis,
        area_to_theta_m_rad=area, area_required_m_rad=area_req,
        clause_a_satisfied=area >= area_req,
        heel_at_gz_max_deg=curve.heel_at_gz_max_deg,
        clause_b_satisfied=curve.heel_at_gz_max_deg >= 10.0,
        unassessable=(
            "(c) steady-wind heel <= 16 deg on h_w = P.A.Z/(9800.disp_t): "
            "the projected lateral area A above the waterline is not "
            "declared in the genome or the mission — on a solar catamaran "
            "the roof and bridge-deck house ARE the windage, and deriving A "
            "from the bare hull profile would understate the heeling "
            "moment, the flattering direction",
            "(d) the residual-area condition: the clause body is NOT READ "
            "(NATIONAL-CODES.md §8.4 records the paywall cut) — an "
            "unread requirement cannot be implemented",
        ))
