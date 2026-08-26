"""Gate G-VISUAL: the canonical views exist, and a refusal can be SEEN.

MOTIVATING INCIDENT, three times over: the 2026-08-23 plank (four hulls
delivered before anyone rendered one), the 2026-08-24 spearhead and the
houseboat19 paddle boat were each found by a HUMAN opening a file — the
render was the last stage of the chain, downstream of every gate, and the
audit's validity ladder read level L4 (visually recognizable) as having NO
enforcement at all. `navalai/views.py` is MORPHOLOGY-V1.md §6 built:
fixed views, identical every time, written beside the descriptor sheet.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from navalai import grammar
from navalai.geometry import Hull
from navalai.reference import REFERENCE_HULL, reference_params
from navalai.views import SECTION_FRACS, canonical_views


def test_the_view_set_is_fixed_and_complete(tmp_path):
    """The §6 contract: profile, plan, design-waterline, body plan,
    transverse sections, isometric — every one, every time, plus the
    machine sheet. No arbitrary cameras, no optional views."""
    sheet = canonical_views(Hull(reference_params()), tmp_path, name="ref")
    assert set(sheet["views"]) == {"profile", "plan", "waterline",
                                   "bodyplan", "sections", "isometric"}
    for p in sheet["views"].values():
        f = Path(p)
        assert f.exists() and f.stat().st_size > 5000, f
    js = tmp_path / "ref-shape.json"
    assert js.exists()
    assert json.loads(js.read_text())["views"] == sheet["views"]


def test_a_refused_shape_is_seen_not_only_read(tmp_path):
    """THE POINT OF THE ARTIFACT. The reference hull is the recorded
    SPEARHEAD specimen; its sheet must carry the failing verdict, the
    NAMED finding and a positive margin — and the views must still be
    written, because an artifact that skips refused hulls is exactly how
    a plank passes review unseen."""
    sheet = canonical_views(Hull(reference_params()), tmp_path, name="ref")
    assert sheet["critique_ok"] is False
    assert any("SPEARHEAD" in f for f in sheet["findings"])
    assert sheet["shape_margin"] > 0
    assert Path(sheet["views"]["isometric"]).exists()


def test_a_plausible_hull_sheet_reads_clean(tmp_path):
    """The landed barge (Gate BARGE's fixture) is critique-clean; its
    sheet must say so with a negative margin — the artifact discriminates,
    it does not merely decorate."""
    g = dict(REFERENCE_HULL, LWL=15.2, BWL=4.0, T=0.391, D=1.55,
             r_stem=0.40, r_transom=0.92, Cp=0.92, lcb=-1.5, x_mb=0.50,
             beta_mid=8.0, beta_bow=10.0, beta_len=0.45, roundness=0.0,
             rocker=0.0, forefoot=0.10, flare=6.0, sheer_rise=0.12)
    sheet = canonical_views(Hull(grammar.vector(g)), tmp_path, name="barge")
    assert sheet["critique_ok"] is True
    assert sheet["findings"] == []
    assert sheet["shape_margin"] < 0


def test_the_section_stations_bracket_both_ends():
    """The fixed fractions must reach into both ends where geometry
    changes fastest — a strip that samples only the midbody would have
    shown the plank as a healthy rectangle."""
    assert min(SECTION_FRACS) <= 0.05 and max(SECTION_FRACS) >= 0.95
    assert list(SECTION_FRACS) == sorted(SECTION_FRACS)
