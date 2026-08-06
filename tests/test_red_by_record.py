"""Gate 0R — a bar a green suite MISSES is RED BY RECORD, never prose.

THE MOTIVATING INCIDENT (gap D11, measured 2026-08-06, fixed 2026-08-07).

`tests/test_phase4.py` passes everything it asserts, and one of the things it
honestly asserts is `f < 0.99` — the plan's generative feasibility bar being
MISSED. So the ladder printed:

    Gate 4  generative + slider p95<100ms; raw feasibility RED
            (GMM 79.3%, pPCA 88.7% vs the >=99% bar)          GREEN

A measured shortfall, in a `scope` string, on a row whose verdict was GREEN, in
a file whose own dataclass documents the neighbouring field as "human context;
NEVER load-bearing". A `scope` is no more load-bearing than a `detail`: the
number could be softened, reworded or deleted by editing one string, no ledger
row owned the clause, no `review_by` date could expire, and nothing anywhere
would have failed if the feasibility got worse.

That is gap D1 — `"RED"` -> `"AMBER"` bought exit 0 — surviving in the one
place D1's own fix did not reach: D1 typed the STATUS field and left the prose
fields able to carry the only copy of a measurement.

Gate 0G is the fence around the status machinery. This file is the fence around
the boundary between the registry and the ledger, and every test below performs
the attack rather than describing it.
"""

from __future__ import annotations

import re

import pytest

import navalai.gates as G

# The row this suite exists because of. Named once; every test reads it here so
# that renaming the row fails loudly rather than quietly skipping the fence.
CLAUSE_ROW = "Gate 4F"

# A number with a decimal point followed by a percent sign. This is what a
# MEASUREMENT looks like in prose; the bars in this registry ("<50ms",
# ">=95% of a 200-hull batch", ">=99%") are round and carry no decimal, which is
# what makes the distinction mechanical rather than a matter of taste.
_MEASUREMENT_IN_PROSE = re.compile(r"\d+\.\d+\s*%")


def _ledger() -> dict:
    return {k: v for k, v in G.load_ledger(None).items()
            if not k.startswith("_")}


# --------------------------------------------------------- the clause itself

def test_the_missed_feasibility_clause_is_its_own_typed_red_row():
    """It cannot ride on Gate 4, because Gate 4's suite genuinely passes.

    Splitting a clause into its own row is the same move as Gate 6R (a clause
    of Gate 6) and Gate 1H (a clause of Gate 1): the ladder should show WHICH
    clause is covered by what, and a clause that is not covered should be the
    row that says so.
    """
    row = next((g for g in G.GATES if g.name == CLAUSE_ROW), None)
    assert row is not None, (
        f"{CLAUSE_ROW} is gone. The raw-feasibility shortfall then has no row "
        f"that can fail, which is the state gap D11 recorded.")
    assert row.status == G.Verdict.RED
    assert row.suite is None, (
        "a status row runs no suite; if this clause acquires one, the row "
        "should go green by measurement, not by acquiring a passing test")


def test_the_clause_has_a_ledger_watermark_that_is_a_number():
    """A recorded red whose watermark is a sentence cannot regress.

    Gate 2M's watermark is deliberately the string "NONE — no reproducible
    measurement exists", which is the honest value when the run directory it
    was measured on has been deleted. This clause has no such excuse: the
    measurement is a 20-second `raw_feasibility()` call and the ledger carries
    the command that reproduces it.
    """
    entry = _ledger().get(CLAUSE_ROW)
    assert entry is not None, (
        f"{CLAUSE_ROW} is RED with no ledger entry. `judge_red` already fails "
        f"the ladder for this; the assertion is here so the reason is named.")
    wm = entry["watermark"]
    assert isinstance(wm, (int, float)) and not isinstance(wm, bool), (
        f"watermark {wm!r} is not a number, so 'REDDER than we recorded' "
        f"cannot be evaluated")
    assert entry["better_is"] == "up"
    assert "99" in entry["bar"], "the bar is the BuildPlan's 99%; do not soften it"
    assert wm < 99.0, (
        f"watermark {wm} clears the bar — this row should be GREEN and its "
        f"ledger entry deleted, not carried as an expected red")
    assert "raw_feasibility" in entry["verify"], (
        "the verify command must re-measure the model, not the rejection loop")


def test_the_bar_is_the_plans_bar_and_the_scope_says_so():
    """Honesty rule 6, mechanically. The cheapest way to make this row green is
    to write 80% where the plan says 99%, so both places that state the bar are
    read and both must still say 99."""
    row = next(g for g in G.GATES if g.name == CLAUSE_ROW)
    assert ">=99%" in row.scope.replace(" ", "")
    assert "99" in _ledger()[CLAUSE_ROW]["bar"]


# ------------------------------------------------------------- the attacks

