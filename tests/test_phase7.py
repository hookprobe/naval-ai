"""Gate 7: harvest feeds provenance, retrain deploys only when the frozen
benchmark does not degrade, corrupted models are refused."""

import json
import pathlib

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


# ---------------------------------------------------------------------------
# I11 — the "frozen benchmark" was the TRAINING DISTRIBUTION
# ---------------------------------------------------------------------------

def test_the_frozen_suite_is_not_the_training_draw(stocked):
    """It was `sample_valid(25, mission, seed=4242)` — the SAME generator over
    the SAME box as training, with a different seed. Every point was
    interpolation, so a model that had quietly specialised on the middle of the
    box scored exactly as well on it as an honest one, and the gate could not
    see distribution shift at all. `benchmarks/` was never imported by this
    module while README and PLM described the frozen suite as being built from
    the plan's KCS/JBC/5415 anchors.

    The suite now has two arms, both fixed forever:
      - hulls carrying a PUBLISHED hull's proportions (`BENCHMARK_PROBES`),
        whose coordinates come from a paper and therefore cannot drift;
      - hulls from a design-space wedge that `harvest()` refuses to train on.

    MEASURED: the suite is 27 points, 2 benchmark + 25 held-out region; uniform
    L0-feasible sampling lands in that wedge 1.3% of the time, and with
    `exclude_heldout` the 60 harvested training rows contain ZERO of them.
    """
    from navalai.flywheel import (BENCHMARK_PROBES, frozen_suite,
                                  in_heldout_region)

    prov, m, _d, _n = stocked
    X, y, labels = frozen_suite(m)
    assert len(X) == len(y) == len(labels) >= 20
    assert np.isfinite(y).all()

    bench = [ell for ell in labels if ell.startswith("benchmark:")]
    assert len(bench) == len(BENCHMARK_PROBES), labels
    assert not any("REJECTED" in ell or "NO_L1" in ell for ell in bench), (
        f"a benchmark probe stopped being L0-legal: {bench}")

    region = np.array([ell == "heldout_region" for ell in labels])
    assert region.sum() >= 20
    assert in_heldout_region(X[region]).all()

    # ...and the training data must not be in the held-out region, or "held
    # out" is a word rather than a fact.
    Xtr, _ytr = prov.training_matrix("L1", "wh_per_nm")
    assert in_heldout_region(Xtr).sum() == 0, (
        f"{in_heldout_region(Xtr).sum()} training rows sit inside the "
        f"benchmark's held-out wedge")


def test_the_benchmark_itself_is_checked_for_drift():
    """A benchmark whose own truth moves is not a benchmark. `REFERENCE_CW` in
    benchmarks/wigley.py is a Michell wave-resistance curve on a converged
    grid; `benchmark_integrity()` recomputes it and refuses if the physics
    underneath has drifted. MEASURED: 0.000% deviation at all seven Froude
    numbers, in 0.07 s — cheap enough to run on every retrain."""
    from navalai.flywheel import benchmark_integrity

    dev = benchmark_integrity()
    assert len(dev) >= 5
    assert max(dev.values()) < 0.02, dev


# ---------------------------------------------------------------------------
# I12 — `log` of a signed quantity
# ---------------------------------------------------------------------------

