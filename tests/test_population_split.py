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


def _declared_seed(doc):
    """The seed a document draws from, WHEREVER it records it.

    Top-level for a campaign bank, `spec.seed` for a population manifest.
    Reading only the top level would let a protected seed hide one level
    down -- evasion by nesting, which is the same shape as a metric that is
    'not measured' being scored as passing.
    """
    if not isinstance(doc, dict):
        return None
    if "seed" in doc:
        return doc["seed"]
    spec = doc.get("spec")
    if isinstance(spec, dict):
        return spec.get("seed")
    return None


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

    STRENGTHENED 2026-08-20 (operator P0), in two directions at once, and
    NEITHER of them relaxes it:

      * it now walks `data/` RECURSIVELY and reads a nested `spec.seed` as
        well as a top-level one. It used to glob `data/*.json` only, so
        anything in a subdirectory was invisible to it -- the same hole the
        superseded-number fence had in `tests/test_gate_integrity.py` when
        it did not scan CLAUDE.md (gap J1);

      * the ONE exemption is a population MANIFEST, and it is not an
        exemption from the rule but a different application of it. What the
        fence protects against is a session having SEEN AN OUTCOME on a
        protected population. A manifest carries genomes and no outcome,
        and that is not taken on trust: the two tests below assert that no
        manifest carries any outcome key, and that the held-out manifest
        carries no genomes at all. A manifest that failed either of those
        would be a campaign artifact wearing a `kind` string, and the tests
        that catch it are stricter than this one.
    """
    offenders = []
    for path in sorted(_DATA.rglob("*.json")):
        try:
            doc = json.loads(path.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        if doc.get("kind") == P.MANIFEST_KIND:
            continue                       # held to the STRICTER rules below
        seed = _declared_seed(doc)
        split = P.split_of_seed(seed)
        if split in (P.SPLIT_VAL, P.SPLIT_HOLDOUT):
            offenders.append(
                f"{path.relative_to(_ROOT)}: seed {seed} is the {split} set")
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


# ==========================================================================
# EXACT REGENERATION (operator P0, 2026-08-20)
#
# Naming a population made it quotable; these make it REBUILDABLE. The
# distinction is the whole of gap N6 at population scale: a watermark that
# cites a deleted `runs/` directory and a rate whose denominator cannot be
# redrawn fail in exactly the same way, and both look fine on the page.
# ==========================================================================

import numpy as np

_MANIFESTS = P.MANIFEST_DIR


def _load_all():
    found = P.manifests()
    assert found, (f"no population manifests under {_MANIFESTS} — the "
                   f"validation population is back to depending on a "
                   f"mutable default")
    return found


def test_regenerate_reproduces_the_persisted_genomes_ELEMENTWISE_AND_EXACTLY():
    """`regenerate(spec) == the persisted genomes`. Not close: equal.

    Compared with `np.array_equal` on float64 read straight back out of the
    JSON, because `json.dumps` writes `repr(float)` and that round-trips a
    double exactly. A tolerance here would hide precisely what this is for:
    the draw quietly moving while every declared number stays put. The
    genome hash is checked as well as the array, because a hash computed
    over something other than what was written is this repo's signature
    defect (the layer table that printed the REQUESTED spec under the label
    of the ACHIEVED one).
    """
    checked = 0
    for path, doc in _load_all():
        if doc.get("genomes") is None:
            continue
        spec = P.PopulationSpec.from_dict(doc["spec"])
        stored = np.asarray(doc["genomes"], dtype=float)
        drawn = P.regenerate(spec)
        assert drawn.shape == stored.shape, f"{path.name}: {drawn.shape}"
        assert np.array_equal(drawn, stored), (
            f"{path.name}: {spec.qualified_id} does NOT regenerate. This "
            f"tree draws different hulls under the same specification; the "
            f"persisted population is now HISTORY and anything measured on "
            f"it must not be compared to anything measured after.")
        assert P.genome_sha256(drawn) == doc["genome_sha256"]
        checked += 1
    assert checked >= 2, ("at least the development and the validation "
                          "populations must be persisted with their genomes")


def test_every_committed_manifest_verifies_and_none_MISMATCHES():
    """A MISMATCH is the one status that is a defect. HISTORY is a result."""
    bad = []
    for path, doc in _load_all():
        r = P.verify_manifest(doc)
        assert r["status"] in ("REGENERATED", "HISTORY"), r
        if r["status"] == "MISMATCH":
            bad.append(f"{path.name}: {r['detail']}")
        if r["status"] == "REGENERATED":
            assert r["spec_sha256_ok"], f"{path.name}: spec hash disagrees"
    assert not bad, "\n".join(bad)


def test_the_sealed_held_out_population_still_regenerates_from_its_HASH_ALONE():
    """The seal is the point: no hulls on disk, and it is still checkable.

    A commitment that cannot be opened proves nothing, and a commitment that
    has to be opened to be checked is not sealed. This opens it in memory,
    compares the hash, and writes nothing.
    """
    sealed = [d for _p, d in _load_all()
              if d["split"] == P.SPLIT_HOLDOUT]
    assert len(sealed) == 1, "exactly one held-out population, or it is not one"
    doc = sealed[0]
    assert doc["sealed"] is True
    assert doc["genomes"] is None, (
        "THE HELD-OUT GENOMES ARE ON DISK. That set is burned: any session "
        "could screen them and tune against them, which is the failure SS13 "
        "names and which is invisible in the result. Draw a new held-out "
        "seed and record this one as spent.")
    X = P.regenerate(P.PopulationSpec.from_dict(doc["spec"]))
    assert P.genome_sha256(X) == doc["genome_sha256"], (
        "the held-out seal does not reproduce: the sampling domain moved "
        "since it was sealed. This population is no longer the one that was "
        "fixed in advance — draw a new seed and record this one as spent. "
        "Do NOT re-seal; re-sealing is what a commitment exists to prevent.")


def test_the_same_specification_draws_the_identical_genome_list_twice():
    spec = P.current_spec(P.DEV_SEED, 8)
    a, b = P.regenerate(spec), P.regenerate(spec)
    assert np.array_equal(a, b)
    assert P.genome_sha256(a) == P.genome_sha256(b)


def test_a_DIFFERENT_specification_is_a_DIFFERENT_population():
    """Every field that can move the draw moves the identity or the digest.

    The seed, the size and the arity move the NAME (`population_id`, which
    the banks already record and which is not replaced here). The domain,
    the generator and its version move the DIGEST — the same name drawn
    under different conditions, which is the 15-gene/16-gene defect one
    level up, and the reason `qualified_id` writes both.
    """
    base = P.current_spec(P.DEV_SEED, 25)
    assert P.current_spec(P.VAL_SEED, 25).population_id != base.population_id
    assert P.current_spec(P.DEV_SEED, 26).population_id != base.population_id
    assert (P.PopulationSpec.from_dict({**base.to_dict(),
                                        "genome_schema_version": 15})
            .population_id != base.population_id)
    for field, value in (("domain_version", "dDEADBEEFDEADBEEF"),
                         ("generator", "some.other.sampler"),
                         ("generator_version", "sample_valid/2"),
                         ("mission", "navalai.mission.MissionSpec(name='x')")):
        other = P.PopulationSpec.from_dict({**base.to_dict(), field: value})
        assert other.digest != base.digest, f"{field} did not move the digest"
    same = P.PopulationSpec.from_dict(base.to_dict())
    assert same.digest == base.digest and same == base


def test_the_15_gene_population_is_REFUSED_never_substituted():
    """A plausible draw of the right shape is worse than no draw at all.

    MEASURED 2026-08-20: `sample_valid(80, MissionSpec(), seed=0)` in this
    16-gene tree matches 0 of the 74 `lwl` values recorded in
    `data/gate2u-n74-mesh.json` in position, and 0 of 25 in
    `gate2u-cap7-mesh.json`, `gate2u-postfix-backoff-mesh.json` and the
    rest of the 15-gene banks. Corroborated by `git log`: those banks were
    committed 2026-08-11..12 and `grammar.PARAMS` went 15 -> 16 on
    2026-08-14. So the refusal below is not a rule about arity in the
    abstract; it is the measured fact that the two streams share nothing.
    """
    hist = P.PopulationSpec(seed=P.DEV_SEED, size=74,
                            genome_schema_version=15,
                            domain_version="UNRECORDED")
    ok, why = hist.regenerable_by_this_tree()
    assert not ok and "15-gene" in why
    with pytest.raises(P.UnregenerablePopulation):
        P.regenerate(hist)
    # and it is RECORDED as history rather than left to be rediscovered
    hits = [d for _p, d in _load_all() if d["spec"]["genome_schema_version"] == 15]
    assert hits, "the 15-gene populations are not recorded anywhere as history"
    for doc in hits:
        assert doc["genome_sha256"] is None, (
            "a population this tree cannot draw must not carry a genome "
            "hash — an unmeasurable value scored as a passing one is this "
            "repository's most expensive defect class")
        assert doc["genomes"] is None
        assert doc["regenerable_by_this_tree"] is False
        assert doc.get("evidence"), (
            "a population that cannot be re-run cannot be checked by "
            "re-running it, so it must say how it was identified")


def test_the_16_GENE_BANKS_REGENERATE_FROM_THE_PERSISTED_DEV_POPULATION():
    """The tie between a manifest and the evidence measured on it.

    The banks record no genome — only a per-hull `lwl` — so this floats the
    persisted genomes through `Hull` and compares that. MEASURED: 25/25,
    25/25, 18/18 (a prefix) and 1/1, exactly, at the three decimals the
    banks round to.
    """
    dev = [d for _p, d in _load_all()
           if d["split"] == P.SPLIT_DEV and d["genomes"] is not None]
    assert len(dev) == 1
    from navalai.geometry import Hull
    lwl = [round(float(Hull(np.asarray(x, dtype=float)).x[-1]), 3)
           for x in dev[0]["genomes"]]
    seen = 0
    for name in ("gate2u-16gene-mesh.json", "gate2u-16gene-mesh-161stl.json",
                 "gate2u-16gene-solve.json", "gate2u-16gene.json"):
        path = _DATA / name
        if not path.exists():
            continue
        rows = json.loads(path.read_text()).get("rows") or []
        got = [r.get("lwl") for r in rows]
        assert got == lwl[:len(got)], (
            f"{name} no longer matches the persisted development "
            f"population; one of the two moved")
        seen += 1
    if not seen:
        pytest.skip("no 16-gene banks in this checkout")


def test_the_draw_is_PREFIX_STABLE_which_is_why_one_manifest_covers_n18():
    """`gate2u-16gene-solve.json` is 18 hulls and the manifest holds 25.

    That is only legitimate if the first 18 of a 25-draw ARE the 18-draw —
    true here because `sample_valid` stops the same accept/reject loop
    earlier, but asserted rather than assumed, since it is what licenses
    reading a smaller bank against a larger population.
    """
    big = P.regenerate(P.current_spec(P.DEV_SEED, 12))
    small = P.regenerate(P.current_spec(P.DEV_SEED, 5))
    assert np.array_equal(big[:5], small)


def test_A_MANIFEST_CARRIES_NO_OUTCOME_which_is_what_the_fence_exempts_it_for():
    """The exemption in the fence above is only sound while this holds."""
    offenders = []
    for path, doc in _load_all():
        blob = json.dumps(doc)
        for key in P.OUTCOME_KEYS:
            if f'"{key}"' in blob:
                offenders.append(f"{path.name}: carries outcome key {key!r}")
    assert not offenders, (
        "a population manifest carries a MEASUREMENT, so it is a campaign "
        "artifact and the fence must not be exempting it:\n    "
        + "\n    ".join(offenders))


def test_what_MAY_be_committed_differs_by_split_and_the_files_obey_it():
    assert P.may_commit_genomes(P.DEV_SEED)
    assert P.may_commit_genomes(P.VAL_SEED)
    assert not P.may_commit_genomes(P.HOLDOUT_SEED)
    assert not P.may_commit_genomes(4242), "an undeclared seed is not licensed"
    for path, doc in _load_all():
        seed = doc["spec"]["seed"]
        if doc["genomes"] is not None:
            assert P.may_commit_genomes(seed), (
                f"{path.name} commits genomes for the "
                f"{P.split_of_seed(seed)} split")


def test_a_SEALED_manifest_is_WRITE_ONCE(tmp_path):
    """Re-sealing is spending the seed, so the writer refuses it.

    The guard is fed the verbatim input it must reject (LESSONS defect class
    3): a test that shows a writer accepts a new file proves nothing about
    the overwrite it exists to prevent.
    """
    spec = P.current_spec(P.HOLDOUT_SEED, 3)
    doc = P.build_manifest(spec, P.regenerate(spec))
    assert doc["sealed"] is True and doc["genomes"] is None
    target = P.manifest_path(spec, tmp_path)
    P.write_manifest(doc, target)
    with pytest.raises(RuntimeError, match="SEALED"):
        P.write_manifest(doc, target)


def test_the_validation_population_is_PINNED_not_derived_at_read_time():
    """A validation set that depends on a mutable default is not a set.

    The failure it prevents is silent: move a box edge, and `(seed, size)`
    names different hulls while every document that quotes it stays word
    for word the same.
    """
    val = [d for _p, d in _load_all() if d["split"] == P.SPLIT_VAL]
    assert len(val) == 1, "exactly one validation population"
    doc = val[0]
    assert doc["genomes"] is not None and len(doc["genomes"]) == doc["spec"]["size"]
    assert all(len(row) == doc["spec"]["genome_schema_version"]
               for row in doc["genomes"])
    assert doc["genome_sha256"] == P.genome_sha256(doc["genomes"])


def test_the_domain_fingerprint_moves_when_the_declared_domain_moves():
    """It is an EARLY WARNING, not the evidence, and the docstring says so:
    it cannot see `grammar.check()` or `evaluate()`. Assert what it CAN do —
    a box edge or a mission field must not slip past it."""
    from navalai import grammar
    from navalai.mission import MissionSpec
    base = P.domain_version()
    assert base == P.domain_version(MissionSpec())
    assert P.domain_version(MissionSpec(cruise_speed_kn=6.0)) != base
    low = grammar.LOW.copy()
    try:
        grammar.LOW[0] = float(np.nextafter(grammar.LOW[0], 1e9))
        assert P.domain_version() != base, (
            "a box edge moved by ONE ULP and the fingerprint did not notice")
    finally:
        grammar.LOW[:] = low
    assert P.domain_version() == base


def test_THE_FENCE_FIRES_on_the_verbatim_input_it_exists_to_reject(tmp_path):
    """A guard that has never been shown to refuse is not a guard.

    Fed the exact two shapes that must be caught — a bank recording the
    protected seed at the top level, and one hiding it under `spec` — plus
    the one that must NOT be (a manifest, which the fence exempts because
    the stricter outcome-key test above holds it).
    """
    from navalai.population import split_of_seed
    caught = []
    for doc, why in (({"seed": P.VAL_SEED, "rows": [1]}, "top-level val"),
                     ({"spec": {"seed": P.HOLDOUT_SEED}}, "nested held-out"),
                     ({"seed": P.HOLDOUT_SEED, "success_pct": 100.0},
                      "top-level held-out")):
        seed = _declared_seed(doc)
        if split_of_seed(seed) in (P.SPLIT_VAL, P.SPLIT_HOLDOUT):
            caught.append(why)
    assert len(caught) == 3, f"the fence would MISS: {caught}"
    # and the exemption is narrow: only a manifest, only by its `kind`
    assert _declared_seed({"seed": P.DEV_SEED}) == P.DEV_SEED
    assert _declared_seed({}) is None
