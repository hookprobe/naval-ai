"""Stage F gate: panels unroll isometrically with an honest development-error
metric; DXF round-trips; Pareto endpoint serves clickable designs; agent
handoff overhead measured (the anti-Zig receipt)."""

import json
import time

import numpy as np
import pytest

from navalai.geometry import Hull
from navalai.mission import MissionSpec, parse_mission
from navalai.unroll import develop, export_dxf, hull_panels, parse_dxf_polylines
from tests.test_phase0 import mid_params


# ---------------- unrolling ----------------

def test_cylinder_develops_exactly():
    """A cylindrical surface is perfectly developable: error must be ~0 and
    the flat width must equal the arc length.

    THE FIXTURE USED TO BE A CONOID, NOT A CYLINDER (gap G5). It ran chords
    from a straight axis to a quarter circle, so the ruling DIRECTION rotated
    along the strip — twist median 0.383, i.e. not developable — and the bar
    was 5e-3, which the hyperbolic paraboloid also clears (6.5e-4 at n=41).
    A cylinder has PARALLEL rulings, and then the development is exact to
    machine precision, which is a bar a conoid cannot pass. See
    tests/test_manufacturing.py for the negative control the pair needs."""
    n = 40
    theta = np.linspace(0, np.pi / 2, n)
    r = 2.0
    A = np.stack([np.zeros(n), r * np.sin(theta), r * (1 - np.cos(theta))],
                 axis=1)
    B = A + np.array([5.0, 0.0, 0.0])
    panel = develop(A, B, "cyl")
    assert panel.dev_error_rel < 1e-12
    assert panel.twist_max < 1e-12
    widths3 = np.linalg.norm(B - A, axis=1)
    widths2 = np.linalg.norm(panel.edge_b - panel.edge_a, axis=1)
    assert np.allclose(widths2, widths3, rtol=1e-9)   # ruling lengths preserved


def test_hull_panels_develop_within_tolerance():
    panels = hull_panels(Hull(mid_params()))
    assert {p.name for p in panels} == {"bottom-stbd", "topside-stbd"}
    for p in panels:
        # ISOMETRY residual only. This is NOT a developability verdict: it is
        # O(h^2) for any smooth surface, so refining the polyline drives it to
        # zero for a hypar as readily as for a cylinder. The verdict lives in
        # `twist_max`/`twist_median`, and on the topside panel it is bad —
        # tests/test_manufacturing.py::test_hull_panel_twist_is_recorded_not_blessed
        assert p.dev_error_rel < 0.05, f"{p.name}: {p.dev_error_rel:.3f}"


def test_edge_lengths_preserved_3d_to_2d():
    h = Hull(mid_params())
    keel = np.stack([h.x, np.zeros_like(h.x), h.z_keel], axis=1)
    chine = np.stack([h.x, h.y_chine, h.z_chine], axis=1)
    p = develop(keel, chine, "bottom")
    for E3, E2 in ((keel, p.edge_a), (chine, p.edge_b)):
        l3 = np.linalg.norm(np.diff(E3, axis=0), axis=1).sum()
        l2 = np.linalg.norm(np.diff(E2, axis=0), axis=1).sum()
        assert l2 == pytest.approx(l3, rel=1e-6)      # isometric edges


def test_dxf_roundtrip(tmp_path):
    """Every placed part survives the write/read, vertex for vertex.

    THE FILE IS NOW A NEST, NOT A STACK (gap G2). It used to draw the two whole
    panels offset in y — 10.05 x 1.62 m and 10.54 x 1.44 m against a
    1.22 x 2.44 m sheet, so `set(back) == {"bottom-stbd", "topside-stbd"}` was
    asserting that the file contained two parts no shop could cut. The
    round-trip is now over the split, rotated, placed pieces."""
    from navalai.unroll import nest, split_panel

    parts = []
    for p in hull_panels(Hull(mid_params())):
        parts += split_panel(p, 0.015)
    layout = nest(parts)
    path = export_dxf(layout, tmp_path / "panels.dxf")
    back = parse_dxf_polylines(path)

    assert {"bottom-stbd", "topside-stbd"} & set(back) == set()   # never whole
    for pl in layout.placements:
        pts = back[pl.part]
        assert len(pts) == len(pl.polygon)
        # Extents survive the write/read, IN THE UNITS THE FILE DECLARES.
        # The writer now emits millimetres and says so via $INSUNITS 4. It
        # previously wrote metres with NO header at all, so a shop importing
        # the file cut a 10 mm part instead of a 10 m one. Comparing the
        # round-trip against the metre-valued outline is what let that pass.
        assert np.ptp(pts[:, 0]) == pytest.approx(
            1000.0 * np.ptp(pl.polygon[:, 0]), abs=1.0)
        assert np.ptp(pts[:, 1]) == pytest.approx(
            1000.0 * np.ptp(pl.polygon[:, 1]), abs=1.0)
    # ...and the declared unit must be present, or "millimetres" is a habit
    # rather than a statement the importer can read.
    head = path.read_text()
    assert "$INSUNITS" in head and "\n4\n" in head.split("$INSUNITS")[1][:20]


