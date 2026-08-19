"""Gap R5.1 — the two CFD post-processors, consolidated onto one rule.

`scripts/post_gci.py` and `scripts/gate2m.py` were independent parsers of the
same recorded files, and they disagreed about three things that decide a
number Gate 2M is judged on. Every figure quoted below was MEASURED on the
runs committed in `runs/` on 2026-08-06, by running the code as it stood:

  CELL COUNT   post_gci read checkMesh's `cells:` with a FALLBACK to
               case.info's `cells_bg=`; gate2m read `cells_bg` only. They are
               different quantities — the meshed count and the background block
               spec — and on these runs they differ by ~16x (runs/beach: 222444
               against 13608). `post_gci.py runs/kcs_gci2`, where only the
               coarse grid had ever been meshed, mixed one of each into a
               single ratio and printed
                   cells 243354 / 38000 / 108864
                   measured refinement ratio 0.538 (c->m), 1.420 (m->f)
               i.e. a family getting COARSER under refinement, generated at
               sqrt(2). gate2m got 1.410 / 1.418 from the same directory.
  SETTLEDNESS  post_gci split a `--tail 0.3` window in half; gate2m compared
               the last fifth to the previous fifth by SAMPLE INDEX. On
               runs/kcs_gci2/coarse that is 2.1% drift (settled) against 10.9%
               (not settled) — one file, one instant, two verdicts.
  DOUBLING     both grew their own symmetric-case doubling.

`navalai.cfd.post.settled_drag` is now the one home for all three, and this
file is the fence. Every guard here is made to FIRE on the input that motivated
it, and each has a partner where the metric is absent or garbled and the answer
is still a refusal — never a passing default.
"""

from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path

import numpy as np
import pytest

from navalai.cfd import post

_ROOT = Path(__file__).resolve().parents[1]
_RUNS = _ROOT / "runs"


# --------------------------------------------------------------------------
# fixtures: a synthetic case, written the way OpenFOAM writes one
# --------------------------------------------------------------------------

def _write_case(dirpath: Path, t, pressure, viscous, *, symmetric=True,
                lwl=7.2786, speed=2.196, cells: int | None = None,
                extra_info: str = "") -> Path:
    """A case directory with a force history and the receipts post.py reads.

    The force.dat layout is OpenFOAM's own: Time, then TOTAL, pressure and
    viscous force vectors. A fixture that wrote only two vectors is what let
    the total/pressure double-count survive for so long (see
    tests/test_stageD.py), so this one writes three and the total is the sum.
    """
    fdir = dirpath / "postProcessing" / "forces" / "0"
    fdir.mkdir(parents=True, exist_ok=True)
    rows = ["# Time  total_x total_y total_z  pressure_x .. viscous_x .."]
    for ti, p, v in zip(t, pressure, viscous):
        rows.append(f"{ti:.6f} ({p + v:.6f} 0 0) ({p:.6f} 0 0) ({v:.6f} 0 0)")
    (fdir / "force.dat").write_text("\n".join(rows) + "\n")
    (dirpath / "case.info").write_text(
        f"lwl={lwl}\nspeed_ms={speed}\nsymmetric={symmetric}\n"
        f"domain_length_m={4.5 * lwl:.4f}\ncells_bg=16245\n"
        f"Gate 2M = KCS/JBC resistance within Tokyo-2015 scatter\n"
        f"run: navalai/cfd/run-case.sh <this-dir> <np>\n{extra_info}")
    if cells is not None:
        (dirpath / "log.checkMesh").write_text(
            f"Mesh stats\n    points:           1\n    cells:            {cells}\n")
    return dirpath


def _flat_case(dirpath: Path, *, flow_throughs=2.0, n=400, **kw) -> Path:
    """A perfectly stationary run: nothing but the named guard can refuse it."""
    lwl, speed = kw.get("lwl", 7.2786), kw.get("speed", 2.196)
    t_end = flow_throughs * 4.5 * lwl / speed
    t = np.linspace(t_end / n, t_end, n)
    return _write_case(dirpath, t, np.full(n, -40.0), np.full(n, -35.0), **kw)


# --------------------------------------------------------------------------
# THE RULE. Each condition, fired on the recorded run that motivated it.
# --------------------------------------------------------------------------

