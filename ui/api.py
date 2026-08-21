"""The mapping layer between the ladder and the builder-facing surface.

WHY THIS FILE EXISTS, AND WHY IT IS NOT IN `ui/server.py`.
`ui/server.py` is pinned by `tests/test_stageF.py` and `tests/test_phase4.py`
down to the strings in its payloads and the shape of its cache; it serves the
ENGINEER's surface (`/eval`, `/bounds`, `/mission`, `/generate`, `/pareto`) and
`docs/BUILD-PLAN.md` §PU says in as many words that the gap to a builder-facing
UI "is a mapping layer, not a rewrite". So the mapping layer is a separate
module with its own routes under `/api/`, and `server.py` gains a dispatch call
rather than five hundred lines.

THE ONE RULE THIS FILE ENFORCES, because a UI cannot enforce it for itself.
Every payload declares its own `source` — `measured`, `absent`, `refused` or
`mock` — and the front end renders the declaration, not a default. The defect
this guards against is the one `docs/BUILDER-UX.html` §00 names: a screen that
reads `tier` and paints L1 green over a sigma somebody typed. MEASURED in this
tree before the fence existed: four sigmas in `ui/server.py` were literal
fractions of their own value (`freeboard` 0.02, `cb` 0.02, solar x0.25,
range_solar x0.35) and every one of them rendered as a confident band.

An ABSENT capability is declared HERE, in `ABSENT`, and nowhere else. A hatched
tile in the HTML with its reason typed into the markup would be the
number-declared-twice defect wearing a `<div>`: the day the backend grows a
stem-rake gene, the tile would go on saying it has not.
"""
from __future__ import annotations

import dataclasses
import json
import math
import threading
import time
import uuid
from pathlib import Path

import numpy as np

from navalai import grammar
from navalai.evaluate import CONSTRAINT_NAMES, evaluate
from navalai.mission import MissionSpec

_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# The absence registry. Shape copied deliberately from `navalai.refdata.absent`
# ({what, why, unblocked_by}), which is the pattern this project already uses
# for a hole it refuses to fill with a plausible number.
# ---------------------------------------------------------------------------

ABSENT: dict[str, dict[str, str]] = {
    "stem_rake": {
        "what": "reverse-raked bow / wave-piercer",
        "why": "there is no stem-rake gene in grammar.PARAMS, so LOA == LWL by "
               "construction. The hull-form library catalogues "
               "wave_piercing_monohull and axe_bow as not expressible.",
        "unblocked_by": "a stem-rake parameter in the grammar and in "
                        "geometry.station_geometry",
        "surface": "studio.bow_attitude",
    },
    "air_draft": {
        "what": "air draft / bridge clearance",
        "why": "no field anywhere in the tree holds it. parse_mission swallows "
               "'3 m total height' as lwl_hint_m = 3.0 — a silent misread, "
               "which is why the mission read-back is mandatory.",
        "unblocked_by": "an air_draft_m field on MissionSpec and a check row "
                        "that can fail on it",
        "surface": "mission.readback",
    },
    "motion_in_chop": {
        "what": "how she rides in a 1 m chop",
        "why": "the sea-state preset and the heave response both exist and are "
               "not wired to each other; slamming pressure is uncalibrated by "
               "a factor of four. The parts exist, the answer does not.",
        "unblocked_by": "seakeeping response joined to the sea-state preset, "
                        "and a calibrated slamming model",
        "surface": "reality.chop",
    },
    "solar_sigma": {
        "what": "an uncertainty band on solar generation",
        "why": "EnergySpec declares solar_yield_kwh_m2_day, panel_packing and "
               "panel_eff as bare floats, so there is no input band to "
               "propagate. The value ships with SIGMA_PLACEHOLDER rather than "
               "with a typed 25% dressed as one sigma.",
        "unblocked_by": "a SOURCED yield spread on EnergySpec — a data "
                        "decision, not a code one",
        "surface": "reality.solar",
    },
    "cb_sigma": {
        "what": "an uncertainty band on block coefficient",
        "why": "cb is a coefficient of the FLOATED hull, so its band is the "
               "sinkage band seen through the volume integral. Nothing "
               "computes that.",
        "unblocked_by": "sinkage uncertainty propagated through the volume "
                        "integral",
        "surface": "hydrostatics.cb",
    },
    "planing": {
        "what": "resistance above Fn 0.45",
        "why": "the thin-ship model disowns itself there and there is no "
               "Savitsky-class model in the tree. Semi-displacement and "
               "planing are refused BY NAME, not extrapolated.",
        "unblocked_by": "a planing model with its own validation anchor",
        "surface": "analysis.speed",
    },
    "hardchine_anchor": {
        "what": "an experimental anchor for hard-chine resistance at Fn 0.26",
        "why": "the only CFD anchor is KCS, a 230 m container ship that shares "
               "no chine, transom or spray physics with these craft. Gate 2M "
               "is SOLVER VERIFICATION ONLY.",
        "unblocked_by": "the Compton 1986 USNA hard-chine series — identified, "
                        "data not held",
        "surface": "validation.physics",
    },
    "assembly_manual": {
        "what": "stitch spacing, wire placement, puzzle joints, an assembly "
                "manual",
        "why": "the backend derives a sequence from sheet assignment and "
               "nothing more. Scarph joints are modelled as material "
               "allowance and split location, NOT as a cut taper — a builder "
               "cutting to the drawn line would get it wrong.",
        "unblocked_by": "a joinery model in navalai/unroll.py",
        "surface": "build.assembly",
    },
    "bom_consumables": {
        "what": "glass cloth, fasteners, copper stitching wire",
        "why": "the BOM engine does not emit them, and epoxy is a single "
               "1.4 kg/m^2 scalar with no split between fillets, coats and "
               "sheathing.",
        "unblocked_by": "consumable lines in the BOM engine",
        "surface": "build.materials",
    },
    "cost_model": {
        "what": "a build cost",
        "why": "no cost model exists in the tree. A number here would be "
               "invented, and a builder would buy plywood with it.",
        "unblocked_by": "a sourced materials price list with a date and a "
                        "currency",
        "surface": "build.cost",
    },
    "state_of_charge": {
        "what": "battery state of charge over a day",
        "why": "there is no SOC model. Animating a battery filling and "
               "emptying would imply a simulation that does not exist.",
        "unblocked_by": "an SOC integrator over the solar day shape",
        "surface": "reality.solar",
    },
}

