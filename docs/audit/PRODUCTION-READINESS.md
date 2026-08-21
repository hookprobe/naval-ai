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
