# End-to-end integration audit — 2026-09-01

**Ask:** validate NavalAI as ONE pipeline rather than as a set of subsystems.
Find integration defects between individually-correct parts, prove them, fix
them in code, and say what remains.

**Method:** measure on this checkout. Every number below was produced by
running the product's own functions; nothing is read from a document. The
audit's own instrument is the FLOW TRACE — one realistic brief driven through
every production stage with every receipt printed — and three of the findings
below were produced by that trace and by nothing else.

**The premise the audit had to work against:** `python -m pytest tests/ -q`
was **2094 passed, 14 skipped, 0 failed** (33 m 32 s) when it started. Every
defect here is one a fully green suite does not catch, because each is an
AGREEMENT BETWEEN TWO SUBSYSTEMS rather than a property of either.

---

## 1 · Defect register

Severity: P0 correctness/physics · P1 production flow broken · P2 integration
gap · P3 maintainability · P4 documentation.

| ID | Sev | Subsystem | Defect | Evidence | Root cause | Fix | Test | Status |
|---|---|---|---|---|---|---|---|---|
| F1 | P1 | geometry → descriptors | `form_coefficients` measured a hull the ladder does not float | split hull: V 31.04 vs 28.86 m³, **Cm 1.1514**, Awp +6.33%; ch2: V −1.9%, Awp −6.19% | a SECOND copy of the sectional area and the waterplane, blind to notch/hole/knuckle chain | `immersed_arguments` is the ONE construction; `form_coefficients` reads it | Gate DELIVERED-FORM | **FIXED** `c5a2951` |
| F2 | P1 | geometry | `ch2_y` silently changes displacement | +0.39% vol at 0.02, +1.96% at 0.10, +4.55% of max section at the 0.25 ceiling | the knuckle wedge is not in the section solve's target (notch/hole are) | MEASURED + REPORTED via `sac_deviation`; gene withheld from every draw | Gate DELIVERED-FORM | **RECORDED** (kernel work owed) |
| F3 | P1 | tests | a guard that could not fire | `test_a_chine_above_the_waterline_leaves_the_hydrostatics_alone` passes only because its fixture floats below its turn of bilge | proposition is false: a dry knuckle redirects the leg beneath it | replaced by `test_a_dry_second_chine_still_moves_the_immersed_area` | Gate DELIVERED-FORM | **FIXED** `c5a2951` |
| F4 | P2 | propulsion ↔ geometry | a declared `prop_tunnel_recess_m` credited to a hull with no tunnel | flat hull, recess 0.50 → `prop_space` +0.1315 → −0.1948; tunnelled hull IDENTICAL | the spec was read, the hull never was | `credited_recess_m` = min(declared, drawn at the prop station) | Gate PROP (5 new cases) | **FIXED** `daf7a97` |
| F5 | P2 | ui | `/generate` conditioned the SCORE on the mission, not the DRAW | 16 m × 4 m brief → LWL 11.71–19.97, BWL 2.20–4.81 | one global generator fit on `_mission_default` | `get_model` keyed by mission | `test_the_generator_is_told_the_mission…` | **FIXED** `16854d6` |
| F6 | P1 | search | 13 of 20 post-hoc genes unreachable from every production generator | dwl, tun_crown, split_w, ch2_y, rho_len **exactly 0.000 in all 128** UI candidates; NSGA-II front likewise | draw box pins them; the exploring stream drew 7 of 20 | classified BLIND / REQUESTED / WITHHELD-with-a-measurement | Gate REACHABILITY (11 cases) | **FIXED** `460b347` |
| F7 | P3 | cfd-kb | the harvester's Ct guard used a density no run used | guard at ρ 1025.0, every case solved at 998.8; implied ρ 998.7–998.8 on all 8 records | a second density inside the fence built to stop a second density | guard calls `post.resistance_coefficient` | reproduces every stored Ct at ratio 1.000000 | **FIXED** `d7bdfbe` |
| F8 | P1 | ui | a catamaran was served the monohull pool | `key(monohull) == key(catamaran)`; shape row −0.128 vs −0.289; catamaran has no energy report | key enumerated 5 of 16 fields by hand | key DERIVED from the dataclass, prose excluded | `test_the_pool_key_covers_every_field…` walks all fields | **FIXED** `16854d6` |
| F9 | P2 | geometry | a designed waterline can CONTRADICT the SAC | `rb_stem` 0.25 with `r_stem` 0 → +0.4310% vol, stations [39,40]; **−0.0000%** when the two agree | one station commanded finite beam AND zero area; the solve honours the waterline | `sac_deviation` receipt + diagnosis pinned | Gate DELIVERED-FORM | **MEASURED** |
| F10 | P4 | search | stale arity in a live comment | "8 aft genes of 34 → 24%/49%"; N_PARAMS is 36 → 22.2%/46.2% | a number in a comment cannot be recomputed | `aft_prior_shares()` computes both | fence recomputes from `N_PARAMS` | **FIXED** `460b347` |
| F11 | P3 | docs | `PRODUCTION_CORE.md` said "16-gene parameterisation" | `N_PARAMS` = 36 | one arity event ago | corrected + points at Gate REACHABILITY | — | **FIXED** `460b347` |
| F12 | P1 | search | the OPTIMIZER could not draw the declared architecture | "protected prop" brief → front hull with tun_* = 0 | `_DrawBoxSampling` draws the frozen legacy box | shared feature bundle seeds half the population | Gate REACHABILITY | **FIXED** `7e05ead` |
| F13 | P1 | geometry | a ratio against a fabricated denominator | abs dev 2.26e-10 m² published as **0.22629**; 4.3e+08 on the dwl case | `/max(A_local, 1e-9)` where the SAC closes to ~1e-9 at the stem | scaled by the MAXIMUM section; NaN, never 0.0, when unmeasurable | Gate DELIVERED-FORM | **FIXED** `7e05ead` |
| F14 | P2 | certify ↔ admissibility | CFD-eligible for a hull the screen calls DANGEROUS | flow trace: `eligible True, score 0.776` vs `screen → DANGEROUS` | `certify` consults `select_fidelity`, never the meshability screen | `cfd_candidate["meshability"]` REPORTS the verdict and the metric that refused; not a veto (that is a bar change) | Gate DC | **REPORTED** — veto is the owner's call |
| F15 | P3 | tests/morphology | "beam carried" names two quantities | 88% on the SHEER beam (`test_barge_bow`) vs **0.5854** on the WATERLINE plan, same parent | two quantities, one name | the sheer measure is named `sheer_beam` and says so in its message | Gate BARGE | **FIXED** |
| F17 | P2 | parents | a critic-CLEAN parent distorts into critic-REJECTED seeds | parent ok=True/1.000; 2 of 3 rescaled seeds refused (waist 0.135 vs 0.120; convexity 0.585 vs 0.700) | the barge band was set 0.015 outside that one parent | seeds placed where the climb repairs them | — | **PARTIAL** `7e05ead` |
| F18 | P2 | search | the repair judged by the wrong bands | climb used the GENERAL bars; `evaluate`'s `shape` row uses the FAMILY's — they differ on the three descriptors the barge row exists to relax | `critique(d)` with no family | family threaded through `inspect`/`search`/the climb | Gate REACHABILITY | **FIXED** `7e05ead` |
| F19 | P1 | search | the climb repaired 9 of 9 seeds and the box clip destroyed all 9 | initial population **0 of 24** shape-plausible under a comment claiming "half … climbed to plausibility" | climbed in the grammar box, clipped into the mission box | the climb searches the box it is judged in | Gate REACHABILITY | **FIXED** `7e05ead` |

