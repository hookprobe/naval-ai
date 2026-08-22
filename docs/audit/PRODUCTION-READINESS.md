# PRODUCTION READINESS — the end-to-end validation, and the plan

**Measured 2026-08-20 on this Mac.** Evidence sources, none restated here:
`docs/audit/MATH-CONSOLIDATION.md` (the M1-M8 matrix), `docs/research/
CROSSOVER.md`, `docs/audit/STATUS.md` (the channel), and
`python scripts/reconcile_gaps.py` for live gap state.

---

## 0. WHERE THE TREE IS

    suite         3 failed / 1563 passed / 21 skipped   (was 14 / 1436 / 18)
    gaps          123 rows: 109 closed, 11 open, 1 needs-human, 2 retired

All three remaining failures are accounted for, and none is an unexplained red:

| failure | what it is |
|---|---|
| `test_resistance::..._bit_identical_to_the_golden` | RED BY CONSTRUCTION on arm64. The golden declares `GOLDEN_ARCH` = x86-64 and reports PLATFORM off it. Re-measured: 530/4906 keys move, max relative 5.656e-13, **none** over the 1e-12 parity bar. |
| `test_phase6r::..._cannot_yet_name_the_editions` | A GATE PROMOTION WAITING. It fails *because* the editions got recorded. Gate 6R sits in the ledger at watermark 0. |
| `test_stageF::..._serves_the_mission_it_was_asked_about` | LEFT FAILING DELIBERATELY. See §2. |

**A correction to an earlier claim of mine, recorded because it went to the
operator and to fortress.** I said unfixed failures should be "recorded in the
ledger with a watermark, an owner and a review_by", quoting BUILD-PLAN §16. The
ledger fence refuses that: MEASURED, all five ledgered gates (2M, 2U, 4F, 6D,
6R) are STATUS ROWS with `suite=None`, while a suite-backed gate's verdict comes
from running its tests. **For a suite failure the only sanctioned outcome is a
FIX.** My "fix or ledger" reading does not execute.

---

## 1. THE END-TO-END FLOW, RUN

`mission text -> parse -> sample -> geometry -> domain -> regime -> model ->
resistance -> mesh/solver prescription -> escalation`, on three briefs:

    brief            parse  sample  hull      model  mesh   result      tier       escalate
    panel default    ok     ok      REFUSED   OK     OK     UNMEASURED  EMPIRICAL  False
    small tender     ok     ok      REFUSED   OK     OK     UNMEASURED  EMPIRICAL  False
    catamaran        ok     ok      REFUSED   OK     OK     UNMEASURED  EMPIRICAL  False

The plumbing is intact — every stage runs, nothing throws, the four verdicts stay
separate and `escalation_required` is stated rather than implied. What the flow
shows is not a wiring defect. It is that **the sampler produces hulls the
contract then refuses**, on every brief tried.

`sample_valid`'s docstring says "clear L0 AND produce a finite L1 evaluation" —
FINITE, not FEASIBLE — so it is not lying. But its name and its position in the
pipeline both imply validity, and everything downstream treats its output as
candidates.

---

## 2. THE BINDING CONSTRAINT, AND IT IS A MATERIALS PROBLEM

MEASURED on 30 hulls, `sample_valid(30, seed=0)`, panel-default brief
(category C, 6 t, 10 m):

    feasible                        2 of 30
    fail ONLY on bend radius        6        <- would pass if the ply bent
    fail on bend radius + others   11
    fail on other things only      11

    achieved bend radii   min 0.30 m   median 0.89 m   max 1.40 m
    required by 18 mm ply                              1.44 m
    hulls reaching the floor                           0 of 17

**NO hull in the population achieves the radius its own required ply can take.**
The best is 1.40 m against a 1.44 m floor. This is not a bug and not a stale
number — the engineer-side agent verified the 18 mm is the LADDER'S OWN correct
ISO 12215-5 selection for a category-C 6 t boat, and `min_bend_radius_m(0.018)`
= 1.44 m is its honest cold-bend limit.

**It is a structural mismatch between the grammar's shape space and the material
the rules require.** The generator draws chines and bilges tighter than 18 mm
plywood can be cold-formed around. Three honest resolutions, none of which is a
tolerance change:

1. **Laminate.** Two 9 mm skins cold-bend to roughly a quarter the radius of one
   18 mm sheet and are standard practice in ply construction. The rules tier
   models a single stock sheet; it does not model a laminate.