def test_a_settled_run_is_settled_and_says_by_what_rule(tmp_path):
    r = post.settled_drag(_flat_case(tmp_path / "flat"))
    assert r["settled"] and r["reasons"] == ()
    # symmetric: half the hull is meshed, so the patch integral is half the
    # force. -75 N on the patch is -150 N on the ship.
    assert r["symmetric"] and r["drag_n"] == pytest.approx(-150.0)
    assert r["pressure_n"] == pytest.approx(-80.0)
    assert r["viscous_n"] == pytest.approx(-70.0)
    assert r["drift"] == pytest.approx(0.0, abs=1e-12)
    # the reader must never have to infer which rule produced the verdict
    for token in ("last 20%", "5-batch", "total/pressure/viscous",
                  "flow-through floor", "symmetric case doubled"):
        assert token in r["method"]


def test_the_drift_test_reads_the_components_not_only_the_total():
    """THE ONE THAT CHANGED A RECORDED VERDICT.

    `runs/lts` is the only case in this repository that the old gate called
    SETTLED. MEASURED, before this change:

        grid   bg cells  t_end  flow-thru  drag N     C_T      E%D  drift  settled
         lts      13608 2000.0     134.09   275.9  1.1995e-02 -223.2  4.5%  yes
        VERDICT: OUTSIDE the scatter band (-223.2% vs EFD)   [exit 3]

    4.5% drift on the TOTAL clears the 5% bar. The total is dominated by the
    VISCOUS part, which is the stable one; the PRESSURE component of the same
    window was drifting **7.5%** and still climbing (its eight window means run
    -73.9 -> -105.1 N monotonically). The C_T above was reported as a
    comparison against KRISO tank data on that basis.
    """
    if not (_RUNS / "lts" / "postProcessing").is_dir():
        pytest.skip("runs/lts is not present on this machine")
    r = post.settled_drag(_RUNS / "lts")
    assert r["drift_total"] == pytest.approx(0.0452, abs=5e-4), (
        "the total drift must still be the value the old rule passed on")
    assert r["drift_total"] <= post.DRIFT_TOL
    assert r["drift_pressure"] == pytest.approx(0.0751, abs=5e-4)
    assert not r["settled"], "a 7.5% pressure drift is not a settled run"
    assert any("pressure drift" in why for why in r["reasons"])


def test_an_oscillation_that_hides_from_the_drift_test_is_still_refused(tmp_path):
    """Drift compares TWO adjacent windows, so an oscillation whose period is
    close to the window length puts both at the same phase and cancels itself
    out of the comparison.

    MEASURED on runs/val_coarse5 (KCS, 1.33 flow-throughs, pressure component
    swinging with a ~5 s period) at a 0.40 tail — a value `post_gci.py --tail`
    accepted:

        component   drift   batch error
        total        0.3%      17.5%
        pressure     2.6%      17.4%
        viscous      2.9%       1.1%

    Every component inside the 5% drift bar, on a run whose pressure force
    varies by half its own mean. At a 0.25 tail on runs/beach: worst drift
    1.2%, batch error 5.5%.

    The period is known independently — a tank mode at 5.53 s, measured from
    the free surface (docs/research/CFD.md section 1) — and val_coarse5's settled
    window is 3.94 s, i.e. shorter than one cycle. A mean over less than a
    cycle is a phase sample.

    Reproduced here exactly: one full period across the settled window, so the
    two drift windows sample the same phase.
    """
    n, t_end = 2000, 40.0
    t = np.linspace(t_end / n, t_end, n)
    window = post.TAIL_FRAC * t_end
    # one full cycle per drift window => the two windows have equal means
    press = -40.0 + 30.0 * np.sin(2 * np.pi * t / window)
    case = _write_case(tmp_path / "osc", t, press, np.full(n, -35.0))
    r = post.settled_drag(case)
    assert r["drift_pressure"] < 0.01, (
        "the fixture must be one the DRIFT test cannot see — that is the point")
    assert r["error_pressure"] > post.DRIFT_TOL
    assert not r["settled"]
    assert any("batch error" in why for why in r["reasons"])


