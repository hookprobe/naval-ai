"""Gate R4: the ladder is REACHABLE from the product — tiers L2, L3 and R are
wired into `evaluate()`/`revalidate()`, and L3 reads evidence instead of
inventing it.

THE MEASURED INCIDENT (docs/GAP-REGISTER.md rows A1 and A2, audited
2026-08-05). An AST import graph of the live checkout found that `evaluate`,
`optimize`, `agents` and `ui/server` reached `seakeeping: no`, `cfd: no`,
`surrogate: no`, `rules: no`. Concretely:

  * `Evaluation.tier` read "L1" in 100% of ~2000 evaluations — there was no
    code path by which a design could reach L2 or L3 at all (A1, CRITICAL);
  * NOTHING in `navalai/` imported `navalai.rules`. Not `evaluate()`, not
    `CONSTRAINT_NAMES`, not NSGA-II, not the agent shell. **A hull failing
    ISO 12215-5 came back `ok=True` and exported.** The rules tier that PLM.md
    section 1 calls a platform truth mechanism which "fails closed" was a
    print statement in a demo (A2, CRITICAL).

`tests/test_ladder.py` (Gate R3) covers the L2 escalation mechanics. This file
covers the two things that gap register rows A1/A2 actually assert, and that a
mechanics test cannot see:

  1. REACHABILITY, measured the same way the audit measured it — by walking
     the package's own import graph — so the defect cannot come back as "the
     module exists, the tests exercise it, and no product code path reaches
     it", which is exactly the shape it had.
  2. That each wired tier CHANGES A VERDICT on realistic input. A constraint
     that is present but never fires is the same nothing in a different place:
     the hull in `hull_that_only_the_rules_tier_rejects()` passes every L1
     constraint and is refused solely by ISO 12217-1's downflooding clause.

L3 is the tier that must be read and never run, so most of the file below is
about what `l3_case_evidence` REFUSES.
"""

import ast
import pathlib

import numpy as np
import pytest

from navalai import db, grammar
from navalai.evaluate import (CONSTRAINT_NAMES, TierRefusal,
                              TierRequiresOperator, evaluate,
                              l3_case_evidence, read_case_info, revalidate,
                              tier_rank)
from navalai.mission import MissionSpec
from navalai.rules import DISCLAIMER
from tests.test_phase0 import mid_params

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PKG = _ROOT / "navalai"


# ------------------------------------------------------------ import graph --