2. **Constrain the grammar** so the drawn radii are buildable in the sheet the
   category demands — i.e. make buildability a BOUND on the search rather than a
   rejection after it, which is exactly what `policy/compiler.py` already does
   for the legal envelope.
3. **Change material.** The standards work already covers foam-cored sandwich
   and GRP, which have no cold-bend limit of this kind.

**This is the production blocker for the flagship brief, and it is an
engineering decision, not a defect to fix quietly.** Recorded for the operator.

### 2a. Why `test_stageF` is left failing
`ui.server.pareto_payload` runs NSGA-II at pop=24/gens=10 = 240 evaluations and
returns an EMPTY front for the panel's own default brief. Budget sweep, seed 0:

    240 evals -> 0 members (2.44 s)   <- the server's live budget
    480 -> 1     800 -> 0     1200 -> 48 (14.69 s)     1500 -> 16

Feasible but not converging, and NON-MONOTONE (800 -> 0 against 480 -> 1), so
the search is unreliable there rather than merely slow. It cannot be bought:
1200 evaluations is 147x over Gate 4's 100 ms interactive bar. With only 2 of 30
draws feasible (§2), a 24-member population is unlikely to contain one.
**The fix is a warm start — seed NSGA-II from feasible draws — or a repair
operator.** Optimiser work with its own experiment.

---

## 3. THE GAP PLAN

### P0 — blocks any honest ≥95% claim
| # | gap | evidence |
|---|---|---|
| P0-1 | **Buildability is a rejection, not a bound.** 0 of 17 hulls reach the required bend radius. Until the grammar draws buildable radii (or the rules model a laminate), the feasible fraction stays ~7% and every campaign measures the sampler, not the physics. | §2 |
| P0-2 | **Search does not converge at the interactive budget.** | §2a |
| P0-3 | **F17 / Gate 2U's "converges" half has no number**, and the screen's bars are still calibrated on a 15-gene genome. Recalibration in flight. | `reconcile_gaps` F17 |

### P1 — correctness, measured and recorded, not yet fixed
| # | gap | evidence |
|---|---|---|
| P1-1 | **Third thickness divergence.** `weight_budget` charges hull+deck at one `t_ply`; `engineer.assess` builds non-bottom panels at nominal 15 mm. Selects BELOW nominal in 11 of 24 category/size combinations, so on small boats **the built boat is heavier than the validated one**. Neither side is right: ISO gives per-zone thicknesses and the engineer's non-bottom value is a nominal. | STATUS 20q |
| P1-2 | **F1 (CRITICAL, `reconcile_gaps`)**: no added-resistance-in-waves routine. A product validated only in calm water is not validated for a mission. | register F1 |
| P1-3 | **F16 / Gate 2M**: no settled triplet, no GCI. | ledger |
| P1-4 | **E5**: no round-trip on 12+ public-CAD hulls; KCS validates no chine, transom or spray physics. | register E5 |

### P2 — the economics (brief §15, "N_candidate >> N_CFD")
`I1` (co-kriging fitted from real high-fidelity rows, not the synthetic
Forrester pair), `I14` (the surrogate spine has no consumer), `I13`.
**Do not start these before P0-1**: an active-learning loop over a design space
that is 93% infeasible will spend its budget discovering the bend-radius floor.

---

## 4. READY FOR THE HELD-OUT GATE 2U CAMPAIGN?

**No, and the reason is P0-1, not the machinery.** The machinery is ready: the
population is regenerable and identity is `(arity, seed)`; the held-out set is
SEALED (hash only, no genomes) so it cannot be tuned against; prescriptions carry
provenance with declared kinds; the domain edge is derived and enforced; the
refuted crossover is frozen with an executable fence.

What is not ready is the POPULATION the gate would measure. With ~7% of draws
feasible, a ≥95% unattended mesh+converge claim over "the supported domain"
would be a claim about whichever 7% survived — the "95% of an easy population"
the brief forbids by name. **Fix P0-1 first, then draw the held-out set.**

---

# FINAL STATE, 2026-08-21 (supersedes §0 above)

    suite    1 failed / 1592 passed / 5 skipped     (was 14 / 1436 / 18)
    gaps     115 closed / 5 open of 123             (was 109 / 11)