def test_gm_is_not_log_transformed(stocked):
    """`retrain` did `GP.fit(X, np.log(y))` unconditionally and `_find_q`
    explicitly advertises the `"gm"` path. GM is SIGNED — a negative
    metacentric height is a boat that capsizes, which is exactly the region a
    stability surrogate must represent.

    MEASURED over the 60 harvested hulls in this fixture: min GM = -0.983 m
    with 22 of 60 negative, so `np.log` produced 22 NaNs and the failure
    surfaced (if at all) as a Cholesky error several frames away. (Under the
    gap-E6 grammar the same seed draws 17 of 60 negative, not 22 — the count
    moves with the feasible set, the defect does not.)

    The relative-error METRIC is signed too: |pred - y| / |y| is unbounded at
    the zero crossing, so an identity-transformed quantity is scored in units
    of the target's own spread and `RetrainReport.err_kind` says which number
    a reader is holding. MEASURED on this fixture: GM read 0.369 as a
    "relative" error, dominated by points near GM = 0, against 0.224 as a
    spread-normalised one.

    THIS TEST NO LONGER ASSERTS THAT THE MODEL DEPLOYS, AND THE REASON IS A
    MEASUREMENT, NOT A CONCESSION. It used to end `assert gp is not None`,
    which is a claim about the DEPLOYMENT GATE (median spread-normalised error
    <= HARD_MAX_MEDIAN_REL_ERR = 0.35) and not about the transform this test is
    named for. That claim held on exactly one draw. MEASURED 2026-08-07 —
    identical code, only `harvest(60, ..., seed=S)` varying, scored on the same
    frozen suite:

        harvest seed   21     1     2     3     5     7    11    13    17    23
        pre-E6 grammar 0.224 0.560 0.905 0.424 0.355 0.564 0.508 0.704 0.540 0.484
        E6 grammar     0.416 0.990 0.827 0.689 0.829 0.441 0.469 0.472 0.451 0.449

    Against the 0.35 floor that is 9 of 10 refused before gap E6 and 10 of 10
    after. Seed 21 was the single ticket that paid, and this fixture holds it.
    E6 did not break the GM surrogate — its median over the ten seeds is
    0.470 against pre-E6's 0.524, i.e. slightly BETTER — it removed a lottery
    win, and the property "60 harvested hulls train a deployable GM surrogate"
    was never true. Register section T records the same defect one level down
    (a bar pinned at the luckiest seed); this is that defect pinned at the
    luckiest DRAW.

    The floor is not moved and the fixture is not grown to chase the number:
    at n=120 (what `scripts/make_baseline.py` uses) seed 21 reads 0.252 and
    deploys while 5 of the same 10 seeds still refuse, so a bigger harvest
    would re-pin the same lottery one size up. The refusal is recorded in
    `data/gate-ledger.json` instead, and what this test asserts is what it was
    always about: nothing in the GM path is a NaN, the transform is identity,
    the metric says which kind of number it is, and if the gate refuses it
    refuses for the ERROR FLOOR rather than for a silent numerical failure.
    """
    from navalai.flywheel import (HARD_MAX_MEDIAN_REL_ERR, NonPositiveTarget,
                                  transform_for)

    prov, m, d, _n = stocked
    _X, ygm = prov.training_matrix("L1", "GM_m")
    assert (ygm <= 0).sum() > 0, (
        "no negative GM in the harvest; this trap needs a fixture that has one")

    tf = transform_for("gm")
    assert tf.name == "identity"
    with pytest.raises(NonPositiveTarget, match="signed quantity"):
        transform_for("wh_per_nm").fwd(ygm)
    # THE DEFECT ITSELF: the targets the GP is handed must all be numbers.
    # `np.log(ygm)` is NaN on every non-positive row; the identity transform
    # is finite on all 60.
    assert np.isfinite(tf.fwd(ygm)).all()
    assert np.isnan(np.log(np.where(ygm > 0, ygm, np.nan))).sum() == (ygm <= 0).sum()

    gp, rep = retrain(prov, m, "gm", baseline_path=d / "gm.json", bootstrap=True)
    assert rep.transform == "identity" and rep.err_kind == "spread-normalised"
    assert np.isfinite(rep.median_rel_err) and np.isfinite(rep.coverage_2sigma)
    if gp is None:
        # Refused. It must be the ERROR FLOOR that refused it — a Cholesky
        # blow-up or a NaN metric arriving here as "not deployed" is the I12
        # failure wearing the gate's clothes, and that is what this branch
        # exists to tell apart.
        assert rep.median_rel_err > HARD_MAX_MEDIAN_REL_ERR, rep.refusals
        assert any("absolute floor" in r for r in rep.refusals), rep.refusals
        assert len(rep.refusals) == 1, rep.refusals
    else:
        assert np.isfinite(gp.predict(np.atleast_2d(_X[:3]))[0]).all()


# ---------------------------------------------------------------------------
# I10 — Gate 7's SECOND clause was never built
# ---------------------------------------------------------------------------

def test_retrain_records_its_wall_clock_and_gates_on_it(stocked, tmp_path):
    """Gate 7's bar is "surrogate error decreases release-over-release AND full
    mission -> validated-hull wall-clock drops with each cycle". The only
    `time.` in this module was a JSON timestamp, `RetrainReport` had no timing
    field, and no test asserted one — half of Gate 7 was unbuilt while the gate
    reported GREEN.

    MEASURED on this fixture: a retrain is 0.60 s and the recorded baseline now
    carries `wall_clock_s` / `best_wall_clock_s` beside the error metrics. The
    tolerance is 3x rather than something tight, because this Mac thermally
    throttles (CLAUDE.md records a Thermal Emergency Sleep mid-campaign) and a
    bar that machine weather can trip is a bar people learn to ignore.
    """
    prov, m, _d, _n = stocked
    bp = tmp_path / "wall.json"
    gp, rep = retrain(prov, m, "wh_per_nm", baseline_path=bp, bootstrap=True)
    assert gp is not None and rep.passed_gate
    assert rep.wall_clock_s > 0.0 and np.isfinite(rep.wall_clock_s)
    assert rep.wall_clock_regressed is False
    base = json.loads(bp.read_text())["wh_per_nm"]
    assert base["wall_clock_s"] > 0 and base["best_wall_clock_s"] > 0
    assert base["suite"] == "frozen_suite"

    # A retrain that got much slower does not deploy, even with good metrics.
    base["best_wall_clock_s"] = rep.wall_clock_s / 100.0
    bp.write_text(json.dumps({"wh_per_nm": base}))
    gp2, rep2 = retrain(prov, m, "wh_per_nm", baseline_path=bp)
    assert rep2.wall_clock_regressed is True
    assert gp2 is None and not rep2.passed_gate


