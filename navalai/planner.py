"""The planner: which experiment next, and is it worth what it costs.

The brief asked for a planner that "maximises engineering information gained
per CPU-hour". That is a real, well-posed thing — it is Bayesian experimental
design — and it is implementable in about a page because this project already
has the two hard prerequisites: a tiered ladder with honest per-tier
uncertainty, and a measured cost model (`fidelity.py`).

WHAT MAKES THIS MORE THAN A LOOKUP TABLE
========================================
The planner scores every candidate experiment by expected information gain per
unit cost. For a Gaussian belief the gain has a closed form, so no sampling is
needed:

    posterior precision  1/s_post^2 = 1/s_prior^2 + 1/s_exp^2
    information gain     I = ln(s_prior / s_post)          [nats]
    score                I / cost

`I` is the KL divergence from posterior to prior for two Gaussians with the
same mean, which is the standard expected-information-gain objective. Three
consequences fall out of it that a hand-written rule table would get wrong:

  - An experiment more uncertain than what you already believe scores ~0. Once
    L2 has pinned a quantity to 5%, an L1 estimate at 25% adds essentially
    nothing, and the planner stops proposing it WITHOUT anyone writing that
    rule down.
  - Diminishing returns are automatic. The second identical CFD run gains
    ln(sqrt(2)) = 0.35 nats where the first gained much more.
  - Refusing to answer is a first-class outcome. An experiment that cannot
    address the question contributes zero information at positive cost, so it
    is never selected — which is how "do I actually need CFD?" gets answered
    by arithmetic instead of by a maintained list of exceptions.

WHAT IT DELIBERATELY DOES NOT DO
================================
It does not choose a geometric scale. `similitude.py` establishes that scale is
not a cost variable in this pipeline (identical cell count at 2.3 m and 230 m),
so a search over it would be a search over a variable with no effect on the
objective — it would return an arbitrary answer and dress it as an optimum.
Scale is chosen by what you are comparing against, and it is an input here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from .fidelity import Budget, CostEstimate, FidelitySpec, MAC_M5, Refusal, admit
from .similitude import Condition

# --- what the ladder can be asked, and what each rung actually knows ---------
# `sigma_rel` is the ONE-SIGMA RELATIVE uncertainty a tier delivers on a
# quantity. These are the project's own recorded bands, not new numbers:
#   L1 resistance: `resistance.total_resistance` returns 0.25*Rw + 0.10*Rf,
#     which is ~25% on a wave-dominated hull — the band the module documents.
#   L1 GM: `evaluate` badges GM with the mass model's own propagated sigma.
#   L3 resistance: Gate 2M's measured miss against KRISO EFD was -15.4% on the
#     old mesh. Until the new mesh produces a number, 15% is what this tier has
#     EARNED, and claiming better would be the soft-green the honesty rules
#     forbid. Lower it when Gate 2M measures lower — not before.
TIER_SIGMA_REL: dict[tuple[str, str], float] = {
    ("L0", "feasible"): 0.00,
    ("L1", "displacement"): 0.06,
    ("L1", "gm"): 0.15,
    ("L1", "resistance"): 0.25,
    ("L1", "trim"): 0.30,
    ("L2", "resistance"): 0.18,
    ("L2", "seakeeping"): 0.20,
    ("L3", "resistance"): 0.15,
    ("L3", "sinkage_trim"): 0.15,
    ("L3", "wake"): 0.25,
    ("R", "compliance"): 0.00,
}

# Wall-clock seconds for the non-CFD tiers. L0/L1 are MEASURED: `evaluate()`
# carries `eval_ms` and Gate 1 holds it under 50 ms. L2 is a Capytaine BEM
# solve, minutes. L3 is not listed — it is priced by `fidelity.estimate` from
# the measured cell-step rate, because it is the only tier whose cost depends
# on how you configure it.
TIER_COST_S: dict[str, float] = {"L0": 0.001, "L1": 0.05, "L2": 300.0, "R": 0.5}


@dataclass(frozen=True)
class Belief:
    """What is currently known about one quantity: a Gaussian, plus its tier.

    `scale` breaks a degeneracy found in adversarial review. Experiment
    uncertainties are RELATIVE, so `sigma = sigma_rel * value` collapses to
    zero for any quantity whose current estimate is zero — and a zero sigma is
    perfect knowledge. A belief centred on zero (a trim angle, a list angle, a
    residuary coefficient near a hump crossing) would therefore be declared
    exactly known by any experiment at all, and every target on it satisfied
    vacuously without running anything. `scale` is the magnitude a relative
    uncertainty is taken against: the value, unless the value is negligible
    against `scale`, in which case `scale`.
    """

    quantity: str
    value: float
    sigma: float                # ABSOLUTE, same units as value
    tier: str = "prior"
    scale: float = 0.0          # 0 => use |value|; set it for near-zero values

    @property
    def magnitude(self) -> float:
        """The magnitude a RELATIVE uncertainty is taken against."""
        return max(abs(self.value), abs(self.scale))

    @property
    def sigma_rel(self) -> float:
        m = self.magnitude
        return self.sigma / m if m > 0.0 else float("inf")


@dataclass(frozen=True)
class Experiment:
    """A candidate run. `answers` is the set of quantities it informs."""

    name: str
    tier: str
    answers: frozenset[str]
    cost_s: float
    sigma_rel: dict[str, float]
    spec: FidelitySpec | None = None
    refusals: tuple[Refusal, ...] = ()
    cost: CostEstimate | None = None

    @property
    def admissible(self) -> bool:
        return not self.refusals


def information_gain(prior_sigma: float, exp_sigma: float) -> float:
    """Expected information gain [nats] from one Gaussian observation.

        I = ln(sigma_prior / sigma_posterior),
        1/sigma_post^2 = 1/sigma_prior^2 + 1/sigma_exp^2

    Returns 0.0, never negative: an observation cannot make a Gaussian belief
    less certain. A zero-sigma (exact) experiment returns infinite gain, which
    is correct — an L0 feasibility check or a rules verdict really does settle
    its question outright — and callers must handle it, so `plan` scores those
    tiers by cost alone rather than dividing by infinity.
    """
    if prior_sigma <= 0.0:
        return 0.0                      # already known exactly
    if exp_sigma <= 0.0:
        return math.inf
    post = 1.0 / math.sqrt(1.0 / prior_sigma**2 + 1.0 / exp_sigma**2)
    return max(math.log(prior_sigma / post), 0.0)


def observation_sigma(prior: Belief, sigma_rel: float,
                      value: float | None = None) -> float:
    """Absolute one-sigma an experiment of relative precision `sigma_rel` gives.

    Taken against `Belief.magnitude`, never against a bare value — see the
    Belief docstring for why a zero-centred quantity would otherwise be
    declared exactly known by any experiment whatsoever.
    """
    m = max(abs(value), abs(prior.scale)) if value is not None else prior.magnitude
    return sigma_rel * m


def update(prior: Belief, tier: str, sigma_rel: float,
           value: float | None = None) -> Belief:
    """Bayesian update of a Gaussian belief by one experiment's result.

    The posterior MEAN is the precision-weighted average, so a sharp new result
    moves the estimate and a vague one barely does. If `value` is None the mean
    is kept and only the sigma tightens — the "what would this experiment buy
    me" question, asked before running it.
    """
    s_exp = observation_sigma(prior, sigma_rel, value)
    new_value = prior.value if value is None else value
    if s_exp <= 0.0:
        # A genuinely exact tier (L0 feasibility, a rules verdict). Only
        # reachable when sigma_rel is itself zero, never by a zero magnitude.
        return Belief(prior.quantity, new_value, 0.0, tier, prior.scale)
    if prior.sigma <= 0.0:
        return prior
    wp, we = 1.0 / prior.sigma**2, 1.0 / s_exp**2
    mean = prior.value if value is None else (wp * prior.value + we * value) / (wp + we)
    return Belief(prior.quantity, mean, 1.0 / math.sqrt(wp + we), tier,
                  prior.scale)


def candidates(cond: Condition, quantities: frozenset[str],
               budget: Budget = MAC_M5,
               densities: tuple[float, ...] = (0.5, 0.7071, 1.0, 1.414),
               ) -> list[Experiment]:
    """Every experiment that could inform `quantities`, priced.

    The cheap tiers are priced from the table; every L3 configuration is priced
    by `fidelity.estimate` from the measured cell-step rate and carries its own
    admissibility refusals, so an unaffordable grid stays in the list with its
    reason attached instead of vanishing.
    """
    out: list[Experiment] = []
    for tier, cost_s in TIER_COST_S.items():
        ans = {q for (t, q) in TIER_SIGMA_REL if t == tier} & quantities
        if not ans:
            continue
        out.append(Experiment(
            name=tier, tier=tier, answers=frozenset(ans), cost_s=cost_s,
            sigma_rel={q: TIER_SIGMA_REL[(tier, q)] for q in ans}))
    ans3 = {q for (t, q) in TIER_SIGMA_REL if t == "L3"} & quantities
    if ans3:
        for d in densities:
            spec = FidelitySpec(mesh_density=d)
            ok, refusals, cost = admit(cond, spec, budget)
            out.append(Experiment(
                name=f"L3 RANS @ density {d:g}", tier="L3",
                answers=frozenset(ans3), cost_s=cost.wall_s,
                # A finer grid earns a tighter band, but not without limit: the
                # tier's floor is set by the WALL MODEL and the fixed
                # first-layer thickness, which no amount of outer-flow
                # refinement improves. Discretisation error shrinks with
                # density; modelling error does not.
                sigma_rel={q: max(TIER_SIGMA_REL[("L3", q)] / d ** 0.5,
                                  0.60 * TIER_SIGMA_REL[("L3", q)])
                           for q in ans3},
                spec=spec, refusals=refusals, cost=cost))
    return out


@dataclass
class Plan:
    """An ordered set of experiments, with what each is expected to buy."""

    question: str
    target_sigma_rel: float
    steps: list[tuple[Experiment, str, float, float]] = field(default_factory=list)
    beliefs: dict[str, Belief] = field(default_factory=dict)
    rejected: list[tuple[Experiment, str]] = field(default_factory=list)
    total_cost_s: float = 0.0
    satisfied: bool = False

    def report(self) -> str:
        lines = [f"question: {self.question}",
                 f"target: {self.target_sigma_rel * 100:.0f}% one-sigma"]
        if not self.steps:
            lines.append("  (no experiment selected)")
        for exp, q, gain, cost in self.steps:
            g = "exact" if math.isinf(gain) else f"{gain:.2f} nats"
            lines.append(f"  {exp.name:24s} -> {q:14s} {g:>10s}  "
                         f"{cost / 3600:8.2f} h")
        for q, b in sorted(self.beliefs.items()):
            lines.append(f"  belief {q:14s} {b.value:12.4g} +/- "
                         f"{b.sigma_rel * 100:5.1f}%  [{b.tier}]")
        lines.append(f"  total {self.total_cost_s / 3600:.2f} h; "
                     f"{'TARGET MET' if self.satisfied else 'TARGET NOT MET'}")
        for exp, why in self.rejected:
            lines.append(f"  rejected {exp.name}: {why}")
        return "\n".join(lines)


def plan(question: str, quantities: frozenset[str], priors: dict[str, Belief],
         target_sigma_rel: float = 0.10, budget: Budget = MAC_M5,
         cond: Condition | None = None, max_steps: int = 6) -> Plan:
    """Greedily pick experiments by information gain per second until the target.

    Greedy is the right algorithm here and not a shortcut: information gain in
    this Gaussian model is submodular (each experiment buys less once others
    have run), so the greedy sequence is within a constant factor of the
    optimal set, and it re-plans after every step against the updated belief.

    Stops for one of three honest reasons, all recorded on the Plan:
      - the target is met (`satisfied=True`) — including the case where it was
        ALREADY met by the priors and nothing needs to run at all;
      - nothing admissible is left inside the budget;
      - no remaining experiment gains anything (every one is vaguer than what
        is already believed).
    """
    cond = cond or Condition(lwl=7.2786, speed=2.196)
    p = Plan(question=question, target_sigma_rel=target_sigma_rel,
             beliefs=dict(priors))
    pool = candidates(cond, quantities, budget)
    for exp in pool:
        if not exp.admissible:
            p.rejected.append((exp, "; ".join(str(r) for r in exp.refusals)))

    def met() -> bool:
        return all(p.beliefs[q].sigma_rel <= target_sigma_rel
                   for q in quantities if q in p.beliefs)

    if met():
        p.satisfied = True
        return p

    used: set[str] = set()
    for _ in range(max_steps):
        best = None
        for exp in pool:
            if not exp.admissible or exp.name in used:
                continue
            if p.total_cost_s + exp.cost_s > budget.max_wall_s:
                continue
            # Score the experiment by the TOTAL gain over every quantity it
            # informs, not by its best single quantity. An experiment's cost is
            # paid once; charging it separately per quantity — or, worse,
            # retiring it after crediting only one — made the planner buy an
            # L1 run for resistance and then buy a SECOND tier for displacement
            # that the same L1 had already delivered for free. Found in
            # adversarial review.
            gains: dict[str, float] = {}
            for q in exp.answers:
                if q not in p.beliefs:
                    continue
                prior = p.beliefs[q]
                if prior.sigma_rel <= target_sigma_rel:
                    continue        # this one is already good enough
                g = information_gain(
                    prior.sigma, observation_sigma(prior, exp.sigma_rel[q]))
                if g > 1e-9:
                    gains[q] = g
            if not gains:
                continue
            total_gain = sum(gains.values())
            # An exact experiment is scored by cost alone; dividing inf by a
            # cost would rank all exact tiers equal regardless of price.
            score = (1e9 / max(exp.cost_s, 1e-9) if math.isinf(total_gain)
                     else total_gain / max(exp.cost_s, 1e-9))
            if best is None or score > best[0]:
                best = (score, exp, gains)
        if best is None:
            break
        _, exp, gains = best
        for q, gain in sorted(gains.items()):
            p.beliefs[q] = update(p.beliefs[q], exp.tier, exp.sigma_rel[q])
            p.steps.append((exp, q, gain, exp.cost_s if q == min(gains) else 0.0))
        p.total_cost_s += exp.cost_s
        used.add(exp.name)
        if met():
            p.satisfied = True
            break
    return p


# --- the "do I actually need CFD?" table, as data ---------------------------
# The brief's most valuable single idea. Each question names the quantities it
# needs; the planner then discovers the cheapest sufficient tier from the
# uncertainty arithmetic rather than from a hard-coded solver choice. A question
# whose quantities no CFD tier answers will never select CFD, because CFD's
# information gain on it is exactly zero.
QUESTION_QUANTITIES: dict[str, frozenset[str]] = {
    "static buoyancy": frozenset({"displacement"}),
    "initial stability": frozenset({"gm", "displacement"}),
    "calm-water resistance": frozenset({"resistance"}),
    "range and endurance": frozenset({"resistance", "displacement"}),
    "sinkage and trim": frozenset({"sinkage_trim", "trim"}),
    "wake quality": frozenset({"wake"}),
    "seakeeping": frozenset({"seakeeping"}),
    "rule compliance": frozenset({"compliance"}),
}


def plan_for(question: str, priors: dict[str, Belief], **kw) -> Plan:
    """Plan by NAME of the engineering question."""
    if question not in QUESTION_QUANTITIES:
        raise KeyError(f"unknown question {question!r}; "
                       f"known: {sorted(QUESTION_QUANTITIES)}")
    return plan(question, QUESTION_QUANTITIES[question], priors, **kw)
