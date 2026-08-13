# NavalAI — Geometry & Architecture Audit

Date: 2026-08-14 · Base commit: `70eb075` (code unchanged since the audit
fan-out began; intervening commits are audit reports only) · Method: 7 parallel read-only
domain inspections (full evidence with file:line citations in
`docs/audit/*.md` — treat those as the appendices of this document) plus a
full pytest baseline. **No OpenFOAM was executed.** Everything below is
static evidence; claims that could not be established from code are marked
`UNKNOWN — requires validation`.

---

## 1 · Executive summary

NavalAI is **much closer to the vision than its own registers believe, and
much further than its gates report.** The core insight of this audit:

- The **kernel is right**: since the P1/P2 rebuild, the genome carries
  design *targets* (Cp, LCB) and the geometry SOLVES a sectional-area curve
  to deliver them, with a section law that expresses both hard-chine and
  round-bilge forms, exact immersed integrals, and refusal-not-clamp error
  handling. That is the "SAC + DWL + section law" architecture the vision
  asks for — already built.
- The **wiring is the defect**: the mission never chooses the targets
  (`prismatic_target(fn)` has zero production consumers — Cp is sampled
  uniformly); the vessel context never reaches the L0 gate (`grammar.check`
  has sourced demihull bands that no production call site can reach — the
  project's own 12×0.8 m catamaran demihull is refused *as a monohull*);
  the optimizer never consults `ev.ok` (on any multihull mission **100% of
  the Pareto front carries a stability refusal and scores anyway**); and
  the CFD case derives its mass model from raw geometry, not the floated
  weight state that L1 validated.
- The **periphery is over-built and under-wired**: ~6,000 LOC of
  built-to-spec subsystems (arrangement 1,620, experiments 2,674, estrin
  479, flotation refdata, fairness, slamming, encounter-frequency
  seakeeping, dynamics, pipeline, planner, agents) have zero production
  callers. Consolidation here means **wiring and deletion, not writing**.
- The **truth machinery has three P0 integrity holes**: the gate ledger's
  regression rule (`judge_red` vs watermark) is not implemented; Gate 2U's
  watermark comes from a calibration the code itself declares void; and the
  Gate 6R reviewer packet contradicts the machine record in
  `rules/review.py`.

Totals from the seven inspections: **~90 classified findings — 14×P0,
~28×P1, ~30×P2, remainder P3/P4** (full lists in appendices).

## 2 · Current architecture (as evidenced)

```
mission text ─ translate ─ MissionSpec ─(only lwl_hint + displacement + category reach the search)
                                   │
    sample_valid / NSGA-II: uniform draw over grammar.LOW/HIGH  ← Cp/LCB drawn, not chosen
                                   │
grammar.check(x)  ── L0 algebraic gate (MONOHULL bands always; vessel= exists, never passed)
                                   │
geometry: sac_exponents(Cp,lcb) → _stations → sample_section (chine|fillet)   ← THE KERNEL (sound)
                                   │
evaluate: weights → solve_to_displacement (level-trim only) → GM/trim/list (linearised)
        → total_resistance (Michell+interference, wired; Watanabe clamps 27%) → energy
                                   │
optimize: 3 objectives; ev.ok ignored; buildability/meshability/fairness invisible
                                   │
cfd/case: SAME Hull, PARALLEL discretisation + PARALLEL mass model (ρ·V, LCB, design WL)
                                   │
case.info receipts (not consumed) · gates (57; 6 ledger-typed with unimplemented regression rule)

UNWIRED ISLANDS: arrangement · flotation · estrin · experiments · fairness · slamming
· waves.heave_response · dynamics · pipeline · planner · agents · hull_ast typology
```

## 3 · Intended architecture

The MISSION → DESIGN CONTRACT → GEOMETRY → PHYSICS → CFD ADAPTER stack (the
task's diagram). Verdict per stage: contract exists as a *scorecard* not a
*driver*; geometry kernel conforms; physics conforms for monohulls at L1;
multihull physics half-wired; CFD adapter breaks the single-state rule;
optimization sees a subset of the truth.

## 4 · Source-of-truth map

| Concern | Authoritative today | Parallel/duplicate implementations | Verdict |
|---|---|---|---|
| Genome/params | `grammar.PARAMS` (16) | mission.lwl band (drifted), TYPOLOGY_RULES, arrangement copy, formlib.MISSION, hull_form_audit | consolidate |
| Typology | **split 3 ways**: `mission.VesselConfig` (partly wired), `limits.HullRole` (declared, unreached), `hull_ast.Typology` (orphan) | — | keep VesselConfig+HullRole; retire hull_ast typology |
| Section/station | `geometry._stations` + `sample_section` | 12 discretisations incl. 3 literal topology transcriptions (admissibility, blender) | kernel sound; de-transcribe or fence |
| Hydrostatics | `hydrostatics.solve` | 6 parallel (form_coefficients, export×2, cfd/post×2, holtrop) — two deliberate cross-checks | keep A + declared cross-checks; retire silent ones |
| Resistance | `resistance.total_resistance` | holtrop (badge-only), 4×ITTC-57, 2×form_factor | single friction line; holtrop stays envelope-badge |
| Constants ρ/ν/g | none | 4 densities, 3 fresh-ν, 2 g, ρ=1000 retyped in 12 signatures | create one constants home |
| Loading | none (single scalar target) | weight_budget ∥ weight_items (live dup) | loading-condition object needed |
| Mesh/STL | `closed_mesh` (derived STL — correct direction) | panel_mesh (unwelded, BEM at design WL), blender/admissibility transcriptions | fix panel_mesh; fence transcriptions |
| CFD config | none (25 constants + dict + case.info) | fidelity holds 3rd copy of domain numbers | manifest object |
| Provenance | `db.Provenance` (sound, E9-fenced) | pipeline.JsonlLog, experiments (in-memory) | optimizer must write; version↔N_PARAMS link |
| Optimization | `optimize.py` | agents.run_plm ranks by different objective | one ranking authority |

## 5 · Generator inventory

Production generators: `evaluate.sample_valid` (rejection), `generative`
PPCA/GMM (grammar-boxed, live), `optimize` NSGA-II (2 problems, duplicated
bodies), `latent` (live via generative). Test/demo-only: `agents.run_plm`,
`pipeline.Genome`, `LatentHullProblem`. Matrix (generator × family):
monohull=PASS at L0/L1; catamaran=**FAIL-BY-WIRING** (bands unreachable,
stability refused, front invalid); trimaran=EXPLICITLY UNSUPPORTED (correct
refusal by name); drone=naming only. No silent third category *except* the
catamaran path, which today fails silently into monohull treatment at L0.

## 6 · Hull representation audit

Closed-form parametric offsets; STL derived (correct); no NURBS in the
active path (a spline was removed for measured 94.95 mm sheer error — the
"fair NURBS surface" of the vision is *deliberately* absent, replaced by
closed-form curves + a fairness functional). The historical
keel→chine→sheer 3-point limitation is **gone in the kernel** (P2 fillet
section) but **alive in the registries and transcriptions** (formlib says
round bilge inexpressible; unroll/buildability refuse roundness>0;
typology pins roundness=0). Families: hard-chine YES, round-bilge YES
(kernel) / NO (registry — contradiction), multi-chine NO, deep-V PARTIAL,
transom YES, wave-piercer/bulb/tunnel/SWATH NO (honest), catamaran demihull
= geometry NO (one hull) + physics scalar YES.

## 7 · Monohull audit

Coherent at L1: one floated state feeds stability, resistance, energy;
delivered-state proportions re-checked; exact section integrals; Wigley
anchor. Defects: level-trim only (all hydrostatics reported upright even at
5.7° computed trim), no GZ(φ), origin-slope GM proxy is the only stability
bar, Watanabe form factor clamps on 27.3% of the box, entrance angle never
computed from geometry.

## 8 · Multihull audit

Wave interference: **implemented, verified three ways, wired**
(`4cos²(k_y s/2)`, enforced θ-resolution). Everything else half-wired:
demihull L0 bands unreachable; **no multihull stability criterion**
(refusal exists; optimizer blind to it); no viscous form interference (declared);
no bridge-deck object (mass/KG/solar/wet-deck absent); per-demihull loading
unrepresentable (n identical copies); `wet_deck_clearance_g` and the
+59.7% separation-optimum finding both orphaned. **No experimental anchor
for any multihull number.**

## 9 · Drone audit

`Manning.UNCREWED` correctly re-routes rules (refuses crewed stability
assessment by name) — that is the entire drone story. No payload object, no
endurance/mission-profile fields, no equipment volume. Same geometry
pipeline works unchanged (no separate engine — good).

## 10 · Hydrostatics audit

Seven volume/wetted implementations (§4). Frames/units consistent (metres,
declared frame, one KG conversion point) with four densities and two g
values as the exception. No trim equilibrium; LCF computed and unconsumed;
no MCT/TPC; heel linear-only; loading = one unnamed condition;
tier E/F masses structurally unable to reach the float; provenance row
records the wrong KG source; "unaccounted" filler up to ~54% of
displacement (honest but information-free).

## 11 · Waterflow / wave / splash audit

Michell (θ-form, E17-correct, grid-converged on the reference hull but
population-worst 0.673% vs a 0.5% bar), JONSWAP (unsourced presets),
encounter-frequency transform (orphan), Wagner-form slamming C_p
(uncalibrated, 4.1× classical peak, no production caller, CFD instrument
exists but comparison never executed), bow-wave rise = hull-blind
stagnation bound. No splash model anywhere and nothing pretends otherwise.
No planing model; Fn>0.45 returns a badged-invalid number.

## 12 · CFD-preparation audit

Case generation consumes the same `Hull` but a parallel discretisation
(documented −0.19% loft bias) and a **parallel mass model** (ρ·V_STL, LCG=LCB,
design WL — never the floated weight state; measured 19% KG error on KCS).
No manifest object (~25 constants + dict + text blob; third copy of domain
numbers in fidelity). Receipts (cells-per-wavelength) written and consumed
by nothing. Import path: winding receipt structurally always "no"
(`diagnose` never sets `applied`) while claiming repair. `run-case.sh` has
no solver timeout. Full inventory: `docs/audit/cfd-prep-timers.md`.

## 13 · STL / NURBS / CAD audit

STL is derived (correct); repair philosophy is upstream-first and refuses
to patch own-generated geometry (correct); forensics honest
(`complete:False` over fake zeros). Defects: `panel_mesh` unwelded and
silently healed by Capytaine; BEM body built at design WL in production
(tests pass `ev.wl`, production does not); absolute mm tolerances (5 mm
refold bar, seam tol, stem widen) on a 2.5–24 m length range; mixed-dimension
epsilon in the intersection kernel; STL resolution clamp binds on every hull.

## 14 · Optimization audit

Three absolute objectives (measured non-degenerate over 898 hulls — good).
P0 leaks: `ev.ok` unconsulted; refusal classes outside G; invalid-badge
resistance scored; buildability/meshability/fairness invisible;
`build_area` misses `n_hulls`; `gm_mid` applies a monohull floor with
design beam to multihulls; surrogate ignores the grammar box; nothing the
optimizer evaluates is recorded in provenance.

## 15 · Timer / timeout audit

One real watchdog (campaign harness). Solver runs unbounded in
`run-case.sh`; kill path unverified `pkill`; two undocumented per-hull
ceilings (7200/3600); magic `sleep 120`, `MAX=20`; gates' pytest
subprocesses timeout-less (historical CI cause). Full table in appendix.

## 16 · Test coverage audit

1,209 collected across 51 files, gate-labelled, largely well-designed
(`test_end_to_end_flow` is the model). Hazards: Gate 2's 18 tests vanish in
CI via module-level `importorskip` while the gate reports GREEN (D15);
16-number reference genome tripled; ~30 exact-float pins that will move
under any consolidation; three bare `==` float comparisons; `blender`
render path untested. Baseline suite result: see
`docs/audit/pytest-baseline.txt` (run in progress at audit time —
`UNKNOWN — requires validation` until it lands).

## 17 · Dead / duplicate / orphaned code

Orphans (zero production callers): experiments (2,674 LOC — carries the
+59.7% separation finding), arrangement (1,620), estrin (479), agents,
dynamics, waves, flotation refdata, policy/dna, pipeline spine, planner,
hull_ast, wet_deck_clearance_g, fairness, prismatic_target, LCF.
Duplicates: 4×wetted-surface, 4×ITTC-57 (+5th ν), 2×form_factor, 3×STL
readers, 3×STL writers, 4×section builders, 3×volume integrators,
3×topology transcriptions, 3×section-area algebra, 2×hull_length_m,
2×mission objects, 3×reference genomes. Zero TODO/FIXME (house style uses
SUPERSEDED markers; ~45 sites).

## 18 · Exact gaps

The classified registers live in the seven appendix reports
(`docs/audit/*.md`), ~90 findings with file:line evidence. The fourteen P0s:

1. Demihull bands unreachable (`evaluate` never passes `vessel`) — G5/G0.
2. Floated-state proportion re-check monohull-only — G5.
3. No requirements→targets stage (prismatic_target unconsumed) — G0.
4. No multihull stability criterion; refusal invisible to optimizer — G3/G6.
5. `ev.ok` never gates fitness — G6.
6. No trim equilibrium — G3.
7. No GZ(φ) anywhere — G3.
8. No loading conditions — G3/G8.
9. Tier E/F masses cannot reach the float — G0.
10. Gate-ledger regression rule unimplemented — G0(gates).
11. Gate 2U watermark from void calibration — G0(gates).
12. Gate 6R reviewer doc contradicts machine record — G11.
13. Import winding receipt structurally false — G7.
14. Solver runs unbounded (no timeout) — G8; plus formlib registry stale
    vs shipped kernel (G0) and refuted seiche model still refusing runs (G8).

## 19 · Severity / priority

P0 = the fourteen above (blocks correct vessel generation or falsifies the
truth record). P1 ≈ 28 (materially wrong designs / dead critical paths).
P2 ≈ 30 (robust-validation blockers). P3/P4 = quality. Full per-domain
tables in appendices.

## 20 · Dependency graph of fixes

```
R0 wiring-truth (vessel threading, optimizer honesty, ledger rule, registry truth)
  └─ R1 mission→targets (Fn→Cp band, lwl band unification, typology consolidation)
       └─ R2 hydrostatics state (trim equilibrium, loading conditions, KG provenance, BEM at floated WL)
            └─ R3 single-truth plumbing (constants home, CFD manifest + floated mass, receipts→gates)
                 └─ R4 retirement & registry reconciliation (orphans wired-or-deleted, stale prose)
                      └─ R5 validation matrix (5 vessel cases) + final report
```
Rationale: R0 items are small diffs with outsized effect and unblock honest
measurement of everything after; R1 delivers form-follows-function; R2 must
precede R3 because the CFD manifest should consume the *corrected* floated
state; R4 shrinks the repo; R5 proves it.

## 21 · Proposed target architecture

Exactly the task's diagram, realised with what exists: `MissionSpec` +
`VesselConfig` becomes the **Design Contract** (gains design speed→Fn,
target Cp band via `prismatic_target`, loading conditions, payload for
drones); `grammar+geometry` stays the one hull kernel (vessel-aware bands);
`evaluate` stays the one state assembler (trim-equilibrium float; tier E/F
masses admitted); physics stays L1 Michell+interference / L2 BEM (floated)
/ Holtrop badge; **CFD adapter** = a manifest object derived from the
floated state + kernel STL with receipts that gate; optimizer sees the
full constraint vector including `ok`; one provenance spine records
everything the search touches.

## 22 · Validation matrix (required end-state)

|  | small | large |
|---|---|---|
| monohull | deterministic case, all quantities | same |
| catamaran | after R0/R2: bands+stability+interference+build×n | same |
| trimaran | EXPLICITLY UNSUPPORTED (refusal by name — already correct) | — |
| drone | monohull pipeline + UNCREWED rule routing (+payload object, R1) | if meaningful |

Per-case checks: geometry, topology, watertightness, normals, dimensions,
volume, displacement, Cp/Cb/Cwp delivered-vs-target, LCB/LCF, wetted,
draft, stability inputs, bow entry (SAC slope — entrance angle needs a
geometry computation, currently absent), stern exit, fairness (functional
exists; needs a consumer), STL export, CFD manifest generation. **No
OpenFOAM execution.**

## 23 · CFD-readiness checklist (status at audit)

Geometry export ✓ (watertight, forensics) · orientation ✓ own / ✗ imported
(false receipt) · units/scale ✓ own / prose-only imported · waterline ✓
(z=0) / ✗ not floated attitude · gravity ✓ (9.81 vs 9.80665 documented) ·
fluid props ✓ single-sourced in case.py / ✗ diverge from L1 · turbulence ✓
kOmegaSST + derived k/ω · domain/refinement ✓ derived-or-constant, ✗ no
manifest object · free-surface band ✓ boxes / ✗ cells-per-λ not gated ·
wall treatment ✗ open blocker per Mac campaign (layer coverage) · timers ✗
unbounded solver. **Verdict: CFD-READY = PARTIAL; CFD-VALIDATED = NO** (no
converged calibration exists; Gate 2M watermark "NONE").

---

*Appendices (full evidence): `docs/audit/geometry-representation.md`,
`grammar-typology-mission.md`, `hydrostatics-loading.md`,
`physics-models.md`, `cfd-prep-timers.md`, `optimization-generative.md`,
`tests-docs-deadcode.md`, `pytest-baseline.txt`.*
