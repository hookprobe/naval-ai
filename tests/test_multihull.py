"""THE VESSEL: three orthogonal axes, and the multihull physics behind axis 1.

    AXIS 1  TOPOLOGY  monohull | catamaran | trimaran | ...
                      selects the I_T sum, whether wave interference applies,
                      and WHICH STABILITY CRITERION GOVERNS
    AXIS 2  MANNING   crewed | liveaboard | uncrewed
                      selects WHICH RULE SET APPLIES
    AXIS 3  REGIME    DERIVED from Fn and Re, never declared
                      selects WHICH PHYSICS MODELS MAY ANSWER

THE FOUR INCIDENTS THIS FILE IS NAMED AFTER, all MEASURED 2026-08-13/14.

1. THERE WERE NO MULTIHULL HYDROSTATICS, so the ladder judged demihulls by a
   monohull GM floor. MEASURED over `grammar.sample(40, default_rng(0))` at
   `MissionSpec()` (6000 kg, 5 kn, category C, crew 2): median GM 0.290 m
   against a 0.45 m floor, worst -0.900 m — a hull that floats upside down —
   with the `gm` row failing 22 of 40 and R-GM/R-OLH dominating the rules tier.
   The hulls are tender BECAUSE THEY ARE SLENDER, which is what the brief asks
   for; they are meant to be DEMIHULLS, and judging one by a monohull floor is
   the same error class as `gate2m.py` printing KCS's EFD figure over a Wigley
   hull.

2. `resistance.total_resistance` CALLED `michell_rw` WITH NO `separation`, so
   every catamaran this project ever evaluated was scored as ONE ISOLATED
   DEMIHULL — while the interference factor sat implemented and verified three
   ways one module away.

3. AND FIXING (1) WOULD HAVE BEEN A SAFETY REGRESSION DRESSED AS A FEATURE.
   The `A_wp d^2` term takes the reference hull's GM from 0.6688 m to 54.39 m,
   so every catamaran clears every metacentric floor in this repository and in
   four national codes by two orders of magnitude — and GM is nearly irrelevant
   to whether a catamaran capsizes. A catamaran's righting moment PEAKS when
   the windward hull lifts and collapses past it, and the vessel is then STABLE
   INVERTED. `hydrostatics.multihull_stability_refusal` is what stops the
   ladder reporting an enormous GM as a safety verdict.

4. THE FRICTION HALF HAD NO ENVELOPE AT ALL. `FN_MICHELL_MAX` bounded the wave
   term; nothing bounded ITTC-1957, which is a FULLY TURBULENT correlation
   line. Froude scales as 1/sqrt(L), so a small hull is a fast hull: a 1 m
   drone crosses Fn 0.45 at ~2.7 kn and is in the laminar-turbulent transition
   at Re 9.03e5 well below that.

NOTHING HERE SOFTENS A BAR. `limits.CATEGORY_TABLE`'s GM floor, the ISO 12217
thresholds and Gate 1's 50 ms latency bar are untouched. What changed is which
VESSEL the ladder measures, and what it refuses to claim about it.
"""

from __future__ import annotations

import dataclasses
import json
import math
import time

import numpy as np
import pytest

from navalai import formlib, grammar
from navalai.evaluate import CONSTRAINT_NAMES, evaluate
from navalai.geometry import RHO_WATER, Hull
from navalai.hydrostatics import (MULTIHULL_CRITERION, moulded_max_beam,
                                  multihull_stability_refusal, solve,
                                  solve_to_displacement, vessel_terms)
from navalai.limits import gm_floor
from navalai.mission import (EVALUABLE_TOPOLOGIES, HULL_COUNT, Manning,
                             MissionSpec, Topology, VesselConfig)
from navalai.resistance import (FN_MICHELL_MAX, RE_FULLY_TURBULENT,
                                RE_TRANSITION_ONSET, bow_wave_rise,
                                flow_regime, michell_rw,
                                n_theta_for_separation, nu_water,
                                total_resistance)

_CENSUS_N = 40
_CENSUS_SEED = 0
_CENSUS_SEP_OVER_LWL = 0.30      # the Fn 0.25 destructive optimum, experiments.py


def _cat(sep: float = 0.60, manning: Manning = Manning.CREWED) -> VesselConfig:
    return VesselConfig(topology=Topology.CATAMARAN, manning=manning,
                        separation_over_lwl=sep)


@pytest.fixture(scope="module")
def population():
    return grammar.sample(_CENSUS_N, np.random.default_rng(_CENSUS_SEED))


@pytest.fixture(scope="module")
def ref_hull():
    """The hull most of this repository's measurements are taken on."""
    from test_phase0 import mid_params
    return mid_params()


# ==========================================================================
# THE CONTRACT: three axes, and no concept declared twice
# ==========================================================================


def test_the_vessel_has_three_axes_and_topology_has_exactly_one_home():
    """`Topology` is `formlib.Topology` — the SAME OBJECT, not a copy.

    `navalai/formlib.py` already owned this enum, with `formlib.MISSION`
    already declaring this product line's topology as CATAMARAN. Writing a
    second three-member `Topology` in `mission.py` would be this codebase's
    recurring defect (a thing declared twice) applied to the one contract three
    agents have to agree on — and the two copies would drift the moment either
    gained a member.

    REGIME IS NOT A FIELD, and that is the axis's definition rather than an
    omission: it is DERIVED from Fn and Re by `resistance.flow_regime`, because
    a declared regime can contradict the geometry that produces it.
    """
    assert Topology is formlib.Topology
    names = {f.name for f in dataclasses.fields(VesselConfig)}
    assert names == {"topology", "manning", "separation_over_lwl"}
    assert "regime" not in names
    # n_hulls is DERIVED from the topology, never a second field.
    assert VesselConfig().n_hulls == 1
    assert _cat().n_hulls == 2
    assert HULL_COUNT[Topology.TRIMARAN] == 3
    assert EVALUABLE_TOPOLOGIES == (Topology.MONOHULL, Topology.CATAMARAN)


def test_a_topology_with_no_hull_count_is_a_category_error_not_a_one():
    """`SUPPORTED` is a lift mechanism and `SMALL_WATERPLANE` a section law.

    Neither has a hull count, and answering 1 for them would be the
    `${VAR:-0}` pattern — an unanswerable question scored as the ordinary
    answer — which has already cost this project a run.
    """
    for topo in (Topology.SUPPORTED, Topology.SMALL_WATERPLANE):
        assert topo not in HULL_COUNT
        with pytest.raises(ValueError, match="category"):
            VesselConfig(topology=topo).n_hulls


def test_the_vessel_contract_refuses_rather_than_clamps():
    """An unspecified vessel is not a magnitude error a clamp could resolve.

    `MissionSpec.clamp()` clamps because a 5000-crew river barge is a number
    out of range. There is no in-range vessel near "a catamaran with no
    spacing" — and `resistance._separation_or_raise` already refuses the same
    thing for the same reason.
    """
    with pytest.raises(ValueError, match="outside"):
        VesselConfig(topology=Topology.CATAMARAN, separation_over_lwl=0.0)
    with pytest.raises(ValueError, match="monohull has nothing"):
        VesselConfig(separation_over_lwl=0.3)
    with pytest.raises(ValueError):
        VesselConfig(topology=Topology.CATAMARAN,
                     separation_over_lwl=float("nan"))
    with pytest.raises(ValueError, match="topology is one of"):
        VesselConfig(topology="hovercraft")
    with pytest.raises(ValueError, match="manning one of"):
        VesselConfig(manning="skeleton")
    # The ratio -> metres conversion has exactly one home and refuses a length
    # it cannot use rather than returning a spacing for it.
    with pytest.raises(ValueError):
        _cat(0.3).separation_m(0.0)
    assert _cat(0.3).separation_m(10.0) == 3.0
    assert VesselConfig().is_multihull is False and _cat().is_multihull is True