# Capabilities that ARE real, with what makes them real. The manifest is what
# the front end reads to decide whether to draw a control at all.
REAL: dict[str, str] = {
    "live_eval": "evaluate() measured 11.35 ms; tests/test_phase4.py enforces "
                 "a 100 ms p95 per widget",
    "fast_mesh": "Hull.panel_mesh() measured 1.66 ms — live during drag",
    "fine_mesh": "Hull.closed_mesh() measured 49.75 ms — on release, not "
                 "during drag",
    "policy_box": "compile_policy(Constitution).box(category) with every move "
                  "recorded as a BoxEdit(param, edge, was, now, source)",
    "constraints": "exactly %d rows: %s" % (len(CONSTRAINT_NAMES),
                                            ", ".join(CONSTRAINT_NAMES)),
    "gz_curve": "hydrostatics.gz_curve floats the hull at 16 heels by "
                "bisection — ~1 s, so it is an action, not a live light",
    "refold_family": "unroll.refold_convergence over a station family returns "
                     "PASSES / REFINING / NON_DEVELOPABLE / REFUSED",
    "nesting": "unroll.hull_panels + nest — measured ~869 ms, export-time only",
    "pareto": "optimize.pareto_front via ui/server.py, NSGA-II pop=48 gens=15",
    "gate_ledger": "data/gate-ledger.json, the ONE home of a red gate's "
                   "watermark",
    "cfd_receipts": "runs/*/case.info written by scripts/make_case.py",
}


def _jsonable(o):
    if isinstance(o, np.ndarray):
        return [_jsonable(v) for v in o.tolist()]
    if isinstance(o, (np.floating, np.integer)):
        o = o.item()
    if isinstance(o, float):
        return None if not math.isfinite(o) else round(o, 6)
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return _jsonable(dataclasses.asdict(o))
    return o


def _hull(params: dict, n_stations: int = 41):
    from navalai.geometry import Hull
    x = _vector(params)
    return Hull(x, n_stations=n_stations)


def _vector(params: dict) -> np.ndarray:
    mid = grammar.named((grammar.LOW + grammar.HIGH) / 2)
    return grammar.vector({**mid,
                           **{k: float(v) for k, v in (params or {}).items()
                              if k in mid}})


# ---------------------------------------------------------------------------
# manifest — what the surface may draw
# ---------------------------------------------------------------------------

def manifest_payload() -> dict:
    """Everything the front end needs to decide what to draw and how to badge
    it, in ONE fetch. `absent` is served, never typed into the markup."""
    return {
        "source": "measured",
        "params": [{"name": n, "unit": u, "low": lo, "high": hi, "desc": d}
                   for (n, u, lo, hi, d) in grammar.PARAMS],
        "constraints": list(CONSTRAINT_NAMES),
        "absent": ABSENT,
        "real": REAL,
        "budgets_ms": {"evaluate": 11.35, "panel_mesh": 1.66,
                       "closed_mesh": 49.75, "hull_panels": 869.0,
                       "gate4_widget_bar": 100.0},
        "budgets_note": "measured on the Mac simulation node; "
                        "tests/test_phase4.py defends the 100 ms bar",
        "froude_ceiling": 0.45,
        "refold_bar_mm": _refold_bar(),
    }


def _route(cp, body: dict) -> dict:
    """The delivery route for the hull length this brief implies.

    Carried as DATA including its refusal: `delivery_route` raises
    `PolicyRefusal` for a craft the RCD does not define (a 26 m hull, a
    category the constitution does not admit), and a refusal is the answer —
    not an exception that empties the screen.
    """
    from navalai.policy import PolicyRefusal
    lh = body.get("hull_length_m")
    if lh is None:
        m = body.get("mission") or {}
        lh = m.get("lwl_hint_m")
    if lh is None:
        return {"mode": "UNKNOWN",
                "refusal": "no hull length is stated yet, and the module "
                           "routing is a function of length and category — "
                           "so there is no route to render, not a default one"}
    try:
        r = cp.delivery_route(float(lh),
                              str(body.get("category") or "C").upper())
    except (PolicyRefusal, Exception) as exc:                   # noqa: BLE001
        return {"mode": "REFUSED", "refusal": str(exc)}
    return r.as_dict() if hasattr(r, "as_dict") else dict(r)


def _refold_bar() -> float:
    # `navalai.limits` is the ONE home of a bar. Reading it here rather than
    # writing 5.0 into a payload is the whole point of that rule.
    from navalai import limits
    return float(limits.REFOLD_BAR_MM)


# ---------------------------------------------------------------------------
# envelope — the compiled parameter box
# ---------------------------------------------------------------------------

def envelope_payload(body: dict) -> dict:
    """The governance kernel's box, and every move that made it.

    This is the screen `docs/BUILDER-UX.html` §01 calls "the one place a novice
    sees the machine think". The measured case for it is the strongest number
    in the project: ungoverned sampling gave roundness > 0 on 60 of 60 draws
    and the unroller refused all 60; with the box, 30 of 30 unrolled.
    """
    from navalai import policy as P
    cat = str(body.get("category") or "C").upper()
    try:
        cp = P.reference_policy()
    except Exception as exc:                                    # noqa: BLE001
        return {"source": "refused", "reason": f"constitution: {exc}"}
    box = cp.box(cat)
    lo0, hi0 = grammar.LOW, grammar.HIGH
    names = list(box.names)
    shrink = 1.0
    for i, _n in enumerate(names):
        base = float(hi0[i] - lo0[i])
        now = float(box.high[i] - box.low[i])
        if base > 0:
            shrink *= max(now / base, 1e-9)
    return {
        "source": "measured",
        "category": cat,
        "names": names,
        "ungoverned_low": [float(v) for v in lo0],
        "ungoverned_high": [float(v) for v in hi0],
        "low": [float(v) for v in box.low],
        "high": [float(v) for v in box.high],
        "edits": [{"param": e.param, "edge": e.edge, "was": float(e.was),
                   "now": float(e.now), "source": e.source}
                  for e in box.edits],
        "rows": list(cp.rows),
        "all_row_names": list(P.ROW_NAMES),
        "disclaimer": cp.disclaimer,
        # PU-7: the legal stage RENDERS this route, it does not compute a
        # second one. `policy/legal.py` already holds OWN_USE_KIT, the
        # five-year Art. 2(2)(a)(vii) embargo and the Art. 19(4) resale
        # clause; a second routing in the UI would be the same clause decided
        # twice, and the two copies would drift the first time one was edited.
        "route": _route(cp, body),
        # volume ratio of the box, reported as a fraction of the ungoverned
        # hyper-box. It is a geometric fact about the bounds, not a claim about
        # how many designs are legal.
        "volume_fraction": shrink,
        "volume_note": "product of per-parameter span ratios — a fact about "
                       "the BOUNDS, not a count of designs",
    }


