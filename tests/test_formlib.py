"""Gate 0F — the form library is self-consistent, and it cannot be talked into
recommending a hull the mission does not want.

MOTIVATING INCIDENT. Until 2026-08-13 this project's entire memory of hull form
was `hull_ast.Typology` with two members, `SHARP_CHINE` and `PRAM`. The twelve
reference drawings in `downloads/hull-examples/` carry roughly forty forms, and
`navalai/formlib.py` now records them. THAT IS THE RISK THIS SUITE EXISTS FOR:
a forty-row library read as a forty-item menu would let NSGA-II spend
evaluations on stepped planing hulls and 24 deg deadrise for a solar-electric
displacement catamaran at Fn 0.2-0.3. So the bars here are about REFUSAL as
much as about arithmetic.

Every guard below is made to FIRE on the verbatim input it must reject
(LESSONS.md #3: a test showing a guard accepts a good case proves nothing about
rejection). The rejecting cases are constructed in-test, never by mutating the
shipped library.
"""

from __future__ import annotations

import pytest

from navalai import formlib as F


# --------------------------------------------------------------------- bands

def test_every_band_in_the_library_is_ordered_low_below_high():
    for fam in F.FAMILIES:
        assert fam.fn.low < fam.fn.high, f"{fam.key}: fn band not ordered"
        for key, band in fam.proportions.items():
            assert band.low < band.high, f"{fam.key}.{key}: band not ordered"
    for fn_band, cp_band in F.CP_VS_FN:
        assert fn_band.low < fn_band.high
        assert cp_band.low < cp_band.high
    for regime, band in F.REGIME_FN.items():
        assert band.low < band.high, f"REGIME_FN[{regime}] not ordered"


def test_an_unordered_or_degenerate_band_is_REFUSED():
    # The guard fired on its own terms. A degenerate band is the shape a single
    # remembered figure takes when it is promoted to a range nobody measured,
    # which is defect class 1 (an unmeasurable value scored as a passing one).
    with pytest.raises(ValueError, match="not ordered"):
        F.Band(0.7, 0.5, F.Basis.APPROX, "reversed")
    with pytest.raises(ValueError, match="not ordered"):
        F.Band(0.6, 0.6, F.Basis.APPROX, "a point pretending to be a band")
    with pytest.raises(ValueError, match="not finite"):
        F.Band(float("nan"), 1.0, F.Basis.APPROX, "unmeasured")
    with pytest.raises(ValueError, match="not finite"):
        F.Band(0.0, float("inf"), F.Basis.APPROX, "unbounded")


def test_every_band_carries_a_basis_and_a_NON_EMPTY_source():
    for fam in F.FAMILIES:
        for label, band in [("fn", fam.fn)] + list(fam.proportions.items()):
            assert isinstance(band.basis, F.Basis), f"{fam.key}.{label}"
            assert band.source.strip(), (
                f"{fam.key}.{label} has an empty source. A band with no stated "
                f"provenance reads as authority it does not have.")


def test_a_band_with_no_provenance_is_REFUSED():
    with pytest.raises(ValueError, match="source is empty"):
        F.Band(0.5, 0.6, F.Basis.APPROX, "   ")
    with pytest.raises(TypeError, match="must be a Basis"):
        F.Band(0.5, 0.6, "series", "a string is not a provenance")


def test_the_only_SERIES_basis_is_the_one_citation_this_tree_actually_carries():
    """`Basis.SERIES` is the strongest rung available here and it is scarce on
    purpose. `navalai/resistance.py`'s catamaran-anchor block says in terms
    that NOTHING in it is in this repository — they are citations. So a SERIES
    band must name that block, and any future one must name a source that has
    been checked the same way. This is the fence against a practice number
    being laundered into a citation.
    """
    seen = [(fam.key, k, b) for fam in F.FAMILIES
            for k, b in list(fam.proportions.items()) + [("fn", fam.fn)]
            if b.basis is F.Basis.SERIES]
    assert seen, "the NPL envelope should be carried as SERIES"
    for key, name, band in seen:
        assert "resistance.py" in band.source, (
            f"{key}.{name} claims Basis.SERIES without naming the citation "
            f"block in navalai/resistance.py that carries it: {band.source!r}")


def test_most_of_this_library_is_APPROX_and_says_so():
    """Not a quality bar — a HONESTY bar. If a later edit ever pushes the
    practice share down, that is either a real transcription (good, and the
    sources will say so) or provenance inflation (the defect). Either way the
    number moving should require someone to look.
    """
    census = F.basis_census()
    total = sum(census.values())
    assert total > 100, "the library shrank unexpectedly"
    assert census[F.Basis.APPROX] / total > 0.75, (
        f"the APPROX share fell to {census[F.Basis.APPROX] / total:.1%}. If "
        f"real data was transcribed, raise this bar deliberately and name the "
        f"source; if not, a band has claimed a basis it does not have.")


# ------------------------------------- a DRAWING band must quote a DRAWN NUMBER

# A `Basis.DRAWING` source that admits, in its own words, that the sheet printed
# no number. Kept as data so the test below and the firing case use ONE list.
_NO_NUMBER_TELLS = ("no number", "as words", "not drawn", "no angle",
                    "no figure", "prints no")


def _launders_a_drawing_basis(band) -> bool:
    """True if `band` claims DRAWING while its source says nothing was drawn."""
    if band.basis is not F.Basis.DRAWING:
        return False
    src = band.source.lower()
    return any(tell in src for tell in _NO_NUMBER_TELLS)


