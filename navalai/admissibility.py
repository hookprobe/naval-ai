"""CFD-admissibility screen: is this grammar-valid hull one the MESHER can hold?

WHY THIS FILE EXISTS. `grammar.check()` decides "valid hull" from closed-form
naval-architecture constraints plus one developability metric, and
`evaluate()` adds "L1 physics returns a finite number". Neither asks the
question the Gate 2U campaign was failing on: can the STL ->
snappyHexMesh -> prism-layer pipeline represent this shape at the cell size
the pipeline picks? The motivating measurement was a seed-0 batch in which
**6 of 18 hulls meshed** against a >=95% bar, every one of them
`grammar.check()`-valid. That batch is HISTORY and is named as such below.

EVERY NUMBER IN THIS MODULE IS NOW ABOUT ONE NAMED POPULATION, AND THAT IS
THE 2026-08-20 CHANGE. `navalai.population` made a population quotable:
identity is `(arity, seed)`, not seed alone, because `sample_valid` draws
from `default_rng(seed)` and ADDING A GENE CHANGES THE DRAW SEQUENCE.
MEASURED there: the 15-gene and 16-gene banks both record `seed = 0` and
share **ZERO** hulls. So the two calibration eras are:

    HISTORY   `a15/s0/n74` and its prefixes — `gate2u-campaign-baseline.json`
              (18 labelled hulls, 6 meshed), `gate2u-campaign-backoff-mesh.json`
              (the ladder-rescue evidence), `gate2u-cap*-mesh.json`. This tree
              CANNOT regenerate them (`navalai.population` prints HISTORY for
              every one), so no rate from them is quotable as current. The
              15-gene confusion table — TP 6, FP 0, FN 6, TN 6; precision
              1.000, recall 0.500; Fisher exact one-sided p = 0.0498 — is
              recorded here as what it was and is NOT this module's result.
    CURRENT   `a16/s0/n25`, the DEVELOPMENT population (`population.DEV_SEED`),
              pinned in `data/populations/a16-s0-n25@*.json` and labelled by
              `CALIBRATION_BANK` below. `calibration_is_current()` compares the
              bank's `genome_sha256` against that manifest's, so a label can
              no longer be transferred to hulls it was not measured on — which
              is exactly how the 15-gene table came to be quoted against
              16-gene hulls in the first place.

WHAT THIS FILE DOES NOT CLAIM, MEASURED ON THE CURRENT POPULATION. It is a
SCREEN, and on `a16/s0/n25` at scale 1.0 it is not even that: it returns **no
DANGEROUS verdict at all**, and the one hull that is refused at rung 0 by the
metal it calls SAFE. The confusion table is pinned by
`test_the_screen_predicts_neither_rung_0_refusal_on_the_16_gene_population`
and the recall is pinned at ZERO on purpose — a later edit that quietly claims
more must fail a test rather than be believed. The metrics an external review
expected to predict mesh failure — the stem cusp and the x_mb tangent break —
measured AUC 0.500 and 0.500 on the 15-gene set, i.e. exactly chance, and are
kept as DIAGNOSTIC readings, reported and forbidden to vote, precisely so a
later session cannot mistake "we compute it" for "it predicts".

WHAT "DANGEROUS" ACTUALLY MEANS HERE, AND IT IS NARROWER THAN THE NAME. A
DANGEROUS verdict predicts *"this hull will be refused at the DERIVED layer
count"*, not *"this hull cannot be meshed"*. The original evidence was the
2026-08-11 back-off campaign (`data/gate2u-campaign-backoff-mesh.json`: hulls
0, 1, 5, 6 and 11 all meshed once the prism-layer ladder stepped down, 3 of 12
at rung 0 becoming 11 of 12 with the ladder) — HISTORY, 15-gene.

RE-MEASURED 2026-08-20 ON THIS TREE, because the 15-gene evidence was
label-void and the ledger's 16-gene corroboration predates the 161-station STL
rebuild. `data/gate2u-a16-s0-n25-backoff-mesh.json`, the same hulls as the
calibration bank's first twelve, `--layer-backoff 3`: **12 of 12 mesh**
against 11 of 12 at rung 0. The single rung-0 refusal, h011, goes derived
n=7 FATAL (26 wrongly-oriented faces, skew 11.30) -> rung 1, n=6 -> CLEAN (0
wrongly-oriented, 0 zero-volume, skew 2.980, 71.0% layer coverage) in TWO
attempts, on a BYTE-IDENTICAL STL (`stl_sha256` 973d90d8.. in both banks). So
the mesh outcome moved with the layer count and nothing else. Naming a rung-0
prediction "unmeshable" would be the same defect as a gate that reports the
requested spec under the label of the achieved result.

WHAT IT MEASURES ABOUT THE MANIFOLD. The distribution over a 200-hull draw is
measured by `test_the_manifold_the_grammar_emits_is_screened_and_mostly_
admissible`, which owns the numbers; they are not restated here.

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

RE-DERIVATION, 2026-08-18 (the meshability-math directive; full derivation and
calibration status in docs/MESHABILITY_MATH.md). Three changes, each measured:

1. `sheer_collapse_cells` IS RETIRED — it was a STALE SECOND COPY of the
   pre-P1 sheer law (`ys = yc + (zs - zc) * tan(flare)` with the UNENVELOPED
   flare). The rebuilt kernel envelopes the flare into the stem
   (`geometry._stations`) and REFUSES a negative sheer at L0 ("tumblehome
   closes the sheer past the centreline"), so the quantity this metric
   measured no longer describes any hull the kernel can deliver. MEASURED on
   the 16-gene seed-0 batch: it refused 5 of 25 hulls whose DELIVERED
   interior sheer half-breadth is 0.06..0.37 m — healthy decks, refused on a
   formula the kernel no longer contains (defect class 2, with the second
   copy voting). Its successor, `min_interior_sheer_halfwidth_cells`, is
   measured on the DELIVERED surface: a deck ridge narrower than a hull cell
   is a sub-cell feature, the same family as V3-V5 — and on the OLD kernel
   the three labelled catches (hulls 5, 11, 12) delivered a LITERAL
   zero-width ridge over a finite run, so the successor refuses every hull
   the retired bar was validated on, by construction.

2. VERDICTS GAINED A RESCUE AXIS (`Metric.ladder_rescuable`). DANGEROUS
   still means exactly what the paragraph above says — "expect a checkMesh
   refusal at the DERIVED layer count" — but the layer-backoff ladder is now
   CANONICAL in run-case.sh (metal-proven 2026-08-18: case a, derived n=6
   FATAL with 16 wrongly-oriented faces -> ladder -> n=5 CLEAN, unattended),
   so a rung-0 refusal has a measured deterministic recovery (~1.9 rungs
   mean). What has NO recovery is a feature the CELL cannot represent: no
   layer count changes the cell size. Each voting metric therefore declares
   whether the ladder can rescue it, `Report.refused_no_rescue` lists the
   ones it cannot, and the case writer refuses on THAT set (plus UNMEASURED,
   always fatal) instead of on all of DANGEROUS. Not a silent weakening: the
   split is the measured rescue record (backoff campaign 2026-08-11: every
   draft-bar refusal meshed on the ladder) plus cell arithmetic (sub-cell
   features are cell-scale, not layer-scale), stated per metric in code.

3. THE SOLVABILITY QUANTITY IS CARRIED AS A RECEIPT. MEASURED 2026-08-18
   (the Mac's paired dataset, docs/audit/STATUS.md): the local flow time
   scale tau = V_cell/(A_max*U) separates solved (7.8e-6..2.1e-5 s) from
   diverged (4.356e-18 s) by TWELVE orders while zero-volume/wrong-oriented/
   skewness are indistinguishable across the same rows. Enforcement lives
   where a mesh exists — run-case.sh aborts a solve whose min flow time
   scale falls below its 1e-12 s bar — and this screen reports the INTENDED
   minimum cell time scale (the smallest cell the derivation asks for, over
   the inlet speed) as a DIAGNOSTIC receipt, so a pathological
   (speed, scale) configuration is visible before any mesh. DIAGNOSTIC
   because it cannot separate hulls (it is a property of the case
   configuration, near-constant across the manifold), and a metric that
   cannot separate must not vote (the `derived_n_layers` precedent).
"""

