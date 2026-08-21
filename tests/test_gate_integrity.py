"""Gate 0G — the ladder itself cannot be talked into passing.

Motivating incident (adversarial review, 2026-08-05). Working proofs showed a
measured RED gate could be erased by editing one prose string, and a failing
gate test silenced by one line:

    "RED (measured): C_t -15.4%"   -> exit 1   (correct)
    "AMBER (measured): C_t -15.4%" -> exit 0
    "METAL-GATED: C_t -15.4%"      -> exit 0
    blocked=None                   -> exit 0
    delete the row                 -> exit 0
    @pytest.mark.xfail             -> GREEN, with no annotation at all
    importorskip in one test       -> "GREEN (1 skipped)"
    conftest printing "20 passed"  -> GREEN on a suite that ran nothing

The tests below are the fence. They are deliberately adversarial: each one
performs the attack and asserts it fails.
"""

from __future__ import annotations

import json
import pathlib
from datetime import date

import pytest

import navalai.gates as G

_ROOT = pathlib.Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- the registry

def test_every_test_file_is_owned_by_a_gate():
    """A suite nobody runs is a suite nobody trusts — and deleting a row from
    GATES used to make its gate silently disappear.

    This file used to be the one exception, on the grounds that the gate
    checking the gates is not itself a gate. That was backwards: it is the row
    whose disappearance would be least noticed. It is Gate 0G now, and there
    is no exception list left.
    """
    on_disk = {f"tests/{p.name}" for p in _ROOT.joinpath("tests").glob("test_*.py")}
    owned = {g.suite for g in G.GATES if g.suite}
    orphans = on_disk - owned
    assert not orphans, f"test files with no gate: {sorted(orphans)}"


def test_a_gate_row_must_verify_something_or_declare_why_not():
    with pytest.raises(ValueError, match="exactly one of"):
        G.Gate("Gate Q", "verifies nothing")
    with pytest.raises(ValueError, match="exactly one of"):
        G.Gate("Gate Q", "both", suite="tests/test_phase0.py",
               status=G.Verdict.RED)


def test_a_status_cannot_be_renamed_into_passing():
    # THE original attack, verbatim: "RED" -> "AMBER" bought exit 0.
    for bogus in ("AMBER", "RED (measured): missed its bar", "PENDING", "red"):
        with pytest.raises(ValueError, match="not a Verdict"):
            G.Gate("Gate Q", "scope", status=bogus)


def test_every_red_gate_has_a_ledger_entry_and_vice_versa():
    ledger = {k for k in G.load_ledger(None) if not k.startswith("_")}
    reds = {g.name for g in G.GATES if g.status == G.Verdict.RED}
    assert reds == ledger, (
        f"ledger and RED set disagree: only-in-gates={sorted(reds - ledger)}, "
        f"only-in-ledger={sorted(ledger - reds)}")


@pytest.mark.parametrize("field", ["metric", "watermark", "units", "better_is",
                                   "bar", "measured_utc", "measured_on",
                                   "owner", "verify", "review_by", "why_red"])
def test_ledger_entries_are_attributable(field):
    """A recorded red with no owner, no measurement date and no review date is
    not a record — it is an excuse with a JSON schema.

    WIDENED 2026-08-11, when Gate 6D was added. The list checked seven fields
    while every entry in the file carried eleven: `units`, `better_is`, `bar`
    and `measured_on` were house convention held up by nothing. A watermark
    with no units and no `better_is` cannot be compared in either direction —
    "REDDER than we recorded" is undefined for a bare number — and a bar that
    is not written down is a bar that can be remembered generously. They were
    present in all four existing entries, so widening the check cost nothing
    and closed the gap through which a fifth entry could have arrived without
    them."""
    for name, entry in G.load_ledger(None).items():
        if name.startswith("_"):
            continue
        assert entry.get(field) not in (None, "", []), f"{name} lacks {field}"


def test_ledger_review_dates_are_parseable_and_not_already_expired():
    today = date.today()
    for name, entry in G.load_ledger(None).items():
        if name.startswith("_"):
            continue
        due = date.fromisoformat(entry["review_by"])
        assert due >= today, (
            f"{name} ledger entry expired {due} — re-measure it or sign a "
            f"dated extension; do not extend it silently")


# ---------------------------------------------------------------- the verdicts

