# Post-rebuild L1 audit — verification at HEAD c017851 (2026-08-14)

Method: every §0 claim probed at HEAD (imports, production call sites, gate
rows, executed smoke checks — not prose). The 2026-08-14 architecture audit
(`docs/NAVALAI_GEOMETRY_ARCHITECTURE_AUDIT.md`) described commit `70eb075`;
this document supersedes its per-item status where they differ. The full
gate + pytest verification of this HEAD runs in a pinned worktree; its
output lands beside the final report.

## VERIFIED (built, wired into production, gated)

- **mission → design targets.** `design_fn`/`mission_cp_target`/
  `mission_cp_band` drive `HullProblem` bounds and `sample_valid`;
  `Evaluation.targets` carries target/gene/delivered Cp with conformance
  judged on the SOLVED equilibrium; LCB target honestly UNKNOWN with the
  safe band. Gate 1b tests + `test_constraints_honest`.
- **SAC/DWL/section-law geometry, curved sections.** P1/P2 kernel;
  `roundness` fillet; formlib registry re-audited to match. Gates 2x/PF.
- **Hydrostatics + trim equilibrium.** `solve`/`solve_trimmed`/
  `solve_equilibrium` (warm-start Newton, bisection fallback);
  `evaluate` reports ALL downstream quantities at the solved attitude;
  artifact fences compare at the attitude. `test_gapfix_physics`.
- **Multihull parallel-axis quantities + interference.** `vessel_terms`,
  I_T sum, `total_resistance(separation=)` measured through `evaluate`
  (Gate 1M).
- **GZ(phi).** `gz_curve`/`heeled_displacement` (polygon clip anchored on
  analytic wedges; trim-0 == level solver bit-for-bit; catamaran
  peak-and-collapse computed). NZ cl. 1.4 (a)/(b) measured
  (`multihull_gz_assessment`); criterion verdict stays REFUSED
  ((c) windage undeclarable, (d) unread).
- **Michell + ITTC-57 resistance** with validity flags (`res.valid`,
  flow envelope); ITTC-57 line single-sourced (holtrop + y+ derivation
  delegate).
- **Energy model + PayloadSpec.** Payload mass positioned, continuous
  draw joins the hotel load, uncrewed provision zeroed-with-note, JSON
  round-trip. Gate VM + `test_gapfix_product`.
- **Constants source of truth.** `navalai/constants.py` + grep fence
  (five viscosities, four densities, two gravities — named conventions).
- **Vessel validation matrix** (Gate VM: five classes end-to-end,
  trimaran refused by name, 12×0.8 judged by role) and **physical-form
  gates** (Gate PF: descriptors + ratchet).
- **Provenance machinery.** `db.Provenance` recorded by the optimizer
  (R0.2f); gate ledger regression rule implemented (`judge_red`).

## PARTIAL (built and tested; production reach incomplete)

- **GZ(phi) reach.** Consumers today: tests + the refusal text. It is NOT
  in `Evaluation`, not in any report surface, and there are no design
  maps over separation/heel. Assumptions (fixed trim through heel, no
  superstructure buoyancy, deck-edge as downflooding proxy) are declared
  on `GZCurve.assumptions` — they must ride into any certification
  output. **Free-to-trim at heel is not solved** (§10 asks where
  justified).
- **CFDManifest reach.** Built + §13/§14 one-state regression green;
  `write_resistance_case(manifest=)` renders it — but no production path
  CONSTRUCTS a manifest yet (tests only). Candidate selection (§24) is
  its natural first production caller.
- **`formcheck.form_descriptors`.** Rich descriptor set (SAC shape, DWL
  entrance, fullness fractions, WS/∇^⅔ …) — consumed by Gate PF and the
  report script only; not available on the evaluation/certification path.
  Curvature/fairness surface metrics absent from it.
- **Regimes.** `formlib.Regime` (displacement / semi-displacement /
  planing) exists as a *label on form families*; nothing routes physics
  by regime, and no reduced-order model exists outside slender/moderate
  displacement. Semi-displacement and planing are UNSUPPORTED in fact
  but not yet refused *by name* at the mission level.
