"""Gate 2C -- `mesh_robustness.classify()` names the MECHANISM that failed.

Gate 2U is an expected RED carried in `data/gate-ledger.json`, so it has no
suite and nothing tested the campaign runner that produces its watermark. That
runner's rate is one number; its TAXONOMY is what tells the next session where
to spend a day, and it was measured wrong twice, in opposite directions:

  * hulls 2 and 19  -- LTS DIVERGENCES labelled `solver-stopped-short`, which
    reads like a timeout. Hull 19's force history is unambiguous: steady at
    ~2.7e3 N through iteration 410, then 5.0e7 -> 3.4e16 -> 8.9e20 -> 4.3e28,
    ending at 3.7e71 N with cumulative continuity error -5.9e26 -- and the
    blow-up began ~560 iterations BEFORE the process was signalled, so the
    SIGTERM did not cause it. The `min_deltaT` guard could never fire: LTS has
    no deltaT, `min_deltaT` is -1.0 on every LTS row, and -1.0 fails `0 <=`.

  * hull 5 -- `mesh-build-failed` with `cells: -1` and `max_skewness: -1.0`,
    while `runner_exit: 0`, `solve_attempted: true`, `solve_reached: 2000.0` of
    a 2000-iteration LTS run in 1108.6 s, `crashed: false`, `fatal: false`, and
    `min_flow_time_scale: 1.04582e-05`. A mesh that failed to BUILD cannot then
    be solved on for 2000 iterations. run-case.sh's checkMesh bar is fatal, so
    interFoam starting is proof the mesh was built and cleared it.

Both are this repo's defect class 1 -- an unmeasurable value scored as a benign
one -- reached from the two opposite directions: a sentinel that silently reads
as "fine" (min_deltaT -1.0) and a sentinel that silently reads as "broken"
(cells -1). The fence below is that neither sentinel may decide a verdict.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "scripts" / "mesh_robustness.py"
_spec = importlib.util.spec_from_file_location("_mesh_robustness", _SRC)
_mr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mr)
classify = _mr.classify


def _lts_row(**over) -> dict:
    """A row shaped like the campaign's own output for a COMPLETED LTS solve.

    `min_deltaT` is -1.0 because LTS has no deltaT -- that is the real value on
    every LTS row, not a placeholder chosen for this test.
    """
    r = dict(
        cells=230725, zero_volume_cells=0, wrong_oriented=0, max_skewness=8.93,
        seconds=1100.0, runner_exit=0, timed_out=False, layer_pass_failed=False,
        solve_requested=2.0, solve_attempted=True, solve_steps=1000,
        solve_end_time=2000.0, solve_reached=2000.0, min_deltaT=-1.0,
        min_flow_time_scale=1.04582e-05, fatal=False, crashed=False, solves=True,
    )
    r.update(over)
    return r


def test_an_lts_divergence_is_not_reported_as_a_short_run():
    """Hulls 2 and 19. The bar is 1e-20 and it is NOT interpolated.

    MEASURED across four solves, min_flow_time_scale is monotone in mesh
    skewness over 35 orders of magnitude: skew 2.87 -> 2.12e-05,
    14.26 -> 2.11e-12, 17.57 -> 2.48e-40. The two that solved sit at 1e-05,
    the divergence at 1e-40, and the bar sits between them by orders of
    magnitude in both directions rather than being fitted to either.
    """
    diverged = _lts_row(min_flow_time_scale=2.48e-40, solves=False,
                        solve_reached=410.0)
    assert classify(diverged) == "solver-lts-time-scale-collapse", (
        "an LTS run whose local time scale collapsed to 1e-40 has DIVERGED; "
        "`solver-stopped-short` reads as a timeout and sent two sessions "
        "looking for a wall-clock problem"
    )


def test_the_deltaT_guard_being_dead_under_lts_is_the_reason_that_bar_exists():
    """The regression fence. If someone restores a deltaT-only guard, the row
    above passes through it untouched and this test says why that is not enough.
    """
    diverged = _lts_row(min_flow_time_scale=2.48e-40, solves=False,
                        solve_reached=410.0)
    assert diverged["min_deltaT"] == -1.0
    assert not (0 <= diverged["min_deltaT"] < 1e-12), (
        "-1.0 fails the `0 <=` test, so the deltaT guard cannot fire on an LTS "
        "row -- which is exactly how two divergences were scored as benign"
    )


def test_a_healthy_lts_solve_is_still_ok():
    """The bar must not be so tight that it condemns the runs it was measured
    against: the two solves that completed sit at ~1e-05, 15 orders above it."""
    assert classify(_lts_row()) == "ok"


def test_a_completed_solve_is_never_blamed_on_the_mesh_failing_to_build():
    """Hull 5. `cells: -1` is an unparsed RECEIPT, not an unbuilt mesh."""
    hull5 = _lts_row(cells=-1, max_skewness=-1.0, seconds=1108.6)
    assert classify(hull5) == "checkmesh-unparsed", (
        "run-case.sh's checkMesh bar is fatal, so 2000 completed iterations "
        "prove the mesh was built; blaming snappy sends the next session to "
        "fix a grep in the wrong file"
    )


def test_an_unparsed_checkmesh_is_not_promoted_to_a_pass_either():
    """The other half, and the one that matters more.

    `zero_volume_cells` and `wrong_oriented` default to a PASSING 0 while
    `cells` and `max_skewness` default to -1. Calling hull 5 `ok` would score
    an unverified mesh as a clean one -- the same defect in the direction that
    inflates the Gate 2U watermark rather than deflating it.
    """
    hull5 = _lts_row(cells=-1, max_skewness=-1.0)
    assert classify(hull5) != "ok"
    assert classify(hull5) != "mesh-build-failed"


def test_a_genuinely_unbuilt_mesh_still_says_so():
    """The discriminator is the SOLVE, not the sentinel. With no solver run
    there is no evidence the mesh existed, and the honest label is unchanged."""
    dead = _lts_row(cells=-1, max_skewness=-1.0, runner_exit=1,
                    solve_attempted=False, solve_steps=0, solves=False)
    assert classify(dead) == "mesh-build-failed"

    layers = dict(dead, layer_pass_failed=True)
    assert classify(layers) == "layer-pass-failed", (
        "the layer pass is an earlier and more specific refusal; it must not "
        "be swallowed by the build-failed branch"
    )


def test_every_stored_campaign_row_re_derives_its_own_label():
    """The artifacts must stay reproducible from the function that wrote them.

    MEASURED 2026-08-12: `data/gate2u-campaign-baseline.json` was written before
    `solve_requested` was recorded PER ROW (it survived only as a top-level
    field), so re-deriving `why` from the stored rows relabelled FIVE hulls --
    7, 9, 13, 15, 17 -- from `ok` to `meshed-no-solve-requested`, purely because
    a field `classify()` reads was missing from the record. The labels quoted in
    the Gate 2U ledger were not reproducible from the artifact that carried
    them, which is docs/LESSONS.md defect class 5 with the evidence still on
    disk. Every later artifact records it; the baseline is backfilled from its
    own top-level value.

    This fence also binds the other way round: change `classify()` and the
    stored taxonomies must be re-derived in the same commit, rather than the
    code and the record drifting into two answers to one question.
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "data"
    seen = 0
    for path in sorted(root.glob("gate2u*.json")):
        rows = json.loads(path.read_text()).get("rows") or []
        for r in rows:
            if "why" not in r:
                continue
            seen += 1
            assert classify(r) == r["why"], (
                f"{path.name} hull {r.get('hull')}: stored {r['why']!r} but "
                f"classify() now says {classify(r)!r} -- re-derive the artifact "
                "in the same commit as the classifier change"
            )
    assert seen >= 20, f"only {seen} labelled rows found; the fence went blind"


@pytest.mark.parametrize("sentinel_field", ["cells", "max_skewness"])
def test_no_negative_sentinel_ever_produces_the_string_ok(sentinel_field):
    """The general fence, so the next sentinel added does not repeat this.

    An unmeasured metric is REFUSED, never assumed good -- the rule CLAUDE.md
    states for run-case.sh's `${VAR:-0}` receipts, applied to the classifier
    that consumes them.
    """
    row = _lts_row(**{sentinel_field: -1.0})
    assert classify(row) != "ok", (
        f"{sentinel_field} = -1.0 means UNMEASURED; a verdict of `ok` on it is "
        "an unmeasurable value scored as a passing one"
    )
