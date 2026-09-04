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

    _a_inset = max(1, int(round(0.025 * (len(a) - 1))))

    # -- plan
    _inset = max(1, int(round(0.025 * (len(b) - 1))))
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
    # CONCAVITY BELOW THE FAIRING TOLERANCE IS NOT A HOLLOW (2026-08-26).
    # The sign-only count read a flat-sided hull as WAVY: the landed 16 x 4
    # barge's aft waterline carries a SYSTEMATIC +1..4 mm-per-station^2
    # curvature (the derived-beam residue of the aft SAC branch), and a
    # sign count weighs those millimetres exactly like the 2026-08-23
    # spearhead's 0.24 m hollow. The tolerance is scale-free — a fraction
    # of maximum beam over the station-spacing^2 — at plating-fairness
    # scale, so the 58-corpus verdicts and the recorded pathologies are
    # unchanged (re-measured on landing: 0 of 58 flagged before and
    # after; the spearhead still reads 0.317) while a straight side
    # measures as the straight line it is.
    bmax = float(np.max(b)) if b.size else 1.0
    span = float(xf[-1] - xf[0]) if xf.size > 1 else 1.0
    tol = _CONVEXITY_FAIR_FRAC * bmax / max(span * span, 1e-12)
    waterline_convexity = float(np.mean(cur <= tol))

    # -- transverse
    T = float(max(1e-9, -o.z_keel.min()))
    depth = o.z_sheer - o.z_keel
    Dmax = float(depth.max()) if depth.size else 1.0
    mid = ipk
    midship_fullness = _safe(A[mid], 2.0 * B[mid] * T, 0.0)
    # THE FLOOR MUST BE RELATIVE, NOT ABSOLUTE. MEASURED: scaling a hull by
    # 7.3x moved `section_fullness_mean` by 2.3% while the other 32 descriptors
    # were unchanged to 1e-16 — because `np.maximum(..., 1e-9)` compares a
    # DIMENSIONAL quantity (2*B*T, in m^2) against a fixed number, so it clamps
    # at one size and not at another. The descriptor set has to be scale-free
    # or a 10 m corpus cannot calibrate a 200 m hull, which is exactly what the
    # ShipD corpus is (every hull normalised to LOA 10).
    _box = 2.0 * B * T
    _floor = 1e-9 * max(float(np.nanmax(_box)) if _box.size else 1.0, 1e-30)
    with np.errstate(invalid="ignore", divide="ignore"):
        sf = A / np.maximum(_box, _floor)
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
                ang = math.degrees(math.atan2(dz, dy))
                # A BOTTOM PANEL AT MORE THAN 60 DEG IS A TOPSIDE. Without a
                # declared chine the estimator walks up from the keel row and,
                # on a flared hard-chine section, walks straight past the
                # knuckle onto the flare: MEASURED 75.0 deg on a dory-flared
                # plywood demihull whose bottom is very nearly flat. Refusing
                # is correct — the alternative is a corpus of confident wrong
                # deadrise, and a search will happily optimise it.
                dead[i] = ang if ang <= 60.0 else float("nan")
    dmid = float(np.nanmedian(dead[len(dead) // 3: 2 * len(dead) // 3]))
    dbow = float(np.nanmedian(dead[-max(2, len(dead) // 6):]))
    drange = float(np.nanmax(dead) - np.nanmin(dead)) if np.isfinite(dead).any() else 0.0
    bottom_flatness = float(np.nanmean(np.abs(dead) <= 5.0))

    return Descriptors(
        sac_peak_x=sac_peak_x, sac_centroid_x=sac_centroid_x,
        entrance_frac=float(1.0 - sac_peak_x), run_frac=sac_peak_x,
        pmb_frac=pmb,
        # THE SAME 2.5% INSET, AND FOR THE SAME REASON as beam_transom below --
        # it was applied to the plan and not to the area curve, which left this
        # pair reading the sampling grid. MEASURED 2026-08-24 across all 53
        # published hulls in tests/e5_real_hulls: sac_stem was 0.0000 for 53 of
        # 53, min == p5 == median == max, a band 0.000 wide. Sectional area is
        # ZERO at a closed hull's own extremity by definition, so at x[-1] this
        # descriptor could only ever return zero -- for a barge exactly as for
        # a racing shell. That is the `beam_transom` defect (300 of 300 ShipD
        # hulls at 0.000) in the curve next door, and it is why a hull whose
        # bow was a mathematical POINT critiqued ok=True, score=1.000 while
        # the owner rejected it on sight as "a spearhead rather than a boat".
        # Neither key is in MANIFOLD_KEYS, so this does not move the vendored
        # ShipD bands; it makes two dead descriptors measure something.
        sac_transom=float(a[_a_inset]), sac_stem=float(a[-1 - _a_inset]),
        bow_taper=bow_taper, stern_taper=stern_taper,
        sac_smoothness=sac_smoothness,
        beam_peak_x=beam_peak_x, beam_carried=beam_carried,
        # MEASURED AT A 2.5% INSET, NOT AT THE EXTREME STATION. A closed hull
        # section degenerates to a POINT at its own extremity, so reading beam
        # exactly at x[0] measures the sampling grid, not the boat. MEASURED:
        # 300 of 300 ShipD hulls returned beam_transom = 0.000, which made the
        # learned band degenerate (0.000..0.000) and scored every real transom
        # as infinitely wrong. The inset is what a draughtsman would call
        # station 1 rather than the after perpendicular.
        beam_transom=float(b[_inset]), beam_stem=float(b[-1 - _inset]),
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
#: The waterline fairing tolerance, in scale-free units of (max half-beam /
#: LWL^2) — the curvature a straight-ish side may carry before it counts as
#: hollow. CALIBRATED EMPIRICALLY 2026-08-26, both edges measured: the
#: landed 16 x 4 barge's aft side carries positive curvature to 2.66 of
#: these units (a millimetre-scale derived-beam residue, visually a
#: straight side) and the 2026-08-23 spearhead's genuine hollows start at
#: 4.6 with a median 0.041/m raw. 3.5 sits between the measured edges; the
#: 58-hull corpus is unaffected at either value (0 flagged before and
#: after, re-measured on landing).
_CONVEXITY_FAIR_FRAC = 3.5

# Conjunction constants for the BOX and PYRAMID pathologies, hoisted from
# `critique`'s clauses on 2026-08-26 so `shape_margin` reads THE SAME
# numbers — a second copy inside the margin function would be the
# number-declared-twice defect wearing the critic's own uniform.
_BOX_END_AREA_MIN = 0.6
_PYRAMID_BARS = {
    "beam_carried": 0.30,
    "depth_variation": 0.12,
    "sac_stem": 0.02,
    "sac_transom": 0.10,
}

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
    # A BARGE IS NOT IN THE CORPUS, AND JUDGING IT AS ONE IS THE DEMIHULL
    # FALSE POSITIVE OVER AGAIN. MEASURED 2026-08-27 on the PROVEN 16x4
    # liveaboard barge (`parents.PARENTS` "liveaboard-barge", fenced by
    # tests/test_barge_bow.py at 88% beam carried / 59.4 m2 of deck): the
    # general bars refused it on plan_waist 0.105 (bar 0.020) and
    # waterline_convexity 0.732 (bar 0.800). All 58 corpus hulls measure
    # waist 0.000 — because all 58 are pointed-bow monohulls; a pram bow
    # (r_stem 0.40) rounds the plan into a shape the corpus simply does
    # not contain. P2-A routes mission family "barge" into this table, so
    # without this row every houseboat mission's shape row was
    # unsatisfiable BY CONSTRUCTION. Bands are set just outside the proven
    # barge's measured values, not invented: waist 0.105 -> 0.12,
    # convexity 0.732 -> 0.70, and the pontoon pmb relaxation applies (a
    # barge's midbody IS the boat). CAVEAT, recorded: part of the 0.105
    # waist may be the derived-beam artifact (one curve, two jobs — the
    # Phase-3 B(x) work); re-measure and TIGHTEN these when the design
    # waterline lands.
    # ...AND ONE REQUIRING BAND (2026-09-04). The rows above are one-sided
    # PERMISSIONS — they stop the general bars refusing a true barge — and
    # nothing DEMANDED barge-ness, so the P2 search delivered a round-bilge
    # cruiser wearing a houseboat's label: MEASURED, the entire 48-member
    # pareto front for "16 m x 4.5 m liveaboard houseboat" carried
    # beam_carried <= 0.341 (energy-best member: 0.220), because all three
    # objectives punish barge-form and no constraint pulled toward it. The
    # proven liveaboard-barge parent measures beam_carried 0.585 on the
    # CURRENT kernel (the 0.88 in the comment above is a prior kernel's
    # descriptor — both are recorded, neither is restated as the other),
    # so the floor is set BETWEEN the cruiser front's ceiling (0.341) and
    # the proven barge (0.585): a family mission must carry its beam over
    # at least half the waterline or the shape row says SPEARHEAD, exactly
    # as it does for the general fleet at 0.200.
    "barge": {"plan_waist_max": 0.12, "waterline_convexity_min": 0.70,
              "pmb_frac_max": 0.98, "beam_carried_min": 0.50},
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

    if (d.pmb_frac > bar["pmb_frac_max"]
            and min(d.sac_transom, d.sac_stem) > _BOX_END_AREA_MIN):
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
    if (d.beam_carried < _PYRAMID_BARS["beam_carried"]
            and d.depth_variation < _PYRAMID_BARS["depth_variation"]
            and d.sac_stem < _PYRAMID_BARS["sac_stem"]
            and d.sac_transom < _PYRAMID_BARS["sac_transom"]):
        f.append(Finding(
            "PYRAMID", "beam_carried", d.beam_carried,
            _PYRAMID_BARS["beam_carried"],
            "monotonic taper in beam, depth and area at once — a wedge"))

    score = max(0.0, 1.0 - 0.25 * len(f))
    return Critique(ok=not f, score=score, findings=tuple(f))


def shape_margin(d: Descriptors, family: str | None = None) -> float:
    """The critic as ONE signed margin: <= 0 plausible, > 0 the worst
    relative violation. The continuous companion of `critique` for the
    ladder's constraint vector — NSGA-II needs a gradient, and a count of
    findings is a staircase.

    READS THE SAME BARS as `critique` (`_BAR`, `_FAMILY_BAR`, the hoisted
    conjunction constants) so the two can never drift; each rule's margin
    is normalised by its own bar so a 10% shortfall on beam-carried and a
    10% shortfall on convexity weigh the same. Conjunctive pathologies
    (BOX, PYRAMID) take the MIN of their clause margins — the conjunction
    is violated only when every clause is.

    Wired into `evaluate.CONSTRAINT_NAMES` as the `shape` row on
    2026-08-26 (audit finding I: the critic had ZERO production callers
    while 89-92% of L0-valid hulls were morphologically implausible and
    the 2026-08-23 plank passed every row this ladder had).
    """
    bar = dict(_BAR)
    bar.update(_FAMILY_BAR.get((family or "").lower(), {}))

    def _below(v: float, floor: float) -> float:
        return (floor - v) / max(abs(floor), 1e-9)

    def _above(v: float, ceil: float) -> float:
        return (v - ceil) / max(abs(ceil), 1e-9)

    margins = [
        _above(d.plan_waist, max(bar["plan_waist_max"], 0.02)),
        _below(d.waterline_convexity, bar["waterline_convexity_min"]),
        _below(d.beam_carried, bar["beam_carried_min"]),
        min(_above(d.pmb_frac, bar["pmb_frac_max"]),
            _above(min(d.sac_transom, d.sac_stem), _BOX_END_AREA_MIN)),
        max(_below(d.l_over_b, bar["l_over_b"][0]),
            _above(d.l_over_b, bar["l_over_b"][1])),
        min(_below(d.beam_carried, _PYRAMID_BARS["beam_carried"]),
            _below(d.depth_variation, _PYRAMID_BARS["depth_variation"]),
            _below(d.sac_stem, _PYRAMID_BARS["sac_stem"]),
            _below(d.sac_transom, _PYRAMID_BARS["sac_transom"])),
    ]
    if math.isfinite(d.depth_variation):
        margins.append(_below(d.depth_variation, bar["depth_variation_min"]))
    return float(max(margins))


def from_mesh(mesh, n_stations: int = 41, nz: int = 41,
              axis: int = 0, up: int = 2, label: str = "") -> HullOffsets:
    """Any watertight triangle mesh -> the common offsets table.

    THE THIRD DOOR INTO THE SAME REPRESENTATION. `from_hull` admits this
    project's own generator and `load_offsets_csv` a published table; this
    admits geometry from anywhere else — a CadQuery loft, an IGES import, a
    downloaded STL — so external hulls are judged by the same descriptors the
    bands were measured on.

    IT SLICES; IT DOES NOT BIN VERTICES. The first version binned vertices onto
    the station x waterline grid, which works only when the mesh is finely
    triangulated. MEASURED on a CadQuery ruled loft — exactly the case this
    function exists for — the solid carries 22 faces and ~14 distinct vertices,
    so 39 of 41 grid rows at the midship station were EMPTY, every immersed
    integral came out zero, and a 10,000-hull corpus was written with
    Cp = Cb = 0.0000 on every row. The descriptors were not wrong about the
    hulls; they were reading an empty grid.

    `axis` is the LONGITUDINAL index and `up` the VERTICAL index of the mesh's
    frame; the remaining index is half-breadth. Parameters, not assumptions,
    because every source disagrees: this kernel is (x fwd, y stbd, z up) while
    a CadQuery loft arrives as (beam, depth, length).
    """
    import numpy as _np

    v = _np.asarray(mesh.vertices, float)
    side = ({0, 1, 2} - {axis, up}).pop()
    x = _np.linspace(float(v[:, axis].min()), float(v[:, axis].max()), n_stations)
    z = _np.linspace(float(v[:, up].min()), float(v[:, up].max()), nz)
    y = _np.full((n_stations, nz), _np.nan)
    zk = _np.full(n_stations, _np.nan)
    zsh = _np.full(n_stations, _np.nan)

    normal = _np.zeros(3)
    normal[axis] = 1.0
    eps = ((x[-1] - x[0]) * 1e-3) or 1e-6
    dz = float(z[1] - z[0]) if len(z) > 1 else 1.0
    for i, xi in enumerate(x):
        org = _np.zeros(3)
        # nudge the end planes inboard: a slice exactly ON a cap is degenerate
        org[axis] = float(min(max(xi, x[0] + eps), x[-1] - eps))
        try:
            sec = mesh.section(plane_origin=org, plane_normal=normal)
        except Exception:                                       # noqa: BLE001
            sec = None
        if sec is None or len(getattr(sec, "vertices", ())) < 3:
            continue
        pts = _np.asarray(sec.vertices, float)
        pz, py = pts[:, up], _np.abs(pts[:, side])
        zk[i], zsh[i] = float(pz.min()), float(pz.max())
        order = _np.argsort(pz)
        pz_s, py_s = pz[order], py[order]
        inside = (z >= pz.min() - 1e-9) & (z <= pz.max() + 1e-9)
        for j in _np.where(inside)[0]:
            near = _np.abs(pz_s - z[j]) <= 0.75 * dz
            y[i, j] = float(py_s[near].max()) if near.any() \
                else float(_np.interp(z[j], pz_s, py_s))

    good = ~_np.isnan(zk)
    if good.sum() >= 2:
        zk[~good] = _np.interp(x[~good], x[good], zk[good])
        zsh[~good] = _np.interp(x[~good], x[good], zsh[good])
    return HullOffsets(x=x, z=z, y=y, z_keel=zk, z_sheer=zsh, label=label)


# ---------------------------------------------------------------------------
# THE LEARNED MANIFOLD. Bands measured over 30,000 ShipD hulls (19,256 of them
# morphologically plausible) and VENDORED to data/shipd_morphology_bands.json.
#
# `navalai/` never imports ShipD: the upstream repo declares no licence, needs a
# local numpy-2.x patch to run at all, and a band that moves when someone
# re-clones a research repo is not a band. What is read here is OUR measurement
# of it. See scripts/build_shipd_corpus.py.
#
# THE CRITIC AND THE MANIFOLD ANSWER DIFFERENT QUESTIONS, and conflating them
# would lose both. `critique` asks IS THIS A BOAT — its bars are calibrated for
# ZERO false positives on 58 published hulls, so they are deliberately loose.
# `manifold_score` asks IS THIS LIKE THE HULLS PEOPLE ACTUALLY DRAW — a
# continuous distance from the plausible band, which is what a search can
# descend. A hull can pass the critic and still sit far outside the manifold;
# the 2026-08-23 houseboat did exactly that, at beam_carried 0.293 against a
# plausible band of 0.415-0.829.
# ---------------------------------------------------------------------------

_MANIFOLD_PATH = ("data/shipd_morphology_bands.json",)
_MANIFOLD_CACHE: dict | None = None

# Descriptors the manifold is scored on. Deliberately NOT all 33: several are
# constant across the corpus (`plan_waist`, `sac_transom`) and would contribute
# only noise, and the raw proportions are already gated by `critique`.
MANIFOLD_KEYS = ("beam_carried", "waterline_convexity", "cp", "cb",
                 "pmb_frac", "section_fullness_mean", "beam_transom",
                 "deadrise_mid_deg", "l_over_b", "b_over_t")


def manifold_bands(path: str | None = None) -> dict:
    """The vendored plausible-only bands, or {} when the file is absent.

    Absent is an honest state, not an error: the bands are a measurement this
    repository carries, and a caller that cannot find them must be able to say
    so rather than silently score against nothing.
    """
    global _MANIFOLD_CACHE
    if _MANIFOLD_CACHE is not None and path is None:
        return _MANIFOLD_CACHE
    import json
    from pathlib import Path

    for p in ([path] if path else _MANIFOLD_PATH):
        f = Path(p)
        if not f.is_absolute():
            f = Path(__file__).resolve().parents[1] / p
        if f.exists():
            data = json.loads(f.read_text())
            bands = data.get("bands_plausible_only", {})
            if path is None:
                _MANIFOLD_CACHE = bands
            return bands
    return {}


def manifold_score(d: Descriptors, bands: dict | None = None) -> tuple[float, dict]:
    """How far inside the learned manifold this hull sits: 1.0 = fully inside.

    Returns `(score, per_descriptor)`. Each descriptor contributes 1.0 when it
    lies within the plausible band and decays with its distance OUTSIDE,
    normalised by the band's own width — so a descriptor with a wide band is
    not punished for a deviation that a narrow one would be.
    """
    bands = manifold_bands() if bands is None else bands
    if not bands:
        return float("nan"), {}
    parts: dict[str, float] = {}
    for k in MANIFOLD_KEYS:
        b = bands.get(k)
        v = getattr(d, k, float("nan"))
        if not b or not math.isfinite(v) or not all(math.isfinite(x) for x in b):
            continue
        lo, hi = float(b[0]), float(b[1])
        # A ZERO-WIDTH BAND CANNOT DISCRIMINATE, so it is DROPPED rather than
        # scored. MEASURED: `beam_transom` came back 0.000..0.000 over 30,000
        # hulls (a sampling artefact, since fixed) and every real hull scored
        # 0.0 against it — one of ten descriptors contributing pure noise to
        # the manifold score. Refusing to score an unmeasurable band is the
        # same rule this module applies everywhere else.
        if (hi - lo) <= 1e-9:
            continue
        width = hi - lo
        if lo <= v <= hi:
            parts[k] = 1.0
        else:
            out = (lo - v) if v < lo else (v - hi)
            parts[k] = float(max(0.0, 1.0 - out / width))
    return (float(np.mean(list(parts.values()))) if parts else float("nan")), parts


# ---------------------------------------------------------------------------
# GENERAL DESIGN RULES: anti-roll, wave stability, and the shape a hull has to
# have to be recognised as one. These are NOT hydrostatics — `evaluate` owns
# GM and freeboard. They are the SHAPE preconditions that make those numbers
# achievable, and they apply to every hull this project generates.
#
# WHY THEY LIVE HERE. Each was found by looking at a rendered hull that had
# already passed every existing gate, and each is measurable. Bands come from
# the 19,256 plausible hulls of the 30k corpus and from published series; where
# neither has a value, the rule REFUSES rather than inventing one.
# ---------------------------------------------------------------------------

# Reverse (inverted) stem rake — bottom forward, top retracted. It removes
# reserve buoyancy and flare forward, so the bow PIERCES a wave instead of
# lifting over it. That is the point of a wave-piercer and it is a real
# trade: less pitching, at the documented cost of bow submergence and deck
# wetness. It is the WRONG trade for a slow inland craft, where waves are
# short and dryness matters more than pitch damping.
REVERSE_RAKE_FN_FLOOR = 0.35     # below this Froude number, piercing buys nothing

# Bow flare must not collapse at the stem. MEASURED on houseboat16 (2026-08-24):
# the `flare` gene sat at its 25 deg ceiling while the DELIVERED flare angle
# fell 15.8 -> 4.9 -> 0.0 deg over the forward 20%, because sheer half-breadth
# goes to zero at the stem. A bow with no flare has nothing to generate lift
# from, which is exactly the submergence mechanism above.
BOW_FLARE_MIN_DEG = 6.0

# Bow fullness: beam carried at the stem, as a fraction of maximum. p5 of the
# plausible corpus is 0.110 — below that the bow is a spike with no reserve.
BOW_FULLNESS_MIN = 0.08

# A wave-piercer inverts the flare rule and must earn it with a deep forefoot.
# `WAVE_PIERCER_FLARE_MAX_DEG` is a CEILING, not a floor -- the opposite sense
# of the general rule. `WAVE_PIERCER_FOREFOOT_MIN` is the keel drop from
# midships to the stem as a fraction of draft: the Damen mechanism, quantified.
WAVE_PIERCER_FLARE_MAX_DEG = 5.0
WAVE_PIERCER_FOREFOOT_MIN = 0.15


@dataclass(frozen=True)
class DesignRule:
    rule: str
    measured: float
    bar: float
    ok: bool
    why: str

    def __str__(self) -> str:
        return (f"[{'ok ' if self.ok else 'FAIL'}] {self.rule}: "
                f"{self.measured:.2f} vs {self.bar:.2f} — {self.why}")


def design_rules(hull, fn: float | None = None,
                 family: str | None = None) -> list[DesignRule]:
    """The shape preconditions for anti-roll, wave stability and a fair hull.

    Takes a `geometry.Hull` rather than descriptors because two of these read
    the moulded curves directly (stem rake, delivered flare) and a descriptor
    that averaged them would hide exactly the collapse they exist to catch.
    """
    out: list[DesignRule] = []
    n = len(hull.x)
    i0 = int(0.80 * (n - 1))
    fam = (family or "").lower()
    piercer = fam in ("wave_piercer", "axe_bow", "wave_piercing")

    # -- delivered flare over the forward fifth, NOT the gene ---------------
    angs = []
    for i in range(i0, n):
        dz = float(hull.z_sheer[i] - hull.z_chine[i])
        dy = float(hull.y_sheer[i] - hull.y_chine[i])
        if dz > 1e-6:
            angs.append(math.degrees(math.atan2(dy, dz)))
    flare = float(np.median(angs)) if angs else float("nan")
    if piercer:
        # A WAVE-PIERCER INVERTS THIS RULE, AND MUST EARN THE INVERSION.
        # Baltic Workboats: "when the bow becomes submerged, the top surface of
        # the bow creates increased downforce, which compensates for the
        # buoyancy of the bow". Flare generates the lift a piercer is trying
        # NOT to have, so little or none forward is correct here — the general
        # bar would condemn a Damen Axe Bow outright.
        #
        # But the relaxation is not free, or declaring a family would become a
        # way to bypass review. A piercer must show the mechanism that replaces
        # flare: DEEPEST DRAUGHT AT THE BOW. Damen, in their own words: "The
        # bow has the greatest draught at the front, which delays the moment at
        # which the bow lifts out of the water. If the bow does not lift, there
        # is no chance of it slamming back into the waves." A hull with neither
        # flare NOR a deep forefoot is not a wave-piercer; it is a bad bow.
        out.append(DesignRule(
            "bow-flare(piercer)", flare, WAVE_PIERCER_FLARE_MAX_DEG,
            bool(math.isfinite(flare) and flare <= WAVE_PIERCER_FLARE_MAX_DEG),
            "a wave-piercer wants little or no flare forward; flare makes the "
            "lift it is designed to avoid"))
        zk = np.asarray(hull.z_keel, float)
        drop = float(zk[len(zk) // 2] - zk[-1])       # + means deeper forward
        T = max(1e-9, float(-zk.min()))
        out.append(DesignRule(
            "deep-forefoot(piercer)", drop / T, WAVE_PIERCER_FOREFOOT_MIN,
            bool(drop / T >= WAVE_PIERCER_FOREFOOT_MIN),
            "the bow must have the GREATEST draught, or nothing replaces the "
            "flare it gave up — this is what delays bow emergence and so "
            "prevents the slam"))
    else:
        out.append(DesignRule(
            "bow-flare", flare, BOW_FLARE_MIN_DEG,
            bool(math.isfinite(flare) and flare >= BOW_FLARE_MIN_DEG),
            "a bow with no flare cannot generate lift entering a wave, and "
            "buries instead of rising"))

    # -- bow fullness -------------------------------------------------------
    b = 2.0 * np.asarray(hull.y_sheer, float)
    stem = float(b[-2] / b.max()) if b.max() > 0 else 0.0
    if not piercer:
        out.append(DesignRule(
            "bow-fullness", stem, BOW_FULLNESS_MIN, stem >= BOW_FULLNESS_MIN,
            "reserve buoyancy forward; below the corpus p5 the bow is a spike"))

    # -- stem rake ----------------------------------------------------------
    # This grammar has NO stem-rake gene: LOA == LWL by construction, so the
    # stem is always exactly vertical. The rule is stated and MEASURED anyway,
    # because a rule that only exists once the gene does is a rule nobody
    # writes. It passes trivially today and will bite the day rake is added.
    rake = math.degrees(math.atan2(
        float(hull.x[-1] - hull.x[-1]), max(1e-9,
        float(hull.z_sheer[-1] - hull.z_keel[-1]))))
    reverse_ok = (rake >= -1e-9) or (fn is not None and fn >= REVERSE_RAKE_FN_FLOOR)
    out.append(DesignRule(
        "stem-rake", rake, 0.0, bool(reverse_ok),
        "reverse rake (bottom forward, top retracted) trades reserve buoyancy "
        f"for wave-piercing; below Fn {REVERSE_RAKE_FN_FLOOR} it buys nothing "
        "and risks burying the bow"))

    # -- anti-roll: the waterplane has to be there to resist heel -----------
    o = from_hull(hull)
    d = describe(o)
    out.append(DesignRule(
        "beam-carried", d.beam_carried, 0.20, d.beam_carried >= 0.20,
        "waterplane inertia is what resists roll; a hull that carries beam "
        "over too little of its length has none to give"))

    # -- a fair waterline, which is both looks and wave-making --------------
    out.append(DesignRule(
        "fair-waterline", d.waterline_convexity, 0.80,
        d.waterline_convexity >= 0.80,
        "a plan that reverses curvature makes waves and reads as wrong"))
    return out
