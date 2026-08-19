"""BUILDABILITY AND MANUFACTURING-COMPLEXITY METRICS — every one a PROXY, and
each one says so in its own docstring.

WHY THIS MODULE EXISTS, and the measurement that asked for it.

`navalai/experiments.py::experiment_5_objective_gaming` asked whether this
project's optimisation objective is gameable the way ShipGen's was — its
authors report a performance-guided optimum with wave drag x0.086 and TOTAL
SURFACE AREA x2.138, lower-half surface x4.365, Gaussian curvature x1.514 and
volume x47.9, and write of their own result "This is not desirable."

The answer measured here is in that experiment's docstring and it is NO for the
objective this repository actually minimises. What the same measurement DID
expose is that the objective carries no manufacturing term at all: the R_w-only
optimum and the R_t optimum differ by **5.6x in non-developable shell area**
(29.46 m^2 against 5.27 m^2) and NOTHING in `evaluate.CONSTRAINT_NAMES` or in
`optimize.HullProblem`'s objective vector can see that difference. This module
is the missing metric, built where it can be reviewed before it is wired.

=============================================================================
THE TWO SHAPE METRICS ARE NOT THE SAME QUANTITY, AND THE DIFFERENCE DECIDES
WHICH ONE MAY BE AN OBJECTIVE
=============================================================================

`non_developable_area_m2`  =  Int |sin psi| dA over the moulded shell [m^2]

    psi is the angle `unroll.ruling_twist` returns: the sine of the angle
    between the edge tangent A' and the plane of (r, r'), for the ruled strip
    X(u, v) = A(u) + v r(u). It is ZERO exactly when that ruling family is
    developable, it is dimensionless and refinement-invariant (that invariance
    is `ruling_twist`'s whole reason for existing — see its docstring), and
    weighting it by element area gives a quantity in SQUARE METRES.

    IT IS RULING-FAMILY DEPENDENT. Measured on the CONSTANT-x family, which is
    the family the grammar's surface is actually defined on: `Hull.section` is
    a straight line from keel to chine at constant x, so the moulded surface IS
    the constant-x ruled surface and this is not an arbitrary choice. A
    different family (`unroll.developable_pairing`) describes a DIFFERENT
    surface — the best developable approximation — and its residual is
    `unroll.refold_surface_deviation_mm`, which is Gate 6D's metric and a
    different question from this one.

`gauss_abs_integral`  =  Int |K| dA  [dimensionless, steradians]

    Discrete Gaussian curvature by ANGLE DEFICIT (Gauss-Bonnet) at interior
    vertices of the triangulated moulded surface. K is INTRINSIC: it does not
    depend on any ruling family, and K == 0 everywhere is developability, full
    stop. This is the metric the four-paper read
    (`docs/research/HULL-GAN-PAPERS.md`) names as the most adoptable idea in
    the literature, because it prices manufacturing difficulty on a continuum
    instead of refusing a hull outright.

=============================================================================
AND HERE IS THE MEASURED TRAP, WHICH IS THE SAME TRAP THE PAPER FELL INTO
=============================================================================

The literature's form is the AREA-AVERAGED Gaussian curvature, Int|K| dA / A.
**Do not make that an objective.** MEASURED on the two optima experiment 5
located (`python -m navalai.experiments`, production Michell grid, fixed speed
3.2544 m/s, fixed displacement 4168.19 kg):

    hull                        shell A   Int|K|dA   Int|K|dA / A   nondev m^2
    R_t optimum   (LWL 12 m)     40.73     0.00594     2.90e-4         8.79
    R_w-only opt  (LWL 20 m)    114.28     0.00575     1.00e-4        29.46

    ratio  (R_w-only / R_t)       2.81x      0.97x       0.34x         3.35x

The R_w-only hull is 2.81x the shell area, 2.83x the structural mass, 114
sheets of plywood against 34, 4778 build hours against 1299, and 28.7% worse in
Wh/NM — the quantity this project actually minimises. **BOTH curvature forms
score it BETTER**: the area-average by 2.9x, and the integral by 3%.

Dividing by an area the optimiser is free to inflate is EXACTLY the
normalisation defect that produced ShipGen's result — they scaled the wave-drag
coefficient by LOA^2 rather than by wetted area, and the optimiser grew the
boat until the headline coefficient fell. An area-averaged curvature objective
reproduces that mechanism on the manufacturing axis.

So of the three candidate forms:

    Int |K| dA / A   REFUSED as an objective. Normalised by a quantity the
                     search controls, and MEASURED inverted by 2.9x on the
                     inflated hull. A SHAPE diagnostic only.
    Int |K| dA       REFUSED as a COST. It is a TOTAL curvature and
                     Gauss-Bonnet is why it barely moves with size: MEASURED
                     0.00575 on a 114 m^2 shell against 0.00594 on a 40.7 m^2
                     one, i.e. mildly inverted as well. It is a good SHAPE
                     metric — it separates the deliberately warped control hull
                     from the reference by 10.6x at equal area — and a bad cost
                     metric, because two boats of the same shape and different
                     size score alike, which is false of labour and of plywood.
    Int |sin psi| dA RECOMMENDED, and the ONLY one of the three that is not
                     inverted. Units of m^2, so it grows with the boat AND with
                     the difficulty of its shape — MEASURED 3.35x on the
                     inflated hull, tracking the 3.35x in plywood sheets almost
                     exactly — and it is zero for a shell that can be cut from
                     flat sheet.

=============================================================================
WHAT IS A PROXY HERE, SAID OUT LOUD
=============================================================================

* `non_developable_area_m2` and the curvature integrals are GEOMETRY. They are
  not costed. Nothing in this repository has ever measured hours against them,
  so calling either one "manufacturing complexity" is a modelling claim and not
  a measurement, and it is labelled `basis="proxy"` in every record.
* `build_hours` comes from `engineer.HOURS_PER_M2`, which that module's own
  source calls "amateur build, approx". It is carried because it is the only
  labour number in the repository, not because it is validated.
* The nesting metrics ARE measurements — `ply_sheets` is COUNTED off the
  layout `unroll.nest` produces, which is what retired the old declared 1.30
  waste factor — but they are measurements of a PLANNED layout, not of a cut.

NOTHING IN THIS MODULE RE-IMPLEMENTS A QUANTITY THAT EXISTS. Wetted surface is
`Hull.wetted_surface`; shell area is `energy.shell_area_m2`; structural mass is
`energy.weight_budget`; the twist criterion is `unroll.ruling_twist`; panels,
strakes, nesting and the BOM are `unroll` and `engineer.assess`. This module
composes them and adds exactly one thing that did not exist: the discrete
Gaussian curvature of the moulded surface.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import grammar
from .energy import EnergySpec, shell_area_m2, weight_budget
from .geometry import Hull
from .limits import PLY_THICKNESS_M
from .unroll import ruling_twist

# ---------------------------------------------------------------------------
# The evaluation protocol. READ AT RUN TIME BY EVERY CALLER, RECORDED IN EVERY
# RECORD — the same rule `experiments.py` applies to the Michell grid, and for
# the same reason: a metric quoted without its grid is not reproducible.
# ---------------------------------------------------------------------------
#
# MEASURED refinement on the reference demihull (`experiments.reference_
# demihull`), constant-x rulings, both shell strips, mask as below:
#
#     n_stations  n_rulings   nondev m^2   Int|K|dA   Int|K|dA / A
#             41          9      9.6576     0.00531      0.000312
#             41         33      9.6576     0.00588      0.000346
#             81         17      9.4707     0.00583      0.000343
#            161          9      9.3801     0.00549      0.000323
#            161         17      9.3801     0.00588      0.000346   <- SHIPPED
#            161         33      9.3801     0.00608      0.000358
#            321         17      9.3356     0.00591      0.000348
#
# `nondev` is converged to 0.5% at 161 stations (9.3801 against 9.3356 at 321)
# and does not depend on `n_rulings` AT ALL — `ruling_twist` is evaluated on the
# two edge curves, not on the interior grid, which is what makes it refinement-
# invariant in that axis by construction. The curvature integral is the slower
# one: it moves 3.4% from n_rulings 9 to 33 at fixed stations, so 17 is chosen
# as the knee and `REFINEMENT_CHECK` exists so a caller can measure the residual
# rather than trust this table.
SHELL_GRID = {"n_stations": 161, "n_rulings": 17}
REFINEMENT_CHECK = {"n_stations": 321, "n_rulings": 33}

# THE END-STATION MASK, AND IT IS NOT A NEW RULE. A ruling whose length goes to
# zero at the stem has an undefined twist and a triangle fan with a degenerate
# vertex has an angle deficit that diverges — a property of every hull that
# comes to a point, not of a badly shaped one. `Hull.fairness` masks at 10% of
# the maximum half-breadth and `Hull.panel_twist_rate` masks at 10% of the
# maximum chine half-breadth, both for exactly this reason and both recording
# that the mask is deliberate. This is the same 10%, applied to the RULING
# LENGTH, and it is named once here rather than typed into two functions.
#
# MEASURED consequence on the reference demihull: without the mask the twist
# maximum is 1.00000 (the degenerate stem ruling) on every hull in the grammar,
# i.e. the metric saturates and stops discriminating. With it, the four hulls
# experiment 5 reports span 0.742 to 0.999.
END_MASK_FRAC = 0.10

# The bases a record may carry. Spelled to match the vocabulary
# `experiments.Quantity` enforces, so a quantity crossing between the two
# modules keeps its meaning.
BASIS_GEOMETRY = "closed-form-geometry"
BASIS_PROXY = "proxy"                    # a modelling claim, NOT a measurement
BASIS_COUNTED = "counted-off-layout"


class BuildabilityError(RuntimeError):
    """A buildability metric could not be measured as specified.

    Raised rather than returning a default. An unmeasurable metric scored as a
    passing one is this repository's defect class 1 (`docs/LESSONS.md`, and the
    `${VAR:-0}` receipts in `run-case.sh` that it cost a run to find), and a
    zero on a complexity metric is the most buildable answer there is.
    """


# ---------------------------------------------------------------------------
# The moulded surface, as this grammar defines it
# ---------------------------------------------------------------------------


def _strips(hull: Hull, n_stations: int, n_rulings: int):
    """The two shell strips as (A, B, grid) — keel->chine and chine->sheer.

    `Hull.edge_curves` is evaluated ANALYTICALLY at the requested stations
    rather than interpolated: that method's own docstring records a spline
    through the 41 station points being 94.95 mm off on the SHEER, which is
    twenty times the refold bar, so an interpolated edge is a different hull.

    The interior grid is the RULED surface X(u, v) = A(u) + v (B(u) - A(u)),
    which for `roundness == 0` IS the moulded surface: `Hull.section` returns
    the three-point polyline and the segment from keel to chine is a straight
    line at constant x. This is asserted, not assumed — see the refusal below.
    """
    rho = float(grammar.named(hull.params)["roundness"])
    if rho > 0.0:
        raise BuildabilityError(
            f"buildability: roundness {rho:.3f}. The moulded surface is only "
            f"the two-strip ruled surface at roundness 0; with a filleted "
            f"bilge the section is a shape function (257 points) and the "
            f"strip between keel and chine is not the hull. `unroll.hull_"
            f"panels` refuses this same hull for the same reason — a radiused "
            f"bilge is doubly curved and not developable from flat sheet, "
            f"which is a fact about the material. Measuring it here anyway "
            f"would report a curvature of a surface the boat does not have.")
    x = np.linspace(float(hull.x[0]), float(hull.x[-1]), int(n_stations))
    keel, chine, sheer = hull.edge_curves(x)
    v = np.linspace(0.0, 1.0, int(n_rulings))
    out = []
    for A, B in ((keel, chine), (chine, sheer)):
        grid = A[:, None, :] + v[None, :, None] * (B - A)[:, None, :]
        out.append((A, B, grid))
    return out


def _angle_deficit(grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(deficit at interior vertices, barycentric area of EVERY vertex).

    Discrete Gaussian curvature by Gauss-Bonnet: K_i dA_i = 2 pi - sum of the
    incident triangle angles at vertex i. Each quad of the (n, m) grid is split
    into the SAME two triangles `unroll.develop` splits it into — on the
    (A[i+1], B[i]) diagonal — so the polyhedral surface this curvature is
    measured on is the one the unroller would actually flatten, rather than a
    second triangulation that would give a second answer.

    Returns the deficit only at INTERIOR vertices because the Gauss-Bonnet
    relation at a boundary vertex carries a geodesic-curvature term this does
    not compute; including boundary vertices as if they were interior would
    report the hull's EDGES as curvature. The full area array is returned
    separately so a caller can normalise by the whole strip.
    """
    n, m, _ = grid.shape
    if n < 3 or m < 3:
        raise BuildabilityError(
            f"_angle_deficit: a {n}x{m} grid has no interior vertex, so there "
            f"is no angle deficit to measure. Refused rather than returned as "
            f"zero curvature, which is what a flat plate reports.")
    deficit = np.full((n, m), 2.0 * math.pi)
    area = np.zeros((n, m))

    def corner(p, q, r):
        u, w = q - p, r - p
        cs = np.einsum("...i,...i", u, w) / np.maximum(
            np.linalg.norm(u, axis=-1) * np.linalg.norm(w, axis=-1), 1e-300)
        return np.arccos(np.clip(cs, -1.0, 1.0))

    for a, b, c in (((0, 0), (1, 0), (0, 1)), ((1, 0), (1, 1), (0, 1))):
        def blk(o):
            return grid[o[0]:n - 1 + o[0], o[1]:m - 1 + o[1]]
        P, Q, R = blk(a), blk(b), blk(c)
        tri = 0.5 * np.linalg.norm(np.cross(Q - P, R - P), axis=-1)
        for o, ang in ((a, corner(P, Q, R)), (b, corner(Q, R, P)),
                       (c, corner(R, P, Q))):
            deficit[o[0]:n - 1 + o[0], o[1]:m - 1 + o[1]] -= ang
            area[o[0]:n - 1 + o[0], o[1]:m - 1 + o[1]] += tri / 3.0
    return deficit[1:n - 1, 1:m - 1], area


