"""ISO 12217-1 (motor craft >= 6 m) — simplified stability assessment.

Implemented tests (each a typed executable checker with clause provenance):
  R-DFH  downflooding height vs design-category floor
  R-OLH  offset-load heel (crew crowding to one side)
  R-GM   metacentric-height floor per category
  R-CAT  category context (significant wave height the category implies)

Thresholds basis='approx': engineering-practice values standing in until the
licensed standard text parity review (BuildPlan Gate 6). The MECHANICS
(moment balance, geometry) are exact.
"""

from __future__ import annotations

import math

from ..evaluate import Evaluation
from . import RuleFinding

# category -> (significant wave height context [m], downflooding floor [m],
#              GM floor [m], max offset-load heel [deg])
CATEGORY_TABLE = {
    "A": (4.0, 0.65, 0.60, 10.0),
    "B": (4.0, 0.50, 0.50, 10.0),
    "C": (2.0, 0.35, 0.45, 10.0),
    "D": (0.3, 0.25, 0.35, 12.0),
}

def gm_floor(category: str) -> float:
    """Metacentric-height floor [m] for a design category.

    Exported so the OPTIMIZER can constrain against the same number the rules
    tier judges by. They were hard-coded separately and drifted: the optimizer
    demanded GM >= 0.35 m while category C requires 0.45 m, so NSGA-II happily
    returned a GM 0.40 m hull that was feasible by its own constraint and then
    failed R-GM at the gate. Platform law (PLM.md §1): a product may configure
    the kernel, never bypass a gate — so the two must read one source.
    """
    if category not in CATEGORY_TABLE:
        raise ValueError(f"unknown design category {category!r}")
    return CATEGORY_TABLE[category][2]


CREW_MASS_KG = 85.0     # ISO default person mass
OFFSET_FRACTION = 0.40  # crew CG offset as fraction of beam (approx)


def assess(ev: Evaluation, category: str, crew: int,
           beam_m: float) -> list[RuleFinding]:
    if category not in CATEGORY_TABLE:
        raise ValueError(f"unknown design category {category!r}")
    hs, dfh_req, gm_req, heel_max = CATEGORY_TABLE[category]
    out: list[RuleFinding] = []

    if ev.hydro is None or ev.gm_m is None:
        out.append(RuleFinding("R-CAT", "ISO 12217-1 §5 (design categories)",
                               "approx", False, 0.0, hs, "m",
                               "no floatation state — cannot assess"))
        return out

    out.append(RuleFinding(
        "R-CAT", "ISO 12217-1 §5 (design categories)", "approx", True, hs, hs,
        "m", f"category {category}: significant wave height context {hs} m"))

    dfh = ev.hydro.freeboard_min   # lowest opening assumed at sheer (conservative
    # only if no lower openings exist — recorded in the note)
    out.append(RuleFinding(
        "R-DFH", "ISO 12217-1 §6.2 (downflooding height)", "approx",
        dfh >= dfh_req, dfh, dfh_req, "m",
        "lowest opening assumed at sheer line; declare real openings to tighten"))

    out.append(RuleFinding(
        "R-GM", "ISO 12217-1 annex (metacentric floor, practice value)",
        "approx", ev.gm_m >= gm_req, ev.gm_m, gm_req, "m", ""))

    # offset-load heel: moment balance m*b = disp*GM*sin(phi)  (exact mechanics)
    m_crew = crew * CREW_MASS_KG
    b = OFFSET_FRACTION * beam_m
    sin_phi = min(m_crew * b / max(ev.hydro.disp_kg * ev.gm_m, 1e-9), 1.0)
    phi = math.degrees(math.asin(sin_phi))
    out.append(RuleFinding(
        "R-OLH", "ISO 12217-1 §6.3 (offset load test)", "approx",
        phi <= heel_max, phi, heel_max, "deg",
        f"{crew} crew x {CREW_MASS_KG:.0f} kg at {b:.2f} m offset"))
    return out
