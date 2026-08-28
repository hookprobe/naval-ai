"""Gate CFD-KB: the anchor book — measured CFD behaviour, reusable and
refused outside its support.

The owner's directive (2026-08-28): the hookprobe/hb19/KCS campaigns'
results must serve future designs without re-running. The book
(`data/cfd_anchors.json`) is EXTRACTED from the runs by
scripts/harvest_cfd_anchors.py — gap N6's answer: a run directory is
deletable, the committed record is not — and `navalai.cfd_kb` consumes
it with the surrogate honesty rule applied to measurements: refuse
outside the measured support, never extrapolate, never silently correct
the ladder.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from navalai import cfd_kb

BOOK = Path(__file__).resolve().parents[1] / "data" / "cfd_anchors.json"


def test_the_book_is_committed_and_carries_the_campaigns():
    doc = json.loads(BOOK.read_text())
    a = doc["anchors"]
    # the three campaign families the owner named, present and settled
    assert any(r["family"].startswith("hookprobe") and r["settled"]
               for r in a.values())
    assert any(r["family"] == "bluff_stern_houseboat" and r["settled"]
               for r in a.values())
    assert any(r["family"] == "slender_cargo_benchmark" and r["settled"]
               for r in a.values())


def test_every_record_is_honest_about_settledness_and_gci():
    doc = json.loads(BOOK.read_text())
    for name, r in doc["anchors"].items():
        assert "settled" in r and isinstance(r["settled"], bool), name
        if not r["settled"]:
            assert r["settle_reasons"], (
                f"{name} is unsettled with no recorded reason")
        assert r.get("single_grid_no_gci") is True, (
            f"{name}: no run in this book has a GCI; the flag must say so")
        assert r["total_n"] > 0 and 0 < (r["pressure_fraction"] or 0) < 1


def test_unsettled_records_never_support_a_prediction():
    settled = cfd_kb.anchors(settled_only=True)
    everything = cfd_kb.anchors(settled_only=False)
    assert len(everything) > len(settled), (
        "the book should carry unsettled records AS DATA (10 kn, 20 kn, "
        "seas) — if they vanished, the harvest dropped honesty for tidiness")
    assert all(a["settled"] for a in settled.values())


def test_the_bluff_family_split_is_the_measured_wave_dominance():
    band = cfd_kb.pressure_fraction_band("hookprobe_hybrid", fn=0.38)
    assert band, getattr(band, "reason", "")
    lo, hi, prov = band
    assert 0.75 <= lo <= hi <= 0.85, (lo, hi)
    # and KCS at its own Fn is NOT wave-dominated — the family distinction
    # is measured, not assumed
    kcs = cfd_kb.pressure_fraction_band("slender_cargo_benchmark", fn=0.26)
    assert kcs, getattr(kcs, "reason", "")
    assert kcs[1] < 0.5


def test_out_of_support_queries_are_refused_by_name():
    r1 = cfd_kb.pressure_fraction_band("hookprobe_hybrid", fn=0.90)
    assert not r1 and "new run" in r1.reason
    r2 = cfd_kb.pressure_fraction_band("no_such_family", fn=0.38)
    assert not r2 and "no_such_family" in r2.reason
    r3 = cfd_kb.l1_anchor_ratio("hookprobe_hybrid")
    assert not r3 and "bluff_stern_houseboat" in r3.reason


def test_the_l1_anchor_is_COMPUTED_from_the_book_not_stored():
    """P0-3: the ratio was a hardcoded 1.57 beside a book that already
    held 1733.47 N — this repo's recurring number-declared-twice defect,
    which cannot notice its own sources moving. It is now derived, and
    this test asserts the derivation rather than the value."""
    row = cfd_kb.l1_anchor_ratio("bluff_stern_houseboat")
    assert row, getattr(row, "reason", "")
    book = json.loads(BOOK.read_text())["anchors"][row["case"]]
    assert row["rans_total_n"] == book["total_n"], (
        "the ratio's numerator is not the book's own measurement")
    assert row["ratio"] == pytest.approx(
        book["total_n"] / row["l1_total_n"], rel=1e-12)
    assert 1.4 < row["ratio"] < 1.8          # the measured neighbourhood
    assert row["rel_sigma"] >= 0.2, (
        "a single-grid anchor with a narrow sigma is a lie about GCI")
    assert "NO GCI" in row["basis"] or "no GCI" in row["basis"]


def test_a_wave_loads_record_never_answers_a_resistance_question():
    """P0-2: the seas run has ZERO forward speed under a nominal speed
    label and a 132% batch error — "wrong measurement type", not merely
    unsettled. It must not reach a resistance query even if it settles."""
    doc = json.loads(BOOK.read_text())["anchors"]
    seas = doc.get("hookprobe_v3_seas")
    assert seas and seas["run_type"] == "wave_loads"
    assert "hookprobe_v3_seas" not in cfd_kb.anchors(settled_only=False)
    assert "hookprobe_v3_seas" in cfd_kb.anchors(settled_only=False,
                                                 run_type=None)


def test_a_failed_layer_stack_invalidates_the_viscous_half_only():
    """P0-2: the 20-kn record shipped a viscous force from a stack that
    achieved ~0.1% coverage. The record stays (it is real pressure/wave
    data) and says so."""
    doc = json.loads(BOOK.read_text())["anchors"]
    v5 = doc.get("hookprobe_v5_20kn")
    assert v5 is not None
    assert v5["viscous_valid"] is False, (
        "a viscous number from a failed layer stack is published as a "
        "measurement of friction")
    # and a well-layered settled run is flagged valid
    assert doc["hookprobe_v3"]["viscous_valid"] is True


def test_ct_is_flagged_untrusted_on_a_coarse_surface():
    """P0-1: v2 and v3 are one edit apart and their STL wetted areas read
    42.14 vs 34.28 m2 — because v2 is a 20096-facet export and v3 is
    152126. The denominator is not wrong; the surfaces are different
    objects, so a Ct compared across them compares triangulations."""
    doc = json.loads(BOOK.read_text())["anchors"]
    assert doc["hookprobe_v2"]["ct_trusted"] is False
    assert doc["hookprobe_v3"]["ct_trusted"] is True
    assert doc["hookprobe_v2"]["surface_facets"] < 50_000
    assert doc["hookprobe_v3"]["surface_facets"] > 100_000


def test_same_geometry_finds_prior_runs_by_sha_and_refuses_without_one():
    doc = json.loads(BOOK.read_text())
    sha = next((r["stl_sha256"] for r in doc["anchors"].values()
                if r.get("stl_sha256")), None)
    if sha:
        hits = cfd_kb.same_geometry(sha)
        assert hits and all(a["stl_sha256"] == sha for a in hits.values())
    assert not cfd_kb.same_geometry("")
    assert not cfd_kb.same_geometry("deadbeef" * 8)
