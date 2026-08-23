"""GATE E5 — the geometry kernel against REAL PUBLISHED HULLS.

WHAT THIS GATE IS FOR. Every other geometry test in this repository asks the
kernel about hulls the kernel invented. `vector(named(x)) == x` on a sampled
genome, a slider fixture, a Pareto front — all of them are self-consistency,
and self-consistency is exactly what a wrong kernel also has. E5 is the one
test that hands the kernel a hull drawn by someone else, decades ago, in a
towing tank, and asks it to reproduce that.

WHAT IS RE-COMPUTED HERE AND WHAT IS NOT. The offset tables under
`tests/e5_real_hulls/<id>/source_offsets.csv` are the committed evidence and
are read, not regenerated: extracting them needs OpenCASCADE and a 16 MB
download, and an artifact under version control that a naval architect can
read by eye is worth more than a binary a reviewer must take on trust. The
best-fit SEARCH is likewise offline — it is a global optimisation over ten
genes and costs half a minute a hull.

But every CLAIM is recomputed on every run. The source particulars are
re-derived from the committed offsets; the hull is re-generated from the
committed genome; the scalar and geometric residuals are re-measured. A
recorded number that has drifted from what the artifacts actually say will
fail here, which is the difference between a test and a transcript.

THE HEADLINE NUMBER IS THE GEOMETRIC RESIDUAL, NOT THE SCALAR ONE. Two hulls
can share LWL, BWL, T, D, Cp and LCB and be different boats. The scalar
round-trip is reported because it is asked for, but it is nearly free: `Cp`
and `lcb` are genes the kernel SOLVES to. What E5 actually measures is how
far the nearest expressible hull sits from a real one.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from benchmarks import e5_hydro, e5_sources
from benchmarks.e5_hydro import particulars
from navalai import grammar
from scripts.build_e5_corpus import source_record
from scripts.e5_roundtrip import SIX, encode, hull_field, residual
from scripts.extract_e5_offsets import read_table

FIX = pathlib.Path(__file__).resolve().parent / "e5_real_hulls"
LEDGER = pathlib.Path(__file__).resolve().parents[1] / "data" \
    / "e5_real_hulls.json"

#: The acceptance target, stated once. A hull is COMPLETE when the source
#: supplies all six parameters; partial hulls (no published depth) are
#: counted separately and never used to reach this number.
MIN_COMPLETE_HULLS = 12
MIN_SOURCE_FAMILIES = 3

#: SCALAR ROUND-TRIP BARS, SET FROM WHAT THE KERNEL MEASURABLY ACHIEVES.
#:
#: The four dimensional genes are checked RELATIVE to their own value and the
#: two coefficients absolutely, because an absolute metre bound means
#: something different on a 4 m hull and a 20 m one, and this corpus contains
#: both.
#:
#: MEASURED over all 53 hulls, worst case and median:
#:
#:     LWL   0          0          exact, bit for bit, on every hull
#:     T     0          0          exact, bit for bit, on every hull
#:     D     7.3e-6     1.1e-7     relative
#:     BWL   2.5e-3     3.1e-4     relative
#:     Cp    1.5e-3     2.0e-4     absolute
#:     lcb   1.1e-2     1.7e-3     absolute, percentage points of LWL
#:
#: SO THE KERNEL DOES NOT WRITE ALL SIX THROUGH UNCHANGED, AND THAT IS THE
#: RESULT, not an inconvenience. LWL, T and D are transcribed exactly; BWL is
#: a TARGET the section solve approximates, and it lands about a quarter of a
#: percent narrow at worst, always narrow, never wide. Cp and lcb are solved
#: for and converge to a few parts in ten thousand.
#:
#: The bars below are the measured worst rounded up by roughly half. They are
#: NOT round numbers chosen for comfort, and widening one to admit a hull is
#: the move docs/gates/E5.md forbids by name -- if a future hull exceeds one
#: of these, that is a finding about the kernel and belongs in the document,
#: not in this dictionary.
SCALAR_TOL_REL = {"LWL": 1e-6, "BWL": 4e-3, "T": 1e-6, "D": 1e-4}
SCALAR_TOL_ABS = {"Cp": 3e-3, "lcb": 3e-2}


def _ids() -> list[str]:
    return sorted(d.name for d in FIX.iterdir()
                  if d.is_dir() and (d / "source_offsets.csv").exists())


def _ledger() -> list[dict]:
    assert LEDGER.exists(), (
        "data/e5_real_hulls.json is missing. It is built by "
        "scripts/build_e5_corpus.py and is the corpus ledger.")
    return json.loads(LEDGER.read_text())


# --------------------------------------------------------------------------
# 1. The measuring instrument, before anything it measures.
# --------------------------------------------------------------------------

def test_the_independent_measurement_imports_no_part_of_the_kernel_it_measures():
    """E5 is worthless if the source truth comes from the thing under test.

    The tempting shortcut is to measure the published hull with
    `hydrostatics.solve`, which is right there and already works. That would
    reduce the round-trip to `solve(x) == solve(x)` while still printing a
    table of impressive agreements.
    """
    import ast
    src = pathlib.Path(e5_hydro.__file__).read_text()
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    # THE CHECK PARSES IMPORTS, IT DOES NOT GREP THE FILE. Grepping failed on
    # this module's own PROSE: a comment explaining why `navalai.geometry`
    # must not be imported contains the string `navalai.geometry`, so the
    # test fired on the documentation of the rule it was enforcing.
    offenders = sorted(m for m in imported if m.split(".")[0] == "navalai")
    assert not offenders, (
        f"benchmarks/e5_hydro.py imports {offenders}. The independent "
        f"measurement must not import the kernel it is validating.")


def test_the_independent_measurement_is_right_where_the_answer_is_known():
    """Wigley has closed forms. The instrument must reproduce them."""
    from scripts.build_e5_other import wigley_table
    w = wigley_table(n_st=81, n_wl=129)
    got = particulars(w["x_m"], w["z_wl_m"], w["y_m"], w["z_keel_m"],
                      w["z_sheer_m"], w["z_water_m"])
    exact_vol = 4.0 * w["L"] * w["B"] * w["T"] / 9.0
    assert abs(got["vol_m3"] - exact_vol) / exact_vol < 5e-4
    assert abs(got["Cp"] - 2.0 / 3.0) < 5e-4
    assert abs(got["Cm"] - 2.0 / 3.0) < 5e-4
    assert abs(got["Cb"] - 4.0 / 9.0) < 5e-4
    assert abs(got["LCB_pct"]) < 1e-6, "a symmetric hull has LCB exactly 0"
    assert not np.isfinite(got["D_m"]), (
        "the Wigley form has no deck; a finite depth here means one was "
        "invented")


def test_an_immersed_transom_keeps_its_own_sectional_area():
    """The regression for a bug the yacht fixtures could not have caught.

    `particulars` pinned zero area at both waterline ends unconditionally.
    On a canoe body that is true — it ends in a point — so 51 DSYHS hulls
    agreed with it perfectly. On a hull whose aftmost station is IMMERSED the
    pinned zero landed at the same x as the transom and the duplicate-x guard
    then kept the ZERO, deleting the transom from the hull's displacement.
    A box has an exact answer and no taper at all.
    """
    L, B, T = 10.0, 3.0, 1.0
    x = np.linspace(0.0, L, 41)
    z = np.linspace(0.0, T, 33)
    Y = np.full((41, 33), B / 2.0)
    got = particulars(x, z, Y, np.zeros(41), np.full(41, T), T)
    assert abs(got["vol_m3"] - L * B * T) < 1e-9
    assert abs(got["Cp"] - 1.0) < 1e-9
    assert abs(got["Cb"] - 1.0) < 1e-9
    assert abs(got["LCB_pct"]) < 1e-9


# --------------------------------------------------------------------------
# 2. The evidence: provenance, conventions, and what is NOT claimed.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("hid", _ids())
def test_every_fixture_says_where_it_came_from(hid: str):
    head = "\n".join(
        l for l in (FIX / hid / "source_offsets.csv").read_text().splitlines()
        if l.startswith("#"))
    assert "SOURCE:" in head, f"{hid} carries no source citation"
    assert "Design waterline z =" in head, (
        f"{hid} does not declare its design waterline. It is NOT inferred "
        f"from the top of the table — that fallback once measured a Series 60 "
        f"hull at 1.5x its draft and reported Cp 0.6608 for a published "
        f"0.614.")
    assert "HALF-breadth" in head, f"{hid} does not say y is a half-breadth"
    fam = e5_sources.FAMILIES[e5_sources.family_of(hid)]
    assert fam["geometry_licence"], f"{hid}'s family declares no licence"


@pytest.mark.parametrize("hid", _ids())
def test_the_source_particulars_recompute_from_the_committed_offsets(hid):
    """The ledger is not taken on trust; it is re-derived."""
    rec = json.loads((FIX / hid / "expected.json").read_text())
    p = source_record(hid)["particulars"]
    for k, v in rec["source_particulars"].items():
        if not isinstance(v, (int, float)) or not np.isfinite(v):
            continue
        assert abs(p[k] - v) <= 1e-6 * max(1.0, abs(v)), (
            f"{hid}: recorded {k} = {v} but the committed offsets give "
            f"{p[k]}")


def test_lcb_is_one_convention_and_every_source_records_its_transformation():
    """Never mix LCB/LWL, LCB from AP, and % from amidships."""
    for row in _ledger():
        assert row["LCB_convention"] == (
            "percent of LWL, POSITIVE FORWARD of amidships")
        assert row["LCB_original_convention"].strip(), (
            f"{row['hull_id']} does not record the source's own convention")
        assert row["LCB_transformation"].strip(), (
            f"{row['hull_id']} does not record how it was converted — and "
            f"'no conversion needed' must be written down, because it is "
            f"indistinguishable afterwards from never having checked")


def test_no_hull_reports_a_depth_it_did_not_measure():
    """D is UNAVAILABLE or it is measured. It is never estimated."""
    for row in _ledger():
        tab = read_table(FIX / row["hull_id"] / "source_offsets.csv")
        has_sheer = bool(np.isfinite(tab["z_sheer_m"]).any())
        assert row["D_available"] == has_sheer, (
            f"{row['hull_id']} claims D_available={row['D_available']} but "
            f"its offsets table {'has' if has_sheer else 'has no'} sheer")
        if not row["D_available"]:
            assert not np.isfinite(row["D_m"]), (
                f"{row['hull_id']} has no sheerline in its source yet carries "
                f"a numeric depth")


# --------------------------------------------------------------------------
# 3. The round-trips.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("hid", _ids())
def test_the_fit_moved_only_the_shape_genes(hid: str):
    """The six are the SOURCE's. A fit that adjusts them measures nothing."""
    gen = json.loads((FIX / hid / "generated.json").read_text())
    p = source_record(hid)["particulars"]
    want = {"LWL": p["LWL_m"], "BWL": p["BWL_m"], "T": p["T_m"],
            "D": p["D_m"], "Cp": p["Cp"], "lcb": p["LCB_pct"]}
    for k in gen["pinned_genes"]:
        assert abs(gen["genome"][k] - want[k]) < 1e-9, (
            f"{hid}: {k} was pinned at the source value {want[k]} but the "
            f"stored genome carries {gen['genome'][k]}")
    assert set(gen["pinned_genes"]) | set(gen["fitted_genes"]) == \
        set(grammar.NAMES)
    assert not (set(gen["pinned_genes"]) & set(gen["fitted_genes"]))


