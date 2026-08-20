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

---

# Part III — the BUILD PLAN to completion (2026-08-20)

What is closed, what is open, who runs it, and in what order. The
directive's §16 acceptance items are the exit criteria; this is the path to
them.

## III.1 · Closed by this campaign

| Directive | Closed by | Evidence |
|---|---|---|
| §3 one contract | `navalai/contract.py` | 10 pins, Gate HC |
| §4 four verdicts | A/B/C/D on the receipt | reference hull: A=REFUSED, B=OK, C=OK |
| §5 mesh prescription | `mesh_prescription` | cell sizes in metres, first layer, expected tau, dt, cells, wall, RAM |
| §6 Gate 2U mathematically | the h011/h012 investigation | no invariant breaks; p=0.601; criterion refused |
| §8 regime taxonomy | `classify_regime` | tuple, not label; boundaries imported |
| §9 fidelity governor | `select_fidelity` | 5 gates, 42 pins, first consumer of the product sigma |
| §11 calibration preserved | untouched + improved | MSER-5 + AR(1) on real histories |
| §13 no new physics | composition only | contract calls, never re-derives |
| §18 the matrix | this document | Parts I-III |
| (unasked) physics sanity | `post.physics_sanity` | the walked exploit closed, Gate 2N |

## III.2 · Open, fortress-side, in order

1. ~~**§14 enforce the supported domain in ONE place.**~~ **DONE
   2026-08-20**: `contract.supported_domain()` refuses by AXIS and by NAME,
   with every bound imported from its owner (RCD_HULL_LENGTH_SCOPE_M,
   FN_PLANING_ONSET, RE_TRANSITION_BAND, EVALUABLE_TOPOLOGIES) so the
   domain cannot drift from the modules that enforce its parts. It is a
   FIFTH receipt field, asked BEFORE the four verdicts, because
   out-of-domain is not a judgement on the boat: a design outside the
   domain is unaddressed, not bad — and the point of saying so is that
   nobody runs it through machinery calibrated for something else and
   reports the number.
2. **§15 the coverage matrix as fixtures.** One certifiable genome per size
   band (2.5-3, 3-5, 5-7, 7-10, 10-12 m) plus a catamaran and a plumb-bow
   form, each pinned through the contract with its regime and prescription.
   These are also the genomes Block 4 needs, so building them serves both.
   MEDIUM.
3. **§7 the per-criterion FP/FN table** — ANSWERED 2026-08-20, and the
   answer is that it CANNOT BE COMPUTED HONESTLY YET
   (`docs/audit/SCREEN-CRITERIA-FPFN.md`). With the ladder ON the
   74-hull corpus meshes 74/74, so the positive class is EMPTY; the only
   corpus carrying screen verdicts pinned the ladder OFF, so its two
   "failures" are the rung-0 artefact Block 1 invalidated; and the
   ladder-ON corpora record no screen verdicts at all. Also found: the
   harness bar and the runner bar disagree on one hull of 16 (13/16
   against 14/16), so any Gate 2U rate must name its bar. RECOMMENDED
   INSTEAD: re-target the screen as a COST predictor (which hulls need a
   backoff rung — 9 of 74 did), which has a non-empty positive class.
4. **§12 wire the D verdict.** `result_verdict` is UNMEASURED by design
   until a solve exists; the contract should read a case directory when
   given one (settled_drag + physics_sanity + the y+ receipt) so the same
   receipt carries the solver and physics verdicts. SMALL once the Mac's
   y+ receipt lands.
5. **The stale pins at HEAD.** At least three numeric pins and two
   wall-clock bars fail on a pristine HEAD checkout, independent of this
   campaign — one traced to a pin written before four legitimate
   hydrostatics changes moved the value under it. Each needs
   re-measurement WITH THE REASON RECORDED, never deletion. SMALL each,
   and until they are done "all tests pass" (§16.A) cannot be claimed.
6. **§10 tier-bias measurement.** Data-gated: it needs the Mac's
   transient-tail numbers (Block 5) beside the L1 predictions. Then
   CoKriging bridges MEASURED bias rather than assumed bias.

## III.3 · The exit criteria, restated honestly

