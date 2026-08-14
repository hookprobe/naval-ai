"""THE reference hull — one set of sixteen numbers, one home (R1.5).

The 10 m Solar-Liveaboard reference genome existed as THREE transcribed
copies (`tests/test_phase0.mid_params`, `arrangement.reference_hull_params`,
`tests/test_geometry_kernel.MID` — audit 2026-08-14, duplication register),
~60 tests hanging off one of them. A reference vector that exists three
times is three chances for a "reference" measurement to describe a boat the
other two files no longer build. All three now import from here.

Provenance of the numbers (kept verbatim from the P1/P2 migration): plate
P1/P2 genome; `p_bow`/`p_stern` are gone (plan-form is a consequence of the
area curve, not an input); `Cp`, `lcb`, `roundness` are genes. Two numbers
MOVED with the kernel, and both are information about the old reference
hull rather than a loosened bar:

  forefoot 0.85 -> 0.60. At 0.85 the keel rises to 0.225 m of draft at
  x/L = 0.95, where the warped deadrise is 24.2 deg, and a section of that
  draft and deadrise cannot enclose the 0.2000 m^2 the area curve asks for
  (`section.solve`). The old kernel had no area curve to be wrong against.

  r_transom 0.75 -> 0.30. The symbol changed meaning: it was the transom
  half-BEAM ratio and is now the transom sectional AREA ratio, and 0.75 of
  the midship area at the transom forces Cp above what the SAC family can
  reach with the rest of the hull.

`panel_twist_rate` still reads 11.22 deg/m on this hull, the number its own
convergence table in geometry.py is quoted at.
"""

from __future__ import annotations

import numpy as np

from . import grammar

# The sixteen numbers, as a dict so callers can `dict(REFERENCE_HULL,
# forefoot=...)` a variant without positional guesswork.
REFERENCE_HULL: dict[str, float] = {
    "LWL": 10.0, "BWL": 3.2, "T": 0.55, "D": 1.55,
    "Cp": 0.60, "lcb": -1.0, "x_mb": 0.55, "r_transom": 0.30,
    "beta_mid": 8.0, "beta_bow": 30.0, "beta_len": 0.35,
    "roundness": 0.0, "rocker": 0.15, "forefoot": 0.60,
    "flare": 10.0, "sheer_rise": 0.18,
}


def reference_params() -> np.ndarray:
    """The reference genome as the grammar's parameter vector."""
    return grammar.vector(REFERENCE_HULL)