---

## 2 · Flow matrix — every stage, its consumer, and whether one exists

| Stage | Input | Function | Output | Consumer | Tested | Gated | Production path |
|---|---|---|---|---|---|---|---|
| Mission | free text | `mission.parse_mission` | `MissionSpec` (16 fields) | grammar box, evaluate, certify, UI | yes | Gate 1 | **yes** |
| Feature request | MissionSpec | `grammar.features_for` | frozenset of architectures | `sample_valid`, `_DrawBoxSampling` | yes | REACHABILITY | **yes** (new) |
| Draw box | mission + policy | `sample_valid` / `grammar.sample` | genome population | optimizer, UI pool, surrogate feed | yes | 0, 4F | **yes** |
| Parent retrieval | `hull_family` | `parents.seed_for_mission` | ≤¼ of the population | `_DrawBoxSampling` | yes | P5 | **yes** |
| Shape repair | genome + family + box | `morphology_search.search` | plausible genome | `_DrawBoxSampling`, `agents` | yes | MORPH | **yes** |
| Genome | 36 genes | `grammar.check` | L0 verdict | evaluate | yes | 0 | **yes** |
| Geometry | genome | `geometry.Hull` | stations, SAC, sections, STL | hydrostatics, resistance, formcheck, CFD | yes | 0E5, RHO-X, TUNNEL, SPLIT, MULTI-CHINE | **yes** |
| Delivered form | Hull | `form_coefficients`, `sac_deviation` | Cp/Cm/Cwp/Cb + delivered-vs-commanded | formcheck → critic → certify | yes | **DELIVERED-FORM** | **yes** |
| Hydrostatics | Hull + mass | `hydrostatics.solve*` | float state, GM, trim | evaluate | yes | 2 | **yes** |
| Resistance | float state | `resistance.total_resistance` | Rt ± σ, method receipt | energy, certify | yes | 2, CFD-CMP | **yes** |
| Propulsion | Hull + float + spec | `propulsion.rows_for` / `assess` | 2 constraint rows + report | `Evaluation.g`, NSGA-II | yes | **PROP** (+5 geometry-coupling cases) | **yes** |
| Morphology | Hull + family | `morphology.critique` | `shape` row + findings | `Evaluation.g`, the climb | yes | MORPH, PF | **yes** |
| Ladder | genome + mission | `evaluate.evaluate` | `Evaluation` (11 g rows, badges) | optimizer, certify, UI | yes | many | **yes** |
| Selection | mission | `optimize.pareto_front` | front | UI `/pareto`, design | yes | 5 | **yes** |
| Certification | genome + mission | `certify.certify` | ACCEPT/MARGINAL/REFUSE + `cfd_candidate` | design report | yes | 6D | **yes** |
| CFD preflight | question, sha, Fn | `cfd/preflight.*` | refuse-or-proceed + reasons | `planner.plan`, `make_case --stl` | yes | PREFLIGHT | **research + CLI** ⚠ |
| CFD manifest | Evaluation | `cfd/manifest.manifest_from_evaluation` | the one vessel description | `make_case --case` | yes | — | **yes** |
| Admissibility | Hull + speed | `admissibility.screen` | meshability verdict | `write_resistance_case` (fatal) **and** `certify.cfd_candidate` (report) | yes | 2A, DC | **yes** |
| Mesh/CFD | STL + manifest | `cfd/case.py`, `run-case.sh` | case + forces | `post`, `gate2m` | yes | 2M/2U (RED by record) | operator |
| CFD knowledge | runs | `harvest_cfd_anchors` → `cfd_kb` | anchor book | `resistance` (NOTE only), preflight | yes | CFD-KB, CFD-CMP | **yes**, deliberately open-loop |

