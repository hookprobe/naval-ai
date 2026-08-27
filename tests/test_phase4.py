"""Gate 4: generative feasibility rate, conditioning actually improves the
objective, latent map round-trip, and slider latency p95 < 100 ms.

THE SUITE IS PARAMETRISED OVER `HullGenerator`, NOT OVER ONE CLASS. PLM lists
"guided tabular diffusion behind `HullFamilyModel`" as READY, and there was no
interface to be behind: `HullFamilyModel` was a concrete dataclass of GMM/PCA
internals, a tree-wide grep for Protocol/ABC/abstractmethod in `navalai/` found
ZERO, `ui/server.py` constructed it with the GMM-specific `k`, and this file
reached into `model.X_train`. Every Gate-4 claim was therefore a claim about
one implementation. It is now a claim about the CONTRACT, checked against two
implementations (GMM and the pPCA latent already in the repo), which is the
smallest number that can tell an interface from a description.
"""

import json
import threading
import time
import urllib.request

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate, sample_valid
from navalai.generative import (DecodeInfo, HullFamilyModel, HullGenerator,
                                make_generator)
from navalai.mission import MissionSpec
from tests.test_phase0 import mid_params

KINDS = ("gmm", "ppca")

# THE REFERENCE HULL, FROM ITS ONE HOME. Three tests below built their slider
# payload as `zip(grammar.NAMES, (15 literal values))`. The geometry-kernel
# rebuild took the genome to 16 parameters and REORDERED it, so `zip` silently
# truncated to the first 15 names and dropped `sheer_rise` from the dict, while
# every remaining value landed under a name that no longer meant it: 8 and 30
# were written for beta_mid/beta_bow and arrived as `Cp = 8.0`, `lcb = 30.0`.
# The payload evaluated to tier L0 (grammar-refused), which is how a genome
# change surfaced as `assert 'L0' == 'L1'` and as `KeyError: 'sheer_rise'`.
#
# A hull spelled out in a test is a hull declared twice. `tests/test_phase0.py`
# already owns the reference hull and eleven modules import it from there; this
# file now does too, so the next genome change moves ONE literal.
_REF = grammar.named(mid_params())


@pytest.fixture(scope="module")
def train_X():
    X, _y = sample_valid(120, MissionSpec(), seed=11)
    return X


@pytest.fixture(scope="module", params=KINDS)
def model(request, train_X):
    return make_generator(train_X, kind=request.param, seed=1)


# ---------------- I8: the interface exists and both implementations meet it ----

def test_the_generator_slot_is_a_protocol_with_two_implementations(model):
    """The "drop-in upgrade slot" must be checkable, or it is a sentence in a
    document. `HullGenerator` is `@runtime_checkable`, so this asserts the
    method set rather than the class."""
    assert isinstance(model, HullGenerator)
    for name in ("sample", "sample_conditioned", "to_latent", "from_latent",
                 "raw_feasibility"):
        assert callable(getattr(model, name)), name
    # `training_data` is the property the tests used to reach past, via
    # `model.X_train`. Reaching into an implementation's field is how a test
    # suite quietly becomes single-implementation.
    assert model.training_data.shape[1] == grammar.N_PARAMS


def test_the_factory_is_the_only_place_that_names_an_implementation(train_X):
    """`ui/server.py` called `HullFamilyModel.fit(X, k=4)` and `k` is a GMM
    word — a diffusion model has no `k`, so the slot could not have been used
    without editing the server. The factory is the seam."""
    import ast

    import ui.server as S

    # Checked on the module NAMESPACE and the AST, not on the source text —
    # the docstring is allowed to name the class it stopped calling.
    assert not hasattr(S, "HullFamilyModel"), (
        "the server imports a concrete generator again; that is the slot closing")
    assert hasattr(S, "make_generator")
    tree = ast.parse(open(S.__file__).read())
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "make_generator" in called
    for concrete in ("HullFamilyModel", "PPCAGenerator"):
        assert concrete not in called, f"the server constructs {concrete} directly"

    with pytest.raises(ValueError, match="unknown generator kind"):
        make_generator(train_X, kind="diffusion")


