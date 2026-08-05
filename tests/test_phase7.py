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
    gp, rep = retrain(prov, m, "wh_per_nm", baseline_path=d / "base.json")
    assert gp is not None and rep.passed_gate
    assert rep.median_rel_err < 0.35        # 60 samples: loose but real
    base = json.loads((d / "base.json").read_text())
    assert "wh_per_nm" in base


def test_second_retrain_gated_against_first(stocked):
    prov, m, d, _n = stocked
    gp, rep = retrain(prov, m, "wh_per_nm", baseline_path=d / "base.json")
    assert gp is not None and rep.baseline    # baseline from previous test used
    assert rep.passed_gate


def test_corrupted_model_never_deploys(stocked, monkeypatch):
    """Simulate a poisoned retrain: shuffle the labels. The frozen-benchmark
    gate must refuse deployment."""
    prov, m, d, _n = stocked
    real_fit = GP.fit
    rng = np.random.default_rng(5)

    def poisoned_fit(X, y, *a, **kw):
        return real_fit(X, rng.permutation(y), *a, **kw)

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
    assert counts(" 4 skipped in 0.01s") == {"passed": 0, "failed": 0,
                                             "skipped": 4, "error": 0}

    # the actual bug: all-skipped exits 0 and must NOT be GREEN
    label, is_fail = status_of(0, counts(" 4 skipped in 0.01s"))
    assert label.startswith("SKIPPED"), label
    assert "GREEN" not in label

    assert status_of(0, counts(" 13 passed in 0.1s")) == ("GREEN", False)
    assert status_of(1, counts(" 1 failed, 3 passed in 1s"))[1] is True
    # a partial skip still counts as green, but says so out loud
    lab, fail = status_of(0, counts(" 9 passed, 2 skipped in 1s"))
    assert lab == "GREEN (2 skipped)" and fail is False
