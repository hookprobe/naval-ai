# Hull Design Architecture Audit — root cause, research, target architecture

**Dated 2026-08-26.** Commissioned by the owner's deep-audit protocol ("why can
Naval-AI generate a mathematically valid 3D object but fail to generate
something that visually and hydrodynamically resembles a real recreational
boat hull?"). Method: four parallel deep audits — geometry kernel, pipeline &
search, gates & validation ladder, and published naval-architecture research —
each tracing real call paths with file:line evidence, plus a source-grounded
research matrix. **No implementation was changed by this audit** (the
protocol's hard rule). Where a finding was already recorded in
`docs/ml-hull-generation.md`, `docs/morphology/MORPHOLOGY-V1.md` or
`docs/research/PROPULSION-INTEGRATION.md`, this report confirms/corrects and
cites rather than restates; findings new to this audit are marked **[NEW]**.

This document is an AUDIT RECORD (like `docs/audit/GATE2-PHYSICS-STACK.md`):
its measurements are dated 2026-08-26 and do not update themselves. Live
state comes from the code and `python -m navalai.gates`.

---

## A. Current architecture (what actually runs)

The production lane, traced (not the aspirational one):

    mission text ─ mission.parse_mission ─→ MissionSpec
        (extracts: length window, Cp band via cruise speed, displacement,
         GM floor via category. DISCARDS: beam ["4 m width" matched by
         _DENY_LENGTH, mission.py:669], vessel family ["houseboat" matches
         nothing], berths [collapses to crew mass], headroom/air draft)
    → ONE of three chains:
      A1 design_report CLI: certifies reference_params() — a FIXED 16-gene
         hull with r_stem=pmb=0 by construction. NO SEARCH (design_report.py:117-121).
      A2 /pareto: NSGA-II pop 48 × 15 gens, F=(Wh/nm, build_area, |GM−mid|),
         G = the 10 CONSTRAINT_NAMES rows (optimize.py:68-69).
      A3 UI sweep /api/search: uniform random over the full box, ranked by
         Wh/nm ALONE (ui/api.py:1105,1132).
    → evaluate() ladder (hydrostatics, resistance, energy, rules, propulsion
      rows) → certify() → contract.evaluate_hull() → STL only at the very
      end (cfd/case.py:2476, blender render) — the FIRST point where shape
      becomes visible, downstream of every gate.

Live-vs-island (verified by call sites): `morphology.critique/design_rules/
manifold_score` — **zero production callers**; `morphology_search` — dead
(tests only); `arrangement.py` — **zero importers**; `pipeline.py` FSM —
unwired; `agents.run_plm` — test-only; `export_step/iges` — tests only
(design_kit ships STL+DXF). `policy/` labels itself unwired but IS consulted
by `ui/api.py:373,1097` (stale label).

## B. Current geometry representation

- **23-gene fixed-topology parametric shape law** (`grammar.PARAMS`). 17 of
  23 are shape-law coefficients; 2 (Cp, lcb) are targets; no keel(x)/chine(x)
  free curves; no NURBS anywhere in production (CadQuery lofts POLYGON wires,
  ruled — a faceted polyhedron, export.py:202,429).
- **A section is five control points** (K, P0, C, P2, S — geometry.py:1039):
  keel on centreline, ONE chine, ONE quadratic bilge fillet with ONE
  hull-wide radius (`self._rho`, geometry.py:997), ONE straight topside
  segment. Monotone-z, single-valued y(z), simply connected — assumed by
  `_halfbreadth_at` (:2069), `_immersed` (:1777, four hardcoded cases),
  `wetted_surface` (:1323), `export._displaced_volume_of` (export.py:232).
- **Beam is an output**: half-breadth is the positive root of the section
  quadratic given the SAC ordinate (geometry.py:548-563). The SAC is the one
  design curve; plan-form, Cb, Cwp, LCF, GM, deck area, entrance angle are
  all arithmetic consequences.
- **Sterns and bows are the last/first stations** plus flat caps; LOA ≡ LWL
  (plane sections at shared x, geometry.py:985,1528) — no stem rake exists.

## C. Why boxes happen — causal chain **[confirmed + NEW links]**

1. Topside = ONE straight segment chine→sheer (geometry.py:577) whose only
   freedom is one angle in [−5°, +25°]; `chine.submerged` (grammar.py:622)
   forces the chine below the waterline at every station → **the entire
   above-water hull is a slab per station**. Slab topsides + low deadrise +
   flat SAC top = box.
2. **[NEW]** `Cp` gene ceiling **0.710** (grammar.py:270 ← limits.py:780,
   the span of PRISMATIC_BY_FROUDE) — a barge/houseboat/pontoon needs
   Cp 0.85–0.95 and **cannot be requested**. This corrects
   ml-hull-generation.md §4's "Cp must approach 0.92": it cannot; the
   request is refused at the bound. Wide-deck demand can then only be met by
   a prismatic slab of near-constant deep section.
3. The optimizer prices deck area as pure COST (`build_area` includes
   deck_area, optimize.py:58) and the GM-band objective
   (`gm_mid = 0.5·(floor + 0.20·B)`) charges a wide shallow hull for the
   large GM it inevitably has — both push toward compact/narrow/deep.
4. The sheet-kit route's own measured "low-twist corner" (flare 0, forefoot
   0, warp ≤ +8°: sharpie/dory class) is the only geometry that satisfies
   the 5 mm refold bar — a second independent pressure toward slabs
   (buildability.kit_buildability docstring).

