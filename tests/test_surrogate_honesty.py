"""Gate 3S: the surrogate's honesty rules, on the path the product uses.

Four register rows meet here, and what they have in common is a mechanism that
was BUILT and then never REACHED:

  A4  `is_ood()` had two call sites in the whole repository and both were in
      tests. `predict_or_escalate()` was written to consume it and nothing in
      production called that either — `retrain` handed back a bare `GP`.
  D3  `data/baselines.json` was untracked, so the first retrain on any clone
      deployed unconditionally and became the eternal reference.
  D4  the regression gate compared against the LAST value and wrote the worse
      metric back, so ten retrains walked the bar downhill with a green light.
  D11 Gate 4's feasibility bar was measured inside the rejection loop, where it
      is 100% by construction and says nothing about the model.

`tests/test_phase3.py` owns the surrogate's internals and `tests/test_phase7.py`
the flywheel's; this file owns the seam between them — the query path a caller
actually holds, and the preconditions the deployment mark needs to mean
anything. Every bar here is a MEASURED one and every guard is shown firing on a
realistic input as well as on an absent or garbled metric.
"""

import json
import pathlib
import shutil
import tempfile
from unittest import mock

import numpy as np
import pytest

import navalai.flywheel as F
from navalai import db, grammar
from navalai.evaluate import evaluate, sample_valid, tier_rank
from navalai.flywheel import (DeployedSurrogate, harvest, retrain,
                              suite_fingerprint, transform_for)
from navalai.generative import make_generator
from navalai.mission import MissionSpec
from navalai.surrogate import GP, OODRefusal

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_COMMITTED = _ROOT / "data" / "baselines.json"


@pytest.fixture(scope="module")
def stocked(tmp_path_factory):
    d = tmp_path_factory.mktemp("honesty")
    prov = db.Provenance(d / "p.sqlite3")
    m = MissionSpec()
    harvest(120, m, prov, seed=21)
    return prov, m, d


@pytest.fixture(scope="module")
def short_hull_model(stocked):
    """A surrogate trained on SHORT hulls only, which is what a real one sees.

    A surrogate is trained on wherever the optimiser has been, never on the
    whole box, so the honest probe for a support test is a training set
    restricted to part of the box. MEASURED at this configuration: 60 of the
    120 harvested hulls have LWL <= 12 m, and 48 of the 60 longer ones are
    out of support by the model's own test.
    """
    prov, m, _d = stocked
    X, y = prov.training_matrix("L1", "wh_per_nm")
    i_lwl = grammar.NAMES.index("LWL")
    short = X[:, i_lwl] <= 12.0
    tf = transform_for("wh_per_nm")
    gp = GP.fit(X[short], tf.fwd(y[short]), seed=1)
    long_hulls = X[~short]
    probe = long_hulls[int(np.argmax(gp.support_distance(long_hulls)))]
    return DeployedSurrogate(gp, "wh_per_nm", m, tf, int(short.sum())), probe


# ---------------------------------------------------------------------------
# A4 — the refusal is on the query path, not in a test
# ---------------------------------------------------------------------------

def test_an_off_support_query_escalates_to_the_ladder_instead_of_answering(
        short_hull_model):
    """A4. `is_ood()` flagged and nothing consumed the flag; Gate 3's bar is
    "OOD queries reliably escalate to L2/L3", and a boolean no caller reads is
    not an implementation of it.

    MEASURED on this fixture (120 harvested hulls, training restricted to
    LWL <= 12 m, probe = the most distant legal hull in the harvest, LWL
    18.47 m, nearest-training-point distance 1.533 against a support radius of
    1.227):

        bare gp.predict     998.29 Wh/NM, sigma 0.767 in LOG space, no tier
        query()             841.82 Wh/NM +- 252.55 Wh/NM, tier L1

    The surrogate's confident-looking number is 18.6% above the one the ladder
    computes for the same hull, and it arrives in the same shape as every
    number this model produces. The escalated answer is the LADDER'S — value
    and sigma both — because the tier a number carries must name the solver
    that produced it.
    """
    model, probe = short_hull_model
    assert model.gp.is_ood(probe[None, :])[0], (
        "the probe is inside the model's support; this trap needs one that is "
        "not")

    got = model.query(probe)
    ev = evaluate(probe, model.mission)
    tier_b, sigma_b, _basis = ev.badges["wh_per_nm"]
    assert got["tier"] == "L1" == tier_b
    assert got["value"] == pytest.approx(ev.energy.wh_per_nm, rel=1e-9)
    assert got["sigma"] == pytest.approx(sigma_b, rel=1e-9)

    # ...and it is a DIFFERENT number from the one the surrogate would have
    # given, or this test would pass on a model that never escalated.
    raw = float(np.exp(model.gp.predict(probe[None, :])[0][0]))
    assert abs(raw - got["value"]) / got["value"] > 0.05, (
        f"surrogate {raw:.1f} and ladder {got['value']:.1f} agree too closely "
        f"for this probe to demonstrate anything")