def test_no_DRAWING_band_rests_on_a_label_that_is_only_WORDS():
    """MOTIVATING INCIDENT, MEASURED 2026-08-13 by re-reading all twelve sheets.

    Two bands claimed `Basis.DRAWING` off labels that are adjectives:
    `cathedral_tunnel.l_over_b` was [2.5, 4.0] sourced to 007's "Low L/B", and
    `stepped_planing.deadrise_deg` was [18, 26] sourced to 007's "constant
    deep-V deadrise" with the edges borrowed from a DIFFERENT sheet. Neither
    number appears anywhere on 007.

    A qualitative label is real evidence about the DIRECTION of a proportion
    and none at all about its EDGES. Promoting it to DRAWING is the
    number-declared-twice defect with the second copy laundered into a
    citation — the one rot this module's docstring says it is most exposed to.
    Both are `Basis.APPROX` now.
    """
    offenders = [
        (fam.key, name, band)
        for fam in F.FAMILIES
        for name, band in list(fam.proportions.items()) + [("fn", fam.fn)]
        if _launders_a_drawing_basis(band)]
    assert not offenders, (
        "these bands claim to have been read off a drawing while their own "
        "source says no number was printed: "
        + "; ".join(f"{k}.{n} = {b}" for k, n, b in offenders))


def test_the_words_only_provenance_guard_FIRES_on_the_two_verbatim_bands():
    """Rejection case, reconstructed VERBATIM from the two rows that were
    wrong. A guard proved only against good input proves nothing (LESSONS.md
    #3), and these are the exact strings that shipped.
    """
    was_cathedral = F.Band(
        2.5, 4.0, F.Basis.DRAWING,
        "007 'Low L/B' — the only proportion the panel states, and it states "
        "it as words")
    was_stepped = F.Band(
        18.0, 26.0, F.Basis.DRAWING,
        "007 'constant deep-V deadrise'; no number printed, band from the "
        "deep-V panel")
    assert _launders_a_drawing_basis(was_cathedral)
    assert _launders_a_drawing_basis(was_stepped)
    # and it must not fire on a band that names a figure the sheet really
    # prints, or it would push honest readings down to APPROX
    honest = F.Band(20.0, 26.0, F.Basis.DRAWING,
                    "hull-designs-gemini.png panel 1, 'DEEP-V HULL (24 DEADRISE)'")
    assert not _launders_a_drawing_basis(honest)


def test_every_DRAWING_band_names_a_sheet_that_is_in_the_set():
    """Provenance has to be resolvable to a file, not to a memory of one."""
    sheets = {f"{i:03d}" for i in range(10)} | {"hull-designs", "gemini"}
    for fam in F.FAMILIES:
        for name, band in list(fam.proportions.items()) + [("fn", fam.fn)]:
            if band.basis is not F.Basis.DRAWING:
                continue
            assert any(s in band.source for s in sheets), (
                f"{fam.key}.{name} claims Basis.DRAWING without naming which "
                f"sheet it was read from: {band.source!r}")


# ------------------------------------------------------------------ families

def test_every_family_carries_a_candidacy_verdict_with_a_reason():
    for fam in F.FAMILIES:
        assert isinstance(fam.candidacy, F.Candidacy)
        assert fam.candidacy_reason.strip(), f"{fam.key}: unreasoned verdict"
        assert fam.efficiency.strip(), f"{fam.key}: no efficiency sentence"
        assert fam.drawings, f"{fam.key}: names no source drawing"


def test_a_family_with_no_candidacy_reason_is_REFUSED():
    with pytest.raises(ValueError, match="with no reason"):
        F.FormFamily(
            key="unreasoned", name="Unreasoned", topology=F.Topology.MONOHULL,
            regime=F.Regime.DISPLACEMENT,
            fn=F.Band(0.1, 0.3, F.Basis.APPROX, "x"),
            efficiency="does something", candidacy=F.Candidacy.EXCLUDED,
            candidacy_reason="   ",
            expressible=F.Expressible.YES, missing=(),
            drawings=("hull-example-000.png",),
            proportions={"l_over_b": F.Band(3.0, 5.0, F.Basis.APPROX, "x")})


def test_a_family_missing_a_required_proportion_is_REFUSED():
    with pytest.raises(ValueError, match="missing required proportion"):
        F.FormFamily(
            key="bandless", name="Bandless", topology=F.Topology.MONOHULL,
            regime=F.Regime.DISPLACEMENT,
            fn=F.Band(0.1, 0.3, F.Basis.APPROX, "x"),
            efficiency="does something", candidacy=F.Candidacy.EXCLUDED,
            candidacy_reason="because", expressible=F.Expressible.YES,
            missing=(), drawings=("hull-example-000.png",), proportions={})


def test_keys_are_unique_and_the_lookup_covers_the_whole_library():
    keys = [f.key for f in F.FAMILIES]
    assert len(keys) == len(set(keys)), "duplicate family key"
    assert set(F.BY_KEY) == set(keys)
    fkeys = [f.key for f in F.FEATURES]
    assert len(fkeys) == len(set(fkeys)), "duplicate feature key"
    assert set(F.FEATURE_BY_KEY) == set(fkeys)
    assert not (set(keys) & set(fkeys)), (
        "a key is both a family and a feature; the split between a whole-hull "
        "form and a local treatment is the point of having both")


def test_every_feature_points_at_families_that_exist():
    for feat in F.FEATURES:
        for k in feat.applies_to:
            assert k in F.BY_KEY, f"{feat.key} applies_to unknown family {k!r}"


# ------------------------------------------------- regime / Froude / Cp coherence

