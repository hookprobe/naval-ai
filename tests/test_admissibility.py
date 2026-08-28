"""Gate tests for the CFD-admissibility screen.

THE MOTIVATING INCIDENT. The Gate 2U seed-0 campaign
(`scripts/mesh_robustness.py --n 25 --seed 0 --solve 2 --np 10`, scale 1.0,
speed 2.57, LTS) meshed **6 of its first 18 hulls** against a >=95% bar, and
all 18 passed `grammar.check()`. Every bar in `navalai/admissibility.py` is
tested here against the VERBATIM geometry it was written to refuse
(docs/LESSONS.md defect class 3: a test showing a guard accepts a good case
proves nothing about rejection).

THE LABELS ARE READ FROM THE BANK NOW, NOT TRANSCRIBED — 2026-08-20, and this
is the change the rest of the module hangs off. This file used to carry
`MESHED = (2, 7, 9, 13, 15, 17)` and eleven tests keyed to those indices, on
the stated grounds that the campaign JSON was "an untracked, still-growing
artefact" a gate test must not read. Both halves of that reasoning expired:
the bank is committed and complete, and a transcription is a number declared
twice (defect class 2) whose second copy CANNOT NOTICE THAT THE POPULATION
UNDER IT MOVED. That is exactly what happened. The geometry kernel took the
genome from 15 to 16 parameters, `sample_valid` draws from `default_rng(seed)`
so an extra gene changes the draw at every index, and the two seed-0
populations share ZERO hulls (`navalai.population`, verified hull for hull).
"Hull 12" kept its name and became a different boat, and eleven tests kept
asserting things about it — which is why they were skipped for nine days.

`admissibility.calibration_labels()` reads the labels out of
`CALIBRATION_BANK` and REFUSES unless the bank's `genome_sha256` matches the
pinned `a16/s0/n25` manifest. A label can no longer be transferred to a hull
it was not measured on, because the transfer is what the fence checks.
"""

import ast
import json
import re
from pathlib import Path

import numpy as np
import pytest

from navalai import grammar, population
from navalai.admissibility import (CALIBRATION_BANK,
                                   CALIBRATION_GENOME_N_PARAMS,
                                   CALIBRATION_POPULATION_ID, Basis, Metric,
                                   Verdict, calibration_is_current,
                                   calibration_labels, screen, surface_grid)
from navalai.cfd.case import _HULL_REFINE, _refine_boxes, layer_spec
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import MissionSpec

SPEED = 2.57
SCALE = 1.0

#: THE SUB-CELL ANCHOR, and finding it is half of what 2026-08-20 recalibrated.
#:
#: No hull of the labelled population `a16/s0/n25` is below any danger edge at
#: scale 1.0 — that is the campaign's own finding, not a gap — so a guard
#: exercised only on those 25 hulls is a guard never made to fire
#: (docs/LESSONS.md defect class 3).
#:
#: THE OBVIOUS FIX WAS TRIED FIRST AND IS REFUTED, so it is written down
#: rather than re-attempted: the bars are CELL-relative, so shrinking the case
#: should trip them, and it does — hull 18's bottom panel goes 0.262 cells at
#: scale 1.0 to 0.092 at 0.35. But `write_resistance_case` CANNOT WRITE those
#: cases: at scale <= 0.4 on that hull the air z-block collapses to one cell
#: and `_write_case_dicts` dies with `ZeroDivisionError` (`case.py` line 2737,
#: `r = grading ** (1.0 / (n - 1))` at n=1). The refusal window (<= 0.35) and
#: the writable window (>= 0.45) are DISJOINT, so a model-scale fixture would
#: have been a defect measured at a configuration the product cannot run
#: (defect class 6). Reported to the case.py owner; not worked around here.
#:
#: So the anchor is a full-scale hull from the DEVELOPMENT stream instead
#: (`population.DEV_SEED`, the only seed that may be tuned or fixtured on).
#: MEASURED: hull 152 of `sample_valid(160, MissionSpec(), seed=0)` is the
#: first hull the screen refuses with NO ladder rescue at scale 1.0 —
#: `min_interior_sheer_halfwidth_cells` 0.0636 and
#: `min_bottom_panel_width_cells` 0.0648, both against a 0.1-cell edge.
#: 2026-08-26 NOTE: the anchor was briefly re-derived as hull 104 while the
#: sac solver's inner bracket refused edge hulls; the float-tolerance fix
#: restored the historical acceptance and the stream ROUND-TRIPPED back to
#: this exact hull and these exact values. The stream is pinned by sha
#: below, so any future drift is loud.
SUB_CELL_HULL = 152
SUB_CELL_DRAW = 160


@pytest.fixture(scope="module")
def campaign_hulls():
    """The CALIBRATION POPULATION, drawn by this tree and hash-checked.

    The draw is `sample_valid(25, MissionSpec(), seed=0)` — what the campaign
    itself ran — and it is fenced against the pinned manifest rather than
    trusted, because the entire defect this module is recovering from is a
    population that changed while keeping its name.
    """
    manifest = next(
        (doc for _p, doc in population.manifests()
         if doc.get("population_id") == CALIBRATION_POPULATION_ID), None)
    assert manifest is not None, (
        f"no manifest for {CALIBRATION_POPULATION_ID} in "
        f"{population.MANIFEST_DIR} — the calibration population is not pinned")
    # THE POPULATION IS THE STORED GENOMES, not a live redraw. Until
    # 2026-08-26 this helper redrew sample_valid(25, seed=0) and checked it
    # hashed to the manifest — which glued the bank's labels to the CURRENT
    # sampler bounds: the day the Cp gene box was widened (audit finding
    # C.2), the same uniforms scaled to different gene values and the fence
    # fired even though the measured hulls had not changed. The bank's
    # labels belong to the hulls they were measured ON, which the manifest
    # itself records; the identity check is now internal (stored genomes
    # hash to the recorded sha), and post-hoc genes are padded at their
    # proven no-op defaults to reach the current arity.
    G = np.asarray(manifest["genomes"], float)
    assert population.genome_sha256(G) == manifest["genome_sha256"], (
        "the manifest's own genomes do not hash to its recorded sha — the "
        "calibration bank has been edited; re-run scripts/mesh_robustness.py")
    if G.shape[1] < grammar.N_PARAMS:
        pad = np.zeros((len(G), grammar.N_PARAMS - G.shape[1]))
        for _nm, _v in grammar.POST_HOC_DEFAULTS.items():
            _i = grammar.NAMES.index(_nm) - G.shape[1]
            if _i >= 0:
                pad[:, _i] = float(_v)
        X = np.hstack([G, pad])
    else:
        X = G
    return X


@pytest.fixture(scope="module")
def reports(campaign_hulls):
    return [screen(x, SPEED, SCALE) for x in campaign_hulls]


