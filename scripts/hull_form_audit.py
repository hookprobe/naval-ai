#!/usr/bin/env python3
"""Measure the CURRENT parameter box against the hull-form rules drawn in
`downloads/hull-examples/*.png`.

This exists because `docs/research/HULL-FORM-RULES.md` states how far the
current batch sits from each drawn rule, and a document that states a distance
without a way to re-measure it is the defect class this repo keeps producing
(LESSONS.md #5: citing evidence that no longer exists). Re-run it and the
numbers in that document are reproduced or refuted.

MEASURED 2026-08-13 on commit 10a255a. Every number quoted in
HULL-FORM-RULES.md §"how far the current batch is" comes from this script.

PATHS MOVED, AND THAT IS ITSELF AN INSTANCE OF THE DEFECT. The drawings were
at `downloads/hull-example-*.png` when the first pass of this script and of
HULL-FORM-RULES.md was written; they are now under
`downloads/hull-examples/`, and six more sheets joined them. A citation that
names a path is only as good as the path, so `check_drawings_on_disk()` below
resolves every named sheet and REFUSES rather than warning — an audit that
cites a file it cannot open is quoting evidence it has not seen.

It reads ONLY: grammar.py, geometry.py, hydrostatics.py, resistance.py, and
(optionally, if present) formlib.py. It writes nothing and runs no solver.

    python scripts/hull_form_audit.py [--n 200] [--seed 0]
"""

from __future__ import annotations

import argparse
import math
import pathlib

import numpy as np

from navalai import grammar
from navalai.geometry import Hull, station_geometry

from navalai.constants import G_STANDARD as G  # C-33: one home
KNOT_MS = 0.514444

_REPO = pathlib.Path(__file__).resolve().parents[1]
DRAWINGS_DIR = _REPO / "downloads" / "hull-examples"

# The demihull the mission actually asks for: L=12, B=0.8, T=0.6 (m).
# Stated by the project owner alongside the drawings; NOT a grammar default.
TARGET_LBT = (12.0, 0.8, 0.6)

# Drawn rules that reduce to a number. Source image in the comment.
CAT_DEMIHULL_L_OVER_B_MIN = 12.0   # hull-example-001, "L/B_h > 12"
DEEP_V_DEADRISE_DEG = 24.0         # hull-designs-gemini, "DEEP-V (24 DEADRISE)"
MODIFIED_V_DEADRISE_DEG = 18.0     # hull-designs-gemini, "MODIFIED-V (18 DEADRISE)"

# The two DIMENSIONED solar catamarans in the set. Every field is a label read
# off the sheet; nothing here is derived by this script except the columns
# `drawn_solar_cats()` computes and prints.
#
#   (sheet, LWL m, B_overall m, L/B_h as printed, tunnel clearance m,
#    entry half-angle ceiling deg, PV area m2, PV peak kWp)
DRAWN_SOLAR_CATS = (
    ("hull-example-008.png", 12.0, 4.0, 15.3, 0.65, 10.0, 35.0, (6.0, 8.0)),
    ("hull-example-009.png", 16.0, 4.5, 17.8, 0.80, 9.0, 55.0, (10.0, 14.0)),
)

# The title block those two sheets share with 004, 005 and 006.
DRAWN_KNOT_BAND = (7.0, 12.0)
DRAWN_FN_BAND = (0.20, 0.35)

# The mission's own ceiling, which is BELOW the drawn band's. Carried so the
# clearance sweep reports the Froude number the design is actually judged at
# and not only the two the sheet prints — the whole point of the sweep is that
# the drawn clearance passes at one and fails at the other.
MISSION_FN_MAX = 0.30

# Every sheet the library and the rules document cite. Named here so ONE list
# is checked against the disk.
DRAWINGS = tuple(f"hull-example-{i:03d}.png" for i in range(10)) + (
    "hull-designs.png", "hull-designs-gemini.png")


