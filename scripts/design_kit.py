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
from navalai.policy import reference_policy
from navalai.translate import translate

MISSION = ("6 tonne solar-electric liveaboard, 10 m, Danube and Black Sea "
           "coastal, cruise 5 knots, 2 crew, 40 kWh battery")

# The measured agreement point of the table in this module's docstring.
POP, GENS = 64, 80


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="design_kit")
    ap.add_argument("--mission", default=MISSION)
    ap.add_argument("--out", default="data/exports/kit")
    ap.add_argument("--pop", type=int, default=POP)
    ap.add_argument("--gens", type=int, default=GENS)
    ap.add_argument("--seed", type=int, default=11)
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
    ev, x = min(scored, key=lambda t: t[0].energy.wh_per_nm)
    p = grammar.named(x)
    print(f"front {len(X)}; selected lowest-energy hull:")
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
