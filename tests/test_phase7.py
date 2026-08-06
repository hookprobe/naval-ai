"""Gate 7: harvest feeds provenance, retrain deploys only when the frozen
benchmark does not degrade, corrupted models are refused."""

import json

import numpy as np
import pytest

from navalai import db
from navalai.flywheel import harvest, retrain
from navalai.mission import MissionSpec
from navalai.surrogate import GP


@pytest.fixture(scope="module")
def stocked(tmp_path_factory):
    d = tmp_path_factory.mktemp("fly")
    prov = db.Provenance(d / "p.sqlite3")
    m = MissionSpec()
    n = harvest(60, m, prov, seed=21)
    return prov, m, d, n


def test_harvest_records_all_quantities(stocked):
    prov, _m, _d, n = stocked
    assert n == 60
    X, y = prov.training_matrix("L1", "wh_per_nm")
    assert len(y) == 60 and (y > 0).all()
    X2, y2 = prov.training_matrix("L1", "GM_m")
    assert len(y2) == 60


def test_retrain_from_provenance_and_baseline_written(stocked):
    prov, m, d, _n = stocked
    # bootstrap=True is now REQUIRED to create the first baseline. Without it a
    # missing file used to mean `prior is None` -> `ok = True`, so the first
    # retrain on any fresh clone deployed unconditionally and wrote its own
    # numbers as the eternal reference. Creating a baseline is legitimate;
    # doing it by accident is what the flag prevents.
    gp, rep = retrain(prov, m, "wh_per_nm", baseline_path=d / "base.json",
                      bootstrap=True)
    assert gp is not None and rep.passed_gate
    assert rep.median_rel_err < 0.35        # 60 samples: loose but real
    base = json.loads((d / "base.json").read_text())
    assert "wh_per_nm" in base


def test_second_retrain_gated_against_first(stocked):
    prov, m, d, _n = stocked
    retrain(prov, m, "wh_per_nm", baseline_path=d / "base.json", bootstrap=True)
    gp, rep = retrain(prov, m, "wh_per_nm", baseline_path=d / "base.json")
    assert gp is not None and rep.baseline    # compared against the first run
    assert rep.passed_gate


def test_corrupted_model_never_deploys(stocked, monkeypatch):
    """Simulate a poisoned retrain: shuffle the labels. The frozen-benchmark
    gate must refuse deployment."""
    prov, m, d, _n = stocked
    real_fit = GP.fit
    rng = np.random.default_rng(5)

    def poisoned_fit(X, y, *a, **kw):
        return real_fit(X, rng.permutation(y), *a, **kw)

    # An honest baseline must exist first, or "refused" would be ambiguous
    # between "the model is bad" and "there was nothing to compare against".
    retrain(prov, m, "wh_per_nm", baseline_path=d / "base.json", bootstrap=True)
    monkeypatch.setattr(GP, "fit", staticmethod(poisoned_fit))
    gp, rep = retrain(prov, m, "wh_per_nm", baseline_path=d / "base.json")
    assert gp is None and not rep.passed_gate
    # baseline file unchanged by the refused model
    base = json.loads((d / "base.json").read_text())
    assert base["wh_per_nm"]["median_rel_err"] == pytest.approx(
        rep.baseline["median_rel_err"])


def test_gate_runner_never_reports_green_for_a_suite_that_ran_nothing():
    """Honesty rule 6, applied to the gate runner itself.

    pytest exits 0 when every test SKIPS, and the runner used to decide GREEN
    purely on the return code. So a machine lacking an optional dependency
    (capytaine, mujoco, cadquery) would have printed "Gate 2 GREEN" while
    verifying nothing at all — a soft green produced by the tool meant to
    prevent soft greens. Found while adding CI, which would have baked it in.
    """
    from navalai.gates import counts, status_of

    assert counts(" 13 passed in 0.11s")["passed"] == 13
    # `xfailed`/`xpassed` joined the dict when the adversarial review showed
    # one @pytest.mark.xfail turned a failing gate GREEN with no annotation,
    # so this compares the outcomes it cares about rather than the whole shape.
    c = counts(" 4 skipped in 0.01s")
    assert {k: c[k] for k in ("passed", "failed", "skipped", "error")} == {
        "passed": 0, "failed": 0, "skipped": 4, "error": 0}

    # the actual bug: all-skipped exits 0 and must NOT be GREEN
    label, is_fail = status_of(0, counts(" 4 skipped in 0.01s"))
    assert label.startswith("SKIPPED"), label
    assert "GREEN" not in label

    assert status_of(0, counts(" 13 passed in 0.1s")) == ("GREEN", False)
    assert status_of(1, counts(" 1 failed, 3 passed in 1s"))[1] is True
    # a partial skip still counts as green, but says so out loud
    lab, fail = status_of(0, counts(" 9 passed, 2 skipped in 1s"))
    assert lab == "GREEN (2 skipped)" and fail is False


