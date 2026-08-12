"""Gate 2L — the prism-layer cap is a MEASURED value, not a preference.

MOTIVATING INCIDENT (2026-08-11, Gate 2U coarse campaign). `_MAX_LAYERS` was
3, then 10, and the 10 shipped for weeks. At 10 the generator requested 8-10
layers on every grammar hull and snappy achieved 3.9-8.1 — not one hull hit
its request. Measured over 20 paired hulls at seed 0, mesh-only, one variable
changed: 7 of 20 clean at the derived count against 14 of 20 at the cap of 7,
by the bars `run-case.sh` actually enforces (0 zero-volume, <=5 wrongly-
oriented, skew <=20). Paired McNemar 8 improved / 1 regressed, p = 0.039.

WHY THIS FILE EXISTS AT ALL. The 10 -> 7 change shipped with NO test —
`grep -rn "_MAX_LAYERS" tests/` returned nothing — so the next session could
have moved it back on an argument, which is exactly how it reached 10 in the
first place: the KCS measurement that justified 3 was correctly retired when
the 38:1 background was rebuilt, and the REPLACEMENT measurement was never
taken. A superseded number is not a licence to guess the new one.
"""
from __future__ import annotations

import json
import pathlib

import navalai.cfd.case as C

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_the_cap_is_the_measured_value_and_moving_it_needs_a_new_measurement():
    assert C._MAX_LAYERS == 7, (
        "_MAX_LAYERS moved. It is 7 because 7 is the largest count MEASURED "
        "clean on this mesh family (data/gate2u-cap7-mesh.json, 25 hulls). "
        "Re-measure before changing it; do not argue it.")


def test_the_cap_binds_rather_than_decorating():
    """A cap the derivation never reaches is not a cap. MEASURED: every one of
    the 25 seed-0 hulls derived a request ABOVE 7, so the cap binds on all of
    them. If the derivation ever falls below it the guard is inert and this
    test says so out loud rather than passing quietly."""
    rows = json.loads((_ROOT / "data" / "gate2u-cap7-mesh.json").read_text())
    rows = rows if isinstance(rows, list) else rows.get("rows", [])
    assert rows, "cap-7 arm missing — the measurement behind the cap is gone"
    req = [r.get("layers_requested") for r in rows if r.get("layers_requested")]
    assert req and all(n == C._MAX_LAYERS for n in req), (
        f"expected every hull to request the cap, got {sorted(set(req))}")


def test_a_clean_mesh_with_no_boundary_layer_is_not_a_pass():
    """THE TRAP, fed the verbatim data that motivated it. At cap 3, 14 of 15
    'clean' hulls achieved 0.31-2.85 layers: a mesh with no prism stack cannot
    FOLD a prism stack, so it sails through checkMesh while destroying the wall
    treatment those bars exist to protect. Optimising the checkMesh number
    alone would have selected cap 3 and produced clean, worthless meshes —
    honesty rule 6 wearing a disguise.

    At cap 7 no clean hull sits below the floor, and this asserts it.
    """
    rows = json.loads((_ROOT / "data" / "gate2u-cap7-mesh.json").read_text())
    rows = rows if isinstance(rows, list) else rows.get("rows", [])
    empty = [r.get("hull") for r in rows
             if r.get("meshed")
             and (r.get("wrong_oriented") or 0) <= 5
             and (r.get("zero_volume_cells") or 0) == 0
             and (r.get("layers_achieved") or 0) < 3.0]
    assert not empty, (
        f"hulls {empty} pass the checkMesh bars on an EMPTY prism stack — "
        f"clean because there is no boundary layer to fold. That is the cap-3 "
        f"failure mode and it must never be counted as a pass.")
