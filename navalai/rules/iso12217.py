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
from ..limits import CATEGORY_TABLE, gm_floor  # single source (navalai/limits.py)
from . import RuleFinding
from .review import basis_for

# category -> (significant wave height context [m], downflooding floor [m],
#              GM floor [m], max offset-load heel [deg])

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
                               basis_for("R-CAT"), False, 0.0, hs, "m",
                               "no floatation state — cannot assess"))
        return out

    out.append(RuleFinding(
        "R-CAT", "ISO 12217-1 §5 (design categories)", basis_for("R-CAT"), True, hs, hs,
        "m", f"category {category}: significant wave height context {hs} m"))

    dfh = ev.hydro.freeboard_min   # lowest opening assumed at sheer (conservative
    # only if no lower openings exist — recorded in the note)
    out.append(RuleFinding(
        "R-DFH", "ISO 12217-1 §6.2 (downflooding height)", basis_for("R-DFH"),
        dfh >= dfh_req, dfh, dfh_req, "m",
        "lowest opening assumed at sheer line; declare real openings to tighten"))

    out.append(RuleFinding(
        "R-GM", "ISO 12217-1 annex (metacentric floor, practice value)",
        basis_for("R-GM"), ev.gm_m >= gm_req, ev.gm_m, gm_req, "m", ""))

    # offset-load heel: moment balance m*b = disp*GM*sin(phi)  (exact mechanics)
    m_crew = crew * CREW_MASS_KG
    b = OFFSET_FRACTION * beam_m
    sin_phi = min(m_crew * b / max(ev.hydro.disp_kg * ev.gm_m, 1e-9), 1.0)
    phi = math.degrees(math.asin(sin_phi))
    out.append(RuleFinding(
        "R-OLH", "ISO 12217-1 §6.3 (offset load test)", basis_for("R-OLH"),
        phi <= heel_max, phi, heel_max, "deg",
        f"{crew} crew x {CREW_MASS_KG:.0f} kg at {b:.2f} m offset"))
    return out