@pytest.fixture(scope="module")
def dev_stream(campaign_hulls):
    """The development stream, long enough to reach `SUB_CELL_HULL`.

    Fenced on PREFIX EQUALITY against `campaign_hulls`, which is itself
    hash-checked against the pinned manifest. Without that, "hull 152" is a
    name for whatever a longer draw happens to produce — the same defect one
    index further out that cost this file eleven tests.
    """
    X, _ = sample_valid(SUB_CELL_DRAW, MissionSpec(), seed=population.DEV_SEED)
    assert len(X) == SUB_CELL_DRAW
    # PINNED BY ITS OWN SHA (2026-08-26). The old fence was prefix-equality
    # with the campaign manifest, which glued this stream to the sampler
    # bounds of the day the bank was measured; the campaign fixture now
    # returns the STORED genomes, so the live stream is pinned directly.
    # When a deliberate bounds change moves this hash: re-record it AND
    # re-derive SUB_CELL_HULL by searching the stream (the constant's
    # comment shows the procedure) — never delete the guard.
    # RE-RECORDED 2026-08-27 (Phase 3 arity 23 -> 27, the dwl genes): the
    # sha covers the full vectors, so four appended no-op columns move it
    # while the HULLS stand still. VERIFIED before re-recording: hull 152
    # round-trips to the identical screen values (sheer ridge 0.0636,
    # bottom panel 0.0648 cells) — the same round-trip proof the
    # 2026-08-26 note demanded. Previous shas: arity 23
    # 60e8596d1b265ef0ef28dce4983d36fab36bcc2213328ab837fc804d1df1a54b,
    # arity 27 (the dwl quartet)
    # e9cb7c8c35dd364c4730df8f1887e9460636773a0153399a1dee0b6ee13fe61e.
    # RE-RECORDED again the same evening for the Phase-4 tunnel trio
    # (27 -> 30); hull 152 round-trips to the identical screen values
    # (0.0636 / 0.0648), exactly as at both prior events.
    # arity 30 (the tunnel trio)
    # f38618a9e8e994f304f8a5009d033db6e89646025d45c8e85f1a12710c560511;
    # arity 32 (the Phase-4B split pair), hull 152 round-tripping to
    # 0.0636 / 0.0648 for the FOURTH consecutive event:
    # 027577658b4cd38aba407779068096da3acaf178037d183a714b60eaad2b03e0.
    # RE-RECORDED 2026-08-28 for arity 32 -> 34 (the rho(x) pair,
    # rho_bow/rho_len). FIFTH consecutive event, and the round trip is
    # again IDENTICAL: hull 152 screens to sheer ridge 0.0636 and bottom
    # panel 0.0648 cells, verdict DANGEROUS, hull cell 0.0424 m, exactly
    # as at all four prior events. That the sha moves while the hulls do
    # not is the POINT of it covering the full vectors: two appended
    # no-op columns are a real change to the stream's identity and a
    # non-change to its geometry, and the guard is what tells them apart.
    assert population.genome_sha256(np.asarray(X, float)) == (
        "cf909c702ebd83c9b582df6ec50fb0fa14aa92f9245f5b6bd030db88e0318bb7"), (
        "the development stream moved — re-derive SUB_CELL_HULL and "
        "re-record this sha alongside the bounds change that moved it")
    return X


# ---------------------------------------------------------------------------
# The screen must not become a SECOND copy of the geometry or of the pipeline.
# ---------------------------------------------------------------------------

def test_surface_grid_is_the_grid_closed_mesh_triangulates():
    """`surface_grid` is a fast replica of `Hull.closed_mesh`'s vertex grid.

    A replica is defect class 2 (a number — here a whole surface — declared
    twice) unless it is fenced, and it exists only because `closed_mesh` is a
    Python double loop costing ~1.4 s per hull at the case's 600x120
    triangulation.

    STRENGTHENED 2026-08-12, when the chine became a grid row: the fence used
    to re-derive the grid from `_section_at` + `_halfbreadth_at`, which is a
    THIRD transcription of the sampling rule and drifts with the other two.
    It now asserts that every point of `surface_grid` is literally a vertex of
    what `closed_mesh` returned — the only statement that cannot be satisfied
    by two copies agreeing with each other and disagreeing with the mesh.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=7)
    for x in X:
        h = Hull(x)
        nx, nz = 61, 12
        S = surface_grid(h, nx, nz)
        verts, tris = h.closed_mesh(nx=nx, nz=nz)
        emitted = {tuple(np.round(v, 9)) for v in verts[tris.ravel()]}
        xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
        for i in (0, 1, nx // 3, nx // 2, nx - 2, nx - 1):
            assert S[i, :, 0] == pytest.approx(xs[i])
            for j in range(nz + 1):
                assert tuple(np.round(S[i, j], 9)) in emitted, (i, j)


def test_the_chine_is_a_row_of_the_grid_not_a_corner_it_chords_across():
    """Stage A, and the reason `chine_row` exists at all.

    MEASURED 2026-08-12 at the nx=600/nz=120 triangulation
    `make_resistance_case` writes: the exact chine point of the blended
    section sat 11.95 / 4.50 / 11.45 mm off the chord the uniform-z grid put
    in its place, on hulls 4 / 8 / 14 of `sample_valid(25, MissionSpec(),
    seed=0)` — at EVERY x, not only at the stem. Bar: 1e-9 m, i.e. the chine
    is ON the surface, not near it (docs/LESSONS.md defect class 3 — the
    assertion has to be the one the old grid FAILS, and the old grid fails
    this by 12 mm).

    PINNED TO roundness = 0 ON 2026-08-13. `chine_row` still exists after the
    geometry rebuild, but for a FILLETED bilge it returns the fillet's
    mid-point, not a corner — so "the chine is a row of the grid" is a claim
    about a hull that HAS a chine. Measured on the reference hull with the
    fillet live, the row sits 0.430 m from `_section_at`'s breakpoint, which is
    the fillet's own curvature and not a regression. At roundness = 0 the
    kernel is bit-identical to the pre-rebuild one (fenced at 1e-12 in
    tests/test_geometry_kernel.py) and the 1e-9 bar below is exactly as hard as
    it was. Relaxing the bar to cover a fillet would have retired the
    measurement this test exists for.
    """
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    ir = grammar.NAMES.index("roundness")
    for hid in (4, 8, 14):
        x = np.asarray(X[hid], float).copy()
        x[ir] = 0.0                       # a chine claim needs a chine
        h = Hull(x)
        nz = 120
        jc = h.chine_row(nz)
        assert 1 <= jc <= nz - 1
        S = surface_grid(h, 97, nz)
        xs = np.linspace(float(h.x[0]), float(h.x[-1]), 97)
        for i in range(0, 97, 7):
            pts = h._section_at(float(xs[i]))
            assert S[i, jc, 1] == pytest.approx(pts[1, 0], abs=1e-9)
            assert S[i, jc, 2] == pytest.approx(pts[1, 1], abs=1e-9)
        # and the row is still a partition: keel at 0, sheer at nz
        assert S[50, 0, 2] == pytest.approx(h._section_at(float(xs[50]))[0, 1])
        assert S[50, nz, 2] == pytest.approx(h._section_at(float(xs[50]))[2, 1])


def test_every_grid_point_still_lies_on_the_analytic_section_polyline():
    """Redistributing rows must MOVE VERTICES ALONG the section, never off it.

    The panels are unchanged straight segments; only the sampling parameter
    changed. If this ever fails, the row split has become a shape change —
    which would be a different boat, not a better mesh.

    PINNED TO roundness = 0 ON 2026-08-13, and the pin is the point rather than
    a convenience. "Lies on the section POLYLINE" is a HARD-CHINE property: the
    geometry kernel rebuild made the bilge a fillet, and a point on a curve is
    not on the chord that used to approximate it — measured 0.058 m off at the
    reference hull, which is the fillet, not a defect. The claim this test was
    written to defend (redistributing rows moves vertices ALONG the section,
    never off it) is exactly true at roundness = 0, where the kernel is
    bit-identical to the old one to 1e-12. The curved case has its own
    assertion in tests/test_geometry_kernel.py, against the analytic CURVE.
    Weakening this bound to swallow a fillet would have made it measure nothing.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=7)
    ir = grammar.NAMES.index("roundness")
    for x in X:
        x = np.array(x, dtype=float).copy()
        x[ir] = 0.0                      # a polyline claim needs a polyline
        h = Hull(x)
        nx, nz = 61, 12
        S = surface_grid(h, nx, nz)
        xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
        for i in range(nx):
            pts = h._section_at(float(xs[i]))
            for j in range(nz + 1):
                y, z = float(S[i, j, 1]), float(S[i, j, 2])
                d = min(_seg_dist(y, z, 0.0, pts[0, 1], pts[1, 0], pts[1, 1]),
                        _seg_dist(y, z, pts[1, 0], pts[1, 1],
                                  pts[2, 0], pts[2, 1]))
                assert d < 1e-12, (i, j, d)