# ---------------------------------------------------------------------------
# The records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShellComplexity:
    """Geometry-only buildability. CHEAP — no nesting, no LM fit.

    Every area is for the WHOLE shell (both sides), matching
    `energy.shell_area_m2`, so a reader never has to ask whether a number is
    per side. The strips are computed on the starboard half and doubled, and
    that doubling is the only place it happens.
    """

    # protocol — recorded, never assumed
    n_stations: int
    n_rulings: int
    end_mask_frac: float

    # areas and mass, every one IMPORTED from the module that owns it
    shell_area_m2: float          # energy.shell_area_m2 (wetted to the sheer)
    deck_area_m2: float           # Hull.deck_area
    wetted_area_m2: float         # Hull.wetted_surface at the floated WL
    build_area_m2: float          # shell + deck — optimize.py's objective 2
    structure_kg: float           # energy.weight_budget

    # non-developability, on the constant-x ruling family
    twist_max: float
    twist_median: float
    non_developable_area_m2: float

    # Gaussian curvature, intrinsic
    gauss_abs_integral: float
    gauss_abs_mean_per_m2: float          # DIAGNOSTIC ONLY — see the module
    gauss_max_abs_per_vertex: float

    # the L0 gate's own developability number, imported not recomputed
    panel_twist_deg_per_m: float

    @property
    def non_developable_frac(self) -> float:
        """Int|sin psi| dA / shell area. Dimensionless shape difficulty.

        Reported for READING, never as an objective, and for the same reason
        the area-averaged curvature is refused: its denominator is a quantity
        the optimiser controls.
        """
        return self.non_developable_area_m2 / max(self.shell_area_m2, 1e-12)


