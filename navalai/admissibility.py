"""CFD-admissibility screen: is this grammar-valid hull one the MESHER can hold?

WHY THIS FILE EXISTS. `grammar.check()` decides "valid hull" from closed-form
naval-architecture constraints plus one developability metric, and
`evaluate()` adds "L1 physics returns a finite number". Neither asks the
question the Gate 2U campaign is failing on: can the STL ->
snappyHexMesh -> prism-layer pipeline represent this shape at the cell size
the pipeline picks? MEASURED on the seed-0 batch (`--n 25`, scale 1.0, speed
2.57, LTS, np=10, `data/gate2u-campaign-baseline.json`): of the first 18 hulls
recorded, **6 meshed and 12 did not** — a 33% mesh rate against a >=95% bar,
with the failures spread over `checkmesh-wrong-oriented` (7),
`checkmesh-zero-volume` (3), `checkmesh-skewness` (1) and
`mesh-build-failed` (1). Every one of those 18 hulls passes `grammar.check()`.

WHAT THIS FILE DOES NOT CLAIM. It is a SCREEN, not a predictor. Two bars below
are derived from the pipeline's own constants and validated against the
labelled campaign; between them they refuse 6 of 12 observed mesh failures
with 0 false alarms on 6 successes — **TP 6, FP 0, FN 6, TN 6; precision
1.000, recall 0.500; Fisher exact one-sided p = 0.0498**, which is evidence
and is not proof. The other half of the failures are NOT predicted by
anything measured here, and the metrics an external review expected to predict
them — the stem cusp and the x_mb tangent break — MEASURED AUC 0.500 and 0.500
respectively on that set, i.e. exactly chance. They are kept as DIAGNOSTIC
readings, reported and forbidden to vote, precisely so a later session cannot
mistake "we compute it" for "it predicts".

WHAT "DANGEROUS" ACTUALLY MEANS HERE, AND IT IS NARROWER THAN THE NAME.
MEASURED 2026-08-11 on the back-off campaign
(`data/gate2u-campaign-backoff-mesh.json`, same seed and hulls, mesh-only,
`--layer-backoff 3`): **every hull this screen refuses meshes cleanly once the
prism-layer ladder is allowed to step down** — hulls 0, 1, 5, 6 and 11 at 8, 7,
8, 8 and 7 layers, 0 zero-volume and 0 wrongly-oriented faces, skew 4.5/3.3/
4.5/4.7/5.1. Over hulls 0-11 the rate goes **3 of 12 at rung 0 to 11 of 12**
with the ladder. So a DANGEROUS verdict here predicts *"this hull will be
refused at the DERIVED layer count"*, not *"this hull cannot be meshed"*, and
the one hull that still fails with the ladder (hull 4) this screen calls SAFE.
Naming it otherwise would be the same defect as a gate that reports the
requested spec under the label of the achieved result.

WHAT IT MEASURES ABOUT THE MANIFOLD. Over 200 grammar-valid hulls (seed 1234,
speed 2.57, scale 1): **68 DANGEROUS / 79 MARGINAL / 53 SAFE**. 19.5% put the
keel inside the free-surface refinement band and 17.0% carry a sheer the
geometry kernel silently clipped to zero. So a third of what `grammar.check()`
blesses is fragile at the derived layer count — the review's structural claim,
quantified and then bounded by the paragraph above.

The bars are per-metric and typed, and there is no single opaque score: a
single score is what lets a system tune the design space until the number goes
green. `docs/BUILD-PLAN.md` §11.6 specifies the gate that consumes this —
Gate 2U split into 2U-A (raw grammar, the denominator that may not be
narrowed) and 2U-B (admissible domain), reported as an eight-stage funnel and
never as one rate. This module supplies exactly one stage of it,
`geometry-admissible`, and is not permitted to be the gate.

COST: no OpenFOAM, no snappy, no STL written to disk. MEASURED 7.6 ms per hull,
so a 200-hull screen is ~1.5 s against a mesh cost of ~80 s each (4.4 hours) —
four orders of magnitude, which is the whole point and is pinned by a test.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass

import numpy as np

from . import grammar
from .cfd.case import (_DOMAIN_LENGTH_L, _HULL_REFINE, _LAYER_EXPANSION,
                       _NX_BASE, _refine_boxes, layer_spec, stl_resolution)
from .geometry import Hull, station_geometry


class Verdict(enum.Enum):
    """Typed, because a verdict carried as a free-form string is editable prose.

    docs/LESSONS.md defect class 4: a measured RED gate that lived in a `scope`
    string could be turned green by editing the string. The ORDER matters —
    `worst()` below takes the maximum.
    """

    SAFE = 0
    MARGINAL = 1
    DANGEROUS = 2
    UNMEASURED = 3          # strictly worse than DANGEROUS: see `Metric.of`

    def __str__(self) -> str:                     # pragma: no cover - display
        return self.name


class Basis(enum.Enum):
    """WHERE A BAR CAME FROM, carried with the bar so it cannot be laundered.

    DERIVED       the bar is computed from the pipeline's own constants
                  (`_FS_BOX`, `_HULL_REFINE`, `_NX_BASE`) and moves when they
                  move. Not a guess and not fitted to any outcome.
    MEASURED      the bar is a value observed to separate real cases, and the
                  cases are named in the metric's `note`.
    PROVISIONAL   the bar is a judgement call. Say so, out loud, in the report.
    DIAGNOSTIC    THERE IS NO BAR. The metric is reported and does not vote.
    """

    DERIVED = "derived"
    MEASURED = "measured"
    PROVISIONAL = "provisional"
    DIAGNOSTIC = "diagnostic"


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    unit: str
    verdict: Verdict
    basis: Basis
    note: str
    danger_below: float | None = None
    danger_above: float | None = None

    @property
    def votes(self) -> bool:
        return self.basis is not Basis.DIAGNOSTIC

    @classmethod
    def of(cls, name, value, unit, basis, note, *,
           danger_below=None, danger_above=None,
           margin_below=None, margin_above=None) -> "Metric":
        """Classify `value` against the bars, refusing an unmeasurable one.

        AN UNMEASURABLE METRIC IS FATAL, NEVER A DEFAULT (docs/LESSONS.md
        defect class 1: `${_MQ_SKEW:-0}` scored a failure to measure as a
        perfect 0 against a bar of 20). A non-finite value here is UNMEASURED
        and UNMEASURED is worse than DANGEROUS, so it can never be the reason a
        hull is admitted.
        """
        if value is None or not math.isfinite(float(value)):
            return cls(name, float("nan"), unit, Verdict.UNMEASURED, basis,
                       f"NOT MEASURABLE: {note}", danger_below, danger_above)
        v = float(value)
        if basis is Basis.DIAGNOSTIC:
            verdict = Verdict.SAFE
        elif ((danger_below is not None and v < danger_below)
                or (danger_above is not None and v > danger_above)):
            verdict = Verdict.DANGEROUS
        elif ((margin_below is not None and v < margin_below)
                or (margin_above is not None and v > margin_above)):
            verdict = Verdict.MARGINAL
        else:
            verdict = Verdict.SAFE
        return cls(name, v, unit, verdict, basis, note,
                   danger_below, danger_above)


@dataclass(frozen=True)
class Report:
    """Per-metric values and per-metric verdicts. There is no scalar score."""

    verdict: Verdict
    metrics: tuple[Metric, ...]
    hull_cell_m: float
    lwl_m: float
    n_layers: int

    @property
    def refused_by(self) -> tuple[str, ...]:
        return tuple(m.name for m in self.metrics
                     if m.votes and m.verdict in (Verdict.DANGEROUS,
                                                  Verdict.UNMEASURED))

    @property
    def marginal_on(self) -> tuple[str, ...]:
        return tuple(m.name for m in self.metrics
                     if m.votes and m.verdict is Verdict.MARGINAL)

    def get(self, name: str) -> Metric:
        for m in self.metrics:
            if m.name == name:
                return m
        raise KeyError(name)

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict.name,
            "lwl_m": self.lwl_m,
            "hull_cell_m": self.hull_cell_m,
            "n_layers": self.n_layers,
            "refused_by": list(self.refused_by),
            "marginal_on": list(self.marginal_on),
            "metrics": {m.name: {"value": m.value, "unit": m.unit,
                                 "verdict": m.verdict.name,
                                 "basis": m.basis.value, "note": m.note}
                        for m in self.metrics},
        }


# --------------------------------------------------------------------------
# The surface the MESHER sees, not the surface the grammar describes.
# --------------------------------------------------------------------------

def surface_grid(hull: Hull, nx: int, nz: int) -> np.ndarray:
    """Vectorised replica of the vertex grid `Hull.closed_mesh` triangulates.

    (nx, nz+1, 3), starboard side only (port is the mirror).

    THIS IS A SECOND COPY OF A GEOMETRY DEFINITION, which is the defect class
    this repository pays for most often, so it is fenced rather than trusted:
    `tests/test_admissibility.py::test_surface_grid_is_the_closed_mesh_grid`
    asserts it equals `Hull._section_at` + `_halfbreadth_at` — the two private
    helpers `closed_mesh` itself calls — at every grid point of a real hull. It
    exists because `closed_mesh` is a Python double loop that costs ~1.4 s per
    hull at 600x120, i.e. ~5 minutes for a 200-hull screen, against 7 ms here.

    NOTE what this shows and the closed form does not: `closed_mesh` samples
    the STATION polylines (41 of them) and interpolates LINEARLY in x, so the
    STL carries a crease at every station and its true longitudinal resolution
    is Lwl/40 (0.25 m on a 10 m hull) however many triangles are written.

    UPDATED 2026-08-12 with `closed_mesh`: the section is sampled PER PANEL
    (keel->chine, chine->sheer) with the chine on row `hull.chine_row(nz)`,
    not uniformly in z across the whole section. The row split is imported
    from `Hull`, never restated here — this function is already a second copy
    of a surface and one number declared twice inside it is enough.
    """
    xs = np.linspace(float(hull.x[0]), float(hull.x[-1]), nx)
    xst = hull.x
    i = np.clip(np.searchsorted(xst, xs), 1, hull.n_stations - 1)
    f = (xs - xst[i - 1]) / (xst[i] - xst[i - 1])

    def lerp(a):
        return a[i - 1] * (1 - f) + a[i] * f

    zk, yc, zc = lerp(hull.z_keel), lerp(hull.y_chine), lerp(hull.z_chine)
    ys, zs = lerp(hull.y_sheer), lerp(hull.z_sheer)
    jc = hull.chine_row(nz)
    t_lo = np.linspace(0.0, 1.0, jc + 1)
    t_hi = np.linspace(0.0, 1.0, nz - jc + 1)[1:]
    Y = np.empty((len(xs), nz + 1))
    Z = np.empty_like(Y)
    Y[:, :jc + 1] = yc[:, None] * t_lo[None, :]
    Z[:, :jc + 1] = zk[:, None] + (zc - zk)[:, None] * t_lo[None, :]
    Y[:, jc + 1:] = yc[:, None] + (ys - yc)[:, None] * t_hi[None, :]
    Z[:, jc + 1:] = zc[:, None] + (zs - zc)[:, None] * t_hi[None, :]
    return np.stack([np.repeat(xs[:, None], nz + 1, axis=1), Y, Z], axis=-1)


def _quad_normals(S: np.ndarray):
    """Unit normal and validity mask per quad, from closed_mesh's triangle split."""
    a, b, c, d = S[:-1, :-1], S[:-1, 1:], S[1:, 1:], S[1:, :-1]
    n = np.cross(b - a, c - a) + np.cross(c - a, d - a)
    ln = np.linalg.norm(n, axis=-1)
    return np.divide(n, np.where(ln > 1e-14, ln, 1.0)[..., None]), ln > 1e-14


