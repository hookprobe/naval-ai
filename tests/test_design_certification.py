"""Gate DC — the pre-CFD design certification layer (screening directive).

Invariants and refusal boundaries, not float pins (§28): the engine must
classify cheaply, carry receipts, refuse unsupported regimes by name, and
never fabricate what the tree cannot answer.
"""

import numpy as np
import pytest

from navalai import formcheck
from navalai.certify import (REGIME_AUTONOMOUS_SLOW_CRUISE, REGIME_PLANING,
                             REGIME_SEMI_DISPLACEMENT, certify,
                             mission_regime, speed_curve)
from navalai.evaluate import evaluate
from navalai.mission import Manning, MissionSpec, VesselConfig
from navalai.reference import reference_params

CASES = {c.key: c for c in formcheck.CASES}


@pytest.fixture(scope="module")
def ref_cert():
    return certify(reference_params(),
                   MissionSpec(cruise_speed_kn=5, lwl_hint_m=10.0))


def test_a_refusal_NAMES_its_defect_and_the_LADDER_now_passes(ref_cert):
    """FIXING THE BEND RADIUS UNCOVERED A DEFECT IT HAD BEEN MASKING.

    This asserted `verdict == "REFUSE"` with "bend radius" among the reasons.
    MEASURED 2026-08-20, before and after the operator adopted LAMINATED
    construction (`limits.laminate_plan`), on the same reference hull and
    mission:

        BEFORE  evaluation_ok False, reasons: ["panel bend radius 0.95 m <
                1.44 m (18 mm ply cold-bend limit)"]
        AFTER   evaluation_ok TRUE, verdict REFUSE, reasons:
                  "loading condition(s) FAIL the seaworthiness floors:
                   PEOPLE_FORWARD"
                  "constraint margin thin: ['rules']"
                  "delivered Cp 0.596 misses the mission target 0.558"

    The hull's 0.95 m radius clears a two-skin laminate's 0.72 m floor where
    it failed a single sheet's 1.44 m. So the LADDER now passes — and
    `certify` walks on to the loading states it had never reached, where
    PEOPLE_FORWARD fails.

    THAT FAILURE IS NOT NEW AND NOT A REGRESSION. It was there all along,
    unreachable behind an earlier refusal: certification stops at
    `evaluation_ok False`, so the three reasons above were never evaluated.
    Removing one defect made an older one VISIBLE, which is the honest
    outcome and worth more than the fix that caused it.

    The verdict is still REFUSE, so this test still exercises what it is for
    — that a refusal NAMES its defect rather than reporting a bare fail — but
    on the reason the boat actually has.
    """
    assert ref_cert.evaluation_ok is True, (
        "the LADDER refuses the reference hull again; the laminate floor may "
        f"have moved: {ref_cert.reasons}")
    assert ref_cert.verdict == "REFUSE"
    assert ref_cert.reasons, "a REFUSE with no reason is a bare fail"
    assert any("seaworthiness floors" in r for r in ref_cert.reasons), (
        f"the loading-state refusal has gone: {ref_cert.reasons}")
    assert any("PEOPLE_FORWARD" in r for r in ref_cert.reasons), (
        "the refusal must NAME the failing service state, not just say one "
        f"failed: {ref_cert.reasons}")
    # the bend radius is no longer the binding constraint
    assert not any("bend radius" in r for r in ref_cert.reasons), (
        "the cold-bend refusal returned; laminate_plan may have regressed")
    # AND A FINDING THIS TEST NOW SURFACES: `cfd_candidate["eligible"]` is
    # TRUE on a certification whose verdict is REFUSE. It tracks the LADDER,
    # which passes, and does not consult the loading states that refused the
    # boat — so the system would spend a CFD budget on a design it has just
    # declined. Pinned as the CURRENT behaviour, not endorsed: it was
    # invisible while the ladder refused this hull outright, and it is
    # recorded in docs/audit/STATUS.md for its owner.
    assert ref_cert.cfd_candidate["eligible"] is True, (
        "eligibility changed; if it now consults the loading states this "
        "assertion should become `is False` and the STATUS note retired")


def test_every_quantity_carries_its_receipt(ref_cert):
    """§25: value/unit/tier/sigma-where-meaningful/basis on every figure."""
    assert ref_cert.quantities, "a certification with no quantities"
    for name, q in ref_cert.quantities.items():
        assert np.isfinite(q.value), name
        assert q.unit, name
        assert q.tier, name
        assert q.basis and len(q.basis) > 10, (
            f"{name}: a basis must say where the number came from")