@dataclass(frozen=True)
class NestingComplexity:
    """Panel, sheet and waste metrics. EXPENSIVE (~4 s/hull) — opt in.

    Straight off `engineer.assess`, which counts sheets from the layout
    `unroll.nest` actually produces. `material_waste_frac` is derived here
    because nothing else names it, and it is derived from the two areas that
    report already carries rather than from a declared packing efficiency —
    the declared one (`engineer.WASTE_FACTOR = 1.30`) is what the measured
    layout retired.
    """

    panel_count: int
    ply_sheets: int
    sheet_area_m2: float
    panel_area_m2: float
    nest_utilisation: float
    material_waste_frac: float
    build_hours: float
    bottom_thickness_mm: float
    thickness_basis: str


# ---------------------------------------------------------------------------
# The measurements
# ---------------------------------------------------------------------------


def shell_complexity(hull: Hull, wl: float = 0.0,
                     spec: EnergySpec | None = None,
                     n_stations: int | None = None,
                     n_rulings: int | None = None,
                     panel_thickness_m: float = PLY_THICKNESS_M
                     ) -> ShellComplexity:
    """Geometry-only buildability metrics for one hull.

    `wl` is the FLOATED waterline and is passed to `Hull.wetted_surface` only;
    every other quantity here is a property of the moulded surface and does not
    depend on how deep the boat is sitting. Stated because mixing a floated
    quantity with a moulded one inside one record is how gap E7 happened.

    MEASURED on the four hulls experiment 5 reports (SHELL_GRID, END_MASK_FRAC
    0.10, reference genes except as noted):

        hull                    shell A   nondev m^2   Int|K|dA   Int|K|/A
        reference (LWL 12)       33.825      9.380      0.00581   3.42e-4
        R_t optimum (LWL 12)     40.730      8.790      0.00594   2.90e-4
        R_w-only opt (LWL 20)   114.276     29.464      0.00575   1.00e-4
        deliberately warped      33.957     11.532      0.06182   3.62e-3

    THE LAST ROW IS THE CONTROL, and it is what makes the curvature number mean
    something: a hull with the deadrise warped 2 -> 45 deg over 0.6 L and 25 deg
    of flare has **10.6x** the reference's curvature integral at the SAME shell
    area. A metric that could not tell that hull from the reference would not be
    measuring shape difficulty, and this one separates them by an order of
    magnitude while the areas agree to 0.4%.
    """
    spec = EnergySpec() if spec is None else spec
    ns = int(SHELL_GRID["n_stations"] if n_stations is None else n_stations)
    nv = int(SHELL_GRID["n_rulings"] if n_rulings is None else n_rulings)

    twists: list[np.ndarray] = []
    nondev = 0.0
    k_abs = 0.0
    k_max = 0.0
    strip_area = 0.0
    for A, B, grid in _strips(hull, ns, nv):
        width = np.linalg.norm(B - A, axis=1)
        keep = width > END_MASK_FRAC * float(width.max())
        if int(np.count_nonzero(keep)) < 3:
            raise BuildabilityError(
                f"shell_complexity: only {int(keep.sum())} of {ns} stations "
                f"survive the {END_MASK_FRAC:.0%} ruling-width mask. This hull "
                f"has no strip to measure and a zero would be reported as "
                f"perfectly buildable.")
        tw = ruling_twist(A, B)
        # Element area per STATION: the along-edge step times the mean ruling
        # length, then split half to each neighbouring station so the weights
        # sum to the strip area rather than to a shifted copy of it.
        step = np.linalg.norm(np.diff(A, axis=0), axis=1)
        cell = step * 0.5 * (width[:-1] + width[1:])
        w = np.concatenate([[cell[0] / 2.0],
                            (cell[:-1] + cell[1:]) / 2.0,
                            [cell[-1] / 2.0]])
        twists.append(tw[keep])
        nondev += float(np.sum(tw[keep] * w[keep]))

        deficit, area = _angle_deficit(grid)
        k_abs += float(np.sum(np.abs(deficit[keep[1:ns - 1]])))
        k_max = max(k_max, float(np.abs(deficit).max()))
        strip_area += float(area.sum())

    tw_all = np.concatenate(twists)
    shell = shell_area_m2(hull)
    deck = hull.deck_area()
    wb = weight_budget(float(hull.x[-1]),
                       float(grammar.named(hull.params)["D"]),
                       shell, deck, spec, panel_thickness_m)
    return ShellComplexity(
        n_stations=ns, n_rulings=nv, end_mask_frac=END_MASK_FRAC,
        shell_area_m2=shell, deck_area_m2=deck,
        wetted_area_m2=hull.wetted_surface(wl),
        build_area_m2=shell + deck, structure_kg=wb.structure_kg,
        twist_max=float(tw_all.max()), twist_median=float(np.median(tw_all)),
        non_developable_area_m2=2.0 * nondev,
        gauss_abs_integral=k_abs,
        gauss_abs_mean_per_m2=k_abs / max(strip_area, 1e-12),
        gauss_max_abs_per_vertex=k_max,
        panel_twist_deg_per_m=hull.panel_twist_rate(),
    )


