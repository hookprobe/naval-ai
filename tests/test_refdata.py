"""Gate V2.0 — the reference-data spine carries its provenance.

BuildPlan2-FullVessel.md §3, verbatim: *"Gate V2.0: constants importable,
every one carries source+basis, no bare numbers."*

The motivating defect class is the one CLAUDE.md names as this codebase's
recurring failure, seen from a new angle. `limits.py` exists because the GM
floor was declared twice and the two copies drifted 0.35 vs 0.45. Reference
data has the mirror-image failure available to it: a number declared ONCE,
correctly, with nothing recording whether it came from a standard text, from
marine practice, or from somebody's recollection — at which point it cannot be
re-checked, cannot be upgraded when the standard is purchased, and cannot be
told apart from an invention.

So these tests do two things a type annotation cannot:

  1. walk every value, INCLUDING the ones nested inside category tables, and
     insist on a source and a basis from the allowed vocabulary;
  2. insist that what the plan marks paywalled is recorded as ABSENT rather
     than filled in at a plausible value.

(2) is the one that matters. An invented constant is indistinguishable from a
transcribed one the moment it lands in a module, and Tier F will divide by it.
"""

from __future__ import annotations

import math

import pytest

from navalai import refdata
from navalai.refdata import BASES, Absent, RefValue, ergonomics, flotation


# ------------------------------------------------------------ the gate bar

def test_the_constants_are_importable_and_there_are_some():
    """'Constants importable' — clause 1 of the gate, and a guard against a
    later refactor emptying the modules while the other tests stay green by
    vacuous truth."""
    all_c = refdata.all_constants()
    assert len(all_c) >= 40, len(all_c)
    assert any(k.startswith("ergonomics.") for k in all_c)
    assert any(k.startswith("flotation.") for k in all_c)


@pytest.mark.parametrize("module", [ergonomics, flotation])
def test_every_constant_carries_a_non_empty_source(module):
    for name, rv in refdata.constants(module).items():
        assert isinstance(rv, RefValue)
        assert rv.source.strip(), f"{module.__name__}.{name} has no source"
        # A source has to identify a document, not just gesture at one.
        assert len(rv.source) > 20, f"{module.__name__}.{name}: {rv.source!r}"


@pytest.mark.parametrize("module", [ergonomics, flotation])
def test_every_constant_carries_a_basis_from_the_allowed_set(module):
    for name, rv in refdata.constants(module).items():
        assert rv.basis in BASES, f"{module.__name__}.{name}: {rv.basis!r}"


def test_no_bare_numbers_sit_beside_the_wrapped_ones():
    """Clause 3 of the gate. A RefValue next to a naked float is exactly how
    the provenance stops meaning anything: the float looks like data too."""
    for module in (ergonomics, flotation):
        for name, obj in vars(module).items():
            if name.startswith("_") or name.isupper() is False:
                continue
            if isinstance(obj, (int, float, complex)) and not isinstance(obj, bool):
                pytest.fail(f"{module.__name__}.{name} is a bare number")
            if isinstance(obj, dict):
                for k, v in obj.items():
                    assert isinstance(v, RefValue), f"{name}[{k!r}] is bare"


def test_a_constant_cannot_be_constructed_without_provenance():
    """Structural, not policed: the guarantee has to hold for code written
    after this test, too."""
    with pytest.raises(ValueError, match="no source"):
        RefValue(1.0, "m", "  ", "approx")
    with pytest.raises(ValueError, match="not in"):
        RefValue(1.0, "m", "a source long enough to identify a document", "guess")


# ------------------------------------------------- provenance is not cosmetic

def test_the_2024_preview_numbers_are_not_attributed_to_the_2003_text():
    """The 2024 seat minimum and the zone system are real, verified, and NOT
    in ISO 15085:2003. Calling them 'standard-2003' would attribute them to a
    document that does not contain them — quiet false provenance, which is the
    failure this field exists to prevent."""
    for rv in [ergonomics.SEAT_MIN_MM,
               ergonomics.MAX_PERSONS_MUST_FIT_IN_Z1_PLUS_INTERIOR,
               *ergonomics.DECK_ZONE_ACCESS.values()]:
        assert "2024" in rv.source
        assert rv.basis == "approx", (
            "a 2024-preview number must not claim the 2003 basis")


def test_the_iso_deck_numbers_do_claim_the_standard_basis():
    # The converse: the 2003 clauses WERE verified from the text, so shipping
    # them as 'approx' would understate what we hold and keep them queued for a
    # purchase that has already effectively happened.
    for rv in [ergonomics.BARRIER_LOW_MIN_MM, ergonomics.BARRIER_HIGH_MIN_MM,
               ergonomics.STANCHION_TEST_LOAD_N,
               *ergonomics.SIDE_DECK_WIDTH_MIN_MM.values()]:
        assert rv.basis == "standard-2003"
        assert "15085:2003" in rv.source