from __future__ import annotations

import enum
import json as _json
import math
import pathlib as _pathlib
from dataclasses import dataclass

import numpy as np

from . import grammar
from .cfd.case import (_DOMAIN_LENGTH_L, _HULL_REFINE, _LAYER_EXPANSION,
                       _LAYER_MIN_THICKNESS_FRAC, _NX_BASE, _REFINE_ROUNDS,
                       _Z_BANDS, _refine_boxes, background_counts, layer_spec,
                       stl_resolution)
# `_stations` (not the `station_geometry` wrapper): the screen needs the
# design-waterline curve `y_wl` as well as the five edge curves, and calling
# `design_waterline` beside `station_geometry` would solve the same stations
# twice — while re-deriving y_wl here from K, yc, d and f would be a second
# copy of the waterline formula (defect class 2, the exact defect the retired
# `sheer_collapse_cells` died of).
from .geometry import Hull, _stations, station_geometry

#: THE GENOME THE SCREEN'S BARS WERE CALIBRATED AGAINST. Not a version number —
#: the parameter COUNT, because that is what makes a stored campaign vector
#: replayable or not.
#:
#: 15 -> 16 ON 2026-08-20, AND THE HISTORY MATTERS MORE THAN THE VALUE. Every
#: numeric bar below was originally set against `gate2u-campaign-baseline.json`
#: — 18 hulls of `a15/s0/n74`, speed 2.57, LTS, np=10, each with a measured
#: checkMesh outcome. The geometry-kernel rebuild took the genome to 16
#: parameters (`p_bow` and `p_stern` dropped, `Cp`, `lcb` and `roundness`
#: added), which VOIDED that calibration outright: a stored 15-gene vector
#: does not describe a hull the current `Hull` can build, and "hull 12" in
#: that file is not `sample_valid(..., seed=0)[12]` today. The LABELS were
#: what was lost.
#:
#: What closed the gap is not a re-tune, it is a RE-MEASUREMENT: the bars were
#: re-based on 2026-08-19 against the first 16-gene confusion table, and this
#: constant now names a campaign run on the CURRENT genome and the CURRENT
#: geometry kernel (`CALIBRATION_BANK`). Nothing was softened to make a test
#: pass — the one bar the 16-gene table refuted, `draft_over_hull_cell`, was
#: DEMOTED to a non-voting receipt rather than moved.
CALIBRATION_GENOME_N_PARAMS = 16