def test_raw_feasibility_is_measured_on_the_model_not_the_sampler(model):
    """RECORDED AS RED (honesty rule 6). Gate 4's bar is >=99% feasible raw
    draws; `sample()` has `grammar.check` INSIDE its rejection loop, so
    measuring there returns 100% by construction and says nothing.

    MEASURED with `raw_feasibility`: GMM 78.2% clipped to the box (31.5%
    unclipped), pPCA 87.8%. Both are far below 99%, and the pPCA latent already
    in the repo BEATS the generative model that was shipped as the generative
    model. That is the gap the diffusion upgrade has to close, and this test
    exists to hold the honest number rather than to pass.
    """
    f = model.raw_feasibility(600, seed=0)
    assert 0.0 <= f <= 1.0
    assert f < 0.99, (
        f"raw feasibility {f:.1%} now clears the 99% bar — if that is real, "
        f"raise this gate to the bar; do not leave it recorded as RED")
    # Collapse floor 0.6 -> 0.4, RE-MEASURED 2026-08-27 at the P1 feed
    # flip: the training draw now VARIES the seven post-hoc genes
    # (explore_post_hoc=True), so the mixture attempts the full 23-gene
    # joint instead of a 16-gene one, and its raw draws leak across more
    # constraint surfaces — 47.3% after re-fairing (Cp, lcb) into the
    # deliverable bands and re-imposing the deadrise law's own ordering,
    # against 62.3% on the pinned feed. That is the measured price of a
    # model that can finally emit a full bow at all; the SERVED path
    # (`sample()`) keeps `grammar.check` inside its rejection loop and
    # stays 100% feasible by construction, and the 99% aspiration stays
    # recorded as RED at Gate 4F, whose diffusion upgrade is the real fix.
    assert f > 0.4, f"raw feasibility collapsed to {f:.1%}"


# ---------------- feasibility + conditioning ----------------

def test_generative_samples_are_feasible(model):
    X = model.sample(40, seed=2)
    ok = sum(grammar.check(x).ok for x in X)
    assert ok == 40      # the gate is IN the sampler; 100% by construction


def test_conditioning_improves_objective(model):
    """Performance knob: percentile=0.85 samples must beat the unconditioned
    mean on Wh/NM (the C-ShipGen 'guidance steers generation' property,
    demonstrated at GMM-baseline scale)."""
    m = MissionSpec()

    def score(X):
        out = []
        for x in X:
            ev = evaluate(x, m)
            out.append(ev.energy.wh_per_nm if ev.energy else 1e9)
        return np.array(out)

    base = score(model.sample(30, seed=8))
    cond = score(model.sample_conditioned(10, score, percentile=0.85, seed=9))
    assert cond.mean() < np.median(base), (
        f"conditioned {cond.mean():.0f} not better than base median {np.median(base):.0f}")


def test_percentile_is_a_strictness_knob_and_the_docstring_now_says_so(model):
    """The parameter reads one way and behaves the other. `cut =
    quantile(ref, 1 - percentile)` with `keep score <= cut` makes the KEPT
    FRACTION `1 - percentile`, so 0.85 means "the best 15%" — strict — while
    the old docstring, "keep draws whose score is in the best `percentile`",
    reads as "keep 85%". The code was right and the sentence was wrong, so the
    sentence changed; this pins the behaviour so it cannot drift to match the
    old prose.
    """
    m = MissionSpec()

    def score(X):
        out = []
        for x in X:
            ev = evaluate(x, m)
            out.append(ev.energy.wh_per_nm if ev.energy else 1e9)
        return np.array(out)

    loose = score(model.sample_conditioned(8, score, percentile=0.2, seed=12))
    strict = score(model.sample_conditioned(8, score, percentile=0.9, seed=12))
    assert strict.mean() <= loose.mean(), (
        f"higher percentile must be STRICTER: 0.9 -> {strict.mean():.0f} vs "
        f"0.2 -> {loose.mean():.0f}")


