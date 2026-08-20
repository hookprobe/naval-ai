# The integration campaign — gap matrix (2026-08-20)

Four read-only subsystem audits (geometry contract + tessellation; case
physics + mesh sizing + y+; post-solve sanity + taxonomy; fidelity routing
+ coverage), reconciled against the research corpus and the last day's real
CFD evidence. Method per the directive: RESEARCH SAYS / IMPLEMENTATION DOES
/ TESTS SHOW / GAP / REQUIRED CHANGE — measured before changed.

## 0 · The headline

The architecture is substantially sound and, at the section level, STRONGER
than the directive's own NURBS proposal: the source of truth is a
closed-form analytic kernel with exact immersed integrals (refusal, never
clamp), STL/STEP are derived artefacts with independent displacement
receipts. The real defects are of three kinds:

1. **A physics-sanity hole with a walked exploit path** (highest risk).
2. **Wiring**: physics floors and regime gates EXIST (fidelity.admit,
   flow_regime, RE_TRANSITION_BAND, WH_PER_NM_SIGMA_PRODUCT) and the lanes
   that need them never call them.
3. **Longitudinal geometry**: the STL path alone never rebuilds the hull,
   so its dominant error is a 41-station lerp, not tessellation density.

The directive's §1 marker sweep is clean: ZERO TODO/FIXME/HACK in
navalai/ + scripts/; every test skip is environmental with a stated reason;
xfail is structurally banned (it counts as failure in the gate parser).

## 1 · Physics sanity — the leak (audit C)

RESEARCH SAYS: a successful solver exit is not a valid result.
IMPLEMENTATION DOES: nothing anywhere checks sign or magnitude of an
extracted force. Every C_T is produced through `abs()`, which makes
pipeline.check_cfd's `ct <= 0` refusal UNREACHABLE.
TESTS SHOW (walked): a sign-flipped -500 N total passes settled_drag, is
rectified by abs(), lands inside the Tokyo band, and mints an L3 "measured"
badge. `l3_case_evidence` (the ONE path where CFD reaches an Evaluation)
uses a raw tail mean with no finiteness check, `drift ... else 0.0` on an
empty window, and no LTS pseudo-time seam — so a diverged LTS case can read
as ">1 flow-through".
GAP: PHYSICS_SANITY_FAILED has no detector; the ingest path is the weakest
link in the whole chain.
REQUIRED: sign+magnitude sanity before any abs(); harden l3_case_evidence
onto settled_drag's discipline; parse_forces must REFUSE unparseable/NaN
rows instead of silently dropping them.

## 2 · Wiring — gates that exist and are never called (audits B, D)