def test_the_vessel_survives_a_json_round_trip():
    """`formlib.Topology` is a plain Enum, so `asdict` does not unwrap it.

    Without the encoder `to_json` raises; without the coercion in
    `__post_init__` the value comes back as the STRING "catamaran" while every
    comparison in the tree is against the enum, and the mission silently
    evaluates as a monohull. Both halves are asserted because either alone
    leaves a round trip that looks like it worked.
    """
    m = MissionSpec(vessel=_cat(0.35, Manning.UNCREWED))
    doc = json.loads(m.to_json())
    assert doc["vessel"] == {"topology": "catamaran", "manning": "uncrewed",
                             "separation_over_lwl": 0.35}
    back = MissionSpec.from_json(m.to_json())
    assert back.vessel.topology is Topology.CATAMARAN
    assert back.vessel.manning is Manning.UNCREWED
    assert back.vessel.n_hulls == 2
    # A spec written before this field existed still loads as a monohull.
    d = json.loads(MissionSpec().to_json())
    d.pop("vessel")
    assert MissionSpec.from_json(json.dumps(d)).vessel.topology is \
        Topology.MONOHULL


# ==========================================================================
# THE MONOHULL PATH IS UNCHANGED
# ==========================================================================


def test_the_one_hull_case_is_the_monohull_bit_for_bit(population):
    """Every field of `HydroState`, with `==` and not `approx`.

    The multihull arithmetic is `n * (I_demi + A_wp d^2)` and `n * v`. At
    n_hulls = 1 and d = 0.0 those are `1 * x` and `x + y * 0.0`, both EXACT in
    IEEE-754 — so "the monohull is unchanged" is a property of the expressions,
    not a tolerance anyone chose. The second half checks the new code against
    the OLD FORMULAS rather than against another call into the new code.
    """
    for x in population[:8]:
        hull = Hull(x)
        a = solve(hull)
        b = solve(hull, vessel=VesselConfig())
        for f in dataclasses.fields(a):
            assert getattr(a, f.name) == getattr(b, f.name), f.name
        assert a.n_hulls == 1 and a.separation_m == 0.0
        arr, brr, _zc = hull.hydro_arrays(0.0)
        xs = hull.x
        vol_old = 2.0 * float(np.trapezoid(arr, xs))
        awp_old = 2.0 * float(np.trapezoid(brr, xs))
        ixx_old = (2.0 / 3.0) * float(np.trapezoid(brr**3, xs))
        assert a.volume == vol_old and a.awp == awp_old
        assert a.i_t == ixx_old and a.bm == ixx_old / vol_old
        assert a.wetted == hull.wetted_surface(0.0)
        assert a.beam_overall_m == a.b_wl_max and a.volume_demi == a.volume


def test_total_resistance_monohull_is_bit_identical_to_the_bare_michell_call(
        ref_hull):
    """`separation=None` must take the identical branch it always took, and
    AXIS 3 must not have moved the monohull's validity flag.

    `valid` used to be `fn <= FN_MICHELL_MAX` alone and is now
    `flow.michell_ok and flow.ittc57_ok`. The second clause is provably True
    everywhere in today's design box (see the Reynolds test below), so the
    expression is the old one — asserted here rather than argued.
    """
    hull = Hull(ref_hull)
    hs, wl = solve_to_displacement(hull, 6000.0, RHO_WATER)
    res = total_resistance(hull, 2.5, hs.wetted, hs.cb, RHO_WATER, wl,
                           beam_wl=hs.b_wl_max, draft=hs.draft)
    ns, nz = res.grid["n_stations"], res.grid["nz"]
    xs, zs, Y = Hull(ref_hull, n_stations=ns).offsets_grid(nz=nz, wl=wl)
    assert res.rw == michell_rw(xs, zs - wl, Y, 2.5, RHO_WATER)
    assert res.n_hulls == 1 and res.separation_m is None
    assert res.method_notes == ()
    assert "n_theta" not in res.grid          # the monohull grid dict is intact
    assert res.valid is (res.fn <= FN_MICHELL_MAX)
    assert res.flow is not None and res.flow.ittc57_ok


def test_a_monohull_mission_reaches_the_ladder_as_a_monohull(ref_hull):
    """The default `MissionSpec` describes exactly the vessel it always did.

    MEASURED as a whole-ladder receipt on 2026-08-14: 30 designs from
    `grammar.sample(30, default_rng(0))` evaluated at `MissionSpec()` against
    the SAME WORKING TREE with `hydrostatics.py`, `evaluate.py` and
    `mission.py` reverted to HEAD produced BYTE-IDENTICAL JSON over the
    violation list, the whole constraint vector and its column names, every
    hydrostatic field, R_w/R_f/R_t/C_w/C_f/sigma/valid/regime, the Michell grid
    dict, the FormFactor, every badge, the rules report, Wh/NM, the ply
    thickness and the unaccounted fraction. Against a FULL HEAD baseline the
    only fields that move are the ones another agent's uncommitted
    `PRODUCTION_GRID` 161x28 -> 241x44 change moves, and `valid`/`regime` are
    identical there too. (Run from an `rsync` copy outside the repository —
    never `git stash`, which has already swept up three agents' uncommitted
    work in this tree once.)
    """
    ev = evaluate(ref_hull, MissionSpec())
    assert ev.hydro.n_hulls == 1
    assert ev.vessel["topology"] == "monohull" and ev.vessel["manning"] == "crewed"
    assert ev.vessel["separation_m"] == 0.0
    assert ev.vessel["beam_overall_wl_m"] == ev.hydro.b_wl_max
    assert ev.vessel["caveats"] == ()
    assert ev.vessel["rules_not_implemented"] == ()
    assert ev.resistance_method == "michell+ittc57"
    assert not any(v.startswith("multihull stability") for v in ev.violations)
    assert ev.g_names == CONSTRAINT_NAMES


# ==========================================================================
# AXIS 1a — the parallel-axis I_T
# ==========================================================================


def test_i_t_is_the_parallel_axis_sum_and_nothing_else(population):
    """I_T = sum_j [ I_T,j + A_wp,j d_j^2 ], checked against the demihull solve.

    Asserted this way round because `i_t` is STORED and `bm` is `i_t / volume`:
    if the two ever came from separate expressions, a number declared twice
    would be back in the one place it does most damage.
    """
    cfg = _cat(0.60)
    for x in population[:10]:
        hull = Hull(x)
        try:
            n, sep, d = vessel_terms(hull, cfg)
        except ValueError:
            continue
        demi, cat = solve(hull), solve(hull, vessel=cfg)
        assert cat.i_t == pytest.approx(n * (demi.i_t + demi.awp * d * d),
                                        rel=1e-14)
        assert cat.bm == pytest.approx(cat.i_t / cat.volume, rel=1e-14)
        assert cat.volume == n * demi.volume and cat.awp == n * demi.awp
        assert cat.wetted == n * demi.wetted
        assert cat.separation_m == sep and d == 0.5 * sep
        # SHARED, because the hulls are identical: adding a demihull moves
        # neither the longitudinal stiffness nor the centres.
        assert cat.bm_l == pytest.approx(demi.bm_l, rel=1e-14)
        assert (cat.lcb, cat.lcf, cat.kb) == (demi.lcb, demi.lcf, demi.kb)
        # DEMIHULL quantities stay the demihull's — `cb` handed to Watanabe's
        # regression against a vessel volume would misreport form drag by
        # exactly the hull count.
        assert (cat.cb, cat.cp, cat.b_wl_max) == (demi.cb, demi.cp,
                                                  demi.b_wl_max)
        assert cat.beam_overall_m == sep + demi.b_wl_max