- **Surrogate.** `surrogate.py` (GP + is_ood) and `flywheel.py`
  (benchmark probes, held-out region) exist with tests; no simple
  baseline benchmark (linear/forest) and no MAE/RMSE/R²/calibration
  report as §21 asks.

## STILL MISSING (the §1 certification layer)

- No **DesignCertification**/verdict object — nothing classifies
  ACCEPT / MARGINAL / REFUSE / CFD-WORTHY.
- No **hydrostatic curves vs draft**, no **Bonjean data**, no
  **loading matrix** (single implicit condition; LIGHTSHIP/DESIGN/MAX and
  people-shift/payload states unrepresented — the audit's R2.3, still
  open).
- No **speed curves** (single-speed evaluation only) and no
  VALID/TRANSITION/EXTRAPOLATED/UNSUPPORTED banding of a curve.
- No **resistance router record** (validity exists inline; no
  model/envelope/extrapolation receipt object).
- No **design-space sweep maps**, no **sensitivity table**, no
  **CFD candidate score**, no **L1 dataset generator** with versioned
  records (provenance DB stores results, not versioned training rows).
- No **geometry fingerprint** (moments; scale-aware/invariant split).
- **Buildability** is a score + refusals (`buildability.py`), not the §17
  engineering report (no panel counts/seam length/waste proxy surfaced).

## DUPLICATED (known, § 27 second pass owed)

- STL readers ×3 (`cfd/post._read_stl_tris`,
  `cfd/case._read_stl_tris_for_motion`, `mesh_repair.load_stl`).
- Wetted-surface/volume cross-checks (declared ones stay; sweep owed).
- `energy.weight_budget` ∥ `weights.MassItem` emission (§10 of the
  consolidation directive, half-done: payload flows through MassItem;
  the five budget buckets still originate in `weight_budget`).

## UNWIRED (the §26 triage roster, verified at HEAD)

| module | state | §26 disposition to decide |
|---|---|---|
| `fairness` (geometry.py:792) | real, tested, consumed by buildability's mask comment only | WIRE (certification §5) |
| `experiments.py` (2.7k LOC) | orphan; holds the +59.7% separation finding | RESEARCH |
| `arrangement.py` | orphan (reference layout demo; masses can't reach the float) | RESEARCH until R2.4 |
| `dynamics.py` | dead heuristics, zero callers | DELETE or RESEARCH |
| `waves.py` | `heave_response` orphan | WIRE into seakeeping or RESEARCH |
| `planner.py`, `agents.py`, `pipeline.py` | demo spine, zero production callers | RESEARCH or DELETE |
| `policy/dna` | compile_policy IS consumed (optimize/evaluate); dna side unverified | verify then triage |
| `hull_ast.py` | typology tables stale (R1.3 open); AST bridge used by agents only | shrink with agents' fate |

## UNKNOWN — requires validation

- Absolute accuracy of Michell+ITTC-57 for these craft (no tank/CFD
  anchor; Gate 2M watermark NONE; **CFD node unavailable** per operator
  2026-08-14).
- Catamaran interference vs experiment (Insel & Molland cited, not
  transcribed).
- Everything semi-displacement/planing.

## Consequence — build order for the certification layer

1. `DesignCertification` = composition over the EXISTING `Evaluation`
   (§4 — no parallel object): descriptors (formcheck + fairness), GZ
   summary, speed curve, loading matrix, verdict + CFD-worthiness, every
   figure carried as (value, unit, tier, sigma, basis).
2. Cheap sweeps that only need existing solvers: hydrostatic curves,
   Bonjean (both are `immersed_section` consumers — ONE sectional
   service already exists), speed curve with validity bands, loading
   matrix.
3. Regime declaration + refusal-by-name for unsupported regimes.
4. CFD candidate score consuming the manifest (its first production
   caller).
5. Dataset generator + baseline surrogate benchmark; §26/§27 triage.