| Gate | Exists | Called by the lane that needs it | Measured consequence |
|---|---|---|---|
| cells-per-wavelength floor (fidelity.admit, 20 c/λ) | yes | NO — planner/demo only | Fn 0.20 case writes at 12.7 c/λ silently |
| Reynolds regime (flow_regime, RE_TRANSITION_BAND) | yes | NO — zero refs in navalai/cfd/* | 2.5-3 m hulls get fully-turbulent RANS inside 5e5-5e6 |
| decision-worthiness sigma (WH_PER_NM_SIGMA_PRODUCT) | yes | NO — zero consumers repo-wide | fidelity is badged, never routed |
| achieved y+ | design-side only | NO post-solve check anywhere | wall-model validity of every quoted C_T unverified |
| write_transient_tail (calibration lane) | yes | NO callers (hand-invoked) | ranking and calibration pay the same wrong budget |

y+ going IN is genuinely computed (ITTC-57 u_tau -> first-layer height,
target 100 consistent with kOmegaSST wall functions, stack-fit checks at
build). `FidelitySpec.target_yplus = 30` is a dead parameter contradicting
the shipped 100.

## 3 · Geometry — the longitudinal delta (audit A)

MEASURED at 600x120 (288,862 triangles): girth chordal error is ALREADY
negligible (<=0.30 mm worst, round bilge; 0.000 mm hard chine), while the
station-lerp error reaches 10.55 mm on the reference hull — and does not
converge in nx/nz because the STL path never rebuilds the hull. At 161
stations it falls to 0.78 mm (13.5x). export.py ALREADY does this rebuild
for STEP (_LOFT_STATIONS=161); hull_to_stl does not.

CONSEQUENCE FOR THE DIRECTIVE'S §8: curvature-aware GIRTH tessellation is
REFUTED BY MEASUREMENT (the section sampler already tracks the bilge ~35x
below the dominant term). The equivalent win is longitudinal: rebuild at
161 stations, then station-align nx (nx=600 currently buys 55x triangles
for zero geometry — 0.68 cells per facet).

Also: watertightness is re-established by coordinate coincidence (6.0x
duplicated vertices, 1e-6 rounding) rather than carried as indexed
topology — the mechanism behind the one measured closure loss (C-10 KCS
re-emit, 15,603 open edges, caught in 1 s by the guard).

## 4 · Taxonomy coverage (audit C)

COVERED with recovery: MESH_GENERATION_FAILED (layer ladder),
MESH_QUALITY_FAILED (checkMesh bars + ladder), SOLVER_DIVERGED (smoke +
live abort), TIMEOUT (watchdog), SOLVER_NOT_CONVERGED (settled_drag 3-way).
HOLES: YPLUS_INVALID (no detector), PHYSICS_SANITY_FAILED (no detector),
FORCE_EXTRACTION_FAILED (exists in post.py, but campaign `ok` is time-only
so a corrupt force.dat still classifies ok), RESOURCE_LIMIT (exit 3 falls
into mesh-build-failed), CURVE/SURFACE/SOLID/TESSELLATION/STL_INVALID
(collapse into one `generation` bucket), BOUNDARY_CONDITION_INVALID,
INITIALISATION_FAILED (lumped), COURANT_FAILED (proxies only).
Also: run-case.sh writes solve_verdict= receipts that NO python reads.

## 5 · Coverage + rates (audit D)

SUPPORTED: hard-chine and round-bilge monohulls; symmetric catamarans
(topology + separation, one demihull mirrored); plumb/fine-entry bows are
expressible (stem is plumb by construction) but have NO fixture.
ABSENT (confirmed): asymmetric catamaran; trimaran (refusal pinned BY NAME
— honest); LWL < 2.5 m is unrepresentable by deliberate scope (RCD box; and
no honest friction line exists below it — the drone descope).

MEASURED STAGE RATES TODAY: grammar 6.75% of the uniform box (N=10,000);
floats 99.7% (299/300); screen-admissible 92.7%; mesh rung-0 92.0% (N=25);
ran-to-budget 88.2% (N=17); SETTLED 17.6% (LTS confound stated).
NO POPULATION RATE EXISTS for: certify verdict distribution, cruise-band
validity, generator-conditional geometry validity. A fortress-only campaign
(N=20,000 -> L0 -> evaluate -> certify) costs UNDER 2 HOURS and fills every
missing row stratified by LWL/Fn — the evidence the fidelity thresholds
need, and the §22 table's missing half.

## 6 · Refuted by this campaign (do not resurrect)

- Curvature-aware girth tessellation as the geometry fix (measured: the
  error is longitudinal).
- The GCI triplet (cancelled by the operator's math directive; replaced by
  one estimator-settled anchor + Richardson band + CoKriging).
- Naive stop-at-first-certification (h003 certifies at 800 iterations then
  moves 23% — the sequential trap, pinned).
- "95% settled" as a target on the LTS lane: those records hold no
  stationary mean at all. LTS is RANKING-grade; calibration-grade truth
  lives in transient tails.

## 7 · Execution order (by risk, not by section number)

1. Physics sanity + ingest hardening (this file §1) — protects everything.
2. Wiring: cpw + regime gates into the case writer; y+ receipt chain;
   dead target_yplus.
3. select_fidelity(): the five gates as deterministic code, consumed by
   certify/cfd_candidate.
4. Geometry: hull_to_stl rebuild at 161 stations; station-aligned nx; NaN
   misattribution; ev at the CFD STL boundary.
5. Taxonomy completion + recovery policies; campaign `ok` requires a
   readable finite force history.
6. Adversarial fixtures for the named holes (wave-piercer, narrow-gap cat,
   long/deep corner, fidelity-envelope adversaries).
7. The fortress statistical campaign (overnight) -> the honest §22 table.

---

# Part II — the CONTRACT directive (2026-08-20, second instruction)

The operator's follow-up: "a large part of the mathematical gap is now
closed, but there is still no sufficiently simple DETERMINISTIC path from
GENOME -> VALID HULL -> APPROPRIATE MODEL -> MESH PRESCRIPTION -> SOLVER ->
VALID RESULT. The pieces exist but are distributed across grammar,
geometry, admissibility, regime research, resistance, screen,
mesh_robustness, CFD, calibration, surrogate and gates. Close it WITHOUT
creating another framework. The goal is to make the mathematics simple
enough that the computer always knows what to do next."

## II.1 · ALREADY FIXED / REMAINING GAP / ROOT CAUSE / MINIMAL FIX

| # | Already fixed | Remaining gap | Root cause | Minimal fix |
|---|---|---|---|---|
| 1 | Geometry truth is closed-form and refuses rather than clamps; STL/STEP derived with independent receipts | Nothing composes the stages into ONE answer; each caller re-derives Fn/Re/regime/validity | The pieces were built bottom-up, each correct in isolation; no top-level contract was ever written | ONE `evaluate_hull()` composing the EXISTING functions (no new physics) returning one receipt |
| 2 | flow_regime, RE_TRANSITION_BAND, FN_MICHELL_MAX, holtrop's Re clause all exist and are correct | The CFD lane never consults any of them | Research landed as constants + reports, not as calls at the seam both entry points pass | Call them in `write_resistance_case` (in flight) and in the contract |
| 3 | fidelity.estimate/admit/cheapest_admissible price and admit a case | Nothing DERIVES a mesh prescription from hull+physics; the case writer holds fixed levels | `admit()` answers "is this option admissible", never "what does THIS hull need" | A `mesh_prescription()` that inverts the existing floors (wave-resolution density, first_layer_thickness, geometric tau) into the numbers the case writer already accepts |
| 4 | Settledness (MSER-5 + AR(1) + CI), product sigma, CoKriging, active selection, KCS anchor | They answer "how accurately do we know a VALID result", not "how does a valid hull REACH one" | Complementary questions; only the first was ever asked | Keep untouched (operator's §11); the contract consumes their verdicts |
| 5 | h011/h012 are DETERMINISTIC geometry failures (both reproduce in two independent campaigns) | The invariant that breaks is not yet named | The screen was calibrated on meshability PROXIES, never on the failing invariant itself | Investigation in flight: name the invariant, exclude the region upstream, score FP/FN on the 25+17 corpus before adopting |
| 6 | The screen's rung-0 half is MEASURED non-predictive and one criterion already demoted for it | Screen criteria carry no per-criterion FP/FN record | Criteria were added as they were hypothesised, scored only in aggregate | Per-criterion receipt table (criterion, equation, reason, source, evidence, FP, FN) — the operator's §7 form |

## II.2 · THE SUPPORTED DOMAIN (operator §14 — declared, not implied)

Stated from the audit evidence, to be ENFORCED by the contract rather than
left as prose. Outside it, the honest answer is a named refusal.

| Axis | Supported | Basis |
|---|---|---|
| LWL | 2.5 – 24 m | grammar box (RCD Art. 3(2)); below 2.5 m the rules tier has nothing to say AND no honest friction line exists (SMALL-CRAFT-REGIMES: the turbulent-Re + displacement-Fn window is EMPTY below ~2.6 m) |
| Fn (resistance) | 0 – 0.45 | FN_MICHELL_MAX; 0.45–0.65 has NO valid empirical tier (CFD-only, and only at L >= 3 m); > 0.65 REFUSED (no Savitsky in the tree) |
| Re | >= 5e5 refuse-below; 5e5–5e6 flagged transitional | RE_TRANSITION_BAND; ITTC 7.5-02-05-01's stimulation floor at 5e6; fully-turbulent RANS reproduces ITTC-57's own bias inside the band |
| Topology | monohull, symmetric catamaran | EVALUABLE_TOPOLOGIES; trimaran refusal is pinned BY NAME; asymmetric cat is not expressible in the kernel |
| Bilge | hard chine and round bilge | roundness gene; the KIT route additionally requires roundness = 0 |
| Bow | plumb / fine-entry expressible (stem is plumb by construction) | formlib; NO fixture exercises it yet — a coverage gap, not a capability gap |
| Environment | calm water; declared sea state/windage are RECORDED but do not yet gate | the environment gate is new physics (windage/orbital estimators) |

NOT SUPPORTED, and the code should say so by name: LWL < 2.5 m (the drone
line — three walls, not one), Fn > 0.65, trimaran, asymmetric catamaran,
planing/semi-displacement case configuration (no config exists at all).

## II.3 · The contract's shape (composition, NOT a new framework)

`evaluate_hull(genome, mission, environment) -> HullEvaluation` calls, in
order, functions that ALL EXIST TODAY, and adds only the prescription:

    grammar.check            -> A: is the hull physically valid?
    evaluate/certify         -> A: hydrostatics, stability, rules, verdict
    resistance.flow_regime   -> B: is the MODEL valid here? (Fn/Re bands)
    select_fidelity          -> B: which tier ANSWERS the question, and why
    admissibility.screen     -> C: is the geometry numerically meshable?
    mesh_prescription        -> C: what mesh does THIS hull require?  [NEW]
    post.settled_drag /
      physics_sanity         -> D: is the RESULT converged and trustworthy?

The operator's §4 is honoured by construction: A, B, C and D are four
SEPARATE verdicts on the receipt and are never collapsed into one
valid/invalid flag. §12's receipt is that dataclass, serialised.