**The single failure is red BY CONSTRUCTION**, not a defect:
`test_resistance_is_bit_identical_to_the_golden` declares `GOLDEN_ARCH` =
x86-64 and reports PLATFORM rather than REGRESSION off it. Re-measured on
arm64: 530 of 4906 keys move, max relative **5.656e-13**, and **none exceeds
the 1e-12 parity bar**. Re-recording it here would blunt the guard on the
architecture that owns it.

## What the buildability decision actually bought

    feasible designs (flagship brief, 30 draws)   2/30  ->  7/30
    bend-radius refusals                         17/30  ->  3/30
    Pareto front at the SERVER'S live budget      0     ->  13 members

The last line matters most: `test_stageF` had been recorded as a
**convergence** defect needing a warm start, on the evidence that 240
evaluations returned 0 members and 1200 returned 48. It was neither. **The
search was fine; the space was empty.** A budget sweep is a poor instrument
for telling "cannot converge" from "nothing to converge on".

## Two defects that only became visible once others were fixed

1. **A crowd state judged by the DESIGN trim bar.** `TRIM_LIMIT_DEG`'s own
   comment says "static attitude from the ARRANGEMENT alone (NO CREW
   MOVEMENT, no seaway)", and it was gating `PEOPLE_FORWARD`/`PEOPLE_AFT`.
   It passed unnoticed at 1.78 deg and failed at 4.05 deg once the laminate
   let those hulls past the ladder. **Every canonical vessel class was
   refusing.** Trim is now reported, not gated; a crowd-state criterion is
   owed and is NOT invented.
2. **A seaworthiness failure behind a manufacturing refusal.** Certification
   stops at `evaluation_ok False`, so while the reference hull was refused on
   its cold-bend radius its loading states were never reached.

**Both were revealed by fixing something else.** That is the argument for
fixing the cheap thing first even when it looks cosmetic.

## READY FOR THE HELD-OUT GATE 2U CAMPAIGN?

**Not yet, and the blocker has changed.** It is no longer the design space —
that was P0-1 and it is closed. What remains:

| # | blocker | state |
|---|---|---|
| 1 | Gate 2U's bar is mesh **AND** convergence over a **HELD-OUT** population | The instrument now exists (`SMOKE_ONLY`, 2 min 40 s/hull) and reads **24/25 = 96.0%** on the DEVELOPMENT set. The held-out set is sealed and unopened. |
| 2 | A smoke verdict is **not** a settled drag | It answers "does this mesh begin to solve". Gate 2U's "converges" needs `settled_drag`, which needs full solves. |
| 3 | Gate 2M (F16) has no settled triplet | ~69 h of CFD, an order of magnitude past the 8-hour cap. |

**Do not open the held-out set until 1 and 2 are settled.** It can be spent
once, and `write_manifest` refuses to overwrite it — re-sealing is spending
the seed.

---

# WHAT IS MISSING TO SHIP (2026-08-21, after the governance wiring)

The question this section answers: **what stands between today's tree and
handing a builder a kit they can cut?** Ranked by whether it stops a kit
shipping, not by how hard it is.

## P0 — BLOCKING. The cut files are wrong, and until today nothing said so

    hull the GOVERNED search delivered, ladder ev.ok = True
      bottom-stbd   refold deviation max    21.2 mm
      topside-stbd  refold deviation max   221.5 mm     bar: 5 mm
      export_dxf -> SUCCEEDED, 67 kB, no complaint

That is the whole problem in four lines. `refold_surface_deviation_mm` is the
two-sided distance from the REFOLDED panel back onto the hull's moulded
surface: cut plywood to these outlines and the topside misses the chine by the
better part of a quarter metre. It does not close. Gate 6D is RED and ledgered
at **124.1 mm** against `limits.REFOLD_BAR_MM` = 5 mm.

**Why it escaped.** `export_dxf` gated on `refuse_unvalidated(ev, 'DXF')` --
did the LADDER pass? The ladder has no refold row in
`evaluate.CONSTRAINT_NAMES`, so it cannot answer the only question a shop
cares about. A red gate whose artefact ships anyway is a gate softened by
omission.

**Closed 2026-08-21 at the boundary**, not by softening the bar: `export_dxf`
now takes the hull, refuses over the bar by name, and STAMPS the verdict into
the DXF header (`999` comment) so the standing travels with the artefact --
`REFOLD VERIFIED n mm <= 5 mm`, or `REFOLD NOT VERIFIED - not a production cut
file` when no hull was supplied. An unmeasured quantity is refused, never
assumed good.

