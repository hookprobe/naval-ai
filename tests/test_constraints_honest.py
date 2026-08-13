"""Gate 1C — the constraint vector: complete, ordered, finite, and never
reporting a state it could not compute as the ideal one.

Motivating incidents, all MEASURED, all from the same family: DEGENERATE
PHYSICS REPORTED AS A PERFECT RESULT.

  E10  `violations = [why[k] for k, v in g.items() if v > 0.0]`. `nan > 0.0`
       is False, so ANY non-finite constraint produced `violations=[]` and
       `ok=True`. A nan cruise speed gave Rt=nan, Fn=nan and Wh/NM=nan, wrote
       `('L1', nan)` badges into the provenance DB, and served them over HTTP
       as a literal `NaN` — not valid JSON (RFC 8259). Found independently on
       the other side of the ladder: Holtrop at Cp=0.96 returned a COMPLEX
       resistance, 8504.47-1749.72j, into a float-typed field. A defect class,
       not a site.

  E11  `weights.trim_angle_deg` returned 0.0 for GM_L <= 0 and `evaluate`
       returned heel 0.0 for GM <= 1e-6 — the BEST POSSIBLE value of each,
       returned exactly where the equilibrium it describes stopped existing.
       With an LCG-LCB lever of 4.0 m: GM_L=+40 -> +5.71 deg (violated),
       GM_L=0 -> +0.000 deg -> g['trim'] = -2.000 FEASIBLE, GM_L=-500
       likewise FEASIBLE.

  E13  g['list'] read EXACTLY -2.000 across 800 evaluations.

  E16  `assert tuple(g) == CONSTRAINT_NAMES` was the ONLY thing binding the
       dict's order to the optimizer's G columns, and `python -O` strips
       asserts (verified: `__debug__` is False).

  B8   LCB unconstrained: -6.47 and -7.86 %LWL on delivered hulls.

  B9   L0 bounds BWL/T at 12 on the PARAMETER vector; a delivered hull floated
       at B/T 14.4. Nothing re-checked proportions on the floated state.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai import db, grammar
from navalai.evaluate import (CONSTRAINT_NAMES, INFEASIBLE_G,
                              ConstraintOrderError, constraint_vector,
                              evaluate, is_real_finite)
from navalai import limits
from navalai.limits import LCB_BAND_PCT_LWL, LIST_LIMIT_DEG, TRIM_LIMIT_DEG
from navalai.mission import MissionSpec
from navalai.weights import MassAggregate, MassItem, aggregate, trim_angle_deg
from tests.test_phase0 import mid_params

_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ref():
    return evaluate(mid_params(), MissionSpec())


# ------------------------------------------------------- E10: non-finite


def test_a_nonfinite_constraint_is_a_violation_not_a_pass(monkeypatch):
    """E10. `nan > 0.0` is False, so the violation filter skipped it and the
    design came back ok=True with violations=(). A quantity we could not
    compute is the one thing that must never read as feasible."""
    import navalai.evaluate as E

    real_gm = E.gm
    monkeypatch.setattr(E, "gm", lambda *a, **k: float("nan"))
    ev = evaluate(mid_params(), MissionSpec())
    monkeypatch.setattr(E, "gm", real_gm)

    assert not ev.ok, "a nan constraint made the design feasible again"
    assert any("not a finite number" in v for v in ev.violations), ev.violations
    # and the value handed to NSGA-II is finite and positive: nan in the G
    # matrix is not "infeasible", it is a comparison that silently answers
    # False in every direction.
    assert all(is_real_finite(v) for v in ev.g.values())
    assert ev.g["gm"] == INFEASIBLE_G


def test_a_nonfinite_quantity_is_never_badged_as_a_plain_l1_result():
    """E10, the badge side. A nan cruise speed produced Rt=nan / Wh_per_NM=nan
    carrying badges ('L1', nan) — honesty rule 1 asks for value, tier and
    sigma, and a nan has no value to badge."""
    m = MissionSpec()
    m.cruise_speed_kn = float("nan")
    ev = evaluate(mid_params(), m)

    assert not ev.ok
    assert ev.badges["resistance"][0] == "L1-INVALID"
    assert ev.badges["wh_per_nm"][0] == "L1-INVALID"
    assert any("not a reportable L1 quantity" in v for v in ev.violations), \
        ev.violations
    # the quantities that ARE computable keep their honest L1 badge
    assert ev.badges["displacement"][0] == "L1"


def test_nonfinite_numbers_never_reach_the_provenance_db(tmp_path):
    """E10 downstream. The nan reached the DB `uncertainty` column and then the
    HTTP response as a bare `NaN`, which no conforming JSON parser accepts. The
    row is refused; the refusal is not silent, it is in ev.violations."""
    m = MissionSpec()
    m.cruise_speed_kn = float("nan")
    prov = db.Provenance(tmp_path / "p.sqlite3")
    ev = evaluate(mid_params(), m, provenance=prov)
    assert not ev.ok

    import json
    rows = _all_results(prov)
    assert rows, "nothing was recorded at all — the guard is too wide"
    for quantity, value, sigma in rows:
        assert is_real_finite(value) and is_real_finite(sigma), \
            f"{quantity} wrote {value!r} +- {sigma!r}"
        # the receipt the gap actually names: it must survive json.dumps and
        # come back as a number, not as the non-standard literal NaN.
        assert "NaN" not in json.dumps({"v": value, "s": sigma})


def test_is_real_finite_rejects_a_complex_resistance():
    """The same defect with a better disguise (navalai.holtrop, Cp=0.96 ->
    8504.47-1749.72j in a float-typed field). `math.isfinite` RAISES on a
    complex, so the naive guard would have crashed rather than caught it."""
    assert is_real_finite(1.5) and is_real_finite(-0.0)
    assert not is_real_finite(float("nan"))
    assert not is_real_finite(float("inf"))
    assert not is_real_finite(complex(8504.47, -1749.72))
    assert not is_real_finite(None)
    with pytest.raises(TypeError):
        math.isfinite(complex(1.0, 1.0))       # why the helper exists


# ------------------------------------- E11: undefined is not ideal


def test_trim_is_none_not_zero_when_the_hull_is_longitudinally_unstable():
    """E11, reproduced with the register's own numbers: an LCG-LCB lever of
    4.0 m against TRIM_LIMIT_DEG. 0.0 deg is PERFECT trim, and it was returned
    exactly where the equilibrium stopped existing."""
    agg = aggregate([MassItem(id="m", mass_kg=1000.0, x_m=9.0, z_m=-0.2)])
    lcb = 5.0                                   # lever = 4.0 m

    assert trim_angle_deg(agg, lcb, 1000.0, 40.0) == pytest.approx(5.7106, abs=1e-3)
    assert trim_angle_deg(agg, lcb, 1000.0, 0.0) is None
    assert trim_angle_deg(agg, lcb, 1000.0, -500.0) is None
    assert trim_angle_deg(agg, lcb, 1000.0, float("nan")) is None
    # the old return value would have satisfied the constraint outright
    assert abs(0.0) - TRIM_LIMIT_DEG < 0.0


def test_an_undefined_angle_makes_its_constraint_infeasible(monkeypatch):
    """E11 in the ladder: the constraint must go INFEASIBLE, and the violation
    must say the angle is UNDEFINED rather than merely too large — those are
    different findings and a designer acts on them differently."""
    import navalai.evaluate as E

    monkeypatch.setattr(E, "gm_long", lambda *a, **k: -500.0)
    monkeypatch.setattr(E, "gm", lambda *a, **k: -0.4)
    ev = evaluate(mid_params(), MissionSpec())

    assert not ev.ok
    assert ev.trim_deg is None and ev.list_deg is None
    assert ev.g["trim"] == INFEASIBLE_G and ev.g["list"] == INFEASIBLE_G
    assert any("static trim is UNDEFINED" in v for v in ev.violations), ev.violations
    assert any("static list is UNDEFINED" in v for v in ev.violations), ev.violations


# ------------------------------------------- E13: the list hook is live


def test_the_list_constraint_responds_to_a_transverse_offset():
    """E13. g['list'] was EXACTLY -2.000 across 800 evaluations because no mass
    item declares a transverse offset. It is KEPT as a tier-E/F hook, and this
    is the evidence that it is a hook and not a rubber stamp: it moves the
    moment an arrangement is asymmetric, which is the ordinary case (a galley
    to port), not an exotic one."""
    base = aggregate([MassItem(id="hull", mass_kg=5000.0, x_m=5.0, z_m=-0.1)])
    assert base.tcg_m == 0.0
    off = aggregate([MassItem(id="hull", mass_kg=5000.0, x_m=5.0, z_m=-0.1),
                     MassItem(id="galley", mass_kg=300.0, x_m=5.0, z_m=0.3,
                              y_m=-0.8, tier="E")])
    assert off.tcg_m == pytest.approx(-0.8 * 300.0 / 5300.0)

    gm_m = 0.6
    heel = math.degrees(math.atan(off.tcg_m / gm_m))
    assert abs(heel) > 0.1, "300 kg 0.8 m off centreline moved nothing"
    assert abs(heel) - LIST_LIMIT_DEG != pytest.approx(-LIST_LIMIT_DEG)


def test_the_list_constraint_is_no_longer_unconditionally_satisfiable():
    """E13's other half, and the reason the dimension is kept rather than
    deleted. MEASURED over 300 L1 evaluations of uniform L0-feasible hulls
    AFTER the E11 fix:

        trim:  UNDEFINED (GM_L <= 0)   1/300 =  0.3% | genuinely > 2 deg 21.0%
        list:  UNDEFINED (GM   <= 0)  76/300 = 25.3% | genuinely > 2 deg  0.0%

    So a quarter of L1-reachable hulls have no upright equilibrium at all, and
    every one of them used to report list 0.00 deg -> g = -2.000 FEASIBLE. The
    constraint that "could not vary" was masking the single most common
    pathology in the search space."""
    import navalai.evaluate as E
    m = MissionSpec()
    rng = np.random.default_rng(3)
    seen_inert = seen_undefined = 0
    n = 0
    while n < 60 and (seen_inert == 0 or seen_undefined == 0):
        x = rng.uniform(grammar.LOW, grammar.HIGH)
        if not grammar.check(x).ok:
            continue
        ev = evaluate(x, m)
        if ev.hydro is None:
            continue
        n += 1
        if ev.g["list"] == INFEASIBLE_G:
            seen_undefined += 1
        elif ev.g["list"] == pytest.approx(-LIST_LIMIT_DEG):
            seen_inert += 1
    assert seen_undefined > 0, (
        f"no hull in {n} had GM <= 0 — if that is now true the register's "
        f"25.3% has moved and this bar needs re-measuring, not deleting")
    assert seen_inert > 0, (
        "no hull reported the centreline value either; the constraint's "
        "documented resting state has changed")


# --------------------------------------------- E16: order without assert


def test_constraint_vector_raises_a_real_exception_not_an_assert():
    """E16. `assert tuple(g) == CONSTRAINT_NAMES` was the only binding between
    the dict and the optimizer's G columns, and -O strips it."""
    good = {k: 0.0 for k in CONSTRAINT_NAMES}
    assert tuple(constraint_vector(good)) == CONSTRAINT_NAMES

    # order of the literal is irrelevant now: the vector is built FROM the names
    shuffled = {k: float(i) for i, k in enumerate(reversed(CONSTRAINT_NAMES))}
    assert tuple(constraint_vector(shuffled)) == CONSTRAINT_NAMES

    with pytest.raises(ConstraintOrderError):
        constraint_vector({k: 0.0 for k in CONSTRAINT_NAMES[:-1]})
    with pytest.raises(ConstraintOrderError):
        constraint_vector({**good, "surprise": 0.0})


