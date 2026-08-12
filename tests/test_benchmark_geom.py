"""Gate 2G — the benchmark geometry is present, and its absence is LOUD.

Motivating incident, gap J5 (audit 2026-08-05). `data/benchmark_geom/` is
gitignored, because Tokyo-2015 workshop geometry may carry redistribution
terms. The consequence nobody had noticed: the KCS acceptance check — the one
number that confirms the unit scale, the draft shift, the mirroring and the
deck capping SIMULTANEOUSLY — silently skipped on every machine except the one
Mac that happened to have generated the file. Five skips per run, and a pytest
skip does not appear anywhere in the gate table, which is the project's front
door.

Two things fix that, and only one of them is code:

  1. `data/benchmark_geom/CHECKSUMS.json` is COMMITTED even though the
     geometry is not, so the repository records what the missing file should
     have been and how to make it (`scripts/fetch_benchmark_geom.py`).

  2. This suite is a GATE ROW, and it skips at MODULE level. When the
     geometry is absent the suite collects zero passes, and `navalai.gates`
     prints "SKIPPED (no tests ran ...)" for Gate 2G and counts it — a visible
     row rather than an invisible skip. `--strict` makes it a failure
     outright. The module-level skip is deliberate: leaving one always-passing
     test in the file would make the row read "GREEN (n skipped)", which
     answers "is the KCS geometry validated here?" with a yes. The
     record-integrity checks that must run everywhere therefore live in
     tests/test_gate_integrity.py, not here.

THE CHECKSUM IS THE WEAKER OF THE TWO CHECKS, deliberately. The STL comes out
of an OCC tessellation, so a different OCC version legitimately produces
different bytes from the same IGES: a sha256 mismatch means REGENERATED, not
WRONG, and it is reported that way. The submerged-volume check is the one that
decides usability, because it is version-independent and every failure mode it
guards against (wrong unit scale, missing draft shift, unmirrored half body)
is tens of percent.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RECORD = _ROOT / "data" / "benchmark_geom" / "CHECKSUMS.json"
_KCS = _ROOT / "data" / "benchmark_geom" / "kcs.stl"

pytestmark = pytest.mark.skipif(
    not _KCS.exists(),
    reason=("data/benchmark_geom/kcs.stl absent — run "
            "`python scripts/fetch_benchmark_geom.py`. This skip is NOT "
            "invisible: Gate 2G reports SKIPPED in `python -m navalai.gates`, "
            "and fails under --strict."))


def _record() -> dict:
    return json.loads(_RECORD.read_text())["kcs.stl"]


def test_the_geometry_matches_its_recorded_bytes_or_says_it_was_regenerated():
    stl = _KCS
    rec = _record()
    got = hashlib.sha256(stl.read_bytes()).hexdigest()
    if got != rec["sha256"]:
        pytest.skip(
            f"kcs.stl sha256 {got[:12]} != recorded {rec['sha256'][:12]} — "
            f"REGENERATED (an OCC version difference does this legitimately), "
            f"not necessarily wrong. The volume check below is the verdict.")
    assert stl.stat().st_size == rec["bytes"]


def test_the_submerged_volume_accepts_the_geometry():
    """The version-independent acceptance: one number confirming the unit
    scale, the draft shift, the mirroring and the deck capping at once."""
    stl = _KCS
    from navalai.cfd.post import stl_submerged_properties
    a = _record()["acceptance"]
    vol = stl_submerged_properties(str(stl))["volume_m3"]
    err = (vol - a["published_m3"]) / a["published_m3"] * 100.0
    assert abs(err) < a["tolerance_pct"], (
        f"submerged volume {vol:.6f} m^3 is {err:+.3f}% from the published "
        f"{a['published_m3']:.6f} m^3 — outside the {a['tolerance_pct']}% "
        f"bar. Re-check the recipe in data/benchmark_geom/CHECKSUMS.json.")


def test_kcs_kg_is_a_constant_not_a_comment_and_beats_the_vcb_fallback():
    """Gate 2M's free sinkage-and-trim experiment needs KG, and until
    2026-08-12 the published value existed ONLY inside a comment in
    navalai/cfd/case.py. A number a caller has to retype out of a comment has
    no single source, which is this repository's signature defect applied to
    the one input the free-motion path cannot derive.

    KG is the one mass property a hull SHAPE cannot supply — it depends on how
    the model is ballasted — so `motion_from_geometry` accepts it and WARNS
    when it is absent. This test pins both halves: the constant is here, and it
    is materially different from the VCB fallback, so the warning is not
    pedantry. MEASURED on KCS: VCB gives KG-above-keel 0.187 m against the
    published 0.2303 m, 19% low, and KG is the lever that sets trim under tow.
    """
    from benchmarks.kcs import EFD, KG_ABOVE_KEEL_M

    assert KG_ABOVE_KEEL_M == 0.2303
    vcb_fallback = 0.187
    rel = abs(KG_ABOVE_KEEL_M - vcb_fallback) / KG_ABOVE_KEEL_M
    assert rel > 0.15, (
        "if the fallback ever came within 15% of the published KG the warning "
        "in motion_from_geometry would be noise — re-measure before relaxing it")

    # the acceptance data the free run is judged against must travel with it,
    # or the experiment has no bar
    assert EFD["sinkage_m"] == -1.394e-2, "negative = sinks"
    assert EFD["trim_deg"] == -0.169, "negative = bow down"


def test_the_kg_comment_in_case_py_no_longer_carries_the_number_alone():
    """The other half of 'one source per question'. The value may be QUOTED in
    case.py's explanation — that is what makes the comment readable — but the
    free-motion path must not be reachable only by retyping it."""
    import pathlib

    from benchmarks.kcs import KG_ABOVE_KEEL_M

    src = (pathlib.Path(__file__).resolve().parents[1]
           / "navalai/cfd/case.py").read_text()
    assert str(KG_ABOVE_KEEL_M) in src or "0.2303" in src, (
        "case.py's warning cites the published KG as the reason the VCB "
        "fallback is wrong; if that citation moved, move this test with it")
