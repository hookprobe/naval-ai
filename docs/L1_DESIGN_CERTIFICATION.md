# L1 Design Certification — the pre-CFD screening engine

**Command:** `python -m navalai.design_report --case d` (or `--mission
"…brief…"`, `--json out.json`). Engine: `navalai/certify.py` (Gate DC).
Cost: a few seconds per design. **No CFD, no BEM, ever, in this layer.**

## What it answers

| Question | How | Verdict source |
|---|---|---|
| Plausible boat? | L0 grammar + Gate-PF descriptor bands | Evaluation + formcheck |
| Right boat for the mission? | targets receipt (target vs delivered Cp on the SOLVED equilibrium; LCB band) | `Evaluation.targets` |
| Displacement distribution sensible? | SAC descriptors, LCB/LCF, unimodality (Gate PF) | formcheck |
| Trim sensible? | solved (wl0, θ) equilibrium + 2° bar + loading matrix trims | hydrostatics |
| Efficient in its valid regime? | validity-banded speed curve, Wh/NM with propagated σ | resistance + energy |
| Multihull arrangement sensible? | parallel-axis GM, interference-aware Rt, GZ peak/collapse, clauses (a)/(b) measured | hydrostatics |
| Stable? | monohull: GM floor + reported GZ curve (max, AVS, area, deck edge). Multihull: **REFUSED by construction** with measured evidence | gz_curve |
| Buildable? | shell/deck/build areas, structure mass, non-developable fraction, twist, Gaussian curvature, fairness — PRELIMINARY, not scantlings | buildability |
| Drone-suitable? | PayloadSpec end-to-end (positioned mass, hotel draw, loading states) | mission + evaluate |
| Worth CFD? | `cfd_candidate` score (single-design factors; population factors live in the dataset layer) | certify |

## The classification

- **ACCEPT** — evaluation ok, regime supported, delivered-Cp conformant,
  cruise point VALID, margins comfortable.
- **MARGINAL** — ok but: a constraint within 5% of its bar, delivered Cp
  off-target, cruise TRANSITION/EXTRAPOLATED, or resistance σ > 35%.
- **REFUSE** — any ladder violation, an unsupported regime (named), or an
  unassessable governing criterion (multihull stability — measured (a)/(b)
  ride along as evidence).
- **CFD-worthiness** is a separate score, never a verdict: validity ×
  certainty × mission conformance × buildability, computed only for
  eligible designs. Pareto/novelty ranking requires a population and says
  so.

## Receipts (§25)

Every quantity is a `Quantity(value, unit, tier, sigma, basis)`. Every
speed point carries VALID / TRANSITION / EXTRAPOLATED / UNSUPPORTED —
UNSUPPORTED points carry no energy figure and must never be drawn into a
smooth curve. Every certification carries its assumptions verbatim
(flotation held over the speed sweep; GZ fixed-trim, sheer-watertight,
deck-edge as downflooding proxy).

## What it will NOT say

"CFD says this is correct." CFD-VALIDATED remains an experimental claim
this repository does not earn (Gate 2M watermark NONE; CFD node currently
unavailable). This layer exists to make sure that when a CFD node returns,
it is spent only on the few designs that survive cheap physics.