## D. Why spearheads happen — causal chain **[confirmed + NEW links]**

1. SAC forward branch `a = r_stem + (1−r_stem)·(1−h(t))` with `r_stem`
   defaulting to 0 → `a(LWL)=0` → area, waterline beam, sheer beam and
   flare all collapse to a **mathematical point** (geometry.py:354,563,577;
   closed_mesh drops all 240 stem-cap triangles as zero-area).
2. Every sampler pins `r_stem` (and the other six post-hoc genes) to zero:
   `grammar.sample` (:672), `evaluate.sample_valid` (evaluate.py:431-443),
   `generative._pin_post_hoc` (generative.py:126-128). The GP surrogate then
   DROPS the constant columns (surrogate.py:225-231); the PPCA genome gets
   seven null directions; the GMM re-pins on the way out. **Every trained
   model has been taught that a bow is a point.**
3. **[NEW]** `flare_bow` is a no-op at the stem: geometry.py:522 multiplies
   the flare law by `env = max(a,0)` — the area envelope the gene was added
   to escape. With r_stem=0 the 2026-08-24 flare fix has exactly zero
   effect where it matters. (`formlib._M_FLARE`'s blocker is accidentally
   still true, for a different mechanism.)
4. **[NEW]** `sac_exponents` never receives `pmb`/`r_stem`
   (geometry.py:328-329 vs 352-357), so both genes silently add area
   forward and shift delivered LCB; the `lcb` row (evaluate.py:1124,
   ±3 %LWL on the floated hull) then FIRES — **the gate layer has a
   gradient pushing the search back toward r_stem = 0**. (Estimated ≈
   +3.6 %LWL for r_stem 0.5 at pf≈2 — needs a 5-line numerical
   confirmation; highest-value single measurement in this audit.)
5. Wh/nm falls monotonically with slenderness (measured: a "10 m" brief ran
   to 18.58 m before an LWL bound was added, optimize.py:112-116); the UI
   sweep — the ONLY production sampler that draws r_stem/pmb — then ranks
   by Wh/nm alone, selecting the slenderest survivor.
6. The critic that names SPEARHEAD (`beam_carried < 0.20`) has zero
   production call sites.

## E. Why complex chines fail