def test_conditioning_reports_when_it_could_not_finish(model):
    """`raise RuntimeError("conditioned sampler starved")` was the only exit
    when the cut could not be met — a UI widget that spins and then throws.
    A wall-clock budget now returns best-so-far with `partial` set.

    THE STARVATION IS RIGGED, DETERMINISTICALLY (2026-08-19). This used to
    score with the real ladder at percentile=1.0 and assume the candidate
    batch never beats the reference batch's minimum — a seed lottery: after
    the physics-correction campaign, the gmm's second batch contains SEVEN
    hulls better than the first batch's best (measured), the sampler filled
    n=6 legitimately and `partial=False` was TRUE reporting that the test
    then failed. A monotone score makes the cut unbeatable by construction:
    the reference batch owns the lowest scores ever issued, so no candidate
    can pass and the budget path MUST engage — on every model, every seed.
    """
    import itertools
    counter = itertools.count()

    def rigged_score(X):
        # strictly increasing across calls: ref gets 0..63, every later
        # candidate scores higher than ref's minimum -> the cut at
        # percentile=1.0 (quantile 0.0 = ref min) is unbeatable.
        return np.array([float(next(counter)) for _ in X])

    X, info = model.sample_conditioned(6, rigged_score, percentile=1.0,
                                       seed=4, time_budget_s=0.0,
                                       return_info=True)
    assert info["partial"] is True and info["n_requested"] == 6
    assert len(X) == info["n_returned"] <= 6
    for x in X:
        assert grammar.check(x).ok, "a cut-short search still returns L0 hulls"


# ---------------- I6: the GMM's covariance floor was scale-blind -------------

def test_gmm_covariance_floor_is_relative_and_starved_components_are_pruned(train_X):
    """The regulariser was a FLAT `1e-6 * I` on parameters spanning LWL in
    [4, 20] m down to rocker in [0, 0.6]. MEASURED per-dimension training
    variance ranges 6.4e-3 to 122.7 — a factor of 19,262 — so one additive
    constant is negligible on the long axes and dominant on the short ones.

    MEASURED with the old EM (flat floor, fixed 60 iterations, no pruning),
    counting eigenvalues pinned EXACTLY at the 1e-6 floor:

        n    k    min eigenvalue   at the floor   min responsibility mass
       150   4      6.18e-04         0 / 60             31.0
        60   4      1.00e-06        13 / 60             11.0
        60   8      1.00e-06        68 / 120             5.0
        60  12      1.00e-06       132 / 180             2.0

    A full covariance in d=15 needs at least d+1 = 16 points. At n=60, k=12,
    73% of the spectrum IS the regulariser: those components are rank-deficient
    and alive only because a constant was added to the diagonal. Recorded
    honestly: at the SHIPPED default (n=150, k=4) nothing was pinned, so the
    register's "the smallest eigenvalue is exactly 1e-6" is true at n=60 and
    not at the server's own configuration.

    The floor is now `1e-6 * diag(cov(X))` — the same relative jitter on every
    axis — and a component whose responsibility mass falls below d+1 is
    reseeded, then dropped if it starves again.
    """
    d = train_X.shape[1]
    var = np.diag(np.cov(train_X.T))
    assert var.max() / var.min() > 1000, (
        "the scale spread that makes a flat floor wrong has gone; re-derive")

    m = HullFamilyModel.fit(train_X, k=4, seed=1)
    assert m.converged and m.n_iter < 400, (
        f"EM ran to the iteration cap ({m.n_iter}) instead of converging")
    assert np.isfinite(m.log_likelihood)
    for c in m.covs:
        ev = np.linalg.eigvalsh(c)
        assert ev.min() > 1e-6 * var.min() * 0.5, "a component is at the floor"

    # No SURVIVING component may be estimated from fewer points than a full
    # covariance in d needs. (A lone survivor carries all n by construction.)
    for k in (4, 8, 12, 16):
        mm = HullFamilyModel.fit(train_X[:60], k=k, seed=1)
        assert len(mm.weights) >= 1
        if len(mm.weights) > 1:
            assert (mm.weights * 60).min() >= d + 1, (
                f"k={k}: a surviving component has "
                f"{(mm.weights * 60).min():.1f} points for a {d}x{d} covariance")
        assert mm.n_dropped == k - len(mm.weights)


