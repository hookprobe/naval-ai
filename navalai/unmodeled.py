"""The UNMODELED-REQUIREMENTS registry — what the product hears and cannot
yet enforce, in ONE structure instead of scattered UI prose.

WHY (2026-09-03, the overnight product directive §7). The requirements
screen already admits, in prose, that "cost, air draft, motion in a chop
and noise" have nowhere to land — but prose admissions scatter, drift and
get copied, and a stored-but-unenforced value is the exact defect class
the mission-language work kept finding (a brief says something, the parser
hears it, and the design path draws as though it had not been said). This
registry is the one home of that admission, per requirement, with its
honest STATUS — because "partially enforced" and "not enforced at all" are
different promises and the UI must not blur them.

RULES. An entry here never fakes physics: `current_effect` states exactly
what the value does today (often "NONE"). A requirement that gains a real
enforcement path moves OUT of this registry in the same commit that lands
the enforcement, with the test updated — a registry entry outliving its
closure would be the stale-document defect in a new home.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UnmodeledRequirement:
    requirement: str
    status: str            # "UNMODELED" | "PARTIAL"
    reason: str
    planned_closure: str
    current_effect: str
    mission_field: str | None = None   # where a stated value lands, if anywhere


REGISTRY: tuple[UnmodeledRequirement, ...] = (
    UnmodeledRequirement(
        requirement="air_draft",
        status="PARTIAL",
        mission_field="air_draft_max_m",
        reason="the parsed ceiling reaches ONE checker "
               "(translate.requirements_from_mission: bare-hull height above "
               "WL vs the stated clearance) on the requirements screen. There "
               "is no superstructure model — a houseboat's cabin is the part "
               "that hits the bridge — and no constraint row, so the SEARCH "
               "is free to propose hulls that fail the check.",
        planned_closure="superstructure height as a mission/arrangement "
                        "quantity, then a check_selection() call (not an "
                        "always-satisfied NSGA row).",
        current_effect="bare-hull advisory check only; no effect on search"),
    UnmodeledRequirement(
        requirement="build_cost",
        status="PARTIAL",
        reason="objective 3 minimises shell+deck AREA as a stated PROXY for "
               "cost (the UI says so). No currency model: materials, labour, "
               "fit-out and propulsion hardware are all outside it, and two "
               "hulls with equal area can differ 2x in real cost.",
        planned_closure="a bill-of-materials cost model over "
                        "engineer.assess()'s BOM, which already counts sheets "
                        "and parts.",
        current_effect="area proxy only, labelled as such in the UI"),
    UnmodeledRequirement(
        requirement="motion_in_chop",
        status="UNMODELED",
        reason="no mission field exists — a brief saying 'comfortable in "
               "chop' parses to NOTHING. navalai.seakeeping exists as the L2 "
               "promotion rung (frequency-domain, calm-water-adjacent), but "
               "no requirement connects a user's comfort statement to it.",
        planned_closure="a mission comfort field routed to the L2 seakeeping "
                        "rung's measured RAOs; refused (not faked) below L2.",
        current_effect="NONE"),
    UnmodeledRequirement(
        requirement="noise",
        status="UNMODELED",
        reason="no field, no model, no data. Electric drive makes this "
               "mostly a structure-borne question nothing here measures.",
        planned_closure="unplanned; record measurements before modelling.",
        current_effect="NONE"),
)


def report(mission) -> list[dict]:
    """The registry, joined against what THIS mission actually stated.

    An entry whose `mission_field` carries a value on this mission gets
    that value attached — this is the payload that lets the UI say
    'you asked for 3.2 m of air draft; here is exactly how much of that
    is enforced' instead of silently storing the number.
    """
    out = []
    for r in REGISTRY:
        d = {"requirement": r.requirement, "status": r.status,
             "reason": r.reason, "planned_closure": r.planned_closure,
             "current_effect": r.current_effect}
        if r.mission_field:
            v = getattr(mission, r.mission_field, None)
            if v is not None:
                d["stated_value"] = v
                d["mission_field"] = r.mission_field
        out.append(d)
    return out
