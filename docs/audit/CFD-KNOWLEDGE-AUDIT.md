# CFD KNOWLEDGE AUDIT — what the campaigns taught, where it lives, where it must go

**Date: 2026-08-28. Status: AUDIT ONLY — no implementation beyond the
evidence-extraction layer (`data/cfd_anchors.json` + `navalai/cfd_kb.py`,
whose own defects are P0 items below). Per the owner's protocol §1/§47:
the map is reconstructed from the receipts and the code, not from commit
messages.**

The question this audit answers: *how does everything learned from
expensive CFD become reusable design intelligence, so future hulls need
fewer CFD evaluations and converge faster?* The answer has a shape the
evidence forces: the corpus is **6 settled single-grid runs across 4 hull
families, no GCI anywhere** — big enough for RULES, NEAREST-ANCHOR
lookups and REFUSING interpolation; far too small for any fitted
surrogate. The highest-value work is therefore not modelling: it is (a)
fixing the places where measured knowledge is mis-recorded or invites
misreads (P0), (b) wiring the ~30 findings that are correct and PROSE-ONLY
into the pipeline stages that can consume them (P1–P2), and (c) buying the
three specific runs that unlock the most knowledge per hour (P3).

---

## DELIVERABLE A+B — the CFD knowledge inventory, with evidence and class

Classes per the protocol §4: OBSERVED (measured once) / REPEATABLE
(multiple independent cases) / CORRELATED (relationship, causality
uncertain) / HYPOTHESIS (untested) / DOMAIN-VALIDATED (external
literature cited in-tree). Every entry names its cases. Validity domains
are in §"validity" notes; the hookprobe-overfit boundary is drawn in
Deliverable C.

### A.1 Resistance and wave-making

| # | Finding | Evidence | Class |
|---|---|---|---|
| R1 | Bluff/hybrid families are WAVE-DOMINATED: pressure is 78–80% of total at Fn 0.33–0.38 (hb19 77.9%, hookprobe v1 79.9 / v2 79.1 / v3 78.9%), 80.8% at Fn 0.48 (unsettled), 83.4% appendaged; the slender benchmark INVERTS it (KCS 39.2% at Fn 0.26) | runs hb19_7kn, hookprobe_v2/v3/v4 (settled), kcs (settled); anchor book | REPEATABLE |
| R2 | The drag lever on bluff-stern forms is AFT (transom clearance, eased shoulder) — v1→v2→v3 fell 3034→2998→2966 N monotonically under aft edits | campaign ledger; JOURNAL | CORRELATED — each step (−1.1..−1.2%) is INSIDE the ±2.5% window scatter; only the direction was ever claimed, and the ladder carries a mesh confound (A.6-M7) |
| R3 | The L1 chain under-predicts the bluff-stern family total by ~1.57× at Fn 0.33 (RANS 1733 N vs L1 ~1103 N) | runs/hb19_7kn settled 2.22 FT | OBSERVED, single grid — a report-tier expectation, never a correction |
| R4 | KCS converges to the WRONG number and more wall-clock will not fix it: E%D −43.5% at 3.40 FT with drift 0.31%; the error is entirely PRESSURE (2.32×, batch error 36%) while viscous is right (1.161×, error 1.7%) | runs/kcs_s1; CFD.md §2 | OBSERVED (retires the run-length hypothesis) |
| R5 | The viscous-right/pressure-wrong split GENERALIZES: on 16 Gate-2U grammar hulls viscous drift is 0.00–0.67% on every hull while pressure drifts 3.08–21.82% and total tracks pressure | g2u-repeat campaign N=25, ledger Gate 2U | REPEATABLE — the strongest cross-family finding in the corpus |
| R6 | Watanabe (1+k)=1.094±0.05 at KCS proportions vs 1.161 RANS-measured — order corroborated, sigma marginal (0.017 outside 1σ) | resistance.form_factor receipt; kcs_s1 | CORRELATED (one anchor; note kcs_s1 records settled:false in the book — provenance must be pinned to the settled `runs/kcs` or restated) |
| R7 | At Fn 0.477 the hookprobe rides its own bow wave — λ=16.9 m > Lwl 11.8 m, one trough spanning the aft half — the hump, VISUALIZED matching theory | v3_10kn wave profile; case.info wavelength | DOMAIN-VALIDATED |
| R8 | 10-kn resistance is ≥3860 N and RISING (drift 11.5% at 3.09 FT) — quotable only as UNDER-RUN; the transient 3391 N read at 2.37 FT was a false plateau | runs/hookprobe_v3_10kn | OBSERVED, refused as an anchor |
| R9 | The solar reframe: at Fn 0.24 the hierarchy INVERTS to ~55% viscous, fins (48% of wetted) cost ~¼ of power, motor right-sizes to 6–8 kW | PROPULSION-INTEGRATION §6 | HYPOTHESIS — a SCALING across the hump, not a run; the 5-kn measured point is the highest-value missing run in the corpus |
| R10 | **RETRACTED 2026-08-28 — and for a better reason than this audit found.** The Fn 0.956 record was called invalid here for fixed attitude and a failed layer stack (0.1% coverage). The CFD session then found the disqualifying fault: the run sat in a 53.2 m tank against its OWN 67.8 m wave, so the box held 0.78 of ONE wavelength and the wave that makes the pressure drag could not form. `ct_trusted` is now false and the domain rule is a gate row (Gate 2E, commit 75f5f85). The record stays IN the book on purpose — a reader meeting the number elsewhere must be able to find out why it is dead. **The supported hookprobe envelope is Fn 0.24-0.48, calm-resistance records only**; the corrected 147.5 m re-run died at t=20.3 with forces still decaying 3.7x and is refused by the harvester. Nothing may cite a 20-kn or Fn ~0.95 hookprobe number. | runs/hookprobe_v5_20kn; handoff §3 | RETRACTED |
| R11 | Michell's slenderness assumption is violated by the median admissible hull (L/B 3.96, 5–95% 2.39–7.44) and nothing flags it; only Fn gates the wave model | resistance.michell_rw receipt, 4000-draw census | REPEATABLE, un-encoded (under-constraint) |
| R12 | Catamaran interference has no single optimum s/Lwl — it moves with Fn, worth up to 60% of the wave term (−25.2% at s/L 0.30 Fn 0.25; +59.7% at s/L 0.20 Fn 0.40) | resistance experiments (Wigley demihull) | REPEATABLE (numerical); encoded as physics, absent as an optimizer prior |
| R13 | Kelvin transverse wavelength matched theory on the computed wake (10.77 m at 8 kn) — the campaign's stated validation anchor, and the least overfit finding available | campaign doc; case.info | DOMAIN-VALIDATED; un-automated (P1-9) |

