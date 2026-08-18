# Code consolidation plan — dependency-ordered (forensics Phase 2)

> **STATUS 2026-08-19 — EXECUTED.** Every item below is landed except the
> two that require the CFD node (Gate 2U item-2 campaign, Gate 2M) and
> the wall-clock bars this box has never met (documented, not softened).
> C-13/C-14 landed with the consolidation-directive work; C-17 (timer
> policy) remains an open next-session item with §17 of the screening
> directive. Landed highlights by commit: C-01..05/09/11/19/20/22 (Phase
> 3 opening), C-06/07 (floated-frame cases), C-18+rescue-axis (54031fa →
> 2e9c2f4), C-15/16, C-10 (fbc1ed7), C-33 (b0b61bc), C-23..28 wave + C-30
> (6ce2ec7), C-29/3E retired (c36b4e3), C-12/34/35 + C-31 (e884dc6),
> C-36 + C-21 (fbb0237), §31 chain test (cf20def), Gate 3 re-measures
> (5b6fda5), C-08 last (752e695). Phase-I full verification at 752e695:
> see docs/audit/STATUS.md and the §34 post-fix answers in
> CODE_FORENSICS_REPORT.md.

Basis: nine banked forensics reports (`docs/forensics/*.md`), HEAD at plan
time `f0ccc5f`. Every item: finding → evidence → change → proof required.
Rules: one migration at a time, tests after each, no deletion before
consumers/gates/docs/history are traced (nothing was classified DEAD, so
this plan contains **zero file deletions** — the cleanup is wiring, labels
and receipts). No CFD. No threshold weakening.

## Phase B — source-of-truth defects (P0/P1)

- **C-01 (P0) frozen_suite infinite loop.** The held-out wedge (top-quarter
  LWL × bottom-quarter BWL) contains ZERO L0-feasible hulls since the
  kernel rebuild widened the box (corner L/B 11.47 > 8.5; measured 0/60,000
  at HEAD **and** at audit base — pre-existing). `while got < n_region`
  (flywheel.py:566) has no draw guard → both verification runs hung 4 days;
  every unmocked retrain/frozen_suite test hangs. FIX: (a) hard draw budget
  in the loop → loud error naming the empty wedge; (b) re-anchor the wedge
  so it intersects the feasible set under the CURRENT box (quantiles chosen
  so corner L/B < 8.5), re-measure acceptance, update the stale docstring
  (1.3% / L/B 6.7); (c) regenerate `data/baselines.json` (its held-out arm
  is void — same class as the gate2u calibration); (d) re-enable the two
  excluded suites. Proof: test_phase7 + test_surrogate_honesty complete in
  bounded time; a synthetic empty wedge raises instead of hanging.
