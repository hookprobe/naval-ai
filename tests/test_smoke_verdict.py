"""Stage 2 of the validation ladder — the smoke solve, classified pure-Python.

The Mac runner (run-case.sh's future SMOKE_ONLY=N mode) runs the first ~200
LTS iterations of the real interFoam solve and keeps the checkpoint;
`navalai.cfd.post.smoke_verdict` is the fortress-side reading of the log it
leaves behind. Every synthetic log here is written in interFoam's own line
formats — the exact heads run-case.sh's live-abort awk and
mesh_robustness.solve_one key on — so the fixture and the shell can never
drift apart silently.

The two incidents the stage exists to catch, reproduced as fixtures:
  * h2  — died at LTS iteration 104 (sigFpe, no "--> FOAM FATAL" line
          anywhere in the log) on a mesh that passed every checkMesh bar,
          discovered at a 323 s full-solve price;
  * h18 — tau collapsed to 4.356e-18 s and burned a 2700 s budget into the
          timeout column.
And the defect-class-1 fence: an unmeasurable case (absent/truncated log, no
tau prints, no force history) must NEVER read as promoted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from navalai.cfd import post

_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# fixtures: a synthetic smoke case, written the way interFoam writes one
# --------------------------------------------------------------------------

def _write_forces(case: Path, n: int, blow_at: int | None = None) -> None:
    """A force.dat in OpenFOAM's own layout (Time, total, pressure, viscous
    vectors — the three-vector discipline test_settled_drag's fixture keeps).
    Under LTS the time column is the iteration count."""
    fdir = case / "postProcessing" / "forces" / "0"
    fdir.mkdir(parents=True, exist_ok=True)
    rows = ["# Time  total_x .. pressure_x .. viscous_x .."]
    for i in range(1, n + 1):
        if blow_at is not None and i >= blow_at:
            # the way an exponent runaway reaches the file (runs/val_coarse's
            # last drag reads -7.57e45; -1e999 parses to -inf)
            rows.append(f"{i} (-1e999 0 0) (-1e999 0 0) (-35.0 0 0)")
        else:
            rows.append(f"{i} (-75.0 0 0) (-40.0 0 0) (-35.0 0 0)")
    (fdir / "force.dat").write_text("\n".join(rows) + "\n")


def _write_smoke_log(case: Path, n: int, tau: float = 1.1e-4,
                     collapse_at: int | None = None,
                     collapse_tau: float = 4.356e-18,
                     fatal_at: int | None = None) -> None:
    """A log.interFoam: banner (WITH the trapFpe line that once read a clean
    run as a crash), then per-iteration Time/tau blocks."""
    case.mkdir(parents=True, exist_ok=True)
    lines = [
        "Build  : _74a3e5f6-20230627 OPENFOAM=2306",
        "trapFpe: Floating point exception trapping enabled (FOAM_SIGFPE).",
        "",
        "Starting time loop",
        "",
    ]
    for i in range(1, n + 1):
        lines.append(f"Time = {i}")
        this = collapse_tau if collapse_at == i else tau
        lines.append(f"Flow time scale min/max = {this:.6g}, 2.02e-2")
        lines.append("smoothSolver:  Solving for alpha.water, Initial "
                     "residual = 0.001, Final residual = 1e-09")
        if collapse_at == i:
            # run-case.sh's live abort kills the run here; the log just ends
            break
        if fatal_at == i:
            # the h2 log shape: NO "--> FOAM FATAL" line, only the handler
            # and the mpirun notice (see solve_one's calibration comment)
            lines.append("#0  Foam::sigFpe::sigHandler(int) at ??:?")
            lines.append("#4  Foam::GAMGSolver::scale(...) at ??:?")
            lines.append("prterun noticed that process rank 7 with PID 0 "
                         "exited on signal 4 (Illegal instruction: 4).")
            break
    (case / "log.interFoam").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------
# the four verdicts, each fired on the incident that motivated it
# --------------------------------------------------------------------------

def test_a_healthy_smoke_window_is_promoted_with_its_receipts(tmp_path):
    case = tmp_path / "ok"
    _write_smoke_log(case, 200)
    _write_forces(case, 200)
    r = post.smoke_verdict(case)
    assert r["verdict"] == "promoted", r
    assert r["iterations_seen"] == 200
    assert r["taus_seen"] == 200
    assert r["min_tau"] == pytest.approx(1.1e-4)
    # the banner's "Floating point exception trapping enabled" line is IN the
    # log and must not read as a crash — solve_one's own recorded trap


def test_tau_exactly_at_the_bar_is_still_promoted(tmp_path):
    """run-case.sh aborts on `v < 1e-12`, strictly below — the boundary
    belongs to the pass side in both parsers or they disagree at the bar."""
    case = tmp_path / "atbar"
    _write_smoke_log(case, 200, tau=1e-12)
    _write_forces(case, 200)
    assert post.smoke_verdict(case)["verdict"] == "promoted"


def test_a_tau_collapse_is_refused_with_minimum_and_iteration(tmp_path):
    """h18's measured 4.356e-18, priced at ~3 min instead of 2700 s."""
    case = tmp_path / "h18"
    _write_smoke_log(case, 200, collapse_at=104)
    _write_forces(case, 104)
    r = post.smoke_verdict(case)
    assert r["verdict"] == "refused-tau", r
    assert r["min_tau"] == pytest.approx(4.356e-18)
    assert r["iteration"] == 104
    assert r["min_tau_iteration"] == 104
    assert r["iterations_seen"] == 104