# ---------------- I7: `from_latent` silently returned a TRAINING HULL --------

def test_latent_map_roundtrip_feasible(model):
    src = model.training_data[:10]
    uv = model.to_latent(src)
    assert uv.shape == (10, 2), "the browsable map is 2-D for every generator"
    X2 = model.from_latent(uv)
    for x in X2:
        assert grammar.check(x).ok
    # decoded hulls stay near their sources (same family)
    rel = np.linalg.norm(X2 - src, axis=1) / np.linalg.norm(
        grammar.HIGH - grammar.LOW)
    assert np.median(rel) < 0.35


def test_latent_grid_decodes_feasible(model):
    grid = np.array([[u, v] for u in (-1.5, 0.0, 1.5) for v in (-1.5, 0.0, 1.5)])
    X = model.from_latent(grid)
    assert all(grammar.check(x).ok for x in X)


def test_from_latent_declares_when_it_substituted_a_different_hull(model):
    """`from_latent` returned only hulls, and its fallback silently swapped in
    a TRAINING HULL for the point that was asked for. The product consequence
    is exact: a slider move returns the same boat, badged as the requested
    design. The old test asserted only post-projection feasibility — which the
    fallback GUARANTEES — so it could never see this.

    MEASURED on a 15x15 latent grid, GMM k=4 over n=150:

        grid extent    unprojected   EXACT training hulls returned
          +-2.0 sigma     100.0%         0 / 225
          +-2.5 sigma      97.3%         5 / 225   = 2.2%
          +-3.0 sigma      94.7%        10 / 225   = 4.4%

    and `Genome.decode` over 200 prior draws: 88.0% unprojected, the register's
    6.0% anchor rate. The 2.2% reproduces the register's figure exactly.

    Two things changed. `_project_to_feasible` bisects toward the feasibility
    boundary instead of stepping a 10-rung ladder whose last rung IS the
    anchor — MEASURED over 1000 prior decodes on three data seeds, mean
    normalised displacement 0.0528 -> 0.0477, 0.0479 -> 0.0430, 0.0452 ->
    0.0402, and anchor returns 0.60% / 1.00% / 0.70% -> 0.00% in all three.
    And the substitution is now REPORTED, which is the part that matters: the
    gate below is on the UNPROJECTED rate, a quantity the fallback cannot fake.

    RECORDED so agreement is not mistaken for confirmation: the two generators
    return the SAME hulls here, to six decimal places (max displacement
    0.115265 against 0.115264). That is not independent corroboration — it is
    identity. The GMM's browsable map is a PCA of the training set and pPCA's
    first two latent axes are the same top-2 principal subspace, differing only
    by pPCA's sigma^2 shrinkage. The implementations diverge where they
    actually differ: raw feasibility 79.2% against 88.3%, and sampling
    entirely.
    """
    grid = np.array([[u, v] for u in np.linspace(-2.5, 2.5, 15)
                     for v in np.linspace(-2.5, 2.5, 15)])
    X, info = model.from_latent(grid, return_info=True)
    assert isinstance(info, DecodeInfo)
    assert len(info.projected) == len(grid) == len(X)

    assert info.anchor_rate == 0.0, (
        f"{info.anchor_rate:.1%} of the map came back as an EXACT training "
        f"hull — a slider move returning the same boat")
    assert info.unprojected_rate >= 0.90, (
        f"only {info.unprojected_rate:.1%} of the map delivers the point that "
        f"was asked for (measured 97.3% GMM / 97.3% pPCA at +-2.5 sigma)")
    # displacement is a real number where it is claimed and zero where it is not
    assert (info.displacement[~info.projected] == 0.0).all()
    assert (info.displacement[info.projected] > 0.0).all()
    assert info.displacement.max() < 0.35
    assert ((info.t > 0.0) == info.projected).all()
    for x in X:
        assert grammar.check(x).ok


