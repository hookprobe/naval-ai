# Small-craft design regimes — what is enabled, and what refuses by name

Router: `certify.mission_regime(mission)` → (regime, supported, why).
Rule (§16 of the screening directive, verbatim): **a regime is enabled only
when its reduced-order physics is implemented and tested in this tree.**
The router names the regime early; the resistance validity flags remain the
per-hull enforcement.

| Regime | Fn band (design Fn from the mission's length hint) | Status | Physics |
|---|---|---|---|
| SLENDER_DISPLACEMENT | ≤ 0.45, floated L/B ≥ 6 | **ENABLED** | Michell (θ-form, grid-converged) + ITTC-57 + Watanabe form factor (clamp reported as EXTRAPOLATED) |
| MODERATE_DISPLACEMENT | ≤ 0.45 | **ENABLED** | same |
| AUTONOMOUS_SLOW_CRUISE | ≤ 0.45, uncrewed | **ENABLED** | same + UNCREWED rule routing + PayloadSpec |
| SEMI_DISPLACEMENT | 0.45 – 0.65 | **NOT YET SUPPORTED** — refused by name | none in tree; adding one requires a sourced reduced-order model (e.g. a transcribed series), never an extended Michell |
| PLANING | > 0.65 | **NOT YET SUPPORTED** — refused by name | none in tree (Savitsky is NOT implemented; do not imply it) |

Notes:
- The 0.65 planing onset is a conventional practice figure used only to
  NAME which unsupported regime a mission asked for; it gates nothing.
- Catamarans in the enabled regimes get interference-aware resistance and
  measured GZ evidence, but their **stability verdict stays REFUSED** until
  the governing criterion's windage clause is declarable (see
  `docs/L1_DESIGN_CERTIFICATION.md`).
- A mission with no length hint has no design Fn; it is routed to the
  displacement regime and judged per-hull by the validity flags.