def check_drawings_on_disk() -> list[str]:
    """Resolve every sheet this audit and the rules document cite, or REFUSE.

    An audit that cites a file it cannot open is quoting evidence it has not
    seen (LESSONS.md #5), and this project has already paid for that once: the
    sheets moved from `downloads/` to `downloads/hull-examples/` between the
    first pass of this script and the second, and six more joined them. A
    warning would have been ignored. This raises.
    """
    if not DRAWINGS_DIR.is_dir():
        raise SystemExit(
            f"the drawings directory does not exist: {DRAWINGS_DIR}. Every "
            f"number this script prints about a DRAWN rule is unverifiable "
            f"without it — refusing rather than printing them anyway.")
    missing = [d for d in DRAWINGS if not (DRAWINGS_DIR / d).is_file()]
    if missing:
        raise SystemExit(
            f"cited but not on disk under {DRAWINGS_DIR}: {missing}")
    extra = sorted({p.name for p in DRAWINGS_DIR.glob("*.png")} - set(DRAWINGS))
    lines = [f"{len(DRAWINGS)} cited sheets all resolve under {DRAWINGS_DIR}"]
    if extra:
        # NOT fatal, but said out loud: a sheet nobody cites is a sheet whose
        # content was dropped, which is the silent half of the same defect.
        lines.append(f"  WARNING: {len(extra)} sheet(s) on disk that this "
                     f"script cites nowhere: {extra}")
    return lines


def drawn_solar_cats() -> list[str]:
    """The two DIMENSIONED solar catamarans, and what their own numbers imply.

    Nothing here is an opinion about the drawings. Each row prints the labels
    as read, then the two quantities the labels DETERMINE but the sheets never
    state: the demihull separation ratio `s/L`, and whether the drawn tunnel
    clearance covers the steady bow-wave rise at each end of the title block's
    Froude band. Both are the sheet being checked against itself.
    """
    lines = ["THE TWO DIMENSIONED SOLAR CATAMARANS, CHECKED AGAINST THEMSELVES"]
    for (sheet, lwl, boa, lob_h, clear, ae_max, pv_m2, kwp) in DRAWN_SOLAR_CATS:
        b_h = lwl / lob_h                    # demihull waterline beam
        s = boa - b_h                        # demihull centreline separation
        lines += [
            f"  {sheet}  LWL {lwl} m  B_oa {boa} m  L/B_h {lob_h} "
            f"(=> B_h {b_h:.3f} m)",
            f"    entry half-angle ceiling {ae_max:g} deg   PV {pv_m2:g} m2 "
            f"at {kwp[0]:g}-{kwp[1]:g} kWp",
            f"    IMPLIED separation s = B_oa - B_h = {s:.3f} m  ->  "
            f"s/L = {s / lwl:.3f}",
        ]
        for fn in sorted({DRAWN_FN_BAND[0], MISSION_FN_MAX, DRAWN_FN_BAND[1]}):
            u = fn * math.sqrt(G * lwl)
            rise = bow_wave_rise(u)
            tag = "  <- mission ceiling" if fn == MISSION_FN_MAX else ""
            lines.append(
                f"    Fn {fn:.2f}  U {u:5.3f} m/s  bow-wave rise {rise:.3f} m  "
                f"vs drawn clearance {clear:.2f} m  -> "
                f"{'clears' if clear >= rise else 'FAILS'}{tag}")
        for kn in DRAWN_KNOT_BAND:
            lines.append(f"    title-block {kn:g} kn on this LWL is "
                         f"Fn {kn * KNOT_MS / math.sqrt(G * lwl):.3f}")
    lines.append(
        f"  the title block reads '{DRAWN_KNOT_BAND[0]:g}-"
        f"{DRAWN_KNOT_BAND[1]:g} knots, Fn {DRAWN_FN_BAND[0]:.2f}-"
        f"{DRAWN_FN_BAND[1]:.2f}'; the two halves above do not describe the "
        f"same boat, and the Fn half is the one adopted")
    return lines