**Any missing consumer is a finding.** One remains: the preflight policy does
not gate the PRODUCTION CFD-candidate decision — it gates `planner`, which
`docs/LIVE_SYSTEM_MAP.md` classifies as RESEARCH, and the `make_case --stl`
CLI. `certify` now reports the meshability verdict beside its eligibility
(F14), so the two no longer contradict each other silently.

---

## 3 · Feature matrix

| Feature | Implemented | Tested | Gated | Production wired | Physics wired | Search wired | CFD wired |
|---|---|---|---|---|---|---|---|
| DWL (`dwl`,`cwp_x`,`rb_*`) | yes | yes | DWL | yes | yes | **`_derived_dwl` only** — blind draw is a REFUTED move | yes |
| rho(x) | yes | yes | RHO-X | yes | yes | **yes** (new: drawn blind) | yes |
| knuckle / multi-chine | yes | yes | MULTI-CHINE | yes | yes — SAC drift now MEASURED | **withheld** until the wedge folds in | yes |
| split stern | yes | yes | SPLIT | yes | yes | withheld — no mission field expresses it | yes |
| W-stern / tunnel | yes | yes | TUNNEL | yes | yes | **yes** (new: mission-REQUESTED bundle) | yes |
| pmb | yes | yes | 0E5 | yes | yes | yes | yes |
| wave-piercing (`stem_depth`,`flare_bow/len`) | yes | yes | 0E5 | yes | yes | yes | yes |
| r_stem | yes | yes | BARGE | yes | yes | yes | yes |
| propulsion | yes | yes | **PROP** (+5 geometry-coupling cases) | yes | **2 constraint rows** | via the rows | manifest |
| wake deficit | yes | yes | PROP | yes | REPORT only (declared) | no | no |
| CFD priors | yes | yes | CFD-KB | yes | NOTE only (declared) | no | n/a |
| aft-mutation prior | yes | yes | REACHABILITY | yes | n/a | **yes** — search ORDER only | n/a |
| parent library | yes | yes | P5 | yes | n/a | yes (F17 partial) | n/a |
| HULL-KB | yes | yes | HULL-KB | yes | n/a | via parents | n/a |
| MORPH / BARGE | yes | yes | MORPH, PF, BARGE | yes | `shape` row | **yes** (family now threaded) | n/a |

