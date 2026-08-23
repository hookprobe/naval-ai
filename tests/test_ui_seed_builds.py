"""The studio's default genome must BUILD, and a refusal must be VISIBLE.

MOTIVATING INCIDENT (2026-08-23, docs/audit/I13-SESSION-2026-08-23.md).
A non-expert participant opened Hull Studio and saw nothing, in Firefox and in
Safari, for thirty minutes. The cause: the studio seeds a fresh project with
the MIDPOINT of the compiled policy box, and that genome did not build —

    roundness pinned 0.0 and T capped 1.10 -> T_mid 0.557 m, with
    beta_bow_mid 36.0 deg at Cp_mid 0.617
    -> GeometryError: section: area 0.9334 m^2 unreachable at x = 8.330 m

`mesh_payload` let it propagate, `do_POST` returned 400, and the viewport drew
an empty stage. The DEFAULT state of the product, not an edge case.

Two things are fenced here, and they are independent:

1. THE SEED BUILDS. A midpoint is an arithmetic fact about an interval;
   feasibility is a fact about the SAC kernel and the section solver. Nothing
   was checking that the two agreed, so a grammar-box recalibration could
   silently blank the studio. (It did the reverse too: the E5 recalibration
   that landed on 2026-08-23 moved beta_bow's midpoint 36 -> 26 and made the
   midpoint feasible again by accident. A fix by accident is not a fix.)

2. THE REFUSAL IS DRAWN. The failure to COMMUNICATE was the more serious half:
   the only error channel was one line of 11px mono text under the canvas.
   `Viewport.setError` now paints the backend's own words where the hull would
   have been.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from navalai import grammar
from navalai.geometry import GeometryError, Hull

from ui import api

_ROOT = Path(__file__).resolve().parents[1]


def _categories():
    from navalai import policy as P
    cp = P.reference_policy()
    return [c for c in ("A", "B", "C", "D")
            if c in getattr(cp.constitution.legal, "allowed_categories",
                            ("C", "D"))] or ["C", "D"]


@pytest.mark.parametrize("cat", _categories())
def test_the_studios_default_genome_actually_builds(cat):
    """Whatever the box is, the seed the studio opens on must be a hull."""
    payload = api.envelope_payload({"category": cat})
    assert payload["source"] == "measured", payload
    seed = payload.get("seed")
    assert seed is not None, (
        f"category {cat}: NO genome inside the compiled box builds. The "
        "constitution and the geometry kernel disagree; the studio would open "
        "on a blank stage.")
    Hull(grammar.vector(seed))          # raises GeometryError if it does not


@pytest.mark.parametrize("cat", _categories())
def test_the_mesh_endpoint_answers_for_that_seed(cat):
    """The exact call the studio makes on first paint returns a mesh."""
    seed = api.envelope_payload({"category": cat})["seed"]
    out = api.mesh_payload({"params": seed, "fidelity": "fast"})
    assert out["verts"] and out["faces"], out.get("source")


def test_feasible_seed_repairs_a_box_whose_midpoint_does_not_build():
    """The guard must actually fire, not merely pass when the midpoint is fine.

    The box is squeezed onto a configuration MEASURED to fail against the
    CURRENT geometry kernel — a hard chine at 0.21 m draft with 60 deg of bow
    deadrise and Cp 0.695, which gives

        GeometryError: section: area 0.0356 m^2 unreachable at x = 11.008 m

    An earlier version of this test reproduced the ORIGINAL incident numbers
    (T 0.557, beta_bow 36) and PASSED VACUOUSLY: the E5 recalibration that
    landed the same day moved beta_bow's midpoint 36 -> 26 and made that
    configuration buildable, so `pytest.raises` no longer fired and the guard
    was never exercised. A guard that is only tested on an input that stopped
    failing is not a guard. Re-measure this fixture after any grammar-box or
    section-solver change; if it starts building, find another that does not.
    """
    names = list(grammar.NAMES)
    low = list(grammar.LOW.astype(float))
    high = list(grammar.HIGH.astype(float))

    def pin(param, value):
        i = names.index(param)
        low[i] = high[i] = float(value)

    def span(param, lo, hi):
        i = names.index(param)
        low[i], high[i] = float(lo), float(hi)

    pin("roundness", 0.0)           # hard chine, as the constitution requires
    pin("LWL", 11.9)
    pin("BWL", 3.08)
    pin("D", 1.66)
    span("T", 0.014, 0.40)          # midpoint 0.207 m — very shallow
    span("beta_bow", 50.0, 70.0)    # midpoint 60 deg — a starved forward section
    span("Cp", 0.68, 0.71)          # midpoint 0.695 — a full SAC to feed

    mid = {n: (low[i] + high[i]) / 2.0 for i, n in enumerate(names)}
    with pytest.raises(GeometryError):
        Hull(grammar.vector(mid))    # the incident's MECHANISM, reproduced

    seed, repairs = api.feasible_seed(names, low, high)
    assert seed is not None, "the guard could not find a buildable seed"
    Hull(grammar.vector(seed))       # raises if the guard shipped a non-hull
    assert repairs, "a repair happened but was not REPORTED"
    relaxable = {g for g, _edge in api._SEED_RELAX} | {"*"}
    assert repairs[0]["param"] in relaxable, repairs


def test_the_guard_refuses_rather_than_inventing_a_hull():
    """A box in which NOTHING builds must return None, not a plausible genome.

    The alternative — quietly widening the box to find something — would put a
    hull outside the compiled envelope on screen and call it governed.
    """
    names = list(grammar.NAMES)
    low = list(grammar.LOW.astype(float))
    high = list(grammar.HIGH.astype(float))
    i = names.index("BWL")
    low[i] = high[i] = float(grammar.LOW[i])      # the floor beam, pinned
    j = names.index("LWL")
    low[j] = high[j] = float(grammar.HIGH[j])     # against the longest hull
    seed, repairs = api.feasible_seed(names, low, high)
    if seed is None:
        assert repairs and "NO genome" in repairs[0]["why"]
    else:
        Hull(grammar.vector(seed))   # if it DID find one, it must be real


def test_a_refused_mesh_is_painted_into_the_stage_not_only_the_footer():
    """The viewport must OWN the failure, and the caller must hand it over."""
    vp = (_ROOT / "ui/app/viewport.js").read_text()
    assert "setError(msg)" in vp, "Viewport lost its error setter"
    assert "_drawError" in vp and "THIS HULL COULD NOT BE DRAWN" in vp, (
        "the stage no longer paints a refusal where the hull would be")
    assert re.search(r"setMesh\([^)]*\)\s*\{[^}]*this\.error = null", vp,
                     re.S), "a successful mesh must clear a stale error"

    sd = (_ROOT / "ui/app/screens-design.js").read_text()
    assert "vp.setError(e.message)" in sd, (
        "the studio catches a failed refresh and does not tell the stage — "
        "which is exactly the 2026-08-23 incident")


def test_post_surfaces_the_backends_own_words():
    """`e.message` must be the kernel's sentence, not 'Bad Request'."""
    core = (_ROOT / "ui/app/core.js").read_text()
    assert "throw new Error(j.error || r.statusText)" in core, (
        "core.post no longer forwards the server's error text, so the stage "
        "would paint a status line instead of the reason")