def test_an_unrecorded_red_is_a_failure_and_a_recorded_one_is_not():
    ledger = {"Gate 2M": {"metric": "m", "watermark": -79.8, "owner": "o",
                          "review_by": "2099-01-01", "measured_utc": "2026-08-05"}}
    assert G.judge_red("Gate 2M", ledger, date(2026, 8, 6))[1] is False
    assert G.judge_red("Gate NEW", ledger, date(2026, 8, 6))[1] is True


def test_an_expired_ledger_entry_fails():
    ledger = {"Gate 2M": {"metric": "m", "watermark": 1, "owner": "o",
                          "review_by": "2026-01-01", "measured_utc": "2025-01-01"}}
    label, fail = G.judge_red("Gate 2M", ledger, date(2026, 8, 6))
    assert fail is True and "EXPIRED" in label


def test_a_recovered_gate_must_not_leave_its_ledger_entry_behind(tmp_path, capsys):
    """A stale ledger is how an expected-red list becomes a list of things
    nobody rechecks."""
    led = tmp_path / "ledger.json"
    led.write_text('{"Gate 0": {"metric": "m", "watermark": 1, "owner": "o", '
                   '"review_by": "2099-01-01", "measured_utc": "2026-01-01"}}')
    real = G.GATES
    try:
        # The fixture needs A green suite, nothing about phase0 — and
        # phase0 carries a 1 ms wall-clock bar that fails under load, which
        # made THIS meta-test flaky-by-hostage (2026-08-18, box under a
        # concurrent full-suite run). test_formlib is deterministic, sub-
        # second and timing-free.
        G.GATES = [G.Gate("Gate 0", "green suite", "tests/test_formlib.py")]
        rc = G.main(["--ledger", str(led)])
        assert rc == 1
        assert "LEDGER STALE" in capsys.readouterr().out
    finally:
        G.GATES = real


# ---------------------------------------------------------------- the silencers

def test_xfail_and_xpass_are_failures_not_decorations():
    # One line — @pytest.mark.xfail(reason='known gap') — turned a failing
    # gate test GREEN with no annotation, because "xfailed" matched none of
    # the alternations the old parser knew.
    label, fail = G.status_of(0, G.counts("= 19 passed, 1 xfailed in 1.0s ="))
    assert fail is True and "xfail" in label
    label, fail = G.status_of(0, G.counts("= 19 passed, 1 xpassed in 1.0s ="))
    assert fail is True


def test_a_suite_that_ran_nothing_is_never_green():
    label, fail = G.status_of(0, G.counts("= 20 skipped in 1.0s ="))
    assert label.startswith("SKIPPED") and fail is False


def test_stdout_cannot_spoof_the_summary_line():
    # A conftest printing "wrote report.xml: 20 passed" AFTER the summary used
    # to win, because the parser scanned in reverse and broke on first match.
    out = "= 20 skipped in 1.0s =\nwrote report.xml: 20 passed\n"
    c = G.counts(out)
    assert c["passed"] == 0 and c["skipped"] == 20
    assert G.status_of(0, c)[0].startswith("SKIPPED")


def test_ansi_colour_does_not_defeat_the_parser():
    # pytest colourises the summary; the anchor must survive it.
    c = G.counts("\x1b[32m= \x1b[1m9 passed\x1b[0m, 2 skipped in 1.0s =\x1b[0m")
    assert c["passed"] == 9 and c["skipped"] == 2


def test_a_partial_skip_still_says_so_out_loud():
    label, fail = G.status_of(0, G.counts("= 9 passed, 2 skipped in 1s ="))
    assert label == "GREEN (2 skipped)" and fail is False


# ------------------------------------------- a DECLARED skip, and its limits
#
# MOTIVATING INCIDENT: CI run 31611386179 on commit 0798182. The `--strict`
# tier printed
#
#     Gate 2B  Blender-native hull generation   SKIPPED (7 skipped in 0.13s)
#     Gate 2G  KCS benchmark geometry           SKIPPED (2 skipped in 0.02s)
#     2 gate(s) ran no tests ... FAILING (--strict).
#
# on every run, and no hosted runner can fix either: there is no Blender on a
# GitHub runner, and scripts/fetch_benchmark_geom.py refuses by design to
# re-host the registration-walled KCS IGES. A check that can never pass is the
# defect .github/workflows/gates.yml exists to remove.
#
# `Requirement` narrows the excuse to a named, PROBED environment fact. These
# four tests are the fence, and they are adversarial in the shape
# docs/LESSONS.md defect class 3 demands: the second one feeds the mechanism
# the VERBATIM case it must refuse (a declared requirement that is PRESENT),
# because a test showing a guard accepts a good case proves nothing about
# rejection.