---

## 4 · Gaps, separated

**FIXED (7 commits):** F1, F3, F4, F5, F6, F7, F8, F10, F11, F12, F13, F18, F19.

**REMAINING (code, this tree could do).** F2 — fold the second chine's knuckle
wedge into the section solve, so `ch2_*` can be drawn. NOT ATTEMPTED HERE, and
the reason is proportion rather than difficulty: it is a fixed-point iteration
inside `_stations`' section quadratic — the single most load-bearing function
in the kernel, whose `_tnotch`/`rhs` path is shared with the tunnel, the split
and the dwl joint solve — in exchange for enabling a gene that is currently
withheld from every production stream, so nothing ships with the drift today.
The derivation is done and is handed over rather than left to be rediscovered:

    the knuckle redirects the topside leg below it from slope f (chine -> sheer)
    to slope f + D, where   D = ch2_y * max(yc, y_sheer) / (ch2_z * (zs - zc))
    the extra immersed HALF-area is 0.5 * h^2 * D,  h = -z_chine = d - m*yc
    and since y_wl = K*yc + d*f = yc + f*h, the closed form's topside term
    absorbs it as f -> f + D in BOTH `rhs = A - d*d*f` and `y_wl`.

D is linear in yc and in f, both of which the solve produces, so a Picard
iteration (solve, recompute D, re-solve) is the shape of the fix; two or three
passes should suffice at a drift of at most 4.55% of the maximum section. The
acceptance bar already exists: `Hull.sac_deviation_rel()` must fall below 1e-9
and `ch2` must move from the WITHHELD set to BLIND in Gate REACHABILITY.

F14's remaining half — whether meshability should VETO CFD eligibility rather than only be
reported beside it; that is a bar change and needs its own calibration, and
the screen's thresholds carry a recorded 16-gene transfer caveat.

**BLOCKED BY EXTERNAL EVIDENCE:** Gate 2M's number and Gate 2U (compute hours
+ the owner's approval; unchanged by this audit). The pressure
over-prediction (BUILD-PLAN bucket B) is untouched here.

**CORRECT REFUSALS — do not "fix" these.** CFD is an anchor, not a loop
(`l1_anchor_ratio` reaches `resistance` as a NOTE carrying its own
prohibition). `design_report --mission` certifies the REFERENCE hull and says
so — it is a certification CLI, not a design CLI. `Hull.section_area` stays an
INDEPENDENT algebraic derivation and now REFUSES rather than answering
wrongly. The imported-STL lane repairs winding and refuses holes; the
generated lane does not heal at all. The surrogate's default target
(`wh_per_nm`) IS the optimizer's objective 1. Blind `dwl` nudging stays
withheld — it is a measured negative result, not an omission.

---

## 5 · Architectural risks — not bugs yet

- **The shape row is a FLOOR and nothing rewards carried beam.** Delivered
  fronts sit at `beam_carried` 0.220–0.244 against a 0.20 SPEARHEAD floor,
  while the proven `liveaboard-barge` parent measures 0.585. Objective 3
  ("build area per m² of usable deck") is meant to reward exactly this and
  measurably does not, because `deck_area` is the sheer plan and a long
  tapered hull still has plenty of it.