**So the product is now HONEST but cannot ship a kit.** That is the correct
state and it is the top of the queue.

**What the fix is — CORRECTED 2026-08-21, and the correction inverts it.**
The cause on record was the unroller ("rulings taken at constant station x").
It is not. Measured against closed-form surfaces: cylinder **0.0000 mm**, flat
plane 0.0002 mm, tapered cone 0.0013 mm, with twisted-cylinder 436.6 mm and
hyperbolic-paraboloid 46.7 mm as negative controls. **The unroller is exact on
developables.**

Gate 6D is measuring a HULL THAT IS NOT DEVELOPABLE. Over governed hulls
corr(non_developable_frac, refold) = **+0.783**, `flare` dominant at **+0.694**:

    flare  0 deg -> ndev_frac 0.0064 -> refold  62.8 mm
    flare 12 deg -> ndev_frac 0.2302 -> refold 149.3 mm
    flare 25 deg -> ndev_frac 0.2953 -> refold 193.0 mm

So this is the ROUNDNESS FINDING AGAIN, one level deeper: the search proposes
shapes flat sheet cannot take, and the manufacturing stage is blamed for it.
The fix is therefore a DESIGN-SIDE bound (a developability constraint the
search respects), not a better solver. Whether the grammar admits a sub-5 mm
hull at all is the open question -- random search over the governed box found
**10.8 mm** at flare -1 deg, 2.2x the bar. If no such hull exists the grammar
needs a developable-by-construction mode.
Owner `chief-architect`, `review_by` 2026-11-11.

## P1 — the performance claim is not yet earned

Both of these are about the NUMBER A CUSTOMER IS QUOTED (range, Wh/NM), not
about whether the boat floats.

1. **Resistance sigma is uncalibrated.** Gate 2M watermark is the string
   `NONE` -- no reproducible measurement exists. Wh/NM carries a DECLARED
   sigma, not a measured one, and range varies ~2.7x across a 0.75-2.0
   resistance bias.
2. **The hard-chine physics has no experimental anchor at our Froude number,
   and it is now the ONLY physics we ship.** The 2026-08-21 bound pins
   `roundness` to 0, so every hull the product proposes is hard-chine -- and
   `dR_chine` at Fn ~ 0.26 is exactly the quantity DSYHS (round bilge) and KCS
   (round bilge, bulbous bow) cannot validate. The experiment EXISTS: Compton's
   1986 USNA series, hard chine and round bilge over Fn 0.10-0.60. The data is
   not held. See `docs/audit/GATE2-PHYSICS-STACK.md`.

## P2 — autonomy, not correctness

| gate | watermark | bar | what it costs today |
|---|---|---|---|
| **2U** unattended meshing | **17.6 %** settled (88.2 % ran to budget) | >= 95 % | CFD cannot run unattended; every campaign needs a human |
| **4F** raw generative feasibility | **79.33 %** (GMM; pPCA 88.67 %) | >= 99 % | the generative model proposes invalid hulls 1 time in 5 |

Neither blocks a kit. Both block doing it AT SCALE without a person watching.

## P3 — evidence and process

- **E5** — no round-trip against 12+ public-CAD hulls; the geometry kernel is
  verified against its own output.
- **I1** — co-kriging still fitted on the synthetic Forrester pair, not real
  high-fidelity rows.
- **I13** — Gate 4 clause 3 has no artefact: no recorded non-expert session
  producing a hull that passes the ladder. **This is the one that decides
  whether the product is usable by its intended customer**, and it needs a
  person, not code.
- **Gate RT** — red on arm64 by construction (530/4906 keys, one-ulp,
  IEEE-legal; golden recorded on x86-64). It CANNOT be ledgered: `judge_red`
  only runs for gates with `suite is None`. The honest fix is a
  per-architecture golden.

## WHAT IS ALREADY PRODUCTION-GRADE, so the list above is read in proportion

Mission parsing -> governed search -> L0/L1 physics -> ISO 12215-5 scantlings
and ISO 12217-1 stability with clause provenance -> loading matrix -> GZ curve
-> weight/energy with propagated sigma -> nesting with a real MaxRects packer
-> line-item BOM -> STL -> content-addressed provenance. 1585 tests green.
`tests/test_end_to_end_flow.py` asserts, at 14 points, that the exported solid,
the CFD STL, the BEM mesh, the BOM and the arrangement are all the SAME hull
the ladder validated.

