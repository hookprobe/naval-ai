"""P5: the parent-hull library, and the two distortion operators that make
it a design method instead of a museum.

RESEARCH GROUNDING (docs/audit/HULL-DESIGN-AUDIT.md, research matrix rows
"variation of a parent" and "learned generation"): industrial hull design
does not draw hulls from a blank page. It selects a PARENT with proven
behaviour and applies a LOW-DIMENSIONAL distortion — Lackenby's quadratic
section shift for Cp/LCB (1950, still the working method in commercial
suites) and homothetic principal-dimension scaling (the NSS and DSYHS
series are built exactly this way). Learned generative models are not
competitive below ~10^3-10^4 training hulls; this corpus holds TENS. So
retrieval + distortion is the honest seeding mechanism, and a network is
not.

WHAT AN OPERATOR IS HERE. In a offsets-table world Lackenby moves stations
fore and aft to change Cp/LCB without touching section shapes. In THIS
grammar the SAC solve (`geometry.sac_exponents`) already turns a (Cp, lcb)
request into the section distribution — the gene IS the Lackenby target —
so the operator reduces to a gene move PROJECTED INTO THE DELIVERABLE BAND
(`cp_band`/`lcb_band`) given the parent's fullness genes. That projection
is the whole operator: an unreachable target is clipped to the nearest
deliverable value, never refused, because a seeding operator's job is to
get close and let the ladder judge, not to raise.

PARENTS ARE PROVEN, NOT ASPIRATIONAL. Every entry names where its numbers
were measured; `tests/test_parents.py` re-proves on every run that each
parent builds, passes L0 and passes the shape critic for its family — a
parent that has decayed into a lens hull would otherwise seed every search
with the very shape the critic exists to refuse.

ONE HOME: the cruiser and deepv genomes lived in
`scripts/hull_kb_reconstruct.py:TARGETS` (which PROVED them against the KB
records); the script now imports them from here. The 16x4 barge probe in
`tests/test_barge_bow.py` deliberately keeps its own inline dict — that
test is a fence, and a fence that moves when the library moves measures
nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import grammar
from .geometry import GeometryError, cp_band, lcb_band


@dataclass(frozen=True)
class Parent:
    name: str
    # family uses the MISSION parser's vocabulary (mission.hull_family):
    # "barge", "pontoon", "wave_piercer" — plus the two regime words the
    # parser does not emit but retrieval falls back on: "displacement",
    # "planing".
    family: str
    genes: dict[str, float] = field(repr=False)
    provenance: str = ""


PARENTS: tuple[Parent, ...] = (
    Parent(
        name="solar-slender-cruiser",
        family="displacement",
        genes={
            "LWL": 12.0, "BWL": 1.85, "T": 0.55, "D": 1.30,
            # Re-tuned 2026-08-26 under the corrected sac solve (audit
            # D.4): the old Cp 0.56 was tuned against a solver that
            # ignored pmb and silently delivered ~0.60. Measured: entry
            # 11.8 deg, transom 0.341, convexity 0.927, zero critique
            # findings.
            "Cp": 0.64, "lcb": -2.0, "x_mb": 0.50, "r_transom": 0.15,
            "beta_mid": 4.0, "beta_bow": 30.0, "beta_len": 0.40,
            "roundness": 0.9, "rocker": 0.20, "forefoot": 0.15,
            "flare": 8.0, "sheer_rise": 0.12,
            "beta_transom": 2.0, "beta_run": 0.25,
            "flare_bow": 2.0, "flare_len": 0.35,
            "stem_depth": 0.0, "r_stem": 0.04, "pmb": 0.12,
        },
        provenance="data/hull_kb.json record 'solar-slender-cruiser'; "
                   "reconstruction proven by "
                   "scripts/hull_kb_reconstruct.py --target cruiser",
    ),
    Parent(
        name="warped-deepv",
        family="planing",
        genes={
            "LWL": 8.0, "BWL": 2.4, "T": 0.45, "D": 1.10,
            # Cp 0.74 is planing-correct and became REQUESTABLE when the
            # Cp gene box was decoupled from the Froude target table; pmb
            # 0.30 carries beam_carried to 0.390 — the published-hull
            # median — with the 24/14/27 deg warped deadrise law
            # delivered exactly.
            "Cp": 0.74, "lcb": -2.0, "x_mb": 0.40, "r_transom": 0.50,
            "beta_mid": 24.0, "beta_bow": 46.0, "beta_len": 0.40,
            "roundness": 0.0, "rocker": 0.05, "forefoot": 0.10,
            "flare": 12.0, "sheer_rise": 0.10,
            "beta_transom": 14.0, "beta_run": 0.35,
            "flare_bow": 5.0, "flare_len": 0.30,
            "stem_depth": 0.05, "r_stem": 0.05, "pmb": 0.30,
        },
        provenance="data/hull_kb.json record 'claude-training-sheet'; "
                   "reconstruction proven by "
                   "scripts/hull_kb_reconstruct.py --target deepv",
    ),
    Parent(
        name="liveaboard-barge",
        family="barge",
        # EXACTLY the measured configuration — the unnamed post-hoc genes
        # sit at POST_HOC_DEFAULTS (grammar.vector fills them), because
        # that is where they sat when the 88%/59.4 m2 was measured. A
        # first draft here added pmb=0.30 on plausibility and the sac
        # solve refused the genome outright (LCB -1.5 fell outside the
        # bracket pmb=0.30 leaves): a parent is a measurement, not an
        # interpretation.
        genes={
            "LWL": 15.2, "BWL": 4.0, "T": 0.391, "D": 1.55,
            "Cp": 0.92, "lcb": -1.5, "x_mb": 0.50, "r_transom": 0.92,
            "beta_mid": 8.0, "beta_bow": 10.0, "beta_len": 0.45,
            "roundness": 0.0, "rocker": 0.05, "forefoot": 0.10,
            "flare": 6.0, "sheer_rise": 0.12,
            "r_stem": 0.40,
        },
        provenance="the 16x4 houseboat landing (commit 6ccc02a): 88% of "
                   "the waterline at full beam, 59.4 m2 of deck (93% of "
                   "the rectangle) where the pre-fix spearhead carried "
                   "39% and 43.6 m2; fenced by tests/test_barge_bow.py",
    ),
)


# ---------------------------------------------------------------------------
# The operators
# ---------------------------------------------------------------------------

def refair(genes: dict[str, float]) -> dict[str, float]:
    """Project (Cp, lcb) into the band the fullness genes can DELIVER, and
    every gene into the legal envelope.

    The same projection `morphology_search._clip` and the optimizer's
    `_SacConsistencyRepair` apply, for the same reason a designer re-fairs
    Cp/LCB after moving anything: the corrected sac solve (audit D.4)
    REFUSES an undeliverable request, which is honest at L0 and fatal in an
    operator whose output feeds a sampler. Returns a NEW dict.
    """
    g = {k: float(v) for k, v in genes.items()}
    # legal envelope first, so the band is computed at the genes that will
    # actually be built
    for name in g:
        if name in grammar.NAMES:
            i = grammar.NAMES.index(name)
            g[name] = float(np.clip(g[name], grammar.LOW[i], grammar.HIGH[i]))
    rs, pm = g.get("r_stem", 0.0), g.get("pmb", 0.0)
    try:
        lo, hi = cp_band(g["LWL"], g["x_mb"], g["r_transom"], rs, pm)
    except (GeometryError, ValueError):
        # the band itself is unreachable at these fullness genes; leave the
        # request standing and let grammar.check refuse it by name
        return g
    # THE BAND OVERPROMISES AT ITS HIGH-Cp EDGE (measured 2026-08-27 on the
    # cruiser parent at Cp band-hi 0.9115): `lcb_band` reported
    # -0.30..+12.73 %LWL deliverable, and `sac_exponents` then lost its
    # inner bracket even 10% inside the Cp band with lcb at band MIDDLE.
    # Mechanism: the outer LCB bisection's residual falls back to a clamped
    # endpoint pf where no admissible pf exists, so near the edge the
    # closed-form interval is wider than what the solver can actually
    # deliver. Until that is fixed in the kernel, band membership is
    # NECESSARY, not sufficient — so this operator VERIFIES each candidate
    # with the solver itself and walks (Cp, lcb) toward band middle until
    # the solve succeeds. The walk is finite and ends at mid-band, where
    # every proven parent solves.
    from .geometry import sac_exponents
    cp0, lcb0 = g["Cp"], g["lcb"]
    mid_cp = 0.5 * (lo + hi)
    for f in (0.0, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0):
        eps = 1e-3 * max(hi - lo, 1e-6)
        cp_t = float(np.clip(cp0 + f * (mid_cp - cp0), lo + eps, hi - eps))
        try:
            l_lo, l_hi = lcb_band(g["LWL"], g["x_mb"], g["r_transom"],
                                  cp_t, rs, pm)
        except (GeometryError, ValueError):
            continue
        eps = 1e-2 * max(l_hi - l_lo, 1e-6)
        mid_l = 0.5 * (l_lo + l_hi)
        lcb_t = float(np.clip(lcb0 + f * (mid_l - lcb0),
                              l_lo + eps, l_hi - eps))
        try:
            sac_exponents(g["LWL"], g["x_mb"], g["r_transom"], cp_t, lcb_t,
                          r_stem=rs, pmb=pm)
        except (GeometryError, ValueError):
            continue
        g["Cp"], g["lcb"] = cp_t, lcb_t
        break
    return g


def rescale(genes: dict[str, float], lwl: float | None = None,
            bwl: float | None = None, t: float | None = None,
            d: float | None = None) -> dict[str, float]:
    """Homothetic principal-dimension scaling (the NSS-series operator).

    Setting LWL scales BWL/T/D by the same ratio so every proportion the
    parent was proven at survives; any dimension given explicitly OVERRIDES
    its scaled value (that is how a 16 m brief gets a 4 m beam from a
    15.2 x 4.0 parent without the beam drifting to 4.21). All shape genes
    are dimensionless by the grammar's own construction, so they carry over
    verbatim; (Cp, lcb) are re-faired because the deliverable band moves
    with the principal dimensions.
    """
    g = dict(genes)
    s = (float(lwl) / float(g["LWL"])) if lwl else 1.0
    g["LWL"] = float(lwl) if lwl else g["LWL"]
    g["BWL"] = float(bwl) if bwl else g["BWL"] * s
    g["T"] = float(t) if t else g["T"] * s
    g["D"] = float(d) if d else g["D"] * s
    return refair(g)


def lackenby(genes: dict[str, float], cp: float | None = None,
             lcb: float | None = None) -> dict[str, float]:
    """Move fullness and its centre the way Lackenby's shift does.

    In this grammar the SAC solve already turns (Cp, lcb) into the section
    distribution, so the classical station-shift reduces EXACTLY to a gene
    move projected into the deliverable band — see the module docstring.
    """
    g = dict(genes)
    if cp is not None:
        g["Cp"] = float(cp)
    if lcb is not None:
        g["lcb"] = float(lcb)
    return refair(g)


# ---------------------------------------------------------------------------
# Retrieval: a mission selects its parents
# ---------------------------------------------------------------------------

def select_parents(mission) -> tuple[Parent, ...]:
    """Parents matching the mission — declared family first, regime second.

    A declared family that some parent carries returns exactly those
    parents. Otherwise the mission's Froude number at its stated (or
    default) length picks the regime: Fn >= 0.40 is past `FN_MICHELL_MAX`'s
    displacement world and retrieves the planing parent, else the
    displacement one. Never returns empty — the fallback is the whole
    library, because retrieval is a seeding heuristic, not a gate.
    """
    fam = (getattr(mission, "hull_family", None) or "").lower()
    matched = tuple(p for p in PARENTS if p.family == fam)
    if matched:
        return matched
    from .formlib import knots_to_fn      # one home for the conversion
    lwl = getattr(mission, "lwl_hint_m", None) or 10.0
    kn = float(getattr(mission, "cruise_speed_kn", 5.0) or 5.0)
    fn = knots_to_fn(kn, lwl) if lwl > 0 else 0.0
    regime = "planing" if fn >= 0.40 else "displacement"
    matched = tuple(p for p in PARENTS if p.family == regime)
    return matched or PARENTS


# genes a seed may jitter, and how far (fraction of the legal span). Shape
# genes only — principal dimensions are the mission's to set, and (Cp, lcb)
# move through refair so the jitter cannot un-fair them.
_JITTER_FRAC: dict[str, float] = {
    "Cp": 0.05, "lcb": 0.05, "x_mb": 0.04, "r_transom": 0.05,
    "beta_mid": 0.05, "beta_bow": 0.05, "beta_len": 0.05,
    "rocker": 0.05, "forefoot": 0.05, "flare": 0.05, "sheer_rise": 0.05,
    "r_stem": 0.04, "pmb": 0.04,
}


def seed_for_mission(mission, n: int, rng: np.random.Generator) -> np.ndarray:
    """Up to n L0-valid genomes: retrieved parents, distorted to the brief.

    Each seed is a selected parent rescaled to the mission's stated
    dimensions (homothetic where the brief is silent), with a small jitter
    on the shape genes so n seeds from one parent are n distinct starting
    points rather than n copies. Every seed is re-faired and L0-checked;
    a candidate the grammar refuses is dropped, so the returned array may
    be shorter than n — the caller tops up from its own sampler.
    """
    parents = select_parents(mission)
    vessel = getattr(mission, "vessel", None)
    out: list[np.ndarray] = []
    for i in range(int(n)):
        p = parents[i % len(parents)]
        g = rescale(p.genes,
                    lwl=getattr(mission, "lwl_hint_m", None),
                    bwl=getattr(mission, "bwl_hint_m", None))
        for name, frac in _JITTER_FRAC.items():
            if name not in g:
                continue
            j = grammar.NAMES.index(name)
            span = float(grammar.HIGH[j] - grammar.LOW[j])
            g[name] = float(np.clip(
                g[name] + rng.normal(0.0, frac * span),
                grammar.LOW[j], grammar.HIGH[j]))
        g = refair(g)
        try:
            x = grammar.vector(g)
        except (KeyError, ValueError):
            continue
        if grammar.check(x, vessel=vessel).ok:
            out.append(x)
    return (np.array(out) if out
            else np.empty((0, grammar.N_PARAMS)))