def test_unsupported_regimes_are_refused_by_name():
    """§16: no regime is enabled until its physics exists. A fast brief is
    routed to SEMI_DISPLACEMENT or PLANING and REFUSED with 'not yet
    supported' — never silently scored by Michell."""
    fast = MissionSpec(cruise_speed_kn=9, lwl_hint_m=8.0)     # Fn ~0.52
    reg, ok, why = mission_regime(fast)
    assert reg == REGIME_SEMI_DISPLACEMENT and not ok
    assert "not yet supported" in why
    planing = MissionSpec(cruise_speed_kn=14, lwl_hint_m=6.0)  # Fn ~0.94
    reg, ok, why = mission_regime(planing)
    assert reg == REGIME_PLANING and not ok
    cert = certify(reference_params(), fast, with_gz=False)
    assert cert.verdict == "REFUSE"
    assert not cert.regime_supported
    drone = MissionSpec(cruise_speed_kn=3, lwl_hint_m=5.0,
                        vessel=VesselConfig(manning=Manning.UNCREWED))
    reg, ok, _ = mission_regime(drone)
    assert reg == REGIME_AUTONOMOUS_SLOW_CRUISE and ok


def test_the_speed_curve_is_banded_and_monotone_where_valid(ref_cert):
    """§15: every point carries a validity band; within the continuously
    VALID/EXTRAPOLATED displacement range total resistance is monotone in
    speed (an invariant, not a float pin); UNSUPPORTED points never carry
    an energy figure."""
    curve = ref_cert.speed_curve
    assert curve
    bands = {p.validity for p in curve}
    assert bands <= {"VALID", "TRANSITION", "EXTRAPOLATED", "UNSUPPORTED"}
    usable = [p for p in curve if p.validity != "UNSUPPORTED"]
    rts = [p.rt_n for p in usable]
    assert rts == sorted(rts), "Rt must rise with speed in-regime"
    for p in curve:
        if p.validity == "UNSUPPORTED":
            assert p.wh_per_nm is None, (
                "an unsupported point carried an energy figure")
        else:
            assert p.wh_per_nm is not None and p.wh_per_nm > 0
        assert p.sigma_rt_n > 0


def test_a_fast_mission_curve_ends_unsupported():
    """Beyond FN_MICHELL_MAX the curve says UNSUPPORTED instead of drawing
    smooth fiction (§15)."""
    m = MissionSpec(cruise_speed_kn=7.5, lwl_hint_m=10.0)      # Fn ~0.39
    ev = evaluate(reference_params(), m)
    assert ev.hydro is not None
    curve = speed_curve(reference_params(), m, ev)
    assert curve[-1].fn > 0.45
    assert curve[-1].validity == "UNSUPPORTED"
    assert any(p.validity != "UNSUPPORTED" for p in curve)


def test_loading_matrix_obeys_conservation_invariants(ref_cert):
    """§28: removing load must not increase displacement; a mirrored
    symmetric loading has zero TCG; the MAXIMUM state is UNKNOWN rather
    than fabricated (no declared maximum exists)."""
    lm = ref_cert.loading
    # The reference mission declares a 6000 kg DISPLACEMENT TARGET, so
    # removing the provision re-grows the declared `unaccounted` filler and
    # both states float at the target (equal within solver tolerance) —
    # the honest invariant under a pinned target is equality-with-tolerance,
    # not decrease. The real decrease is asserted on the drone case below,
    # whose budget exceeds its target.
    assert lm["LIGHTSHIP"]["displacement_kg"] <= \
        lm["DESIGN"]["displacement_kg"] * (1.0 + 2e-3)
    drone = certify(CASES["e"].params, CASES["e"].mission, with_gz=False)
    dl = drone.loading
    assert dl["LIGHTSHIP"]["displacement_kg"] < \
        dl["DESIGN"]["displacement_kg"] - 1.0, (
        "removing the drone's provision must reduce displacement")
    for st in ("DESIGN", "LIGHTSHIP"):
        assert lm[st]["tcg_m"] == pytest.approx(0.0, abs=1e-9)
        assert lm[st]["freeboard_m"] > 0
    assert "unknown" in lm["MAXIMUM"]
    assert "not fabricated" in lm["MAXIMUM"]["unknown"]
    # the people-shift states exist for a crewed mission and TRIM apart
    assert "PEOPLE_FORWARD" in lm and "PEOPLE_AFT" in lm
    tf = lm["PEOPLE_FORWARD"]["trim_deg"]
    ta = lm["PEOPLE_AFT"]["trim_deg"]
    if tf is not None and ta is not None:
        assert tf > ta, "people forward must trim the bow DOWN relative " \
                        "to people aft"