def test_no_family_claims_a_froude_band_outside_its_own_regime():
    for fam in F.FAMILIES:
        allowed = F.REGIME_FN[fam.regime]
        assert fam.fn.within(allowed), (
            f"{fam.key} claims regime {fam.regime.value} with Fn {fam.fn} "
            f"which is not inside {allowed}")


def test_no_family_claims_a_froude_regime_that_contradicts_its_Cp():
    """THE DRAWINGS' OWN ERROR, made unrepeatable.

    Five panels print 'High Cp, Low Fn'. It is backwards — Cp RISES with Fn,
    fine ends at low speed and full ends at high speed. `CP_VS_FN` is the
    monotone rule. A family whose Cp band does not even TOUCH the practice
    envelope over its own Froude band has either a typo or a copied label.

    Overlap, not containment, is the right strength: the envelope is APPROX
    and a slender demihull legitimately runs above the monohull practice band.
    A bar tighter than the evidence would be softening in reverse.
    """
    for fam in F.FAMILIES:
        cp = fam.band("cp")
        if cp is None:
            continue
        env = F.cp_envelope(fam.fn)
        assert cp.overlaps(env), (
            f"{fam.key}: Cp {cp} does not touch the practice envelope {env} "
            f"for Fn {fam.fn}. Either the Cp band or the Froude band is wrong "
            f"— and 'High Cp, Low Fn' as printed on the drawings is the wrong "
            f"one.")


def test_the_Cp_envelope_is_MONOTONE_in_Froude_number():
    """The rule R5 adopts, asserted rather than described. Both edges of the
    practice band must be non-decreasing as Fn rises; a table that sagged would
    reintroduce the drawings' label by the back door.
    """
    rows = F.CP_VS_FN
    for (fn_a, cp_a), (fn_b, cp_b) in zip(rows, rows[1:]):
        assert fn_a.low < fn_b.low, "CP_VS_FN is not ordered by Froude number"
        assert cp_b.low >= cp_a.low, f"Cp floor falls from {cp_a} to {cp_b}"
        assert cp_b.high >= cp_a.high, f"Cp ceiling falls from {cp_a} to {cp_b}"


def test_the_Cp_contradiction_guard_FIRES_on_the_drawings_own_label():
    """Verbatim rejection case: a displacement form at Fn 0.1-0.25 with the
    high Cp the panels imply. Constructed here rather than by mutating the
    library, so the shipped rows stay the shipped rows.
    """
    bad = F.FormFamily(
        key="high_cp_low_fn", name="the drawings' label, taken literally",
        topology=F.Topology.MONOHULL, regime=F.Regime.DISPLACEMENT,
        fn=F.Band(0.10, 0.25, F.Basis.APPROX, "low Fn"),
        efficiency="none — this row exists to be refused",
        candidacy=F.Candidacy.EXCLUDED, candidacy_reason="it is wrong",
        expressible=F.Expressible.NO, missing=("everything",),
        drawings=("hull-example-003.png",),
        proportions={"l_over_b": F.Band(3.0, 5.0, F.Basis.APPROX, "x"),
                     "cp": F.Band(0.88, 0.96, F.Basis.APPROX, "'High Cp'")})
    assert not bad.band("cp").overlaps(F.cp_envelope(bad.fn)), (
        "the guard would accept 'High Cp, Low Fn' — the one drawing error "
        "this suite is named for")


# -------------------------------------------------------------- expressibility

def test_expressible_and_the_missing_list_are_ONE_statement():
    for fam in F.FAMILIES:
        if fam.expressible is F.Expressible.YES:
            assert not fam.missing, (
                f"{fam.key} is YES with a non-empty missing list")
        else:
            assert fam.missing, (
                f"{fam.key} is {fam.expressible.value} and names nothing that "
                f"is missing. 'Not expressible, reason unrecorded' is the same "
                f"defect as an unmeasured metric scored as passing.")


def test_a_family_whose_two_expressibility_fields_disagree_is_REFUSED():
    with pytest.raises(ValueError, match="are one statement"):
        F.FormFamily(
            key="contradictory", name="Contradictory",
            topology=F.Topology.MONOHULL, regime=F.Regime.DISPLACEMENT,
            fn=F.Band(0.1, 0.3, F.Basis.APPROX, "x"),
            efficiency="x", candidacy=F.Candidacy.EXCLUDED,
            candidacy_reason="x", expressible=F.Expressible.YES,
            missing=("a round bilge",), drawings=("hull-example-000.png",),
            proportions={"l_over_b": F.Band(3.0, 5.0, F.Basis.APPROX, "x")})


def test_the_target_family_is_NOT_yet_expressible_and_says_why():
    """A statement about the CODE, not a status claim about the project: the
    mission's own form cannot be built by the current grammar, and the library
    records the reasons rather than implying the hull is reachable.

    REWRITTEN DELIBERATELY 2026-08-14 (the rewrite this docstring demands):
    the registry re-audit removed two of the five recorded absences because
    their premises are DEAD IN CODE — the `roundness` gene ships a real
    bilge fillet, and `total_resistance(..., separation=)` carries demihull
    spacing into the production interference term. What remains missing is a
    second hull AS GEOMETRY, the wet deck, and the sourced-evidence B/T
    floor; the two retired reasons must NOT reappear, because a registry
    that re-claims a shipped capability is impossible is exactly the defect
    the audit caught (G0-P0).
    """
    tgt = F.target()
    assert tgt.expressible is not F.Expressible.YES
    assert len(tgt.missing) == 3, (
        f"{tgt.key} names {len(tgt.missing)} missing capabilities; the "
        f"recorded set is a second hull as geometry, the wet deck, and the "
        f"Southampton B/T evidence floor")
    joined = " ".join(tgt.missing).lower()
    for needle in ("second hull", "wet deck", "b/t"):
        assert needle in joined, f"target family does not name {needle!r}"
    for retired in ("round bilge: there is no bilge radius",
                    "total_resistance does not pass it"):
        assert retired not in joined, (
            f"a retired inexpressibility claim reappeared: {retired!r} — the "
            f"kernel ships this; see geometry.roundness / resistance.py")