def _seg_dist(py, pz, ay, az, by, bz) -> float:
    e = np.array([by - ay, bz - az])
    q = np.array([py - ay, pz - az])
    den = float(e @ e)
    t = 0.0 if den <= 1e-30 else float(np.clip((q @ e) / den, 0.0, 1.0))
    return float(np.linalg.norm(q - t * e))


def test_the_batch_section_sampler_is_the_loop():
    """`Hull._sections_at_rows_batch` == a loop over `Hull._section_at_rows`.

    The batch is a SECOND COPY of the section sampler (defect class 2), kept
    only because the per-station call overhead of `sample_section` put the
    screen at ~140 ms/hull against its 100 ms bar (~600 stations per hull on
    the round-bilge path). The screen's danger/margin bars were MEASURED
    through this grid, so the batch must be VALUE-PRESERVING: every sampled
    point equal to the single-x path at 1e-12, on BOTH branches — roundness 0
    (the vectorised polyline) and roundness > 0 (the Bezier + arc-length
    resample) — INCLUDING at the real 600x120 screen resolution, because the
    bars' calibration lives at that grid, not at a toy one.
    `_section_at_rows` stays the definition; this fence is what lets
    `surface_grid` call the copy.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=7)
    ir = grammar.NAMES.index("roundness")
    exercised_round = False
    for x in X:
        for force_hard_chine in (False, True):
            xv = np.asarray(x, float).copy()
            if force_hard_chine:
                xv[ir] = 0.0
            h = Hull(xv)
            exercised_round |= h.roundness > 0.0
            nz = 24
            jc = h.chine_row(nz)
            xs = np.linspace(float(h.x[0]), float(h.x[-1]), 37)
            batch = h._sections_at_rows_batch(xs, jc, nz - jc)
            assert batch.shape == (37, nz + 1, 2)
            for k, xq in enumerate(xs):
                ref = h._section_at_rows(float(xq), jc, nz - jc)
                err = float(np.max(np.abs(batch[k] - ref)))
                assert err < 1e-12, (float(xq), h.roundness, err)
    assert exercised_round, (
        "seed-7 draw no longer contains a round-bilge hull — the Bezier "
        "branch went untested; pick a seed that exercises it")
    # ...and once at the resolution the screen actually samples (600x120,
    # from `stl_resolution` at scale 1), on one round-bilge hull: the
    # calibrated bars were measured through THIS grid, so the equality
    # claim has to hold where they live, not only on a small grid.
    h = Hull(np.asarray(X[0], float))
    assert h.roundness > 0.0
    nx, nz = 600, 120
    jc = h.chine_row(nz)
    xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
    batch = h._sections_at_rows_batch(xs, jc, nz - jc)
    for k in range(nx):
        ref = h._section_at_rows(float(xs[k]), jc, nz - jc)
        err = float(np.max(np.abs(batch[k] - ref)))
        assert err < 1e-12, (k, err)


def test_no_pipeline_constant_is_restated_in_this_module():
    """The bars are IMPORTED from `navalai.cfd.case`, never transcribed.

    The draft bar is 14.187 cells at scale 1 — but that number appears nowhere
    in `admissibility.py`, because it is `_refine_boxes(...)[-1]['bz1']` over
    the level-5 hull cell and it must move when `_FS_BOX`, `_HULL_REFINE` or
    `_NX_BASE` move. A transcribed copy is the defect this repository pays for
    most often (docs/LESSONS.md class 2).
    """
    src = Path("navalai/admissibility.py").read_text()
    # Comments and docstrings QUOTE these numbers on purpose — that is the
    # measurement record. Only executable code is checked (docs/LESSONS.md
    # defect class 8: a predicate that reads comments finds the word it is
    # looking for sitting in the comment ON the defect).
    code = re.sub(r"#.*", "", re.sub(r'"""(?:.|\n)*?"""', "", src))
    for literal in (r"14\.18", r"\b0\.035\b", r"\b0\.025\b", r"\b_FS_BOX\b"):
        assert not re.search(literal, code), \
            f"pipeline constant {literal!r} restated in code"
    # ...and the ones it MUST import instead. Read from the AST, not from the
    # text: an import list wraps across lines and a line-anchored regex then
    # silently stops seeing half of it.
    imported = {a.name for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.ImportFrom) for a in n.names}
    assert {"_refine_boxes", "_HULL_REFINE", "_NX_BASE", "layer_spec",
            "_LAYER_EXPANSION", "_DOMAIN_LENGTH_L"} <= imported


def test_the_draft_bar_is_demoted_to_a_receipt_by_the_confusion_table(
        campaign_hulls, reports):
    """RE-POINTED 2026-08-19: the first 16-gene confusion table
    (data/gate2u-16gene-mesh.json) measured this bar 0-for-4 as a rung-0
    predictor — hulls 4/5/6/8 below it all meshed CLEAN with the ladder
    unused — while catching neither actual refusal. The value is still
    RECORDED (the receipt survives); it votes on nothing, and this fence
    keeps it demoted until a measurement says otherwise."""
    m = reports[0].get("draft_over_hull_cell")
    assert m is not None, "the receipt must survive the demotion"
    assert m.danger_below is None, (
        "draft_over_hull_cell is voting again — the 16-gene confusion "
        "table measured it 0-for-4; re-basing it needs NEW evidence")
    assert "DEMOTED" in m.note


# ---------------------------------------------------------------------------
# Every bar, fed the input it must REFUSE.
# ---------------------------------------------------------------------------

# The tests below read a LABELLED mesh campaign — the screen's verdicts scored
# against measured checkMesh outcomes, hull by hull.
#
# THE SKIP THIS REPLACES, AND WHY IT LASTED NINE DAYS. Until 2026-08-20 these
# tests carried hard-coded hull indices from `gate2u-campaign-baseline.json`
# and skipped on `calibration_is_current()`, which was `grammar.N_PARAMS == 15`
# — an ARITY comparison. Eleven tests skipped with the reason "the screen's
# bars were calibrated on a 15-parameter genome and this tree has 16". The
# probe is now the GENOME HASH (the bank's against the pinned `a16/s0/n25`
# manifest's), which is a strictly stronger statement: two populations can
# agree about their arity and still share no hulls, and an arity check cannot
# tell them apart. The labels come from the bank, so nothing here can be
# re-pointed at a different population by editing an index.
_needs_calibration = pytest.mark.skipif(
    not calibration_is_current(),
    reason=(f"{CALIBRATION_BANK.name} does not label "
            f"{CALIBRATION_POPULATION_ID} as this tree draws it (arity "
            f"{grammar.N_PARAMS} vs calibrated {CALIBRATION_GENOME_N_PARAMS}, "
            f"or the genome hash / row set does not match) — re-run "
            f"scripts/mesh_robustness.py --population "
            f"{CALIBRATION_POPULATION_ID} --n 25 --np 10 --json "
            f"{CALIBRATION_BANK.name}"))


@pytest.fixture(scope="module")
def labels():
    """(bank, meshed ids, failed ids) — refuses if the bank is not ours."""
    return calibration_labels()


@pytest.mark.parametrize("mutate,why", [
    (lambda b: b.update(genome_sha256="0" * 64),
     "a bank measured on a DIFFERENT population — the verbatim 15-gene "
     "defect, which an arity check cannot see"),
    (lambda b: b.update(genome_arity=15),
     "a 15-gene bank, the era whose labels were transferred for nine days"),
    (lambda b: b.__setitem__("rows", b["rows"][:7]),
     "a PARTIAL bank: mesh_robustness.py rewrites its JSON after every hull "
     "so a thermal sleep cannot lose a campaign, and a seven-row file names "
     "itself `a16/s0/n7` — a population nobody drew"),
    (lambda b: b.__setitem__("rows", []),
     "an empty bank, which must not read as 'no failures'"),
])
@_needs_calibration
def test_the_calibration_probe_fires_on_the_input_it_exists_to_reject(
        tmp_path, monkeypatch, mutate, why):
    """docs/LESSONS.md defect class 3: a guard that was never made to fire.

    THE INCIDENT THIS NAMES. `calibration_is_current()` was
    `grammar.N_PARAMS == 15` from 2026-08-14 to 2026-08-20 and nothing ever
    fed it a wrong bank, because there was no bank — the labels were
    transcribed into this file as tuples. It said the calibration was void
    while the file next to it went on asserting things about "hull 12", and
    the two statements never met. The probe now reads a FILE, so it can be
    fed the file it must reject, and it is.

    Every mutation below is a real failure mode, not a fuzz: the hash swap is
    the 15-gene/16-gene defect itself, the partial bank is what this campaign
    looked like 20 minutes into its 41-minute run, and the empty bank is the
    `${VAR:-0}` shape (no rows must never read as no failures).
    """
    import navalai.admissibility as adm
    assert calibration_is_current(), (
        "the real bank is not current, so this test cannot show that a "
        "BROKEN one is rejected — it would pass for the wrong reason")
    bank = json.loads(CALIBRATION_BANK.read_text())
    mutate(bank)
    bad = tmp_path / CALIBRATION_BANK.name
    bad.write_text(json.dumps(bank))
    monkeypatch.setattr(adm, "CALIBRATION_BANK", bad)
    assert not adm.calibration_is_current(), why
    with pytest.raises(RuntimeError, match="refusing to hand back labels"):
        adm.calibration_labels()


@pytest.mark.parametrize("write", [None, "not json at all"])
def test_an_unreadable_calibration_bank_is_REFUSED_not_scored_as_clean(
        tmp_path, monkeypatch, write):
    """docs/LESSONS.md defect class 1, applied to the probe itself.

    `${_MQ_SKEW:-0}` turned "I could not measure this" into "this is
    perfect", and `not ledger_has("Gate 2M")` was TRUE when there was no
    ledger — inside the tool built to catch that defect. A missing or
    corrupt bank must therefore make `calibration_bank()` return None and the
    probe return False. It must NOT return `{}`, because `{}.get("rows") or
    []` reads as "no failures" and every label-scoring test in this file
    would then pass vacuously on a file that does not exist.
    """
    import navalai.admissibility as adm
    bad = tmp_path / "gone.json"
    if write is not None:
        bad.write_text(write)
    monkeypatch.setattr(adm, "CALIBRATION_BANK", bad)
    assert adm.calibration_bank() is None
    assert not adm.calibration_is_current()


@_needs_calibration
def test_the_draft_receipt_does_not_separate_the_labelled_campaign(
        reports, labels):
    """SUPERSEDES `test_draft_bar_refuses_the_hulls_whose_keel_sits_in_the_
    refine_band`, which asserted the OPPOSITE and was measured wrong.

    THE OLD ASSERTION (15-gene, `a15/s0/n74` prefix): campaign hulls 0, 1, 6
    and 12 at 10.14 / 12.31 / 11.82 / 13.20 hull cells of draft all failed
    checkMesh, and the screen refused all four while refusing none of the six
    that meshed. That was a real measurement on a population this tree cannot
    build, and it did NOT transfer: the first 16-gene table measured the bar
    0-for-4 as a rung-0 predictor, and `draft_over_hull_cell` was demoted to a
    non-voting receipt on 2026-08-19 rather than moved to a friendlier value.

    THE NEW ASSERTION is the refutation itself, on `a16/s0/n25`: the rung-0
    refusals are NOT the shallow-draft hulls. MEASURED — the one hull that
    failed (h011) has 15.06 cells of draft, and FOUR hulls that meshed clean
    sit BELOW it at 5.17 / 9.74 / 9.76 / 10.02 cells. That is the same
    0-for-4 the 2026-08-19 table found, on an independently re-run campaign.
    The test states it as an ordering fact — some hull that MESHED sits below
    some hull that FAILED — because that is what "this quantity does not
    separate them" means, and it is a claim the old bar's evidence, where all
    four hulls below the bar failed, would have failed.
    """
    m = reports[0].get("draft_over_hull_cell")
    assert m is not None and m.basis is Basis.DERIVED
    assert m.danger_below is None, "the demoted receipt is voting again"
    _bank, meshed, failed = labels
    assert failed, "no labelled failure in the bank: nothing to separate"
    draft = {h: reports[h].get("draft_over_hull_cell").value
             for h in meshed + failed}
    worst_fail = max(draft[h] for h in failed)
    below = sorted(h for h in meshed if draft[h] < worst_fail)
    assert below, (
        "every meshed hull has MORE draft than every failed one — the draft "
        "bar separates this population after all, and its demotion is now "
        "the thing that needs re-measuring")


def test_the_delivered_deck_ridge_bar_refuses_a_verbatim_sub_cell_deck(
        dev_stream):
    """SUPERSEDES `test_collapse_bar_refuses_the_hulls_whose_sheer_was_
    silently_clipped`, whose anchors this tree cannot build.

    THE OLD ANCHORS were 15-gene campaign hulls 5, 11 and 12, to which the
    PRE-P1 kernel delivered a LITERAL zero-width deck ridge (0.0 cells against
    a bar of 1.0). They live in `a15/s0/n74`, which `navalai.population`
    reports as HISTORY — the draw cannot be reproduced at 16 genes — so that
    test could never have un-skipped, whatever a campaign measured. Its own
    docstring said so ("permanently skipped in practice") and it still sat
    behind a probe that implied it might.

    THE GUARD IS NOT DELETED, IT IS RE-ANCHORED (the skip reason's own
    instruction), and it no longer needs the calibration at all: it is a
    statement about a BAR, not about a labelled outcome, so gating it on a
    campaign was part of why it never ran. `min_interior_sheer_halfwidth_
    cells` is the successor bar and it is fed the input it must reject
    (docs/LESSONS.md defect class 3) — hull 152 of the development stream,
    delivered deck ridge 0.0636 cells against a 0.1-cell edge, at full scale.
    """
    r = screen(dev_stream[SUB_CELL_HULL], SPEED, SCALE)
    m = r.get("min_interior_sheer_halfwidth_cells")
    assert m.verdict is Verdict.DANGEROUS, (
        f"hull {SUB_CELL_HULL} reads {m.value:.4f} cells against a "
        f"{m.danger_below} edge and is no longer refused — re-anchor this "
        f"guard on a hull that IS below the edge (search the development "
        f"stream), do not delete it")
    assert m.value < m.danger_below
    assert m.basis is Basis.DERIVED
    assert m.ladder_rescuable is False, (
        "a sub-cell feature has no rung: the cell size does not depend on the "
        "layer count")
    assert "min_interior_sheer_halfwidth_cells" in r.refused_no_rescue


def test_sub_cell_bars_refuse_a_verbatim_sub_cell_hull(dev_stream,
                                                       campaign_hulls):
    """RE-ANCHORED 2026-08-20 from 15-gene hull 20 to development hull 152.

    THE OLD ANCHOR: `a15/s0/n74` hull 20, bottom panel 0.998 cells and transom
    half-beam 0.998 cells, tripping both bars at scale 1. It was written as a
    PRE-REGISTERED prediction and its mesh outcome was never recorded before
    the genome changed underneath it, so the prediction can never be scored.

    THE NEW ANCHOR: hull 152 of the development stream, bottom panel 0.0648
    cells at scale 1.0 against the 0.1-cell edge. The edge itself is the one
    the 16-gene table re-based 1.0 -> 0.1 on 2026-08-19, because hull 18 of
    the labelled population reads 0.262 cells and MESHED CLEAN on the metal —
    so the second half of this test is the other direction of the same
    measurement: the bar must refuse 0.0648 and admit 0.262, and a bar that
    refused both would have been a bar softened in the wrong direction.
    """
    r = screen(dev_stream[SUB_CELL_HULL], SPEED, SCALE)
    m = r.get("min_bottom_panel_width_cells")
    assert m.verdict is Verdict.DANGEROUS, (
        f"hull {SUB_CELL_HULL} reads {m.value:.4f} cells against a "
        f"{m.danger_below} edge — re-anchor the fixture, do not delete it")
    assert r.verdict is Verdict.DANGEROUS
    assert "min_bottom_panel_width_cells" in r.refused_no_rescue
    # THE MEASURED-CLEAN SIDE OF THE SAME EDGE, at the same scale.
    good = screen(campaign_hulls[18], SPEED, SCALE)
    assert good.get("min_bottom_panel_width_cells").verdict is Verdict.MARGINAL
    assert good.refused_no_rescue == ()


def test_an_unmeasurable_metric_is_refused_and_beats_every_other_verdict():
    """docs/LESSONS.md defect class 1: `${_MQ_SKEW:-0}` scored 'could not
    measure' as a perfect 0 against a bar of 20. A NaN here must never be able
    to admit a hull, and it must SAY which metric could not be read."""
    m = Metric.of("x", float("nan"), "cells", Basis.DERIVED, "why",
                  danger_below=1.0)
    assert m.verdict is Verdict.UNMEASURED
    assert "NOT MEASURABLE" in m.note
    assert Verdict.UNMEASURED.value > Verdict.DANGEROUS.value
    assert Metric.of("y", None, "-", Basis.DERIVED, "z").verdict is \
        Verdict.UNMEASURED


def test_a_diagnostic_metric_never_votes(reports):
    """The stem cusp and the x_mb tangent break are REAL and do not predict.

    AUC against mesh failure over 15-gene campaign hulls 0-17 (hull 5
    excluded, its record is self-contradictory): bow_bluntness_cells 0.500,
    xmb_tangent_break_deg 0.500 — chance, both of them. HISTORY, `a15/s0/n74`:
    the AUC cannot be re-measured on `a16/s0/n25` because that campaign has
    ONE labelled failure and an AUC from a single positive is a number the
    window invented (docs/LESSONS.md, the period-from-too-few-cycles lesson).
    So the metrics stay DIAGNOSTIC on the older evidence plus the absence of
    newer evidence, which is the honest reason, and no later session can
    promote 'we compute it' into 'it predicts it'.
    """
    diag = [m for m in reports[7].metrics if m.basis is Basis.DIAGNOSTIC]
    assert {m.name for m in diag} >= {"bow_bluntness_cells",
                                      "xmb_tangent_break_deg"}
    for m in diag:
        assert not m.votes
        assert m.verdict is Verdict.SAFE
    # RE-MEASURED 2026-08-20 on `a16/s0/n25`: hull 7 reads bow_bluntness 0.41
    # cells and a 16.1 deg tangent break, and hull 11 — the ONE rung-0 refusal
    # in the bank — reads 0.39 and 18.1. Neither diagnostic separates them, and
    # hull 7 must still come out unrefused.
    assert reports[7].refused_by == ()


# ---------------------------------------------------------------------------
# The 2026-08-18 re-derivation (docs/MESHABILITY_MATH.md): retirement fences,
# the rescue axis, and the solvability receipt.
# ---------------------------------------------------------------------------

def test_the_stale_sheer_formula_is_retired_and_its_successor_exists(reports):
    """`sheer_collapse_cells` recomputed the PRE-P1 sheer law (unenveloped
    flare) while the rebuilt kernel refuses a negative sheer at L0 — a second
    copy, voting. MEASURED: it refused 5 of 25 seed-0 hulls whose delivered
    interior sheer is 0.06..0.37 m. This fence keeps it dead and pins the
    successor's contract (delivered surface, sub-cell bar, no ladder rescue).
    """
    names = {m.name for m in reports[0].metrics}
    assert "sheer_collapse_cells" not in names, (
        "the retired stale-copy metric is back; see admissibility module "
        "docstring item 1 before resurrecting it")
    m = reports[0].get("min_interior_sheer_halfwidth_cells")
    assert m.basis is Basis.DERIVED
    # 1.0 -> 0.1 (2026-08-19): hull 18 at 0.35 cells meshed clean at rung
    # 0 on the metal; the labelled-fatal anchors are literal 0.0 ridges.
    assert m.danger_below == 0.1
    assert m.ladder_rescuable is False


def test_the_rescue_axis_matches_each_metrics_mechanism(reports):
    """Cell-scale metrics have no rung (the cell ignores the layer count);
    layer-scale metrics are the ladder's own domain (measured: the backoff
    campaign meshed every draft-bar refusal at a lower count, and the stack
    height falls with n). The writer refuses only the first set."""
    r = reports[0]
    for nm in ("min_bottom_panel_width_cells", "min_topside_panel_height_cells",
               "transom_half_beam_cells", "transom_immersion_cells",
               "min_interior_sheer_halfwidth_cells"):
        assert r.get(nm).ladder_rescuable is False, nm
    for nm in ("draft_over_hull_cell", "stack_over_min_radius"):
        assert r.get(nm).ladder_rescuable is True, nm


def test_refused_no_rescue_is_the_unrescuable_subset_and_unmeasured_is_fatal():
    """The writer's refusal set: DANGEROUS-without-a-rung plus UNMEASURED —
    an unmeasurable quantity must never admit a hull (defect class 1), and a
    rescuable DANGEROUS must never appear here (it has a measured
    deterministic path, the run-case.sh ladder)."""
    from navalai.admissibility import Report
    mets = (
        Metric.of("cell_scale", 0.5, "cells", Basis.DERIVED, "sub-cell",
                  danger_below=1.0, ladder_rescuable=False),
        Metric.of("layer_scale", 0.5, "cells", Basis.DERIVED, "rung-0",
                  danger_below=1.0, ladder_rescuable=True),
        Metric.of("unread", float("nan"), "-", Basis.DERIVED, "unmeasured",
                  danger_below=1.0, ladder_rescuable=True),
        Metric.of("diag", 0.0, "-", Basis.DIAGNOSTIC, "reported only"),
    )
    rep = Report(Verdict.UNMEASURED, mets, 0.04, 10.0, 7)
    assert set(rep.refused_no_rescue) == {"cell_scale", "unread"}
    assert set(rep.refused_by) == {"cell_scale", "layer_scale", "unread"}


def test_the_solvability_receipt_carries_the_measured_anchors(reports):
    """tau = V/(A_max*U) separates solved (7.8e-6..2.1e-5 s) from diverged
    (4.356e-18 s) by 12 orders while checkMesh is blind (docs/audit/STATUS.md,
    2026-08-18). The screen's pre-mesh receipt is the INTENDED minimum cell
    time scale; a healthy scale-1 case intends ~1e-4 s, orders above the
    run-case.sh 1e-12 s abort bar, and the receipt must say so and not vote.
    """
    m = reports[0].get("intended_min_cell_flow_time_scale_s")
    assert m.basis is Basis.DIAGNOSTIC and not m.votes
    assert 1e-5 < m.value < 1e-2, (
        f"intended tau {m.value:.3g}s is outside the healthy design decade — "
        f"either the layer/fs derivation moved or the receipt broke")
    assert "1e-12" in m.note and "7.8e-6" in m.note


def test_the_bilge_fillet_radius_is_reported_and_does_not_vote_yet(reports):
    """The 16th gene's own failure mode: NO round-bilge hull has a measured
    mesh outcome (case a is a hard chine; every labelled campaign is
    15-gene), so the fillet-radius metric reports its pre-registered window
    (stl_row < r < cell) and is forbidden to vote until a campaign labels
    it. Promoting it without labels would be the V6-first-draft defect."""
    m = reports[0].get("bilge_min_radius_cells")
    assert m.basis is Basis.DIAGNOSTIC and not m.votes
    # a hard chine reports inf: no fillet, no radius, nothing to resolve
    X, _ = sample_valid(1, MissionSpec(), seed=0)
    xr = np.asarray(X[0], float).copy()
    xr[grammar.NAMES.index("roundness")] = 0.0
    hard = screen(xr, SPEED, SCALE).get("bilge_min_radius_cells")
    assert not (hard.value < float("inf"))


# ---------------------------------------------------------------------------
# The screen as a whole, against every historical case.
# ---------------------------------------------------------------------------

@_needs_calibration
def test_the_screen_refuses_no_hull_that_actually_meshed(reports, labels):
    """Zero false alarms on the hulls that meshed — the direction that
    matters, because a screen that refuses good hulls silently shrinks the
    design space and Gate 2U would then pass by exclusion.

    RE-POINTED 2026-08-20 from the 15-gene labels (6 meshed of 18) to the
    `a16/s0/n25` bank. The claim is unchanged and it is now measured on hulls
    this tree can build.
    """
    _bank, meshed, _failed = labels
    assert meshed, "the bank records no mesh success: nothing is being checked"
    for hid in meshed:
        assert reports[hid].verdict is not Verdict.DANGEROUS, (
            f"hull {hid} MESHED but the screen refused it: "
            f"{reports[hid].refused_by}")


@_needs_calibration
def test_the_screen_predicts_neither_rung_0_refusal_on_the_16_gene_population(
        reports, labels):
    """PINS THE MEASUREMENT, INCLUDING ITS LIMIT — and the limit got worse.

    OLD, on `a15/s0/n74` rows 0-17 (`gate2u-campaign-baseline.json`):
    **TP 6, FP 0, FN 6, TN 6** — precision 1.000, recall 0.500, Fisher exact
    one-sided p = 0.0498. Real, and void for transfer: those vectors do not
    describe hulls this `Hull` can build.

    NEW, on `a16/s0/n25` (`gate2u-a16-s0-n25-mesh.json`, mesh-only, rung 0,
    LAYER_BACKOFF=0, speed 2.57, scale 1.0, np=10): **TP 0, FP 0** — the
    screen returns no DANGEROUS verdict at all, so it catches neither rung-0
    refusal and raises no false alarm. RECALL IS ZERO AND IT IS PINNED AT
    ZERO. That is not a softened bar: nothing was moved to make this pass, and
    the one bar the 16-gene table refuted (`draft_over_hull_cell`) was demoted
    to a non-voting receipt rather than re-tuned. A future edit that quietly
    claims more must fail this test rather than be believed — which is the
    same reason the recall was pinned when it was 0.500.

    The precision is `nan` here (no positives), so it is deliberately NOT
    asserted: a precision computed on an empty denominator is the
    unmeasurable-value-scored-as-passing defect (docs/LESSONS.md class 1).
    """
    _bank, meshed, failed = labels
    tp = sum(reports[h].verdict is Verdict.DANGEROUS for h in failed)
    fp = sum(reports[h].verdict is Verdict.DANGEROUS for h in meshed)
    assert (tp, fp) == (0, 0), (
        f"the screen's 16-gene confusion table moved: TP {tp} FP {fp} over "
        f"{len(failed)} failures and {len(meshed)} successes. If this is a "
        f"real improvement, re-base the pinned numbers WITH the campaign that "
        f"measured it; if it is a bar that drifted, that is the regression "
        f"this test exists to catch")
    assert len(failed) >= 1, (
        "the bank records no mesh failure at rung 0, so 'the screen predicts "
        "neither refusal' is vacuous — re-state the claim against the bank "
        "that has one")


@_needs_calibration
def test_a_rung_0_refusal_is_ladder_rescuable_and_the_module_says_so(reports,
                                                                    labels):
    """THE FINDING THAT BOUNDS THIS WHOLE MODULE, pinned so it cannot be
    quietly dropped when someone wants a stronger claim.

    OLD (15-gene, `data/gate2u-campaign-backoff-mesh.json`, `--layer-backoff
    3`): hulls 0, 1, 5, 6 and 11 — every hull the screen refused — MESH once
    the prism-layer count steps down, at 8/7/8/8/7 layers with 0 zero-volume
    and 0 wrongly-oriented faces and skew 4.52/3.25/4.54/4.65/5.13, while hull
    4, which the ladder could not save, the screen called SAFE. Over hulls
    0-11 the rate went 3/12 at rung 0 to 11/12 with the ladder.

    WHY THAT ASSERTION COULD NOT SIMPLY BE RE-POINTED: on `a16/s0/n25` the
    screen refuses NOTHING at scale 1, so "every hull the screen refuses is
    rescuable" has no instances and asserting it would be vacuous. And the
    ledger's 16-gene corroboration (BLOCK 1: h011 and h012 clean at n=6, 13
    and 12 wrongly-oriented faces -> 0, skew 247.226 -> 3.497) was measured
    BEFORE the 161-station STL rebuild, so it does not reconcile with this
    tree: h012 now meshes clean at rung 0, and h011's rung-0 failure reads 26
    wrongly-oriented faces at skew 11.30, not 13 at 247.23.

    SO IT WAS RE-MEASURED, on this tree, this genome and this surface
    resolution (`data/gate2u-a16-s0-n25-backoff-mesh.json`, hulls 0-11 of the
    calibration population, `--layer-backoff 3`): **12 of 12 mesh**, against
    11 of 12 at rung 0. h011 goes derived n=7 FATAL -> rung 1, n=6 -> CLEAN
    (0 wrongly-oriented, 0 zero-volume, skew 2.980, 71.0% coverage) in two
    attempts, and the `stl_sha256` is IDENTICAL in the two banks — the
    outcome moved with the layer count and nothing else moved at all. That
    last check is the load-bearing one: without it "we re-generated the case
    and it worked" is compatible with having re-generated a different case.

    So DANGEROUS means "expect a refusal at the DERIVED layer count", and the
    module must not sell it as "unmeshable". A docstring is not usually
    load-bearing, but this one is the difference between a screen and a claim
    the data does not support (docs/LESSONS.md defect class 4), so it is
    asserted.
    """
    bank, _meshed, failed = labels
    for hid in failed:
        assert reports[hid].verdict is not Verdict.DANGEROUS, (
            f"hull {hid} is now refused by the screen — the 'no instances' "
            f"premise of this test has changed and the rescue claim can and "
            f"should be re-anchored on it directly")
    import navalai.admissibility as adm
    assert "back-off campaign" in adm.__doc__
    assert "not *\"this hull cannot be meshed\"*" in adm.__doc__ or \
        "cannot be meshed" in adm.__doc__
    assert "rung 0" in adm.screen.__doc__

    # THE RESCUE, from the campaign that measured it on these hulls.
    ladder = json.loads(adm.CALIBRATION_BACKOFF_BANK.read_text())
    assert ladder["population_manifest"] == bank["population_manifest"], (
        "the back-off bank measures a different population from the rung-0 "
        "bank, so the two cannot be compared hull for hull")
    rung0 = {r["hull"]: r for r in bank["rows"]}
    rescued = {r["hull"]: r for r in ladder["rows"]}
    covered = [h for h in failed if h in rescued]
    assert covered, (
        f"the back-off bank covers hulls {sorted(rescued)} and the rung-0 "
        f"refusals are {sorted(failed)} — no overlap, so nothing here "
        f"measures the rescue this module's bound rests on")
    for hid in covered:
        row = rescued[hid]
        assert row["meshed"], (
            f"hull {hid} fails checkMesh even WITH the ladder — 'DANGEROUS "
            f"means rung-0 refusal, not unmeshable' no longer holds and the "
            f"module docstring must be re-worded, not this assertion")
        assert row["stl_sha256"] == rung0[hid]["stl_sha256"], (
            f"hull {hid}'s geometry is not byte-identical between the two "
            f"banks, so the ladder is not the only thing that changed")
        assert row["n_layers_used"] < row["n_layers_derived"], (
            f"hull {hid} meshed at the DERIVED layer count in the back-off "
            f"run, so this row is not evidence about the ladder")


def test_the_manifold_the_grammar_emits_is_screened_and_mostly_admissible():
    """RE-PINNED 2026-08-18 with the re-derivation (was "a third
    inadmissible": 68 DANGEROUS / 79 MARGINAL / 53 SAFE on the 15-gene-era
    metrics, 17.0% of it the retired stale sheer formula firing on decks the
    rebuilt kernel delivers healthy).

    RE-MEASURED 2026-08-19 after the confusion-table re-base (the
    2026-08-18 row read 39 DANGEROUS / 86 MARGINAL / 75 SAFE with
    writer-admissible 189/200 — dominated by the draft bar the table then
    measured 0-for-4): now **0 DANGEROUS / 11 MARGINAL / 189 SAFE**,
    refused_by empty, writer-admissible **200/200** at scale 1. The
    DANGEROUS class has not vanished from the screen — it lives below the
    0.1-cell edge and at model scales (see the Gate 2D sliver test) —
    it has vanished from the FULL-SCALE grammar manifold, which is what
    the metal measured: 23/25 mesh at rung 0 and the 2 that do not are
    not screen-predictable.

    Bounds, not equality: `sample_valid` depends on `evaluate()`, which is
    not this module's to freeze.
    """
    X, _ = sample_valid(200, MissionSpec(), seed=1234)
    reps = [screen(x, SPEED, SCALE) for x in X]
    dangerous = sum(r.verdict is Verdict.DANGEROUS for r in reps)
    assert dangerous <= 10, (
        f"{dangerous} DANGEROUS at full scale — the re-based bars moved, "
        f"or the grammar started emitting sub-0.1-cell features")
    # the writer's denominator: most of what the grammar emits must keep a
    # deterministic CFD path, or the screen has become a second grammar
    admissible = sum(1 for r in reps if not r.refused_no_rescue)
    assert admissible >= 190, f"writer admits only {admissible}/200"


def test_screening_is_cheaper_than_meshing_by_four_orders_of_magnitude():
    """The whole point: ~8 ms against ~80 s of snappy per hull. A screen that
    is not cheap is a second mesher."""
    import time
    X, _ = sample_valid(20, MissionSpec(), seed=3)
    t0 = time.perf_counter()
    for x in X:
        screen(x, SPEED, SCALE)
    per = (time.perf_counter() - t0) / len(X)
    assert per < 0.10, f"{per * 1000:.1f} ms/hull"


def test_a_grammar_valid_hull_is_not_the_same_thing_as_a_meshable_one():
    """The claim the module exists to make, stated as an assertion: a hull
    `grammar.check()` blesses can still be refused here — the screen is a
    statement about a (hull, speed, SCALE) case, not about the genome.
    RE-BASED 2026-08-19: at full scale the re-based bars admit the whole
    seed-11 draw (measured — that is the confusion table's verdict, not a
    regression), so the demonstration lives where the physics puts it: at
    model scale the cell coarsens relative to the features and the SAME
    grammar-valid hulls go sub-0.1-cell, refused with no rescue."""
    X, _ = sample_valid(19, MissionSpec(), seed=0)
    assert all(grammar.check(x).ok for x in X)
    # hull 18's bottom panel measures 0.26 cells at scale 1 (metal-clean,
    # warn band) and 0.065 at scale 0.25 — below every measured-clean
    # anchor, refused with no rescue. Same genome, same grammar blessing.
    rep = screen(X[18], SPEED, 0.25)
    assert rep.verdict is Verdict.DANGEROUS
    assert rep.refused_no_rescue


def test_the_screen_guards_the_case_writer_C18(tmp_path, monkeypatch):
    """Forensics C-18, RE-SCOPED 2026-08-18 (docs/MESHABILITY_MATH.md): the
    writer refuses the hulls the layer ladder CANNOT rescue — sub-cell
    features and anything UNMEASURED (`Report.refused_no_rescue`) — and
    WRITES a rescuable-DANGEROUS hull with a warning, because run-case.sh's
    canonical backoff ladder is its measured deterministic recovery
    (metal-proven on case a: derived n=6 FATAL -> n=5 CLEAN, unattended).
    Refusing rescuable hulls at the writer was blocking hulls with a
    measured path; the phantom half of those refusals came from the retired
    stale sheer formula. Declared experiments still bypass with
    allow_dangerous_mesh=True, and every case records the verdict.

    RECALIBRATED 2026-08-20 — AND THE RECALIBRATION IS ITSELF A FINDING.
    This test used to hunt both fixtures out of `sample_valid(30, seed=0)` at
    the default scale and SKIPPED when it found neither: "seed-0/30 no longer
    holds both guard fixtures — recalibrate the fixture, do not delete the
    guard test". Doing as instructed, and measuring instead of guessing:

      * the UN-RESCUABLE fixture exists, one draw further out. No hull of
        `a16/s0/n25` is refused at scale 1.0, but hull 152 of the same
        DEVELOPMENT stream is (`SUB_CELL_HULL`; sheer ridge 0.0636 cells,
        bottom panel 0.0648, both under the 0.1-cell edge) — and the writer
        takes it, which the model-scale alternative does not (see
        `SUB_CELL_HULL`'s note on the `ZeroDivisionError` at scale <= 0.4).
      * the RESCUABLE-DANGEROUS fixture DOES NOT EXIST, and not by accident.
        After `draft_over_hull_cell` was demoted to a non-voting receipt on
        2026-08-19, the only ladder-rescuable metric that can still vote is
        `stack_over_min_radius`, whose bar is 1.0. MEASURED maxima: **0.150**
        over `a16/s0/n25`, **0.305** over `sample_valid(200, seed=0)`,
        **0.393** over `sample_valid(200, seed=1234)`, and **0.454** over the
        423 grammar-valid genomes in 6000 uniform draws from the raw
        `grammar.LOW/HIGH` box. It is also scale-INVARIANT (0.150 at every
        scale from 1.0 to 0.05), so no configuration reaches it either. The
        writer's "write it with a warning" branch is therefore unreachable
        from the grammar as it stands.

    A branch nothing can reach is still a branch that must not silently
    invert, so it is exercised with a REAL `Report` carrying a rescuable
    DANGEROUS metric, injected at the seam `case.py` imports. That is stated
    here rather than hidden: parts 1 and 3 run on verbatim geometry, part 2
    runs on a constructed verdict because the population cannot supply one.
    """
    import warnings as _warnings

    import pytest

    import navalai.admissibility as adm
    from navalai.admissibility import Basis, Metric, Report, Verdict, screen
    from navalai.cfd.case import write_resistance_case
    from navalai.evaluate import sample_valid
    from navalai.geometry import Hull
    from navalai.mission import MissionSpec

    X, _ = sample_valid(SUB_CELL_DRAW, MissionSpec(), seed=population.DEV_SEED)
    no_rescue = Hull(X[SUB_CELL_HULL])
    assert screen(no_rescue, SPEED, SCALE).refused_no_rescue, (
        f"hull {SUB_CELL_HULL} no longer trips a no-rescue bar — recalibrate "
        f"the fixture by searching the development stream, do not delete the "
        f"guard test")

    # THE ABSENCE IS ASSERTED, NOT ASSUMED. If the grammar or a bar ever moves
    # far enough to produce a real rescuable-DANGEROUS hull, this fails and
    # part 2 should be re-anchored on it instead of on the injected verdict.
    live = [i for i, x in enumerate(X)
            if screen(Hull(x), SPEED, SCALE).verdict is Verdict.DANGEROUS
            and not screen(Hull(x), SPEED, SCALE).refused_no_rescue]
    assert not live, (
        f"hulls {live} are now rescuable-DANGEROUS — the population CAN "
        f"supply the part-2 fixture; use it instead of the injected verdict")

    # 1. un-rescuable (sub-cell feature): REFUSED with the metric receipt
    with pytest.raises(ValueError, match="admissibility screen"):
        write_resistance_case(no_rescue, SPEED, tmp_path / "refused",
                              end_time=1.0, symmetric=True, n_layers=2)

    # 2. rescuable DANGEROUS: WRITES, warns, and records the prediction.
    # A real Report over a real Metric — the only fabricated thing is which
    # hull the screen says it about.
    def _rescuable_screen(hull, speed=SPEED, scale=SCALE):
        real = screen(hull, speed, scale)
        m = Metric.of("stack_over_min_radius", 1.7, "-", Basis.DERIVED,
                      "injected: the prism stack is taller than the radius it "
                      "bends around; the ladder walks it back under 1",
                      danger_above=1.0, ladder_rescuable=True)
        return Report(Verdict.DANGEROUS, real.metrics + (m,),
                      real.hull_cell_m, real.lwl_m, real.n_layers)

    monkeypatch.setattr(adm, "screen", _rescuable_screen)
    with _warnings.catch_warnings(record=True) as w:
        _warnings.simplefilter("always")
        write_resistance_case(Hull(X[0]), SPEED, tmp_path / "rescuable",
                              end_time=1.0, symmetric=True, n_layers=2)
    assert any("admissibility screen" in str(x.message) for x in w), (
        "the rung-0 prediction must be warned, not silent")
    info = (tmp_path / "rescuable" / "case.info").read_text()
    assert "admissibility_verdict=DANGEROUS" in info
    assert "admissibility_no_rescue=none" in info
    assert "stack_over_min_radius" in info
    monkeypatch.undo()

    # 3. the declared-experiment override still writes the un-rescuable one
    write_resistance_case(no_rescue, SPEED, tmp_path / "declared",
                          end_time=1.0, symmetric=True, n_layers=2,
                          allow_dangerous_mesh=True)
    info = (tmp_path / "declared" / "case.info").read_text()
    assert "admissibility_verdict=" in info
    assert "admissibility_no_rescue=" in info
    assert "admissibility_no_rescue=none" not in info