- **A tunnel costs flotation and buys only a constraint.** It relieves
  `prop_space`, enters no objective, and loses ~⅓ of a population's flotation
  solutions — so the search discards it whenever `prop_space` can be met
  another way. Measured on two briefs; on both it is discarded.
- **The shape-plausible region inside a dimensioned mission's own box is
  nearly empty at the repair's reach**: 1 of 12 against 9–10 of 11 in the
  grammar box, at 60 AND 200 iterations. The box clip was hiding this.
- **The barge critic band has ~0.015 of margin around ONE parent**, so any
  distortion of that parent leaves it.
- **Companion-gated genes are unreachable by mutation.** Any feature needing
  2–3 genes non-zero at once cannot be found by polynomial mutation from an
  all-zero start; every such feature needs an explicit bundle. This is a
  property of the representation and will recur with every new phase.
- **Genome growth**: 16 → 36 genes in a fortnight, and the classification of
  which are reachable is now a tested fact (Gate REACHABILITY) precisely so
  the next arity event cannot silently repeat F6.

---

## 6 · The question this audit was built to answer

> *If I ask NavalAI today to design a new 16 m recreational coastal/inland
> boat, exactly which code path runs?*

`mission.parse_mission` → `grammar.features_for` → `optimize.pareto_front`
(NSGA-II over 36 genes, box = grammar ∩ policy ∩ `lwl_hint` ±10% ∩
`bwl_hint` ±10% ∩ the Froude window on Cp; initial population = the frozen
draw box, ¼ seeded from `parents` on even rows, half climbed to family-aware
plausibility inside that same box, half odd rows carrying the requested
architecture) → per candidate `evaluate.evaluate` (L0 `grammar.check` → `Hull`
→ `hydrostatics.solve_to_displacement`/`solve_equilibrium` → `weights` →
`resistance` → `energy` → `rules` → `propulsion.rows_for` →
`morphology.critique`) returning 3 objectives and 11 constraint rows →
`certify.certify` (verdict + `cfd_candidate`) → `cfd/manifest` →
`admissibility.screen` → `cfd/case.py` → `run-case.sh` → `post` →
`harvest_cfd_anchors` → `cfd_kb` → `preflight`.

Cheap checks that reject candidates: `grammar.check` (0.24 ms), the flotation
solve, the 11 constraint rows, the `shape` critic. CFD is purchased only where
`select_fidelity` says it is both admissible and decision-worthy; it never
executes inside L0/L1 — `evaluate` contains no subprocess, and the whole L1
call is 13.6 ms. The CFD result returns as an anchor book that informs a
report-tier NOTE and the preflight refusals; it does NOT close a loop into the
optimizer, by decision. Final proof that the object is a boat: the `shape`
row, the ISO rules row, the flotation solve, `Gate DELIVERED-FORM` (the
descriptors describe the hull the ladder floats) and `Gate PF`/`BARGE`.

A full trace of one such run, with every receipt, is reproducible from
`docs/audit/` — the script is short enough to rewrite; the values in §1 are
what it printed.

---

## 7 · Round two — the gap sweep, and the small-boat flow

The first pass fixed seams found by reading and by one flow trace. This pass
built the instrument (`scripts/gap_sweep.py`, Gate SWEEP) and drove a SMALL
boat end to end, which is a different population and found different things.

### 7.1 · What the register actually holds

`python scripts/reconcile_gaps.py`: **123 rows, 117 closed, 3 open, 1
needs-human, 2 retired** — unchanged by this audit, which is the point. The
four non-closed rows are **not code**:

| row | blocker | price |
|---|---|---|
| F16 (Gate 2M) | compute | ~69 h for a settled GCI triplet |
| F17 (Gate 2U) | compute | hours × N hulls, `mesh_robustness --solve` |
| I13 | a human — an agent cannot be the non-expert | — |
| N6 | a human — the predicate would have to read prose semantics | — |

Gate 2M and Gate 2U come up for **review on 2026-09-06**. The gate ladder is
`exit 0`: five RED gates (2M, 2U, 4F, 6D, 0E5C-CAP), all carried by
`data/gate-ledger.json` with watermark, owner and review date, and no new red.