def test_the_rebuild_backlog_is_DERIVED_from_the_library_not_restated():
    backlog = F.unexpressible()
    assert backlog, "nothing is recorded as unexpressible, which cannot be true"
    for key in backlog:
        assert key in F.BY_KEY or key in F.FEATURE_BY_KEY
    for fam in F.FAMILIES:
        if fam.expressible is F.Expressible.YES:
            assert fam.key not in backlog


# ------------------------------------------------------------------- mission

def test_exactly_one_family_is_the_TARGET():
    tgt = F.target()
    assert tgt.key == "slender_symmetric_cat_demihull"
    assert tgt.topology is F.MISSION.topology
    assert tgt.regime is F.MISSION.regime


def test_two_TARGET_families_are_REFUSED():
    # A mission with two target forms has not chosen one. Fired by patching the
    # module's tuple inside the test and restoring it, rather than by shipping
    # a second target.
    original = F.FAMILIES
    try:
        F.FAMILIES = original + (original[0],)
        # `original[0]` is ADJACENT, so force the collision explicitly.
        clone = F.FormFamily(
            key="second_target", name="Second target",
            topology=F.Topology.CATAMARAN, regime=F.Regime.DISPLACEMENT,
            fn=F.Band(0.2, 0.3, F.Basis.APPROX, "x"),
            efficiency="x", candidacy=F.Candidacy.TARGET,
            candidacy_reason="x", expressible=F.Expressible.NO,
            missing=("x",), drawings=("hull-example-000.png",),
            proportions={"l_over_b": F.Band(12.0, 18.0, F.Basis.APPROX, "x")})
        F.FAMILIES = original + (clone,)
        with pytest.raises(ValueError, match="exactly one TARGET"):
            F.target()
    finally:
        F.FAMILIES = original


def test_the_SKU_relevant_family_is_REACHABLE_by_its_own_bands():
    """The mission's demihull must fall inside the target family's bands.

    This is the check that keeps the library connected to the boat. A library
    whose target family excluded the target hull would be a taxonomy, not a
    design memory — and the numbers involved (L/B 15.0, B/T 1.33) are exactly
    the two the current `grammar.check` REFUSES, so the two files disagreeing
    is the finding, not an error here.
    """
    tgt, m = F.target(), F.MISSION
    assert m.fn.within(tgt.fn), (
        f"mission Fn {m.fn} is not inside the target family's {tgt.fn}")
    lob = tgt.band("l_over_b")
    assert lob is not None and lob.contains(m.l_over_b), (
        f"mission demihull L/B {m.l_over_b:.2f} is outside {lob}")
    bot = tgt.band("b_over_t")
    assert bot is not None and bot.contains(m.b_over_t), (
        f"mission demihull B/T {m.b_over_t:.2f} is outside {bot}")


def test_the_mission_is_reachable_by_at_least_one_PROPOSABLE_family():
    ok = [f for f in F.proposable()
          if f.topology is F.MISSION.topology and F.MISSION.fn.overlaps(f.fn)]
    assert ok, ("no proposable family matches the mission topology and Froude "
                "band; an optimiser would have nothing to sample")


def test_every_planing_and_lift_dominant_form_is_EXCLUDED():
    """THE BAR THIS SUITE IS FOR. Dynamic lift is irrelevant below Fn ~0.5 and
    the mission ends at 0.3. A planing family reaching CANDIDATE would put
    24 deg deadrise and ventilated steps inside the optimiser's search space.
    """
    for fam in F.families(regime=F.Regime.PLANING):
        assert fam.candidacy is F.Candidacy.EXCLUDED, (
            f"{fam.key} is a planing form marked {fam.candidacy.value}")
    for key in ("swath", "semi_submersible", "air_cushion", "foil_assisted",
                "deep_v_planing", "stepped_planing", "bulbous_bow_displacement"):
        assert F.BY_KEY[key].candidacy is F.Candidacy.EXCLUDED, (
            f"{key} was named in the brief as NOT a candidate")
    for key in ("transverse_step", "lifting_strakes", "chine_flat",
                "wave_cancellation_bulb", "ride_control_fins"):
        assert F.FEATURE_BY_KEY[key].candidacy is F.Candidacy.EXCLUDED


def test_no_proposable_family_sits_entirely_above_the_mission_Froude_band():
    """An ADJACENT family may exist for its transferable rules, but nothing
    proposable may be a form whose whole speed range the SKU never reaches
    without saying so on the row.
    """
    for fam in F.proposable():
        if not F.MISSION.fn.overlaps(fam.fn):
            assert fam.candidacy in (F.Candidacy.ADJACENT, F.Candidacy.CANDIDATE)
            assert ("transfer" in fam.candidacy_reason
                    or "borrow" in fam.candidacy_reason
                    or "approximation" in fam.candidacy_reason.lower()), (
                f"{fam.key} is proposable, never overlaps the mission's Fn "
                f"{F.MISSION.fn}, and its reason does not say what transfers")


# ------------------------------------------------- the one dimensioned table

