"""The gate ladder, one command: python3 -m navalai.gates

Prints the honest status of every phase gate. GREEN gates are enforced by the
pytest suites (this runner re-executes them); METAL-GATED entries name exactly
what hardware/software the remaining evidence needs — never faked green.

WHY THIS FILE LOOKS THE WAY IT DOES (audit 2026-08-05/06)
---------------------------------------------------------
A red-team pass demonstrated, with working proofs, that a measured RED gate
could be erased by editing ONE PROSE STRING:

    "RED (measured): C_t -15.4% vs EFD"     -> exit 1   (correct)
    "AMBER (measured): C_t -15.4% vs EFD"   -> exit 0
    "METAL-GATED: C_t -15.4% vs EFD"        -> exit 0
    blocked=None                            -> exit 0
    (delete the row entirely)               -> exit 0

because the failure test was `str(blocked).upper().startswith("RED")`. Nothing
pinned the GATES list, so a row could also just vanish. A status that is
free text is not a verdict; it is a suggestion.

Three changes follow from that:

1. STATUS IS A TYPED ENUM, not a string that happens to start with "RED".
   `Verdict.RED` cannot be renamed into passing.
2. EVERY RED GATE MUST APPEAR IN A COMMITTED LEDGER (`data/gate-ledger.json`)
   with a measured watermark, an owner, and a review-by date. This is what
   restores CI as a REGRESSION signal: the question stops being "is anything
   red?" (a constant, since 2M and 2U are honestly red) and becomes "is
   anything red that we did not already record, or REDDER than we recorded?"
   Nothing is softened — the red rows still print, first, every run.
3. A SUITE THAT STOPS RUNNING IS A FAILURE, not a comfortable green. pytest
   exits 0 when every test skips, and `xfail` produced a GREEN row with no
   annotation at all because "xfailed" matched none of the alternations in
   the old summary parser.

The `review_by` date is the anti-wallpaper clause: an expected-red gate cannot
quietly become permanent furniture. It forces a re-measurement or an explicit,
dated, owner-signed extension — PLM.md section 3 step 6 ("regression gates keep
them honest forever") applied to the reds themselves.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = _ROOT / "data" / "gate-ledger.json"


class Verdict:
    """Typed statuses for gates with no pytest suite.

    Deliberately not free text. RED means "ran and missed its bar"; METAL and
    REVIEW mean "honestly unverifiable here", which is a different claim and
    must never be reachable by editing a RED row's wording.

    METAL and REVIEW are currently UNUSED, and that is not an oversight to be
    tidied away. They describe a gate with NO SUITE that no machine here can
    verify. Every gate that reads like one — 2M needs an OpenFOAM node, 6R
    needs a qualified reviewer — is instead a typed RED with a ledger entry,
    which is the STRONGER claim: it carries a measured watermark, an owner and
    a review_by date, where METAL carries only a sentence. Reclassifying either
    of them as METAL would remove the number and the deadline, so it is a
    softening wearing a taxonomy's clothes. For a gate that DOES have a suite
    and needs software this node lacks, the mechanism is `Requirement` below —
    METAL's per-suite analogue, which keeps the suite running wherever the
    software IS present.
    """

    RED = "RED"          # ran, missed its bar, kept red
    METAL = "METAL"      # needs hardware/software this machine lacks
    REVIEW = "REVIEW"    # needs a qualified human


@dataclass(frozen=True)
class Requirement:
    """An environment fact a suite needs, NAMED, REASONED and PROBEABLE.

    MOTIVATING INCIDENT (CI run 31611386179, commit 0798182). The `--strict`
    tier — "a suite that ran NOTHING is a failure, not a comfortable green" —
    could never pass on a GitHub runner, because two gates skip there for
    reasons no runner can fix:

        Gate 2B  needs the Blender binary; no hosted runner has one.
        Gate 2G  needs data/benchmark_geom/kcs.stl, which is gitignored and
                 whose SOURCE is a registration-walled workshop bundle that
                 scripts/fetch_benchmark_geom.py deliberately refuses to
                 re-host ("IT DOES NOT DOWNLOAD ANYTHING, AND THAT IS NOT AN
                 OVERSIGHT").

    An always-red check is the very defect .github/workflows/gates.yml was
    written to remove: it cannot distinguish "2B still cannot run here" from
    "Gate 3 just broke". But the answer is NOT a flag that ignores skips,
    because a skip nobody wrote down is the defect, not the skip.

    So a skip is EXPECTED only where the gate declares, in committed code,
    WHAT it needs and WHY this environment may lack it — and the declaration
    is not taken on trust. `probe()` is run, and the three outcomes are
    different verdicts:

        requirement ABSENT   -> the skip is expected; --strict does not fail
        requirement PRESENT  -> the suite COULD have run and did not: FAILURE,
                                with or without --strict. This is the clause
                                that stops the declaration becoming a blanket
                                excuse, and it is the surviving rule.
        probe RAISES         -> FAILURE. An unmeasurable prerequisite is not a
                                satisfied one (docs/LESSONS.md defect class 1:
                                `${_MQ_SKEW:-0}` scored a metric it could not
                                read as perfect).

    `why` is prose and is NEVER load-bearing — the verdict comes from `probe`.
    """

    what: str                      # the thing, named: "the Blender binary"
    why: str                       # why an environment may honestly lack it
    probe: Callable[[], bool]      # is it present HERE? may raise; may not lie

    def present(self) -> bool:
        return bool(self.probe())


def _blender_binary_present() -> bool:
    """Probes exactly what tests/test_blender_hull.py's skipif probes.

    Imported rather than reimplemented: `have_blender` checks the FILE and
    never `shutil.which`, and that distinction is itself a measured lesson
    (an empty PATH once read as "Blender is not installed" while 5.2.0 LTS
    sat in /Applications).
    """
    from navalai.blender.run import have_blender
    return have_blender()


_KCS_GEOM = _ROOT / "data" / "benchmark_geom" / "kcs.stl"


def _kcs_geometry_present() -> bool:
    """The artefact tests/test_benchmark_geom.py skips on.

    This states the path a second time, deliberately and safely: a
    disagreement between this probe and that suite's `_KCS` cannot hide. If
    the probe pointed at something that exists while the suite skipped, the
    row reads "the suite COULD have run and did not" and FAILS. The one
    direction that goes quiet — probe wrong about an absent file while the
    suite runs — leaves the gate GREEN on a suite that actually executed,
    which is not a claim anybody loses by.
    """
    return _KCS_GEOM.exists()


@dataclass(frozen=True)
class Gate:
    name: str
    scope: str
    suite: str | None = None      # pytest file, or None for a status row
    status: str | None = None     # a Verdict, required when suite is None
    detail: str = ""              # human context; NEVER load-bearing
    requires: Requirement | None = None   # declared, probed prerequisite

    def __post_init__(self) -> None:
        if (self.suite is None) == (self.status is None):
            raise ValueError(
                f"{self.name}: exactly one of suite/status must be set — a row "
                f"with neither is a gate that verifies nothing while looking "
                f"like a gate")
        if self.status is not None and self.status not in vars(Verdict).values():
            raise ValueError(f"{self.name}: {self.status!r} is not a Verdict")
        if self.requires is not None and self.suite is None:
            raise ValueError(
                f"{self.name}: `requires` explains why a SUITE skipped, so it "
                f"is meaningless on a status row — a status row runs nothing "
                f"by construction and would be excused for free")


GATES = [
    # The row that judges the rows. It was deliberately NOT registered when it
    # was written — "the gate checking the gates is not itself a gate" — which
    # was backwards: it is the one whose disappearance would be least noticed.
    # THE SHAPE GATES. Added 2026-08-23 after this ladder certified a hull that
    # was, in the STL, a rectangular plank: displacement, Cp, Cb, LCB, GM,
    # freeboard, scantlings, all eight constraint rows, seven of seven rule
    # findings and the arrangement gate all passed, and no gate read SHAPE.
    # A numerically valid object is not necessarily a valid boat hull.
    # THE PADDLE-BOAT GATE. houseboat19 passed every row this runner had and
    # the owner refused it on sight — the stern offered a 0.26 m disc to a
    # thrust wanting 0.42 m, and no gate could say so. The owner then made
    # the scope a product definition ("naval-ai only designs boats with
    # motors"), so the drive is a design-stage quantity with its own gate.
    Gate("Gate PROP", "propulsion integration: motor power and prop space "
         "are constraint rows; transom Froude, bilge-keel span and pitch "
         "entry are measured reports", "tests/test_propulsion.py"),
    Gate("Gate MORPH", "morphological plausibility: a hull must LOOK like a "
         "boat, judged on descriptors measured against 58 published hulls "
         "(89-92% of L0-valid generated hulls fail; 0 of 58 real ones do)",
         suite="tests/test_morphology.py"),
    # THE FISHING-BOAT GATE. The owner, 2026-08-25: "naval-ai currently
    # fails to design boats and succeeds at designing fishing boats" — and
    # the protocol that followed demanded reconstruction of known hulls
    # from the reference corpus be PROVEN before novel generation is
    # trusted. data/hull_kb.json is the extracted-feature record of
    # downloads/hull-examples; the suite pins the measured reconstructions
    # (cruiser entry <=12 deg with a clean critique; the 24-deg warped
    # deadrise law; the one-body-to-two topology under the 10-deg
    # divergence bar) so a grammar change that silently breaks a proven
    # reconstruction fails loudly.
    Gate("Gate HULL-KB", "the reference corpus is learned and reconstruction "
         "is proven: KB citations resolve, and the measured cruiser / "
         "warped-V / split-topology reconstructions stand",
         suite="tests/test_hull_kb.py"),
    # THE HELD BARGE, landed 2026-08-26 with the recalibration event it
    # waited for (r_transom -> 0.92, Cp -> 0.95): the 16 x 4 m houseboat
    # carries 88% of its beam and 59.4 m2 of deck where the spearhead
    # carried 39% and 43.6 m2 — and the DRAW box still holds the
    # historical ceilings, so no recorded population moved.
    Gate("Gate BARGE", "a houseboat is a rectangle: the widened envelope "
         "draws it, the frozen DRAW box protects history, and the pointed "
         "bow stays reachable", suite="tests/test_barge_bow.py"),
    # Phase 3 slice 1, 2026-08-27: the design waterline B(x) — the second
    # of the three coupled curves, closed-form (the joint solve's f^2 term
    # vanishes by the fillet identity), bit-identical at dwl = 0, and
    # measured to take the proven barge from critic +4.26 to +0.06 under
    # the GENERAL bar. The single-panel-topside limitation is a recorded
    # sentinel, to be inverted when the waterline knuckle lands.
    # Phase 4A, 2026-08-27: houseboat17's W-stern in-genome — the tunnel
    # notch as three no-op genes, the SAC delivered NET of it in closed
    # form, the crown-submerged rule refusing what vessel_terms cannot
    # model, and the sections carrying the W the hydrostatics integrate.
    # Phase 4B, 2026-08-28: the split stern — the waterplane hole is the
    # DESIGN, so the hydrostatics integrate it (awp/ixx/lcf/I_L on the
    # reduced strip) instead of refusing; the kernel piece the
    # recorded-OPEN hookprobe 70-80% split was waiting for.
    # The owner's CFD-distillation directive (2026-08-28): the campaigns'
    # measured behaviour, harvested into a committed book before any purge
    # can lose it (gap N6), consumed with surrogate-honesty refusals.
    # CFD-audit P1, 2026-08-28: the cheap questions asked before the
    # expensive ones — theory, then the book, then a solve — plus the two
    # free checks the project had the inputs for and never ran (Kelvin
    # wavelength; A/B mesh-match against the family scatter).
    Gate("Gate PREFLIGHT", "before a solve is bought: theory answers what "
         "it can, a surface already solved is recognised, the family band "
         "speaks, an impulsive start above the measured Fn ceiling is "
         "refused — and after it, Kelvin validates and an A/B is only "
         "attributable when the meshes match",
         suite="tests/test_preflight.py"),
    # The end-to-end integration audit (2026-09-01). Two seams the suite was
    # fully green across: the descriptor layer measuring a hull the ladder
    # does not float, and four kernel phases no production search could
    # reach. Both are SEAM gates — they assert that two subsystems agree
    # about one hull, which is exactly the class of defect a per-module
    # suite cannot see.
    Gate("Gate DELIVERED-FORM", "form_coefficients measures the surface the "
         "ladder floats — notch, hole and knuckle chain included; no feature "
         "reports an impossible Cm; the delivered SAC is the commanded SAC "
         "for every feature that folds its area into the solve, and the two "
         "that do not DECLARE their drift",
         suite="tests/test_delivered_form.py"),
    # THE SEARCH BESIDE THE RATCHET (2026-09-01). Nineteen seam defects were
    # found against a 2094-green suite because a test pins a known answer and
    # nothing swept a PROPERTY across a seam. `scripts/gap_sweep.py` does
    # that; this row makes it run on every push, with the ledger's own rule —
    # a declared finding is recorded with its number, a new one fails.
    Gate("Gate SWEEP", "seam properties swept over the production flow: "
         "descriptors vs ladder, the SAC contract, declared-vs-drawn levers, "
         "cache identity, gene reachability, repair-vs-constraint, exception "
         "containment, receipts, numbers declared twice, the two design "
         "routes, and station convergence",
         suite="tests/test_gap_sweep.py"),
    Gate("Gate REACHABILITY", "every post-hoc gene is classified BLIND, "
         "REQUESTED or WITHHELD-with-a-measurement; a mission that asks for "
         "a protected prop gets a hull that draws the tunnel, one that does "
         "not gets none, and the aft prior's share is recomputed rather than "
         "remembered",
         suite="tests/test_feature_reachability.py"),
    Gate("Gate CFD-KB", "the CFD anchor book: every record honest about "
         "settledness and GCI, unsettled records never support a "
         "prediction, family bands refuse outside measured Fn support, "
         "and the hb19 L1 anchor carries its sigma and basis",
         suite="tests/test_cfd_kb.py"),
    # Phase 3's named remainder, 2026-08-28: rho(x). The corpus holds
    # round_bilge and hard_chine as separate FAMILIES because a hull that
    # transitions was not expressible — one global rho, stem to stern.
    Gate("Gate RHO-X", "the bilge radius varies along the length: the warp "
         "is the flare law's shape, rho_len = 0 is bit-identical legacy, "
         "the control points and the area coefficients are per-station, "
         "and a hull may be hard aft and round forward",
         suite="tests/test_rho_x.py"),
    Gate("Gate SPLIT", "the split stern: split genes are no-ops at zero, "
         "the SAC stays the net contract, the wall is vertical at "
         "y_split, the waterplane integrals subtract the hole, and split "
         "+ tunnel on one station is refused by name",
         suite="tests/test_split.py"),
    Gate("Gate TUNNEL", "the W-stern: tunnel genes are no-ops at zero, the "
         "SAC stays the net displacement contract to the bit, a crown "
         "above the waterline is refused by name, and the wetted surface "
         "counts the tunnel walls", suite="tests/test_tunnel.py"),
    Gate("Gate DWL", "the design waterline: dwl = 0 is bit-identical "
         "legacy, the SAC stays the displacement contract at every dwl, "
         "the barge passes the general critic, and the requested-vs-"
         "achieved gap is a receipt (Hull.dwl_deviation)",
         suite="tests/test_dwl.py"),
    # P5, 2026-08-27: with a corpus of TENS of hulls, retrieval + parent
    # distortion is the honest seeding mechanism and a learned generator is
    # not (research matrix, docs/audit/HULL-DESIGN-AUDIT.md). The suite
    # re-proves every parent on every run — a decayed parent would seed
    # every family search with a refused shape — and fences the barge
    # family bar that keeps P2-A's family routing satisfiable.
    Gate("Gate PARENTS", "the parent library is proven and the distortion "
         "operators deliver: parents pass their family critic, Lackenby "
         "clips into the deliverable band, rescale stays homothetic, and "
         "family missions seed the optimizer without touching recorded "
         "streams", suite="tests/test_parents.py"),
    Gate("Gate HB16", "the 16 m liveaboard probe's refusals stay refusals: "
         "3 t is refused naming the family, and the motor-power fix the "
         "old sentinel demanded stays landed",
         suite="tests/test_houseboat_16m.py"),
    # LEVEL L4 OF THE VALIDITY LADDER, previously unenforced: every
    # recorded shape incident (plank, spearhead, paddle boat) was found
    # by a human opening a file downstream of every gate.
    Gate("Gate G-VISUAL", "the canonical views ship with every deliverable "
         "and a refused shape is SEEN: fixed cameras, descriptor sheet "
         "beside the pictures, written on refused hulls too",
         suite="tests/test_views.py"),
    # THE PRODUCT'S FRONT DOOR, which had no gate and no tests at all until
    # 2026-09-02. `docs/PRODUCTION_CORE.md` lists design_report.py as core,
    # "the CLI face"; nothing in tests/ imported it. That is precisely how
    # `--reference` came to be declared, documented in --help, and NEVER
    # READ, while `--mission` certified the REFERENCE HULL under a header
    # naming the user's brief -- a 2643 kg hull and a VERDICT: REFUSE for a
    # 1.8 t plywood launch, none of it about the boat that was asked for.
    Gate("Gate CLI", "the CLI face DESIGNS for a brief rather than grading "
         "the reference hull under its name, says which of the front's "
         "designs it is reporting and why, and refuses an impossible brief "
         "with the rows that refused it instead of a plausible boat",
         suite="tests/test_design_report_cli.py"),
    Gate("Gate UI-SEED", "the studio's default genome BUILDS before it is "
         "served, and a refused mesh is PAINTED in the viewport rather than "
         "leaving a blank stage with the reason in the response body",
         suite="tests/test_ui_seed_builds.py"),
    Gate("Gate 0G", "the ladder cannot be talked into passing",
         "tests/test_gate_integrity.py"),
    # Gate 0G's sibling, split out for the reason Gate 1H was: the ladder should
    # show WHICH clause is covered by what. 0G guards the STATUS machinery (a
    # verdict cannot be reworded, a row cannot vanish, a skipped suite is not
    # green). This one guards the boundary between the registry and the ledger:
    # a bar that a green suite MISSES must be a typed RED row with a ledger
    # watermark, never a sentence in a `scope`. Gate 4 carried its miss in prose
    # for a day and nothing could have failed on it (gap D11).
    Gate("Gate 0R", "a missed clause is RED BY RECORD, never prose in a scope",
         "tests/test_red_by_record.py"),
    # THE GENERATOR COULD NOT AIM, AND THIS ROW IS WHAT PROVES IT NOW CAN.
    # MEASURED before the kernel rebuild, over 200 `sample_valid` draws: the
    # three quantities a naval architect DESIGNS were all emergent outputs of
    # fifteen unrelated shape knobs —
    #
    #     Cp      0.386 .. 0.832    18.0% inside the 0.55-0.62 band
    #     LCB   -10.02 .. +13.88    46.5% inside +-3 %LWL
    #     alpha_e 10.6 .. 60.5 deg  1 of 74 inside 7-12 deg
    #
    # A designer CHOOSES Cp for the design Froude number and CHOOSES LCB for
    # balance, then finds a surface satisfying them. The old kernel sampled
    # knobs and reported what fell out, which is the whole explanation for
    # hulls that looked arbitrary: they were. The sectional area curve and the
    # design waterline are now the design curves and Cp/lcb are GENES; measured
    # after, on the same 200 draws, Cp lands within +-0.01 of its target on
    # 96.5% and LCB within +-0.3 %LWL on 100.0%.
    #
    # The section is also no longer three points, which is what made every hull
    # a hard chine BY CONSTRUCTION and made surface fairness identically zero.
    Gate("Gate 0K", "geometry kernel: SAC/DWL design curves + N-point section",
         "tests/test_geometry_kernel.py"),
    # NINE STAGES, AND NOTHING HAD EVER ASSERTED THAT TWO OF THEM AGREE. Every
    # other gate tests ONE stage; this one tests the HANDOFFS, and the audit
    # that produced it (docs/research/FLOW-AUDIT.md) found the class of defect
    # that only a handoff test can see:
    #
    #   * the exported STEP solid was never compared to the displacement the
    #     ladder validated — the geometry rebuild made that a -99.994% error
    #     with a receipt that scored the sliver against the sliver and printed
    #     ~0%, because both sides read the section through the same broken index
    #   * `resistance.py` reads `hull.x[-1]`, the DESIGN length, while
    #     `hs.lwl_eff` — the FLOATED length gap E7 already fixed — sits in the
    #     same object: worst -15.0% on length, +2.575% on total resistance
    #   * one geometry LAW, five independent DISCRETISATIONS; the L2 BEM panel
    #     mesh solves a body 1.98% smaller than the mass it is handed
    #
    # Its bars are MEASURED, not chosen, and each names the defect it refuses.
    Gate("Gate 1E", "the stages agree with each other: one geometry, one "
         "resistance, one ply, tier+sigma across every handoff",
         "tests/test_end_to_end_flow.py"),
    # Before designing a hull the system should know what hull forms EXIST and
    # what makes each efficient. It knew two typologies. `formlib` is that
    # memory, as committed data with a provenance on every band — and the
    # judgement that matters is which families are NOT candidates for a
    # solar-electric displacement catamaran at Fn 0.2-0.3, since a library
    # implying all forty are options sends the optimiser hunting in the wrong
    # space.
    Gate("Gate 0F", "the hull-form library: bands ordered, every band carries "
         "its basis, no family contradicts its own Froude regime",
         "tests/test_formlib.py"),
    # MEASURED 2026-08-13, and the row exists because the suite settled two
    # questions this project had been answering from intuition. (1) "Sharper
    # bow = better" is FALSE: R_t span over each lever's full gene range is
    # Cp 26.35% / lcb 16.86% / bow shape 1.36% at Fn 0.45 — volume
    # distribution dominates bow shape by 19.4x, and at Fn >= 0.40 the
    # SHARPEST bow is measurably worse than mid-range. (2) The catamaran
    # interference phase is k0.sec^2(theta).sin(theta) — sec SQUARED — verified
    # against an independent complex superposition at 0.0 relative difference,
    # where the plausible-but-wrong sec^1 form differs by 3.99.
    Gate("Gate 0X", "the experiment suite: controlled sweeps hold their "
         "controlled quantities, out-of-envelope points are refused, and the "
         "Michell interference phase matches an independent superposition",
         "tests/test_experiments.py"),
    # MEASURED 2026-08-14. The parallel-axis term takes the reference hull from
    # GM 0.6688 m to 54.39 m at s/L 0.60 — 121x the category-C floor — while
    # `total_resistance` had never once passed `separation` to `michell_rw`, so
    # every catamaran this project ever evaluated was scored as one isolated
    # demihull. The dangerous half is the FIRST number, not the second: a
    # catamaran clears a monohull GM floor trivially and remains capsizable,
    # because its righting moment peaks when the windward hull lifts and it is
    # then STABLE INVERTED. So this row also fences the refusal — a multihull
    # gets no safety verdict from a criterion that does not govern it.
    Gate("Gate 1M", "the vessel: topology/manning/regime, the parallel-axis "
         "I_T, separation in the PRODUCTION wave term, and no multihull safety "
         "verdict from a monohull GM floor", "tests/test_multihull.py"),
    # MEASURED 2026-08-14: `grammar.check` refused this project's OWN target —
    # a 12.0 x 0.8 m catamaran demihull — on three clauses at once
    # (`bound[BWL] 0.8 outside [1.2, 6.0]`, `L/B 15.00 outside [2.2, 8.5]`,
    # `B/T 1.33 outside [1.8, 12.0]`). Every one is a CORRECT MONOHULL BAND
    # applied to an object that is not a monohull. The fix conditions the bands
    # on topology rather than loosening them: the same dimensions as a MONOHULL
    # are still refused, and the demihull's draft is still refused because
    # B/T 1.33 sits below the sourced series floor — out of EVIDENCE, not out
    # of physics, and the message says so.
    Gate("Gate PV-B", "vessel-conditional proportion bands, the sourced size "
         "box, and the multihull stability refusal",
         "tests/test_vessel_bands.py"),
    # MEASURED 2026-08-14, and it OVERTURNED THE RECOMMENDATION THIS PROJECT
    # WAS ABOUT TO ACT ON. A four-paper read named area-averaged Gaussian
    # curvature the single most adoptable manufacturing metric available.
    # Experiment 5 measured it over ten candidate objectives on 898 feasible
    # hulls and it is the WORST column: it scores the inflated hull 2.9x better
    # while that hull costs 3.35x the plywood (34 -> 114 counted sheets) and
    # +28.7% Wh/NM. Adopted as advised it would have been the most inflating
    # term in the vector.
    #
    # The mechanism generalises past that one metric, and it is the point of
    # this row: the partition is NOT between good and bad denominators, it is
    # between RATIOS and ABSOLUTES. C_T normalised by WETTED AREA -- the fix the
    # literature's own diagnosis implies -- still picks the same inflated hull
    # (2.318e-3 against 3.075e-3, a 25% "better" coefficient on a boat burning
    # 28.7% more energy per mile), because the optimiser inflates the
    # DENOMINATOR. Changing what you divide by does not fix it. Dividing at all
    # is the defect. So buildability is priced in absolute m^2, never in a
    # ratio, and this row fences that.
    Gate("Gate 0B", "buildability metrics are PROXIES that refuse rather than "
         "default, are grid-converged by a measured residual, and price "
         "manufacturing in ABSOLUTE m^2 — never in a ratio an optimiser can "
         "inflate", "tests/test_buildability.py"),
    Gate("Gate 0", "grammar/geometry/DB", "tests/test_phase0.py"),
    # Gate 0 asks the kernel about hulls the kernel invented -- `vector(named(x))`
    # on a sampled genome is self-consistency, and a wrong kernel is
    # self-consistent too. E5 is the row that hands it a hull somebody else
    # drew, in a towing tank, and asks it to come back. It reads committed
    # offset tables, so it needs neither OpenCASCADE nor the 16 MB geometry
    # release to run.
    Gate("Gate 0E5", "the geometry kernel against REAL PUBLISHED hulls: "
         "offsets from three independent source families round-trip through "
         "the genome, and the SHAPE residual is reported, not just the six "
         "scalars", "tests/test_e5_real_hulls.py"),
    # E5's sibling, and separate on purpose. E5 is green over published
    # ROUND-BILGE families; this one asks the question the product actually
    # depends on, because a plywood boat is hard-chine by construction and a
    # chine is a slope discontinuity that no integral in E5 can see. It is
    # RED, with the reason recorded as three measured numbers.
    Gate("Gate 0E5C", "the hard-chine EVIDENCE: published hard-chine geometry "
         "is acquired, is PUBLISHED_PARAMETRIC rather than traced off a "
         "drawing, carries a real chine, and every refusal is recorded with "
         "its reason", "tests/test_e5_hard_chine.py"),
    # THE CAPABILITY CLAUSE IS NOT IN THAT SUITE, and this is Gate 4F's shape
    # exactly: the suite above PASSES — the evidence really was acquired and
    # really is recorded honestly — while the thing the product needs is
    # MISSED. Splitting them is what stops a green suite being quoted as a
    # capability. See data/gate-ledger.json and docs/gates/E5-CHINE.md.
    Gate("Gate 0E5C-CAP", "the hard-chine CAPABILITY: 2 of 7 published series "
         "are expressible. No parallel middle body (Cp ceiling 0.848 against "
         "a real 0.95-0.97), no aft deadrise warp (beta_len <= 0.60, so "
         "warped series miss by 8-9 deg), beta_mid capped at 25 deg",
         status=Verdict.RED),
    Gate("Gate 1", "L1 physics + Wigley anchor + <50ms", "tests/test_phase1.py"),
    # Gate 1's own bar names Holtrop-Mennen, and `grep -rin holtrop` used to hit
    # the plan document and nothing else while Gate 1 printed GREEN. Split out
    # rather than folded into Gate 1 so the ladder shows WHICH clause is
    # covered by what.
    Gate("Gate 1H", "Holtrop-Mennen vs the 1982 worked example",
         "tests/test_holtrop.py"),
    # Split out from Gate 1 for the same reason as Gate 1H: the ladder should
    # show WHICH clause is covered by what. This one owns the "never map
    # undefined onto ideal" family — a non-finite constraint that read as
    # feasible, trim/heel returning their BEST possible value where the
    # equilibrium stopped existing, an inert constraint, an order guard that
    # `python -O` deletes, and two proportions nobody re-checked on the hull
    # that actually floated.
    Gate("Gate 1C", "the constraint vector: complete, ordered, finite, and no "
         "undefined state reported as ideal", "tests/test_constraints_honest.py"),
    # Registered on the suite's behalf, and the scope is its own header line
    # rather than a guess: file ownership put navalai/gates.py with a different
    # agent than tests/test_gapfix_physics.py, and an unregistered suite makes
    # Gate 0G RED for a reason that has nothing to do with the code under test.
    # The register already recorded this coordination cost once, for Gate SR.
    Gate("Gate 1P", "the L1 physics core says what it actually computed",
         "tests/test_gapfix_physics.py"),
    Gate("Gate 1b", "NSGA-II Pareto front", "tests/test_optimize.py"),
    Gate("Gate 2", "Capytaine BEM (Hulme anchor)", "tests/test_phase2.py"),
    Gate("Gate 2R", "CFD reference parity + GCI honesty",
         "tests/test_cfd_reference_parity.py"),
    # Split out from Gate 2R for the reason Gate 1H and Gate 1C were: the
    # ladder should show WHICH clause is covered by what, and this one is not a
    # parity clause — it is a CAPABILITY clause. MEASURED 2026-08-13:
    # `grep -c "surfaceFieldValue\|hull_bow\|bowSlam" navalai/cfd/case.py`
    # returned 0, so P_slam had no instrument at L3 and no closed form at L0.
    # It was unmeasurABLE, which is a different and worse state than unmeasured,
    # and a gate row is what makes its disappearance visible.
    Gate("Gate 2P", "slamming pressure is measurable: a bow patch that "
         "partitions the hull, a function object that refuses to point at "
         "nothing, and a Wagner C_p guarded at both limits",
         "tests/test_slamming.py"),
    # Scope re-read against the suite 2026-08-06. It is no longer "Forrester +
    # an L1 GP": test_phase3.py also holds OOD refusal that separates error
    # rather than merely flagging it, the KOH rho estimator and its degeneracy
    # warnings, and the batched-EI diversity filter measured in the CANDIDATE
    # box. A scope line that names half a suite is a registry that under-reports
    # what would be lost if the suite stopped running.
    # The held-out ERROR BAR lives IN this suite again: Gate 3E was retired
    # 2026-08-18 per its own clearing contract ("delete it the moment the bar
    # is MET") — measured 0.1471 (2026-08-13, the improvement's authoring
    # measurement) then 0.1323 across seeds (2026-08-18, fortress001, at the
    # audit base AND at HEAD). test_phase3's across-seed test now ASSERTS the
    # bar and re-opens the row with a dated measurement if it is ever missed
    # again; the retirement history is in that test's docstring.
    Gate("Gate 3", "surrogate spine: GP + co-kriging rho, OOD refusal, "
         "batched-EI infill + the held-out across-seed error bar",
         "tests/test_phase3.py"),
    # The feasibility clause is NOT here. It is Gate 4F, below, because a
    # shortfall stated in this row's `scope` was prose — see that row.
    Gate("Gate 4", "generative + slider p95<100ms (raw feasibility: Gate 4F)",
         "tests/test_phase4.py"),
    # THE BUILDER-FACING SURFACE HAD NO GATE, AND `test_every_test_file_is_
    # owned_by_a_gate` caught it the moment the suite landed — which is the
    # fence working exactly as intended. Gate 4 owns the LATENCY clause of the
    # interactive surface (`p95 < 100 ms` per widget) and keeps it; this row
    # owns the HONESTY clauses of the mapping layer in `ui/api.py`, which are
    # a different question and would have been invisible inside Gate 4's
    # scope: every payload declares its own `source`; a NaN is a refusal and
    # never reaches the wire; an absence is declared in exactly ONE place and
    # is SERVED rather than typed into the markup; the route verdict reads the
    # refold TREND and not one station count (PU-4); KG is measured from the
    # keel plane and not from the waterline (measured wrong at -0.02 m while
    # the endpoint was being wired); a speed past Fn 0.45 is REFUSED by name
    # rather than extrapolated; and no gate verdict is claimed by a page that
    # ran no suite.
    Gate("Gate 4U", "the builder surface's honesty contract: every payload "
         "declares its source, no NaN on the wire, one home per absence, the "
         "kit/mould route reads the refold TREND, KG from the keel plane, "
         "Fn > 0.45 refused by name, and no gate verdict without a suite run",
         "tests/test_ui_surface.py"),
    Gate("Gate 5", "mission translation + LLM seam", "tests/test_phase5.py"),
    Gate("Gate 6", "rules-as-code mechanics", "tests/test_phase6.py"),
    # Re-read against the suite 2026-08-06. Gate 7 has TWO clauses and the row
    # named neither: the frozen suite is no longer the training draw, the mark
    # is a monotone high-water ratchet, the wall clock (clause 2) is measured
    # and gated, and a MISSING baseline now refuses instead of passing — the
    # last of which is only meaningful because `data/baselines.json` is
    # committed (gap D3; `scripts/make_baseline.py` regenerates it).
    Gate("Gate 7", "flywheel: frozen suite != training draw, monotone "
         "regression mark, wall clock, committed baseline",
         "tests/test_phase7.py"),
    Gate("Gate B", "grammar AST + bend radius + 8-D genome", "tests/test_stageB.py"),
    Gate("Gate C", "agentic PLM network + engineer + STEP/IGES",
         "tests/test_stageC.py"),
    Gate("Gate D", "waves/RAO response + dynamics + CFD post", "tests/test_stageD.py"),
    Gate("Gate E", "latent-space evolution + latent GP", "tests/test_stageE.py"),
    Gate("Gate F", "panel unroll/DXF + Pareto dash + handoff receipt",
         "tests/test_stageF.py"),
    # Carried over from the APSE line when the four parallel branches were
    # consolidated onto master. APSE is the fidelity/similitude work: scale is
    # not a cost variable, fidelity is, and it is measured.
    Gate("Gate G", "APSE: similitude/ITTC-78/cost/planner/evidence",
         "tests/test_stageG.py"),
    # CFD knowledge audit R2 + handoff item 4 (2026-08-28). The hookprobe
    # ladder read three aft-edit improvements out of 3034 -> 2998 -> 2966 N;
    # each step is 1.1-1.2% against a 2.5% window scatter, and v2 carries 19%
    # more cells than v3. Separately, v2/v3 read 42.14 vs 34.28 m2 wetted for
    # the SAME hull (20 096 vs 152 126 facets), so every Ct in the book sits
    # on a denominator that moved 23%. The kernel therefore compares NEWTONS
    # at equal speed, through one sanctioned comparator, and this row is the
    # fence.
    # PHASE 5 / BUILD-PLAN PV-4. `docs/audit/geometry-representation.md` read
    # "multi-chine NO" and the consequence was measured as a capability gap:
    # the grammar reached TWO of the five standard body plans and the two it
    # missed are the double-chine forms. The topside is now a KNUCKLE LIST
    # rather than a hand-written special case per breakpoint -- k = 0 recovers
    # the legacy clip and k = 1 the Phase-3 waterline knuckle, expression for
    # expression, which is why the pre-Phase-5 fences still hold at exactly
    # 0.0 instead of at a tolerance.
    Gate("Gate MULTI-CHINE", "the topside is a knuckle list: a second chine "
                             "is an exact vertex, and k=0/1 are unchanged",
         "tests/test_multichine.py"),
    Gate("Gate CFD-CMP", "CFD comparisons are in newtons, above the scatter, "
                         "on matched meshes -- or refused",
         "tests/test_cfd_compare.py"),
    # BuildPlan 2 V2.1 -- the arrangement grammar and its algebraic gate. The
    # suite found FIVE defects in a module that had never been executed, the
    # worst of which let the reference layout PASS L0-A while the saloon stood
    # 435 mm through each side of the coachroof: the envelope-Y rule checked
    # the box FLOOR only, on a docstring argument ("half-breadth is
    # non-decreasing upward") that is true of a hull and stops being true the
    # moment a trunk is added.
    Gate("Gate V2.1", "arrangement grammar: envelope, spaces, deck zones, and "
         "an L0-A that names the space it refuses", "tests/test_arrangement.py"),
    # BuildPlan 3 V3.0 -- the governance kernel. Its load-bearing clause is the
    # structural one: delete the constitution and every physics result must be
    # bit-identical, proved against a saboteur policy that perturbs gm_m by a
    # tenth of a part per billion and must be CAUGHT.
    Gate("Gate V3.0", "governance compiles to a parameter box and to constraint "
         "rows, ratchets only tighter, and the ladder never imports it",
         "tests/test_policy.py"),
    # Gate 0G reported tests/test_gapfix_product.py as owned by NO gate while
    # the tests inside it -- the proofs for register rows G7 (ES-TRIN) and G8
    # (the ISO 12217-1 scope guard) -- were FAILING. An unowned suite is outside
    # the ladder, so its failures reddened nothing, and reconcile_gaps.py still
    # reported both rows CLOSED because it measures that the symbol EXISTS
    # rather than that the proof PASSES. Three honesty mechanisms, one blind
    # spot. Registered here so the ladder carries it.
    Gate("Gate 6P", "the product surface: scope guards refuse what does not "
         "govern, and the mission contract binds", "tests/test_gapfix_product.py"),
    Gate("Gate L", "one limit, one home; scantling derived from the rule",
         "tests/test_limits_single_source.py"),
    # Gate L's own fence had gap J1's shape. Its scan required `"=" in
    # stripped`, so it only ever inspected ASSIGNMENTS: contract.py carried
    # `Re {speed_ms * lwl_m / 1.09e-6:.3g}` in an f-string for the entire life
    # of that line, with "1.09e-6" on the hunted list, and Gate L was green
    # throughout. Dropping the "=" was a string-level patch to a structural
    # problem, so the scan is now AST-level (`navalai/constpolicy.py`) and
    # this row is the proof that it CATEGORISES rather than bans: it fires on
    # a crafted constant in seventeen syntactic positions and stays silent on
    # 2, 0.5, 100.0 and 1000.0, which are mathematics and units.
    Gate("Gate L2", "numeric literals are categorised, not banned: an AST "
         "fence that catches a physical constant in any expression position",
         "tests/test_constpolicy.py"),
    # Split out of Gate 6, which tested the RULES mechanics only. The
    # manufacturing back end is the other half of the plan's Phase 6 and it
    # was the half with no bar it could fail: no nesting, no BOM, no refold
    # test, and a developability metric that passes a hyperbolic paraboloid.
    # The row already existed; the scope now names the export receipt too,
    # which is a third of what the suite asserts (`export_dxf` nests rather
    # than stacks, a ladder-failing design is REFUSED an export, and STEP/IGES
    # loft the validated discretisation instead of a hard-coded 12 stations).
    # "developability controls" is plural on purpose: the suite carries the
    # POSITIVE controls (cylinder, cone) and the NEGATIVE one (hypar) — a
    # metric with no negative control is not a metric.
    #
    # THE REFOLD CLAUSE IS NO LONGER HERE. It is Gate 6D, below, because this
    # suite PASSES while the clause is MISSED — Gate 4F's shape exactly.
    Gate("Gate 6M", "manufacturing back end: nesting, BOM, developability "
         "controls, export receipt (refold onto the hull: Gate 6D)",
         "tests/test_manufacturing.py"),
    Gate("Gate R3", "the ladder is climbable: L2 escalation, monotone tier "
         "promotion, honest refusal of L3", "tests/test_ladder.py"),
    # THE SPINE. Gap register section A is one finding restated seven ways: the
    # ladder is not a ladder, and nothing in the product could report a design
    # that entered a stage and never came back (`Evaluation.tier` read "L1" in
    # 100% of ~2000 evaluations). `navalai/pipeline.py` is the object that can,
    # and this row is what makes its central invariant a gate rather than a
    # docstring: every genome ends in EXACTLY ONE terminal state.
    #
    # The suite also owns the "unmeasured is never a pass" rule at the Python
    # level. It is the same rule `run-case.sh` learned on 2026-08-06 when
    # `${_MQ_SKEW:-0}` scored an unreadable skewness as perfect and a mesh at
    # 42.94 reached a 10-rank solve; the three checkMesh bars are READ out of
    # that script rather than restated, and one test doctors a copy of it to
    # prove the verdict follows the file.
    Gate("Gate S", "the MDO spine: one terminal state per genome, append-only "
         "archive, legal-transition graph, unmeasured metric refused",
         "tests/test_pipeline.py"),
    # The register was a document, so nothing could be assigned, nothing had a
    # state, and nothing noticed when a row went stale — section J's own
    # diagnosis, applied to section J's own file. This row guards the live
    # queue: the forward-only lifecycle, the append-only log, and the import
    # that turns docs/GAP-REGISTER.md's 119 findings into work items without
    # editing the audit record it reads.
    Gate("Gate SG", "the gap queue: findings are work items, not prose",
         "tests/test_gaps.py"),
    # A1/A2. `revalidate()` raised TierRequiresOperator UNCONDITIONALLY at L3
    # while its own docstring promised "the result then enters the ladder
    # through the provenance DB as an L3 row" — and nothing read that row. L3
    # is now READ from a recorded campaign and never solved; tier R alone can
    # refuse a design. MEASURED: nine of the ten case directories here lack
    # `domain_length_m` and are refused rather than defaulted.
    Gate("Gate R4", "the ladder is WIRED: every claimed tier reachable from "
         "evaluate(), L3 read from recorded evidence and never solved, tier R "
         "alone can refuse a design",
         "tests/test_ladder_wiring.py"),
    # The queue imported 119 findings ALL marked OPEN — the register document's
    # state, not the codebase's. ~45 were closed by commits nobody told it
    # about. This row guards the reconciliation being a REPEATABLE predicate
    # over the code rather than a one-off edit, and that a gap whose predicate
    # cannot be written reports NEEDS-HUMAN instead of being guessed closed.
    Gate("Gate SR", "gap state is derived from the code, not from prose",
         "tests/test_reconcile_gaps.py"),
    # R5.1. gate2m and post_gci disagreed on the cell count for r (checkMesh
    # with fallback vs cells_bg only) and on what "settled" means (last-fifth
    # by sample vs tail-fraction by time), so one triplet could yield two GCIs.
    # MEASURED 2026-08-06: drift on the TOTAL is dominated by the stable
    # viscous part, so gate2m called runs/beach settled at 0.70 flow-throughs
    # on 3.3% drift while its pressure component swung 1.80x-4.64x.
    Gate("Gate 2S", "one settled_drag: one cell-count rule, one settledness "
         "rule, and a component that oscillates cannot hide under a stable "
         "total", "tests/test_settled_drag.py"),
    # A4. Honesty rule 2 says a surrogate refuses OOD queries; `is_ood()` had
    # two call sites and BOTH WERE TESTS, so in production it extrapolated
    # silently.
    Gate("Gate 4H", "the surrogate refuses what it has not seen, and the "
         "feasibility bar measures the model rather than the sampler",
         "tests/test_surrogate_honesty.py"),
    # R5.5. The pressure component oscillates 0.27x-5.92x its expected value
    # with a domain-scale period while viscous holds at 1.22-1.36x ITTC-57.
    # This row guards the DIAGNOSTIC: a force history too short to resolve a
    # period must REFUSE to report one rather than return a noisy number.
    # RENAMED 2026-08-07: this row landed as a second "Gate 2R", colliding with
    # the CFD reference-parity row above. A gate NAME is the ledger's key —
    # `judge_red`, the stale-entry check and Gate 0G's `reds == ledger` all
    # index by it — and two rows sharing one collapse to a single set member, so
    # a ledger entry could account for a red that was never measured. The suite
    # named no gate in its own docstring, so nothing else moved. Uniqueness is
    # now asserted by tests/test_red_by_record.py rather than left to review.
    Gate("Gate 2T", "tank resonance is diagnosed, and a period is never "
         "claimed from too few cycles", "tests/test_tank_resonance.py"),
    # BuildPlan 2 V2.0. Its bar is provenance, not physics: "constants
    # importable, every one carries source+basis, no bare numbers".
    Gate("Gate V2.0", "refdata spine: every constant carries source + basis",
         "tests/test_refdata.py"),
    # Gap J5. This row exists to make a SKIP LOUD. The KCS geometry is
    # gitignored, so five tests skipped invisibly on every machine but the one
    # that generated the file — a pytest skip is not visible in the gate table,
    # and the table is the project's front door.
    # A GRAMMAR-VALID HULL IS NOT A CFD-MESHABLE ONE, and until 2026-08-11
    # nothing in the ladder said so. Gate 2U's campaign measured 5 clean of 18
    # at the derived layer count; the admissibility screen refuses the subset
    # it can name a mechanism for (precision 1.000, recall 0.500, Fisher
    # p=0.0498 at N=18) and is DIAGNOSTIC — it may never narrow Gate 2U-A's
    # denominator, which is the gaming signature the split exists to expose.
    Gate("Gate 2A", "CFD-admissibility screen: a grammar-valid hull is not a "
         "CFD-meshable one", "tests/test_admissibility.py"),
    # The 2026-08-18 meshability-math re-derivation (docs/MESHABILITY_MATH.md):
    # the admissible design space, ATTACKED. Every deliberately pathological
    # hull must be refused BEFORE OpenFOAM by the NAMED gate — L0 for what the
    # section law cannot deliver (sac.target, section.solve, chine.submerged,
    # panel.twist), the screen's un-rescuable set for what the cell cannot
    # represent (sub-cell features; the writer refuses on it) — and the §17
    # property funnel pins attribution + cost (10k uniform genomes MEASURED:
    # L0 admits 6.75% at 4-6 ms/genome; writer admits 92.7% of L0-passers;
    # 19.5 ms/genome end to end, seed 42, 2026-08-18).
    Gate("Gate 2D", "the admissible design space refuses pathological hulls "
         "before OpenFOAM, by the named gate, at milliseconds per genome",
         "tests/test_admissible_space.py"),
    # The 10 -> 7 cap shipped with NO test; `grep _MAX_LAYERS tests/` was empty,
    # so the value that fixed Gate 2U could have been argued back to 10 the way
    # it got there. Gate 2L pins it to its measurement and refuses the cap-3
    # trap (clean because the stack is empty).
    Gate("Gate 2L", "the prism-layer cap is a measured value, and a clean mesh "
         "with no boundary layer is not a pass", "tests/test_layer_cap.py"),
    # Registered on the suite's behalf (file ownership put navalai/gates.py with
    # a different agent), and it exists because "the STLs are bad" was the third
    # mechanism proposed for Gate 2U's failures and the third to be REFUTED by
    # its own data: best-of-37 metrics under a 20000-draw family-wise
    # permutation scored fw p 0.207 / 0.279 / 0.437 across three labellings,
    # against 0.21 on 29 geometry metrics and 0.24 on 48 third-party ones.
    # Two things the study measured that were being ASSUMED, which is why the
    # suite is worth keeping after a negative result: `stl_watertight_report`
    # cannot see a self-intersection BY CONSTRUCTION (two overlapping tetrahedra
    # in one solid pass it), and the surface handed to snappy is 600x120 =
    # 288956 triangles, not the 5244 the 80x16 default suggests.
    Gate("Gate 2F", "STL forensics: watertight is not valid, and the surface "
         "handed to snappy is measured rather than assumed",
         "tests/test_stl_forensics.py"),
    # Gate 2B is a NEGATIVE RESULT kept as a fence, which is the only reason it
    # is a gate at all: nothing in `navalai/blender/` is in the ladder, in
    # `pipeline.py` or in the case writer, and `docs/research/BLENDER.md`
    # records that Blender-native generation is NOT closer to the analytic hull
    # than the current path.
    #
    # It is registered because the refuted proposal is cheap to re-propose. A
    # voxel Remesh at 0.05 m — 50 mm on an 8.9-12.3 m hull — looks like a
    # tidy-up and MEASURED 2026-08-12 it takes the chine dihedral 5 mm off the
    # knuckle from 53.5 / 69.4 / 72.0 deg to 0.0 / 0.0 / 0.0 on hulls 4/8/14,
    # i.e. deletes the feature commit bbf1a47 had just made exact to 1e-9 m,
    # while every x/L bin's deviation from the analytic surface rises from a
    # 0.01-3.03 mm band to 22.2-57.6 mm and `surfaceFeatureExtract` at the
    # pipeline's own `includedAngle 150` goes from 6-7 feature points and 0
    # internal edges to 489-524 and 123-156. The suite feeds that VERBATIM
    # configuration to the guard, so a change that made it safe would have to
    # re-measure rather than inherit the refusal.
    #
    # The suite SKIPS where the Blender binary is absent (fortress001 has no
    # /Applications). A skip is not a pass and the document, not the suite,
    # is the home of the numbers. That skip is now DECLARED rather than merely
    # tolerated (see Requirement): where Blender IS present and the suite still
    # runs nothing, the row fails.
    #
    # This row deliberately stays a SUITE and does not become Verdict.METAL.
    # METAL runs nothing anywhere; this suite runs on the Mac simulation node,
    # where it is the fence that makes the voxel-remesh refutation
    # re-measurable rather than inherited. Converting a gate that DOES execute
    # somewhere into one that executes nowhere would trade a real fence for a
    # tidier table.
    Gate("Gate 2B", "Blender-native hull generation, measured and REFUSED on "
         "the hull path: a 0.05 m voxel remesh destroys the chine",
         "tests/test_blender_hull.py",
         requires=Requirement(
             what="the Blender binary",
             why="Blender is the Mac simulation node's tool and is not "
                 "installable on a hosted CI runner in any form this project "
                 "uses (the package deliberately does not `import bpy`); "
                 "fortress001 has no /Applications either. "
                 "docs/research/BLENDER.md carries the measurements.",
             probe=_blender_binary_present)),
    # Gate 2U is an EXPECTED RED with no suite, so nothing tested the campaign
    # runner that produces its number — and `classify()` mislabelled the
    # mechanism twice, in opposite directions, on rows the ledger then quoted.
    # MEASURED: two LTS DIVERGENCES (hulls 2 and 19) read `solver-stopped-short`
    # because the `min_deltaT` guard is dead code under LTS, and hull 5 read
    # `mesh-build-failed` while its solver ran 2000 iterations to completion.
    # The rate is one number; the TAXONOMY is what sends the next session to
    # snappy or to the solver, and it was sending them to the wrong one.
    Gate("Gate 2C", "the campaign classifier names the mechanism that actually "
         "failed, and refuses one it cannot measure",
         "tests/test_campaign_classifier.py"),
    # The ladder's stage-2 fortress half (BUILD-PLAN 11.8). The smoke parser
    # and run-case.sh's live-abort awk read the SAME log line against the
    # SAME bar, and the fence test quotes the shell source so the two can
    # never drift apart — a cheap-stage verdict that disagrees with the
    # runner's own abort would poison every campaign row it touches.
    Gate("Gate 2K", "the smoke verdict is the runner's own bar, an absent or "
         "truncated log is never promoted, and a smoke refusal can never "
         "read as a solve failure", "tests/test_smoke_verdict.py"),
    # A solver that exits 0 has not thereby produced physics. Until
    # 2026-08-20 nothing checked the SIGN or MAGNITUDE of an extracted
    # force: every C_T was produced through abs(), which also made
    # pipeline.check_cfd's `ct <= 0` refusal unreachable, so a sign-flipped
    # thrust could mint an L3 "measured" badge. This row owns the bars that
    # close it — including the reader, where a NaN row did not merely drop
    # but parsed as EXACTLY ZERO.
    # ONE deterministic path, ONE receipt. The pieces all existed and
    # nothing composed them, so every caller re-derived Fn, Re, the regime
    # and the model's validity for itself. This row owns the composition —
    # above all that the four questions stay FOUR verdicts.
    # The resistance tier's own suite. Registered when the file appeared
    # under a bit-exactness brief: the Michell integral is ~50% of what
    # `evaluate()` still costs, and any speed work on it must reproduce the
    # SAME accumulation order — a 1e-16 difference here moves pinned
    # numbers downstream.
    Gate("Gate RT", "the resistance tier: its envelope, and bit-exact "
         "values under any optimisation of the Michell integral",
         "tests/test_resistance.py"),
    # The two machines were MEASURED not to agree bitwise (one ulp on a
    # geometry fence; stl_sha256 non-portable). Comparing exactly cries
    # wolf; reading the other machine's prose produced the 2026-08-20 P0
    # incident. This row owns the tool that does neither.
    Gate("Gate XP", "cross-machine parity: platform-class differences are "
         "distinguished from code-class ones, and a verdict is never "
         "excused by a tolerance", "tests/test_parity.py"),
    # Gate XP's sibling, and the same lesson one level up. XP guards the
    # NUMBERS two machines produce; this guards the STANDING of the words
    # attached to them. `test_contract.py` already enforces that every
    # prescribed number opens with DERIVED / EMPIRICAL / RECEIPT ONLY /
    # INPUT — and nothing enforced what the sentence AFTER the label says,
    # so `"RECEIPT ONLY: measured on 4 points"` could become `"RECEIPT
    # ONLY: scale helps BECAUSE ..."` in one edit with every existing check
    # still green. MEASURED 2026-08-20: 17 basis strings, one causal hit,
    # and it is pinned with its scope rather than exempted. The motivating
    # case is the mesh-scale crossover — REAL as an observation (6/6 out of
    # sample, d92d548) and refuted twice as a mechanism (57da605 by
    # counterexample; permutation at family-wise p = 0.700) — whose
    # refutation lived only in commit messages and a rolling log until
    # 635eb07, i.e. in exactly the channels the next session reads past.
    Gate("Gate EP", "evidence promotion: a RECEIPT ONLY or EMPIRICAL basis "
         "may never be reworded into a mechanism, the crossover is never "
         "cited without its standing, and the refutation record cannot thin "
         "out", "tests/test_evidence_promotion.py"),
    Gate("Gate HC", "the hull evaluation contract: four separate verdicts, "
         "a regime, a derived mesh+solver prescription and its cost, in one "
         "receipt that never reads OK without evidence",
         "tests/test_contract.py"),
    # M6 (2026-08-20). A ">= 95% unattended" claim is a claim about a
    # POPULATION, and MEASURED that day every Gate 2U bank recorded seed 0
    # while the 15-gene and 16-gene banks shared ZERO hulls — the same seed
    # naming two disjoint populations, and the larger one no longer
    # regenerable by this tree. This gate keeps the three splits apart and
    # makes "never tuned against" checkable instead of promised.
    Gate("Gate 2Y", "population identity: (arity, seed) not seed alone, an "
         "undeclared seed is UNKNOWN and never silently development, and NO "
         "committed artifact may draw from the validation or held-out seed",
         "tests/test_population_split.py"),
    Gate("Gate 2N", "physics sanity: a force must have the right sign, a "
         "finite magnitude, and a defensible ratio to the cheap model — and "
         "an unreadable history is never a result",
         "tests/test_physics_sanity.py"),
    # The case writer's physics floors, wired at the one seam both entry
    # points pass: the wave-resolution bar and the Reynolds regime gate
    # existed as constants for weeks and were called by nothing.
    Gate("Gate 2W", "the case writer consults the physics floors it was "
         "given: cells-per-wavelength and the Reynolds regime decide before "
         "a mesh is sized", "tests/test_case_wiring.py"),
    # MEASURED 2026-08-28: a 24 s Fn 0.95 solve produced a drag number for a
    # tank 0.78 of one wavelength long, and case.info printed
    # domain_length_m=53.19 beside wavelength_m=67.82 without comparing them.
    # The DEPTH had scaled with the wave since it was written; the LENGTH had
    # not. This row owns the x-axis half of the deep-water discipline.
    Gate("Gate 2E", "the tank contains the ship's OWN wave: the domain length "
         "scales with 2*pi*U^2/g, not with hull length alone, and the design "
         "point is left bit-identical", "tests/test_domain_wavelength.py"),
    # h011/h012 meshed-and-failed deterministically in two independent
    # campaigns while the screen called them SAFE. This row owns whatever
    # invariant that investigation PROVED.
    # INVESTIGATED 2026-08-20 AND THE ANSWER WAS NO: h011/h012's geometry is
    # valid by construction by every test this repo can run (section solve
    # feasible with margin, no edge crossings, z-monotone sections, 0 folded
    # or inward quads, watertight, 0 self-intersections), and an 83-descriptor
    # separation scan scored with the repo's own permutation instrument
    # returns best family-wise p = 0.601. The best candidate criterion beat
    # the shipped screen on raw counts and was REFUSED anyway, because its
    # threshold was h011's own value to four decimals. This row owns what was
    # PROVED, including the refusal to invent a boundary.
    Gate("Gate 2X", "h011/h012: the geometry is provably clean, and no "
         "measured descriptor separates the failures from the passers — a "
         "criterion that does not separate is not a criterion",
         "tests/test_h011_h012_invariant.py"),
    # The repair literature's whole taxonomy, implemented on the IMPORT
    # boundary only. MEASURED 2026-08-12: our own surfaces are already clean by
    # every classical metric (0 degenerate, 0 slivers, 0 zero-length edges,
    # 0 boundary edges, 0 winding conflicts, min area 7.24e-06 m^2 over 288890
    # triangles), so a MeshFix-style pass would find nothing and would COST the
    # chine row bbf1a47 put on the grid to 1e-9 m — Blender's voxel remesh was
    # measured taking that chine from 72.0 deg to 0.0.
    #
    # So the gate's load-bearing clause is the REFUSAL: a defect in a generated
    # hull is a bug in Hull.closed_mesh, and healing it would make the bug
    # survive as a warning. Only winding is auto-repaired, because relabelling
    # triangles does not move a vertex; holes and true self-intersections are
    # REPORTED, because closing them retriangulates and a repair that silently
    # changes the shape is a different boat.
    Gate("Gate 2H", "surface repair on the import boundary, and generated "
         "geometry refused rather than healed", "tests/test_mesh_repair.py"),
    # The skip is DECLARED, not excused. `scripts/fetch_benchmark_geom.py` is
    # the committed recipe, and running it in CI was the obvious fix and is not
    # available: the script's own docstring says "IT DOES NOT DOWNLOAD
    # ANYTHING, AND THAT IS NOT AN OVERSIGHT" — the Tokyo-2015 bundle sits
    # behind a registration the script cannot honestly complete on a user's
    # behalf, and re-hosting the geometry is what its terms may forbid. So no
    # hosted runner can obtain kcs.stl, and the honest statement is that fact,
    # probed. Where the STL IS present and this suite still runs nothing, the
    # row fails — which is the case CLAUDE.md's "loudly, by design" was about.
    Gate("Gate 2G", "KCS benchmark geometry: present and accepted "
         "(scripts/fetch_benchmark_geom.py)", "tests/test_benchmark_geom.py",
         requires=Requirement(
             what="data/benchmark_geom/kcs.stl",
             why="gitignored by workshop terms, and its SOURCE IGES is behind "
                 "a registration wall that scripts/fetch_benchmark_geom.py "
                 "refuses to work around, so no hosted runner can produce it. "
                 "Restore it locally with "
                 "`python scripts/fetch_benchmark_geom.py --iges <KCS.igs>`.",
             probe=_kcs_geometry_present)),
    # Gap D8, AND THE PARITY HALF IS NOW CARRIED HERE TOO (2026-08-20).
    # There used to be a SECOND row, a typed-RED `Gate 6R` status gate with a
    # ledger entry, because is_complete() required a DATED edition per
    # standard and none was recorded. MEASURED 2026-08-20 both are:
    #   ISO 12217-1 -> "ISO 12217-1:2015 (Third edition, 2015-10-15)"
    #   ISO 12215-5 -> "ISO 12215-5:2008(E), First edition, 2008-04
    #                   (withdrawn; replaced by 2019 — do not mix editions)"
    # while the ledger watermark still read "0 editions recorded, of 2
    # required". The work was done and the gate stayed red because nobody
    # promoted it; a stale RED is as dishonest as a soft GREEN, and
    # tests/test_phase6r.py was asking for the flip in its own assertion.
    #
    # The status row is DELETED rather than turned green, because there is no
    # GREEN verdict and there should not be: `Verdict` exists for gates with
    # NO suite, and a gate is green by having a PASSING SUITE. This file
    # already owns that suite, so a second row on it would be the
    # declared-twice defect. Its ledger entry is deleted in the same commit.
    #
    # STILL NOT CLAIMED: this is threshold parity against a DATED text, not
    # VERDICT parity, and 12215-5:2008(E) is WITHDRAWN — the record says so.
    # Gap D9 stays open.
    Gate("Gate 6R", "review-record mechanics, basis routing, AND edition "
         "parity: both implemented standards name the dated edition held",
         "tests/test_phase6r.py"),
    # 2026-08-14 directive: "add regression tests so future architecture
    # changes cannot make the generated forms progressively less boat-like
    # while all software tests remain green." Six deterministic vessel cases
    # (navalai/formcheck.py CASES), descriptors read off the kernel's own
    # arrays, sourced-range verdicts, and a ratcheted baseline
    # (tests/formcheck_baseline.json) that a form shift trips with a
    # re-baseline instruction instead of drifting silently.
    Gate("Gate PF", "physical form regression: six deterministic hulls stay "
         "boat-like (descriptors, SAC shape, sourced bands, ratchet)",
         "tests/test_physical_form.py"),
    # Consolidation directive §19/§20: the same deterministic vessels
    # (formcheck.CASES — ONE fixture set), judged end to end through the
    # ladder and the CFD manifest; every cell PASS or EXPLICITLY
    # UNSUPPORTED, trimaran refused by name, and the historical 12x0.8 m
    # demihull judged differently under its two roles.
    Gate("Gate VM", "vessel matrix: five vessel classes end-to-end "
         "(ladder + manifest), refusals explicit, roles judged apart",
         "tests/test_vessel_matrix.py"),
    # The pre-CFD screening engine (2026-08-14 directive): classify
    # ACCEPT/MARGINAL/REFUSE + CFD-worthiness from cheap physics only —
    # receipts on every figure, validity-banded speed curves, loading
    # matrix, regime refusals by name. Invariant tests, not float pins.
    Gate("Gate DC", "design certification: cheap classify-and-rank with "
         "receipts, banded speed curves, loading matrix, regime refusals",
         "tests/test_design_certification.py"),
    # The FIDELITY GOVERNOR (directive §21 / BUILD-PLAN §11.8 / research
    # SMALL-CRAFT-REGIMES.md §16), 2026-08-20: five gates — environment, wave
    # existence, friction regime, Froude, decision-worthiness — that ROUTE a
    # design to a tier instead of badging it, each exercised in BOTH
    # directions on the study's own measured numbers, plus the missing-input
    # receipts. Registered here because Gate 0G's registry fence is right: a
    # suite nobody owns is a suite nobody runs.
    Gate("Gate FG", "fidelity governor: five gates route (not badge) a design "
         "to a tier, with named receipts and no silent passes",
         "tests/test_select_fidelity.py"),
    # GAP D11, and HONESTY RULE 6 APPLIED TO THIS FILE'S OWN REGISTRY.
    #
    # Gate 4's suite passes everything it asserts, so the row printed a blanket
    # GREEN while the plan's headline generative bar — "raw draws are >=99%
    # feasible" — was MISSED. The 2026-08-06 fix put the miss in Gate 4's
    # `scope` string, and that was the defect wearing the fix's clothes: this
    # file documents `detail` as "human context; NEVER load-bearing", and a
    # `scope` is no more load-bearing than a `detail`. The measured shortfall
    # could be deleted, softened or left to rot by editing one prose string, and
    # nothing anywhere would fail — which is gap D1 ("RED" -> "AMBER" bought
    # exit 0) surviving in the one place D1's own fix did not reach. MEASURED at
    # the time: the ladder printed GREEN for Gate 4, the ledger had no row for
    # it, and the number got no worse only because nobody re-ran it.
    #
    # So the clause is split into its own typed RED row, the same move as Gate
    # 6R (a clause of Gate 6) and Gate 1H (a clause of Gate 1). It now prints
    # RED first on every run, `judge_red` fails CI if the ledger does not
    # account for it, and `review_by` stops it becoming furniture. THE NUMBERS
    # ARE NOT REPEATED HERE — watermark, model, draw and owner are in
    # data/gate-ledger.json, which is the single home for them (gap J1).
    # tests/test_red_by_record.py is the fence, and it fails if any scope or
    # detail string starts carrying a measurement again.
    Gate("Gate 4F", "raw generative feasibility: UNFILTERED model draws vs the "
         ">=99% bar (BuildPlan Phase 4)",
         status=Verdict.RED,
         detail="see data/gate-ledger.json for the measured watermark"),
    # GAP D10's Gate 3E row stood here from 2026-08-12 (across-seed watermark
    # 0.183 against the 0.15 bar) until 2026-08-18, when it was RETIRED per
    # its own clearing contract: the physics-correction campaign brought the
    # across-seed median to 0.1471 (2026-08-13) then 0.1323 (2026-08-18,
    # fortress001, reproduced at the audit base — the improvement predates
    # that day's changes). D10's discipline survives the row: the Gate 3
    # suite's across-seed test now ASSERTS the bar on five honest query
    # draws (never one chosen seed) and re-opens the ledger row with a dated
    # measurement if the bar is ever missed again.
    # GATE 2 WAS REFRAMED 2026-08-21 (operator directive), and the reason is
    # that the QUESTION changed rather than the answer.
    #
    # Gate 2M was written when this project intended to design arbitrary
    # ships, and KCS -- a 230 m round-bilge container ship with a bulbous bow
    # -- was the right anchor for that. The product is now low-cost BUILDABLE
    # PLYWOOD boats: hard-chine, developable panels, shallow draft,
    # displacement to semi-displacement. KCS shares no chine, transom or
    # spray physics with any of them.
    #
    # KCS IS KEPT AND DEMOTED, not discarded. At model scale it sits at
    # Fn 0.260 / Re 1.40e7 against our 10 m at 5 kn (Fn 0.260 / Re 2.26e7),
    # so it remains an excellent test of the NUMERICS -- free-surface
    # resolution, layer stack, y+, turbulence closure, grid convergence -- at
    # our own operating point. What it cannot do is validate the physics our
    # hulls actually have. The row now SAYS which of those two claims it
    # carries, because the old title did not and that is how a solver
    # benchmark came to be read as small-craft validation.
    #
    # The rest of the stack (2-PHYS-A hydrostatics, 2-PHYS-B Wigley free
    # surface, 2-PHYS-C DSYHS displacement, 2-PHYS-E hard-chine) is tracked in
    # docs/audit/GATE2-PHYSICS-STACK.md. Only the rows with a suite or a
    # ledger entry appear here; a gate with neither would be a gate that
    # verifies nothing.
    # Gate 2's EXECUTABLE physics rungs. NOTE THE NAMESPACE: the physics
    # ladder is 2-PHYS-A..H, NOT 2A..2H. Seven of those eight letters are
    # already executable gates in THIS FILE meaning something else entirely
    # (2A is the admissibility screen, 2G is "the KCS STL is on disk"), and
    # for a while this comment used both meanings a dozen lines apart. See the
    # collision table in docs/audit/GATE2-PHYSICS-STACK.md.
    #
    # 2-PHYS-A is the strongest benchmark in the
    # project: the Wigley hull's displaced volume is exactly 4LBT/9, so the
    # integrator is checked against MATHEMATICS rather than an experiment
    # with a scatter band to hide in. The rungs that need data this tree does
    # not hold (2-PHYS-C DSYHS, 2-PHYS-E Naples) are recorded in
    # docs/audit/GATE2-PHYSICS-STACK.md and are deliberately NOT stubbed
    # here -- a gate that asserts nothing is worse than an absent one.
    Gate("Gate 2P-Stack", "Gate 2 physics stack: hydrostatics as a "
         "MATHEMATICAL invariant (Wigley 4LBT/9, second-order convergence), "
         "and KCS pinned as solver verification only",
         "tests/test_gate2_physics_stack.py"),
    Gate("Gate 2M", "SOLVER VERIFICATION ONLY (not small-craft validation): "
                    "KCS/JBC OpenFOAM numerics w/ per-case GCI",
         status=Verdict.RED,
         detail="see data/gate-ledger.json; demoted from primary physical "
                "anchor 2026-08-21 — see docs/audit/GATE2-PHYSICS-STACK.md"),
    Gate("Gate 2U", "unattended meshing (plan: >=95% of a 200-hull batch)",
         status=Verdict.RED,
         detail="see data/gate-ledger.json for the measured watermark"),
    # GAP G4, AND GATE 4F'S SHAPE FOUND A SECOND TIME (2026-08-11 ALIGNMENT
    # re-verdict).
    #
    # BuildPlan section 12.3 requires that "panels re-fold to the hull within
    # the stated millimetre bar". They do not, by a factor of ~28x and ~45x
    # against the 5 mm bar, and the shortfall does not refine away.
    #
    # ~~so it is a geometric property of taking the rulings at constant
    # station x~~ — SUPERSEDED 2026-08-21, and the correction moves the blame
    # off the unroller entirely. MEASURED against surfaces whose
    # developability is known in CLOSED FORM
    # (tests/test_manufacturing.py::test_the_unroller_is_EXACT_on_a_developable
    # _surface): cylinder 0.0000 mm, flat plane 0.0002 mm, tapered cone 0.0013
    # mm — and, as negative controls, twisted cylinder 436.6 mm and hyperbolic
    # paraboloid 46.7 mm. THE UNROLLER IS EXACT ON DEVELOPABLES and correctly
    # flags what is not one.
    #
    # AND THE WATERMARK'S OWN COUNT IS PART OF IT (2026-08-21, later). The
    # 124.1 mm is measured at `geometry._LADDER_STATIONS` = 41, where the panel
    # is a 40-segment polyline and part of every reading is that polyline's
    # sagitta: a surface with Gaussian curvature 7.8e-14 reads 17.1 mm there
    # and 1.5 mm at 321. So a single count is a number and only a FAMILY is a
    # verdict -- `unroll.refold_convergence`, falling = measurement, rising =
    # geometry. It cuts both ways: a refinement search scored on n=41 returned
    # a hull at 4.92 / 5.22 / 8.71 mm, under the bar where it was optimised and
    # RISING. `export_dxf` now refuses on the trend.
    #
    # What this gate measures is the HULL. Over governed hulls
    # corr(non_developable_frac, refold) = +0.783, with `flare` dominant at
    # +0.694 (flare 0° -> ndev_frac 0.0064; flare 25° -> 0.2953). The
    # shortfall does not refine away because REFINEMENT CANNOT FLATTEN DOUBLE
    # CURVATURE — not because the ruling family is wrong. It is not a
    # discretisation artefact either way. And yet NOTHING OWNED THE FAILURE:
    # `tests/test_manufacturing.py::test_gate6_refold_clause_is_red_on_the_hull`
    # ASSERTS the shortfall, honestly and deliberately, so the suite is GREEN
    # BECAUSE the bar is missed; Gate 6M therefore printed GREEN; the only
    # place the measurement lived outside that test was a sentence in
    # ALIGNMENT.md's STEP/IGES/DXF row; and the ledger had no entry, so no
    # owner, no review_by, and no way for CI to notice it getting worse.
    #
    # That is precisely gap D11 recurring: a measured miss that no STATUS can
    # see. The remedy is the one Gate 4F established, and the one Gate 1H and
    # Gate 6R used before it — split the clause into its own typed RED row so
    # the ladder shows WHICH clause is covered by what, and let the ledger own
    # the number. A test that encodes a miss is a good test; it is not a
    # verdict, because a verdict is a thing the ladder can print and CI can
    # fail on.
    #
    # THE NUMBERS ARE NOT REPEATED HERE. Watermark, units, configuration,
    # owner and the reproducing command are in data/gate-ledger.json, which is
    # the single home for them (gap J1). tests/test_red_by_record.py is the
    # fence: it fails if this scope or detail starts carrying a measurement,
    # if the row goes missing, or if Gate 6M stops pointing at it.
    Gate("Gate 6D", "developable-panel refold: EXPORTED panels back onto the "
         "hull vs the 5 mm bar (BuildPlan 12.3)",
         status=Verdict.RED,
         detail="the kit admission (buildability.kit_buildability) routes "
                "every design sheet-kit or mould with this gate's own meter; "
                "the low-twist kit corner and the kit reference hull PASS "
                "while the mould-class reference hull stays RED — watermarks "
                "and the re-framing decision live in the ledger row and "
                "docs/GATE-6D-DESIGN.md"),
]

# Summary line only. pytest writes it two ways depending on flags —
#   "= 3 failed, 19 passed, 2 skipped in 0.42s ="   (banner form)
#   "13 passed in 0.11s"                            (-q form)
# — so the anchor is the TIMING CLAUSE plus a leading count, not the '=' rule.
# That is what a spoof lacks: a conftest printing "wrote report.xml: 20 passed"
# has no "in <n>s", and the old reverse-scan-and-break parser accepted it,
# turning an all-skipped suite GREEN.
_SUMMARY_HEAD = re.compile(
    r"^[=\s]*\d+\s+(passed|failed|skipped|error|errors|xfailed|xpassed|deselected)")
_SUMMARY_TAIL = re.compile(r"\bin\s[\d.]+\s*s\b")
_COUNT = re.compile(r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed)")


def counts(output: str) -> dict:
    """Parse pytest's SUMMARY line into a count dict."""
    out = {"passed": 0, "failed": 0, "skipped": 0, "error": 0,
           "xfailed": 0, "xpassed": 0}
    for line in reversed(output.strip().splitlines()):
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        if not (_SUMMARY_HEAD.match(clean) and _SUMMARY_TAIL.search(clean)):
            continue
        for n, what in _COUNT.findall(clean):
            out["error" if what.startswith("error") else what] = int(n)
        break
    return out


def status_of(returncode: int, c: dict) -> tuple[str, bool]:
    """(label, counts_as_failure).

    A gate is GREEN only if tests actually RAN and passed. pytest exits 0 when
    every test SKIPS, so a machine without capytaine would have reported
    "Gate 2 GREEN" while verifying nothing.

    xfail/xpass are failures here, not decorations. One line —
    `@pytest.mark.xfail(reason='known gap')` — turned a failing gate test into
    a GREEN row with NO annotation, because the old parser did not know the
    word. A known gap belongs in the ledger where it has an owner and a date,
    not in a marker that silences the ladder.
    """
    if returncode != 0 or c["failed"] or c["error"]:
        return "RED", True
    if c["xfailed"] or c["xpassed"]:
        return (f"RED (xfail/xpass: {c['xfailed']}/{c['xpassed']} — put known "
                f"gaps in the ledger, not in a marker)", True)
    if c["passed"] == 0:
        return ("SKIPPED (no tests ran — missing dependency, or absent data "
                "such as data/benchmark_geom/kcs.stl?)"), False
    if c["skipped"]:
        return f"GREEN ({c['skipped']} skipped)", False
    return "GREEN", False


def judge_skip(gate: Gate, label: str) -> tuple[str, bool, bool]:
    """A suite ran nothing. (label, is_failure, the_skip_was_declared)

    THE RULE THAT SURVIVES: a suite that COULD have run and did not is still a
    failure. `Requirement` narrows the excuse to a named, probed environment
    fact; it never grants one. See Requirement's docstring for the incident.
    """
    if gate.requires is None:
        # Undeclared. Unchanged behaviour: --strict fails on it, and a gate
        # that starts skipping for a NEW reason lands here rather than being
        # absorbed by somebody else's declaration.
        return label, False, False
    req = gate.requires
    try:
        here = req.present()
    except Exception as exc:
        return (f"SKIPPED — the requirement '{req.what}' could NOT BE PROBED "
                f"({type(exc).__name__}: {exc}). An unmeasurable prerequisite "
                f"is not a satisfied one.", True, False)
    if here:
        return (f"SKIPPED, BUT '{req.what}' IS PRESENT HERE — the suite could "
                f"have run and did not. Failure, with or without --strict.",
                True, False)
    return (f"SKIPPED (declared: needs '{req.what}', absent here — {req.why})",
            False, True)


def load_ledger(path: str | Path | None) -> dict:
    p = Path(path) if path else DEFAULT_LEDGER
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def _worse_than(measured: float, wm: float, better_is: str) -> bool | None:
    """True/False, or None when `better_is` names no implemented direction."""
    if better_is == "up":
        return measured < wm
    if better_is == "down":
        return measured > wm
    if better_is == "toward_zero":
        return abs(measured) > abs(wm)
    return None


def judge_red(name: str, ledger: dict, today: date,
              measured: float | None = None) -> tuple[str, bool]:
    """Is this RED gate expected, regressed, or new? (label, is_failure)

    THE REGRESSION RULE IS IMPLEMENTED HERE (audit 2026-08-14, G0-01). The
    ledger's own README promised "a RED gate worse than watermark -> FAIL (it
    regressed)" while this function never read `better_is` at all — the rule
    the whole file exists for was prose. It cannot re-measure by itself (the
    verify commands need the CFD node or hours of batch), so the fresh number
    arrives as `measured` — from `--measured "Gate 2U=31.4"` on the CLI after
    running the entry's own `verify` command — and:

      - measured WORSE than watermark (per `better_is`)  -> FAIL, REGRESSED
      - measured equal/better                            -> expected; better
        prints "IMPROVED — update the watermark" so the ledger ratchets
      - watermark not a number, or the entry carries `calibration_void`
        (the population that produced it no longer exists — e.g. Gate 2U's
        27.8% was measured on the 15-parameter genome, audit G0-02) ->
        UNCOMPARABLE: with a fresh number that is a FAIL (the ledger must be
        re-based before the number means anything); without one the label
        says re-measurement is owed instead of implying a comparison held.
    """
    entry = ledger.get(name)
    if entry is None:
        return ("RED (NEW — not in the ledger. Record it with a measured "
                "watermark and an owner, or fix it.)", True)
    try:
        due = date.fromisoformat(str(entry.get("review_by", "")))
    except ValueError:
        return ("RED (ledger entry has no valid review_by date)", True)
    if today > due:
        return (f"RED (LEDGER EXPIRED — unreviewed since {due.isoformat()}. "
                f"Re-measure or sign a dated extension.)", True)
    wm = entry.get("watermark")
    void = entry.get("calibration_void")
    comparable = isinstance(wm, (int, float)) and not void
    if measured is not None:
        if not comparable:
            why = (str(void) if void else f"watermark is {wm!r}, not a number")
            return (f"RED (measured {measured} but the watermark is "
                    f"UNCOMPARABLE — {why}. Re-base the ledger entry with "
                    f"this measurement and its config before comparing.)",
                    True)
        worse = _worse_than(float(measured), float(wm),
                            str(entry.get("better_is", "")))
        if worse is None:
            return (f"RED (better_is {entry.get('better_is')!r} names no "
                    f"implemented direction — fix the ledger entry)", True)
        if worse:
            return (f"RED (REGRESSED — measured {measured} is worse than the "
                    f"watermark {wm} ({entry.get('better_is')} is better). "
                    f"Fix it, or re-measure and sign a new watermark.)", True)
        improved = _worse_than(float(wm), float(measured),
                               str(entry.get("better_is", "")))
        note = (" IMPROVED — update the watermark so the ratchet holds."
                if improved else "")
        return (f"RED (expected: measured {measured} vs watermark {wm}, not "
                f"worse.{note} Owner {entry.get('owner', '?')}, review by "
                f"{due.isoformat()})", False)
    suffix = ""
    if not comparable:
        suffix = (" UNCOMPARABLE — no regression check is possible against "
                  "this watermark; re-measurement owed via the entry's "
                  "verify command.")
    return (f"RED (expected: {entry.get('metric', '?')} watermark {wm}, "
            f"measured {entry.get('measured_utc', '?')}, "
            f"owner {entry.get('owner', '?')}, review by {due.isoformat()})"
            + suffix, False)


# --------------------------------------------------------------- the README
#
# GAP J2. README's gate table was hand-maintained, and every hand-maintained
# copy of a machine-readable fact drifts. MEASURED at the 2026-08-05 audit:
# per-gate test counts stale throughout (Gate 1 said 13 against 22 actual,
# Gate 2 said 4 against 18, Gate D said 12 against 19); NO Gate 2U row at all,
# so a RED gate was invisible in the project's front door; and Gate 2M's row
# carried a prose figure (-151%) that three later commits had superseded.
#
# The fix is not "update the README". It is to stop the README being a second
# source. The table is GENERATED from GATES, and a test fails when the file on
# disk and this function disagree. `--readme --write` performs the update, so
# the failure costs one command rather than a hand edit that will drift again.

README_BEGIN = "<!-- BEGIN GATE TABLE — generated by `python -m navalai.gates --readme` -->"
README_END = "<!-- END GATE TABLE -->"


def collect_counts(root: Path | None = None) -> dict[str, int]:
    """Tests per suite, from pytest's own collection.

    Collection, not execution: it costs ~0.5 s for the whole tree, so the
    README can carry a real count instead of a remembered one.

    A suite whose module-level `importorskip` fires collects ZERO. That is
    reported as 0 and the caller decides — the README test skips rather than
    baking "0 tests" into the file, because a missing optional dependency is
    an environment fact, not a project fact.
    """
    root = root or _ROOT
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/",
                        "--collect-only", "-q", "--no-header"],
                       capture_output=True, text=True, cwd=root)
    out: dict[str, int] = {}
    for line in r.stdout.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        if "::" in line and line.startswith("tests/"):
            out[line.split("::", 1)[0]] = out.get(line.split("::", 1)[0], 0) + 1
    return out