def _angle_deg(u, v):
    return np.degrees(np.arccos(np.clip(np.sum(u * v, axis=-1), -1.0, 1.0)))


# --------------------------------------------------------------------------
# The screen
# --------------------------------------------------------------------------

def _pipeline_scales(lwl: float, speed: float, scale: float) -> dict:
    """Cell size, prism stack and refinement band — READ FROM THE PIPELINE.

    Every number here is imported from `navalai.cfd.case`, never restated. If
    `_HULL_REFINE`, `_NX_BASE` or `_FS_BOX` move, these bars move with them,
    which is the only way a screen of a pipeline stays a screen OF THAT
    PIPELINE (docs/LESSONS.md defect class 2).
    """
    spec = layer_spec(lwl, speed, scale)
    # `layer_spec` reports the cell at the MINIMUM hull refinement level; the
    # surface actually snaps at the maximum, one level finer.
    cell = spec["hull_cell_m"] / 2.0 ** (_HULL_REFINE[1] - _HULL_REFINE[0])
    stack = (spec["first_layer_m"]
             * (_LAYER_EXPANSION ** spec["n_layers"] - 1) / (_LAYER_EXPANSION - 1))
    bg_dx = _DOMAIN_LENGTH_L * lwl / max(int(round(_NX_BASE * scale)), 20)
    nx, nz = stl_resolution(lwl, 0.5 * bg_dx / 2 ** _HULL_REFINE[1])
    return {"cell": cell, "stack": stack, "n_layers": spec["n_layers"],
            "first_layer_m": spec["first_layer_m"], "nx": nx, "nz": nz,
            # half-height of the TIGHTEST post-snappy z-refinement box
            "fs_band_m": _refine_boxes(lwl, True)[-1]["bz1"]}