def test_genome_decode_reports_its_projection_too():
    """`navalai.latent.Genome.decode` had the same silent fallback and the
    register measured it at 6.0% of 200 draws. MEASURED after the fix: 88.0%
    of 200 prior draws delivered unprojected, 0.0% anchors.

    RE-BASED 2026-08-19: the physics-correction campaign tightened L0 (the
    vessel-aware bands, the freeboard floors, the kernel rebuild), so more
    prior draws land infeasible and get HONESTLY projected — 73.0 / 77.0 /
    72.0% unprojected over rng streams 0/1/2, anchors still 0.0% on all
    three (also 73.0% at the audit base f0ccc5f: the move predates this
    change). Projection is not the defect this test guards; SILENT
    projection is, and anchor_rate == 0 still carries that claim. The bar
    sits just under the measured band; a fall below it means the latent
    family stopped covering the feasible set and must be re-fit, not
    re-worded.

    RE-BASED again 2026-08-27 (the dwl + tunnel arity events, 23 -> 30):
    the PPCA now spans seven more constant columns and the grammar box
    seven more clauses, and the same three rng streams read 69.5 / 75.0 /
    68.5% unprojected — the band moved down ~4 points, anchors still 0.0%
    everywhere, which is the claim. Bar 0.70 -> 0.65, just under the new
    band by the same margin the old bar sat under the old one."""
    from navalai.latent import Genome

    X, _y = sample_valid(120, MissionSpec(), seed=11)
    g = Genome.fit(X)
    Z = np.random.default_rng(0).standard_normal((200, 8))
    Xd, info = g.decode(Z, return_info=True)
    assert info.anchor_rate == 0.0
    assert info.unprojected_rate >= 0.65
    assert all(grammar.check(x).ok for x in Xd)
    # project=False must not claim a projection it did not do
    _Xr, info0 = g.decode(Z, project=False, return_info=True)
    assert (info0.displacement == 0.0).all() and info0.anchor_rate == 0.0


# ---------------- I9: the slider bar applies to EVERY widget ----------------

def _p95(fn, n=30):
    fn()                                   # warm
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1e3)
    return float(np.percentile(ts, 95))


