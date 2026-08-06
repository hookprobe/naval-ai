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

# The project's own resolution bar: below 20 cells per wavelength the wave field
# is decoration and the drag rides on hull-local refinement instead.
MIN_CELLS_PER_WAVELENGTH = 20.0


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

        lambda = 2 pi Fn^2 L,   dx_fs = 4.5 L / nx / 2^2,   nx = 54 * density
        =>  cells/wavelength = 2 pi Fn^2 * 4 * nx / 4.5 = 5.585 Fn^2 nx

    The Lwl cancels — the same Froude-similarity that makes geometric scale
    free. What does NOT cancel is Fn, and it enters SQUARED, which is the
    non-obvious part: LOW-Froude cases are the expensive ones to resolve. At
    Fn 0.26 the scale-1 grid gives 20.4, just over the bar; at Fn 0.20 the same
    grid gives 12.1 and would be refused.
    """
    nx = max(int(round(54 * mesh_density)), 20)
    return 2.0 * math.pi * fn**2 * 4.0 * nx / 4.5


def density_for_wave_resolution(fn: float,
                                bar: float = MIN_CELLS_PER_WAVELENGTH) -> float:
    """Minimum mesh density that resolves the wave field at this Froude number.

    Inverts the relation above. This is the floor the cost search runs into
    from below, and it is PHYSICS — it is what stops "find the cheapest grid"
    from returning an arbitrarily cheap and arbitrarily wrong answer.
    """
    if fn <= 0.0:
        return math.inf
    return bar * 4.5 / (2.0 * math.pi * fn**2 * 4.0 * 54.0)


@dataclass(frozen=True)
class FidelitySpec:
    """A resolution request, in NON-DIMENSIONAL terms wherever possible.

    `mesh_density` is the one cost knob (case.py's `scale`). Everything a user
    would rather express — cells per wavelength, cells along the hull — is
    DERIVED from it against a given Condition, because the mesh is generated
    from `mesh_density` and deriving the other way would put the same number in
    two places.
    """

    mesh_density: float = 1.0
    symmetric: bool = True
    flow_throughs: float = 5.0        # domain lengths of flow; 75 s on KCS
    target_yplus: float = 30.0
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
    cells = spec.cells()
    dz = free_surface_dz(cond, spec)
    dt = COURANT_EFFICIENCY * MAX_ALPHA_CO * dz / max(cond.speed, 1e-6)
    # Run length in flow-throughs of the 4.5 Lwl domain — Froude-similar, so
    # the STEP COUNT is scale-invariant even though dt and T both are not.
    sim_time = spec.flow_throughs * 4.5 * cond.lwl / max(cond.speed, 1e-6)
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
    cpw = cond.wavelength / (4.5 * cond.lwl / background_counts(
        spec.mesh_density, spec.symmetric)[0] / 2 ** 2)

    return CostEstimate(
        cells=cells, timesteps=steps, dt_s=dt, sim_time_s=sim_time,
        wall_s=wall, wall_s_sigma=wall_sigma, ram_gb=ram, ram_gb_sigma=ram_sigma,
        cells_per_wavelength=cpw,
        basis={
            "cells": f"background x {spec.refine_factor:.2f} measured on KCS",
            "wall": f"{CELL_STEP_S * 1e6:.1f} us/cell-step measured on "
                    f"runs/kcs_sym, np={budget.np_procs}",
            "ram": "ASSUMED 1.5 kB/cell — never measured, owed",
        })


# Domain length as a multiple of Lwl, from `cfd.case`: x in [-2.5 L, 2.0 L].
DOMAIN_LWL = 4.5
# A tank resonance within this factor of the wave period contaminates the force
# signal at the frequency we are trying to measure. Declared, basis='approx'.
SEICHE_SEPARATION = 3.0


def seiche_period(cond: Condition, depth: float | None = None) -> float:
    """Fundamental longitudinal sloshing period of the numerical tank [s].

        T = 2 L_tank / sqrt(g h)

    Note what is NOT in that expression: the hull. It is a property of the BOX,
    so it does not go away by choosing a better hull or a finer mesh, and — the
    part that matters for a scaling engine — it is Froude-similar and therefore
    survives scaling exactly. With the depth floor binding (h = 0.6 L) and the
    domain at 4.5 L:

        T_seiche / sqrt(L/g) = 2 * 4.5 / sqrt(0.6) = 11.62
        T_wave   / sqrt(L/g) = 2 pi Fn

    so their RATIO is a function of Froude number alone. Shrinking the model
    carries the resonance along with it into every case, unchanged. Depth is
    already sized against the wave (max(0.6 L, 1.5 lambda/2)); LENGTH is not,
    and this is the check that says so.
    """
    if depth is None:
        half_lambda = 0.5 * cond.wavelength
        depth = max(0.6 * cond.lwl, 1.5 * half_lambda)
    return 2.0 * DOMAIN_LWL * cond.lwl / math.sqrt(cond.g * depth)


def seiche_check(cond: Condition, spec: FidelitySpec) -> tuple[float, float, str]:
    """(T_seiche, T_wave, verdict) for the generated domain.

    MEASURED on runs/kcs_sym (Lwl 7.2786 m, U 2.196 m/s, depth 4.3672 m):
    T_seiche = 10.0 s against a wave period of 1.41 s — a factor of 7.1 apart,
    so the resonance does NOT sit on the wave frequency. But the run had only
    reached t = 13.7 s when it stopped, i.e. 1.4 seiche periods: any force
    average taken from that log is taken across an incompletely damped tank
    oscillation, not across a settled flow. That is a settling-time finding,
    not a frequency-contamination one, and the two are worth separating.
    """
    t_s = seiche_period(cond)
    t_w = cond.wavelength / max(cond.speed, 1e-6)
    sim = spec.flow_throughs * DOMAIN_LWL * cond.lwl / max(cond.speed, 1e-6)
    if t_w > 0 and abs(t_s / t_w - 1.0) < 1.0 / SEICHE_SEPARATION:
        v = (f"tank seiche {t_s:.2f} s sits ON the wave period {t_w:.2f} s — "
             "the force signal is contaminated at exactly the frequency being "
             "measured; lengthen the domain or add outlet damping")
    elif sim < 3.0 * t_s:
        v = (f"run is {sim / t_s:.1f} seiche periods long ({t_s:.2f} s each) — "
             "too short for the tank oscillation to damp; early force averages "
             "include it")
    else:
        v = (f"seiche {t_s:.2f} s vs wave {t_w:.2f} s ({t_s / t_w:.1f}x apart), "
             f"{sim / t_s:.1f} periods simulated: clear")
    return t_s, t_w, v


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
    t_s, t_w, verdict = seiche_check(cond, spec)
    if verdict.startswith("tank seiche"):
        out.append(Refusal(verdict, f"T_seiche = 2 x {DOMAIN_LWL} Lwl / "
                                    f"sqrt(g h) = {t_s:.2f} s"))
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