# ---------------- Pareto dashboard ----------------

def test_pareto_endpoint_serves_designs():
    """THE COUNT WAS A DRAW, NOT A BAR — and what replaced it asks more.

    MEASURED, CI run 31611386179 on ubuntu-latest: `assert (2 >= 3)`. This Mac
    serves 24 points from the same commit, the same mission and the SAME
    SEED — `ui/server.py` calls `pareto_front(mission, pop=48, gens=15,
    seed=2)` (raised 2026-08-14 with the mission-chosen Cp box, R1.1), and pymoo 0.6.2 derives a local PCG64 from that seed, so the RNG
    is pinned and thread counts provably change nothing. What is not pinned is
    the trajectory: NSGA-II ranks each generation by DOMINATION, a discrete
    decision on continuous inputs, so a last-bit arithmetic difference sends
    ten generations somewhere else. Swept over 100 seeds on this machine the
    front spans **0 to 24 members**, and is under 3 on 2% of them.

    So `>= 3` described one draw on one platform. `ui/server.py`'s own comment
    calls 24/10 a "BUDGET, not bar"; this test had turned that budget's
    observed output into a bar.

    The count is replaced by the properties the ENDPOINT actually owes, two of
    which were not being asked at all:

      - it serves designs (>= 1) with the declared payload shape,
      - every served design RE-VALIDATES on the ladder for the mission it was
        served for (honesty rule 2), and
      - the served `gm_m` is the LADDER's GM. `ui/server.py` records that this
        field was once `-f[2]`, minus a distance, and reported gm_m = -0.047
        for a hull whose GM is +0.514 m. Nothing here checked it.

    WHAT IS NOT REPLACED, and is owed in `ui/server.py` rather than here: at
    some seeds `pareto_front` returns ZERO members and `get_pareto` caches and
    serves `{"points": []}` without refusing or flagging it — a dashboard
    drawing nothing, or one point instead of a trade-off, which is the very
    failure the pop=16/gens=6 -> 24/10 budget change was made to fix. A test
    cannot assert a floor the search does not guarantee; the endpoint has to
    declare a degenerate front. That file is not this change's to edit.
    """
    import numpy as np

    from navalai import grammar
    from navalai.evaluate import evaluate
    from ui.server import _mission_default, get_pareto

    d = get_pareto()
    assert d["tier"] == "L1"
    assert len(d["points"]) >= 1, "the endpoint served no designs at all"
    for p in d["points"]:
        assert set(p) == {"params", "wh_per_nm", "build_area_m2", "gm_m"}
        # NOT A LITERAL. 15 until the plate-P1/P2 genome, and a served payload
        # that is short by a gene is a payload the ladder cannot re-evaluate —
        # which is what the next two lines do. `grammar.N_PARAMS` is the one
        # home of the count; a second copy here is what made this test fail
        # for a reason unconnected to the endpoint.
        assert len(p["params"]) == grammar.N_PARAMS
        x = np.array([p["params"][n] for n in grammar.NAMES], float)
        ev = evaluate(x, _mission_default)
        assert ev.ok, f"a served design fails the ladder: {ev.violations}"
        assert p["gm_m"] == pytest.approx(round(float(ev.gm_m), 3)), (
            f"served gm_m {p['gm_m']} is not the ladder's {ev.gm_m} — this "
            f"field was once minus an objective distance and read -0.047 m "
            f"for a hull at +0.514 m")
    # cached: second call is instant
    t0 = time.perf_counter()
    get_pareto()
    assert time.perf_counter() - t0 < 0.01


