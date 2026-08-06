# Gap register — NavalAI audited against its own build plans

**Audited 2026-08-05** against `NavalArchAI-BuildPlan.md` (Phases 0–7),
`BuildPlan2-FullVessel.md` (V2.0–V2.6), `PLM.md` (platform law, gate registry,
lifecycle) and the six honesty rules in `CLAUDE.md`.

Method: seven independent audits of the live checkout at `5bbffb7` + uncommitted
free-motion work — L0/L1 physics, L2/L3 CFD, learning spine, front end/rules/
export, PLM+CI/CD+docs, an end-to-end naval-architecture reality check driving
four missions, and an adversarial red team with working proofs-of-concept.
Findings that are asserted rather than measured are marked `[unverified]`; every
other row was reproduced numerically. Overlapping findings from different audits
are merged, and the corroboration is noted — three audits independently found
the mission-length defect, which is why it leads the register.

**Baseline at audit time:** 135 tests pass in 182 s; `python -m navalai.gates`
reports 15 GREEN, 2 RED, exit 1. **Every finding below is invisible to that run.**
That is the register's central point: the suite is not wrong, it is aimed
somewhere else.

---

## Severity

- **CRITICAL** — the system reports something untrue about itself, or a gate
  cannot fail. Fix before any other work is trusted.
- **HIGH** — a plan clause is unmet and the gate that owns it reports GREEN, or
  a number the product delivers is wrong.
- **MED** — real defect, bounded blast radius, or currently masked by another gap.
- **LOW** — hygiene, staleness, fragility.

---

## A · The ladder is not a ladder

Honesty rule 2 says "any kept design re-validates up the ladder". Measured by
AST import graph: `evaluate`, `optimize`, `agents` and `ui/server` reach
`seakeeping: no`, `cfd: no`, `surrogate: no`, `rules: no`. In code today, rule 2
amounts to nothing — there is no `keep` verb, no trust-region re-validation, no
escalation, and no path that could refuse an export.

| ID | Plan clause | Finding | Evidence | Sev |
|---|---|---|---|---|
| A1 | Honesty rule 2; §2 architecture | L2/L3 unreachable from the product. Only importer of `seakeeping` outside tests is a print-only spot-check in `demo_mission.py`; only importers of `cfd` are operator CLIs. `Evaluation.tier` was `"L1"` in 100% of ~2000 evaluations. | `evaluate.py:15-24`, `agents.py:26-33`, `ui/server.py:25-42`, `demo_mission.py:21` | **CRITICAL** |
| A2 | PLM §1 "rules tier fails closed"; platform law | **Nothing in `navalai/` imports `navalai.rules`.** Not `evaluate()`, not `CONSTRAINT_NAMES`, not NSGA-II, not the agent shell. A hull failing ISO 12215-5 is `ok=True` and exports. The rules gate is a print statement in a demo. | import scan; `evaluate.py:33`, `agents.py:99-111` | **CRITICAL** |
| A3 | Honesty rule 2 | The test whose comment cites honesty rule 2 asserts `ev.tier == "L1"` — it would **fail** if a kept design ever escalated. | `tests/test_optimize.py:23` | **HIGH** |
| A4 | Gate 3 "OOD queries reliably escalate to L2/L3" | `is_ood()` has two call sites, both in tests. Nothing escalates. | `surrogate.py:11,89-93` | **CRITICAL** |
| A5 | Honesty rule 2 "nothing ships un-re-validated" | `export_dxf`/`export_step` take a `Hull`, not an `Evaluation`. Verified: an **L0-failing** hull (`deadrise.order`) exported to an 8,487-byte DXF and a 174,406-byte STEP without complaint. | `export.py:40,52`; `unroll.py:97` | **HIGH** |
| A6 | Gate 3 | `is_ood` is a σ-threshold, not a support test, and does not discriminate: median error of kept 0.161 vs rejected 0.200. Fires 100% only on hulls 3× outside the box, which `grammar.check` already rejects; fires **0.0%** on in-box points whose error reaches 113%. | measured | **HIGH** |
| A6b | Gate 3 | **HALF OF A6 WAS THE PROBE, not the detector, and the register did not say so.** Gate 3 draws its training hulls AND its query hulls uniformly from the same grammar box, so the experiment **contained no out-of-distribution query at all** — nothing can separate an empty set, and "no separation" could not have come out any other way. Restrict the training support the way a real surrogate is restricted (it is trained on wherever the optimiser has been) and the picture inverts. MEASURED: full box → rejected/kept error ratio 1.08; training support LWL ≤ 12 m → **3.16×, recall 0.89**; β_mid ≥ 12° → 2.08; T ≤ 0.85 m → 1.77. So the σ test was not as broken as A6 implies — **what it lacked was RECALL** on axes the kernel ignores. Recorded 2026-08-06. | measured | **HIGH** *(corrects A6)* |
| A6c | Gate 3 / honesty rule 1 | **ARD lengthscales saturate at the optimiser's bound, so σ is blind to two axes entirely.** MEASURED on the GP trained on 100 L1 hulls: `ls[3]` (D) and `ls[5]` (β_bow) sit at exactly **10.0**, the L-BFGS-B upper bound. Any support test that divides by those lengthscales inherits the blind spot and adds nothing, which is why the distance test added for A6 is deliberately NOT lengthscale-weighted. The saturation itself is unfixed: it means the kernel has decided two design axes do not matter, and no uncertainty the GP reports can disagree. | measured | **MED** *(open)* |

---

## B · Mission fidelity — the delivered boat is not the boat asked for

Four missions driven end to end; **all four hulls rejected** by naval-architecture
review. Corroborated independently by three audits.

| ID | Plan clause | Finding | Evidence | Sev |
|---|---|---|---|---|
| B1 | Gate 5 "translates to correct specs" | **`lwl_hint_m` is parsed, range-clamped, prompted for, asserted in two tests, and consumed by nothing.** Measured: 10 m → **18.58 m** (+86%); 5 m → **15.57 m** (+211%); 14 m → 19.85 m (0.96% off the 20 m grammar ceiling); 6 m → 14.27 m. Fraction of each 40-member Pareto front within ±10% of the stated length: 0/40, 0/40, 4/40, 0/40. | `mission.py:23,72`; `translate.py:32,48`; zero reads outside tests | **CRITICAL** |
| B2 | Gate 5 requirement checkers | **`carries-target` cannot fail.** `target = max(agg.total_kg, mission.target)` and the hull is then floated *to* that target. Median delivered displacement **2.12× the mission target**; a 400 kg mission delivered at **2387 kg (+497%)** printing "5/5 requirements pass". | `evaluate.py:105`; `translate.py:128-132` | **CRITICAL** |
| B3 | Gate 5 | **`"a 6,000 kg river cruiser"` parses to 6.000 kg.** `parse_mission` does `.replace(",", ".")` on the whole string before matching; `notes` comes back empty, so it reads as a clean parse. | `mission.py:49,56` | **HIGH** |
| B4 | Phase 1 "weight/CG budget" | `payload_kg` is a flat 800 kg regardless of `crew`. Measured: `crew=12` puts 1020 kg on the rail for R-OLH while the boat floats at **6004 kg — identical to `crew=2`**. Only 4 of MissionSpec's fields reach physics at all. | `energy.py:23`; `evaluate.py:101-105` | **HIGH** |
| B5 | Phase 1 optimizer | Wh/NM falls monotonically with length and **nothing costs length** — no structure/length scaling, no cost, no mooring or lock limit. Build area is a Pareto axis, and the selection rule everyone uses (`min wh_per_nm`) discards it. LWL was the only parameter within 1% of a bound. | `optimize.py:26-52`; `agents.py:_engineer`; `demo_mission.py` | **HIGH** |
| B6 | — | **`−GM` is maximised as an objective.** That is a hazard above ~0.20·B, not a goal. Direct cause of GM/B **0.82** and a **1.5 s roll period** on a boat sold as a dayboat. All four hulls over-stiff (GM/B 0.205–0.821 against a 0.08–0.20 band). | `optimize.py:47` | **HIGH** |
| B7 | §1.2 Michell validity | **No Froude validity envelope.** A 25 kn mission ran the Michell thin-ship integral at **Fn 1.09 / Fn∇ 3.42** and reported PASS, with no planing lift, no dynamic trim, no spray. β_mid 7.5° for a 25 kn cat-C boat (wants 18–24°). | `resistance.py`; `evaluate.py` | **HIGH** |
| B8 | naval-architecture practice | **LCB unconstrained**: −6.47 and −7.86 %LWL on two of four hulls against a −3…+3 band; all four out of band on LCF. Stays out of band even at pinned length. | measured | **HIGH** |
| B9 | L0 gate | L0 checks `BWL/T` on the **parameter** vector; the delivered hull floats at **B/T 14.4** against the project's own ≤12 bar. Proportions are never re-checked on the floated state. | `grammar.py:71`; `evaluate.py` | **HIGH** |
| B10 | — | Price of honouring the mission, measured: pinning LWL to the hint costs **+21% to +76% Wh/NM** and moves DLR from 21–43 into 122–387, L/B into 2.9–4.0, Cb into 0.55–0.72, and makes the trim constraint binding. **The trade is worth taking.** | measured | *(decision input)* |