def nesting_complexity(hull: Hull, wl: float = 0.0,
                       mldc_kg: float | None = None) -> NestingComplexity:
    """Panel, sheet and waste metrics — via `engineer.assess`, which owns them.

    EXPENSIVE: ~3.6 s on the reference hull, because `unroll.hull_panels` runs
    a Levenberg-Marquardt developable pairing and `engineer` searches
    `STRAKE_TRIALS` layouts. Call it on the handful of hulls a decision turns
    on, never inside a sweep.

    MEASURED on experiment 5's optima, nominal stock sheet (no mLDC), and this
    is the table that prices the gaming direction in materials and labour:

        hull                   panels   sheets   util   waste   build hours
        reference (LWL 12)         41       31   0.823   0.498         1123
        R_t optimum (LWL 12)       41       34   0.824   0.470         1299
        R_w-only opt (LWL 20)      73      114   0.821   0.552         4778

    The R_w-only optimum costs **3.35x the plywood** and **3.68x the labour**
    of the hull that minimises the quantity this project actually reports, and
    it is 28.7% worse on that quantity as well. Utilisation barely moves
    (0.824 -> 0.821), which is the point: the nesting is not what got worse,
    the BOAT did, and a layout-efficiency metric alone would not have seen it.

    Note the 3.35x in sheets against 3.35x in `non_developable_area_m2` from
    `shell_complexity` — the cheap geometry proxy tracks the expensive counted
    layout to two significant figures on this pair. That is ONE PAIR OF HULLS
    and it is not a calibration; it is the reason the cheap metric is worth
    carrying in a sweep where the expensive one cannot be afforded.

    The import is deliberately LATE. `engineer` imports `unroll`, which imports
    `geometry`, and this module is meant to stay importable by anything that
    only wants `shell_complexity`; paying the developable-pairing import at
    module load would put a heavy dependency behind a cheap metric.
    """
    from .engineer import assess

    rep = assess(hull, wl=wl, mldc_kg=mldc_kg)
    if rep.sheet_area_m2 <= 0.0:
        raise BuildabilityError(
            f"nesting_complexity: engineer.assess returned sheet_area_m2 = "
            f"{rep.sheet_area_m2!r}. A waste fraction cannot be computed "
            f"against a zero sheet area and REFUSING is the only honest "
            f"answer — 1 - x/0 would print as perfect utilisation.")
    basis = ("ISO 12215-5 derived" if mldc_kg is not None
             else "nominal stock sheet — NOT rule-derived")
    return NestingComplexity(
        panel_count=rep.panel_count, ply_sheets=rep.ply_sheets,
        sheet_area_m2=rep.sheet_area_m2, panel_area_m2=rep.panel_area_m2,
        nest_utilisation=rep.nest_utilisation,
        material_waste_frac=1.0 - rep.panel_area_m2 / rep.sheet_area_m2,
        build_hours=rep.build_hours,
        bottom_thickness_mm=rep.bottom_thickness_mm,
        thickness_basis=basis,
    )