def test_dashboard_html_has_pareto_ui():
    html = open("ui/index.html").read()
    assert 'id="pareto"' in html and "/pareto" in html


def _panel_default_mission_text() -> str:
    """The brief the SHIPPED page opens with, read out of the page itself.

    Retyping it here would make the test pass while the page drifted — the
    number-declared-twice defect wearing a string."""
    html = open("ui/index.html").read()
    return html.split('id="mission" rows="2">')[1].split("</textarea>")[0]


def test_pareto_serves_the_mission_it_was_asked_about():
    """`/pareto` WAS THE LAST ENDPOINT ANSWERING THE DEFAULT MISSION'S QUESTION.

    `get_pareto(mission)` and its per-mission cache landed on 2026-08-11, but
    the HTTP surface did not: `do_GET` served `/pareto` with no mission and
    there was no POST route, so no caller could reach a second cache entry. The
    dashboard drew one boat's trade-off surface beside sliders evaluating
    another. Gap I9's shape ("it was a SINGLE pool, which is why `/generate`
    could only ever answer the default mission"), one endpoint later.

    THE VERBATIM BROKEN CASE IS THE PAGE'S OWN OPENING BRIEF — no exotic input
    was needed. `MissionSpec()` has `lwl_hint_m=None` while the textarea's
    "6 tonne ... 10 m ... 5 knots" parses to 10.0 m, so a user who pressed
    "Apply mission" without editing a character already had sliders on one
    mission and a front on another.

    MEASURED 2026-08-11 on this Mac, at HEAD 140f7e4 WITH `navalai/evaluate.py`
    being edited concurrently by another agent — which is why the counts below
    are dated and the assertions are not written against them:

        the panel's opening brief    24 members, Wh/NM  376.6 - 2093.0
        "3 tonne dayboat ... 9 kn"   13 members, Wh/NM 2175.1 - 4080.7

    Two runs an hour apart returned 16/12 and then 24/24 members for the same
    two missions, because the constraint set moved underneath them. A test that
    asserted the counts would have been measuring the other agent's work; what
    is asserted is the STRUCTURAL claim — different missions, different fronts,
    and no cross-serving — which is what the fix is about.

    Defect class 3: a guard fed the input it must reject. Under the old code the
    two fronts are the SAME LIST, and `POST /pareto` is a 404.
    """
    import ui.server as S

    panel = json.loads(parse_mission(_panel_default_mission_text()).to_json())
    other = json.loads(parse_mission(
        "3 tonne dayboat, 8 m, coastal, cruise 9 knots, 2 crew").to_json())
    assert panel["lwl_hint_m"] == 10.0 and other["cruise_speed_kn"] == 9.0
    # the page's own opening brief was never the server's default mission
    assert S.mission_key(S._mission_from(panel)) != \
           S.mission_key(MissionSpec())

    a = S.pareto_payload(panel)
    b = S.pareto_payload(other)

    # THE DIAGNOSTIC WAS MISLEADING AND THE FAILURE IS REAL (2026-08-20).
    # This assertion read `a["points"] != b["points"]` with the message
    # "two different missions returned the same front", and it fired as
    # `assert [] != []` — BOTH fronts empty. The wiring it was written to
    # police is fine; what is broken is that the search returns NOTHING at
    # the budget the server actually uses.
    #
    # MEASURED on the panel's own default brief, seed 0:
    #     pop=24 gens=10   240 evals   0 members   2.44 s  <- SERVER'S BUDGET
    #     pop=24 gens=20   480 evals   1 member    5.41 s
    #     pop=40 gens=20   800 evals   0 members   9.35 s
    #     pop=48 gens=25  1200 evals  48 members  14.69 s
    #     pop=60 gens=25  1500 evals  16 members  17.75 s
    # The mission is FEASIBLE — 1200 evals finds 48 members — so this is a
    # convergence/budget defect, not an infeasible brief. Note 800 -> 0
    # against 480 -> 1: non-monotone, so feasibility is marginal and the
    # search is unreliable in this regime, not merely slow.
    #
    # It cannot be bought with a bigger budget: 1200 evals is 14.69 s
    # against Gate 4's 100 ms interactive bar, 147x over. The fix is a warm
    # start or a repair operator, which is optimiser work and is NOT done
    # here — this test is left FAILING on purpose, because a dashboard that
    # draws an empty trade-off surface for its own opening brief is a
    # product defect and softening its guard would hide it.
    assert a["points"], (
        "the PANEL'S OWN DEFAULT MISSION returned an EMPTY Pareto front at "
        "the server's live budget (pop=24/gens=10, 240 evaluations). The "
        "mission is feasible — 1200 evaluations finds 48 members — so the "
        "search is not converging, it is not that no boat exists. A user "
        "pressing 'Apply mission' without editing a character gets a blank "
        "trade-off surface.")
    assert b["points"], "the second mission returned an EMPTY front"
    assert a["points"] != b["points"], (
        "two different missions returned the same front — the mission is not "
        "reaching the search")
    assert [p["wh_per_nm"] for p in a["points"]] != \
           [p["wh_per_nm"] for p in b["points"]]
    assert a["mission"]["cruise_speed_kn"] == 5.0
    assert b["mission"]["cruise_speed_kn"] == 9.0
    assert b["mission"]["displacement_target_kg"] == 3000.0

    # ...and one mission's cached answer is never served for another. This is
    # the half that a single global `_pareto_cache` got wrong even when the
    # search was right: the FIRST caller's front was served to every later one.
    again = S.pareto_payload(panel)
    assert again["points"] == a["points"] and again["live"] is False
    assert again["points"] != b["points"]
    # ...including the server's OWN default, which is the front the GET-only
    # endpoint handed to every caller regardless of what they had typed.
    assert S.get_pareto(MissionSpec())["points"] != b["points"], (
        "the server's own default front is being served for a typed mission")