**The honest summary: the design side is production-grade and the
MANUFACTURING side is one solver short.** Everything upstream of the cut file
is measured, badged and fenced. The cut file itself is geometry that does not
yet close, and as of today it says so instead of shipping.


## A correction to this session's own report on `rulings="strakes"`

I measured `hull_panels(hull, rulings="strakes")` at **8231.9 mm** against
`"developable"`'s 221.5 mm on the same hull, with an overflow warning out of
`numpy.linalg`, and reported it as an unrecorded defect — "37x worse than the
family its own docstring presents as the better one". **That characterisation
is wrong and is withdrawn.**

`hull_panels`'s one-line summary says strakes exist because "a single family
cannot span the panel", which reads as an improvement. The FULL docstring on
`strake_pairings` says the opposite in capitals:

> MEASURED 2026-08-12 — THIS DOES NOT WORK YET, AND IT IS RECORDED RATHER THAN
> SHIPPED. […] Worse than the fitted pairing in five of six, and it clears the
> bar in none.

It even carries the diagnosis (`_branch_pairing`'s monotone clamp binds at up
to half the stations inside a segment, destroying planarity exactly where the
panel needed it) and the reason it is kept: "this mode exists to be measured,
not adopted". My number is CONSISTENT with that recorded state, not a new
finding.

**The lesson is the one this repository already has**, and I hit it again: I
read the SUMMARY of an artefact and not the artefact. `docs/LESSONS.md` records
it as "A summariser that truncates is a receipt that lies"; here nothing
truncated anything — I simply stopped at the short docstring one call up.

What IS unrecorded and stands: the `numpy.linalg` **overflow** on this hull.
The recorded strakes figures span 112–868 mm; 8231.9 mm with an arithmetic
overflow is a different failure mode from "worse than the alternative", and it
belongs in that docstring's table if the mode is ever revisited.

---

# GATE 6D IS CLOSABLE — the existence proof, and what it costs (2026-08-21)

## A seaworthy hull that unrolls under the bar EXISTS in this grammar

Found by a dedicated (1+1)-ES over the GOVERNED box, minimising refold subject
to the full ladder passing, and then **independently re-measured**:

    bottom-stbd      4.932 mm
    topside-stbd     4.952 mm      <- WORST, against the 5 mm bar: PASS
    ndev_frac        0.0091
    ladder ok        True, violations NONE (under the reference constitution)
    GM              +2.545 m       displacement 6000 kg (mission target)
    L/B              2.54          flare -0.58 deg      roundness 0

So Gate 6D is **not** a physics impossibility and **not** an unroller defect.
The grammar contains boats that are simultaneously seaworthy and cuttable.

## The first answer was wrong, and the way it was wrong is the finding

An unconstrained refold search reached **3.900 mm** — and that hull has
**GM = -0.35 m**. It capsizes. L/B 5.1, D 2.12 m: narrow and deep means little
transverse curvature, which is developability-friendly and stability-poor.

**Developability wants narrow and flat; stability wants beam.** Gate 6D is a
TRADE between two things the product needs at once, which is why neither "fix
the solver" nor "add a bound" was ever going to be the whole answer.

## And the trade is expensive — stated, not buried

Against the lowest-energy (unverified) hull from the same governed mission:

    quantity        lowest-energy hull    verified-buildable hull
    refold                   221.5 mm                   4.952 mm
    ply sheets                     59                        121
    build hours                  1825                       3679
    Wh/NM                         412                        595

The buildable boat is beamier, roughly twice the build, and 44 % thirstier.
That is a PRODUCT decision, not a defect.

## Why the search never finds it, and what is actually owed

NSGA-II's objectives and constraints contain **no buildability term**, so a
larger budget searches harder for the same thing. The fix is STEERING, and the
cost question is settled:

| candidate | cost / hull | corr with refold | usable? |
|---|---|---|---|
| `unroll.refold_surface_deviation_mm` | **2301 ms** | 1.000 (it IS the meter) | **no** — 8561x `grammar.check`; 3.3 h for a pop-64 x 80-gen run |
| `Hull.panel_twist_rate()` (L0) | **0.02 ms** | **+0.089** (Spearman +0.224) | **NO — it does not separate.** 0 of 30 governed hulls under 5 mm, and the cheapest-twist hull refolds at 43.4 mm while the 5th-cheapest is at 1274 mm |
| `shell_complexity(...).non_developable_frac` | **1.8 ms** | **+0.783** | **YES** — ~9 s across a whole NSGA-II run |

