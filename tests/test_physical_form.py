"""Gate PF — PHYSICAL FORM REGRESSION: the generated hulls must stay boats.

THE DIRECTIVE THIS FILE ENFORCES (2026-08-14): "Do not accept a hull merely
because it passes grammar.check. A mathematically admissible hull that has an
inappropriate SAC, entrance geometry, L/B, B/T or displacement distribution is
NOT a successful vessel design. Add regression tests so future architecture
changes cannot make the generated forms progressively less boat-like while all
software tests remain green."

Six deterministic cases (`navalai.formcheck.CASES` — fixed parameter vectors,
no sampling) are measured, judged against the SOURCED ranges in this tree,
checked for structural boat-likeness (unimodal SAC, sections that grow then
shrink, an entrance finer than a barge front), and pinned by a RATCHET
(`tests/formcheck_baseline.json`): a change that silently moves a form fails
here with instructions to re-baseline WITH justification, never to widen a
tolerance.

Known findings of the CURRENT tree are themselves fenced (see
`test_case_b_entrance_angle_is_a_recorded_finding`): if a finding silently
disappears, that is information and the test says what to do with it.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from navalai import geometry, grammar
from navalai.formcheck import (ALPHA_E_PROVISIONAL_CEILING_DEG, CASES,
                               SourcedRange, form_descriptors,
                               ratchet_entries, sourced_ranges)
from navalai.formlib import alpha_e_chord_floor_deg
from navalai.limits import hull_role

BASELINE_PATH = Path(__file__).parent / "formcheck_baseline.json"

CASE_KEYS = [c.key for c in CASES]

# Descriptors whose sourced-range verdict is asserted by a DEDICATED test
# below rather than by the blanket sweep (entrance angle has a recorded
# finding on case b; the blanket sweep must not silently absorb it).
_ENTRANCE = "entrance_half_angle_deg"


@pytest.fixture(scope="module")
def described() -> dict:
    """Descriptors for all six cases, computed once per test run."""
    return {c.key: form_descriptors(c.params, c.mission) for c in CASES}


def _case(key: str):
    return next(c for c in CASES if c.key == key)


# ======================================================================= 0.
# the cases themselves are admissible AS THEIR OWN ROLE

def test_there_are_exactly_six_cases_and_they_are_L0_feasible():
    assert len(CASES) == 6
    assert CASE_KEYS == ["a", "b", "c", "d", "e", "f"]
    for c in CASES:
        rep = grammar.check(c.params, vessel=c.vessel)
        assert rep.ok, (
            f"case {c.key} ({c.title}) is no longer L0-feasible as a "
            f"{hull_role(c.vessel).value}: {rep.violations}. The six cases "
            f"are the physical-form regression anchors — re-pick the vector "
            f"with a recorded justification, do not delete the case.")


def test_the_two_drone_cases_are_uncrewed_and_the_two_cats_are_catamarans():
    from navalai.formlib import Topology
    from navalai.mission import Manning
    assert _case("c").vessel.topology is Topology.CATAMARAN
    assert _case("d").vessel.topology is Topology.CATAMARAN
    assert _case("e").vessel.manning is Manning.UNCREWED
    assert _case("f").vessel.manning is Manning.UNCREWED
    # the target class is the target class
    d = _case("d").named
    assert (d["LWL"], d["BWL"]) == (12.0, 0.8), (
        "case d stopped being the project's 12 x 0.8 m demihull class")


# ======================================================================= i.
# descriptors compute, and compute FINITE

@pytest.mark.parametrize("key", CASE_KEYS)
def test_descriptors_compute_finite(described, key):
    d = described[key]
    assert d["meta"]["grammar_ok"], d["meta"]["grammar_violations"]
    assert d["scalars"], "no scalar descriptors at all"
    for name, v in d["scalars"].items():
        assert isinstance(v, float) and math.isfinite(v), (
            f"case {key}: descriptor {name} is not a finite float: {v!r}")
    sac = np.asarray(d["arrays"]["sac_norm"])
    assert np.all(np.isfinite(sac)), f"case {key}: SAC has non-finite entries"
    # normalised by the CONTINUOUS maximum (dense grid including x_mb), so
    # the 11 linspace stations straddle it: the station max sits just under 1
    assert sac.min() >= -1e-12
    assert 0.85 < sac.max() <= 1.0 + 1e-12, (
        f"case {key}: no report station comes near the SAC maximum "
        f"(max {sac.max():.3f}) — the curve is normalised wrongly or the "
        f"peak left the station grid")
    # fullness may be nan ONLY where the section has vanished (the stem)
    full = np.asarray(d["arrays"]["section_fullness"])
    bad = ~np.isfinite(full[:-1])
    assert not bad.any(), (
        f"case {key}: sectional fullness non-finite away from the stem at "
        f"stations {np.flatnonzero(bad)}")
    # every absent descriptor carries a real reason, never a bare flag
    for name, reason in d["absent"].items():
        assert isinstance(reason, str) and len(reason) > 20, (
            f"case {key}: absent descriptor {name} has no substantive reason")
    # the six floats the ladder must deliver for every case that floats
    for name in ("Fn", "Re", "GM_m", "KB_m", "BM_m", "KG_m"):
        assert name in d["scalars"], (
            f"case {key}: {name} missing — the evaluated state stopped "
            f"reaching the descriptors ({d['absent'].get(name)})")


# ====================================================================== ii.
# every descriptor with a SOURCED range in the tree lies inside it

@pytest.mark.parametrize("key", CASE_KEYS)
def test_sourced_ranges_hold(described, key):
    case = _case(key)
    d = described[key]
    sr = sourced_ranges(case)
    for name, rng in sr.items():
        if not isinstance(rng, SourcedRange):
            continue                      # UNKNOWN/REFUSED: no bar to apply
        if name == _ENTRANCE:
            continue                      # dedicated tests below (finding)
        v = d["scalars"].get(name)
        if v is None:
            continue                      # absent-with-reason, checked above
        assert rng.contains(v), (
            f"case {key}: {name} = {v:.4f} is OUTSIDE the sourced range "
            f"{rng} — source: {rng.source}. The form regressed against an "
            f"in-tree source; fix the generator (or the case, with recorded "
            f"justification), do not widen the band.")


def test_the_demihull_cases_respect_the_southampton_bt_floor(described):
    """The one number the whole 2026-08-14 band incident turns on: a demihull
    below B/T 1.50 is OUT OF SOURCED RANGE (Southampton series floor,
    formlib.SOTON_DEMIHULL_B_OVER_T) and the cases must sit above it."""
    from navalai import formlib
    floor = formlib.SOTON_DEMIHULL_B_OVER_T.low
    for key in ("c", "d"):
        v = described[key]["scalars"]["B_over_T"]
        assert v >= floor, (
            f"case {key}: design B/T {v:.3f} fell below the Southampton "
            f"demihull floor {floor} — {formlib.SOTON_DEMIHULL_B_OVER_T.source}")


# ===================================================================== iii.
# SAC is unimodal-ish: rises to ONE maximum near x_mb, then falls

@pytest.mark.parametrize("key", CASE_KEYS)
def test_sac_is_unimodal_with_its_maximum_near_x_mb(key):
    case = _case(key)
    p = case.named
    L = p["LWL"]
    xs = np.linspace(0.0, L, 161)
    A = geometry.sectional_area(case.params, xs)
    a_max = float(A.max())
    assert a_max > 0.0
    i_max = int(np.argmax(A))
    x_max = float(xs[i_max])
    # the maximum sits at the declared max-area station, within one report
    # station spacing (L/10)
    assert abs(x_max - p["x_mb"] * L) <= L / 10.0, (
        f"case {key}: SAC maximum at x = {x_max:.2f} m is not near the "
        f"declared x_mb = {p['x_mb'] * L:.2f} m — the area curve no longer "
        f"peaks where the genome says it does")
    # ONE hump: non-decreasing up to the max, non-increasing after it. The
    # final 2% of length is excluded from the falling branch: the geometric
    # floor on the chine half-breadth (geometry._stations) flattens the
    # delivered area inside the last fraction of the stem, which is a
    # documented kernel property, not a second hump.
    tol = 1e-9 * a_max
    rise = np.diff(A[: i_max + 1])
    assert np.all(rise >= -tol), (
        f"case {key}: SAC falls before its maximum (worst step "
        f"{rise.min():.3e} m^2) — a double hump or hollow in the run")
    keep = xs[i_max:] <= 0.98 * L
    fall = np.diff(A[i_max:][keep])
    assert np.all(fall <= tol), (
        f"case {key}: SAC rises after its maximum (worst step "
        f"{fall.max():.3e} m^2) — a second hump in the forebody")
    # no flat-zero span mid-body: the hull must carry area everywhere
    # between 5% and 95% of LWL
    mid = (xs >= 0.05 * L) & (xs <= 0.95 * L)
    assert float(A[mid].min()) > 0.05 * a_max, (
        f"case {key}: the SAC collapses to "
        f"{float(A[mid].min()) / a_max:.3f} of A_max inside the mid-body — "
        f"a hull with a waist is not one of these six boats")


# ====================================================================== iv.
# entrance angle: above the arithmetic chord floor, below the provisional
# ceiling; the demihull cases inside their DRAWING band; case b's excess is a
# RECORDED FINDING and fenced as such

@pytest.mark.parametrize("key", CASE_KEYS)
def test_entrance_angle_sits_between_floor_and_provisional_ceiling(described,
                                                                   key):
    d = described[key]
    alpha = d["scalars"][_ENTRANCE]
    l_over_b = d["scalars"]["L_over_B"]
    floor = alpha_e_chord_floor_deg(l_over_b, 0.60)
    # the 2%-chord at the stem of a convex waterline cannot be finer than the
    # whole-entry chord; 0.95 covers the floor's L_E/L convention spread
    assert alpha >= 0.95 * floor, (
        f"case {key}: entrance half-angle {alpha:.2f} deg is BELOW the "
        f"arithmetic chord floor {floor:.2f} deg at L/B {l_over_b:.2f} "
        f"(formlib.alpha_e_chord_floor_deg) — the waterline near the stem is "
        f"no longer convex, or the measurement broke")
    assert alpha <= ALPHA_E_PROVISIONAL_CEILING_DEG, (
        f"case {key}: entrance half-angle {alpha:.2f} deg exceeds the "
        f"PROVISIONAL ceiling {ALPHA_E_PROVISIONAL_CEILING_DEG} deg "
        f"(formcheck.ALPHA_E_PROVISIONAL_CEILING_DEG — labelled provisional; "
        f"no in-tree source bounds it) — the bow has collapsed toward a "
        f"barge front")


@pytest.mark.parametrize("key", ("c", "d"))
def test_the_demihull_entrances_sit_inside_the_drawn_band(described, key):
    """The solar-cat demihulls DO meet their family band today (6-12 deg,
    Basis.DRAWING, hull-example sheets 008/009) — pinned so they keep doing
    so."""
    case = _case(key)
    rng = sourced_ranges(case)[_ENTRANCE]
    assert isinstance(rng, SourcedRange)
    alpha = described[key]["scalars"][_ENTRANCE]
    assert rng.contains(alpha), (
        f"case {key}: demihull entrance {alpha:.2f} deg left the drawn band "
        f"{rng} — source: {rng.source}")


def test_case_b_entrance_angle_is_a_recorded_finding(described):
    """FINDING, FENCED. The 15 m round-bilge monohull delivers a 2%-chord
    entrance of ~23 deg against its family band of 7-14 deg (approx) — the
    generated forebody is blunter than fine-entry practice, exactly the class
    of defect the audit said nothing measured. This test asserts the finding
    IS STILL THERE; when kernel or case work closes it, invert this into a
    contains() assertion and re-baseline, do not delete it."""
    rng = sourced_ranges(_case("b"))[_ENTRANCE]
    assert isinstance(rng, SourcedRange)
    alpha = described["b"]["scalars"][_ENTRANCE]
    assert alpha > rng.high, (
        f"case b entrance {alpha:.2f} deg is now INSIDE {rng} — the recorded "
        f"finding has been closed. Good: move case b into "
        f"test_the_demihull_entrances_sit_inside_the_drawn_band's pattern, "
        f"update docs/PHYSICAL_FORM_REPORT.md, and re-baseline the ratchet "
        f"with this justification.")


# ======================================================================= v.
# monotone shape sanity on the report stations: sections grow, then shrink

@pytest.mark.parametrize("key", CASE_KEYS)
def test_sections_grow_then_shrink_along_x(described, key):
    sac = np.asarray(described[key]["arrays"]["sac_norm"])
    i = int(np.argmax(sac))
    assert 0 < i < len(sac) - 1, (
        f"case {key}: the maximum section is at the {'transom' if i == 0 else 'stem'}")
    assert np.all(np.diff(sac[: i + 1]) > 0.0), (
        f"case {key}: station areas do not strictly grow toward the maximum: "
        f"{np.round(sac, 3).tolist()}")
    assert np.all(np.diff(sac[i:]) < 0.0), (
        f"case {key}: station areas do not strictly shrink toward the stem: "
        f"{np.round(sac, 3).tolist()}")


# ====================================================================== vi.
# the RATCHET: measured values pinned with descriptor-appropriate tolerances

def test_the_baseline_file_exists_and_covers_all_six_cases():
    assert BASELINE_PATH.exists(), (
        "tests/formcheck_baseline.json is missing. Generate it with "
        "`python3 scripts/physical_form_report.py --write-baseline` and "
        "commit it — the ratchet is the regression fence.")
    base = json.loads(BASELINE_PATH.read_text())
    assert sorted(base) == sorted(CASE_KEYS)


@pytest.mark.parametrize("key", CASE_KEYS)
def test_ratchet_no_silent_form_drift(described, key):
    base = json.loads(BASELINE_PATH.read_text())[key]
    current = ratchet_entries(described[key])
    gone = sorted(set(base) - set(current))
    new = sorted(set(current) - set(base))
    assert not gone, (
        f"case {key}: descriptors {gone} vanished since the baseline. A "
        f"descriptor that stops being computable is a regression, not a "
        f"cleanup — restore it or re-baseline with a written justification "
        f"(scripts/physical_form_report.py --write-baseline).")
    assert not new, (
        f"case {key}: new descriptors {new} are not in the baseline — "
        f"re-baseline (scripts/physical_form_report.py --write-baseline) in "
        f"the same commit that adds them.")
    drifted = []
    for name, b in base.items():
        v = current[name]["value"]
        if abs(v - b["value"]) > b["tol"]:
            drifted.append(f"{name}: {b['value']:.5g} -> {v:.5g} "
                           f"(tol {b['tol']:.3g})")
    assert not drifted, (
        f"case {key}: the physical form MOVED:\n  " + "\n  ".join(drifted) +
        "\nThis ratchet exists so architecture changes cannot silently make "
        "the generated hulls less boat-like while software tests stay green. "
        "If the movement is intended and MEASURED to be an improvement, "
        "re-baseline with `python3 scripts/physical_form_report.py "
        "--write-baseline` and record the justification in the same commit; "
        "do not widen a tolerance to make this pass.")


# ===================================================================== vii.
# multihull configuration descriptors are real, and refusal paths are honest

def test_multihull_cases_carry_a_physical_separation(described):
    for key in ("c", "d"):
        s = described[key]["scalars"]
        assert s["separation_m"] > s["demihull_beam_m"], (
            f"case {key}: demihulls at {s['separation_m']:.2f} m spacing "
            f"with {s['demihull_beam_m']:.2f} m beams would intersect")
        # and the ladder said so too: the evaluation carries the explicit
        # multihull-stability refusal, never a silent GM pass
        viols = described[key]["meta"]["evaluation"]["violations"]
        assert any("multihull stability" in v for v in viols), (
            f"case {key}: the multihull stability refusal vanished from the "
            f"evaluation — a catamaran must never be silently blessed on GM")


def test_uncrewed_cases_are_refused_a_stability_ruleset_not_granted_one(
        described):
    for key in ("e", "f"):
        viols = described[key]["meta"]["evaluation"]["violations"]
        assert any("manning=uncrewed" in v for v in viols), (
            f"case {key}: the UNCREWED refusal vanished — a drone must not "
            f"come back blessed by a crewed rule set (or by none at all, "
            f"silently)")


def test_a_grammar_refused_vector_yields_absent_descriptors_not_numbers():
    """Refusal path: the owner's 12 x 0.8 m dimensions AS A MONOHULL are
    refused by L0, and form_descriptors must report absence-with-reason, not
    fabricate geometry descriptors for a hull that cannot be built."""
    bad = _case("d").params.copy()          # 12 x 0.8 — a demihull vector
    d = form_descriptors(bad, mission=None)  # judged as a MONOHULL (no vessel)
    assert not d["meta"]["grammar_ok"]
    assert not d["scalars"], "descriptors were computed for a refused vector"
    assert d["absent"], "no absence reasons recorded"
    assert all("grammar.check refused" in r for r in d["absent"].values())