def test_the_drawn_dimension_table_is_ordered_and_sourced_like_any_other_band():
    for row, cols in F.DRAWN_DIMENSION_RANGES.items():
        assert cols, f"{row}: no columns transcribed"
        for name, band in cols.items():
            assert band.low < band.high, f"{row}.{name} not ordered"
            assert band.basis is F.Basis.DRAWING, (
                f"{row}.{name} is a transcription of a printed table and must "
                f"say so")
            assert "000" in band.source, f"{row}.{name} does not name sheet 000"


def test_a_column_the_sheet_prints_as_Varies_is_ABSENT_not_invented():
    """`hull-example-000.png`'s "special forms" row prints "Varies" for beam
    and draft. An adjective is not a band. The keys are absent, and
    `drawn_dimension_verdict` returns None rather than True for them —
    "I could not measure this" must never become "this passes" (LESSONS.md #1,
    the `${VAR:-0}` class).
    """
    special = F.DRAWN_DIMENSION_RANGES["special forms"]
    assert "beam_m" not in special and "draft_m" not in special
    verdict = F.drawn_dimension_verdict("special forms", 12.0, 4.0, 0.6)
    assert verdict["beam_m"] is None, "an unstated column scored as a pass"
    assert verdict["draft_m"] is None
    assert verdict["lwl_m"] is True
    # and the guard must still be able to FAIL a stated column
    assert F.drawn_dimension_verdict("special forms", 99.0, 4.0, 0.6)["lwl_m"] \
        is False


def test_the_mission_sits_inside_the_catamaran_row_of_the_drawn_table():
    """The one place the library can check itself against a printed number
    instead of against practice. B_oa 4.0 m is 008's own label; the demihull
    beam is NOT what this table's column means and passing it would compare
    two different quantities.
    """
    verdict = F.drawn_dimension_verdict(
        "catamaran", F.MISSION.hull_lwl_m, 4.0, F.MISSION.hull_draft_m)
    assert all(v is True for v in verdict.values()), verdict


# ---------------------------------------------------- the library's own counts

def test_the_counts_the_docstrings_quote_are_the_counts_the_tuples_have():
    """A prose count drifting from the data it describes is how "3 of 3 layers"
    happened. `FAMILIES` is quoted as 31 with 24 EXCLUDED in the module
    docstring and again in the comment above the tuple; both said something
    else before the tuple was counted.
    """
    assert len(F.FAMILIES) == 31, (
        f"FAMILIES is now {len(F.FAMILIES)}; update the module docstring and "
        f"the comment above the tuple in the SAME change, or they become a "
        f"second, wrong copy of this number")
    assert len(F.families(candidacy=F.Candidacy.EXCLUDED)) == 24
    assert len(F.proposable()) == len(F.FAMILIES) - 24
    # The docstring line-wraps, so compare on whitespace-normalised text.
    src = " ".join((F.__doc__ or "").split())
    assert "24 of the 31 families are `EXCLUDED`" in src


# ------------------------------------------- the bridge to hull_ast.Typology

def test_every_hull_ast_typology_is_named_by_exactly_one_family():
    """The two vocabularies must not drift into being unrelated.

    `hull_ast.Typology` was this project's ENTIRE memory of hull form until
    2026-08-13: two members against the ~40 forms the drawings carry. It is not
    replaced — it is the part the geometry kernel dispatches on — so the
    library has to say which of its families each member IS, and
    `FormFamily.ast_typology` carries that. Without this fence the 31 families
    and the 2 typologies become two vocabularies for one question, which is the
    thing-declared-twice defect applied to a taxonomy.

    Read-only against `hull_ast`; this test owns nothing there.
    """
    from navalai.hull_ast import TYPOLOGY_RULES, Typology

    claimed = [f for f in F.FAMILIES if f.ast_typology is not None]
    by_member: dict[str, list[str]] = {}
    for fam in claimed:
        assert fam.ast_typology in Typology.__members__, (
            f"{fam.key} names hull_ast typology {fam.ast_typology!r}, which "
            f"does not exist; members are {list(Typology.__members__)}")
        by_member.setdefault(fam.ast_typology, []).append(fam.key)

    for member in Typology.__members__:
        hits = by_member.get(member, [])
        assert len(hits) == 1, (
            f"hull_ast.Typology.{member} is named by {len(hits)} families "
            f"{hits}. Every typology the geometry kernel can dispatch on must "
            f"correspond to exactly one form family, or the two vocabularies "
            f"have drifted.")
    # ...and the mapping covers every typology that actually carries rules, so
    # a third typology added to hull_ast fails HERE rather than silently
    # gaining no family.
    assert {t.name for t in TYPOLOGY_RULES} == set(by_member), (
        f"TYPOLOGY_RULES covers {sorted(t.name for t in TYPOLOGY_RULES)} but "
        f"formlib names {sorted(by_member)}")


def test_the_two_ast_typologies_are_the_grammars_reach_and_the_library_says_so():
    """REWRITTEN DELIBERATELY 2026-08-14, per this test's own instruction
    ("if a second family ever becomes expressible..."): the `roundness` gene
    put a real quadratic-Bezier bilge into the section law, so the two
    displacement-monohull families whose ONLY recorded absence was the round
    bilge are now buildable. The registry said they were impossible while the
    kernel shipped them — audit finding G0-P0 — and the YES set is the fact
    about the code that fixes it. Candidacy is untouched: buildable is not an
    argument for the mission, and all three stay EXCLUDED on the physics.
    """
    yes = sorted(f.key for f in F.FAMILIES if f.expressible is F.Expressible.YES)
    assert yes == ["full_displacement", "hard_chine_displacement",
                   "moderate_displacement"], yes
    for key in yes:
        assert F.BY_KEY[key].candidacy is F.Candidacy.EXCLUDED, (
            f"{key}: a buildable family must still be judged on the physics; "
            f"'it is what we can build' is not a candidacy argument")