**The L0 developability number is not a buildability predictor**, and that is
worth having measured: it is the obvious thing to reach for, it is free, and
it is wrong. A criterion that does not separate is not a criterion.

## Shipped now, at the boundary

`scripts/design_kit.py` verifies the AUTHORITATIVE meter on the front (64
members x 2.3 s = ~147 s, paid once) and delivers a hull whose panels are
MEASURED to close, or refuses and says by how much. `export_dxf` refuses over
the bar and stamps its verdict into the file. So nothing unbuildable can leave
the system today, even though the search cannot yet aim at buildability.

**Owed:** the `non_developable_frac` steering row, appended by the constitution
when `construction = sheet-developable`. Note the contract it must respect —
`policy.rows_for` is a READER of a finished evaluation and measures nothing
itself, so the quantity has to reach `Evaluation` first.


---

# THE 41-STATION CORRECTION (2026-08-21, later the same day)

Every refold number above was measured at `geometry._LADDER_STATIONS` = 41.
The other session measured what that count is worth, and it changes how two of
this document's claims must be read.

`refold_surface_deviation_mm` builds the panel as straight chords between the
hull's stations, so part of every reading is a 40-segment polyline's SAGITTA —
discretisation, not surface. A hull with Gaussian curvature **7.8e-14** (machine
zero, exactly developable) reads **17.1 mm at n=41** and **1.5 mm at n=321**.
41 was chosen for hydrostatics cost; nothing about manufacturing picked it.
That is CLAUDE.md rule 4 — a defect measured at a configuration the product
never runs — except here it also produced a false PASS.

**The discriminator is the TREND, not the value**, exactly as `cfd.post.gci`
treats a mesh family: falling under refinement is measurement, rising is
geometry. `unroll.refold_convergence` returns it.

## What survives, and what is retracted

| hull | 41 / 81 / 161 mm | verdict | standing |
|---|---|---|---|
| the **4.952 mm existence proof** | 4.95 · 2.71 · **2.36** | **PASSES** | **STANDS — and is stronger than reported**: it is 2.36 mm at n=161, falling |
| the other session's kit corner (flare 0) | 17.13 · 5.77 · **4.10** | **PASSES** | independent second existence proof |
| the 3.900 mm unconstrained hull | 3.90 · 4.35 · 4.32 | NON_DEVELOPABLE | was already discarded — GM −0.35 m, it capsizes |
| **the hull the kit lane DELIVERED** | 4.92 · 5.22 · **8.71** | **NON_DEVELOPABLE** | **RETRACTED. It is not buildable.** |

**So Gate 6D is still closable — two independent hulls pass the family test —
and the DELIVERY PATH was broken.** The refinement stage scored on the
41-station number, so it optimised the sagitta artefact rather than the
curvature and returned a hull that games the metric. That is the sharpest
failure in this session: not a wrong measurement, but a search pointed at one.

## Fixed

- `unroll.export_dxf` gates on `refold_convergence`'s trend and refuses the
  delivered hull by name. Verified against that exact hull.
- `scripts/design_kit.py` still DRIVES the search on the cheap 41-station score
  (the family costs several times more per step) but CONFIRMS every candidate
  on the family before returning it, and says so when the coarse count was
  flattering.

## The DEFAULT path, re-measured on the family (2026-08-21)

"0 of 7 cuttable on the default path" was first measured at n=41 — the very
count shown above to be an unreliable instrument. It could have been an
artefact in EITHER direction, so it was re-run with `refold_convergence`:

    #0  (194.18,  82.66, 295.38)  NON_DEVELOPABLE
    #1  (221.52, 105.83, 232.89)  NON_DEVELOPABLE
    #2  (193.01,  81.18, 294.10)  NON_DEVELOPABLE
    #3  (200.70, 105.11,  61.99)  REFINING
    #4  (120.32,  80.32, 321.25)  NON_DEVELOPABLE
    #5  (122.48, 296.17, 324.84)  NON_DEVELOPABLE
    #6  (215.67, 206.25,  62.09)  REFINING
    ------------------------------------------------
    cuttable on the DEFAULT governed front: 0 / 7

