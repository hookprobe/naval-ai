"""Gate HULL-KB: the reference corpus is learned, and reconstruction is proven.

INCIDENT, 2026-08-25. The owner: "naval-ai currently fails to design boats
and succeeds at designing fishing boats" — and the protocol that followed
demanded the system PROVE it can reconstruct known hulls from extracted
features before being trusted to invent new ones. `data/hull_kb.json` is the
extracted-feature record of every image in `downloads/hull-examples` (which
is gitignored, so the KB must stand alone — gap J5's shape), and
`scripts/hull_kb_reconstruct.py` holds the parametric interpretations. These
tests pin the measured reconstruction results so a grammar or morphology
change that silently breaks a proven reconstruction fails loudly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from navalai import grammar, morphology  # noqa: E402
from navalai.geometry import Hull  # noqa: E402

import hull_kb_reconstruct as rk  # noqa: E402


def _load_kb() -> dict:
    return json.loads((REPO / "data" / "hull_kb.json").read_text())


def test_kb_taxonomy_cites_only_records_that_exist():
    """Every attested_by id must be a record id — a citation to a deleted
    record is gap N6's shape (prose outliving the artifact it cites)."""
    kb = _load_kb()
    ids = {r["id"] for r in kb["records"]}
    for fam, spec in kb["taxonomy"].items():
        if fam.startswith("_"):
            continue
        for ref in spec["attested_by"]:
            assert ref in ids, f"taxonomy {fam} cites missing record {ref}"


def test_kb_records_carry_their_provenance():
    kb = _load_kb()
    for r in kb["records"]:
        assert r.get("source_image"), r["id"]
        assert r.get("kind"), r["id"]


def test_cruiser_reconstruction_meets_the_reference_labels():
    """hull-example-004 labels: entrance < 12 deg, round bilge, parallel
    midbody. MEASURED at reconstruction (2026-08-25): alpha_e 11.8 deg,
    critique score 1.0 with zero findings. The bar is the SHEET'S label,
    not a preference."""
    genes = rk.TARGETS["cruiser"]["genes"]
    x = rk.vector_from_genes(genes)
    rep = grammar.check(x)
    assert rep.ok, rep.violations
    hull = Hull(x)
    assert hull.alpha_e_deg() <= 12.0
    crit = morphology.critique(morphology.describe(morphology.from_hull(hull)))
    assert not crit.findings, [str(f) for f in crit.findings]


def test_deepv_reconstruction_expresses_the_warped_deadrise_law():
    """hull-designs-gemini cell 1 labels 24 deg deadrise; the warped family
    (Naples NSS shape) needs transom < midship < forward. MEASURED at
    reconstruction: 14.0 / 24.0 / 27.1 deg. Gate 0E5C-CAP's 'no aft warp'
    verdict predates beta_run/beta_transom — this test is the measured
    counterexample that stands until that gate is re-verdicted."""
    genes = rk.TARGETS["deepv"]["genes"]
    x = rk.vector_from_genes(genes)
    assert grammar.check(x).ok
    hull = Hull(x)
    dy = np.maximum(hull.y_chine, 1e-9)
    beta = np.degrees(np.arctan2(hull.z_chine - hull.z_keel, dy))
    n = len(beta)
    mid = float(beta[n // 2])
    assert abs(mid - 24.0) <= 0.5, mid
    assert float(beta[0]) < mid < float(beta[int(0.75 * (n - 1))])


def test_concept_kernel_splits_one_body_into_two():
    """The hybrid topology is a TRANSITION, not two glued hulls: the tunnel
    half-width must be zero forward of the split and open aft of it, and the
    morph's divergence half-angle stays under the 10 deg separation bar the
    kernel documents (a diffusing passage past ~10 deg separates — drag paid
    for nothing)."""
    import math

    import hookprobe_hull as hp

    h = hp.Hookprobe()
    assert float(h.tunnel_half(np.array([0.90]))[0]) == 0.0
    assert float(h.tunnel_half(np.array([0.05]))[0]) > 0.0
    span = (h.x_split - h.x_full) * h.loa
    div = math.degrees(math.atan(1.875 * h.tunnel_half_max / span))
    assert div <= 10.0, div


def test_concept_wake_first_channel_arithmetic():
    """§11 of the owner's concept protocol: channel = D·(1 − 2·overlap), so
    the stern is sized BY the propulsor. The identity, and the overlap
    recovered from a measured channel, must agree."""
    import naval_ai_concept as nc

    D = 0.592
    chan = D * (1.0 - 2.0 * nc.OVERLAP_TARGET)
    overlap = (D - chan) / (2.0 * D)
    assert abs(overlap - nc.OVERLAP_TARGET) < 1e-12
    lo, hi = nc.drag_band_n(113.7, 16.0, 6 * 0.514444)
    assert 0 < lo < hi