def bow_wave_rise(speed: float) -> float:
    """Stagnation rise of the free surface at the stem, metres.

    SECOND COPY WARNING, and it is deliberate: the production definition is
    `navalai.resistance.bow_wave_rise`. This script does NOT import it, because
    it must keep running against an archived tree while `resistance.py` is being
    rewritten. `check_bow_wave_rise_matches_production()` below asserts the two
    agree, so the copy cannot drift silently -- which is the only reason a
    second copy is admissible at all (LESSONS.md #2).
    """
    return speed * speed / (2.0 * G)


def check_bow_wave_rise_matches_production() -> str:
    try:
        from navalai.resistance import bow_wave_rise as prod
    except Exception as exc:                      # pragma: no cover
        return f"NOT CHECKED against production ({type(exc).__name__}: {exc})"
    worst = 0.0
    for u in (0.5, 1.0, 2.0, 2.17, 3.255, 5.0):
        worst = max(worst, abs(prod(u) - bow_wave_rise(u)))
    if worst > 1e-12:
        raise SystemExit(f"bow_wave_rise drifted from production by {worst:g} m")
    return f"agrees with navalai.resistance.bow_wave_rise to {worst:g} m"


def waterline_halfbreadth(params: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Half-breadth of the DESIGN waterline (z=0) at longitudinal stations x.

    The section is keel -> chine -> sheer with two straight segments, so the
    waterline half-breadth is a linear interpolation inside whichever segment
    spans z=0. Above the sheer or below the keel the hull is not there and the
    half-breadth is not defined; those stations return NaN rather than 0.0,
    because a station that does not reach the waterline is UNMEASURED and
    scoring it as zero beam is exactly the `${VAR:-0}` defect (LESSONS.md #1).
    """
    zk, yc, zc, ys, zs = station_geometry(params, x)
    out = np.full_like(x, np.nan)
    # segment keel -> chine
    lo = (zk <= 0.0) & (zc >= 0.0) & (zc > zk)
    out[lo] = yc[lo] * (0.0 - zk[lo]) / (zc[lo] - zk[lo])
    # segment chine -> sheer
    hi = (zc < 0.0) & (zs >= 0.0) & (zs > zc)
    out[hi] = yc[hi] + (ys[hi] - yc[hi]) * (0.0 - zc[hi]) / (zs[hi] - zc[hi])
    # entirely submerged station (sheer under water): no waterline here
    return out


def alpha_e_deg(params: np.ndarray, frac: float = 0.05) -> float:
    """Half-angle of entrance, degrees, MEASURED off the waterline curve.

    Definition stated because there are several in the literature and they do
    not agree: this is the angle between the centreline and the chord of the
    design waterline from the stem to the station `frac * LWL` aft of it. A
    tangent at the stem is NOT used -- `station_geometry` carries a `w**0.15`
    sheer taper with an unbounded x-derivative at the stem, so a tangent there
    is a property of the parametrisation's singularity, not of the hull. The
    chord basis is stated in HULL-FORM-RULES.md wherever the number is quoted.
    """
    lwl = float(grammar.named(params)["LWL"])
    x_stem = lwl
    x_aft = lwl * (1.0 - frac)
    xs = np.linspace(x_aft, x_stem, 41)
    y = waterline_halfbreadth(params, xs)
    good = np.isfinite(y)
    if good.sum() < 2:
        return float("nan")
    xs, y = xs[good], y[good]
    dy = y[0] - y[-1]           # half-breadth at the aft end minus at the stem
    dx = xs[-1] - xs[0]
    if dx <= 0.0:
        return float("nan")
    return math.degrees(math.atan2(max(dy, 0.0), dx))


def target_verdict() -> list[str]:
    """Every grammar clause the 12 x 0.8 x 0.6 demihull violates, by name."""
    lwl, bwl, t = TARGET_LBT
    lines = [f"TARGET DEMIHULL  LWL {lwl} m  BWL {bwl} m  T {t} m",
             f"  L/B = {lwl / bwl:.3f}   B/T = {bwl / t:.3f}"]
    for name, val, (lo, hi) in (
            ("PARAMS bound[LWL]", lwl, (4.0, 20.0)),
            ("PARAMS bound[BWL]", bwl, (1.2, 6.0)),
            ("PARAMS bound[T]", t, (0.2, 1.5)),
            ("grammar.L_OVER_B_BAND", lwl / bwl, grammar.L_OVER_B_BAND),
            ("grammar.B_OVER_T_BAND", bwl / t, grammar.B_OVER_T_BAND)):
        ok = lo <= val <= hi
        lines.append(f"  {'ok  ' if ok else 'FAIL'} {name:<24} "
                     f"{val:8.3f} against [{lo}, {hi}]")
    lines.append(f"  drawn rule L/B_h > {CAT_DEMIHULL_L_OVER_B_MIN}: "
                 f"{'SATISFIED' if lwl / bwl > CAT_DEMIHULL_L_OVER_B_MIN else 'violated'}"
                 f" at {lwl / bwl:.3f}")
    return lines


def formlib_crosscheck() -> list[str]:
    """Check the drawn numbers THIS script owns against `navalai.formlib`.

    The two files necessarily restate a few of the same figures — the drawn
    catamaran L/B rule, the deep-V and modified-V deadrise angles, the 12 m
    demihull. That is a second copy, so it gets a fence rather than a comment
    (LESSONS.md #2). Optional because `formlib` is data and this script must
    keep running against an archived tree that predates it; ABSENCE is
    reported, never silently treated as agreement.
    """
    try:
        from navalai import formlib as F
    except Exception as exc:
        return [f"formlib cross-check: NOT RUN ({type(exc).__name__}: {exc})"]

    lines = ["FORMLIB CROSS-CHECK (the figures both files carry)"]
    bad: list[str] = []

    tgt = F.target()
    lob = tgt.band("l_over_b")
    lines.append(f"  target family {tgt.key!r}  L/B {lob}  "
                 f"(drawn rule > {CAT_DEMIHULL_L_OVER_B_MIN})")
    if lob is None:
        bad.append("formlib's target family carries no l_over_b band")
    else:
        if lob.low < CAT_DEMIHULL_L_OVER_B_MIN:
            bad.append(f"formlib target L/B band {lob} does not respect the "
                       f"drawn rule L/B_h > {CAT_DEMIHULL_L_OVER_B_MIN}")
        for sheet, _lwl, _boa, lob_h, *_rest in DRAWN_SOLAR_CATS:
            if not lob.contains(lob_h):
                bad.append(f"{sheet} prints L/B_h {lob_h}, outside the target "
                           f"family's band {lob}")

    mission_lbt = (F.MISSION.hull_lwl_m, F.MISSION.hull_bwl_m,
                   F.MISSION.hull_draft_m)
    if mission_lbt != TARGET_LBT:
        bad.append(f"TARGET_LBT {TARGET_LBT} disagrees with formlib.MISSION "
                   f"{mission_lbt}")
    else:
        lines.append(f"  demihull {TARGET_LBT[0]} x {TARGET_LBT[1]} x "
                     f"{TARGET_LBT[2]} m agrees with formlib.MISSION")

    for key, drawn in (("deep_v_planing", DEEP_V_DEADRISE_DEG),
                       ("modified_v_planing", MODIFIED_V_DEADRISE_DEG)):
        band = F.BY_KEY[key].band("deadrise_deg")
        ok = band is not None and band.contains(drawn)
        lines.append(f"  {key:<20} drawn {drawn:g} deg inside {band}: "
                     f"{'yes' if ok else 'NO'}")
        if not ok:
            bad.append(f"{key} deadrise band {band} excludes the drawn "
                       f"{drawn} deg")

    if bad:
        raise SystemExit("formlib cross-check FAILED:\n  - " +
                         "\n  - ".join(bad))
    lines.append("  all agree")
    return [ln for ln in lines if ln]


def pct(a: np.ndarray, q: float) -> float:
    return float(np.nanpercentile(a, q))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    for line in check_drawings_on_disk():
        print(line)
    print("bow_wave_rise:", check_bow_wave_rise_matches_production())
    print()
    for line in target_verdict():
        print(line)
    print()
    for line in drawn_solar_cats():
        print(line)
    print()
    for line in formlib_crosscheck():
        print(line)
    print()

    rng = np.random.default_rng(args.seed)
    X = grammar.sample(args.n, rng)
    named = [grammar.named(x) for x in X]

    lwl = np.array([d["LWL"] for d in named])
    bwl = np.array([d["BWL"] for d in named])
    t = np.array([d["T"] for d in named])
    lob = lwl / bwl
    bot = bwl / t
    ae = np.array([alpha_e_deg(x) for x in X])
    flare = np.array([d["flare"] for d in named])
    bmid = np.array([d["beta_mid"] for d in named])

    print(f"SAMPLED BATCH  n={args.n}  seed={args.seed}  "
          f"(grammar.sample, i.e. L0-feasible parameter vectors)")
    for label, arr, rule in (
            ("L/B", lob, f"drawn cat rule > {CAT_DEMIHULL_L_OVER_B_MIN}"),
            ("B/T", bot, f"grammar band {list(grammar.B_OVER_T_BAND)}"),
            ("alpha_e deg", ae, "fine-entry 7-12 deg"),
            ("flare deg", flare, "axe bow: 0"),
            ("beta_mid deg", bmid, "displacement: low")):
        print(f"  {label:<14} min {np.nanmin(arr):7.3f}  p50 {pct(arr, 50):7.3f}"
              f"  max {np.nanmax(arr):7.3f}   [{rule}]")

    # The box and the gate disagree, and which one refuses matters: a BOUND can
    # be widened, an L0 gate clause has to be re-argued.
    lwl_hi = dict((p[0], p[3]) for p in grammar.PARAMS)["LWL"]
    bwl_lo = dict((p[0], p[2]) for p in grammar.PARAMS)["BWL"]
    print(f"  box-maximal L/B = LWL_hi/BWL_lo = {lwl_hi}/{bwl_lo} = "
          f"{lwl_hi / bwl_lo:.3f}  -> the PARAMS box DOES reach "
          f"L/B > {CAT_DEMIHULL_L_OVER_B_MIN}")
    print(f"  but grammar.check's L/B clause caps it at "
          f"{grammar.L_OVER_B_BAND[1]}, so the refusal is the L0 GATE, "
          f"not the bounds")

    n_slender = int((lob > CAT_DEMIHULL_L_OVER_B_MIN).sum())
    n_fine = int(np.nansum((ae >= 7.0) & (ae <= 12.0)))
    n_zeroflare = int((np.abs(flare) < 0.5).sum())
    print(f"  hulls with L/B > {CAT_DEMIHULL_L_OVER_B_MIN}: {n_slender}/{args.n}"
          f"  (grammar.L_OVER_B_BAND caps L/B at {grammar.L_OVER_B_BAND[1]},"
          f" so this is STRUCTURALLY 0)")
    print(f"  hulls with alpha_e in [7, 12] deg: {n_fine}/{args.n}")
    print(f"  hulls with |flare| < 0.5 deg:      {n_zeroflare}/{args.n}")
    print()

    print("WET-DECK CLEARANCE the drawn rule needs, on the 12 m target")
    for fn in (0.20, 0.25, 0.30):
        u = fn * math.sqrt(G * TARGET_LBT[0])
        print(f"  Fn {fn:.2f}  U {u:6.3f} m/s  bow_wave_rise "
              f"{bow_wave_rise(u):.3f} m")
    print("  (there is no clearance parameter in grammar.NAMES, so no hull in "
          "the batch can be scored against this)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
