"""APSE end-to-end demo: python scripts/demo_apse.py

Shows the five pieces on the project's own KCS numbers — no OpenFOAM needed.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai import extrapolate, fidelity, planner, similitude
from navalai.evidence import EvidenceGraph, EvidenceTier, Kind
from navalai.fidelity import Budget, FidelitySpec
from navalai.planner import Belief
from navalai.similitude import Condition

KCS_EFD_CT = 3.711e-3
SHIP = Condition(230.0, 0.26 * math.sqrt(9.80665 * 230.0),
                 *similitude.SEA_WATER_15C, label="KCS ship")
MODEL = Condition(7.2786, 2.196, *similitude.FRESH_WATER_15C, label="KCS model")


def rule(t: str) -> None:
    print(f"\n\033[1m{t}\033[0m\n" + "-" * len(t))


rule("1. Geometric scale is not a cost variable")
for lwl in (2.3, 7.2786, 230.0):
    c = Condition(lwl, 0.26 * math.sqrt(9.80665 * lwl))
    cost = fidelity.estimate(c, FidelitySpec())
    print(f"  Lwl {lwl:8.3f} m   Re {c.re:9.3e}   "
          f"{cost.cells:,} cells   {cost.timesteps:,} steps   "
          f"{cost.wall_hours:6.2f} h")
print("  same mesh, same steps, same wall clock — 1000x of Reynolds thrown away")

rule("2. Scale effects, stated rather than hidden")
print(similitude.scale_effects(SHIP, MODEL).report())
tiny = similitude.scale_effects(Condition(10.0, 3.0), Condition(10.0, 3.0).at_scale(200.0))
print(f"\n  a 1:200 model of a 10 m dayboat -> admissible = {tiny.admissible}")
for w in tiny.warnings:
    print(f"    - {w}")

rule("3. ITTC-78: KCS model C_T 3.711e-3 -> ship")
s_m = 9.4379
p = extrapolate.ittc78(MODEL, SHIP, KCS_EFD_CT, s_m, s_m * (230.0 / 7.2786) ** 2,
                       form_k=0.10, sigma_ct_model=0.05 * KCS_EFD_CT)
print(p.report())
print("\n  form-factor sanity:")
for k in (0.10, 0.27):
    cr, verdict = extrapolate.residuary_check(MODEL, KCS_EFD_CT, k)
    print(f"    (1+k) = {1 + k:.2f}: {verdict}")

rule("4. Cost, and what the machine will refuse")
for d in (0.5, 0.7071, 1.0, 1.414, 2.0):
    ok, refusals, cost = fidelity.admit(MODEL, FidelitySpec(mesh_density=d),
                                        fidelity.MAC_M5)
    print(f"  density {d:6.4f}  {cost.cells:8,} cells  {cost.wall_hours:7.2f} h  "
          f"{'ADMIT' if ok else 'REFUSE'}")
    for r in refusals:
        print(f"      {r.reason}")
spec, _ = fidelity.cheapest_admissible(MODEL, fidelity.MAC_M5)
print(f"  cheapest admissible on this Mac: density {spec.mesh_density:.4f}"
      if spec else "  nothing fits this Mac")
print("  seiche: " + fidelity.seiche_check(MODEL, FidelitySpec())[2])

rule("5. The planner: which experiment, and is it needed at all")
for q, priors in [
    ("initial stability", {"gm": Belief("gm", 0.8, 0.4),
                           "displacement": Belief("displacement", 6000.0, 900.0)}),
    ("calm-water resistance", {"resistance": Belief("resistance", 4000.0, 2000.0)}),
]:
    print(planner.plan_for(q, priors, target_sigma_rel=0.12,
                           budget=Budget(max_wall_s=72 * 3600, max_ram_gb=64.0,
                                         np_procs=10)).report())
    print()

rule("6. Design Evidence Graph")
g = EvidenceGraph()
# Every node declares its tier — there is no default. A requirement and a
# decision are choices, not measurements, so NA is the honest answer and the
# only one the kind admits; the experiment declares the fidelity it was run at
# and the evidence declares what the number is worth.
g.add("req", Kind.REQUIREMENT, "hold 25 kn at 6 t displacement",
      tier=EvidenceTier.NA)
g.add("dec", Kind.DECISION, "raise L/B to 9.5", tier=EvidenceTier.NA)
g.add("exp", Kind.EXPERIMENT, "L3 RANS @ density 1.0, 3.2 h",
      tier=EvidenceTier.L3)
g.add("ev", Kind.EVIDENCE, "R_T = 4.10 kN", value=4100.0, sigma=620.0,
      tier=EvidenceTier.L3, confidence=0.85)
g.add("asm", Kind.ASSUMPTION, "appendage drag is 4% of bare hull",
      tier=EvidenceTier.NA, confidence=0.60)
g.add("dec2", Kind.DECISION, "transom immersion 0.40 m", tier=EvidenceTier.NA)
for s, t in (("req", "dec"), ("exp", "ev"), ("ev", "dec"), ("asm", "dec"),
             ("req", "dec2")):
    g.support(s, t)
print(g.explain("dec"))
print("\n  decisions resting on no evidence:")
for n in g.unsupported():
    print(f"    - {n.text}")

print("\n  the vocabulary is closed, and it separates computed from observed:")
for bad, why in (
    (dict(node_id="ev_typo", kind=Kind.EVIDENCE, text="R_T from the tank",
          tier="CFD"), "a tier nobody defined"),
    (dict(node_id="dec_launder", kind=Kind.DECISION, text="raise L/B to 9.5",
          tier=EvidenceTier.L3), "a decision wearing a solve's authority"),
):
    try:
        g.add(**bad)
    except ValueError as e:
        print(f"    REFUSED ({why}): {e}")
try:
    g.add("trial", Kind.EXPERIMENT, "sea trial, hull 004", tier=EvidenceTier.M1)
    g.add("ev_sim", Kind.EVIDENCE, "R_T = 4.10 kN as measured", value=4100.0,
          sigma=310.0, tier=EvidenceTier.L3)
    g.support("trial", "ev_sim")
except ValueError as e:
    print(f"    REFUSED (an observation relabelled as a solve): {e}")
