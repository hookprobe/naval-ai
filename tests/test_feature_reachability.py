"""Gate REACHABILITY — which kernel features can the PRODUCTION search reach?

THE MEASURED INCIDENT (2026-09-01, the end-to-end integration audit). Four
kernel phases — the design waterline (Phase 3), the tunnel stern (Phase 4),
the split stern (Phase 4B) and the second chine (Phase 5) — were implemented,
unit-tested, gated and documented, and produced by NO production search path.

The audit measured every source a genome can come from:

  * `grammar.DRAW_LOW == DRAW_HIGH == 0` pins all thirteen genes in the frozen
    draw box, so `grammar.sample` and the default `sample_valid` never move
    them;
  * `grammar._explore_post_hoc_inplace` — the ONE stream that explores
    post-hoc genes, used by `ui/server.py::/generate` and `agents.py` — drew
    SEVEN of the twenty post-hoc genes and none of the thirteen;
  * `morphology_search._REPAIR` moves only `pmb` and `r_stem` of the post-hoc
    set;
  * the parent library (3 parents) carries non-zero values for
    beta_transom, beta_run, flare_bow, flare_len, r_stem, pmb, stem_depth and
    for none of the thirteen;
  * NSGA-II's polynomial mutation over `grammar.LOW/HIGH` is the only route
    left, and MEASURED on the server's live budget (pop 48, 15 gens, the
    16 x 4 m houseboat brief) the front carried tun_len 0, tun_crown 0,
    split_len 0, ch2_y 0, rho_len 0, dwl 0 — because every one of these
    features needs TWO OR THREE genes non-zero AT ONCE and mutation from an
    all-zero start does not deliver a coherent bundle.

  MEASURED on the live UI pool for that brief: dwl, tun_crown, split_w, ch2_y
  and rho_len were EXACTLY 0.000 in all 128 candidates.

This file holds the answer as a TESTED FACT rather than something a reader
has to re-derive from four modules, and it holds the REASON each unreachable
gene is unreachable — because "we did not get to it" and "we decided not to,
and here is the measurement" are different states and this repository's rule
is that they must not be collapsed (docs/LESSONS.md, "prose standing in for a
verdict").
"""

from __future__ import annotations

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import parse_mission

#: The genes the exploring stream draws BLIND on every candidate. READ from
#: the module, never restated: a set typed here would be a second copy of the
#: answer, and the first version of this file was wrong about `flare_bow`
#: (drawn from its FULL BOX, because it is signed) precisely that way.
BLIND = grammar.EXPLORE_BLIND_GENES

#: Drawn only when the mission asks for the architecture.
REQUESTED = frozenset({"tun_w", "tun_crown", "tun_len"})

#: Deliberately unreachable, each with the measurement behind the decision.
#: A gene here is a RECORDED REFUSAL, not an oversight.
WITHHELD = {
    "dwl": "blind nudging is a REFUTED move (morphology_search: 2/8 -> 0/8, "
           "12 of 18 losing walks ended at dwl = 0); the designed route is "
           "_derived_dwl",
    "cwp_x": "companion of dwl",
    "rb_transom": "companion of dwl",
    "rb_stem": "companion of dwl; rb_stem > 0 with r_stem = 0 commands a "
               "contradiction (Gate DELIVERED-FORM)",
    "split_w": "an architecture no mission field expresses yet",
    "split_len": "an architecture no mission field expresses yet",
    "ch2_z": "the knuckle wedge is not in the section solve's target",
    "ch2_y": "the knuckle wedge is not in the section solve's target: up to "
             "5.75% of a station's area at the gene ceiling "
             "(Gate DELIVERED-FORM)",
}


def test_every_post_hoc_gene_is_classified_exactly_once():
    """No gene may fall between the three states. This is the fence that
    makes the file a map rather than a snapshot: append a gene to
    `POST_HOC_DEFAULTS` and this fails until you say which state it is in."""
    post = set(grammar.POST_HOC_DEFAULTS)
    classified = BLIND | REQUESTED | set(WITHHELD)
    assert post == classified, (
        f"unclassified: {sorted(post - classified)}; "
        f"classified but not post-hoc: {sorted(classified - post)}")
    assert not (BLIND & REQUESTED) and not (BLIND & set(WITHHELD))
    assert not (REQUESTED & set(WITHHELD))