§16.A (all tests pass) is blocked by III.2.5, not by new work. §16.B
(regime boundaries + refusals) is DONE (42 governor pins + the contract's
regime tests). §16.C (h011/h012) is DONE, with the answer "generated
validly, no repair needed" pending Block 1's confirmation. §16.D (mesh
bank) is Block 2. §16.E (end-to-end per regime) is III.2.2 + Block 4.
§16.F (the 200-hull campaign) stays GATED behind all of the above, and
Gate 2U stays RED until its evidence changes — at 17.6% settled, which is
harsher than the 88.2% the directive quotes, because "ran to budget" was
never convergence.


---

# Part IV — the §22 rate nobody had measured (2026-08-20)

Building the §15 coverage genomes produced the population rate the audit
listed as missing, and it is worth more than the genomes were.

**MEASURED, 60 uniform grammar draws, each given a mission whose cruise
speed puts it at Fn 0.25 (so size bands are compared at the same Froude
number rather than at one boat's speed): 40 REFUSED, 1 MARGINAL, 0
ACCEPT.** Dominant causes, in order:

| count / 60 | cause |
|---|---|
| 29 | **GM negative** — the hull is unstable |
| 29 | static list UNDEFINED (the same hulls: no positive GM, so no equilibrium heel) |
| 20 | panel bend radius below the plywood cold-bend limit |
| 14 | GM positive but under the category floor |
| 13 | floated L/B outside its band |
| 6 | floated B/T outside its band |

**THE GRAMMAR BOX IS A GEOMETRY BOX, NOT A DESIGN BOX.** It admits hulls
that are buildable as surfaces and unstable as boats. Two consequences
that matter more than the number:

1. **The supported domain (II.2) is not the grammar box** — it is a much
   smaller subset inside it, and certifiable designs must be SEARCHED
   (which is what the optimiser is for), not sampled. Any statement of
   the form "N% of the design space is valid" must say which denominator
   it used; uniform-in-box is nearly all invalid and that is not a defect.
2. **A coverage matrix built by rejection sampling cannot be a matrix of
   certifiable designs.** `data/coverage-band-hulls.json` is therefore
   labelled for what it is: MESHING-coverage hulls, grammar-valid and
   mesh-screen clean, spanning 3-12 m at a common Fn — the right input for
   Block 4, which measures the MESHER across the size range. The 2.5-3 m
   band yielded nothing even meshing-clean in ten draws, which is its own
   small finding about where the box thins out.

Found on the way, and fixed: 5 of the first 40 draws were refused with
"constraint 'rules' is not a finite number" — an UNDECIDABLE ES-TRIN
finding (ES-REC reports `measured = nan` on purpose, because craft type
is not modelled) poisoning a `max()` aggregate. That is now 0 of 40; see
the commit for the mechanism.


---

# Part V — what the OPTIMISER finds, and the question it raises for §16.F

Part IV measured that uniform sampling yields 0 ACCEPT / 1 MARGINAL in 60.
The obvious next question is whether the SEARCH finds what the draw cannot.
**MEASURED 2026-08-20, `pareto_front(pop=40, gens=25, seed=3)`, 454 s, 25
front members: 15 MARGINAL, 10 REFUSED, 0 ACCEPT.** The best is a 12.10 m
hull at Fn 0.236, mesh-screen OK, EMPIRICAL tier, prescribed 6 prism
layers, refused nothing — its only reason is `constraint margin thin:
['gm', 'rules']`.

So the search works: the MARGINAL rate goes from 1-in-60 to 15-in-25,
roughly 36x. **But nothing reaches ACCEPT, and that is probably correct
rather than a defect.** MARGINAL in this tree means every floor is MET and
something sits within 5% of its bar. An optimiser minimising energy drives
the design onto its constraints — that is what optimisation IS — so the
optimum of a constrained problem should be expected to sit ON the
constraint boundary, i.e. MARGINAL. Demanding ACCEPT would be demanding
that the optimiser leave margin on the table it was asked to consume.

**THE QUESTION THIS RAISES IS THE OPERATOR'S TO ANSWER, and it changes
what §16.F measures:** the acceptance target is "≥95% valid unattended
end-to-end". Does MARGINAL count as valid?

- If YES (the defensible reading — every floor is met, and the margin is
  reported), then the target is measurable and the search already produces
  candidates at a useful rate.
- If NO, then the target is unreachable BY CONSTRUCTION for any optimised
  design, and what should be measured instead is the margin DISTRIBUTION —
  how close to which bars, and whether the thin margins are on quantities
  the product can carry (a 5%-thin GM is a different risk from a 5%-thin
  scantling).

Recorded rather than decided here. What the evidence supports either way:
the binding constraints on the optimised front are GM and the rules tier —
the same two that dominate the sampled refusals — so the design space is
tight against STABILITY and STANDARDS, not against geometry or meshability
(mesh verdict was OK on every front member examined).


---

# Part VI — the two campaigns converge on ONE variable (2026-08-20)

Block 1 and Block 4 were aimed at different questions and landed on the
same mechanism, which is the strongest kind of evidence this project gets.

**Block 1 (h011/h012, the two Gate 2U failures):** both mesh CLEAN at n=6
and fail at n=7 — 13 and 12 wrongly-oriented faces, skew 247 and 9.9,
falling to 0 and 3.5 / 4.5. Layer COVERAGE barely moved (73.5 -> 73.6%)
while skewness fell 71x.

**Block 4 (the four Fn-matched size bands, none of them related to those
hulls):** all four mesh clean at rung 0 with no per-band tuning — §15's
question answered YES — and the ONLY monotone trend across the range is
the prism stack. Skewness rises 3.28 -> 4.59 -> 5.80 -> 10.76 with size
while cell count shows NO trend (301k-382k), and the largest band is the
one that loses its stack: 5.02 of 7 layers at 71.7% coverage against
85-92% elsewhere.

**THE MECHANISM, stated once:** a derived layer count the local geometry
cannot carry produces PARTIAL stacks, and partial stacks are what skew.
Not the surface, not the cell count, not the station count. The largest
band sits nearest the cliff without going over it — with the ladder
deliberately disabled — which is why the shipped pipeline (ladder ON)
recovers hulls the campaign recorded as failures.

That makes the prescribed layer count the single most valuable number in
`mesh_prescription`, and it is why the Block 3 A/B is worth running: the
prescription and the shipped writer disagree about exactly this quantity
on 24 of 25 hulls.

**A defect of this module's own, found by Block 4 and fixed:** all four
bands wrote at 19.90 cells per wavelength against a bar of 20 — the same
0.5% miss in every band, because Fn-matched cases share their rounding.
`density_for_wave_resolution` inverts the floor EXACTLY, and the writer
then rounded the background cell count to NEAREST, stepping under it. A
floor that the prescription's own discretisation steps under is not a
floor; it now rounds up, at a cost of at most one background cell in x.

**And the Reynolds floor earned its keep on the small band:** 3.44 m at
Re 4.59e6 sits inside the transition band, receipted with the consequence
spelled out — a fully-turbulent closure there reproduces ITTC-57's own
bias at RANS cost, so agreement with the L1 tier would be CORRELATED
ERROR rather than validation. That is precisely the trap
docs/research/SMALL-CRAFT-REGIMES.md predicted, caught by the gate that
research produced, on the first population it was pointed at.


---

# Part VII — the baseline was far redder than reported (2026-08-20)

A full-suite run on a PRISTINE checkout of the HEAD this campaign started
from finished after 5h08m:

    30 failed, 1299 passed, 39 skipped

I had reported "at least five stale pins" from spot checks. That was an
undercount by a factor of six, and the correction matters more than the
number: **the suite was substantially red BEFORE this campaign began**,
and nobody knew, because the pre-push fence runs a 134-test
record-integrity subset rather than the whole suite. A green fence and a
green suite are different claims, and only the first was ever being made.

WHAT THIS DOES NOT MEAN. It is not 30 defects in the product. The five
examined in detail were all of one family — pins whose underlying value
moved through legitimate, well-documented changes that nobody
re-measured (an LCB pin that survived four hydrostatics revisions; a ply
thickness that predated Gate 6R's implementation of the operator's own
delivered ISO text; an equality pinned tighter than the solver
converges). Each was re-measured with its reason recorded rather than
deleted or loosened, and each took minutes once located.

WHAT IT DOES MEAN, and it is the §16.A consequence: "all existing tests
pass" was never a satisfiable acceptance criterion at this HEAD, and any
plan that treated it as a checkbox was mis-scoped. The honest sequence is
(a) run the FULL suite to get today's number, (b) triage it by family
rather than by test, (c) re-measure with reasons, and only then (d) claim
§16.A. Steps (a)-(c) are hours of work, not minutes, and they are hours
nobody had budgeted.

RECOMMENDED, and not yet done: put the full suite on a schedule — nightly,
or at minimum before any acceptance claim — so that the distance between
"the fence is green" and "the suite is green" can never again grow to 30
without anyone noticing. The fence stays as it is: it is fast because it
is a subset, and that is the right trade for a pre-push hook.


## Part VII.b — today's number, and a mistake in how I measured it

A full-suite run on the WORKING TREE (mid-campaign, before the kernel
performance work landed) finished after 5h07m:

    BASELINE (pristine starting HEAD):  30 failed, 1299 passed, 39 skipped
    TODAY    (mid-campaign tree):       22 failed, 1406 passed, 24 skipped

Eight failures cleared, 107 tests added, 15 fewer skips. The direction is
right and the remaining 22 are the honest §16.A backlog.

**A METHOD MISTAKE WORTH RECORDING, because it cost the most useful half
of the result.** Both runs were launched through a `grep -E "^FAILED|
passed|failed"` filter to keep the log small. pytest colourises its
summary, so every `FAILED` line begins with an ANSI escape and `^FAILED`
matched NONE of them — leaving a 1.1 KB file with the totals and not one
test name, from a five-hour run, twice. The totals are real; the triage
list is gone and cannot be recovered without re-running.

WHAT TO DO INSTEAD, for whoever runs this next: `python3 -m pytest tests/
-q -p no:cacheprovider -rf --color=no > full-suite.log 2>&1` — `-rf`
prints a clean failure list, `--color=no` removes the escapes that broke
the filter, and NOTHING is filtered at launch. Filter the file afterwards,
when it is cheap to re-filter and free to be wrong.

The run also cannot be repeated right now for a second reason worth
stating: the tree is under active optimisation (kernel landed, resistance
in flight), so a five-hour run measures a tree that no longer exists by
the time it finishes. The full suite belongs on a schedule against a
QUIET tree, which is exactly the recommendation Part VII already makes.


---

# Part VIII — the empty coverage band, explained in closed form (2026-08-20)

`data/coverage-band-hulls.json` has no 2.5-3.0 m entry: nothing in that
band came back meshing-clean in ten draws, and the file records the
absence rather than substituting something. The reason is not sampling
luck.

A hull reaches the full-fidelity chain only if it is BOTH fully turbulent
(Re >= `RE_TRANSITION_BAND[1]`) and inside the thin-ship envelope
(Fn <= `FN_MICHELL_MAX`). Those conditions fight as length falls, because

    Re = Fn * sqrt(g) * L^1.5 / nu

so shrinking a hull costs Reynolds number as L^1.5 against a FIXED Froude
ceiling. Setting them equal gives the shortest hull whose window is not
empty:

    L = (Re * nu / (Fn * sqrt(g)))^(2/3) = **2.61 m**

Across the band, at nu = 1.19e-6:

| LWL | Fn needed for Re 5e6 | verdict |
|---|---|---|
| 2.50 m | 0.48 | PAST the Michell limit — window empty |
| 2.75 m | 0.42 | just inside |
| 3.00 m | 0.37 | comfortably inside |

So the band is not uniformly out of scope: its BOTTOM is and its TOP is
not, with the crossover at 2.61 m.

**THIS IS THE THIRD INDEPENDENT ROUTE TO THE SAME NUMBER, and that is why
it is worth recording.** `docs/research/SMALL-CRAFT-REGIMES.md` derived
~2.6 m from three physical walls (Reynolds, environmental forcing, and the
cube-law payload floor) with no reference to Michell. The RCD scope that
`supported_domain` enforces starts at 2.5 m for a legal reason unrelated
to either. Recovering 2.61 m from two constants the code already owns is a
CHECK on the research rather than a restatement of it — and it means the
supported domain's lower edge is not a policy choice we could soften if we
wanted to. It is where two of our own models stop overlapping.

Pinned by `tests/test_contract.py::
test_the_supported_domains_lower_edge_is_derivable_from_two_constants`.