def _skipped_run(monkeypatch, gates):
    """Run main() with every suite forced to report 'ran nothing'."""
    class _R:
        returncode = 0
        stdout = "= 20 skipped in 1.0s =\n"
    monkeypatch.setattr(G.subprocess, "run", lambda *a, **k: _R())
    monkeypatch.setattr(G, "GATES", gates)
    return G.main(["--strict"])


def _row(**kw):
    return G.Gate("Gate Q", "a suite that ran nothing",
                  "tests/test_phase0.py", **kw)


def test_an_undeclared_skip_still_fails_strict(monkeypatch, capsys):
    """THE RULE THAT SURVIVES. Nothing about Requirement relaxes this."""
    assert _skipped_run(monkeypatch, [_row()]) == 1
    assert "did NOT declare why" in capsys.readouterr().out


def test_a_declared_skip_whose_requirement_is_ABSENT_does_not_fail_strict(
        monkeypatch, capsys):
    req = G.Requirement(what="the Blender binary", why="no runner has one",
                        probe=lambda: False)
    assert _skipped_run(monkeypatch, [_row(requires=req)]) == 0
    out = capsys.readouterr().out
    # loud, not silent: the reason is printed on the row AND in the summary
    assert "the Blender binary" in out and "no runner has one" in out
    assert "DECLARED, PROBED" in out


def test_a_declared_skip_whose_requirement_is_PRESENT_is_a_failure(
        monkeypatch, capsys):
    """THE ATTACK. Declaring a requirement must not buy a pass once the thing
    it names is installed — otherwise `Requirement` is the blanket
    "ignore skips" flag it was written instead of. It fails WITHOUT --strict
    too, so no CI tier can opt out of it."""
    req = G.Requirement(what="the Blender binary", why="no runner has one",
                        probe=lambda: True)
    assert _skipped_run(monkeypatch, [_row(requires=req)]) == 1
    assert "could have run and did not" in capsys.readouterr().out

    class _R:
        returncode = 0
        stdout = "= 20 skipped in 1.0s =\n"
    monkeypatch.setattr(G.subprocess, "run", lambda *a, **k: _R())
    monkeypatch.setattr(G, "GATES", [_row(requires=req)])
    assert G.main([]) == 1, "no --strict, and it must STILL fail"


def test_a_requirement_that_cannot_be_PROBED_is_a_failure_not_a_pass(
        monkeypatch, capsys):
    """docs/LESSONS.md defect class 1, applied to this mechanism before it can
    produce an instance of it: `${_MQ_SKEW:-0}` turned "I could not measure
    this" into a perfect score. A probe that raises means the prerequisite is
    UNKNOWN, and unknown is never satisfied."""
    def boom():
        raise OSError("no such file")
    req = G.Requirement(what="the Blender binary", why="no runner has one",
                        probe=boom)
    assert _skipped_run(monkeypatch, [_row(requires=req)]) == 1
    assert "could NOT BE PROBED" in capsys.readouterr().out


def test_a_status_row_cannot_carry_a_requirement():
    """A status row runs nothing by construction, so a Requirement on one
    would excuse a gate that never had a suite to skip."""
    with pytest.raises(ValueError, match="meaningless on a status row"):
        G.Gate("Gate Q", "scope", status=G.Verdict.RED,
               requires=G.Requirement(what="x", why="y", probe=lambda: False))


@pytest.mark.parametrize("name", ["Gate 2B", "Gate 2G"])
def test_the_two_declared_gates_probe_the_same_thing_their_suite_does(name):
    """A declaration nobody checked against the suite is prose. Both probes
    must agree with the suite's own skip condition ON THIS MACHINE, or the
    row would read "could have run and did not" for a suite that honestly
    cannot."""
    g = next(x for x in G.GATES if x.name == name)
    assert g.requires is not None and g.suite is not None
    here = g.requires.present()          # must not raise on any machine
    if name == "Gate 2B":
        from navalai.blender.run import have_blender
        assert here is have_blender()
    else:
        assert here is (_ROOT / "data/benchmark_geom/kcs.stl").exists()


# ------------------------------------------------------------- the documents
#
# GAP J2. Five different Gate 2M numbers circulated at once because five
# documents each held their own copy of one measurement (gap J1), and README's
# per-gate test counts were stale throughout (Gate 1 said 13 against 22
# actual, Gate 2 said 4 against 18, Gate D said 12 against 19) while Gate 2U
# — RED — had no row in the front door at all. Doc drift is a defect class
# here, not cosmetics, so it gets a gate like any other.