def test_the_blind_genes_actually_vary_in_a_production_draw():
    """A gene in BLIND that does not move is BLIND in name only."""
    m = parse_mission("14 m river cruiser, 6 knots, 5 tonne, category C")
    X, _y = sample_valid(24, m, seed=5, explore_post_hoc=True)
    X = np.asarray(X, float)
    for nm in sorted(BLIND):
        col = X[:, grammar.NAMES.index(nm)]
        assert float(col.max()) > 1e-6, (
            f"{nm} is classified as explored blind and is 0 in all 24 "
            f"candidates — the classification is wrong or the draw is")


def test_rho_x_reaches_production_and_the_sac_survives_it():
    """rho(x) is the gene this gate ADDED to the blind set, and it is safe to
    add precisely because its SAC contract is exact: a hull that softens its
    bilge toward the bow still delivers the commanded sectional area."""
    assert "rho_len" in BLIND and "rho_bow" in BLIND
    m = parse_mission("14 m river cruiser, 6 knots, 5 tonne, category C")
    X, _y = sample_valid(16, m, seed=11, explore_post_hoc=True)
    warped = 0
    for x in np.asarray(X, float):
        if x[grammar.NAMES.index("rho_len")] <= 1e-9:
            continue
        warped += 1
        h = Hull(x)
        rel = float(np.max(np.abs(h.sac_deviation())
                           / np.maximum(h.A_sac, 1e-9)))
        assert rel < 1e-9, f"rho(x) moved the delivered SAC by {rel:.3e}"
    assert warped >= 8, f"only {warped} of 16 candidates carry a bilge warp"


def test_a_mission_that_asks_for_a_protected_prop_gets_a_hull_that_has_one():
    """THE END-TO-END LINK, and the reason the tunnel is REQUESTED rather than
    blind. "protected prop" -> `parse_mission` sets drive "tunnel" ->
    `grammar.features_for` asks for the tunnel bundle -> the kernel DRAWS the
    notch -> `propulsion.credited_recess_m` reads it off the hull and the
    `prop_space` row is scored with a lever the boat actually has.

    Before this landed the chain broke in the middle: the mission asked for a
    protected prop, every candidate came out flat-bottomed, and the propulsion
    row credited a recess from the spec that no hull carried.
    """
    from navalai import propulsion

    m = parse_mission("16 m x 4 m houseboat with a protected prop, 5 knots, "
                      "6 tonne, category C")
    assert m.energy.drive == "tunnel"
    assert grammar.features_for(m) == frozenset({"tunnel"})
    X, _y = sample_valid(12, m, seed=5, explore_post_hoc=True)
    X = np.asarray(X, float)
    for nm in sorted(REQUESTED):
        col = X[:, grammar.NAMES.index(nm)]
        assert float(col.min()) > 0.0, (
            f"{nm} is zero on some candidate — a tunnel needs all three genes "
            f"at once, and a partial bundle is no tunnel at all")
    recess = [propulsion.drawn_tunnel_recess_m(Hull(x)) for x in X]
    assert min(recess) > 0.0, (
        f"the drawn tunnel does not reach the prop station: {recess}")


def test_a_mission_that_does_not_ask_gets_no_tunnel():
    """The other direction. An architecture drawn on a brief that did not ask
    for it is not exploration, it is noise — and it would put a notch in every
    hull the yard quotes."""
    m = parse_mission("16 m x 4 m houseboat, 5 knots, 6 tonne, category C")
    assert m.energy.drive != "tunnel"
    assert grammar.features_for(m) == frozenset()
    X, _y = sample_valid(12, m, seed=5, explore_post_hoc=True)
    for nm in sorted(REQUESTED):
        col = np.asarray(X, float)[:, grammar.NAMES.index(nm)]
        assert float(np.max(np.abs(col))) == 0.0, nm


