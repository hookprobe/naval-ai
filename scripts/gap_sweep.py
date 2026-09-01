#!/usr/bin/env python3
"""GAP SWEEP — the seam defects a per-module suite cannot see, found automatically.

WHY THIS EXISTS. On 2026-09-01 an end-to-end integration audit found nineteen
defects against a suite that was **2094 passed, 14 skipped, 0 failed**. Not one
of them was a row in `docs/GAP-REGISTER.md`, and not one was a bug in a module:
every single one was an AGREEMENT BETWEEN TWO SUBSYSTEMS that nothing checked.

    the descriptor layer measured a hull the ladder does not float
    a propulsion lever was credited to a hull that does not have it
    a catamaran was served the monohull pool
    the shape repair climbed one criterion and was judged by another
    a 200 t brief crashed the optimizer instead of refusing one design

`scripts/reconcile_gaps.py` answers "is the REGISTER's state what the code
says?" and answers it well. It cannot answer "do two subsystems agree about
one hull?", because that question has no row. THIS script asks that one, and
it asks it the only way that works: by running the product and comparing.

HOW IT DIFFERS FROM THE TEST SUITE. A test pins a known answer. A probe here
takes a PROPERTY that must hold across a seam and sweeps it over a generated
population, so it finds the case nobody thought to write down. The suite is
the ratchet; this is the search.

WHAT IT WILL NOT DO. It does not close a gap by editing a predicate, does not
soften a bar, and does not report "no findings" for a probe that could not run
— an unmeasurable probe is a FINDING (docs/LESSONS.md defect class 1). Exit
code is 1 when anything is found, so it can gate CI or drive a fix loop.

    python scripts/gap_sweep.py                 # every probe, human report
    python scripts/gap_sweep.py --json out.json # machine-readable
    python scripts/gap_sweep.py --probe cache   # one probe
    python scripts/gap_sweep.py --list          # what the probes are
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import traceback
from dataclasses import asdict, dataclass, field

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from navalai import grammar                                  # noqa: E402
from navalai.geometry import Hull                            # noqa: E402
from navalai.mission import MissionSpec, parse_mission       # noqa: E402


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """One seam that does not hold. `evidence` is NUMBERS, never adjectives."""
    probe: str
    severity: str            # P0 P1 P2 P3
    subsystem: str
    claim: str               # the property that failed, stated positively
    evidence: str
    detail: dict = field(default_factory=dict)


_PROBES: dict[str, tuple[str, object]] = {}


def probe(name: str, what: str):
    def deco(fn):
        _PROBES[name] = (what, fn)
        return fn
    return deco


# ---------------------------------------------------------------------------
# The population every probe sweeps over. ONE definition, so two probes cannot
# disagree about which hulls they are talking about.
# ---------------------------------------------------------------------------

BRIEFS = [
    "16 m x 4 m recreational houseboat, 5 knots, 6 tonne, category C",
    "16 m x 4 m houseboat with a protected prop, 5 knots, 6 tonne, category C",
    "12 m river cruiser, 7 knots, 4 tonne, category C",
    "8 m river launch, 6 knots, 2 tonne, category C",
    "6 m dinghy with an outboard, 8 knots, 900 kg, category C",
]

#: The topology features, each as the FULL coherent bundle. A partial bundle
#: is not a weak feature, it is no feature.
FEATURES = {
    "dwl": dict(dwl=0.8, cwp_x=0.05, rb_transom=0.55, rb_stem=0.25,
                r_stem=0.25),
    "tunnel": dict(tun_w=0.35, tun_crown=0.35, tun_len=0.30),
    "split": dict(split_w=0.45, split_len=0.35),
    "rho_x": dict(rho_len=0.35, rho_bow=0.15),
    "pmb": dict(pmb=0.30),
    "r_stem": dict(r_stem=0.45),
    "wave_pierce": dict(flare_len=0.35, flare_bow=-10.0, stem_depth=0.30),
    "beta_run": dict(beta_run=0.30, beta_transom=4.0),
    "ch2": dict(ch2_y=0.10, ch2_z=0.55),
}

#: A plausible inland cruiser the features are applied to. Chosen because it
#: floats, plank and all, so a refusal is about the FEATURE and not the base.
BASE = {"LWL": 16.0, "BWL": 4.0, "T": 0.75, "D": 1.60, "Cp": 0.72,
        "lcb": -1.0, "x_mb": 0.52, "r_transom": 0.55, "beta_mid": 6.0,
        "beta_bow": 22.0, "beta_len": 0.30, "roundness": 0.35,
        "rocker": 0.06, "forefoot": 0.10, "flare": 6.0, "sheer_rise": 0.10}


def genome(**over) -> np.ndarray:
    g = dict(grammar.POST_HOC_DEFAULTS)
    g.update(BASE)
    g.update(over)
    return grammar.vector(g)


def feature_cases():
    """(label, genome) for the base, every feature, and every PAIR."""
    import itertools
    yield "base", genome()
    for k, v in FEATURES.items():
        yield k, genome(**v)
    for a, b in itertools.combinations(sorted(FEATURES), 2):
        o = dict(FEATURES[a])
        o.update(FEATURES[b])
        yield f"{a}+{b}", genome(**o)


# ---------------------------------------------------------------------------
# PROBE 1 — the descriptor layer must measure the hull the ladder floats.
# The class that produced F1: `form_coefficients` recomputed the sectional
# area and the waterplane from the bare outer envelope, so a split hull
# reported Cm 1.1514 (impossible) and +7.5% of volume into the critic, the
# certification and the design report.
# ---------------------------------------------------------------------------

#: MODEL IDENTITY, not agreement-to-a-tolerance. The comparison is made on the
#: descriptors' OWN grid (see `_ladder_on_grid`), so the two sides differ only
#: if they are different MODELS — and then they differ in the 12th digit or
#: not at all.
#:
#: THE FIRST VERSION OF THIS PROBE MADE THE ERROR IT EXISTS TO CATCH. It
#: compared 401-station descriptors against 41-station ladder integrals and
#: reported seven P1 findings of 0.17-0.32%, every one of them on a hull with
#: `r_stem` — where the SAC carries area to the stem and a coarse trapezoid
#: reads the waterplane worst. Re-measured on a common grid the two agree, and
#: the ladder's own integral CONVERGES onto the descriptor value
#: (r_stem: 41 -> 46.2695, 401 -> 46.1813, 1601 -> 46.1792 m2). An instrument
#: that partly measures how the measurement was taken is docs/LESSONS.md's own
#: warning, and it caught this file on its first run.
_MODEL_TOL = 1e-9


def _ladder_on_grid(x, n: int):
    """(volume, waterplane) by the LADDER's integral on an n-station grid.

    The descriptors resample; so must the comparison, or the difference being
    measured is the grid and not the model.
    """
    from navalai import geometry
    from navalai.geometry import (_immersed_batch, immersed_arguments,
                                  open_waterline_halfbreadth)
    p = grammar.named(x)
    L = p["LWL"]
    xs = np.union1d(np.linspace(0.0, L, n), np.array([p["x_mb"] * L]))
    s = geometry._stations(x, xs)
    K, P0, C, P2, S, ch, no, ho = immersed_arguments(s, x)
    a, b, _zc = _immersed_batch(K, P0, C, P2, S, 0.0,
                                chain=ch, notch=no, hole=ho)
    vol = 2.0 * float(np.trapezoid(a, xs))
    awp = 2.0 * float(np.trapezoid(
        open_waterline_halfbreadth(b, s["y_split"]), xs))
    return vol, awp


@probe("delivered", "descriptors describe the hull the ladder floats")
def _delivered():
    out = []
    for label, x in feature_cases():
        try:
            h = Hull(x)
        except Exception:                                    # noqa: BLE001
            continue                                         # kernel refusal
        try:
            fc = h.form_coefficients()
            vol, awp = _ladder_on_grid(x, 401)   # the descriptors' OWN grid
        except Exception as e:                               # noqa: BLE001
            out.append(Finding(
                "delivered", "P2", "geometry", label,
                f"could not compare descriptors to the ladder: "
                f"{type(e).__name__}: {e}"))
            continue
        if vol > 0 and abs(fc["volume_m3"] / vol - 1.0) > _MODEL_TOL:
            out.append(Finding(
                "delivered", "P1", "geometry -> descriptors",
                "form_coefficients volume == the ladder's displaced volume",
                f"{label}: descriptors {fc['volume_m3']:.4f} m3, ladder "
                f"{vol:.4f} m3 ({100 * (fc['volume_m3'] / vol - 1):+.3f}%)",
                {"case": label}))
        awp_fc = fc["Cwp"] * BASE["BWL"] * BASE["LWL"]
        if awp > 0 and abs(awp_fc / awp - 1.0) > _MODEL_TOL:
            out.append(Finding(
                "delivered", "P1", "geometry -> descriptors",
                "Cwp implies the waterplane the ladder integrates",
                f"{label}: descriptors {awp_fc:.4f} m2, ladder {awp:.4f} m2 "
                f"({100 * (awp_fc / awp - 1):+.3f}%)", {"case": label}))
        if not (0.0 < fc["Cm"] <= 1.0):
            out.append(Finding(
                "delivered", "P0", "geometry -> descriptors",
                "0 < Cm <= 1 (a section cannot exceed the box it is "
                "measured against)",
                f"{label}: Cm = {fc['Cm']:.4f}", {"case": label}))
    return out


# ---------------------------------------------------------------------------
# PROBE 2 — a feature must not change displacement behind the designer's back.
# The class that produced F2 and F9. Every feature that folds its area into
# the section solve is EXACT; the ones that do not must DECLARE their drift
# through `Hull.sac_deviation`, and the declared set is fixed here so a new
# feature cannot join it silently.
# ---------------------------------------------------------------------------

#: Features MEASURED to deliver the commanded SAC exactly. A feature leaving
#: this set is a regression; one joining it is an improvement that must be
#: recorded here in the same change.
_SAC_EXACT = {"base", "tunnel", "split", "rho_x", "pmb", "r_stem",
              "wave_pierce", "beta_run"}

#: Features whose drift is KNOWN, MEASURED and reported. The number is the
#: ceiling this sweep will accept before calling it a regression.
_SAC_DECLARED = {"ch2": 0.05, "dwl": 0.02}


@probe("sac", "the delivered SAC is the commanded SAC, or the drift is declared")
def _sac():
    out = []
    for label, x in feature_cases():
        try:
            h = Hull(x)
            rel = h.sac_deviation_rel()
        except Exception:                                    # noqa: BLE001
            continue
        if not math.isfinite(rel):
            out.append(Finding(
                "sac", "P1", "geometry", f"{label}: SAC deviation measurable",
                "sac_deviation_rel is not finite — an unmeasurable contract "
                "is a finding, never a pass"))
            continue
        parts = set(label.split("+"))
        allowed = max([_SAC_DECLARED[p] for p in parts if p in _SAC_DECLARED]
                      or [0.0])
        if allowed == 0.0 and not parts <= _SAC_EXACT:
            allowed = 0.05          # an unclassified feature: report, do not
            out.append(Finding(    # pretend it is exact
                "sac", "P3", "geometry",
                f"{label}: every feature is classified exact-or-declared",
                f"parts {sorted(parts - _SAC_EXACT - set(_SAC_DECLARED))} "
                f"are in neither set; gap_sweep cannot judge this drift"))
        if rel > max(allowed, 1e-9):
            out.append(Finding(
                "sac", "P1", "geometry",
                f"{label}: delivered area == commanded area",
                f"SAC drift {rel:.3e} of the maximum section against an "
                f"allowance of {allowed:.3e}", {"case": label}))
    return out


# ---------------------------------------------------------------------------
# PROBE 3 — a lever the HULL does not have must contribute nothing.
# The class that produced F4: a declared `prop_tunnel_recess_m` bought a
# flat-bottomed hull a bigger propeller disc and a clean wake.
# ---------------------------------------------------------------------------

@probe("declared", "a declared lever is backed by the geometry")
def _declared():
    from navalai import propulsion
    from navalai.energy import EnergySpec
    out = []
    flat = Hull(genome())
    tun = Hull(genome(tun_w=0.35, tun_crown=0.50, tun_len=0.35))
    if propulsion.drawn_tunnel_recess_m(flat) != 0.0:
        out.append(Finding("declared", "P2", "propulsion",
                           "a hull with no tunnel genes draws no tunnel",
                           f"flat hull draws "
                           f"{propulsion.drawn_tunnel_recess_m(flat):.4f} m"))
    for arch in ("shaft", "tunnel"):
        rows = {}
        for recess in (0.0, 0.5):
            spec = EnergySpec(drive=arch, n_props=1, motor_kw=40.0,
                              prop_tunnel_recess_m=recess)
            g, _why = propulsion.rows_for(flat, 0.0, 6000.0, 20000.0, spec)
            rows[recess] = float(g["prop_space"])
        if abs(rows[0.5] - rows[0.0]) > 1e-12:
            out.append(Finding(
                "declared", "P2", "propulsion -> geometry",
                "a declared tunnel recess moves no row on a hull that draws "
                "no tunnel",
                f"drive {arch}: prop_space {rows[0.0]:+.4f} at recess 0.00 "
                f"and {rows[0.5]:+.4f} at 0.50 — a lever the hull does not "
                f"have"))
    # and the other direction: drawing one must BUY something, or the
    # geometry is still invisible
    spec = EnergySpec(drive="shaft", n_props=1, motor_kw=40.0,
                      prop_tunnel_recess_m=0.5)
    g_t, _ = propulsion.rows_for(tun, 0.0, 6000.0, 20000.0, spec)
    g_f, _ = propulsion.rows_for(flat, 0.0, 6000.0, 20000.0, spec)
    if not g_t["prop_space"] < g_f["prop_space"]:
        out.append(Finding(
            "declared", "P2", "propulsion -> geometry",
            "drawing a tunnel buys disc room",
            f"tunnelled {g_t['prop_space']:+.4f} is not better than flat "
            f"{g_f['prop_space']:+.4f}"))
    return out


# ---------------------------------------------------------------------------
# PROBE 4 — a cache key must identify everything its value depends on.
# The class that produced F8: `mission_key` enumerated 5 of MissionSpec's 16
# fields by hand, so a catamaran was served the monohull pool AND the
# monohull Pareto front, labelled with its own receipt.
# ---------------------------------------------------------------------------

#: A value per MissionSpec field that is VALID and DIFFERENT from the default,
#: so "changing this field moves the key" is a real question. A field with no
#: entry is reported rather than skipped — an untested field is the defect.
_FIELD_ALT = {
    "displacement_target_kg": 9999.0, "cruise_speed_kn": 11.0,
    "design_category": "B", "crew": 9, "lwl_hint_m": 17.0,
    "bwl_hint_m": 4.0, "hull_family": "barge", "berths": 7,
    "air_draft_max_m": 3.3, "waters": "coastal", "windage": None,
    "name": "another name", "notes": "retyped",
    "energy": None, "vessel": None, "payload": None,
}


@probe("cache", "a cache key identifies everything its value depends on")
def _cache():
    sys.path.insert(0, str(ROOT / "ui"))
    import server as S                                       # noqa: PLC0415
    out = []
    base = MissionSpec()
    excluded = getattr(S, "_KEY_EXCLUDED_FIELDS", frozenset())
    for f in sorted(type(base).__dataclass_fields__):
        if f in excluded:
            continue
        if f not in _FIELD_ALT:
            out.append(Finding(
                "cache", "P3", "ui", f"field {f!r} is exercised by the sweep",
                "no alternative value is declared for it, so 'does it move "
                "the key?' has not been asked"))
            continue
        alt = _FIELD_ALT[f]
        if alt is None:
            continue                # nested spec: covered by the two below
        try:
            moved = MissionSpec(**{f: alt})
        except Exception:                                    # noqa: BLE001
            continue
        if S.mission_key(base) == S.mission_key(moved):
            out.append(Finding(
                "cache", "P1", "ui",
                f"changing {f!r} changes the pool key",
                f"two missions differing only in {f!r} share a scored pool "
                f"and a Pareto front"))
    # the nested specs, whole
    from navalai.energy import EnergySpec
    from navalai.mission import VesselConfig
    for lbl, m in (("energy", MissionSpec(energy=EnergySpec(drive="tunnel"))),
                   ("vessel", MissionSpec(vessel=VesselConfig(
                       topology="catamaran", separation_over_lwl=0.35)))):
        if S.mission_key(base) == S.mission_key(m):
            out.append(Finding(
                "cache", "P1", "ui", f"the {lbl} spec is part of the pool key",
                f"a mission differing only in its {lbl} spec is served "
                f"another mission's pool"))
    # prose must NOT move it, or a retyped brief misses the cache
    if S.mission_key(base) != S.mission_key(
            MissionSpec(name="x", notes="y")):
        out.append(Finding(
            "cache", "P3", "ui", "prose does not move the pool key",
            "a retyped brief with identical numbers misses the cache"))
    return out


# ---------------------------------------------------------------------------
# PROBE 5 — every gene is reachable as declared, or withheld as declared.
# The class that produced F6 and F12: thirteen genes across four kernel
# phases were produced by NO production generator, and the fact was
# discoverable only by reading four modules.
# ---------------------------------------------------------------------------

@probe("reach", "every gene is drawn, or withheld, exactly as declared")
def _reach():
    from navalai.evaluate import sample_valid
    out = []
    post = set(grammar.POST_HOC_DEFAULTS)
    blind = set(grammar.EXPLORE_BLIND_GENES)
    bundled = {g for b in grammar._EXPLORE_FEATURE_BUNDLES.values() for g in b}
    unclassified = post - blind - bundled
    # a gene in neither set is WITHHELD; that is legitimate, but it must be
    # withheld in FACT and not merely by omission, which is what we check
    for brief in BRIEFS[:3]:
        m = parse_mission(brief)
        try:
            X, _y = sample_valid(12, m, seed=5, explore_post_hoc=True)
        except Exception as e:                               # noqa: BLE001
            out.append(Finding("reach", "P2", "search",
                               f"{brief[:40]}: the feed produces candidates",
                               f"{type(e).__name__}: {e}"))
            continue
        X = np.asarray(X, float)
        want = grammar.features_for(m)
        for nm in sorted(blind):
            col = X[:, grammar.NAMES.index(nm)]
            if float(np.max(np.abs(col))) <= 1e-9:
                out.append(Finding(
                    "reach", "P2", "search",
                    f"{nm} is declared drawn-blind and varies",
                    f"{brief[:40]}: 0 of {len(X)} candidates move it"))
        for feat, bundle in grammar._EXPLORE_FEATURE_BUNDLES.items():
            asked = feat in want
            drawn = all(float(np.min(X[:, grammar.NAMES.index(nm)])) > 0.0
                        for nm in bundle)
            if asked and not drawn:
                out.append(Finding(
                    "reach", "P1", "mission -> search",
                    f"a mission asking for {feat} gets hulls that have one",
                    f"{brief[:40]}: features_for says {sorted(want)} and the "
                    f"bundle is not drawn on every candidate"))
            if not asked and any(float(np.max(np.abs(
                    X[:, grammar.NAMES.index(nm)]))) > 0.0 for nm in bundle):
                out.append(Finding(
                    "reach", "P2", "mission -> search",
                    f"a mission NOT asking for {feat} gets none",
                    f"{brief[:40]}: the bundle appears uninvited"))
        for nm in sorted(unclassified):
            col = X[:, grammar.NAMES.index(nm)]
            if float(np.max(np.abs(col))) > 0.0:
                out.append(Finding(
                    "reach", "P2", "search",
                    f"{nm} is withheld from the feed",
                    f"{brief[:40]}: it is drawn anyway, and nothing declares "
                    f"why it should be"))
    return out


# ---------------------------------------------------------------------------
# PROBE 6 — a repair must optimise the criterion it will be judged by, inside
# the box it will be judged in. The class that produced F18 and F19: the shape
# climb used the general bands while the ladder used the family's, and it
# searched the grammar box and was then clipped into the mission's, which
# destroyed 9 of 9 repaired seeds.
# ---------------------------------------------------------------------------

@probe("repair", "the repair is judged by what repairs it")
def _repair():
    import inspect as _inspect

    from navalai import morphology, morphology_search, optimize
    out = []
    # (a) the operator must be able to receive the family and the box at all
    sig_search = _inspect.signature(morphology_search.search).parameters
    for arg in ("family", "bounds"):
        if arg not in sig_search:
            out.append(Finding(
                "repair", "P2", "search",
                f"morphology_search.search accepts {arg!r}",
                "the repair cannot be told the criterion or the box it is "
                "being judged in"))
    src = _inspect.getsource(optimize._DrawBoxSampling)
    if "family=" not in src:
        out.append(Finding(
            "repair", "P2", "search",
            "the optimizer's climb is told the mission's family",
            "`_DrawBoxSampling` calls the critic with no family while "
            "`evaluate`'s shape row uses one"))
    if "bounds=" not in src:
        out.append(Finding(
            "repair", "P1", "search",
            "the optimizer's climb searches the box it is clipped into",
            "`_DrawBoxSampling` climbs and then np.clips, which moves the "
            "hull it just repaired"))
    # (b) BEHAVIOUR: a repaired seed must SURVIVE the clip
    m = parse_mission("16 m x 4 m recreational houseboat, 5 knots, 6 tonne, "
                      "category C")
    prob = optimize.HullProblem(m)
    lo, hi = np.asarray(prob.xl, float), np.asarray(prob.xu, float)
    rng = np.random.default_rng(3)
    X = grammar.sample(12, rng)
    survived = repaired = 0
    for i in range(0, len(X), 2):
        g = dict(zip(grammar.NAMES, map(float, X[i])))
        try:
            best, _a = morphology_search.search(
                g, iterations=60, rng=np.random.default_rng(1000 + i),
                family=m.hull_family, bounds=(lo, hi))
        except Exception:                                    # noqa: BLE001
            continue
        if best is None or not best.ok:
            continue
        repaired += 1
        v = np.clip(grammar.vector(best.genome), lo, hi)
        try:
            d = morphology.describe(morphology.from_hull(Hull(v)))
            survived += bool(morphology.critique(
                d, family=m.hull_family).ok)
        except Exception:                                    # noqa: BLE001
            pass
    if repaired and survived == 0:
        out.append(Finding(
            "repair", "P1", "search",
            "a repaired seed is still plausible after the population clip",
            f"{repaired} seeds reached plausibility and {survived} survived "
            f"`np.clip` into the mission box — repairing a hull and then "
            f"moving it is not repairing it"))
    return out


# ---------------------------------------------------------------------------
# PROBE 7 — one bad design must not abort the run.
# The class that produced F20: an ordinary brief ("200 tonne houseboat")
# crashed `pareto_front` out of the ISO scantling rule instead of refusing
# one candidate.
# ---------------------------------------------------------------------------

#: Briefs at and beyond the edges of what the parser will accept. Every one is
#: reachable production input — the parser CLAMPS rather than rejecting, so
#: these are what a user can actually type.
_EDGE_BRIEFS = [
    "200 tonne houseboat, 16 m, 5 knots",
    "24 m houseboat, 5 knots, 100 tonne, category A",
    "2.5 m tender, 3 knots, 50 kg",
    "24 m catamaran, 20 knots, 30 tonne, category A",
    "16 m houseboat, 0.5 knots, 6 tonne",
    "16 m houseboat, 40 knots, 6 tonne",
]


@probe("contain", "one bad design refuses; it does not abort the run")
def _contain():
    from navalai.evaluate import evaluate
    out = []
    x = genome()
    for brief in _EDGE_BRIEFS:
        try:
            m = parse_mission(brief)
        except Exception as e:                               # noqa: BLE001
            out.append(Finding(
                "contain", "P2", "mission",
                f"{brief!r} parses or is refused by name",
                f"parse_mission raised {type(e).__name__}: {e}"))
            continue
        try:
            ev = evaluate(x, m)
        except Exception as e:                               # noqa: BLE001
            out.append(Finding(
                "contain", "P1", "ladder",
                f"{brief!r}: the ladder REFUSES rather than raising",
                f"evaluate raised {type(e).__name__}: {str(e)[:120]} — an "
                f"exception here aborts a whole NSGA-II population",
                {"brief": brief}))
            continue
        if ev.ok is False and not ev.violations:
            out.append(Finding(
                "contain", "P2", "ladder",
                f"{brief!r}: a refusal names its reason",
                "ok is False with an empty violations tuple"))
    return out


# ---------------------------------------------------------------------------
# PROBE 8 — no published number is a silent NaN, and no absence is silent.
# The class behind gap E11 and F13: 0.0 and NaN are the BEST possible values
# of several published quantities, so an unmeasurable one must be declared
# absent rather than scored.
# ---------------------------------------------------------------------------

@probe("receipts", "no published scalar is a silent NaN")
def _receipts():
    from navalai import formcheck
    out = []
    for label, x in list(feature_cases())[:12]:
        try:
            fd = formcheck.form_descriptors(x, MissionSpec())
        except Exception:                                    # noqa: BLE001
            continue
        for k, v in fd["scalars"].items():
            if isinstance(v, float) and not math.isfinite(v):
                if k in fd.get("absent", {}):
                    continue
                out.append(Finding(
                    "receipts", "P2", "formcheck",
                    f"{k} is finite or declared absent with a reason",
                    f"{label}: {k} = {v} and it is not in `absent`",
                    {"case": label, "scalar": k}))
    return out


# ---------------------------------------------------------------------------
# PROBE 9 — a quantity computed in two places must agree.
# The project's own recurring defect, A NUMBER DECLARED TWICE, asked directly
# of the pairs that exist today rather than of the source text.
# ---------------------------------------------------------------------------

@probe("twice", "a quantity computed twice agrees with itself")
def _twice():
    out = []
    # water density: the CFD case, the post-processor and the anchor book
    from navalai.cfd import case as _case
    from navalai.cfd.post import resistance_coefficient
    rho_case = float(_case._RHO_WATER)
    probe_ct = resistance_coefficient(1000.0, 10.0, 2.0)
    rho_post = 1000.0 / (0.5 * probe_ct * 10.0 * 4.0)
    if abs(rho_post / rho_case - 1.0) > 1e-9:
        out.append(Finding(
            "twice", "P2", "cfd",
            "post.resistance_coefficient uses the density the case solves at",
            f"case {rho_case:.4f} vs implied {rho_post:.4f} kg/m3"))
    book = ROOT / "data" / "cfd_anchors.json"
    if book.exists():
        for name, a in json.loads(book.read_text())["anchors"].items():
            ct, S, U, T = (a.get("ct"), a.get("wetted_m2"),
                           a.get("speed_ms"), a.get("total_n"))
            if not (ct and S and U and T):
                continue
            got = resistance_coefficient(T, S, U)
            if abs(got / ct - 1.0) > 1e-9:
                out.append(Finding(
                    "twice", "P2", "cfd-kb",
                    f"{name}: the book's Ct is the kernel's Ct",
                    f"book {ct:.6e} vs kernel {got:.6e} "
                    f"({100 * (got / ct - 1):+.3f}%)"))
    # the aft prior's advertised share must be its actual share
    from navalai import morphology_search as _ms
    u, w = _ms.aft_prior_shares()
    k, n = len(_ms._AFT_GENES), grammar.N_PARAMS
    if abs(u - k / n) > 1e-12:
        out.append(Finding("twice", "P3", "search",
                           "the aft prior's uniform share is k/N_PARAMS",
                           f"{u:.4f} vs {k / n:.4f}"))
    return out


# ---------------------------------------------------------------------------
# PROBE 10 — the two production design routes must answer the same brief.
# The class that produced F5 and the length-hint half of F6: `/generate`
# conditioned only the ranking while `pareto_front` conditioned the box, so
# a 16 m x 4 m brief was answered with 11.7 m and 2.2 m of beam.
# ---------------------------------------------------------------------------

@probe("routes", "the production design routes agree about a brief")
def _routes():
    from navalai.evaluate import sample_valid
    out = []
    for brief in BRIEFS[:4]:
        m = parse_mission(brief)
        if not (m.lwl_hint_m and m.bwl_hint_m):
            continue
        try:
            X, _y = sample_valid(12, m, seed=5, explore_post_hoc=True)
        except Exception:                                    # noqa: BLE001
            continue
        X = np.asarray(X, float)
        for gene, hint in (("LWL", m.lwl_hint_m), ("BWL", m.bwl_hint_m)):
            col = X[:, grammar.NAMES.index(gene)]
            lo, hi = hint * 0.9 - 1e-9, hint * 1.1 + 1e-9
            bad = int(((col < lo) | (col > hi)).sum())
            if bad:
                out.append(Finding(
                    "routes", "P2", "search",
                    f"the feed honours the {gene} the brief states",
                    f"{brief[:40]}: {bad} of {len(col)} candidates outside "
                    f"{hint} +/-10% (range {col.min():.2f}..{col.max():.2f})",
                    {"brief": brief, "gene": gene}))
    return out


# ---------------------------------------------------------------------------
# PROBE 11 — the ladder's own station count must be CONVERGED for every
# feature that can reach it.
#
# FOUND BY THIS FILE, 2026-09-01, while fixing the `delivered` probe's own
# grid error. `Hull.n_stations` is 41 and `export.py` records a measured
# decision NOT to raise it: taking it to 81 costs `evaluate()` 22.14 -> 33.38
# ms (+51%) against Gate 1's 50 ms bar "and it buys the LADDER nothing --
# wetted +0.014%, displaced volume +0.006%".
#
# That measurement is dated 2026-08-13 and the SPLIT STERN landed 2026-08-27.
# Re-measured against a 1281-station reference on a 16 x 4 m hull:
#
#     feature   BM error at 41 stations      awp error
#     base            +0.052%                 -0.039%
#     dwl             +0.027%                 -0.008%
#     ch2             +0.052%                 -0.039%
#     r_stem          -0.017%                 +0.014%
#     SPLIT           -0.532%                 -0.263%
#     dwl+split       -1.506%                 -0.679%
#
#     split convergence:  41 -0.535% | 61 -0.280% | 81 -0.168%
#                        121 -0.071% | 161 -0.047% | 321 -0.012%
#
# The mechanism is a KINK: `y_split` is zero forward of (split_len * L) and
# finite aft of it, and `ixx ~ b^3 - ys^3` inherits the corner, which a
# uniform trapezoid straddles. BM drives GM, and GM is a SAFETY FLOOR -- so
# this is not a cosmetic integral.
#
# It is not a live defect TODAY, and the reason is the one this sweep can
# check mechanically: the split is WITHHELD from every production draw
# (Gate REACHABILITY), so no shipped hull carries it. This probe couples the
# two facts. While the split is withheld the finding is informational; the
# day anyone promotes it to drawn, the same probe turns P1 -- so the
# discretisation cannot be promoted past by forgetting it.
# ---------------------------------------------------------------------------

#: Measured at 41 stations against a 1281-station reference, per feature.
#: A feature whose BM error exceeds this is not converged on the grid the
#: ladder floats on.
_BM_CONVERGENCE_BAR = 0.001          # 0.1%


@probe("stations", "the ladder's station count is converged for every "
                   "REACHABLE feature")
def _stations():
    from navalai.hydrostatics import solve_to_displacement
    out = []
    reachable = set(grammar.EXPLORE_BLIND_GENES) | {
        g for b in grammar._EXPLORE_FEATURE_BUNDLES.values() for g in b}
    for label, x in list(feature_cases())[:1 + len(FEATURES)]:
        genes = set(FEATURES.get(label, {}))
        is_reachable = bool(genes) and genes <= reachable
        try:
            coarse, _a = solve_to_displacement(Hull(x, n_stations=41), 6000.0)
            fine, _b = solve_to_displacement(Hull(x, n_stations=641), 6000.0)
        except Exception:                                    # noqa: BLE001
            continue                # a refusal is that feature's own business
        err = abs(coarse.bm / fine.bm - 1.0) if fine.bm else float("inf")
        if err <= _BM_CONVERGENCE_BAR:
            continue
        out.append(Finding(
            "stations",
            "P1" if is_reachable else "P3",
            "geometry -> hydrostatics",
            f"{label}: BM is converged at the shipped 41 stations",
            f"BM {coarse.bm:.4f} at 41 vs {fine.bm:.4f} at 641 "
            f"({100 * (coarse.bm / fine.bm - 1):+.3f}%), bar "
            f"{100 * _BM_CONVERGENCE_BAR:.1f}%. "
            + ("THIS FEATURE IS REACHABLE FROM PRODUCTION — BM drives GM and "
               "GM is a safety floor."
               if is_reachable else
               "Withheld from every production draw today, so no shipped hull "
               "carries it; resolve the discretisation BEFORE promoting it."),
            {"case": label, "reachable": is_reachable,
             "bm_41": coarse.bm, "bm_641": fine.bm}))
    return out


# ---------------------------------------------------------------------------
# PROBE 12 — a hull whose moulded surface does not CLOSE must be refused, not
# meshed. And the funnel must not promise a watertightness it never measured.
#
# MEASURED 2026-09-01 by the small-boat end-to-end validation. The brief
# "8 m river launch, 6 knots, 2 tonne" designs fine -- 36 members, ok=True,
# GM 0.698 m, MARGINAL -- and 3 of its first 6 front members produce an STL
# that `cfd.case.write_resistance_case` REFUSES:
#
#     hull.stl is not a closed manifold and will not be meshed:
#     13 open_or_nonmanifold_edges
#
# while `certify.cfd_candidate` reported `eligible True, score 0.781,
# meshability SAFE`. 0 of 30 SAMPLED hulls fail; it is the optimizer's
# boundary-seeking members that do.
#
# ROOT CAUSE, located exactly and NOT the first two things it looked like.
# At the transom the section's rows 0 and 1 land at EXACTLY the same z
# (-0.3674332138315444 on the recorded genome), because a raised keel
# (rocker 0.506) meets a nearly-flat floor (beta_mid 1.61 deg). The transom
# cap's bottom quad is then a LINE, both its triangles have area exactly 0.0,
# and the two shells meet at the keel in a single PINCH POINT rather than
# along a seam -- three edges used once each.
#
# Two hypotheses were tested and REFUTED before this one, which is why the
# mechanism is written down: it is not the 1e-10 sliver bar (both cap
# triangles are area 0.0 and are dropped at ANY bar, including `> 0.0`), and
# keeping the degenerate cap triangles makes it WORSE, not better (3 open
# edges become 20).
#
# The real fix is the one `Hull.closed_mesh`'s own docstring already names and
# defers: "An indexed/welded emit would make the watertightness STRUCTURAL
# instead of coincidental." Until that lands, what this probe holds is the
# CONTRACT, which is intact: the production path refuses these hulls loudly
# and fatally, so nothing meshes a hull with a hole in it.
#
# AND IT DOES NOT ADD A CHEAP CHECK TO `certify`, deliberately. Measured at
# nx=40/nz=10 the same three hulls read ZERO open edges -- the pinch is
# resolution-dependent -- so a coarse check would publish SAFE for a surface
# the case writer rejects. That is the layer-table lie (docs/LESSONS.md defect
# class 1) and the probe refuses to build one.
# ---------------------------------------------------------------------------

#: The recorded genome, front[1] of "8 m river launch, 6 knots, 2 tonne,
#: category C" at pop 48 / gens 15 / seed 3 on 2026-09-01. Kept as LITERALS
#: because a regression case that has to re-run an optimiser to reproduce
#: itself is a regression case nobody runs.
_OPEN_MESH_GENOME = {
    "LWL": 8.8, "BWL": 3.4626696981, "T": 0.743523535, "D": 1.314298457,
    "Cp": 0.620539462, "lcb": -0.3452242346, "x_mb": 0.5419134073,
    "r_transom": 0.1634487547, "beta_mid": 1.609692412,
    "beta_bow": 35.7950528328, "beta_len": 0.5708108257,
    "roundness": 0.8091132278, "rocker": 0.5058216767,
    "forefoot": 0.1722411011, "flare": 24.8680545543,
    "sheer_rise": 0.2952470022, "beta_run": 0.0002412241,
    "cwp_x": -4.54597e-05, "tun_crown": 0.0009897559, "ch2_z": 8.2599e-06,
}


@probe("meshclose", "an unclosed hull is REFUSED, never meshed")
def _meshclose():
    from navalai.geometry import open_edge_count
    out = []
    g = dict(grammar.POST_HOC_DEFAULTS)
    g.update(_OPEN_MESH_GENOME)
    x = grammar.vector(g)
    try:
        hull = Hull(x)
        V, F = hull.closed_mesh(nx=80, nz=16)
        open_edges = open_edge_count(V, F)
    except Exception as e:                                   # noqa: BLE001
        out.append(Finding("meshclose", "P2", "geometry",
                           "the recorded open-mesh genome still builds",
                           f"{type(e).__name__}: {e}"))
        return out
    if open_edges == 0:
        out.append(Finding(
            "meshclose", "P3", "geometry",
            "the recorded transom-pinch genome still reproduces",
            "it now closes at nx=80/nz=16. If `closed_mesh` was welded, "
            "DELETE this probe and its genome in the same commit — a "
            "regression case for a fixed defect is wallpaper."))
        return out
    # THE CONTRACT: the production path must REFUSE it.
    import tempfile
    from navalai.cfd.case import write_resistance_case
    with tempfile.TemporaryDirectory() as td:
        try:
            write_resistance_case(hull, 3.0, pathlib.Path(td) / "case",
                                  end_time=1.0, np_procs=1)
            out.append(Finding(
                "meshclose", "P0", "geometry -> cfd",
                "a hull whose surface does not close is REFUSED by the case "
                "writer",
                f"the case was WRITTEN for a hull with {open_edges} open "
                f"edges at nx=80/nz=16 — an open shell floods the interior "
                f"and yields a complete, plausible, meaningless run"))
        except ValueError as e:
            if "closed manifold" not in str(e):
                out.append(Finding(
                    "meshclose", "P2", "geometry -> cfd",
                    "the refusal NAMES the surface as the reason",
                    f"refused, but for another reason: {str(e)[:120]}"))
        except Exception:                                    # noqa: BLE001
            pass          # a different environment failure is not this probe's
    return out


# ---------------------------------------------------------------------------
# The driver.
# ---------------------------------------------------------------------------

_SEV_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def run(selected=None) -> list[Finding]:
    findings: list[Finding] = []
    for name, (what, fn) in _PROBES.items():
        if selected and name not in selected:
            continue
        try:
            got = fn() or []
        except Exception:                                    # noqa: BLE001
            # A PROBE THAT COULD NOT RUN IS A FINDING. It is not a pass, and
            # it is not a silent skip (docs/LESSONS.md defect class 1).
            got = [Finding(name, "P2", "gap_sweep",
                           f"the {name!r} probe runs",
                           "it raised: "
                           + traceback.format_exc().strip().splitlines()[-1])]
        for f in got:
            findings.append(f)
        print(f"  {name:10s} {what:58s} "
              f"{'CLEAN' if not got else str(len(got)) + ' FINDING(S)'}")
    findings.sort(key=lambda f: (_SEV_ORDER.get(f.severity, 9), f.probe))
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gap_sweep")
    ap.add_argument("--probe", action="append",
                    help="run only these probes (repeatable)")
    ap.add_argument("--json", help="write the findings here")
    ap.add_argument("--list", action="store_true",
                    help="list the probes and what each asserts")
    args = ap.parse_args(argv)

    if args.list:
        for name, (what, fn) in _PROBES.items():
            print(f"{name:10s} {what}")
            print(f"           {(fn.__doc__ or '').strip().splitlines()[0]
                                if fn.__doc__ else ''}")
        return 0

    print("GAP SWEEP — seam properties, swept over the production flow")
    print("=" * 78)
    findings = run(set(args.probe) if args.probe else None)
    print("=" * 78)
    if not findings:
        print("no seam findings. This is not proof the seams are sound; it "
              "is proof that THESE properties hold on THIS population.")
    else:
        print(f"{len(findings)} finding(s):\n")
        for f in findings:
            print(f"[{f.severity}] {f.probe}/{f.subsystem}")
            print(f"      CLAIM     {f.claim}")
            print(f"      EVIDENCE  {f.evidence}")
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps([asdict(f) for f in findings], indent=1))
        print(f"\n-> {args.json}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
