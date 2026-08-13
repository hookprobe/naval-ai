"""End-to-end demo: one mission sentence -> a validated hull with provenance.

python3 scripts/demo_mission.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from navalai import db, grammar
from navalai.evaluate import evaluate
from navalai.optimize import pareto_front
from navalai.rules import report
from navalai.rules.iso12215 import assess as scantling
from navalai.rules.iso12217 import assess as stability
from navalai.engineer import assess as engineer_assess
from navalai.seakeeping import heave_coeffs
from navalai.translate import grade, requirements_from_mission, translate

MISSION = ("6 tonne solar-electric liveaboard, 10 m, Danube and Black Sea "
           "coastal, cruise 5 knots, 2 crew, 40 kWh battery")


def main() -> None:
    print(f"MISSION: {MISSION}\n")
    m = translate(MISSION)
    print(f"spec: {m.displacement_target_kg:.0f} kg, {m.cruise_speed_kn} kn, "
          f"category {m.design_category}, battery {m.energy.battery_kwh} kWh\n")

    print("NSGA-II over the grammar (pop 24 x 10 gens) ...")
    res = pareto_front(m, pop=24, gens=10, seed=11)
    scores = [(evaluate(x, m), x) for x in res.X]
    scores = [(ev, x) for ev, x in scores if ev.ok and ev.energy]
    ev, x = min(scores, key=lambda t: t[0].energy.wh_per_nm)
    p = grammar.named(x)
    print(f"front size {len(res.X)}; selected lowest-energy hull:")
    print(f"  LWL {p['LWL']:.2f} m · BWL {p['BWL']:.2f} m · T {p['T']:.2f} m · "
          f"deadrise {p['beta_mid']:.1f}°  Cp {p['Cp']:.3f}\n")

    print("L1 physics (tier-badged):")
    print(f"  displacement {ev.hydro.disp_kg:.0f} kg | GM {ev.gm_m:.2f} m | "
          f"freeboard {ev.hydro.freeboard_min:.2f} m")
    print(f"  Rt {ev.resistance.total:.0f}±{ev.resistance.uncertainty:.0f} N @ "
          f"{m.cruise_speed_kn} kn (Fn {ev.resistance.fn:.2f})")
    print(f"  {ev.energy.wh_per_nm:.0f} Wh/NM | solar {ev.energy.solar_kwh_day:.1f} "
          f"kWh/day | solar-only range {ev.energy.range_solar_nm_day:.0f} NM/day\n")

    reqs = grade(ev, requirements_from_mission(m))
    print(f"mission requirements: {reqs['passed']}/{reqs['total']} pass")
    for r in reqs["requirements"]:
        print(f"  [{'PASS' if r['pass'] else 'FAIL'}] {r['name']}: {r['detail']}")

    # mLDC is the LOADED DISPLACEMENT, not the weight budget — feeding the
    # budget (2769 kg where the boat floats at 6004 kg) under-specified the
    # bottom panel by 8%. And the provided thickness is the DERIVED sheet the
    # ladder actually built with; this line used to hand-pass 20.0 mm, a number
    # that appeared nowhere else and was the only value that made R-TBM pass.
    rr = report(stability(ev, m.design_category, m.crew, p["BWL"])
                + scantling(ev.hydro.disp_kg,
                            provided_mm=ev.ply_thickness_m * 1e3))
    print(f"\nrules tier R ({rr['disclaimer']}): {rr['passed']}/{rr['total']} pass")
    for f in rr["findings"]:
        print(f"  [{'PASS' if f['passed'] else 'FAIL'}] {f['rule_id']} "
              f"{f['measured']:.2f}/{f['required']:.2f} {f['unit']} — {f['clause']}")

    print("\nL2 spot-check (Capytaine heave, 3 freqs, coarse):")
    from navalai.geometry import Hull
    am, dp, nb = heave_coeffs(Hull(x), np.array([0.8, 1.5, 2.5]), nx=24, nz=6)
    print(f"  {nb} panels; added mass {am.round(0)} kg; damping {dp.round(0)} N·s/m")

    # MANUFACTURING TAIL. The demo used to END at provenance, which meant the
    # script a reader runs to judge the project stopped one clause short of the
    # project's own headline claim -- "...before it exports as build-ready
    # geometry". The capability was never missing: agents.run_plm reaches it
    # because engineer imports unroll. The DEMONSTRATION was missing, and a
    # reader who runs the demo concludes the manufacturing tail does not exist.
    # Recorded in docs/BUILD-PLAN.md section 4.4 as the cheaper of that audit's
    # two findings.
    print("\nmanufacturing (tier: derived from the VALIDATED hull):")
    rep = engineer_assess(Hull(x), wl=ev.wl, mldc_kg=ev.hydro.disp_kg)
    print(f"  {rep.panel_count} developable panels, {rep.bulkheads} bulkheads, "
          f"{rep.frames} frames")
    print(f"  {rep.ply_sheets} ply sheets ({rep.panel_area_m2:.1f} m2 panel area, "
          f"nest utilisation {rep.nest_utilisation * 100:.1f}%)")
    print(f"  {rep.epoxy_kg:.1f} kg epoxy; build estimate {rep.build_hours:.0f} h "
          f"(basis={rep.basis})")
    print(f"  BOM: {len(rep.bom)} line items")

    prov = db.Provenance("data/navalai.sqlite3")
    evaluate(x, m, provenance=prov)
    hid = db.hull_id(x)
    print(f"\nprovenance: hull {hid} + L1 results recorded in data/navalai.sqlite3")


if __name__ == "__main__":
    main()
