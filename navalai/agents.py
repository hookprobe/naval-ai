"""The agentic PLM network (original plan, Phase 2) — async message passing.

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

from . import grammar
from .engineer import EngineerReport, assess
from .evaluate import Evaluation, evaluate, sample_valid
from .geometry import Hull
from .hull_ast import HullDesign, Typology, type_check
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
            msg = Message("builder", "validator", "candidate", x)
            audit.log(msg)
            await out.put(msg)


async def _validator(inbox: asyncio.Queue, out: asyncio.Queue, audit: Audit,
                     mission: MissionSpec) -> None:
    while True:
        msg = await inbox.get()
        if msg.kind == "stop":
            return
        x = msg.payload
        rep = type_check(HullDesign.from_vector(x, Typology.SHARP_CHINE))
        ev = evaluate(x, mission) if rep.ok or grammar.check(x).ok else None
        if ev is None or not ev.ok:
            reason = (ev.violations if ev else rep.violations)
            audit.log(Message("validator", "orchestrator", "rejected",
                              {"fitness": float("inf"), "why": reason}))
            continue
        out_msg = Message("validator", "engineer", "validated", (x, ev))
        audit.log(out_msg)
        await out.put(out_msg)


async def _engineer(inbox: asyncio.Queue, out: asyncio.Queue, audit: Audit,
                    mission: MissionSpec) -> None:
    while True:
        msg = await inbox.get()
        if msg.kind == "stop":
            return
        x, ev = msg.payload
        eng = assess(Hull(x), ev.wl)
        reqs = grade(ev, requirements_from_mission(mission))
        rec = DesignRecord(x, ev, eng, reqs, fitness=ev.energy.wh_per_nm)
        out_msg = Message("engineer", "orchestrator", "engineered", rec)
        audit.log(out_msg)
        await out.put(out_msg)


async def _orchestrate(mission_text: str, n_designs: int, batch: int,
                       timeout_s: float) -> tuple[list[DesignRecord], Audit, MissionSpec]:
    mission = translate(mission_text)
    audit = Audit()
    audit.log(Message("orchestrator", "orchestrator", "mission",
                      {"spec": mission.name,
                       "displacement": mission.displacement_target_kg}))

    # the builder's generative basis: a genome fitted on-mission
    X, _ = sample_valid(80, mission, seed=17)
    genome = Genome.fit(X)

    q_build: asyncio.Queue = asyncio.Queue()
    q_val: asyncio.Queue = asyncio.Queue()
    q_eng: asyncio.Queue = asyncio.Queue()
    q_out: asyncio.Queue = asyncio.Queue()

    tasks = [
        asyncio.create_task(_builder(q_build, q_val, audit, genome, batch)),
        asyncio.create_task(_validator(q_val, q_eng, audit, mission)),
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
            timeout_s: float = 120.0):
    """Synchronous entry: mission text -> validated, engineered designs +
    the full message audit trail."""
    return asyncio.run(_orchestrate(mission_text, n_designs, batch, timeout_s))