def test_the_readme_gate_table_agrees_with_the_runner():
    """The one mechanism that stops this drifting again.

    Fix a failure with `python -m navalai.gates --readme --write`, never by
    hand — a hand-edited copy of a generated table is the defect.
    """
    counts = G.collect_counts()
    missing = [g.suite for g in G.GATES
               if g.suite and counts.get(g.suite, 0) == 0]
    if missing:
        pytest.skip(f"collection is empty for {missing} — an optional "
                    f"dependency is absent, which is an environment fact and "
                    f"must not be baked into the README as '0 tests'")
    readme = (_ROOT / "README.md").read_text()
    block = G.readme_block(counts)
    assert block in readme, (
        "README.md's gate table is out of date. Regenerate it:\n"
        "    python -m navalai.gates --readme --write")


def test_the_readme_carries_all_six_honesty_rules():
    """It listed five. Rule 6 — 'never soften a failing gate threshold to make
    it pass' — is the rule under which Gate 2M, 2U and now 6R are recorded RED
    rather than reworded, so its absence from the front door was the least
    affordable of the six."""
    readme = (_ROOT / "README.md").read_text()
    rules = readme.split("## Honesty rules")[1].split("##")[0]
    for n in range(1, 7):
        assert f"\n{n}." in rules, f"honesty rule {n} missing from README"
    assert "soften" in rules.lower()


def test_no_document_restates_a_gate_2m_figure():
    """Gap J1. `data/gate-ledger.json` is the one place a Gate 2M measurement
    lives. A document that restates one is a document that will be superseded
    silently — which is exactly what happened to -151%, twice.
    """
    superseded = ("9.33e-3", "-151%", "−151%", "4.283e-3", "-15.4%", "−15.4%",
                  "3.8958e-3", "7.3706e-3")
    # CLAUDE.md ADDED 2026-08-11, and it was carrying two of them. MEASURED:
    # `4.283e-3` and `-15.4%` sat in its Gate 2M section, purged from every
    # other document when J1 closed and surviving here for five days because
    # this list did not name the file. That is the fence with a hole in it, in
    # the ONE document every agent session is told to read as the authority —
    # the worst possible place for a superseded measurement to persist.
    #
    # docs/ IS DELIBERATELY NOT SCANNED. docs/GAP-REGISTER.md and
    # docs/CFD-BLOCKER-BRIEF.md both quote `9.33e-3`, correctly: the register is
    # an immutable audit record and the brief is explicitly marked SUPERSEDED.
    # A record that quotes a retired figure IN ORDER TO RETIRE IT is doing its
    # job; banning it there would delete the history this rule exists to keep.
    for name in ("README.md", "PLM.md", "MACBOOK.md", "ALIGNMENT.md",
                 "CLAUDE.md"):
        text = (_ROOT / name).read_text()
        hits = [s for s in superseded if s in text]
        assert not hits, (
            f"{name} restates superseded Gate 2M figures {hits}. Point at "
            f"data/gate-ledger.json instead; the register's J1 row and the "
            f"ledger's why_red carry the history.")


# ----------------------------------------------------- the records it rests on

def test_the_benchmark_geometry_record_is_committed_though_the_geometry_is_not():
    """Gap J5. `data/benchmark_geom/` is gitignored, so the KCS acceptance
    check silently skipped everywhere but the machine that generated the file.
    This assertion never skips: on every machine the repository must say what
    the missing file is and how to make it."""
    rec = json.loads(
        (_ROOT / "data/benchmark_geom/CHECKSUMS.json").read_text())["kcs.stl"]
    assert len(rec["sha256"]) == 64 and rec["bytes"] > 0
    assert rec["recipe"] and rec["source_document"]
    assert (_ROOT / "scripts/fetch_benchmark_geom.py").exists()
    assert any(g.suite == "tests/test_benchmark_geom.py" for g in G.GATES), (
        "the geometry needs a GATE ROW, or its absence is an invisible skip "
        "again")