---

## C · A number declared twice

CLAUDE.md names this the codebase's recurring defect. `limits.py` was the right
response; the pattern is still live in eleven places.

| ID | Finding | Evidence | Sev |
|---|---|---|---|
| C1 | **The platform's own 15 mm ply fails its own ISO 12215-5 rule for every SKU it sells.** Required thickness crosses 15 mm at **mLDC 845 kg**; Dayboat 1–3 t needs 15.2–16.9 mm, Solar Liveaboard 6 t needs **18.24 mm (15 mm fails by 22%)**, 12 t needs 19.8 mm. | `limits.py:39`; `rules/iso12215.py:29-33` | **CRITICAL** |
| C2 | The demo hides C1 with a **fourth, undeclared thickness**: `provided_mm=20.0`, a literal in neither `limits.py` nor the weight model, and the only value that makes R-TBM pass. `test_phase6.py:87` bakes the same 20.0 into the gate test. | `demo_mission.py:58`; `tests/test_phase6.py:87` | **CRITICAL** |
| C3 | `0.015` hard-coded twice more as a default in the weight model, never overridden by `evaluate()` — so structural mass runs on a private copy of the sheet. `limits.py:36-38` explicitly claims these are kept together; the claim is false. | `energy.py:48,78` | **HIGH** |
| C4 | **The scantling rule is fed the wrong mass.** mLDC comes from the weight *budget* (2769.6 kg) while the boat *displaces* 6003.5 kg → panel under-specified by 1.5 mm (8%). ISO 12215-5's mLDC is loaded displacement. | `evaluate.py:105`; `demo_mission.py:58` | **HIGH** |
| C5 | **Frame spacing describes two different boats.** Scantlings assume 400 mm; `engineer.py` builds bulkheads at 1400 mm with no intermediate frames. At the spacing actually built, t_req(6 t) = **63.8 mm** of plywood. | `rules/iso12215.py:29,36`; `engineer.py:20` | **HIGH** |
| C6 | `translate.py` still holds a private copy of the freeboard floor (`>= 0.25` + the clause string) in the same file that correctly imports `gm_floor`. The GM copy was fixed; the freeboard copy was left. | `translate.py:123-126` vs `limits.py:33` | **HIGH** |
| C7 | VCG fractions declared twice — inlined literals in `weight_budget`'s `kg` expression and again in `VCG_FRACTION` 15 lines below. They agree only because a test guards them. | `energy.py:56-57` vs `72-73` | **MED** |
| C8 | `limits.min_bend_radius_m()` is defined and never called; `evaluate.py` recomputes `BEND_RADIUS_RATIO * PLY_THICKNESS_M` inline. | `limits.py:50`; `evaluate.py:126` | **MED** |
| C9 | An undocumented `× 1.6` shell-area factor duplicates a quantity computed exactly elsewhere (true factor 1.688; `wetted_surface(z_sheer.max())` gives it). Right today by luck of the factor. | `evaluate.py:101,103` vs `optimize.py:43`, `engineer.py:37-39` | **LOW** |
| C10 | `CREW_MASS_KG = 85` exists only in the rules tier; the weight budget knows nothing about crew count. The stability check and the weight budget disagree about how many people are aboard. | `rules/iso12217.py:26`; `energy.py:17` | **MED** |
| C11 | **Two GCI implementations that disagree.** `gate2m.py` defines its own alongside `post.gci`; they differ on p-clamping and argument order, and the gate is the *less* careful — it computes r₂₃ and never checks it against r₁₂, which `post_gci.py` does warn about. | `gate2m.py:113-122` vs `post.py:444-460` | **MED** |
| C12 | `WASTE_FACTOR = 1.30` asserts nesting waste that the DXF layout could measure. | `engineer.py:17,52` | **LOW** |

---

## D · Gates that cannot fail, and gates that referee themselves

All proven with working PoCs.

