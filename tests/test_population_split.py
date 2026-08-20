"""M6: development / validation / held-out, and the fence that keeps them apart.

MEASURED 2026-08-20. Every Gate 2U artifact in `data/` records `seed = 0`,
and they are NOT one population: the 15-gene banks and the 16-gene banks
share ZERO hulls (0 of 25 by waterline length, 0 as a set), because
`sample_valid` draws from `default_rng(seed)` and adding a gene changes the
draw sequence. The same seed named two different populations, which is this
codebase's cardinal defect -- a thing declared twice -- applied to the
evidence base itself.
"""
import json
import pathlib

import pytest

from navalai import population as P

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DATA = _ROOT / "data"


def test_the_seed_is_not_an_identity_and_the_arity_is_part_of_it():
    """`seed=0` is ambiguous across a grammar change; `(arity, seed)` is not."""
    assert P.population_id(15, 0, 74) != P.population_id(16, 0, 74)
    assert P.population_id(16, 0, 25) == P.population_id(16, 0, 25)
    # and a population with no declared seed must not masquerade as one
    assert "UNKNOWN" in P.population_id(16, None)


def test_an_undeclared_seed_is_UNKNOWN_and_never_silently_development():
    """The dangerous default. If an unrecognised seed fell through to 'dev'
    the fence below would license tuning on anything at all."""
    assert P.split_of_seed(P.DEV_SEED) == P.SPLIT_DEV
    assert P.split_of_seed(P.VAL_SEED) == P.SPLIT_VAL
    assert P.split_of_seed(P.HOLDOUT_SEED) == P.SPLIT_HOLDOUT
    for stranger in (7, 1234, -1, None):
        assert P.split_of_seed(stranger) == P.SPLIT_UNKNOWN
        assert not P.may_tune_on(stranger)


def test_the_three_seeds_are_distinct():
    seeds = {P.DEV_SEED, P.VAL_SEED, P.HOLDOUT_SEED}
    assert len(seeds) == 3, "a split that shares a seed is not a split"


def test_NO_ARTEFACT_MAY_BE_DRAWN_FROM_THE_VALIDATION_OR_HELD_OUT_SEED():
    """THE FENCE. This is what makes 'never used to tune' checkable.

    A promise that a held-out set was not tuned against is worth nothing --
    the whole point of the operator's SS13 is that repeated tuning against
    the same cases is invisible in the result. So it is enforced from the
    other side: any campaign artifact committed under `data/` is BY
    DEFINITION something a session looked at and reacted to, and therefore
    must not carry the validation or held-out seed.

    If this fails, the held-out set is BURNED. Do not relax the test; draw a
    new held-out seed and record that the old one was spent.
    """
    offenders = []
    for path in sorted(_DATA.glob("*.json")):
        try:
            doc = json.loads(path.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        seed = doc.get("seed")
        split = P.split_of_seed(seed)
        if split in (P.SPLIT_VAL, P.SPLIT_HOLDOUT):
            offenders.append(f"{path.name}: seed {seed} is the {split} set")
    assert not offenders, (
        "a committed artifact draws from a protected population:\n    "
        + "\n    ".join(offenders))


def test_the_15_gene_banks_are_HISTORY_because_this_tree_cannot_regenerate_them():
    """The 74-hull bank is the largest evidence base here and today's code
    cannot reproduce one hull of it.

    `is_regenerable` is the honest gate on quoting a rate: a percentage whose
    denominator cannot be reconstructed is a percentage of an unnamed set.
    Same defect as a ledger watermark pointing at a deleted run directory
    (gap N6), applied to a population.
    """
    assert P.current_arity() == 16, (
        "the grammar arity changed; the population ids in "
        "navalai/population.py are stale and the banks must be re-labelled")
    assert not P.is_regenerable(15)
    assert P.is_regenerable(16)


def test_every_gate2u_bank_can_be_told_which_stream_it_belongs_to():
    """A bank that cannot be placed in a stream cannot be compared to any
    other bank, so this refuses silence rather than guessing."""
    banks = sorted(_DATA.glob("gate2u-*.json"))
    if not banks:
        pytest.skip("no gate2u banks in this checkout")
    unplaceable = []
    for path in banks:
        try:
            doc = json.loads(path.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        rows = doc.get("rows") or []
        if not rows:
            continue          # an empty bank carries no claim
        if doc.get("seed") is None:
            unplaceable.append(f"{path.name}: {len(rows)} rows and NO seed")
    assert not unplaceable, (
        "these banks carry rows but no seed, so nothing can say which "
        "population they measured:\n    " + "\n    ".join(unplaceable))