def test_the_query_path_refuses_when_no_escalation_is_offered(short_hull_model):
    """The fallback when the caller offers no route to real physics is a
    REFUSAL carrying its reason — silence is the one answer that is never
    honest. The message must carry the numbers that produced it, because a
    refusal nobody can audit is a different kind of silence."""
    model, probe = short_hull_model
    with pytest.raises(OODRefusal) as e:
        model.query(probe, escalate=False)
    assert e.value.distance > e.value.threshold > 0
    assert np.isfinite(e.value.sigma)
    assert "outside the surrogate's support" in str(e.value)


def test_a_deployed_surrogate_has_no_unguarded_array_path(short_hull_model):
    """`predict()` is the method a caller reaches for, and on a bare `GP` it
    answers everywhere. A deployed model with one unguarded method has no
    guard, so the wrapper's `predict()` refuses the rows it cannot support and
    names them."""
    model, probe = short_hull_model
    supported = model.gp.X[:3] * model.gp.x_hi + model.gp.x_lo   # de-normalised
    batch = np.vstack([supported, probe[None, :]])
    with pytest.raises(OODRefusal, match=r"rows \[3\]"):
        model.predict(batch)
    # the supported rows on their own are answered, in modelled space
    mean, sigma = model.predict(supported)
    assert np.isfinite(mean).all() and (sigma > 0).all()


def test_the_escalation_refuses_a_design_the_ladder_cannot_answer(
        short_hull_model):
    """The absent-metric half of the same guard. A hull the grammar rejects
    never reaches L1, so `evaluate` stops at tier L0 with no energy report, and
    an escalation that cannot run is not an escalation — it is the surrogate's
    guess with a better badge on it.

    MEASURED: a vector three box-widths outside the grammar box (LWL 68 m,
    BWL 20.4 m) is out of support AND out of the grammar, and the query path
    returns no number at all — where `gp.predict` answers 1068.4 Wh/NM for a
    68-metre boat this model has never been near (770.9 Wh/NM from the
    full-box model of the same harvest, for a defect that does not depend on
    the fixture).
    """
    model, _probe = short_hull_model
    wild = grammar.HIGH + 3.0 * (grammar.HIGH - grammar.LOW)
    assert model.gp.is_ood(wild[None, :])[0]
    assert np.isfinite(model.gp.predict(wild[None, :])[0]).all(), (
        "the raw model still answers this — which is the point")
    with pytest.raises(OODRefusal, match="cannot answer it either"):
        model.query(wild)


def test_the_escalation_refuses_a_ladder_answer_that_is_not_reportable(
        short_hull_model):
    """The GARBLED half. `evaluate` downgrades a quantity whose value or sigma
    is not finite to an `L1-INVALID` badge (gap E10's fix). An escalation that
    passed that off as an L1 answer would launder the exact defect the badge
    exists to announce, so it is refused — and refused for the badge, not for
    the value, so a nan sigma on a finite value is caught too.
    """
    model, probe = short_hull_model
    real = evaluate(probe, model.mission)

    class _Invalid:
        tier = "L1"
        violations = ("resistance is not a reportable L1 quantity",)
        energy = real.energy
        gm_m = real.gm_m
        resistance = real.resistance
        badges = {"wh_per_nm": ("L1-INVALID", float("nan"), "assumed")}

    with mock.patch.object(F, "evaluate", return_value=_Invalid()):
        with pytest.raises(OODRefusal, match="L1-INVALID"):
            model.query(probe)