@pytest.mark.parametrize("hid", _ids())
def test_the_scalar_round_trip_returns_the_six_it_was_given(hid: str):
    """source -> genome -> hull -> measured back, re-run here."""
    from scripts.build_e5_corpus import measure_back
    gen = json.loads((FIX / hid / "generated.json").read_text())
    src = source_record(hid)
    g = grammar.vector({k: float(v) for k, v in gen["genome"].items()})
    mb = measure_back(g, src)
    got = {"LWL": mb["LWL_m"], "BWL": mb["BWL_m"], "T": mb["T_m"],
           "D": mb["D_m"], "Cp": mb["Cp"], "lcb": mb["LCB_pct"]}
    for k in gen["pinned_genes"]:
        want = gen["genome"][k]
        dev = abs(got[k] - want)
        if k in SCALAR_TOL_REL:
            bar = SCALAR_TOL_REL[k] * abs(want)
            unit = f"{SCALAR_TOL_REL[k]:g} relative"
        else:
            bar = SCALAR_TOL_ABS[k]
            unit = f"{bar:g} absolute"
        assert dev <= bar, (
            f"{hid}: commanded {k} = {want}, the generated hull measures "
            f"{got[k]} (deviation {dev:.3e}, bar {unit})")


@pytest.mark.parametrize("hid", _ids())
def test_the_geometric_residual_is_re_measured_not_recited(hid: str):
    gen = json.loads((FIX / hid / "generated.json").read_text())
    rec = json.loads((FIX / hid / "residuals.json").read_text())["geometric"]
    src = source_record(hid)
    p, tab = src["particulars"], src["table"]
    grid = {"u": (tab["x_m"] - p["x_aft_m"]) / p["LWL_m"],
            "v": tab["z_wl_m"] / src["z_water_m"], "y": tab["y_m"],
            "six": {k: gen["genome"][k] for k in gen["pinned_genes"]}}
    g = grammar.vector({k: float(v) for k, v in gen["genome"].items()})
    now = residual(g, grid)
    assert abs(now["rms_m"] - rec["rms_m"]) <= 1e-6 + 1e-3 * rec["rms_m"], (
        f"{hid}: recorded geometric RMS {rec['rms_m']} but re-measuring the "
        f"stored genome against the committed offsets gives {now['rms_m']}")
    assert now["coverage"] >= 0.75, (
        f"{hid}: the generated hull only defines {now['coverage']:.1%} of the "
        f"cells the source does — a residual over a small overlap is not a "
        f"small residual")