def screen(hull: Hull | np.ndarray, speed: float = 2.57,
           scale: float = 1.0) -> Report:
    """CFD-admissibility of one hull, without meshing it.

    `speed` and `scale` are the case the hull would be meshed FOR: every bar
    below is relative to the cell size that case picks, so the same hull can be
    admissible at one scale and not at another. State the configuration
    (docs/LESSONS.md defect class 6).

    THE CONFIGURATION THIS VERDICT IS ABOUT is the pipeline at **rung 0** — the
    layer count `n_layers_to_bridge` derives, no back-off. Measured, every hull
    it refuses meshes with the ladder enabled (module docstring). Read a
    DANGEROUS as "expect a checkMesh refusal at the derived layer count", which
    is worth ~80 s of snappy per hull to know in 7.6 ms, and not as "this hull
    is unmeshable".
    """
    h = hull if isinstance(hull, Hull) else Hull(np.asarray(hull, dtype=float))
    x = h.params
    p = grammar.named(x)
    lwl = float(h.x[-1])
    sc = _pipeline_scales(lwl, speed, scale)
    cell = sc["cell"]

    t = np.linspace(0.0, lwl, 4001)
    zk, yc, zc, ysh, zs = station_geometry(x, t)
    interior = t < 0.98 * lwl        # the last 2% is the stem run-out, below

    metrics: list[Metric] = []
    add = metrics.append

    # ---- V1: keel inside the post-snappy z-refinement box -----------------
    # The bar is `fs_band / cell`, computed from _FS_BOX and _HULL_REFINE. It
    # is 14.187 at scale 1 and it is NOT fitted to any outcome. Validated on
    # the labelled campaign (18 hulls, 6 meshed): it refuses hulls 0, 1, 6 and
    # 12 at 10.14, 12.31, 11.82 and 13.20 cells of draft, ALL FOUR of which
    # failed checkMesh, and refuses none of the 6 that meshed (minimum 20.13).
    # The nearest failure above the bar is 15.55, so the bar is not sitting in
    # a gap it was placed in.
    #
    # The MECHANISM is a candidate, not a finding: below this bar the keel sits
    # inside the band that `topoSet` + `refineMesh` split in z after snapping,
    # so the refinement transition wraps under the keel instead of crossing the
    # topsides. `navalai/cfd/case.py`'s TOPO_SET comment records that z-refine
    # transitions were the source of every wrongly-oriented face this project
    # had measured (0 rounds -> 0 faces in 7 of 7 meshes; 3 rounds -> 2..47 in
    # 4 of 4) before the hexes-only fix. NOT VERIFIED for these hulls: no
    # re-mesh with the band moved has been run. Do not quote it as established.
    draft = float(-zk.min())
    add(Metric.of("draft_over_hull_cell", draft / cell, "cells", Basis.DERIVED,
                  f"design draft in level-{_HULL_REFINE[1]} hull cells; below "
                  f"{sc['fs_band_m'] / cell:.3f} the keel is inside the "
                  f"tightest free-surface z-refinement box. 4 of 4 hulls below "
                  f"it failed checkMesh; 0 of 6 that meshed are below it.",
                  danger_below=sc["fs_band_m"] / cell,
                  margin_below=2.0 * sc["fs_band_m"] / cell))

    # ---- V2: the sheer half-breadth the grammar asked for was NEGATIVE ----
    # `station_geometry` writes `np.maximum(ys, 0.0)`, so when flare and the
    # topside height drive the sheer inboard of the centreline the code
    # SILENTLY SUBSTITUTES a different hull — a zero-width deck over a finite
    # run of x, where port and starboard topsides meet in a ridge and the deck
    # lid degenerates to zero-area quads that `closed_mesh` drops. That is a
    # geometry the grammar did not specify and nothing reports.
    #
    # The bar is > 0 stations clipped, which needs no calibration: it asks
    # whether the clip fired at all. Validated on the labelled campaign: it
    # refuses hulls 5, 11 and 12 (3.04, 2.13 and 4.36 cells of collapsed run),
    # all three of which failed to mesh, and no hull that meshed.
    #
    # ONE MECHANISM IS ALREADY REFUTED and is recorded so it is not re-proposed:
    # the collapsed deck does NOT open the STL. `stl_watertight_report` on
    # hulls 5, 11 and 12 at the case's own 600x120 triangulation returns 0
    # open/non-manifold edges, 0 winding conflicts, watertight True, outward
    # True — identical to hulls 7 and 13, which mesh. Whatever the collapsed
    # ridge does to snappy, it is not a hole.
    ys_unclipped = yc + (zs - zc) * math.tan(math.radians(p["flare"]))
    clipped = ys_unclipped <= 0.0
    run, best = 0, 0
    for c in clipped:
        run = run + 1 if c else 0
        best = max(best, run)
    add(Metric.of("sheer_collapse_cells", best * (t[1] - t[0]) / cell, "cells",
                  Basis.DERIVED,
                  "longest run of x where np.maximum(ys, 0.0) in "
                  "station_geometry replaced a NEGATIVE sheer half-breadth "
                  "with zero. Any non-zero run is a hull the grammar did not "
                  "specify. 3 of 3 labelled hulls with a non-zero run failed.",
                  danger_above=0.0))

    # ---- V3-V5: features thinner than the cell that must resolve them -----
    # A surface feature narrower than one cell cannot be represented by that
    # cell, whatever snappy does with it. The bar is 1.0 cell and it is DERIVED
    # (it IS the cell). None of these fire on campaign hulls 0-17 — the whole
    # labelled batch sits above them — so they carry NO validation from the
    # confusion matrix, and saying so is the point of this comment. They fire
    # on 0.5%, 0.0%, 0.5% and 0.0% of a 200-hull manifold respectively, and
    # campaign hull 20 trips the first and third at 0.998 cells each, which is
    # a PRE-REGISTERED prediction (docs/BUILD-PLAN.md §11.6).
    add(Metric.of("min_bottom_panel_width_cells",
                  float(yc[interior].min()) / cell, "cells", Basis.DERIVED,
                  "narrowest bottom panel (chine half-breadth) forward of the "
                  "stem run-out, in hull cells. A panel thinner than a cell "
                  "cannot be resolved by it. Unexercised by campaign hulls "
                  "0-17 (minimum 2.04 cells); 0.5% of a 200-hull manifold.",
                  danger_below=1.0, margin_below=2.0))
    add(Metric.of("min_topside_panel_height_cells",
                  float((zs - zc)[interior].min()) / cell, "cells",
                  Basis.DERIVED,
                  "shortest topside panel (sheer minus chine) in hull cells. "
                  "Unexercised by campaign hulls 0-17 (minimum 19.4) AND by "
                  "the 200-hull manifold (minimum 12.2). It has never fired.",
                  danger_below=1.0, margin_below=2.0))
    add(Metric.of("transom_half_beam_cells", float(yc[0]) / cell, "cells",
                  Basis.DERIVED,
                  "transom half-breadth in hull cells: the transom cap is a "
                  "flat patch and a sub-cell patch is a sub-cell feature. "
                  "Unexercised by campaign hulls 0-17 (minimum 3.97); 0.5% of "
                  "a 200-hull manifold.",
                  danger_below=1.0, margin_below=2.0))
    add(Metric.of("transom_immersion_cells", float(-zk[0]) / cell, "cells",
                  Basis.DERIVED,
                  "immersed transom depth in hull cells. Unexercised by "
                  "campaign hulls 0-17 (minimum 6.16) AND by the 200-hull "
                  "manifold (minimum 3.33). It has never fired.",
                  danger_below=1.0, margin_below=2.0))

    # ---- V6: prism stack against the LOCAL concave radius ------------------
    # A prism stack of height s inserted on a surface whose concave radius of
    # curvature is R self-intersects at s -> R: the layer normals converge. The
    # bar s/R < 1 is geometry, not calibration. The grammar's sections are two
    # straight segments, so the only transverse curvature is at the chine and
    # keel creases, which are CONVEX (layers diverge there, they do not fold);
    # the concave curvature that remains is longitudinal, on the keel rocker /
    # forefoot and the sheer rise.
    #
    # THE BREAKPOINTS ARE EXCLUDED, AND THE FIRST DRAFT OF THIS METRIC DID NOT
    # EXCLUDE THEM. `station_geometry` is piecewise about x_mb, 0.3L, 0.7L and
    # the deadrise-warp start, and at a C1 break a discrete curvature is not a
    # radius at all — it is 1/h and grows without bound as the sampling
    # refines. MEASURED on the labelled batch before the fix: `max kappa` gave
    # stack/R of 28..50 and the metric refused 16 of 18 hulls including 4 of
    # the 6 that meshed. A metric that refuses everything is not a screen, and
    # the number it was refusing on was a sampling artefact of the very
    # tangent break that `xmb_tangent_break_deg` reports as a DIAGNOSTIC.
    breakpoints = [p["x_mb"] * lwl, 0.3 * lwl, 0.7 * lwl,
                   lwl - p["beta_len"] * lwl]
    smooth = interior.copy()
    for bp in breakpoints:
        smooth &= np.abs(t - bp) > 3.0 * (t[1] - t[0])
    stack_over_r = 0.0
    for yy, zz in ((np.zeros_like(t), zk), (yc, zc), (ysh, zs)):
        d1 = np.stack([np.ones_like(t), np.gradient(yy, t), np.gradient(zz, t)], 1)
        d2 = np.stack([np.gradient(d1[:, k], t) for k in range(3)], 1)
        kappa = (np.linalg.norm(np.cross(d1, d2), axis=1)
                 / np.maximum(np.linalg.norm(d1, axis=1) ** 3, 1e-12))
        stack_over_r = max(stack_over_r, sc["stack"] * float(kappa[smooth].max()))
    add(Metric.of("stack_over_min_radius", stack_over_r, "-", Basis.DERIVED,
                  "prism-stack height x maximum edge-curve curvature away from "
                  "the four piecewise breakpoints. At 1.0 the stack is as tall "
                  "as the radius it bends around and the layer normals cross.",
                  danger_above=1.0, margin_above=0.5))

    # ---- DIAGNOSTIC: the two defects an external review expected to drive it
    # Both are REAL and both are CONFIRMED analytically (see
    # docs/BUILD-PLAN.md). Neither predicts the observed mesh outcome, so
    # neither votes. Recorded here so the next session does not re-derive them
    # and then assume they matter.
    #
    # (a) y_sheer = max(ys,0) * max(w,0)**0.15 has an UNBOUNDED x-derivative at
    #     the stem: w ~ p_bow*(L-x)/(L-x_mb) there, so y_sheer ~ (L-x)**0.15
    #     and dy/dx ~ (L-x)**-0.85 -> -inf. Measured local exponent on the
    #     reference hull: 0.3265 at 0.1 m from the stem, 0.1714 at 10 mm,
    #     0.1502 at 0.1 mm, 0.1500 at 1 um. In CFD terms the deck is already
    #     `bow_bluntness` cells wide one cell aft of the stem, i.e. the bow
    #     closes over a length the mesh cannot resolve. It is a property of the
    #     GRAMMAR, present in every hull it emits (median 6.2 cells over 200),
    #     and MEASURED AUC against mesh failure on the labelled batch: 0.500.
    # (b) the chine/sheer plan-form is piecewise about x_mb with dw/dx jumping
    #     from (1-r_transom)*p_stern/x_mb to 0. On the reference hull the chine
    #     tangent breaks by 12.308 deg and the closed form matches the
    #     prediction 0.5*B*(1-r)*p_stern/(x_mb*L) to 6 significant figures.
    #     MEASURED AUC against mesh failure: 0.500.
    add(Metric.of("bow_bluntness_cells",
                  float(station_geometry(x, np.array([lwl - cell]))[3][0]) / cell,
                  "cells", Basis.DIAGNOSTIC,
                  "sheer half-breadth one hull cell aft of the stem. The "
                  "w**0.15 taper gives an unbounded plan-form tangent there, "
                  "so this is how many cells wide the bow already is at the "
                  "first cell. AUC vs mesh failure on the labelled batch: "
                  "0.500 (chance). Reported, does not vote."))
    xm = p["x_mb"] * lwl
    eps = 1e-5 * lwl

    def _slope(idx, a, b):
        return float(station_geometry(x, np.array([b]))[idx][0]
                     - station_geometry(x, np.array([a]))[idx][0]) / (b - a)

    breaks = [abs(math.degrees(math.atan(_slope(i, xm - 2 * eps, xm - eps))
                               - math.atan(_slope(i, xm + eps, xm + 2 * eps))))
              for i in (1, 3)]
    add(Metric.of("xmb_tangent_break_deg", max(breaks), "deg", Basis.DIAGNOSTIC,
                  "plan-form tangent discontinuity at x_mb, max over chine and "
                  "sheer. AUC vs mesh failure on the labelled batch: 0.500 "
                  "(chance). Reported, does not vote."))

    S = surface_grid(h, sc["nx"], sc["nz"])
    N, ok = _quad_normals(S)
    good = ok[:-1] & ok[1:]
    dih = np.where(good, _angle_deg(N[:-1], N[1:]), np.nan)
    add(Metric.of("max_facet_turn_deg", float(np.nanmax(dih)), "deg",
                  Basis.DIAGNOSTIC,
                  "largest normal change between longitudinally adjacent STL "
                  "quads. Dominated by the 41-station crease pattern, not by "
                  "the hull's shape: labelled failures span 24.7..40.9 deg and "
                  "successes 24.9..42.2 deg, AUC 0.673. Does not vote."))
    add(Metric.of("stack_over_hull_cell", sc["stack"] / cell, "-",
                  Basis.DIAGNOSTIC,
                  "prism-stack height in hull cells. docs/LESSONS.md records a "
                  "build-time cap on this ratio being DRAFTED AND KILLED by "
                  "its own data (Wigley solves at 1.084, KCS dies at 0.952). "
                  "Labelled AUC 0.621. Does not vote, for that reason."))
    add(Metric.of("derived_n_layers", float(sc["n_layers"]), "layers",
                  Basis.DIAGNOSTIC,
                  "prism-layer count `n_layers_to_bridge` derives for this "
                  "hull. It is 8-10 for essentially every hull the grammar "
                  "emits, so it cannot separate them — but it is the lever the "
                  "back-off campaign moved: on hulls 0-4, rung 0 meshed 1 of 5 "
                  "and the back-off ladder meshed 4 of 5. Does not vote."))
    add(Metric.of("panel_twist_deg_per_m", h.panel_twist_rate(), "deg/m",
                  Basis.DIAGNOSTIC,
                  "the grammar's own developability metric, repeated here so "
                  "the two screens can be compared on one line. Gated by "
                  "grammar.check at "
                  f"{grammar.MAX_PANEL_TWIST_DEG_PER_M:.0f} deg/m, so every "
                  "hull reaching this screen is already under it."))

    worst = max((m.verdict for m in metrics if m.votes), default=Verdict.SAFE,
                key=lambda v: v.value)
    return Report(worst, tuple(metrics), cell, lwl, sc["n_layers"])