def test_a_surrogate_number_carries_value_tier_and_sigma_in_physical_units(
        short_hull_model):
    """Honesty rule 1, on the object a caller holds.

    Two things this pins. The tier badge `S1` is DELIBERATELY not a member of
    `evaluate.TIER_ORDER`, so `tier_rank("S1")` is -1 — below L0 — and a
    surrogate answer can never satisfy a requirement stated in ladder tiers.
    And the sigma comes back in the units of the VALUE: the GP reports 0.0011
    in log space at this in-support point and the caller is handed 2.69 Wh/NM
    against a 2443.9 Wh/NM value, not 0.0011. A sigma in the wrong space is a
    number wearing the wrong units, which in this repository is how
    `forceCoeffs` came out wrong by exactly 2x.
    """
    model, _probe = short_hull_model
    inside = model.gp.X[3] * model.gp.x_hi + model.gp.x_lo
    got = model.query(inside)
    assert got["tier"] == "S1" and tier_rank("S1") == -1 < tier_rank("L0")
    assert set(got) == {"value", "tier", "sigma", "quantity"}

    z, sz = model.gp.predict(inside[None, :])
    assert got["value"] == pytest.approx(float(np.exp(z[0])), rel=1e-12)
    # delta method through the log: sigma_y = y * sigma_z, and NOT sigma_z
    assert got["sigma"] == pytest.approx(got["value"] * float(sz[0]), rel=1e-12)
    assert got["sigma"] > 10.0 * float(sz[0])


def test_retrain_hands_back_a_guarded_model_and_records_what_it_refuses(
        stocked, tmp_path):
    """A4 end to end: the deployment path is where the bare GP escaped from.

    Also records `frozen_ood_rate` — the share of its own deployment benchmark
    the model would refuse in production. It is a RECEIPT and not a bar: the
    benchmark's held-out wedge is deliberately outside the training draw, so a
    nonzero rate is the design working. MEASURED at the shipped configuration
    (120 harvested hulls, wh_per_nm, harvest seed 21, holdout seed 4242): 1 of
    27 points, 3.7%. The wedge is out of the training SAMPLE but inside the
    model's support radius (distances 0.726-1.098 against d_support 1.075),
    which is the same thing the 10.4% median error there says.
    """
    prov, m, _d = stocked
    bp = tmp_path / "baselines.json"
    shutil.copy(_COMMITTED, bp)
    model, rep = retrain(prov, m, "wh_per_nm", baseline_path=bp)
    assert isinstance(model, DeployedSurrogate) and not isinstance(model, GP)
    assert not hasattr(model, "fit")

    assert np.isfinite(rep.frozen_ood_rate)
    Xt, _yt, _labels = F.frozen_suite(m, "wh_per_nm", seed=4242)
    assert rep.frozen_ood_rate == pytest.approx(float(np.mean(
        model.gp.is_ood(Xt))))
    assert json.loads(bp.read_text())["wh_per_nm"]["frozen_ood_rate"] == (
        pytest.approx(rep.frozen_ood_rate))


# ---------------------------------------------------------------------------
# D3 / D4 — the mark, and what it is a mark OF
# ---------------------------------------------------------------------------

def test_the_committed_baseline_is_reproducible_and_says_which_suite_it_is():
    """D3. The file exists and is tracked; this asserts it is REPRODUCIBLE and
    SELF-DESCRIBING, which is what makes it a baseline rather than a magic
    number. Every metric in it was computed by the deployment gate itself
    (`scripts/make_baseline.py` runs the real path); re-running that script on
    this machine reproduced `median_rel_err` for all three quantities to the
    last digit — 0.10446180024836133 for wh_per_nm.

    The fingerprint is the field D4 needs: a mark is only comparable to a
    metric measured on the SAME benchmark, and `"suite": "frozen_suite"` is a
    constant string that is true of every suite this code can produce.
    """
    base = json.loads(_COMMITTED.read_text())
    for q in ("wh_per_nm", "gm", "rt"):
        assert q in base, f"the committed baseline has no mark for {q}"
        row = base[q]
        for key in ("suite_fingerprint", "n_frozen", "best_median_rel_err",
                    "best_coverage_2sigma", "best_wall_clock_s", "transform"):
            assert key in row, f"{q} baseline has no {key}"
        X, _y, labels = F.frozen_suite(MissionSpec(), q, seed=4242)
        assert row["suite_fingerprint"] == suite_fingerprint(X, labels), (
            f"the committed mark for {q} was measured on a different frozen "
            f"suite than this code produces — regenerate it with "
            f"scripts/make_baseline.py")
        assert row["n_frozen"] == len(labels)