### A.2 Propulsion and wake

| # | Finding | Evidence | Class |
|---|---|---|---|
| P1 | The tunnel stays WET at cruise: ≥0.98 water at all prop-plane stations, deep layer at 99–107% U0 (z=−0.4 m, ≥0.5 D behind the keel tail) on all three hulls | campaign inflow tables v1–v3 @ 8 kn | REPEATABLE — the strongest measured feature→flow link in the tree |
| P2 | The near-surface layer carries a 16–30% wake deficit (0.70–0.84 U0 at z=−0.2) — design rule: prop axis in the deep layer | same tables | REPEATABLE; the rule is prose, `DriveLaw` has no vertical axis field |
| P3 | The v2 fin-TE taper improved the near-surface deficit (0.70→0.75, 0.78→0.84) and v3 preserved it | JOURNAL A/B | CORRELATED — the A/B is confounded (v2 has 24% more cells, a 7.5×-coarser bow patch, and 474 self-intersections) |
| P4 | Tunnel inflow DEGRADES GRACEFULLY at the hump: at Fn 0.48 prop depth stays wet (0.96–1.00) at 0.86–1.00 U0, more surface aeration | 10-kn row | OBSERVED (single, unsettled forces; local field read) |
| P5 | The drawn appendage package costs +33% (+979 N, 97% pressure) vs a 3–8% expectation — RESOLVED (far above scatter), settled A/B | v3 vs v4 | OBSERVED — a verdict on THIS drawn geometry, not on appendages |
| P6 | The mechanism is near-surface ring VENTILATION: water fraction 0.00 down to z=−0.65 BEHIND the rings while rings/rudder stay wet | v4 fields | OBSERVED (field) + CORRELATED (attribution); confound: pods were lifted +50 mm by an export repair, so the tested geometry is not the drawn one |
| P7 | The package is a pressure object, not friction: +8.1% wetted bought only +4.7% viscous; the 4-contributor ranking (ring exposure > pod frontal > flat rudder TE base drag > junctions) is diagnostic only | anchors v3/v4 | OBSERVED (split) + HYPOTHESIS (ranking — no per-patch force decomposition was run) |
| P8 | v5 remedies (one pod, axis ≤ −0.4 m, faired, tapered TE, fillets) are UNVALIDATED — the 8-kn v5 A/B never ran | campaign closing | HYPOTHESIS |
| P9 | Disc loading decides the propulsion choice, not motor efficiency: 290 mm rim ~0.57 ideal η, 450 mm shaft 0.72–0.78, twin 420 pods ~0.80, motors differ 2–4 pts; a 300 kgf STATIC spec equals the 8-kn drag → tops out ~7 kn | trade study on settled 2966 N | DOMAIN-VALIDATED (momentum theory) on an OBSERVED drag |
| P10 | Clearance geometry at 8 t: a 420 mm pod fits only aft of the fin TEs with 200 mm submergence; fin tips ground 0.28 m FIRST (fins are prop guards); at 6 t margin falls to ~110 mm | trade study, floated STL | OBSERVED; displacement-sensitive |
| P11 | w/t/η_H (wake fraction, thrust deduction, hull efficiency) are ABSENT as symbols from the entire codebase; a flat 0.55 lumps everything; co-design literature puts >8% resistance on the table | PROPULSION-INTEGRATION §2–3; grep | OBSERVED absence; the >8% is DOMAIN-VALIDATED external |
| P12 | The 12.5% prop-overlap of the flagship concept has NO measured support at any value; the 5/10/15/20% ranking is owed | HULL-KB; naval_ai_concept.py | HYPOTHESIS (fenced arithmetic, unmeasured value) |
| P13 | Transom Fn_T < ~2.5 drags a dead-water eddy: hb19 measures 1.42 @ 5 kn / 1.99 @ 7 kn — deliberately a report, not a row; but the report has NO consumer (`assess()` is never called in navalai/) | propulsion.py; tests | OBSERVED + DOMAIN-VALIDATED threshold; inert receipt |