- **C-02 (P0) trim `or 0.0` cluster.** certify.py:313/340/357 +
  cfd/manifest.py:128 collapse a REFUSED trim (None, E11) into 0.0 — one
  site feeds CFD. FIX: certify carries trim as None-with-refusal in the
  Quantity (or refuses the stability block); manifest guard also requires
  `ev.trim_deg is not None` (its docstring already promises "an OK L1
  evaluation"). Proof: a trim-refused evaluation yields no 0.0-labelled
  "solved equilibrium" anywhere; manifest raises.
- **C-04 (P0) one rule, two mLDCs.** evaluate.py:505 selects the stock
  sheet from the MISSION target; :772/:786 assess R-TBM at the FLOATED
  displacement — whenever budget > target the rule fails by construction
  (case a refused on a 0.02 mm sliver). FIX: one displacement (the floated
  state's, per §13 single-truth) for both selection and assessment; pinned
  cases re-measured. Proof: case a's R-TBM verdict consistent; the split
  can be reproduced in a regression test that then passes.
- **C-05 (P1) certify's second weight model.** certify.py:372 lets
  shell_complexity default to 15 mm + build its own weight_budget → 29%
  structure-mass divergence inside one certification (measured). FIX: pass
  `panel_thickness_m=ev.ply_thickness_m` and consume `ev.weights` where
  buildability needs masses. Proof: cert.buildability.structure_kg equals
  the ladder's on the case-b chine variant.
- **C-07 (P1) manifest re-derives Fn/Re/λ** with case constants while
  `ev.vessel["fn"]/["re"]` exist (Re drift +4.6%). FIX: consume ev values;
  keep the case-convention numbers as SEPARATE named fields (fn_case,
  re_case) if the case genuinely needs them. Proof: manifest fn == ev fn.
- **C-09 (P1) grammar_version decorative.** db.py:84 defaults "chine-v1";
  no caller passes it; 15- and 16-gene rows share one label. FIX: default
  derives from `grammar.N_PARAMS` (e.g. f"genome-{N_PARAMS}"); migration
  note for existing local DBs. Proof: a new row's version differs from the
  15-gene era's.
- **C-11 (P1) NU_SEA naming collision.** holtrop re-exports its 1.1883e-6
  as NU_SEA_15C while constants' NU_SEA_15C = 1.18831e-6; resistance
  imports the holtrop alias under an ITTC-attributed comment. FIX: rename
  the holtrop alias (NU_SEA_HOLTROP end-to-end), correct the resistance
  comment. Proof: one name = one number repo-wide; fence extended.
- **C-13 (P1) two design-Fn definitions / inert targets stage.**
  formcheck.design_froude (genome LWL) vs mission.design_fn (hint); all
  six deterministic CASES leave the hint unset so the R1.1 targets stage
  never engages for the project's own fleet. FIX: CASES declare
  lwl_hint_m; formcheck.design_froude renamed/documented as the GENOME
  Froude; receipt distinguishes them. Proof: mutation probe shows
  cp_target moving for case missions.
- **C-14 (P1) certify speed curve reads raw mission.energy** while
  evaluate uses the payload-adjusted spec (latent two-specs-one-boat).
  FIX: build the adjusted spec once (mission-level helper) consumed by
  both. Proof: a payload.power_w mission yields identical hotel terms.
- **C-08 (P1, careful) resistance design-length mix.** resistance.py:973
  uses hull.x[-1] for Fn/Cf/form-factor beside floated wetted/cb/beam/
  draft; hs.lwl_eff unused (documented worst +2.575% Rt). Known and
  pinned widely — schedule as its OWN migration with population
  re-measurement; do not bundle.

## Phase C — E2E paths (P1)

- **C-06 the manifest must matter.** B5: write_resistance_case records the
  manifest but meshes the DESIGN frame (case a floats +122.9% heavy vs
  its certified state); B6: make_case.py bypasses mission/evaluate/
  manifest entirely; the G7 free_motion fix has zero production callers.
  FIX (stages): (1) write_resistance_case(manifest=) REFUSES when the
  case's z=0 displacement disagrees with manifest.displacement_kg beyond
  a measured tolerance, unless free-surface trim is explicitly declared
  out-of-scope for the fixed-hull case — the disagreement becomes a named
  receipt either way; (2) make_case.py gains `--mission` (evaluate →
  certify-gate → manifest → case) as the canonical genome lane;
  free-motion for genome hulls uses manifest.free_motion. Proof: the §31
  four-vessel E2E tests drive mission→manifest→case with no manual mass.
- **C-18 admissibility screen wired.** The SAFE/DANGEROUS meshability
  verdict is never consulted by the case writer. FIX: write_resistance_case
  consults screen() for genome hulls; DANGEROUS → refuse with the
  verdict's reason (override flag for deliberate experiments). Proof:
  a DANGEROUS hull cannot silently produce a case.
- **C-19 round-bilge CFD eligibility.** buildability refusal (roundness>0)
  must not hard-zero cfd_candidate.eligible — the project's own target
  class can never be CFD-worthy today. FIX: buildability refusal becomes
  a MISSING metric with note; eligibility keyed on physics/validity;
  buildable-part omitted from the score with basis. Proof: case d scores
  eligible (its refusals remain stability-only).
- **C-12/C-34/C-35 the wire and NL front ends.** HTTP drops `energy`
  silently and has no vessel decoder (monohull-only UI); the NL path
  cannot declare a vessel. FIX (minimum honest): record a note on the
  mission when energy/vessel keys are dropped; (full): decode
  energy+vessel dicts on both fronts (rehydration already exists on
  MissionSpec). Proof: a wire mission with battery_kwh moves the served
  numbers, or carries the refusal note.

## Phase D — silent fallbacks & timers (P1)

- **C-15 evaluate broad-except narrows** (AttributeError/KeyError from
  code bugs masked as 'vessel:' refusals): catch ValueError/TypeError
  as design refusals; let code errors crash or prefix 'checker error:'.
- **C-16 timeout hygiene:** gates.py pytest subprocess gains a per-suite
  timeout (the 4-day lesson, measured); mesh_robustness timeout inversion
  fixed (outer > inner) + verified pkill; blender_isosurface_probe exit
  code on failed export.
- **C-22 receipts gain identity:** DesignCertification JSON + export
  .receipt.json carry genome sha256 + code version (the gate2u lesson).

## Phase G — tests (P2)

- **C-03** delete the dead assertion (`or True`, test_phase0.py:80) —
  replace with the real symmetry assert.
- **C-29** Gate 3's two expected-fail tests → typed RED ledger rows or
  retirement per their own instructions (re-measure first: the 3E bar may
  now be met).
- **C-30** test_phase2 importorskip split: BEM tests skip per-test;
  ~14 capytaine-free case tests always run.
- **C-31** ITTC envelope two-homes: reconcile limits.friction_line_validity
  (strict, unwired) with resistance.flow_regime (wired) — one envelope,
  one bar, the tripwire retired deliberately.
- **C-32** surrogate mark false-refusing its own seed: re-mark with C-01's
  regenerated baseline; ledger row if red persists.

## Phase H — scripts/artifacts/docs (P2/P4)

- **C-20** `git rm --cached renders/*.png` + J6 guard probes git ls-files.
- **C-21** hooks re-install (core.hooksPath portable) — currently silently
  disabled on this box.
- **C-23/24/25/26/27** wiring-or-label decisions: estrin (wire into
  evaluate's rules for inland scope OR docs stop claiming), policy
  compiler (EXPERIMENT label + a governed entrypoint decision),
  pipeline/latent/agents/hull_ast (RESEARCH banners per §26),
  waves↔seakeeping docstring, demo_mission.py legacy banner or certify
  routing.
- **C-28** doc truth wave: PLM.md §2.0 payload denial, BUILD-PLAN PV-1/2
  + entry table (run_plm/Pipeline), STATUS self-contradiction, CLAUDE.md
  machine absolutes, ALIGNMENT counts, ui/server stale comment.
- **C-33** minor constants: PV-area single expression in energy.py; formlib
  0.45 fence; freeboard floors relationship note; scripts G stray;
  rho-default fence.
- **C-36** ledger prose withdrawals (Gate 6D figures) + red_by_record
  fence widened beyond N.N%.

## Phase I — verification

Re-run gates (now hang-proof) + full pytest + reconcile; §31 four canonical
E2E tests (mission→…→manifest, no injected results); §32 checklist; the
§34 seventeen answers with evidence.