def refinement_residual(hull: Hull, wl: float = 0.0) -> dict[str, float]:
    """|metric(SHELL_GRID) - metric(REFINEMENT_CHECK)|, per metric.

    THE SIGMA ON EVERY NUMBER IN `ShellComplexity` IS THIS, and it is a
    MEASUREMENT rather than a declared percentage — the same rule
    `experiments.hydro_quantities` applies to the hydrostatic integrals. A
    caller that reports a complexity metric without it is reporting a
    quadrature to more digits than it has.
    """
    a = shell_complexity(hull, wl)
    b = shell_complexity(hull, wl, n_stations=REFINEMENT_CHECK["n_stations"],
                         n_rulings=REFINEMENT_CHECK["n_rulings"])
    return {
        "non_developable_area_m2": abs(a.non_developable_area_m2
                                       - b.non_developable_area_m2),
        "gauss_abs_integral": abs(a.gauss_abs_integral - b.gauss_abs_integral),
        "gauss_abs_mean_per_m2": abs(a.gauss_abs_mean_per_m2
                                     - b.gauss_abs_mean_per_m2),
        "twist_max": abs(a.twist_max - b.twist_max),
    }


# ---------------------------------------------------------------------------
# The kit-line admission: the gate metric itself, as a certification check
# ---------------------------------------------------------------------------


