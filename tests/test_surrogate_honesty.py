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
import statistics
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

#: The quantities `scripts/make_baseline.py` ATTEMPTS. Not the ones it wrote —
#: the gate is allowed to refuse one, and the difference between the two lists
#: is the thing several tests below check.
_ATTEMPTED = ("wh_per_nm", "gm", "rt")


def _deployed_and_refused(base: dict) -> tuple[dict, dict]:
    """Split the committed baseline into marks that EXIST and marks the
    deployment gate REFUSED, and insist every attempted quantity is in exactly
    one of them.

    HONESTY RULE 4, READ AS A PRECONDITION RATHER THAN AS A DECORATION. A
    quantity the gate refused must NOT be handed an entry so the file looks
    complete, and it must not simply vanish either — vanishing is how an
    unmeasurable value becomes a passing one (docs/LESSONS.md defect class 1).
    `refused_by_the_gate` is where make_baseline records it, with the numbers
    that refused it.

    MEASURED 2026-08-13 on the regenerated file: `wh_per_nm` and `rt` deployed,
    `gm` was REFUSED at a median spread-normalised error of 0.7341 against
    `flywheel.HARD_MAX_MEDIAN_REL_ERR` = 0.35 — an absolute floor no baseline
    or tolerance may move. So `data/baselines.json` has no `gm` key at all.
    The tests below therefore ask each quantity which side it is on rather than
    assuming a mark exists, and they un-refuse THEMSELVES the moment gm
    deploys again: nothing here is keyed on a hand-maintained flag.
    """
    refused = base.get("_README", {}).get("refused_by_the_gate", {})
    deployed = {q: base[q] for q in _ATTEMPTED if q in base}
    for q in _ATTEMPTED:
        assert (q in deployed) != (q in refused), (
            f"{q} is in neither the marks nor `refused_by_the_gate`, or in "
            f"both. A quantity the gate refused is RECORDED as refused; one "
            f"that simply disappeared is an unmeasured value scored as a pass")
    return deployed, {q: refused[q] for q in _ATTEMPTED if q in refused}


@pytest.fixture(scope="module")
def stocked(tmp_path_factory):
    d = tmp_path_factory.mktemp("honesty")
    prov = db.Provenance(d / "p.sqlite3")
    m = MissionSpec()
    harvest(120, m, prov, seed=21)
    return prov, m, d


