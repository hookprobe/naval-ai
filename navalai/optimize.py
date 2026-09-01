"""Phase 1 baseline optimizer: NSGA-II directly on grammar parameters (pymoo).

BuildPlan: "Baseline optimizer: NSGA-II directly on grammar parameters (no
learning needed yet)." Objectives are mission-level: energy per mile, build
material, stability margin. Constraints come from the ladder itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.core.repair import Repair
from pymoo.core.sampling import Sampling
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from . import grammar
from .energy import shell_area_m2
from .evaluate import CONSTRAINT_NAMES, INFEASIBLE_G, evaluate
from .geometry import GeometryError, Hull, cp_band, lcb_band


class _DrawBoxSampling(Sampling):
    """Initialise inside the FROZEN DRAW box, not the full legal envelope.

    2026-08-26: the legal envelope widened (Cp to 0.95, r_transom to 0.92,
    beta_mid to 38 deg) and pymoo's default FloatRandomSampling over it
    left pop-48 populations with ~0 feasible members — the front came back
    EMPTY for the panel's own default brief. The DRAW box is the measured-
    feasible region every seeded stream samples; starting there and letting
    crossover/mutation walk outward (the repair below keeps the walk
    consistent) searches the widened envelope without starting lost in it.
    """

    def _do(self, problem, n_samples, **kwargs):
        # FEASIBLE initialisation via the grammar's own rejection sampler:
        # a uniform draw — even inside the DRAW box — is only a few percent
        # L0-valid, and at pop 16 that leaves 0-1 feasible members and a
        # front that sometimes comes back empty (measured, order-flaky).
        # Determinism: THIS pymoo threads a PRIVATE `random_state` through
        # operators (Algorithm.setup: `self.random_state =
        # np.random.default_rng(self.seed)`) — global np.random is never
        # reseeded, and drawing from it made two identically-seeded fronts
        # differ (measured, (8,23) vs (4,23) back to back). Derive the
        # sampler's Generator from the passed random_state.
        rs = kwargs.get("random_state")
        seed_int = (int(rs.integers(2 ** 31)) if rs is not None
                    else np.random.randint(2 ** 31))
        rng = np.random.default_rng(seed_int)
        X = grammar.sample(n_samples, rng)
        # THE MISSION'S REQUESTED ARCHITECTURE (2026-09-01). `grammar.sample`
        # draws the FROZEN LEGACY BOX, in which every architecture gene is
        # pinned at zero — so a brief saying "protected prop" produced a front
        # whose chosen hull had tun_w = tun_crown = tun_len = 0 while
        # `propulsion` was asked to score its tunnel drive. MEASURED by the
        # end-to-end flow trace, one commit after `sample_valid` learned to
        # draw the same bundle: two production design routes, one able to
        # express the architecture the mission declared and the other not.
        #
        # DRAWN FROM A SPAWNED GENERATOR and ONLY when a feature was asked
        # for, exactly as the exploring stream does it, so every mission that
        # requests none consumes this stream bit-identically to before —
        # which is what keeps the seeded fixtures and sealed manifests
        # standing.
        # HALF the population, on the ODD rows, so it is DISJOINT from the
        # shape-feasible climb below (which takes the even ones) and so the
        # search still explores from the legacy distribution — the same
        # argument, and the same split, the climb already makes. MEASURED and
        # this is why it is a half and not all: seeding EVERY member with a
        # tunnel returned an EMPTY front on the houseboat brief, because a
        # tunnelled hull loses ~1/3 of its flotation solutions (the crown
        # scales with the DESIGN draft and these hulls float at ~57% of it),
        # and the population had no un-tunnelled members left to survive on.
        _feat = grammar.features_for(getattr(problem, "mission", None))
        if _feat:
            _brng = np.random.default_rng(int(rng.integers(2 ** 31)))
            for _row in X[1::2]:
                grammar.apply_feature_bundles_inplace(_row, _brng, _feat)
        # P5 RETRIEVAL SEEDING (2026-08-27). A mission that DECLARES a hull
        # family starts up to a quarter of its population from the parent
        # library, distorted to the brief (homothetic rescale to the stated
        # dims + band-projected Cp/lcb — `navalai.parents`). Research row
        # "variation of a parent": below ~10^3 corpus hulls, retrieval +
        # low-dimensional distortion beats any learned generator, and it
        # starts the search where a naval architect would — on a proven
        # hull of the right KIND. GATED ON `hull_family` so every
        # family-less mission (including all seeded fixtures) consumes the
        # RNG stream bit-identically to before this landed.
        mission = getattr(problem, "mission", None)
        if getattr(mission, "hull_family", None):
            from .parents import seed_for_mission
            S = seed_for_mission(
                mission, max(1, n_samples // 4),
                np.random.default_rng(int(rng.integers(2 ** 31))))
            # ON EVEN ROWS, so every parent seed is covered by the
            # shape-feasibility climb below (which visits `range(0, len(X),
            # 2)`). MEASURED 2026-09-01: `seed_for_mission` distorts a
            # critic-CLEAN parent into critic-REJECTED seeds — the
            # `liveaboard-barge` parent scores ok=True / 1.000, and of three
            # seeds homothetically rescaled from 15.2 x 4.0 m to the brief's
            # 16 x 4 m, TWO are refused (plan_waist 0.135 against the barge
            # bar of 0.120; waterline_convexity 0.585 against 0.700). The
            # barge band was calibrated just outside that one parent's own
            # values (waist 0.105 -> 0.12), so a 5% rescale walks out of it.
            # Placing the seeds where the climb can see them is the fix that
            # uses machinery already here; the knife-edge band is recorded as
            # a risk, not silently widened.
            for k in range(len(S)):
                j = 2 * k
                if j < len(X):
                    X[j] = S[k]
        # SHAPE-FEASIBLE SEEDING (2026-08-27). `grammar.sample` draws the
        # legacy stream, whose every member is a lens hull the `shape` row
        # refuses — MEASURED at the server's live budget (pop 48, 15
        # gens): the panel's own default mission returned an EMPTY front,
        # because a population that starts 100% shape-infeasible has 15
        # generations to find a region SBX cannot see. Half the initial
        # population is climbed to plausibility by the directed repair
        # (`morphology_search.search`, the critic-guided operator); the
        # other half stays raw so the search still explores from the
        # legacy distribution. Deterministic: the climb's rng derives from
        # the same seeded stream.
        from .geometry import GeometryError as _GErr
        from .geometry import Hull as _Hull
        from .morphology import critique as _crit
        from .morphology import describe as _desc
        from .morphology import from_hull as _fh
        from .morphology_search import search as _climb
        # THE CLIMB JUDGES BY THE MISSION'S FAMILY, because the row it is
        # repairing does. MEASURED 2026-09-01: both this test and
        # `morphology_search.inspect` used the GENERAL monohull bands while
        # `evaluate`'s `shape` row uses `_FAMILY_BAR[mission.hull_family]`,
        # and on a barge the two differ on exactly the three descriptors that
        # table exists to relax (plan_waist 0.12 vs 0.02, waterline_convexity
        # 0.70 vs 0.80, pmb_frac 0.98 vs 0.90). The repair was climbing toward
        # a criterion the ladder does not score.
        _fam = getattr(mission, "hull_family", None)
        for i in range(0, len(X), 2):
            try:
                if _crit(_desc(_fh(_Hull(X[i]))), family=_fam).ok:
                    continue
            except (_GErr, ValueError):
                continue
            g = dict(zip(grammar.NAMES, map(float, X[i])))
            # AND INSIDE THE BOX THIS POPULATION WILL BE CLIPPED INTO.
            # MEASURED 2026-09-01: the climb reached plausibility on 9 of 9
            # seeds and the `np.clip` below destroyed ALL NINE, because it
            # searched the grammar box and was then forced into the mission's
            # (LWL 14.4-17.6, BWL 3.6-4.4, plus the Froude window on Cp).
            # Repairing a hull and then moving it is not repairing it.
            best, _ = _climb(g, iterations=60,
                             rng=np.random.default_rng(
                                 int(rng.integers(2 ** 31))),
                             family=_fam,
                             bounds=(np.asarray(problem.xl, float),
                                     np.asarray(problem.xu, float)))
            if best is not None:
                X[i] = grammar.vector(best.genome)
        lo = np.asarray(problem.xl, float)
        hi = np.asarray(problem.xu, float)
        return np.clip(X, lo, hi)


class _SacConsistencyRepair(Repair):
    """Project (Cp, lcb) into the band the fullness genes can DELIVER.

    The corrected sac solve (audit finding D.4) refuses a (Cp, pmb, r_stem)
    request the family cannot reach — honest at L0, wasteful in a search:
    an SBX/PM offspring that moves pmb without moving Cp is dead on
    arrival. This is the same projection `morphology_search._clip` applies,
    for the same reason a designer re-fairs Cp/LCB after moving fullness.
    """

    def _do(self, problem, X, **kwargs):
        X = np.atleast_2d(np.asarray(X, float))
        iC = grammar.NAMES.index("Cp")
        iL = grammar.NAMES.index("lcb")
        g = {n: grammar.NAMES.index(n)
             for n in ("LWL", "x_mb", "r_transom", "r_stem", "pmb")}
        lo, hi = np.asarray(problem.xl, float), np.asarray(problem.xu, float)
        for row in X:
            try:
                b_lo, b_hi = cp_band(row[g["LWL"]], row[g["x_mb"]],
                                     row[g["r_transom"]], row[g["r_stem"]],
                                     row[g["pmb"]])
            except (GeometryError, ValueError):
                continue
            eps = 1e-3 * max(b_hi - b_lo, 1e-6)
            row[iC] = min(min(b_hi - eps, hi[iC]),
                          max(max(b_lo + eps, lo[iC]), row[iC]))
            try:
                l_lo, l_hi = lcb_band(row[g["LWL"]], row[g["x_mb"]],
                                      row[g["r_transom"]], row[iC],
                                      row[g["r_stem"]], row[g["pmb"]])
            except (GeometryError, ValueError):
                continue
            eps = 1e-2 * max(l_hi - l_lo, 1e-6)
            row[iL] = min(min(l_hi - eps, hi[iL]),
                          max(max(l_lo + eps, lo[iL]), row[iL]))
        return X
from .mission import MissionSpec, mission_cp_band


def _score(x, mission: MissionSpec, policy, names, provenance=None):
    """One design through the ladder -> (F_row, G_row), or None to REJECT.

    THE ONE SCORING BODY for both problems (they had drifted into two
    transcribed copies — R0.2e). None means "leave the caller's infeasible
    defaults standing" (F = 1e9, G = INFEASIBLE_G), the same Fitness = inf
    pattern the L0 reject has always used.

    `ev.ok` IS CONSULTED (R0.2a — audit G6-01). The refusal classes that are
    deliberately NOT constraint rows — `early` (speed outside the L1 model),
    the multihull stability refusal, the manning refusals — used to leave
    every g row satisfied, so NSGA-II ranked the design FEASIBLE and a
    multihull front arrived 100% ok=False (audit G6-02). They are still not
    rows: the E4 finding stands (a constant row carries no gradient while
    occupying a dimension, and would change the vector's shape for
    monohulls). Instead a design that is refused WITHOUT a positive g row is
    rejected outright here. A design whose refusal IS a g row keeps its row —
    that is the gradient NSGA-II descends out of the infeasible region — and
    constraint domination already keeps it from dominating any feasible one.
    """
    ev = evaluate(x, mission, policy=policy, provenance=provenance)
    if ev.tier == "L0" or ev.hydro is None or ev.energy is None:
        return None
    if not ev.ok and not any(ev.g[k] > 0.0 for k in names if k in ev.g):
        return None
    hull = Hull(x)
    # Build material is the VESSEL's, not one moulded surface's (R0.2c —
    # audit: the inline copy missed the hull count). `shell_area_m2` is the
    # single home of the planked-to-the-sheer integral (gap C9); the bridge
    # deck contributes nothing because the genome does not carry one, which
    # is already a recorded caveat in `ev.vessel`.
    n_hulls = int(ev.vessel.get("n_hulls", 1))
    build_area = n_hulls * (shell_area_m2(hull) + hull.deck_area())
    # OBJECTIVE 3 REWORKED (P2-A, 2026-08-27 — audit finding #4/#20). The
    # GM-band term charged a wide shallow hull for the large GM it
    # inevitably has (`gm_mid` scales with beam), and `build_area` already
    # prices the deck as pure COST — together the search was paid to avoid
    # exactly the boats the missions describe. The gm FLOOR row still
    # guards stability (it always did), the ceiling stays what limits.py
    # says it is (a report — "a genuinely beamy shallow hull can exceed it
    # for good reasons"), and the third objective becomes DECK
    # EFFICIENCY: build area per m^2 of usable deck. Minimising it rewards
    # a hull that turns material into deck — the entire product value of a
    # houseboat — without unbounded growth, because objective 2 still
    # prices the material itself and the trade-off tension the front test
    # pins (area rises with length, energy falls) is untouched.
    deck = max(float(hull.deck_area()), 1e-6)
    f_row = (ev.energy.wh_per_nm, build_area, build_area / deck)
    g_row = [ev.g[k] for k in names]
    return f_row, g_row


class HullProblem(Problem):
    """3 objectives: min Wh/NM, min build panel area (m^2), min build area
    per m^2 of usable deck (deck efficiency — see the P2-A rework in _score).
    Inequality constraints (g <= 0) are the ladder's own — CONSTRAINT_NAMES —
    plus, when a compiled constitution is passed, that policy's appended rows.
    """

    def __init__(self, mission: MissionSpec, length_tol: float = 0.10,
                 policy=None, provenance=None):
        self.mission = mission
        # WHAT THE SEARCH TOUCHED IS RECORDED (R0.2f — audit: three provenance
        # mechanisms existed and the optimizer wrote to none of them). None
        # keeps the un-recorded run identical to what it always was.
        self.provenance = provenance
        # GOVERNANCE REACHES THE SEARCH, NOT ONLY THE LADDER (BuildPlan 3 §2.2).
        # `policy` is an optional COMPILED constitution
        # (`navalai.policy.compile_policy` / `reference_policy`). It is
        # keyword-usable, defaults to None, and every line that touches it sits
        # behind `if policy is not None` — so an ungoverned run executes the
        # identical code it executed before governance existed, which is what
        # Gate V3.0(d) has to mean for the optimizer as well as for `evaluate`.
        #
        # A compiled policy supplies BOTH of the compiler's outputs here:
        #   (1) `box(category)` becomes xl/xu, so `LOA <= 12 m` is a BOUND the
        #       population is constructed inside. MEASURED on the reference SKU
        #       at category C (pop 24, 8 generations, seed 5): the ungoverned
        #       search drew 143 of 192 individuals above the 11.9 m ceiling and
        #       floated every one of them through L1 before `policy_legal`
        #       rejected it; the governed search drew 0. A bound checked only on
        #       the returned front is a rejection wearing a bound's name.
        #   (2) `constraint_names()` sizes and fills G, so the policy rows
        #       constrain NSGA-II exactly the way the ladder's own rows do —
        #       the same reason `CONSTRAINT_NAMES` is read here and not
        #       re-listed.
        self.policy = policy
        self.constraint_names = (tuple(CONSTRAINT_NAMES) if policy is None
                                 else tuple(policy.constraint_names()))
        # THE MISSION'S LENGTH IS A SEARCH BOUND, not decoration.
        # `lwl_hint_m` was parsed, range-clamped, prompted for and asserted in
        # two tests while being READ BY NOTHING. Measured end to end: a mission
        # saying "10 m" produced an 18.58 m hull (+86%), "5 m" produced 15.57 m
        # (+211%), and 0 of 40 Pareto members were within 10% of the stated
        # length. The cause is structural: Wh/NM falls monotonically with
        # length and nothing in the objective costs length, so the search runs
        # to the grammar's 20 m ceiling every time.
        xl, xu = grammar.LOW.copy(), grammar.HIGH.copy()
        if policy is not None:
            # The grammar's own bounds go IN and the governed ones come out.
            # `box` only ever moves an edge inward (max on the low edge, min on
            # the high), so this cannot widen the search — the ratchet law on
            # output (1).
            xl, xu = policy.box(mission.design_category,
                                low=xl, high=xu).as_bounds()
        # The widest box that survives governance. The hint is clamped against
        # THIS, not against the grammar, so the two compose by INTERSECTION:
        # whichever of hint and policy is tighter on an edge wins, and a hint
        # that would widen a governed edge cannot, because `min`/`max` below
        # start from the governed value.
        box_lo, box_hi = xl.copy(), xu.copy()
        hint = mission.lwl_hint_m
        i = grammar.NAMES.index("LWL")
        if hint:
            xl[i] = max(xl[i], hint * (1.0 - length_tol))
            xu[i] = min(xu[i], hint * (1.0 + length_tol))
            if xl[i] > xu[i]:
                # The hint's window does not meet the box at all — a 16 m hint
                # under an 11.9 m ceiling. There is no intersection to take, so
                # the hint is dropped and the BOX stands. Dropping the box
                # instead would let a mission string loosen governance, and
                # falling back to `grammar.LOW/HIGH` (which is what this line
                # did when the grammar was the only box) would do exactly that.
                xl[i], xu[i] = box_lo[i], box_hi[i]
        # THE BEAM BINDS THE SAME WAY THE LENGTH DOES (P2-A, 2026-08-27).
        # "i have asked for a 4m width boat" was parsed, refused as a
        # length hint (correctly) and then DROPPED — no field existed. It
        # exists now, and it composes with governance by the identical
        # intersection law: tighter edge wins, an empty intersection drops
        # the hint with the box left standing.
        bhint = getattr(mission, "bwl_hint_m", None)
        jb = grammar.NAMES.index("BWL")
        if bhint:
            xl[jb] = max(xl[jb], bhint * (1.0 - length_tol))
            xu[jb] = min(xu[jb], bhint * (1.0 + length_tol))
            if xl[jb] > xu[jb]:
                xl[jb], xu[jb] = box_lo[jb], box_hi[jb]
        # THE MISSION CHOOSES THE PRISMATIC (R1.1). Same composition law as
        # the length hint: intersection with whatever box survives
        # governance, so a target that would widen a governed edge cannot,
        # and a window that misses the box entirely is dropped with the box
        # left standing. Computed AFTER the LWL intersection so the Fn
        # window reflects the lengths the search can actually draw.
        band = mission_cp_band(mission, float(xl[i]), float(xu[i]))
        if band is not None:
            j = grammar.NAMES.index("Cp")
            lo, hi = max(xl[j], band[0]), min(xu[j], band[1])
            if lo <= hi:
                xl[j], xu[j] = lo, hi
        # Constraint values (and therefore the GM floor, the freeboard floor
        # and the bend limit) come from evaluate() — see CONSTRAINT_NAMES, plus
        # the compiled policy's appended rows when there is one.
        super().__init__(n_var=grammar.N_PARAMS, n_obj=3,
                         n_ieq_constr=len(self.constraint_names),
                         xl=xl, xu=xu)

    def _evaluate(self, X, out, *_args, **_kwargs):
        names = self.constraint_names
        F = np.full((len(X), 3), 1e9)
        Gc = np.full((len(X), len(names)), INFEASIBLE_G)
        self._seen = getattr(self, "_seen", 0) + len(X)
        for i, x in enumerate(X):
            # Constraints come from the ladder itself, so a check added there
            # (trim and list, most recently) constrains the search immediately
            # instead of producing optima the ladder then rejects. With a
            # compiled policy `names` is CONSTRAINT_NAMES + that policy's rows,
            # in `Evaluation.g_names` order, so a governance row constrains
            # NSGA-II by the same mechanism and with no second code path.
            scored = _score(x, self.mission, self.policy, names,
                            provenance=self.provenance)
            if scored is not None:
                F[i], Gc[i] = scored
        self._tally(names, Gc)
        out["F"] = F
        out["G"] = Gc

    def _tally(self, names, Gc) -> None:
        """Count which constraint rows BOUND, so an empty front can say why.

        AN EMPTY FRONT WITH NO EXPLANATION IS THE WORST ANSWER THIS PRODUCT
        GIVES. MEASURED 2026-09-01 on the brief "6 m dinghy with an outboard,
        8 knots, 900 kg": 720 evaluations, 0 designs, and an empty array
        returned to the caller. The information the user needs was computed
        720 times and thrown away every time — `motor_power` bound on 497 of
        them and was the WORST row on 373, because a 6 m hull at 8 kn is
        Fn 0.536 and a 15 kW motor's 12 kW continuous rating cannot push it.
        With the engine raised to 60 kW the answer changes to `rules`,
        `gm`, `prop_space` and `bend_radius`, which is a DIFFERENT and equally
        actionable sentence.

        Counting is all this does: `violated` is how many candidates each row
        refused, `worst` is how many times it was the row furthest from
        satisfaction. Neither is a verdict about the brief — it is the
        arithmetic the caller needs to write one.
        """
        b = getattr(self, "_binding", None)
        if b is None:
            b = self._binding = {"violated": {n: 0 for n in names},
                                 "worst": {n: 0 for n in names},
                                 "evaluated": 0, "feasible": 0}
        G = np.asarray(Gc, float)
        b["evaluated"] += G.shape[0]
        pos = G > 0.0
        b["feasible"] += int((~pos.any(axis=1)).sum())
        for j, n in enumerate(names):
            b["violated"][n] += int(pos[:, j].sum())
        rows = np.flatnonzero(pos.any(axis=1))
        if rows.size:
            for j in np.asarray(G[rows].argmax(axis=1)).ravel():
                b["worst"][names[int(j)]] += 1


class LatentHullProblem(Problem):
    """Same objectives/constraints as HullProblem, explored in the 8-D genome
    (original plan Phase 4: 'the optimizer explores the latent space')."""

    def __init__(self, mission: MissionSpec, genome, z_range: float = 2.5,
                 policy=None, provenance=None):
        self.mission = mission
        self.genome = genome
        self.provenance = provenance
        # Output (2) only, and the asymmetry is the point rather than an
        # omission: the decision variables here are the 8-D genome, and the
        # parameter box is a box in GRAMMAR space. `genome.decode` is what
        # produces the parameters, so there is no bound on z that expresses
        # `LWL <= 11.9 m`. This is precisely the case the compiler's docstring
        # names — "a design can enter the ladder from a saved genome, a latent
        # decode or a hand-written array, none of which passed through the box"
        # — and it is why the policy emits a ROW as well as a bound. Here the
        # row is the whole of the enforcement, so it does the whole of the work.
        self.policy = policy
        self.constraint_names = (tuple(CONSTRAINT_NAMES) if policy is None
                                 else tuple(policy.constraint_names()))
        q = genome.W.shape[1]
        super().__init__(n_var=q, n_obj=3,
                         n_ieq_constr=len(self.constraint_names),
                         xl=-z_range * np.ones(q), xu=z_range * np.ones(q))

    def _evaluate(self, Z, out, *_args, **_kwargs):
        X = self.genome.decode(Z)              # gate-projected to feasibility
        names = self.constraint_names
        F = np.full((len(X), 3), 1e9)
        Gc = np.full((len(X), len(names)), INFEASIBLE_G)
        for i, x in enumerate(X):
            scored = _score(x, self.mission, self.policy, names,
                            provenance=self.provenance)
            if scored is not None:
                F[i], Gc[i] = scored
        out["F"] = F
        out["G"] = Gc


@dataclass
class ParetoResult:
    X: np.ndarray
    F: np.ndarray          # (wh_per_nm, build_area_m2, |GM - band middle|)
    n_evals: int
    #: WHY, when X is empty — and useful even when it is not. See
    #: `HullProblem._tally`: {"violated": {row: n}, "worst": {row: n},
    #: "evaluated": n, "feasible": n}. Empty dict when nothing was tallied,
    #: which is honest: it means no candidate reached the constraint vector,
    #: never that nothing bound.
    binding: dict = field(default_factory=dict)

    def why_empty(self) -> str:
        """One sentence a user can act on, or '' when the front is not empty.

        Names the row that refused the most designs and the row that was
        furthest from satisfaction, because they are DIFFERENT questions and
        the answer to the second is usually the lever.
        """
        if len(self.X) or not self.binding:
            return ""
        b = self.binding
        worst = sorted(b["worst"].items(), key=lambda kv: -kv[1])
        viol = sorted(b["violated"].items(), key=lambda kv: -kv[1])
        worst = [(k, v) for k, v in worst if v]
        viol = [(k, v) for k, v in viol if v]
        if not viol:
            return (f"no design satisfied the brief, and no constraint row "
                    f"was ever reached — every one of {b['evaluated']} "
                    f"candidates was refused before the ladder built its "
                    f"constraint vector (an L0 or flotation refusal).")
        return (f"no design satisfied the brief in {b['evaluated']} "
                f"candidates. The row furthest from satisfaction was "
                f"{worst[0][0]!r} on {worst[0][1]} of them"
                + (f"; the row that refused the most was {viol[0][0]!r} on "
                   f"{viol[0][1]}" if viol[0][0] != worst[0][0] else "")
                + f". Full count: "
                + ", ".join(f"{k}={v}" for k, v in viol[:6]) + ".")


def _front(res, n_var: int) -> tuple[np.ndarray, np.ndarray]:
    """(X, F) as float arrays — EMPTY when the run found nothing feasible.

    pymoo returns `res.X is None` when no individual satisfied every
    constraint, and `np.atleast_2d(None)` is an OBJECT array holding one None.
    That is a front of one design whose every parameter is None: it has a
    length, it indexes, and it reaches the caller looking like a result. It was
    reachable before governance and is reachable more often after it, because a
    compiled policy is exactly what makes the feasible set small enough to miss
    at a small budget — MEASURED on the reference SKU at category C, pop 16 /
    5 gens, seed 5. An empty front says "no feasible design" in a way a `for`
    loop can act on; the None row says it in a TypeError three call frames
    later, which is where this was found.

    Wherever a real front exists this is `np.atleast_2d` and nothing else, so
    an ungoverned run that found designs returns bit-identical arrays.
    """
    if res.X is None:
        return np.zeros((0, n_var)), np.zeros((0, 3))
    return np.atleast_2d(res.X), np.atleast_2d(res.F)


def pareto_front(mission: MissionSpec, pop: int = 40, gens: int = 30,
                 seed: int = 1, policy=None, provenance=None) -> ParetoResult:
    """`policy` is an optional compiled constitution; None is the ungoverned
    search, unchanged. `provenance` is an optional `db.Provenance`; every
    ladder evaluation the search makes is recorded to it (R0.2f). See
    `HullProblem.__init__`."""
    problem = HullProblem(mission, policy=policy, provenance=provenance)
    algo = NSGA2(pop_size=pop, sampling=_DrawBoxSampling(),
                 repair=_SacConsistencyRepair())
    res = minimize(problem, algo, get_termination("n_gen", gens), seed=seed,
                   verbose=False)
    X, F = _front(res, problem.n_var)
    return ParetoResult(X, F, pop * gens,
                        binding=getattr(problem, "_binding", {}) or {})


def pareto_front_latent(mission: MissionSpec, genome, pop: int = 40,
                        gens: int = 30, seed: int = 1,
                        policy=None, provenance=None) -> ParetoResult:
    """NSGA-II in the 8-D genome; returns decoded (feasible) designs."""
    problem = LatentHullProblem(mission, genome, policy=policy,
                                provenance=provenance)
    algo = NSGA2(pop_size=pop)
    res = minimize(problem, algo, get_termination("n_gen", gens), seed=seed,
                   verbose=False)
    Z, F = _front(res, problem.n_var)
    if len(Z) == 0:
        return ParetoResult(np.zeros((0, grammar.N_PARAMS)), F, pop * gens)
    return ParetoResult(genome.decode(Z), F, pop * gens)