def test_nothing_claims_a_purchased_basis_yet():
    """'purchased' means somebody bought and read the text. Nothing has been.
    If this test starts failing, the PURCHASE queue should have shrunk in the
    same change."""
    claimed = {k: v for k, v in refdata.all_constants().items()
               if v.basis == "purchased"}
    assert not claimed, claimed
    assert len(refdata.PURCHASE_QUEUE) >= 6


def test_side_deck_widths_are_ordered_by_exposure():
    w = ergonomics.SIDE_DECK_WIDTH_MIN_MM
    assert w["D"].value < w["C"].value < w["A"].value
    assert w["A"].value == w["B"].value


# ------------------------------------------------------- the flotation core

def test_the_submerged_factor_formula_reproduces_the_printed_K():
    """K = (SG-1)/SG is exact arithmetic, so the two materials whose SG the
    plan ALSO prints are a transcription check on both numbers at once — the
    same trick benchmarks/holtrop_cases.py uses to trust an OCR'd table."""
    # Tolerance is ONE UNIT IN THE LAST PRINTED PLACE (the plan prints K to
    # two decimals), not a tuned number. MEASURED residuals: GRP 0.0033
    # (0.3333 printed 0.33), fir plywood 0.0082 (-0.8182 printed -0.81) —
    # both pure rounding of the plan's own arithmetic. A transcription error
    # in either SG or K breaks this.
    for material in ("grp_laminate", "fir_plywood"):
        sg = flotation.MATERIAL_SG[material].value
        printed = flotation.MATERIAL_K[material].value
        assert flotation.submerged_factor(sg) == pytest.approx(printed, abs=1e-2)


def test_plywood_floats_and_grp_does_not():
    """The finding BuildPlan 2 §1.4 turns into a product decision: our own
    developable-plywood grammar is already halfway to an unsinkable SKU."""
    assert flotation.MATERIAL_K["fir_plywood"].value < 0
    assert flotation.MATERIAL_K["grp_laminate"].value > 0
    assert flotation.submerged_factor(1.0) == 0.0
    with pytest.raises(ValueError):
        flotation.submerged_factor(0.0)


def test_the_foam_buoyancy_restatement_is_consistent():
    """60.3 lb/ft^3 and 966 kg/m^3 are the SAME number printed twice by the
    plan. Two printings of one quantity is the drift risk limits.py exists
    for, so it is checked rather than trusted."""
    lb_ft3 = flotation.FOAM_NET_BUOYANCY_LB_FT3.value
    kg_m3 = flotation.FOAM_NET_BUOYANCY_KG_M3.value
    assert lb_ft3 * 16.018463 == pytest.approx(kg_m3, rel=2e-3)


def test_the_aging_derate_is_labelled_as_ours_not_as_a_source():
    """A policy number wearing a regulator's citation is the worst kind of
    false provenance, because it is the one nobody re-opens."""
    rv = flotation.FOAM_AGING_DERATE
    assert rv.value == -0.15
    assert "OURS" in rv.note and "no standard" in rv.note
    assert "policy" in rv.source.lower()


def test_polystyrene_is_banned_with_its_reason_attached():
    rv = flotation.POLYSTYRENE_BANNED
    assert rv.value is True
    assert "gasoline" in rv.note and "flammable" in rv.note


def test_the_uscg_scope_says_it_does_not_govern_us():
    """Honesty rule 5's shape, one tier over: we adopt a method, not a
    regulation. 6.096 m is BELOW the whole SKU range (4-14 m nominally, but
    the Solar Liveaboard is 9-14 m and the reference product is 10 m)."""
    rv = flotation.SCOPE_IS_NOT_OURS
    assert rv.value == pytest.approx(6.096, abs=1e-3)
    assert "does not govern" in rv.note or "do not govern" in rv.note
    assert "assessment aid" in rv.note


def test_the_two_swamped_heel_bars_are_distinct():
    # 10 deg swamped and 30 deg with an off-centre load are different tests.
    # Collapsing them was not observed here; it is pinned before it can be.
    assert (flotation.SWAMPED_HEEL_MAX_DEG.value
            < flotation.SWAMPED_OFFCENTRE_LOAD_HEEL_MAX_DEG.value)


# --------------------------------------------------- what we did NOT source