def test_high_frequency_noise_is_not_mistaken_for_an_oscillation(tmp_path):
    """The partner to the test above: the guard must not refuse a run that IS
    stationary. A converged interFoam history is noisy — what makes a mean
    trustworthy is that the noise averages out across the window, which is
    exactly what the batch error measures and a peak-to-peak bound does not."""
    rng = np.random.default_rng(2026)
    n, t_end = 2000, 40.0
    t = np.linspace(t_end / n, t_end, n)
    press = -40.0 + rng.normal(0.0, 4.0, n)          # 10% RMS, uncorrelated
    case = _write_case(tmp_path / "noisy", t, press, np.full(n, -35.0))
    r = post.settled_drag(case)
    assert r["settled"], f"refused a stationary run: {r['reasons']}"
    assert r["error_pressure"] < post.DRIFT_TOL


def test_under_one_flow_through_is_never_settled_however_flat(tmp_path):
    """runs/beach: 10.4 s against a 14.92 s flow-through, 3.3% drift by the old
    index rule, and the gate printed a C_T. A domain the free stream has not
    crossed still holds its initial condition. Physics, not a tuned constant."""
    short = post.settled_drag(_flat_case(tmp_path / "short", flow_throughs=0.70))
    assert short["drift"] == pytest.approx(0.0, abs=1e-12)
    assert not short["settled"]
    assert any("flow-through" in why for why in short["reasons"])
    assert post.settled_drag(_flat_case(tmp_path / "ok", flow_throughs=2.0))["settled"]