# ---------------------------------------------------------------------------
# geometry — the viewport
# ---------------------------------------------------------------------------

def mesh_payload(body: dict) -> dict:
    """Hull geometry for the viewport, at the fidelity the caller asks for.

    The two-rate loop (PU-2) is a CLIENT decision, so the server exposes both
    rates and declares what each cost. `fast` is panel_mesh (measured 1.66 ms),
    `fine` is closed_mesh (49.75 ms). The unroller is NOT reachable from here —
    at 869 ms it is export-time only, and it lives on /api/buildability behind
    an explicit user action.
    """
    params = body.get("params", {})
    fid = str(body.get("fidelity") or "fast")
    t0 = time.perf_counter()
    h = _hull(params)
    if fid == "fine":
        V, F = h.closed_mesh()
    else:
        V, F = h.panel_mesh()
    keel, chine, sheer = h.edge_curves()
    wl = body.get("waterline_z")
    out = {
        "source": "measured",
        "fidelity": fid,
        "verts": [[round(float(c), 4) for c in v] for v in V],
        "faces": [[int(i) for i in f] for f in F],
        "edges": {"keel": _jsonable(keel), "chine": _jsonable(chine),
                  "sheer": _jsonable(sheer)},
        "waterline_z": (float(wl) if wl is not None else None),
        "gen_ms": round((time.perf_counter() - t0) * 1e3, 2),
    }
    return out


def sections_payload(body: dict) -> dict:
    """Body-plan stations: the blueprint view. Real offsets, not a sketch.

    `Hull.section(i)` is indexed by STATION, not by x — the hull carries its
    own station abscissae in `hull.x`, and inventing an x-grid here would
    resample a curve the kernel already discretised.
    """
    params = body.get("params", {})
    n = int(body.get("n", 11))
    h = _hull(params)
    lwl = float(grammar.named(_vector(params))["LWL"])
    ns = int(h.n_stations)
    idx = sorted({int(round(v)) for v in
                  np.linspace(0, ns - 1, max(3, min(n, ns)))})
    secs = []
    for i in idx:
        try:
            pts = h.section(int(i))
        except Exception:                                       # noqa: BLE001
            continue
        secs.append({"i": int(i), "x": round(float(h.x[i]), 4),
                     "pts": _jsonable(pts)})
    return {"source": "measured", "lwl": lwl, "n_stations": ns,
            "sections": secs,
            "keel": _jsonable(np.column_stack([h.x, h.z_keel])),
            "chine": _jsonable(np.column_stack([h.x, h.y_chine, h.z_chine])),
            "sheer": _jsonable(np.column_stack([h.x, h.y_sheer, h.z_sheer])),
            "sac": _jsonable(np.column_stack([h.x, h.A_sac]))}


# ---------------------------------------------------------------------------
# stability — the capsize check
# ---------------------------------------------------------------------------

def capsize_payload(body: dict) -> dict:
    """Large-angle stability, on demand.

    NOT a live light. The curve floats the hull at 16 heels by bisection and
    costs about a second, and a light that lags a slider by a second is a light
    that lies for a second.
    """
    from navalai.hydrostatics import GZ_ASSUMPTIONS, gz_curve
    params = body.get("params", {})
    mission = _mission(body.get("mission"))
    t0 = time.perf_counter()
    ev = evaluate(_vector(params), mission)
    if ev.hydro is None or ev.masses is None:
        return {"source": "refused",
                "reason": "the hull does not float at this displacement, so "
                          "there is no equilibrium to heel from"}
    h = _hull(params)
    # KG IS MEASURED FROM THE KEEL PLANE, AND `MassAggregate.vcg_m` IS NOT.
    # The mass model's VCG is in hull coordinates, where z = 0 is the design
    # waterline and the keel sits at -T, so handing `vcg_m` straight to
    # `gz_curve` reads the lever from the wrong datum. MEASURED while wiring
    # this endpoint: it produced KG = -0.02 m — a centre of gravity BELOW the
    # keel — and the whole curve turns on that lever. `evaluate` itself calls
    # `agg.vcg_above_keel(t_design)` at line 794 and this must be the same
    # conversion, not a second one.
    t_design = float(grammar.named(_vector(params))["T"])
    try:
        kg = float(ev.masses.vcg_above_keel(t_design))
    except Exception as exc:                                    # noqa: BLE001
        return {"source": "refused",
                "reason": f"no KG available from the mass model ({exc}), and "
                          f"KG is the lever the whole curve turns on"}
    if not math.isfinite(kg):
        return {"source": "refused", "reason": "KG is not finite"}
    try:
        gz = gz_curve(h, float(ev.hydro.disp_kg), kg,
                      trim_deg=float(ev.trim_deg or 0.0),
                      tcg_m=float(getattr(ev.masses, "tcg_m", 0.0) or 0.0))
    except Exception as exc:                                    # noqa: BLE001
        return {"source": "refused", "reason": str(exc)}
    return {"source": "measured",
            "elapsed_ms": round((time.perf_counter() - t0) * 1e3, 1),
            "kg_above_keel_m": round(kg, 4),
            "curve": _jsonable(gz),
            "assumptions": list(GZ_ASSUMPTIONS)
            if not isinstance(GZ_ASSUMPTIONS, str) else [GZ_ASSUMPTIONS]}


# ---------------------------------------------------------------------------
# buildability — the route verdict (PU-4) and the cut file
# ---------------------------------------------------------------------------