def test_separation_and_not_demihull_beam_is_what_makes_a_catamaran_stiff(
        ref_hull):
    """MEASURED on `tests/test_phase0.mid_params` at the 6000 kg mission.

    Table RE-MEASURED IN FULL 2026-08-14 at the SOLVED trim equilibrium
    (R2.1) — every asserted quantity reads `ev.hydro`, which now describes
    the attitude the boat actually takes, so the whole row moves together
    (catamaran GM +1.6%: 25.1147 -> 25.5217, 54.3946 -> 55.2817; I_T
    155.200 -> 157.515, 331.015 -> 336.075; the 2026-08-13 level-float
    record is in git history).

        config              KB       BM        I_T [m^4]    T        GM(eq)
        monohull          0.2604    1.3260        7.956   0.4291    0.6685
        cat s/Lwl 0.40    0.1725   26.2525      157.515   0.2657   25.5217
        cat s/Lwl 0.60    0.1725   56.0125      336.075   0.2657   55.2817

    The demihull is not one millimetre wider in any of those rows. I_T rises
    19.5x from the A_wp d^2 term alone, which is the entire argument for a
    slender multihull: deck and roof area for solar, without wetted beam.
    """
    mono = evaluate(ref_hull, MissionSpec())
    c40 = evaluate(ref_hull, MissionSpec(vessel=_cat(0.40)))
    c60 = evaluate(ref_hull, MissionSpec(vessel=_cat(0.60)))
    assert mono.gm_m == pytest.approx(0.6688, abs=5e-3)
    assert c40.gm_m == pytest.approx(25.5217, rel=1e-3)
    assert c60.gm_m == pytest.approx(55.2817, rel=1e-3)
    assert c40.hydro.i_t == pytest.approx(157.515, rel=1e-3)
    assert c40.hydro.b_wl_max == pytest.approx(c60.hydro.b_wl_max, rel=1e-12)
    assert c40.hydro.cb == pytest.approx(c60.hydro.cb, rel=1e-12)
    # The vessel floats HIGHER: 6000 kg split between two hulls.
    assert c40.hydro.draft < mono.hydro.draft
    assert c40.hydro.volume == pytest.approx(mono.hydro.volume, rel=2e-3)


def test_a_catamaran_is_refused_when_its_demihulls_would_intersect(ref_hull):
    """Two hulls in the same water is not a narrow catamaran.

    Thin-ship theory is linear in the hull surface and the waterplane integral
    is linear in the half-breadth: BOTH return a plausible number for two
    demihulls that overlap. `resistance._separation_or_raise` already refused
    this on the wave side; this is the same refusal on the stability side, and
    it must be here because `hydrostatics` runs first.

    MEASURED on `mid_params`: LWL 10.000 m, moulded max beam 3.5527 m, so
    s/Lwl 0.30 = 3.000 m INTERSECTS and 0.40 = 4.000 m does not.
    """
    hull = Hull(ref_hull)
    assert moulded_max_beam(hull) == pytest.approx(3.5527, abs=1e-3)
    with pytest.raises(ValueError, match="INTERSECT"):
        vessel_terms(hull, _cat(0.30))
    ev = evaluate(ref_hull, MissionSpec(vessel=_cat(0.30)))
    assert not ev.ok and ev.tier == "L0"
    assert any(v.startswith("vessel:") and "INTERSECT" in v
               for v in ev.violations), ev.violations
    assert ev.hydro is None and ev.resistance is None
    assert ev.hull_lwl_m == pytest.approx(10.0)   # a known length is not lost


def test_a_trimaran_is_declarable_and_refused_by_name(ref_hull):
    """The AXIS EXISTS and the capability does not — those are different.

    A trimaran's amas are not copies of its centre hull, `grammar.PARAMS`
    carries exactly one moulded surface, and `catamaran_interference` derives
    its factor from two IDENTICAL translated Kochin amplitudes. Refusing by
    name keeps the gap visible; summing three copies of one genome would report
    a vessel nobody would build.
    """
    ev = evaluate(ref_hull, MissionSpec(
        vessel=VesselConfig(topology=Topology.TRIMARAN,
                            separation_over_lwl=0.60)))
    assert not ev.ok and ev.tier == "L0" and ev.hydro is None
    msg = "; ".join(ev.violations)
    assert "trimaran" in msg and "NOT IMPLEMENTED" in msg
    assert "monohull" in msg and "catamaran" in msg      # what IS evaluable


# ==========================================================================
# AXIS 1b — THE SAFETY HALF. What a catamaran is told about its stability.
# ==========================================================================


def test_an_enormous_gm_is_never_reported_as_a_multihull_safety_verdict(
        ref_hull):
    """THE REGRESSION THIS FEATURE WOULD OTHERWISE HAVE BEEN.

    The parallel-axis term takes the reference hull from GM 0.6688 m to
    54.3946 m at s/Lwl 0.60 — against a `limits.CATEGORY_TABLE` floor of 0.45 m
    for category C, and against 0.15-0.35 m in the four national codes
    transcribed in `docs/research/standards/NATIONAL-CODES.md` §9. So R-GM
    passes by 121x, and a reader of `ev.rules` alone would conclude the boat is
    safe.

    IT IS NOT THE SAME QUESTION. A monohull self-rights below its angle of
    vanishing stability, so a GM floor is a fair proxy. A catamaran's righting
    moment PEAKS when the windward hull lifts and collapses past it, and the
    vessel is then STABLE INVERTED and cannot self-right — which is why ISO
    12217 addresses inversion and escape for habitable multihulls rather than
    resting on a metacentric floor.

    So a multihull is INFEASIBLE BY EXPLICIT REFUSAL. It is a violation and not
    a constraint row on purpose: a row that is a large constant for every
    multihull and satisfied for every monohull carries no gradient while
    occupying an NSGA-II dimension (the E4 defect), and it would have changed
    the vector's SHAPE for monohulls.
    """
    ev = evaluate(ref_hull, MissionSpec(vessel=_cat(0.60)))
    assert ev.gm_m > 100.0 * gm_floor("C")
    assert ev.g["gm"] < 0.0                    # the monohull proxy is satisfied
    # RE-MEASURED 2026-08-19 (R2.2): the blanket refusal is REPLACED by a
    # computed criterion for this sub-15 m class — NZ Part 40A App.1
    # cl 1.3, uncontrolled-crowding heel/trim, bar 8 deg — so feasibility
    # is now DECIDED, not refused. The claim this test exists for
    # survives intact: GM is not what decided. The receipt names the
    # criterion, carries its measured angles, and never cites GM.
    cl13 = ev.vessel["cl13"]
    assert cl13 is not None and cl13["passes"] is not None
    assert ev.vessel["stability_criterion"].startswith("NZ Part 40A")
    assert "GM" not in ev.vessel["stability_criterion"].split("—")[0]
    if not cl13["passes"]:
        assert any("cl 1.3 FAILED" in v for v in ev.violations)
    # A monohull gets none of this: no cl13 receipt, no refusal strings.
    mono = evaluate(ref_hull, MissionSpec())
    assert mono.vessel["cl13"] is None
    assert multihull_stability_refusal(mono.hydro, 0.5) == ()