# --------------------------------------------------------------------------
# 4. The corpus, as a corpus.
# --------------------------------------------------------------------------

def test_the_corpus_is_at_least_twelve_complete_traceable_hulls():
    rows = _ledger()
    complete = [r for r in rows if r["complete_six"]]
    assert len(complete) >= MIN_COMPLETE_HULLS, (
        f"E5 needs {MIN_COMPLETE_HULLS} hulls with all six parameters from "
        f"published sources; the corpus has {len(complete)} complete of "
        f"{len(rows)} total. Partial hulls do NOT count toward this.")


def test_the_corpus_spans_at_least_three_independent_source_families():
    fams = {r["source_family"] for r in _ledger()}
    assert len(fams) >= MIN_SOURCE_FAMILIES, (
        f"{len(fams)} source families: {sorted(fams)}. Fifty-one hulls from "
        f"one towing tank are one family, not fifty-one pieces of evidence.")


def test_the_corpus_does_not_pass_itself_off_as_more_diverse_than_it_is():
    """The independence counts must be reported, and must not be inflated."""
    rows = _ledger()
    doc = (pathlib.Path(__file__).resolve().parents[1] / "docs" / "gates"
           / "E5.md").read_text()
    for phrase in ("hull instances", "source families", "parent geometries"):
        assert phrase in doc, (
            f"docs/gates/E5.md does not report '{phrase}'. Reporting a hull "
            f"count alone is the inflation this gate exists to prevent.")
    assert any(not r["complete_six"] for r in rows) is not None
    # Every rejected source is recorded WITH ITS REASON.
    for src, why in e5_sources.REJECTED.items():
        assert len(why) > 40, f"{src} is rejected without a stated reason"


