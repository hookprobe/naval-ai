"""Gate VM — the vessel matrix (consolidation directive §19/§20).

Five-plus deterministic vessels, judged END TO END through the ladder and
the CFD manifest — every cell PASS or EXPLICITLY UNSUPPORTED, never
silently treated as a different vessel type. The vectors are
`navalai.formcheck.CASES` (defined ONCE; the physical-form gate and this
matrix must describe the same boats — a third fixture set would be the
number-declared-twice defect wearing a fleet).
"""

import numpy as np
import pytest

from navalai import formcheck, grammar
from navalai.cfd.manifest import manifest_from_evaluation
from navalai.evaluate import evaluate
from navalai.mission import (EVALUABLE_TOPOLOGIES, Manning, MissionSpec,
                             Topology, VesselConfig)

CASES = {c.key: c for c in formcheck.CASES}


@pytest.mark.parametrize("key", sorted(CASES))
def test_the_case_is_judged_as_the_vessel_it_declares(key):
    """§19 row: topology honoured, hull floats, state coherent, targets
    receipt present, stability either assessed (monohull) or refused BY
    NAME (multihull) — and the CFD manifest builds from the same state."""
    case = CASES[key]
    ev = evaluate(case.params, case.mission)
    v = case.mission.vessel

    # never silently another vessel type
    assert ev.vessel["topology"] == v.topology.value
    assert ev.vessel["manning"] == v.manning.value
    assert ev.vessel["n_hulls"] == (2 if v.topology is Topology.CATAMARAN
                                    else 1)
    # it floats, and the state is one state
    assert ev.hydro is not None and ev.masses is not None
    assert ev.hydro.disp_kg > 0
    assert ev.hydro.wetted > 0
    assert ev.gm_m is not None
    # the §5 receipt exists on every case
    assert "cp_delivered" in ev.targets
    assert ev.targets["cp_delivered"] == pytest.approx(float(ev.hydro.cp))

    if v.topology is Topology.CATAMARAN:
        # EXPLICIT refusal, not silence: the multihull criterion cannot
        # pass ((c) windage undeclarable, (d) unread) and says so
        assert not ev.ok
        joined = " ".join(ev.violations)
        assert "NO CRITERION IS IMPLEMENTED" in joined
        assert "righting-arm curve" in joined

    # the manifest builds from the same floated state (CFD-READY: the
    # safety verdict is separate from whether a case can be written)
    man = manifest_from_evaluation(ev, case.mission)
    assert man.waterline_m == ev.wl
    assert man.trim_deg == float(ev.trim_deg or 0.0)
    assert man.mass_kg == ev.masses.total_kg
    assert man.n_hulls == ev.vessel["n_hulls"]


def test_trimaran_is_EXPLICITLY_unsupported():
    """§19: no faking. A trimaran mission is refused BY NAME at L0 — one
    moulded surface cannot build a centre hull that differs from its amas —
    and the refusal lists what IS evaluable."""
    m = MissionSpec(vessel=VesselConfig(topology=Topology.TRIMARAN,
                                        separation_over_lwl=0.30))
    ev = evaluate(CASES["a"].params, m)
    assert not ev.ok and ev.tier == "L0"
    joined = " ".join(ev.violations)
    assert "NOT IMPLEMENTED" in joined
    for t in EVALUABLE_TOPOLOGIES:
        assert t.value in joined


def test_the_historical_target_is_judged_by_role_S20():
    """§20: the 12 x 0.8 m demihull class — the finding that started the
    campaign. THE SAME GEOMETRY under two vessel roles receives different
    judgments where the rules legitimately differ: as a monohull it is
    refused on the monohull L/B band; as a catamaran demihull that clause
    is accepted and only the sourced Southampton B/T evidence floor (for
    the owner's 0.6 m draft) or the multihull stability refusal remains."""
    p = dict(LWL=12.0, BWL=0.8, T=0.6, D=1.1, Cp=0.575, lcb=0.0, x_mb=0.55,
             r_transom=0.20, beta_mid=8.0, beta_bow=20.0, beta_len=0.35,
             roundness=0.0, rocker=0.05, forefoot=0.30, flare=5.0,
             sheer_rise=0.10)
    x = grammar.vector(p)
    as_mono = evaluate(x, MissionSpec())
    as_demi = evaluate(x, MissionSpec(vessel=VesselConfig(
        topology=Topology.CATAMARAN, separation_over_lwl=0.30)))
    mono_txt = " ".join(as_mono.violations)
    demi_txt = " ".join(as_demi.violations)
    # monohull role: refused on the monohull L/B band, and says which role
    assert "L/B 15.00" in mono_txt and "monohull" in mono_txt
    # demihull role: the L/B clause is GONE (Southampton runs to 15.1)...
    assert "L/B 15.00" not in demi_txt
    # ...and what remains is the EVIDENCE floor, named as evidence
    assert "B/T 1.33" in demi_txt and "demihull" in demi_txt
    assert "OUT OF SOURCED RANGE" in demi_txt