def gate_rows(counts: dict[str, int] | None = None) -> list[tuple[str, str, str]]:
    """(gate, scope, evidence) for every row, in ladder order."""
    rows = []
    for g in GATES:
        if g.suite is None:
            if g.status == Verdict.RED:
                ev = "**RED** — `data/gate-ledger.json`"
            else:
                ev = f"**{g.status}-GATED** — {g.detail}"
        elif counts is None:
            ev = f"`{g.suite}`"
        else:
            n = counts.get(g.suite, 0)
            ev = f"`{g.suite}` ({n} tests)"
        rows.append((g.name, g.scope, ev))
    return rows


def markdown_table(counts: dict[str, int] | None = None) -> str:
    rows = gate_rows(counts)
    lines = ["| Gate | Scope | Verified by |", "|---|---|---|"]
    lines += [f"| {n} | {s} | {e} |" for n, s, e in rows]
    return "\n".join(lines)


def readme_block(counts: dict[str, int] | None = None) -> str:
    return "\n".join([
        README_BEGIN,
        "",
        "Run `python -m navalai.gates` for live status; this table is the",
        "REGISTRY (what is gated by what), regenerated from `navalai/gates.py`.",
        "A RED row's measured watermark, owner and review-by date live in",
        "`data/gate-ledger.json` — never in prose here, which is how five",
        "different Gate 2M numbers came to circulate at once (gap J1).",
        "",
        markdown_table(counts),
        "",
        README_END,
    ])