# ------------------------------------------------------ the speed-label conflict

def test_the_drawings_knots_and_Froude_labels_really_do_disagree():
    """MEASURED, not asserted from the prose. Four sheets are headed
    '7-12 knots, Fn 0.2-0.35'. On the 12 m waterline that 008 dimensions,
    7 kn is Fn 0.33 and 12 kn is Fn 0.57 — above `FN_MICHELL_MAX` (0.45),
    where this project's own wave model declares itself invalid. The library
    adopts the Froude half; this test is why it is allowed to.
    """
    assert F.knots_to_fn(7.0, 12.0) == pytest.approx(0.332, abs=0.002)
    assert F.knots_to_fn(12.0, 12.0) == pytest.approx(0.569, abs=0.002)
    assert F.knots_to_fn(12.0, 16.0) == pytest.approx(0.493, abs=0.002)
    # and the mission, stated in Froude numbers, is a different boat's speeds
    assert F.fn_to_knots(0.20, 12.0) == pytest.approx(4.22, abs=0.02)
    assert F.fn_to_knots(0.30, 12.0) == pytest.approx(6.33, abs=0.02)
    assert F.knots_to_fn(12.0, 12.0) > 0.45, (
        "12 kn on a 12 m waterline must be above FN_MICHELL_MAX for the "
        "conflict to matter")


def test_knots_to_fn_refuses_a_length_it_cannot_use():
    for bad in (0.0, -1.0):
        with pytest.raises(ValueError, match="must be positive"):
            F.knots_to_fn(10.0, bad)
        with pytest.raises(ValueError, match="must be positive"):
            F.fn_to_knots(0.3, bad)


# ------------------------------------------------------------------ boundaries

def test_the_library_imports_no_geometry_and_no_grammar():
    """`formlib` is DATA. It must stay importable while the geometry kernel is
    being rewritten, and the dependency must run one way: a sampler reads a
    family from here, never the reverse. Enforced on the source text because
    an import added inside a function would not show up in `sys.modules`.
    """
    import pathlib
    src = pathlib.Path(F.__file__).read_text()
    for forbidden in ("from .geometry", "from .grammar", "from navalai.geometry",
                      "from navalai.grammar", "import navalai.geometry",
                      "import navalai.grammar", "from . import geometry",
                      "from . import grammar"):
        assert forbidden not in src, (
            f"navalai/formlib.py imports {forbidden!r}. The form library is "
            f"data and must not depend on the geometry kernel.")