| ID | Finding | Evidence | Sev |
|---|---|---|---|
| D1 | **A measured RED gate is erased by editing one prose string.** `"RED (measured)…"` → `"AMBER (measured)…"` gives exit **0**. So does `"METAL-GATED: …"`, `blocked=None`, or deleting the row. Converting a live suite row to `(…, None, "PENDING: refactor")` also exits 0. **No test pins the `GATES` list.** | `gates.py:97`; PoC | **CRITICAL** |
| D2 | **One line silences a failing gate test.** `pytest.importorskip('some_optional_solver')` → `GREEN (1 skipped)`. `@pytest.mark.xfail` → **GREEN with no annotation** (`xfailed` matches no alternation in `counts()`). | `gates.py:50-55`; PoC | **HIGH** |
| D3 | **`data/baselines.json` does not exist and is not tracked.** With no file `prior is None` → `ok = True` → the first retrain always deploys and writes its own numbers as the eternal reference. PoC: a label-shuffled model, `median_rel_err 0.407` vs 0.165 honest, **DEPLOYED**. | `flywheel.py:51,64-71`; PoC | **CRITICAL** |
| D4 | **The regression gate is a ratchet, not a floor.** 10 consecutive retrains all passed while error went 0.100 → **0.859** (8.6×) and coverage 0.950 → **−0.450**. A negative probability passes because it is only compared to `prior − 0.15`. | `flywheel.py:70,73-74`; PoC | **CRITICAL** |
| D5 | **The "frozen" holdout is caller-controlled.** `harvest(seed=4242)` + `retrain(holdout_seed=4242)` → `median_rel_err = 0.00000`, passed. Varying the mission (which the LLM writes) moves it 0.165 → 0.784. | `flywheel.py:60-62`; PoC | **HIGH** |
| D6 | **A sloppier grid study is easier to pass.** `inside = (ct+unc) >= lo and (ct-unc) <= hi` with no cap on GCI. At the recorded C_T: 2.5% → FAIL, 5% → FAIL, 12.8% → FAIL, **15% → PASS**, 100% → PASS. Tokyo groups achieved 2.5–3.5%. Uncertainty widens the acceptance region. | `gate2m.py:197`; PoC | **CRITICAL** |
| D7 | `gate2m.py` prints "this cannot close the gate on its own" and then returns **0** from that branch. Any CI reads the exit code. | `gate2m.py:174-179` | **MED** |
| D8 | `review.py` states "a confirmation that cannot say WHO checked WHICH edition is not a review, it is a rumour" — then `is_complete()` checks `reviewer` and `confirmed` but **not `editions`**, which read `"edition not recorded — set this"`. Gate 6R is GREEN on a record that admits it cannot name the document it checked. | `review.py:23-33` vs `:82-89`; `test_phase6r.py:21-25` | **HIGH** |
| D9 | **Gate 6R answers a different question than Gate 6.** Its scope is "threshold parity only" — zero reference designs, zero hand calculations. Gate 6's bar is *verdict parity with a qualified reviewer on ≥3 reference designs*. A green 6R is not evidence for it. The reviewer is also the project owner reviewing his own code, with no qualification recorded. | `review.py:28,34`; BuildPlan:122 | **HIGH** |
| D10 | Gate 3's (already softened) 15% bar **passes only on its chosen seed**: 0.112 on seed 991, and 0.193 / 0.170 / 0.184 on the three alternates tried. Plan bar is 1–2%; no "near optima" or "benchmark hulls" evaluation exists at all. | `tests/test_phase3.py:50-59` | **HIGH** |
| D11 | **Gate 4's feasibility bar is measured on the wrong quantity.** `grammar.check` sits *inside* the rejection loop, so 100% is true by construction. Model feasibility — the ShipGen-comparable number — is **31.98% raw / 77.60% clipped** against a 99% bar. The pPCA latent already in the repo scores **89.4%**. | `generative.py:64-77`; `tests/test_phase4.py:24-27` | **CRITICAL** |
| D12 | **`sample_conditioned` performs no conditioning.** Reference batch and first candidate batch are `np.array_equal == True`. Control "best 10 of 64 plain draws" is **bit-identical** (316.3/316.3, 313.4/313.4, 317.7/317.7). The Gate 4 conditioning test would pass for any sampler. | `generative.py:79-98`; `tests/test_phase4.py:30-43` | **CRITICAL** |
| D13 | `counts()` scans lines in reverse and breaks on first match, so whatever prints last wins: a `conftest.py` printing `"wrote report.xml: 20 passed"` turns an all-skipped suite GREEN. (Cannot flip a genuinely failing suite — returncode dominates.) | `gates.py:50-55`; PoC | **LOW** |
| D14 | **CI is permanently red by construction** — `gates.py` counts the hardcoded RED rows and `gates.yml` omits `--suites-only`, so the required check exits 1 on every push forever. One status per job means "2M still red" and "Gate 3 just broke" are indistinguishable. Branch protection can never be enabled. PLM §6 marks this epic **DONE**. | `gates.py:97,115`; `gates.yml`; measured exit 1 | **CRITICAL** |
| D15 | **Gate 2 is wholly unverified in CI** — module-level `importorskip("capytaine")` and CI installs only `requirements.txt`, so all 18 tests vanish. Gates C and D report GREEN while their cadquery/mujoco claims skip. `--strict`, documented as "use that in CI", is used **nowhere**. | `test_phase2.py:18`; `gates.yml` | **HIGH** |
| D16 | `-x` on the ladder run stops at the first failure, so the printed tail understates the damage. | `gates.py:101` | **LOW** |

---

## E · Physics validity

The kernels are sound — independently verified. Michell reproduces an exact
separable solution to **−0.86…−2.11%**; ITTC-57 matches published anchors
bit-for-bit; fourteen hydrostatic integrals on a barge match closed form to
≤0.0012%; `bm_l` genuinely uses the parallel axis through LCF (midships would be
50% stiff); `evaluate()` runs in 7 ms against a 50 ms bar; `g` matches what
NSGA-II enforces on all 5 × 12 values. **The defects are in what surrounds them.**