def refold_payload(body: dict) -> dict:
    """PU-4: the route verdict reads the TREND, never one station count.

    MEASURED 2026-08-21 and it retracted a hull this project had already
    called buildable: n=41 -> 4.92 mm, n=81 -> 5.22 mm, n=161 -> 8.71 mm —
    RISING, so NON_DEVELOPABLE. A shortfall that FALLS under refinement is the
    41-station polyline's sagitta (a measurement artefact); one that RISES is
    double curvature (a property of the boat). Only the second is a reason to
    change the hull. A hull with Gaussian curvature 7.8e-14 reads 17.1 mm at
    n=41 and 1.5 mm at n=321.
    """
    from navalai import unroll
    params = body.get("params", {})
    counts = tuple(int(c) for c in (body.get("counts") or (41, 81, 161)))
    t0 = time.perf_counter()
    try:
        rc = unroll.refold_convergence(_vector(params), counts=counts)
    except Exception as exc:                                    # noqa: BLE001
        return {"source": "refused", "reason": str(exc),
                "elapsed_ms": round((time.perf_counter() - t0) * 1e3, 1)}
    d = _jsonable(rc)
    d["source"] = "measured"
    d["elapsed_ms"] = round((time.perf_counter() - t0) * 1e3, 1)
    d["route"] = ("kit" if rc.verdict == "PASSES" else
                  "search" if rc.verdict == "REFINING" else "mould")
    d["verdict_meaning"] = {
        "PASSES": "every station count clears the bar — this is a flat-pack kit",
        "REFINING": "the shortfall FALLS under refinement, so part of it is "
                    "the polyline's sagitta rather than the surface. Refine "
                    "before routing to a mould.",
        "NON_DEVELOPABLE": "the shortfall RISES under refinement — genuine "
                           "double curvature. The panels will not lie flat.",
        "REFUSED": "the shell is not a two-panel developable pairing at all "
                   "(a radiused bilge cannot be cut from flat sheet).",
    }.get(rc.verdict, "")
    return d


def buildability_payload(body: dict) -> dict:
    """Panels, strakes, the nested sheet layout and the BOM — from ONE nest.

    MEASURED ~4.5 s on the reference hull, so this is an explicit user action
    and never part of the slider loop.

    It calls `engineer.assess`, which returns `layout` AND `parts` AND `bom`
    off a single nesting. Re-deriving the layout from the panels here is the
    exact defect `EngineerReport.layout` was added to prevent: MEASURED
    2026-08-21, rebuilding the parts from the shell panels alone produced a
    DXF with 84 outlines against a BOM of 186 sheet-good parts — 102 parts the
    builder is told to cut were not drawn.

    The ladder's own `ply_thickness_m` is PASSED IN rather than left to the
    nominal stock sheet, because the two derivations have already disagreed:
    the delivered BOM was cut to 18.0 mm while the same ladder run charged the
    boat 15.0 mm of structure.
    """
    from navalai import engineer, unroll
    params = body.get("params", {})
    t0 = time.perf_counter()
    h = _hull(params)
    try:
        panels = unroll.hull_panels(h)
    except Exception as exc:                                    # noqa: BLE001
        # The unroller refusing IS the answer, and it is the last honest
        # moment: this same refusal measured 19 of 19 on an ungoverned front.
        return {"source": "refused", "reason": str(exc),
                "at": "unroll.hull_panels",
                "elapsed_ms": round((time.perf_counter() - t0) * 1e3, 1)}
    mission = _mission(body.get("mission"))
    ev = evaluate(_vector(params), mission)
    thick = (float(ev.ply_thickness_m)
             if ev.ply_thickness_m and math.isfinite(ev.ply_thickness_m)
             else None)
    # EITHER the ladder's derived scantling OR a mass for `assess` to derive
    # one from — NEVER both. `engineer.assess` refuses both by name, and it is
    # right to: two sources for one thickness is how the delivered BOM came to
    # be cut to 18.0 mm while the ladder charged the boat 15.0 mm.
    kw = ({"bottom_thickness_m": thick} if thick is not None
          else {"mldc_kg": (float(ev.masses.total_kg)
                            if ev.masses is not None else None)})
    try:
        rep = engineer.assess(h, **kw)
    except Exception as exc:                                    # noqa: BLE001
        return {"source": "refused", "reason": str(exc), "at": "engineer.assess",
                "elapsed_ms": round((time.perf_counter() - t0) * 1e3, 1)}
    layout = None
    lay = getattr(rep, "layout", None)
    if lay is not None and getattr(lay, "placements", None):
        sheets = sorted({pl.sheet for pl in lay.placements})
        # `Placement.part` is the part's NAME, not the Part. Thickness is
        # looked up from the SAME nest's parts rather than re-derived, so a
        # sheet drawn 15 mm cannot end up on a 18 mm bin in the BOM.
        thick_by = {p.name: float(p.thickness_m) for p in (rep.parts or ())}
        layout = {
            "sheet_w": float(lay.sheet_w), "sheet_l": float(lay.sheet_l),
            "n_sheets": len(sheets),
            "utilisation": float(rep.nest_utilisation),
            "utilisation_note": "sheet count is COUNTED off this layout, "
                                "never estimated from area",
            "placements": [{"part": str(pl.part), "sheet": int(pl.sheet),
                            "x": round(float(pl.x), 4),
                            "y": round(float(pl.y), 4),
                            "w": round(float(pl.w), 4),
                            "h": round(float(pl.h), 4),
                            "rotated": bool(pl.rotated),
                            "thickness_mm": (
                                round(thick_by[str(pl.part)] * 1e3, 1)
                                if str(pl.part) in thick_by else None)}
                           for pl in lay.placements],
        }
    return {
        "source": "measured",
        "elapsed_ms": round((time.perf_counter() - t0) * 1e3, 1),
        "ply_thickness_m": thick,
        "ply_thickness_basis": "derived by the rules tier from ISO 12215-5 and "
                               "passed IN to the BOM, so the cut sheet and the "
                               "charged structural mass are one number",
        "bottom_thickness_mm": float(rep.bottom_thickness_mm),
        "panels": [{"name": p.name, "dev_error_rel": float(p.dev_error_rel),
                    "twist_max": float(p.twist_max),
                    "twist_median": float(p.twist_median),
                    "rulings": p.rulings} for p in panels],
        "summary": {"panel_count": int(rep.panel_count),
                    "bulkheads": int(rep.bulkheads),
                    "frames": int(rep.frames),
                    "panel_area_m2": float(rep.panel_area_m2),
                    "ply_sheets": int(rep.ply_sheets),
                    "epoxy_kg": float(rep.epoxy_kg),
                    "interior_volume_m3": float(rep.interior_volume_m3),
                    "build_hours": float(rep.build_hours),
                    "sheet_area_m2": float(rep.sheet_area_m2),
                    "basis": rep.basis},
        "bom": [{"part": b.part, "qty": int(b.qty), "material": b.material,
                 "thickness_mm": float(b.thickness_mm),
                 "area_m2": round(float(b.area_m2), 4),
                 "source_panel": b.source_panel,
                 "sheet": (int(b.sheet) if b.sheet is not None else None),
                 "note": b.note} for b in rep.bom],
        "layout": layout,
        "missing_from_bom": [ABSENT["bom_consumables"], ABSENT["cost_model"]],
    }