def test_the_geometry_acceptance_bar_is_measured_and_can_fail():
    """Gap F18 and gap J1's lesson in one place. benchmarks/kcs.py records
    -0.09% on displacement; re-measuring the actual file gives -0.267% and
    that test's rel=0.01 hides the 0.18% disagreement. The record carries the
    number MEASURED on the file it describes.

    And the bar has to be able to fail: it must admit an OCC-version
    difference in the tessellation while rejecting every recipe error it
    exists to catch, all of which are tens of percent.
    """
    rec = json.loads(
        (_ROOT / "data/benchmark_geom/CHECKSUMS.json").read_text())["kcs.stl"]
    a = rec["acceptance"]
    err = (a["measured_m3"] - a["published_m3"]) / a["published_m3"] * 100.0
    assert err == pytest.approx(a["error_pct"], abs=0.01)
    assert abs(err) < a["tolerance_pct"] < 5.0
    for factor, label in [(0.5, "unmirrored half body"),
                          (2.0, "z=0 at the keel, not the waterline"),
                          (1e9, "millimetres read as metres")]:
        wrong = a["measured_m3"] * factor
        bad = abs(wrong - a["published_m3"]) / a["published_m3"] * 100.0
        assert bad > a["tolerance_pct"], label


def test_every_ledger_verify_names_something_that_exists():
    """The ledger's `verify` is the only thing that makes a watermark checkable.

    GENERALISED 2026-08-12 from a guard that covered ONE ROW and could not
    fail. `test_the_gate2m_ledger_entry_points_at_something_real` hardcodes
    ["Gate 2M"] and asserts that each `runs/...` path its verify names still
    exists — but no verify command references a `runs/` path any more, so the
    loop body never executes and the assertion is vacuous. A guard that cannot
    fire is docs/LESSONS.md defect class 3, and this file is where that class
    is supposed to be caught.

    The rule with teeth is the one that generalises: whatever a verify command
    INVOKES must exist. A watermark whose reproduction instructions name a
    deleted script is gap N6 in a new place — the number outlives the evidence
    and nothing says so.

    MEASURED at the time of writing, all five RED rows pass:

        Gate 2M  scripts/make_case.py, scripts/run_campaign.sh, scripts/gate2m.py
        Gate 2U  scripts/mesh_robustness.py
        Gate 4F  tests/test_surrogate_honesty.py
        Gate 6D  tests/test_manufacturing.py
        Gate 6R  tests/test_phase6r.py
    """
    import re

    led = json.loads((_ROOT / "data/gate-ledger.json").read_text())
    checked = 0
    for gate, entry in led.items():
        if not isinstance(entry, dict) or "verify" not in entry:
            continue
        verify = entry["verify"]
        verify = " ".join(verify) if isinstance(verify, list) else str(verify)
        refs = re.findall(
            r"(?:scripts|navalai|tests|data|docs)/[A-Za-z0-9_./-]+"
            r"\.(?:py|json|md|sh)", verify)
        assert refs, (
            f"{gate}: its verify command names no file at all, so nobody can "
            f"tell what would reproduce the watermark — {verify[:120]!r}")
        for ref in refs:
            assert (_ROOT / ref).exists(), (
                f"{gate}: verify names {ref}, which does not exist. A verify "
                f"that cannot run is not a verification, and the watermark "
                f"beside it is unreproducible.")
            checked += 1
    assert checked >= 5, (
        f"only {checked} verify references checked; the fence went blind")


def test_judge_red_regression_rule_R03():
    """AUDIT G0-01 (2026-08-14): the ledger README promised "a RED gate worse
    than watermark -> FAIL (it regressed)" while `judge_red` never read
    `better_is` at all — the rule the ledger exists for was prose. The fresh
    figure arrives via `--measured` (this function cannot re-run a CFD
    campaign); comparison per `better_is`, void/non-numeric watermarks are
    UNCOMPARABLE, and a fresh number against an uncomparable watermark FAILS
    so the ledger must be re-based before the number is read as a verdict."""
    from datetime import date

    led = {
        "G-up": {"watermark": 50.0, "better_is": "up",
                 "review_by": "2027-01-01"},
        "G-dn": {"watermark": 10.0, "better_is": "down",
                 "review_by": "2027-01-01"},
        "G-tz": {"watermark": -3.0, "better_is": "toward_zero",
                 "review_by": "2027-01-01"},
        "G-void": {"watermark": 27.8, "better_is": "up",
                   "review_by": "2027-01-01",
                   "calibration_void": "measured on the retired genome"},
        "G-str": {"watermark": "NONE", "better_is": "up",
                  "review_by": "2027-01-01"},
        "G-bad": {"watermark": 5.0, "better_is": "sideways",
                  "review_by": "2027-01-01"},
    }
    t = date(2026, 8, 14)
    # (gate, fresh measurement, must_fail, marker expected in the label)
    cases = [
        ("G-up", 40.0, True, "REGRESSED"),
        ("G-up", 60.0, False, "IMPROVED"),
        ("G-up", 50.0, False, "not worse"),
        ("G-dn", 12.0, True, "REGRESSED"),
        ("G-dn", 8.0, False, "IMPROVED"),
        ("G-tz", -5.0, True, "REGRESSED"),
        ("G-tz", 1.0, False, "IMPROVED"),
        ("G-void", 33.0, True, "UNCOMPARABLE"),
        ("G-void", None, False, "UNCOMPARABLE"),
        ("G-str", 33.0, True, "UNCOMPARABLE"),
        ("G-str", None, False, "UNCOMPARABLE"),
        ("G-bad", 4.0, True, "no "),
    ]
    for name, m, must_fail, marker in cases:
        label, fail = G.judge_red(name, led, t, measured=m)
        assert fail is must_fail, (name, m, label)
        assert marker in label, (name, m, label)
    # Without a fresh measurement a comparable entry behaves as it always
    # did: expected, not a failure, no comparison implied.
    label, fail = G.judge_red("G-up", led, t)
    assert fail is False and "REGRESSED" not in label


