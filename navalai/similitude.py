"""Similitude: dimensionless state, scale transforms, and HONEST scale effects.

WHY THIS MODULE EXISTS, AND WHY IT IS NOT A COST OPTIMISER
==========================================================
The brief that motivated this subsystem proposed treating GEOMETRIC SCALE as a
search variable to make CFD cheaper: try 1:1, 1:20, 1:50, 1:100 and keep the
cheapest that clears a confidence bar. That premise is false for this pipeline,
and the pipeline itself proves it.

`cfd.case.background_counts` takes no `lwl`. Every domain extent is a multiple
of Lwl and the tank depth is max(0.6 L, 1.5 lambda/2) with lambda/L = 2 pi Fn^2,
so at a fixed Froude number the mesh is Froude-similar. MEASURED by generating
three cases at Fn 0.26 and diffing case.info:

    hull                Lwl [m]         Re     background cells
    1:100 of the ship    2.3000  2.492e+06                13608
    KCS model 1:31.6     7.2786  1.403e+07                13608
    KCS ship 1:1       230.0000  2.492e+09                13608

A 100:1 span of hull size and the same mesh to the cell. The timestep is
Courant-limited (dt ~ dx/U) and the run length is a fixed number of
flow-throughs (T ~ L/U), so the STEP COUNT is scale-invariant as well. Shrinking
the geometry therefore costs exactly the same CPU while dropping Reynolds number
by lambda^1.5 (1:50 -> 354x) and Weber number by lambda^2. It is strictly worse.

Model scale is what a TOWING TANK is forced into, because a 230 m basin does not
exist. CFD has no such constraint. So this module's job is NOT to pick a cheap
scale — `fidelity.py` owns cost, via mesh density, which is the real knob. This
module's job is the other one, and it is a real one:

  1. Reproduce a scale a MEASUREMENT was taken at, so we can compare like with
     like. Every anchor this project has or wants is model-scale: KCS is already
     run at 1:31.5995 because that is where the EFD data lives, and the owed
     second anchor (Fridsma, DSYHS) is model-scale too.
  2. Say out loud which dimensionless groups the comparison BREAKS and by how
     much, instead of letting the mismatch hide inside an agreeing number.

Honesty rule 1 (`CLAUDE.md`) says every quantity carries {value, tier, sigma}.
A scaled quantity additionally carries WHICH SIMILARITY LAW produced it and
WHICH GROUPS WERE VIOLATED getting there, because that is where its real error
comes from.

REFERENCES
  ITTC 7.5-02-01-03  Fresh Water and Seawater Properties (rho, nu at 15 C)
  ITTC 7.5-02-02-01  Resistance Test (model size, turbulence stimulation)
  ITTC 7.5-02-03-01.4 1978 Performance Prediction Method (see extrapolate.py)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum

from .geometry import G

# ITTC 7.5-02-01-03 at 15 C. The repo's `geometry.RHO_WATER` is 1000.0 for the
# Danube dayboat SKUs; these are the values a tank quotes its Reynolds number
# with, so a benchmark comparison must use them or it compares two different
# Reynolds numbers and calls the difference physics.
FRESH_WATER_15C = (999.0, 1.13902e-6)      # (rho [kg/m3], nu [m2/s])
SEA_WATER_15C = (1026.0, 1.18831e-6)

# Surface tension, water/air at 15 C [N/m]. basis='approx' — it is a handbook
# value, not an ITTC-procedure value, and it only ever feeds a WARNING here.
SIGMA_WATER = 0.0735

# --- Practice thresholds. These are NOT derived; they are what tanks do. ------
# ITTC 7.5-02-02-01 requires turbulence stimulation on resistance models and the
# accepted floor for a model test is Re ~ 1e6; below roughly 5e6 the boundary
# layer is transitional enough that the stimulation device, not the hull, sets
# where transition happens. Carried as declared constants with basis='approx'
# so that `limits.py`'s rule holds: a threshold exists ONCE, and it is visible.
RE_MODEL_FLOOR = 1.0e6      # below: a model test is not accepted at all
RE_TRIP_FLOOR = 5.0e6       # below: transition is device-controlled, not hull-
# Weber number below which surface tension materially alters the free surface
# (spray sheets fail to break up, bow-wave crests are held together). Quoted in
# the planing-craft literature as the reason small models over-read spray drag.
WE_FLOOR = 200.0


class Similarity(str, Enum):
    """Which dimensionless group is held EQUAL between ship and model."""

    FROUDE = "froude"        # gravity waves — the default for ship resistance
    REYNOLDS = "reynolds"    # viscous — deeply submerged / no free surface
    WEBER = "weber"          # surface tension — spray, droplet breakup
    EULER = "euler"          # pressure — cavitation tunnels
    CAUCHY = "cauchy"        # elastic — hydroelastic slamming models


# Exponent p in  ship_value = model_value * lambda**p,  under FROUDE similarity
# in the SAME fluid (rho_s == rho_m). Derived, not tabulated from memory:
#   L ~ lambda            (definition of the scale ratio)
#   U ~ lambda^0.5        (Fn equal => U/sqrt(gL) equal, g equal)
#   t ~ lambda^0.5        (t = L/U)
#   a ~ lambda^0          (a = U^2/L)  -- accelerations are UNCHANGED
#   F ~ lambda^3          (F = rho U^2 L^2)
#   p ~ lambda            (p = rho U^2)
#   P ~ lambda^3.5        (P = F U)
# Densities that differ (fresh model, salt ship) are handled by `rho_ratio`
# in `scale_value`, because rho enters F and p linearly and L, U, t not at all.
FROUDE_EXPONENTS: dict[str, float] = {
    "length": 1.0, "area": 2.0, "volume": 3.0, "mass": 3.0,
    "velocity": 0.5, "time": 0.5, "frequency": -0.5, "acceleration": 0.0,
    "angle": 0.0, "force": 3.0, "moment": 4.0, "pressure": 1.0,
    "power": 3.5, "density": 0.0,
}
# Quantities whose scale factor carries rho linearly (the rest are kinematic).
_RHO_LINEAR = {"mass", "force", "moment", "pressure", "power"}


@dataclass(frozen=True)
class Condition:
    """A hull at a speed in a fluid — everything the groups below need.

    Immutable. `at_scale()` returns a NEW Condition; nothing is mutated, so a
    PhysicalModel can hold both endpoints of a scaling without either drifting.
    """

    lwl: float                       # waterline length [m]
    speed: float                     # [m/s]
    rho: float = FRESH_WATER_15C[0]  # [kg/m3]
    nu: float = FRESH_WATER_15C[1]   # kinematic viscosity [m2/s]
    sigma_surface: float = SIGMA_WATER
    g: float = G
    label: str = ""

    def __post_init__(self) -> None:
        if self.lwl <= 0.0:
            raise ValueError(f"lwl must be positive, got {self.lwl}")
        if self.speed < 0.0:
            raise ValueError(f"speed must be non-negative, got {self.speed}")

    @property
    def fn(self) -> float:
        """Length Froude number U / sqrt(g L)."""
        return self.speed / math.sqrt(self.g * self.lwl)

    @property
    def re(self) -> float:
        """Length Reynolds number U L / nu."""
        return self.speed * self.lwl / self.nu

    @property
    def we(self) -> float:
        """Weber number rho U^2 L / sigma."""
        return self.rho * self.speed**2 * self.lwl / self.sigma_surface

    @property
    def wavelength(self) -> float:
        """Deep-water wavelength of the hull's own transverse wave, 2 pi U^2/g.

        Same expression `cfd.case` sizes the tank depth with. lambda/L is
        2 pi Fn^2, which is why the domain is Froude-similar.
        """
        return 2.0 * math.pi * self.speed**2 / self.g

    def at_scale(self, lam: float, rho: float | None = None,
                 nu: float | None = None, label: str = "") -> "Condition":
        """This condition reproduced at 1:lam under FROUDE similarity.

        lam > 1 shrinks (a 1:31.6 model of a ship). The fluid may change with
        it — a tank tests a saltwater ship in fresh water — and then the
        Reynolds and Weber ratios are NOT the clean powers of lambda; that is
        exactly why `ScaleEffects` measures them rather than assuming them.
        """
        if lam <= 0.0:
            raise ValueError(f"scale ratio must be positive, got {lam}")
        return Condition(
            lwl=self.lwl / lam,
            speed=self.speed / math.sqrt(lam),
            rho=self.rho if rho is None else rho,
            nu=self.nu if nu is None else nu,
            sigma_surface=self.sigma_surface, g=self.g,
            label=label or (f"{self.label} at 1:{lam:g}" if self.label else ""))


def scale_value(value: float, quantity: str, lam: float,
                to: str = "ship", rho_ratio: float = 1.0) -> float:
    """Transform one quantity between ship and model under Froude similarity.

    `lam` is the scale ratio L_ship / L_model (so 31.5995 for KCS). `to='ship'`
    converts a model-scale number up; `to='model'` converts a ship number down.
    `rho_ratio` is rho_ship / rho_model, applied only to the quantities that
    carry density linearly — a fresh-water tank result for a seawater ship is
    2.7% light in force and nothing at all in velocity.
    """
    if quantity not in FROUDE_EXPONENTS:
        raise KeyError(f"no Froude exponent for {quantity!r}; "
                       f"known: {sorted(FROUDE_EXPONENTS)}")
    if to not in ("ship", "model"):
        raise ValueError(f"`to` must be 'ship' or 'model', got {to!r}")
    p = FROUDE_EXPONENTS[quantity]
    factor = lam**p * (rho_ratio if quantity in _RHO_LINEAR else 1.0)
    return value * factor if to == "ship" else value / factor


@dataclass(frozen=True)
class GroupMismatch:
    """One dimensionless group, and what the scaling did to it."""

    group: str
    ship: float
    model: float
    preserved: bool
    note: str = ""

    @property
    def ratio(self) -> float:
        """model / ship. 1.0 == preserved."""
        return self.model / self.ship if self.ship else float("nan")


@dataclass(frozen=True)
class ScaleEffects:
    """The full accounting: what was held, what was broken, what it costs.

    This is the object that makes model-scale data usable honestly. It is
    deliberately not a single scalar 'confidence' — a Reynolds violation is
    correctable (that is what ITTC-78 extrapolation is FOR) while a Weber
    violation is not, and collapsing both into one number hides the difference
    that decides whether a comparison is admissible.
    """

    lam: float
    mode: Similarity
    mismatches: tuple[GroupMismatch, ...]
    warnings: tuple[str, ...]

    def get(self, group: str) -> GroupMismatch:
        for m in self.mismatches:
            if m.group == group:
                return m
        raise KeyError(group)

    @property
    def preserved(self) -> tuple[str, ...]:
        return tuple(m.group for m in self.mismatches if m.preserved)

    @property
    def violated(self) -> tuple[str, ...]:
        return tuple(m.group for m in self.mismatches if not m.preserved)

    @property
    def admissible(self) -> bool:
        """False when a violation is NOT correctable by a standard procedure.

        Reynolds mismatch is expected and handled (ITTC-78). A model below the
        Reynolds floor, or a Weber number under WE_FLOOR, is not: no
        extrapolation procedure exists to undo laminar flow or surface-tension-
        held spray, so the result answers a different question than the ship.
        """
        return not self.warnings

    def report(self) -> str:
        lines = [f"scale 1:{self.lam:g} under {self.mode.value} similarity"]
        for m in self.mismatches:
            mark = "held" if m.preserved else f"x{m.ratio:.3g}"
            lines.append(f"  {m.group:9s} ship {m.ship:.4g}  "
                         f"model {m.model:.4g}  [{mark}]"
                         + (f"  {m.note}" if m.note else ""))
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return "\n".join(lines)


def scale_effects(ship: Condition, model: Condition,
                  mode: Similarity = Similarity.FROUDE) -> ScaleEffects:
    """Measure every group on both conditions and report the damage.

    Nothing here is assumed from the scale ratio: the numbers are computed from
    the two Conditions as given, so a tank that ran 2% off the target speed, or
    in fresh water when the ship is in salt, shows up as a real mismatch rather
    than a clean lambda^-1.5 that was never actually achieved.
    """
    lam = ship.lwl / model.lwl
    tol = 1e-3        # relative; a 0.1% group difference is bookkeeping, not physics
    groups = [
        ("froude", ship.fn, model.fn,
         "gravity waves — the group ship resistance is scaled on"),
        ("reynolds", ship.re, model.re,
         "viscous; correctable by ITTC-78 extrapolation, NOT by meshing harder"),
        ("weber", ship.we, model.we,
         "surface tension; NO standard correction exists"),
    ]
    mismatches = tuple(
        GroupMismatch(name, s, m, abs(m / s - 1.0) <= tol if s else False, note)
        for name, s, m, note in groups)

    warn: list[str] = []
    held = {Similarity.FROUDE: "froude", Similarity.REYNOLDS: "reynolds",
            Similarity.WEBER: "weber"}.get(mode)
    if held is not None:
        m = next(x for x in mismatches if x.group == held)
        if not m.preserved:
            warn.append(f"{mode.value} similarity was requested but {held} is "
                        f"not equal (model/ship = {m.ratio:.4g}); the scaling "
                        f"law this model claims does not hold")
    if model.re < RE_MODEL_FLOOR:
        warn.append(f"model Re {model.re:.3g} is below the {RE_MODEL_FLOOR:.0e} "
                    "floor for an accepted resistance model (ITTC 7.5-02-02-01) "
                    "— the boundary layer is substantially laminar and no "
                    "extrapolation undoes that")
    elif model.re < RE_TRIP_FLOOR:
        warn.append(f"model Re {model.re:.3g} < {RE_TRIP_FLOOR:.0e}: transition "
                    "is set by the turbulence-stimulation device, not the hull; "
                    "a CFD model at this Re has no such device and will not "
                    "reproduce the tank")
    if model.we < WE_FLOOR:
        warn.append(f"model We {model.we:.3g} < {WE_FLOOR:g}: surface tension "
                    "holds the free surface together at this size; spray and "
                    "crest breakup are not scaled and cannot be corrected")
    return ScaleEffects(lam, mode, mismatches, tuple(warn))


@dataclass(frozen=True)
class PhysicalModel:
    """The immutable object every downstream stage consumes instead of numbers.

    It is the single source of truth for ONE analysis of ONE hull: the ship it
    represents, the condition actually simulated or measured, how the two are
    related, and what that relation broke. `fidelity.FidelitySpec` and its cost
    estimate hang off it; `evidence.py` cites it.

    Immutability is the point. The recurring defect in this codebase is a number
    declared twice (see `limits.py`), and a mutable model handed down a pipeline
    is the same defect with extra steps: stage 4 edits the speed, stage 6 reads
    the original, and the two disagree for the rest of the run. `with_()`
    returns a new instance so a change is always visible as a new object.
    """

    ship: Condition
    simulated: Condition
    mode: Similarity = Similarity.FROUDE
    question: str = ""
    effects: ScaleEffects | None = None
    fidelity: object | None = None        # fidelity.FidelitySpec (avoid a cycle)
    notes: tuple[str, ...] = ()

    @property
    def lam(self) -> float:
        """Scale ratio L_ship / L_simulated. 1.0 for a full-scale computation."""
        return self.ship.lwl / self.simulated.lwl

    @property
    def full_scale(self) -> bool:
        return abs(self.lam - 1.0) < 1e-9

    def with_(self, **kw) -> "PhysicalModel":
        """A NEW model with fields replaced; effects re-measured if needed."""
        m = replace(self, **kw)
        if "ship" in kw or "simulated" in kw or "mode" in kw:
            m = replace(m, effects=scale_effects(m.ship, m.simulated, m.mode))
        return m

    def to_ship(self, value: float, quantity: str) -> float:
        """Lift a simulated/measured quantity to full scale (kinematic + rho)."""
        return scale_value(value, quantity, self.lam, "ship",
                           rho_ratio=self.ship.rho / self.simulated.rho)

    def to_model(self, value: float, quantity: str) -> float:
        return scale_value(value, quantity, self.lam, "model",
                           rho_ratio=self.ship.rho / self.simulated.rho)


def physical_model(ship: Condition, lam: float = 1.0,
                   mode: Similarity = Similarity.FROUDE,
                   question: str = "",
                   rho: float | None = None, nu: float | None = None,
                   ) -> PhysicalModel:
    """Build a PhysicalModel for `ship` analysed at 1:lam.

    lam = 1.0 (the default) is FULL SCALE, and for CFD it is almost always the
    right answer: it costs the same as any other scale in this pipeline and it
    is the only one with no Reynolds or Weber violation to explain away. Choose
    lam > 1 when you are reproducing a measurement that exists at that scale.
    """
    sim = ship if lam == 1.0 and rho is None and nu is None else \
        ship.at_scale(lam, rho=rho, nu=nu)
    return PhysicalModel(ship=ship, simulated=sim, mode=mode, question=question,
                         effects=scale_effects(ship, sim, mode))