@pytest.mark.parametrize("module", [ergonomics, flotation])
def test_absent_quantities_are_recorded_with_a_reason(module):
    assert module.NOT_SOURCED, f"{module.__name__} claims nothing is missing"
    for a in module.NOT_SOURCED:
        assert isinstance(a, Absent)
        assert a.what and len(a.why) > 40, a


def test_the_paywalled_material_is_absent_rather_than_invented():
    """The specific things BuildPlan 2 §1 names as paywalled or uncaptured.
    Each must appear as ABSENT — not as a plausible float."""
    names = set(refdata.absent())
    for expected in ("ergonomics.anthropometric_percentile_tables",
                     "ergonomics.percentile_stretch_factor",
                     "ergonomics.abyc_h41_dimensions",
                     "ergonomics.iso15085_2024_zone_equipment",
                     "flotation.iso9094_fire_thresholds",
                     "flotation.reference_area_freeboard_rules"):
        assert expected in names, expected


def test_no_anthropometric_body_dimension_was_invented():
    """Panero & Zelnik is the book the plan names, and we do not hold it. The
    accommodation numbers we DO ship are marine practice, and every one of
    them says so — none is attributed to Panero."""
    for name, rv in refdata.constants(ergonomics).items():
        assert "Panero" not in rv.source, name


def test_gate_v24_has_no_validation_set_and_says_so():
    """Gap E1's shape, caught before it can repeat: Gate 1's bar named
    Holtrop-Mennen while nothing implemented it, and Gate 1 printed GREEN.
    Gate V2.4's bar names the USCG worked examples. They are not in the repo,
    and that is recorded as ABSENT so V2.4 cannot go green on the method
    alone."""
    a = refdata.absent()["flotation.uscg_worked_examples"]
    assert "worked example" in a.why


def test_percentile_is_available_but_never_faked():
    """The plan's ergonomic rules are percentile-PARAMETERISED. The field
    exists on RefValue; nothing fills it, because we hold no percentile
    table. An empty field here is the honest state, not an oversight."""
    assert "percentile" in RefValue.__dataclass_fields__
    assert all(rv.percentile is None
               for rv in refdata.constants(ergonomics).values())


def test_units_are_declared_everywhere_including_flags():
    for name, rv in refdata.all_constants().items():
        assert rv.unit is not None, name
        if isinstance(rv.value, bool):
            assert rv.unit == "", f"{name}: a flag has no unit"
        elif isinstance(rv.value, (int, float)):
            assert rv.unit, f"{name}: numeric value with no unit"
            assert math.isfinite(rv.value)


def test_every_edition_defect_has_a_purchase_row():
    """What closes a RED gate must be on the list a purchaser actually runs.

    MEASURED 2026-08-12. `review.edition_defects()` named the two standards
    Gate 6R is red for:

        ISO 12215-5: edition is a placeholder ('edition not recorded — set this')
        ISO 12217-1: edition is a placeholder ('edition not recorded — set this')

    `refdata.PURCHASE_QUEUE` listed NEITHER, while docs/research/COMPLIANCE.md
    §11 listed "ISO 12217-1 full text" and not 12215-5. Three lists of what to
    buy, all three different, and the one in CODE — the one anyone would run to
    answer "what do I buy to go green" — omitted both items that would do it.
    A list declared twice, applied to this project's own procurement.

    The fence is deliberately one-directional: a queue row may exist without an
    edition defect (12217-2 and 12215-7 block SKUs rather than a gate, and
    nothing implements them, so they CANNOT have an edition defect). What may
    never happen is the reverse — a standard whose absence is holding a gate
    red, with nothing telling the buyer to buy it.
    """
    from navalai.refdata import PURCHASE_QUEUE
    from navalai.rules.review import edition_defects

    queue = "\n".join(PURCHASE_QUEUE)
    missing = []
    for defect in edition_defects():
        std = defect.split(":")[0].strip()          # "ISO 12215-5"
        if std not in queue:
            missing.append(std)
    assert not missing, (
        f"{missing} hold Gate 6R RED and are not in PURCHASE_QUEUE — the buyer "
        f"cannot find what closes the gate. Add a row naming WHICH numbers the "
        f"purchase supplies, not just the standard's title")


def test_a_purchase_row_says_what_it_supplies_not_just_a_title():
    """A row reading 'ISO 12217-1' is a shopping list entry nobody can act on:
    it does not say which numbers are stand-ins, so a buyer cannot tell whether
    the PDF they found is the one that helps. Every row names its consequence.
    """
    from navalai.refdata import PURCHASE_QUEUE

    for row in PURCHASE_QUEUE:
        assert len(row) > 60, f"purchase row is a bare title: {row!r}"
        assert "—" in row or "-" in row, f"no rationale separator: {row!r}"