def test_slider_eval_p95_under_100ms():
    from ui.server import eval_payload
    p = dict(_REF)
    out = eval_payload(p, None)  # warm
    p95 = _p95(lambda: eval_payload(p, None))
    assert p95 < 100.0, f"slider p95 {p95:.1f} ms"
    assert out["tier"] == "L1"
    # fidelity badges are mandatory on every quantity. `basis` joined the
    # envelope: a band the user reads must declare whether it was PROPAGATED
    # from a model or asserted as a fraction of its own value. The audit found
    # every sigma in the UI was the latter — freeboard a constant 0.02,
    # wh_per_nm literally 0.30 x value — which is a decoration, not a band.
    # 2026-08-12: `wh_per_nm` stopped being "assumed" and became
    # "propagated-lower-bound", because evaluate() now serves the sigma
    # `energy.wh_per_nm_sigma` computed from the resistance band instead of its
    # own inline 0.30. The accepted set widens to the vocabulary `energy`
    # owns — but NOT to "placeholder", which is the string that means no input
    # sigma reached the propagation.
    from navalai.energy import (SIGMA_PLACEHOLDER, SIGMA_PROPAGATED,
                                SIGMA_PROPAGATED_LOWER_BOUND)
    # PER QUANTITY, NOT PER SET (2026-08-21). The blanket form of this
    # assertion admitted "assumed" for everything, and "assumed" is what four
    # typed sigmas in this file were wearing: freeboard 0.02, cb 0.02,
    # solar_kwh_day * 0.25 and range_solar_nm_day * 0.35. Two of those are
    # literal declared fractions of their own value — verbatim the thing gap
    # H1's prose says is gone — and the blanket check could not see them
    # because it asked about the VOCABULARY and not about which quantity used
    # which word. Banning "placeholder" outright made it worse: it forced the
    # two quantities that genuinely have no input sigma to call themselves
    # something warmer than they are.
    #
    # So: every served quantity must name a basis, and the two that CAN
    # propagate must be shown doing it.
    propagatable = {"displacement_kg", "GM_m", "Rt_N", "freeboard_m",
                    "wh_per_nm", "range_solar_nm_day"}
    for name, q in out["quantities"].items():
        assert set(q) == {"value", "tier", "sigma", "basis"}
        assert q["basis"] in ("measured", SIGMA_PROPAGATED,
                             SIGMA_PROPAGATED_LOWER_BOUND, SIGMA_PLACEHOLDER)
        if name in propagatable:
            assert q["basis"] != SIGMA_PLACEHOLDER, (
                f"{name} has a propagatable band and is serving none")
            assert q["sigma"] is None or q["sigma"] > 0.0, name
        else:
            # A placeholder carries NO band. Serving a number under it would
            # be the same defect one word further along.
            assert q["basis"] == SIGMA_PLACEHOLDER and q["sigma"] == 0.0, (
                name, q)
    assert out["quantities"]["freeboard_m"]["basis"] == \
        SIGMA_PROPAGATED_LOWER_BOUND, (
            "freeboard is back to a typed 0.02 m; the mass sigma reaches it "
            "through the waterplane stiffness and must be shown doing so")
    assert out["quantities"]["wh_per_nm"]["basis"] == \
        SIGMA_PROPAGATED_LOWER_BOUND, (
            "the UI is back to serving a declared fraction as a one-sigma band")


def test_every_interactive_endpoint_meets_the_p95_bar_not_just_eval():
    """Gate 4's bar is "every widget answering in <100 ms" and `/eval` was the
    ONLY path tested. MEASURED before the fix, on this Mac:

        /eval          6.75 ms   the one endpoint with a test        PASS
        /generate       861 ms   at n=3; 11.5 s at n=20; UNTESTED    FAIL
        first request  1018 ms   extra — a blocking model fit        FAIL
        /pareto         440 ms   cold, 0.00 ms after                 FAIL

    MEASURED after: prefit pays 3.4 s ONCE at `serve()` (model 1.0 s, a
    48+128 scored pool 1.2 s, the Pareto front 1.2 s), and then
    /generate p95 is 0.030 ms at n=3, 0.041 ms at n=10, 0.036 ms at n=20, with
    /pareto at 0.0003 ms.

    The 100 ms bar is not reachable live for `/generate`: it scores candidates
    through L1 at ~13 ms each and 100 ms buys seven, which is not enough to
    condition on. It is reachable by doing that scoring at startup, which is
    what `get_pool()` does — and the reference and candidate batches stay
    DISJOINT in the pool exactly as `sample_conditioned` draws them, or the
    endpoint would quietly become the same-batch top-k control that
    conditioning is supposed to beat.
    """
    import ui.server as S

    S.prefit()
    assert _p95(lambda: S.generate_payload(3, 0.5)) < 100.0
    assert _p95(lambda: S.generate_payload(20, 0.5)) < 100.0
    assert _p95(lambda: S.get_pareto()) < 100.0

    out = S.generate_payload(3, 0.5)
    assert out["n_returned"] == 3 and out["partial"] is False
    assert out["tier"] == "L1" and out["source"] == "prefit_pool"
    # the reference batch that sets the cut is NOT the candidate pool
    assert out["n_reference"] == S.N_REF and out["n_pool"] == S.N_CAND
    for h in out["hulls"]:
        assert grammar.check(grammar.vector(h)).ok

    # a request the pool cannot fill says so instead of raising or padding
    tight = S.generate_payload(500, 1.0)
    assert tight["partial"] is True and tight["n_returned"] < 500
    assert tight["n_requested"] == 500
    with pytest.raises(ValueError, match="percentile must be in"):
        S.generate_payload(3, 1.4)