def test_pareto_declares_the_cold_search_instead_of_hiding_it():
    """GATE 4'S BAR IS 100 ms AND A NEW MISSION MISSES IT. Not softened.

    MEASURED 2026-08-11 over seven briefs on this Mac: cold 1.88-2.30 s
    (NSGA-II at pop=24/gens=10), warm 0.023-0.032 ms — a 19-23x miss. The
    payload declares `live` and `elapsed_ms`, the same two keys `/generate`
    uses, so the miss is visible in the answer rather than averaged away by the
    cached calls around it.

    The receipt is checked against the CALLER'S OWN wall clock. An
    `elapsed_ms` nobody compares to a real duration is decoration, and this
    repo's most expensive defect class is a metric that is not actually
    measured (LESSONS class 1)."""
    import ui.server as S

    mis = json.loads(parse_mission(
        "9 tonne canal barge, 15 m, river, cruise 4 knots, 3 crew").to_json())
    t0 = time.perf_counter()
    cold = S.pareto_payload(mis)
    wall_ms = (time.perf_counter() - t0) * 1e3
    assert cold["live"] is True
    assert cold["elapsed_ms"] == pytest.approx(wall_ms, rel=0.25)
    assert cold["elapsed_ms"] > 100.0, (
        "a live NSGA-II search came in under Gate 4's bar — re-measure the "
        "budget before believing it")

    t0 = time.perf_counter()
    warm = S.pareto_payload(mis)
    assert (time.perf_counter() - t0) * 1e3 < 100.0      # Gate 4, cached path
    assert warm["live"] is False and warm["points"] == cold["points"]

    # the cache is BOUNDED — it is keyed on user input now that POST reaches it
    for kn in range(1, 4 + S.MAX_POOLS):
        S.pareto_payload({"cruise_speed_kn": float(kn)})
    assert len(S._pareto_cache) <= S.MAX_POOLS


