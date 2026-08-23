#!/usr/bin/env python
"""Can the grammar's deadrise law express a real hard-chine hull? GATE E5-CHINE.

THIS TEST NEEDS NO OFFSETS, WHICH IS WHY IT EXISTS. Offsets for the hard-chine
series are mostly locked behind paywalls or printed only as body plans -- but
De Luca & Pensa (2017), Table 1(a,b), publishes something almost as useful and
far more portable: the DEADRISE DISTRIBUTION of eight systematic hard-chine
series, as three numbers each (at the transom, at 50% and at 75% of LWL). A
deadrise distribution IS the shape of a chine hull's bottom.

So the question becomes exact and cheap: set `beta_mid`, `beta_bow` and
`beta_len` to their best possible values and ask how close the grammar's
deadrise law can come to each published series.

    beta(x) = beta_mid                                   x <= (1 - beta_len) L
    beta(x) = beta_mid + (beta_bow - beta_mid) frac^2    forward of that

MEASURED, and the answer splits the families cleanly in two:

    series                              published        best fit      max err
    Series 62 (Clement & Blount 1963)   12.5/13.0/19.2   12.5/13.0/19.2   0.00
    Keuning & Gerritsma 1982            25.0/26.0/30.7   25.0/25.5/30.7   0.53
    Taunton & Alii 2010                 22.5/22.5/35.3   23.1/23.9/32.3   3.02
    USCG (Kowalyshyn & Metcalf 2006)    16.6/22.5/34.4   20.4/21.2/30.5   3.92
    Keuning & Alii 1993                 30.0/31.2/35.8   25.0/25.7/33.5   5.51
    NSS (De Luca & Pensa 2017)          13.2/22.3/38.5   20.0/20.9/30.2   8.27
    NTUA (Grigoropoulos & Loukakis)     10.0/22.5/38.0   18.6/19.5/29.3   8.69

MONOHEDRAL HULLS FIT EXACTLY. WARPED HULLS DO NOT, AND THE REASON IS
STRUCTURAL. `beta_len` is bounded at 0.60, so the deadrise is CONSTANT over at
least the after 40% of every hull this grammar can build, and warps only
forward. A warped hull's deadrise grows from the transom onward -- NSS runs
13.2 deg at the transom to 22.3 at midships -- which is warp in exactly the
region the law holds flat. No choice of the three genes reaches it; the fit
above drives `beta_bow` to its 50 deg ceiling and still lands 8 deg out.

Keuning & Alii 1993 fails for a different and simpler reason worth keeping
apart: its deadrise is 30 deg and `beta_mid` is bounded at 25, so a deep-V is
outside the box rather than outside the law.

THE PRODUCT CONSEQUENCE. NavalAI builds plywood boats. A warped bottom is what
a developable-panel hull naturally wants -- the Naples parent was explicitly
"changed to obtain the plating as developable surfaces" -- so this is not an
exotic form the product can decline. It is arguably the form the product is
FOR, and the grammar cannot draw it.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy.optimize import differential_evolution

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from navalai import grammar                                       # noqa: E402

#: Deadrise at the transom, at 50% LWL and at 75% LWL, in degrees.
#: SOURCE: De Luca, F. and Pensa, C., "The Naples warped hard chine hulls
#: systematic series", Ocean Engineering 139 (2017) 205-236, Table 1(a, b),
#: p. 206. Open access under CC BY-NC-ND. The table is that paper's own survey
#: of the field, so each row also carries its original citation.
#:
#: SEVEN ROWS ARE NOT SEVEN FAMILIES, and the count is kept honest here for
#: the same reason it is in `benchmarks/e5_sources.py`. Radojcic, Kalajdzic
#: and Simic, "Power Prediction Modeling of Conventional High-Speed Craft"
#: (Springer, 2019), Sect. 3.3, records that Clement & Blount 1963
#: (beta = 12.5 deg), Keuning & Gerritsma 1982 (25 deg) and Keuning et al.
#: 1993 (30 deg) are ONE series tested across three decades -- Series 62,
#: later called PHF and then DSDS, the Delft Systematic Deadrise Series. So
#: the survey covers FIVE independent families over seven deadrise
#: variations. It still separates monohedral from warped cleanly, which is
#: the finding; it just must not be described as seven families.
PUBLISHED_WARP = {
    "series62_clement_blount_1963": (12.5, 13.0, 19.2, "monohedral"),
    "keuning_gerritsma_1982": (25.0, 26.0, 30.7, "monohedral"),
    "keuning_alii_1993": (30.0, 31.2, 35.8, "monohedral deep-V"),
    "taunton_alii_2010": (22.5, 22.5, 35.3, "monohedral"),
    "uscg_kowalyshyn_metcalf_2006": (16.6, 22.5, 34.4, "part-warped"),
    "ntua_grigoropoulos_loukakis": (10.0, 22.5, 38.0, "warped, double chine"),
    "nss_deluca_pensa_2017": (13.2, 22.3, 38.5, "warped"),
}

STATIONS = (0.0, 0.50, 0.75)          # x / LWL from the transom

#: The bar. A hard-chine hull whose deadrise the grammar cannot reach within
#: this is NOT expressible, and the gate says so. Set at 1 degree because a
#: degree of deadrise is a real difference to a builder: on a 1 m half-beam it
#: moves the chine 17 mm, which is more than the 5 mm refold tolerance the
#: cut-file gate already enforces on the same panels.
WARP_TOL_DEG = 1.0


def beta_of(u, beta_mid: float, beta_bow: float, beta_len: float):
    """The grammar's deadrise law. `u` is x/LWL measured from the transom."""
    u = np.asarray(u, dtype=float)
    w0 = 1.0 - beta_len
    b = np.full_like(u, float(beta_mid))
    m = u > w0
    b[m] = beta_mid + (beta_bow - beta_mid) * ((u[m] - w0) / beta_len) ** 2
    return b


