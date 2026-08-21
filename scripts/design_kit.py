"""GOVERNED design lane: a mission sentence -> a hull a builder can cut.

    python scripts/design_kit.py --mission "..." --out data/exports/kit1

WHAT THIS IS, AND WHY IT IS NOT `demo_mission.py`. It is the first entry point
in this repository that COMPILES A CONSTITUTION and hands it to the search.
Until 2026-08-21 every non-test caller of `reference_policy`/`compile_policy`
was a docstring: Gate V3.0 was implemented, tested and wired to nothing, so the
legal envelope and the design DNA governed nothing that shipped.

The consequence was measured, and it is the reason this file exists. The
reference constitution has declared the CNC sheet-goods kit path since it was
written -- the shell is cut flat, bent and stitched, never laid into a mould --
and the search never saw it. On the flagship mission:

    ungoverned: roundness > 0 on 60 of 60 draws (median 0.541)
                `unroll.hull_panels` REFUSED 60 of 60
    governed  : roundness 0 on 30 of 30, unroll ACCEPTED 30 of 30

The ungoverned product was searching, validating, badging and RANKING a design
space that is entirely unbuildable in the one material it is made of, and
finding out at the shop door.

STITCH AND GLUE is what `construction=sheet-developable` means concretely:
flat plywood panels, edge-drilled and wired together, filleted and taped on the
seams, then sheathed in epoxy and glass cloth. `engineer.assess` already
quantifies that sheathing (`epoxy_kg`, EPOXY_KG_PER_M2 = 1.4 approx). The
geometric precondition is DEVELOPABILITY -- a flat sheet bends but does not
stretch, so a radiused bilge is not a two-panel developable shell, and
`roundness` must be 0. That is a BOUND on the search, not a filter after it.

THE SEARCH BUDGET IS NOT DECORATIVE. MEASURED on the flagship mission, front
size against budget:

    budget                governed, unbounded roundness    governed, bounded
    pop 24  x 10 gens                 3                            0
    pop 48  x 40 gens                28                           25
    pop 64  x 80 gens                62                           64

At the legacy demo's 24 x 10 a governed run returns an EMPTY front, which reads
as "no valid designs" when the truth is "the search was too short". The default
here is the budget at which the bounded and unbounded fronts agree. Lowering it
is a false economy that produces a confident wrong answer.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from navalai import grammar, unroll
from navalai.certify import certify
from navalai.cfd.case import hull_to_stl
from navalai.engineer import assess as engineer_assess
from navalai.evaluate import evaluate
from navalai.geometry import Hull
from navalai.optimize import pareto_front
from navalai.limits import REFOLD_BAR_MM
from navalai.policy import reference_policy
from navalai.translate import translate

MISSION = ("6 tonne solar-electric liveaboard, 10 m, Danube and Black Sea "
           "coastal, cruise 5 knots, 2 crew, 40 kWh battery")

# The measured agreement point of the table in this module's docstring.
POP, GENS = 64, 80


def _refine(x0, mission, policy, box, budget_s, seed):
    """(1+1)-ES on the AUTHORITATIVE refold meter, subject to the full ladder.

    Lexicographic: feasibility first, then refold. A step that breaks the
    ladder is never accepted, so the hull that comes out is a hull the ladder
    passed AND whose panels are measured to close — not a buildable shape that
    happens to sink, which is exactly what an unconstrained refold search
    returns (measured: 3.900 mm at GM -0.35 m, i.e. it capsizes).
    """
    lo = np.array(box.low, float)
    hi = np.array(box.high, float)
    width = hi - lo                 # EXACTLY zero on a pinned gene, on purpose:
                                    # an epsilon here puts roundness at 1e-13
                                    # and `hull_panels` refuses `> 0.0`
                                    # strictly — measured, it rejected 600 of
                                    # 600 draws.
    rng = np.random.default_rng(seed + 1)

    def score(x):
        try:
            if not grammar.check(x).ok:
                return (1e6, 1e6)
            ev = evaluate(x, mission, policy=policy)
            if not ev.ok or ev.energy is None:
                viol = sum(max(0.0, min(v, 1e3))
                           for v in (ev.g or {}).values())
                return (viol if viol > 0 else 1.0, 1e6)
            h = Hull(x)
            r = max(float(np.max(unroll.refold_surface_deviation_mm(h, pan)))
                    for pan in unroll.hull_panels(h))
            return (0.0, r)
        except Exception:
            return (1e6, 1e6)

    t0 = time.time()
    best, bx = score(np.asarray(x0, float)), np.asarray(x0, float).copy()

    # SEED PHASE, and it is not optional. MEASURED 2026-08-21, same mission,
    # same box, same refiner: seeded from the lowest-ENERGY front member
    # (refold 120.3 mm) it did not reach the bar in 900 s; seeded from the best
    # of a random sweep (refold 38.37 mm) it reached 4.952 mm in ~335 s.
    #
    # The seed dominates because the buildable region is TINY -- 3 of 400
    # random draws clear 5 mm -- and a local search started 120 mm away spends
    # its whole budget walking. Cheapest fix by far: sweep the box first on the
    # lexicographic score and start from the best point found, so the ES begins
    # inside the right basin instead of proving it can walk.
    sweep_s = min(0.35 * budget_s, 300.0)
    n_sweep = 0
    while time.time() - t0 < sweep_s:
        cand = lo + rng.random(len(lo)) * width
        s_ = score(cand)
        n_sweep += 1
        if s_ < best:
            best, bx = s_, cand
    print(f"    seed sweep: {n_sweep} draws, best "
          f"{'infeasible' if best[0] > 0 else f'{best[1]:.1f} mm'}")
    sigma = 0.10
    while time.time() - t0 < budget_s:
        cand = np.clip(bx + rng.normal(0, sigma, len(lo)) * width, lo, hi)
        s = score(cand)
        if s < best:
            best, bx, sigma = s, cand, min(sigma * 1.2, 0.25)
            if best[0] == 0.0 and best[1] <= REFOLD_BAR_MM:
                return bx, evaluate(bx, mission, policy=policy), best[1]
        else:
            sigma = max(sigma * 0.995, 0.004)
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="design_kit")
    ap.add_argument("--mission", default=MISSION)
    ap.add_argument("--out", default="data/exports/kit")
    ap.add_argument("--pop", type=int, default=POP)
    ap.add_argument("--gens", type=int, default=GENS)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--refine-s", type=float, default=900.0,
                    help="seconds of buildability refinement when no "
                         "front member unrolls within the bar")
    ap.add_argument("--no-refine", action="store_true",
                    help="skip refinement and report the refusal")
    ap.add_argument("--ungoverned", action="store_true",
                    help="compile NO constitution. Kept so the difference is "
                         "demonstrable rather than asserted -- it is not a "
                         "supported way to produce a kit")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    m = translate(a.mission)
    print(f"MISSION: {a.mission}")
    print(f"spec: {m.displacement_target_kg:.0f} kg, {m.cruise_speed_kn} kn, "
          f"category {m.design_category}")

    policy = None if a.ungoverned else reference_policy()
    if policy is None:
        print("\nCONSTITUTION: none (--ungoverned). The search is NOT bounded "
              "to buildable hulls and the kit stage is expected to refuse.")
    else:
        dna = policy.constitution.dna
        box = policy.box(m.design_category)
        j = box.names.index("roundness")
        print(f"\nCONSTITUTION: {policy.constitution.name}")
        print(f"  construction : {dna.construction.value}  -> shell must be "
              f"developable")
        print(f"  roundness box: [{box.low[j]:.3g}, {box.high[j]:.3g}]  "
              f"(grammar allows [0, 1])")
        print(f"  appended rows: {list(policy.rows)}")
        for e in box.edits:
            print(f"  bound        : {e.param} {e.edge} {e.was:.4g} -> "
                  f"{e.now:.4g}")

    print(f"\nNSGA-II under the box (pop {a.pop} x {a.gens} gens) ...")
    res = pareto_front(m, pop=a.pop, gens=a.gens, seed=a.seed, policy=policy)
    X = np.atleast_2d(res.X)
    if X.size == 0:
        print("EMPTY FRONT — no design satisfied the constraints. This is a "
              "REFUSAL, not a kit. Raise --pop/--gens before concluding the "
              "space is empty (see this module's docstring).")
        return 2
    scored = [(evaluate(x, m, policy=policy), x) for x in X]
    scored = [(ev, x) for ev, x in scored if ev.ok and ev.energy]
    if not scored:
        print("front returned but nothing passed the full ladder — REFUSED")
        return 2

    # ---- STAGE 2: VERIFY BUILDABILITY ON THE FRONT ------------------------
    #
    # Refold accuracy is the only thing that decides whether these panels can
    # be cut, and it CANNOT be a constraint inside NSGA-II: MEASURED, it costs
    # 2301 ms per hull against `grammar.check`'s 0.27 ms -- 8561x -- so a
    # pop-64 x 80-gen run would spend 3.3 hours on it.
    #
    # The obvious cheap proxy DOES NOT WORK and that is recorded here rather
    # than discovered again: `Hull.panel_twist_rate()` is 122319x cheaper and
    # correlates with refold at **+0.089** over 30 governed hulls (Spearman
    # +0.224). A criterion that does not separate is not a criterion.
    # `buildability.shell_complexity(...).non_developable_frac` DOES correlate
    # (+0.783) and costs 1.8 ms, which is ~9 s across a whole NSGA-II run --
    # that is the number to steer with if this is ever moved inside the search.
    #
    # So the front is verified with the AUTHORITATIVE meter instead: 64
    # members x 2.3 s = ~147 s, paid once. The product then delivers a hull
    # whose panels are MEASURED to close, or it refuses and says by how much.
    print(f"\nfront {len(X)}; verifying refold on {len(scored)} ladder-valid "
          f"member(s) (~{2.3 * len(scored):.0f} s) ...")
    verified = []
    refined = False
    best_miss = (float("inf"), None)
    for e, xx in scored:
        try:
            w = max(float(np.max(unroll.refold_surface_deviation_mm(Hull(xx), pan)))
                    for pan in unroll.hull_panels(Hull(xx)))
        except ValueError:
            continue
        if w <= REFOLD_BAR_MM:
            verified.append((e, xx, w))
        elif w < best_miss[0]:
            best_miss = (w, e)
    if not verified and not a.no_refine:
        # ---- STAGE 3: BUILDABILITY REFINEMENT ----------------------------
        #
        # This is the stage that makes the tool produce boats instead of
        # reporting that it cannot. NSGA-II optimises the mission; NOTHING in
        # its objectives or constraints is buildability, so it lands in the
        # buildable region only by accident. MEASURED on the flagship mission:
        #
        #     NSGA-II governed front          0 of N under the 5 mm bar
        #     400 random draws in the box     3 under the bar (0.75%)
        #     refold-targeted (1+1)-ES        FOUND ONE: 4.952 mm, GM +2.545 m,
        #                                     zero ladder violations
        #
        # So the search direction is the whole difference, and the ONLY meter
        # that can supply it is the authoritative one. Two cheap proxies were
        # measured and BOTH FAILED to separate, which is why this stage pays
        # 2.3 s a step instead of steering for free:
        #
        #     Hull.panel_twist_rate()   0.02 ms   r = +0.089
        #     shell_complexity().ndev   1.80 ms   r = +0.460 over N=400
        #         and at its most selective useful threshold (ndev <= 0.005)
        #         only 33% of hulls clear the bar, while the three measured
        #         passers span ndev 0.0019..0.0816 — so a bar tight enough to
        #         steer EXCLUDES TWO OF THE THREE KNOWN SOLUTIONS.
        #
        # A criterion that does not separate is not a criterion. Refinement on
        # the real meter is slower and it is the one that works.
        print(f"  no front member is buildable (best {best_miss[0]:.1f} mm) — "
              f"REFINING on the authoritative meter for up to "
              f"{a.refine_s:.0f} s ...")
        seed_ev, seed_x = min(scored, key=lambda t: t[0].energy.wh_per_nm)
        got = _refine(seed_x, m, policy, box, a.refine_s, a.seed)
        if got is not None:
            x, ev, worst_ok = got
            verified = [(ev, x, worst_ok)]
            refined = True
            print(f"  REFINED to {worst_ok:.2f} mm — buildable, ladder-valid")

    if not verified:
        print(f"  NO MEMBER of the front unrolls within {REFOLD_BAR_MM:.0f} mm."
              f" Best was {best_miss[0]:.1f} mm.")
        print("  REFUSED — this is Gate 6D, and a cut file is not produced.")
        # AND DO NOT SAY "RAISE THE BUDGET". That was this script's first
        # message here and it is WRONG: NSGA-II's objectives and constraints
        # contain no buildability term at all, so more generations search
        # harder for the same thing and never for this one. MEASURED — a
        # seaworthy hull at 4.952 mm refold, GM +2.545 m, zero ladder
        # violations, EXISTS in this grammar and was found by a dedicated
        # refold search, not by a longer NSGA-II run.
        print("  The space is NOT empty: a seaworthy hull at 4.952 mm refold "
              "with GM +2.545 m and zero violations was measured in this same "
              "governed box (2026-08-21).")
        print("  The search simply does not AIM at buildability — there is no "
              "such term in its objectives or constraints — so a bigger "
              "budget will not find it. What is owed is STEERING: "
              "buildability.shell_complexity(...).non_developable_frac "
              "correlates +0.783 with refold and costs 1.8 ms, i.e. ~9 s "
              "across a whole pop-64 x 80-gen run. Hull.panel_twist_rate() is "
              "cheaper still and does NOT work (+0.089).")
        return 3
    ev, x, worst_ok = min(verified, key=lambda t: t[0].energy.wh_per_nm)
    print(f"  {len(verified)}/{len(scored)} member(s) verified buildable; "
          f"selected one refolds to {worst_ok:.2f} mm")
    p = grammar.named(x)
    # NOT "selected lowest-energy hull" any more. When stage 3 runs, this hull
    # was REFINED and is not a member of the front at all -- saying otherwise
    # would be a label that survived the change beneath it, which is the defect
    # class this repository keeps catching.
    print(f"HULL ({'refined for buildability' if refined else 'selected from the front, lowest energy'}):")
    print(f"  LWL {p['LWL']:.2f} m · BWL {p['BWL']:.2f} m · T {p['T']:.2f} m "
          f"· deadrise {p['beta_mid']:.1f}° · roundness {p['roundness']:.4f}")
    print(f"  displacement {ev.hydro.disp_kg:.0f} kg | GM {ev.gm_m:.2f} m | "
          f"Rt {ev.resistance.total:.0f}±{ev.resistance.uncertainty:.0f} N | "
          f"{ev.energy.wh_per_nm:.0f} Wh/NM")

    hull = Hull(x)

    # --- the geometry a mesher / viewer sees -------------------------------
    stl = out / "hull.stl"
    sha = hull_to_stl(hull, stl, wl=ev.wl)
    print(f"\nSTL: {stl}  sha256 {sha[:16]}…")

    # --- the stitch-and-glue panels ----------------------------------------
    try:
        panels = unroll.hull_panels(hull)
    except ValueError as exc:
        print(f"\nKIT REFUSED: {exc}")
        print("This is the refusal the constitution exists to prevent. It is "
              "reported, not worked around.")
        return 3
    print(f"\nSTITCH AND GLUE: {len(panels)} developable panel(s)")
    # REPORTED AGAINST ITS BAR, because a millimetre figure with no bar beside
    # it reads as a pass. This is Gate 6D, which is RED and ledgered: the
    # two-sided distance from the REFOLDED panel back onto the hull's moulded
    # surface, against BuildPlan 12.3's 5 mm. A panel that misses by this much
    # is not yet a cut file a shop should trust.
    worst = 0.0
    for pan in panels:
        dev = float(np.max(unroll.refold_surface_deviation_mm(hull, pan)))
        worst = max(worst, dev)
        print(f"  {pan.name:12s} refold deviation max {dev:8.1f} mm "
              f"{'OK' if dev <= 5.0 else 'OVER the 5 mm bar'}")
    if worst > 5.0:
        print(f"  GATE 6D: worst {worst:.1f} mm against a 5 mm bar — RED, and "
              f"expected-red in data/gate-ledger.json. The panels below are "
              f"GEOMETRY, not yet a release-grade cut file.")

    # CONSUME the ladder's derived scantling; do NOT also pass mldc_kg.
    # `assess` refuses both, by name: two sources for one number is the defect
    # that parameter exists to close, and it caught this script on its first
    # run. The 2026-08-20 incident it guards is a BOM cut to 18.0 mm while the
    # same ladder run derived 15.0 mm.
    eng = engineer_assess(hull, wl=ev.wl,
                          bottom_thickness_m=ev.ply_thickness_m)
    print(f"\nKIT: {eng.ply_sheets} ply sheets, nest utilisation "
          f"{eng.nest_utilisation * 100:.1f}%")
    print(f"  bottom {eng.bottom_thickness_mm:.0f} mm (ISO 12215-5 derived)")
    print(f"  epoxy {eng.epoxy_kg:.0f} kg (sheathing + fillets + coats, "
          f"approx) · build {eng.build_hours:.0f} h")
    print(f"  BOM {len(eng.bom)} line items")

    cert = certify(x, m, policy=policy)
    (out / "certification.json").write_text(json.dumps({
        "mission": a.mission,
        "constitution": (None if policy is None
                         else policy.constitution.name),
        "params": [float(v) for v in x],
        "stl_sha256": sha,
        "verdict": getattr(cert, "verdict", None),
        "bom": [b.as_dict() for b in eng.bom],
    }, indent=1, default=str))
    print(f"\nwrote {out}/certification.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
