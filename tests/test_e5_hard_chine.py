"""GATE E5-CHINE — the geometry kernel against real HARD-CHINE hulls.

E5 validated the kernel against published round-bilge and mathematical hulls
and it passes. This gate exists because that is not the same claim as the one
this product needs, and merging the two would let the weaker claim be quoted
as the stronger. NavalAI designs plywood stitch-and-glue boats. Those are
hard-chine by construction, and a chine is a DISCONTINUITY in surface slope
that no integral quantity in E5 can see: volume, waterplane area and prismatic
coefficient are identical for a sharp chine and a radiused bilge of the same
sectional area.

    E5       = the kernel reproduces published round-bilge hull families
    E5-CHINE = the kernel reproduces published HARD-CHINE hull families

THIS GATE IS EXPECTED RED, AND THE LEDGER SAYS SO. It is red because the
kernel measurably cannot express the hulls, not because the evidence is
missing -- the evidence was acquired, it is public-domain and closed-form,
and the refusals are precise. A gate that goes red for a reason nobody can
state is a broken gate; this one names three numbers.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from benchmarks.e5_chine import CHINE_STATIONS
from benchmarks.e5_hydro import particulars
from navalai import grammar
from scripts.extract_e5_offsets import read_table

FIX = pathlib.Path(__file__).resolve().parent / "e5_hard_chine"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


def _ids() -> list[str]:
    return sorted(d.name for d in FIX.iterdir()
                  if d.is_dir() and (d / "source_offsets.csv").exists())


# --------------------------------------------------------------------------
# The evidence.
# --------------------------------------------------------------------------

def test_the_corpus_contains_real_hard_chine_geometry():
    rows = list(_ids())
    assert len(rows) >= 5, (
        f"E5-CHINE has {len(rows)} hard-chine fixtures. The point of this "
        f"gate is external hard-chine evidence; without it the gate is an "
        f"opinion.")


@pytest.mark.parametrize("hid", _ids())
def test_the_hard_chine_geometry_is_not_digitised_from_a_picture(hid: str):
    """PUBLISHED_PARAMETRIC or nothing.

    A body plan traced off a scan is `DIGITIZED_FROM_PUBLISHED_LINES` and must
    never be presented as original offsets. The Fridsma fixtures avoid the
    question entirely: Figure 1 of R-1275 PRINTS the equations of the chine
    planform and the keel profile, so the geometry is evaluated, not traced.
    """
    rec = json.loads((FIX / hid / "expected.json").read_text())
    assert rec["geometry_status"] == "PUBLISHED_PARAMETRIC"
    head = (FIX / hid / "source_offsets.csv").read_text()
    assert "NOTHING HERE IS DIGITISED FROM A DRAWING" in head
    assert "public release" in head


@pytest.mark.parametrize("hid", _ids())
def test_the_fixture_has_an_actual_chine(hid: str):
    """A chine is a corner. Assert the corner, not the parameter name."""
    rec = json.loads((FIX / hid / "expected.json").read_text())
    dead = np.array(rec["chine"]["deadrise_deg"])
    beta = rec["beta_deg"]
    mid = np.array(rec["chine"]["u"])
    body = (mid >= 0.2) & (mid <= 0.6)          # the prismatic run
    assert np.allclose(dead[body], beta, atol=0.05), (
        f"{hid}: the source deadrise over the prismatic body reads "
        f"{dead[body]} where the report states a constant {beta} deg")
    # The surface turns through the chine by 90 - deadrise, which is a real
    # corner for every deadrise the source uses.
    turn = np.array(rec["chine"]["turn_deg"])
    assert np.nanmin(turn[body]) > 55.0, (
        f"{hid}: the chine turns by only {np.nanmin(turn[body]):.1f} deg — "
        f"that is not a hard chine")


@pytest.mark.parametrize("hid", _ids())
def test_the_source_particulars_recompute_from_the_committed_offsets(hid):
    rec = json.loads((FIX / hid / "expected.json").read_text())
    tab = read_table(FIX / hid / "source_offsets.csv")
    head = [l for l in (FIX / hid / "source_offsets.csv").read_text()
            .splitlines() if l.startswith("#")]
    zw = [float(l.split("Design waterline z =")[1].split()[0])
          for l in head if "Design waterline z =" in l][0]
    p = particulars(tab["x_m"], tab["z_wl_m"], tab["y_m"], tab["z_keel_m"],
                    tab["z_sheer_m"], zw)
    for k, v in rec["source_particulars"].items():
        if not isinstance(v, (int, float)) or not np.isfinite(v):
            continue
        assert abs(p[k] - v) <= 1e-6 * max(1.0, abs(v))


# --------------------------------------------------------------------------
# The result: what the kernel does with them.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("hid", _ids())
def test_the_round_trip_result_is_recorded_and_is_not_dressed_up(hid: str):
    """Whatever happened, it is on the record and labelled honestly."""
    rec = json.loads((FIX / hid / "residuals.json").read_text())
    ap = rec["as_published"]
    assert ap["status"] in ("BUILT", "REFUSED")
    if ap["status"] == "REFUSED":
        assert ap["refusal"].strip(), "a refusal with no reason is useless"
        assert ap["is_pass"] is False
    ne = rec.get("nearest_expressible", {})
    if ne:
        assert ne["is_pass"] is False, (
            "the nearest-expressible hull has a CLAMPED Cp and can never be "
            "a pass; labelling it one would be reporting a hull the source "
            "does not describe as agreement with the source")


def test_the_reason_the_gate_is_red_is_a_number_not_a_shrug():
    """Three measured limits, each recoverable from a committed artifact."""
    rt = json.loads((DATA / "e5_hard_chine_roundtrip.json").read_text())
    assert rt, "no hard-chine round-trip record"
    cp_ceiling = float(grammar.HIGH[grammar.NAMES.index("Cp")])
    for hid, rec in rt.items():
        assert rec["source_Cp"] > cp_ceiling, (
            f"{hid} is inside the Cp box after all — then it should have "
            f"been round-tripped, not refused")
        assert rec["as_published"]["status"] == "REFUSED"

    warp = json.loads((DATA / "e5_chine_warp.json").read_text())
    res = warp["results"]
    ok = [k for k, v in res.items() if v["expressible"]]
    assert res["series62_clement_blount_1963"]["expressible"], (
        "a MONOHEDRAL hard-chine series must be expressible — if Series 62 "
        "has stopped fitting, the deadrise law changed")
    assert not res["nss_deluca_pensa_2017"]["expressible"], (
        "the Naples warped series is recorded as inexpressible; if that has "
        "changed the grammar gained an aft warp and this gate should be "
        "re-run, not quietly passed")
    assert 0 < len(ok) < len(res), (
        "the warp survey should separate monohedral from warped families; "
        f"it currently reports {len(ok)} of {len(res)} expressible")


def test_the_gate_document_states_the_limitation_in_words():
    doc = (pathlib.Path(__file__).resolve().parents[1] / "docs" / "gates"
           / "E5-CHINE.md").read_text()
    for phrase in ("parallel middle body", "warp", "Cp", "RED"):
        assert phrase in doc, f"docs/gates/E5-CHINE.md does not mention {phrase!r}"


# --------------------------------------------------------------------------
# THE BAR. This is the clause E5-CHINE is RED on, and it is meant to fail
# until the grammar can draw the hulls. It is NOT softened to pass: the
# refusal is recorded in data/gate-ledger.json with a measured watermark, an
# owner and a review_by date, which is how this project keeps a known red
# distinguishable from a new one.
# --------------------------------------------------------------------------

def test_the_recorded_hard_chine_limits_are_still_what_the_ledger_says():
    """The WATERMARK clause. Gate 0E5C-CAP is the RED row; this pins its number.

    The capability itself is declared RED as a status row, exactly as Gate 4F
    and Gate 6D are, because this suite legitimately PASSES: the evidence was
    acquired, the refusals are recorded, and nothing is dressed up. What must
    not happen silently is the measurement CHANGING -- if the grammar gains an
    aft warp tomorrow, or someone widens `beta_len`, this test fires and
    forces `data/gate-ledger.json` to be updated rather than letting a stale
    watermark describe a kernel that has moved.

    It fires in BOTH directions on purpose. Better is as much a reason to
    re-record as worse.
    """
    from scripts.e5_chine_warp import WARP_TOL_DEG
    warp = json.loads((DATA / "e5_chine_warp.json").read_text())["results"]
    rt = json.loads((DATA / "e5_hard_chine_roundtrip.json").read_text())
    expressible = sorted(k for k, v in warp.items() if v["expressible"])
    refused = sorted(k for k, v in rt.items()
                     if v["as_published"]["status"] == "REFUSED")
    led = json.loads((DATA / "gate-ledger.json").read_text())["Gate 0E5C-CAP"]
    assert len(expressible) == 2 and len(refused) == 5, (
        f"the hard-chine watermark has MOVED: {len(expressible)} of "
        f"{len(warp)} series expressible within {WARP_TOL_DEG} deg "
        f"({expressible}), {len(refused)} of {len(rt)} hulls refused. The "
        f"ledger records 2 and 5. Re-measure, then update "
        f"data/gate-ledger.json — do not edit this number to match.")
    assert "2 of 7" in led["watermark"], (
        "the ledger watermark no longer states the measured count")