def test_pareto_over_http_takes_a_mission():
    """The wire, not the function. `get_pareto` already took a mission; what
    was missing was any way for the dashboard to pass one — GET carries no
    body and there was no POST route, so this request used to 404.

    THE FRONT SIZE IS NO LONGER ASSERTED HERE. CI run 31611386179 failed this
    test on `len(default["points"]) >= 3` — a clause incidental to the wire,
    duplicating one `test_pareto_endpoint_serves_designs` already owns, and
    measured over 100 seeds to span 0 to 24 members (see that test for the
    mechanism and why a count is not a bar). Two copies of a bar is this
    repo's number-declared-twice defect wearing a count; the wire claims below
    — the typed mission's speed round-trips, the typed front differs from the
    default, the payload keys — are structural and platform-independent, and
    they are what this test exists for."""
    from http.server import ThreadingHTTPServer
    import threading
    import urllib.request

    from ui.server import Handler

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        # 600 s: a cold /pareto is a full NSGA-II run, and the budget rose
        # to pop=48/gens=15 with the mission-chosen Cp box (R1.1) — MEASURED
        # ~2 min cold on the slow audit box under concurrent suite load. The
        # timeout is a hang guard, not a latency bar; the latency claim
        # lives in the payload's own declared cost.
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/pareto",
                                    timeout=600) as r:
            default = json.loads(r.read())          # GET still works
        body = json.dumps({"mission": json.loads(parse_mission(
            "3 tonne dayboat, 8 m, coastal, cruise 9 knots, 2 crew").to_json())
        }).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/pareto",
                                     data=body)
        with urllib.request.urlopen(req, timeout=600) as r:
            typed = json.loads(r.read())
    finally:
        srv.shutdown()

    assert default["tier"] == "L1"
    assert typed["mission"]["cruise_speed_kn"] == 9.0
    assert typed["points"] != default["points"], (
        "POST /pareto returned the default mission's front")
    for d in (default, typed):
        assert set(d) >= {"points", "n_evals", "tier", "mission", "live",
                          "elapsed_ms"}


def test_dashboard_sends_its_mission_to_pareto():
    """The page held a mission all along (`/eval` and `/generate` both send it)
    and the Pareto button was the one fetch that did not, so the dashboard
    could only ever draw the server's default. Checked in the page source
    because there is no browser in this suite to click the button."""
    html = open("ui/index.html").read()
    call = html.split('getElementById("loadPareto")')[1].split("\n});")[0]
    assert 'fetch("/pareto"' in call and 'method: "POST"' in call
    assert "mission" in call.split('fetch("/pareto"')[1][:200]
    # and the cold cost is shown, not swallowed
    assert "d.live" in call and "elapsed_ms" in call


# ---------------- handoff-latency receipt ----------------

def test_agent_handoff_overhead_is_noise():
    """Original plan Phase 5 wanted Zig to cut agent-handoff latency. Measure
    it instead: queue round-trip must be <1% of one L1 physics evaluation."""
    import asyncio

    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec

    async def roundtrip(n=200):
        q = asyncio.Queue()
        t0 = time.perf_counter()
        for _ in range(n):
            await q.put(1)
            await q.get()
        return (time.perf_counter() - t0) / n

    handoff = asyncio.run(roundtrip())
    evaluate(mid_params(), MissionSpec())   # warm
    t0 = time.perf_counter()
    evaluate(mid_params(), MissionSpec())
    physics = time.perf_counter() - t0
    ratio = handoff / physics
    assert ratio < 0.01, f"handoff {handoff*1e6:.1f} us vs physics {physics*1e3:.1f} ms"


def test_a_wire_mission_energy_dict_reaches_the_evaluation_C12():
    """C-12: `_mission_from` DROPPED the `energy` key (a nested dict the
    spec could not hold), so a wire mission's battery_kwh silently never
    reached the evaluation — the served numbers were computed under the
    DEFAULT energy spec while the payload named the caller's mission.
    MissionSpec.__post_init__ now rehydrates energy dicts exactly as it
    does vessel and payload, and the wire decoder passes the key through.
    """
    import ui.server as S

    base = {"displacement_target_kg": 4000.0}
    with_batt = {"displacement_target_kg": 4000.0,
                 "energy": {"battery_kwh": 60.0}}
    m0 = S._mission_from(base)
    m1 = S._mission_from(with_batt)
    from navalai.energy import EnergySpec
    assert isinstance(m1.energy, EnergySpec), (
        "the energy dict must rehydrate at the MissionSpec boundary")
    assert m1.energy.battery_kwh == pytest.approx(60.0)
    assert m0.energy.battery_kwh != m1.energy.battery_kwh, (
        "the wire energy no longer moves the spec — C-12 regressed")
    # and the condition separates the answers a caller is served under
    assert S.mission_key(m0) != S.mission_key(m1), (
        "two missions differing only in energy share a cache key — the "
        "served numbers would be conditioned on the wrong spec")
