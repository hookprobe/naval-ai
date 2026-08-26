"""GOVERNED design lane: a mission sentence -> a hull a builder can cut.

    python scripts/design_kit.py --mission "..." --out data/exports/kit1

WHAT THIS IS, AND WHY IT IS NOT `demo_mission.py`. It is the first entry point
in this repository that COMPILES A CONSTITUTION and hands it to the search.
Until 2026-08-21 every non-test caller of `reference_policy`/`compile_policy`
was a docstring: Gate V3.0 was implemented, tested and wired to nothing, so the
legal envelope and the design DNA governed nothing that shipped.

The consequence was measured, and it is the reason this file exists. The
reference constitution has declared the CNC sheet-goods kit path since it was
written -- the shell is cut flat, bent and stitched, never laid into a mould --
and the search never saw it. On the flagship mission:

    ungoverned: roundness > 0 on 60 of 60 draws (median 0.541)
                `unroll.hull_panels` REFUSED 60 of 60
    governed  : roundness 0 on 30 of 30, unroll ACCEPTED 30 of 30

The ungoverned product was searching, validating, badging and RANKING a design
space that is entirely unbuildable in the one material it is made of, and
finding out at the shop door.

STITCH AND GLUE is what `construction=sheet-developable` means concretely:
flat plywood panels, edge-drilled and wired together, filleted and taped on the
seams, then sheathed in epoxy and glass cloth. `engineer.assess` already
quantifies that sheathing (`epoxy_kg`, EPOXY_KG_PER_M2 = 1.4 approx). The
geometric precondition is DEVELOPABILITY -- a flat sheet bends but does not
stretch, so a radiused bilge is not a two-panel developable shell, and
`roundness` must be 0. That is a BOUND on the search, not a filter after it.

THE SEARCH BUDGET IS NOT DECORATIVE. MEASURED on the flagship mission, front
size against budget:

    budget                governed, unbounded roundness    governed, bounded
    pop 24  x 10 gens                 3                            0
    pop 48  x 40 gens                28                           25
    pop 64  x 80 gens                62                           64

At the legacy demo's 24 x 10 a governed run returns an EMPTY front, which reads
as "no valid designs" when the truth is "the search was too short". The default
here is the budget at which the bounded and unbounded fronts agree. Lowering it
is a false economy that produces a confident wrong answer.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from navalai import grammar, unroll
from navalai.certify import certify
from navalai.cfd.case import hull_to_stl
from navalai.engineer import assess as engineer_assess
from navalai.evaluate import evaluate
from navalai.geometry import Hull
from navalai.optimize import pareto_front
from navalai.limits import REFOLD_BAR_MM
from navalai.policy import reference_policy
from navalai.translate import translate

MISSION = ("6 tonne solar-electric liveaboard, 10 m, Danube and Black Sea "
           "coastal, cruise 5 knots, 2 crew, 40 kWh battery")

# The measured agreement point of the table in this module's docstring.
POP, GENS = 64, 80


# THE STATION COUNT THE REFINEMENT SCORES ON, and it is the whole fix.
#
# MEASURED 2026-08-21: scoring on the ladder's 41 stations produced TWO hulls
# stamped buildable that the station family refuses (4.92/5.22/8.71 and
# 4.84/3.88/3.95). At n=41 the panel is a 40-segment polyline and part of every
# reading is its SAGITTA, so a search rewarded for driving that number down
# optimises the DISCRETISATION instead of the curvature. It is not a subtle
# effect: a surface with Gaussian curvature 7.8e-14 reads 17.1 mm at n=41.
#
# Scoring at the FINEST count removes the incentive rather than policing it
# afterwards — there is no sagitta left to harvest. It costs 3.7x:
#
#     n= 41   1.52 s/hull
#     n= 81   2.84 s/hull
#     n=161   5.62 s/hull
#
# That is the price of searching for the thing instead of for its shadow.
#
# DERIVED, never typed: it is the finest member of the family the verdict is
# read over, so the search and the gate cannot drift apart. A literal 161 here
# would be the same number declared twice.
_REFINE_STATIONS = max(unroll.REFOLD_COUNTS)


def _refine(x0, mission, policy, box, budget_s, seed, max_steps=0,
):
    """(1+1)-ES on the AUTHORITATIVE refold meter, subject to the full ladder.

    Lexicographic: feasibility first, then refold. A step that breaks the
    ladder is never accepted, so the hull that comes out is a hull the ladder
    passed AND whose panels are measured to close — not a buildable shape that
    happens to sink, which is exactly what an unconstrained refold search
    returns (measured: 3.900 mm at GM -0.35 m, i.e. it capsizes).
    """
    lo = np.array(box.low, float)
    hi = np.array(box.high, float)
    width = hi - lo                 # EXACTLY zero on a pinned gene, on purpose:
                                    # an epsilon here puts roundness at 1e-13
                                    # and `hull_panels` refuses `> 0.0`
                                    # strictly — measured, it rejected 600 of
                                    # 600 draws.
    rng = np.random.default_rng(seed + 1)

    def score(x):
        try:
            if not grammar.check(x).ok:
                return (1e6, 1e6)
            ev = evaluate(x, mission, policy=policy)
            if not ev.ok or ev.energy is None:
                viol = sum(max(0.0, min(v, 1e3))
                           for v in (ev.g or {}).values())
                return (viol if viol > 0 else 1.0, 1e6)
            # SCORED ON THE FINEST COUNT, AND THE FAMILY IS THE DEFENCE.
            #
            # MEASURED 2026-08-22: a single count is gameable AT ANY COUNT. The
            # score moved from n=41 to n=161 to kill the sagitta exploit, and
            # the search promptly found a new one — a hull reading 38.86 /
            # 39.58 / 2.23 / 40.04 mm at 41 / 81 / 161 / 321. About 40 mm
            # everywhere except the single count being optimised.
            #
            # THE OBVIOUS FIX DOES NOT WORK, and it was tried and measured
            # rather than reasoned about: scoring the WORST of (41, 161) would
            # make acceptance unreachable, because n=41 reads high for GOOD
            # hulls by design — that is the polyline sagitta. Every hull this
            # lane has actually delivered scores 10.9-18.4 mm on worst-of-two
            # against a 5 mm gate:
            #
            #     m06  family (13.5, 6.01, 3.09)  PASSES -> worst-of-two 13.50
            #     m08  family (18.4, 1.79, 1.47)  PASSES -> worst-of-two 18.40
            #     s11  family (10.93, 9.52, 2.31) PASSES -> worst-of-two 10.93
            #
            # So the defence stays where it already was and where it already
            # works: `accept` confirms every candidate on the FAMILY, which
            # refused the exploit above before it could be stamped. The cost is
            # a wasted budget when the search chases a resonance — a
            # performance problem, not a wrong answer, and the near-miss file
            # now records what it chased.
            h = Hull(x, n_stations=_REFINE_STATIONS)
            r = max(float(np.max(unroll.refold_surface_deviation_mm(h, pan)))
                    for pan in unroll.hull_panels(h))
            return (0.0, r)
        except Exception:
            return (1e6, 1e6)

    def verdict_of(x):
        """The FAMILY verdict — the only thing that decides buildability.

        MEASURED 2026-08-21 and it is why this function exists. Scoring the
        refinement on the 41-station number alone produced a hull reading
        4.92 / 5.22 / 8.71 mm at 41 / 81 / 161: UNDER the bar at the count it
        was optimised against, and RISING. It gamed the metric. Part of every
        41-station reading is a 40-segment polyline's sagitta -- a surface with
        Gaussian curvature 7.8e-14 reads 17.1 mm there -- so a single count is
        a number and only a family is a verdict.

        The cheap score above still DRIVES the search, because the family costs
        several times more per step. This confirms the winner.
        """
        try:
            return unroll.refold_convergence(grammar.named(x),
                                             bar_mm=REFOLD_BAR_MM)
        except Exception as exc:                                # noqa: BLE001
            # SAY SO. MEASURED 2026-08-22: this returned a bare None and
            # `accept` prints its reason only when the verdict is not None, so
            # a candidate that REACHED 2.2 mm against a 5 mm bar was refused
            # with no rejection line, no reason and no trace — the run simply
            # ended saying "no member unrolls within 5 mm" while the search had
            # found one. An error rendering as a decision, for the third time
            # in this file today.
            print(f"    family check FAILED on a {best[1]:.2f} mm candidate: "
                  f"{type(exc).__name__}: {exc} — this is an ERROR, not a "
                  f"verdict, and the candidate is neither accepted nor "
                  f"honestly refused")
            return None

    t0 = time.time()
    best, bx = score(np.asarray(x0, float)), np.asarray(x0, float).copy()

    # SEED PHASE, and it is not optional. MEASURED 2026-08-21, same mission,
    # same box, same refiner: seeded from the lowest-ENERGY front member
    # (refold 120.3 mm) it did not reach the bar in 900 s; seeded from the best
    # of a random sweep (refold 38.37 mm) it reached 4.952 mm in ~335 s.
    #
    # The seed dominates because the buildable region is TINY -- 3 of 400
    # random draws clear 5 mm -- and a local search started 120 mm away spends
    # its whole budget walking. Cheapest fix by far: sweep the box first on the
    # lexicographic score and start from the best point found, so the ES begins
    # inside the right basin instead of proving it can walk.
    # A DRAW TARGET WITH A TIME CEILING, not a pure time box. MEASURED
    # 2026-08-22: the same 300 s sweep on the same mission did 35086 draws on a
    # quiet machine and 22958 under a concurrent CFD campaign — 35% fewer — and
    # the best it found went from 7.3 mm to 29.9 mm. The lane then delivered a
    # 1.92 mm boat in the first case and REFUSED THE MISSION in the second.
    #
    # Search quality became a function of machine load, which is the wrong
    # thing to make load-dependent: the same request answered differently
    # depending on what else the box happened to be doing. Draws are the unit
    # of search here, so the sweep now counts them, and the time cap is a
    # CEILING that keeps a loaded machine from spending the whole budget
    # seeding rather than a target it silently falls short of.
    sweep_draws = 35000
    sweep_s = min(0.6 * budget_s, 900.0)
    n_sweep = 0
    # NO BASIN RESTART. It was built, measured over three arms at a fixed
    # 280-step budget on five seeds, and it LOSES:
    #
    #     seed   no restart   capped restart   uncapped
    #       11     2.31 ok        refused        11.1
    #       23     5.9           3.88 ok         3.88 ok
    #       37     8.8           5.9            26.8
    #       51     4.59 ok       8.9            24.9
    #       67     5.2          14.8            11.6
    #            ---------      ---------      ---------
    #              2 of 5        1 of 5         1 of 5
    #
    # It kills two boats to rescue one. The idea was sound — escape a basin
    # that is dead — but a 40-step silence cannot tell a DEAD basin from a SLOW
    # one, and getting that wrong costs more than getting it right saves. Seeds
    # 11 and 51 were descending perfectly well and were dragged out of it.
    #
    # Recorded rather than deleted silently so it is not reinvented: the
    # missing piece is a stall test that measures whether the basin is still
    # yielding, not merely whether it has been quiet.
    while n_sweep < sweep_draws and time.time() - t0 < sweep_s:
        cand = lo + rng.random(len(lo)) * width
        s_ = score(cand)
        n_sweep += 1
        if s_ < best:
            best, bx = s_, cand
    print(f"    seed sweep: {n_sweep} draws"
          f"{'' if n_sweep >= sweep_draws else f' (TIME-CAPPED short of {sweep_draws})'}"
          f", best {'infeasible' if best[0] > 0 else f'{best[1]:.1f} mm'}")

    def accept(x):
        """Is this candidate feasible, under the bar, AND family-confirmed?

        MEASURED 2026-08-22 and this function exists because it was not one.
        The acceptance test used to live INSIDE the ES's improvement branch
        (`if s < best:`), so a candidate found by the SEED SWEEP was never
        tested: if no mutation subsequently beat it, the loop simply ran to the
        end of its budget and returned None. On the 8 m / 3 t mission the sweep
        found a hull at **1.5 mm** against a 5 mm bar and the lane REFUSED the
        mission, printing "the search does not aim at buildability" while
        holding the answer.
        """
        if best[0] != 0.0 or best[1] > REFOLD_BAR_MM:
            return None
        conv = verdict_of(x)
        if conv is not None and conv.verdict == "PASSES":
            return x, evaluate(x, mission, policy=policy), float(conv.finest_mm)
        if conv is not None:
            print(f"    n={_REFINE_STATIONS} said {best[1]:.2f} mm but the "
                  f"family {tuple(round(v, 2) for v in conv.worst_mm)} is "
                  f"{conv.verdict} — rejected, continuing")
        return None

    got = accept(bx)
    if got is not None:
        return got, best, bx

    # STEP-BOUNDED, NOT WALL-CLOCK BOUNDED, when a step budget is given.
    #
    # MEASURED 2026-08-22 and it invalidated an A/B I had already run twice.
    # `while time.time() - t0 < budget_s` makes the number of ES steps depend
    # on machine load, so a FIXED rng seed does NOT reproduce a run: seed 11
    # delivered 2.31 mm twice and 8.00 mm on a third attempt with a
    # byte-identical seed sweep (35000 draws, best 7.3 mm both times) and the
    # restart firing zero times. Nothing in the algorithm differed. The step
    # COUNT did.
    #
    # That makes "2 of 5 against k of 5" a comparison of two different
    # experiments — the change under test is confounded with however many steps
    # each run happened to get. Any reliability number quoted from a wall-clock
    # budget is a statement about the machine as much as the search.
    #
    # Wall-clock stays the DEFAULT because a user wants a bounded wait; a step
    # budget is what an experiment must use.
    sigma = 0.10
    steps = 0
    while ((steps < max_steps) if max_steps else
           (time.time() - t0 < budget_s)):
        steps += 1
        cand = np.clip(bx + rng.normal(0, sigma, len(lo)) * width, lo, hi)
        s = score(cand)
        if s < best:
            best, bx, sigma = s, cand, min(sigma * 1.2, 0.25)
            got = accept(bx)
            if got is not None:
                return got, best, bx
        else:
            sigma = max(sigma * 0.995, 0.004)
    return None, best, bx


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="design_kit")
    ap.add_argument("--mission", default=MISSION)
    ap.add_argument("--out", default="data/exports/kit")
    ap.add_argument("--pop", type=int, default=POP)
    ap.add_argument("--gens", type=int, default=GENS)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--refine-s", type=float, default=900.0,
                    help="seconds of buildability refinement when no "
                         "front member unrolls within the bar")
    ap.add_argument("--refine-steps", type=int, default=0,
                    help="bound the refinement by ES STEPS instead of "
                         "seconds. Wall-clock is the default because a "
                         "user wants a bounded wait; an EXPERIMENT must "
                         "use steps, or the step count varies with machine "
                         "load and a fixed seed stops reproducing")
    ap.add_argument("--no-escalate", action="store_true",
                    help="refuse an empty front instead of retrying "
                         "at a larger budget (diagnostic)")
    ap.add_argument("--no-refine", action="store_true",
                    help="skip refinement and report the refusal")
    ap.add_argument("--ungoverned", action="store_true",
                    help="compile NO constitution. Kept so the difference is "
                         "demonstrable rather than asserted -- it is not a "
                         "supported way to produce a kit")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    m = translate(a.mission)
    print(f"MISSION: {a.mission}")
    print(f"spec: {m.displacement_target_kg:.0f} kg, {m.cruise_speed_kn} kn, "
          f"category {m.design_category}")

    policy = None if a.ungoverned else reference_policy()
    if policy is None:
        print("\nCONSTITUTION: none (--ungoverned). The search is NOT bounded "
              "to buildable hulls and the kit stage is expected to refuse.")
    else:
        dna = policy.constitution.dna
        box = policy.box(m.design_category)
        j = box.names.index("roundness")
        print(f"\nCONSTITUTION: {policy.constitution.name}")
        print(f"  construction : {dna.construction.value}  -> shell must be "
              f"developable")
        print(f"  roundness box: [{box.low[j]:.3g}, {box.high[j]:.3g}]  "
              f"(grammar allows [0, 1])")
        print(f"  appended rows: {list(policy.rows)}")
        for e in box.edits:
            print(f"  bound        : {e.param} {e.edge} {e.was:.4g} -> "
                  f"{e.now:.4g}")

    print(f"\nNSGA-II under the box (pop {a.pop} x {a.gens} gens) ...")
    res = pareto_front(m, pop=a.pop, gens=a.gens, seed=a.seed, policy=policy)
    X = np.atleast_2d(res.X)
    # AN EMPTY FRONT IS A BUDGET SYMPTOM BEFORE IT IS A VERDICT, so escalate
    # once before refusing. MEASURED 2026-08-22 on the 6 m / 1400 kg / cat D
    # dayboat, where the feasible region is 0.8% of the governed box (32 of
    # 4000 draws pass the full ladder — `gm` and `rules` bind, a small boat is
    # tender against category D's 0.35 m GM floor):
    #
    #     pop  24 x  20 gens =    480 evals -> front   0   <- the old default
    #     pop  48 x  40 gens =   1920 evals -> front  17
    #     pop  64 x  80 gens =   5120 evals -> front  29
    #     pop  96 x 120 gens =  11520 evals -> front  96
    #
    # At 0.8% density a 24-member initial population is all-infeasible with
    # probability ~0.82, so NSGA-II never gets a foothold and reports an empty
    # front for a mission that has 96 answers. Refusing there told the user
    # their boat is impossible when the truth was that the search was too
    # small — the same shape as the roundness episode, one level up.
    if X.size == 0 and not a.no_escalate:
        big_pop, big_gens = max(a.pop * 2, 48), max(a.gens * 4, 80)
        print(f"  empty front at pop {a.pop} x {a.gens} — ESCALATING to "
              f"pop {big_pop} x {big_gens} before refusing")
        res = pareto_front(m, pop=big_pop, gens=big_gens, seed=a.seed,
                           policy=policy)
        X = np.atleast_2d(res.X)
    if X.size == 0:
        print("EMPTY FRONT after escalation — no design satisfied the "
              "constraints. This is a REFUSAL, not a kit. The binding rows "
              "are worth reading before concluding the mission is "
              "impossible: a tender small craft usually fails `gm` against "
              "its category floor, which is a MISSION problem (more beam, "
              "less height) and not a search one.")
        return 2
    scored = [(evaluate(x, m, policy=policy), x) for x in X]
    scored = [(ev, x) for ev, x in scored if ev.ok and ev.energy]
    if not scored:
        print("front returned but nothing passed the full ladder — REFUSED")
        return 2

    # ---- STAGE 2: VERIFY BUILDABILITY ON THE FRONT ------------------------
    #
    # Refold accuracy is the only thing that decides whether these panels can
    # be cut, and it CANNOT be a constraint inside NSGA-II: MEASURED, it costs
    # 2301 ms per hull against `grammar.check`'s 0.27 ms -- 8561x -- so a
    # pop-64 x 80-gen run would spend 3.3 hours on it.
    #
    # The obvious cheap proxy DOES NOT WORK and that is recorded here rather
    # than discovered again: `Hull.panel_twist_rate()` is 122319x cheaper and
    # correlates with refold at **+0.089** over 30 governed hulls (Spearman
    # +0.224). A criterion that does not separate is not a criterion.
    # `buildability.shell_complexity(...).non_developable_frac` DOES correlate
    # (+0.783) and costs 1.8 ms, which is ~9 s across a whole NSGA-II run --
    # that is the number to steer with if this is ever moved inside the search.
    #
    # So the front is verified with the AUTHORITATIVE meter instead: 64
    # members x 2.3 s = ~147 s, paid once. The product then delivers a hull
    # whose panels are MEASURED to close, or it refuses and says by how much.
    print(f"\nfront {len(X)}; verifying refold on {len(scored)} ladder-valid "
          f"member(s) (~{2.3 * len(scored):.0f} s) ...")
    verified = []
    refined = False
    refine_best = None
    refine_x = None
    best_miss = (float("inf"), None)
    for e, xx in scored:
        try:
            w = max(float(np.max(unroll.refold_surface_deviation_mm(Hull(xx), pan)))
                    for pan in unroll.hull_panels(Hull(xx)))
        except ValueError:
            continue
        if w <= REFOLD_BAR_MM:
            verified.append((e, xx, w))
        elif w < best_miss[0]:
            best_miss = (w, e)
    if not verified and not a.no_refine:
        # ---- STAGE 3: BUILDABILITY REFINEMENT ----------------------------
        #
        # This is the stage that makes the tool produce boats instead of
        # reporting that it cannot. NSGA-II optimises the mission; NOTHING in
        # its objectives or constraints is buildability, so it lands in the
        # buildable region only by accident. MEASURED on the flagship mission:
        #
        #     NSGA-II governed front          0 of N under the 5 mm bar
        #     400 random draws in the box     3 under the bar (0.75%)
        #     refold-targeted (1+1)-ES        FOUND ONE: 4.952 mm, GM +2.545 m,
        #                                     zero ladder violations
        #
        # So the search direction is the whole difference, and the ONLY meter
        # that can supply it is the authoritative one. Two cheap proxies were
        # measured and BOTH FAILED to separate, which is why this stage pays
        # 2.3 s a step instead of steering for free:
        #
        #     Hull.panel_twist_rate()   0.02 ms   r = +0.089
        #     shell_complexity().ndev   1.80 ms   r = +0.460 over N=400
        #         and at its most selective useful threshold (ndev <= 0.005)
        #         only 33% of hulls clear the bar, while the three measured
        #         passers span ndev 0.0019..0.0816 — so a bar tight enough to
        #         steer EXCLUDES TWO OF THE THREE KNOWN SOLUTIONS.
        #
        # A criterion that does not separate is not a criterion. Refinement on
        # the real meter is slower and it is the one that works.
        print(f"  no front member is buildable (best {best_miss[0]:.1f} mm) — "
              f"REFINING on the authoritative meter for up to "
              f"{a.refine_s:.0f} s ...")
        seed_ev, seed_x = min(scored, key=lambda t: t[0].energy.wh_per_nm)
        got, refine_best, refine_x = _refine(
            seed_x, m, policy, box, a.refine_s, a.seed, a.refine_steps)
        if got is not None:
            x, ev, worst_ok = got
            verified = [(ev, x, worst_ok)]
            refined = True
            print(f"  REFINED to {worst_ok:.2f} mm — buildable, ladder-valid")

    if not verified:
        # REPORT WHAT THE SEARCH REACHED, NOT WHAT THE FRONT HAD. MEASURED
        # 2026-08-22 in the reliability sweep: this line printed the FRONT's
        # best -- computed before refinement ever ran -- so a run whose ES had
        # reached 6.3 mm against a 5 mm bar reported "Best was 80.1 mm". A
        # reader would conclude the search was 16x away when it was within
        # 1.3x, and would go looking for a different hull instead of a longer
        # budget.
        reached = (refine_best[1] if refine_best is not None
                   and refine_best[0] == 0.0 and refine_best[1] < 1e5
                   else None)
        # HAND BACK THE NEAR MISS. A refusal that keeps its best hull to itself
        # cannot be investigated: MEASURED 2026-08-22, a run reported "the
        # refinement reached 2.2 mm" against a 5 mm bar and then discarded the
        # hull, so the reason it was refused anyway could not be reproduced
        # without re-running the whole search. The closest candidate is the
        # single most useful artefact a failed run has.
        if refine_best is not None and refine_best[0] == 0.0 \
                and refine_best[1] < 1e5 and refine_x is not None:
            import json as _json
            (out / "near_miss.json").write_text(_json.dumps({
                "why": "refused — kept for inspection, NOT a deliverable",
                "refold_mm_at_finest": float(refine_best[1]),
                "bar_mm": float(REFOLD_BAR_MM),
                "params": [float(v) for v in refine_x],
                "named": {k: float(v) for k, v in
                          grammar.named(refine_x).items()},
            }, indent=1))
            print(f"  near miss saved -> {out}/near_miss.json "
                  f"({refine_best[1]:.2f} mm) — inspect it rather than "
                  f"re-running the search")
        print(f"  NO MEMBER unrolls within {REFOLD_BAR_MM:.0f} mm. "
              f"Front's best {best_miss[0]:.1f} mm"
              + (f"; the refinement reached {reached:.1f} mm"
                 if reached is not None else
                 "; the refinement found nothing feasible") + ".")
        print("  REFUSED — this is Gate 6D, and a cut file is not produced.")
        # AND DO NOT SAY "RAISE THE BUDGET". That was this script's first
        # message here and it is WRONG: NSGA-II's objectives and constraints
        # contain no buildability term at all, so more generations search
        # harder for the same thing and never for this one. MEASURED — a
        # seaworthy hull at 4.952 mm refold, GM +2.545 m, zero ladder
        # violations, EXISTS in this grammar and was found by a dedicated
        # refold search, not by a longer NSGA-II run.
        print("  The space is NOT empty: a seaworthy hull at 4.952 mm refold "
              "with GM +2.545 m and zero violations was measured in this same "
              "governed box (2026-08-21).")
        print("  The search simply does not AIM at buildability — there is no "
              "such term in its objectives or constraints — so a bigger "
              "budget will not find it. What is owed is STEERING: "
              "buildability.shell_complexity(...).non_developable_frac "
              "correlates +0.783 with refold and costs 1.8 ms, i.e. ~9 s "
              "across a whole pop-64 x 80-gen run. Hull.panel_twist_rate() is "
              "cheaper still and does NOT work (+0.089).")
        return 3
    ev, x, worst_ok = min(verified, key=lambda t: t[0].energy.wh_per_nm)
    print(f"  {len(verified)}/{len(scored)} member(s) verified buildable; "
          f"selected one refolds to {worst_ok:.2f} mm")
    p = grammar.named(x)
    # NOT "selected lowest-energy hull" any more. When stage 3 runs, this hull
    # was REFINED and is not a member of the front at all -- saying otherwise
    # would be a label that survived the change beneath it, which is the defect
    # class this repository keeps catching.
    print(f"HULL ({'refined for buildability' if refined else 'selected from the front, lowest energy'}):")
    print(f"  LWL {p['LWL']:.2f} m · BWL {p['BWL']:.2f} m · T {p['T']:.2f} m "
          f"· deadrise {p['beta_mid']:.1f}° · roundness {p['roundness']:.4f}")
    print(f"  displacement {ev.hydro.disp_kg:.0f} kg | GM {ev.gm_m:.2f} m | "
          f"Rt {ev.resistance.total:.0f}±{ev.resistance.uncertainty:.0f} N | "
          f"{ev.energy.wh_per_nm:.0f} Wh/NM")

    hull = Hull(x)

    # --- the geometry a mesher / viewer sees -------------------------------
    stl = out / "hull.stl"
    sha = hull_to_stl(hull, stl, wl=ev.wl)
    print(f"\nSTL: {stl}  sha256 {sha[:16]}…")

    # --- G-VISUAL: the canonical views, ALWAYS (2026-08-27) ----------------
    # Every recorded shape incident was found by a human opening a file
    # after delivery; the fixed view set + descriptor sheet now ship WITH
    # the deliverable so the looking happens before the handoff, and a
    # refused shape is SEEN, not only read (MORPHOLOGY-V1.md §6).
    from navalai.views import canonical_views
    sheet = canonical_views(hull, out / "views", name="hull")
    print(f"views: {out / 'views'}  critique_ok={sheet['critique_ok']}"
          + ("" if sheet["critique_ok"] else
             f"  findings={sheet['findings']}"))

    # --- the stitch-and-glue panels ----------------------------------------
    try:
        panels = unroll.hull_panels(hull)
    except ValueError as exc:
        print(f"\nKIT REFUSED: {exc}")
        print("This is the refusal the constitution exists to prevent. It is "
              "reported, not worked around.")
        return 3
    print(f"\nSTITCH AND GLUE: {len(panels)} developable panel(s)")
    # REPORTED AGAINST ITS BAR, because a millimetre figure with no bar beside
    # it reads as a pass. This is Gate 6D, which is RED and ledgered: the
    # two-sided distance from the REFOLDED panel back onto the hull's moulded
    # surface, against BuildPlan 12.3's 5 mm. A panel that misses by this much
    # is not yet a cut file a shop should trust.
    # REPORT THE FAMILY, NOT THE LADDER'S COUNT. This block used to print the
    # per-panel deviation at the default 41 stations and label anything over
    # 5 mm "OVER the bar / GATE 6D RED" — directly above a cut-file header
    # reading REFOLD VERIFIED 1.92 mm, PASSES. Two verdicts on one screen, and
    # the alarming one was the wrong instrument: at n=41 part of every reading
    # is the panel polyline's sagitta, which is exactly what
    # `refold_convergence` exists to separate out.
    fam = unroll.refold_convergence(grammar.named(x), bar_mm=REFOLD_BAR_MM)
    for pan in panels:
        print(f"  {pan.name}")
    print(f"  refold family {fam.counts} -> "
          f"{tuple(round(v, 2) for v in fam.worst_mm)} mm   "
          f"verdict {fam.verdict}")
    if fam.verdict == "PASSES":
        print(f"  converged to {fam.finest_mm:.2f} mm against the "
              f"{REFOLD_BAR_MM:.0f} mm bar — the falling trend is the coarse "
              f"count's sagitta, not curvature")
    else:
        print(f"  GATE 6D: {fam.verdict} — the panels below are GEOMETRY, not "
              f"a release-grade cut file. Gate 6D stays RED regardless: it is "
              f"about the DEFAULT path (measured 0 of 7), not about a search "
              f"job that found one.")

    # CONSUME the ladder's derived scantling; do NOT also pass mldc_kg.
    # `assess` refuses both, by name: two sources for one number is the defect
    # that parameter exists to close, and it caught this script on its first
    # run. The 2026-08-20 incident it guards is a BOM cut to 18.0 mm while the
    # same ladder run derived 15.0 mm.
    eng = engineer_assess(hull, wl=ev.wl,
                          bottom_thickness_m=ev.ply_thickness_m)
    print(f"\nKIT: {eng.ply_sheets} ply sheets, nest utilisation "
          f"{eng.nest_utilisation * 100:.1f}%")
    print(f"  bottom {eng.bottom_thickness_mm:.0f} mm (ISO 12215-5 derived)")
    print(f"  epoxy {eng.epoxy_kg:.0f} kg (sheathing + fillets + coats, "
          f"approx) · build {eng.build_hours:.0f} h")
    print(f"  BOM {len(eng.bom)} line items")

    # ---- THE CUT FILE, from the SAME nest the BOM was read off ----------
    #
    # MEASURED 2026-08-21: re-deriving the nest for the exporter (rebuilding
    # from `_shell_parts` and forgetting `fixed` — deck, transom, eight
    # bulkheads) produced a DXF with 84 outlines against a BOM of 186
    # sheet-good parts. 102 parts the builder is told to cut were not drawn.
    # `EngineerReport` now carries `layout`, so there is one nest and the
    # question cannot be asked twice.
    dxf = out / "cut.dxf"
    try:
        unroll.export_dxf(eng.layout, dxf, ev=ev, hull=hull)
        drawn = set(unroll.parse_dxf_polylines(dxf))
        drawn = {k for k in drawn if not k.startswith("SHEET-")}
        want = {b.part for b in eng.bom if b.sheet is not None}
        if want - drawn:
            print(f"\n  CUT FILE INCOMPLETE: {len(want - drawn)} BOM part(s) "
                  f"are not drawn — REFUSED as a kit")
            return 4
        print(f"\nCUT FILE: {dxf}  ({len(drawn)} part outlines over "
              f"{eng.layout.sheets} sheets, every BOM part drawn)")
        print(f"  header: {dxf.read_text().splitlines()[1]}")
    except ValueError as exc:
        print(f"\nCUT FILE REFUSED: {exc}")
        return 3

    cert = certify(x, m, policy=policy)
    (out / "certification.json").write_text(json.dumps({
        "mission": a.mission,
        "constitution": (None if policy is None
                         else policy.constitution.name),
        "params": [float(v) for v in x],
        "stl_sha256": sha,
        "cut_file": str(dxf),
        "ply_sheets": eng.ply_sheets,
        "verdict": getattr(cert, "verdict", None),
        "bom": [b.as_dict() for b in eng.bom],
    }, indent=1, default=str))
    print(f"\nwrote {out}/certification.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