def best_fit(target) -> dict:
    names = ("beta_mid", "beta_bow", "beta_len")
    box = [(float(grammar.LOW[grammar.NAMES.index(n)]),
            float(grammar.HIGH[grammar.NAMES.index(n)])) for n in names]
    t = np.array(target[:3])
    u = np.array(STATIONS)

    def cost(v):
        return float(np.sqrt(np.mean((beta_of(u, *v) - t) ** 2)))

    r = differential_evolution(cost, box, seed=3, maxiter=400, tol=1e-10,
                               polish=True)
    got = beta_of(u, *r.x)
    return {"published_deg": t.tolist(), "fitted_deg": got.tolist(),
            "max_err_deg": float(np.max(np.abs(got - t))),
            "rms_err_deg": float(np.sqrt(np.mean((got - t) ** 2))),
            "genes": dict(zip(names, [float(v) for v in r.x])),
            "expressible": bool(np.max(np.abs(got - t)) <= WARP_TOL_DEG)}


def main() -> int:
    out = {}
    print(f"{'series':38s} {'published':16s} {'best fit':16s} {'max err':>8s}"
          f"  expressible")
    for key, target in PUBLISHED_WARP.items():
        r = best_fit(target)
        r["kind"] = target[3]
        out[key] = r
        print(f"{key:38s} {'/'.join(f'{v:.1f}' for v in r['published_deg']):16s}"
              f" {'/'.join(f'{v:.1f}' for v in r['fitted_deg']):16s}"
              f" {r['max_err_deg']:7.2f}d  "
              f"{'YES' if r['expressible'] else 'NO'}")
    (ROOT / "data" / "e5_chine_warp.json").write_text(
        json.dumps({"tolerance_deg": WARP_TOL_DEG, "stations": STATIONS,
                    "results": out}, indent=2))
    n = sum(1 for v in out.values() if v["expressible"])
    print(f"\n{n} of {len(out)} published hard-chine series are expressible "
          f"within {WARP_TOL_DEG} deg -> data/e5_chine_warp.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