# ---------------------------------------------------------------------------
# analysis — speed sweep with the Froude guard
# ---------------------------------------------------------------------------

def speedsweep_payload(body: dict) -> dict:
    """Resistance / power / range against speed, with the model's own refusal
    drawn as a refusal.

    The thin-ship model is valid to Fn 0.45. Past it we do not extrapolate and
    we do not fade a curve out: the point is REFUSED by name, because
    `docs/research/SMALL-CRAFT-REGIMES.md` records that no model in this tree
    covers the semi-displacement band and there is no Savitsky-class model at
    all.
    """
    from navalai.constants import G_STANDARD
    params = body.get("params", {})
    mission = _mission(body.get("mission"))
    x = _vector(params)
    lwl = float(grammar.named(x)["LWL"])
    kn = body.get("speeds_kn")
    if not kn:
        kn = [round(0.5 * i, 1) for i in range(2, 41)]
    pts = []
    for v_kn in kn:
        u = float(v_kn) * 0.514444
        fn = u / math.sqrt(G_STANDARD * lwl)
        if fn > 0.45:
            pts.append({"kn": float(v_kn), "fn": round(fn, 4),
                        "state": "REFUSED",
                        "reason": "Fn %.2f is past the thin-ship limit 0.45; "
                                  "no model in this tree covers it" % fn})
            continue
        m2 = dataclasses.replace(mission, cruise_speed_kn=float(v_kn))
        try:
            ev = evaluate(x, m2)
        except Exception as exc:                                # noqa: BLE001
            pts.append({"kn": float(v_kn), "fn": round(fn, 4),
                        "state": "REFUSED", "reason": str(exc)})
            continue
        r = ev.resistance
        e = ev.energy
        pts.append({
            "kn": float(v_kn), "fn": round(fn, 4), "state": "OK",
            "rt_n": round(float(r.total), 2),
            "rw_n": round(float(r.rw), 2),
            "rf_n": round(float(r.rf), 2),
            "sigma_rt_n": round(float(r.uncertainty), 2),
            "power_w": round(float(e.prop_power_w), 1),
            "wh_per_nm": round(float(e.wh_per_nm), 1),
            "sigma_wh_per_nm": round(float(e.sigma_wh_per_nm), 1),
            "trim_deg": (round(float(ev.trim_deg), 3)
                         if ev.trim_deg is not None else None),
            "regime": r.regime, "valid": bool(r.valid),
        })
    return {"source": "measured", "lwl_m": lwl, "froude_ceiling": 0.45,
            "points": pts,
            "breakdown_note": "rw is wave-making (Michell thin-ship), rf is "
                              "friction (ITTC-57 with a form factor). The "
                              "split is the MODEL's, not a fitted one."}


# ---------------------------------------------------------------------------
# validation — gates, ledger, benchmarks, CFD receipts
# ---------------------------------------------------------------------------

def gates_payload() -> dict:
    """Gate status, and the thing this screen must never do.

    A gate's verdict comes from RUNNING its suite (~4 min), so this endpoint
    does not claim one. It serves three real things: the gate table, the
    expected-red ledger verbatim, and the fact that no suite was run in this
    request. A green dot because a page loaded is exactly the dishonesty the
    ledger exists to prevent.
    """
    import navalai.gates as GT
    rows = [{"name": n, "scope": s, "suite": suite}
            for (n, s, suite) in GT.gate_rows()]
    led_path = _ROOT / "data" / "gate-ledger.json"
    ledger: dict = {}
    try:
        raw = json.loads(led_path.read_text())
        for k, v in raw.items():
            if k.startswith("_") or not isinstance(v, dict):
                continue
            ledger[k] = {
                "metric": v.get("metric"),
                "watermark": v.get("watermark"),
                "units": v.get("units"),
                "bar": v.get("bar"),
                "better_is": v.get("better_is"),
                "measured_utc": v.get("measured_utc"),
                "measured_on": v.get("measured_on"),
                "owner": v.get("owner"),
                "verify": v.get("verify"),
                "review_by": v.get("review_by"),
                "why_red": v.get("why_red"),
            }
    except Exception as exc:                                    # noqa: BLE001
        return {"source": "refused", "reason": f"ledger unreadable: {exc}"}
    return {
        "source": "measured",
        "gates": rows,
        "ledger": ledger,
        "suite_run": False,
        "suite_note": "no suite was run to build this page. A gate's verdict "
                      "comes from `python -m navalai.gates`, which runs the "
                      "tests; the rows below are the DEFINITIONS and the "
                      "expected-red ledger, not live verdicts.",
        "how_to_verify": "source ~/.venvs/naval/bin/activate && "
                         "python -m navalai.gates --ledger "
                         "data/gate-ledger.json",
    }