def test_the_withheld_genes_stay_at_their_proven_no_op():
    """A withheld gene must be withheld from EVERY production draw, not just
    the one this file remembered to check."""
    for brief in ("16 m x 4 m houseboat with a protected prop, 5 knots",
                  "12 m river cruiser, 7 knots, 4 tonne, category C"):
        m = parse_mission(brief)
        X, _y = sample_valid(12, m, seed=3, explore_post_hoc=True)
        X = np.asarray(X, float)
        for nm, why in WITHHELD.items():
            col = X[:, grammar.NAMES.index(nm)]
            assert float(np.max(np.abs(col))) == 0.0, (
                f"{nm} was drawn on {brief!r}, and it is withheld because: "
                f"{why}")


def test_the_draw_box_still_pins_every_withheld_gene():
    """`DRAW_LOW == DRAW_HIGH == 0` is the second fence, and it must not be
    relaxed as a shortcut to reachability — the exploring stream is where a
    feature is switched on, deliberately and per mission."""
    for nm in WITHHELD:
        i = grammar.NAMES.index(nm)
        assert grammar.DRAW_LOW[i] == grammar.DRAW_HIGH[i] == 0.0, nm


def test_features_for_is_the_only_translation_of_a_mission_to_a_feature():
    """One home, so the sampler and any future caller cannot disagree about
    what "protected prop" means."""
    from navalai.energy import EnergySpec
    from navalai.mission import MissionSpec
    assert grammar.features_for(None) == frozenset()
    assert grammar.features_for(MissionSpec()) == frozenset()
    assert grammar.features_for(
        MissionSpec(energy=EnergySpec(drive="tunnel"))) == frozenset({"tunnel"})
    # a declared recess is also a request: it says the boat has a tunnel
    assert grammar.features_for(
        MissionSpec(energy=EnergySpec(drive="shaft",
                                      prop_tunnel_recess_m=0.2))
    ) == frozenset({"tunnel"})


def test_the_aft_prior_share_is_what_the_comment_claims():
    """A NUMBER IN A COMMENT CANNOT BE RECOMPUTED BY THE READER, and this one
    went stale one arity event after it was written.

    `AFT_EXPLORE_WEIGHT`'s comment read "at 8 aft genes of 34, uniform gives
    them 24% of picks and this gives 49%". That was correct at N_PARAMS 34 and
    `ch2_z`/`ch2_y` took the grammar to 36 the same week, so the shares became
    22.2% and 46.2% while the comment kept its old arithmetic. Same defect
    class as a bar written twice; this is the fence.
    """
    from navalai import morphology_search as ms

    uniform, weighted = ms.aft_prior_shares()
    assert uniform == pytest.approx(len(ms._AFT_GENES) / grammar.N_PARAMS)
    assert weighted > uniform, "a prior that does not bias is not a prior"
    assert weighted < 0.60, (
        f"the aft genes take {weighted:.1%} of the exploration; above ~60% "
        f"the prior has stopped ordering the search and started BEING the "
        f"search, which is the PRIOR != CONSTRAINT line this repository draws")
    # and every aft gene is a real gene of the current grammar
    for nm in ms._AFT_GENES:
        assert nm in grammar.NAMES, nm


