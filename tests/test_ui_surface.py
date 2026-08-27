"""The builder-facing surface: the contracts it must not quietly break.

`ui/index.html` (the engineer's sixteen-slider page) is pinned by
`tests/test_stageF.py` and `tests/test_phase4.py`. NOTHING pinned the mapping
layer that `docs/BUILD-PLAN.md` §PU asks for, and every rule it has to keep is
a rule this project already learned the hard way somewhere else. This module is
that fence.

Each test names the MEASURED incident that motivated it, in the house style,
because a bar with no incident behind it is a bar nobody can argue with later.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from navalai import grammar, limits
from navalai.evaluate import CONSTRAINT_NAMES

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "ui" / "app"


def _params(**over):
    p = grammar.named((grammar.LOW + grammar.HIGH) / 2)
    p["roundness"] = 0.0            # the compiled box pins this; so does the UI
    # post-hoc genes at their NO-OPS, not their mids (2026-08-27, the
    # tunnel arity event): mid-dwl + mid-tunnel is an active-everything
    # hull the UI never serves, and its transom refuses at L0
    for _nm, _v in grammar.POST_HOC_DEFAULTS.items():
        p[_nm] = float(_v)
    p.update(over)
    return p


# ---------------------------------------------------------------------------
# 1 · EVERY PAYLOAD DECLARES ITS OWN SOURCE
# ---------------------------------------------------------------------------

def test_every_api_payload_declares_a_source():
    """A SCREEN CANNOT DECIDE WHETHER ITS DATA IS REAL; THE PAYLOAD MUST SAY.

    The defect class is `docs/BUILDER-UX.html` §00's: a component that decides
    confidence for itself renders a typed sigma as L1 green. MEASURED before
    that rule existed, four sigmas in `ui/server.py` were literal fractions of
    their own value (`freeboard` 0.02, `cb` 0.02, solar x0.25, range_solar
    x0.35) and every one of them rendered as a confident band.

    So the wire contract is: `source` is one of `measured`, `absent`,
    `refused`, `mock` — and the front end renders the declaration rather than
    a default. A payload with no `source` would render as whatever the screen
    assumed, which is the thing this whole surface exists not to do.
    """
    import ui.api as api

    allowed = {"measured", "absent", "refused", "mock"}
    seen = 0
    for path, fn in api._GET.items():
        out = fn()
        assert isinstance(out, dict), path
        assert out.get("source") in allowed, f"{path} -> {out.get('source')!r}"
        seen += 1
    for path, fn in api._POST.items():
        if path.startswith("/api/search/"):
            continue                    # covered by its own test below
        out = fn({"params": _params()})
        assert isinstance(out, dict), path
        assert out.get("source") in allowed, f"{path} -> {out.get('source')!r}"
        seen += 1
    assert seen >= 10, f"only {seen} routes exercised — did the table shrink?"


def test_no_payload_ships_a_nan():
    """NaN IS NOT VALID JSON (RFC 8259) AND IT WAS ONCE EMITTED RAW.

    `ui/server._q` already refuses a non-finite value as
    `{"value": null, "state": "non-finite — refused"}`. The mapping layer has
    its own float paths — `Evaluation.non_developable_frac` is NaN *by design*
    when the meter could not run, precisely so it cannot be read as "0% non-
    developable" — and `float(nan)` would put a bare `NaN` token on the wire
    that `JSON.parse` rejects, taking the whole screen down.
    """
    import ui.api as api

    def walk(o, where):
        if isinstance(o, float):
            assert math.isfinite(o), f"non-finite at {where}"
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{where}.{k}")
        elif isinstance(o, (list, tuple)):
            for i, v in enumerate(o):
                walk(v, f"{where}[{i}]")

    for name, out in [("twin", api.twin_payload({"params": _params()})),
                      ("envelope", api.envelope_payload({})),
                      ("refold", api.refold_payload(
                          {"params": _params(), "counts": (41, 81)}))]:
        walk(out, name)
        json.dumps(out)                 # the real bar: it must serialise


# ---------------------------------------------------------------------------
# 2 · THE ABSENCE REGISTRY IS DECLARED ONCE
# ---------------------------------------------------------------------------

def test_an_absence_is_declared_in_exactly_one_place():
    """A NUMBER LIVES IN ONE PLACE. SO DOES A HOLE.

    A hatched tile whose reason is typed into the markup is this project's
    signature defect wearing a `<div>`: the day the backend grows a stem-rake
    gene, the tile goes on saying it has not. So `ui/api.ABSENT` is the one
    home, it is SERVED, and no front-end file may contain the prose.
    """
    import ui.api as api

    files = [p.read_text() for p in APP.glob("*.js")] + \
            [(APP / "index.html").read_text()]
    for key, a in api.ABSENT.items():
        # a distinctive fragment of the reason, long enough not to collide
        needle = a["why"][:48]
        for src in files:
            assert needle not in src, (
                f"absence {key!r} is restated in the front end — it must be "
                f"read from /api/manifest, not typed into the UI")
    assert "stem_rake" in api.ABSENT and "air_draft" in api.ABSENT
    assert "motion_in_chop" in api.ABSENT


def test_the_manifest_carries_the_absences_and_the_real_bars():
    import ui.api as api

    m = api.manifest_payload()
    assert m["absent"] == api.ABSENT
    assert m["froude_ceiling"] == 0.45
    # THE BAR IS READ FROM `limits`, NOT TYPED. `limits.REFOLD_BAR_MM` is the
    # single source; a 5.0 written into a payload is the second copy that
    # `tests/test_limits_single_source.py` exists to prevent.
    assert m["refold_bar_mm"] == limits.REFOLD_BAR_MM


# ---------------------------------------------------------------------------
# 3 · EXACTLY EIGHT ROWS. NOT NINE.
# ---------------------------------------------------------------------------

def test_the_surface_never_invents_an_eleventh_constraint_row():
    """`Evaluation.g` has exactly TEN rows and that is the complete set of
    things this platform can fail a design on. A UI that draws an eleventh
    light is claiming an enforcement that does not exist — and a policy may
    only APPEND a row, never rewrite one, so the appended names are the
    constitution's and are named as such.

    EIGHT -> TEN, 2026-08-25, and the change is the OWNER'S, not drift: "all
    boats will have motors, electric motors and solar panels ... naval-ai
    only designs boats with motors" (stated twice). `motor_power` and
    `prop_space` joined `CONSTRAINT_NAMES` because houseboat19 passed all
    eight rows and was still, by inspection, "ok for a paddle boat not for a
    motor boat" — the stern offered a 0.26 m disc to a thrust wanting
    0.42 m and nothing here could say so. This fence still does its job: it
    pins the EXACT set, so the next row must arrive the way these did — as a
    deliberate product decision recorded in the row's own module — or not at
    all."""
    import ui.api as api

    m = api.manifest_payload()
    assert tuple(m["constraints"]) == CONSTRAINT_NAMES
    # TEN -> ELEVEN, 2026-08-26, the way this fence demands rows arrive: a
    # deliberate product decision recorded in the row's own module. `shape`
    # is `morphology.shape_margin` — the plausibility critic as a
    # continuous margin — appended after the audit measured that the critic
    # had ZERO production callers while 89-92% of L0-valid hulls were
    # morphologically implausible and the 2026-08-23 plank passed every
    # row this surface could draw.
    assert len(m["constraints"]) == 11
    assert CONSTRAINT_NAMES[8:] == ("motor_power", "prop_space", "shape")

    twin = api.twin_payload({"params": _params()})
    for r in CONSTRAINT_NAMES:
        assert r in twin["constraints"]["g"], r
    # the convention is stated on the wire, because "-2.0" means SAFE here and
    # a reader who assumes the other sign gets every light backwards
    assert "<= 0" in twin["constraints"]["convention"]


# ---------------------------------------------------------------------------
# 4 · PU-4 — THE ROUTE READS THE TREND
# ---------------------------------------------------------------------------

def test_the_route_verdict_never_reads_one_station_count():
    """PU-4, AND IT ALREADY RETRACTED A HULL THIS PROJECT HAD SHIPPED.

    Re-measured as a FAMILY rather than at one station count, a hull reported
    as buildable at 4.92 mm read n=41 4.92 / n=81 5.22 / n=161 8.71 mm —
    RISING, verdict NON_DEVELOPABLE. A shortfall that FALLS under refinement is
    the 41-station polyline's sagitta; one that RISES is double curvature. Only
    the second is a reason to change the boat.

    So `route` is a function of the VERDICT and of nothing else. In particular
    REFINING — falling but still over the bar — must NOT route to a mould.
    """
    import ui.api as api

    out = api.refold_payload({"params": _params(), "counts": (41, 81)})
    assert out["source"] in ("measured", "refused")
    if out["source"] == "refused":
        pytest.skip("the unroller refused this hull; the mapping is asserted "
                    "structurally below")
    assert out["verdict"] in ("PASSES", "REFINING", "NON_DEVELOPABLE",
                              "REFUSED")
    assert len(out["counts"]) >= 2, "one count is a number, not a verdict"
    assert out["verdict_meaning"], "a verdict with no explanation is a wall"

    # the mapping itself, asserted over every verdict rather than over the one
    # this hull happened to produce
    mapping = {"PASSES": "kit", "REFINING": "search",
               "NON_DEVELOPABLE": "mould", "REFUSED": "mould"}
    assert mapping[out["verdict"]] == out["route"]
    assert mapping["REFINING"] != "mould"


# ---------------------------------------------------------------------------
# 5 · KG IS MEASURED FROM THE KEEL PLANE
# ---------------------------------------------------------------------------

def test_the_capsize_check_measures_kg_from_the_keel_not_the_waterline():
    """MEASURED 2026-08-21 WHILE WIRING THIS ENDPOINT: KG CAME OUT −0.02 m.

    `MassAggregate.vcg_m` is in hull coordinates, where z = 0 is the design
    waterline and the keel sits at −T. `hydrostatics.gz_curve` wants KG ABOVE
    THE KEEL. Handing it `vcg_m` produced a centre of gravity BELOW the keel,
    and the entire GZ curve turns on that lever — so the screen would have
    drawn a confident, plausible, wrong righting curve.

    `evaluate` itself calls `agg.vcg_above_keel(t_design)`; this endpoint must
    use the SAME conversion, not a second one.
    """
    import ui.api as api

    out = api.capsize_payload({"params": _params()})
    if out["source"] == "refused":
        pytest.skip("no equilibrium at this displacement: " + out["reason"])
    kg = out["kg_above_keel_m"]
    assert kg > 0.0, (
        f"KG {kg} is at or below the keel plane — this is the vcg_m/"
        f"vcg_above_keel confusion, measured at -0.02 m")
    t = _params()["T"]
    assert 0.0 < kg < 3.0 * t, f"KG {kg} is not a plausible height over T={t}"
    assert out["assumptions"], "a GZ curve with no stated assumptions is a claim"


# ---------------------------------------------------------------------------
# 6 · THE FROUDE GUARD REFUSES BY NAME
# ---------------------------------------------------------------------------

def test_speeds_past_the_thin_ship_limit_are_refused_not_extrapolated():
    """The drag model is valid to Fn 0.45 and there is no Savitsky-class model
    in this tree, so the semi-displacement and planing bands are refused BY
    NAME. A faded curve there would be a guess wearing a line style."""
    import ui.api as api

    out = api.speedsweep_payload({"params": _params(),
                                  "speeds_kn": [3.0, 5.0, 20.0]})
    states = {p["kn"]: p["state"] for p in out["points"]}
    assert states[3.0] == "OK" and states[5.0] == "OK"
    assert states[20.0] == "REFUSED"
    fast = [p for p in out["points"] if p["kn"] == 20.0][0]
    assert "0.45" in fast["reason"], "the refusal must name the limit it hit"
    assert "rt_n" not in fast or fast.get("rt_n") is None, (
        "a refused point must not carry a resistance — that is the "
        "extrapolation this guard exists to prevent")


# ---------------------------------------------------------------------------
# 7 · THE VALIDATION SCREEN CANNOT CLAIM A VERDICT IT DID NOT RUN
# ---------------------------------------------------------------------------

def test_the_gates_screen_says_it_ran_no_suite():
    """A GREEN DOT BECAUSE A PAGE LOADED IS THE DISHONESTY THE LEDGER PREVENTS.

    A gate's verdict comes from RUNNING its suite. This endpoint serves the
    registry and the expected-red ledger and says, in the payload, that it ran
    nothing — so a screen cannot render a status it was never given.
    """
    import ui.api as api

    out = api.gates_payload()
    assert out["suite_run"] is False
    assert "no suite was run" in out["suite_note"]
    assert out["gates"], "the gate registry is empty"
    # every ledgered gate keeps its watermark verbatim — including the one that
    # is deliberately the STRING "NONE", because the run that carried its
    # number was deleted and the figure is unreproducible
    assert out["ledger"], "no expected-red rows served"
    for name, row in out["ledger"].items():
        assert row["owner"], f"{name} has no owner"
        assert row["review_by"], f"{name} has no review_by"
        assert row["watermark"] is not None, f"{name} has no watermark"


def test_no_benchmark_is_served_without_its_scope():
    """Gate 2M is SOLVER VERIFICATION ONLY: the only CFD anchor is a 230 m
    container ship that shares no chine, transom or spray physics with these
    craft. A benchmark row served without that sentence is an invitation to
    read a green gate as small-craft validation."""
    import ui.api as api

    out = api.validation_payload()
    ids = {b["id"] for b in out["benchmarks"]}
    assert {"KCS", "DSYHS", "HARD-CHINE"} <= ids
    for b in out["benchmarks"]:
        if b.get("error"):
            continue
        assert b.get("scope_warning"), f"{b['id']} has no scope line"
        assert b["confidence"] in out["confidence_model"], b["id"]
    kcs = [b for b in out["benchmarks"] if b["id"] == "KCS"][0]
    assert "SOLVER VERIFICATION ONLY" in kcs["scope_warning"]
    # the hard-chine hole is a ROW, not an omission
    hc = [b for b in out["benchmarks"] if b["id"] == "HARD-CHINE"][0]
    assert hc["confidence"] == "UNVALIDATED"


# ---------------------------------------------------------------------------
# 8 · STATIC SERVING, AND THE ENGINEER'S PAGE STAYS REACHABLE
# ---------------------------------------------------------------------------

def test_the_static_handler_refuses_to_escape_its_directory():
    """`_app_file` concatenates a REQUEST PATH onto a directory and is
    reachable from a browser. Every such handler is a path traversal until it
    proves otherwise."""
    import ui.server as S

    assert S._app_file("index.html")
    for bad in ("../server.py", "../../CLAUDE.md", "../api.py",
                "../../data/gate-ledger.json"):
        with pytest.raises((FileNotFoundError, ValueError)):
            S._app_file(bad)


def test_the_root_still_serves_the_engineers_page():
    """THE BUILDER SURFACE DOES NOT GET TO TAKE `/` BY DEFAULT.

    It was briefly served there, and `tests/test_phase4.py::
    test_http_server_smoke` failed on `assert "slider surface" in html` — an
    EXISTING fence over an entry point this work was not asked to move. The
    routing changed rather than the assertion: `/` and `/index.html` keep the
    engineer's page, `/app` serves the builder surface, `serve()` prints both.

    PU-1 also requires the raw `/bounds` sliders to stay reachable with the
    SAME evaluation behind them; both surfaces call the same `/eval`.
    """
    src = (ROOT / "ui" / "server.py").read_text()
    assert '("/", "/index.html", "/legacy")' in src
    assert '("/app", "/app/", "/studio")' in src
    assert (ROOT / "ui" / "index.html").is_file()
    assert (APP / "index.html").is_file()


def test_the_app_ships_no_external_asset():
    """A loopback design tool that goes blank without a network is a design
    tool that fails in a workshop. No CDN script, no external stylesheet, no
    remote font."""
    for p in list(APP.glob("*")):
        src = p.read_text()
        for bad in ("https://", "http://cdn", "cdnjs", "unpkg", "jsdelivr",
                    "fonts.googleapis"):
            if bad == "https://" and p.suffix == ".js":
                # a bare URL in a comment is fine; a fetch of one is not
                assert "fetch(\"https://" not in src and \
                       "fetch('https://" not in src, p.name
                continue
            assert bad not in src, f"{p.name} reaches out to {bad}"


# ---------------------------------------------------------------------------
# 9 · THE SEARCH REPORTS WHY A DESIGN DIED
# ---------------------------------------------------------------------------

def test_the_sweep_names_the_row_that_killed_each_design():
    """NEVER HIDE A FAILED DESIGN. MEASURED on 30 draws from the panel's own
    default brief: 2 of 30 feasible, 6 failing ONLY on bend radius, and NO hull
    in the population reaching the radius its own required ply can take (best
    1.40 m against a 1.44 m floor). That is a finding about the product, and it
    is only visible if rejections carry their reason."""
    import time

    import ui.api as api

    started = api.search_start({"n": 12, "governed": True, "seed": 0})
    jid = started["job"]
    for _ in range(600):
        st = api.search_status({"job": jid})
        if st["state"] != "RUNNING":
            break
        time.sleep(0.1)
    assert st["state"] == "DONE", st.get("error")
    assert st["done"] == 12
    assert st["n_kept"] + st["n_rejected"] == 12
    if st["n_rejected"]:
        assert st["rejected_counts"], "rejections were counted but not named"
        for r in st["rejections"]:
            assert r["row"] and r["why"], "a rejection with no reason is a wall"
    assert api.search_status({"job": "nope"})["source"] == "refused"


# ---------------------------------------------------------------------------
# 10 · PU-7 — THE LEGAL STAGE RENDERS A ROUTE, IT DOES NOT COMPUTE ONE
# ---------------------------------------------------------------------------

def test_the_delivery_route_is_rendered_not_recomputed():
    """`policy/legal.py` already decides the conformity module from hull length
    and design category, with the article and the clause text. A second routing
    in the UI would be the same clause decided twice, and the two copies would
    drift the first time one was edited — which is this repository's signature
    defect applied to law instead of to a number.

    So the envelope payload CARRIES the route, including its refusals: a craft
    the RCD does not define (26 m) is a refusal, and a brief with no stated
    length has no route rather than a default one.
    """
    import ui.api as api

    ok = api.envelope_payload({"category": "C",
                               "mission": {"lwl_hint_m": 10.0}})["route"]
    assert ok["mode"] == "module_a_self_certified"
    assert ok["article"].startswith("RCD Art. 20")
    assert ok["conditions"], "a module cell with no condition text is a claim"
    # the AI Act limb is decided, and the OTHER limb is explicitly left open
    assert ok["ai_act"]["high_risk"] is None

    none_stated = api.envelope_payload({"category": "C"})["route"]
    assert none_stated["mode"] == "UNKNOWN"
    assert "not a default one" in none_stated["refusal"]

    outside = api.envelope_payload({"category": "C",
                                    "hull_length_m": 26.0})["route"]
    assert outside["mode"] == "REFUSED"
    assert "24.0" in outside["refusal"]