def validation_payload() -> dict:
    """Benchmark provenance: reference, condition, what we hold, what we do not.

    PHYSICS CONFIDENCE, never "AI confidence 94%". Four registers:
    VALIDATED (reproduced against experiment), CALIBRATED (fitted to data),
    EXTRAPOLATED (outside the anchor's envelope), UNVALIDATED (no anchor).
    """
    out: list[dict] = []

    # --- KCS: solver verification only, and the scope line matters ---------
    try:
        from benchmarks import kcs
        out.append({
            "id": "KCS",
            "title": "KRISO Container Ship — RANS solver verification",
            "confidence": "EXTRAPOLATED",
            "reference": "Tokyo 2015 CFD Workshop; KRISO EFD",
            "kind": "experiment + CFD",
            "conditions": {
                "Lpp_m": float(kcs.LPP),
                "Fn": float(kcs.DESIGN_FN),
                "Re": float(kcs.DESIGN_RE),
                "speed_ms": float(kcs.DESIGN_SPEED),
                # KCS Case 2.1 is towed FREE to sink and trim; the solver runs
                # FIXED. Stating the EFD attitude here is what makes that
                # difference visible rather than a footnote.
                "EFD_sinkage_m": _f(kcs.EFD.get("sinkage_m")),
                "EFD_trim_deg": _f(kcs.EFD.get("trim_deg")),
            },
            "reference_value": {"name": "C_T",
                                "value": _f(kcs.EFD.get("ct")), "unit": "-"},
            "scatter_band": [float(v) for v in kcs.scatter_band()],
            "our_value": None,
            "scope_warning":
                "SOLVER VERIFICATION ONLY. A 230 m container ship shares no "
                "chine, transom or spray physics with a 10 m plywood boat. "
                "Gate 2M going green would not be small-craft validation.",
            "gate": "Gate 2M",
        })
    except Exception as exc:                                    # noqa: BLE001
        out.append({"id": "KCS", "confidence": "UNVALIDATED",
                    "error": str(exc)})

    # --- DSYHS: real hulls, real friction band ----------------------------
    try:
        from benchmarks import dsyhs
        pts = dsyhs.friction_band_points()
        out.append({
            "id": "DSYHS",
            "title": "Delft Systematic Yacht Hull Series — friction line "
                     "against 51 real hulls",
            "confidence": "VALIDATED",
            "reference": "Delft Systematic Yacht Hull Series",
            "kind": "experiment",
            "conditions": {"Fn_band": [float(v)
                                       for v in dsyhs.FRICTION_BAND_FN]},
            "reference_value": {"name": "friction fraction (median)",
                                "value": float(dsyhs.FRICTION_FRACTION_MEDIAN),
                                "unit": "-"},
            "n_points": len(pts) if hasattr(pts, "__len__") else None,
            "scope_warning":
                "keeled sailing yachts. The band's edge is an INSTRUMENT "
                "limit, not a model failure — see docs/research/.",
            "gate": "Gate 2C",
        })
    except Exception as exc:                                    # noqa: BLE001
        out.append({"id": "DSYHS", "confidence": "UNVALIDATED",
                    "error": str(exc)})

    # --- Wigley: analytic, so it verifies the CODE not the physics ---------
    try:
        from benchmarks import wigley
        out.append({
            "id": "WIGLEY",
            "title": "Wigley parabolic hull — Michell integral against the "
                     "closed form",
            "confidence": "VALIDATED",
            "reference": "analytic Michell solution",
            "kind": "analytic",
            "conditions": {"L/B": float(wigley.L_OVER_B),
                           "B/T": float(wigley.B_OVER_T)},
            "reference_value": {"name": "Cw", "value": None, "unit": "-"},
            "tolerance": {"converged": float(wigley.ANALYTIC_TOL_CONVERGED),
                          "production": float(wigley.ANALYTIC_TOL_PRODUCTION)},
            "scope_warning":
                "an ANALYTIC check: it proves our integral is the Michell "
                "integral. It says nothing about whether thin-ship theory "
                "describes a hard-chine plywood boat.",
            "gate": "Gate 2-PHYS-B",
        })
    except Exception as exc:                                    # noqa: BLE001
        out.append({"id": "WIGLEY", "confidence": "UNVALIDATED",
                    "error": str(exc)})

    # --- Holtrop: printed worked cases ------------------------------------
    try:
        from benchmarks import holtrop_cases
        out.append({
            "id": "HOLTROP",
            "title": "Holtrop-Mennen worked cases from the printed paper",
            "confidence": "CALIBRATED",
            "reference": "Holtrop & Mennen, printed worked examples",
            "kind": "published regression",
            "conditions": {},
            "not_implemented": list(getattr(holtrop_cases,
                                            "NOT_IMPLEMENTED", ()) or ()),
            "not_verified": list(getattr(holtrop_cases,
                                         "NOT_VERIFIED", ()) or ()),
            "scope_warning":
                "a statistical regression over merchant ships. Outside its "
                "own population it is an extrapolation, and the envelope "
                "violations are reported per-evaluation.",
            "gate": "Gate 2-PHYS-*",
        })
    except Exception as exc:                                    # noqa: BLE001
        out.append({"id": "HOLTROP", "confidence": "UNVALIDATED",
                    "error": str(exc)})

    # --- the hole, declared as a first-class row --------------------------
    out.append({
        "id": "HARD-CHINE",
        "title": "Hard-chine planing/semi-displacement resistance at Fn 0.26",
        "confidence": "UNVALIDATED",
        "reference": "candidate: Compton (1986) USNA hard-chine series",
        "kind": "absent",
        "conditions": {},
        "scope_warning": ABSENT["hardchine_anchor"]["why"],
        "unblocked_by": ABSENT["hardchine_anchor"]["unblocked_by"],
        "gate": None,
    })
    return {"source": "measured", "benchmarks": out,
            "confidence_model": {
                "VALIDATED": "reproduced against an experiment we hold, "
                             "inside its envelope",
                "CALIBRATED": "fitted to data; honest inside the fit's "
                              "population",
                "EXTRAPOLATED": "the anchor exists but this craft is outside "
                                "its envelope",
                "UNVALIDATED": "no anchor. Not a low score — an absent one.",
            }}