def kit_buildability(hull: Hull) -> dict:
    """Can THIS hull be built from CNC-cut flat sheets? The measured answer.

    Runs the actual Gate 6D meter — `unroll.hull_panels` (the shipped
    developable fit) refolded onto the moulded surface via
    `refold_surface_deviation_mm`, both panels, against `limits.REFOLD_BAR_MM`
    — and returns a BUILD ROUTE, not a pass/fail on the hull:

        route = "sheet-kit"   both panels refold within the bar
        route = "mould"       the shell is intrinsically too twisted (or has
                              a radiused bilge) — build it on a mould/strip-
                              plank; a routing fact, not a defect

    WHY A ROUTE AND NOT A GATE ON EVERY HULL — the 2026-08-19 measurement
    campaign, reference 7 m hull:

      * The deviation is INTRINSIC surface twist, not unroller error.
        Transverse seams at 1, 2 and 3 stations moved the two-sided set
        metric by < 0.1 mm (bottom stayed 124.0 mm to the second decimal):
        the twist is local to the forefoot, not accumulated along the
        development, so no amount of cutting fixes it.
      * Dial isolation: deadrise warp (8 -> 30 deg) alone puts the bottom at
        ~52 mm even under a C1-smooth area curve; flare 10 deg alone holds
        the topside above ~40 mm; forefoot rise contributes at the ~1 mm
        level on its own but interacts with warp.
      * THE LOW-TWIST CORNER EXISTS, under the shipped kernel: at
        flare = 0, forefoot = 0, warp <= +8 deg the reference proportions
        measure 4.6-5.0 mm on BOTH panels — sharpie/dory-class shapes. The
        kit product class is that corner; everything else is a mould boat.

    Cost: ~9 s on the reference hull (the developable-pairing LM ladder is
    ~4 s and the two-sided meter ~5 s), which is why `certify` runs this only
    when asked (`with_kit=True`) and records honestly when it did not.
    """
    from .limits import REFOLD_BAR_MM
    from .unroll import hull_panels, refold_surface_deviation_mm

    try:
        panels = hull_panels(hull)
    except ValueError as e:
        # roundness > 0: a radiused bilge is not a two-panel developable
        # shell — the unroller's own refusal text says "take this hull to a
        # mould, not a cutter", and this is where that routing lands.
        return {"route": "mould", "kit_buildable": False,
                "why": str(e), "bar_mm": REFOLD_BAR_MM,
                "basis": BASIS_GEOMETRY}
    refold_mm = {p.name: float(refold_surface_deviation_mm(hull, p))
                 for p in panels}
    ok = all(v <= REFOLD_BAR_MM for v in refold_mm.values())
    return {"route": "sheet-kit" if ok else "mould",
            "kit_buildable": ok,
            "refold_mm": refold_mm,
            "bar_mm": REFOLD_BAR_MM,
            "why": ("both panels refold within the bar" if ok else
                    "intrinsic shell twist exceeds the kit bar — mould build"),
            "basis": BASIS_GEOMETRY}