def test_a_mark_measured_on_a_different_benchmark_is_refused(stocked, tmp_path):
    """D4's precondition, fired on a realistic input: one benchmark probe stops
    being part of the suite.

    Dropping `wigley_like_proportions` takes the suite from 27 points to 26.
    MEASURED at two training sizes, because the size of the move is not the
    point and quoting one number would overstate the case:

        harvest            median_rel_err        move
        60 hulls, seed 7   0.102623 -> 0.102540  -0.08%
        120 hulls, seed 21 0.104462 -> 0.098547  -5.66%   (THIS fixture)

    Neither is anywhere near the 1.25 tolerance, and the second moves in the
    PASSING direction — a smaller benchmark made the model look better. The
    error gate cannot see this in either direction, so the fingerprint is what
    has to refuse, and it says which suite it expected.
    """
    prov, m, _d = stocked
    bp = tmp_path / "baselines.json"
    shutil.copy(_COMMITTED, bp)
    good, rep = retrain(prov, m, "wh_per_nm", baseline_path=bp)
    assert good is not None and not rep.suite_mismatch

    saved = dict(F.BENCHMARK_PROBES)
    F.BENCHMARK_PROBES.pop("wigley_like_proportions")
    try:
        model, rep2 = retrain(prov, m, "wh_per_nm", baseline_path=bp)
    finally:
        F.BENCHMARK_PROBES.clear()
        F.BENCHMARK_PROBES.update(saved)
    assert len(rep2.labels) == len(rep.labels) - 1
    prior_best = json.loads(bp.read_text())["wh_per_nm"]["best_median_rel_err"]
    assert rep2.median_rel_err <= prior_best * 1.25, (
        "the shrunken suite moved the metric outside the tolerance, so the "
        "error gate would have caught it and this trap demonstrates nothing")
    assert model is None and rep2.suite_mismatch and not rep2.passed_gate
    assert any("not the one the baseline was measured on" in r
               for r in rep2.refusals)


def test_a_baseline_with_no_fingerprint_cannot_be_compared_and_refuses(
        tmp_path):
    """The ABSENT-metric half. A baseline written before fingerprints existed
    carries a mark nobody can show is a mark of this benchmark. Unverifiable is
    not the same as fine, and defaulting an unmeasurable precondition to 'pass'
    is gap D3 one level up — that is precisely how a missing file became an
    unconditional deploy.

    An explicit `bootstrap=True` is the deliberate way through, and it DROPS
    the incomparable prior rather than carrying its record across benchmarks.
    """
    bp = tmp_path / "baselines.json"
    legacy = {"wh_per_nm": {"median_rel_err": 0.10, "coverage_2sigma": 0.95,
                            "best_median_rel_err": 0.10,
                            "best_coverage_2sigma": 0.95}}
    bp.write_text(json.dumps(legacy))
    with mock.patch.object(F, "_metrics", return_value=(0.11, 0.95)), \
         mock.patch.object(F, "frozen_suite", return_value=(None, None, [])), \
         mock.patch.object(F.GP, "fit", staticmethod(lambda *a, **k: object())):
        model, rep = retrain(_stub_prov(), None, baseline_path=bp)
        assert model is None and not rep.passed_gate
        assert any("NOT RECORDED" in r for r in rep.refusals)

        model2, rep2 = retrain(_stub_prov(), None, baseline_path=bp,
                               bootstrap=True)
        assert model2 is not None and rep2.passed_gate
        assert "re-baselined" in rep2.rebaselined
    row = json.loads(bp.read_text())["wh_per_nm"]
    assert row["best_median_rel_err"] == 0.11, (
        "the 0.10 record was measured on another benchmark and must not be "
        "carried into this one")


def _stub_prov():
    class P:
        def training_matrix(self, *_a):
            return np.zeros((30, 15)), np.ones(30)
    return P()


