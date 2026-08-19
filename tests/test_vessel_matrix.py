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
        # R2.2 (2026-08-19): the blanket refusal is GONE for this class —
        # every canonical cat is < 15 m LOA with <= 50 persons, so NZ Part
        # 40A App.1 cl 1.3 governs, is COMPUTED, and the verdict is a
        # measured receipt. ok is decided by the whole ladder (case d
        # genuinely fails R-DFH); what must hold for ALL cats is that the
        # criterion DECIDED and left its audit trail.
        cl13 = ev.vessel["cl13"]
        assert cl13 is not None and cl13["passes"] is not None
        assert ev.vessel["stability_criterion"].startswith("NZ Part 40A")
        if not cl13["passes"]:
            assert any("cl 1.3 FAILED" in x for x in ev.violations)
        else:
            assert not any(x.startswith("multihull stability")
                           for x in ev.violations)

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


def test_the_four_canonical_classes_certify_end_to_end_S31():
    """Forensics section-31: the canonical fleet driven through the WHOLE
    screening chain — mission -> evaluate -> certify -> (manifest when the
    physics is certifiable) — with no manual mass injection anywhere.

    MEASURED 2026-08-19 (fortress001, the section-31 baseline): a REFUSE,
    b MARGINAL + CFD-eligible, c/d REFUSE (the multihull criterion is
    refusal-first until R2.2 lands windage/declared clauses), e/f REFUSE.
    Only the STRUCTURAL claims and the refusal-first cats are pinned —
    a/e/f verdicts may legitimately improve with the physics; what must
    never change silently is the chain running end-to-end, refusals
    carrying named reasons, and receipts carrying identity (C-22).
    """
    import hashlib

    import numpy as np

    from navalai.certify import certify

    verdicts = {}
    for case in CASES.values():
        cert = certify(case.params, case.mission)
        verdicts[case.key] = cert.verdict
        assert cert.verdict in ("ACCEPT", "MARGINAL", "REFUSE"), case.key
        # C-22: the receipt names the design and the code that judged it
        want_sha = hashlib.sha256(
            np.asarray(case.params, float).tobytes()).hexdigest()
        assert cert.genome_sha256 == want_sha, case.key
        assert cert.code_version, case.key
        if cert.verdict == "REFUSE":
            assert cert.reasons or cert.violations, (
                f"{case.key}: a REFUSE with no named reason is a verdict "
                f"nobody can act on")
        if case.mission.vessel.topology is Topology.CATAMARAN:
            # RE-MEASURED 2026-08-19, exactly as the previous pin
            # instructed: R2.2's cl 1.3 landed and the cats are judged by
            # a computed criterion. Measured: c MARGINAL (heel 0.77 deg,
            # trim 0.93 deg vs the 8 deg bar), d REFUSE on a GENUINE
            # rules finding (R-DFH downflooding height), not on a
            # criterion gap. The structural pin: the stability verdict is
            # never "REFUSED" for this sub-15 m class anymore.
            assert cert.stability.get("verdict") != "REFUSED", (
                f"{case.key}: the sub-15 m catamaran class regressed to "
                f"refusal-first — cl 1.3 stopped being computed")
        if (isinstance(cert.cfd_candidate, dict)
                and cert.cfd_candidate.get("eligible")):
            # an eligible certification hands off through the manifest —
            # the same floated state, no re-derivation
            ev = evaluate(case.params, case.mission)
            man = manifest_from_evaluation(ev, case.mission)
            assert man.mass_kg == ev.masses.total_kg, case.key
    # at least one class must remain CFD-worthy end-to-end, or the funnel
    # is closed and every campaign starves at the gate
    assert any(v in ("ACCEPT", "MARGINAL") for v in verdicts.values()), (
        f"no canonical class certifies: {verdicts}")
