# CFD candidate selection — spending the expensive tier last

Principle (§24/§29 of the screening directive): CFD is bought for the few
designs that survive cheap physics — never for the lowest predicted
resistance alone, and never before the screening engine has classified the
population.

## Implemented today (single-design factors)

`certify(...).cfd_candidate` scores an ELIGIBLE design (evaluation ok,
regime supported, cruise point not UNSUPPORTED, buildability computable):

    validity   — resistance model inside its support at cruise
    certainty  — 1 − σ_Rt/Rt (the model's own confidence in this hull)
    mission    — delivered-Cp conformance (full/half credit)
    buildable  — 1 − 2 × non-developable fraction

score = mean of parts; an ineligible design scores 0 with the reason
recorded. The manifest (`cfd.manifest.CFDManifest`) is the hand-off object:
a selected candidate's case is generated FROM its certification's floated
state, never re-derived.

## Owed to the population layer (dataset generator — next)

The remaining §24 factors need a POPULATION and are refused by name until
the versioned L1 dataset exists:

    Pareto competitiveness   — rank on (Wh/NM, build area, |GM − band|)
    novelty                  — distance in the geometry-fingerprint space
    robust winner            — Pareto rank stability under loading states
    uncertainty candidate    — high-σ region the surrogate cannot resolve

Selection slate per campaign (when a CFD node is available again):
baseline + Pareto winner + robust winner + novel candidate + uncertainty
candidate + one multihull. Six cases, chosen by evidence — against the
2026-08-13 practice of triplets burnt on a single hand-picked hull.

## Blockers for the expensive tier (unchanged, recorded)

- **Gate 2M** (KCS calibration): watermark NONE; needs a CFD node — the
  Mac is currently unavailable (operator, 2026-08-14).
- **Gate 2U** (unattended meshing): calibration void (15-gene batch);
  re-base owed on the same node.
- Wall-layer coverage findings from the last Mac campaign remain open.