#: The DEVELOPMENT population the bars are calibrated on, by name. `seed = 0`
#: is development permanently (`population.DEV_SEED`): it is where the rules
#: were discovered and the bars were moved, and contamination is a one-way
#: door. Calibrating against `population.VAL_SEED` or `HOLDOUT_SEED` would
#: destroy the only two populations this project has that were never tuned on.
CALIBRATION_POPULATION_ID = "a16/s0/n25"

#: The LABELLED campaign: one `scripts/mesh_robustness.py` row per hull of
#: `CALIBRATION_POPULATION_ID`, with a measured checkMesh outcome. RUNG 0 —
#: `LAYER_BACKOFF=0`, the pipeline as it ships — which is the configuration a
#: DANGEROUS verdict is a prediction about.
CALIBRATION_BANK = (_pathlib.Path(__file__).resolve().parents[1] / "data"
                    / "gate2u-a16-s0-n25-mesh.json")

#: The SAME hulls with the layer-backoff ladder enabled. It is what bounds
#: the word "DANGEROUS" (module docstring), and it is a SEPARATE file rather
#: than a column because mixing two configurations into one bank is how a
#: rate stops meaning anything.
CALIBRATION_BACKOFF_BANK = (_pathlib.Path(__file__).resolve().parents[1]
                            / "data"
                            / "gate2u-a16-s0-n25-backoff-mesh.json")


def calibration_bank() -> dict | None:
    """The labelled campaign the bars are calibrated against, or None.

    None is returned for a missing or unparseable file and NEVER an empty
    dict: "I could not read the labels" must not be able to look like "the
    labels say nothing is wrong" (docs/LESSONS.md defect class 1).
    """
    try:
        return _json.loads(CALIBRATION_BANK.read_text())
    except (OSError, ValueError):
        return None


def calibration_is_current() -> bool:
    """Do the labelled campaign's labels belong to THIS tree's hulls?

    A probe, not a belief — the same discipline as `gates.Requirement`.

    STRENGTHENED 2026-08-20. It used to be `grammar.N_PARAMS == 15`, i.e. an
    ARITY comparison, and an arity comparison cannot see the defect it was
    written for: two populations of the same arity drawn either side of a box
    edge moving are different hulls carrying the same name. So the probe is
    now the GENOME HASH — the bank's `genome_sha256` against the pinned
    manifest's — which is the only statement that cannot be satisfied by two
    populations agreeing about their arity and disagreeing about their hulls.
    The arity check is kept as a necessary condition so the failure reads in
    the right order.

    Every clause is a REFUSAL on missing evidence: an unreadable bank, an
    absent manifest and a null hash all return False, because a screen whose
    labels cannot be located is not a calibrated screen.
    """
    if grammar.N_PARAMS != CALIBRATION_GENOME_N_PARAMS:
        return False
    bank = calibration_bank()
    if bank is None:
        return False
    if bank.get("genome_arity") != CALIBRATION_GENOME_N_PARAMS:
        return False
    banked = bank.get("genome_sha256")
    if not banked:
        return False
    from . import population as _population
    doc = None
    for _path, cand in _population.manifests():
        if cand.get("population_id") == CALIBRATION_POPULATION_ID:
            doc = cand
            break
    if doc is None or doc.get("genome_sha256") != banked:
        return False
    # A PARTIAL BANK IS NOT A CALIBRATION. `mesh_robustness.py` writes its
    # JSON after every hull so a thermal sleep cannot lose a campaign, so a
    # bank in hand may be seven rows of a twenty-five-hull population — and
    # its `population_id` then reads `a16/s0/n7`, a name for a set that was
    # never drawn as such. The labels are only this population's labels when
    # every hull of it carries one.
    want = int(str(CALIBRATION_POPULATION_ID).rsplit("/n", 1)[-1])
    hulls = {int(r["hull"]) for r in (bank.get("rows") or []) if "hull" in r}
    return hulls == set(range(want))


