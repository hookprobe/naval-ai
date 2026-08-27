"""The CFD anchor book's consumer: measured expectations for new designs.

THE OWNER'S DIRECTIVE (2026-08-28): the hookprobe/hb19/KCS campaigns
measured how these hull families behave — wave-dominated split, tunnel
inflow, the appendage cost — and future designs should CONSULT that
record instead of re-running CFD for questions it already answers.

WHAT THIS MODULE IS, AND IS NOT. It reads `data/cfd_anchors.json` (the
committed harvest of every citable run — see
scripts/harvest_cfd_anchors.py) and answers three questions:

  1. `same_geometry(stl_sha)` — has THIS exact surface been solved
     before? The strongest reuse: an identical STL at a nearby condition
     never needs the same run twice.
  2. `pressure_fraction_band(family, fn)` — what force split should a
     hull of this family expect? (Design guidance: 78-83% pressure on
     the bluff families across Fn 0.33-0.48 means the drag levers are
     AFT — transom clearance, eased shoulder — before any new run.)
  3. `l1_anchor_ratio(family)` — how far off is the L1 prediction known
     to be for this family? (hb19: RANS total = ~1.57x the L1 chain at
     Fn 0.33, single grid, no GCI — a research anchor, sigma stated
     WIDE.)

Every answer is REFUSED outside the measured support — wrong family,
Fn outside the anchored band, or only-unsettled coverage — because an
anchor book that extrapolates is a surrogate lying about its domain
(honesty rule 2: surrogates refuse OOD queries). And the L1 physics is
NEVER silently corrected: these are labelled expectations for reports,
critics and campaign planning, not a hidden multiplier on the ladder.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

_BOOK_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "cfd_anchors.json"

#: Fn distance within which an anchor is considered to speak for a query.
#: Half the spacing of the measured hookprobe points (0.33 -> 0.38 -> 0.48);
#: outside it the book refuses rather than interpolates across a hump.
FN_SUPPORT = 0.08

#: The hb19 L1-anchor ratio: RANS 1733 N settled vs the L1 chain's ~1103 N
#: at 7 kn (docs/HULL-KB.md, runs/hb19_7kn in the anchor book). SINGLE
#: GRID, NO GCI — the sigma is the honest half of the number.
L1_ANCHOR = {
    "bluff_stern_houseboat": {"ratio": 1.57, "rel_sigma": 0.25,
                              "basis": "runs/hb19_7kn settled vs L1 at "
                                       "Fn 0.33; single grid, no GCI"},
}


@dataclass(frozen=True)
class Refusal:
    reason: str

    def __bool__(self) -> bool:
        return False


def _book() -> dict:
    if not _BOOK_PATH.exists():
        return {"anchors": {}}
    return json.loads(_BOOK_PATH.read_text())


def anchors(family: str | None = None, settled_only: bool = True) -> dict:
    """The raw records, optionally filtered. Unsettled records are DATA
    (they exist, honestly labelled) but never support a prediction."""
    out = {}
    for name, a in _book().get("anchors", {}).items():
        if settled_only and not a.get("settled"):
            continue
        if family is not None and a.get("family") != family:
            continue
        out[name] = a
    return out


def same_geometry(stl_sha: str):
    """Every prior run of THIS exact surface, settled or not — the caller
    sees what exists before paying for a duplicate."""
    if not stl_sha:
        return Refusal("no stl sha given — identity is the whole question")
    hits = {n: a for n, a in _book().get("anchors", {}).items()
            if a.get("stl_sha256") == stl_sha}
    if not hits:
        return Refusal(f"no run of surface {stl_sha[:12]}… in the book")
    return hits


def pressure_fraction_band(family: str, fn: float):
    """(lo, hi, provenance) over the settled anchors of this family within
    FN_SUPPORT of the queried Froude number — or a Refusal naming exactly
    what is missing."""
    fam = anchors(family=family)
    if not fam:
        known = sorted({a["family"]
                        for a in _book().get("anchors", {}).values()})
        return Refusal(f"no settled anchor for family {family!r}; the book "
                       f"covers {known}")
    near = {n: a for n, a in fam.items()
            if a.get("fn") is not None and abs(a["fn"] - fn) <= FN_SUPPORT}
    if not near:
        fns = sorted(round(a["fn"], 2) for a in fam.values() if a.get("fn"))
        return Refusal(f"family {family!r} is anchored at Fn {fns}, not at "
                       f"Fn {fn:.2f} (+/-{FN_SUPPORT}) — a new run is the "
                       f"honest answer there")
    fr = [a["pressure_fraction"] for a in near.values()
          if a.get("pressure_fraction") is not None]
    return (min(fr), max(fr),
            f"{len(near)} settled anchor(s): {sorted(near)}")


def l1_anchor_ratio(family: str):
    """The measured RANS/L1 ratio for a family, or a Refusal. NEVER apply
    this inside the ladder — it is a report-tier expectation whose sigma
    is as much the answer as its value."""
    row = L1_ANCHOR.get(family)
    if row is None:
        return Refusal(f"no L1 anchor measured for family {family!r} — the "
                       f"only anchored family is "
                       f"{sorted(L1_ANCHOR)} (hb19); anchoring a new "
                       f"family needs one settled run of one of its hulls")
    return dict(row)
