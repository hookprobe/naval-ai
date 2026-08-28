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

#: The L1 REFERENCE each anchored family is compared against — the L1
#: chain's own total at that anchor's condition, in newtons. THE RATIO IS
#: NOT STORED: it is computed from this and the book's measured total, so
#: the number cannot be a second copy that fails to notice its own sources
#: moving (the audit's P0-3; this repo's recurring number-declared-twice
#: defect, which had produced a hardcoded 1.57 beside a book that already
#: held 1733.47 N).
#: WHY `c06_case_a_n5` IS NOT HERE, recorded so the next session does not
#: re-derive it. The audit named it "the one L1-vs-RANS comparison buyable
#: without any new CFD" — a SETTLED run of a GRAMMAR-EMITTED hull, the
#: only anchor whose L1 side this tree can compute at all. ATTEMPTED
#: 2026-08-28 and REFUSED: the run's manifest records genome sha
#: 9163220c..., today's canonical case-a hashes bb47e95d..., and the
#: hull's wetted area reads 6.401 m2 against the manifest's 6.733. The
#: genome moved when the canonical cases were upgraded to critic-passing
#: forms (commit 4bca549) — legitimately, and with a full suite behind
#: it, but it means the solved hull and the computable hull are DIFFERENT
#: BOATS. The naive ratio is 3.03x and it is meaningless: it compares an
#: old surface's RANS against a new surface's L1.
#:
#: THE FREE PATH WAS TAKEN AND IT REFUSES TOO, for a better reason. The
#: pre-upgrade genome was reconstructed from `git show 4bca549^` and its
#: L1 computed at the run's own condition (903.3 kg, 2.0578 m/s, rho
#: 998.8): total 119.91 N = 55.82 wave + 64.09 friction, against the
#: settled RANS 376.95 N = 324.53 pressure + 52.42 viscous.
#:
#:     ratio RANS/L1   3.14x        (hb19 measures 1.57x)
#:     viscous half    0.82x        — the L1 friction is the right size
#:     pressure half   5.81x        — and this is the whole discrepancy
#:
#: A 5.8x pressure ratio is NOT a property of this hull family: it is the
#: same unexplained pressure over-prediction this project has measured
#: and not closed (CFD.md §2: KCS pressure 2.32x too high with a 36%
#: batch error while viscous sits at 1.161x; CLAUDE.md's beach/val_coarse
#: windows span 2.6-6.0x on the same signal). Publishing 3.14x as "the L1
#: gap for canonical case a" would encode an open SOLVER defect as a hull
#: property — the defect class this book exists to prevent.
#:
#: Identity is also not confirmed: the reconstructed genome hashes
#: 84b932a6 against the manifest's 9163220c (the digest covers the full
#: vector and the arity has moved 16 -> 32 since), and its wetted area
#: reads 6.844 m2 against the manifest's 6.733, a 1.6% gap. Close, not
#: equal.
#:
#: So the entry stays out, and what it is waiting on is named: the
#: pressure over-prediction, not another run.
L1_REFERENCE_N = {
    "hb19_7kn": {"l1_total_n": 1103.0, "rel_sigma": 0.25,
                 "basis": "the L1 chain (ITTC-57 friction x form-factor "
                          "band + Michell wave) at 7 kn on the houseboat19 "
                          "genome, docs/HULL-KB.md; the CFD side is "
                          "runs/hb19_7kn, single grid, NO GCI — the sigma "
                          "is the honest half of the number"},
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


def anchors(family: str | None = None, settled_only: bool = True,
            run_type: str | None = "calm_resistance") -> dict:
    """The raw records, optionally filtered. Unsettled records are DATA
    (they exist, honestly labelled) but never support a prediction.

    `run_type` defaults to `calm_resistance` because a wave-loads record
    and a resistance record are DIFFERENT MEASUREMENTS: the seas run
    carries zero forward speed under a nominal speed label, and its 132%
    batch error is "wrong measurement type", not "unsettled". Pass None
    to see every kind.
    """
    out = {}
    for name, a in _book().get("anchors", {}).items():
        if settled_only and not a.get("settled"):
            continue
        if family is not None and a.get("family") != family:
            continue
        if run_type is not None and a.get("run_type", "calm_resistance") \
                != run_type:
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
    """The measured RANS/L1 ratio for a family, COMPUTED from the book.

    NEVER apply this inside the ladder — it is a report-tier expectation
    whose sigma is as much the answer as its value. Returns a Refusal
    when the family has no anchor with a stored L1 reference, or when the
    anchor that would carry it is not a settled calm-water record.
    """
    book = _book().get("anchors", {})
    for case, ref in L1_REFERENCE_N.items():
        a = book.get(case)
        if a is None or a.get("family") != family:
            continue
        if not a.get("settled") or a.get("run_type") != "calm_resistance":
            return Refusal(f"{case} is not a settled calm-water record; a "
                           f"ratio taken from it would compare a "
                           f"prediction against a transient")
        l1 = float(ref["l1_total_n"])
        if l1 <= 0.0:
            return Refusal(f"{case} has no positive L1 reference")
        return {"ratio": float(a["total_n"]) / l1,
                "rans_total_n": float(a["total_n"]),
                "l1_total_n": l1,
                "fn": a.get("fn"),
                "rel_sigma": float(ref["rel_sigma"]),
                "basis": ref["basis"], "case": case}
    fams = sorted({book[c]["family"] for c in L1_REFERENCE_N if c in book})
    return Refusal(f"no L1 anchor measured for family {family!r} — the "
                   f"anchored families are {fams}; anchoring a new one "
                   f"needs one settled run of one of its hulls plus its "
                   f"L1 reference")