def test_no_document_renames_an_executable_gate_letter():
    """MEASURED 2026-08-21. `docs/audit/GATE2-PHYSICS-STACK.md` introduced a
    physics ladder written `2A`..`2H`, and SEVEN of those eight letters were
    already executable gates in `navalai/gates.py` meaning something else:
    2A was the CFD-admissibility screen, not hydrostatics; 2C the campaign
    classifier, not DSYHS; 2G "the KCS STL is on disk", not waves and RAOs.

    2G is the one that bites. The runner prints it SKIPPED when the gitignored
    benchmark geometry is absent — by design, loudly — and a reader holding the
    document's meaning reads that as SEAKEEPING IS UNVERIFIED. That is the
    project's signature defect, A NAME DECLARED TWICE, applied to gate
    identifiers instead of to numbers.

    The executable rows are the incumbents (README, the ledger and eleven test
    modules cite them), so the physics ladder took the `2-PHYS-*` namespace.
    This fence keeps it there: no document may attach a physics-ladder meaning
    to a letter the runner has already spent.
    """
    executable = {g.name for g in G.GATES}
    # Words that mean the PHYSICS ladder's rung, not the executable gate.
    physics_words = ("hydrostatic", "wigley", "dsyhs", "planing", "seakeep",
                     "added resistance", "rao", "naples", "hard-chine")
    doc = _ROOT / "docs" / "audit" / "GATE2-PHYSICS-STACK.md"
    raw = doc.read_text()
    # The document explains the collision with a table that necessarily QUOTES
    # the taken letters. That region is fenced by markers and excluded here --
    # excluded by an explicit delimiter rather than by loosening the pattern,
    # so a new bare `Gate 2G` written anywhere else still trips the test.
    assert raw.count("<!-- COLLISION-EXPLANATION BEGIN -->") == 1
    head, rest = raw.split("<!-- COLLISION-EXPLANATION BEGIN -->", 1)
    explanation, tail = rest.split("<!-- COLLISION-EXPLANATION END -->", 1)
    text = head + tail
    for letter in "ABCDEFGH":
        if f"Gate 2{letter}" not in executable:
            continue
        # A bare `2A`/`Gate 2A` token in the physics document is forbidden:
        # the ladder must say 2-PHYS-A.
        for token in (f"Gate 2{letter}", f"**2{letter}**"):
            assert token not in text, (
                f"{doc.name} uses {token!r}, which navalai/gates.py already "
                f"defines as an executable gate with a different meaning. "
                f"The physics rung is 2-PHYS-{letter}."
            )
    # And the ladder actually uses its own namespace for every rung it claims.
    for letter in "ABCDEFGH":
        assert f"2-PHYS-{letter}" in text, f"rung 2-PHYS-{letter} missing"
    # The collision must stay EXPLAINED, not merely fixed: the next author
    # reaching for `2A` needs to find out why it is taken.
    assert "A NAME DECLARED TWICE" in explanation
    assert "2-PHYS-" in (_ROOT / "navalai" / "gates.py").read_text(), (
        "gates.py's own comment used both meanings a dozen lines apart; the "
        "corrected namespace must be visible where the gates are defined"
    )
