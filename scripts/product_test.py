#!/usr/bin/env python3
"""PRODUCT TEST — can NavalAI turn a real mission into a boat, or say why not?

ROUND 3 §5/§28/§40/§41. The suite answers "is this module right?"; the gate
ladder answers "is this bar met?". Neither answers the question a product has
to answer:

    given a mission a customer would actually type, what comes out, and
    where do the candidates that do NOT come out die?

So this runs the missions end to end through the SAME functions the
application calls, and prints a SURVIVAL FUNNEL — the count surviving each
stage — plus the family coherence checks and every refusal reason. A stage
where most candidates die is the next product-development problem, and that is
the output this script exists to produce.

WHAT IT WILL NOT DO. It does not lower a bar to improve a number, does not
drop hard missions, and does not special-case any hull. A mission that cannot
be met must appear as a REFUSAL WITH A REASON, which is a product outcome and
not a failure of the harness.

    python scripts/product_test.py                # every mission
    python scripts/product_test.py --mission P2   # one
    python scripts/product_test.py --n 100        # funnel width
    python scripts/product_test.py --json out.json
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from navalai import grammar                                  # noqa: E402
from navalai.evaluate import evaluate                        # noqa: E402
from navalai.geometry import Hull                            # noqa: E402
from navalai.mission import parse_mission                    # noqa: E402


#: The product's own briefs, in the customer's words. P7 is expected to be
#: REFUSED — a product that cannot say no is not a product.
MISSIONS: dict[str, tuple[str, str]] = {
    "P1": ("10 m recreational boat with an inboard, 7 knots, 3 tonne, "
           "category C, inland waters",
           "simple displacement monohull"),
    "P2": ("16 m x 4.5 m liveaboard houseboat, 5 knots, 6 tonne, category C, "
           "4 berths, coastal and inland",
           "coastal houseboat"),
    "P3": ("14 m catamaran, 8 knots, 7 tonne, category C, 4 berths",
           "catamaran"),
    "P4": ("13 m river cruiser with a protected prop, 6 knots, 5 tonne, "
           "category C",
           "tunnel-stern vessel"),
    "P5": ("9 m hard chine plywood launch, 7 knots, 2.5 tonne, category C",
           "hard-chine / sheet-built"),
    "P6": ("15 m wave piercing cruiser, 9 knots, 6 tonne, category C",
           "wave-piercing"),
    "P7": ("30 m submarine, 40 knots, 500 tonne, category A",
           "IMPOSSIBLE — must be refused with a reason"),
}

#: The funnel's stages, in the order a candidate meets them.
STAGES = ("generated", "L0 valid", "floats", "hydrostatics ok",
          "propulsion ok", "morphology ok", "all rows ok", "buildable",
          "mesh-closed", "CFD-admissible")


def _family_of_mission(m) -> str | None:
    return getattr(m, "hull_family", None)


def funnel(brief: str, n: int, seed: int = 5) -> dict:
    """Drive `n` candidates from one brief and count where they die."""
    out: dict = {"brief": brief, "n": n}
    t0 = time.perf_counter()
    m = parse_mission(brief)
    out["parsed"] = {
        "displacement_target_kg": m.displacement_target_kg,
        "cruise_speed_kn": m.cruise_speed_kn, "lwl_hint_m": m.lwl_hint_m,
        "bwl_hint_m": m.bwl_hint_m, "design_category": m.design_category,
        "hull_family": m.hull_family, "crew": m.crew, "berths": m.berths,
        "drive": m.energy.drive, "motor_kw": m.energy.motor_kw,
        "topology": getattr(getattr(m, "vessel", None), "topology", None),
        "notes": m.notes,
        "features_requested": sorted(grammar.features_for(m)),
    }
    counts = collections.Counter()
    deaths = collections.Counter()
    survivors = []

    # THE DRAW IS THE PRODUCTION FEED, not a hand-picked set: `sample_valid`
    # with the exploring stream is what `ui/server.py` fits its generator on.
    # Anything else would be measuring a distribution the product never uses.
    from navalai.evaluate import MissionInfeasible, sample_valid
    try:
        X, _y = sample_valid(n, m, seed=seed, explore_post_hoc=True)
        X = np.asarray(X, float)
    except MissionInfeasible as e:
        # THE PRODUCT SAYING NO IS A RESULT, not a harness failure. P7 exists
        # to reach this branch; a mission that cannot be met must arrive here
        # with its reasons rather than hanging or returning a plausible hull.
        out["refused"] = str(e)
        out["refusal_tally"] = e.refusals
        out["elapsed_s"] = round(time.perf_counter() - t0, 1)
        return out
    except Exception as e:                                   # noqa: BLE001
        out["fatal"] = (f"the feed raised something other than a refusal: "
                        f"{type(e).__name__}: {e}")
        out["elapsed_s"] = round(time.perf_counter() - t0, 1)
        return out

    # `sample_valid` returns only hulls that already clear L0 and reach L1, so
    # the funnel's first two rows are the FEED's own yield and are recorded as
    # such rather than implied.
    counts["generated"] = len(X)
    counts["L0 valid"] = len(X)

    for x in X:
        ev = evaluate(x, m)
        if ev.hydro is None:
            deaths["floatation"] += 1
            continue
        counts["floats"] += 1
        counts["hydrostatics ok"] += 1
        g = ev.g
        prop_ok = all(g.get(k, 1.0) <= 0 for k in ("motor_power", "prop_space"))
        counts["propulsion ok"] += prop_ok
        shape_ok = g.get("shape", 1.0) <= 0
        counts["morphology ok"] += shape_ok
        if not ev.ok:
            # MEASURED VIOLATIONS OUTRANK UNMEASURABLE ROWS. `Evaluation.
            # worst_row` is the one statement of that rule — a raw max over
            # `g` names the INFEASIBLE_G sentinel every time, and MEASURED
            # 2026-09-01 that reported 10 of 25 candidates as dying on
            # `list` when every one of them had NEGATIVE GM and the heel
            # angle was not a number at all.
            measured, unmeasurable = ev.binding_rows()
            worst = ev.worst_row()
            deaths[f"row:{worst}" if worst else "refused (no row)"] += 1
            for k in unmeasurable:
                deaths[f"unmeasurable:{k}"] += 0   # keep the key visible
            continue
        counts["all rows ok"] += 1
        survivors.append(x)

    # the expensive stages run only on survivors — that is the product's own
    # ordering and measuring it any other way would price a funnel nobody runs
    routes = collections.Counter()
    for x in survivors:
        hull = Hull(x)
        # BUILDABILITY IS A ROUTE, NOT A PASS/FAIL -- and this harness got
        # that wrong until 2026-09-01. It called `shell_complexity`, which is
        # a GEOMETRY METRIC defined only on the two-strip ruled surface and
        # so REFUSES any hull with roundness > 0 by design, and it labelled
        # that refusal "not sheet-developable". Result: `buildable = 0` on
        # ALL SEVEN missions, printed as though NavalAI could not deliver a
        # manufacturable boat for any brief. It can: 6 of 6 sampled hulls
        # route `mould`, and a mould boat is a boat. The instrument had
        # committed the mislabelled-metric defect it exists to catch.
        #
        # `kit_buildability` is the meter that actually answers the question,
        # and it answers with a ROUTE. Both routes are counted, because the
        # product metric is "did a mission yield a buildable design", not
        # "did it yield a CNC kit".
        try:
            from navalai import buildability
            route = buildability.kit_buildability(hull)["route"]
            counts["buildable"] += 1
            routes[route] += 1
        except Exception as e:                               # noqa: BLE001
            deaths[f"buildability: {type(e).__name__}"] += 1
        try:
            from navalai.geometry import open_edge_count
            V, F = hull.closed_mesh(nx=80, nz=16)
            if open_edge_count(V, F) == 0:
                counts["mesh-closed"] += 1
            else:
                deaths["mesh: surface does not close"] += 1
        except Exception as e:                               # noqa: BLE001
            deaths[f"mesh: {type(e).__name__}"] += 1
        try:
            from navalai.certify import certify
            cc = certify(x, m, with_gz=False).cfd_candidate
            if cc.get("eligible"):
                counts["CFD-admissible"] += 1
            else:
                deaths["cfd: not decision-worthy"] += 1
        except Exception as e:                               # noqa: BLE001
            deaths[f"certify: {type(e).__name__}"] += 1

    # THE PRODUCT'S OWN DESIGN ROUTE IS A SEARCH, NOT A SAMPLER -- and this
    # harness measured only the sampler until 2026-09-01, which made it
    # report a product failure that was really a statement about uniform
    # draws.
    #
    # MEASURED, same three briefs, pop=48 gens=30 seed=0:
    #
    #     brief          sample_valid (40 draws)   pareto_front
    #     P1 monohull        3 all-rows-ok             48
    #     P4 tunnel          0 all-rows-ok             41  (tun_w 0.065)
    #     P5 plywood         2 all-rows-ok             45
    #
    # P4 -- "13 m river cruiser with a protected prop" -- reads 0 of 40 from
    # the feed and 41 designs from the optimizer, WITH a drawn tunnel. A
    # uniform draw is not the instrument for a brief whose feasible set is
    # a thin sliver of the box; the search is. Reporting only the feed's
    # yield as "mission -> valid design rate" would have libelled the
    # product on the strength of the wrong instrument.
    try:
        from navalai.optimize import pareto_front
        _r = pareto_front(m, pop=48, gens=30, seed=0)
        _X = getattr(_r, "X", None)
        out["optimizer_front"] = 0 if _X is None else len(np.atleast_2d(_X))
        if not out["optimizer_front"]:
            out["optimizer_why_empty"] = str(_r.why_empty())[:200]
    except Exception as e:                                   # noqa: BLE001
        out["optimizer_front"] = None
        out["optimizer_error"] = f"{type(e).__name__}: {e}"

    out["funnel"] = {s: int(counts[s]) for s in STAGES}
    out["deaths"] = dict(deaths.most_common())
    out["survivors"] = len(survivors)
    out["routes"] = dict(routes.most_common())
    out["elapsed_s"] = round(time.perf_counter() - t0, 1)
    return out


def coherence(brief: str) -> dict:
    """§25/§26 — the families must AGREE, and a mismatch is a routing defect.

    The recent UI defect (a catamaran served the monohull pool) was exactly a
    family that agreed in the JSON and disagreed in the code path. This asks
    each layer what family it thinks it is designing.
    """
    from navalai import morphology, parents
    m = parse_mission(brief)
    got: dict = {"mission_family": _family_of_mission(m)}
    vessel = getattr(m, "vessel", None)
    got["mission_topology"] = getattr(getattr(vessel, "topology", None),
                                      "value", None) or str(
                                          getattr(vessel, "topology", None))
    got["hull_role"] = getattr(grammar.hull_role(vessel), "name", None)
    try:
        sel = parents.select_parents(m)
        got["parent_family"] = [p.name for p in sel] or None
    except Exception as e:                                   # noqa: BLE001
        got["parent_family"] = f"{type(e).__name__}: {e}"
    got["critic_band"] = ("family-specific"
                          if (_family_of_mission(m) or "").lower()
                          in morphology._FAMILY_BAR else "general")
    got["features_requested"] = sorted(grammar.features_for(m))
    # the RESISTANCE model's own idea of the vessel
    from navalai.evaluate import sample_valid
    try:
        X, _y = sample_valid(1, m, seed=3, explore_post_hoc=True)
        ev = evaluate(np.asarray(X, float)[0], m)
        got["ladder_topology"] = ev.vessel.get("topology")
        got["ladder_n_hulls"] = ev.vessel.get("n_hulls")
        got["stability_criterion"] = ev.vessel.get("stability_criterion")
        got["resistance_models"] = ev.vessel.get("models_admitted")
    except Exception as e:                                   # noqa: BLE001
        got["ladder_topology"] = f"{type(e).__name__}: {str(e)[:80]}"
    return got


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="product_test")
    ap.add_argument("--mission", action="append",
                    help="run only these (P1..P7); repeatable")
    ap.add_argument("--n", type=int, default=40,
                    help="candidates per mission (default 40)")
    ap.add_argument("--json", help="write the full result here")
    args = ap.parse_args(argv)

    keys = args.mission or list(MISSIONS)
    results: dict = {}
    print("PRODUCT TEST — mission in, boat or reason out")
    print("=" * 78)
    for k in keys:
        brief, what = MISSIONS[k]
        print(f"\n{k} — {what}\n    {brief}")
        r = funnel(brief, args.n)
        r["what"] = what
        r["coherence"] = coherence(brief)
        results[k] = r
        p = r["parsed"]
        print(f"    parsed: {p['displacement_target_kg']:.0f} kg, "
              f"{p['cruise_speed_kn']:.1f} kn, L {p['lwl_hint_m']}, "
              f"B {p['bwl_hint_m']}, cat {p['design_category']}, "
              f"family {p['hull_family']!r}, drive {p['drive']!r}, "
              f"motor {p['motor_kw']} kW, features {p['features_requested']}")
        if r.get("fatal"):
            print(f"    FATAL: {r['fatal']}")
            continue
        if r.get("refused"):
            print(f"    REFUSED (this is the correct outcome for P7):")
            print(f"      {r['refused'][:300]}")
            continue
        f = r["funnel"]
        prev = None
        for s in STAGES:
            v = f[s]
            drop = "" if prev is None else f"  (-{prev - v})" if prev > v else ""
            print(f"      {s:18s} {v:5d}{drop}")
            prev = v
        if r.get("optimizer_front") is not None:
            print(f"      SEARCH (pareto_front, the product's own design "
                  f"route): {r['optimizer_front']} designs")
        if r.get("routes"):
            print("      build route: "
                  + ", ".join(f"{k} x{v}"
                              for k, v in sorted(r["routes"].items())))
        if r["deaths"]:
            print("    where they died:")
            for why, n in list(r["deaths"].items())[:8]:
                print(f"      {n:5d}  {why}")
    print("\n" + "=" * 78)
    print("SUMMARY — mission -> valid design rate")
    print(f"{'':4s} {'what':28s} {'gen':>5s} {'rows ok':>8s} "
          f"{'buildable':>10s} {'meshes':>7s} {'CFD-adm':>8s} {'SEARCH':>7s}")
    for k in keys:
        r = results[k]
        if r.get("fatal"):
            print(f"{k:4s} {r['what'][:28]:28s}   FATAL")
            continue
        if r.get("refused"):
            print(f"{k:4s} {r['what'][:28]:28s}   REFUSED WITH REASONS (correct)")
            continue
        f = r["funnel"]
        print(f"{k:4s} {r['what'][:28]:28s} {f['generated']:5d} "
              f"{f['all rows ok']:8d} {f['buildable']:10d} "
              f"{f['mesh-closed']:7d} {f['CFD-admissible']:8d} "
              f"{('n/a' if r.get('optimizer_front') is None else r['optimizer_front']):>7}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(results, indent=1,
                                                      default=str))
        print(f"\n-> {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