**So an "automated fixer" cannot close a single remaining register gap**, and
one that claimed to would be the failure the ledger exists to prevent. The
code-shaped gaps live at the SEAMS, which the register does not model — every
one of F1–F19 was a seam, and none was a row.

### 7.2 · Round-two defect register

| ID | Sev | Subsystem | Defect | Evidence | Fix | Status |
|---|---|---|---|---|---|---|
| F20 | P1 | ladder | a 200 t brief CRASHED the optimizer | `parse_mission` clamps to 200 000 kg; `select_stock_thickness_m` raises out of `evaluate` and out of `_score`; `pareto_front` dies | the scantling refusal returns as an `Evaluation` carrying the rule's words verbatim | **FIXED** `ca46d9a` |
| F21 | P1 | mission | the brief could not state its ENGINE | "60 kW outboard" → `motor_kw` 15.0 (the default), while `motor_power` is a live row binding 497 of 720 candidates | kW + hp parsed, clamped and announced | **FIXED** `e037185` |
| F22 | P1 | search | an empty front said NOTHING | 720 evaluations, 0 designs, empty array; the binding row was computed 720 times and discarded | `ParetoResult.why_empty()` off a per-row tally | **FIXED** `e037185` |
| F23 | P1 | geometry → cfd | delivered designs produce a NON-WATERTIGHT STL | 3 of 6 front members of the 8 m launch; 13 open edges; 0 of 30 sampled hulls | `closed_mesh` drops a triangle for TWO IDENTICAL VERTICES, never for a small area — a zero-area triangle with three distinct vertices IS the seam | **FIXED** `4daac14` + round three |
| F24 | P2 | certify | meshability SAFE did not cover closure | `eligible True, meshability SAFE` for a hull the case writer refuses | `does_not_cover` names it; a cheap check was measured and REFUSED as a false-green | **NAMED** `4daac14` |
| F25 | P3 | geometry → hydrostatics | the split's BM is not converged at 41 stations | −0.532% alone, −1.506% with dwl, vs ≤0.052% for every other feature | measured, and the probe is COUPLED to the split's withheld status — it turns P1 on promotion | **RECORDED** `eb85a7b` |
| F26 | P2 | grammar | two gene boxes jointly exclude a region one was widened to reach | see below | — | **OPEN** |

### 7.3 · F26 — the transom the grammar can draw and cannot float

`r_transom` was widened to 0.92 on 2026-08-26 expressly to reach the published
planing canon (`morphology_families.HARD_CHINE_PLANING` records
`transom_area_ratio` **0.8–0.94**, De Luca & Pensa 2017 Table 1). MEASURED
2026-09-01: the largest `r_transom` whose DELIVERABLE LCB band still intersects
the `lcb` gene's own ±3 %LWL box:

| Cp | 0.55 | 0.62 | 0.69 | 0.78 | 0.90 |
|---|---|---|---|---|---|
| max `r_transom` | 0.47–0.54 | 0.55–0.61 | 0.64–0.70 | 0.77–0.80 | 0.92 |

At `r_transom` 0.85 the deliverable band is **entirely outside** the gene box
at every `x_mb` from 0.42 to 0.60 (e.g. −13.4 … −9.0 %LWL), so the hull is
L0-refused for EVERY value of `lcb`. The mission-driven Cp for a planing
dinghy at Fn 0.54 is 0.673–0.710, which caps the transom at ~0.65–0.70. **The
planing canon is expressible in one gene and refused by another.**

`LCB_BAND_PCT_LWL = 3.0` states its own provenance: *"displacement-hull
practice (Holtrop's own lcb regressor spans roughly −4..+2% for the merchant
hulls behind it) … a PRACTICE figure, basis approx."* It is being applied to
planing hulls, whose LCB is legitimately far aft. That is the shape of two
defects this tree has already fixed — the demihull L/B false positive
(a 58-monohull corpus condemning demihulls) and the barge critic bands (which
made "every houseboat mission's shape row unsatisfiable BY CONSTRUCTION").

