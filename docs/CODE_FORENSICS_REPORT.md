# Code forensics report — master synthesis (Phase 2)

Repository state at synthesis: `master`, clean, synced. Nine domain
reports are the evidence base (`docs/forensics/`: failure-paths,
tests-honesty-batch, import-graph, scripts-files-artifacts, docs-vs-code,
tests-phase-batch, ownership, e2e-map, shadow-api) — treat them as
appendices; every claim below carries file:line evidence there. Companion
deliverables: `LIVE_SYSTEM_MAP.md`, `docs/forensics/e2e-map.md`,
`docs/forensics/import-graph.md`,
`docs/forensics/scripts-files-artifacts.md`,
`CODE_CONSOLIDATION_PLAN.md`. (The three forensics files had a
byte-identical second copy at the top level of `docs/` until
2026-08-20; the duplicates are deleted and these are the one home.)

## The verdict in one paragraph

The physics discipline is genuinely clean — one evaluator behind every
generator, no unlabelled shadow physics, honest refusals at every claiming
stage, zero dead files, zero dead scripts, zero dead commands, 100% of
test suites gate-owned. The entropy is not abandoned code; it is
**dangling wires and anonymous receipts**: the newest single-truth objects
(CFDManifest, admissibility screen, policy, estrin) are built and gated
but not consumed by the live lanes; the newest layer (certify) reintroduced
two solved defect classes (trim-`or 0.0`, a second weight model); and one
pre-existing geometric drift (the held-out wedge emptied by the box move)
turned into a live 4-day infinite loop that no timer caught.

## Exact bugs (the P0 set)

1. **frozen_suite infinite loop** — held-out wedge contains zero
   L0-feasible hulls since the box widened (corner L/B 11.47 > 8.5;
   0/60,000 at HEAD and at audit base); no draw guard; both verification
   runs hung 4+ days; every unmocked retrain test hangs;
   `data/baselines.json`'s held-out arm is void. (C-01)
2. **Refused trim becomes 0.0** at four sites in the newest code, one
   feeding CFD manifests. (C-02)
3. **One rule, two displacements** — R-TBM selects its sheet from the
   mission target but is assessed at the floated state; designs fail by
   construction when budget > target (measured 0.02 mm sliver refusal). (C-04)
4. **Dead assertion** `… or True` in test_phase0.py:80. (C-03)

## Exact risks (the P1 set)

- The CFD case a manifest certifies is not the case that gets written
  (design-frame float: +122.9% displacement on case a; +5.7% case d);
  make_case.py bypasses the whole canonical chain; the G7 mass fix has
  zero production callers. (C-06)
- certify's buildability runs a second weight model (29% divergence
  measured inside one certification). (C-05)
- grammar_version is decorative — two genome eras share one label. (C-09)
- The meshability screen never guards the mesher (C-18); round-bilge
  hulls are structurally CFD-ineligible via the buildability refusal
  (C-19); the HTTP lane silently drops EnergySpec and cannot express a
  vessel (C-12/34); the NL lane is monohull-only (C-35).
- evaluate's broad except masks code bugs as design refusals (C-15); the
  gate runner's suite subprocesses have no timeout — the mechanism that
  turned a latent loop into a 4-day wedge (C-16).
- Naming: NU_SEA_15C = two numbers; resistance misattributes its salt
  anchor (C-11). Two design-Fn definitions; the mission-targets stage is
  inert for the project's own deterministic fleet (C-13).
- Receipts: certification/export JSON cannot name the hull or code
  version that produced them — the gate2u mistake in miniature (C-22).

## Duplicates and constants (post-consolidation residue)

Resolved at HEAD: ITTC-57 (one line), section builders (one kernel),
wetted/volume (named cross-checks), weight_budget∥MassItem (bridged +
fenced), constants home (fence live, caught 3 strays on first run).
Remaining: two ASCII-STL writers and two STL parsers with different weld
semantics concentrated in cfd/post.py (C-10); PV-area expression twice in
energy.py; formlib's comment-enforced 0.45; two freeboard floors with an
undeclared relationship; one scripts-side G literal (C-33).

## Tests and gates

All 30 audited suites STRONG/ADEQUATE; physics mocking essentially absent
(only adversarial controls with unmocked counterparts). Defects: Gate 3
carries two deliberately-failing tests with no ledger row (the repo's own
doctrine says typed RED); test_phase2's module-level importorskip hides
~14 capytaine-free tests; Holtrop branch tests are
transcription-tautological; the ITTC validity envelope has two homes with
two bars; the committed surrogate mark refuses its own generating seed;
red_by_record's prose fence only matches N.N%. Docs-vs-code: PLM §2.0 and
BUILD-PLAN PV-1/2 still deny capabilities that landed under Gates VM/1M;
STATUS contradicted itself on "next"; the BUILD-PLAN entry table names
test-only modules as system entries; hooks are silently disabled on this
machine (stale absolute core.hooksPath).

## Old artifacts and caches

gate2u JSONs: VALID_HISTORICAL, correctly quarantined (the tree itself
declares the 15-gene calibration void); renders/: tracked despite ignore +
"fixed" register row (guard blind — C-20); no cross-process stale-cache
path found; ladder-consumed artifacts carry strong provenance while
operator-facing receipts carry none.

## The §34 questions — answered at Phase-4 (post-fix) state, 2026-08-19