def test_the_order_guard_survives_python_dash_O():
    """E16, performed as the attack. Under -O `__debug__` is False and every
    `assert` in the package is gone; the guard must still fire. Run in a
    subprocess because -O is an interpreter flag, not a runtime setting."""
    prog = (
        "import sys;"
        "assert not __debug__, 'the -O flag did not take';"
        "from navalai.evaluate import constraint_vector, CONSTRAINT_NAMES,"
        " ConstraintOrderError;"
        "\ntry:\n"
        "    constraint_vector({k: 0.0 for k in CONSTRAINT_NAMES[:-1]})\n"
        "except ConstraintOrderError:\n"
        "    print('GUARD FIRED')\n"
        "else:\n"
        "    print('SILENT')\n"
    )
    out = subprocess.run([sys.executable, "-O", "-c", prog], cwd=_ROOT,
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr
    assert "GUARD FIRED" in out.stdout, out.stdout + out.stderr


def test_the_optimizer_reads_the_columns_the_ladder_writes():
    """The invariant the order exists to protect: optimize.py builds its G
    matrix as `[ev.g[k] for k in CONSTRAINT_NAMES]`, so the two must agree on
    both membership and length."""
    from navalai.optimize import HullProblem
    ev = evaluate(mid_params(), MissionSpec())
    assert tuple(ev.g) == CONSTRAINT_NAMES
    assert HullProblem(MissionSpec()).n_ieq_constr == len(CONSTRAINT_NAMES)
    # and the sentinel the optimizer fills rejected rows with is the ladder's
    # own, not a second copy of 1e3 (this codebase's recurring defect)
    import navalai.optimize as O
    src = Path(O.__file__).read_text()
    assert "1e3" not in src, "optimize.py re-declared the infeasible sentinel"


# ------------------------------------------------------------ B8: LCB


def test_lcb_is_constrained_and_the_kernel_now_delivers_it(ref):
    """B8, AND THE CLAIM IN THIS TEST'S OLD NAME IS NOW FALSE.

    IT WAS `test_lcb_is_constrained_and_the_reference_hull_fails_it`, and that
    was the honest record for as long as LCB was an EMERGENT OUTPUT: the
    hand-picked reference hull floated at -5.36 %LWL against a +-3% band and
    was INFEASIBLE (-4.19 until 2026-08-12, when the wet-station truncation in
    `lwl_eff` was corrected — the old figure was the bug and it had been
    flattering the hull; see `hydrostatics._waterline_ends`).

    PLATE P1 FIXED THE HULL, NOT THE BAR. `lcb` is now a GENE — a design
    TARGET the sectional area curve is solved to deliver — bounded by
    `grammar.PARAMS` to exactly `limits.LCB_BAND_PCT_LWL`, and the reference
    hull asks for -1.0 %LWL. RE-MEASURED 2026-08-13 it FLOATS at -1.68 %LWL
    and `g['lcb']` is -1.32, i.e. feasible. That is not a softened check; it is
    the same check on a hull that can now be aimed.

    So the assertion that this test exists for has to move to a hull that
    FAILS, or it stops proving the row can fire — see
    `test_the_lcb_row_still_refuses_a_hull_that_floats_out_of_band` below,
    which is fed the verbatim input. What is asserted HERE is the identity that
    was the gap's actual subject: the row exists, and it is computed from the
    FLOATED waterline rather than from the gene.

    The percentage is taken about the midpoint of the FLOATED waterline
    (`HydroState.lcb_pct_lwl`), not about half the LWL parameter — the transom
    lifts clear under rocker, so those are different stations. That is why the
    delivered -1.68 is not the requested -1.00: the gene is delivered at the
    DESIGN waterline and the row judges the one the boat actually floats at.
    """
    assert "lcb" in CONSTRAINT_NAMES
    hs = ref.hydro
    assert hs.lcb_pct_lwl == pytest.approx(-1.68, abs=0.05)
    assert ref.g["lcb"] == pytest.approx(abs(hs.lcb_pct_lwl) - LCB_BAND_PCT_LWL,
                                         abs=1e-9)
    assert ref.g["lcb"] < 0.0
    assert not any("LCB" in v for v in ref.violations), ref.violations
    # ...and it is NOT the gene read back to itself. The row would be
    # decorative if it judged the target instead of the flotation.
    assert grammar.named(ref.params)["lcb"] == pytest.approx(-1.0)
    assert abs(hs.lcb_pct_lwl - (-1.0)) > 0.5


def test_the_lcb_row_still_refuses_a_hull_that_floats_out_of_band():
    """THE ROW FED THE VERBATIM INPUT IT MUST REJECT.

    The reference hull stopped being that input when plate P1 made `lcb` a
    gene (above), and a constraint whose only witness has been fixed is a
    constraint nobody is checking any more. `grammar.PARAMS` bounds the GENE to
    +-`LCB_BAND_PCT_LWL`, so the refusal this row exists for is now the one the
    box cannot prevent: a hull that asks for an in-band LCB and FLOATS outside
    it. MEASURED over the L0-feasible box, that is 15% of hulls (see
    `test_the_lcb_band_bites_without_emptying_the_box`), and this finds the
    first one and asserts the row names it.
    """
    m = MissionSpec()
    rng = np.random.default_rng(3)
    found = None
    for _ in range(400):
        x = rng.uniform(grammar.LOW, grammar.HIGH)
        if not grammar.check(x).ok:
            continue
        ev = evaluate(x, m)
        if ev.hydro is None or ev.g["lcb"] <= 0.0:
            continue
        found = (x, ev)
        break
    assert found is not None, "no L0-clean hull floated out of the LCB band"
    x, ev = found
    # the gene was INSIDE the band — the box did its job and the row still had
    # something to say, which is the whole point of having both
    assert abs(grammar.named(x)["lcb"]) <= LCB_BAND_PCT_LWL
    assert abs(ev.hydro.lcb_pct_lwl) > LCB_BAND_PCT_LWL
    assert ev.g["lcb"] > 0.0 and not ev.ok
    assert any("LCB" in v for v in ev.violations), ev.violations


def test_the_lcb_band_bites_without_emptying_the_box():
    """A constraint nothing can violate is `keel.rocker` (0 hits in 400,000,
    deleted); a constraint nothing can satisfy is just as useless.

    THE QUESTION CHANGED WITH PLATE P1, AND THE OLD BAND ASKED THE OLD ONE.
    It read `0.20 < frac < 0.80` under the sentence "outside 20-80% it has
    stopped being a TRADE-OFF", and that was right while LCB was an emergent
    output of fifteen shape knobs: MEASURED then, 47.3% of L0-feasible hulls
    landed inside +-3%, with min -10.22, median +0.49 and max +17.53 %LWL, so
    the row really was a dimension the optimiser had to trade against.

    RE-MEASURED 2026-08-13: 85%. `lcb` is now a GENE that `grammar.PARAMS`
    bounds to exactly `LCB_BAND_PCT_LWL`, so the search cannot PROPOSE an
    out-of-band target any more — which is the governance pattern this project
    states explicitly (a box bounds what may be proposed, a row measures what
    actually FLOATED) and is a strict improvement, not a regression. The row is
    therefore no longer a trade-off and asking whether it still is would be
    asking a question plate P1 deliberately retired.

    What it must still be is LIVE: the gene is delivered at the DESIGN
    waterline and the row judges the FLOATED one, and 15% of the box is pushed
    out of band by flotation alone. That 15% is what
    `test_the_lcb_row_still_refuses_a_hull_that_floats_out_of_band` above is
    fed. The bar here is now the MEASUREMENT, pinned, so a drift toward either
    0% (dead row) or 100% (dead row) fails — which the 20-80% band would not
    have caught at 85% either, since it had already stopped describing the
    thing it was watching.
    """
    m = MissionSpec()
    rng = np.random.default_rng(3)
    inside = total = 0
    while total < 60:
        x = rng.uniform(grammar.LOW, grammar.HIGH)
        if not grammar.check(x).ok:
            continue
        ev = evaluate(x, m)
        if ev.hydro is None:
            continue
        total += 1
        inside += ev.g["lcb"] <= 0.0
    frac = inside / total
    assert frac == pytest.approx(0.85, abs=0.07), (
        f"LCB band passes {100 * frac:.0f}% of the L0-feasible box; measured "
        f"85% on 2026-08-13 (47.3% before `lcb` became a bounded gene). "
        f"Re-measure and record BEFORE/AFTER rather than widening this.")
    # and it is neither dead nor universal — the two ways a row stops being one
    assert 0.0 < frac < 1.0


# ------------------------------- B9: the floated hull, not the parameters


def test_l0_and_l1_judge_proportions_by_the_same_band():
    """B9's root cause was two copies of one band. `grammar.proportion_margins`
    is the shared kernel; L0 applies it to the parameter vector, evaluate() to
    HydroState."""
    # SCANNED ON EXECUTABLE LINES ONLY, from 2026-08-14. It used to scan raw
    # text, and then `grammar.py` acquired the incident block that RECORDS the
    # 12.0 x 0.8 m demihull refusal verbatim — `L/B: 15.00 outside [2.2, 8.5]`
    # — plus the line showing how the demihull union is formed from the same
    # interval. The test failed on its own explanation, which is a scanner bug
    # and not a finding; `tests/test_limits_single_source.py::_code_lines`
    # already carries the same fix for the same reason, in the same words.
    # The PROPERTY is unchanged and is still the one B9 needs: exactly one
    # DECLARATION of each band in code.
    src = "\n".join(
        ln for ln in (_ROOT / "navalai" / "grammar.py").read_text().splitlines()
        if not ln.strip().startswith("#"))
    assert src.count("2.2, 8.5") == 1 and src.count("1.8, 12.0") == 1, \
        "the proportion bands are declared more than once again"
    # ...and the MONOHULL band is what an ungoverned call is judged by, which is
    # what makes "declared once" the right property to test. The demihull band
    # is a SECOND ROW built from this one plus a sourced envelope, not a second
    # copy of it — `tests/test_vessel_bands.py` owns that distinction.
    assert grammar.PROPORTION_BANDS[limits.HullRole.MONOHULL]["L/B"][0] \
        is grammar.L_OVER_B_BAND
    assert grammar.proportion_margins(10.0, 3.0, 0.5)["L/B"] < 0.0
    # exactly at the edge is inside; one part in a thousand past it is not
    lo, hi = grammar.B_OVER_T_BAND
    assert grammar.proportion_margins(10.0, hi, 1.0)["B/T"] == pytest.approx(0.0)
    assert grammar.proportion_margins(10.0, hi * 1.001, 1.0)["B/T"] > 0.0
    assert grammar.proportion_margins(10.0, lo * 0.999, 1.0)["B/T"] > 0.0


def test_a_hull_that_floats_out_of_proportion_is_caught_even_though_l0_passed():
    """B9, the measured incident: L0 bounds BWL/T at 12 on the DESIGN draft and
    a delivered hull floated at B/T 14.4. The design draft is a parameter; the
    floated draft is whatever the weight model produces, so the gate was
    checking a number nobody sails."""
    m = MissionSpec()
    rng = np.random.default_rng(3)
    found = None
    for _ in range(4000):
        x = rng.uniform(grammar.LOW, grammar.HIGH)
        rep = grammar.check(x)
        if not rep.ok:
            continue
        ev = evaluate(x, m)
        if ev.hydro is None:
            continue
        bt = ev.hydro.b_wl_max / ev.hydro.draft
        if bt > grammar.B_OVER_T_BAND[1]:
            found = (x, ev, bt)
            break
    assert found is not None, "no L0-clean hull floated out of band to check"
    x, ev, bt = found
    p = grammar.named(x)
    assert grammar.check(x).ok, "L0 passed it"
    assert p["BWL"] / p["T"] <= grammar.B_OVER_T_BAND[1], \
        "the parameter vector was already out of band — not the B9 case"
    assert ev.g["proportions"] > 0.0 and not ev.ok
    assert any("this is the hull that floated" in v for v in ev.violations), \
        ev.violations


# ------------------------------------------------ E4: no dead constraints


def test_every_relational_l0_constraint_can_actually_fire():
    """E4. Four checks — `keel.rocker`, `keel.forefoot`, `x_mb.margin` and
    `flare.fold` — scored 0 hits in 400,000 uniform in-bounds vectors, because
    each is arithmetically unreachable inside the declared bounds. They padded
    a constraint count and nothing else, and `ALIGNMENT.md`'s "30+ constraints"
    was measured at 9 live ones. Deleted; this stops any of them coming back
    and stops a new one being added dead.

    MEASURED over the same 400,000 samples, the nine that survived then:

        freeboard.rel  33.039%   chine.height       12.557%
        L/B            32.419%   panel.twist         6.819%
        freeboard.abs  23.097%   transom.chine       5.497%
        deadrise.order 22.204%   chine.below.sheer   3.059%
        B/T            18.618%

    RE-MEASURED 2026-08-13 over 20,000 uniform in-bounds vectors on the
    plate-P1/P2 genome. **The live relational count is 8, not 9, and the drop
    is a DELETION with gap E4's evidence, not a check that rotted:**
    `chine.height` (the midship chine may sit 0.25 T ABOVE the waterline) was
    REPLACED by the tighter `chine.submerged` (the chine is at or below the
    design waterline at EVERY station, measured on the delivered geometry), and
    `transom.chine` was deleted because `chine.submerged` subsumes it and it
    then fired on ZERO of 40,000 in-bounds vectors. Both are recorded in
    `navalai/grammar.py` at the point of deletion.

        section.solve  35.455%   panel.twist         9.520%
        freeboard.rel  33.395%   sac.target          5.580%
        L/B            32.025%   chine.below.sheer   3.160%
        freeboard.abs  23.325%   chine.submerged     1.230%
        deadrise.order 22.170%
        B/T            18.170%

    `section.solve` and `sac.target` are NOT `_rel` rows and are deliberately
    not counted below: they are the two REFUSALS plate P1 added — a design
    TARGET the shape family cannot reach, and a station whose area the draft
    and deadrise cannot enclose — and they are reported by name from a
    `GeometryError` rather than from a boolean relation. They are listed here
    because a reader counting rows in the output would otherwise find ten.

    20,000 samples here rather than 400,000 for runtime; the rarest live check
    fires 1.23% of the time, so ~250 hits are expected and 0 is decisive."""
    n = 20_000
    rng = np.random.default_rng(0)
    X = rng.uniform(grammar.LOW, grammar.HIGH, size=(n, grammar.N_PARAMS))
    hits: dict[str, int] = {}
    for x in X:
        for v in grammar.check(x).violations:
            name = v.split(":")[0]
            if not name.startswith("bound["):
                hits[name] = hits.get(name, 0) + 1

    src = (_ROOT / "navalai" / "grammar.py").read_text()
    body = src[src.index("def check("):src.index("def sample(")]
    declared = {ln.split('_rel("')[1].split('"')[0]
                for ln in body.splitlines() if '_rel("' in ln
                and 'bound[' not in ln}
    dead = sorted(declared - set(hits))
    assert not dead, (
        f"{dead} never fired in {n} in-bounds samples — a constraint that "
        f"cannot be violated is a count, not a gate. Delete it or widen it.")
    assert len(declared) == 8, (
        f"the live relational count moved to {len(declared)}; ALIGNMENT.md "
        f"quotes 8 and that figure is measured, not aspirational")
    # The two named refusals plate P1 added are live too, and they are counted
    # HERE rather than folded into the number above, because they are not
    # relations: an unreachable design target is refused, never approximated.
    assert {"sac.target", "section.solve"} <= set(hits), sorted(hits)
    for name in ("keel.rocker", "keel.forefoot", "x_mb.margin", "flare.fold",
                 # deleted by plate P1/P2 with the same rule and the same
                 # evidence; `chine.submerged` subsumes both
                 "chine.height", "transom.chine"):
        assert name not in declared, f"{name} came back"
        # named in the comment that records WHY it went, and nowhere else
        assert f'_rel("{name}"' not in src, f"{name} came back"


def test_no_ast_node_validator_is_dead_and_the_layer_says_what_it_does_not_do():
    """Gap E18: `Profile.validate` and `Topside.validate` read `return []`.

    A guard that cannot fire is defect class 3, and this pair was worse than an
    absent guard because `hull_ast.type_check` called it in a loop and got a
    clean answer back — the layer LOOKED like it was validating two of the five
    nodes. It is the same finding as `test_every_relational_l0_constraint_can_
    actually_fire` above, aimed at the AST layer instead of at `grammar.check`,
    and it is settled the same way E4's four tautological constraints were:
    measure, then delete rather than invent a threshold to fill the slot.

    MEASURED 2026-08-12 over 4000 `grammar.sample` vectors (all 4000 pass
    `grammar.check`): the node layer returned ZERO violations in total — not
    just from these two, from ALL FIVE nodes. `Planform`'s `x_mb < 0.3` cannot
    fire while `grammar.PARAMS` bounds x_mb at [0.40, 0.68], and
    `SectionLaw`'s rule is `grammar.check`'s `deadrise.order` a second time.
    The two surviving rules are kept because each rejects a verbatim input
    below; the two empty ones are gone, and `type_check` now distinguishes "no
    node-local rule" (no method) from "rules, all passing" (a method returning
    []), which are opposite claims that used to look identical.
    """
    import ast as _ast
    from navalai import hull_ast as HA

    # 1. NO VALIDATOR IS UNCONDITIONALLY EMPTY. Aimed at the verbatim body that
    #    stood in Profile and Topside, so it fires on the defect.
    src = (_ROOT / "navalai" / "hull_ast.py").read_text()
    dead = []
    for node in _ast.walk(_ast.parse(src)):
        if not (isinstance(node, _ast.FunctionDef) and node.name == "validate"):
            continue
        body = [b for b in node.body
                if not (isinstance(b, _ast.Expr)
                        and isinstance(b.value, _ast.Constant)
                        and isinstance(b.value.value, str))]
        if (len(body) == 1 and isinstance(body[0], _ast.Return)
                and isinstance(body[0].value, _ast.List)
                and not body[0].value.elts):
            dead.append(node.lineno)
    assert not dead, (
        f"a validator at line(s) {dead} returns [] unconditionally — say the "
        f"node has no node-local rule by NOT defining validate()")

    # 2. THE NODES WITH NO RULE REALLY HAVE NONE, and type_check still runs.
    assert not hasattr(HA.Profile(0.2, 0.5), "validate")
    assert not hasattr(HA.Topside(8.0, 0.2), "validate")
    d = HA.HullDesign.from_vector(mid_params(), HA.Typology.SHARP_CHINE)
    HA.type_check(d)                       # must not raise on the missing method

    # 3. EVERY SURVIVING VALIDATOR IS MADE TO FIRE, on the verbatim input it
    #    exists to reject. Without this the deletion could have been bought by
    #    deleting the ones that worked.
    assert HA.Principal(LWL=0.0, BWL=3.2, T=0.55, D=1.2).validate()
    assert HA.Planform(x_mb=0.25,
                       r_transom=0.5).validate()
    assert HA.SectionLaw(beta_mid=18.0, beta_bow=6.0, beta_len=0.3,
                          roundness=0.0).validate()
    # ...and each accepts the good case, so it is a test and not a constant.
    assert not HA.Principal(LWL=10.0, BWL=3.2, T=0.55, D=1.2).validate()
    assert not HA.Planform(0.55, 0.5).validate()
    assert not HA.SectionLaw(18.0, 24.0, 0.3, 0.0).validate()

    # 4. THE MEASUREMENT ITSELF, re-derived rather than quoted: the node layer
    #    moves no verdict on in-bounds hulls. If it ever does, this assertion
    #    fails and the docstring above is the thing that was wrong.
    rng = np.random.default_rng(0)
    X = grammar.sample(4000, rng)
    fired = 0
    for x in X:
        dd = HA.HullDesign.from_vector(x, HA.Typology.SHARP_CHINE)
        for nd in (dd.principal, dd.planform, dd.sections, dd.profile,
                   dd.topside):
            rule = getattr(nd, "validate", None)
            if rule is not None and rule():
                fired += 1
    assert fired == 0, (
        f"the node layer fired {fired} times on 4000 in-bounds vectors — it "
        f"now carries information, so re-state the measurement above")


def _all_results(prov) -> list[tuple[str, float, float]]:
    """(quantity, value, uncertainty) for every row in the provenance DB."""
    return [(str(q), v, u) for q, v, u in prov.con.execute(
        "SELECT quantity, value, uncertainty FROM result")]
