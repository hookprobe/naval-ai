"""Gate CFD-CMP — a CFD-informed comparison is in NEWTONS, or it is refused.

THE INCIDENT, and it is this project's own (CFD knowledge audit finding
R2). The hookprobe ladder recorded v1 -> v2 -> v3 as 3034 -> 2998 ->
2966 N and three aft-edit improvements were read out of it. MEASURED:
each step is 1.1-1.2%, inside the +/-2.5% window scatter, and v2 carries
19% more cells than v3 — the mesh differs by roughly twenty times the
effect claimed across it. The direction was defensible. Three numbers
were not.

THE SECOND INCIDENT (handoff item 4, 2026-08-28). `settled_drag.ct`
divides by each run's own STL wetted area, and v2/v3 read 42.14 vs
34.28 m2 FOR THE SAME HULL one edit apart, because v2 is a 20 096-facet
export and v3 is 152 126. A 23% denominator swing sits under every Ct in
the book. `ct_trusted` fences the records; it does not give the book one
denominator. So the kernel compares NEWTONS at equal speed, and this
suite is the fence that keeps it that way.

Both clauses already existed in `cfd/preflight.ab_comparable` and had NO
CALLER for a day — the defect class BUILD-PLAN section 16 names from nine
incidents in one day: a bar that exists and is not consulted. These tests
assert the bar FIRES, in both directions, on the real book.
"""

import numpy as np
import pytest

from navalai import cfd_kb
from navalai.cfd import preflight


def test_the_ladder_comparison_that_started_this_is_refused():
    """v2 vs v3 — the actual campaign comparison — must not produce a number."""
    book = cfd_kb.anchors(settled_only=False, run_type=None)
    if not {"hookprobe_v2", "hookprobe_v3"} <= set(book):
        pytest.skip("the hookprobe v2/v3 anchors are not in the book")
    out = cfd_kb.compare("hookprobe_v2", "hookprobe_v3")
    assert not out, (
        "the comparator returned a delta for v2 vs v3. Those meshes "
        "differ by 19% and the claimed effect is ~1% — this is the "
        "comparison the audit refused by hand, and the code must refuse "
        f"it too. Got: {out}")
    assert "mesh" in out.reason or "cells" in out.reason, (
        f"refused for the wrong reason: {out.reason}")


def test_a_real_effect_is_still_reported_and_in_newtons():
    """The appendage cost is 20x the scatter; refusing it would be a bug."""
    book = cfd_kb.anchors(settled_only=False, run_type=None)
    if not {"hookprobe_v3", "hookprobe_v4"} <= set(book):
        pytest.skip("the hookprobe v3/v4 anchors are not in the book")
    out = cfd_kb.compare("hookprobe_v3", "hookprobe_v4")
    assert out, (
        "the comparator refused the v3->v4 appendage A/B. That delta is "
        f"MEASURED at ~+979 N (24.8%), ten times the window scatter, on "
        f"meshes within 3% — a bar that refuses this refuses everything: "
        f"{getattr(out, 'reason', '')}")
    assert out["units"] == cfd_kb.COMPARE_UNITS == "newtons"
    assert out["delta_n"] > 0.0, "the appendages cost drag; the sign moved"
    assert out["delta_rel"] > preflight.WINDOW_SCATTER


def test_a_cross_speed_difference_is_not_a_geometry_comparison():
    # SETTLED calm-water records only, so the clause under test is the
    # SPEED one and not settledness firing first — a test that passes
    # because an earlier guard tripped proves nothing about this guard.
    book = cfd_kb.anchors(settled_only=True)
    pairs = [(a, b) for a in book for b in book
             if abs(float(book[a].get("speed_ms") or 0)
                    - float(book[b].get("speed_ms") or 0)) > 1e-3]
    if not pairs:
        pytest.skip("the book has no two anchors at different speeds")
    a, b = pairs[0]
    out = cfd_kb.compare(a, b)
    assert not out and "speed" in out.reason, (
        f"{a} vs {b} sit at different speeds and were differenced anyway: "
        f"{out}")


def test_the_window_scatter_is_single_sourced():
    """The bar is `preflight.WINDOW_SCATTER` and nothing may re-declare it.

    This repository's recurring defect is A NUMBER DECLARED TWICE, and it
    has already produced forceCoeffs wrong by exactly 2x and two GCI
    implementations disagreeing about a diverging family. 0.025 is a bar,
    so it gets the same treatment.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    hits = []
    for f in sorted((root / "navalai").rglob("*.py")):
        txt = f.read_text()
        for i, line in enumerate(txt.splitlines(), 1):
            if "0.025" in line and "WINDOW_SCATTER" not in line \
                    and "scatter" in line.lower():
                hits.append(f"{f.relative_to(root)}:{i}: {line.strip()}")
    assert not hits, ("the window scatter is declared a second time:\n"
                      + "\n".join(hits))


def test_the_books_ct_is_not_read_by_any_kernel_path():
    """Handoff item 4, fenced rather than merely written down.

    `cfd_kb` must not hand a Ct to a caller: its denominator is each run's
    own STL wetted area and that area moved 23% for one hull between two
    exports. `compare()` is the sanctioned path and it is in newtons.
    """
    out = cfd_kb.compare("hookprobe_v3", "hookprobe_v4")
    if out:
        assert "ct" not in out, (
            "compare() returned a Ct. Until the book has ONE wetted-area "
            "definition, a Ct crossing this boundary is a comparison "
            "against a moving denominator")
    # And the decision itself is single-sourced, so a future reader finds
    # the reasoning rather than re-deriving it from two exports.
    assert "wetted" in cfd_kb.__doc__.lower() or \
        "wetted" in open(cfd_kb.__file__).read().lower()


def test_every_comparison_the_book_supports_is_reachable_or_explained():
    """No settled same-speed pair may be silently uncomparable.

    A refusal is information; a refusal with no reason is a hole. Every
    pair the book could support must come back either with a delta or
    with a named clause.
    """
    book = cfd_kb.anchors(settled_only=True)
    names = sorted(book)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            out = cfd_kb.compare(a, b)
            if not out:
                assert out.reason and ":" in out.reason, (
                    f"{a} vs {b} refused without a named clause")
            else:
                assert np.isfinite(out["delta_n"])
