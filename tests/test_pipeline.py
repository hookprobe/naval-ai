"""Gate tests for the MDO spine (`navalai.pipeline`).

PLM.md §3 step 4: code + gate test in the same change, and the test comment
names the motivating incident. Two incidents motivate this file, and every
guard below is tested by making it FIRE on realistic input, not only by
watching it pass:

INCIDENT 1 (MEASURED 2026-08-06) — a bar shipped with no test. `run-case.sh`
carried the checkMesh bars 0 zero-volume cells / 5 incorrectly-oriented faces /
20 max skewness, and the awk that read skewness never matched the line checkMesh
actually prints:

    ***Max skewness = 42.9417, 23 highly skew faces detected

`${_MQ_SKEW:-0}` then turned "could not measure" into "perfect" — 0 passes every
bar — and a mesh with max skewness 42.94 was handed to a 10-rank solve that spun
18 minutes at deltaT 2.5e-26 producing 61 timesteps all at the same instant.
The lesson encoded here: AN UNMEASURABLE METRIC IS FATAL, NEVER A PASSING
DEFAULT, and a bar with no test is a bar that has not been checked.

INCIDENT 2 (gap register §A, audited 2026-08-05) — nothing could see an
abandoned design. `evaluate`, `optimize`, `agents` and `ui/server` reach
`seakeeping: no, cfd: no, surrogate: no, rules: no`; `Evaluation.tier` read
"L1" in 100% of ~2000 evaluations. There was no object able to say "this genome
entered MESHING and never came back". Hence the property test below, which
drives random legal AND illegal sequences and asserts every genome reaches
exactly one terminal state.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import pytest

from navalai import db, grammar
from navalai.mission import MissionSpec
from navalai.pipeline import (ARCHIVE_PATH, CYCLE_REQUIREMENTS, FAILURES,
                              STAGE_ORDER, Genome, GenomeError,
                              IllegalTransition, JsonlLog, LogTruncated,
                              Pipeline, RECEIPT_NAMES, Stage,
                              Terminal, Unmeasurable, check_cfd, check_geometry,
                              check_hydrostatics, check_mesh, check_stl,
                              legal_targets, mesh_quality_bars,
                              settle_tolerance, transition)

_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _genome(seed: int = 0) -> Genome:
    return Genome.from_vector(grammar.sample(1, np.random.default_rng(seed))[0])


def _pipeline(tmp_path: Path) -> Pipeline:
    return Pipeline(tmp_path / "archive.jsonl")


def _walk_to(pl: Pipeline, g: Genome, stage: Stage) -> None:
    pl.start(g)
    for s in STAGE_ORDER[1:_STAGE_POS[stage] + 1]:
        pl.advance(g.id, s)


_STAGE_POS = {s: i for i, s in enumerate(STAGE_ORDER)}


# ---------------------------------------------------------------------------
# The genome is named by its contents
# ---------------------------------------------------------------------------

def test_the_genome_id_is_content_derived_and_shared_with_provenance():
    x = grammar.sample(1, np.random.default_rng(3))[0]
    a, b = Genome.from_vector(x), Genome.from_vector(list(x), label="other name")
    assert a.id == b.id, "the same parameters must name the same genome"
    # And it is db.hull_id, not a second hashing scheme. Two content addresses
    # for one hull would mean the spine and `data/navalai.sqlite3` disagreed
    # about which design they were describing.
    assert a.id == db.hull_id(np.asarray(x, dtype=float))
    y = x.copy()
    y[0] += 0.5
    assert Genome.from_vector(y).id != a.id


def test_a_genome_that_cannot_be_written_down_is_refused():
    x = grammar.sample(1, np.random.default_rng(4))[0]
    with pytest.raises(GenomeError):
        Genome(tuple(x[:-1]))                      # wrong length
    bad = x.copy()
    bad[2] = float("nan")
    with pytest.raises(GenomeError):
        Genome.from_vector(bad)                    # nan is never a value


def test_the_genome_does_not_restate_the_design_vector():
    # Rule 3, applied to the parameter set: `grammar.PARAMS` is the one source
    # and `optimize.HullProblem` / `geometry.Hull` read it too. A spine with its
    # own field list would be a sixteenth place for the design vector to drift.
    src = (_ROOT / "navalai" / "pipeline.py").read_text()
    for name in grammar.NAMES:
        assert f'"{name}"' not in src and f"'{name}'" not in src, (
            f"pipeline.py names the grammar parameter {name!r}; it must take "
            f"the vector from navalai.grammar, not restate it")


# ---------------------------------------------------------------------------
# INCIDENT 1: an unmeasurable metric is fatal, never a passing default
# ---------------------------------------------------------------------------

_GOOD_MESH = {"zero_volume_cells": 0, "wrong_oriented_faces": 0,
              "max_skewness": 8.93076}          # runs/val_coarse5, which SOLVED


@pytest.mark.parametrize("metric", ["zero_volume_cells", "wrong_oriented_faces",
                                    "max_skewness"])
@pytest.mark.parametrize("unmeasured", [None, "UNPARSED", "", "n/a", float("nan"),
                                        float("inf"), "***Max skewness ="])
def test_an_unmeasured_mesh_metric_is_fatal_never_a_passing_default(metric,
                                                                    unmeasured):
    """The 2026-08-06 incident, as a test.

    `${_MQ_SKEW:-0}` scored an unreadable skewness as 0, and 0 passes every
    bar. Each of these values is a way the measurement can come back absent —
    missing key, run-case.sh's own UNPARSED sentinel, an empty capture, a
    non-numeric token, and the nan/inf that arithmetic on a broken log
    produces. Every one must REFUSE.
    """
    metrics = dict(_GOOD_MESH)
    if unmeasured is None:
        metrics.pop(metric)                       # the key never arrived at all
    else:
        metrics[metric] = unmeasured
    check = check_mesh(metrics)
    assert not check.ok
    assert check.terminal is Terminal.FAILED_MESH
    assert metric in check.reason
    assert "could not be measured" in check.reason
    assert check.evidence[metric] == "UNMEASURED", (
        "the receipt must say UNMEASURED, not 0 — recording a 0 is the defect")


def test_the_mesh_that_died_is_refused_and_the_mesh_that_solved_is_not():
    """Calibrated on the two real meshes, not on numbers between them.

    MEASURED (CLAUDE.md, 2026-08-06 sweep, same hull and background, only
    n_layers varying):
        n=5  0 zeroVol,  0 wrongOri, max skewness  8.93  -> SOLVES
        n=7  0 zeroVol, 10 wrongOri, max skewness 42.94  -> DIES at t=0.0072 s
    """
    assert check_mesh(_GOOD_MESH).ok
    died = {"zero_volume_cells": 0, "wrong_oriented_faces": 10,
            "max_skewness": 42.9417}
    check = check_mesh(died)
    assert not check.ok
    assert check.terminal is Terminal.FAILED_MESH
    assert "wrong_oriented_faces" in check.reason
    assert "max_skewness" in check.reason


def test_the_mesh_bars_are_read_from_run_case_sh_and_the_verdict_follows_it(tmp_path):
    """A number lives in exactly one place — proved by moving it.

    The bars are extracted from the shipped guard, so this test doctors a COPY
    of run-case.sh and shows the verdict changes with the file. A restated
    constant would not move, which is exactly how `forceCoeffs` stayed wrong by
    2x and a 15 mm ply failed its own scantling rule.
    """
    bars = mesh_quality_bars()
    # The measured calibration, stated out loud so that moving it in
    # run-case.sh has to be a deliberate act that updates this line:
    #   0 zero-volume cells; 5 incorrectly-oriented faces (5 is the largest
    #   count measured to SOLVE, 10 is measured to die); max skewness 20, which
    #   is checkMesh's own boundary-face limit.
    assert (bars.zero_volume_cells, bars.wrong_oriented_faces,
            bars.max_skewness) == (0.0, 5.0, 20.0)
    assert bars.source.endswith("run-case.sh")

    script = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    doctored = tmp_path / "run-case.sh"
    doctored.write_text(script.replace("s+0 > 20.0) ? 1 : 0",
                                       "s+0 > 4.0) ? 1 : 0"))
    tight = mesh_quality_bars(doctored)
    assert tight.max_skewness == 4.0
    assert check_mesh(_GOOD_MESH).ok, "8.93 passes the shipped bar of 20"
    assert not check_mesh(_GOOD_MESH, bars=tight).ok, (
        "the same metrics must fail a tightened bar — if they do not, the bar "
        "in use is a copy inside pipeline.py, not the one in run-case.sh")


def test_a_bar_that_cannot_be_read_raises_rather_than_defaulting(tmp_path):
    """Same rule one level up: an unreadable BAR is refused too.

    If the guard is refactored out from under this module, the right answer is
    a loud failure, never a plausible default. A fallback constant here would
    be a second source of the bar the moment it disagreed with the script.
    """
    empty = tmp_path / "run-case.sh"
    empty.write_text("#!/bin/bash\necho hello\n")
    with pytest.raises(Unmeasurable):
        mesh_quality_bars(empty)
    with pytest.raises(Unmeasurable):
        settle_tolerance(empty)


def test_the_settling_tolerance_comes_from_gate2m():
    # gate2m.py prints the Gate 2M verdict, so its SETTLE_TOL is the number.
    # CLAUDE.md: drift > 5% over the averaging tail means NOT SETTLED and the
    # result is not to be reasoned about.
    assert settle_tolerance() == 0.05


def test_an_unsettled_or_unmeasurable_cfd_run_is_not_a_result():
    assert check_cfd(0.01, ct=3.711e-3, flow_throughs=5.0).ok
    unsettled = check_cfd(0.12, ct=3.7e-3)
    assert not unsettled.ok and unsettled.terminal is Terminal.FAILED_CFD
    assert "has not settled" in unsettled.reason
    for bad in (None, "UNPARSED", float("nan")):
        c = check_cfd(bad)
        assert not c.ok and "could not be measured" in c.reason
    # CLAUDE.md: at KCS Fn 0.26 one flow-through is 14.92 s, so --end-time 20 is
    # 1.34 of them and every run in the repository at re-audit sat at 0.13-0.70.
    # A number from under one flow-through describes startup, not resistance.
    startup = check_cfd(0.01, ct=3.7e-3, flow_throughs=0.70)
    assert not startup.ok and "startup" in startup.reason


# ---------------------------------------------------------------------------
# The other stage guards, made to fire
# ---------------------------------------------------------------------------

def test_the_geometry_guard_fires_on_a_hull_the_l0_gate_rejects():
    ok = _genome(11)
    assert check_geometry(ok).ok
    # deadrise.order: beta_bow below beta_mid. A real L0 violation, one of the
    # nine that fire (22.2% of uniform in-bounds vectors), not a contrived one.
    bad = dict(ok.named())
    bad["beta_mid"], bad["beta_bow"] = 24.0, 3.0
    check = check_geometry(Genome.from_named(bad))
    assert not check.ok
    assert check.terminal is Terminal.FAILED_GEOMETRY
    assert any("deadrise.order" in r for r in check.reasons)


def test_the_hydrostatics_guard_is_exactly_the_ladders_constraint_vector():
    """It delegates; it does not re-derive a GM floor or a freeboard floor.

    `limits.py` exists because the GM floor was hard-coded in four places
    (0.35 / 0.45 / 0.35 / 0.35) and NSGA-II optimised to its own copy. The spine
    must read `Evaluation.g`, so that a constraint added to `evaluate()`
    constrains this stage automatically — the way it already constrains the
    optimizer.
    """
    from navalai.evaluate import CONSTRAINT_NAMES, evaluate

    mission = MissionSpec(name="spine test", displacement_target_kg=6000.0)
    fired = 0
    for seed in range(12):
        g = _genome(100 + seed)
        check = check_hydrostatics(g, mission)
        ev = evaluate(g.vector(), mission)
        if ev.tier == "L0":
            continue
        expected = all(ev.g[k] <= 0.0 for k in CONSTRAINT_NAMES)
        assert check.ok is expected, (
            f"verdict disagrees with the ladder's own g vector for {g.id}")
        if not check.ok:
            fired += 1
            assert check.terminal is Terminal.FAILED_HYDROSTATICS
            assert any(k in check.reason for k in CONSTRAINT_NAMES)
    assert fired > 0, ("no sampled hull violated a constraint — this guard has "
                       "then only been watched passing, which is the failure "
                       "mode this file exists to avoid")


def test_the_stl_guard_fires_on_an_open_shell(tmp_path):
    # CLAUDE.md: an open shell floods the interior of the mesh. A single
    # triangle is the smallest honest instance of one.
    open_shell = tmp_path / "open.stl"
    open_shell.write_text(
        "solid hull\n facet normal 0 0 1\n  outer loop\n"
        "   vertex 0 0 0\n   vertex 1 0 0\n   vertex 0 1 0\n"
        "  endloop\n endfacet\nendsolid hull\n")
    check = check_stl(open_shell)
    assert not check.ok and check.terminal is Terminal.FAILED_GEOMETRY
    assert "closed manifold" in check.reason
    missing = check_stl(tmp_path / "nope.stl")
    assert not missing.ok and "no STL" in missing.reason
    # A closed, outward-wound tetrahedron passes.
    v = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
    faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
    lines = ["solid hull"]
    for f in faces:
        lines += [" facet normal 0 0 0", "  outer loop"]
        lines += [f"   vertex {v[i][0]} {v[i][1]} {v[i][2]}" for i in f]
        lines += ["  endloop", " endfacet"]
    lines.append("endsolid hull")
    closed = tmp_path / "closed.stl"
    closed.write_text("\n".join(lines) + "\n")
    assert check_stl(closed).ok


# ---------------------------------------------------------------------------
# The lifecycle graph
# ---------------------------------------------------------------------------

def test_an_illegal_stage_transition_raises(tmp_path):
    pl = _pipeline(tmp_path)
    g = _genome(21)
    pl.start(g)
    with pytest.raises(IllegalTransition):          # skipping a stage
        pl.advance(g.id, Stage.HYDROSTATICS)
    pl.advance(g.id, Stage.GENERATING)
    pl.advance(g.id, Stage.VALIDATING)
    with pytest.raises(IllegalTransition):          # backwards
        pl.advance(g.id, Stage.GENERATING)
    with pytest.raises(IllegalTransition):          # standing still
        pl.advance(g.id, Stage.VALIDATING)
    with pytest.raises(IllegalTransition):          # SUCCESS before ARCHIVED
        pl.succeed(g.id)
    with pytest.raises(IllegalTransition):          # a failure with no reason
        pl.fail(g.id, Terminal.FAILED_MESH, "   ")
    # and none of those refusals wrote a record
    assert len(pl.log.read()) == 3
    assert pl.state(g.id).stage is Stage.VALIDATING


def test_a_terminal_state_is_terminal(tmp_path):
    pl = _pipeline(tmp_path)
    g = _genome(22)
    pl.start(g)
    pl.fail(g.id, Terminal.FAILED_RESOURCE, "no OpenFOAM on this node")
    for target in (Stage.GENERATING, Terminal.FAILED_MESH):
        assert target not in legal_targets(Terminal.FAILED_RESOURCE)
    with pytest.raises(IllegalTransition):
        pl.advance(g.id, Stage.GENERATING)
    with pytest.raises(IllegalTransition):
        pl.fail(g.id, Terminal.FAILED_MESH, "a second terminal")
    with pytest.raises(IllegalTransition):
        pl.succeed(g.id)


def test_a_failure_carries_a_reason_and_the_stage_it_failed_at(tmp_path):
    pl = _pipeline(tmp_path)
    g = _genome(23)
    _walk_to(pl, g, Stage.MESHING)
    check = check_mesh({"zero_volume_cells": 0, "wrong_oriented_faces": 10,
                        "max_skewness": 42.9417})
    pl.apply_check(g.id, check)
    st = pl.state(g.id)
    assert st.terminal is Terminal.FAILED_MESH
    assert st.failed_at is Stage.MESHING
    assert "42.9417" in st.terminal_reason
    rec = [r for r in pl.log.read() if r["kind"] == "terminal"][-1]
    assert rec["at_stage"] == "MESHING" and rec["reason"]


def test_success_is_only_reachable_from_the_end_of_the_ladder():
    for s in STAGE_ORDER[:-1]:
        assert Terminal.SUCCESS not in legal_targets(s)
        with pytest.raises(IllegalTransition):
            transition(s, Terminal.SUCCESS)
    assert Terminal.SUCCESS in legal_targets(Stage.ARCHIVED)
    transition(Stage.ARCHIVED, Terminal.SUCCESS)


# ---------------------------------------------------------------------------
# INCIDENT 2: no genome may be abandoned
# ---------------------------------------------------------------------------

def test_no_genome_can_be_abandoned_under_random_legal_and_illegal_walks(tmp_path):
    """Property-style: drive nonsense at the graph and count the terminals.

    Gap register §A: nothing in the product could report a design that entered
    a stage and never came back — `Evaluation.tier` read "L1" in 100% of ~2000
    evaluations because there was no lifecycle to leave. So: 60 genomes, each
    walked by a mix of legal and deliberately illegal moves, and afterwards
    EVERY one must hold exactly one terminal record. Illegal moves must raise
    and must leave no trace.
    """
    rng = random.Random(20260806)
    pl = _pipeline(tmp_path)
    genomes = [_genome(500 + i) for i in range(60)]
    for g in genomes:
        pl.start(g)

    for _ in range(2500):
        g = rng.choice(genomes)
        st = pl.state(g.id)
        if st.is_terminal:
            # Every move out of a terminal must raise, and after it the file
            # must be exactly as long as before (st_size, so the check is O(1)
            # and the loop does not become quadratic).
            before = pl.log.path.stat().st_size
            with pytest.raises(IllegalTransition):
                if rng.random() < 0.5:
                    pl.advance(g.id, rng.choice(STAGE_ORDER))
                else:
                    pl.fail(g.id, rng.choice(FAILURES), "second terminal")
            assert pl.log.path.stat().st_size == before
            continue
        roll = rng.random()
        if roll < 0.15:                              # deliberately illegal
            bad = rng.choice([s for s in STAGE_ORDER
                              if s not in legal_targets(st.stage)])
            before = pl.log.path.stat().st_size
            with pytest.raises(IllegalTransition):
                pl.advance(g.id, bad)
            assert pl.log.path.stat().st_size == before
        elif roll < 0.30:                            # a failure with no reason
            with pytest.raises(IllegalTransition):
                pl.fail(g.id, rng.choice(FAILURES), "")
        elif roll < 0.45:                            # a real failure
            pl.fail(g.id, rng.choice(FAILURES), f"measured: {rng.random():.4f}")
        elif st.stage is Stage.ARCHIVED:
            pl.succeed(g.id)
        else:
            pl.advance(g.id, STAGE_ORDER[_STAGE_POS[st.stage] + 1])

    # Anything still walking is driven to an end. THIS IS THE INVARIANT: the
    # coordinator must always be able to close a genome out.
    for g in genomes:
        st = pl.state(g.id)
        while not st.is_terminal:
            if st.stage is Stage.ARCHIVED:
                st = pl.succeed(g.id)
            else:
                st = pl.advance(g.id, STAGE_ORDER[_STAGE_POS[st.stage] + 1])

    assert pl.abandoned() == []
    terminals: dict[str, int] = {}
    for rec in pl.log.read():
        if rec["kind"] == "terminal":
            terminals[rec["genome_id"]] = terminals.get(rec["genome_id"], 0) + 1
    assert set(terminals) == {g.id for g in genomes}
    assert set(terminals.values()) == {1}, (
        "every genome must hold EXACTLY one terminal record, never zero "
        "(abandoned) and never two (two endings for one life)")
    # And a fresh reader, replaying only the file, sees the same thing.
    assert Pipeline(pl.log.path).abandoned() == []


def test_abandoned_reports_a_genome_left_in_a_stage(tmp_path):
    # The negative half: if a genome IS left mid-ladder, the query must say so.
    # A predicate that can only return the good answer is not a check.
    pl = _pipeline(tmp_path)
    left, done = _genome(31), _genome(32)
    _walk_to(pl, left, Stage.CFD)
    pl.start(done)
    pl.fail(done.id, Terminal.FAILED_TIMEOUT, "wall clock exceeded on the node")
    assert pl.abandoned() == [left.id]


# ---------------------------------------------------------------------------
# The archive is append-only
# ---------------------------------------------------------------------------

def test_the_archive_is_append_only_and_a_state_change_never_rewrites(tmp_path):
    """Nothing edits or deletes a prior record — checked at the BYTE level.

    `db.py` states the same rule for the provenance database ("rows are
    append-only; re-runs append, never overwrite"). Checking the prefix bytes
    rather than the parsed records is deliberate: a rewrite that happened to
    produce equivalent JSON would still be a rewrite of history.
    """
    pl = _pipeline(tmp_path)
    g = _genome(41)
    pl.start(g)
    snapshots = [pl.log.path.read_bytes()]
    for s in STAGE_ORDER[1:]:
        pl.advance(g.id, s, evidence={"note": f"entered {s.value}"})
        cur = pl.log.path.read_bytes()
        prev = snapshots[-1]
        assert cur.startswith(prev), (
            "a state change rewrote bytes that were already committed")
        assert len(cur) > len(prev), "a state change must APPEND a record"
        snapshots.append(cur)
    pl.succeed(g.id)
    pl.receipt(g.id, "knowledge", {"lesson": "kept"})
    final = pl.log.path.read_bytes()
    assert final.startswith(snapshots[-1])
    # Every line is still valid JSON, and the first record is still the first.
    lines = final.decode().strip().splitlines()
    assert json.loads(lines[0])["state"] == "NEW"
    assert len(lines) == len(STAGE_ORDER) + 2
    # There is no update or delete verb on the log, by construction.
    assert not hasattr(pl.log, "update") and not hasattr(pl.log, "delete")


def test_a_shortened_log_is_refused_rather_than_replayed(tmp_path):
    """History that got shorter is not history.

    `clean-runs.sh --purge` deleting a run directory while the prose citing it
    survived is gap N6 — the ledger now refuses to quote a deleted directory.
    Same rule here, at the file level: if the archive shrinks under a live
    Pipeline, the replayed state is no longer the state that was recorded, and
    saying so beats carrying on.
    """
    pl = _pipeline(tmp_path)
    g = _genome(42)
    pl.start(g)
    pl.advance(g.id, Stage.GENERATING)
    text = pl.log.path.read_text()
    pl.log.path.write_text(text.splitlines()[0] + "\n")     # someone truncated it
    with pytest.raises(LogTruncated):
        pl.advance(g.id, Stage.VALIDATING)


def test_a_corrupt_record_is_not_skipped(tmp_path):
    pl = _pipeline(tmp_path)
    g = _genome(43)
    pl.start(g)
    with pl.log.path.open("a") as fh:
        fh.write("{not json\n")
    with pytest.raises(LogTruncated):
        JsonlLog(pl.log.path).read()


def test_a_non_finite_evidence_value_never_lands_as_a_number(tmp_path):
    """nan is not a value, and a bare NaN is not valid JSON (RFC 8259).

    Gap E10 measured exactly this escaping over HTTP. Non-finite numbers are
    written as STRINGS so no reader can average them by accident.
    """
    pl = _pipeline(tmp_path)
    g = _genome(44)
    pl.start(g, evidence={"drift": float("nan"), "ratio": float("inf"),
                          "ok": 1.5})
    rec = json.loads(pl.log.path.read_text().splitlines()[0])
    assert rec["evidence"]["drift"] == "nan"
    assert rec["evidence"]["ratio"] == "inf"
    assert rec["evidence"]["ok"] == 1.5
    with pytest.raises(TypeError):
        pl.log.append({"genome_id": g.id, "kind": "stage", "state": "NEW",
                       "evidence": {"hull": object()}})


def test_replay_reconstructs_exactly_what_was_recorded(tmp_path):
    pl = _pipeline(tmp_path)
    made = []
    for i in range(6):
        g = _genome(60 + i)
        made.append(g)
        pl.start(g)
        for s in STAGE_ORDER[1:4]:
            pl.advance(g.id, s)
        if i % 2:
            pl.fail(g.id, Terminal.FAILED_HYDROSTATICS, f"GM below floor, run {i}")
        else:
            for s in STAGE_ORDER[4:]:
                pl.advance(g.id, s)
            pl.succeed(g.id)
            pl.artifact(g.id, "stl", f"/tmp/{g.id}.stl", sha256="deadbeef")
            for name in RECEIPT_NAMES:
                pl.receipt(g.id, name)
    fresh = Pipeline(pl.log.path)
    for g in made:
        a, b = pl.state(g.id), fresh.state(g.id)
        assert (a.stage, a.terminal, a.terminal_reason, a.failed_at) == \
               (b.stage, b.terminal, b.terminal_reason, b.failed_at)
        assert a.receipts == b.receipts and a.artifacts == b.artifacts
        assert a.params == b.params == g.params
        assert fresh.cycle_complete(g.id) == pl.cycle_complete(g.id)


def test_a_genome_cannot_be_started_twice(tmp_path):
    pl = _pipeline(tmp_path)
    g = _genome(45)
    pl.start(g)
    with pytest.raises(IllegalTransition):
        pl.start(Genome.from_vector(g.vector()))


def test_the_replayer_refuses_a_life_that_starts_in_the_middle(tmp_path):
    log = JsonlLog(tmp_path / "a.jsonl")
    log.append({"kind": "stage", "genome_id": "abc", "state": "MESHING"})
    with pytest.raises(LogTruncated):
        Pipeline(log.path)


# ---------------------------------------------------------------------------
# cycle_complete(): all five, or INCOMPLETE
# ---------------------------------------------------------------------------

def _complete_cycle(pl: Pipeline, g: Genome, omit: str | None = None) -> None:
    pl.start(g)
    if omit != "archive":
        for s in STAGE_ORDER[1:]:
            pl.advance(g.id, s)
        pl.succeed(g.id)
    if omit != "artifacts":
        pl.artifact(g.id, "stl", f"/tmp/{g.id}.stl")
    for name in RECEIPT_NAMES:
        if name != omit:
            pl.receipt(g.id, name)


def test_cycle_complete_requires_all_five_and_says_which_is_missing(tmp_path):
    """The user's explicit rule: anything short of all five is INCOMPLETE.

    Tested by REMOVING each condition in turn, not only by watching the happy
    path — a predicate only ever seen returning True is the same class of
    non-check as a bar with no test (incident 1 above).
    """
    assert set(CYCLE_REQUIREMENTS) == {"archive", "knowledge", "mutation_stats",
                                       "gap_queue", "artifacts"}
    pl = _pipeline(tmp_path)
    whole = _genome(70)
    _complete_cycle(pl, whole)
    assert pl.cycle_complete(whole.id)
    assert pl.cycle_missing(whole.id) == []

    for i, condition in enumerate(CYCLE_REQUIREMENTS):
        pl2 = Pipeline(tmp_path / f"omit_{condition}.jsonl")
        g = _genome(80 + i)
        _complete_cycle(pl2, g, omit=condition)
        assert not pl2.cycle_complete(g.id), (
            f"cycle_complete() returned True with {condition} missing")
        assert pl2.cycle_missing(g.id) == [condition]


def test_a_receipt_cannot_be_filed_for_work_the_record_must_prove(tmp_path):
    # 'archive' and 'artifacts' are satisfied by the terminal record and by a
    # real artifact record. A receipt a caller can type for either of them
    # would be a green light, not a check.
    pl = _pipeline(tmp_path)
    g = _genome(90)
    pl.start(g)
    for name in ("archive", "artifacts", "anything_else"):
        with pytest.raises(ValueError):
            pl.receipt(g.id, name)


def test_the_default_archive_path_is_gitignored():
    # gap J6: build artefacts that became tracked dirtied the tree on every
    # test run and conflicted on every cherry-pick. This one is a machine's own
    # history and must never be committed.
    ignore = (_ROOT / ".gitignore").read_text()
    assert "data/evolution/" in ignore
    assert ARCHIVE_PATH.name == "archive.jsonl"
    assert ARCHIVE_PATH.parent.name == "evolution"