def test_the_multihull_criterion_decides_on_every_multihull(population):
    """No catamaran, at any spacing, is ever feasible on a GM floor alone.

    RE-POINTED 2026-08-19 (R2.2): the mechanism carrying that claim moved
    from a blanket refusal to a COMPUTED criterion (NZ Part 40A App.1
    cl 1.3 for this sub-15 m population). What must hold on every
    multihull now: the cl13 receipt exists and DECIDED — feasible only
    through a passing criterion, never through the GM row alone — and a
    failing criterion is a named violation. A criterion that decided on
    some designs and not others would be worse than none.
    """
    seen = 0
    for x in population[:12]:
        for sep in (0.30, 0.50, 0.80):
            ev = evaluate(x, MissionSpec(vessel=_cat(sep)))
            if ev.hydro is None:
                continue                        # refused earlier, intersection
            seen += 1
            cl13 = ev.vessel["cl13"]
            if cl13 is None:
                # the population spans past 15 m LWL: those hulls are the
                # cl 1.4 class, which stays refusal-first until the windage
                # declarables land — and the refusal must still fire.
                assert not ev.ok
                assert any(v.startswith("multihull stability")
                           for v in ev.violations)
                continue
            assert cl13["passes"] is not None
            if ev.ok:
                assert cl13["passes"], (
                    "a catamaran came back feasible WITHOUT a passing "
                    "criterion — the GM-floor regression this file exists "
                    "to prevent")
            if not cl13["passes"]:
                assert any("cl 1.3 FAILED" in v for v in ev.violations)
    assert seen >= 10, seen


def test_the_offset_load_lever_is_the_vessel_beam_not_the_demihull_beam(
        ref_hull):
    """R-OLH's crew crowd to the edge of the BRIDGE DECK, s further out.

    `iso12217.assess` uses `beam_m` for exactly one thing, `b = 0.40 * beam`,
    and passing a demihull's beam for a catamaran would understate the heeling
    moment by the whole separation — the flattering direction. MEASURED on
    `mid_params` at s/Lwl 0.60: the demihull's moulded beam is 3.0824 m and the
    vessel's is 6.000 + 3.0824 = 9.0824 m, so the crew lever is 3.6330 m rather
    than 1.2330 m and the offset moment is 2.9465x what a demihull lever gives.
    """
    ev = evaluate(ref_hull, MissionSpec(vessel=_cat(0.60)))
    olh = [f for f in ev.rules["findings"] if f["rule_id"] == "R-OLH"]
    assert olh, ev.rules
    b_demi = 2.0 * float(Hull(ref_hull).y_chine.max())
    b_oa = ev.hydro.separation_m + b_demi
    assert b_demi == pytest.approx(3.0824, abs=1e-3)
    assert f"{0.40 * b_oa:.2f} m offset" in olh[0]["note"], olh[0]["note"]
    assert b_oa / b_demi == pytest.approx(2.9465, abs=1e-3)


def test_two_demihulls_are_two_shells(ref_hull):
    """Counting, not modelling: the same moulded surface built twice.

    MEASURED on `mid_params` at the 6000 kg mission: shell area 46.707 m^2
    per demihull; `structure_kg` 1087.187 -> 1824.921 (RE-MEASURED
    2026-08-19 at the Gate 6R re-shape — the ISO 12215-5:2008(E) selection
    picks a thinner sheet for this boat than the flat-floor model did, so
    both masses dropped from the 1268.385 -> 2129.074 of the previous
    pin; the CLAIM — two shells, one deck — is unchanged). NOT exactly
    2x, and it must not be — `weight_budget` also carries the deck and
    the fit-out, and only the SHELL is built twice.
    """
    from navalai.energy import shell_area_m2
    assert shell_area_m2(Hull(ref_hull)) == pytest.approx(46.707, abs=1e-3)
    mono = evaluate(ref_hull, MissionSpec())
    cat = evaluate(ref_hull, MissionSpec(vessel=_cat(0.60)))
    assert mono.weights.structure_kg == pytest.approx(1087.187, abs=1e-2)
    assert cat.weights.structure_kg == pytest.approx(1824.921, abs=1e-2)
    assert 1.0 < cat.weights.structure_kg / mono.weights.structure_kg < 2.0
    assert any("KG is a single-hull KG" in c for c in cat.vessel["caveats"])
    assert any("bridge deck contributes none" in c
               for c in cat.vessel["caveats"])


# ==========================================================================
# AXIS 2 — MANNING selects the rule set
# ==========================================================================


def test_uncrewed_is_not_crewed_with_zero_people(ref_hull):
    """The RCD does not govern uncrewed craft, so ISO 12217-1 cannot answer.

    12217-1 is harmonised UNDER Directive 2013/53/EU and its whole assessment
    is built out of crew mass, accommodation and escape. Running it on a drone
    would produce a heel angle from a crew that is not aboard, under a header
    naming a standard that does not cover the craft — `gate2m.py` printing
    KCS's EFD figure over a Wigley hull, in the rules tier.

    So the assessment is NOT RUN and its absence is a REFUSAL, never a silence:
    nothing in this repository implements a stability rule set for uncrewed
    craft, and such a hull must not come back blessed by the scantling half
    alone.
    """
    crewed = evaluate(ref_hull, MissionSpec())
    drone = evaluate(ref_hull, MissionSpec(
        vessel=VesselConfig(manning=Manning.UNCREWED)))
    ids = lambda ev: {f["rule_id"] for f in ev.rules["findings"]}   # noqa: E731
    assert {"R-GM", "R-OLH", "R-DFH", "R-CAT"} <= ids(crewed)
    assert not ({"R-GM", "R-OLH", "R-DFH", "R-CAT"} & ids(drone))
    assert ids(drone), "the scantling rules still apply to a drone"
    assert not drone.ok
    body = " ".join(drone.violations)
    assert "manning=uncrewed" in body
    assert "NOT ASSESSED and NOTHING was assessed in its place" in body
    assert "NO stability assessment of any kind" in body
    assert "IGNORED" in body                    # mission.crew is not applied
    assert drone.vessel["manning"] == "uncrewed"
    assert drone.vessel["rules_not_implemented"]
    # An uncrewed MULTIHULL must not be told that R-OLH's verdict is a monohull
    # verdict, because R-OLH was never run — a refusal that misdescribes what
    # happened is worse than one clause shorter.
    dc = evaluate(ref_hull, MissionSpec(vessel=_cat(0.60, Manning.UNCREWED)))
    # RE-MEASURED 2026-08-19 (R2.2): an uncrewed sub-15 m cat passes
    # cl 1.3 TRIVIALLY (zero persons, zero crowding moment — the receipt
    # says so) and no multihull refusal string remains; the R-OLH caveat
    # is gone WITH the refusal, which is what this assert always wanted.
    assert not [v for v in dc.violations
                if v.startswith("multihull stability")]
    assert dc.vessel["cl13"]["persons"] == 0
    assert dc.vessel["cl13"]["passes"] is True