### A.3 Meshing and numerics (the teacher's own trustworthiness)

| # | Finding | Evidence | Class |
|---|---|---|---|
| M1 | snappy refines isotropically; a 38:1 background folds cells at snap. Fix: near-cubic background → snap → z-only refineMesh → layers-only pass; KCS went 72 988 zero-vol cells → 4 open / 5 wrongOri, coverage 32→75% | CLAUDE.md root cause, 3-level sweep | DOMAIN-VALIDATED (DTCHull corroborates) |
| M2 | Settledness = drift ≤5% on total AND pressure AND viscous separately, ≥1.0 flow-throughs, batch error ≤5% — each clause anchored on a named run that passed without it (beach, lts, val_coarse5) | cfd/post.py | REPEATABLE — the settling triad is the corpus's most battle-tested rule |
| M3 | The settled-window scatter on the hookprobe family is ~±2.5%: any delta below it is noise, whatever its sign | campaign; LESSONS Bin 3 | OBSERVED (recipe-specific) |
| M4 | No build-time predictor of solve death exists: quality bars passed on every dying mesh (4 independent failures); the illegal-faces count interleaves; stack/hull_cell REFUTED (KCS dies at 0.952, Wigley solves at 1.084) | CLAUDE.md; case.info census | REPEATABLE (refutations) |
| M5 | Meshability is non-monotone in layer count with HOLES (hull 10 only n=8, hull 12 only n=6, failures strictly between passes); and some defects are layer-INVARIANT (hull 4 identical at n=3..9) — the ladder cannot rescue those | layer-search bank | REPEATABLE |
| M6 | Speed is a mesh parameter: same recipe solves at Fn 0.38, dies at 0.53 at ALL stack depths (deltaT→1e-105 with one cell's Courant ~10); the fix is a velocity RAMP, not layer backoff; and a naive ramp is WORSE (ramped inlet + un-ramped forced outlet drains the tank at t≈0.0008 s) | three 11-kn deaths; ramped-death root cause | REPEATABLE, with a corrected diagnosis |
| M7 | The v1→v3 A/B ledger's meshes are NOT constant (415k/514k/414k cells, layers 9.3/8.4/9.3) while the claimed deltas are 1.1–1.2% — the ladder's monotonicity cannot be cleanly attributed to geometry; the +33% v4 delta SURVIVES (far above any mesh effect) | anchor book cells fields | OBSERVED confound, undisclosed by the doc |
| M8 | v2 — the "going-forward hull" — solved on the campaign's dirtiest surface: 474 self-intersections and a 7.5×-coarser bow patch, violating the campaign's own recipe rule | case.info v2 | OBSERVED — weakens both headline v2 causal links |
| M9 | Wall-clock: cost/cell-step ~constant (2.8 µs np=10), runs get cheaper as they settle (×2.7 opening-rate error), +25% speed tripled wall/sim-s, GCI triplet = ~21× coarse (not 12×: Courant adds √2 steps per √2 refinement) | fidelity.py constants; APSE §4 | REPEATABLE (machine-specific absolutes, transferable ratios) |
| M10 | The budget and the wave-resolution bar are UNSATISFIABLE together at KCS Fn 0.26 (coarsest admissible grid = 3.24 h > 2 h budget); the way out is running at higher Fn (cells/λ ∝ Fn²·nx, Lwl cancels) | APSE §4, pinned test | OBSERVED; the Fn² rule is the strongest un-consumed scheduling heuristic |
| M11 | `--anchor fine` GCI families are INADMISSIBLE (coarser members fall under 20 cells/λ) — prose-only; make_case still exposes it without refusal | APSE §4 | OBSERVED |
| M12 | LTS cannot produce a resistance number (14.5× error; waves are unsteady); retained only as an initialiser | CFD.md §3 | OBSERVED (elimination) |
| M13 | Six machine-hour eliminations stand: convergence-insufficiency (no), missing boundary layer (fixed, viscous only), wave reflection (beach made it WORSE 2.9→5.7×), LTS (no), mass leak (no), tank mode/relaxation zone (refuted at 3.40 FT — weeks of absorbing-domain work avoided) | CFD.md §3, §2 | REPEATABLE — the do-not-re-try list, prose-only |
| M14 | The KCS benchmark is structurally BLIND to the air-block defect class (its deck never enters the air block) — the first measured case of the benchmark being unable to see a defect | CFD.md §6 | OBSERVED; Gate 2M correctly demoted to numerical anchor |
| M15 | No geometric feature separates mesh-clean from refusing hulls at N=25 (nine candidates, all AUC ≈ 0.5); when a failure rate is flat across a population, sweep the MESH, not the hulls | CFD.md §6 | OBSERVED (negative result, honoured by DIAGNOSTIC bases) |
| M16 | `tet_bad_faces_at_1e-15` is measured on every case and read by NOTHING — the most promising unused feature for a solvability classifier (n=4 failures: enough to falsify current bars, too thin to fit) | case.info census | OBSERVED |
| M17 | Ct COMPARISON IS BROKEN: `stl_wetted_area` gave 34.19/42.14/34.28 m² on near-identical hulls → Ct 0.0106/0.0085/0.0103 for hulls 2.3% apart in Newtons; the anchor book ships the bad field unflagged | anchors; campaign "pitfall" note | OBSERVED, LIVE BUG (P0-1) |
| M18 | Divergence discriminator: deltaT TREND (not alpha undershoot, not Courant alone) — pinned dt at speed, relaxing dt when healthy; on Apple Silicon the FPE surfaces as SIGILL, not sigFpe | campaign; JOURNAL | REPEATABLE |
| M19 | The seas machinery EXISTS and was commissioned against theory (flume 0.0500 m vs 0.0500 m spec); the v3 head-seas run COMPLETED with converged wave loads (heave 199 kN p2t, pitch 1128 kNm, 5 encounters, spreads 2.7–4.7%) — and the campaign doc still calls wave machinery absent | runs/hookprobe_v3_seas; wave_commission; JOURNAL | OBSERVED — an undocumented completed capability (P0-4) |
| M20 | The seas record CANNOT be read as resistance (zero forward speed — waveModels has no mean current; the book's 2.57 m/s label is nominal) and its 132% batch error is "wrong measurement type", not "unsettled" — the schema needs `run_type` | anchors; post.py batch guard | OBSERVED (P0-2) |

### A.4 Stability, seakeeping, geometry-adjacent

| # | Finding | Evidence | Class |
|---|---|---|---|
| S1 | v2 @ 8 t statics: Awp 21.58 m², I_T 14.38 m⁴, BM_T 1.84 m, GM_T 1.63–1.03 m over KG 0.9–1.5, GM_L ~19 m, entry 11.5° — static indicators only, no dynamics | campaign stability section | OBSERVED (hydrostatics method DOMAIN-VALIDATED) |
| S2 | Wave loads on the fixed v3 hull in H=2.0 m / T=4.5 s head seas: heave 199 kN, pitch 1128 kNm p2t, clean sinusoids, no slam spikes | v3_seas | OBSERVED (loads, not motions — fixed hull, zero speed) |
| S3 | Roll DAMPING is absent tree-wide (GM stiffness only); the measured 12 m²/side lateral plane + 3 fins is an unused damping estimate | PROPULSION-INTEGRATION §3 | OBSERVED absence |
| S4 | The axe entry (11.5°) sits inside the ≤12° band the critic already enforces from the visual corpus — the one CFD-adjacent number that was already anchored | campaign; morphology bands | OBSERVED |

### A.5 The fifteen feature→consequence chains

Each link labelled MEASURED or INFERRED (protocol §5/§6). The inference
boundaries are the design priors' validity limits.

1. **Bluff stern → stern wave dominance → drag lever is AFT.** Pressure fraction MEASURED (R1); that easing the shoulder reduces drag CORRELATED-only (R2 + M7 confound). Now expressible (`dwl`/`rb_transom`).
2. **Parallel midbody → beam carried → not-a-spearhead.** Geometry MEASURED (corpus + barge landing); hydrodynamic consequence INFERRED — no run varies pmb. Terminates at plausibility, not drag.
3. **Fine entry + deep forefoot → reduced pitch excitation.** Geometry MEASURED; pitch response INFERRED (no pitch RAO exists).
4. **Transom immersion → Fn_T < 2.5 → dead-water eddy.** Immersion/Fn_T MEASURED; the eddy's drag cost INFERRED (threshold is literature).
5. **Tunnel + keel tail → attached, wet, near-freestream inflow.** MEASURED end-to-end at 8 kn (P1) — the flagship chain; generalisation beyond the configuration INFERRED, causal attribution to keel-line curvature UNMEASURED (keel slope at the disc is not a quantity anywhere).
6. **Fins upstream → near-surface wake deficit.** Deficit MEASURED (P2); the taper-improvement lever CORRELATED with confounds (P3, M8); no gene can carry it.
7. **Fin wetted area → low-speed viscous share → hierarchy inversion at Fn 0.24.** Components MEASURED at 0.38; the inversion SCALED (R9) — highest leverage, least anchored.
8. **Small disc → high loading → low ideal η → "the prop is the lever."** Drag MEASURED; efficiencies momentum-theory (P9).
9. **Tip clearance < 15% D → pressure pulse → noise/erosion.** Nothing measured here; literature throughout.
10. **Tunnel recess → diameter for free?** The published ±3–4.5% drag cost is NOT charged anywhere — the recess is a free lever in the optimizer's eyes (and the magnitude sits at the scatter floor).
11. **Working prop → t, w, η_H inside the loop.** Nothing measured; no actuator disc has ever run here; symbols absent (P11).
12. **Topology split → two clean streams.** Topology MEASURED; "clean streams" never sampled; geometrically blocked upstream by the 70–80% split loft (now unblocked in-kernel by Phase 4B's `y_split` — the loft consumer is the remaining work).
13. **Prop overlap 12.5% → channel width.** Arithmetic fenced; the VALUE unmeasured at any percentage (P12).
14. **Chine termination → wake fed to the prop.** Nothing measured; not drawable (per-station chine is Phase 3's remaining generality item); the protocol's exemplar of a KB entry that may exist only after the variant experiment.
15. **Spray/ventilation paths → aerated water at the prop.** Only Fn_T reported; "only CFD can see this" — report fields first, bars after measurement.

---

## DELIVERABLE C — knowledge-to-code matrix (where it lives vs where it must go)

### C.1 Correctly encoded (KEEP — the honest machinery to build on)

- The settling triad + batch error + LAST-FIFTH-BY-TIME window + LTS refusal + symmetric factor + cell-count refusal (`cfd/post.py`) — the teacher's trust layer.
- The mesh laws with receipts: near-cubic background, z-band equality, `_NX_BASE 57` families, layer cap 7 with requested-vs-achieved, backoff ladder with holes, depth-from-wave with assertion, first-layer from ITTC y+ (`cfd/case.py`).
- The admissibility screen's basis discipline (DIAGNOSTIC metrics forbidden to vote; label-void history; genome-hashed calibration banks).
- `form_factor`'s clamp-with-sigma; `_require_theta_resolution`'s refusal; the GCI single-source with printed method; similitude's Re/We floors kept separate.
- The anchor book's refusal semantics (`settled_only`, `FN_SUPPORT`, family refusal by name) — right shape, wrong completeness (P0-2) and zero callers (P1-6).

### C.2 Encoded at the WRONG scope (MODIFY)

| Item | Defect | Fix target |
|---|---|---|
| `cfd_kb.L1_ANCHOR` hardcoded 1.57 | number-declared-twice: not computed from the book's own 1733.47 N | derive from anchors + a stored L1 reference (P0-3) |
| `form_factor` RANS receipt | cites "settled" kcs_s1 which the book records unsettled | pin provenance to `runs/kcs` or re-verdict wording (P0-3) |
| `draft_over_hull_cell` | demoted in prose, still `Basis.DERIVED` → re-armable silently | `Basis.DIAGNOSTIC` (P0-5) |
| checkMesh bars (0/5/20) | shell-script literals, declared-twice risk | single-source in limits.py (P2) |
| `flow_regime` | Fn-only gate on a model whose slenderness assumption the median hull violates | add slender clause / envelope field (P2-13) |
| APSE depth floor 0.6 L vs case.py 1.0 L | two coefficients for one law across research docs | re-verdict APSE §1/§4 (P0-4) |
| PROPULSION-INTEGRATION §6 "no prop-plane sampling" | falsified by the same doc's campaign section; two sections numbered §6 | re-verdict rows (P0-4, owner's doc — flagged, not edited unilaterally) |
| `DRIVE_LAWS[TUNNEL]` note | carries design-intent AND config-specific CFD in one prose blob; no vertical axis field | split; add prop-axis-depth (P2-15) |
| stl_resolution | measured inert (lwl cancels; STL ships 1.353× coarser than asked); disclosed, uncorrected | make the STL-finer-than-cells requirement a checked bar (P2) |

### C.3 Measured, correct, and PROSE-ONLY (ADD — the knowledge-loss list, protocol §32/§33)

**HIGH PRIORITY — demonstrated repeatedly, encoded nowhere:**
1. The ±2.5% resolvability bar as a machine constraint on any CFD-informed ranking (M3 → P2-12).
2. The viscous-right/pressure-wrong triage classifier (R4+R5 → P2-11).
3. The Fn² scheduling rule + cost surrogate (M9/M10 → P1-10).
4. The velocity-ramp-above-Fn-0.5 rule with the passive-outlet condition (M6 → P1-7).
5. The six eliminations + do-not-re-try list as KB entries (M13).
6. The extend-on-drift stopping criterion (runs stop at target time, not at convergence — R8, M2).
7. The layer-invariant-defect ladder stop (M5).
8. The Kelvin-wavelength auto-check (R13 → P1-9).
9. same_geometry preflight before any solve (3 of 11 book records share a sha — P1-6).
10. The theory-first CFD trigger (the owner's methodology split, executable via select_fidelity + cfd_kb).

### C.4 The hookprobe-overfit boundary (protocol §22)

Generalizable (mechanism-carried): the settling triad; the mesh laws;
Fn² scheduling; the Kelvin check; the pressure-fraction FAMILY structure
(that families differ — R1's contrast with KCS proves the tag matters);
the deficit-layer CONCEPT (prop axis below the surface wake, in z/T form).
Hookprobe-specific (must stay family-tagged): every absolute Newton; the
48% appendage share; the −0.4 m depth (0.44·T on THIS hull); the +33%
package verdict; the fin-taper lever; the tunnel-wetness numbers; the v5
remedies. The book's family tags + `FN_SUPPORT` are the enforcement
mechanism; the missing piece is `run_type` and the viscous-validity flag
(P0-2).

---

## DELIVERABLE D — the CFD-aware search architecture

The target loop, mapped onto files that exist:

```
anchors (data/cfd_anchors.json, harvested; run_type-tagged after P0)
   │
   ├─ RULES  → refusals & stopping criteria (cfd/post, case, run-case)
   ├─ PRIORS → report-tier expectations (cfd_kb bands + L1 ratio, surfaced
   │           in ResistanceResult.method_notes / certify / UI — never
   │           silently applied to physics)
   └─ TRIGGERS → select_fidelity asks, in order:
        1. does theory answer this? (Kelvin/ITTC/hydrostatics — refuse CFD)
        2. does the book answer this? (same_geometry; family band in Fn
           support — refuse CFD, cite the anchor)
        3. else schedule CFD, ordered by the Fn²/cost model, meshed by the
           speed-conditioned rules, stopped by drift-not-time, A/B-paired
           under the mesh-match constraint, auto-validated by the Kelvin
           check, harvested back into the book on exit.
```

Search-side consumption (protocol §29/§30): the derived-dwl move is the
template — a deterministic, measured lever fired when a named finding
appears. The two CFD analogues ready today: (a) at Fn > 0.35 in a bluff
family, spend mutation budget AFT (R1/R2 prior, surfaced as a move
ordering, not a bar); (b) any CFD-informed ranking refuses deltas below
the family scatter (M3). Local gradients (protocol §31) are NOT currently
licensable: the only paired perturbations (v1→v2→v3) are sub-scatter and
mesh-confounded — the honest gradient corpus starts with the A/B validity
constraint (P0) applied to future pairs.

---

## DELIVERABLE E — surrogate/prior proposal (sized to the corpus)

Corpus: 6 settled anchors, 4 families, single-grid, no GCI, Fn ∈ {0.26,
0.29, 0.33, 0.38×2, 0.38}. Verdict per protocol §24: **rules +
nearest-anchor + refusal only.** A GP/RSM over 6 points spanning 4
discrete families would be fitting family labels, not physics; ranking
models have nothing to rank (no two settled anchors share family AND
differ in a designed variable beyond scatter). The one legitimate
"model" is the family-tagged lookup with hard support boundaries — which
is what `cfd_kb` is. Upgrade triggers, stated now: fit a per-family
response surface only when a family holds ≥5 settled points spanning a
designed variable with deltas above scatter; consider GP/ML only past
~20 settled anchors with GCI on ≥3. Until then, P4 is frozen (protocol
§45's own rule).

---

## DELIVERABLE F — the CFD budget strategy

The funnel exists in pieces; the numbers come from the measured cost
model (`fidelity.py`: 2.8 µs/cell-step np=10, ~3.2 h per settled 8-kn
hookprobe run, ~21× for a GCI triplet):

```
candidates (NSGA / PLM)             ~10³ per campaign
  → L0 + shape row + screens        (ms each; already wired)
  → theory tier (L1 + anchors as    (ms; refuses known-answered questions)
    report-tier priors)
  → admissibility screen + writer   (~140 ms; refuses unmeshables)
  → same_geometry dedup             (free; refuses paid-for questions)
  → CFD selection: highest info per hour —
      * per protocol §25: promising, uncertain, novel, boundary-defining
      * ordered by Fn² cost rule; A/B pairs mesh-matched; budget in
        wall-hours from the cost model, not run counts
  → 2–5 solves per campaign, stopped by drift, harvested on exit
```

Success metric (protocol §42/§43): design quality per CFD hour. The
BEFORE state is measured: the hookprobe campaign spent ~7 solves and two
failed-speed excursions to answer questions of which at least two
(identical-surface re-queries; the 11-kn attempts after the first
signature) the wired funnel would have refused for free.

---

## DELIVERABLE G — the replay/validation benchmark

What the corpus can honestly support today (protocol §40/§41 scaled to
n=6): a LEAVE-ONE-OUT on the family-level claims — hide each settled
anchor, predict its pressure fraction from its family's remaining
anchors, and its settledness class from its run parameters. Computable
now; expected result: hookprobe members predict each other within the
band, KCS is refused (no family sibling) — which IS the correct answer
and demonstrates the refusal semantics. What the corpus CANNOT support:
predicting absolute resistance for unseen geometry (no two settled
anchors differ by a designed variable above scatter). Named limitation:
the hookprobe hull is not grammar-expressible, so the L1 chain cannot
even be evaluated on the measured family — the L1-anchor benchmark is
BLOCKED on either a grammar reconstruction of hookprobe or a settled run
of a grammar-emitted hull (c06_case_a_n5 is settled and IS
grammar-emitted: the one L1-vs-RANS comparison buyable without any new
CFD — flagged as the first benchmark computation to run after P0).

---

## DELIVERABLE H — implementation plan (P0–P4, protocol §45)

**P0 — prevents wrong designs (the book must not lie):**
1. Fix the Ct wetted-area denominator (`cfd/post.py:stl_wetted_area`
   inconsistency, 34.2 vs 42.1 m² on near-identical hulls) — MODIFY.
2. Anchor schema honesty: `run_type` (calm-resistance / wave-loads /
   mesh-study), `ct_trusted`, `viscous_valid` (false where layers
   failed: v5_20kn), forward-speed field for seas records — MODIFY
   `scripts/harvest_cfd_anchors.py` + re-harvest.
3. Single-source the L1 anchor ratio (compute from the book + a stored
   L1 reference; fix the kcs_s1-vs-kcs provenance in `form_factor`'s
   receipt) — MODIFY `cfd_kb.py`, `resistance.py`.
4. Re-verdict stale research rows (APSE depth coefficient + "never
   merged back" claim; PROPULSION-INTEGRATION §6 duplicate/stale rows;
   campaign doc's missing seas + 20-kn sections) — flagged to the owner;
   research docs are the owner's record.
5. `Basis.DIAGNOSTIC` for `draft_over_hull_cell` — MODIFY one line.

**P1 — directly reduces CFD spend:**
6. Wire `same_geometry` as a preflight in `make_case.py`/`run-case.sh`.
7. Stopping criteria: extend-on-drift (not fixed end-time); two-strike
   no-progress; live divergence classifier (deltaT trend + Courant
   signature) aborting solves; layer-invariant ladder stop — MODIFY
   `run-case.sh`, `run_campaign.sh`, ADD the classifier.
8. The theory-first trigger in `select_fidelity` (theory → book → CFD).
9. Kelvin-wavelength auto-validation per run (post-processing gate).
10. The Fn²/cost scheduling rule into `planner.py`; velocity ramp (with
    passive outlet) into `make_case.py`; A/B mesh-match validity check.

**P2 — search efficiency:**
11. Surface the priors: 1.57× + pressure-fraction band into
    `ResistanceResult.method_notes`/certify/UI as labelled expectations;
    the viscous/pressure triage classifier on CFD post-processing.
12. Minimum-resolvable-delta bar on CFD-informed comparisons.
13. Michell slenderness clause in `flow_regime`.
14. Aft-mutation ordering for bluff families in the search (derived-dwl
    pattern).
15. `DriveLaw` vertical axis (prop-axis depth vs deficit layer, z/T
    form) + call `propulsion.assess` somewhere (the report is inert).

**P3 — prediction accuracy (buys runs, in value order):**
16. The 5-kn mission-point run (cheap: large timesteps; converts R9 from
    HYPOTHESIS and re-prices the fins/appendage objective).
17. The c06_case_a_n5 L1-vs-RANS comparison (free — data exists).
18. The second benchmark anchor (Fridsma/DSYHS — already on the standing
    CFD approval list) and the Wigley-vs-Michell wave-machinery check.
19. Wetted-only y+ and interface-cells-per-column as case.info receipts.

**P4 — frozen** until the corpus crosses the Deliverable-E thresholds.

---

---

## ADDENDUM 2026-08-28 — what the parallel CFD session changed under this audit

This audit was written against the tree as it stood; two of its entries
have since been overtaken by measurement, and one deliverable item was
re-priced. Recorded here rather than edited away, because the audit is a
dated record and the correction is the interesting part.

1. **R10 retracted on the domain, not the attitude** (see the row above).
   The audit's Deliverable-B validity column for that record named the
   right verdict for the wrong reason. The domain/wavelength rule now
   exists as Gate 2E — a rule this audit did not know to ask for.
2. **`ct_trusted` gained a second clause.** This audit added the
   facet-count test (>= 100k) after tracing the v2/v3 wetted-area gap to
   two different surfaces. The CFD session added `domain_wavelengths >=
   1.5` beside it, which is what actually caught the 20-kn record. Both
   clauses are needed and neither implies the other.
3. **P3's "free" item is not free** (see `navalai/cfd_kb.py`'s
   `L1_REFERENCE_N` note): the c06 L1-vs-RANS comparison was attempted,
   the genome had moved, the pre-upgrade genome was reconstructed, and
   the decomposition then refused the anchor on a better ground — the
   5.81x pressure ratio is the project's open pressure over-prediction,
   not a hull-family property. Deliverable H's P3 ordering should read:
   the pressure over-prediction is a PREREQUISITE, not a peer, of every
   remaining L1 anchor.

*Method note (protocol §47): reconstructed from docs/research/*,
docs/LESSONS.md, docs/HULL-KB.md, docs/audit/HULL-DESIGN-AUDIT.md, the
gate ledger, runs/* case.info + force histories, JOURNAL.md, and the
call graphs of resistance/propulsion/admissibility/cfd/fidelity/
morphology/parents/energy — four parallel read passes, findings merged
and cross-checked. Where two records disagreed (depth coefficients,
settledness of kcs_s1, the §6 sampling row), the disagreement is itself
recorded above rather than silently resolved.*