def test_the_named_source_drawings_are_the_twelve_that_exist():
    """LESSONS.md #5: citing evidence that no longer exists. Every drawing
    named by a family or a feature must be on disk under
    `downloads/hull-examples/`, or the provenance is a claim nobody can check.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "downloads" / "hull-examples"
    if not root.is_dir():
        pytest.skip("downloads/hull-examples/ is not present in this tree")
    on_disk = {p.name for p in root.glob("*.png")}
    named = {d for f in F.FAMILIES for d in f.drawings}
    named |= {d for f in F.FEATURES for d in f.drawings}
    missing = named - on_disk
    assert not missing, f"library cites drawings that are not on disk: {sorted(missing)}"
    unused = on_disk - named
    assert not unused, (
        f"drawings on disk that no row cites: {sorted(unused)}. Every sheet "
        f"was read; a sheet with no row is a sheet whose content was dropped.")


# ------------------------------------------------------- Basis.LITERATURE
# ADDED 2026-08-13 with the sourcing pass recorded in
# `docs/research/HULL-FORM-RULES.md` §7. MOTIVATING INCIDENT: this module was
# built entirely from twelve illustrations, and §7 was the first attempt to
# corroborate them against published work. The specific failure that pass could
# have produced is the one `Basis`'s docstring already names — a number read
# once, on one day, from one PDF, presented with the authority of a systematic
# series. The `SERIES` rung means "the citation is in this tree"; `LITERATURE`
# means "one document was opened". These guards keep the two apart, and keep a
# SECONDARY quotation from being dressed as a primary one.

def _module_level_bands():
    """Every `Band` bound at module scope, i.e. the citation blocks.

    `basis_census` and the band-ordering test walk FAMILIES; the literature
    constants are NOT in a family, so without this they would be the one part
    of the module no fence covers.
    """
    return {name: obj for name, obj in vars(F).items()
            if isinstance(obj, F.Band)}


def test_every_MODULE_LEVEL_band_is_ordered_and_carries_a_source():
    bands = _module_level_bands()
    assert bands, "the citation blocks vanished from formlib"
    for name, band in bands.items():
        assert band.low < band.high, f"{name}: band not ordered"
        assert band.source.strip(), f"{name}: band with an empty source"


def test_every_LITERATURE_band_names_where_the_argument_is_recorded():
    """A `LITERATURE` band must point at the section of HULL-FORM-RULES.md that
    carries its argument. Without it the band is a number with an author's name
    attached, and the reader cannot see the Froude range, the hull family or
    the caveats — which §7.0 rule 1 says is not a usable band at all.
    """
    lit = [(n, b) for n, b in _module_level_bands().items()
           if b.basis is F.Basis.LITERATURE]
    assert lit, "the literature citations vanished from formlib"
    for name, band in lit:
        assert "HULL-FORM-RULES.md" in band.source, (
            f"{name} claims Basis.LITERATURE without naming the section of "
            f"docs/research/HULL-FORM-RULES.md that carries the argument: "
            f"{band.source!r}")
        assert any(y in band.source for y in
                   ("19", "20")), (
            f"{name} claims Basis.LITERATURE without naming a year: "
            f"{band.source!r}")


def test_a_SECONDARY_quotation_must_SAY_it_is_secondary():
    """THE LOAD-BEARING GUARD OF THIS BLOCK.

    The Southampton catamaran demihull envelope is the strongest finding in §7
    — it is the only published series envelope that CONTAINS this project's own
    target hull, and it is the argument for moving `grammar.L_OVER_B_BAND`'s
    8.5 ceiling. And it was NOT read from Molland, Wellicome & Couser's Ship
    Science Report 71: `eprints.soton.ac.uk` returned 401/403 on every route
    tried on 2026-08-13, so it is quoted from Petersson (2020) Table 3, which
    tabulates it. A band that important, sourced that way, must say so on its
    own face — otherwise the next reader promotes it, and this project's
    recurring defect (a number that acquires authority it was never given)
    happens to the one number the L/B decision rests on.
    """
    soton = [(n, b) for n, b in _module_level_bands().items()
             if n.startswith("_SOTON_")]
    assert soton, "the Southampton envelope vanished from formlib"
    for name, band in soton:
        assert "SECONDARY" in band.source, (
            f"{name} quotes the Southampton series without recording that the "
            f"report itself could not be opened: {band.source!r}")
        assert "Petersson" in band.source, (
            f"{name} does not name the source it was actually read from")


def test_the_SECONDARY_guard_FIRES_on_a_laundered_citation():
    """LESSONS.md #3: prove the guard REJECTS. This is the exact string a
    future edit would produce by "tidying" the caveat out of the source.
    """
    laundered = F.Band(7.00, 15.10, F.Basis.LITERATURE,
                       "Southampton catamaran series (Molland, Wellicome & "
                       "Couser, Ship Science Report 71, 1994) demihull "
                       "envelope; see HULL-FORM-RULES.md §7.4")
    assert "SECONDARY" not in laundered.source, (
        "the constructed counter-example must be the laundered form")
    assert "HULL-FORM-RULES.md" in laundered.source, (
        "it must pass the OTHER literature guard, so that this test is "
        "demonstrating the secondary-source guard specifically")


# ------------------------------------------- alpha_e is not a free variable

def test_the_target_demihull_is_INSIDE_Southampton_and_OUTSIDE_NPL():
    """The finding §7.4 and §7.6 exist to record, fenced so it cannot quietly
    reverse. The two envelopes DISAGREE about this project's own hull and both
    are kept, because one is a catamaran demihull series and the other is a
    monohull series — averaging them is what this repo calls a fake consensus.
    """
    l_over_b = F.MISSION.l_over_b
    assert F._SOTON_L_OVER_B.low <= l_over_b <= F._SOTON_L_OVER_B.high, (
        f"the mission's demihull L/B {l_over_b:.2f} left the Southampton "
        f"demihull envelope {F._SOTON_L_OVER_B}")
    assert not (F._NPL_L_OVER_B.low <= l_over_b <= F._NPL_L_OVER_B.high), (
        f"the mission's demihull L/B {l_over_b:.2f} is now inside the NPL "
        f"MONOHULL envelope {F._NPL_L_OVER_B}; if that is real, the argument "
        f"in HULL-FORM-RULES.md §7.4 needs rewriting, not this bar moving")
    # and the B/T finding, which points the OTHER way and must not be lost
    assert F.MISSION.b_over_t < F._SOTON_B_OVER_T.low, (
        f"the mission's B/T {F.MISSION.b_over_t:.2f} was BELOW the Southampton "
        f"band {F._SOTON_B_OVER_T} when §7.4 was written — the slenderness is "
        f"sourced and the draft is not, and that asymmetry is the point")


def test_the_alpha_e_chord_floor_FALLS_with_slenderness_and_is_a_FLOOR():
    """`alpha_e_chord_floor_deg` is arithmetic, not a source, and the whole
    argument of §7.7 rests on two properties of it: it is monotone decreasing
    in L/B, and a real hull sits ABOVE it. The second is checked at the one
    hull where both numbers are known (FDS-5, n = 1, and treated as such).
    """
    prev = None
    for l_over_b in (2.2, 3.0, 4.0, 6.0, 8.5, 12.0, 15.0, 17.8):
        deg = F.alpha_e_chord_floor_deg(l_over_b, 0.60)
        assert 0.0 < deg < 90.0
        if prev is not None:
            assert deg < prev, "the chord floor must fall as L/B rises"
        prev = deg
    # a longer entry gives a finer angle, at fixed L/B
    assert (F.alpha_e_chord_floor_deg(8.0, 0.60)
            < F.alpha_e_chord_floor_deg(8.0, 0.50))
    # FDS-5: MEASURED 11 deg at L/B 8 sits ABOVE the floor. If this ever
    # inverts, the expression is not a floor and §7.7's argument is void.
    floor = F.alpha_e_chord_floor_deg(8.0, 0.60)
    assert floor < F._FDS5_ALPHA_E_DEG, (
        f"FDS-5's measured i_e {F._FDS5_ALPHA_E_DEG} deg fell below the chord "
        f"floor {floor:.2f} deg — the expression is no longer a floor")


def test_a_7_to_12_degree_alpha_e_band_is_UNREACHABLE_at_the_grammars_L_over_B_floor():
    """THE MEASURED FINDING THIS FUNCTION EXISTS FOR. The audit reports a
    median entry half-angle near 32 deg over the sampled population and 1 hull
    of 74 inside 7-12 deg. At the monohull grammar's L/B floor of ~2.2 the
    CHORD angle alone exceeds 12 deg at every published entry-length fraction,
    so no bow shape whatsoever puts such a hull in the band: most of that
    median is the L/B box, not the bows. Constraining alpha_e without moving
    L/B first would be two constraint rows measuring one degree of freedom.
    """
    for le_over_l in (F._LE_OVER_L.low, F._LE_OVER_L.high):
        assert F.alpha_e_chord_floor_deg(2.2, le_over_l) > 12.0, (
            "at L/B 2.2 the chord floor dropped inside the 7-12 deg window; "
            "re-read HULL-FORM-RULES.md §7.7 before trusting either number")
    # and it IS reachable for the target demihull, which is the other half
    assert F.alpha_e_chord_floor_deg(F.MISSION.l_over_b, 0.50) < 9.0, (
        "the target demihull can no longer reach 009's drawn '<9 deg'")


def test_alpha_e_chord_floor_REFUSES_a_non_physical_argument():
    """An unmeasurable input must raise, not return a plausible number
    (LESSONS.md #1). `le_over_l` is a FRACTION of Lwl; 1.5 is the mistake a
    caller makes by passing metres.
    """
    for bad in (0.0, -3.0):
        with pytest.raises(ValueError):
            F.alpha_e_chord_floor_deg(bad, 0.60)
    for bad in (0.0, 1.0, 1.5, -0.2):
        with pytest.raises(ValueError):
            F.alpha_e_chord_floor_deg(8.0, bad)


def test_the_FDS5_entrance_angle_is_a_POINT_and_is_NOT_dressed_as_a_band():
    """One measured hull is one measured hull. `Band(x, x)` is already refused
    by this module; the subtler error is inventing edges around a point to make
    it look like a range, which is exactly what the two verbatim DRAWING bands
    did with words. FDS-5's 11 deg is therefore a bare float.
    """
    assert isinstance(F._FDS5_ALPHA_E_DEG, float)
    assert not isinstance(F._FDS5_ALPHA_E_DEG, F.Band)
    assert "Petersson" in F._FDS5_SRC and "FDS-5" in F._FDS5_SRC


def test_the_sourced_alpha_e_flat_band_records_that_its_low_edge_is_NOT_a_floor():
    """Blount & McGrath measured NO effect on R/W down to 3.7 deg — the finest
    hull in the data, not a limit. §7.9 item 3 records that this project has
    been auditing against a 7 deg floor with no source in either the drawings
    (all three labels are one-sided ceilings) or the literature. The band must
    carry that caveat or it becomes a two-sided bar by accident.
    """
    band = F._BLOUNT_ALPHA_E_FLAT
    assert band.basis is F.Basis.LITERATURE
    assert "NOT a floor" in band.source, (
        f"the flat band no longer records that its low edge is the finest "
        f"hull measured rather than a limit: {band.source!r}")
    assert band.low < 7.0, (
        "the sourced band's low edge rose above the unsourced 7 deg the audit "
        "uses; that would make the audit window look corroborated when §7.9 "
        "item 3 says it is not")


def test_registry_claims_cannot_contradict_the_shipped_kernel_R04f():
    """THE FENCE the 2026-08-14 audit asked for (G0-P0). The registry once
    said "round bilge: there is no bilge radius" while `geometry` shipped the
    `roundness` fillet, and "total_resistance does not pass it" while the
    signature carried `separation=` into the production interference term —
    a capability registry claiming a shipped feature is impossible, which is
    strictly worse than no registry. Each check here couples the CLAIM text
    to the LIVE capability probe, so the pair can only drift together.
    """
    import inspect
    import pathlib as _pl

    from navalai import grammar as _g
    from navalai import resistance as _r

    src = _pl.Path(F.__file__).read_text()
    if "roundness" in _g.PARAMS:
        for dead in ("there is no bilge radius", "only a chine crease"):
            assert dead not in src, (
                f"formlib claims {dead!r} while grammar carries a "
                f"`roundness` gene and geometry ships the bilge fillet")
    if "separation" in inspect.signature(_r.total_resistance).parameters:
        assert "total_resistance does not pass it" not in src, (
            "formlib claims separation never reaches total_resistance while "
            "the signature carries it into the interference term")
    # the 3-point-polyline description died with the P1/P2 kernel
    assert "3-point keel/chine/sheer polyline" not in src, (
        "formlib describes the retired three-point section law as current")


def test_the_deadrise_bound_is_not_declared_twice():
    """`formlib`'s deadrise band must equal `grammar.PARAMS` beta_mid.

    `grammar` imports `formlib`, so formlib cannot read the bound back at
    module level without a circular import — the literal is therefore FENCED
    here instead of derived. It was 25.0 in both places until 2026-08-23,
    when Gate 0E5C found the grammar bound had no provenance and seven
    published hard-chine series outside it, and moved it to 35. A number
    declared twice is this repository's recurring defect; this is the fence
    that stops the second copy drifting.
    """
    from navalai import formlib, grammar

    i = grammar.NAMES.index("beta_mid")
    lo, hi = float(grammar.LOW[i]), float(grammar.HIGH[i])
    checked = 0
    for fam in formlib.families():
        band = fam.proportions.get("deadrise_deg")
        if band is None or "grammar.PARAMS beta_mid" not in str(band.source):
            continue
        assert (band.low, band.high) == (lo, hi), (
            f"{fam.key}: formlib states deadrise {band.low}..{band.high} and "
            f"cites grammar.PARAMS beta_mid, which is {lo}..{hi}")
        checked += 1
    assert checked >= 1, (
        "no formlib family cites grammar.PARAMS beta_mid any more — either "
        "the citation was dropped or this fence is guarding nothing")
