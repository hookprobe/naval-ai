# NavalAI — autonomous naval-architecture validation AI

Licensed under **GNU AGPL-3.0** (see `LICENSE`).

Mission in natural language → grammar-constrained hull generation → slider
surface with live physics → tiered validation ladder → rules gate → export.
Built to `NavalArchAI-BuildPlan.md` (research-grounded; 24 primary sources,
11 claims adversarially verified).

## The ladder

| Tier | What | Speed | Module |
|---|---|---|---|
| L0 | algebraic feasibility (30+ closed-form checks) | ~0.05 ms | `grammar.py` |
| L1 | hydrostatics · Michell+ITTC57 · energy/weight budget | ~20 ms | `hydrostatics.py` `resistance.py` `energy.py` |
| L2 | Capytaine BEM seakeeping (convergence-swept) | ~s–min | `seakeeping.py` |
| L3 | OpenFOAM interFoam resistance (case templates) | hrs | `cfd/` |
| R | ISO 12217 / 12215-5 subsets (assessment aid) | ~ms | `rules/` |

Surrogate spine (`surrogate.py`): ARD kriging + Kennedy–O'Hagan co-kriging,
batched-EI infill, OOD → ladder escalation. Generative (`generative.py`):
GMM family model + performance-conditioned sampling + 2-D latent map (guided
tabular diffusion is the planned drop-in upgrade behind the same interface).

## Honesty rules (enforced by tests, not vibes)

1. every quantity carries `{value, tier, sigma}` — no bare numbers
2. any kept design re-validates up the ladder; surrogates refuse OOD queries
3. the LLM translates missions and explains — it has **no code path to geometry**
4. retrained surrogates that degrade the frozen benchmark **never deploy**
5. rules output leads with `ASSESSMENT AID — NOT CERTIFICATION` and declares
   every approx-basis threshold

## Gate status (2026-08-05)

Run `python3 -m navalai.gates`. Summary:

| Gate | Scope | Status |
|---|---|---|
| 0 | grammar round-trip, L0 < 1 ms, DB reproducibility | GREEN (8 tests) |
| 1 | Wigley Michell anchor (band + humps + <2% grid conv), eval < 50 ms | GREEN (13) |
| 1b | NSGA-II Pareto, all designs re-validate | GREEN (1) |
| 2 | Capytaine wired: Hulme hemisphere 0.8310 anchor, convergence sweeps | GREEN (4) |
| 3 | co-kriging 2× vs kriging (Forrester); L1 GP ~10% median, calibrated | GREEN (5) |
| 4 | 100% feasible generation, conditioning wins, slider p95 < 100 ms | GREEN (6) |
| 5 | ≥90% mission briefs, hostile-LLM seam neutralised | GREEN (6) |
| 6 | rules mechanics: right verdicts flip, fails closed, clauses cited | GREEN (6) |
| 7 | flywheel: harvest → retrain → poisoned model refused | GREEN (4) |
| R3 | ladder is climbable: `revalidate()` to L2, monotone tier promotion, L3 refused with its operator route named | GREEN (8) |
| 2M | KCS/JBC OpenFOAM calibration, per-case GCI | **RED** — ran 2026-08-05 on the Mac: C_t 9.33e-3 vs EFD 3.711e-3 (−151%), outside the Tokyo-2015 scatter. Cause: 16.3% of wetted faces in the y+ band. Kept red. |
| 6R | ISO thresholds parity vs licensed standard text | **REVIEW-GATED** (qualified reviewer) |

## Run it

```bash
python3 -m pytest tests/ -q          # the whole ladder (~2.5 min)
python3 -m navalai.gates             # gate table
python3 ui/server.py                 # slider surface → http://127.0.0.1:8642
python3 benchmarks/wigley.py         # print the Michell Wigley curve
```

Deps: numpy, scipy, pymoo, capytaine, pytest (`pip install --user --break-system-packages ...`).

## Alignment campaign (stages B–F, see ALIGNMENT.md)

The original agentic-PLM plan was audited against the build; all 11 gaps
closed behind gates:

| Stage | Closed | Gate |
|---|---|---|
| B | grammar AST + typology type-checker · plywood bend-radius · 8-D pPCA genome | GREEN (11) |
| C | async agent network (Orchestrator/Builder/Validator/Engineer, audit trail) · engineer metrics · STEP/IGES export (CadQuery/OCP) | GREEN (7) |
| D | JONSWAP + heave-RAO response spectra · inertia/mooring/lifting + MuJoCo cross-check · CFD runner + forces parser + Roache GCI | GREEN (12) |
| E | NSGA-II over the 8-D genome · latent-GP (measured: 8-D costs 2–3× accuracy) | GREEN (3) |
| F | developable-panel unrolling → DXF · Pareto dashboard · handoff-latency receipt (<1% of physics) | GREEN (7) |

## What is deliberately NOT here yet

- guided tabular diffusion (GMM baseline stands in; same interface)
- LoRA-fine-tuned translator (rule floor + sanitising LLM seam stand in)
- OpenFOAM execution + Tokyo-2015 calibration (templates + runner + GCI
  post-processor ready and synthetic-tested; metal-gated)
- ES-TRIN checks, licensed-text ISO parity (declared approx bases)