def test_solver_death_mid_window_is_refused_fatal_at_the_iteration(tmp_path):
    """h2: sigFpe at iteration 104, NO '--> FOAM FATAL' line in the log —
    the detector keyed on that line reported fatal: false and misnamed it."""
    case = tmp_path / "h2"
    _write_smoke_log(case, 200, fatal_at=104)
    _write_forces(case, 104)
    r = post.smoke_verdict(case)
    assert r["verdict"] == "refused-fatal", r
    assert r["iteration"] == 104
    assert r["iterations_seen"] == 104
    # the healthy taus before the death are still receipts
    assert r["min_tau"] == pytest.approx(1.1e-4)


def test_a_nonfinite_force_is_refused_fatal_not_averaged(tmp_path):
    case = tmp_path / "blown"
    _write_smoke_log(case, 200)
    _write_forces(case, 200, blow_at=180)
    r = post.smoke_verdict(case)
    assert r["verdict"] == "refused-fatal", r
    assert r["iteration"] == 180
    assert "non-finite" in r["why"]


def test_a_truncated_log_is_unmeasured_never_promoted(tmp_path):
    """Defect class 1, the whole point: a smoke that stopped at 50 of 200
    with no death marker is 'I could not measure this', not a pass."""
    case = tmp_path / "short"
    _write_smoke_log(case, 50)
    _write_forces(case, 50)
    r = post.smoke_verdict(case)
    assert r["verdict"] == "unmeasured", r
    assert r["iterations_seen"] == 50
    assert "50" in r["why"] and "200" in r["why"]

    # an absent log is the same refusal
    r2 = post.smoke_verdict(tmp_path / "never-ran")
    assert r2["verdict"] == "unmeasured"
    assert r2["iterations_seen"] == 0


def test_a_complete_log_without_receipts_is_unmeasured(tmp_path):
    # no force history at all: finite forces are part of the promotion bar
    case = tmp_path / "noforces"
    _write_smoke_log(case, 200)
    r = post.smoke_verdict(case)
    assert r["verdict"] == "unmeasured", r
    assert "force" in r["why"]

    # 200 Time lines but zero tau prints: not an LTS smoke log, and a bar
    # that was never measured must not be vacuously passed
    case2 = tmp_path / "notau"
    case2.mkdir()
    (case2 / "log.interFoam").write_text(
        "\n".join(f"Time = {i}" for i in range(1, 201)) + "\n")
    _write_forces(case2, 200)
    r2 = post.smoke_verdict(case2)
    assert r2["verdict"] == "unmeasured", r2
    assert r2["taus_seen"] == 0


def test_events_beyond_the_smoke_window_do_not_decide_the_smoke(tmp_path):
    """The verdict is about the FIRST n_iters iterations. A collapse at
    iteration 300 of a 400-iteration log is the full solve's business."""
    case = tmp_path / "later"
    _write_smoke_log(case, 400, collapse_at=300)
    _write_forces(case, 400)
    r = post.smoke_verdict(case, n_iters=200)
    assert r["verdict"] == "promoted", r
    assert r["iterations_seen"] == 200


# --------------------------------------------------------------------------
# the fence: this parser and run-case.sh's live abort are ONE bar
# --------------------------------------------------------------------------

def test_the_smoke_bar_and_patterns_are_the_runners_own():
    """The two parsers over one log must never disagree: the bar literal and
    the line head are read out of run-case.sh itself, the way
    test_the_gate_settle_tol_is_the_library_one fences SETTLE_TOL."""
    src = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    assert "v + 0 < 1e-12" in src, (
        "run-case.sh's live-abort bar moved; move post.SMOKE_TAU_FLOOR with "
        "it in the same commit")
    assert post.SMOKE_TAU_FLOOR == 1e-12
    # the awk keys on this exact head, escaped slash and all
    assert r"/^Flow time scale min\/max = /" in src
    assert post._SMOKE_TAU_PREFIX == "Flow time scale min/max = "