def test_the_floor_and_the_ratchet_each_catch_what_the_other_cannot(tmp_path):
    """D4, stated as the reason BOTH exist.

    `tests/test_phase7.py` fences the ten-retrain downhill walk. This one
    fences the two single cases that decide the design:

      - 0.10 -> 0.34 is a 3.4x degradation that NEVER trips the 0.35 floor.
        Only a high-water mark sees it, which is why the gate has one.
      - 0.36 on a bootstrap has no history to ratchet against at all. Only the
        floor sees it, which is why the ratchet did not replace it.
      - a metric that could not be computed (nan) is refused by both, because
        an unmeasurable number is never a pass.
    """
    bp = tmp_path / "b.json"
    fp = suite_fingerprint(None, [])          # the stubbed suite's fingerprint
    good = {"wh_per_nm": {"median_rel_err": 0.10, "coverage_2sigma": 0.95,
                          "best_median_rel_err": 0.10,
                          "best_coverage_2sigma": 0.95,
                          "suite_fingerprint": fp}}

    def run(med, cov, **kw):
        with mock.patch.object(F, "_metrics", return_value=(med, cov)), \
             mock.patch.object(F, "frozen_suite",
                               return_value=(None, None, [])), \
             mock.patch.object(F.GP, "fit",
                               staticmethod(lambda *a, **k: object())):
            return retrain(_stub_prov(), None, baseline_path=bp, **kw)

    bp.write_text(json.dumps(good))
    assert 0.34 < F.HARD_MAX_MEDIAN_REL_ERR, "this trap needs 0.34 to be legal"
    model, rep = run(0.34, 0.95)
    assert model is None and not rep.passed_gate
    assert any("best ever recorded" in r for r in rep.refusals)

    bp.write_text("{}")
    model, rep = run(F.HARD_MAX_MEDIAN_REL_ERR * 1.03, 0.95, bootstrap=True)
    assert model is None and not rep.passed_gate
    assert any("absolute floor" in r for r in rep.refusals)

    for med, cov in ((float("nan"), 0.95), (0.10, float("nan"))):
        bp.write_text(json.dumps(good))
        model, rep = run(med, cov)
        assert model is None and not rep.passed_gate, (
            f"a model whose metrics are ({med}, {cov}) DEPLOYED — an "
            f"unmeasurable metric must never default to a passing value")


def test_the_deployment_gate_refuses_a_benchmark_whose_physics_moved(stocked,
                                                                     tmp_path):
    """`benchmark_integrity()` existed, was tested once, and had NO production
    caller — the same shape as A4, in the module that depends on it. A gate
    measured against a moving benchmark cannot fail honestly, so `retrain` now
    calls it first (0.079 s, outside the timed region so `wall_clock_s` still
    means the retrain).

    Fired on a realistic input: the Wigley Michell Cw reference shifted by 10%,
    which is what a change to the resistance code looks like from here. Note
    the fingerprint does NOT catch this — it hashes the probe COORDINATES, so
    the physics needs its own guard, and this is it.
    """
    import benchmarks.wigley as W

    prov, m, _d = stocked
    bp = tmp_path / "baselines.json"
    shutil.copy(_COMMITTED, bp)
    moved = {fn: cw * 1.10 for fn, cw in W.REFERENCE_CW.items()}
    with mock.patch.object(W, "REFERENCE_CW", moved):
        with pytest.raises(AssertionError, match="NOT frozen"):
            retrain(prov, m, "wh_per_nm", baseline_path=bp)


# ---------------------------------------------------------------------------
# D11 — feasibility is a property of the MODEL
# ---------------------------------------------------------------------------

def test_feasibility_measured_on_the_sampler_is_100_percent_by_construction():
    """D11's negative control, and the thing the register row is about.

    `sample()` has `grammar.check` INSIDE its rejection loop, so a feasibility
    rate read off its output is 1.0 for ANY proposal distribution whatsoever —
    it measures the loop, not the model, and Gate 4's >=99% bar was reading it.
    `raw_feasibility()` asks the model.

    MEASURED on a generator fit to `sample_valid(120, MissionSpec(), seed=11)`,
    300 sampled draws and `raw_feasibility(600, seed=0)`:

        implementation   sampler loop   raw model
        GMM                 100.00%       79.33%
        pPCA                100.00%       88.67%

    Both are far below the 99% bar, and the pPCA latent already in the repo
    beats the model shipped as the generative one. `tests/test_phase4.py`
    asserts the honest number; this asserts that the two ways of measuring it
    are DIFFERENT, so a future edit cannot quietly point the bar back at the
    tautology.
    """
    X, _y = sample_valid(120, MissionSpec(), seed=11)
    for kind in ("gmm", "ppca"):
        g = make_generator(X, kind=kind, seed=1)
        drawn = g.sample(300, seed=0)
        sampler_rate = float(np.mean([grammar.check(x).ok for x in drawn]))
        model_rate = g.raw_feasibility(600, seed=0)
        assert sampler_rate == 1.0, (
            f"{kind}: sample() returned an infeasible hull — that is a real "
            f"bug, but it also means this control no longer demonstrates the "
            f"tautology")
        assert model_rate < sampler_rate - 0.05, (
            f"{kind}: raw model feasibility {model_rate:.2%} has caught up with "
            f"the sampler loop. If that is real it is excellent news and Gate "
            f"4's scope line must be re-measured; if it is not, the metric has "
            f"been re-pointed at the rejection loop.")
        assert model_rate < 0.99, (
            f"{kind}: raw feasibility {model_rate:.2%} now clears the 99% bar — "
            f"re-measure Gate 4's scope line before believing it")
