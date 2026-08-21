"""EXPERIMENT (forensics section-26, C-25): the Phase-2 agentic island.
Test-only — no production entrypoint imports this module. It becomes
LIVE only via a wired, gated entrypoint (its own plan item), not by
silently importing it somewhere. The agentic PLM network — async message passing.The agentic PLM network (original plan, Phase 2) — async message passing.

Four agents, typed messages, an auditable trail:

  Orchestrator  mission text -> MissionSpec; delegates; collects; stops
  Builder       emits ONLY parameter vectors (grammar mutations / genome
                samples) — it structurally cannot touch vertices
  Validator     the gatekeeper: L0 type-check + L1 ladder; failure =>
                Fitness = inf, candidate dies before costing anything more
  Engineer      materials, panels, interior volume, build hours

Design stance (BuildPlan 1.5 + HookProbe C9): the deterministic solvers stay
deterministic; 'agent' here is an isolation + audit + async-throughput shell,
not an LLM. The LLM seam remains only in mission translation (translate.py).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .engineer import EngineerReport, assess
from .evaluate import Evaluation, evaluate, sample_valid
from .geometry import Hull
from .hull_ast import (HullDesign, Typology, fit_typology, infer_typology,
                       type_check)
from .latent import Genome
from .mission import MissionSpec
from .translate import grade, requirements_from_mission, translate


@dataclass(frozen=True)
class Message:
    sender: str
    recipient: str
    kind: str                 # 'candidate' | 'validated' | 'rejected' | 'engineered' | 'stop'
    payload: Any
    t: float = field(default_factory=time.monotonic)


@dataclass
class DesignRecord:
    params: np.ndarray
    evaluation: Evaluation
    engineering: EngineerReport
    requirements: dict
    fitness: float
    # Which typology the Validator's L0 type-check actually accepted. It used
    # to be nowhere on the record because the check could not reject anything
    # (see `_validator`), so there was no accepted typology to name.
    typology: str = ""


class Audit:
    def __init__(self) -> None:
        self.trail: list[Message] = []

    def log(self, msg: Message) -> None:
        self.trail.append(msg)

    def flows(self) -> list[tuple[str, str, str]]:
        return [(m.sender, m.recipient, m.kind) for m in self.trail]


async def _builder(inbox: asyncio.Queue, out: asyncio.Queue, audit: Audit,
                   genome: Genome, batch: int) -> None:
    seed = 0
    while True:
        req = await inbox.get()
        if req.kind == "stop":
            return
        seed += 1
        X = genome.sample(batch, seed=seed, temperature=1.0)
        for x in X:
            # THE BUILDER PROJECTS ONTO A TYPOLOGY; IT DOES NOT LEAVE THE
            # VALIDATOR TO REJECT A DRAW FOR A PARAMETER THE TYPOLOGY *SETS*.
            #
            # `TYPOLOGY_RULES` carries two kinds of rule (see `hull_ast.Pin`): a
            # BAND, which the sampler is expected to satisfy sometimes, and a
            # PIN, which the typology fixes. `roundness` is pinned at 0 for both
            # sheet-built typologies because a filleted bilge is not developable
            # from flat sheet. It used to be a band — (0.0, 0.15) and (0.0,
            # 0.25) — and a continuous sampler hits the one admissible point in
            # those bands with probability ZERO. MEASURED 2026-08-13 over 4096
            # draws of this exact genome (seed 17 fit, `sample(4096, seed=1)`):
            # **4** vectors type-checked as any typology and NOT ONE had
            # `roundness == 0`, so every design that reached the Engineer was
            # refused by `unroll.hull_panels`, and `run_plm` delivered ZERO.
            # Projecting the pin here takes the same 4096 draws to **1594**.
            #
            # A projection is a generative act and belongs on this side of the
            # queue. Nothing is softened downstream: the Validator still runs
            # the strict `infer_typology` on what arrives, and a draw whose
            # BANDS (Cp, forefoot, rocker, sheer_rise, beta_bow) miss every
            # typology is forwarded UNPROJECTED so the Validator refuses it and
            # the audit trail records why.
            fit = fit_typology(x)
            if fit is not None:
                x = fit[1]
            msg = Message("builder", "validator", "candidate", x)
            audit.log(msg)
            await out.put(msg)


async def _validator(inbox: asyncio.Queue, out: asyncio.Queue, audit: Audit,
                     mission: MissionSpec, policy=None) -> None:
    while True:
        msg = await inbox.get()
        if msg.kind == "stop":
            return
        x = msg.payload
        # THE L0 TYPE-CHECK COULD NOT REJECT ANYTHING. It read
        #
        #     rep = type_check(HullDesign.from_vector(x, Typology.SHARP_CHINE))
        #     ev = evaluate(x, mission) if rep.ok or grammar.check(x).ok else None
        #
        # and `type_check` ends by appending `grammar.check(...).violations` to
        # its own list (hull_ast.py:168-169), so `rep.ok` IMPLIES
        # `grammar.check(x).ok` and the disjunction is identically
        # `grammar.check(x).ok`. The typology arm was inert. MEASURED over
        # 200,000 uniform in-box vectors: 48,243 pass `grammar.check`, of which
        # 27,440 (56.9%) FAIL the sharp-chine type check — example violation
        # "typology[sharp-chine]: forefoot 0.32 outside [0.4, 1.0]" — and the
        # shipped code delivered 100% of them while the docstring above claimed
        # an "L0 type-check".
        #
        # It is now ENFORCED, and the typology is INFERRED rather than asserted.
        # Hard-coding SHARP_CHINE would have the Validator reject hulls for not
        # being a typology nobody asked for: the Builder samples a Genome fitted
        # on `sample_valid` draws, which carries no typology conditioning.
        # `infer_typology` asks the question the grammar can actually answer —
        # "does this vector type-check as ANY declared typology, and which?" —
        # and the answer is recorded on the delivered design. MEASURED on the
        # Builder's own distribution (512 genome samples): 512 pass
        # `grammar.check`, 324 pass sharp-chine, 324 pass some typology, so on
        # today's genome the inferred form costs nothing against the hard-coded
        # one; it is simply the honest question, and stays right when a PRAM
        # genome is added.
        typ = infer_typology(x)
        if typ is None:
            why = []
            for t in Typology:
                why += list(type_check(HullDesign.from_vector(x, t)).violations)
            audit.log(Message("validator", "orchestrator", "rejected",
                              {"fitness": float("inf"), "why": tuple(why),
                               "stage": "L0 type-check"}))
            continue
        ev = evaluate(x, mission, policy=policy)
        if not ev.ok:
            audit.log(Message("validator", "orchestrator", "rejected",
                              {"fitness": float("inf"), "why": ev.violations,
                               "stage": "L1 ladder"}))
            continue
        out_msg = Message("validator", "engineer", "validated", (x, ev, typ))
        audit.log(out_msg)
        await out.put(out_msg)


async def _engineer(inbox: asyncio.Queue, out: asyncio.Queue, audit: Audit,
                    mission: MissionSpec) -> None:
    while True:
        msg = await inbox.get()
        if msg.kind == "stop":
            return
        x, ev, typ = msg.payload
        # THE BOTTOM-PANEL THICKNESS IS NOT THIS STAGE'S TO CHOOSE, in
        # either of the two ways it has been got wrong here.
        # FIRST WAY: `assess(Hull(x), ev.wl)` bills the
        # NOMINAL stock sheet while the SAME ladder run already derived the
        # bottom-panel thickness from ISO 12215-5 and charged the boat that
        # structural weight. MEASURED on a 6 t mission: the delivered BOM read
        # 15.0 mm bottom / 140 sheets against `ev.ply_thickness_m` = 21.0 mm,
        # and the BOM lines even carried the note "thickness nominal stock
        # sheet (no mLDC given — NOT rule-derived)". Honest, and still a bill
        # of materials for a boat that fails the platform's own scantling rule.
        # PASSING `mldc_kg` WAS NOT ENOUGH, AND THAT IS THE 2026-08-20
        # INCIDENT. `assess(..., mldc_kg=...)` re-derived the sheet from ONE
        # ladder argument and hard-coded the rest, so the delivered BOM came
        # out at **18.0 mm** against `ev.ply_thickness_m` = **15.0 mm** on the
        # 6 t Danube mission: the ladder passes `mission.design_category` (D,
        # kDC 0.4) and the engineer assumed "category C default" (kDC 0.6).
        # Same formula, same mLDC, different boat. Handing over the ARGUMENTS
        # and re-running the rule is still two sources for one number, so the
        # delivery path now consumes the ANSWER — the exact thickness the
        # ladder derived and charged as structural weight.
        # `evaluate()` selects it with `select_stock_thickness_m` at the
        # mission's category and its thickness-mass fixed point; there is
        # nothing left here to keep in step with.
        # A DESIGN THE ENGINEER CANNOT BUILD IS A REJECTION, NOT THE END OF THE
        # STAGE. MEASURED 2026-08-13: `assess` raises for a hull the unroller
        # refuses (`roundness > 0` — a radiused bilge is not a two-panel
        # developable shell), the raise escaped this coroutine, and
        # `_orchestrate` gathers the tasks with `return_exceptions=True`, so
        # the ENGINEER TASK DIED SILENTLY on the first such design and every
        # later one queued behind it was never seen. A `run_plm` at batch 1500
        # produced 55,500 candidates, 43 of which passed the validator, and
        # delivered ZERO records with nothing in the audit trail saying why.
        # A stage that stops is indistinguishable from a stage with no input.
        try:
            eng = assess(Hull(x), ev.wl,
                         bottom_thickness_m=ev.ply_thickness_m)
        except ValueError as exc:
            audit.log(Message("engineer", "orchestrator", "rejected",
                              {"fitness": float("inf"), "why": (str(exc),),
                               "stage": "engineer"}))
            continue
        reqs = grade(ev, requirements_from_mission(mission))
        rec = DesignRecord(x, ev, eng, reqs, fitness=ev.energy.wh_per_nm,
                           typology=typ.value)
        out_msg = Message("engineer", "orchestrator", "engineered", rec)
        audit.log(out_msg)
        await out.put(out_msg)


async def _orchestrate(mission_text: str, n_designs: int, batch: int,
                       timeout_s: float, policy=None
                       ) -> tuple[list[DesignRecord], Audit, MissionSpec]:
    mission = translate(mission_text)
    audit = Audit()
    audit.log(Message("orchestrator", "orchestrator", "mission",
                      {"spec": mission.name,
                       "displacement": mission.displacement_target_kg}))

    # the builder's generative basis: a genome fitted on-mission
    X, _ = sample_valid(80, mission, seed=17, policy=policy)
    genome = Genome.fit(X)

    q_build: asyncio.Queue = asyncio.Queue()
    q_val: asyncio.Queue = asyncio.Queue()
    q_eng: asyncio.Queue = asyncio.Queue()
    q_out: asyncio.Queue = asyncio.Queue()

    tasks = [
        asyncio.create_task(_builder(q_build, q_val, audit, genome, batch)),
        asyncio.create_task(_validator(q_val, q_eng, audit, mission,
                                       policy)),
        asyncio.create_task(_engineer(q_eng, q_out, audit, mission)),
    ]

    results: list[DesignRecord] = []
    deadline = time.monotonic() + timeout_s
    await q_build.put(Message("orchestrator", "builder", "request", batch))
    try:
        while len(results) < n_designs and time.monotonic() < deadline:
            try:
                msg = await asyncio.wait_for(q_out.get(), timeout=2.0)
                results.append(msg.payload)
            except asyncio.TimeoutError:
                await q_build.put(Message("orchestrator", "builder", "request", batch))
    finally:
        for q in (q_build, q_val, q_eng):
            await q.put(Message("orchestrator", "*", "stop", None))
        await asyncio.gather(*tasks, return_exceptions=True)

    results.sort(key=lambda r: r.fitness)
    return results[:n_designs], audit, mission


def run_plm(mission_text: str, n_designs: int = 3, batch: int = 8,
            timeout_s: float = 120.0, policy=None):
    """Synchronous entry: mission text -> validated, engineered designs +
    the full message audit trail.

    `policy` is an optional COMPILED constitution. It reaches BOTH of the
    compiler's outputs: the generative genome is fitted on a draw from the
    GOVERNED box, and the validator appends the constitution's rows.

    It matters most here, and the reason is measured. The engineer stage calls
    `unroll.hull_panels`, which REFUSES a radiused bilge by name -- so under a
    sheet-built constitution an ungoverned run fits its genome on hulls the
    shop cannot cut and then discards them one at a time, in the last stage,
    with the audit trail reading "rejected" over and over. Governing the DRAW
    aims the generative model inside the buildable space instead.
    """
    return asyncio.run(_orchestrate(mission_text, n_designs, batch, timeout_s,
                                    policy))