def test_liveaboard_records_the_gap_it_has_without_inventing_a_bar(ref_hull):
    """ISO 12217-1 DOES cover habitable craft, so the rule set still applies.

    What is missing is the habitability/downflooding-opening/escape half, and
    that is recorded rather than turned into a violation: a monohull liveaboard
    is not thereby unsafe, and inventing a bar for it would be the mirror of
    the defect this whole file exists to prevent. For a habitable MULTIHULL the
    missing piece IS inversion and escape, and the multihull refusal already
    fails on exactly that — so it is not counted twice.
    """
    live = evaluate(ref_hull, MissionSpec(
        vessel=VesselConfig(manning=Manning.LIVEABOARD)))
    assert {"R-GM", "R-OLH"} <= {f["rule_id"] for f in live.rules["findings"]}
    gaps = " ".join(live.vessel["rules_not_implemented"])
    assert "manning=liveaboard" in gaps and "ESCAPE" in gaps
    assert not any("liveaboard" in v for v in live.violations)
    assert live.ok == evaluate(ref_hull, MissionSpec()).ok


# ==========================================================================
# AXIS 3 — REGIME, derived from Fn and Re, and it REFUSES
# ==========================================================================


def test_a_small_hull_is_a_fast_hull_and_both_envelopes_are_derived():
    """MEASURED with `nu_water(1000.0)` — Froude scales as 1/sqrt(L).

        L [m]   speed   Fn      Re         Michell   ITTC-57
        1.0     2 kn    0.329   9.03e5     inside    inside (transition band)
        1.0     3 kn    0.493   1.35e6     OUTSIDE   inside (transition band)
        1.0     4 kn    0.657   1.81e6     OUTSIDE   inside (transition band)
        1.0     1 kn    0.164   4.51e5     inside    OUTSIDE — laminar
        12.0    6 kn    0.285   3.25e7     inside    inside

    A 1 m drone crosses FN_MICHELL_MAX at about 2.7 kn, and it is inside the
    laminar-turbulent transition — where ITTC-57, a FULLY TURBULENT correlation
    line, is being extrapolated — at every speed in that table. There is no
    transitional correction in `resistance` and none is invented here.
    """
    rows = ((1.0, 2, 0.3286, 9.025e5, True, True),
            (1.0, 3, 0.4928, 1.354e6, False, True),
            (1.0, 4, 0.6571, 1.805e6, False, True),
            (1.0, 1, 0.1643, 4.513e5, True, False),
            (12.0, 6, 0.2845, 3.249e7, True, True))
    for lwl, kn, fn, re, michell, ittc in rows:
        fr = flow_regime(kn * 0.514444, lwl, RHO_WATER)
        assert fr.fn == pytest.approx(fn, abs=5e-4)
        assert fr.re == pytest.approx(re, rel=1e-3)
        assert (fr.michell_ok, fr.ittc57_ok) == (michell, ittc)
        assert fr.valid is (michell and ittc)
        assert bool(fr.envelope) is not (michell and ittc
                                         and re >= RE_FULLY_TURBULENT)


def test_the_friction_line_is_refused_below_transition_not_quietly_used():
    """Re < RE_TRANSITION_ONSET is the existing L1-INVALID machinery, extended.

    `L1-INVALID` ranks BELOW L0 in `tier_rank`, so an out-of-envelope number can
    never compare as a valid L1 result. The refusal says which model left its
    envelope, because validity now has TWO causes and a message naming only the
    Froude one would misreport a slow 1 m hull as a planing boat.
    """
    fr = flow_regime(0.5, 1.0, RHO_WATER)
    assert not fr.ittc57_ok and fr.michell_ok and not fr.valid
    why = " ".join(fr.envelope)
    assert "ITTC-1957" in why and "FULLY TURBULENT" in why
    assert "no transitional correction" in why
    assert nu_water(RHO_WATER) > 0.0


def test_the_transition_band_is_reported_and_the_gap_is_recorded(ref_hull):
    """A model out of SUPPORT but inside VALIDITY is a receipt, not a bar.

    The band 5e5..3e6 IS reachable in today's design box — `grammar.PARAMS`
    bottoms out at LWL 4.0 m and `mission.FIELD_RANGES` at 1.0 kn, which is
    Re 1.81e6. Turning it into a refusal would move the friction number on
    hulls the product runs, and that is a MEASURED decision about a bar rather
    than a drive-by change. So it is carried on `Evaluation.resistance_envelope`
    beside `holtrop_envelope_violations` and NOT counted as a violation, and
    the gap is stated in `resistance.py` above the constants.

    The LAMINAR bound below it is provably unreachable in the current box (the
    smallest, slowest admissible hull is 3.6x above it), which is why it could
    be added without touching one existing result.
    """
    # The smallest, slowest hull the design box admits: LWL 4.0 m at 1.0 kn.
    # It is INSIDE the transition band and 3.61x clear of laminar.
    worst = flow_regime(1.0 * 0.514444, 4.0, RHO_WATER)
    assert RE_TRANSITION_ONSET <= worst.re < RE_FULLY_TURBULENT
    assert worst.re / RE_TRANSITION_ONSET == pytest.approx(3.61, abs=0.05)
    assert worst.valid and worst.ittc57_ok and worst.envelope
    assert "EXTRAPOLATION" in " ".join(worst.envelope)
    # It is carried as a RECEIPT on the evaluation and never as a violation.
    hull = Hull(ref_hull)
    hs, wl = solve_to_displacement(hull, 6000.0, RHO_WATER)
    res = total_resistance(hull, 0.20, hs.wetted, hs.cb, RHO_WATER, wl,
                           beam_wl=hs.b_wl_max, draft=hs.draft)
    assert RE_TRANSITION_ONSET <= res.flow.re < RE_FULLY_TURBULENT
    assert res.valid and "EXTRAPOLATION" in " ".join(res.flow.envelope)
    ev = evaluate(ref_hull, MissionSpec())
    assert isinstance(ev.resistance_envelope, tuple)
    assert not any("ITTC" in v for v in ev.violations)


def test_every_hull_in_todays_box_keeps_the_old_validity_expression(population):
    """`valid` gained a clause and did not change value. Asserted, not argued.

    This is the other half of "the monohull path is unchanged": AXIS 3 widened
    the definition of validity, and if any hull in the design box were below
    the transition Reynolds number, that widening would have silently
    invalidated results the ladder used to accept.
    """
    m = MissionSpec()
    for x in population:
        ev = evaluate(x, m)
        if ev.resistance is None:
            continue
        assert ev.resistance.flow.ittc57_ok
        assert ev.resistance.valid is (ev.resistance.fn <= FN_MICHELL_MAX)


# ==========================================================================
# HALF TWO: separation in the PRODUCTION wave-resistance path
# ==========================================================================


