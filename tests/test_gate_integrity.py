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

import pathlib
from datetime import date

import pytest

import navalai.gates as G

_ROOT = pathlib.Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- the registry

def test_every_test_file_is_owned_by_a_gate():
    """A suite nobody runs is a suite nobody trusts — and deleting a row from
    GATES used to make its gate silently disappear."""
    on_disk = {f"tests/{p.name}" for p in _ROOT.joinpath("tests").glob("test_*.py")}
    owned = {g.suite for g in G.GATES if g.suite}
    orphans = on_disk - owned - {"tests/test_gate_integrity.py"}
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


@pytest.mark.parametrize("field", ["metric", "watermark", "owner", "verify",
                                   "measured_utc", "review_by", "why_red"])
def test_ledger_entries_are_attributable(field):
    """A recorded red with no owner, no measurement date and no review date is
    not a record — it is an excuse with a JSON schema."""
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
        G.GATES = [G.Gate("Gate 0", "green suite", "tests/test_phase0.py")]
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