One `(y_chine, z_chine)` slot per station (geometry.py:593-596); one
hull-wide bilge radius (:997); `sample_section` emits exactly one bilge
feature (:695); `chine_row` returns ONE integer per hull — valid only
because section topology is x-invariant (:1611-1634); `unroll._PANEL_EDGES`
hardcodes exactly two panels (unroll.py:908). Therefore: no chine
termination, no hardness variation (round-fwd/chine-aft unreachable), no
second chine, no chine flats, no lifting strakes, and a keel KNUCKLE on
every hull (the only fillet is at the chine). The escape is already drawn
in-tree: `hookprobe_hull.roundness_at/turn_frac/deadrise` — section SHAPE
as C² splines of x (scripts/hookprobe_hull.py:242-279).

## F. Why bow geometry fails

No stem-profile curve (LOA≡LWL, plane sections) → no rake, no overhang, no
reverse/X/tulip bow. `r_stem` pinned by samplers (D.2). Flare law killed by
`env` (D.3). Bulbous bow impossible: the SAC forward branch is monotone by
construction (`_shape`, geometry.py:180-184). Delivered flare measured
falling 15.8°→0.0° over the forward 20% while the gene sat at its ceiling —
no gate saw it. `alpha_e_deg` is computed and read by nothing.

## G. Why stern geometry fails

The stern is "the last station + a flat vertical cap" (geometry.py:
1603-1604). `r_transom` ceiling **0.50** (grammar.py:275) vs published
transom-beam ratios 0.8–1.0 — the direct cause of the measured 0.413-vs-
0.687 gap; measured consequence: **0 of 1592 hulls reach 3.0 m transom
beam** (MORPHOLOGY-V1.md §4). The ceiling is a CORE gene held hostage by
seeded-population reproducibility; the fix's fence test exists and is
deliberately held out of tests/ (`docs/morphology/pending/
test_barge_bow.py.held`, commit 6e91d33). There is **no stern gate at
all** — no transom fullness bar, no run fairness, no buttock rule;
`transom_froude` is deliberately a report, not a row.

## H. Why propulsion integration fails

`propulsion.rows_for` is a READER of a finished evaluation (its own
contract, propulsion.py:18-22). Its levers (n_props, tunnel recess, hang,
motor_kw) live on EnergySpec, not in the decision vector — **NSGA-II cannot
move a single propulsion variable** (optimize.py:159). 13 of the owner
protocol's 14 requirements are ABSENT (PROPULSION-INTEGRATION.md §6). The
only propulsion failure any gate can see is "disc doesn't fit the transom".

## I. Why the gates miss all of this

1. **The gate list is a test-runner manifest.** All 79 rows pass on the
   same condition: their pytest suite exits 0. There is no gate-level bar.
2. **Shape modules have zero production callers** (critique, design_rules,
   manifold_score, morphology_search). `certify` computes
   form_descriptors and fairness and **discards them from the verdict**;
   `contract.evaluate_hull`'s hull_verdict inherits certify's — the whole
   four-verdict contract is shape-blind.