**NOT FIXED, and the reason is evidence, not effort.** The in-idiom repair is
a regime-specific band beside `morphology._FAMILY_BAR` and
`grammar.PROPORTION_BANDS` — and this tree holds **no sourced planing LCB
range**. The families table records transom area, deadrise at three stations
and L/B, and no LCB. Widening a band without a source is the one move this
repository forbids. What is owed is the evidence: an LCB/LCG range from the
planing series already cited (Naples NSS, Clement & Blount, Keuning), after
which the band is a two-line change beside the ones that precede it.

### 7.4 · The small boat, end to end

**"8 m river launch, 6 knots, 2 tonne, category C, 2 berths"** — the product
line's own size. 36 designs from 720 candidates (238 feasible); chosen
LWL 8.75 m, BWL 2.93 m, T 0.724 m, Cp 0.621; floats at 0.310 m with 0.973 m of
freeboard, GM 0.698 m, trim −0.40°; 298.4 ± 47.1 N at 6 kn (Fn 0.333); 303.4
Wh/NM at 1.82 kW. **All eleven constraint rows satisfied**, critic plausible
(score 1.000), verdict **MARGINAL** (`rules` thin; delivered Cp 0.620 misses
the 0.599 target). Production: 15 mm ply, STEP solid exported, CFD-eligible
(score 0.781), meshability SAFE, prop 0.218 m needed against 0.514 m
available, transom Fn 2.76 against a 2.5 clean bar.

Two production truths the run surfaced, both CORRECT REFUSALS stated by the
system in its own words:

- **it is not sheet-buildable.** roundness 0.776, so `unroll.hull_panels` and
  `buildability.shell_complexity` both refuse — *"a radiused bilge is doubly
  curved and not developable from flat sheet, which is a fact about the
  material."* The kit line's developability is a POLICY row, applied only when
  a constitution is compiled; an ungoverned run is free to draw a moulded
  hull. That is the design, and `certify.buildability` carries the refusal.
- **3 of its 6 front members cannot be meshed** (F23).

**"6 m dinghy with an outboard, 8 knots, 900 kg"** — refused, and the refusal
is right. Fn 0.536 is semi-planing; a 15 kW motor's 12 kW continuous rating
cannot push it (`motor_power` worst on 373 of 720). With the engine raised the
blockers become `rules`, `gm`, `prop_space`, `bend_radius` — a plywood
displacement product line declining a planing dinghy. The same hull designs at
6 kn (27 members, GM 0.49 m) and 5 kn (18 members). What was broken was the
SILENCE, and that is fixed.

### 7.5 · The mechanism, and what it is honestly for

`scripts/gap_sweep.py` — 12 probes, 4.0 s, Gate SWEEP. It is a SEARCH beside
the suite's ratchet: a property swept over a generated population rather than
a pinned answer. It caught its own first version making the error it exists to
catch (comparing 401-station descriptors against 41-station integrals and
calling the difference a defect), and that mistake led to F25.

It cannot close a compute-blocked or human-blocked gap, and it does not
pretend to. What it does is make the seam class — the class that produced
every defect in this document — mechanically checkable on every push, with the
ledger's own rule: a declared finding is carried with its number and its
reason, a new one fails, a stale declaration fails, and **nothing above P3 may
be merely declared**.

---

## 8 · Round three — the seam that was a hole, and the evidence that was there

### 8.1 · F23 FIXED — a zero-area triangle with three distinct vertices is the SEAM

The deferred "welded emit" turned out not to be the fix, and the real one is
two lines. `Hull.closed_mesh` dropped a triangle when `area > 1e-10` failed.
At the transom of the recorded genome, rows 0 and 1 land at **exactly** the
same z (a raised keel, rocker 0.506, meeting a nearly-flat floor, beta_mid
1.61°), so the cap's bottom quad is four points on a line. Its second triangle
has three DISTINCT vertices and zero area — and it is the only face pairing the
starboard shell's edge `S[0,0]→S[0,1]` with the port shell's `P[0,0]→P[0,1]`.
Dropping it left the two shells meeting at a **pinch point**, not a seam.

**Degeneracy is a statement about VERTICES.** The rule is now "drop iff two
vertices are identical", and:

| hull | `area > 1e-10` | identical-vertex rule |
|---|---|---|
| failing 80×16 | 3 open, 5243 tris | **0 open**, 5244 |
| failing 200×40 | 7 open, 32311 | **0 open**, 32316 |
| failing 600×120 | — | **0 open**, 288956 |
| reference 80×16 | 0 open, 5232 | 0 open, **5232** |
| reference 200×40 | 0 open, 32284 | 0 open, **32284** |
| 4 sampled hulls | — | identical at both resolutions |