def cfd_cases_payload() -> dict:
    """Real OpenFOAM case receipts off disk. Nothing simulated here.

    A case is listed with what its OWN receipt says. `settled` is not asserted:
    a run below 1.0 flow-throughs has not been crossed by the free stream and
    still holds its initial condition, and `docs/research/CFD.md` records a run
    that printed `settled: yes` on 3.3% drift at 0.70 flow-throughs while the
    pressure part swung 2.6x underneath it.
    """
    runs = _ROOT / "runs"
    if not runs.is_dir():
        return {"source": "absent", "reason": "no runs/ directory on this "
                                              "machine", "cases": []}
    cases = []
    for info in sorted(runs.glob("*/case.info")):
        d: dict[str, str] = {}
        try:
            for line in info.read_text().splitlines():
                if "=" in line and not line.startswith(" "):
                    k, _, v = line.partition("=")
                    d[k.strip()] = v.strip()
        except Exception:                                       # noqa: BLE001
            continue
        ft = d.get("end_time_flow_throughs")
        try:
            ftv = float(ft)
        except (TypeError, ValueError):
            ftv = None
        cases.append({
            "name": info.parent.name,
            "benchmark": d.get("benchmark", "unknown"),
            "lwl_m": _f(d.get("lwl")),
            "speed_ms": _f(d.get("speed_ms")),
            "cells_bg": _f(d.get("cells_bg")),
            "cells_per_wavelength": _f(d.get("cells_per_wavelength")),
            "n_layers": _f(d.get("n_layers")),
            "first_layer_m": _f(d.get("first_layer_m")),
            "symmetric": d.get("symmetric"),
            "free_motion": d.get("free_motion"),
            "flow_throughs": ftv,
            "flow_throughs_raw": ft,
            "domain_length_m": _f(d.get("domain_length_m")),
            "state": ("UNDER-RUN" if (ftv is not None and ftv < 1.0)
                      else "SETTLING-UNVERIFIED" if ftv is not None and ftv < 5.0
                      else "RECEIPT ONLY"),
        })
    return {
        "source": "measured", "n": len(cases), "cases": cases,
        "bars": {"flow_throughs_floor": 1.0,
                 "flow_throughs_settled": 5.0,
                 "cells_per_wavelength": 20.0},
        "note": "these are RECEIPTS written at mesh time. A force history is "
                "not read here and no C_T is claimed: scripts/gate2m.py is "
                "the only thing in this tree allowed to print that verdict, "
                "and it refuses one it cannot support.",
    }