def test_the_catamaran_certification_assesses_and_measures(ref_cert):
    """The 12 m catamaran case, RE-POINTED at the R2.2 flip (2026-08-19):
    the sub-15 m class is now GOVERNED by NZ Part 40A App.1 cl 1.3, which
    the ladder computes, so stability is ASSESSED with the cl13 receipt on
    the certification — while the cl 1.4 curve clauses (a)/(b) stay
    MEASURED beside it as supplementary evidence and (c)'s windage gap is
    still named for the bigger class. Case d's overall verdict remains
    REFUSE on a GENUINE rules finding (R-DFH downflooding height), which
    is what a working criterion looks like: the refusals that remain are
    design findings, not criterion gaps."""
    case = CASES["d"]
    cert = certify(case.params, case.mission)
    assert cert.verdict == "REFUSE"
    assert any("R-DFH" in v for v in cert.violations)
    st = cert.stability
    assert st["verdict"] == "ASSESSED"
    assert st["criterion"].startswith("NZ Part 40A App.1 cl 1.3")
    assert st["cl13"]["passes"] is True
    assert st["cl13"]["heel_deg"] is not None
    assert st["clause_a"]["area_m_rad"] > 0
    assert st["clause_b"]["heel_at_gz_max_deg"] > 0
    assert any("windage" in u or "lateral area" in u
               for u in st["unassessable"])
    assert any("fixed longitudinal attitude" in a for a in cert.assumptions)
    assert any("watertight to the sheer" in a for a in cert.assumptions)


def test_certification_composes_it_does_not_fork():
    """§4: the engine composes the EXISTING Evaluation — same verdict
    inputs, same violations, no parallel ladder."""
    m = MissionSpec(cruise_speed_kn=5, lwl_hint_m=10.0)
    ev = evaluate(reference_params(), m)
    cert = certify(reference_params(), m, with_gz=False)
    assert cert.violations == ev.violations
    assert cert.evaluation_ok == ev.ok
    assert cert.targets == dict(ev.targets)


def test_a_refused_trim_equilibrium_is_never_an_even_keel_C02():
    """Forensics C-02 (E11 reborn): four sites collapsed a REFUSED trim
    (None) into 0.0 — one of them fed CFD manifests. A hull whose
    equilibrium the solver refused must not carry a 'solved equilibrium'
    quantity, must not get a GZ curve at a fabricated attitude, and must
    not become an even-keel CFD case."""
    from navalai.cfd.manifest import manifest_from_evaluation
    from navalai.evaluate import evaluate
    from navalai.mission import PayloadSpec
    from navalai.reference import reference_params

    m = MissionSpec(payload=PayloadSpec(mass_kg=3000.0, x_frac_lwl=0.99,
                                        z_frac_depth=0.5))
    ev = evaluate(reference_params(), m)
    assert ev.trim_deg is None and ev.hydro is not None, (
        "fixture must float but refuse the trim equilibrium")

    cert = certify(reference_params(), m)
    assert cert.verdict == "REFUSE"
    assert "trim" not in cert.quantities, (
        "a refused equilibrium reappeared as a 'solved' trim quantity")
    assert "refused" in cert.stability
    assert "fabricated attitude" in cert.stability["refused"]
    assert "gz_max_m" not in cert.stability, (
        "a GZ curve was computed at an attitude the solver refused")

    with pytest.raises(ValueError, match="REFUSED"):
        manifest_from_evaluation(ev, m)


def test_the_certification_and_the_ladder_plank_the_same_boat_C05():
    """Forensics B2/C-05: certify's buildability ran the DEFAULT 15mm sheet
    with its own weight budget — 29% structure-mass divergence inside one
    certification. It now consumes the ladder's derived sheet."""
    from navalai.evaluate import evaluate

    case = CASES["a"]
    ev = evaluate(case.params, case.mission)
    cert = certify(case.params, case.mission, with_gz=False)
    assert "refused" not in cert.buildability
    assert cert.buildability["structure_kg"] == pytest.approx(
        ev.weights.structure_kg, abs=0.5)
    # The kit route is OPT-IN (the refold meter costs ~9 s) and an absent
    # check is recorded as absent — never implied as a pass.
    assert cert.buildability["kit"]["route"] == "not measured"
    assert "with_kit" in cert.buildability["kit"]["why"]