def test_the_mission_to_validated_hull_cycle_is_timed():
    """The second half of Gate 7's clause 2: the timed path is the PRODUCT's
    path — parse a mission in natural language, search, and put the winner
    through the ladder until it validates. MEASURED at the small fixed budget
    used here: 0.25 s total (parse 0.3 ms, search 0.20 s over 48 evaluations,
    validate 53 ms), returning an L1-validated hull.

    The budget is fixed on purpose. This number is a REGRESSION detector, and
    two runs at different budgets compare nothing.
    """
    from navalai.flywheel import cycle_time

    c = cycle_time()
    assert c["validated"] is True and c["tier"] == "L1"
    assert c["params"] is not None and len(c["params"]) == 15
    assert c["total_s"] > 0
    assert c["parse_s"] + c["search_s"] + c["validate_s"] == pytest.approx(
        c["total_s"], rel=1e-6)
    assert c["n_evals"] > 0


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
             mock.patch.object(F, "frozen_suite", return_value=(None, None, [])), \
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
         mock.patch.object(F, "frozen_suite", return_value=(None, None, [])), \
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
         mock.patch.object(F, "frozen_suite", return_value=(None, None, [])), \
         mock.patch.object(F.GP, "fit", staticmethod(lambda *a, **k: object())):
        with pytest.raises(FileNotFoundError, match="frozen benchmark"):
            F.retrain(_stub_prov(), None, baseline_path=missing)
        # ...but an explicit bootstrap is allowed, and still honours the floors
        _gp, rep = F.retrain(_stub_prov(), None, baseline_path=missing,
                             bootstrap=True)
        assert rep.passed_gate is False, "0.407 is above the absolute floor"


# ---------------------------------------------------------------------------
# D3, the other half — the mechanism was fixed and the artefact was missing
# ---------------------------------------------------------------------------

def test_the_committed_baseline_exists_and_can_refuse_a_poisoned_model(tmp_path):
    """Making a missing baseline a REFUSAL closed the hole above and opened a
    different one: with no committed `data/baselines.json`, the flywheel could
    not deploy on ANY clone. The register recorded the mechanism as fixed while
    the plan's other half was undone.

    The file is now generated by `scripts/make_baseline.py`, which runs the
    REAL path — a seeded harvest into a throwaway provenance DB, then
    `retrain(..., bootstrap=True)`. No metric in it was written by hand, which
    is the only kind of baseline that means anything.

    MEASURED against the committed file, from an INDEPENDENT harvest (seed 7,
    60 hulls, against the file's own seed 21 / 120):

        honest retrain    median rel err 0.1026 vs best 0.1045   DEPLOYED
        label-shuffled    median rel err 0.7251                  REFUSED

    The second row is the D3 proof-of-concept verbatim — the poisoned model
    that used to deploy and become the eternal reference.
    """
    import shutil

    root = pathlib.Path(__file__).resolve().parents[1]
    committed = root / "data" / "baselines.json"
    assert committed.exists(), (
        "data/baselines.json is missing: retrain refuses without it, so the "
        "flywheel cannot deploy on this clone. Run scripts/make_baseline.py")
    base = json.loads(committed.read_text())
    assert "wh_per_nm" in base
    for key in ("best_median_rel_err", "best_coverage_2sigma",
                "best_wall_clock_s", "n_train", "suite", "transform"):
        assert key in base["wh_per_nm"], f"baseline has no {key}"
    # it says how it was made and how to remake it, or it is a magic number
    assert "scripts/make_baseline.py" in base["_README"]["regenerate"]

    bp = tmp_path / "baselines.json"
    shutil.copy(committed, bp)
    prov = db.Provenance(tmp_path / "p.sqlite3")
    m = MissionSpec()
    harvest(60, m, prov, seed=7)

    gp, rep = retrain(prov, m, "wh_per_nm", baseline_path=bp)
    assert gp is not None and rep.passed_gate, (
        f"an honest retrain no longer clears the committed baseline "
        f"({rep.median_rel_err:.4f} vs {rep.baseline.get('best_median_rel_err')})")

    real_fit = GP.fit
    rng = np.random.default_rng(5)
    try:
        GP.fit = staticmethod(
            lambda X, y, **k: real_fit(X, rng.permutation(np.asarray(y)), **k))
        gp2, rep2 = retrain(prov, m, "wh_per_nm", baseline_path=bp)
    finally:
        GP.fit = real_fit
    assert gp2 is None and not rep2.passed_gate, (
        f"a label-shuffled model DEPLOYED against the committed baseline "
        f"(median rel err {rep2.median_rel_err:.4f})")