def test_red_gates_fail_the_runner_but_suites_only_does_not():
    """Audit finding (2026-08-05): `python -m navalai.gates` exited 0 with Gate
    2M and 2U RED, because rows without a pytest suite printed their status and
    `continue`d without touching the failure counter. CI therefore went green
    with KCS at -151% vs EFD, and pre-push's "BLOCKED: a gate is RED" could
    never fire for the gates that were actually red.

    Two behaviours are pinned, because they are in tension:
      - a RED row must make the FULL run fail (honesty rule 6);
      - --suites-only must NOT count it, so the pre-push hook blocks
        REGRESSIONS without blocking every push on a known recorded red gate.
        A hook that always blocks is a hook everyone bypasses.

    NOTE: this exercises main() in-process with a stub. It must NEVER shell out
    to `python -m navalai.gates` — the runner executes tests/test_phase7.py,
    so a subprocess call from here recurses without limit. (Learned the hard
    way; the first version of this test did exactly that.)
    """
    import navalai.gates as G

    real = G.GATES
    try:
        # An UNLEDGERED red is a NEW break and must fail the full run.
        G.GATES = [G.Gate("Gate X", "a red gate nobody recorded",
                          status=G.Verdict.RED)]
        assert G.main([]) == 1, "a RED row must fail the full run"
        assert G.main(["--suites-only"]) == 0, \
            "--suites-only must ignore recorded reds"

        G.GATES = [G.Gate("Gate Y", "metal", status=G.Verdict.METAL,
                          detail="needs hardware")]
        assert G.main([]) == 0, \
            "METAL/REVIEW rows are honestly unverifiable, not failures"
    finally:
        G.GATES = real


# ---------------------------------------------------------------------------
# Gate 7 clause 1: "surrogate error DECREASES release-over-release"
# ---------------------------------------------------------------------------

def _stub_prov():
    class P:
        def training_matrix(self, *a):
            return np.zeros((30, 15)), np.ones(30)
    return P()


def test_the_regression_gate_does_not_ratchet_downhill(tmp_path):
    """Adversarial finding (2026-08-05), reproduced here as a fence.

    The gate accepted `med <= prior * 1.25` and then wrote the accepted, WORSE
    metric back as the new prior. MEASURED with a stubbed metric: ten
    consecutive retrains ALL passed while median_rel_err went 0.100 -> 0.859
    (8.6x) and coverage 0.950 -> -0.450. A negative probability passed,
    because it was only ever compared against `prior - 0.15`.

    Gate 7's word is "decreases". The comparison is now against a monotone
    high-water mark, so drift cannot accumulate one tolerance at a time.
    """
    from unittest import mock

    import navalai.flywheel as F

    bp = tmp_path / "baselines.json"
    bp.write_text(json.dumps({"wh_per_nm": {
        "median_rel_err": 0.10, "coverage_2sigma": 0.95,
        "best_median_rel_err": 0.10, "best_coverage_2sigma": 0.95}}))

    med, cov, deployed = 0.10, 0.95, 0
    for _ in range(10):
        med, cov = med * 1.24, cov - 0.14      # just inside the OLD tolerance
        with mock.patch.object(F, "_metrics", return_value=(med, cov)), \
             mock.patch.object(F, "sample_valid", return_value=(None, None)), \
             mock.patch.object(F.GP, "fit", staticmethod(lambda *a, **k: object())):
            _gp, rep = F.retrain(_stub_prov(), None, baseline_path=bp)
        deployed += bool(rep.passed_gate)
    assert deployed <= 1, (
        f"{deployed}/10 degrading models deployed — the ratchet is back")


def test_absolute_floors_bind_even_without_history(tmp_path):
    # No baseline, no tolerance and no ratchet may admit a model this bad.
    from unittest import mock

    import navalai.flywheel as F

    bp = tmp_path / "baselines.json"
    bp.write_text("{}")
    with mock.patch.object(F, "_metrics",
                           return_value=(F.HARD_MAX_MEDIAN_REL_ERR * 1.1, 0.95)), \
         mock.patch.object(F, "sample_valid", return_value=(None, None)), \
         mock.patch.object(F.GP, "fit", staticmethod(lambda *a, **k: object())):
        _gp, rep = F.retrain(_stub_prov(), None, baseline_path=bp)
    assert rep.passed_gate is False


def test_a_missing_baseline_refuses_instead_of_passing(tmp_path):
    """data/baselines.json was untracked, so on a fresh clone `prior is None`
    made `ok = True` unconditionally: the FIRST retrain always deployed and
    wrote its own numbers as the eternal reference. Proven with a
    label-shuffled model (median_rel_err 0.407 vs an honest 0.165) which
    deployed and became the benchmark.

    Creating the first baseline is legitimate; doing it by accident is not.
    """
    from unittest import mock

    import navalai.flywheel as F

    missing = tmp_path / "nope.json"
    with mock.patch.object(F, "_metrics", return_value=(0.407, 0.9)), \
         mock.patch.object(F, "sample_valid", return_value=(None, None)), \
         mock.patch.object(F.GP, "fit", staticmethod(lambda *a, **k: object())):
        with pytest.raises(FileNotFoundError, match="frozen benchmark"):
            F.retrain(_stub_prov(), None, baseline_path=missing)
        # ...but an explicit bootstrap is allowed, and still honours the floors
        _gp, rep = F.retrain(_stub_prov(), None, baseline_path=missing,
                             bootstrap=True)
        assert rep.passed_gate is False, "0.407 is above the absolute floor"