3. **The 11-level validity ladder, mapped**: L0/L1 (params, geometry) FULL;
   L2 (watertight) enforced only OFF-path (pipeline FSM unwired — the
   hookprobe 635-self-intersection failure was caught by a script, not a
   gate); **L3 (plausible) NONE; L4 (visually recognizable) NONE**;
   L5 (hydrostatics) FULL — strongest tier; L6 (meshable) WEAK (Gate 2U
   RED at 21.7% vs 95%); L7 (CFD) RED (watermark NONE); L8 no
   competitiveness bar; L9 mission-dimensional intent not bound ("4 m
   width" not expressible as a constraint); L10 one row (bend radius) +
   Gate 6D RED at 124.1 mm vs 5 mm.
4. **Every admissibility bar is a MINIMUM** (cell-scale thinness). A box
   maximises all 15 — Gate 2A is structurally incapable of refusing one.
5. Measured composite: **89–92% of L0-valid generated hulls are
   morphologically implausible; 0 of 58 published hulls are** — and the
   2026-08-23 plank passed displacement, Cp, Cb, LCB, GM, freeboard,
   scantlings, all constraint rows, seven rule findings and arrangement;
   four hulls shipped before anyone rendered one.
6. Family bias where the critic IS used (tests/scripts): `_FAMILY_BAR` has
   3 rows (demihull/catamaran/pontoon), none for axe/piercer/planing/
   barge; 55 of 300 plywood demihulls were false-refused on the monohull
   L/B ceiling; the team already overrides piercer flags by hand
   (HULL-KB.md) — a gate routinely overridden is not a gate. Latent bug:
   `morphology_search._REPAIR` nudges gene `l_pmb`, which no longer
   exists — silently skipped, so the SPEARHEAD/BOX repairs are missing
   exactly the `pmb` lever (and never mention `r_stem` at all).

## J. Research findings (full matrix: agent report, 2026-08-26; sources in
## the table below are the load-bearing subset)

1. **Parent + distortion is the professional method.** Every systematic
   series since 1963 (Series 60, DSYHS, NPL, Series 62/Fridsma, Naples NSS,
   Southampton cats, NTUA) is ONE proven hand-faired parent + a 2–5-dim
   distortion (slenderness, loading, LCB, B/T, deadrise warp). Nobody
   searches section shapes. DSYHS adopted a NEW parent when style moved.
   NSS scaled B and T homothetically — ALL coefficients invariant — a
   one-parameter slenderness sweep Naval-AI can implement and verify by
   hydrostatics invariance.
2. **The lines plan is three coupled curves** — SAC, design waterline,
   section character (Larsson & Eliasson; Harries/Abt form-parameter
   design). Naval-AI has the SAC only; **the independent design-waterline
   curve B(x) is the single kernel repair the literature names** for the
   measured one-curve-two-jobs defect.
3. **Lackenby transformation** (1950) is the industry variation operator:
   shifts stations longitudinally, changes Cp/LCB, PRESERVES section
   character — implementable directly on the SAC kernel.
4. **Developability by construction**: ply designers define strakes as
   ruled surfaces between chine curves; the NSS proved making a proven
   parent developable costs ~nothing hydrodynamically. Gaussian curvature
   becomes a receipt, not a repair loop.
5. **Multihulls need no new surface kernel**: demihull (a family member) +
   layout variables (s/L, wet-deck height) — Insel–Molland. Dissolves the
   "multi-hull not possible" blocker cheaply.
6. **Images**: lines-plan-quality views yield offsets to plating tolerance
   (published NURBS skinning); a perspective photo yields family + ratios
   only, never the underwater body — photo-derived quantities must carry
   an image-estimate tier with wide sigma.
7. **Optimization practice**: Pareto + constraints, never fixed weights;
   degenerate optima (over-fine bows, displacement leakage) are prevented
   by putting the plausibility critic and equality/band constraints INSIDE
   the loop — otherwise the optimizer finds the 8–11% gap.
8. **AI**: every published learned generator (ShipGen/ShipHullGAN) uses
   10⁴–10⁵ designs, bootstraps its OWN corpus from parent+distortion, and
   still leaks implausible shapes (repo-measured: ShipD 64.2% plausible).
   At ~60 real hulls, learned generation is hopeless; procedural
   generation + learned bands/critics is the demonstrated hybrid. The
   repo's "no neural network, deliberately" is what the evidence supports.

| Topic | Source | Finding → implication |
|---|---|---|
| Series methodology | Todd '63; Keuning (DSYHS); Bailey '76 (NPL); Clement & Blount '63 + Fridsma '69; De Luca & Pensa 2017 (NSS, local `SSN.pdf`); Insel & Molland '92; Grigoropoulos (NTUA) | parent + low-dim distortion; adopt a parent LIBRARY |
| Form-parameter design | Harries & Abt (FRIENDSHIP/CAESES) | section drivers = longitudinal curves with few knots — the target for deadrise/flare/chine genes |
| Cp/LCB variation | Lackenby 1950 | the distortion operator; preserves sections by construction |
| Buildability | stitch-and-glue practice; NSS §2.1 | ruled strakes between chine curves = developable BY CONSTRUCTION |
| Propulsive coefficients | Radojčić 2019 (local PDF); Bailey '82; Blount & Bjarne '89; Wärtsilä clearance practice | w/t carry their CONVENTION as metadata; tip clearance ≥ 0.15–0.20 D is an L0-cheap row |
| MOO practice | arXiv 2403.05832 review; ShipGen's own failure | critic inside the loop as constraints; Pareto, no baked weights |
| Learned generation | Ship-D/ShipGen (MIT), ShipHullGAN | not competitive below ~10³–10⁴ diverse hulls |

## K. Architecture gap (current vs required)

| Required | Current state |
|---|---|
| Independent B(x) design waterline | beam solved from SAC — the root defect |
| Full-form Cp (to ~0.95) and full transom (to ~0.92) | gene ceilings 0.710 / 0.50 |
| Section = knuckle list, ρ(x), multi-chine | 5 fixed control points, one global ρ |
| Stem profile (rake, LOA≠LWL) | plane sections, LOA≡LWL |
| W-sections / tunnel sterns / demihulls | monotone-z assumption in 4 functions |
| Parent library + Lackenby/homothetic distortions | uniform draws from a hyper-box |
| Critic + visual gate in the loop | zero production callers; render is post-hoc |
| Mission binds beam/family/berths/headroom | parsed and discarded |
| Propulsion levers in the decision vector | on EnergySpec; reader-only rows |
| Corpus consumed at runtime | transcribed literals + comments only |

## L. Proposed target architecture

    Reference corpus (hull_kb + E5 + owner hulls + negative fixtures)
      → HULL KNOWLEDGE BASE (families, parents, bands, w/t with conventions)
      → HullIR:  family/parent id
               + distortion vector (Lackenby shift, homothetic B/T, L/∇^⅓)
               + longitudinal form curves (SAC, B(x) DWL, deadrise(x),
                 flare(x), chine y/z(x), ρ(x), keel(x) w/ stem profile)
               + section family (knuckle list)
               + topology (mono | W-stern | demihull+layout | split)
               + propulsion architecture (enum: shaft/pod/tunnel/outboard →
                 selects which constraint rows EXIST) + envelope
               + manufacturing route (sheet-kit | mould) chosen up front
      → parametric kernel (extended geometry.py; closed forms kept)
      → GATES, in ladder order: L0 params → L1 geometry → G-Section →
        G-Longitudinal → G-Bow/G-Stern → G-Morph (critique+design_rules+
        manifold_score AS ROWS) → G-Visual (7 canonical views + descriptor
        sheet on EVERY delivered hull, diffed) → L2 watertight (wired) →
        hydrostatics → propulsion integration → mesh → CFD → optimization
        (critic inside the loop; volume-per-build-area replaces raw deck
        penalty; GM band becomes a CONSTRAINT, not an objective)
      → design knowledge (measured causal records only)

  The G-Visual v1 is composable TODAY from committed code:
  `critique(d).ok ∧ manifold_score ≥ τ ∧ fairness ≤ φ ∧ max_facet_turn ≤ κ
  ∧ feature-edge count in corpus band`, computed on the delivered mesh via
  `morphology.from_mesh`, with the seven canonical views written beside the
  numbers. Calibrate τ/φ/κ on the 58-hull positive corpus and the
  reproducible negative fixtures (plank, spearhead, box — already in-tree).

## M. Migration plan (staged; each phase independently shippable)

**KEEP**: hydrostatics tier (strongest in the tree), honesty machinery
(gates 0G/0R/L/L2/EP), the closed-form kernel style, NSGA-II + constraint
vector, mesh_repair's refuse-don't-heal, the POST_HOC no-op discipline.
**MODIFY**: grammar bounds, samplers, objectives, mission parser, formlib
verdicts, `_REPAIR` table. **REPLACE**: 5-point section (generalize to
knuckle list), polygon-wire loft (spline wires). **ADD**: B(x), stem
profile, parent library, IR, gates G-Morph/G-Visual/G-Stern/G-Bow,
propulsion architecture enum. **REMOVE**: dead `l_pmb` reference, stale
formlib rows (re-verdict), the stale `policy/` "unwired" label.

- **Phase 0 — wire what exists (days, no representation change).**
  (a) `critique` + `design_rules` into `evaluate` as report + constraint
  rows; `manifold_score` for OOD-shape refusal. (b) G-Visual render
  artifact on every delivered hull. (c) Fix `sac_exponents` to receive
  `pmb`/`r_stem` (closes the LCB-punishes-the-fix trap — measure the
  estimate in D.4 first). (d) Decouple flare law from `env`.
  (e) `_REPAIR`: `l_pmb`→`pmb`, add `r_stem`; add a NAMES-membership
  assertion. (f) Re-verdict formlib's stale rows. (g) Update the
  LIVE_SYSTEM_MAP/policy labels.
- **Phase 1 — sampler coverage (a deliberate re-baselining event).**
  Post-hoc genes explored on a separate RNG stream; retrain surrogate/
  generative/populations; recalibrate Gate 4F. Same class as the arity
  16→20 event; planned, not incidental.
- **Phase 2 — the CORE-gene recalibration event.** `r_transom` 0.50→~0.92,
  `Cp` ceiling →~0.95, `beta_mid` ceiling up; land the held barge test;
  mission gains `bwl_hint_m`, `family`, `berths`, `air_draft_max_m` as
  bounds/rows; objectives rework (GM band → constraint; deck area moves
  from cost to the value side via volume-per-build-area); wire
  `arrangement` as the `accommodation` row.
- **Phase 3 — section generality.** Knuckle-list sections, ρ(x), chine
  curves as designed quantities, keel extent genes; `chine_row` becomes
  per-station.
- **Phase 4 — topology.** (A) drop z-monotonicity (4 functions) — the
  owner-approved houseboat17 W-stern becomes IN-genome; then (B) the inner
  boundary for true wet-deck/tunnel sections (hookprobe's generalisation,
  `y_inner ≡ 0` as the proven no-op).
- **Phase 5 — parents + distortions.** Parent library (per family, incl. a
  developable NSS-style planing parent and the owner's hybrid), Lackenby +
  homothetic operators, corpus-retrieval seeding of NSGA-II populations.
- **Phase 6 — propulsion architecture.** Enum + envelope in the IR,
  drive-conditional rows (tip clearance ≥ 0.15–0.20 D; shaft angle),
  promoting n_props/recess into the decision space; wake-first mode.
- **Phase 7 — CFD.** Gates 2M/2U off RED; the §24 propulsion variant
  experiment; only then wake-quality bars and the causal KB.

**Ranked by incidents caught** (each recorded incident named): Phase 0(a)+
(b) alone would have refused every hull in the incident record — the plank,
the spearhead, the paddle boat, the fishing-boat complaint — at a cost of
days, because the machinery is already written, tested, and calibrated.

## N. Function-level and gate-level detail

The four full audit reports (function table with 20 rows, 79-gate
enumeration with false-positive/negative analysis, research matrix with
~30 sourced rows) were produced 2026-08-26 by parallel audit agents; their
load-bearing content is folded into §A–§M above. Key per-function rows:

| Function | Problem | Evidence | Change | Pri |
|---|---|---|---|---|
| `sac_exponents` | never receives pmb/r_stem → delivered Cp/LCB drift → lcb row punishes the anti-spearhead gene | geometry.py:328-329 vs 352-357; evaluate.py:1124 | pass both; extend `_sac_terms` | P0 |
| `_stations` flare | `f = tan(flare)·env` re-couples flare to area; `flare_bow` no-op at stem | geometry.py:522 | split closure env from flare law | P0 |
| `grammar.sample` / `sample_valid` / `_pin_post_hoc` | 7 genes never drawn; all trained models blind | grammar.py:672; evaluate.py:431-443; generative.py:126-128 | explore on separate RNG stream | P0 |
| `optimize._score` | F rewards spearheads (Wh/nm) and boxes-away (deck as cost, GM-band beam tax); critic absent | optimize.py:58,66-68 | critic row; volume-per-area; GM→constraint | P0 |
| `mission.parse_mission` | beam DISCARDED; no family/berths/headroom fields | mission.py:669,758,787-790 | add fields → bounds/rows | P0 |
| corpus files | zero runtime consumption | manifold_bands 0 call sites; bands transcribed as literals | load at import; retrieval seeding | P0 |
| `sample_section`/`section_control`/`_rho` | 5 points, one chine, one radius | geometry.py:695,1039,997 | knuckle list + ρ(x) | P1 |
| `_halfbreadth_at`/`_immersed` | monotone-z topology blocker | geometry.py:2069,1777 | segment scan / polygon clip | P1 |
| `PARAMS` ceilings | Cp 0.710, r_transom 0.50, beta_mid 25° | grammar.py:270,275,277 | Phase-2 recalibration | P1 |
| `export._station_wires` | polygon wires, ruled loft; 2 mm stem hack | export.py:197-202,429 | spline wires, smooth loft | P1 |
| `sac_ordinate` | SAC has a CORNER at x_mb unless pf>1∧pa<1 — candidate mechanism for convexity 0.512 | geometry.py:180-184,352-357 | constrain the solve or spline SAC | P1 |
| `design_report.main` | certifies a fixed hull, no search | design_report.py:117-121 | route through the front | P0 |
| `morphology_search._REPAIR` | dead + stale (`l_pmb`); missing r_stem/pmb | morphology_search.py:57-67 | fix and wire as post-front repair | P1 |
| `NSGA2(...)` defaults | blind SBX/PM, ~1 gene/individual/gen | optimize.py:258 | feature-group operators + repair | P1 |
| `propulsion.rows_for` | levers not in decision vector | propulsion.py:246-283; optimize.py:159 | promote to variables | P1 |
| `arrangement.py` | zero importers; berths unverifiable | grep ∅ | wire as accommodation row | P1 |

Missing gates ranked (see §I and the gates report): 1 G-Morph-production
(~1 day), 2 G-Visual (~2 days), 3 G-Stern (needs Phase-2 recalibration),
4 G-Bow (~0.5 day — rules already written), 5 G-Longitudinal/SAC,
6 G-Sampler-coverage (Phase 1), 7 G-Topology (wire stl_forensics),
8 G-Propulsion-extend, 9 G-Mission-dimensional, 10 G-Section families,
11 G-Buildability-enforced (Gate 6D is RED at 24.8× the bar).

## O. The one-paragraph verdict

Naval-AI is rigorous about everything except shape. The kernel gained the
anti-spearhead and anti-box genes on 2026-08-24, but the samplers pin them
to zero, the SAC solver mis-delivers Cp/LCB when they are used (so a gate
punishes them), the flare fix is multiplied away by the area envelope, the
optimizer's objectives reward exactly the two pathologies complained
about, the mission's most product-defining words (beam, houseboat, berths)
are parsed and discarded, two gene ceilings (Cp 0.710, r_transom 0.50)
exclude the entire full-form recreational family, and the only code that
can say "this is not a boat" — calibrated, tested, and proven against
every recorded incident — has no callers. The fix is therefore staged
wiring and recalibration, not a rewrite: the professional representation
the research prescribes (parents + longitudinal form curves + low-dim
distortions, critic inside the loop, visual gate on every delivered hull)
is reachable from the existing kernel in seven phases, of which Phase 0 is
days of work and would already have refused every hull in the incident
record.