def test_separation_reaches_the_production_wave_resistance(ref_hull):
    """The incident: `total_resistance` called `michell_rw` with no separation.

    MEASURED on `mid_params` at the 6000 kg mission, 5 kn (Fn 0.260), floated
    as a catamaran so both arms share one waterline and one rho — R_w(pair)
    against twice one demihull's R_w at the SAME state:

        s/Lwl   sep [m]   n_theta   R_w pair   2 x R_w demi     ratio
        0.40      4.000      880     272.376      246.120     1.106683
        0.60      6.000      880     246.705      246.120     1.002379
        1.00     10.000      880     245.124      246.120     0.995955

    The ratio is neither 1 nor monotone, which is the point: separation is a
    real optimisation variable and the wiring is what lets an optimiser see it.
    Before this, all three rows read 246.120.

    (An earlier draft read 1.0797/0.9779/0.9717 because the demihull arm was
    computed at rho 1025 against the ladder's 1000 — a 2.5% error on a RATIO
    that should be rho-free. Recorded because it is the trap `nu_water` exists
    for: the two arms of a comparison must describe the same water.)
    """
    hull = Hull(ref_hull)
    seen = {}
    # RE-MEASURED 2026-08-14 (R2.1): the resistance inputs now come from
    # the SOLVED trim equilibrium, moving each ratio by <0.04% — the
    # interference physics is untouched (same 4cos^2 factor), only the
    # draft/wetted inputs describe the attitude the boat actually takes.
    for s, want in ((0.40, 1.107024), (0.60, 1.002418), (1.00, 0.995957)):
        m = MissionSpec(vessel=_cat(s))
        ev = evaluate(ref_hull, m)
        demi = total_resistance(hull, m.cruise_speed_ms(), ev.hydro.wetted / 2,
                                ev.hydro.cb, RHO_WATER, ev.wl,
                                beam_wl=ev.hydro.b_wl_max,
                                draft=ev.hydro.draft)
        seen[s] = ev.resistance.rw / (2.0 * demi.rw)
        assert seen[s] == pytest.approx(want, rel=2e-4), (s, seen[s])
        assert ev.resistance.separation_m == pytest.approx(s * 10.0)
        assert ev.resistance.n_hulls == 2
        assert ev.resistance.grid["n_theta"] == n_theta_for_separation(
            10.0, s * 10.0)
    assert not math.isclose(seen[0.40], seen[0.60], rel_tol=1e-3), (
        "the interference term is inert — a separation sweep that returns one "
        "number is the defect this test is named after")


def test_the_production_wave_term_is_the_module_s_own_interference_call(
        ref_hull):
    """`total_resistance(separation=s).rw` is EXACTLY `michell_rw(..., s)`.

    Not "close to": the same float. There must be no second implementation of
    the interference factor inside `total_resistance` — `catamaran_interference`
    is its one home.
    """
    m = MissionSpec(vessel=_cat(0.60))
    ev = evaluate(ref_hull, m)
    ns, nz = ev.resistance.grid["n_stations"], ev.resistance.grid["nz"]
    xs, zs, Y = Hull(ref_hull, n_stations=ns).offsets_grid(nz=nz, wl=ev.wl)
    assert ev.resistance.rw == michell_rw(
        xs, zs - ev.wl, Y, m.cruise_speed_ms(), RHO_WATER, separation=6.0)


def test_the_catamaran_result_says_what_it_does_not_model(ref_hull):
    """No experimental anchor, and no stand-in constant pretending otherwise.

    Insel & Molland decompose a catamaran into a WAVE interference factor and a
    VISCOUS FORM interference factor. The first is now exact within thin-ship
    theory; the second is NOT modelled and nothing multiplies the friction by a
    fabricated 1.1 to make the model look complete.
    """
    ev = evaluate(ref_hull, MissionSpec(vessel=_cat(0.60)))
    notes = " ".join(ev.resistance.method_notes)
    assert "VISCOUS form interference is NOT modelled" in notes
    assert "NO EXPERIMENTAL ANCHOR" in notes
    assert "catamaran" in ev.resistance_method
    assert "NOT modelled" in ev.resistance_method


def test_the_derived_vessel_quantities_are_reported_not_constrained(ref_hull):
    """Overall beam and bridge-deck clearance are a REPORT.

    The genome declares no wet-deck height, so there is nothing to subtract the
    bow-wave rise from; `resistance.wet_deck_clearance_g` refuses an unmeasured
    clearance rather than scoring it as satisfied, and an always-satisfied
    constraint row occupying an NSGA-II dimension is a defect this repository
    has already shipped once. So these are reported and the constraint vector
    is UNCHANGED in length.
    """
    m = MissionSpec(vessel=_cat(0.60))
    ev = evaluate(ref_hull, m)
    assert ev.g_names == CONSTRAINT_NAMES and set(ev.g) == set(CONSTRAINT_NAMES)
    assert ev.vessel["beam_overall_wl_m"] == pytest.approx(
        ev.hydro.separation_m + ev.hydro.b_wl_max, rel=1e-12)
    assert ev.vessel["bridge_deck_clearance_required_m"] == pytest.approx(
        bow_wave_rise(m.cruise_speed_ms()), rel=1e-12)
    assert ev.vessel["separation_over_lwl"] == pytest.approx(0.60)
    assert ev.vessel["models_admitted"] == "michell+ittc57"


# ==========================================================================
# THE CENSUS: what the change is worth, and what it does NOT fix
# ==========================================================================