def test_a_round_bilge_hull_can_be_cfd_worthy_C19():
    """Forensics B13/C-19: the sheet-development analyser's refusal of
    roundness>0 zeroed CFD eligibility, making the project's own round-
    bilge target class structurally un-selectable. The refusal is now a
    MISSING metric with a note; eligibility is physics + validity."""
    case = CASES["b"]                     # 15 m round-bilge cruiser
    cert = certify(case.params, case.mission, with_gz=False)
    assert "refused" in cert.buildability
    assert "NOT a physics verdict" in cert.buildability["note"]
    assert cert.cfd_candidate["eligible"] is True
    assert "buildable" not in cert.cfd_candidate["parts"]
    assert "buildable part omitted" in cert.cfd_candidate["note"]
    assert cert.cfd_candidate["score"] > 0


def test_loading_states_gate_the_verdict_on_seaworthiness_floors_R23():
    """R2.3: a certification is for every declared service state, not the
    design point alone — and the states are judged on the SEAWORTHINESS
    floors (float, GM, trim, list, freeboard), never on design-balance
    constraints (a shifted crowd MUST move LCB; refusing the state for the
    displacement the test creates would refuse every boat whose crew can
    walk). MEASURED at the wire: case b keeps MARGINAL with every state
    seaworthy; case c REFUSES because its crowd-aft state swamps the bow
    freeboard and trims past the limit — a real, actionable finding, with
    the failing floors named per state. Asymmetric cargo on a multihull is
    a DOCUMENTED refusal (PayloadSpec has no transverse coordinate), and
    it does not gate — unassessed is not failed.
    """
    # CASE B NOW REFUSES, AND THAT IS GAP B4 WORKING (2026-08-20).
    # MEASURED: case b declares SIX crew, and the payload provision used to
    # be a flat 800 kg that did not move with `mission.crew` — so the boat
    # floated at a two-crew displacement while claiming six. B4 scaled it to
    # 6 x 85 + 630 = 1140 kg, and the extra 340 kg is exactly what puts its
    # PEOPLE_AFT and PEOPLE_FORWARD states under the seaworthiness floors.
    #
    # That is the defect B4 names, made visible: "a 12-crew boat put 12 x 85
    # kg on the rail for the stability check and floated at exactly the
    # two-crew displacement". The old expectation here — "case b keeps
    # MARGINAL with every state seaworthy" — was measured on a boat 340 kg
    # light. A six-crew boat that cannot carry six crew safely SHOULD be
    # refused, and asserting otherwise would re-hide the defect.
    b = CASES["b"]
    assert b.mission.crew == 6, "fixture changed; re-measure the provision"
    cert_b = certify(b.params, b.mission, with_gz=False)
    assert cert_b.verdict == "REFUSE"
    assert any("seaworthiness floors" in r for r in cert_b.reasons)
    failed_b = {k for k, st in cert_b.loading.items()
                if isinstance(st, dict) and st.get("seaworthy") is False}
    assert failed_b, "the loading states that refuse case b are not named"
    assert "PEOPLE_AFT" in failed_b or "PEOPLE_FORWARD" in failed_b, failed_b
    # and the DESIGN POINT itself is still fine — it is the crowd states that
    # fail, which is the distinction this test exists to keep
    assert cert_b.evaluation_ok is True, cert_b.reasons

    c = CASES["c"]
    cert_c = certify(c.params, c.mission, with_gz=False)
    assert cert_c.verdict == "REFUSE"
    aft = cert_c.loading["PEOPLE_AFT"]
    assert aft["seaworthy"] is False
    assert "freeboard" in aft["floor_failures"]
    assert any("seaworthiness floors" in r for r in cert_c.reasons)
    # the multihull's asymmetric-cargo gap is documented, and non-gating
    assert "ASYMMETRIC_PAYLOAD" in cert_c.loading
    assert "not representable" in cert_c.loading["ASYMMETRIC_PAYLOAD"]["refused"]