def test_no_scope_or_detail_carries_a_measurement_the_ledger_owns():
    """THE ATTACK THAT SUCCEEDED, run against the whole registry.

    On 2026-08-06 Gate 4's scope read "raw feasibility RED (GMM 79.3%, pPCA
    88.7% vs the >=99% bar)". Both numbers were real, both were measured, and
    both were in the one kind of field this file's own dataclass says is never
    load-bearing. This test fails on that string, and on any future one like
    it, in any row.

    A gate row may state a BAR. It may not state a MEASUREMENT: measurements
    live in `data/gate-ledger.json`, which has an owner, a date and an
    expiry — gap J1's rule, applied to the registry that J1's fix created.
    """
    offenders = []
    for g in G.GATES:
        for field, value in (("scope", g.scope), ("detail", g.detail)):
            if _MEASUREMENT_IN_PROSE.search(value or ""):
                offenders.append(f"{g.name}.{field}: {value!r}")
    assert not offenders, (
        "these gate rows carry a measured figure in a prose field, where "
        "nothing can fail on it and nothing expires:\n  "
        + "\n  ".join(offenders)
        + "\nPut the number in data/gate-ledger.json and point at it.")

    # The other direction: a watermark must not have been copied out of the
    # ledger into the registry, which is the same number in two homes.
    for name, entry in _ledger().items():
        wm = entry.get("watermark")
        if not isinstance(wm, float):
            continue
        for g in G.GATES:
            assert str(wm) not in (g.scope + " " + (g.detail or "")), (
                f"{g.name} restates {name}'s watermark {wm}. One number, one "
                f"home; the ledger is the home.")


def test_rewording_the_clause_cannot_buy_a_pass(tmp_path, capsys):
    """D1's original attack, aimed at the new row.

    The registry is replaced by a single, cheerful-sounding version of the
    clause row and judged against a ledger that does not account for it. If the
    verdict followed the prose, this would exit 0.
    """
    led = tmp_path / "ledger.json"
    led.write_text("{}")
    real = G.GATES
    try:
        G.GATES = [G.Gate(CLAUSE_ROW, "generative feasibility: healthy",
                          status=G.Verdict.RED,
                          detail="nothing to see here")]
        rc = G.main(["--ledger", str(led)])
        out = capsys.readouterr().out
    finally:
        G.GATES = real
    assert rc == 1, "an unrecorded RED clause bought exit 0"
    assert "RED (NEW" in out, out


def test_deleting_the_ledger_entry_is_a_failure_not_a_silence(tmp_path, capsys):
    """The absent-record failure mode this repository keeps re-learning.

    `not ledger_has("Gate 2M")` was TRUE when no ledger existed at all, and the
    gap reconciler read that as a green gate. The ladder must go the other way:
    a red row the ledger does not mention is a NEW break, loudly.
    """
    led = tmp_path / "ledger.json"
    led.write_text('{"Gate 2M": {"metric": "m", "watermark": 1, "owner": "o", '
                   '"review_by": "2099-01-01", "measured_utc": "2026-01-01"}}')
    real = G.GATES
    try:
        G.GATES = [g for g in real if g.name == CLAUSE_ROW]
        assert len(G.GATES) == 1
        rc = G.main(["--ledger", str(led)])
        out = capsys.readouterr().out
    finally:
        G.GATES = real
    assert rc == 1 and "not in the ledger" in out, out


def test_the_recorded_clause_does_not_fail_the_ladder_on_its_own(capsys):
    """The complement, and the reason this is a LEDGER and not a blocklist: a
    red that is recorded, owned and in date is a known state, not a new break.
    Without this, the fix would just make the ladder permanently red and train
    everyone to ignore it — which is how a gate stops being a signal.
    """
    real = G.GATES
    try:
        G.GATES = [g for g in real if g.name == CLAUSE_ROW]
        rc = G.main([])
        out = capsys.readouterr().out
    finally:
        G.GATES = real
    assert rc == 0, out
    assert "review by" in out and "ml-engineer" in out


def test_gate_names_are_unique_because_the_ledger_is_keyed_on_them():
    """MEASURED 2026-08-07: `Gate 2R` was in the registry TWICE — CFD reference
    parity, and the tank-resonance diagnostic added a day later.

    A gate's name is the ledger's key. `judge_red` looks a red row up by it,
    the stale-entry check intersects a SET of names with the ledger, and Gate
    0G asserts `reds == ledger` on sets — so two rows sharing one name collapse
    to a single member and one ledger entry silently accounts for both. A row
    could then be red with no watermark of its own while the ladder exited 0.
    Nothing had gone wrong yet because neither row was red; the collision is
    the kind that only bites the day something else changes.
    """
    names = [g.name for g in G.GATES]
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, (
        f"duplicate gate names {dupes}: the ledger is keyed on the name, so "
        f"one entry would account for two rows")


@pytest.mark.parametrize("row", ["Gate 4", "Gate 4F"])
def test_both_halves_of_gate_4_are_on_the_ladder(row):
    """A reader of the front door must be able to get from the green half to
    the red one. Gate 4's scope names Gate 4F for exactly that reason."""
    assert any(g.name == row for g in G.GATES)
    if row == "Gate 4":
        g4 = next(g for g in G.GATES if g.name == "Gate 4")
        assert CLAUSE_ROW in g4.scope, (
            "Gate 4 prints GREEN; if it does not point at the row carrying its "
            "missed clause, the miss is invisible at the front door again")