def test_the_multihull_census_reports_the_unlock_and_the_refusal_together(
        population):
    """THE NUMBER THIS WORK IS JUSTIFIED BY, and the number it is NOT.

    Configuration: `grammar.sample(40, default_rng(0))`, `MissionSpec()` —
    6000 kg, 5 kn, category C, crew 2 — against
    `VesselConfig(CATAMARAN, CREWED, separation_over_lwl=0.30)`. MEASURED
    2026-08-14 on the 22 of 40 whose demihulls clear each other at that spacing
    (the other 18 are correctly REFUSED: a grammar hull at L/B 2.2 is 0.45 Lwl
    wide and cannot sit 0.30 Lwl from its twin):

                        feasible   median GM   `gm` row   `list` row   `rules`
        monohull         2 / 22      0.289 m      13          8          13
        catamaran        0 / 22     31.854 m       0          0           0

    READ BOTH COLUMNS. The stability PHYSICS unlock is real and complete — the
    `gm` row, the `list` row (which used to read INFEASIBLE_G because GM <= 0
    leaves no upright equilibrium to heel about) and the whole rules tier go to
    zero, and the median GM moves from below the floor to 110x it. The
    feasibility COUNT goes to zero anyway, because every one of those 22 now
    carries the explicit multihull-stability refusal. That is the SAFE answer
    and the honest one: a catamaran must not become feasible by clearing a
    monohull GM floor, and until a multihull criterion exists it is refused.

    The bars below are the STRUCTURAL claims rather than the counts, because
    two other agents are concurrently moving `grammar`'s L/B band and
    `limits`'s thresholds — a hard-coded 2/22 would fail for a reason that has
    nothing to do with multihulls. The counts above are the snapshot; the
    assertions are what must hold at any bands.
    """
    cfg = _cat(_CENSUS_SEP_OVER_LWL)
    admissible = [x for x in population if _clears(x, cfg)]
    assert 10 <= len(admissible) < _CENSUS_N, len(admissible)

    def census(mission, xs):
        ok, gms, rows, refused = 0, [], {}, 0
        cl13_pass, cl13_fail, cl14 = 0, 0, 0
        ok_without_pass = 0
        for x in xs:
            e = evaluate(x, mission)
            ok += bool(e.ok)
            if e.hydro is None:
                continue
            gms.append(e.gm_m)
            refused += any(v.startswith("multihull stability")
                           for v in e.violations)
            c = e.vessel.get("cl13")
            if c is None:
                cl14 += (e.vessel.get("n_hulls", 1) or 1) > 1
            elif c["passes"]:
                cl13_pass += 1
            else:
                cl13_fail += 1
            if e.ok and (c is None or not c["passes"]):
                ok_without_pass += 1
            for k in e.g_names:
                if e.g[k] > 0.0:
                    rows[k] = rows.get(k, 0) + 1
        return (ok, gms, rows, refused,
                cl13_pass, cl13_fail, cl14, ok_without_pass)

    (ok_m, gm_m, rows_m, ref_m, *_rest) = census(MissionSpec(), admissible)
    (ok_c, gm_c, rows_c, ref_c,
     p13, f13, n14, ok_no_pass) = census(MissionSpec(vessel=cfg), admissible)

    # The problem exists: judged as monohulls these demihulls are tender.
    assert rows_m["gm"] > 0 and rows_m["list"] > 0 and rows_m["rules"] > 0
    assert min(gm_m) < 0.0 and np.median(gm_m) < gm_floor("C")
    assert ref_m == 0
    # The physics unlock is complete on the stability rows.
    assert rows_c.get("gm", 0) == 0 and rows_c.get("list", 0) == 0
    # The `rules` row is no longer identically zero for cats (2026-08-19):
    # C-23 wired ES-TRIN, the default mission declares river waters, and
    # the census's biggest hulls (>= 20 m / L.B.T >= 100 m3) enter the
    # Directive's scope — where ES-COV honestly FAILS (31 of 33 chapters
    # unimplemented; two bars must not bless a barge). Measured: 5 of 22.
    # The bound: only ES-scope-sized hulls may fire it, and never more
    # than the >= 15 m class count.
    assert rows_c.get("rules", 0) <= n14, (
        f"rules row {rows_c.get('rules', 0)} exceeds the big-hull class "
        f"{n14} — something besides ES-TRIN scope is firing on cats")
    assert min(gm_c) > gm_floor("C")
    assert np.median(gm_c) > 20.0 * max(np.median(gm_m), gm_floor("C"))
    # RE-MEASURED 2026-08-19 (R2.2): the verdict SPLITS by the rule's own
    # applicability. Snapshot on this census: 9 cats in the cl 1.3 class
    # (< 15 m span), every one deciding by the computed criterion (9 pass,
    # 0 fail); 13 in the cl 1.4 class (>= 15 m), every one still
    # refusal-first; 4 of 22 FEASIBLE end-to-end — the first non-empty
    # catamaran feasible set in the project's history, and every one of
    # them earned it through a PASSING criterion, never through the GM
    # row. The structural bars (band-independent):
    assert ref_c == n14 > 0, (
        "every cl 1.4-class cat must still carry the refusal, and only "
        "that class")
    assert p13 + f13 + n14 == len(gm_c)
    assert ok_no_pass == 0, ("a catamaran came back feasible without a "
                             "passing criterion — the GM-floor regression")
    # What the multihull does NOT fix is still there, and this assertion exists
    # so nobody reads the lines above as "feasibility solved": `bend_radius`
    # (plywood cold-bend) and `proportions` (the demihull floating outside
    # `grammar.L_OVER_B_BAND`, a ceiling `docs/SESSION-2026-08-13-HANDOFF.md`
    # records as REFUTED with sources for demihulls — Southampton demihulls run
    # L/B 7-15.1) are untouched by anything here.
    assert rows_c.get("bend_radius", 0) > 0 or rows_c.get("proportions", 0) > 0


def _clears(x, cfg) -> bool:
    try:
        vessel_terms(Hull(x), cfg)
        return True
    except ValueError:
        return False


def test_the_catamaran_latency_is_measured_and_gate_1_s_bar_is_untouched(
        ref_hull):
    """A catamaran evaluation is dearer, and the reason is a MEASURED rule.

    `michell_rw` requires `n_theta >= 880 * max(1, s/Lwl)` for the interference
    term because at the shipped 220 nodes the quadrature error reaches 1.2% and
    CHANGES SIGN with separation, which an optimiser reads as a real optimum.
    Obeying it costs, MEASURED on the production 241 x 44 grid: the Michell
    integral is 6.2 ms at 220 nodes and 24.3 ms at 880.

    MEASURED end to end on `mid_params`, warm, median of five:

        monohull        21.7 ms   <- Gate 1's 50 ms bar, and it did NOT move
        cat s/Lwl 0.40  41.6 ms
        cat s/Lwl 0.60  41.7 ms

    The bar here is 120 ms — ~3x the measured figure, and deliberately not a
    tightened 45: this catches the interference term becoming quadratic in
    something, it does not police milliseconds on a shared machine. Gate 1's
    own bar stays at 50 ms on the monohull it has always measured; softening it
    to admit a catamaran would be moving a bar to make a design pass.
    """
    m = MissionSpec(vessel=_cat(0.60))
    evaluate(ref_hull, m)
    ts = [_timed(ref_hull, m) for _ in range(5)]
    assert float(np.median(ts)) < 120.0, ts
    evaluate(ref_hull, MissionSpec())
    assert _timed(ref_hull, MissionSpec()) < 50.0


def _timed(x, m) -> float:
    t0 = time.perf_counter()
    evaluate(x, m)
    return (time.perf_counter() - t0) * 1e3


def test_the_cl13_criterion_fails_and_capsizes_in_the_directions_it_should(
        ref_hull):
    """The bar fires BOTH ways (LESSONS defect class 3): the same vessel
    that passes with 2 crew must FAIL when the crowd is heavy enough, and
    the no-equilibrium branch must read as a hard fail, not a crash.
    RE-MEASURED expectations, 2026-08-19, on ref_hull as a catamaran at
    s/Lwl 0.60 with the ladder's own displacement and KG.
    """
    from navalai.evaluate import evaluate
    from navalai.geometry import Hull
    from navalai.hydrostatics import multihull_crowding_heel

    ev = evaluate(ref_hull, MissionSpec(vessel=_cat(0.60)))
    hull = Hull(ref_hull)
    t_design = -float(hull.z_keel.min())
    kg = float(ev.masses.vcg_above_keel(t_design))

    # 2 persons: passes, on the small-angle fast path (basis says so).
    t2 = multihull_crowding_heel(hull, ev.hydro, kg, 2,
                                 vessel=_cat(0.60), gm_m=ev.gm_m)
    assert t2.passes is True and t2.heel_deg is not None
    assert t2.heel_deg <= 4.0
    assert any("small-angle" in b for b in t2.basis)

    # 50 persons at the applicability edge on THIS stiff platform:
    # MEASURED exact equilibrium 3.87 deg (fast estimate 3.09 — the 25%
    # nonlinearity that set the fast gate at 2 deg) — a LEGITIMATE pass,
    # through the exact path. The clause is satisfied and the receipt
    # must say which path decided.
    t50 = multihull_crowding_heel(hull, ev.hydro, kg, 50,
                                  vessel=_cat(0.60), gm_m=ev.gm_m)
    assert t50.passes is True
    assert 3.0 < t50.heel_deg < 5.0
    assert not any("small-angle slope" in b for b in t50.basis)

    # THE FAIL DIRECTION (LESSONS defect class 3): the same crowd with the
    # CG raised 20 m — GM collapses, the fast path stands aside, the exact
    # scan finds NO equilibrium at or below 10 deg, and the clause FAILS
    # hard rather than crashing or defaulting.
    th = multihull_crowding_heel(hull, ev.hydro, kg + 20.0, 50,
                                 vessel=_cat(0.60))
    assert th.passes is False
    assert th.heel_deg is None and th.heel_ok is None
    assert any("both fail the 8 deg bar" in b for b in th.basis)

    # uncrewed: trivially true with the zero-moment note.
    t0 = multihull_crowding_heel(hull, ev.hydro, kg, 0,
                                 vessel=_cat(0.60), gm_m=ev.gm_m)
    assert t0.passes is True and "zero" in t0.heel_lever_note

    # applicability: > 50 persons is the cl 1.4 class — computed numbers
    # still returned, but passes is None (not this clause's verdict).
    t51 = multihull_crowding_heel(hull, ev.hydro, kg, 51,
                                  vessel=_cat(0.60), gm_m=ev.gm_m)
    assert t51.applicable is False and t51.passes is None