Post-fix state at 752e695 (the pre-fix answers are kept below for the
record). Items landed since Phase 2: C-01..07, C-09..12, C-15/16,
C-18..23(label)/24(label)/25/26/27, C-28(PLM wave), C-29(3E retired),
C-30/31/32/33/34/35/36, C-08 (last), the §31 four-class chain test, the
meshability-math re-derivation (Gate 2D), and the solvability chain
(early abort + reclassify + re-based 1e-12 bar).

1. ONE production E2E path? **YES for design AND for CFD** — make_case's
   `--case` lane runs mission→evaluate→certify-state→manifest→case; the
   §31 test pins the chain for all four canonical classes.
2. One geometry truth? **YES** (unchanged).
3. One hydrostatics truth? **YES** (unchanged).
4. One resistance truth? **YES, completed** — C-08 put the floated
   length into the one-state contract (measured: median +0.000%, worst
   +1.279%); C-31 unified the ITTC envelope on one band.
5. One mass/loading truth? **YES everywhere** — the manifest lane
   carries the certified mass; free_motion comes from the manifest.
6. One CFD-input truth? **YES** — the manifest is APPLIED and verified
   at write (2% displacement refusal bar); case.info renders it.
7. Can a candidate bypass validation? **Not on the canonical lane** —
   the admissibility screen guards the writer (refused_no_rescue;
   rescuable predictions warn + record and the runner's metal-proven
   ladder recovers them); Hull() still builds anything for research,
   which is a declared property, not a leak.
8. Physics failure silently valid? **The trim-`or 0.0` cluster is
   gone** (C-02); the swamped-hull path is violations-first and the
   pipeline guard reads it (2026-08-19).
9. Old artifacts consumed accidentally? **No** — baselines regenerated
   on the live wedge, grammar_version derives from N_PARAMS, the gate2u
   corpus rows re-derive their own labels (h18 relabeled a divergence).
10. Orphaned production modules? **None unlabeled** — the experiment
    island, policy kernel, waves, demo_mission and estrin all carry
    their classification and promotion path in their own docstrings.
11. Duplicate quantity implementations? **Closed** — one facet emitter,
    two STL parsers with DECLARED distinct weld jobs, PV area one
    expression, constants fences extended to scripts/, the
    formlib↔Michell edge identity is executable.
12. All supported families through one pipeline? **YES** — Gate VM +
    the §31 chain test (cats refusal-first by name until R2.2).
13. Production files? `PRODUCTION_CORE.md` (unchanged).
14. Delete? Nothing further — zero DEAD stands.
15. Research/experimental labels? **Done** (C-25 banners).
16. Before production testing? **Done** — Phases B–D landed, §31 tests
    landed, receipts carry identity (C-22), suites that hung now
    bounded (C-01/C-16).
17. Before CFD testing? **This box's half is done** (screen wired with
    the rescue axis, math re-derived, Gate 2D, solvability receipts).
    Remaining is CFD-node work: the one-random-admissible-mesh check
    (protocol in docs/MESHABILITY_MATH.md §H), then the Gate 2U item-2
    dual-denominator campaign and Gate 2M calibration.

## The §34 questions — answered at Phase-2 (pre-fix) state

1. ONE production E2E path? **YES for design** (mission→evaluate→certify),
   **NO for CFD** (make_case bypasses the chain) — C-06.
2. One geometry truth? **YES** (grammar+kernel; STL derived; cross-checks
   declared).
3. One hydrostatics truth? **YES** (solve family; no unlabelled shadow).
4. One resistance truth? **YES** (total_resistance; holtrop = guard;
   residue: design-length input, C-08).
5. One mass/loading truth? **YES in the ladder; NO on the CFD lane**
   (motion_from_geometry is the only reachable free-motion path) — C-06.
6. One CFD-input truth? **NO** — the manifest is recorded, not applied
   (B5); case.info is authoritative-in-practice — C-06/C-07.
7. Can a candidate bypass validation? **YES** — Hull() builds refused
   genomes and the case writer checks watertightness only (B12/C-18).
8. Can a physics failure silently become valid? **The four trim-`or 0.0`
   sites** (C-02); otherwise the refusal discipline held everywhere
   audited.
9. Old artifacts consumed accidentally? **No** — the void sets are
   quarantined; the risk is the decorative grammar_version (C-09) and the
   void baselines held-out arm (C-01).
10. Orphaned production modules? **No orphans mislabelled as production**;
    four built-but-unwired capabilities (manifest, screen, policy,
    estrin) and one agentic island are named in the map.
11. Duplicate quantity implementations? Residue only (C-10/C-33).
12. All supported families through one pipeline? **YES** (Gate VM proves
    it; trimaran refused by name; multihull verdict honestly REFUSED).
13. Production files? See `PRODUCTION_CORE.md`.
14. Delete? **Nothing yet** — zero DEAD; only renders/*.png untracking
    (C-20) and label-then-decide for legacy demo (C-27).
15. Move to research/experimental? agents+hull_ast, policy, pipeline+
    latent front, arrangement (labels, §26) — C-25.
16. Before production testing? Phases B–D of the plan (C-01…C-16) + the
    §31 four E2E tests + receipts (C-22).
17. Before CFD testing? C-06/C-18 (the case lane consumes manifest +
    screen), Gate 2U 16-gene re-campaign, Gate 2M calibration — all
    requiring the CFD node, which is currently unavailable.