def test_the_optimizer_can_draw_the_architecture_the_mission_declared():
    """THE SECOND PRODUCTION DESIGN ROUTE, and it was still blind.

    After `sample_valid` learned to draw a requested tunnel, the end-to-end
    flow trace showed `optimize.pareto_front` still could not: its
    `_DrawBoxSampling` draws the FROZEN LEGACY BOX through `grammar.sample`,
    in which every architecture gene is pinned at zero. MEASURED on
    "16 m x 4 m recreational houseboat with a protected prop": the front's
    chosen hull had tun_w = tun_crown = tun_len = 0 while `propulsion` was
    being asked to score its tunnel drive.

    This asserts the WIRING — that the initial population can express the
    architecture — and deliberately NOT that the front retains it. Whether a
    tunnel survives selection depends on whether it earns its place against
    the three objectives, and MEASURED on two briefs it does not: on both, a
    hull that satisfies `prop_space` by other means dominates. That is the
    search working, not a defect, and claiming otherwise would be reading a
    design preference as a bug.
    """
    from navalai.optimize import HullProblem, _DrawBoxSampling
    from navalai.geometry import Hull as _H  # noqa: F401

    m = parse_mission("16 m x 4 m houseboat with a protected prop, 5 knots, "
                      "6 tonne, category C")
    prob = HullProblem(m)
    X = _DrawBoxSampling()._do(
        prob, 24, random_state=np.random.default_rng(3))
    # THE CRITERION IS THE DRAWN CROWN AT THE PROP STATION, not "the genes
    # are non-zero". The shape-repair climb's blind branch can pick any gene
    # in the genome, so a tunnel gene wanders off zero on missions that never
    # asked — MEASURED at tun_crown 0.021 / tun_len 0.031 with tun_w 0.000,
    # which is not a weak tunnel, it is no tunnel. What `propulsion` reads,
    # and therefore what counts as a tunnel existing, is the crown the hull
    # actually carries where the disc sits.
    from navalai import propulsion

    def _drawn(rows):
        out = []
        for r in rows:
            try:
                out.append(propulsion.drawn_tunnel_recess_m(
                    Hull(np.asarray(r, float))))
            except Exception:                              # noqa: BLE001
                out.append(0.0)
        return np.asarray(out, float)

    seeded = _drawn(X) > 1e-4
    assert seeded.any(), (
        "no member of the initial population carries the tunnel the mission "
        "declared — the optimizer cannot express the architecture it is being "
        "asked to design")
    assert seeded.sum() < len(X), (
        "EVERY member carries a tunnel. Seeding all of them returned an EMPTY "
        "front (measured): a tunnelled hull loses about a third of its "
        "flotation solutions, so the population must keep an un-tunnelled "
        "half to search from — the same split the shape-feasible climb makes")
    # a brief that does NOT ask gets no tunnel anywhere in its population
    m0 = parse_mission("16 m x 4 m houseboat, 5 knots, 6 tonne, category C")
    X0 = _DrawBoxSampling()._do(
        HullProblem(m0), 24, random_state=np.random.default_rng(3))
    assert not (_drawn(X0) > 1e-4).any()


def test_the_tunnel_bundle_is_calibrated_against_flotation():
    """The bundle's crown range is MEASURED, not chosen.

    The crown is a fraction of the LOCAL DRAFT and these hulls float at ~57%
    of their design draft, so a tall crown lands near the floated waterline
    and `solve_to_displacement` stops converging. MEASURED on 120 legacy draws
    under the 16 x 4 m / 6 t brief:

        tun_crown   0.05  0.10  0.15  0.20  0.25  0.30  0.40
        non-conv     30    39    49    56    62    64    72   of 120
        (legacy draw, no tunnel: 0 of 120)

    `tun_w` costs nothing measurable across 0.10..0.60 (39-40 of 120), so the
    width is set by what a propeller needs and the CROWN is what is bought
    carefully.
    """
    lo, span = grammar._EXPLORE_FEATURE_BUNDLES["tunnel"]["tun_crown"]
    assert lo >= 0.05 and lo + span <= 0.25, (
        f"tun_crown drawn over [{lo}, {lo + span}] — above ~0.25 more than "
        f"half the population loses its flotation solution, and a bundle that "
        f"makes the hull unfloatable is not exploration")
    for nm in ("tun_w", "tun_crown", "tun_len"):
        f, sp = grammar._EXPLORE_FEATURE_BUNDLES["tunnel"][nm]
        assert f > 0.0, (
            f"{nm} has a floor of 0 — a bundle that can draw a zero is a "
            f"bundle that can draw NO tunnel while claiming to draw one")