| ID | Plan clause | Finding | Evidence | Sev |
|---|---|---|---|---|
| E1 | Gate 1 "Holtrop reproduces its own validation set" | **Holtrop-Mennen does not exist.** `grep -rin holtrop` hits only the plan document. Gate 1 prints GREEN. | none | **CRITICAL** — **CLOSED 29f5dc6** (Gate 1H, `navalai/holtrop.py` + `benchmarks/holtrop_cases.py`, worst per-intermediate agreement 0.383%) |
| E1b | — | **E1's LETTER is closed; its value to the product line is not.** Holtrop-Mennen is implemented and anchored against the 1982 worked example, but **it is not wired into `evaluate()`** — that seam is owned elsewhere and was not claimed — and **our own small craft fall outside its statistical envelope**. MEASURED: a 10 m tender returns `L1H-INVALID` on B/T **6.67** against a band of 2.1–4.0 and L/B **3.33** against 3.9–9.5. It is a 1982 merchant-ship regression offered as one: available, anchored, and honest about where it does not apply. Same root cause as R4b — a ship method reaching for a boat. | measured | **MED** *(open)* |
| E2 | Gate 1 "Wigley matches the analytic/tank curve within published error bars" | **The anchor is not anchored.** Tests assert a magnitude band (`8e-4 < Cw < 5e-3`) and ≥2 sign changes. No reference curve exists in the repo; no per-point comparison is made. | `tests/test_phase1.py:34-63` | **CRITICAL** |
| E3 | "hydrostatics (volume, GM, trim)" | **GM — the binding constraint — uses the light-ship KG at the ballasted displacement.** At the 6 t mission **3230 kg (54% of displacement) has no declared position**; at 12 t, 77%. KG stays pinned at 0.9330 m while GM swings 3.80 → 1.78 → 0.78 m. Every stability verdict rests on a mass model that does not sum to the displacement. | `evaluate.py:105,115-118` | **CRITICAL** |
| E4 | Gate 0 "49 closed-form constraints" | **9 live constraints, not 49.** 28 emitted; 15 are bound checks the optimiser cannot violate; 4 more are tautologies inside the declared bounds (0 hits in 400,000 in-bounds samples). `ALIGNMENT.md` claims "30+". | `grammar.py:57-108` | **HIGH** |
| E5 | Gate 0 "round-trip 12+ known hulls" | **Absent.** The only round-trip is `vector(named(x))` on one hand-picked vector. No public-CAD hull is reconstructed anywhere. | `tests/test_phase0.py:21-23` | **HIGH** |
| E6 | Phase 0 "developable-surface constraints" | **The twist constraint measures the wrong quantity.** The proxy uses *mean* twist; the geometry warps quadratically so the true max is **1.88×** larger. **18.8% of hulls pass the plywood buildability bar with true twist above it** (up to 26.4 vs a 14 deg/m limit). `Hull.panel_twist_rate()`, the honest metric, is consumed by no gate. | `grammar.py:104-106` vs `geometry.py:64-65` | **HIGH** |
| E7 | "Michell + ITTC-1957" | **The form factor rides its clamp on 30.8% of the design space** (raw k 0.470 → returned 0.4500), and is fed *design* beam and draft while `cb` comes from the *floated* state (0.55 m passed vs floated 0.3737 m — a 47% error on the argument) → Rf overstated 4.9% on the reference hull, 15–20% across a third of the space. Watanabe is calibrated for L/B 6–8; the grammar allows 2.2. | `resistance.py:69-72,82-83` | **HIGH** |
| E8 | "integration + calibration harness" | **Michell is not grid-converged at production defaults**: 425.8 N shipped vs 456.0 N converged = **−6.6%**; the z-grid adds −2.0%. The Wigley convergence test uses its own finer grid and never exercises the shipped ones. | `geometry.py:27`; `resistance.py:77` | **MED** |
| E9 | Gate 0 "DB reproduces any stored result bit-for-bit" | **`hull_id` collides.** It hashes `round(v, 10)` but stores unrounded floats under `INSERT OR IGNORE`; two designs differing by 1e-11 collide and `get_params` returns the *first* one's parameters. Result rows record no mission, no rho, no library versions; `solver_version` is the literal `"0.1"` typed three times. | `db.py:47-49,58-65`; `evaluate.py:169-174` | **HIGH** |
| E10 | honesty rule 1 | **NaN in any constraint makes a design feasible** — `nan > 0.0` is False → `violations=[]`, `ok=True`. The NaN reaches the DB `uncertainty` column and the HTTP response as invalid JSON. | `evaluate.py:147` | **HIGH** |
| E10b | honesty rule 1 | **E10 has a COMPLEX-NUMBER variant, and it is the better-disguised one.** MEASURED while implementing Holtrop: at Cp = 0.96 the method returns `(8504.47-1749.72j)` N — a complex resistance landing in a float-typed dataclass field — from `(0.95-Cp)^-0.521448`. Sibling defects in the same family, all reproduced on the first draft: `Cwp = 1.0` → ZeroDivisionError inside c1 (i_E lands on exactly 90° and c1 carries `(90-i_E)^-1.37565`); `Cp = 0.25` → division by `(4Cp-1)`; `A_T > B·T·C_M` → **no error at all**, c5 goes negative and R_W comes back as a plausible **positive 2528 N computed from a negative amplitude**. `holtrop.domain_errors()` now names each impossibility in words and `total()` refuses — but the register's E10 row should be read as covering non-finite AND non-real, because a `>` comparison against a complex number raises rather than returning False, and a `nan` silently passes. Two different failures, one root: no type or finiteness guard on the constraint vector. | measured | **HIGH** |
| E11 | honesty rule 1 | **Pathological states are reported as the best possible case.** Trim returns 0.0 when GM_L ≤ 0; heel returns 0.0 when GM ≤ 1e-6. So a longitudinally unstable hull satisfies the trim constraint and a negative-GM hull satisfies the list constraint — 2 of 5 constraints are "satisfied" exactly where the physics broke. | `weights.py:129`; `evaluate.py:122` | **HIGH** |
| E12 | — | **`_FIELD_RANGES` guards only the LLM path.** `parse_mission("… 0 knots")` → speed 0.0; `"5000 crew"` → 5000. At 0 kn: **1.278e13 NM/day solar range**, `ok=True`, tier L1, no warning. `ui/server.py` builds `MissionSpec(**body)` with no clamp at all. | `mission.py`; `ui/server.py:69-71` | **HIGH** |
| E13 | "`Evaluation.g` is the ONE inequality vector" | **The `list` constraint is inert** — identically `−2.000` across 800 evaluations, because no mass item declares a transverse offset. It occupies an NSGA-II constraint dimension and carries no information. | `evaluate.py:122,132`; `energy.py:94-102` | **MED** |
| E14 | — | `solve_to_displacement` verifies only the **upper** bracket: target 1.00 kg returns 4.13 kg (**+313%**) with no exception; after 80 iterations it returns the midpoint with no convergence flag. | `hydrostatics.py:105-110,124` | **LOW** |
| E15 | — | `grade()` and `translate()` use bare `except Exception`, so a *broken checker* is indistinguishable from a *failed design*. | `translate.py:96,148-150` | **MED** |
| E16 | — | `CONSTRAINT_NAMES` ↔ `g` order is bound only by an `assert`, stripped under `python -O`. | `evaluate.py:134` | **MED** |
| E17 | — | `NU_WATER` is a fresh-water constant never re-derived from `rho`; `wetted_surface` ignores longitudinal slope (−0.62% on Rf); `offsets_grid` uses `endpoint=False` so the Michell z-grid omits z = wl where the kernel is largest. | `resistance.py:24`; `geometry.py:134-166` | **LOW** |
| E18 | Stage B | Three of five AST node validators are dead; the only node-level violation ever raised duplicates `grammar.check`. | `hull_ast.py:57-89` | **LOW** |

---

## F · L2 / L3