def test_the_cl14_class_verdicts_with_a_declared_windage_and_refuses_without():
    """R2.2's second half (2026-08-19): with clauses (c)/(d) READ and a
    WindageSpec declared, the >= 15 m catamaran class gets the FULL
    four-clause NZ Part 40A cl 1.4 verdict; undeclared, it refuses by name
    exactly as before. MEASURED on the first >= 15 m-span cat of the
    seed-0 population (17.83 m): 40 m2 at 2.0 m passes all four (wind
    heel 0.7 deg); 400 m2 at 6.0 m fails (c) with the named violation.
    """
    from navalai import grammar
    from navalai.geometry import Hull

    X = grammar.sample(40, np.random.default_rng(0))
    big = next(x for x in X
               if float(Hull(x).x[-1] - Hull(x).x[0]) >= 15.0)
    cfg = _cat(0.30)

    m = MissionSpec(vessel=cfg, windage={"lateral_area_m2": 40.0,
                                         "centroid_above_wl_m": 2.0})
    ev = evaluate(big, m)
    c14 = ev.vessel["cl14"]
    assert c14 is not None and c14["passes"] is True
    assert all(c14["clauses"].values())
    assert not any(v.startswith("multihull stability")
                   for v in ev.violations)

    # the fail direction: an absurd sail-area declaration fails (c), named
    m2 = MissionSpec(vessel=cfg, windage={"lateral_area_m2": 400.0,
                                          "centroid_above_wl_m": 6.0})
    e2 = evaluate(big, m2)
    assert e2.vessel["cl14"]["passes"] is False
    assert any("cl 1.4 FAILED" in v and "(c)" in v for v in e2.violations)

    # undeclared: the refusal, by name, with the declaration instruction
    e0 = evaluate(big, MissionSpec(vessel=cfg))
    assert e0.vessel["cl14"] is None
    assert any("mission.windage" in v or "lateral area" in v
               for v in e0.violations)


def test_the_wind_lever_is_the_rules_own_algebra():
    """h_w = P.A.Z/(9800.Delta_t) with Z = centroid_above_wl + T/2, read
    verbatim — asserted against hand arithmetic on the assessment's own
    output, so the formula cannot drift inside the implementation."""
    from navalai.evaluate import evaluate as _eval
    from navalai.geometry import Hull
    from navalai.hydrostatics import multihull_gz_assessment
    from navalai.mission import WindageSpec
    from tests.test_phase0 import mid_params

    x = mid_params()
    ev = _eval(x, MissionSpec(vessel=_cat(0.60)))
    hull = Hull(x)
    t_design = -float(hull.z_keel.min())
    kg = float(ev.masses.vcg_above_keel(t_design))
    w = WindageSpec(lateral_area_m2=25.0, centroid_above_wl_m=1.5,
                    wind_pressure_pa=350.0)
    a = multihull_gz_assessment(hull, float(ev.hydro.disp_kg), kg,
                                vessel=_cat(0.60), windage=w, persons=2)
    z = 1.5 + 0.5 * t_design
    want = 350.0 * 25.0 * z / (9800.0 * (float(ev.hydro.disp_kg) / 1000.0))
    assert a.wind_lever_m == pytest.approx(want, rel=1e-12)
    # theta_h (wind + crowd) can never sit BELOW the wind-only heel
    if a.wind_heel_deg is not None and a.theta_h_deg is not None:
        assert a.theta_h_deg >= a.wind_heel_deg - 1e-9
    # and the spec refuses an off-table pressure — the rule's, not a knob
    with pytest.raises(ValueError, match="not a row"):
        WindageSpec(lateral_area_m2=25.0, centroid_above_wl_m=1.5,
                    wind_pressure_pa=400.0)


def test_the_6_6_ladder_and_the_rules_tier_vessel_fix_2026_08_19():
    """Two findings in one wire. (1) ev_for_rules carried NO vessel dict,
    so every catamaran was MONOHULL-classified inside the rules tier —
    R-GM emitted on the quantity that does not govern (the exact green
    tick the R-MHS comment warns about). Fixed: the vessel rides along.
    (2) cl 6.6 (operator-sourced 2026-08-19) binds HABITABLE multihulls:
    a crewed cat's R-MHS is now a receipt deferring to the ladder's
    computed criterion; a liveaboard category-C cat gets the 6.6.3
    susceptibility test on its declared windage centroid, continuous at
    V_D^(1/3) = 2.6; susceptible refuses on the NAMED 12217-2 §7.12/7.13
    clauses.
    """
    from dataclasses import replace

    from navalai.formcheck import CASES
    from navalai.rules.iso12217 import inversion_susceptible_6_6_3

    # branch continuity at the transcription's own crossover
    s_at, r_at, l_at = inversion_susceptible_6_6_3(1.0, 2.0, 2.6 ** 3)
    assert l_at == pytest.approx(0.572, abs=1e-12)
    s_lo, _r, l_lo = inversion_susceptible_6_6_3(1.0, 2.0, 1.0)
    assert l_lo == pytest.approx(0.22, abs=1e-12)

    c = {x.key: x for x in CASES}["c"]
    # crewed cat: no monohull R-GM, R-MHS is the deferring receipt
    ev = evaluate(c.params, c.mission)
    ids = {f["rule_id"]: f for f in ev.rules["findings"]}
    assert "R-GM" not in ids, "monohull R-GM re-emitted for a catamaran"
    assert ids["R-MHS"]["passed"] is True
    assert "cl13/cl14" in ids["R-MHS"]["note"]

    v = replace(c.mission.vessel, manning=Manning.LIVEABOARD)
    # liveaboard C, tall declared profile: susceptible, refused on the
    # named 12217-2 clauses
    m = replace(c.mission, vessel=v, design_category="C",
                windage={"lateral_area_m2": 26.0,
                         "centroid_above_wl_m": 6.0})
    e = evaluate(c.params, m)
    f = [x for x in e.rules["findings"] if x["rule_id"] == "R-MHS"][0]
    assert f["passed"] is False and "7.12" in f["note"] and "7.13" in f["note"]
    # liveaboard C, undeclared windage: the refusal names the declaration
    m0 = replace(c.mission, vessel=v, design_category="C")
    e0 = evaluate(c.params, m0)
    f0 = [x for x in e0.rules["findings"] if x["rule_id"] == "R-MHS"][0]
    assert f0["passed"] is False and "mission.windage" in f0["note"]