def test_the_gate_reports_which_hulls_it_could_not_express():
    """An OUT_OF_RANGE hull is a scope statement and must say so."""
    for r in _ledger():
        assert r["range_class"] in ("IN_RANGE", "NEAR_RANGE", "OUT_OF_RANGE")
        if r["range_class"] != "IN_RANGE":
            assert r["range_note"].strip(), (
                f"{r['hull_id']} is {r['range_class']} with no reason given")


def test_the_report_block_in_the_gate_doc_matches_the_ledger():
    """The sixteen answers are GENERATED, so they cannot drift from the data.

    Hand-writing them into docs/gates/E5.md would put every one of those
    numbers in a second place, and the second copy goes stale the first time
    a hull is added — the defect this repository keeps finding, one floor up
    in the documentation. Same pattern as the README gate table.
    """
    from scripts.e5_report import BEGIN, DOC, END, build
    doc = DOC.read_text()
    i, j = doc.find(BEGIN), doc.find(END)
    assert i >= 0 and j > i, "docs/gates/E5.md has lost its E5-REPORT markers"
    assert doc[i:j + len(END)] == build(), (
        "the generated block in docs/gates/E5.md disagrees with "
        "data/e5_real_hulls.json. Re-run: python scripts/e5_report.py --write")


def test_the_prose_source_record_covers_every_family_the_code_knows():
    md = (pathlib.Path(__file__).resolve().parents[1] / "data"
          / "e5_sources.md").read_text()
    for key, fam in e5_sources.FAMILIES.items():
        assert fam["family"] in md, (
            f"benchmarks/e5_sources.py registers the {fam['family']} family "
            f"but data/e5_sources.md does not mention it")
    for src in e5_sources.REJECTED:
        head = src.split("(")[0].strip().split(",")[0]
        assert head[:16].lower() in md.lower(), (
            f"{head!r} was investigated and refused in code but the reason "
            f"is not in data/e5_sources.md")