def test_http_server_smoke():
    from http.server import ThreadingHTTPServer

    from ui.server import Handler
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/bounds", timeout=10) as r:
            spec = json.loads(r.read())
        assert len(spec) == grammar.N_PARAMS
        # the reference hull over the wire, from its one home. Spelled out here
        # it was a fourth copy of the genome, and the only one of the four that
        # the rebuild happened to leave correct.
        body = json.dumps({"params": _REF}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/eval", data=body)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        assert d["tier"] == "L1" and "quantities" in d
        # /generate is an endpoint too, and it was never exercised over HTTP
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/generate",
            data=json.dumps({"n": 2, "percentile": 0.5}).encode())
        with urllib.request.urlopen(req, timeout=60) as r:
            gen = json.loads(r.read())
        assert len(gen["hulls"]) == 2 and gen["partial"] is False
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as r:
            html = r.read().decode()
        assert "slider surface" in html
    finally:
        srv.shutdown()


# ---------------------------------------------------------------------------
# H3 — honesty rule 1 in the one place a user reads
# ---------------------------------------------------------------------------

def test_every_mass_line_carries_a_tier_and_a_sigma():
    """`/eval` returned `weights_kg` as six BARE rounded floats while
    `weights.aggregate()` had already computed the uncertainty item by item and
    in quadrature. Honesty rule 1 is "every quantity carries {value, tier,
    sigma}", and the weight panel was the one place that ignored it.

    MEASURED on the reference hull after the fix, and RE-MEASURED 2026-08-13 on
    the rebuilt geometry kernel: total 6000 kg +/- 1432 -> 1520 kg, a 24% -> 25%
    band the panel simply did not show.

    The second arm is the one that actually cost something. `ev.weights` is the
    five-bucket BUDGET; the hull is floated at `ev.masses.total_kg`, which
    includes the DECLARED `unaccounted` item — MEASURED at 2826 kg (47% of
    displacement) on the 15-parameter genome and 3011 kg (50.2%) on this one.
    MECHANISM: the reference hull's five real buckets total 2989 kg against an
    unchanged 6 t mission displacement, and `structure` fell as the rebuilt
    kernel re-derived the plating area, so the declared gap grew by what
    structure lost. The panel showed the budget's total right next to
    `displacement_kg` — two numbers that are supposed to be the same mass,
    differing by half the boat, with nothing saying why. The positioned model is
    the one truth, so the lines now sum to the displacement above them.

    THE UNACCOUNTED ITEM IS NOW MORE THAN HALF THE BOAT. That is not this
    test's finding to fix and it is not softened here: the assertion is that the
    panel DECLARES it, which is the honesty rule. It is worth someone's
    attention that the declared gap crossed 50%.
    """
    from ui.server import eval_payload

    p = dict(_REF)
    out = eval_payload(p, None)
    w = out["weights_kg"]
    assert set(w) >= {"structure", "battery", "panels", "outfit", "payload",
                      "unaccounted", "total"}
    for name, q in w.items():
        assert set(q) == {"value", "tier", "sigma", "basis"}, (
            f"{name} is not a badged quantity: {q}")
        assert q["tier"] and q["sigma"] is not None
        assert q["basis"] in ("measured", "assumed")
    # the propagated total, not the five-bucket budget
    assert w["total"]["basis"] == "measured"
    assert w["total"]["sigma"] > 0
    lines = sum(q["value"] for k, q in w.items() if k != "total")
    assert lines == pytest.approx(w["total"]["value"], rel=1e-6)
    assert w["total"]["value"] == pytest.approx(
        out["quantities"]["displacement_kg"]["value"], rel=0.01)