# --------------------------------------------------------------------------
# CLI: the manifold, and the confusion matrix against a real campaign
# --------------------------------------------------------------------------

def _confusion(screened: list[tuple[int, Report]], rows: list[dict]) -> dict:
    """Screen verdict vs the campaign's own `meshed` flag, per hull."""
    by_hull = {r["hull"]: r for r in rows}
    tp = fp = fn = tn = 0
    detail = []
    for hid, rep in screened:
        row = by_hull.get(hid)
        if row is None:
            continue
        failed = not row["meshed"]
        refused = rep.verdict in (Verdict.DANGEROUS, Verdict.UNMEASURED)
        tp += refused and failed
        fp += refused and not failed
        fn += (not refused) and failed
        tn += (not refused) and not failed
        detail.append({"hull": hid, "verdict": rep.verdict.name,
                       "refused_by": list(rep.refused_by),
                       "meshed": row["meshed"], "why": row["why"]})
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": prec, "recall": rec, "detail": detail}


def main(argv=None) -> int:                       # pragma: no cover - CLI
    import argparse
    import json
    from pathlib import Path

    from .evaluate import sample_valid
    from .mission import MissionSpec

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--speed", type=float, default=2.57)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--campaign", default=None,
                    help="a mesh_robustness --json record. The hulls are "
                         "regenerated from ITS seed and n, and the screen is "
                         "scored against its `meshed` column.")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    if args.campaign:
        rec = json.loads(Path(args.campaign).read_text())
        X, _ = sample_valid(max(r["hull"] for r in rec["rows"]) + 1,
                            MissionSpec(), seed=rec["seed"])
        screened = [(r["hull"], screen(X[r["hull"]], rec["speed"], rec["scale"]))
                    for r in rec["rows"]]
        cm = _confusion(screened, rec["rows"])
        print(f"{args.campaign}: n={rec['n']} seed={rec['seed']} "
              f"speed={rec['speed']} scale={rec['scale']}")
        print(f"{'#':>3} {'verdict':<11} {'meshed':>6} {'why':<26} refused_by")
        for d in cm["detail"]:
            print(f"{d['hull']:3d} {d['verdict']:<11} {str(d['meshed']):>6} "
                  f"{d['why']:<26} {','.join(d['refused_by'])}")
        print(f"\nconfusion (refused = screen says DANGEROUS/UNMEASURED, "
              f"positive = hull FAILED to mesh)")
        print(f"  TP {cm['tp']}   FP {cm['fp']}   FN {cm['fn']}   TN {cm['tn']}")
        print(f"  precision {cm['precision']:.3f}   recall {cm['recall']:.3f}")
        if args.json:
            Path(args.json).write_text(json.dumps(cm, indent=2))
        return 0

    X, _ = sample_valid(args.n, MissionSpec(), seed=args.seed)
    reps = [screen(x, args.speed, args.scale) for x in X]
    names = [m.name for m in reps[0].metrics]
    print(f"{args.n} grammar-valid hulls, seed {args.seed}, speed "
          f"{args.speed} m/s, scale {args.scale}")
    print(f"\n{'metric':<32} {'basis':<12} {'min':>9} {'p05':>9} {'median':>9} "
          f"{'p95':>9} {'max':>9}  refused%")
    for nm in names:
        v = np.array([r.get(nm).value for r in reps])
        b = reps[0].get(nm).basis
        bad = 100.0 * np.mean([r.get(nm).verdict in (Verdict.DANGEROUS,
                                                     Verdict.UNMEASURED)
                               for r in reps])
        print(f"{nm:<32} {b.value:<12} {np.nanmin(v):9.3f} "
              f"{np.nanpercentile(v, 5):9.3f} {np.nanmedian(v):9.3f} "
              f"{np.nanpercentile(v, 95):9.3f} {np.nanmax(v):9.3f}  "
              f"{'' if b is Basis.DIAGNOSTIC else f'{bad:6.1f}%'}")
    tally: dict[str, int] = {}
    for r in reps:
        tally[r.verdict.name] = tally.get(r.verdict.name, 0) + 1
    print("\nverdict over the manifold:", tally)
    ref: dict[str, int] = {}
    for r in reps:
        for nm in r.refused_by:
            ref[nm] = ref.get(nm, 0) + 1
    print("refused by:", ref or "(nothing)")
    if args.json:
        Path(args.json).write_text(json.dumps(
            [r.as_dict() for r in reps], indent=1))
    return 0


if __name__ == "__main__":                        # pragma: no cover
    raise SystemExit(main())