The old kept-set is a strict SUBSET of the new one (identical vertices imply
zero area), so equal counts **prove** the mesh is bit-identical on every hull
that was already closed. `write_resistance_case` now ACCEPTS the recorded hull
(watertight, 0 open edges). 150 tests across geometry, STL forensics, case
wiring, mesh repair and manufacturing pass.

Two hypotheses were refuted first and are recorded in the kernel so nobody
re-tries them: it is not the sliver bar dropping one side of a shared edge, and
keeping ALL degenerate cap triangles makes it worse (3 open edges → 20).

**And broadening the probe found a new one.** The SPLIT STERN's surface does
not close at all — **57 open edges at 80×16, 141 at 200×40** — because
`closed_mesh` builds a starboard shell, a port shell, a deck lid and two caps,
and the split's inner walls and wet deck are drawn by none of them. The
hydrostatics integrate the hole; the mesh never learned to. Withheld from
production, contract held by the case writer, coupled to reachability, and now
the **second** recorded blocker on promoting the split.

### 8.2 · F26 — my "no sourced range in tree" was FALSE

Round two recorded that a planing LCB band could not be sourced from this tree.
**That was wrong, and it was wrong the way this repository has a lesson about:
a negative result about the literature is a claim about your search, and mine
was two greps.** `docs/research/HULL-FORM-RULES.md` §7.3 tabulates eight
published centres and states the consequence outright:

> *"`LCB_BAND_PCT_LWL` is a band of ±3% and the sources put the CENTRE at −5 to
> −12% depending on speed … A ±3% band applied around midships would exclude
> every semi-displacement series in the table above."*

| series | LCB %Lwl | Fn | expressible by the `lcb` gene? |
|---|---|---|---|
| MARIN FDS semi-displacement transom | −5.19 … −5.05 | 0.14–1.30 | **no** |
| DTMB Series 64 round bilge | −6.56 | 0.06–1.50 | **no** |
| Southampton catamaran demihull | −6.40 | 0.20–1.00 | **no** |
| USCG hard chine | −12.00 | ≤2.54 | **no** |
| semi-displacement min-R/W locus | −10.00 | ~0.6 | **no** |
| NPL round bilge | −6.40 … −2.00 | 0.30–1.20 | yes (one end) |
| Taylor standard series | 0.00 | ≤0.60 | yes (fixed by construction) |
| DSYHS canoe body, 61 hulls | −7.90 … +0.01 | n/s | yes (tail only; median −3.28 is outside) |

**5 of 8 are outside the gene's own box** — and that number was itself wrong at
first: I counted DSYHS by its median and got 6, and the sweep's own probe
caught the arithmetic. The band's comment also records this ladder's delivered
hulls at −6.47 and −7.86 %Lwl, so the system's own output sits outside the band
it is judged by.

**What was fixed, and what was deliberately not.** `mission_lcb_band`'s basis
string said *"UNKNOWN target law — no sourced Fn/topology→LCB relation in
tree"*, and its docstring said *"no source, no series, no measurement"*. Both
were false when written. The evidence now has a home
(`limits.LCB_SOURCED_CENTRES`, `lcb_sourced_span(fn)`, precedented by
`PRISMATIC_BY_FROUDE`) and the receipt tells the truth, including the
uncomfortable part.

**The bar is unchanged**, because §7.3 reserves that decision — *"Whether it is
applied around midships or around a target is a question for `limits.py`'s
owner and is NOT answered here"* — and because most rows are series DATA, not
optima: only Blount's minimum-R/W locus is a measured best. Fitting a curve
through series data and calling it a target would manufacture a recommendation
nobody made. The `evidence` probe now counts the shortfall against a watermark
of 5, so it cannot widen quietly.

**The decision the owner now has, with its numbers**: centring the ±3% band on
an Fn-dependent target would let the grammar express the semi-displacement and
hard-chine canon it currently refuses, and would move every seeded population
and recorded front. That is the trade; the evidence is now in `limits.py` to
take it with.

