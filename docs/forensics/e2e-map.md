# Forensics — E2E trace + mutation probes (§2/§3/§14), HEAD 3527a59

> **DATED SNAPSHOT — NOT A CURRENT STATE.** This file was measured at
> `HEAD 3527a59` (2026-08-18). That commit is now **174 commits**
> behind `master`. Read it as evidence of what was true THEN, never as
> an answer to "what is the state now" — CLAUDE.md routes that question
> to `python -m navalai.gates` and `python scripts/reconcile_gaps.py`.
> The 2026-08-11 incident this repo records is exactly this failure: four
> documents each asserted a subsystem did not exist, and all four were
> false because they were read as current.
EXECUTED (not read): formcheck CASES a/b/d/e through evaluate → certify →
manifest → write_resistance_case(manifest=); refused vector traced; two
mutation probes. Full stage table + traces in agent record; breaks here.

## Measured SSOT / reconstruction breaks
- **B1 one rule, two mLDCs**: evaluate.py:505 selects stock sheet from the
  MISSION TARGET; :772/:786 assess the same rule at the FLOATED
  displacement → whenever budget > target, R-TBM fails by construction
  (case a REFUSEs on a 0.02mm sliver of exactly this split).
- **B2 two ply thicknesses in one certification**: certify.py:372 calls
  shell_complexity without panel_thickness_m → 15mm default + its OWN
  weight_budget instead of ev.weights/ev.ply_thickness_m. Measured: 29%
  structure-mass divergence inside one DesignCertification (case-b chine
  variant: 1389.7 vs ladder 1945.5 kg @ derived 21mm).
- **B3 trim or-0.0 collapse** (cross-confirmed): certify.py:313/340/357 +
  manifest.py:128.
- **B4 manifest reconstructs Fn/Re/wavelength** (G_OPENFOAM + NU_FRESH_20C
  vs ev.vessel's flow values; Re drift +4.6%) — convention declared, the
  DUPLICATE derivation is not.
- **B5 the manifest's floated attitude is recorded, never applied**:
  write_resistance_case meshes at the DESIGN frame, tank splits at z=0;
  manifest= only fingerprints + renders. MEASURED: case a runs at 1909kg
  vs certified 856.7 (+122.9%); case d 4547 vs 4300 (+5.7%).
- **B6 production CFD CLI bypasses the chain**: scripts/make_case.py
  hardcodes a REFERENCE genome, no mission/evaluate/manifest;
  --free-motion requires --stl → motion_from_geometry (the G7 parallel
  mass model) is the ONLY reachable free-motion path.
- **B7 resistance mixes floated state with design length**:
  resistance.py:973 lwl=hull.x[-1] for Fn/Cf/form factor while
  hs.lwl_eff sits unused (known: worst -15% length, +2.575% Rt).
- B8 ui/server drops `energy` silently (no receipt). B9 NL/LLM path
  cannot declare a vessel (monohull-only front end). B10 two design-Fn
  definitions (formcheck genome-LWL vs mission hint) — targets stage
  INERT for all four deterministic CASES (no lwl_hint set). B11 certify
  speed curve reads raw mission.energy vs evaluate's payload-adjusted
  spec (latent). B12 no admissibility gate inside the CFD writer (Hull
  builds refused genomes; watertightness is the only check). **B13 the
  target class is structurally CFD-ineligible**: buildability refuses
  roundness>0 → certify makes that a hard precondition of
  cfd_candidate.eligible → the project's own round-bilge 12x0.8 class can
  never score CFD-worthy.

## Mutation probes
Speed: everything moved (fn/re/Rt/wh/ranges/cert/manifest) except the
INERT targets stage (B10). Payload: full propagation incl. manifest when
budget>target; under a pinned displacement target the 50%-σ unaccounted
item re-partitions instead (DESIGNED + receipted; noted: resistance/
energy/manifest-mass are functions of the TARGET in that regime).
Positioned payload moves lcg/trim strongly (verified).

## Refused-vector traversal
grammar refuses w/ provenance; formcheck ABSENT-with-reason; evaluate L0;
certify REFUSE + ineligible; manifest RAISES (correct); **Hull() builds
anyway and write_resistance_case would accept it** (B12).

## Verified sound
One floated HydroState to resistance (E7); separation resolved once;
σ propagation; manifest consumes ev.masses/hydro (G7 real AT THE MANIFEST
LAYER); floated re-check same vessel; multihull GM refused; honest
refusals at every claiming stage.
