"""BuildPlan 2 V2.1 — the arrangement grammar, its AST, and L0-A.

`hull_ast.py` is the model this file copies deliberately: a hierarchy above a
flat vector, every node validating itself, and a gate that runs before any
geometry is constructed. BuildPlan2-FullVessel.md §2 draws the hierarchy:

  Vessel
   ├─ Envelope        from the geometry kernel: interior volume, sole z, deck plan
   ├─ Interior zones  spaces: berth | galley | head | saloon | nav | stowage | machinery
   │    each space = envelope box + function tags + adjacency prefs + masses
   └─ Deck zones      Z1/Z2/Z3 (ISO 15085) + cockpit + side decks + barriers

and §3 sets the bar: *"L0-A algebraic feasibility (overlap, envelope, min
dims) < 10 ms. Gate V2.1: the Solar-Liveaboard reference layout (hand-authored)
round-trips and passes L0-A; violations report reasons."*

WHAT IS IN SCOPE HERE, AND WHAT IS EMPHATICALLY NOT
---------------------------------------------------
L0-A is the ALGEBRAIC floor, the arrangement's counterpart to `grammar.check`.
Three rule families and no more: a box is inside the envelope, boxes do not
occupy the same volume, and a box is not smaller than its function's floor.

  - Adjacency preferences are PARSED AND CARRIED, never checked. They are the
    soft objective V2.3's GA optimises (BuildPlan2 §1.5's ISA vocabulary), and
    a soft preference enforced as a hard gate is a gate nobody can satisfy.
  - Percentile envelopes, circulation widths, heel-aware sole angles and the
    ISO 15085 deck assessment are TIER E — V2.2 — and are not attempted here.
    `navalai/rules/ergonomics.py` already owns the deck-area limb of that.
  - There is no solver. V2.3 is the CP+GA generator and BuildPlan2 §4 risk 4
    says in as many words that it carries the schedule risk. The flat vector
    below is the interface it will consume; writing the optimiser here would
    be borrowing that risk a phase early.

NUMBERS COME FROM `refdata`, ALWAYS
-----------------------------------
Not one dimensional literal appears in the rules. Every minimum dimension is a
`RefValue` from `navalai/refdata/ergonomics.py` carrying its `source` and
`basis`, and a violation REPORTS them — so a report says which document the
bar came from and how strongly it is attributable, not merely that something
is too small. Two floors are arithmetic on refdata values rather than new
constants (`_galley_min_height_mm`), because a derived number typed out again
is the "declared twice" defect this project keeps catching.

MASS: ONE POSITIONED WEIGHT MODEL, NOT A SECOND PLACEMENT TABLE
---------------------------------------------------------------
A `Space` declares a mass, and its POSITION is its box — there is no table of
LCG fractions anywhere in this module. That is not a stylistic choice: the
2026-08-05 audit found three placement tables that disagreed by 0.7 m on
payload LCG, and `weights.MassItem` exists to be the one truth. `mass_items()`
emits tier-'E' MassItems straight from the boxes, so moving a berth aft moves
the LCG by construction.

The corollary is `supersede_outfit()`. `energy.weight_items` already declares a
lump 'outfit' bucket at `OUTFIT_KG_PER_M * lwl`, placed at 0.50 LWL. The
interior spaces here ARE that outfit, described properly. Adding both lists
double-counts roughly half a tonne on a 10 m boat, so the merge is a function
rather than a docstring instruction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum

import numpy as np

from . import limits
# `_halfbreadth_at` is the geometry kernel's own section-interpolation. Reading
# a private helper is the lesser evil: the alternative is a second
# implementation of "where is the hull at this z", and this codebase's
# recurring defect is a thing declared twice.
from .geometry import Hull, _halfbreadth_at
from .refdata import RefValue
from .refdata import ergonomics as E
from .weights import MassItem

# --------------------------------------------------------------- vocabulary


class Function(Enum):
    """The interior space vocabulary, verbatim from BuildPlan2 §2."""

    BERTH = "berth"
    GALLEY = "galley"
    HEAD = "head"
    SALOON = "saloon"
    NAV = "nav"
    STOWAGE = "stowage"
    MACHINERY = "machinery"


class DeckKind(Enum):
    COCKPIT = "cockpit"
    SIDE_DECK = "side-deck"
    FOREDECK = "foredeck"
    AFTDECK = "aftdeck"


class Zone(Enum):
    """ISO 15085:2024 risk-based deck zones.

    The zone SYSTEM is verified (`refdata.ergonomics.DECK_ZONE_ACCESS`); the
    per-zone EQUIPMENT lists are paywalled and recorded absent. So a zone label
    is carried and reported, and no equipment is inferred from it.
    """

    Z1 = "Z1"       # access at any time
    Z2 = "Z2"       # access at or below 4 kn
    Z3 = "Z3"       # access nearly stationary


class Adjacency(Enum):
    """ISA's soft-constraint vocabulary (BuildPlan2 §1.5): adjacency and
    separation. Carried by the AST, optimised by V2.3, NEVER gated by L0-A."""

    PREFER = "prefer"
    AVOID = "avoid"


# ------------------------------------------------------------------- geometry


@dataclass(frozen=True)
class Box:
    """An axis-aligned interior volume in the hull frame.

    Frame is `weights.py`'s and `grammar.py`'s, so a box needs no conversion to
    become a mass: x = 0 at the transom and +forward, z = 0 at the design
    waterline and +up, y = 0 on centreline and +starboard.
    """

    x0: float
    x1: float
    y0: float
    y1: float
    z0: float
    z1: float

    SLOTS = ("x0", "x1", "y0", "y1", "z0", "z1")

    @property
    def dx(self) -> float:
        return self.x1 - self.x0

    @property
    def dy(self) -> float:
        return self.y1 - self.y0

    @property
    def dz(self) -> float:
        return self.z1 - self.z0

    @property
    def centre(self) -> tuple[float, float, float]:
        return (0.5 * (self.x0 + self.x1),
                0.5 * (self.y0 + self.y1),
                0.5 * (self.z0 + self.z1))

    @property
    def volume(self) -> float:
        return max(self.dx, 0.0) * max(self.dy, 0.0) * max(self.dz, 0.0)

    @property
    def plan_long(self) -> float:
        """Longer of the two PLAN dimensions [m].

        Minimum dimensions are compared long-to-long and short-to-short rather
        than x-to-length, because orientation is a layout decision: an aft
        cabin double lies athwartships and a quarter berth lies fore-and-aft,
        and both are berths. An axis-keyed floor would pass one and fail the
        other for no reason a naval architect would recognise.
        """
        return max(self.dx, self.dy)

    @property
    def plan_short(self) -> float:
        return min(self.dx, self.dy)

    @property
    def half_beam(self) -> float:
        """Largest |y| the box reaches — what the hull has to be wide enough for."""
        return max(abs(self.y0), abs(self.y1))

    def overlaps(self, other: "Box", tol: float = 0.0) -> bool:
        """True if the two boxes share volume by more than `tol` on every axis.

        `tol` is a TOUCHING allowance, not a fudge: two spaces that share a
        bulkhead have equal coordinates on that face and must not be reported
        as overlapping.
        """
        return (min(self.x1, other.x1) - max(self.x0, other.x0) > tol
                and min(self.y1, other.y1) - max(self.y0, other.y0) > tol
                and min(self.z1, other.z1) - max(self.z0, other.z0) > tol)

    def to_slots(self) -> tuple[float, ...]:
        return (self.x0, self.x1, self.y0, self.y1, self.z0, self.z1)

    @staticmethod
    def from_slots(s) -> "Box":
        return Box(*(float(v) for v in s))


@dataclass(frozen=True)
class PlanBox:
    """A deck zone's footprint. Deck zones are 2-D by nature: they are areas of
    a surface, and their third dimension is the barrier standing on them."""

    x0: float
    x1: float
    y0: float
    y1: float

    SLOTS = ("x0", "x1", "y0", "y1")

    @property
    def dx(self) -> float:
        return self.x1 - self.x0

    @property
    def dy(self) -> float:
        return self.y1 - self.y0

    @property
    def plan_long(self) -> float:
        return max(self.dx, self.dy)

    @property
    def plan_short(self) -> float:
        return min(self.dx, self.dy)

    @property
    def half_beam(self) -> float:
        return max(abs(self.y0), abs(self.y1))

    @property
    def centre(self) -> tuple[float, float]:
        return (0.5 * (self.x0 + self.x1), 0.5 * (self.y0 + self.y1))

    def overlaps(self, other: "PlanBox", tol: float = 0.0) -> bool:
        return (min(self.x1, other.x1) - max(self.x0, other.x0) > tol
                and min(self.y1, other.y1) - max(self.y0, other.y0) > tol)

    def to_slots(self) -> tuple[float, ...]:
        return (self.x0, self.x1, self.y0, self.y1)

    @staticmethod
    def from_slots(s) -> "PlanBox":
        return PlanBox(*(float(v) for v in s))


@dataclass(frozen=True)
class Trunk:
    """A DECLARED coachroof, and the only thing in this module the geometry
    kernel does not know about.

    The hull grammar emits a flush deck at the sheer — `Hull` has `y_sheer` and
    `z_sheer` and no superstructure — so on a 10 m hull with D = 1.55 m and
    T = 0.55 m the whole interior is 1.5 m tall and NOTHING can stand up in it.
    Standing headroom on such a boat comes from a coachroof, which is a real
    part of the vessel that this platform does not yet generate.

    Declaring it here is the honest option, and it is labelled: the trunk is an
    ASSUMPTION of the arrangement, not a measurement of the hull. Nothing
    validates its structure, its windage or its effect on stability, and the
    volume it adds is reported separately by `Envelope.trunk_volume_m3` so a
    reader can see how much of the interior is assumed rather than extracted.
    """

    x0: float
    x1: float
    half_width: float
    height: float           # above the sheer at each station

    def spans(self, x: float) -> bool:
        return self.x0 <= x <= self.x1


# ------------------------------------------------------------------ envelope


@dataclass(frozen=True, eq=False)
class Envelope:
    """Interior volume, sole plane and deck plan, extracted from a `Hull`.

    Read-only with respect to the geometry kernel: this class calls `Hull`, and
    `Hull` never hears about arrangement.

    `eq=False` because the cached numpy tables make dataclass equality
    ambiguous (and because two envelopes off the same hull ARE the same
    object in every use — `from_vector` hands the template's envelope straight
    through, so identity is the right relation for the round-trip test).
    """

    lwl: float
    sole_z: float
    panel_thickness_m: float
    trunk: Trunk | None
    x: np.ndarray                   # station positions, transom -> stem
    z_grid: np.ndarray              # z levels the half-breadth table is on
    y_int: np.ndarray               # (n_stations, n_z) INTERIOR half-breadth
    z_sheer: np.ndarray             # deck z per station
    y_sheer: np.ndarray             # deck half-breadth per station

    # ---- construction ----

    @staticmethod
    def from_hull(hull: Hull, trunk: Trunk | None = None,
                  panel_thickness_m: float = limits.PLY_THICKNESS_M,
                  n_z: int = 41) -> "Envelope":
        """Extract the arrangement envelope from an evaluated hull.

        The interior half-breadth is the hull's, less the panel thickness the
        boat is built from — `limits.PLY_THICKNESS_M`, the platform's single
        definition of the nominal stock sheet. Framing is NOT deducted; there
        is no sourced frame depth, and inventing one would shrink every space
        in the ladder by a number nobody could check.

        THE SOLE IS THE CHINE PLANE AT THE MAXIMUM-BEAM STATION, and that is a
        geometric statement about this grammar rather than a number: every hull
        it emits is two straight segments per side, so the chine IS the break
        between the bottom panels and the topsides. Below it the section is a
        V and the volume is bilge; at it the section is at full beam.

        The first attempt defined the sole instead as the lowest plane at least
        `SOLE_MIN_CLEAR_WIDTH_MM` wide, which is what the constant literally
        says. MEASURED on the reference hull it put the sole at z = -0.509 m,
        160 mm below the chine and 20 mm off the keel, where the section is
        680 mm across: a criterion satisfied deep inside the bilge, and every
        space fitted to it came out 0.68 m wide because an axis-aligned box in
        a V section is only as wide as its floor. The clear-width constant is
        the wrong tool for placing the plane; it is used below for what it can
        actually decide — where the accommodation ENDS.
        """
        z_lo = float(hull.z_keel.min())
        z_hi = float(hull.z_sheer.max())
        z_grid = np.linspace(z_lo, z_hi, n_z)
        y = np.empty((hull.n_stations, n_z))
        for i in range(hull.n_stations):
            pts = hull.section(i)
            for j in range(n_z):
                y[i, j] = _halfbreadth_at(pts, float(z_grid[j]))
        y_int = np.maximum(y - panel_thickness_m, 0.0)

        # No bilge depth is added on top of the chine, because none is sourced
        # (refdata NOT_SOURCED 'bilge_depth_mm'). A builder's sole sits a
        # little higher; ours sits exactly on the chine and says so.
        i_mb = int(np.argmax(hull.y_chine))
        sole_z = float(hull.z_chine[i_mb])

        clear = 2.0 * float(np.interp(
            sole_z, z_grid, y_int[i_mb]))
        need = _mm(E.SOLE_MIN_CLEAR_WIDTH_MM)
        if clear < need:
            # A construction guard, not a live gate limb, and the difference is
            # worth stating. The sole's clear width at the chine is essentially
            # BWL, so this binds only below BWL ~ 0.6 m — outside the hull
            # grammar's own 1.2 m floor (`grammar.PARAMS`). It is here because
            # `Envelope` is public and nothing stops a caller building one from
            # a hull the grammar would never emit; it is NOT counted as one of
            # L0-A's rules, because a rule that cannot fire inside the
            # parameter space is not a gate.
            raise ValueError(
                f"sole clear width {clear * 1e3:.0f} mm is below the "
                f"{need * 1e3:.0f} mm floor: this hull has no interior")

        return Envelope(lwl=float(hull.x[-1]), sole_z=sole_z,
                        panel_thickness_m=panel_thickness_m, trunk=trunk,
                        x=hull.x.copy(), z_grid=z_grid, y_int=y_int,
                        z_sheer=hull.z_sheer.copy(),
                        y_sheer=hull.y_sheer.copy())

    # ---- queries ----

    def _half_breadth_column(self, z: float) -> np.ndarray:
        """Interior half-breadth at level `z`, every station, vectorised."""
        zg = self.z_grid
        if z <= zg[0]:
            return np.zeros_like(self.x)
        j = int(np.clip(np.searchsorted(zg, z) - 1, 0, zg.size - 2))
        t = (z - zg[j]) / (zg[j + 1] - zg[j])
        t = min(max(t, 0.0), 1.0)
        return self.y_int[:, j] * (1.0 - t) + self.y_int[:, j + 1] * t

    def min_half_breadth(self, x0: float, x1: float, z: float) -> float:
        """Narrowest interior half-breadth over [x0, x1] at level `z` [m].

        Evaluated at `z` alone, which is sufficient because a section's
        half-breadth is non-decreasing upward (keel -> chine -> sheer): the
        bottom of a box is always its tightest level.
        """
        col = self._half_breadth_column(z)
        inner = col[(self.x >= x0) & (self.x <= x1)]
        ends = [float(np.interp(x0, self.x, col)),
                float(np.interp(x1, self.x, col))]
        return min(float(inner.min()) if inner.size else math.inf, *ends)

    def overhead_z(self, x0: float, x1: float) -> float:
        """Lowest overhead over [x0, x1] [m]: sheer, plus the trunk where it
        spans. A box straddling the trunk's edge gets the sheer, which is the
        conservative and correct answer."""
        top = self.z_sheer.copy()
        if self.trunk is not None:
            inside = (self.x >= self.trunk.x0) & (self.x <= self.trunk.x1)
            top = np.where(inside, top + self.trunk.height, top)
        sel = top[(self.x >= x0) & (self.x <= x1)]
        ends = [float(np.interp(x0, self.x, top)),
                float(np.interp(x1, self.x, top))]
        return min(float(sel.min()) if sel.size else math.inf, *ends)

    def min_deck_half_breadth(self, x0: float, x1: float) -> float:
        """Narrowest deck half-breadth over [x0, x1] [m] — the deck plan."""
        sel = self.y_sheer[(self.x >= x0) & (self.x <= x1)]
        ends = [float(np.interp(x0, self.x, self.y_sheer)),
                float(np.interp(x1, self.x, self.y_sheer))]
        return min(float(sel.min()) if sel.size else math.inf, *ends)

    def lowest_z_for_half_breadth(self, x0: float, x1: float,
                                  half_beam: float) -> float | None:
        """Lowest level at which [x0, x1] is at least `half_beam` wide [m].

        The hand-authoring aid the forward end of a boat needs: at the stem the
        keel rises above the sole plane, so a V-berth sits on a platform and
        the platform height is geometry, not taste. Returns None when the hull
        is never that wide over that run — which is information, and is why it
        is not clamped to something plausible.
        """
        lo = max(self.sole_z, float(self.z_grid[0]))
        for z in self.z_grid:
            if z < lo:
                continue
            if self.min_half_breadth(x0, x1, float(z)) >= half_beam:
                return float(z)
        return None

    # ---- integral properties ----

    @property
    def sole_clear_width_m(self) -> float:
        """Clear width of the sole at the widest station [m]."""
        col = self._half_breadth_column(self.sole_z)
        return 2.0 * float(col.max())

    @property
    def accommodation_x(self) -> tuple[float, float]:
        """The run over which the sole is wide enough to be accommodation [m].

        This is what `SOLE_MIN_CLEAR_WIDTH_MM` can honestly decide: not how
        high the floor is, but where it stops. Forward of the forward bound the
        section at sole level is narrower than the smallest clear width any
        source here gives for a space a person stands in — so anything put
        there is a locker, or sits on a platform above the sole
        (`lowest_z_for_half_breadth`), which is exactly how the forepeak of a
        real boat is built.

        MEASURED on the 10 m reference hull: (0.00, 9.20) m, i.e. it takes
        800 mm off the bow and nothing off the stern, the transom being wide.
        """
        col = self._half_breadth_column(self.sole_z)
        wide = col >= 0.5 * _mm(E.SOLE_MIN_CLEAR_WIDTH_MM)
        if not wide.any():
            return (0.0, 0.0)
        idx = np.flatnonzero(wide)
        return (float(self.x[idx[0]]), float(self.x[idx[-1]]))

    @property
    def interior_volume_m3(self) -> float:
        """Volume between the sole and the overhead, both sides [m^3].

        Gross: joinery, structure and tankage are not deducted. It is the
        volume an arrangement is fitted INTO, not the volume left over.
        """
        area = np.empty_like(self.x)
        for i in range(self.x.size):
            zs = self.z_grid
            top = float(self.z_sheer[i])
            m = (zs >= self.sole_z) & (zs <= top)
            if m.sum() >= 2:
                area[i] = 2.0 * float(np.trapezoid(self.y_int[i][m], zs[m]))
            else:
                area[i] = 0.0
        hull_part = float(np.trapezoid(area, self.x))
        return hull_part + self.trunk_volume_m3

    @property
    def trunk_volume_m3(self) -> float:
        """The DECLARED part of the interior — see `Trunk`. Reported apart from
        the extracted part so 'assumed' never reads as 'measured'."""
        t = self.trunk
        if t is None or t.height <= 0:
            return 0.0
        return 2.0 * t.half_width * t.height * (t.x1 - t.x0)

    @property
    def deck_area_m2(self) -> float:
        return 2.0 * float(np.trapezoid(self.y_sheer, self.x))


# ------------------------------------------------------------------ the AST


@dataclass(frozen=True)
class Space:
    """One interior space: envelope box + function tags + adjacency prefs +
    masses, exactly the four things BuildPlan2 §2 lists.

    `mass_kg` covers the space's fit-out — joinery, appliances, upholstery,
    the systems inside it — and NOT the hull structure, batteries or PV, which
    stay in `energy.weight_budget`'s own buckets. See `supersede_outfit`.
    """

    id: str
    function: Function
    box: Box
    mass_kg: float = 0.0
    sigma_kg: float = 0.0
    tags: tuple[str, ...] = ()
    adjacency: tuple[tuple[str, Adjacency], ...] = ()

    def validate(self) -> list[str]:
        v: list[str] = []
        if not self.id.strip():
            v.append("space: empty id")
        if self.mass_kg < 0:
            v.append(f"space[{self.id}]: negative mass {self.mass_kg}")
        if self.mass_kg > 0 and self.sigma_kg <= 0:
            # Honesty rule 1: every quantity carries value, tier and sigma. A
            # hand-authored fit-out mass is an estimate by definition, so a
            # zero sigma on one is a claim of exactness nobody can make.
            v.append(f"space[{self.id}]: mass declared with no sigma")
        return v

    def mass_item(self) -> MassItem:
        """The space as a positioned mass, at its box centroid.

        There is no placement table here and there must never be one: the
        position IS the geometry. Three tables that disagreed by 0.7 m on
        payload LCG is what `weights.py` was written to end.
        """
        cx, cy, cz = self.box.centre
        return MassItem(id=f"space:{self.id}", mass_kg=self.mass_kg,
                        x_m=cx, y_m=cy, z_m=cz, sigma_kg=self.sigma_kg,
                        tier="E", source="arrangement.Space (box centroid)",
                        basis="approx")


@dataclass(frozen=True)
class DeckZone:
    """A deck area with its ISO 15085 zone label and, if fitted, its barrier.

    `barrier_height_mm` is None for "no barrier declared", which is NOT the
    same as zero and is not treated as a failure: WHICH zones require a
    barrier is in the 2024 equipment lists, which are paywalled and recorded
    absent (`refdata.ergonomics.NOT_SOURCED`). What L0-A can check is a
    declared barrier against the 2003 numeric floor.
    """

    id: str
    kind: DeckKind
    zone: Zone
    plan: PlanBox
    barrier_height_mm: float | None = None
    mass_kg: float = 0.0
    sigma_kg: float = 0.0

    def validate(self) -> list[str]:
        v: list[str] = []
        if not self.id.strip():
            v.append("deck zone: empty id")
        if self.mass_kg > 0 and self.sigma_kg <= 0:
            v.append(f"deck[{self.id}]: mass declared with no sigma")
        return v

    def mass_item(self, deck_z: float) -> MassItem:
        cx, cy = self.plan.centre
        return MassItem(id=f"deck:{self.id}", mass_kg=self.mass_kg,
                        x_m=cx, y_m=cy, z_m=deck_z, sigma_kg=self.sigma_kg,
                        tier="E", source="arrangement.DeckZone (plan centroid)",
                        basis="approx")


@dataclass(frozen=True)
class Arrangement:
    """The vessel node: one envelope, the interior spaces, the deck zones.

    `category` is the ISO 12217 design category, and it is here because the
    ISO 15085 side-deck floor is category-dependent — the Solar Liveaboard is
    cat C/D (PLM.md §2), and C and D differ by 20 mm of side deck.
    """

    envelope: Envelope
    spaces: tuple[Space, ...] = ()
    deck_zones: tuple[DeckZone, ...] = ()
    category: str = "C"

    # ---- AST <-> flat vector bridge (the V2.3 solver's interface) ----
    #
    # Same split as `HullDesign.from_vector(x, typology)`: the vector carries
    # only what a solver MOVES, and everything else — ids, functions, zone
    # labels, masses, adjacency preferences — rides on a template. A solver
    # that could rewrite a function tag by perturbing a float would be able to
    # turn a head into a berth by rounding.

    def to_vector(self) -> np.ndarray:
        out: list[float] = []
        for s in self.spaces:
            out.extend(s.box.to_slots())
        for d in self.deck_zones:
            out.extend(d.plan.to_slots())
        return np.asarray(out, dtype=float)

    @staticmethod
    def from_vector(x: np.ndarray, template: "Arrangement") -> "Arrangement":
        x = np.asarray(x, dtype=float)
        n = template.n_slots
        if x.size != n:
            raise ValueError(f"expected {n} slots for this template, got {x.size}")
        k = 0
        spaces = []
        for s in template.spaces:
            spaces.append(replace(s, box=Box.from_slots(x[k:k + 6])))
            k += 6
        decks = []
        for d in template.deck_zones:
            decks.append(replace(d, plan=PlanBox.from_slots(x[k:k + 4])))
            k += 4
        return replace(template, spaces=tuple(spaces), deck_zones=tuple(decks))

    @property
    def n_slots(self) -> int:
        return 6 * len(self.spaces) + 4 * len(self.deck_zones)

    def slot_names(self) -> list[str]:
        """One name per slot, so a solver's variable index is readable —
        `grammar.NAMES`' role for the hull vector."""
        names: list[str] = []
        for s in self.spaces:
            names.extend(f"{s.id}.{k}" for k in Box.SLOTS)
        for d in self.deck_zones:
            names.extend(f"{d.id}.{k}" for k in PlanBox.SLOTS)
        return names

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Box bounds for every slot, from the envelope — `grammar.LOW/HIGH`'s
        role. A solver still has to run L0-A: these bound the SEARCH, they do
        not imply feasibility (the hull is not a cuboid)."""
        env = self.envelope
        y_max = float(env.y_sheer.max())
        z_hi = env.overhead_z(0.0, env.lwl)
        z_lo = float(env.z_grid[0])
        lo_s = [0.0, 0.0, -y_max, -y_max, z_lo, z_lo]
        hi_s = [env.lwl, env.lwl, y_max, y_max, z_hi, z_hi]
        lo_d = [0.0, 0.0, -y_max, -y_max]
        hi_d = [env.lwl, env.lwl, y_max, y_max]
        lo = lo_s * len(self.spaces) + lo_d * len(self.deck_zones)
        hi = hi_s * len(self.spaces) + hi_d * len(self.deck_zones)
        return np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)

    # ---- masses ----

    def mass_items(self) -> list[MassItem]:
        """Every declared mass, positioned by its own geometry, tier 'E'."""
        items = [s.mass_item() for s in self.spaces if s.mass_kg > 0]
        for d in self.deck_zones:
            if d.mass_kg > 0:
                cx, _ = d.plan.centre
                items.append(d.mass_item(
                    float(np.interp(cx, self.envelope.x, self.envelope.z_sheer))))
        return items

    @property
    def interior_volume_used_m3(self) -> float:
        return math.fsum(s.box.volume for s in self.spaces)


# The `energy.weight_budget` bucket these spaces ARE. Named once, consumed by
# `supersede_outfit`, so the coupling is not a sentence in a docstring.
SUPERSEDED_WEIGHT_BUCKET = "outfit"


def supersede_outfit(hull_items: list[MassItem],
                     arr: Arrangement) -> list[MassItem]:
    """Merge hull-side masses with arrangement masses without double-counting.

    `energy.weight_items` places a single 'outfit' lump — 55 kg/m of LWL, so
    550 kg on the reference boat — at 0.50 LWL and 0.60 D. That lump is the
    interior. Once the interior exists as located spaces, keeping both adds
    half a tonne of furniture that is not there and pins its LCG at midships,
    which is precisely the invisible-mass failure `weights.py` was written to
    end. The bucket is dropped, and it is dropped HERE rather than at each
    call site so there is one place to be wrong.
    """
    kept = [m for m in hull_items if m.id != SUPERSEDED_WEIGHT_BUCKET]
    return kept + arr.mass_items()


# ------------------------------------------------- L0-A: minimum dimensions


@dataclass(frozen=True)
class MinBox:
    """A function's dimensional floor, each limb sourced or explicitly absent.

    `None` means NO SOURCE HOLDS A FLOOR FOR THIS LIMB, and it is left
    unbounded on purpose. Filling it with a plausible number is the failure
    `refdata`'s whole design prevents: an invented constant is
    indistinguishable from a transcribed one the moment it lands in a module.
    """

    plan_long: RefValue | None = None
    plan_short: RefValue | None = None
    height: RefValue | None = None
    why_unbounded: str = ""


def _mm(rv: RefValue, index: int | None = None) -> float:
    """A refdata millimetre value in metres. The unit conversion lives here so
    a 1000 does not get typed in eight places."""
    v = rv.value if index is None else rv.value[index]
    return float(v) / 1e3


def _galley_min_height_mm() -> float:
    """Working height plus the clearance that must exist above the hob.

    DERIVED from two refdata constants rather than added as a third. A galley
    shorter than this cannot have a hob in it, which makes it not a galley.
    """
    return (float(E.GALLEY_HOB_HEIGHT_MM.value)
            + float(E.GALLEY_CLEARANCE_ABOVE_HOB_MIN_MM.value))


_GALLEY_MIN_HEIGHT = RefValue(
    _galley_min_height_mm(), "mm",
    "DERIVED: GALLEY_HOB_HEIGHT_MM + GALLEY_CLEARANCE_ABOVE_HOB_MIN_MM, both "
    + E.GALLEY_HOB_HEIGHT_MM.source, "approx",
    "Not a transcribed constant: the sum of two of them, computed so the "
    "number exists in exactly one place.")

# Function -> dimensional floor. Every limb is a `RefValue`, so a violation can
# print the document it came from and how attributable it is.
MIN_DIMS: dict[Function, MinBox] = {
    Function.BERTH: MinBox(
        plan_long=E.BERTH_LENGTH_MIN_MM,
        plan_short=E.BERTH_WIDTH_HEAD_MM,
        height=None,
        why_unbounded="no source gives a clearance above a mattress "
                      "(refdata NOT_SOURCED 'berth_vertical_clearance_mm')"),
    Function.GALLEY: MinBox(
        plan_long=None, plan_short=None,
        height=_GALLEY_MIN_HEIGHT,
        why_unbounded="no source gives a galley footprint; the hob stack is "
                      "the only galley dimension §1.1 yields"),
    Function.HEAD: MinBox(
        plan_long=E.SHOWER_MIN_SQUARE_MM,
        plan_short=E.HEAD_BOWL_TO_DOOR_MIN_MM,
        height=E.HEADROOM_COMPROMISE_MIN_MM),
    Function.SALOON: MinBox(
        plan_long=E.SETTEE_WIDTH_PER_PERSON_MM,
        plan_short=E.SETTEE_DEPTH_MM,
        height=E.HEADROOM_COMPROMISE_MIN_MM),
    Function.NAV: MinBox(
        plan_long=E.SEAT_MIN_MM,          # (width, depth) -> depth is longer
        plan_short=E.SEAT_MIN_MM,
        height=None,
        why_unbounded="a seated station; no seated headroom is sourced"),
    Function.STOWAGE: MinBox(
        why_unbounded="a locker has no minimum size; a shallow one is still a "
                      "locker, and inventing a floor would evict real stowage"),
    Function.MACHINERY: MinBox(
        plan_long=E.HATCH_CLEAR_MIN_MM,
        plan_short=E.HATCH_CLEAR_MIN_MM,
        height=None,
        why_unbounded="access is the binding constraint, and it is a plan "
                      "dimension: the minimum clear hatch must fit the "
                      "footprint or the space cannot be serviced"),
}

# SEAT_MIN_MM is a (width, depth) PAIR, so its two limbs index different
# elements. Held here rather than special-cased in the checker.
_PAIR_INDEX: dict[int, dict[Function, int]] = {
    0: {Function.NAV: 1},    # plan_long  <- depth 750
    1: {Function.NAV: 0},    # plan_short <- width 400
}


def _limb_mm(rv: RefValue, func: Function, limb: int) -> float:
    if isinstance(rv.value, tuple):
        return _mm(rv, _PAIR_INDEX[limb][func])
    return _mm(rv)


def min_dims_m(func: Function) -> dict[str, float | None]:
    """The floors for a function, in metres — the checker's numbers, exposed so
    a test or a UI reads the same values the gate applies."""
    mb = MIN_DIMS[func]
    return {
        "plan_long": None if mb.plan_long is None else _limb_mm(mb.plan_long, func, 0),
        "plan_short": None if mb.plan_short is None else _limb_mm(mb.plan_short, func, 1),
        "height": None if mb.height is None else _mm(mb.height),
    }


def deck_min_width_m(kind: DeckKind,
                     category: str) -> tuple[float, RefValue] | None:
    """Narrow-dimension floor for a deck zone, with the RefValue behind it.

    Side decks are the ISO 15085:2003 clause, and it is category-dependent —
    which is why `Arrangement` carries the design category at all. A cockpit's
    floor is the footwell taper's TOP width, the widest of the pair and so the
    one a rectangle has to clear; the taper itself (610 -> 460 mm, and the
    reason for it) is a Tier E shape check, not an L0-A dimension.

    Foredecks and aftdecks get None: no source here gives a floor for them,
    and the ISO side-deck number is about a passage between the coachroof and
    the toerail, not about open deck.
    """
    if kind is DeckKind.SIDE_DECK:
        rv = E.SIDE_DECK_WIDTH_MIN_MM[category]
        return _mm(rv), rv
    if kind is DeckKind.COCKPIT:
        rv = E.COCKPIT_FOOTWELL_TAPER_MM
        return _mm(rv, 0), rv
    return None


# ------------------------------------------------------------- L0-A: the gate


@dataclass(frozen=True)
class Violation:
    """A reason, not a boolean.

    Gate V2.1's bar says 'violations report reasons', and this project's
    standing complaint about `gate2m.py` was a verdict with no way back to the
    measurement. So a violation names the rule, the SUBJECT (which space), the
    measured value, the bar, and — where a bar came from a document — that
    document and its basis. A reader can re-derive the verdict from the row.
    """

    rule: str
    subject: str
    detail: str
    measured: float | None = None
    required: float | None = None
    source: str = ""
    basis: str = ""

    def __str__(self) -> str:
        s = f"[{self.rule}] {self.subject}: {self.detail}"
        if self.source:
            s += f" (bar: {self.source}, basis={self.basis})"
        return s


@dataclass(frozen=True)
class ArrangementReport:
    ok: bool
    violations: tuple[Violation, ...] = ()

    @property
    def messages(self) -> tuple[str, ...]:
        return tuple(str(v) for v in self.violations)

    def by_rule(self, rule: str) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.rule == rule)

    def subjects(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(v.subject for v in self.violations))


# Rule ids. Strings, not an enum, because they are printed into reports and
# grepped for in tests; an enum would only add a `.value` to every use.
R_DEGENERATE = "L0A-DEGENERATE"
R_ENVELOPE_X = "L0A-ENVELOPE-X"
R_ENVELOPE_Y = "L0A-ENVELOPE-Y"
R_ENVELOPE_Z = "L0A-ENVELOPE-Z"
R_OVERLAP = "L0A-OVERLAP"
R_MIN_DIMS = "L0A-MIN-DIMS"
R_DECK_PLAN = "L0A-DECK-PLAN"
R_DECK_TRUNK = "L0A-DECK-TRUNK"
R_DECK_OVERLAP = "L0A-DECK-OVERLAP"
R_DECK_MIN_WIDTH = "L0A-DECK-MIN-WIDTH"
R_BARRIER = "L0A-BARRIER"
R_NODE = "L0A-NODE"

# Touching faces are how bulkheads work, so the overlap test needs a width
# below which two boxes are sharing a plane rather than intersecting. 1 mm:
# an order of magnitude under the smallest sourced dimension in MIN_DIMS
# (100 mm, the cat-D side deck) and an order of magnitude over float noise on
# metre-scale coordinates.
TOUCH_TOL_M = 1e-3


def check_l0a(arr: Arrangement) -> ArrangementReport:
    """The algebraic arrangement gate: fits-in-envelope, no overlap, min dims.

    `grammar.check` is the model — same shape, same job, one level up. It runs
    on the AST alone: no solver, no geometry construction, no CAD kernel.
    BuildPlan2 §3 budgets < 10 ms; see `tests/test_arrangement.py` for the
    measurement.
    """
    v: list[Violation] = []
    env = arr.envelope

    for node in (*arr.spaces, *arr.deck_zones):
        for msg in node.validate():
            v.append(Violation(R_NODE, node.id, msg))

    # ---- interior spaces ----
    for s in arr.spaces:
        b = s.box
        if b.dx <= 0 or b.dy <= 0 or b.dz <= 0:
            v.append(Violation(
                R_DEGENERATE, s.id,
                f"non-positive extent dx={b.dx:.3f} dy={b.dy:.3f} dz={b.dz:.3f} m"))
            continue

        if b.x0 < 0.0 or b.x1 > env.lwl:
            v.append(Violation(
                R_ENVELOPE_X, s.id,
                f"x range [{b.x0:.3f}, {b.x1:.3f}] outside the hull "
                f"[0, {env.lwl:.3f}] m",
                measured=max(-b.x0, b.x1 - env.lwl), required=0.0))

        if b.z0 < env.sole_z - TOUCH_TOL_M:
            v.append(Violation(
                R_ENVELOPE_Z, s.id,
                f"floor {b.z0:.3f} m is below the sole {env.sole_z:.3f} m",
                measured=b.z0, required=env.sole_z))
        top = env.overhead_z(b.x0, b.x1)
        if b.z1 > top + TOUCH_TOL_M:
            v.append(Violation(
                R_ENVELOPE_Z, s.id,
                f"ceiling {b.z1:.3f} m is above the overhead {top:.3f} m "
                f"over its length",
                measured=b.z1, required=top))

        # Widest point of the box against the narrowest hull section under it.
        avail = env.min_half_breadth(max(b.x0, 0.0), min(b.x1, env.lwl), b.z0)
        if b.half_beam > avail + TOUCH_TOL_M:
            v.append(Violation(
                R_ENVELOPE_Y, s.id,
                f"reaches y={b.half_beam:.3f} m at z={b.z0:.3f} m where the "
                f"interior is {avail:.3f} m half-breadth",
                measured=b.half_beam, required=avail))

        v.extend(_min_dim_violations(s))

    # ---- no two spaces in the same volume ----
    for i in range(len(arr.spaces)):
        for j in range(i + 1, len(arr.spaces)):
            a, c = arr.spaces[i], arr.spaces[j]
            if a.box.overlaps(c.box, TOUCH_TOL_M):
                ov = _overlap_extent(a.box, c.box)
                v.append(Violation(
                    R_OVERLAP, f"{a.id}|{c.id}",
                    f"{a.id} ({a.function.value}) and {c.id} "
                    f"({c.function.value}) share "
                    f"{ov[0]:.3f}x{ov[1]:.3f}x{ov[2]:.3f} m",
                    measured=ov[0] * ov[1] * ov[2], required=0.0))

    # ---- deck zones ----
    for d in arr.deck_zones:
        p = d.plan
        if p.dx <= 0 or p.dy <= 0:
            v.append(Violation(
                R_DEGENERATE, d.id,
                f"non-positive deck extent dx={p.dx:.3f} dy={p.dy:.3f} m"))
            continue

        if p.x0 < 0.0 or p.x1 > env.lwl:
            v.append(Violation(
                R_DECK_PLAN, d.id,
                f"x range [{p.x0:.3f}, {p.x1:.3f}] outside the deck "
                f"[0, {env.lwl:.3f}] m"))
        avail = env.min_deck_half_breadth(max(p.x0, 0.0), min(p.x1, env.lwl))
        if p.half_beam > avail + TOUCH_TOL_M:
            v.append(Violation(
                R_DECK_PLAN, d.id,
                f"reaches y={p.half_beam:.3f} m where the deck is "
                f"{avail:.3f} m half-breadth",
                measured=p.half_beam, required=avail))

        if env.trunk is not None and env.trunk.height > 0:
            t = env.trunk
            foot = PlanBox(t.x0, t.x1, -t.half_width, t.half_width)
            if p.overlaps(foot, TOUCH_TOL_M):
                v.append(Violation(
                    R_DECK_TRUNK, d.id,
                    "deck zone lies under the coachroof "
                    f"(x {t.x0:.2f}-{t.x1:.2f} m, half-width "
                    f"{t.half_width:.2f} m) — that area is not deck"))

        floor = deck_min_width_m(d.kind, arr.category)
        if floor is not None:
            need, rv = floor
            if p.plan_short < need - TOUCH_TOL_M:
                v.append(Violation(
                    R_DECK_MIN_WIDTH, d.id,
                    f"{d.kind.value} is {p.plan_short * 1e3:.0f} mm wide, "
                    f"floor is {need * 1e3:.0f} mm (design category "
                    f"{arr.category})",
                    measured=p.plan_short, required=need,
                    source=rv.source, basis=rv.basis))

        if d.barrier_height_mm is not None:
            need_mm = float(E.BARRIER_LOW_MIN_MM.value)
            if d.barrier_height_mm < need_mm:
                v.append(Violation(
                    R_BARRIER, d.id,
                    f"barrier {d.barrier_height_mm:.0f} mm is below the low-"
                    f"barrier floor {need_mm:.0f} mm",
                    measured=d.barrier_height_mm / 1e3, required=need_mm / 1e3,
                    source=E.BARRIER_LOW_MIN_MM.source,
                    basis=E.BARRIER_LOW_MIN_MM.basis))

    for i in range(len(arr.deck_zones)):
        for j in range(i + 1, len(arr.deck_zones)):
            a, c = arr.deck_zones[i], arr.deck_zones[j]
            if a.plan.overlaps(c.plan, TOUCH_TOL_M):
                v.append(Violation(
                    R_DECK_OVERLAP, f"{a.id}|{c.id}",
                    f"{a.id} ({a.kind.value}, {a.zone.value}) and {c.id} "
                    f"({c.kind.value}, {c.zone.value}) share deck area"))

    return ArrangementReport(len(v) == 0, tuple(v))


def _overlap_extent(a: Box, b: Box) -> tuple[float, float, float]:
    return (min(a.x1, b.x1) - max(a.x0, b.x0),
            min(a.y1, b.y1) - max(a.y0, b.y0),
            min(a.z1, b.z1) - max(a.z0, b.z0))


def _min_dim_violations(s: Space) -> list[Violation]:
    mb = MIN_DIMS[s.function]
    out: list[Violation] = []
    checks = (
        ("plan_long", mb.plan_long, s.box.plan_long, 0,
         "longer plan dimension"),
        ("plan_short", mb.plan_short, s.box.plan_short, 1,
         "shorter plan dimension"),
        ("height", mb.height, s.box.dz, None, "height"),
    )
    for _name, rv, got, limb, label in checks:
        if rv is None:
            continue
        need = _mm(rv) if limb is None else _limb_mm(rv, s.function, limb)
        if got < need - TOUCH_TOL_M:
            out.append(Violation(
                R_MIN_DIMS, s.id,
                f"{s.function.value} {label} {got * 1e3:.0f} mm is below the "
                f"{need * 1e3:.0f} mm floor",
                measured=got, required=need, source=rv.source, basis=rv.basis))
    return out


# ------------------------------------------- the hand-authored reference SKU


# PLM.md §2: Solar Liveaboard — 6 t, 9-14 m, Danube/Black Sea, cat C/D. The
# reference product is the 10 m boat every test in this repo uses.
REFERENCE_CATEGORY = "C"


def reference_hull_params() -> np.ndarray:
    """The 10 m Solar-Liveaboard hull, from `tests/test_phase0.mid_params`.

    Re-declared here so `arrangement` has a reference vessel without importing
    a test module — and it is the SAME fifteen numbers, which is a duplication
    this module would rather not have. It is confined to the reference-layout
    demo; nothing in the grammar or the gate reads it.
    """
    from . import grammar
    return grammar.vector({
        "LWL": 10.0, "BWL": 3.2, "T": 0.55, "D": 1.55,
        "beta_mid": 8.0, "beta_bow": 30.0, "p_bow": 2.2, "p_stern": 3.0,
        "x_mb": 0.55, "r_transom": 0.75, "rocker": 0.15, "forefoot": 0.85,
        "flare": 10.0, "sheer_rise": 0.18, "beta_len": 0.35,
    })


def reference_trunk(hull: Hull) -> Trunk:
    """The coachroof the reference layout declares, sized by the headroom it
    has to deliver rather than picked.

    height = HEADROOM_PREFERRED_MM - (sheer - sole) over the trunk's run. So
    the trunk is exactly as tall as standing headroom requires and not a
    millimetre of it is a taste; if the hull gets deeper the trunk shrinks.
    """
    bare = Envelope.from_hull(hull)
    x0, x1 = _TRUNK_X0 * bare.lwl, _TRUNK_X1 * bare.lwl
    have = bare.overhead_z(x0, x1) - bare.sole_z
    need = _mm(E.HEADROOM_PREFERRED_MM)
    height = max(need - have, 0.0)
    # Half-width leaves a side deck each side. That WIDTH is a design decision
    # of the reference layout (a wide side deck is a nicer boat), and L0-A
    # checks it against the ISO floor rather than against this choice.
    half = bare.min_deck_half_breadth(x0, x1) - _SIDE_DECK_M
    return Trunk(x0=x0, x1=x1, half_width=half, height=height)


# Layout decisions of the hand-authored reference boat, as fractions of LWL.
# They are the AUTHOR'S, not derived from anything, which is what
# "hand-authored" means in Gate V2.1 — and they are named rather than inlined
# so the plan is readable as a plan.
_TRUNK_X0, _TRUNK_X1 = 0.13, 0.70
_SIDE_DECK_M = 0.42          # side deck each side of the coachroof [m]
_COCKPIT_X0, _COCKPIT_X1 = 0.01, 0.125
_MACHINERY_X0, _MACHINERY_X1 = 0.015, 0.13
_AFT_BERTH_X0, _AFT_BERTH_X1 = 0.135, 0.345
_HEAD_X0, _HEAD_X1 = 0.135, 0.215
_GALLEY_X0, _GALLEY_X1 = 0.355, 0.475
_NAV_X0, _NAV_X1 = 0.355, 0.435
_SALOON_X0, _SALOON_X1 = 0.485, 0.690
_FWD_BERTH_X0, _FWD_BERTH_X1 = 0.705, 0.915
_FOREPEAK_X0, _FOREPEAK_X1 = 0.925, 0.985


def reference_layout(hull: Hull | None = None) -> Arrangement:
    """The hand-authored Solar-Liveaboard reference layout — Gate V2.1's fixture.

    Aft to forward: machinery under the cockpit, a quarter berth to port with
    the head opposite, galley and nav station amidships, saloon, a V-berth
    forward on the platform the forefoot forces, and a forepeak locker. On
    deck: cockpit (Z1), a side deck each side of the coachroof (Z2) and the
    foredeck (Z3), which is where anchor work happens and is therefore the
    zone whose access condition is 'nearly stationary'.

    The x-stations are the author's. The WIDTHS and the two floor levels are
    read off the envelope, because a hull's half-breadth at a station is not a
    matter of opinion — hand-authoring them would be inventing geometry the
    kernel already knows, and would silently stop matching the hull the moment
    a slider moved.

    PLM.md §5 registers this layout as a retirement candidate: it retires when
    V2.3 generates a better one that passes every tier.
    """
    if hull is None:
        hull = Hull(reference_hull_params())
    L = float(hull.x[-1])
    env = Envelope.from_hull(hull, trunk=reference_trunk(hull))
    sole = env.sole_z

    def clear_half(x0: float, x1: float, z: float, margin: float) -> float:
        """Half-width available between x0 and x1 at level z, less a margin for
        the joinery's own linings."""
        return max(env.min_half_breadth(x0, x1, z) - margin, 0.0)

    spaces: list[Space] = []

    # --- machinery: electric drive and its systems, aft, under the cockpit.
    x0, x1 = _MACHINERY_X0 * L, _MACHINERY_X1 * L
    hb = clear_half(x0, x1, sole, 0.10)
    spaces.append(Space(
        "machinery", Function.MACHINERY,
        Box(x0, x1, -hb, hb, sole, sole + 0.80),
        mass_kg=95.0, sigma_kg=20.0,
        tags=("wet", "serviceable"),
        adjacency=(("cockpit", Adjacency.PREFER),
                   ("berth.aft", Adjacency.AVOID),
                   ("saloon", Adjacency.AVOID))))

    # --- quarter berth to port, head to starboard, sharing the aft bulkhead.
    x0, x1 = _AFT_BERTH_X0 * L, _AFT_BERTH_X1 * L
    hb = clear_half(x0, x1, sole, 0.06)
    spaces.append(Space(
        "berth.aft", Function.BERTH,
        Box(x0, x1, -hb, -hb + 0.95, sole, sole + 0.95),
        mass_kg=85.0, sigma_kg=17.0,
        tags=("sea-berth", "lee-cloth"),
        adjacency=(("head", Adjacency.PREFER),
                   ("machinery", Adjacency.AVOID))))

    x0, x1 = _HEAD_X0 * L, _HEAD_X1 * L
    hb = clear_half(x0, x1, sole, 0.06)
    spaces.append(Space(
        "head", Function.HEAD,
        Box(x0, x1, hb - 0.95, hb, sole, env.overhead_z(x0, x1)),
        mass_kg=70.0, sigma_kg=15.0,
        tags=("wet", "standing"),
        adjacency=(("berth.aft", Adjacency.PREFER),
                   ("galley", Adjacency.AVOID))))

    # --- galley to port, nav to starboard, both under the coachroof.
    x0, x1 = _GALLEY_X0 * L, _GALLEY_X1 * L
    hb = clear_half(x0, x1, sole, 0.05)
    spaces.append(Space(
        "galley", Function.GALLEY,
        Box(x0, x1, -hb, -hb + 0.72, sole, env.overhead_z(x0, x1)),
        mass_kg=130.0, sigma_kg=26.0,
        tags=("standing", "gimballed-stove", "wet"),
        adjacency=(("saloon", Adjacency.PREFER),
                   ("head", Adjacency.AVOID))))

    x0, x1 = _NAV_X0 * L, _NAV_X1 * L
    hb = clear_half(x0, x1, sole, 0.05)
    spaces.append(Space(
        "nav", Function.NAV,
        Box(x0, x1, hb - 0.62, hb, sole + 0.36, sole + 1.05),
        mass_kg=45.0, sigma_kg=12.0,
        tags=("seated",),
        adjacency=(("cockpit", Adjacency.PREFER),
                   ("saloon", Adjacency.PREFER))))

    # --- saloon amidships, full width, standing headroom under the coachroof.
    x0, x1 = _SALOON_X0 * L, _SALOON_X1 * L
    hb = clear_half(x0, x1, sole, 0.05)
    spaces.append(Space(
        "saloon", Function.SALOON,
        Box(x0, x1, -hb, hb, sole, env.overhead_z(x0, x1)),
        mass_kg=115.0, sigma_kg=23.0,
        tags=("standing", "settee", "convertible-double"),
        adjacency=(("galley", Adjacency.PREFER),
                   ("nav", Adjacency.PREFER),
                   ("machinery", Adjacency.AVOID))))

    # --- V-berth forward. Its floor is NOT the sole: the forefoot lifts the
    # keel above the sole plane, so the berth sits on the platform height the
    # geometry dictates. Asking the envelope for it is the point of
    # `lowest_z_for_half_breadth`.
    x0, x1 = _FWD_BERTH_X0 * L, _FWD_BERTH_X1 * L
    want_half = 0.5 * _mm(E.DOUBLE_BERTH_WIDTH_MIN_MM) + 0.05
    z_plat = env.lowest_z_for_half_breadth(x0, x1, want_half)
    if z_plat is None:
        raise ValueError("this hull is too fine forward to carry a V-berth; "
                         "the reference layout does not fit it")
    hb = clear_half(x0, x1, z_plat, 0.05)
    spaces.append(Space(
        "berth.fwd", Function.BERTH,
        Box(x0, x1, -hb, hb, z_plat, env.overhead_z(x0, x1)),
        mass_kg=95.0, sigma_kg=19.0,
        tags=("double", "at-anchor"),
        adjacency=(("stowage.fwd", Adjacency.PREFER),
                   ("machinery", Adjacency.AVOID))))

    # --- forepeak locker: ground tackle, warps, fenders.
    x0, x1 = _FOREPEAK_X0 * L, _FOREPEAK_X1 * L
    z_lkr = env.lowest_z_for_half_breadth(x0, x1, 0.12)
    if z_lkr is None:
        raise ValueError("no forepeak volume on this hull")
    hb = clear_half(x0, x1, z_lkr, 0.03)
    spaces.append(Space(
        "stowage.fwd", Function.STOWAGE,
        Box(x0, x1, -hb, hb, z_lkr, env.overhead_z(x0, x1)),
        mass_kg=55.0, sigma_kg=14.0,
        tags=("ground-tackle", "heavy"),
        adjacency=(("berth.fwd", Adjacency.PREFER),)))

    # --- deck zones.
    t = env.trunk
    assert t is not None
    y_deck_cockpit = env.min_deck_half_breadth(_COCKPIT_X0 * L, _COCKPIT_X1 * L)
    deck: list[DeckZone] = [
        DeckZone("cockpit", DeckKind.COCKPIT, Zone.Z1,
                 PlanBox(_COCKPIT_X0 * L, _COCKPIT_X1 * L,
                         -y_deck_cockpit, y_deck_cockpit),
                 barrier_height_mm=float(E.BARRIER_LOW_MIN_MM.value),
                 mass_kg=40.0, sigma_kg=10.0),
    ]
    for side, sgn in (("stbd", 1.0), ("port", -1.0)):
        y_out = env.min_deck_half_breadth(t.x0, t.x1)
        a, b = sgn * t.half_width, sgn * y_out
        deck.append(DeckZone(
            f"sidedeck.{side}", DeckKind.SIDE_DECK, Zone.Z2,
            PlanBox(t.x0, t.x1, min(a, b), max(a, b)),
            barrier_height_mm=float(E.BARRIER_LOW_MIN_MM.value)))
    y_fore = env.min_deck_half_breadth(t.x1, L)
    deck.append(DeckZone("foredeck", DeckKind.FOREDECK, Zone.Z3,
                         PlanBox(t.x1, L, -y_fore, y_fore),
                         barrier_height_mm=float(E.BARRIER_LOW_MIN_MM.value)))

    return Arrangement(envelope=env, spaces=tuple(spaces),
                       deck_zones=tuple(deck), category=REFERENCE_CATEGORY)


__all__ = [
    "Function", "DeckKind", "Zone", "Adjacency",
    "Box", "PlanBox", "Trunk", "Envelope",
    "Space", "DeckZone", "Arrangement",
    "MinBox", "MIN_DIMS", "min_dims_m", "deck_min_width_m",
    "Violation", "ArrangementReport", "check_l0a",
    "supersede_outfit", "SUPERSEDED_WEIGHT_BUCKET",
    "reference_layout", "reference_trunk", "reference_hull_params",
    "REFERENCE_CATEGORY", "TOUCH_TOL_M",
    "R_DEGENERATE", "R_ENVELOPE_X", "R_ENVELOPE_Y", "R_ENVELOPE_Z",
    "R_OVERLAP", "R_MIN_DIMS", "R_DECK_PLAN", "R_DECK_TRUNK",
    "R_DECK_OVERLAP", "R_DECK_MIN_WIDTH", "R_BARRIER", "R_NODE",
]