def test_the_mass_sigmas_are_the_models_own_not_retyped_in_the_server():
    """A per-bucket sigma had to come from somewhere, and retyping `0.15 *
    mass` in `ui/server.py` would have been the "number declared twice" defect
    CLAUDE.md's design-side invariants exist to prevent — the same shape as GM
    0.35 vs 0.45. `MassAggregate` now carries its items so a consumer reports
    the model's own numbers.
    """
    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec
    from ui.server import eval_payload

    p = dict(_REF)
    ev = evaluate(grammar.vector(p), MissionSpec())
    served = eval_payload(p, None)["weights_kg"]
    assert ev.masses.items and len(ev.masses.items) == ev.masses.n_items
    for item in ev.masses.items:
        assert served[item.id]["sigma"] == pytest.approx(item.sigma_kg, abs=1e-3)
        assert served[item.id]["tier"] == item.tier


# ---------------------------------------------------------------------------
# I9 — /generate could not be asked about a mission
# ---------------------------------------------------------------------------

def test_generate_answers_the_mission_it_was_asked_about():
    """`do_POST` passed only `n` and `percentile`, and `_score` read the
    module-level `_mission_default`, so a mission-specific generate was not
    slow — it was IMPOSSIBLE, while the panel showed a mission box beside the
    button. The widget ranked candidates by Wh/NM at 5 knots under a 6 t budget
    whatever the user had typed, and said nothing about it.

    MEASURED after wiring it through, same 128 candidates:

        default mission    top-3 Wh/NM  278.7 282.2 293.6   0.085 ms (prefit)
        9 kn / 3 t  cold   top-3 Wh/NM  642.7 707.7 736.6   1074 ms  live=True
        9 kn / 3 t  warm                                    0.046 ms

    HONESTY RULE 6 APPLIES TO THE 1074 ms. A mission the server has not scored
    costs 176 L1 evaluations and MISSES Gate 4's 100 ms bar by 10x. That is not
    softened and not hidden: it is paid once per mission, and the payload
    declares `live` and `elapsed_ms` so the cost is visible rather than assumed.
    The default mission is still prefit at `serve()`, so the bar the gate
    asserts is measured on the path the panel actually opens with.
    """
    import ui.server as S

    S.prefit()
    base = S.generate_payload(3, 0.8)
    assert base["live"] is False and base["source"] == "prefit_pool"

    mis = {"displacement_target_kg": 3000.0, "cruise_speed_kn": 9.0,
           "design_category": "C"}
    cold = S.generate_payload(3, 0.8, mis)
    assert cold["mission"]["cruise_speed_kn"] == 9.0
    assert cold["live"] is True and cold["source"] == "live_pool"
    assert cold["hulls"] != base["hulls"], (
        "a different mission returned the same hulls — the mission is still "
        "not reaching the score")
    assert cold["wh_per_nm"] != base["wh_per_nm"]

    warm = S.generate_payload(3, 0.8, mis)
    assert warm["live"] is False and warm["hulls"] == cold["hulls"]
    assert _p95(lambda: S.generate_payload(3, 0.8, mis)) < 100.0

    # the cache is bounded: an unbounded map keyed on user input is a leak
    for kn in range(1, 4 + S.MAX_POOLS):
        S.generate_payload(1, 0.8, {"cruise_speed_kn": float(kn)})
    assert len(S._pool) <= S.MAX_POOLS
