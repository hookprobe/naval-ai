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


# ---------------------------------------------------------------- the ladder

def test_the_ladder_searches_BOTH_directions_and_reaches_the_counts_hulls_need():
    """THE OLD LADDER COULD NOT REACH THE ANSWER, measured on the 25-hull
    seed-0 matrix. It started at n_derived - step and only descended, so from
    rung 0 = _MAX_LAYERS = 7 with step 2 the reachable set was {5, 3}. But:

        hull 10 meshes ONLY at n=8      hull 12 meshes ONLY at n=6
        hull 18 meshes CLEAN at n=10 (skew 6.19) and FAILS at 7 (skew 70.98)

    None of those is in {5, 3}. The step of 2 also skipped every even count
    from an odd start, so hull 12's 6 was unreachable even below rung 0.

    Fed the verbatim counts that motivated it.
    """
    from navalai.cfd.case import layer_backoff_ladder
    rungs = layer_backoff_ladder(7, ceiling=10)
    for hull, need in ((10, 8), (12, 6), (18, 10)):
        assert need in rungs, (
            f"hull {hull} meshes only at n={need}; the ladder from 7 offers "
            f"{rungs} and cannot reach it")
    assert 3 in rungs, "the floor must still be reachable"


def test_the_ladder_is_ordered_outward_so_the_nearest_rung_is_tried_first():
    """The derived count is still the best single guess -- it is right on 19 of
    25 hulls -- so a hull that needs a rung usually needs a NEAR one. Ordering
    outward keeps the measured mean at ~1.9 rungs per hull; ordering by
    magnitude would pay the full ladder on every rescue."""
    from navalai.cfd.case import layer_backoff_ladder
    rungs = layer_backoff_ladder(7, ceiling=10)
    assert [abs(n - 7) for n in rungs] == sorted(abs(n - 7) for n in rungs), (
        f"rungs {rungs} are not ordered by distance from the derived count")


def test_the_search_never_leaves_the_measured_envelope():
    """Below `floor` the stack is empty (cap 3 gave 0.31-2.85 achieved layers,
    passing checkMesh with no boundary layer). Above `ceiling` the near-wall
    cell cannot support the stack. Both ends are bounds, not preferences."""
    from navalai.cfd.case import layer_backoff_ladder, _LAYER_FLOOR
    for n0, ceil in ((7, 10), (10, 10), (4, 8), (3, 3)):
        for n in layer_backoff_ladder(n0, ceiling=ceil):
            assert _LAYER_FLOOR <= n <= ceil, f"rung {n} outside [{_LAYER_FLOOR}, {ceil}]"
            assert n != n0, "rung 0 must not repeat inside the ladder"


def test_the_case_records_the_ladder_the_runner_will_walk(tmp_path):
    """MEASURED 2026-08-18 (the case-a metal check): the derived n=6 gave 16
    wrongly-oriented faces (bar 5) and n=5 gave 0 -- and the recovery ladder
    existed only in scripts/mesh_robustness.py, so the canonical lane's only
    move was a FATAL telling the operator to re-generate by hand.

    The generator now writes the measured outward ladder into case.info;
    run-case.sh walks THAT, so shell never re-derives (and never disagrees
    with) the Python truth. This test pins both halves of the contract:
    the receipt exists and equals `layer_backoff_ladder(n_layers, ceiling=
    n_ideal)`, and the runner parses the same key.
    """
    from navalai.evaluate import sample_valid
    from navalai.geometry import Hull
    from navalai.mission import MissionSpec

    X, _ = sample_valid(1, MissionSpec(), seed=0)
    case = tmp_path / "ladder-receipt"
    C.write_resistance_case(Hull(X[0]), 2.57, case,
                            allow_dangerous_mesh=True)
    info = dict(
        line.split("=", 1)
        for line in (case / "case.info").read_text().splitlines()
        if "=" in line and not line.lstrip().startswith("#"))
    n = int(info["n_layers"])
    n_ideal = int(info["n_layers_to_fully_bridge"])
    want = C.layer_backoff_ladder(n, ceiling=n_ideal)
    got = ([] if info["layer_backoff_ladder"] == "none"
           else [int(s) for s in info["layer_backoff_ladder"].split(",")])
    assert got == want, (
        f"case.info records ladder {got} while layer_backoff_ladder({n}, "
        f"ceiling={n_ideal}) says {want} -- the runner would walk stale rungs")

    runner = (_ROOT / "navalai" / "cfd" / "run-case.sh").read_text()
    for marker, why in [
        ("layer_backoff_ladder=", "the runner no longer reads the receipt"),
        ("polyMesh.prelayer", "no pre-layer snapshot: a retry would redo "
         "castellate/snap or relayer a layered mesh"),
        ('LAYER_BACKOFF:-3', "the attempt cap (and the harness's =0 off "
         "switch) is gone"),
        ("layer_backoff_attempt_", "failed attempts leave no receipt"),
        ("n_layers_meshed", "after a backoff, nothing records the count the "
         "final mesh actually carries"),
    ]:
        assert marker in runner, f"run-case.sh: {why} (marker {marker!r})"