def write_readme(path: Path, block: str) -> bool:
    """Replace the marked block in README.md. True if the file changed."""
    text = path.read_text()
    i, j = text.find(README_BEGIN), text.find(README_END)
    if i < 0 or j < 0:
        raise SystemExit(f"{path}: gate-table markers not found")
    new = text[:i] + block + text[j + len(README_END):]
    if new == text:
        return False
    path.write_text(new)
    return True


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    strict = "--strict" in argv          # CI: skipped gates are not acceptable
    # --suites-only: judge ONLY the pytest-backed gates. The pre-push hook uses
    # this so it blocks REGRESSIONS without blocking every push on gates that
    # are known, measured and recorded red. Making the hook unusable is how you
    # train people to --no-verify, which is worse than either.
    suites_only = "--suites-only" in argv
    if "--readme" in argv:
        block = readme_block(collect_counts())
        if "--write" in argv:
            changed = write_readme(_ROOT / "README.md", block)
            print("README.md rewritten" if changed else "README.md already current")
        else:
            print(block)
        return 0
    ledger_path = None
    # --measured "Gate 2U=31.4" (repeatable): a fresh figure produced by
    # running a red gate's own `verify` command, handed to `judge_red` so the
    # ledger README's regression rule actually executes (audit G0-01). A
    # malformed value is a hard error — a typo silently dropped would report
    # "expected" for a gate the operator believed they had just re-measured.
    fresh: dict[str, float] = {}
    for i, a in enumerate(argv):
        if a == "--ledger" and i + 1 < len(argv):
            ledger_path = argv[i + 1]
        if a == "--measured" and i + 1 < len(argv):
            spec = argv[i + 1]
            gate_name, _sep, raw = spec.partition("=")
            try:
                fresh[gate_name.strip()] = float(raw)
            except ValueError:
                print(f"--measured {spec!r}: expected '<gate name>=<number>'")
                return 2
    ledger = load_ledger(ledger_path)
    today = date.today()

    failures = skipped_gates = red_gates = declared_skips = 0
    green_names: list[str] = []
    print(f"{'gate':13} {'scope':45} status")
    print("-" * 84)
    for g in GATES:
        if g.suite is None:
            if g.status == Verdict.RED:
                label, is_fail = judge_red(g.name, ledger, today,
                                           measured=fresh.get(g.name))
                if not suites_only and is_fail:
                    red_gates += 1
            else:
                label = f"{g.status}-GATED — {g.detail}"
            print(f"{g.name:13} {g.scope:45} {label}")
            continue
        # C-16 (forensics, the 4-day lesson): this call had NO timeout, so
        # when a suite acquired an infinite loop (frozen_suite's emptied
        # held-out wedge) two verification runs spun for FOUR DAYS with the
        # ladder reporting nothing. A hung suite is a FAILURE, not a wait.
        # 3600 s sits ~2x above the heaviest measured suite on the slow
        # box (test_phase7 ~10.5 min, Gate 2 BEM ~27 min under load);
        # override per-run with NAVALAI_SUITE_TIMEOUT_S, 0 disables.
        suite_timeout = float(os.environ.get("NAVALAI_SUITE_TIMEOUT_S",
                                             "3600")) or None
        try:
            r = subprocess.run([sys.executable, "-m", "pytest", g.suite,
                                "-q", "--no-header"], capture_output=True,
                               text=True, timeout=suite_timeout)
        except subprocess.TimeoutExpired:
            failures += 1
            print(f"{g.name:13} {g.scope:45} RED (SUITE TIMED OUT after "
                  f"{suite_timeout:.0f}s — a hung suite is a failure; find "
                  f"the loop, do not raise the timeout)")
            continue
        c = counts(r.stdout)
        label, is_fail = status_of(r.returncode, c)
        ran_nothing = label.startswith("SKIPPED")
        if ran_nothing:
            label, is_fail, declared = judge_skip(g, label)
            # Only an UNDECLARED skip arms --strict. A declared one is counted
            # and printed separately so it stays visible rather than vanishing
            # into a green check.
            declared_skips += 1 if declared else 0
            skipped_gates += 0 if declared else 1
        elif not is_fail:
            green_names.append(g.name)
        failures += 1 if is_fail else 0
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        print(f"{g.name:13} {g.scope:45} {label}  ({tail})")

    # A gate that RECOVERED must not leave its entry behind: a stale ledger is
    # how an expected-red list turns into a list of things nobody rechecks.
    stale = sorted(set(ledger) & set(green_names))
    if stale and not suites_only:
        print(f"\nLEDGER STALE: {', '.join(stale)} now GREEN — remove the "
              f"entry so the ledger keeps meaning what it says.")
        red_gates += len(stale)

    if red_gates:
        print(f"\n{red_gates} gate(s) are red in a way the ledger does not "
              f"account for. A failing gate is information; never soften it.")
    if skipped_gates:
        print(f"\n{skipped_gates} gate(s) ran no tests and did NOT declare why "
              f"— a missing optional dependency, or an artefact this machine "
              f"does not have. Give the row a Requirement naming what it needs "
              f"and how this environment can lack it, or install the thing. "
              f"{'FAILING (--strict).' if strict else 'Nothing was verified by them.'}")
    if declared_skips:
        print(f"\n{declared_skips} gate(s) ran no tests for a DECLARED, PROBED "
              f"reason (printed above). Nothing was verified by them HERE, and "
              f"that is not softened: the declaration lives in "
              f"navalai/gates.py where it is reviewable in a diff, and the "
              f"probe makes it fail the moment the thing it names is present.")
    return 1 if (failures or red_gates or (strict and skipped_gates)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