| ID | Plan clause | Finding | Evidence | Sev |
|---|---|---|---|---|
| F1 | Gate 2 "KCS added-resistance-in-waves within workshop scatter via Capytaine" | **Zero implementation.** No drift-force routine, no heading sweep, no Case 2.10 EFD data, no gate row, no test. The largest un-started clause of Gate 2. | `seakeeping.py` (whole file) | **CRITICAL** |
| F2 | §1.3 "the default indirect BIE is inaccurate — switch to the direct BIE" | Every solver is bare `cpt.BEMSolver()`; 2.3.1 defaults to `method='indirect'` — **the code runs the exact trap the plan names.** | `seakeeping.py:49,73,122` | **HIGH** |
| F3 | §1.3 "use the finer 676×372 grid" | Correct **only because the library defaults to it**. A pin or downgrade re-opens the trap silently and no test would notice. | `seakeeping.py:49` | **MED** |
| F4 | honesty rule 1 | **`SeakeepingResult` — the only L2 type carrying `uncertainty_rel` — is defined and never constructed anywhere.** No L2 number ever leaves the module with a convergence-derived sigma. `convergence_sweep()` is called only from tests. | `seakeeping.py:22-29,93-105` | **HIGH** |
| F5 | §1.3 forward speed | `waves.heave_response` convolves a zero-speed RAO with JONSWAP in **absolute** frequency — no encounter-frequency transform. Harmless only because nothing calls it. `heave_rao` hard-codes `wave_direction=0.0` while its docstring says "head/beam". | `waves.py:60-70`; `seakeeping.py:81` | **MED** |
| F6 | Gate 2 sinkage/trim | **The trim sign is inverted.** KCS bow is at +x (verified from the STL); rotation about +y is therefore bow-**down**, so a physically correct answer prints **+0.169°** against EFD's −0.169° — **≈+200% error on a perfect result**. The docstring says this check exists to catch sign errors. | `gate2m.py:59-70`; `benchmarks/kcs.py:125` | **HIGH** |
| F7 | — | **`runs/kcs_free` diverged on timestep 1 and nothing records it.** Log ends at `Time = 0.0012`, alpha solver at its 1000-iteration ceiling, `Min(alpha.water) = -81402.5`, FPE in `GAMGSolver::scale`. Mesh has **47 incorrectly oriented faces, skewness 15.66**. `gate2m.py` prints "no force data yet" — a crash is indistinguishable from an unstarted run. Cause is `nLimiterIter 3` vs the tutorial's 15; the dict structure matches `DTCHullMoving` entry-for-entry. | `runs/kcs_free/log.interFoam:155-159`; `log.checkMesh:128-134` | **CRITICAL** |
| F8 | — | **`post_gci.py` has no `symmetric` handling at all.** `gate2m.py` doubles the drag for a half-domain; `post_gci.py` does not, and `runs/kcs_gci` *is* symmetric → it reports exactly **half** the drag: the "single easiest way to be exactly 2× wrong" that gate2m's own docstring warns about. | `post_gci.py` (no hits); `gate2m.py:94-96` | **HIGH** |
| F9 | §1.3 V&V | **The GCI p-clamp understates uncertainty 5.37× at the low end.** On an exact Richardson triplet with true p=0.1, analytic GCI is 6.392% and `post.gci` reports **1.191%** — precisely the direction that lets a barely-converging triplet claim the ≤2.5% bar. (High-end clamp is conservative and fine.) | `post.py:456` | **HIGH** |
| F10 | CLAUDE.md "a refinement that silently did not happen is a WRONG mesh" | **`setFields … \|\| true`**: if it fails the tank starts as pure air and the run produces plausible garbage — and the newly added `boxToFace` is exactly the entry that can fail on a version mismatch. **`checkMesh … \|\| true` has no fatal threshold**: 47 wrongly-oriented faces went straight to a diverging multi-hour solve. | `run-case.sh:137,163` | **HIGH** |
| F11 | — | The new concurrency guard sits **after** the whole mesh is built and after `rm -rf constant/polyMesh processor*`, so a refused run has already destroyed and rebuilt the mesh; it is also after the resume early-exit (so it never fires in the normal mode), fires for `MESH_ONLY=1` sweeps that CLAUDE.md recommends running concurrently, and misses the serial path. `run_campaign.sh` retries exit-3 up to 20×. | `run-case.sh:129-134` vs `:49-57` | **MED** |
| F12 | — | Pitch restoring stiffness is **3.96× too high** (`ρgA_wp(L/2)²` instead of `ρgI_L`; measured I_L = 19.854 m⁴). ζ_pitch is **0.597, not the intended 0.30** — roughly doubles settling time on a multi-day run. Not an equilibrium bias. Heave is fine by luck (ζ = 0.295). | `case.py:140-144` | **MED** |
| F13 | — | With `--kg` omitted the VCG falls back to VCB → KG-above-keel 0.187 m vs KCS's published 0.2303 m, **19% low**, silently answering a different ship. No warning. | `case.py:180`; `make_case.py:81-82` | **MED** |
| F14 | — | Regenerating a case **fixed** over a previously **free** one leaves `dynamicMeshDict` and `pointDisplacement` in place — the case still moves. The test uses a fresh `tmp_path` and cannot catch it. | `case.py:962-975` | **MED** |
| F15 | — | `correctPhi` and the `boxToFace` block are applied **unconditionally**, so any regenerated fixed case is no longer the configuration that produced the recorded Gate 2M numbers. | `case.py:496-499,523-533` | **MED** |
| F16 | Gate 2 GCI ≤2.5% | **No GCI triplet exists.** `runs/kcs_gci/{coarse,medium,fine}` are generated with **zero force data**. `runs/kcs_sym` is at t=13.7 of 75 s, drift 10.6%; `gate2m` correctly returns NO RESULT. Compute-bound, honestly reported. | `find runs -name 'force*.dat'` | **HIGH** *(open)* |
| F17 | Gate 2 ">=95% of 200 hulls mesh **and converge**" | 75.0% at N=8, RED and recorded. `--solve` exists but has never been run, so the "converges" half has no number at all. | `gates.py:37-41` | **MED** *(open)* |
| F18 | — | KCS submerged volume measures **−0.27%** vs published, while `benchmarks/kcs.py` records −0.09%. The test's `rel=0.01` hides the 0.18% disagreement. | `benchmarks/kcs.py:161` | **LOW** |
| F19 | — | The scatter band is described as "13 independent CFD groups" in `benchmarks/kcs.py` and CLAUDE.md; `SUBMITTED_CT_FINEST` holds **7** entries. The band is attributed to nearly twice the evidence transcribed. | `benchmarks/kcs.py` | **LOW** |
| F20 | — | `stl_submerged_properties` **verified exact** — box and wedge to 1e-12 including at offset waterlines, sphere to −0.016% tessellation. Symmetric half-domain mass *and* inertia halving verified correct both ways. Damper dimensional analysis correct. *(No defect — recorded so it is not re-litigated.)* | measured | — |

---

## G · Manufacturing and rules (the moat)