**The figure stands, and now on the right instrument.** Five are genuinely
doubly curved; two are still falling at n=161 but are two orders of magnitude
over the 5 mm bar, so neither is a near miss. Gate 6D stays RED and the kit
route depends on the search job (`docs/BUILD-PLAN.md` §PU, item PU-3).

Worth stating plainly because it is the shape of the whole problem: the
optimiser is not *nearly* producing buildable hulls and losing them to a
measurement. It is not producing them at all, because nothing in its
objectives or constraints asks for one.

---

# THE 2026-08-22 CAMPAIGN — what running it four ways found

An operator-granted 30-hour window, spent on simulation and validation rather
than on reading the code. Two campaigns ran throughout: a Gate 2U
re-measurement on the shipped configuration, and a repeatability sweep of the
kit lane across four missions.

**The sweep is what earned its keep.** The lane had delivered ONE buildable
boat, which looked like a working product. Running four missions found two
failures with completely different causes, and a third defect surfaced only
because a fifth run repeated a mission that had already succeeded.

## Nine defects, and what they have in common

| # | defect | why it mattered |
|---|---|---|
| 1 | BOM had no tape, wire or epoxy LINE | stitch-and-glue IS the tape; a builder could not buy the boat |
| 2 | 40% of displacement at an assumed height, no declared consequence | moving it ±0.60 m moves GM ∓0.243 m, ≈ the whole propagated sigma |
| 3 | empty front reported as an impossible mission | the region is 0.8% dense; pop 24 seeds it ~18% of the time |
| 4 | `solar_kwh_day` served UNBADGED | a basis-coloured UI renders an unbadged number as measured |
| 5 | acceptance test trapped in the ES improvement branch | REFUSED a mission while holding a 1.5 mm answer |
| 6 | Gate 2U's own `verify` reproduced 83.3%, not its 17.6% watermark | anyone re-measuring would read a 4.7x improvement that never happened |
| 7 | ledger `units` mislabelled the watermark's quantity | same entry, same shape |
| 8 | an `AttributeError` served as `source: refused` | "refused" is an HONEST state here; a crash inherited its credibility |
| 9 | seed sweep counted SECONDS | 35% fewer draws under load -> 29.9 mm instead of 7.3 mm -> a refusal instead of a boat |

**Not one was a physics error.** The unroller is exact on developables
(cylinder 0.0000 mm). The KG conversion was always right in the product path.
Viscous drag settles on all 16 archived hulls. What failed, every time, was the
layer that REPORTS — and specifically the places where "we cannot answer" and
"here is an answer" look identical.

## Two failures that were NOT the same

- **m10 (10 m / 6 t) — a load artefact.** Delivered 1.92 mm at 3000 s on a
  quiet machine; refused at 1500 s under a concurrent CFD campaign. Same seed.
  Fixed (defect 9), and confirmed by re-running under the same load: the
  draw-counted sweep found 7.3 mm again — the quiet machine's figure — and the
  lane delivered 2.31 mm.
- **m12 (12 m / 9 t) — possibly the envelope.** 137345 draws, no time cap, best
  341.7 mm. That is not budget starvation. It is the first evidence that
  DEVELOPABILITY MAY DEGRADE WITH SIZE: a bigger, fuller hull needs beam and
  depth, and flat sheet takes less of both. If a size trend confirms it, the
  honest output is a PRODUCT ENVELOPE — "sheet-ply kits work up to about X
  metres" — beside the RCD length ceiling, not a bug to keep hunting.

## What the lane actually is

Not a deterministic pipeline. A **stochastic search with a budget-dependent
success rate**, and the claim has to carry both numbers. Delivered so far:

    m06  6 m / 1.4 t   3.09 mm   family (13.5, 6.01, 3.09)  PASSES
    m08  8 m / 3 t     1.47 mm   family (18.4, 1.79, 1.47)  PASSES
    m10  10 m / 6 t    1.92 mm   family (17.07, 6.6, 1.92)  PASSES
    m10  10 m / 6 t    2.31 mm   (repeat, different seed)   PASSES

Every one falls under refinement, which is the signature of a coarse-count
artefact clearing rather than curvature. And the variance has MOVED rather than
gone: after the seed fix, seed 23's sweep found a BETTER start than seed 11
(6.3 mm against 7.3 mm) and still failed where seed 11 reached 2.31 mm. The
local search is now the variance source, and keeping the top-K sweep candidates
instead of the single best is the obvious next lever.
