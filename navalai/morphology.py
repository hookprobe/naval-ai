"""Hull MORPHOLOGY: what a hull LOOKS like, measured — not what it weighs.

WHY THIS MODULE EXISTS. On 2026-08-23 this repository generated, validated and
certified a 16 m liveaboard whose hydrostatics, stability, freeboard, scantlings
and all eight constraint rows passed, and which was — visibly, in the STL — a
rectangular plank. It was found by a human opening the file, not by any gate.
Four successive hulls were delivered before anyone rendered one.

The failure is architectural and it is stated once here:

    A NUMERICALLY VALID OBJECT IS NOT NECESSARILY A VALID BOAT HULL.

`evaluate` answers "is this legal and does it float". Nothing answered "does
this look like a boat". Cp, Cb, LCB, GM and displacement are NECESSARY
engineering properties and they are NOT SUFFICIENT MORPHOLOGICAL DESCRIPTORS:
a plank and a fine displacement hull can share every one of them.

WHAT THIS MODULE IS, AND WHAT IT IS NOT. It is a deterministic descriptor set
plus a critic with bands MEASURED on the real-hull corpus. It contains no
learning, no network and no latent space, deliberately: the corpus on disk is
51 Delft yachts, one Series 60, one Wigley, five Fridsma planing models and one
container ship — effectively ONE morphological family. A model trained on that
would learn Delft yachts badly. Ship-D's own lesson points the same way: 30,000
parametric hulls still contain a great many shapes no naval architect would
recognise, so more random geometry is not the answer. The missing layer is a
VALIDATED realistic-hull manifold, and this module is its first, honest,
hand-measurable version.

THE COMMON REPRESENTATION IS AN OFFSETS TABLE, not a `Hull`. A descriptor that
only a generated hull can have cannot be calibrated against a published one,
and calibrating against published hulls is the entire point. So everything here
consumes `HullOffsets`, and `from_hull` is a thin adapter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class HullOffsets:
    """The common currency: half-breadths on a station x waterline grid.

    x        (nx,)      station positions, 0 at the transom, increasing forward
    z        (nz,)      waterline heights, increasing upward, 0 = design WL
    y        (nx, nz)   half-breadth; NaN where the waterline is below the keel
    z_keel   (nx,)      keel height at each station
    z_sheer  (nx,)      sheer height at each station
    """

    x: np.ndarray
    z: np.ndarray
    y: np.ndarray
    z_keel: np.ndarray
    z_sheer: np.ndarray
    label: str = ""
    n_gaps: int = 0            # stations whose keel/sheer had to be interpolated
    # THE CHINE, WHEN THE SOURCE KNOWS IT. Deadrise is the angle of the BOTTOM
    # panel — keel point to chine — and it CANNOT be recovered by sampling a
    # station in z: a flat bottom is horizontal, so it occupies a single
    # waterline and the rows above it describe the topside. MEASURED before
    # this field existed: `deadrise_mid_deg` tracked the `beta_mid` gene
    # exactly over 5-25 deg and returned **80 deg for a flat bottom (0 deg)**,
    # reading the flare instead. A search then "optimised" deadrise to 65 deg
    # on a hull whose bottom gene was 0.0. NaN where the source cannot say.
    y_chine: np.ndarray | None = None
    z_chine: np.ndarray | None = None

    @property
    def lwl(self) -> float:
        return float(self.x[-1] - self.x[0])

    @property
    def half_beam_max(self) -> float:
        return float(np.nanmax(self.y))

    def beam_at_station(self) -> np.ndarray:
        """Maximum half-breadth at each station, over all waterlines.

        A STATION WITH NO OFFSETS AT ALL IS A GAP, NOT A ZERO-BEAM STATION.
        MEASURED on dsyhs_49: 3 of 41 stations are blank in the published
        extraction, and reading them as beam = 0 put a false pinch in the plan
        that made `plan_waist` report 0.98 on a perfectly fair Delft yacht --
        a pathology detector firing on its own teacher. Empty stations are
        interpolated from their neighbours and never counted as narrow.
        """
        with np.errstate(invalid="ignore"):
            filled = np.where(np.isnan(self.y), -np.inf, self.y)
            b = np.max(filled, axis=1)
        gap = ~np.isfinite(b)
        if gap.any() and (~gap).sum() >= 2:
            b[gap] = np.interp(self.x[gap], self.x[~gap], b[~gap])
        return np.where(np.isfinite(b), b, 0.0)

    def section_area(self) -> np.ndarray:
        """Immersed sectional area at each station, up to z = 0."""
        out = np.zeros(len(self.x))
        below = self.z <= 0.0
        if below.sum() < 2:
            return out
        zz = self.z[below]
        for i in range(len(self.x)):
            yy = self.y[i, below]
            good = ~np.isnan(yy)
            if good.sum() >= 2:
                out[i] = 2.0 * np.trapezoid(yy[good], zz[good])
        return out


def from_hull(hull, nz: int = 41) -> HullOffsets:
    """Adapter: a generated `geometry.Hull` -> the common offsets table.

    THE ADAPTER AND THE LOADER MUST PRODUCE THE SAME KIND OF OBJECT, or every
    band measured on published hulls is meaningless when applied to generated
    ones. A first version interpolated each station from its THREE moulded
    points (keel, chine, sheer) onto a global z grid. That is not what
    `load_offsets_csv` reads: a published table gives the real half-breadth at
    every waterline, following the actual section curve including the bilge
    fillet. MEASURED with the 3-point version: the reference hull scored
    waterline_convexity 0.341 against a corpus p5 of 0.840 and was REJECTED as
    wavy — while the 58 published hulls all passed. The hull was fine; the
    representation was coarse, and the steps it introduced read as curvature
    reversals.

    So the section is sampled from the kernel's own section curve, which is the
    same surface the STL is built from.
    """
    x = np.asarray(hull.x, float)
    zk = np.asarray(hull.z_keel, float)
    zs = np.asarray(hull.z_sheer, float)
    z = np.linspace(float(zk.min()), float(zs.max()), nz)
    y = np.full((len(x), nz), np.nan)
    for i in range(len(x)):
        try:
            pts = np.asarray(hull.section(i), float)      # (n, 2) as (y, z)
            if pts.ndim != 2 or pts.shape[0] < 3:
                raise ValueError
            py, pz = pts[:, 0], pts[:, 1]
        except Exception:                                  # noqa: BLE001
            py = np.array([0.0, float(hull.y_chine[i]), float(hull.y_sheer[i])])
            pz = np.array([zk[i], float(hull.z_chine[i]), zs[i]])
        o = np.argsort(pz)
        pz, py = pz[o], py[o]
        inside = (z >= pz[0]) & (z <= pz[-1])
        y[i, inside] = np.interp(z[inside], pz, py)
    return HullOffsets(x=x, z=z, y=y, z_keel=zk, z_sheer=zs,
                       label=getattr(hull, "label", ""),
                       y_chine=np.asarray(hull.y_chine, float),
                       z_chine=np.asarray(hull.z_chine, float))


# ---------------------------------------------------------------------------
# The descriptors. Every one is dimensionless or normalised by a hull
# dimension, because the corpus spans 5 m yachts to a 230 m container ship and
# a band measured in metres would be meaningless across it.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Descriptors:
    # -- longitudinal ------------------------------------------------------
    sac_peak_x: float           # station of max sectional area, fraction of LWL
    sac_centroid_x: float       # SAC centroid, fraction of LWL (LCB proxy)
    entrance_frac: float        # length fwd of the SAC peak, fraction of LWL
    run_frac: float             # length aft of the SAC peak, fraction of LWL
    pmb_frac: float             # fraction of LWL within 2% of peak area
    sac_transom: float          # sectional area at the transom / max
    sac_stem: float             # sectional area at the stem / max
    bow_taper: float            # d(area)/d(x) over the forward quarter, normalised
    stern_taper: float          # same over the after quarter
    sac_smoothness: float       # RMS 2nd difference of the SAC, normalised
    # -- plan / beam -------------------------------------------------------
    beam_peak_x: float          # station of max beam, fraction of LWL
    beam_carried: float         # fraction of LWL at >= 90% of max beam
    beam_transom: float         # beam at transom / max beam
    beam_stem: float            # beam at stem / max beam
    waterline_convexity: float  # fraction of the plan that is convex
    plan_waist: float           # deepest dip below a monotone rise to max beam
    # -- transverse --------------------------------------------------------
    midship_fullness: float     # midship area / (beam x draft)
    section_fullness_mean: float
    deadrise_mid_deg: float
    deadrise_bow_deg: float
    deadrise_range_deg: float
    bottom_flatness: float      # fraction of the bottom within 5 deg of flat
    # -- profile -----------------------------------------------------------
    depth_variation: float      # (max - min) hull depth / max depth
    sheer_rise_frac: float      # sheer rise / max depth
    rocker_frac: float          # keel rise aft / draft
    forefoot_frac: float        # keel rise forward / draft
    # -- global ------------------------------------------------------------
    l_over_b: float
    b_over_t: float
    d_over_t: float
    cp: float
    cb: float
    cm: float

    def as_dict(self) -> dict:
        return {k: float(getattr(self, k)) for k in self.__dataclass_fields__}


def _span_frac(arr: np.ndarray, denom: float) -> float:
    """(max - min) / denom, or NaN when the quantity was never measured.

    A descriptor that cannot be computed must say so. Returning 0.0 would make
    an absent sheer line indistinguishable from a hull that genuinely has none.
    """
    a = np.asarray(arr, float)
    if not np.isfinite(a).any() or not math.isfinite(denom) or denom <= 0.0:
        return float("nan")
    span = float(np.nanmax(a) - np.nanmin(a))
    return float("nan") if span < 1e-9 else span / denom


def _safe(a: float, b: float, default: float = 0.0) -> float:
    return float(a / b) if b not in (0.0, None) and math.isfinite(b) else default


def describe(o: HullOffsets) -> Descriptors:
    """Every descriptor, from an offsets table alone."""
    x, L = o.x, o.lwl
    xf = (x - x[0]) / L if L else x * 0.0
    A = o.section_area()
    Amax = float(A.max()) if A.size and A.max() > 0 else 1.0
    a = A / Amax
    B = o.beam_at_station()
    B = np.where(np.isfinite(B), B, 0.0)
    Bmax = float(B.max()) if B.size and B.max() > 0 else 1.0
    b = B / Bmax

    # -- longitudinal
    ipk = int(np.argmax(A))
    sac_peak_x = float(xf[ipk])
    tot = float(np.trapezoid(a, xf)) or 1.0
    sac_centroid_x = float(np.trapezoid(a * xf, xf) / tot)
    pmb = float(np.mean(a >= 0.98))
    d1 = np.gradient(a, xf)
    q = max(2, len(a) // 4)
    bow_taper = float(-np.mean(d1[-q:]))
    stern_taper = float(np.mean(d1[:q]))
    d2 = np.gradient(d1, xf)
    sac_smoothness = float(np.sqrt(np.mean(d2 ** 2)))

    # -- plan
    ibk = int(np.argmax(B))
    beam_peak_x = float(xf[ibk])
    beam_carried = float(np.mean(b >= 0.90))
    # THE WAIST IS NON-MONOTONICITY, NOT TAPER. A first version took the
    # running max from the BOW end, which on any normally-tapered hull returns
    # 1 - b(transom) and reported the reference hull as 61% waisted. What a
    # waist actually is: the plan RISES, then FALLS BACK, before reaching
    # maximum beam -- a pinch between a wide transom and a wide midbody, which
    # is what made the 2026-08-23 houseboat look wrong. So: running max from
    # the TRANSOM end, minus the current value.
    fwd = b[: ibk + 1]
    plan_waist = (float(np.max(np.maximum.accumulate(fwd) - fwd))
                  if fwd.size else 0.0)
    cur = np.gradient(np.gradient(b, xf), xf)
    waterline_convexity = float(np.mean(cur <= 1e-9))

    # -- transverse
    T = float(max(1e-9, -o.z_keel.min()))
    depth = o.z_sheer - o.z_keel
    Dmax = float(depth.max()) if depth.size else 1.0
    mid = ipk
    midship_fullness = _safe(A[mid], 2.0 * B[mid] * T, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        sf = A / np.maximum(2.0 * B * T, 1e-9)
    section_fullness_mean = float(np.nanmean(np.where(np.isfinite(sf), sf, np.nan)))

    # DEADRISE IS THE ANGLE OF THE BOTTOM PANEL: keel point to chine.
    dead = np.full(len(x), np.nan)
    if o.y_chine is not None and o.z_chine is not None:
        yc = np.asarray(o.y_chine, float)
        zc = np.asarray(o.z_chine, float)
        rise = zc - np.asarray(o.z_keel, float)
        with np.errstate(invalid="ignore", divide="ignore"):
            dead = np.degrees(np.arctan2(rise, np.where(yc > 1e-9, yc, np.nan)))
    else:
        # No chine declared (a published offsets table gives none). Fall back to
        # the lowest waterlines and ACCEPT the limitation: on a flat-bottomed
        # section this reads the topside, so it is refused rather than reported
        # when the keel row is already near full width.
        for i in range(len(x)):
            col = o.y[i]
            good = np.where(~np.isnan(col))[0]
            if good.size < 3:
                continue
            j0, j1 = good[0], good[min(good.size - 1, 2)]
            lower = col[good[: max(3, good.size // 2)]]
            widest = float(np.nanmax(lower)) if lower.size else 0.0
            if widest > 1e-9 and col[j0] / widest > 0.90:
                continue          # flat bottom: not resolvable from a z-grid
            dy = col[j1] - col[j0]
            dz = o.z[j1] - o.z[j0]
            if dy > 1e-9:
                dead[i] = math.degrees(math.atan2(dz, dy))
    dmid = float(np.nanmedian(dead[len(dead) // 3: 2 * len(dead) // 3]))
    dbow = float(np.nanmedian(dead[-max(2, len(dead) // 6):]))
    drange = float(np.nanmax(dead) - np.nanmin(dead)) if np.isfinite(dead).any() else 0.0
    bottom_flatness = float(np.nanmean(np.abs(dead) <= 5.0))

    return Descriptors(
        sac_peak_x=sac_peak_x, sac_centroid_x=sac_centroid_x,
        entrance_frac=float(1.0 - sac_peak_x), run_frac=sac_peak_x,
        pmb_frac=pmb, sac_transom=float(a[0]), sac_stem=float(a[-1]),
        bow_taper=bow_taper, stern_taper=stern_taper,
        sac_smoothness=sac_smoothness,
        beam_peak_x=beam_peak_x, beam_carried=beam_carried,
        beam_transom=float(b[0]), beam_stem=float(b[-1]),
        waterline_convexity=waterline_convexity, plan_waist=plan_waist,
        midship_fullness=midship_fullness,
        section_fullness_mean=section_fullness_mean,
        deadrise_mid_deg=dmid, deadrise_bow_deg=dbow,
        deadrise_range_deg=drange, bottom_flatness=bottom_flatness,
        # NaN, NOT ZERO, WHEN THERE IS NO SHEER TO MEASURE. MEASURED: Series 60
        # and Wigley offsets are published to a CONSTANT level -- they carry no
        # sheer line at all -- so a literal reading gave depth_variation = 0.000
        # and the PLANK detector fired on two of its own teachers. An
        # unmeasurable quantity is refused, never scored as the worst case.
        # NaN, NOT ZERO, WHEN THERE IS NO SHEER TO MEASURE. MEASURED: Series 60
        # publishes offsets to a CONSTANT level and Wigley carries no sheer
        # column AT ALL (every value NaN), so a literal reading returned
        # depth_variation = 0.000 and the PLANK detector fired on two of its
        # own teachers. Worse, it arrived via `_safe`, which returns its
        # DEFAULT when the denominator is not finite -- turning "I could not
        # measure this" into "this is the worst case", the same failure class
        # as a mesh receipt defaulting to zero.
        depth_variation=_span_frac(depth, Dmax),
        sheer_rise_frac=_span_frac(o.z_sheer, Dmax),
        rocker_frac=_safe(float(o.z_keel[0] - o.z_keel.min()), T),
        forefoot_frac=_safe(float(o.z_keel[-1] - o.z_keel.min()), T),
        l_over_b=_safe(L, 2.0 * Bmax), b_over_t=_safe(2.0 * Bmax, T),
        d_over_t=_safe(Dmax, T),
        cp=_safe(float(np.trapezoid(A, x)), Amax * L),
        cb=_safe(float(np.trapezoid(A, x)), 2.0 * Bmax * T * L),
        cm=midship_fullness,
    )


def load_offsets_csv(path) -> HullOffsets:
    """Read an E5 `source_offsets.csv` — a PUBLISHED hull — into the common form.

    This is the function that makes the corpus usable as a teacher: a descriptor
    only a generated hull can have is a descriptor nothing can calibrate.

    TWO THINGS THIS HAS TO GET RIGHT, both found by reading the files rather
    than assuming:

    1. THE DATUM. Published offsets measure z from the MOULDED BASELINE, and
       the header records the design waterline separately ("Design waterline
       z = 0.473 m"). The descriptors expect the DWL at z = 0, so the datum is
       parsed from the header and subtracted. Getting this wrong does not
       raise — it silently reports every immersed quantity against the wrong
       plane, which is the shape of defect this project keeps finding.
    2. GAPS. MEASURED on dsyhs_49: 3 of 41 stations carry the literal string
       "nan" for keel and sheer. They are interior stations, so they are
       interpolated across and the count is recorded on the result rather than
       being silently absorbed.
    """
    import csv
    import re
    from pathlib import Path as _P

    path = _P(path)
    text = path.read_text()
    dwl = 0.0
    m = re.search(r"[Dd]esign waterline\s*z\s*=\s*([0-9.]+)", text)
    if m:
        dwl = float(m.group(1))
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    rows = list(csv.DictReader(lines))
    if not rows:
        raise ValueError(f"{path}: no data rows")

    wl_cols = sorted(((k, float(k[3:])) for k in rows[0] if k.startswith("wl_")),
                     key=lambda t: t[1])
    z = np.array([v for _k, v in wl_cols], float) - dwl
    x = np.array([float(r["x_m"]) for r in rows], float)

    def _col(name: str) -> np.ndarray:
        vals = []
        for r in rows:
            s_ = (r.get(name) or "").strip()
            try:
                vals.append(float(s_))
            except ValueError:
                vals.append(float("nan"))
        return np.array(vals, float)

    zk, zs = _col("z_keel_m") - dwl, _col("z_sheer_m") - dwl
    n_gaps = int(np.isnan(zk).sum())
    for arr in (zk, zs):                       # interpolate interior gaps
        bad = np.isnan(arr)
        if bad.any() and (~bad).sum() >= 2:
            arr[bad] = np.interp(x[bad], x[~bad], arr[~bad])

    y = np.full((len(rows), len(z)), np.nan)
    for i_, r in enumerate(rows):
        for j, (k, _v) in enumerate(wl_cols):
            s_ = (r.get(k) or "").strip()
            if s_:
                try:
                    y[i_, j] = float(s_)
                except ValueError:
                    pass
    return HullOffsets(x=x, z=z, y=y, z_keel=zk, z_sheer=zs,
                       label=f"{path.parent.name}", n_gaps=n_gaps)


# ---------------------------------------------------------------------------
# THE CRITIC. Deterministic, no learning, bands MEASURED on the positive corpus
# (`data/morphology_corpus.json`, 58 published hulls). It answers the question
# no gate in this repository asked: does this look like a boat?
#
# It runs BEFORE any expensive validation, and every rejection names the
# descriptor and BOTH numbers -- the one measured and the one required -- so a
# refusal teaches instead of merely blocking.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    pathology: str
    descriptor: str
    measured: float
    bar: float
    detail: str

    def __str__(self) -> str:
        return (f"[{self.pathology}] {self.descriptor} = {self.measured:.3f} "
                f"(bar {self.bar:.3f}) — {self.detail}")


@dataclass(frozen=True)
class Critique:
    ok: bool
    score: float                      # 0 = pathological, 1 = fully plausible
    findings: tuple[Finding, ...] = ()

    @property
    def pathologies(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(f.pathology for f in self.findings))


# Bands from the 58-hull positive corpus. p5/p95 unless a tighter statement is
# justified in the comment. These are MEASUREMENTS, not preferences; widen them
# only by re-running scripts/build_morphology_corpus.py on more real hulls.
_CORPUS_N = 58
_BAR = {
    # Real hulls do not have a waist: p5 AND p95 are both exactly 0.000 across
    # all 58. A plan that rises, falls back, then rises again to maximum beam
    # is a shape nobody draws. This is the sharpest discriminator in the set.
    "plan_waist_max": 0.02,
    # Convexity p5 = 0.840. Below that the waterline is wandering.
    "waterline_convexity_min": 0.80,
    # Depth variation p5 = 0.100. A hull whose depth never changes is a PLANK;
    # the 2026-08-23 houseboat measured here.
    "depth_variation_min": 0.06,
    # Beam carried p5 = 0.317. Below that the hull is mostly taper: a SPEARHEAD.
    "beam_carried_min": 0.20,
    # Parallel middle body p95 = 0.827 (Fridsma prismatic models are genuinely
    # near-constant). Above 0.90 with abrupt ends is a BOX, not a hull.
    "pmb_frac_max": 0.90,
    # L/B p5 2.39, p95 5.00; the grammar's own band is (2.2, 8.5). Take the
    # union rather than the corpus alone -- a 10:1 rowing shell is a real hull
    # that this corpus simply does not contain.
    "l_over_b": (1.9, 10.5),
}


# A DEMIHULL IS NOT A MONOHULL, AND JUDGING IT AS ONE IS A FALSE POSITIVE.
#
# MEASURED 2026-08-23 on 300 generated plywood catamaran demi-hulls: 55 of them
# were rejected as PROPORTION failures purely because L/B ran past 10.5 — a
# ceiling measured on a corpus of 58 MONOHULLS. Slenderness is the whole point
# of a demihull: a solar-electric catamaran has almost no power, so wave-making
# has to be starved by L/B, and `grammar.L_OVER_B_BAND_DEMIHULL` already says
# (2.2, 15.1). The critic was condemning the correct answer.
#
# This is the smallest honest version of family-specific validation: only the
# bands that are KNOWN to differ are overridden, and the rest stay shared. A
# family whose band nobody has measured gets the general one, not an invented
# one.
_FAMILY_BAR: dict[str, dict] = {
    "demihull": {"l_over_b": (2.2, 15.5)},
    "catamaran": {"l_over_b": (2.2, 15.5)},
    "pontoon": {"l_over_b": (2.2, 15.5), "pmb_frac_max": 0.98},
}


def critique(d: Descriptors, family: str | None = None) -> Critique:
    """Judge a hull's SHAPE. Engineering validity is somebody else's job.

    `family` selects the bands that are known to differ for that hull type; an
    unknown or absent family uses the general (monohull-calibrated) set.
    """
    bar = dict(_BAR)
    bar.update(_FAMILY_BAR.get((family or "").lower(), {}))
    f: list[Finding] = []

    if d.plan_waist > bar["plan_waist_max"]:
        f.append(Finding(
            "WAIST", "plan_waist", d.plan_waist, bar["plan_waist_max"],
            "the plan rises, falls back, then rises again before maximum beam; "
            f"all {_CORPUS_N} published hulls measure exactly 0.000"))

    if d.waterline_convexity < bar["waterline_convexity_min"]:
        f.append(Finding(
            "WAVY-PLAN", "waterline_convexity", d.waterline_convexity,
            bar["waterline_convexity_min"],
            "the waterline is not convex over enough of its length"))

    if math.isfinite(d.depth_variation) and \
            d.depth_variation < bar["depth_variation_min"]:
        f.append(Finding(
            "PLANK", "depth_variation", d.depth_variation,
            bar["depth_variation_min"],
            "hull depth is essentially constant end to end — a slab, not a hull"))

    if d.beam_carried < bar["beam_carried_min"]:
        f.append(Finding(
            "SPEARHEAD", "beam_carried", d.beam_carried,
            bar["beam_carried_min"],
            "too little of the waterline carries beam; the hull is mostly taper"))

    if d.pmb_frac > bar["pmb_frac_max"] and min(d.sac_transom, d.sac_stem) > 0.6:
        f.append(Finding(
            "BOX", "pmb_frac", d.pmb_frac, bar["pmb_frac_max"],
            "near-constant sectional area terminating abruptly at both ends"))

    lo, hi = bar["l_over_b"]
    if not (lo <= d.l_over_b <= hi):
        f.append(Finding(
            "PROPORTION", "l_over_b", d.l_over_b, lo if d.l_over_b < lo else hi,
            "length-to-beam outside anything in the corpus or the grammar band"))

    # A PYRAMID tapers in several dimensions at once: little beam carried AND
    # little depth variation AND a vanishing stem. Any one of those alone is a
    # legitimate hull; all three together is a wedge.
    if (d.beam_carried < 0.30 and d.depth_variation < 0.12
            and d.sac_stem < 0.02 and d.sac_transom < 0.10):
        f.append(Finding(
            "PYRAMID", "beam_carried", d.beam_carried, 0.30,
            "monotonic taper in beam, depth and area at once — a wedge"))

    score = max(0.0, 1.0 - 0.25 * len(f))
    return Critique(ok=not f, score=score, findings=tuple(f))


def from_mesh(mesh, n_stations: int = 41, nz: int = 41,
              axis: int = 0, up: int = 2, label: str = "") -> HullOffsets:
    """Any watertight triangle mesh -> the common offsets table.

    THE THIRD DOOR INTO THE SAME REPRESENTATION. `from_hull` admits this
    project's own generator and `load_offsets_csv` admits a published table;
    this admits geometry from anywhere else — a CadQuery loft, an IGES import,
    a downloaded STL — so that external hulls can be described and judged by
    exactly the same descriptors the bands were measured on.

    `axis` is the LONGITUDINAL index and `up` the VERTICAL index of the mesh's
    coordinate frame; the remaining index is taken as half-breadth. They are
    parameters rather than assumptions because every source disagrees: this
    kernel is (x fwd, y stbd, z up), while a CadQuery loft extruded along its
    workplane normal arrives as (beam, depth, length).
    """
    import numpy as _np

    v = _np.asarray(mesh.vertices, float)
    side = ({0, 1, 2} - {axis, up}).pop()
    xs, zs, ys = v[:, axis], v[:, up], v[:, side]

    x = _np.linspace(float(xs.min()), float(xs.max()), n_stations)
    z = _np.linspace(float(zs.min()), float(zs.max()), nz)
    y = _np.full((n_stations, nz), _np.nan)
    zk = _np.full(n_stations, _np.nan)
    zsh = _np.full(n_stations, _np.nan)

    # Bin the surface points by station, then by height, and take the widest
    # half-breadth in each cell. A binned read of a closed surface is enough for
    # DESCRIPTORS (which are all normalised aggregates) and avoids depending on
    # a section/plane intersection that fails on degenerate slivers -- and the
    # bow of a developable hull is deliberately a sliver.
    dx = (x[-1] - x[0]) / max(1, n_stations - 1)
    dz = (z[-1] - z[0]) / max(1, nz - 1)
    si = _np.clip(((xs - x[0]) / dx).round().astype(int), 0, n_stations - 1)
    zi = _np.clip(((zs - z[0]) / dz).round().astype(int), 0, nz - 1)
    ay = _np.abs(ys)
    for k in range(len(v)):
        i, j = si[k], zi[k]
        if _np.isnan(y[i, j]) or ay[k] > y[i, j]:
            y[i, j] = ay[k]
    for i in range(n_stations):
        col = _np.where(~_np.isnan(y[i]))[0]
        if col.size:
            zk[i], zsh[i] = z[col[0]], z[col[-1]]
    good = ~_np.isnan(zk)
    if good.sum() >= 2:
        zk[~good] = _np.interp(x[~good], x[good], zk[good])
        zsh[~good] = _np.interp(x[~good], x[good], zsh[good])
    return HullOffsets(x=x, z=z, y=y, z_keel=zk, z_sheer=zsh, label=label)