def calibration_labels() -> tuple[dict, tuple[int, ...], tuple[int, ...]]:
    """(bank, meshed hull ids, failed hull ids) for the calibration campaign.

    THE LABELS ARE READ, NEVER TRANSCRIBED. Until 2026-08-20 this file
    transcribed `MESHED = (2, 7, 9, 13, 15, 17)` into the test module, on the
    stated grounds that the campaign JSON was an untracked, still-growing
    artefact. It is now a committed, complete bank with a genome hash — and a
    transcription is a number declared twice (defect class 2) whose second
    copy cannot notice that the population under it moved. That is precisely
    what happened: the transcribed labels outlived the hulls they described by
    six days.

    Raises rather than returning stale labels if the bank is not this tree's.
    """
    if not calibration_is_current():
        raise RuntimeError(
            f"{CALIBRATION_BANK.name} does not label {CALIBRATION_POPULATION_ID}"
            f" as this tree draws it — refusing to hand back labels that would"
            f" be attached to hulls nobody measured.")
    bank = calibration_bank() or {}
    rows = bank.get("rows") or []
    meshed = tuple(int(r["hull"]) for r in rows if r.get("meshed"))
    failed = tuple(int(r["hull"]) for r in rows if not r.get("meshed"))
    return bank, meshed, failed


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
    #: Can the run-case.sh layer-backoff ladder rescue a hull this metric
    #: refuses? True for metrics whose mechanism moves with the LAYER COUNT
    #: (measured: the 2026-08-11 backoff campaign meshed every draft-bar
    #: refusal at a lower rung, and a smaller n shrinks the prism stack that
    #: `stack_over_min_radius` bounds). False for metrics whose mechanism is
    #: the CELL SIZE (a sub-cell feature is sub-cell at every layer count).
    #: The case writer refuses only the un-rescuable set — see
    #: `Report.refused_no_rescue` and the module docstring, item 2.
    ladder_rescuable: bool = True

    @property
    def votes(self) -> bool:
        return self.basis is not Basis.DIAGNOSTIC

    @classmethod
    def of(cls, name, value, unit, basis, note, *,
           danger_below=None, danger_above=None,
           margin_below=None, margin_above=None,
           ladder_rescuable=True) -> "Metric":
        """Classify `value` against the bars, refusing an unmeasurable one.

        AN UNMEASURABLE METRIC IS FATAL, NEVER A DEFAULT (docs/LESSONS.md
        defect class 1: `${_MQ_SKEW:-0}` scored a failure to measure as a
        perfect 0 against a bar of 20). A non-finite value here is UNMEASURED
        and UNMEASURED is worse than DANGEROUS, so it can never be the reason a
        hull is admitted.
        """
        if value is None or not math.isfinite(float(value)):
            return cls(name, float("nan"), unit, Verdict.UNMEASURED, basis,
                       f"NOT MEASURABLE: {note}", danger_below, danger_above,
                       ladder_rescuable)
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
                   danger_below, danger_above, ladder_rescuable)


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

    @property
    def refused_no_rescue(self) -> tuple[str, ...]:
        """The refusals the layer-backoff ladder CANNOT recover.

        This is the set the case writer refuses on (module docstring item 2):
        a metric that is DANGEROUS with `ladder_rescuable=False` names a
        feature the cell cannot represent at ANY layer count, and an
        UNMEASURED metric is fatal regardless — an unmeasurable quantity must
        never be the reason a hull is admitted (defect class 1). A hull whose
        refusals are all rescuable has a measured deterministic path: the
        run-case.sh ladder, ~1.9 rungs mean, metal-proven 2026-08-18.
        """
        return tuple(m.name for m in self.metrics if m.votes and (
            m.verdict is Verdict.UNMEASURED
            or (m.verdict is Verdict.DANGEROUS and not m.ladder_rescuable)))

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
            "refused_no_rescue": list(self.refused_no_rescue),
            "marginal_on": list(self.marginal_on),
            "metrics": {m.name: {"value": m.value, "unit": m.unit,
                                 "verdict": m.verdict.name,
                                 "basis": m.basis.value, "note": m.note,
                                 "ladder_rescuable": m.ladder_rescuable}
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

    UPDATED 2026-08-13 with plate P2: the vectorised branch below is the
    HARD-CHINE case, where the two panels are straight and linear
    interpolation IS the section. A radiused bilge is not linear in either
    panel, so the round-bilge branch used to loop the ONE sampler
    (`Hull._section_at_rows`) per station — measured ~90 ms against 7 ms at
    600x120, and later ~113 ms/hull (~140 ms/hull for the whole screen)
    against the 100 ms bar the four-orders claim is pinned by.

    UPDATED 2026-08-20: the round-bilge branch calls
    `Hull._sections_at_rows_batch` — the same sampler with the station axis
    vectorised, owned by `Hull` beside `_section_at_rows` so the two copies
    live one screen apart. The screen's bars were MEASURED through this grid,
    so the batch is fenced VALUE-PRESERVING against a loop over
    `_section_at_rows` at 1e-12 on both roundness branches, at this exact
    600x120 resolution among others
    (tests/test_admissibility.py::test_the_batch_section_sampler_is_the_loop).
    MEASURED after the switch: ~28 ms/hull here, ~48 ms/hull for the screen.
    """
    xs = np.linspace(float(hull.x[0]), float(hull.x[-1]), nx)
    jc = hull.chine_row(nz)
    if hull.roundness > 0.0:
        S = np.empty((len(xs), nz + 1, 3))
        S[:, :, 0] = xs[:, None]
        S[:, :, 1:] = hull._sections_at_rows_batch(xs, jc, nz - jc)
        return S
    xst = hull.x
    i = np.clip(np.searchsorted(xst, xs), 1, hull.n_stations - 1)
    f = (xs - xst[i - 1]) / (xst[i] - xst[i - 1])

    def lerp(a):
        return a[i - 1] * (1 - f) + a[i] * f

    zk, yc, zc = lerp(hull.z_keel), lerp(hull.y_chine), lerp(hull.z_chine)
    ys, zs = lerp(hull.y_sheer), lerp(hull.z_sheer)
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
    # The finest INTENDED cell dimensions of this case, for the flow-time-
    # scale receipt: the layer minThickness (snappy may squeeze a layer down
    # to this, and no further, by its own dict) and the free-surface cell
    # height after the z-only refineMesh rounds. Both are read from the
    # pipeline's constants, never restated (defect class 2).
    nz_hull_band = background_counts(scale, True)[3]
    fs_dz = (_Z_BANDS["hull"] * lwl / nz_hull_band
             / 2 ** 2 / 2 ** _REFINE_ROUNDS)
    return {"cell": cell, "stack": stack, "n_layers": spec["n_layers"],
            "first_layer_m": spec["first_layer_m"], "nx": nx, "nz": nz,
            "min_thickness_m": _LAYER_MIN_THICKNESS_FRAC * spec["first_layer_m"],
            "fs_dz_m": fs_dz,
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
    layer count `n_layers_to_bridge` derives, no back-off. Read a DANGEROUS as
    "expect a checkMesh refusal at the derived layer count", which is worth
    ~80 s of snappy per hull to know in ~50 ms, and NOT as "this hull is
    unmeshable": every rung-0 refusal measured on either genome meshed clean
    once the ladder stepped down (module docstring).

    AND READ A `SAFE` AS EVEN LESS THAN THAT. On the current calibration
    population this screen returns no DANGEROUS verdict at all and misses the
    one rung-0 refusal the metal found, so `SAFE` here means "no bar in this
    module fired", not "this hull will mesh".
    """
    h = hull if isinstance(hull, Hull) else Hull(np.asarray(hull, dtype=float))
    x = h.params
    p = grammar.named(x)
    lwl = float(h.x[-1])
    sc = _pipeline_scales(lwl, speed, scale)
    cell = sc["cell"]

    t = np.linspace(0.0, lwl, 4001)
    # ONE station solve for every curve the screen reads — the edge curves AND
    # the design waterline (`y_wl`), which the bilge-fillet radius needs. See
    # the import comment: a second solve or a re-derived y_wl would each be a
    # copy of something the kernel already owns.
    st = _stations(x, t)
    zk, yc, zc = st["z_keel"], st["y_chine"], st["z_chine"]
    ysh, zs = st["y_sheer"], st["z_sheer"]
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
    # BASIS FOLLOWS THE DEMOTION (2026-08-28, the CFD audit's P0-5). The
    # note below has said "DEMOTED TO A RECEIPT" since 2026-08-19, but the
    # basis stayed DERIVED — so `Metric.votes` was still True and only the
    # absent thresholds kept it silent. A future edit adding a
    # `danger_below=` would have re-armed a predictor measured 0-for-4.
    # `Basis.DIAGNOSTIC` is this module's own word for "reported, does not
    # vote", and every other retired metric already carries it.
    add(Metric.of("draft_over_hull_cell", draft / cell, "cells",
                  Basis.DIAGNOSTIC,
                  f"design draft in level-{_HULL_REFINE[1]} hull cells; below "
                  f"{sc['fs_band_m'] / cell:.3f} the keel is inside the "
                  f"tightest free-surface z-refinement box. DEMOTED TO A "
                  f"RECEIPT 2026-08-19 by the first 16-gene confusion table "
                  f"(data/gate2u-16gene-mesh.json): as a rung-0 predictor it "
                  f"went 0-for-4 — hulls 4/5/6/8 at 5.2..10.0 cells all "
                  f"meshed CLEAN at rung 0 with the ladder unused — while "
                  f"catching neither actual refusal. The 15-gene evidence "
                  f"('4 of 4 below it failed checkMesh') was label-void for "
                  f"transfer, and the transfer is now measured to fail. The "
                  f"value stays recorded; it votes on nothing.",
                  ladder_rescuable=True))

    # ---- V2 (re-derived): the DELIVERED deck narrower than the cell --------
    # `sheer_collapse_cells` WAS RETIRED HERE (module docstring, item 1). It
    # recomputed `ys = yc + (zs - zc) * tan(flare)` with the UNENVELOPED
    # flare — the pre-P1 kernel's formula — while the rebuilt kernel envelopes
    # the flare into the stem and REFUSES a negative sheer at L0
    # (`geometry._stations`: "tumblehome closes the sheer past the
    # centreline"). MEASURED on the 16-gene seed-0 batch: the stale formula
    # refused 5 of 25 hulls whose delivered interior sheer half-breadth is
    # 0.06..0.37 m. A metric measuring a formula the kernel no longer
    # contains is a second copy voting, and it is retired EXPLICITLY, not
    # softened.
    #
    # The successor measures the DELIVERED surface: the narrowest interior
    # deck half-width, in hull cells. A deck ridge narrower than one cell is
    # a sub-cell feature — the same inequality as V3-V5 (a feature thinner
    # than the cell cannot be represented by it), applied to the deck lid,
    # whose degenerate quads `closed_mesh` drops by area. On the OLD kernel
    # the three labelled catches (hulls 5, 11, 12) delivered a LITERAL
    # zero-width ridge over a finite run of x, i.e. 0.0 cells < 1.0, so this
    # bar refuses every hull its predecessor was validated on. MEASURED on
    # the 16-gene seed-0 batch: exactly one hull below 1.0 (hull 18, 0.35
    # cells — the same sliver hull the bottom-panel bar refuses), and no
    # phantom refusals. NOT ladder-rescuable: cell arithmetic, not layers.
    add(Metric.of("min_interior_sheer_halfwidth_cells",
                  float(ysh[interior].min()) / cell, "cells", Basis.DERIVED,
                  "narrowest DELIVERED deck half-width (sheer half-breadth) "
                  "forward of the transom and aft of the stem run-out, in "
                  "hull cells. Successor of the retired sheer_collapse_cells "
                  "(a stale pre-P1 second copy of the sheer law): a deck "
                  "ridge narrower than a cell is a sub-cell feature. The "
                  "retired bar's three labelled catches delivered literal "
                  "zero-width ridges, so they are refused here too. DANGER "
                  "EDGE RE-BASED 1.0 -> 0.1 cells (2026-08-19, the 16-gene "
                  "confusion table): hull 18 at 0.35 cells meshed CLEAN at "
                  "rung 0, so the 1-cell edge refused a measured-good hull; "
                  "the labelled-fatal anchors sit at literal 0.0. 0.1 is "
                  "2.6x under the measured-clean floor (0.26) and still "
                  "refuses every true ridge; [0.1, 1.0) is the warn band "
                  "pending the solve rows.",
                  danger_below=0.1, margin_below=1.0,
                  ladder_rescuable=False))

    # ---- V3-V5: features thinner than the cell that must resolve them -----
    # A surface feature narrower than one cell cannot be represented by that
    # cell, whatever snappy does with it. The bar is 1.0 cell and it is DERIVED
    # (it IS the cell). None of these fire on campaign hulls 0-17 — the whole
    # labelled batch sits above them — so they carry NO validation from the
    # confusion matrix, and saying so is the point of this comment. They fire
    # on 0.5%, 0.0%, 0.5% and 0.0% of a 200-hull manifold respectively, and
    # campaign hull 20 trips the first and third at 0.998 cells each, which is
    # a PRE-REGISTERED prediction (docs/BUILD-PLAN.md §11.6).
    # NONE is ladder-rescuable: the mechanism is cell size, which no layer
    # count moves — these are the refusals the case writer enforces.
    add(Metric.of("min_bottom_panel_width_cells",
                  float(yc[interior].min()) / cell, "cells", Basis.DERIVED,
                  "narrowest bottom panel (chine half-breadth) forward of the "
                  "stem run-out, in hull cells. A panel thinner than a cell "
                  "cannot be resolved by it. DANGER EDGE RE-BASED 1.0 -> 0.1 "
                  "cells with the deck-ridge family (2026-08-19 confusion "
                  "table: hull 18 at 0.26 cells and hull 22 at 0.57 meshed "
                  "CLEAN at rung 0; labelled-fatal anchors at 0.0); "
                  "[0.1, 1.0) warns pending the solve rows.",
                  danger_below=0.1, margin_below=1.0,
                  ladder_rescuable=False))
    add(Metric.of("min_topside_panel_height_cells",
                  float((zs - zc)[interior].min()) / cell, "cells",
                  Basis.DERIVED,
                  "shortest topside panel (sheer minus chine) in hull cells. "
                  "Unexercised by campaign hulls 0-17 (minimum 19.4) AND by "
                  "the 200-hull manifold (minimum 12.2). It has never fired.",
                  danger_below=1.0, margin_below=2.0,
                  ladder_rescuable=False))
    add(Metric.of("transom_half_beam_cells", float(yc[0]) / cell, "cells",
                  Basis.DERIVED,
                  "transom half-breadth in hull cells: the transom cap is a "
                  "flat patch and a sub-cell patch is a sub-cell feature. "
                  "DANGER EDGE RE-BASED 1.0 -> 0.1 cells (2026-08-19: hull "
                  "22 at 0.57 cells meshed CLEAN at rung 0); [0.1, 1.0) "
                  "warns pending the solve rows. The topside and "
                  "transom-immersion siblings stay at 1.0: they have never "
                  "fired and carry NO measurement in either direction — a "
                  "family-uniformity move would be interpolation by analogy.",
                  danger_below=0.1, margin_below=1.0,
                  ladder_rescuable=False))
    add(Metric.of("transom_immersion_cells", float(-zk[0]) / cell, "cells",
                  Basis.DERIVED,
                  "immersed transom depth in hull cells. Unexercised by "
                  "campaign hulls 0-17 (minimum 6.16) AND by the 200-hull "
                  "manifold (minimum 3.33). It has never fired.",
                  danger_below=1.0, margin_below=2.0,
                  ladder_rescuable=False))

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
                  "as the radius it bends around and the layer normals cross. "
                  "LADDER-RESCUABLE: the stack height falls with the layer "
                  "count (floor 3 gives a 3.6*t1 stack against 12.9*t1 at "
                  "n=7), so the ladder walks this ratio back under 1.",
                  danger_above=1.0, margin_above=0.5,
                  ladder_rescuable=True))

    # ---- The bilge-fillet radius, in cells — the 16th gene's OWN failure
    # mode, DIAGNOSTIC until a round-bilge hull is meshed. `roundness` made a
    # radiused bilge expressible on 2026-08-13 and NO round-bilge hull has
    # ever been through snappy (the only 16-gene metal case, case a, is a
    # hard chine; every labelled campaign is 15-gene). The closed form, from
    # the fillet's own Bezier (see `geometry._fillet_coeffs`): with
    # a = rho*(C-K), b = rho*(W-C), the arc's curvature is
    # k(s) = |a x b| / (2*|(1-s)a + s b|^3) (the numerator is constant — the
    # cross terms cancel), so r_min = 2*d_min^3/|a x b| with d_min the
    # closest approach of segment a->b to the origin. r_min is LINEAR in
    # roundness, so the gene walks the surface continuously from a crease
    # (r = 0) to a fully resolvable round.
    #
    # THE PRE-REGISTERED WINDOW, stated before any label exists: trouble is
    # predicted where the STL RESOLVES the fillet as smooth but the CELL
    # cannot — stl_row < r_min < cell (r below the STL's own girth-row
    # spacing renders as a crease and behaves as the hard chine the pipeline
    # already meshes; r above the cell is resolvable curvature). MEASURED on
    # the 16-gene seed-0 batch that window holds 2-3 of 25 hulls; 0 < r <
    # cell alone holds ~half the batch, which is why an unvalidated bar here
    # would refuse half the manifold on zero labels — the V6-first-draft
    # defect. It votes when the 16-gene campaign labels it; the window is
    # the prediction to score.
    stl_arc = (float(np.mean(np.hypot(yc, zc - zk)))
               + float(np.mean(np.hypot(ysh - yc, zs - zc)))) / sc["nz"]
    K2 = np.stack([np.zeros_like(t), zk], 1)
    C2 = np.stack([yc, zc], 1)
    W2 = np.stack([st["y_wl"], np.zeros_like(t)], 1)
    rho = float(p["roundness"])
    if rho > 0.0:
        fa = rho * (C2 - K2)
        fb = rho * (W2 - C2)
        fcross = np.abs(fa[:, 0] * fb[:, 1] - fa[:, 1] * fb[:, 0])
        fd = fb - fa
        fdd = np.maximum(np.sum(fd * fd, axis=1), 1e-30)
        fs_par = np.clip(-np.sum(fa * fd, axis=1) / fdd, 0.0, 1.0)
        dmin = np.linalg.norm(fa + fs_par[:, None] * fd, axis=1)
        with np.errstate(divide="ignore"):
            r_arc = np.where(fcross > 1e-30,
                             2.0 * dmin ** 3 / np.maximum(fcross, 1e-30),
                             np.inf)
        wmask = interior & (yc > 0.10 * float(yc.max()))
        r_min = float(r_arc[wmask].min()) if wmask.any() else float("inf")
    else:
        r_min = float("inf")                      # a hard chine has no fillet
    _bilge_note = (
        f"minimum bilge-fillet radius in hull cells (inf = hard chine, no "
        f"fillet). Closed form off the fillet Bezier; linear in the "
        f"roundness gene. Pre-registered trouble window: STL girth row "
        f"{stl_arc:.4f} m < r < cell {cell:.4f} m — smooth to the STL, "
        f"sub-cell to the mesher. NO round-bilge hull has a measured mesh "
        f"outcome yet, so this reports and does not vote (the doctrine that "
        f"keeps an unvalidated bar from refusing half the manifold).")
    if math.isfinite(r_min):
        add(Metric.of("bilge_min_radius_cells", r_min / cell, "cells",
                      Basis.DIAGNOSTIC, _bilge_note))
    else:
        # A hard chine has NO fillet: infinity here is the honest reading,
        # not a failure to measure — `Metric.of` would misfile inf as
        # UNMEASURED, so the metric is built directly. DIAGNOSTIC never
        # votes, so the verdict field is inert either way.
        add(Metric("bilge_min_radius_cells", float("inf"), "cells",
                   Verdict.SAFE, Basis.DIAGNOSTIC, _bilge_note))

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
                  "first cell. AUC vs mesh failure on the 15-gene labelled "
                  "batch (`a15/s0/n74`, HISTORY): 0.500, chance. Not "
                  "re-measurable on `a16/s0/n25` — one labelled failure "
                  "cannot carry an AUC. Reported, does not vote."))
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
                  "sheer. AUC vs mesh failure on the 15-gene labelled batch "
                  "(`a15/s0/n74`, HISTORY): 0.500, chance. Reported, does "
                  "not vote."))

    S = surface_grid(h, sc["nx"], sc["nz"])
    N, ok = _quad_normals(S)
    good = ok[:-1] & ok[1:]
    dih = np.where(good, _angle_deg(N[:-1], N[1:]), np.nan)
    add(Metric.of("max_facet_turn_deg", float(np.nanmax(dih)), "deg",
                  Basis.DIAGNOSTIC,
                  "largest normal change between longitudinally adjacent STL "
                  "quads. Dominated by the 41-station crease pattern, not by "
                  "the hull's shape: on the 15-gene labelled batch "
                  "(`a15/s0/n74`, HISTORY) failures spanned 24.7..40.9 deg "
                  "and successes 24.9..42.2, AUC 0.673. Does not vote."))
    add(Metric.of("stack_over_hull_cell", sc["stack"] / cell, "-",
                  Basis.DIAGNOSTIC,
                  "prism-stack height in hull cells. docs/LESSONS.md records a "
                  "build-time cap on this ratio being DRAFTED AND KILLED by "
                  "its own data (Wigley solves at 1.084, KCS dies at 0.952). "
                  "AUC 0.621 on the 15-gene labelled batch (`a15/s0/n74`, "
                  "HISTORY). Does not vote, for that reason."))
    add(Metric.of("derived_n_layers", float(sc["n_layers"]), "layers",
                  Basis.DIAGNOSTIC,
                  "prism-layer count `n_layers_to_bridge` derives for this "
                  "hull. It is 8-10 for essentially every hull the grammar "
                  "emits, so it cannot separate them — but it is the lever the "
                  "back-off campaign moved: on 15-gene hulls 0-4 "
                  "(`a15/s0/n74`, HISTORY) rung 0 meshed 1 of 5 and the "
                  "ladder meshed 4 of 5, and on 16-gene hulls h011/h012 the "
                  "ladder's FIRST rung cleared both (Gate 2U ledger, BLOCK "
                  "1, 2026-08-20). Does not vote."))
    # The INTENDED minimum cell flow time scale of this case: the smallest
    # cell dimension the derivation asks for (the layer minThickness snappy
    # may squeeze to, or the post-refine free-surface cell height, whichever
    # is smaller) over the inlet speed. tau = V/(A_max*U) ~ h_min/U for the
    # thinnest intended cell. MEASURED anchors (the Mac's paired dataset,
    # 2026-08-18): solved runs bottom out at 7.8e-6..2.1e-5 s; the one
    # measured divergence sits at 4.356e-18 s; run-case.sh aborts a live
    # solve below its 1e-12 s bar. This receipt is the PRE-MESH end of that
    # chain: a healthy configuration intends ~1e-4 s, eight orders above the
    # abort bar, and the gap is the margin ACCIDENTAL cells (folded layers,
    # bad snaps) must consume before a solve can die — which is why the
    # geometric feature bars above exist. Near-constant across the manifold
    # (it is a property of speed and scale, not of the hull), so it cannot
    # separate hulls and does not vote.
    add(Metric.of("intended_min_cell_flow_time_scale_s",
                  min(sc["min_thickness_m"], sc["fs_dz_m"]) / max(speed, 1e-9),
                  "s", Basis.DIAGNOSTIC,
                  "smallest INTENDED cell dimension (layer minThickness vs "
                  "post-refine free-surface dz) over the inlet speed — the "
                  "design value of the quantity run-case.sh aborts on at "
                  "1e-12 s (solved floor 7.8e-6 s, measured divergence "
                  "4.356e-18 s). Reports the configuration's own margin; "
                  "does not vote."))
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
        # RE-DRAWING FROM `seed` ALONE IS THE DEFECT THIS TOOL EXISTS TO
        # REPORT ON (`navalai.population`, 2026-08-20): the 15-gene and
        # 16-gene banks both record `seed = 0` and share ZERO hulls, so
        # scoring a bank by re-sampling its seed silently attaches its labels
        # to whatever the current box draws. If the bank carries a content
        # hash, it is CHECKED; if it does not, that is said out loud rather
        # than assumed benign.
        from . import population as _population
        banked = rec.get("genome_sha256")
        if banked:
            got = _population.genome_sha256(X[:rec.get("n", len(X))])
            if got != banked:
                print(f"REFUSING {args.campaign}: it records genome_sha256 "
                      f"{banked} and this tree draws {got} from seed "
                      f"{rec['seed']}. These are not the same hulls; the "
                      f"labels cannot be transferred.")
                return 2
        else:
            print(f"WARNING: {args.campaign} carries no genome_sha256 (it "
                  f"predates navalai.population). Its rows are being scored "
                  f"against a re-draw from seed {rec['seed']}, which is only "
                  f"the same population if the grammar box has not moved "
                  f"since. UNVERIFIED.")
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