def _f(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _ff(v):
    """A non-finite quantity is a REFUSAL, not a number (honesty rule 1).
    `evaluate.non_developable_frac` is NaN when the meter could not run, and
    NaN is not valid JSON either (RFC 8259) — it was once emitted raw."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


# ---------------------------------------------------------------------------
# search — the autonomous mode, and it is a REAL search
# ---------------------------------------------------------------------------

_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
MAX_JOBS = 8


def _mission(mission_d: dict | None) -> MissionSpec:
    import ui.server as S
    return S._mission_from(mission_d)


def search_start(body: dict) -> dict:
    """A governed sweep over the real ladder, with every rejection NAMED.

    This is the "AI optimization" screen's data source and it is deliberately
    NOT dressed up as evolution. MEASURED and recorded in `docs/BUILD-PLAN.md`
    §PU-3: only 3 of 400 random draws clear the 5 mm refold bar, and the recipe
    that works is a large seed sweep (most candidates die in `grammar.check` at
    0.27 ms) followed by a refine. So the sweep is the honest primitive: every
    candidate is evaluated through the SAME `evaluate()` the sliders call, and
    a design that dies reports the constraint row that killed it.

    `docs/audit/PRODUCTION-READINESS.md` §2a measured NSGA-II at the server's
    live budget returning an EMPTY front for the panel's own default brief, and
    non-monotonically (480 -> 1 member, 800 -> 0). That is why the front stays
    on `/pareto`, declared, rather than being presented here as a converged
    result.
    """
    n = max(1, min(int(body.get("n", 200)), 5000))
    mission_d = body.get("mission")
    governed = bool(body.get("governed", True))
    seed = int(body.get("seed", 0))
    jid = uuid.uuid4().hex[:12]
    job = {"id": jid, "state": "RUNNING", "n": n, "done": 0,
           "governed": governed, "started": time.time(),
           "kept": [], "rejected_counts": {}, "rejections": [],
           "best": None, "cancel": False,
           "method": "governed uniform sweep over the compiled box, every "
                     "candidate through evaluate()" if governed else
                     "UNGOVERNED uniform sweep over grammar bounds"}
    with _JOBS_LOCK:
        while len(_JOBS) >= MAX_JOBS:
            _JOBS.pop(next(iter(_JOBS)))
        _JOBS[jid] = job
    threading.Thread(target=_search_run,
                     args=(job, mission_d, seed), daemon=True).start()
    return {"source": "measured", "job": jid, "n": n,
            "method": job["method"]}


def _search_run(job: dict, mission_d: dict | None, seed: int) -> None:
    try:
        mission = _mission(mission_d)
        rng = np.random.default_rng(seed)
        lo, hi = np.asarray(grammar.LOW, float), np.asarray(grammar.HIGH, float)
        if job["governed"]:
            try:
                from navalai import policy as P
                box = P.reference_policy().box(
                    getattr(mission, "design_category", "C") or "C")
                lo, hi = np.asarray(box.low, float), np.asarray(box.high, float)
            except Exception:                                   # noqa: BLE001
                pass
        for i in range(job["n"]):
            if job["cancel"]:
                job["state"] = "CANCELLED"
                return
            x = lo + rng.random(lo.size) * (hi - lo)
            chk = grammar.check(x)
            if not chk.ok:
                _reject(job, "grammar",
                        "; ".join(chk.violations) or "grammar refused the draw",
                        x)
                job["done"] = i + 1
                continue
            try:
                ev = evaluate(x, mission)
            except Exception as exc:                            # noqa: BLE001
                _reject(job, "evaluate-raised", str(exc), x)
                job["done"] = i + 1
                continue
            if not ev.ok:
                worst = None
                if isinstance(ev.g, dict) and ev.g:
                    worst = max(ev.g.items(), key=lambda kv: kv[1])[0]
                _reject(job, worst or "unknown",
                        "; ".join(ev.violations) or "constraint violated", x)
            else:
                rec = {"params": {k: round(float(v), 5)
                                  for k, v in grammar.named(x).items()},
                       "wh_per_nm": round(float(ev.energy.wh_per_nm), 1),
                       "gm_m": (round(float(ev.gm_m), 3)
                                if ev.gm_m is not None else None),
                       "disp_kg": round(float(ev.hydro.disp_kg), 1)
                       if ev.hydro else None,
                       "rt_n": round(float(ev.resistance.total), 1)}
                job["kept"].append(rec)
                if (job["best"] is None
                        or rec["wh_per_nm"] < job["best"]["wh_per_nm"]):
                    job["best"] = rec
            job["done"] = i + 1
        job["state"] = "DONE"
    except Exception as exc:                                    # noqa: BLE001
        job["state"] = "FAILED"
        job["error"] = str(exc)
    finally:
        job["elapsed_s"] = round(time.time() - job["started"], 2)


def _reject(job: dict, row: str, why: str, x) -> None:
    job["rejected_counts"][row] = job["rejected_counts"].get(row, 0) + 1
    if len(job["rejections"]) < 60:
        job["rejections"].append({
            "row": row, "why": why[:240],
            "params": {k: round(float(v), 4)
                       for k, v in grammar.named(x).items()}})


def search_status(body: dict) -> dict:
    jid = str(body.get("job", ""))
    job = _JOBS.get(jid)
    if job is None:
        return {"source": "refused", "reason": "no such job"}
    kept = job["kept"]
    return {
        "source": "measured",
        "id": job["id"], "state": job["state"], "method": job["method"],
        "n": job["n"], "done": job["done"],
        "n_kept": len(kept), "n_rejected": job["done"] - len(kept),
        "rejected_counts": dict(job["rejected_counts"]),
        "rejections": job["rejections"][-30:],
        "best": job["best"],
        "kept": kept[-40:],
        "elapsed_s": job.get("elapsed_s",
                             round(time.time() - job["started"], 2)),
        "error": job.get("error"),
    }


def search_cancel(body: dict) -> dict:
    job = _JOBS.get(str(body.get("job", "")))
    if job is None:
        return {"source": "refused", "reason": "no such job"}
    job["cancel"] = True
    return {"source": "measured", "id": job["id"], "state": "CANCELLING"}


# ---------------------------------------------------------------------------
# digital twin — one assembled record, every field naming its producer
# ---------------------------------------------------------------------------

def twin_payload(body: dict) -> dict:
    """Everything known about ONE design, assembled from the modules that own
    each part. No field is computed here; this endpoint is a JOIN, so it cannot
    become a second home for a number."""
    params = body.get("params", {})
    mission = _mission(body.get("mission"))
    x = _vector(params)
    ev = evaluate(x, mission)
    named = grammar.named(x)
    derived = {}
    if ev.hydro is not None:
        h = ev.hydro
        derived = {
            "displacement_kg": float(h.disp_kg), "draft_m": float(h.draft),
            "volume_m3": float(h.volume), "lcb_m": float(h.lcb),
            "lcf_m": float(h.lcf), "kb_m": float(h.kb), "bm_m": float(h.bm),
            "bm_l_m": float(h.bm_l), "awp_m2": float(h.awp),
            "wetted_m2": float(h.wetted), "cb": float(h.cb),
            "cp": float(h.cp), "b_wl_max_m": float(h.b_wl_max),
            "lwl_eff_m": float(h.lwl_eff),
            "freeboard_min_m": float(h.freeboard_min),
        }
    return {
        "source": "measured",
        "genome": {"fixed": {}, "mutable": named,
                   "derived": derived,
                   "note": "MUTABLE is the 16-parameter grammar the search may "
                           "move. DERIVED is computed by the hydrostatics tier "
                           "from the floated hull and is not editable — an "
                           "editable-looking derived field is a lie about "
                           "which way causality runs."},
        "mission": json.loads(mission.to_json()),
        "constraints": {"names": list(ev.g_names),
                        "g": {k: float(v) for k, v in ev.g.items()},
                        "convention": "g <= 0 is satisfied; the value is the "
                                      "normalised margin, so 0 is exactly at "
                                      "the limit",
                        "ok": bool(ev.ok),
                        "violations": list(ev.violations)},
        "badges": {k: {"tier": v[0], "sigma": float(v[1]), "basis": v[2]}
                   for k, v in (ev.badges or {}).items()},
        "weights": ({"items": [{"id": it.id, "mass_kg": float(it.mass_kg),
                                "sigma_kg": float(it.sigma_kg),
                                "tier": it.tier, "x_m": float(it.x_m),
                                "y_m": float(getattr(it, "y_m", 0.0) or 0.0),
                                "z_m": float(it.z_m)}
                               for it in ev.masses.items],
                     "total_kg": float(ev.masses.total_kg),
                     "sigma_kg": float(ev.masses.sigma_kg),
                     "lcg_m": float(getattr(ev.masses, "lcg_m", 0.0) or 0.0),
                     "tcg_m": float(getattr(ev.masses, "tcg_m", 0.0) or 0.0),
                     "vcg_m": float(getattr(ev.masses, "vcg_m", 0.0) or 0.0),
                     "unaccounted_frac": _ff(ev.unaccounted_frac)}
                    if ev.masses is not None else None),
        "resistance": _jsonable(ev.resistance),
        "energy": _jsonable(ev.energy),
        "rules": _jsonable(ev.rules),
        "ply_thickness_m": _ff(ev.ply_thickness_m),
        # NaN here means UNMEASURABLE, not zero — `evaluate` sets it to NaN
        # deliberately so a receipt cannot read "0% non-developable" when the
        # meter could not run. It must reach the UI as null, never as 0.
        "non_developable_frac": _ff(ev.non_developable_frac),
        "seakeeping": _jsonable(ev.seakeeping),
        "cfd": _jsonable(ev.cfd),
        "tier": ev.tier,
        "eval_ms": round(float(ev.eval_ms), 2),
        "absent": ABSENT,
    }


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

_GET = {
    "/api/manifest": lambda: manifest_payload(),
    "/api/gates": lambda: gates_payload(),
    "/api/validation": lambda: validation_payload(),
    "/api/cfd/cases": lambda: cfd_cases_payload(),
}

_POST = {
    "/api/envelope": envelope_payload,
    "/api/mesh": mesh_payload,
    "/api/sections": sections_payload,
    "/api/capsize": capsize_payload,
    "/api/refold": refold_payload,
    "/api/buildability": buildability_payload,
    "/api/speedsweep": speedsweep_payload,
    "/api/search/start": search_start,
    "/api/search/status": search_status,
    "/api/search/cancel": search_cancel,
    "/api/twin": twin_payload,
}


def handle_get(path: str):
    fn = _GET.get(path)
    return None if fn is None else fn()


def handle_post(path: str, body: dict):
    fn = _POST.get(path)
    return None if fn is None else fn(body or {})
