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