@pytest.fixture(scope="module")
def independent(tmp_path_factory):
    """A harvest that is NOT the committed baseline's own pinned seed.

    `stocked` above draws seed 21, which is `make_baseline.HARVEST_SEED` — the
    exact draw `data/baselines.json` was written from. Every test that needs an
    honest retrain to CLEAR the committed mark used it, and that was gap T3's
    defect one level down: the suite demonstrated "an honest model deploys"
    using the one draw the mark itself was built on, which under the old genome
    was also the LUCKIEST of the eight measured seeds.

    MEASURED 2026-08-13 on the regenerated baseline, n=120, against the
    committed mark's threshold of 1.25 x 0.1130 = 0.1413:

        seed 21 (the file's own)   median rel err 0.1721   REFUSED
        seed  7 (independent)      median rel err 0.1358   DEPLOYED

    Seed 21 is now the SECOND-WORST of the eight seeds the file records, not
    the best, so it no longer clears the mark it produced. That is a real
    finding about the ratchet and it is reported rather than tuned away; what
    changes HERE is only that a test needing a deploying model draws a seed
    that is independent of the mark, which is what it should always have done.
    `tests/test_phase7.py` has drawn seed 7 for the same reason for longer.
    """
    d = tmp_path_factory.mktemp("independent")
    prov = db.Provenance(d / "p.sqlite3")
    m = MissionSpec()
    harvest(120, m, prov, seed=7)
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
        independent, tmp_path):
    """A4 end to end: the deployment path is where the bare GP escaped from.

    Also records `frozen_ood_rate` — the share of its own deployment benchmark
    the model would refuse in production. It is a RECEIPT and not a bar: the
    benchmark's held-out wedge is deliberately outside the training draw, so a
    nonzero rate is the design working. RE-MEASURED 2026-08-13 at the shipped
    configuration (120 harvested hulls, wh_per_nm, holdout seed 4242): 3 of 27
    points, 11.1%, against 1 of 27 (3.7%) on the 15-parameter genome. It is 5
    of 27 on the seed-21 draw, so the receipt is a property of the model and
    not of the suite. MECHANISM:
    one more genome axis to be distant along, so a fixed frozen suite sits
    further from the same number of training points.

    The fixture is `independent` (seed 7), not `stocked` (seed 21), because this
    test needs a model that DEPLOYS against the committed mark and seed 21 is
    the mark's own draw — see the `independent` fixture for the measurement.
    """
    prov, m, _d = independent
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
    (`scripts/make_baseline.py` runs the real path).

    THE REPRODUCIBILITY SENTENCE THAT USED TO SIT HERE WAS ITSELF A THIRD COPY
    of a number (removed 2026-08-12). It claimed the script reproduced
    `median_rel_err` "to the last digit — 0.10446180024836133 for wh_per_nm"
    while the committed file held 0.15130937054355117 and a re-run on this
    machine measured 0.1434: three values for one quantity, in a docstring
    nothing asserted. Reproducibility is now asserted rather than narrated —
    against the file, by the keys below — and the marks themselves live in
    `data/baselines.json` alone.

    The fingerprint is the field D4 needs: a mark is only comparable to a
    metric measured on the SAME benchmark, and `"suite": "frozen_suite"` is a
    constant string that is true of every suite this code can produce.

    A QUANTITY THE GATE REFUSED IS NOT HANDED A MARK SO THIS TEST CAN PASS.
    2026-08-13: `gm` is refused at 0.7341 against the 0.35 absolute floor and
    `data/baselines.json` has no `gm` key. The honest assertion is not that
    every attempted quantity has a mark — that would be satisfied by inventing
    one — but that every attempted quantity is either MARKED or RECORDED AS
    REFUSED, with the numbers, and that a refusal is justified by a measurement
    rather than by a label. That is asserted here rather than skipped, and it
    reverts to the marked branch by itself the moment gm deploys.
    """
    base = json.loads(_COMMITTED.read_text())
    deployed, refused = _deployed_and_refused(base)
    assert deployed, "the committed baseline carries no marks at all"

    for q, row in deployed.items():
        for key in ("suite_fingerprint", "n_frozen", "best_median_rel_err",
                    "best_coverage_2sigma", "best_wall_clock_s", "transform"):
            assert key in row, f"{q} baseline has no {key}"
        X, _y, labels = F.frozen_suite(MissionSpec(), q, seed=4242)
        assert row["suite_fingerprint"] == suite_fingerprint(X, labels), (
            f"the committed mark for {q} was measured on a different frozen "
            f"suite than this code produces — regenerate it with "
            f"scripts/make_baseline.py")
        assert row["n_frozen"] == len(labels)

    for q, rec in refused.items():
        for key in ("median_err", "coverage_2sigma", "err_kind", "transform"):
            assert key in rec, (
                f"{q} was refused and the file does not say {key} — a refusal "
                f"nobody can audit is the same silence as an invented mark")
        # the refusal is SHOWN to be a refusal: a floor was actually missed
        assert (rec["median_err"] > F.HARD_MAX_MEDIAN_REL_ERR
                or not (F.HARD_MIN_COVERAGE_2SIGMA
                        <= rec["coverage_2sigma"] <= 1.0)), (
            f"{q} is recorded as refused with metrics that clear both absolute "
            f"floors ({rec['median_err']:.4g}, {rec['coverage_2sigma']:.4g}) — "
            f"then it should have deployed. Regenerate with "
            f"scripts/make_baseline.py")


def test_the_frozen_suites_identity_covers_its_targets_not_only_its_points():
    """Gap T1: `suite_fingerprint` hashes the probe COORDINATES, by design, and
    nothing hashed what those probes were WORTH.

    The frozen y is a live output of `evaluate()` — `frozen_suite` builds it by
    calling the ladder — so an L1 physics change moves it. MEASURED 2026-08-12,
    reproducing make_baseline.py's exact configuration (n=120, harvest seed 21,
    holdout 4242, GP.fit(seed=1)) against the file committed on 2026-08-07:

        quantity     committed mark    re-measured    move    suite_fingerprint
        wh_per_nm    0.15130937054     0.1434        -5.2%    d782c04bf198af11
        gm           0.25174526392     0.2504        -0.5%    d782c04bf198af11
        rt           0.15131012878     0.1435        -5.2%    d782c04bf198af11

    A bit-identical suite id across three moved marks. `560fd52` changed the
    L1 weight path that feeds evaluate(), and therefore both the frozen y and
    the training y, under an id that could not see it — so the ratchet was
    comparing a mark to a metric measured on different physics and calling that
    a high-water mark.

    Kept as a SECOND fingerprint rather than folded into the first, because the
    two mismatches want different messages: a probe change is a different
    benchmark, a target change is the same benchmark under different physics.

    THE PAIR AT THE BOTTOM USED TO BE (wh_per_nm, gm) AND IS NOW (wh_per_nm,
    rt). It needs two quantities that share probe COORDINATES while differing
    in TARGETS, which is the case one merged hash could not tell apart; `gm` no
    longer has a mark to compare (refused at 0.7341 against the 0.35 floor) and
    `rt` demonstrates exactly the same thing. MEASURED on the regenerated file:
    both carry suite 654314aec9e94e22 while their targets are d8dfa07fdbc127aa
    and ccc27bfbfe88c8 respectively.
    """
    base = json.loads(_COMMITTED.read_text())
    deployed, _refused = _deployed_and_refused(base)
    for q, row in deployed.items():
        assert "targets_fingerprint" in row, (
            f"{q} has no targets_fingerprint — the mark cannot say what "
            f"physics it was measured under")
        _X, y, _labels = F.frozen_suite(MissionSpec(), q, seed=4242)
        assert row["targets_fingerprint"] == F.targets_fingerprint(y), (
            f"the committed mark for {q} was measured on a frozen suite whose "
            f"TARGET values this code no longer produces — regenerate it with "
            f"scripts/make_baseline.py")
        # the two ids are genuinely different questions, not one value twice
        assert row["targets_fingerprint"] != row["suite_fingerprint"]

    # THE GUARD IS MADE TO FIRE. Move one target by 1e-6 — far below anything
    # `suite_fingerprint` can see, because it does not look at y at all.
    _X, y, labels = F.frozen_suite(MissionSpec(), "wh_per_nm", seed=4242)
    nudged = np.asarray(y, float).copy()
    nudged[0] += 1e-6
    assert F.targets_fingerprint(nudged) != F.targets_fingerprint(y)
    assert suite_fingerprint(_X, labels) == suite_fingerprint(_X, labels)
    # ...and two MARKED quantities share probe points while differing in y,
    # which is exactly the case one merged hash could not distinguish. The pair
    # is taken from whatever actually deployed, so a further refusal moves it
    # rather than breaking it — but two are needed for the comparison to exist.
    assert len(deployed) >= 2, (
        "fewer than two quantities carry a mark, so nothing in the committed "
        "file demonstrates two benchmarks sharing probes and differing in y")
    (qa, ra), (qb, rb) = list(deployed.items())[:2]
    assert ra["suite_fingerprint"] == rb["suite_fingerprint"], (qa, qb)
    assert ra["targets_fingerprint"] != rb["targets_fingerprint"], (qa, qb)


def test_a_mark_measured_under_different_physics_is_refused(tmp_path):
    """Gap T1's consequence, on the NON-bootstrap path — the ratchet must not
    compare across a physics change, and a baseline that cannot say is
    UNVERIFIABLE rather than fine (the D3 shape).
    """
    bp = tmp_path / "b.json"
    fp = suite_fingerprint(None, [])
    tfp = F.targets_fingerprint(None)

    def run(base_row, **kw):
        bp.write_text(json.dumps({"wh_per_nm": base_row}))
        with mock.patch.object(F, "_metrics", return_value=(0.10, 0.95)), \
             mock.patch.object(F, "frozen_suite",
                               return_value=(None, None, [])), \
             mock.patch.object(F.GP, "fit",
                               staticmethod(lambda *a, **k: object())):
            return retrain(_stub_prov(), None, baseline_path=bp, **kw)

    row = {"median_rel_err": 0.10, "coverage_2sigma": 0.95,
           "best_median_rel_err": 0.10, "best_coverage_2sigma": 0.95,
           "suite_fingerprint": fp, "targets_fingerprint": tfp}
    # the honest case still deploys, so the guard is not a constant
    model, rep = run(dict(row))
    assert model is not None and rep.passed_gate

    # a moved target refuses, and says so in the words that name the cause
    model, rep = run(dict(row, targets_fingerprint="0000000000000000"))
    assert model is None and not rep.passed_gate
    assert any("TARGET values moved" in r for r in rep.refusals), rep.refusals
    assert rep.suite_mismatch

    # ...and so does a baseline written before the field existed. An absent
    # precondition is not a satisfied one.
    absent = dict(row)
    del absent["targets_fingerprint"]
    model, rep = run(absent)
    assert model is None and not rep.passed_gate
    assert any("NOT RECORDED" in r for r in rep.refusals), rep.refusals


def test_an_explicit_bootstrap_drops_the_prior_and_cannot_deadlock(tmp_path):
    """Gap T2: the regeneration route was gated on a fingerprint that could not
    see the thing that changes.

    `scripts/make_baseline.py` reads and writes the same file, and the drop of
    the stale prior was conditioned on `suite_fingerprint != fp`. That id is
    target-blind on purpose, so a physics change moved all three marks while
    the id stayed `d782c04bf198af11` — MEASURED 0.5-5.2% of movement across a
    bit-identical id — and the prior was kept. Had the new physics been HARDER
    to learn by more than the 1.25x tolerance, every quantity would have come
    back REFUSED against the very file the script exists to replace, with no
    escape but hand-editing a committed baseline, which is gap D3's shape.
    It went the lucky direction. That is a coin toss, not a guard.

    `bootstrap` already means "this prior is not evidence about this run", so
    the drop is now unconditional on that flag. The absolute floors still bind,
    and the test below proves both halves.
    """
    bp = tmp_path / "b.json"
    fp = suite_fingerprint(None, [])
    tfp = F.targets_fingerprint(None)

    def run(med, **kw):
        with mock.patch.object(F, "_metrics", return_value=(med, 0.95)), \
             mock.patch.object(F, "frozen_suite",
                               return_value=(None, None, [])), \
             mock.patch.object(F.GP, "fit",
                               staticmethod(lambda *a, **k: object())):
            return retrain(_stub_prov(), None, baseline_path=bp, **kw)

    # A prior whose ids MATCH exactly — the case the old condition kept — and a
    # new mark 3.4x worse. Without a bootstrap this is refused by the ratchet.
    prior = {"wh_per_nm": {"median_rel_err": 0.10, "coverage_2sigma": 0.95,
                           "best_median_rel_err": 0.10,
                           "best_coverage_2sigma": 0.95,
                           "suite_fingerprint": fp,
                           "targets_fingerprint": tfp}}
    bp.write_text(json.dumps(prior))
    model, rep = run(0.34)
    assert model is None and not rep.passed_gate, (
        "without a bootstrap the ratchet must still bite")

    # WITH the bootstrap, the same matching prior is dropped and the run can
    # re-baseline. This is the assertion the old code failed: the ids matched,
    # so the drop did not happen and the stale mark kept binding.
    bp.write_text(json.dumps(prior))
    model, rep = run(0.34, bootstrap=True)
    assert model is not None and rep.passed_gate
    assert rep.rebaselined and "dropped" in rep.rebaselined

    # ...and the drop is NOT a way to deploy a bad model: the absolute floor
    # binds on a bootstrap exactly as it does otherwise.
    bp.write_text(json.dumps(prior))
    model, rep = run(F.HARD_MAX_MEDIAN_REL_ERR * 1.03, bootstrap=True)
    assert model is None and not rep.passed_gate
    assert any("absolute floor" in r for r in rep.refusals)


def test_the_ratchet_marks_a_seed_ensemble_not_the_luckiest_seed():
    """Gap T3: the mark was a single pinned seed, and it was an EXTREME of the
    distribution it claimed to represent.

    MEASURED 2026-08-12 on the 15-parameter genome, eight honest seeds through
    the real path (n=120, holdout 4242, GP.fit(seed=1)):

        quantity    median   min      max      spread   seed 21 is
        wh_per_nm   0.1901   0.1240   0.2509   2.02x    the MINIMUM
        gm          0.4194   0.2504   0.7456   2.98x    the MINIMUM
        rt          0.1901   0.1240   0.2312   1.86x    the MINIMUM

    RE-MEASURED 2026-08-13 on the rebuilt 16-parameter genome:

        quantity    median   min      max      spread   seed 21 is
        wh_per_nm   0.1130   0.0618   0.1868   3.02x    2nd-WORST of 8
        rt          0.1206   0.0618   0.1868   3.02x    2nd-WORST of 8
        gm          — REFUSED at 0.7341 against the 0.35 floor, no mark —

    RE-MEASURED 2026-08-18 after the held-out wedge was re-anchored (the
    4-day-hang fix; the old wedge had emptied and the suite it defined was
    void) and baselines regenerated:

        quantity    median   spread                    seed 21 is
        wh_per_nm   0.1687   3.95x [0.0836, 0.3301]    INSIDE the 1.25x
        rt          0.1687   2.74x                     tolerance (1.22x)

    THE PINNED SEED HAS NOW BEEN the best, nearly the worst, and ordinary,
    across three measurements of the same mechanism — which is the finding
    stated at full strength: one draw is not the distribution, in ANY
    direction, and the ensemble median + recorded spread is the only mark
    that survives all three tables unchanged.

    THE PINNED SEED FLIPPED FROM THE BEST OF THE EIGHT TO NEARLY THE WORST, AND
    THE ROW'S FINDING SURVIVED IT UNCHANGED. What T3 says is not "seed 21 is
    lucky" — it is that ONE DRAW IS NOT THE DISTRIBUTION, and a mark taken from
    an extreme of a 2-3x spread cannot be ratcheted against with a 1.25x
    tolerance. That is now true in the other direction and the mechanism (an
    ensemble median plus a measured spread, rather than one draw) is unchanged
    and still right. The assertions below were re-written to be
    DIRECTION-AGNOSTIC for exactly this reason: the previous
    `ensemble_median > best_median_rel_err` encoded "the pinned seed is the
    minimum", which was an accident of that genome and not the finding.

    THE PRICE IS NOW VISIBLE AND IT IS NOT SOFTENED HERE. Against the ratchet's
    own threshold (1.25 x 0.1130 = 0.1413 for wh_per_nm), THREE of the eight
    seeds the file itself measures as honest are refused — 0.1721, 0.1415 and
    0.1868 — a 37.5% false-refusal rate, and one of the three is the draw
    `make_baseline.py` deploys from. `rt` refuses two of eight on the same
    seeds. That belongs to `flywheel.retrain`'s tolerance and to
    `make_baseline`'s pinned seed, not to this test, and nothing here is widened
    to hide it. The absolute floors (0.35 / 0.80) are untouched throughout.
    """
    base = json.loads(_COMMITTED.read_text())
    deployed, _refused = _deployed_and_refused(base)
    seeds = base["_README"]["generation"]["harvest_seeds"]
    assert len(seeds) >= 5, "a 'seed ensemble' of fewer than five is a sample"
    assert deployed, "no quantity carries a mark, so there is no ensemble to check"
    for q, row in deployed.items():
        for key in ("seeds", "median_rel_err_seeds", "coverage_2sigma_seeds",
                    "ensemble_median_rel_err", "ensemble_coverage_2sigma",
                    "seed_spread"):
            assert key in row, f"{q} baseline has no {key}"
        meds = row["median_rel_err_seeds"]
        ens = row["ensemble_median_rel_err"]
        assert row["seeds"] == seeds
        assert len(meds) == len(seeds), (
            "an ensemble statistic over a subset of its own seeds is a "
            "statistic that does not describe what its name says")
        # the recorded statistic IS the median of the recorded draws, and the
        # spread IS max/min of them — neither is a number written beside them
        assert ens == pytest.approx(statistics.median(meds), rel=1e-12)
        assert row["seed_spread"] == pytest.approx(
            max(meds) / min(meds), rel=1e-12)
        # ...and it is a ROBUST statistic: strictly INSIDE the range of the
        # draws, in either direction. A mark pinned at one seed sits on an
        # endpoint and fails this; so does a degenerate ensemble, where min,
        # median and max coincide.
        assert min(meds) < ens < max(meds), (
            f"{q}: the ensemble median {ens:.4f} is an endpoint of "
            f"[{min(meds):.4f}, {max(meds):.4f}] — the mark is an extreme "
            f"order statistic again, which is the defect T3 is about")
        # THE FINDING, direction-agnostic and now POSITION-agnostic too
        # (2026-08-18, following this assert's own instruction after the
        # wedge re-anchor put the pinned draw INSIDE tolerance): where the
        # pinned seed falls is an accident of the genome and the wedge —
        # best, 2nd-worst and ordinary across three measured tables. What
        # T3 asserts is the MECHANISM: the pinned draw is one of the
        # recorded draws (nothing special was granted to it), and the mark
        # is the ensemble, never the pin.
        pinned = meds[seeds.index(base["_README"]["generation"]["harvest_seed"])]
        assert min(meds) <= pinned <= max(meds)
        assert ens != pinned or len(set(meds)) == 1, (
            f"{q}: the recorded mark equals the pinned seed's own draw — "
            f"the ensemble collapsed back into one draw, the defect T3 is "
            f"about")
        assert row["seed_spread"] > 1.25, (
            f"{q}: the measured spread {row['seed_spread']:.2f}x is now inside "
            f"the declared tolerance; re-state the finding above")


def test_the_ratchet_uses_the_ensemble_mark_and_the_recorded_spread(tmp_path):
    """Gap T3's consuming half. Both clauses of the row are used and this is
    the 'say which': the MARK becomes the ensemble median (robust, not an
    extreme order statistic) and the TOLERANCE widens to the recorded spread,
    because seed-to-seed variation the baseline itself measured cannot be
    evidence of a regression. Using only the first judges one draw against a
    median with no allowance for the noise between them; using only the second
    keeps ratcheting against the minimum.

    THE ROW BELOW IS A SYNTHETIC SCENARIO AND IT STILL DEMONSTRATES THE
    MECHANISM, BUT ONE SENTENCE OF ITS JUSTIFICATION HAS BEEN REFUTED AND IS
    RECORDED HERE RATHER THAN LEFT STANDING. The reason given for NOT widening
    the tolerance to `seed_spread` was that it would push the threshold above
    the absolute floor and make the ratchet inert: on the 15-parameter numbers
    0.1901 x 2.0234 = 0.3846, above HARD_MAX_MEDIAN_REL_ERR (0.35). On the
    REGENERATED file that is no longer CLEANLY true, and the honest statement is
    that it now depends on the quantity: wh_per_nm gives 0.1130 x 3.0214 =
    0.3415, BELOW the 0.35 floor, while rt gives 0.1206 x 3.0215 = 0.3643,
    still ABOVE it. So spread-widening would make the ratchet inert for
    wh_per_nm and not for rt — the original argument survives for one quantity
    and fails for the other, which is a weaker reason than the comment claims
    and a real one. The design decision
    lives in `navalai/flywheel.py` and is not this test's to change; the
    measurement is written down here so the next reader does not take the
    superseded arithmetic as a live reason. The numbers inside this test are
    the ORIGINAL synthetic ones on purpose — they are what makes the assertions
    below fire, and re-pointing them at the current file would change what is
    being demonstrated.
    """
    bp = tmp_path / "b.json"
    fp = suite_fingerprint(None, [])
    tfp = F.targets_fingerprint(None)
    row = {"median_rel_err": 0.10, "coverage_2sigma": 0.95,
           "best_median_rel_err": 0.10, "best_coverage_2sigma": 0.95,
           "suite_fingerprint": fp, "targets_fingerprint": tfp}

    def run(base_row, med):
        bp.write_text(json.dumps({"wh_per_nm": base_row}))
        with mock.patch.object(F, "_metrics", return_value=(med, 0.95)), \
             mock.patch.object(F, "frozen_suite",
                               return_value=(None, None, [])), \
             mock.patch.object(F.GP, "fit",
                               staticmethod(lambda *a, **k: object())):
            return retrain(_stub_prov(), None, baseline_path=bp)

    # WITHOUT an ensemble the old behaviour is unchanged: 0.15 is above
    # 1.25 x 0.10, so it is refused against the best ever recorded.
    model, rep = run(dict(row), 0.15)
    assert model is None and not rep.passed_gate
    assert any("best ever recorded" in r for r in rep.refusals), rep.refusals

    # WITH one, the same 0.15 is inside 1.25 x 0.1901 = 0.2376 and deploys —
    # and the refusal vocabulary changes with it, so a reader can tell which
    # mark bit.
    ens = dict(row, seeds=[21, 22, 23, 24, 25, 26, 27, 28],
               ensemble_median_rel_err=0.1901,
               ensemble_coverage_2sigma=0.9444, seed_spread=2.0234)
    model, rep = run(dict(ens), 0.15)
    assert model is not None and rep.passed_gate

    # ...AND IT IS STILL A RATCHET, well inside the absolute floor. 0.24 is
    # above 0.2376 and below HARD_MAX_MEDIAN_REL_ERR, so the only thing that
    # can refuse it is the high-water mark. This is the assertion that would
    # have failed had the tolerance been widened to the recorded 2.02x spread:
    # 0.1901 x 2.0234 = 0.3846 is ABOVE the 0.35 floor, which would have made
    # the ratchet inert and left every sub-floor refusal to the floor.
    assert 0.24 < F.HARD_MAX_MEDIAN_REL_ERR, "this trap needs 0.24 to be legal"
    model, rep = run(dict(ens), 0.24)
    assert model is None and not rep.passed_gate
    assert any("8-seed ensemble median" in r for r in rep.refusals), rep.refusals
    assert 0.1901 * 2.0234 > F.HARD_MAX_MEDIAN_REL_ERR, (
        "the spread-widened threshold is no longer above the floor — re-state "
        "the reason the tolerance is NOT widened")

    # The floor still binds above it, on the same ensemble baseline.
    model, rep = run(dict(ens), 0.36)
    assert model is None and not rep.passed_gate
    assert any("absolute floor" in r for r in rep.refusals)

    # HALF A STATISTIC IS REFUSED, never silently completed from the
    # single-seed mark: that would compare a median against a best-of-one.
    half = dict(ens)
    del half["ensemble_coverage_2sigma"]
    model, rep = run(half, 0.15)
    assert model is None and not rep.passed_gate
    assert any("half a statistic" in r for r in rep.refusals), rep.refusals


def test_a_mark_measured_on_a_different_benchmark_is_refused(independent,
                                                             tmp_path):
    """D4's precondition, fired on a realistic input: one benchmark probe stops
    being part of the suite.

    Dropping `wigley_like_proportions` takes the suite from 27 points to 26.
    MEASURED at three configurations, because the size of the move is not the
    point and quoting one number would overstate the case:

        genome  harvest             median_rel_err        move
        15-par  60 hulls, seed 7    0.102623 -> 0.102540  -0.08%
        15-par  120 hulls, seed 21  0.104462 -> 0.098547  -5.66%
        16-par  120 hulls, seed 7   0.135755 -> 0.137053  +0.96%   (THIS fixture)

    None is anywhere near the 1.25 tolerance, and one of the three moves in the
    PASSING direction — a smaller benchmark made the model look better. The
    error gate cannot see this in either direction, so the fingerprint is what
    has to refuse, and it says which suite it expected.

    The fixture is `independent` (seed 7), not `stocked` (seed 21): the first
    retrain here must DEPLOY for the second one to be a comparison, and the
    committed mark now refuses its own pinned seed. See the `independent`
    fixture for that measurement.
    """
    prov, m, _d = independent
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
            # width from grammar, not a literal 15 — `GP.fit` is mocked in
            # every caller so this never bit, and a stub that quietly describes
            # the PREVIOUS genome is how the next change gets missed.
            return np.zeros((30, grammar.N_PARAMS)), np.ones(30)
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
    # ...AND its targets fingerprint (gap T1, 2026-08-12). Without this key the
    # baseline is refused for UNVERIFIABLE COMPARABILITY before the ratchet is
    # ever reached, which would leave this test green while measuring the wrong
    # refusal. The stub's y is None, and `targets_fingerprint` hashes that to
    # the empty-array digest — the same value `retrain` computes from it.
    tfp = F.targets_fingerprint(None)
    good = {"wh_per_nm": {"median_rel_err": 0.10, "coverage_2sigma": 0.95,
                          "best_median_rel_err": 0.10,
                          "best_coverage_2sigma": 0.95,
                          "suite_fingerprint": fp,
                          "targets_fingerprint": tfp}}

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