def _module_name(path: pathlib.Path) -> str:
    rel = path.relative_to(_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imports_of(path: pathlib.Path) -> set[str]:
    """Every `navalai.*` module this file imports, relative imports resolved.

    Function-level imports count. They have to: `evaluate.revalidate` imports
    `seakeeping` and `navalai.cfd.post` inside the branch that needs them, so a
    top-of-file-only scan would report the very "no" this test exists to deny.
    """
    tree = ast.parse(path.read_text())
    pkg = _module_name(path).rsplit(".", 1)[0] if path.name != "__init__.py" \
        else _module_name(path)
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("navalai"):
                    out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg.split(".")
                base = base[:len(base) - (node.level - 1)] or ["navalai"]
                root = ".".join(base + ([node.module] if node.module else []))
            elif node.module and node.module.startswith("navalai"):
                root = node.module
            else:
                continue
            out.add(root)
            for a in node.names:
                out.add(f"{root}.{a.name}")
    return out


def _reachable_from(start: str) -> set[str]:
    graph = {_module_name(p): _imports_of(p) for p in sorted(_PKG.rglob("*.py"))}
    seen: set[str] = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        for dep in graph.get(cur, set()):
            if dep in seen:
                continue
            seen.add(dep)
            stack.append(dep)
    return seen


@pytest.mark.parametrize("tier_module, tier", [
    ("navalai.seakeeping", "L2"),
    ("navalai.cfd", "L3"),
    ("navalai.rules", "R"),
])
def test_every_claimed_tier_is_reachable_from_evaluate(tier_module, tier):
    """The audit's own measurement, kept executable.

    The register recorded `seakeeping: no`, `cfd: no`, `rules: no` from
    `navalai.evaluate`. Anything that makes one of those a "no" again — a
    refactor that moves a tier behind a script, a lazy import deleted with the
    branch that used it — fails here rather than in an audit a year later.
    """
    reach = _reachable_from("navalai.evaluate")
    assert any(m == tier_module or m.startswith(tier_module + ".")
               for m in reach), (
        f"tier {tier} ({tier_module}) is not reachable from navalai.evaluate — "
        f"that is gap A1/A2 verbatim: the tier exists, the tests exercise it, "
        f"and no product code path can get to it")


def test_the_ladder_never_starts_a_solver_from_inside_the_product():
    """L3 READS a campaign; it must never launch one.

    An in-process RANS call cannot be honest here: the KCS case is ~6 h on 10
    ranks on the simulation node and does not survive a thermal sleep, so
    anything short enough to return from `evaluate()` is not the number it
    claims to be. The guard is structural — no process-spawning name may appear
    in the ladder orchestrator at all — because "we only call it when the user
    asks" is how it would come back.
    """
    tree = ast.parse((_PKG / "evaluate.py").read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add(a.name.split(".")[0])
            if isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
    forbidden = {"subprocess", "popen", "Popen", "system", "spawn",
                 "check_call", "check_output", "fork", "execv"}
    assert not (names & forbidden), (
        f"evaluate.py references {sorted(names & forbidden)} — the ladder "
        f"orchestrator must not be able to start a solver process")


# --------------------------------------------------------- tier R (gap A2) --

def hull_that_only_the_rules_tier_rejects() -> np.ndarray:
    """A 15.57 m hull whose ONLY failing constraint is an ISO 12217 clause.

    MEASURED 2026-08-13: floated freeboard 0.8827 m. `limits.FREEBOARD_FLOOR_M`
    is 0.25 m, so the L1 freeboard constraint reads -0.633 (comfortably
    feasible), while ISO 12217-1's downflooding height for design category A on
    a hull this long is 1.038 m, so R-DFH fails by 155 mm. Every other
    constraint is negative.

    That is the point: before tier R was wired, this boat was `ok=True` with no
    violations and exported. The same hull under category C — where Table A.1
    clamps the requirement to 0.750 m — is `ok=True`, which is the negative
    control that keeps this test about the RULES tier and not about a hull that
    is simply bad.

    THE VECTOR CHANGED ON 2026-08-13 AND THE OLD ONE STOPPED BEING A WITNESS.
    It was a 13.45 m hull (freeboard 0.597 m, R-DFH short by 53 mm on a 0.65 m
    floor). Under the plate-P1/P2 kernel that same vector floats differently
    and now ALSO fails `gm` (+0.221) and `bend_radius` (+0.914), so it no
    longer demonstrates a refusal that is tier R's alone — the assertion below
    is `all(g[k] <= 0 for k != "rules")` and it is the whole test. This vector
    was found by searching the L0-feasible box for the property the test needs
    (rules > 0, every other row <= 0 under category A, and `ok` under C and D),
    not by relaxing anything: 8,359 draws of `rng(11)` produced four, and this
    is the one with the widest margin, so the witness is not a near-miss that
    the next re-measurement flips. NO BAR MOVED — R-DFH, the GM floors and the
    bend-radius limit are all where they were.
    """
    return grammar.vector({
        "LWL": 15.5719, "BWL": 2.9137, "T": 0.4960, "D": 1.2838,
        "Cp": 0.5930, "lcb": -2.5474, "x_mb": 0.4561, "r_transom": 0.0901,
        "beta_mid": 14.4169, "beta_bow": 25.8859, "beta_len": 0.2059,
        "roundness": 0.3008, "rocker": 0.1490, "forefoot": 0.4675,
        "flare": 14.0069, "sheer_rise": 0.4793,
    })


def test_the_rules_tier_alone_can_refuse_a_design():
    x = hull_that_only_the_rules_tier_rejects()
    assert grammar.check(x).ok, "the L0 gate must not be doing this work"

    ev_a = evaluate(x, MissionSpec(design_category="A"))
    assert not ev_a.ok
    assert ev_a.g["rules"] > 0.0
    # every OTHER constraint is satisfied — the refusal is tier R's alone
    assert all(ev_a.g[k] <= 0.0 for k in CONSTRAINT_NAMES if k != "rules"), \
        {k: round(v, 3) for k, v in ev_a.g.items()}
    assert len(ev_a.violations) == 1 and "R-DFH" in ev_a.violations[0], \
        ev_a.violations
    # 0.597 m until 2026-08-13 on the 13.45 m vector this fixture used to hold
    assert ev_a.hydro.freeboard_min == pytest.approx(0.8827, abs=0.01)

    # ...and category B, which shares A's requirement, fails identically — so
    # the refusal tracks the CLAUSE and not one enum value.
    ev_b = evaluate(x, MissionSpec(design_category="B"))
    assert not ev_b.ok and ev_b.g["rules"] == pytest.approx(ev_a.g["rules"])

    # NEGATIVE CONTROL: same hull, category C. ISO 12217-1:2015 Annex A makes
    # the required downflooding height hD(R) = (LH/15) x F1..F5 CLAMPED to
    # Table A.1, so it scales with length and then stops. This hull is 15.57 m,
    # giving 1.038 m for A and B and 0.750 m (the Table A.1 ceiling) for C —
    # against 0.8827 m of freeboard, so C passes and A fails on the same boat.
    # The old fixed floors (0.65/0.50/0.35 m) were length-blind and would have
    # passed all three. D clamps lower still and also passes.
    for cat in ("C", "D"):
        ev_ok = evaluate(x, MissionSpec(design_category=cat))
        assert ev_ok.ok and ev_ok.violations == () and ev_ok.g["rules"] < 0.0, \
            (cat, ev_ok.violations)


def test_the_rules_constraint_is_a_margin_the_optimizer_can_descend():
    """A boolean would give NSGA-II nothing to follow out of an infeasible
    region, and `Evaluation.g` is the ONE inequality vector the optimizer
    consumes — so 'rules' has to be a continuous relative shortfall, finite in
    both directions."""
    assert "rules" in CONSTRAINT_NAMES
    fail = evaluate(hull_that_only_the_rules_tier_rejects(),
                    MissionSpec(design_category="A"))
    ok = evaluate(np.array(mid_params()), MissionSpec())
    for ev in (fail, ok):
        assert "rules" in ev.g and np.isfinite(ev.g["rules"])
    # the shortfall is 1.038 - 0.8827 = 155 mm on a 1.038 m requirement, i.e.
    # ~15% (0.334 until 2026-08-13, on the 13.45 m vector this fixture used to
    # hold — see `hull_that_only_the_rules_tier_rejects` for why it moved)
    assert fail.g["rules"] == pytest.approx(0.1498, abs=0.01)
    assert ok.g["rules"] < 0.0


def test_the_rules_payload_says_assessment_aid_and_never_certification():
    """Honesty rule 5. The tier is now in the product's constraint vector, so
    the disclaimer travels with the verdict rather than sitting in a module
    docstring nobody serves."""
    ev = evaluate(np.array(mid_params()), MissionSpec())
    assert ev.rules["disclaimer"] == DISCLAIMER
    assert "NOT CERTIFICATION" in ev.rules["disclaimer"].upper()
    assert ev.rules["total"] >= 4 and ev.rules["findings"]
    for f in ev.rules["findings"]:
        assert f["basis"] in ("standard", "approx")
        assert f["clause"], "a finding with no clause is not a rule check"


# -------------------------------------------------------- tier L3 (gap A1) --

_SPEED = MissionSpec().cruise_speed_ms()          # 2.572 m/s at the 5 kn default


def write_recorded_case(tmp_path, params, *, speed=_SPEED, symmetric=False,
                        t_end=30.0, drag=900.0, domain_length=None,
                        omit=(), lwl=None) -> pathlib.Path:
    """A campaign directory as `make_case.py` + a completed run leave it.

    Written by hand rather than by calling the case generator because this test
    is about what the LADDER does with a recorded result, and the generator's
    own correctness is Gate 2M's business. The STL is real, though — it comes
    from `navalai.cfd.case.hull_to_stl`, so the geometry identity check is
    exercised against the file format it will actually meet.
    """
    from navalai.cfd.case import hull_to_stl
    from navalai.geometry import Hull

    case = pathlib.Path(tmp_path)
    (case / "constant" / "triSurface").mkdir(parents=True, exist_ok=True)
    sha = hull_to_stl(Hull(np.asarray(params, float)),
                      case / "constant" / "triSurface" / "hull.stl",
                      nx=120, nz=24)
    hull_lwl = float(np.asarray(params, float)[0] if lwl is None else lwl)
    dom = 4.5 * hull_lwl if domain_length is None else domain_length

    info = {
        "speed_ms": f"{speed}", "lwl": f"{hull_lwl}", "scale": "1.0",
        "stl_sha256": sha, "benchmark": "unknown", "free_motion": "False",
        "symmetric": str(bool(symmetric)),
        "domain_length_m": f"{dom:.4f}",
        "flow_through_s": f"{dom / speed:.4f}",
        "cells_bg": "16245",
    }
    lines = [f"{k}={v}" for k, v in info.items() if k not in omit]
    lines.append("NOTE: written by tests/test_ladder_wiring.py")
    lines.append("run: navalai/cfd/run-case.sh <this-dir> <np>")
    (case / "case.info").write_text("\n".join(lines) + "\n")

    # A settled force history: 60 samples, a small oscillation about `drag`,
    # in the exact column layout post.parse_forces reads (total | pressure |
    # viscous, x y z each).
    fdir = case / "postProcessing" / "forces" / "0"
    fdir.mkdir(parents=True, exist_ok=True)
    rows = ["# Time  (total_x total_y total_z)  (pressure_x ...)  (viscous_x ...)"]
    n = 60
    for i in range(n):
        t = t_end * (i + 1) / n
        # A startup transient with a 5 s time constant — in ABSOLUTE time, so a
        # long run has shed it by the tail and a short one has not. (It was
        # written as exp(-4t/t_end) first, which is the same curve at every
        # run length and therefore could not tell a settled run from a
        # drifting one at all: the drift test below passed 1.00x.)
        fx = drag * (1.0 + 0.6 * np.exp(-t / 5.0) + 0.01 * np.sin(9.0 * t))
        half = 0.5 * fx if symmetric else fx
        rows.append(f"{t:.5f}\t(({half:.6e} 0 0) ({0.7 * half:.6e} 0 0) "
                    f"({0.3 * half:.6e} 0 0))")
    (fdir / "force.dat").write_text("\n".join(rows) + "\n")
    return case


def test_l3_refuses_when_there_is_no_recorded_evidence(tmp_path):
    """"No evidence at this tier" is a RESULT, and it is the only honest one on
    a machine holding no RANS run for this hull. The failure mode it forecloses
    is handing back the L1 Michell number wearing an L3 badge."""
    m = MissionSpec()
    ev = evaluate(np.array(mid_params()), m)
    with pytest.raises(TierRequiresOperator) as e:
        revalidate(ev, m, "L3")
    msg = str(e.value)
    assert "NO EVIDENCE AT THIS TIER" in msg
    assert "scripts/make_case.py" in msg          # the route, not just a "no"
    assert ev.tier == "L1", "a refused escalation must not mutate the input"

    # an EMPTY provenance DB is still no evidence, not a blank pass
    prov = db.Provenance(tmp_path / "p.sqlite3")
    with pytest.raises(TierRequiresOperator):
        revalidate(ev, m, "L3", provenance=prov)


def test_l3_reads_a_recorded_case_and_badges_it_measured(tmp_path):
    """The Gate R4 bar: a kept design reaches L3 from a directory that has
    already been run, the badge carries a MEASURED sigma, the L1 verdict
    survives, and provenance records it."""
    m = MissionSpec()
    x = np.array(mid_params())
    prov = db.Provenance(tmp_path / "p.sqlite3")
    ev1 = evaluate(x, m, provenance=prov)
    case = write_recorded_case(tmp_path / "run", x, drag=900.0)

    ev3 = revalidate(ev1, m, "L3", provenance=prov, case_dir=case)
    assert ev3.tier == "L3" and tier_rank(ev3.tier) > tier_rank(ev1.tier)
    # the L1 findings survive the promotion; the badge is superseded, not the
    # evaluation (same invariant Gate R3 asserts for L2)
    assert ev3.ok == ev1.ok and ev3.gm_m == ev1.gm_m
    assert ev3.badges["resistance"][0] == "L1", "the Michell number is still L1"
    assert ev3.badges["resistance_cfd"][0] == "L3"
    assert ev3.badges["resistance_cfd"][1] > 0.0, "a declared-zero sigma is not"\
        " a measurement"
    assert ev3.cfd["drag_n"] == pytest.approx(900.0, rel=0.03)
    assert ev3.cfd["flow_throughs"] >= 1.0
    assert ev3.cfd["ct"] > 0.0
    # the escalation states the disagreement rather than hiding it
    assert ev3.cfd["l1_rt_n"] == pytest.approx(ev1.resistance.total)
    assert ev3.cfd["l3_over_l1"] > 0.0

    rows = prov.results(db.hull_id(x), "L3")
    assert rows, "an escalation that leaves no history did not happen"
    for _t, solver, _q, value, unc, _meta in rows:
        assert solver == "openfoam-interfoam"
        assert value is not None and unc is not None and unc >= 0.0
    # The solver VERSION is 'unrecorded' rather than an invented "v2606":
    # case.info does not write the OpenFOAM build today, and a version string
    # made up at read time is provenance that looks checkable and is not.
    ver = prov.con.execute(
        "SELECT solver_version FROM result WHERE tier='L3'").fetchone()[0]
    assert ver == "unrecorded"

    # and it can be re-read from provenance alone, with no directory in hand
    ev3b = revalidate(ev1, m, "L3", provenance=prov)
    assert ev3b.tier == "L3"
    assert ev3b.cfd["drag_n"] == pytest.approx(ev3.cfd["drag_n"])


def test_a_symmetric_case_has_its_force_doubled(tmp_path):
    """Half the hull is meshed, so the patch integral is half the force.

    CLAUDE.md records `forceCoeffs wrong by exactly 2x on every symmetric run`
    as a defect that shipped. Same trap, other side of the pipe: this asserts
    the SAME physical drag comes back from a full-domain run and from a
    symmetric one whose patch reports half of it.
    """
    m = MissionSpec()
    x = np.array(mid_params())
    from navalai.geometry import Hull
    full = l3_case_evidence(write_recorded_case(tmp_path / "full", x,
                                                symmetric=False),
                            Hull(x), m)
    half = l3_case_evidence(write_recorded_case(tmp_path / "half", x,
                                                symmetric=True),
                            Hull(x), m)
    assert half["symmetric"] and not full["symmetric"]
    # 1e-6, not 1e-9: the force file itself is written to six significant
    # figures, so halving and re-doubling loses the ninth digit in the FIXTURE,
    # not in the doubling.
    assert half["drag_n"] == pytest.approx(full["drag_n"], rel=1e-6)
    assert half["sigma_n"] == pytest.approx(full["sigma_n"], rel=1e-6)


def test_l3_refuses_a_campaign_run_on_a_different_hull(tmp_path):
    """gate2m.py's own incident, forestalled one layer up: it applied the KRISO
    KCS tank data to ANY directory and printed `C_T 5.9010e-03, E%D -59.0` for
    a Wigley hull under a header naming KCS's speed and Lpp. A recorded drag is
    evidence about the geometry that produced it and about nothing else."""
    m = MissionSpec()
    x = np.array(mid_params())
    other = np.array(mid_params())
    other[0] = 12.5                                   # a 12.5 m boat, not 10 m
    from navalai.geometry import Hull
    case = write_recorded_case(tmp_path / "other", other)
    with pytest.raises(TierRefusal) as e:
        l3_case_evidence(case, Hull(x), m)
    assert "12.500" in str(e.value) and "10.000" in str(e.value)


def test_l3_refuses_a_same_length_hull_of_a_different_shape(tmp_path):
    """Length agreement is not identity. The submerged volume of the case's own
    STL is compared against the genome's displacement, which is what separates
    two 10 m boats. MEASURED slack: `hull_to_stl` at nx=120 reproduces the
    analytic displacement to within 0.5%, so a 3% bar is triangulation noise
    and not a doorway."""
    m = MissionSpec()
    x = np.array(mid_params())
    deeper = np.array(mid_params())
    deeper[2] = 0.75                                  # 0.55 m draft -> 0.75 m
    from navalai.geometry import Hull
    case = write_recorded_case(tmp_path / "deep", deeper, lwl=float(x[0]))
    with pytest.raises(TierRefusal) as e:
        l3_case_evidence(case, Hull(x), m)
    assert "below the waterline" in str(e.value)


def test_l3_refuses_a_run_towed_at_a_different_speed(tmp_path):
    """Resistance is a function of speed; a drag recorded at another one is a
    different design point, not a better answer at this one."""
    m = MissionSpec()
    x = np.array(mid_params())
    from navalai.geometry import Hull
    case = write_recorded_case(tmp_path / "fast", x, speed=_SPEED * 1.3)
    with pytest.raises(TierRefusal) as e:
        l3_case_evidence(case, Hull(x), m)
    assert "different design point" in str(e.value)


def test_l3_refuses_a_run_shorter_than_one_flow_through(tmp_path):
    """MEASURED 2026-08-06: the re-audit found EVERY run in this repository
    sitting between 0.13 and 0.70 of ONE flow-through, with conclusions drawn
    from all of them — `runs/beach` returned `settled: yes` on a 3.3% drift at
    0.70. A domain the free stream has not crossed still contains its initial
    condition, so no average over it is stationary."""
    m = MissionSpec()
    x = np.array(mid_params())
    from navalai.geometry import Hull
    # 45 m domain at 2.572 m/s is a 17.5 s flow-through; 10 s is 0.57 of one.
    case = write_recorded_case(tmp_path / "short", x, t_end=10.0)
    with pytest.raises(TierRefusal) as e:
        l3_case_evidence(case, Hull(x), m)
    assert "flow-through" in str(e.value) and "startup" in str(e.value)


def test_l3_refuses_a_case_that_cannot_say_how_long_its_domain_is(tmp_path):
    """The `${VAR:-0}` rule. Without `domain_length_m` the flow-through count
    is UNKNOWABLE, and gate2m.py substitutes 4.5*Lwl for it — a stationarity
    claim resting on an assumed domain. Refused here instead.

    This guard fires on REAL data, not only on a fixture: every case directory
    in this repository predates the 2026-08-06 receipt and is refused by it.
    """
    m = MissionSpec()
    x = np.array(mid_params())
    from navalai.geometry import Hull
    case = write_recorded_case(tmp_path / "nodom", x, omit=("domain_length_m",))
    with pytest.raises(TierRefusal) as e:
        l3_case_evidence(case, Hull(x), m)
    assert "domain_length_m" in str(e.value)

    real = _ROOT / "runs" / "wigley"
    if (real / "case.info").exists():
        assert "domain_length_m" not in read_case_info(real), (
            "runs/wigley gained a domain_length_m — re-point this assertion at "
            "a case that still lacks one, or drop it, but do not delete the "
            "fixture half above")


def test_l3_refuses_a_directory_with_no_forces_and_no_case_info(tmp_path):
    """A campaign that did not run, or did not survive, has no number to read —
    and an empty directory must never read as a zero drag."""
    m = MissionSpec()
    x = np.array(mid_params())
    from navalai.geometry import Hull
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(TierRefusal):
        l3_case_evidence(empty, Hull(x), m)

    case = write_recorded_case(tmp_path / "nof", x)
    for p in (case / "postProcessing" / "forces" / "0").glob("*.dat"):
        p.unlink()
    with pytest.raises(TierRefusal) as e:
        l3_case_evidence(case, Hull(x), m)
    assert "force history" in str(e.value)


def test_l3_sigma_widens_when_the_run_is_still_drifting(tmp_path):
    """The sigma is measured, not declared: the scatter over the settled tail,
    or the drift between that tail and the window before it, whichever is
    larger. A run whose transient has not died reports a WIDE L3 band rather
    than a confident wrong one — the honest alternative to inventing a
    settledness threshold this module does not own (gate2m.py does)."""
    m = MissionSpec()
    x = np.array(mid_params())
    from navalai.geometry import Hull
    settled = l3_case_evidence(write_recorded_case(tmp_path / "s", x,
                                                   t_end=60.0), Hull(x), m)
    drifting = l3_case_evidence(write_recorded_case(tmp_path / "d", x,
                                                    t_end=18.0), Hull(x), m)
    # same hull, same nominal drag; the shorter run is still shedding its
    # transient, so its band has to be the wider one
    assert drifting["sigma_n"] > 3.0 * settled["sigma_n"]
    assert settled["sigma_n"] > 0.0