| ID | Plan clause | Finding | Evidence | Sev |
|---|---|---|---|---|
| G1 | Gate 6 manufacturing back end | **DXF has no units and writes metres.** No `HEADER`, no `$INSUNITS`. A shop importing this cuts a **10 mm** part instead of a 10 m one. | `unroll.py:88-107` | **HIGH** |
| G2 | Gate 6 "DXF nesting" | **There is no nesting — only stacking** by y-offset. No rotation, no sheet boundaries, no packing. The two hull panels are 10.05 × 1.62 m and 10.54 × 1.44 m against a 1.22 × 2.44 m sheet — **neither fits, and nothing splits or scarphs them** — while `engineer.assess()` reports "35 ply sheets". | `unroll.py:97-111`; `engineer.py:52` | **HIGH** |
| G3 | Gate 6 "bill of materials" | **No BOM.** Three aggregate scalars, no line items, no part list, no panel→sheet assignment, no cost. | `engineer.py:23-33` | **MED** |
| G4 | Gate 6 "exported panels re-fold to the hull within tolerance" | **The refold is never tested.** Only the forward direction is; no code maps 2-D back to 3-D. Gate 6's refold clause is unmet. | `tests/test_stageF.py:18-51` | **HIGH** |
| G5 | Gate 6 tolerance | **`dev_error_rel` cannot distinguish developable from non-developable** — it is a per-quad chord residual, i.e. O(h²) for *any* smooth surface. A genuinely non-developable hyperbolic paraboloid scores **9.4e-4 at n=40**, inside the 5e-3 bar. Refining the polyline makes anything look developable. (The hull's topside panel does carry a real warp: 1.88e-3 falling only as O(h^0.7).) | `unroll.py:67-75` | **HIGH** |
| G6 | honesty rule 2 | **The exported solid is not the validated hull** — 12 stations lofted vs 41 validated → 0.50% volume difference between what passed the ladder and what ships. | `export.py:40,52`; `geometry.py:27` | **MED** |
| G7 | Gate 6 "ES-TRIN as executable checkers" | **Not implemented — zero code.** The Solar Liveaboard (Danube) is the one SKU that requires it and PLM lists it "demo green". | `navalai/rules/` | **HIGH** |
| G8 | Gate 6 "ISO 12217-**1/-3**" | **-3 not implemented, and no scope guard.** The grammar admits hulls from 4.0 m and the Dayboat SKU is 4–7 m, so every sub-6 m design is assessed by a standard that does not govern it. | `rules/iso12217.py:1`; `grammar.py:25` | **HIGH** |

---

## H · Uncertainty is decoration

| ID | Finding | Evidence | Sev |
|---|---|---|---|
| H1 | **Every badge sigma is a hard-coded fraction of its own value**: displacement `0.02×`, Wh/NM `0.30×`, GM `0.15\|v\|+0.05`, Rt `0.25Rw+0.10Rf`, freeboard and cb **constants**, solar `0.25×`, `MassItem.sigma_kg = 0.15m` and exactly **0.0 for payload**. All persisted into a DB column documented as "one-sigma". These are declarations, not uncertainties. | `evaluate.py:158-163`; `ui/server.py:82-89`; `energy.py:101` | **MED** |
| H2 | **The one real sigma is computed and thrown away.** `agg.sigma_kg = 178 kg (6.4%)` never reaches `Evaluation`; KG uncertainty never reaches GM. | `weights.py:108`; `evaluate.py:158-163` | **MED** |
| H3 | **"No bare numbers" is violated in user-facing output.** `/eval` returns `weights_kg` with no tier and no sigma while `aggregate()` has already computed `3191 ± 222 kg`. `/pareto` returns three bare floats with one tier on the container. `demo_mission.py` prints GM, freeboard, Wh/NM and solar range with no band. | `ui/server.py:46-51`; `demo_mission.py:45-50` | **MED** |

---

## I · Learning spine

| ID | Plan clause | Finding | Evidence | Sev |
|---|---|---|---|---|
| I1 | §1.2 multi-fidelity | **Co-kriging has never seen a real high-fidelity number** — one call site, fed the synthetic Forrester pair. `training_matrix` is queried only with `"L1"`. PLM still lists "Forrester anchor" as the spine's truth mechanism. | `tests/test_phase3.py:20`; `flywheel.py:55` | **HIGH** |
| I2 | KOH AR(1) | ρ is selected by **absolute** LOO-RMSE, which tracks `\|delta\|` scale — a residual-magnitude minimiser, not the KOH likelihood the comment claims. Non-monotone in data, and in a broad-HF/narrow-LF case it **selects ρ̂ = 0.0000**, silently discarding the low-fidelity model with no diagnostic. | `surrogate.py:109-121` | **HIGH** |
| I3 | — | `CoKriging.is_ood` consults **only `gp_delta`**, ignoring the LF GP whose mean is multiplied by ρ into every prediction. Demo: probes where `gp_lo.is_ood` is `[True, True]` return `[False, False]`. | `surrogate.py:130-131` | **MED** |
| I4 | §1.2 "batch the infill" | `batch_infill`'s mutual-distance filter normalises by the **HF training span**, not the candidate box → with HF on [0.40,0.55] and candidates on [0,1], k=5 returns `[1.00, 0.99, 0.98, 0.97, 0.96]` — five near-identical expensive runs. Batching is defeated exactly where it exists. Also silently returns fewer than k (asked 40 → got 17). | `surrogate.py:151-163` | **HIGH** |
| I5 | Gate 3 "calibration plots show honest uncertainty" | **No calibration metric exists** beyond one coverage assertion that accepts **75% of a 2σ band**. Measured 0.85–0.91 — persistently overconfident. The GP has **no noise term**, so under σ=0.05 label noise coverage drops to 0.782. | `surrogate.py:43,86-87` | **HIGH** |
| I6 | — | GMM EM has no convergence check, no pruning, no restarts, and a **scale-blind flat `1e-6·I`** covariance floor on parameters spanning LWL [4,20] to rocker [0,0.6]. At the shipped default the smallest eigenvalue is **exactly the floor** — already rank-deficient. | `generative.py:33-60` | **MED** |
| I7 | §1.4 latent map | `from_latent()` **silently returns a training hull** instead of the requested point: 2.2% of a 15×15 grid; `Genome.decode` 6.0%. A slider move returns the same hull, badged as the requested design. The test asserts only post-projection feasibility, which the fallback guarantees. | `generative.py:105-125`; `latent.py:50-69` | **HIGH** |
| I8 | PLM "diffusion upgrade slot … behind the same interface" | **There is no interface.** `HullFamilyModel` is a concrete dataclass of GMM/PCA internals; zero `Protocol`/`ABC` in the package. The server calls it with the GMM-specific `k`, and tests reach into `model.X_train`. A diffusion model cannot drop in without editing the server and the tests. | `generative.py:20-28`; `ui/server.py:60` | **HIGH** |
| I9 | Gate 4 "slider p95 < 100 ms" | `/eval` is 6.75 ms ✓ and is the **only** path tested. `/generate` — the function-knob widget — is **1704 ms** (11.5 s at n=20), plus a 1011 ms blocking model fit on first request; `/pareto` blocks 0.4 s. `percentile` semantics are inverted vs the docstring. | `ui/server.py:55-61` | **HIGH** |
| I10 | Gate 7 "wall-clock drops each cycle" | **Not implemented, not measured, not tested.** The only `time.` use is a JSON timestamp. Half of Gate 7 is unbuilt while it reports GREEN. | `flywheel.py:33-39` | **HIGH** |
| I11 | Gate 7 "degrades on KCS/JBC/5415 never deploys" | The "frozen benchmark" is `sample_valid(25, seed=4242)` — **same generator, same distribution** as training. It cannot detect distribution shift. `benchmarks/` is never imported by `flywheel.py`. | `flywheel.py:60-62` | **HIGH** |
| I12 | — | `retrain` does `GP.fit(X, np.log(y))` unconditionally; for `quantity="gm"` that is log of a signed quantity — measured 16/60 negative → **16 NaNs**. `_find_q` explicitly advertises the `"gm"` path. | `flywheel.py:58,83-84` | **MED** |
| I13 | Gate 4 clause 3 | "A designated non-expert produces a hull that passes the full ladder unassisted" — no test, no recorded session, no artifact. Gate 4 is GREEN on two of three clauses, and clause 1 is the tautology in D11. | `tests/test_phase4.py` | **MED** |
| I14 | — | The surrogate spine has **no consumer**: `ui/server.py` never imports `surrogate` or `flywheel`. The slider is under budget *because* the spine is disconnected. | `ui/server.py:23-28` | **MED** |

---

## J · Documentation, process, reproducibility

| ID | Finding | Evidence | Sev |
|---|---|---|---|
| J1 | **Gate 2M has five numbers in circulation and the published one was invalidated by your own bug fix.** `a982414` wrote **9.33e-3 / −151%** into README, PLM §5, PLM §6, ALIGNMENT.md and `docs/CFD-BLOCKER-BRIEF.md`; `cf76704` then proved the force parser double-counted pressure; `b8fcd4e` fixed reading a pre-restart fragment. Only `gates.py` was updated, to −15.4% — **which `scripts/gate2m.py` cannot reproduce from any run dir in the repo.** The only settled grid (`runs/kcs`) reads **C_T 6.6719e-3, −79.8%**. | git archaeology; measured | **CRITICAL** |
| J2 | **README's gate table has no Gate 2U row at all** — a RED gate is invisible in the project's front door. README also lists only **5** honesty rules; rule 6 is absent. | `README.md:38-50` | **MED** |
| J3 | **Gate 6R: code says GREEN, four documents say not done.** It went green in `5bbffb7` and README/PLM were not updated in the same push — a direct violation of PLM §4. | `README.md:50`; `PLM.md:74,88` | **HIGH** |
| J4 | **`requirements.txt` is completely unpinned.** A project whose gates are numeric bars cannot tell a real regression from a scipy minor bump. | `requirements.txt` | **HIGH** |
| J5 | **KCS benchmark geometry is gitignored**, so the "−0.09% displacement" validation silently skips on every machine but this Mac, with no committed checksum or fetch recipe. | `.gitignore`; `test_phase2.py:233` | **MED** |
| J6 | `renders/` is not ignored and **9 PNGs (~2.3 MB) are committed**; `data/exports/hull.{iges,step}` are tracked build artifacts re-modified by 5 of the last 10 commits. | `git ls-files` | **MED** |
| J7 | ALIGNMENT.md carries three findings CLAUDE.md marks **SUPERSEDED 2026-08-05**, and its scorecard still says OpenFOAM execution is BLOCKED/synthetic-only. PLM §3 step 7 requires removal "with a note, never left ambiguous". | `ALIGNMENT.md:57-60,124-128` | **MED** |
| J8 | MACBOOK.md promises "93 passed, 14 GREEN gates"; actual is 135 passed, 15 GREEN + 2 RED across 17. README per-gate test counts stale throughout (Gate 1 13→22, Gate 2 4→18, Gate D 12→19). | measured | **LOW** |
| J9 | **PLM §3 step 4 compliance: 7 of 10 recent commits comply, 3 violate**, and the violations are consistently CFD-path and script changes. **`scripts/gate2m.py` — now the executable authority on Gate 2M — has no test of its own**, which is how its number diverged from `gates.py`'s. | `git log` audit | **MED** *(open — `scripts/` is CFD-owned)* |
| J10 | Uncommitted CFD work sits in the working tree while docs and the gate registry are read as truth. | live tree vs `5bbffb7` | **LOW** |

### J · what closed, and how (2026-08-06)

The fix for this whole section is one idea: **stop the documents being a second
source.** Every J row above is the same defect wearing different clothes — a
machine-readable fact copied into prose, where it cannot be re-derived and
nothing notices when it goes stale.

| ID | Closed by | Mechanism |
|---|---|---|
| J1 | ledger + a test | `data/gate-ledger.json` is the ONLY place a Gate 2M measurement lives, with the superseded-by trail naming all five figures. `test_gate_integrity.py::test_no_document_restates_a_gate_2m_figure` fails if any of them reappears in README, PLM, MACBOOK or ALIGNMENT. `docs/CFD-BLOCKER-BRIEF.md` keeps its figure under a SUPERSEDED banner, because deleting the elimination work in it would cost machine-days to redo. |
| J2 | generation, not correction | README's gate table is emitted by `navalai.gates.readme_block()` with test counts from pytest's own collection; `--readme --write` regenerates it; a test fails when file and runner disagree. Honesty rule 6 added. Gate 2U now has a row — it never did. |
| J3 | **Gate 6R flipped RED** | See the 6R block below. |
| J5 | committed record + a gate row | `data/benchmark_geom/CHECKSUMS.json` (committed although the geometry is not) + `scripts/fetch_benchmark_geom.py`; **Gate 2G** is a row whose whole purpose is that a missing artefact prints `SKIPPED` in the gate table instead of skipping invisibly inside Gate 2. Its module-level skip is deliberate: one always-passing test in that file would make the row read `GREEN (n skipped)`, which answers "is the KCS geometry validated here?" with a yes. |
| J6 | `.gitignore` + `git rm --cached` | `renders/` (9 PNGs, ~2.3 MB) and `data/exports/` (regenerated by the suite on every run) untracked. **Cost, recorded:** CLAUDE.md cites `renders/medium-t40-fixed.png` as the one clean free-surface render; it survives on this Mac and is now reproducible-only elsewhere. |
| J7 | supersessions applied | ALIGNMENT.md's three superseded rows are struck through **with the superseding measurement beside them**, not deleted (PLM §3 step 7). Its scorecard's `BLOCKED 1` row is retired: OpenFOAM executes, so "blocked on hardware" understated the state — Gate 2M is measured and failing, which is a worse claim, not a better one. |
| J8 | literals removed | MACBOOK.md quotes no test or gate count; it points at `python -m navalai.gates`. Its "leave efficiency cores for the OS" was also false — `sysctl hw.perflevel{0,1}` shows no efficiency tier on this M5 Pro, and np=10 is the MEASURED optimum (np=5 212.7 s, np=10 127.2 s, np=15 153.1 s on the same slice). |
| E4 (doc half) | count removed | README's "30+ closed-form checks" and ALIGNMENT.md's identical claim replaced with the measured 9 live / 28 emitted, and the plan's "49" named as wrong. |

**NOT CLOSED, and why.** J4 (`requirements.txt` completely unpinned) and J9
(`scripts/gate2m.py` has no test) are both real and both untouched here: the
files belong to other roles who were editing them concurrently, and pinning an
environment out from under three running agents would have been the more
expensive kind of correct.

**OWED TO CLAUDE.md, and it cannot be written by an agent.** CLAUDE.md's
root-cause section states, as a measured result of the isotropy fix, *"hull
patch fully layered (3 of 3 layers, near-wall 0.795 mm against a 0.706 mm
target)"*. **That claim is now known to be FALSE**: the mesh had NO prism
layers, and the summary table that produced the sentence was printing the
REQUESTED spec rather than the achieved one. The correction belongs in
CLAUDE.md itself, which is the project's operating instructions — an agent must
not edit it on another agent's say-so, so it is recorded here instead. A reader
who acts on that sentence will believe the wall treatment is solved when it is
not, which is exactly the class of error CLAUDE.md exists to prevent.

### J3 · Gate 6R: flipped RED, deliberately, on 2026-08-06

`review.py`'s own docstring reads *"a confirmation that cannot say WHO checked
WHICH edition is not a review, it is a rumour"* — and `is_complete()` checked
`reviewer` and `confirmed` and **not `editions`**, whose two values both read
`"edition not recorded — set this"` (gap D8). The parity gate was green on a
record that admits in its own field values that it cannot name the document it
checked.

`is_complete()` now requires every edition to be present and to carry a year,
and `edition_defects()` reports the reasons in words. **This flipped Gate 6R
red.** Under honesty rule 6 that is the correct outcome and not a regression:
the check got stricter, the state did not get worse, and nothing was reworded to
absorb it. The row is in `data/gate-ledger.json` — metric "dated editions
recorded", watermark 0 of 2, owner **compliance**, review by **2026-11-06** —
and the clearing condition costs no compute: a reviewer writes two edition
strings. `tests/test_phase6r.py` asserts that a properly filled record *does*
complete, so the clearing condition is executable rather than prose.

The suite split in two so this does not swallow what is genuinely verified:
**Gate 6R** (the parity claim) is RED, **Gate 6R-mech** (basis routing, no
unreviewed basis leaking `'standard'`, our own practice values not blessed by a
green gate) is GREEN.

**AND 6R ANSWERS A DIFFERENT QUESTION THAN GATE 6 (gap D9), which no amount of
edition-recording changes.** Gate 6R's scope is **THRESHOLD parity**: does our
number equal the standard's number. **BuildPlan Gate 6's bar is VERDICT
parity** — the same verdict as a qualified reviewer on **≥ 3 reference
designs**, hand-calculated. Zero reference designs and zero hand calculations
exist anywhere in the repository. The reviewer of record is also the project
owner reviewing his own code, with no qualification recorded. **Clearing 6R does
not open Gate 6**, and a green 6R must never be cited as evidence for it.

---

## K · BuildPlan 2 — coverage

At audit time no file matching `refdata`, `ergonom*`, `flotation*`, `arrange*`
or `material*` existed anywhere in the repo. **V2.0 landed 2026-08-06**; the
rest is unchanged.

| Phase | Deliverable | Status |
|---|---|---|
| V2.0 | `refdata/ergonomics.py`, `flotation.py` | **CLOSED 2026-08-06** — Gate V2.0, `navalai/refdata/` |
| V2.1 | Arrangement grammar + AST, L0-A | **ABSENT** |
| V2.2 | Tier E ergonomics checker | **ABSENT** |
| V2.3 | CP + GA arrangement solver | **ABSENT** (no CP library in requirements) |
| V2.4 | Tier F flotation solver | **PARTIAL — struct fields only** |
| V2.5 | Material DB + fire posture | **ABSENT** |
| V2.6 | "Unsinkable Solar Liveaboard" SKU | **ABSENT** |

PLM's "PLANNED" is accurate for V2.1–V2.6. But the hook in `weights.py` is
half-real: `x_m`, `y_m`, `z_m`, `sigma_kg`, `slack`/`fluid_rho`/`fsm_i_t_m4` are
**load-bearing and tested**, while `volume_m3`, `material`, `by_tier` and the
`'E'`/`'F'` tier vocabulary have **no reader anywhere** — no producer ever emits
`tier="E"` or `tier="F"`. Worth one word of precision so a future reader does
not assume the tier half is live.

### K1 · V2.0, and the part of it that is a finding

Gate V2.0's bar is provenance, not physics: *"constants importable, every one
carries source+basis, no bare numbers."* `navalai/refdata/` meets it
structurally — a `RefValue` cannot be constructed without a non-empty `source`
and a `basis` from `('standard-2003' | 'approx' | 'purchased')`, and
`tests/test_refdata.py` walks every value including the ones nested inside
category tables.

**Two provenance decisions are worth recording because both were tempting to
get wrong:**

- **ISO 15085:2024 preview numbers ship as `'approx'`, not `'standard-2003'`.**
  The zone system (Z1/Z2/Z3, Z2 at ≤ 4 kn) and the 400 × 750 mm seat minimum
  are real and verified, and they are **not in the 2003 text**. Labelling them
  `standard-2003` would attribute them to a document that does not contain
  them — quiet false provenance, which is the exact failure the field exists to
  prevent. A test asserts it.
- **Nothing carries `'purchased'`, and a test asserts that too.** Six documents
  are in `refdata.PURCHASE_QUEUE`, and `refdata.absent()` names which quantity
  each purchase unblocks.

**WHAT COULD NOT BE SOURCED, AND IS THEREFORE ABSENT RATHER THAN INVENTED**
(`refdata.absent()`, 11 entries). An invented constant is indistinguishable
from a transcribed one the moment it lands in a module, and the tiers above
will divide by it:

| Absent | Why |
|---|---|
| Panero & Zelnik anthropometric tables | The book is named as the canonical decomposition and its 5th–95th percentile organisation is verified, but no body dimension is reproduced in anything we hold. **No anthropometric number is in `refdata`**, and a test asserts no constant cites Panero. Every accommodation number we do ship is marine practice and says so. |
| percentile stretch factor | BuildPlan 2 §1.1 states the MECHANISM (1979 data, modern bodies larger) and no value. A plausible invented multiplier would silently resize every Tier-E envelope. `RefValue.percentile` exists and is `None` everywhere — the honest state. |
| ABYC H-41 dimensions | Only the 1780 N (400 lb) load and "unassisted reboarding on all boats" are verified at claim level; ladder step spacing, immersion depth and handhold clearance are in inches behind membership. |
| handhold spacing | Named as a first-class layout element by two sources; neither yields a spacing. |
| ISO 15085:2024 per-zone equipment lists | Paywalled. Zone STRUCTURE encoded, 2003 numeric floors alongside. |
| ISO 12217-3:2022 thresholds | Paid text. (§1's own refutation list corrects an earlier "category D ceiling" claim to **C or D**.) |
| USCG reference-area freeboard rules | The level-flotation criteria include freeboard rules against a reference area; the plan names them without the geometry, and they cannot be inferred from the heel angles. |
| ISO 9094 fire thresholds | Not captured free at all. **No fire number ships.** |
| fire-retardant coating ratings | §1.4 sends the specifics to the purchase list explicitly. |
| SG for aluminium and steel | The plan prints **K** for both and SG for neither. Back-solving `1/(1-K)` gives 2.70 and **8.33** — and structural steel is ~7.85, so the second would be a manufactured number wearing transcribed clothes. K is stored alone, with the discrepancy in the note. |
| **USCG handbook worked examples** | **This one is a gate defect, not a data gap.** Gate V2.4's bar is *"reproduces the USCG handbook worked examples exactly, including the plywood −0.81 negative-contribution case"* — and no worked example is transcribed anywhere in this repository. That is gap **E1's shape** (Gate 1's bar named Holtrop-Mennen while nothing implemented it, and Gate 1 printed GREEN), caught before V2.4 can be written. V2.4 must not go green on the method alone. |

**What IS transcribed, with the K = (SG−1)/SG core:** GRP +0.33 (SG 1.50),
fir plywood **−0.81** (SG 0.55 — negative, i.e. inherently buoyant), aluminium
+0.63, steel +0.88; 2 lb/ft³ PU foam netting 60.3 lb/ft³ ≈ 966 kg/m³ after
self-weight and a 5% moisture allowance; the swamped criteria (heel ≤ 10°,
off-centre load ≤ 30°); 3-D placement (propulsion flotation within 36 in of the
transom, passenger flotation within 6 in of the sides); §183.114 durability
(≤ 5% loss after 30-day immersion) and the **polystyrene ban** that follows from
it; the Etap acceptance criterion (fully flooded, freeboard loss < 3% LOA, still
manoeuvrable). `submerged_factor()` computes K rather than tabulating it, and a
test closes the printed K against the printed SG for the two materials where
both are given — one unit in the last printed place, the same trick
`benchmarks/holtrop_cases.py` uses on an OCR'd table.

Two numbers are labelled **OURS** and must never be cited as sourced: the −15%
foam aging derate and "foam is never the only defence". Both are policy adopted
in response to the field evidence; no standard sets either. And
`SCOPE_IS_NOT_OURS` records that 33 CFR 183 governs monohulls **under 20 ft**
and therefore does not govern a single SKU — we adopt its method, and the output
is an assessment aid, exactly as honesty rule 5 requires of `rules/`.

---

## What is genuinely strong

Stated plainly so the register is not read as the whole picture.

- **The physics kernels are correct** and independently re-derived (E section header).
- The RED gates are honestly red and **stayed red under pressure**.
- `status_of()` refusing to call an all-skipped suite GREEN is a real, tested
  anti-soft-green mechanism.
- `limits.py` single-sourcing after a measured 0.35-vs-0.45 GM drift is exactly
  the right response to the defect class.
- The pre-push hook's `--suites-only` reasoning is correct and works today.
- **There is genuinely no path from LLM JSON to a parameter vector** — the
  whitelist drops `__class__`, `__reduce__`, `hull_params` and the literal
  grammar names. Rule 3's structural claim is sound; the leak is via thresholds.
- `MassItem`/`aggregate` refuse negative mass, negative sigma, slack tanks with
  no free-surface moment, and empty lists ("refusing to invent a displacement").
- `stl_submerged_properties` is exact; the symmetric half-domain mass/inertia
  halving is correct.
- `test_phase6r.py::test_our_own_practice_values_are_not_blessed_by_this_gate`
  is an unusually careful piece of gate design.
- No optimiser parameter runs to a bound (0/15 in all four missions).
- STEP/IGES loft reproduces the validated geometry to −0.08…−0.29% on displacement.

---

## The structural observation

**The check and the thing checked share an owner.** `flywheel` writes the
baseline it will later be judged against (D3, D4). `gate2m` lets the uncertainty
it computes widen the band it must fall inside (D6). `gates.py` reads a status
string authored by whoever would have to record the failure (D1). The LLM
supplies both the design category and the energy plan that the requirements are
graded against (B-section, D). Each is individually fixable; the pattern is what
lets a green ladder mean less than it says — and it is why the fix plan opens by
making the gates unfakeable rather than by fixing physics.
