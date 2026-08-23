#!/usr/bin/env python
"""source -> genome -> generated hull -> measured back. The E5 round-trip.

GATE E5. Two tests live here and they are NOT the same test:

  THE SCALAR ROUND-TRIP asks whether the kernel HONOURS a commanded set of
  six numbers. The six are read off the source geometry, written into the
  genome, and read back off the generated hull with the same independent
  measurement code that read the source. It is the weaker test, and it is
  weak for a reason worth stating: `Cp` and `lcb` are genes the kernel SOLVES
  to, so a pass mostly confirms the solver converged.

  THE GEOMETRIC ROUND-TRIP asks the question that matters. Two hulls can
  share all six numbers and be different boats -- so with the six PINNED at
  the source values, the ten remaining shape genes are fitted to the source's
  own offsets and the residual THAT REMAINS is reported. That residual is not
  an error to be tuned away: it is the distance between a real published hull
  and the nearest hull this grammar can express, which is the one thing E5
  exists to find out.

WHAT IS NOT ALLOWED HERE, and the whole exercise is worthless without it: the
fit may move only the TEN. The moment `LWL`, `BWL`, `T`, `D`, `Cp` or `lcb`
is allowed to drift to improve the picture, the test stops measuring the
kernel and starts measuring the optimiser. `_assert_six_held` enforces it.

THE GENOME IS SIXTEEN GENES, NOT SIX. NavalAI has never claimed the six
determine a hull, and E5 must not be written as though it had. The six fix
size and two integral coefficients; the ten fix the SHAPE. Reporting the
scalar round-trip alone would be claiming a sufficiency the kernel does not
assert -- which is why the geometric residual is the headline number.
"""
from __future__ import annotations

import numpy as np

from navalai import geometry, grammar

#: STATION COUNT FOR EVERY EVALUATION, FIT AND MEASUREMENT ALIKE.
#: It is one constant because the two must not disagree. MEASURED: the
#: kernel's own constructibility is station-count dependent -- a genome whose
#: sectional-area target is reachable at every one of 161 stations can be
#: REFUSED at 321, because the finer grid samples a station where
#: `_stations` finds the demanded area unreachable at that draft and
#: deadrise ("area 0.2310 m^2 unreachable at x = 9.451 m"). Fitting at the
#: coarse count and measuring at the fine one therefore let the search
#: settle on hulls that cannot be built, and the first such hull killed the
#: run. The expressible set is defined by what the kernel will actually
#: build, so the fit searches at the same resolution the measurement uses.
N_STATIONS = 321

#: The six the source supplies, in genome order.
SIX = ("LWL", "BWL", "T", "D", "Cp", "lcb")

#: The ten the fit may move. Everything in `grammar.PARAMS` that is not one
#: of the six -- derived, not listed, so a gene added to the grammar joins the
#: fit instead of being silently frozen at a default nobody revisits.
TEN = tuple(n for n in grammar.NAMES if n not in SIX)


def hull_field(genome: np.ndarray, u: np.ndarray, v: np.ndarray,
               n_stations: int = N_STATIONS) -> tuple:
    """Half-breadth of a GENERATED hull on a normalised (u, v) grid.

    `u` is x/LWL from the transom, `v` is height above the baseline over T.
    The hull is built densely and INTERPOLATED onto the source's grid -- never
    the other way round. Interpolating the source would smooth the very shape
    the residual is trying to measure, and it is the source that is scarce.
    """
    h = geometry.Hull(genome, n_stations=n_stations)
    d = grammar.named(genome)
    z_base = float(h.z_keel.min())
    T = -z_base                       # z = 0 is the design waterline

    xs = h.x / d["LWL"]
    Y = np.empty((n_stations, len(v)))
    zk = (h.z_keel - z_base) / T
    zs = (h.z_sheer - z_base) / T
    for i in range(n_stations):
        p = h.section(i)
        zz = (p[:, 1] - z_base) / T
        yy = p[:, 0]
        o = np.argsort(zz)
        Y[i] = np.interp(v, zz[o], yy[o], left=np.nan, right=np.nan)
        Y[i][(v < zk[i] - 1e-12) | (v > zs[i] + 1e-12)] = np.nan
    out = np.empty((len(u), len(v)))
    for j in range(len(v)):
        out[:, j] = np.interp(u, xs, Y[:, j])
    return out, T, np.interp(u, xs, zk), np.interp(u, xs, zs)


def encode(six: dict, ten: dict) -> np.ndarray:
    """A genome from the source's pinned genes and the fitted ones."""
    d = {**{k: float(v) for k, v in six.items()},
         **{k: float(v) for k, v in ten.items()}}
    missing = [n for n in grammar.NAMES if n not in d]
    if missing:
        raise ValueError(f"genome incomplete, missing {missing}")
    return grammar.vector(d)


def _assert_six_held(genome: np.ndarray, six: dict, tol: float = 1e-9) -> None:
    got = grammar.named(genome)
    for k in six:
        if abs(got[k] - float(six[k])) > tol:
            raise AssertionError(
                f"the fit moved {k}: {six[k]} -> {got[k]}. The six are the "
                f"SOURCE's, and a fit that adjusts them measures the "
                f"optimiser, not the kernel.")


def residual(genome: np.ndarray, src: dict) -> dict:
    """Offset residual of a generated hull against a source offsets table.

    Compared at the SOURCE's own normalised stations and waterlines, in
    metres and as a percentage of the source's half-beam. Cells the source
    does not define (waterline below the local keel) are not compared, and
    are not counted as agreement either.
    """
    u, v, Ysrc = src["u"], src["v"], src["y"]
    _assert_six_held(genome, src["six"])
    Ygen, T, _, _ = hull_field(genome, u, v)
    ok = np.isfinite(Ysrc) & np.isfinite(Ygen)
    if ok.sum() < 20:
        return {"rms_m": float("inf"), "max_m": float("inf"),
                "n": int(ok.sum()), "rms_pct_halfbeam": float("inf"),
                "coverage": float(ok.sum()) / Ysrc.size}
    d = Ygen[ok] - Ysrc[ok]
    half = float(np.nanmax(Ysrc))
    below = v[None, :] <= 1.0 + 1e-9
    okb = ok & np.broadcast_to(below, ok.shape)
    return {
        "rms_m": float(np.sqrt(np.mean(d ** 2))),
        "max_m": float(np.max(np.abs(d))),
        "rms_pct_halfbeam": float(100.0 * np.sqrt(np.mean(d ** 2)) / half),
        "max_pct_halfbeam": float(100.0 * np.max(np.abs(d)) / half),
        "rms_below_dwl_m": (float(np.sqrt(np.mean(
            (Ygen[okb] - Ysrc[okb]) ** 2))) if okb.sum() else float("nan")),
        "n": int(ok.sum()),
        "coverage": float(ok.sum()) / float(np.isfinite(Ysrc).sum()),
    }


def cost(ten_vec: np.ndarray, six: dict, src: dict,
         free: tuple = TEN) -> float:
    g = encode(six, dict(zip(free, ten_vec)))
    try:
        r = residual(g, src)
    except Exception:                                   # noqa: BLE001
        return 1e6
    if not np.isfinite(r["rms_m"]):
        return 1e6
    # Coverage is part of the cost, not a filter: a hull that simply stops
    # short of the source's stations can otherwise score well on the few
    # cells it does define. Missing a cell is charged like a full half-beam
    # of error at that cell.
    miss = 1.0 - r["coverage"]
    half = float(np.nanmax(src["y"]))
    return r["rms_m"] + miss * half
