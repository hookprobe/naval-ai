"""Fidelity and cost: the knob that actually buys CPU time back.

`similitude.py` shows that geometric scale does not change the cost of a
Froude-similar CFD case — the mesh is identical at any hull size. MESH DENSITY
does, and it is the `scale` argument of `cfd.case.write_resistance_case`, a name
that has caused enough confusion to be worth restating: it is a resolution
multiplier, not a scale ratio.

EVERY CONSTANT BELOW IS MEASURED ON THIS MACHINE, FROM runs/ LOGS
=================================================================
Read out of `runs/kcs_sym/log.interFoam` (241,946 cells, symmetric, np=10, one
unbroken ExecutionTime segment, 3145 steps to t = 13.739 s):

    window t [s]      steps   dt_avg [ms]   wall/sim-s   wall per cell-step
     0.00 ->  2.43      786       3.095         241.7          3.09 us
     2.43 ->  5.85      786       4.341         229.9          4.13 us
     5.85 ->  9.52      786       4.680         109.9          2.13 us
     9.52 -> 13.74      786       5.362          90.1          2.00 us

Two things fall out, and both matter for planning:

  1. Cost per cell-step is roughly CONSTANT (2.0-4.1 us), and `runs/kcs_iso` at
     637k cells sits in the same band (2.6-3.0 us). So wall time is LINEAR in
     cell count on this machine, which is what lets a single measured constant
     predict a grid it has never run.
  2. The run gets CHEAPER as it settles: dt grows 3.1 -> 5.4 ms as the wave
     field develops and the pressure solve converges in fewer sweeps. Costing a
     run at its opening rate over-budgets it ~2.7x.

CORRECTION TO A BUDGET IN CLAUDE.md, which this model contradicts
================================================================
CLAUDE.md says of the GCI triplet: "medium is ~3x coarse and fine ~8x". Those
are CELL ratios (measured here as 2.79x and 7.79x) and they are right as cell
ratios — but they are not COST ratios. The timestep is Courant-limited, so a
sqrt(2) finer grid also takes sqrt(2) more steps:

    cost ratio = cells x steps = 2.79 x 1.414 = 3.9x   (not 3x)
                                 7.79 x 2.0   = 15.6x  (not 8x)

so a full triplet is ~21x the coarse grid, not ~12x. A plan built on the cell
ratio under-budgets the triplet by 75%. This is exactly the class of error the
subsystem exists to prevent: a cost estimated from the part of the problem that
was easy to count.

WHAT IS STILL ASSUMED, AND SAYS SO
==================================
Memory per cell has NOT been measured here — no run recorded RSS. It is carried
as an assumption with a 50% sigma and `basis='assumed'`, and `CostEstimate`
reports it as such, so a RAM-based refusal is never quoted as if it were
measured. Measuring it is one `/usr/bin/time -l` away and is owed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .cfd.case import background_counts
from .constants import G_STANDARD
from .similitude import Condition

# --- MEASURED on runs/kcs_sym, np=10, Apple M5 Pro -------------------------
# Seconds of WALL CLOCK per cell per timestep, AT np = NP_REFERENCE. The
# central value is the whole-run mean of the calibration case,
#   2157.43 s / (241946 cells x 3145 steps) = 2.835e-6
# and the sigma covers the 2.0-4.1 us window spread. Note the rate is already
# a parallel rate: it must NOT be divided by the speedup again at np=10, only
# adjusted for OTHER rank counts. Getting that wrong under-predicts by 1.7x.
# The non-circular check is runs/kcs_iso at 637k cells — a 2.6x larger mesh —
# which lands at 2.56-2.96 us/cell-step, inside this band.
CELL_STEP_S = 2.835e-6
CELL_STEP_S_SIGMA = 0.7e-6

# Effective interface Courant number. The case asks for maxAlphaCo 2, but maxCo
# 5 on the momentum equation and local velocities above the free-stream both
# bind, so the achieved dt is about half the nominal:
#   dt_nominal = 2 * fs_dz / U = 2 * 0.01024 / 2.196 = 9.33 ms
#   dt_measured (mean over 3145 steps) = 13.739 / 3145 = 4.37 ms
# ratio 0.468. basis='measured' on ONE case; re-measure for a very different
# Froude number, where the velocity field around the bow is differently peaked.
COURANT_EFFICIENCY = 0.47
MAX_ALPHA_CO = 2.0

# Total cells / background cells, after snappy refinement and layers.
# MEASURED: 241946 / 13608 = 17.78 on KCS, symmetric, hull refinement (4,5),
# 3 z-only refineMesh rounds. It is a property of the HULL and the refinement
# settings, not a universal constant — a hull with more wetted area or a
# different refinement box will differ, so it carries a wide sigma and any
# planner output that leans on it should be re-measured with a mesh-only run
# (~2 min) before a multi-hour solve is launched on the strength of it.
REFINE_FACTOR = 17.78
REFINE_FACTOR_SIGMA = 4.0

# Assumed, NOT measured — see the module docstring.
BYTES_PER_CELL = 1500.0
BYTES_PER_CELL_SIGMA = 750.0

# Parallel efficiency, MEASURED on the same 0.4 s slice of the medium grid:
#   np=5 -> 212.7 s, np=10 -> 127.2 s (1.67x), np=15 -> 153.1 s
# 15 ranks is 20% SLOWER than 10 — oversubscribing all 15 cores costs. The
# table is measured points, not a fitted Amdahl curve, because the non-monotone
# point at 15 is the whole reason the table exists.
NP_SPEEDUP = {1: 1.0, 5: 1.0, 10: 1.672, 15: 1.389}
NP_REFERENCE = 10

# This Mac's cooling cannot sustain long runs: `pmset -g log` recorded
# "Thermal Emergency Sleep" on 2026-08-04 23:19, losing a triplet. caffeinate
# does not prevent it (that is the IDLE path). Runs longer than this must be
# resumable or they are a gamble, not a plan.
THERMAL_SAFE_HOURS = 6.0

# The project's own resolution bar — RAISED 20 -> 30 on 2026-09-04, by the
# strongest single measurement this project has produced. The old 20 was a
# literature floor ("below 20 the wave field is decoration"); the KCS
# campaign then measured what sits JUST ABOVE it:
#
#   21.5 c/lambda (the old scale-1 recipe): pressure drag wandering 5-129 N
#     around a ~21 N expected mean, broadband (no mode above an 8.4%
#     explained fraction), immune to critical body damping, NOT decaying
#     with run length — drift 19/11/23% across 4/6/8 flow-throughs. The
#     free-trim case could never settle; neither could the fixed one under
#     the current bars (kcs_s1 harvests unsettled).
#   30.2 c/lambda (runs/kcs_fs30, same hull, same speed, fixed): pressure
#     ~22 N with ~1 N std, SETTLED at drift 0.7%, C_T within 4.3% of the
#     KRISO EFD on a single grid. Transfer evidence on one NavalAI design
#     (flywheel_a/flywheel_fs30, same genome): the coarse twin never
#     settled in 3.7 FT, the fine twin settled in 1.5.
#
# So 20-21 is not "just above the bar", it is measured-inadequate: a bar a
# failing configuration PASSES is the bar telling you nothing. 30 is the
# lowest resolution measured to work, not a proven optimum — a cheaper
# working point may exist in (21.5, 30.2) and nobody has bought the sweep.
# TIGHTENED, never softened; the planner's density derivation and every
# admissibility check inherit it from this one home.
MIN_CELLS_PER_WAVELENGTH = 30.0


@dataclass(frozen=True)
class Budget:
    """What the user will actually spend. A ceiling, not a target."""

    max_wall_s: float = float("inf")
    max_ram_gb: float = float("inf")
    np_procs: int = NP_REFERENCE
    resumable: bool = True
    label: str = ""

    @property
    def speedup(self) -> float:
        """Measured speedup at this rank count, interpolated between points."""
        if self.np_procs in NP_SPEEDUP:
            return NP_SPEEDUP[self.np_procs]
        pts = sorted(NP_SPEEDUP)
        if self.np_procs <= pts[0]:
            return NP_SPEEDUP[pts[0]]
        if self.np_procs >= pts[-1]:
            return NP_SPEEDUP[pts[-1]]
        lo = max(p for p in pts if p <= self.np_procs)
        hi = min(p for p in pts if p >= self.np_procs)
        f = (self.np_procs - lo) / (hi - lo)
        return NP_SPEEDUP[lo] + f * (NP_SPEEDUP[hi] - NP_SPEEDUP[lo])


MAC_M5 = Budget(max_wall_s=THERMAL_SAFE_HOURS * 3600, max_ram_gb=20.0,
                np_procs=10, label="Mac M5 Pro simulation node")

# The STATED budget, which is tighter than what the hardware survives and is
# therefore the one that governs: coarse ~15 min, medium <=2 h, fine ~4-5 h on
# 10 cores. Recorded as a constraint, not an overhead — "a configuration that
# cannot fit this is not an acceptable configuration; change the case, not the
# hours."
STATED_COARSE = Budget(max_wall_s=15 * 60, max_ram_gb=20.0, np_procs=10,
                       label="stated budget, coarse grid")
STATED_MEDIUM = Budget(max_wall_s=2 * 3600, max_ram_gb=20.0, np_procs=10,
                       label="stated budget, medium grid")
STATED_FINE = Budget(max_wall_s=5 * 3600, max_ram_gb=20.0, np_procs=10,
                     label="stated budget, fine grid")


def cells_per_wavelength(fn: float, mesh_density: float) -> float:
    """Closed form: cells across one transverse wave, from Fn and density alone.

        lambda = 2 pi Fn^2 L,   dx_fs = DOMAIN_LWL L / nx / 2^2
        =>  cells/wavelength = 2 pi Fn^2 * 4 * nx / DOMAIN_LWL

    The Lwl cancels — the same Froude-similarity that makes geometric scale
    free. What does NOT cancel is Fn, and it enters SQUARED, which is the
    non-obvious part: LOW-Froude cases are the expensive ones to resolve. At
    Fn 0.26 the scale-1 grid gives 21.5, just over the bar; at Fn 0.20 the same
    grid gives 12.7 and would be refused.

    nx COMES FROM `background_counts`, and that is the point. This function
    carried its own literal `54` — a THIRD copy of `_NX_BASE`, after the one in
    case.py and the one in the mesh writer. When the base moved 54 -> 57 (the
    measured fix that makes nx divisible by 3 at every triplet member, dropping
    the symmetric family's refinement-ratio spread from 0.85% to 0.03%), this
    copy did not move, and the closed form disagreed with the mesh it claimed
    to describe: 8.49 against the generated case's 8.94. A number declared
    twice, found by the two copies drifting apart.
    """
    nx = background_counts(mesh_density, True)[0]
    return 2.0 * math.pi * fn**2 * 4.0 * nx / DOMAIN_LWL


def density_that_clears_wave_resolution(
        fn: float, bar: float = MIN_CELLS_PER_WAVELENGTH) -> float:
    """The density that clears the bar AFTER the writer discretises it.

    `density_for_wave_resolution` inverts the floor EXACTLY, so its answer
    buys precisely `bar` cells per wavelength as a CONTINUOUS quantity — and
    the case writer then turns it into an integer background cell count.
    Rounding steps under the bar whenever the fraction is below a half, and
    a floor the pipeline's own discretisation steps under is not a floor.

    MEASURED (Mac, Block 4, 2026-08-20): all four Fn-matched coverage bands
    wrote at 19.90 cells per wavelength against a bar of 20 — the SAME 0.5%
    miss in every band, because Fn-matched cases share their rounding. A
    first fix rounded up inside `contract.mesh_prescription` and was
    CORRECT AND UNREACHED: `navalai/cfd/case.py` has zero references to
    `contract`, so the number the screen actually reports as `scale_needed`
    was still the continuous one. This is that fix at the home BOTH callers
    already share.

    Costs at most one background cell in x. `density_for_wave_resolution`
    is left exactly as it was: it answers the continuous question, which is
    the right question for the cost search that consumes it.
    """
    from .cfd.case import _NX_BASE
    d = density_for_wave_resolution(fn, bar)
    if not math.isfinite(d):
        return d
    nx = max(1, int(math.ceil(_NX_BASE * d - 1e-9)))
    return nx / float(_NX_BASE)


def density_for_wave_resolution(fn: float,
                                bar: float = MIN_CELLS_PER_WAVELENGTH) -> float:
    """Minimum mesh density that resolves the wave field at this Froude number.

    Inverts the relation above. This is the floor the cost search runs into
    from below, and it is PHYSICS — it is what stops "find the cheapest grid"
    from returning an arbitrarily cheap and arbitrarily wrong answer.
    """
    if fn <= 0.0:
        return math.inf
    # THE FOURTH COPY OF _NX_BASE, RETIRED (audit: the sibling above narrates
    # fixing 54 -> 57 while this inverse still carried 54.0 — the closed form
    # and its own inverse disagreed by 5.6%). The base is imported from the
    # mesh writer, the only place it is declared.
    from .cfd.case import _NX_BASE
    return bar * DOMAIN_LWL / (2.0 * math.pi * fn**2 * 4.0
                                * float(_NX_BASE))


@dataclass(frozen=True)
class FidelitySpec:
    """A resolution request, in NON-DIMENSIONAL terms wherever possible.

    `mesh_density` is the one cost knob (case.py's `scale`). Everything a user
    would rather express — cells per wavelength, cells along the hull — is
    DERIVED from it against a given Condition, because the mesh is generated
    from `mesh_density` and deriving the other way would put the same number in
    two places.

    `target_yplus` WAS A FIELD HERE AND IS RETIRED (2026-08-20). It defaulted
    to 30.0, and it was read by NOTHING: not by `background_cells`, not by
    `cells`, not by `free_surface_dz`, not by `estimate`, not by `admit`, not
    by any caller in the tree (`grep -rn target_yplus` found this line and the
    `first_layer_thickness` PARAMETER in `cfd/case.py`, which takes its value
    from `case._TARGET_YPLUS` and never from here). So it was a second, dead
    declaration of a number the case writer already owns — and it declared the
    WRONG one: `case._TARGET_YPLUS` is 100.0, and the docstring beside it
    records why 30 was retired there. MEASURED at y+ 30 with 3 layers at
    expansion 1.3: snappy extruded 44.98% of hull faces on iteration 0 and
    DECAYED TO ZERO over 35 iterations, i.e. no prism cells at all, while the
    summary table went on printing the requested spec. A cost model that
    reported the retired target beside a case built to the shipped one is the
    same class of receipt.

    It was RETIRED rather than re-pointed at `case._TARGET_YPLUS` because
    importing it would have kept a field nothing reads, and a value nothing
    reads cannot be wrong loudly. The wall model has ONE home,
    `cfd.case._TARGET_YPLUS`, and `tests/test_case_wiring.py` fences this
    module against declaring a second: a y+ target reappearing here would fail
    that test rather than silently disagree by 3.3x again.
    """

    mesh_density: float = 1.0
    symmetric: bool = True
    flow_throughs: float = 5.0        # domain lengths of flow; 75 s on KCS
    free_motion: bool = False
    tier: str = "L3"
    refine_factor: float = REFINE_FACTOR

    def __post_init__(self) -> None:
        if self.mesh_density <= 0.0:
            raise ValueError("mesh_density must be positive")

    def background_cells(self) -> int:
        nx, ny, *nz = background_counts(self.mesh_density, self.symmetric)
        return nx * ny * sum(nz)

    def cells(self) -> int:
        """Total cells after refinement — background x the measured factor."""
        return int(round(self.background_cells() * self.refine_factor))

    def coarser(self, r: float = math.sqrt(2.0)) -> "FidelitySpec":
        return replace(self, mesh_density=self.mesh_density / r)

    def finer(self, r: float = math.sqrt(2.0)) -> "FidelitySpec":
        return replace(self, mesh_density=self.mesh_density * r)


@dataclass(frozen=True)
class CostEstimate:
    """Predicted cost, with the basis of every component visible."""

    cells: int
    timesteps: int
    dt_s: float
    sim_time_s: float
    wall_s: float
    wall_s_sigma: float
    ram_gb: float
    ram_gb_sigma: float
    cells_per_wavelength: float
    basis: dict[str, str]

    @property
    def wall_hours(self) -> float:
        return self.wall_s / 3600.0

    def report(self) -> str:
        return "\n".join([
            f"  cells        {self.cells:,}  ({self.basis['cells']})",
            f"  dt           {self.dt_s * 1e3:.3f} ms x {self.timesteps:,} steps "
            f"= {self.sim_time_s:.1f} s simulated",
            f"  wall clock   {self.wall_hours:.2f} h +/- "
            f"{self.wall_s_sigma / 3600.0:.2f} h  ({self.basis['wall']})",
            f"  memory       {self.ram_gb:.1f} GB +/- {self.ram_gb_sigma:.1f} GB "
            f"  ({self.basis['ram']})",
            f"  wave field   {self.cells_per_wavelength:.1f} cells/wavelength "
            f"(bar {MIN_CELLS_PER_WAVELENGTH:.0f})",
        ])


def free_surface_dz(cond: Condition, spec: FidelitySpec) -> float:
    """Interface cell height [m] — the length that sets the timestep.

    Derived the way `cfd.case` derives it: the hull z-band is 0.09 Lwl split
    into nz_hull cells, then halved once per z-only refineMesh round (3), and
    once more for the snappy free-surface level-2 box... which is where the
    0.01024 m in runs/kcs_sym/case.info comes from. Reproduced here rather than
    imported because case.py computes it inside the writer; the test asserts
    the two agree on the real case, so a drift is caught rather than assumed
    away.
    """
    nz_hull = background_counts(spec.mesh_density, spec.symmetric)[3]
    dz_core = 0.09 * cond.lwl / nz_hull
    return dz_core / 2 ** 2 / 2 ** 3


def estimate(cond: Condition, spec: FidelitySpec,
             budget: Budget = MAC_M5) -> CostEstimate:
    """Predict the cost of running `cond` at `spec` on `budget`'s machine.

    Note what this does NOT depend on: `cond.lwl`, except through ratios. Halve
    the hull at fixed Froude number and every number below is unchanged. That is
    `similitude`'s point, arriving here as arithmetic rather than as an opinion.
    """
    # THE BOX GROWS WITH THE WAVE, AND SO DOES THE BILL. `cfd.case` sizes
    # the tank from `domain_x_bounds` at FIXED dx — the x count follows the
    # length — so cells scale with the domain multiple and the cell SIZE
    # (hence every resolution number below) does not. Below Fn ~0.52 this
    # factor is exactly 1.0 and the estimate is bit-identical to every one
    # recorded before 2026-08-28.
    dom = domain_lwl(cond.fn)
    domain_factor = dom / DOMAIN_LWL
    cells = int(round(spec.cells() * domain_factor))
    dz = free_surface_dz(cond, spec)
    dt = COURANT_EFFICIENCY * MAX_ALPHA_CO * dz / max(cond.speed, 1e-6)
    # Run length in flow-throughs of the ACTUAL domain — Froude-similar, so
    # the STEP COUNT is scale-invariant even though dt and T both are not.
    # A flow-through of a longer tank is a longer flow-through: this is the
    # second place the Fn^2 domain enters, and together with the cell count
    # it makes wall-clock scale as the SQUARE of the domain multiple.
    sim_time = spec.flow_throughs * dom * cond.lwl / max(cond.speed, 1e-6)
    steps = int(round(sim_time / dt))

    # CELL_STEP_S is measured AT np=NP_REFERENCE, so the correction is the
    # RATIO of speedups, not the speedup itself.
    wall = (CELL_STEP_S * cells * steps
            * NP_SPEEDUP[NP_REFERENCE] / budget.speedup)
    # Sigma: the per-cell-step band plus the refinement-factor band, in
    # quadrature. The refinement factor is the bigger of the two and is the
    # reason a mesh-only run is worth its 2 minutes before a 6-hour solve.
    rel_rate = CELL_STEP_S_SIGMA / CELL_STEP_S
    rel_refine = REFINE_FACTOR_SIGMA / spec.refine_factor
    wall_sigma = wall * math.hypot(rel_rate, rel_refine)
    if spec.free_motion:
        # 6DoF adds a mesh-motion solve and tightens dt near the ends of the
        # pitch cycle. NOT measured here (runs/kcs_free logged no ExecutionTime
        # segments), so it is a declared 20% with basis='assumed'.
        wall *= 1.2
        wall_sigma = math.hypot(wall_sigma, 0.2 * wall)

    ram = cells * BYTES_PER_CELL / 1e9
    ram_sigma = cells * BYTES_PER_CELL_SIGMA / 1e9
    # cpw uses DOMAIN_LWL and not `dom` ON PURPOSE: `background_counts`
    # returns the count for the NOMINAL tank, and case.py holds dx at that
    # value while adding x cells for the longer box. The cell size is the
    # invariant, so the resolution of the wave is unchanged by the domain
    # opening — only the number of cells is. Substituting `dom` here would
    # report a longer tank as a FINER one.
    cpw = cond.wavelength / (DOMAIN_LWL * cond.lwl / background_counts(
        spec.mesh_density, spec.symmetric)[0] / 2 ** 2)

    return CostEstimate(
        cells=cells, timesteps=steps, dt_s=dt, sim_time_s=sim_time,
        wall_s=wall, wall_s_sigma=wall_sigma, ram_gb=ram, ram_gb_sigma=ram_sigma,
        cells_per_wavelength=cpw,
        basis={
            "cells": f"background x {spec.refine_factor:.2f} measured on KCS"
                     f" x {domain_factor:.3f} domain (tank {dom:.2f} Lwl)",
            "wall": f"{CELL_STEP_S * 1e6:.1f} us/cell-step measured on "
                    f"runs/kcs_sym, np={budget.np_procs}",
            "ram": "ASSUMED 1.5 kB/cell — never measured, owed",
        })


# Domain length as a multiple of Lwl, from `cfd.case`: x in [-2.5 L, 2.0 L].
#: The hull-scale tank bounds, in Lwl — `cfd.case._DOMAIN_X`. Named here so
#: `domain_lwl` reads as the rule rather than as four magic numbers, and so
#: the fence has something to compare.
_DOMAIN_X_FRAC = (-2.5, 2.0)

DOMAIN_LWL = 4.5
# A tank resonance within this factor of the wave period contaminates the force
# signal at the frequency we are trying to measure. Declared, basis='approx'.
SEICHE_SEPARATION = 3.0


def domain_lwl(fn: float) -> float:
    """The tank length in Lwl at this Froude number — the SCHEDULING rule.

    CFD audit P1-10a, and it landed as a live number-declared-twice: on
    2026-08-28 `cfd.case.domain_x_bounds` made the tank length a function
    of SPEED (the tank must contain the ship's own wave: >= 1.5 lambda
    astern, >= 0.5 lambda ahead), and this module went on pricing every
    grid against a fixed 4.5 Lwl written out as a literal in six places.
    A cost model that does not know the box grew UNDER-PREDICTS by the
    ratio, and MEASURED at Fn 0.95 that ratio is 2.8x — the difference
    between a plan that fits the machine and one that does not.

    Scale-free by construction, which is why it takes Fn and not (L, U):
    lambda/Lwl = 2 pi Fn^2, so every term below is a pure number and the
    length cancels exactly as `similitude` says it must.

        downstream / L = max(2.5, 1.5 * 2 pi Fn^2)
        upstream   / L = max(1.0, 0.5 * 2 pi Fn^2) + 1.0

    Below Fn ~0.52 the hull terms bind and this returns exactly
    DOMAIN_LWL, so every estimate this project has ever recorded is
    bit-identical. Above it the cost rises as Fn^2 — which is the
    scheduling consequence: high-Froude runs are expensive for a reason
    that has nothing to do with the timestep, and a planner ordering
    experiments by knowledge-per-hour has to see it.

    `test_fidelity` fences this against `domain_x_bounds` itself rather
    than trusting the transcription; the two must agree at every Fn.
    """
    lam_over_l = 2.0 * math.pi * max(0.0, float(fn)) ** 2
    downstream = max(-_DOMAIN_X_FRAC[0], 1.5 * lam_over_l)
    upstream = max(_DOMAIN_X_FRAC[1] - 1.0, 0.5 * lam_over_l) + 1.0
    return downstream + upstream



def wave_speed(wavelength: float, depth: float,
               g: float = G_STANDARD) -> float:
    """Linear free-surface phase speed, FULL dispersion relation [m/s].

        c = sqrt( g/k * tanh(k h) ),  k = 2 pi / lambda

    ONE home (consolidation): `scripts/tank_resonance.py` measured with this
    and imports it from here; a shallow-water sqrt(gh) shortcut differs by
    7.6% on this project's own tank and was the first thing the measurement
    retired.
    """
    k = 2.0 * math.pi / max(wavelength, 1e-9)
    return math.sqrt(g / k * math.tanh(k * depth))


def _tank_depth(cond: Condition, depth: float | None) -> float:
    if depth is None:
        half_lambda = 0.5 * cond.wavelength
        depth = max(0.6 * cond.lwl, 1.5 * half_lambda)
    return depth


def tank_mode_periods(cond: Condition, depth: float | None = None,
                      n_max: int = 12) -> dict[int, float]:
    """Doppler-shifted apparent periods of the tank's standing modes [s].

    THE MEASURED MECHANISM (scripts/tank_resonance.py, 2026-08-13): the
    low-frequency force oscillation is a TANK MODE lambda_n = 2 L_tank / n
    carried on the current — T_n = lambda_n / (c(lambda_n) - U) — NOT the
    still-water seiche 2L/sqrt(gh) this module used to compute. Same tank at
    two speeds: measured 5.53 s and 3.67 s against Doppler predictions of
    5.64 s and 3.66 s (0.3% / 1.9%), while the seiche formula said 7.75 s
    for BOTH and matched neither. A mode whose phase speed does not outrun
    the current (c <= U) is BLOCKED — its energy holds station and it has no
    finite apparent period — and is omitted, which is itself the worst case:
    the blocked wavelength is the one that cannot drain.

    Still Froude-similar, so the resonance survives geometric scaling
    exactly as the refuted formula did: with h = 0.6 L binding,
    k_n h = 0.419 n is dimensionless, so T_n / sqrt(L/g) is a function of
    Froude number alone.
    """
    depth = _tank_depth(cond, depth)
    L_tank = domain_lwl(cond.fn) * cond.lwl
    out: dict[int, float] = {}
    for n in range(1, n_max + 1):
        lam = 2.0 * L_tank / n
        c = wave_speed(lam, depth, cond.g)
        if c > cond.speed + 1e-9:
            out[n] = lam / (c - cond.speed)
    return out


def tank_resonance_check(cond: Condition,
                         spec: FidelitySpec) -> tuple[float, float, str]:
    """(T_resonance, T_wave, verdict) for the generated domain.

    REPLACES `seiche_check` (audit G8-P0, 2026-08-14): the still-water
    seiche model was REFUTED BY MEASUREMENT — see `tank_mode_periods` — yet
    this module still refused runs on it. The reported T is the mode the
    tank actually selects: the one nearest the blocking condition c = 2U,
    where the group velocity matches the current and the wave's energy
    holds station (measured: n = 6 at Fn 0.26 on the KCS tank, 5.53 s).
    The two verdicts keep their meanings: contamination if ANY mode's
    apparent period sits on the wave period being measured; settling if the
    run is shorter than three of the slowest finite mode period.
    """
    modes = tank_mode_periods(cond)
    depth = _tank_depth(cond, None)
    t_w = cond.wavelength / max(cond.speed, 1e-6)
    sim = (spec.flow_throughs * domain_lwl(cond.fn) * cond.lwl
           / max(cond.speed, 1e-6))
    if not modes:
        return (float("inf"), t_w,
                "every tank mode is BLOCKED (c <= U): no finite resonance "
                "period exists and no force average can outlast it — "
                "lengthen the domain or add outlet damping")
    # The selected mode: nearest to blocking, c(lambda) = 2 U.
    def _c_gap(n: int) -> float:
        return abs(wave_speed(2.0 * domain_lwl(cond.fn) * cond.lwl / n,
                              depth, cond.g) - 2.0 * cond.speed)
    n_sel = min(modes, key=_c_gap)
    t_res = modes[n_sel]
    t_slow = max(modes.values())
    on_wave = [n for n, t in modes.items()
               if t_w > 0 and abs(t / t_w - 1.0) < 1.0 / SEICHE_SEPARATION]
    if on_wave:
        v = (f"tank mode n={on_wave[0]} ({modes[on_wave[0]]:.2f} s) sits ON "
             f"the wave period {t_w:.2f} s — the force signal is contaminated "
             "at exactly the frequency being measured; lengthen the domain or "
             "add outlet damping")
    elif sim < 3.0 * t_slow:
        v = (f"run is {sim / t_slow:.1f} of the slowest tank-mode period "
             f"({t_slow:.2f} s, n=1) long — too short for the tank "
             "oscillation to damp; early force averages include it")
    else:
        v = (f"tank mode n={n_sel} {t_res:.2f} s vs wave {t_w:.2f} s "
             f"({t_res / t_w:.1f}x apart), {sim / t_slow:.1f} slow-mode "
             "periods simulated: clear")
    return t_res, t_w, v


@dataclass(frozen=True)
class Refusal:
    """Why a run was not launched. Recorded, never silently downgraded."""

    reason: str
    measured: str = ""

    def __str__(self) -> str:
        return f"{self.reason}" + (f" [{self.measured}]" if self.measured else "")


def admit(cond: Condition, spec: FidelitySpec,
          budget: Budget = MAC_M5) -> tuple[bool, tuple[Refusal, ...], CostEstimate]:
    """Fail fast: decide BEFORE meshing whether this run may proceed.

    Returns (admitted, refusals, cost). A refusal is information — it is
    returned rather than raised so a planner can compare a rejected option's
    cost against an accepted one instead of losing it.

    The cost ceiling is checked against wall + 1 sigma, not the central value.
    A 50/50 chance of blowing the budget is not "within budget", and on this
    machine an over-run is not a slow answer, it is a lost run: the box goes to
    Thermal Emergency Sleep and takes the campaign with it.
    """
    cost = estimate(cond, spec, budget)
    out: list[Refusal] = []

    if cost.wall_s + cost.wall_s_sigma > budget.max_wall_s:
        out.append(Refusal(
            f"predicted {cost.wall_hours:.1f} h (+1 sigma "
            f"{(cost.wall_s + cost.wall_s_sigma) / 3600:.1f} h) exceeds the "
            f"{budget.max_wall_s / 3600:.1f} h ceiling",
            "measured rate, runs/kcs_sym"))
    if cost.ram_gb + cost.ram_gb_sigma > budget.max_ram_gb:
        out.append(Refusal(
            f"predicted {cost.ram_gb:.1f} GB exceeds the "
            f"{budget.max_ram_gb:.1f} GB ceiling",
            "ASSUMED 1.5 kB/cell — measure before trusting this refusal"))
    if cost.cells_per_wavelength < MIN_CELLS_PER_WAVELENGTH:
        out.append(Refusal(
            f"{cost.cells_per_wavelength:.1f} cells per wavelength is below the "
            f"{MIN_CELLS_PER_WAVELENGTH:.0f} bar — the wave field would not be "
            "resolved and the drag would ride on hull-local refinement",
            "CLAUDE.md: 'resolve the free surface or the whole run is "
            "decoration'"))
    t_s, t_w, verdict = tank_resonance_check(cond, spec)
    if verdict.startswith("tank mode") and "sits ON" in verdict:
        out.append(Refusal(verdict,
                           "T_n = lambda_n/(c(lambda_n) - U), the Doppler-"
                           "shifted tank mode scripts/tank_resonance.py "
                           "MEASURED (5.53 s vs 5.64 s predicted; the "
                           "still-water seiche predicted 7.75 s and matched "
                           "nothing)"))
    if (cost.wall_hours > THERMAL_SAFE_HOURS and not budget.resumable):
        out.append(Refusal(
            f"{cost.wall_hours:.1f} h exceeds the {THERMAL_SAFE_HOURS:.0f} h "
            "this machine sustains without a Thermal Emergency Sleep, and the "
            "run was not marked resumable",
            "pmset -g log, 2026-08-04 23:19"))
    return (not out), tuple(out), cost


def cheapest_admissible(cond: Condition, budget: Budget = MAC_M5,
                        base: FidelitySpec | None = None,
                        steps: int = 8, r: float = math.sqrt(2.0),
                        ) -> tuple[FidelitySpec | None, tuple[Refusal, ...]]:
    """The COARSEST mesh density that still clears every admissibility bar.

    This is the search the brief wanted over geometric scale, run over the
    variable that actually moves the cost. It searches upward from the coarsest
    density, so it returns the cheapest option rather than the best one: the
    resolution bars (cells per wavelength) are what stop it going cheaper, and
    they are physics, not preference.

    Returns (None, refusals) when nothing fits — with the refusals from the
    cheapest candidate, which is the most informative failure: if even the
    coarsest grid blows the budget, no amount of coarsening helps and the
    honest answer is that this machine cannot answer this question.
    """
    base = base or FidelitySpec()
    candidates = [replace(base, mesh_density=base.mesh_density * r ** (i - steps // 2))
                  for i in range(steps)]
    candidates.sort(key=lambda s: s.mesh_density)
    first_refusals: tuple[Refusal, ...] = ()
    for spec in candidates:
        ok, refusals, _ = admit(cond, spec, budget)
        if not first_refusals:
            first_refusals = refusals
        if ok:
            return spec, ()
    return None, first_refusals
