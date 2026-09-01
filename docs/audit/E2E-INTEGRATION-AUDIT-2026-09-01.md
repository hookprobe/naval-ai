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

**REMAINING (code, this tree could do):** F2 — fold the second chine's
knuckle wedge into the section solve, so `ch2_*` can be drawn. F14's remaining
half — whether meshability should VETO CFD eligibility rather than only be
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