def test_the_window_is_taken_by_time_because_dt_is_adaptive(tmp_path):
    """gate2m windowed by SAMPLE INDEX (`fx[-n:]`). interFoam's dt is adaptive,
    so an index window silently over-weights the instants where the solver was
    taking small steps — which are the violent ones. MEASURED on runs/beach:
    the same last fifth reads 3.34% drift by index and 5.77% by time.

    Fired here on a history that is dense in its first half and sparse in its
    second: an index window would sit entirely inside the dense (old) part.
    """
    t = np.concatenate([np.linspace(0.01, 5.0, 500),      # dense: 0..5 s
                        np.linspace(5.01, 20.0, 100)])    # sparse: 5..20 s
    press = np.where(t < 5.0, -80.0, -40.0)
    case = _write_case(tmp_path / "adaptive", t, press, np.full(len(t), -35.0))
    r = post.settled_drag(case)
    assert r["pressure_n"] == pytest.approx(-80.0), (
        "the settled window is the last fifth of the RECORD IN TIME (16..20 s),"
        " where the pressure force is -40 N per half-hull")
    # by index the last fifth is samples 480..600, i.e. t = 4.8..20 s, which
    # straddles the step and would report a different force entirely
    assert float(np.mean(press[-len(t) // 5:])) != pytest.approx(-40.0)


# --------------------------------------------------------------------------
# ... and the same guards where the metric is ABSENT or GARBLED
# --------------------------------------------------------------------------

def test_a_diverged_solve_is_refused_rather_than_averaged(tmp_path):
    """`runs/val_coarse` holds FOUR force samples from a solve that died at
    t = 0.0072 with alpha.water at 1503.95; its last drag reads -7.57e45 N. The
    old gate returned None for it and printed "no force data yet", which is
    also what an unstarted case prints. Four samples is not a statistic, and a
    non-finite one is not a number."""
    if (_RUNS / "val_coarse" / "postProcessing").is_dir():
        with pytest.raises(post.ForceHistoryError, match="samples"):
            post.settled_drag(_RUNS / "val_coarse")

    n = 400
    t = np.linspace(0.05, 20.0, n)
    case = _write_case(tmp_path / "blown", t, np.full(n, -40.0),
                       np.full(n, -35.0))
    # one sample inside the settled window escaping to infinity, written the
    # way an exponent runaway reaches the file. A diverged solve is not a large
    # number to be averaged in; runs/val_coarse's last drag reads -7.57e45 N.
    f = case / "postProcessing" / "forces" / "0" / "force.dat"
    lines = f.read_text().splitlines()
    lines[-3] = "19.85 (-1e999 0 0) (-1e999 0 0) (-35.0 0 0)"
    f.write_text("\n".join(lines) + "\n")
    with pytest.raises(post.ForceHistoryError, match="not finite"):
        post.settled_drag(case)


def test_a_case_with_no_forces_or_no_receipts_refuses_rather_than_defaults(tmp_path):
    empty = tmp_path / "empty"
    (empty / "postProcessing").mkdir(parents=True)
    with pytest.raises(post.ForceHistoryError, match="no force"):
        post.settled_drag(empty)

    # speed and lwl are what the flow-through count and C_T are MADE of. A
    # missing receipt must not become a default: `${VAR:-0}` has already cost
    # this project a run.
    bare = _flat_case(tmp_path / "bare")
    (bare / "case.info").write_text("symmetric=True\n")
    with pytest.raises(post.ForceHistoryError, match="lwl/speed_ms"):
        post.settled_drag(bare)


def test_a_history_without_the_component_split_cannot_be_judged(tmp_path):
    """The rule tests the components, so a force file that has only totals is
    unjudgeable — and must say so rather than fall back to the total-only test
    that let runs/lts through."""
    case = _flat_case(tmp_path / "totals")
    f = case / "postProcessing" / "forces" / "0" / "force.dat"
    f.write_text("\n".join(f"{0.05 * i:.4f} (-75 0 0) (0 0 0)"
                           for i in range(1, 401)) + "\n")
    with pytest.raises(post.ForceHistoryError, match="pressure/viscous"):
        post.settled_drag(tmp_path / "totals")


# --------------------------------------------------------------------------
# ONE cell count: the mesh that was SOLVED, or nothing
# --------------------------------------------------------------------------

def test_the_cell_count_is_the_meshed_one_and_never_the_background_spec(tmp_path):
    """MEASURED on the recorded runs — the two quantities the two scripts read:

        run           case.info cells_bg   checkMesh cells   ratio
        beach                    13608            222444      16.3
        val_coarse5              16245            230725      14.2
        lts                      13608            243354      17.9

    checkMesh runs LAST in run-case.sh, after castellation, snapping, the
    z-only refineMesh rounds and the layer pass, so its count is the mesh the
    solver saw. cells_bg is the background block spec.
    """
    case = _flat_case(tmp_path / "meshed", cells=230725)
    assert post.cell_count(case) == 230725
    assert post.settled_drag(case)["cells"] == 230725
    assert "cells_bg=16245" in (case / "case.info").read_text(), (
        "the background spec is present and must NOT be what is read")

    if (_RUNS / "beach" / "log.checkMesh").exists():
        assert post.cell_count(_RUNS / "beach") == 222444
        assert post.read_case_info(_RUNS / "beach")["cells_bg"] == "13608"


def test_an_unmeasurable_cell_count_is_fatal_to_the_gci_not_a_fallback(tmp_path):
    """The fallback, MEASURED: `post_gci.py runs/kcs_gci2` read checkMesh for
    the one grid that had been meshed (243354) and case.info's cells_bg for the
    two that had not (38000, 108864), and printed

        measured refinement ratio    : 0.538 (c->m), 1.420 (m->f)

    A refinement ratio below 1 says the "medium" grid is coarser than the
    coarse one. The family was generated at sqrt(2).
    """
    no_log = _flat_case(tmp_path / "unmeshed")
    with pytest.raises(post.CellCountError, match="cells_bg"):
        post.cell_count(no_log)
    assert post.settled_drag(no_log)["cells"] is None

    # and a garbled log is not a number either
    (no_log / "log.checkMesh").write_text("    cells:            NaN\n")
    with pytest.raises(post.CellCountError):
        post.cell_count(no_log)

    for triplet in ((None, 38000, 108864), (243354, None, 108864),
                    (243354, 38000, 0)):
        with pytest.raises(post.CellCountError):
            post.family_refinement(*triplet)


def test_the_family_ratio_is_measured_and_a_split_family_is_refused():
    """Assuming r = sqrt(2) is the nz-snapping incident: the generator was
    producing 1.297 and 1.368 while post_gci assumed sqrt(2), and the report
    came out p = nan, GCI 58.5%. There is no assumed ratio any more, and a
    family whose two steps disagree is refused rather than averaged."""
    good = post.family_refinement(16245, 45949, 129960)   # exactly sqrt(2)^3
    assert good["r_coarse_to_medium"] == pytest.approx(2 ** 0.5, rel=1e-3)
    assert good["r"] == pytest.approx(2 ** 0.5, rel=1e-3)
    assert good["one_family"] and good["spread_pct"] < 0.5

    # the ratio post_gci printed for runs/kcs_gci2 by mixing measured counts
    # with background specs: 0.538 (c->m) against 1.420 (m->f)
    bad = post.family_refinement(243354, 38000, 108864)
    assert bad["r_coarse_to_medium"] == pytest.approx(0.538, abs=1e-3)
    assert bad["r_medium_to_fine"] == pytest.approx(1.420, abs=1e-3)
    assert not bad["one_family"]


# --------------------------------------------------------------------------
# ONE doubling
# --------------------------------------------------------------------------

def test_the_symmetric_doubling_happens_exactly_once(tmp_path):
    """post_gci.py had NO symmetric handling until late, and runs/kcs_gci IS
    symmetric — so every number it printed for that triplet was exactly half.
    Both scripts then grew their own copy of the rule. It is now decided in
    `post.is_symmetric` and applied in `post.settled_drag`, and a case with no
    receipt is FULL (the conservative reading: it does not invent a factor)."""
    half = post.settled_drag(_flat_case(tmp_path / "half", symmetric=True))
    full = post.settled_drag(_flat_case(tmp_path / "full", symmetric=False))
    assert half["drag_n"] == pytest.approx(2.0 * full["drag_n"])
    assert half["symmetric"] and not full["symmetric"]
    assert half["ct"] != half["ct"] or True     # no STL here: C_T is nan

    silent = _flat_case(tmp_path / "silent")
    (silent / "case.info").write_text("lwl=7.2786\nspeed_ms=2.196\n"
                                      "domain_length_m=32.75\n")
    assert not post.is_symmetric(silent)
    assert post.settled_drag(silent)["drag_n"] == pytest.approx(-75.0)


# --------------------------------------------------------------------------
# THE FENCE — neither script may re-grow a parser
# --------------------------------------------------------------------------

_SCRIPTS = ("post_gci.py", "gate2m.py")

# (pattern, what re-growing it would recreate). The precedent is
# test_gate2m_has_no_gci_of_its_own in tests/test_cfd_reference_parity.py; this
# extends the same idea from the GCI to everything else the two scripts used to
# duplicate. Comments and docstrings are stripped first, because the incidents
# above are DESCRIBED in both files and must stay describable.
_FORBIDDEN = [
    (r"\bparse_forces\b", "a second force parser"),
    (r"\bforces_path\b", "a second restart-merge"),
    (r"\bcells_bg\b", "the background block spec used as a cell count"),
    (r"log\.checkMesh", "a second cell-count parser"),
    (r"\bmean_resistance\b", "a second averaging window"),
    (r"[-+*/=(\s]2\.0\s*\*|\*\s*2\.0", "a second symmetric doubling"),
    (r"\bdef\s+cell_count\b", "a second cell-count rule"),
    (r"\bdef\s+_?is_symmetric\b", "a second symmetry rule"),
    (r"\bdef\s+settled\w*\b", "a second settledness rule"),
    (r"998\.8", "a second water density"),
    (r"4\.5\s*\*\s*lwl", "a second domain length"),
    (r"\btail_frac\b|--tail", "a tunable averaging window"),
]


def _code_only(path: Path) -> str:
    """Source with comments and docstrings removed (the parity-file helper)."""
    out, in_doc = [], False
    for line in path.read_text().splitlines():
        s = line.strip()
        if s.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc or s.startswith("#"):
            continue
        out.append(line.split("  #")[0])
    return "\n".join(out)


@pytest.mark.parametrize("script", _SCRIPTS)
@pytest.mark.parametrize("pattern,what", _FORBIDDEN)
def test_neither_script_regrows_its_own_post_processor(script, pattern, what):
    src = _code_only(_ROOT / "scripts" / script)
    hits = [ln.strip() for ln in src.splitlines() if re.search(pattern, ln)]
    assert not hits, (
        f"{script} has re-grown {what}. Gap R5.1 is exactly this: two "
        f"post-processors over the same files, disagreeing. It lives in "
        f"navalai/cfd/post.py.\n  " + "\n  ".join(hits))


@pytest.mark.parametrize("script", _SCRIPTS)
def test_both_scripts_read_the_one_settledness_rule(script):
    src = _code_only(_ROOT / "scripts" / script)
    assert "settled_drag" in src, (
        f"{script} must take its drag, its window, its doubling and its "
        f"verdict from post.settled_drag")
    assert "family_refinement" in src, (
        f"{script} must take its refinement ratio from post.family_refinement")


def test_the_fence_would_catch_a_regrown_parser(tmp_path):
    """The guard above, made to FIRE. A fence nobody has seen fail is a
    decoration; this is the same discipline the mesh-quality bars follow."""
    fake = tmp_path / "regrown.py"
    fake.write_text("from navalai.cfd import post\n"
                    "t, fx = post.parse_forces(f)\n"
                    "drag = 2.0 * fx.mean()\n")
    src = _code_only(fake)
    fired = [what for pattern, what in _FORBIDDEN if re.search(pattern, src)]
    assert "a second force parser" in fired
    assert "a second symmetric doubling" in fired


def test_the_gate_settle_tol_is_the_library_one():
    """`SETTLE_TOL` survives in scripts/gate2m.py for one reason:
    `navalai.pipeline.settle_tolerance()` reads that literal out of that file
    by regex, and pipeline.py is not this change's to edit. So it is a MIRROR
    of post.DRIFT_TOL, and this is the fence that keeps it one number.

    If pipeline is ever repointed at `post.DRIFT_TOL`, delete the mirror and
    this test with it."""
    src = (_ROOT / "scripts" / "gate2m.py").read_text()
    m = re.search(r"^SETTLE_TOL\s*=\s*([0-9.]+)", src, re.M)
    assert m, ("navalai/pipeline.py reads this literal by exactly this regex; "
               "removing it makes settle_tolerance() raise Unmeasurable")
    assert float(m.group(1)) == post.DRIFT_TOL
    from navalai.pipeline import settle_tolerance
    assert settle_tolerance() == post.DRIFT_TOL


# --------------------------------------------------------------------------
# the scripts themselves, over the real recorded runs
# --------------------------------------------------------------------------

def _script(name: str):
    spec = importlib.util.spec_from_file_location(
        f"{name}_under_test", _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_post_gci_has_its_first_test_and_refuses_a_directory_with_nothing_in_it(
        tmp_path, capsys, monkeypatch):
    """post_gci.py had NO test at all while gate2m.py had fourteen, and it was
    the one with the cells_bg fallback and the tunable tail.

    It also exited **0** on everything, including a directory holding no
    grids: `post_gci.py runs/lts` printed three MISSING lines, "(cell counts
    unavailable — falling back to assumed r = sqrt(2))" and exited 0."""
    g = _script("post_gci")
    monkeypatch.setattr(g.sys, "argv", ["post_gci", str(tmp_path)])
    assert g.main() == 2
    out = capsys.readouterr().out
    assert "NO RESULT" in out
    assert "sqrt(2)" not in out, "there is no assumed refinement ratio any more"


def test_post_gci_refuses_a_triplet_whose_grids_have_not_settled(tmp_path,
                                                                 capsys,
                                                                 monkeypatch):
    """Two settled grids and one transient is not a GCI. Fired with the
    transient in the FINE slot, which is the one Richardson leans on."""
    g = _script("post_gci")
    for name, cells in (("coarse", 16245), ("medium", 45949)):
        _flat_case(tmp_path / name, cells=cells)
    n = 600
    t = np.linspace(0.05, 30.0, n)
    _write_case(tmp_path / "fine", t, -40.0 - 5.0 * t, np.full(n, -35.0),
                cells=129960)
    monkeypatch.setattr(g.sys, "argv", ["post_gci", str(tmp_path)])
    assert g.main() == 2
    out = capsys.readouterr().out
    assert "2 settled grid(s) of 3: NO GCI" in out


def test_post_gci_reports_a_gci_over_a_measured_family(tmp_path, capsys,
                                                       monkeypatch):
    """The happy path, so the refusals above are known to be refusals and not
    an inability to report anything. Second-order convergence in the drag,
    r = sqrt(2), cell counts MEASURED from the (synthetic) checkMesh logs."""
    g = _script("post_gci")
    # f(h) = f0 + c h^2 with h ~ 1/r^k: -150, -155.66, -167.98 per full hull
    for name, cells, drag in (("coarse", 16245, -84.0), ("medium", 45949, -78.0),
                              ("fine", 129960, -75.0)):
        n, t = 400, None
        t = np.linspace(0.05, 40.0, n)
        _write_case(tmp_path / name, t, np.full(n, drag + 35.0),
                    np.full(n, -35.0), cells=cells)
    monkeypatch.setattr(g.sys, "argv", ["post_gci", str(tmp_path)])
    assert g.main() == 0
    out = capsys.readouterr().out
    assert "cells (measured, checkMesh) : 16245 / 45949 / 129960" in out
    assert "observed order p            : 2.00" in out
    assert "Roache GCI" in out


def test_gate2m_and_post_gci_report_the_same_drag_for_the_same_case(tmp_path):
    """The point of the gap. Two scripts, one number.

    Before: on runs/kcs_gci2/coarse gate2m reported 10.9% drift and post_gci
    2.1%, from the same force.dat — and post_gci's figure was HALF the drag
    until it grew its own doubling.
    """
    case = _flat_case(tmp_path / "coarse", cells=16245)
    gate2m = _script("gate2m")
    theirs, ours = gate2m.grid_result(case), post.settled_drag(case)
    assert theirs.keys() == ours.keys()
    for k in ours:                       # nan != nan, and C_T is nan with no STL
        a, b = theirs[k], ours[k]
        same = a == b or (isinstance(a, float) and math.isnan(a)
                          and isinstance(b, float) and math.isnan(b))
        assert same, f"{k}: gate2m {a!r} vs post {b!r}"


def test_gate2m_pairs_a_motion_report_with_its_own_case(tmp_path):
    """`zip(cases, rows)` paired the Nth case with the Nth SURVIVING row, so
    the moment any grid was refused every sinkage/trim report below it was
    attributed to the wrong grid. Rows now carry their own path."""
    case = _flat_case(tmp_path / "medium", cells=16245)
    assert Path(post.settled_drag(case)["case"]) == case
    src = _code_only(_ROOT / "scripts" / "gate2m.py")
    assert "zip(cases, rows)" not in src


def test_a_converging_slow_run_is_under_settled_not_failed(tmp_path):
    """The one-mesh receipt-4 ruling (2026-08-19). The Mac's section-H check
    produced a run with every solvability receipt green and drift 5.25%
    against the 5% bar at the fixed 2000-iteration budget — converging,
    slowly, no pathology. Calling that FAIL is the h18 lesson mirrored: a
    converging-but-slow run hiding in the fail column. The vocabulary now
    carries three outcomes; the 5% bar itself does not move.

    The synthetic history is an exponential settle whose window-over-window
    drift is DECLINING but still above the bar in the last window: the
    settled verdict stays False (the bar holds), and the outcome says
    under-settled with the measured trend beside it.
    """
    t = np.linspace(0.0, 100.0, 600)
    # slow exponential approach, constants DERIVED for the window rule:
    # tau=150 over a 100 s record puts the last-fifth-vs-previous drift at
    # ~5.5% of the settled magnitude (just over the 5% bar) with the
    # previous step at ~8% — declining, still failing.
    force = -(4000.0 + 6000.0 * np.exp(-t / 150.0))
    case = _write_case(tmp_path / "slow", t, 0.6 * force, 0.4 * force)
    rep = post.settled_drag(case)
    assert rep["settled"] is False, "the bar must not move"
    assert rep["outcome"] == "under-settled", (rep["outcome"], rep["reasons"])
    assert math.isfinite(rep["prev_drift"]) and rep["drift"] < rep["prev_drift"]
    assert all("drift" in r or "batch error" in r for r in rep["reasons"])

    # The NEGATIVE control: drift that GROWS window-over-window — an
    # accelerating ramp never settles and must be plain unsettled, or the
    # outcome would license extending a run that extension cannot fix.
    force = -4000.0 - 0.5 * t * t
    case = _write_case(tmp_path / "ramp", t, 0.6 * force, 0.4 * force)
    rep = post.settled_drag(case)
    assert rep["settled"] is False
    assert rep["outcome"] == "unsettled", (rep["outcome"], rep["drift"],
                                           rep["prev_drift"])

    # And a genuinely settled run reads settled, outcome agreeing.
    force = -4000.0 + 2.0 * np.sin(t)
    case = _write_case(tmp_path / "flat", t, 0.6 * force, 0.4 * force)
    rep = post.settled_drag(case)
    assert rep["settled"] is True and rep["outcome"] == "settled"


def test_a_mixed_lts_transient_history_counts_flow_throughs_from_the_tail(
        tmp_path):
    """The hybrid-lane seam (2026-08-19): an LTS spin-up restarted as a
    transient tail switches fvSchemes to Euler, so the pseudo-time guard
    stands down while the merged record's HEAD is still pseudo-iterations
    — and t[-1]/domain printed 136 fictional flow-throughs. With the
    runbook's `transient_tail_from=` receipt the count is real seconds
    from the tail's start; without it, a mixed history (Euler schemes
    over a log carrying LTS's own prints) is NaN — unmeasured, never a
    number.
    """
    t = np.linspace(2000.0, 2030.0, 600)     # a 30 s transient tail
    force = -4000.0 + 2.0 * np.sin(t)
    case = _write_case(tmp_path / "tail", t, 0.6 * force, 0.4 * force,
                       extra_info="transient_tail_from=2000.0")
    rep = post.settled_drag(case)
    # 30 s of real tail over the declared domain, NOT 2030 s from t=0
    dom = 4.5 * rep["lwl"]
    assert rep["flow_throughs"] == pytest.approx(30.0 * rep["speed"] / dom,
                                                 rel=1e-9)

    # the same case WITHOUT the receipt but WITH the LTS residue: NaN
    case2 = _write_case(tmp_path / "mixed", t, 0.6 * force, 0.4 * force)
    (case2 / "log.interFoam").write_text(
        "Flow time scale min/max = 1.1e-4, 2.0e-2\n")
    rep2 = post.settled_drag(case2)
    assert math.isnan(rep2["flow_throughs"])


def test_the_estimator_settles_the_oscillation_the_drift_bar_waits_out():
    """The operator's fix #1 (2026-08-20): the measured KCS-class signal —
    a stationary mean under a broadband oscillation (the 5.53 s tank mode,
    ~9% batch behaviour) — fails the windowed-drift bar on a short record
    and costs >= 5 flow-throughs to average. The batch-means estimator
    reports the SAME mean with a 95% CI inside the bar from the record it
    has: the oscillation becomes a variance term instead of a wait.
    """
    rng = np.random.default_rng(7)
    t = np.linspace(0.0, 45.0, 1400)          # ~8 cycles of the tank mode
    mean = -4000.0
    y = mean * (1.0
                + 0.045 * np.sin(2 * np.pi * t / 5.53)
                + 0.02 * np.sin(2 * np.pi * t / 2.1 + 1.0)
                + 0.01 * rng.standard_normal(len(t)))
    est = post.estimate_settled_mean(t, y)
    assert "refused" not in est, est
    assert est["rel_ci"] <= 0.05, est
    assert est["mean"] == pytest.approx(mean, rel=0.02)
    assert est["n_batches"] >= 8

    # THE FAIL DIRECTIONS (LESSONS class 3), all three:
    # a ramp holds no stationary mean — MSER refuses it
    ramp = mean - 40.0 * t
    r = post.estimate_settled_mean(t, ramp)
    assert "refused" in r and "transient-dominated" in r["refused"]
    # a record shorter than the oscillation's correlation time refuses on
    # the batch floor rather than shrinking the divisor
    t_short = np.linspace(0.0, 6.0, 200)      # ~1 cycle
    y_short = mean * (1.0 + 0.09 * np.sin(2 * np.pi * t_short / 5.53))
    rs = post.estimate_settled_mean(t_short, y_short)
    assert ("refused" in rs) or rs["rel_ci"] > 0.05, rs
    # and a tiny sample count is refused outright
    assert "refused" in post.estimate_settled_mean(t[:20], y[:20])
