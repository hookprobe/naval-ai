# Mission → Hull
## A Research-Grounded Build Plan for an Autonomous Naval-Architecture Validation AI

**Goal.** A system where a non-expert states a mission in natural language — *"a 6-tonne solar-electric liveaboard for the Danube and Black Sea coast"* — and the AI generates a family of valid hulls, lets them steer **form and function with sliders backed by instant physics surrogates**, and guarantees that anything they keep has passed a calibrated, tiered physics-and-rules validation ladder before it exports as build-ready geometry.

**Method.** This plan is grounded in a deep-research sweep (2018–2026 literature; 24 primary sources fetched and claim-extracted; 11 core claims adversarially verified 3-0, zero refuted; remaining claims carry direct primary-source quotes but no panel vote). Every load-bearing choice below cites what is *proven*, flags what is *hype*, and names the gaps we must build ourselves.

---

## 1 · What the research actually supports

### 1.1 Generative hull representation — SOLVED ENOUGH TO REUSE

The single most important finding: **the parametric-hull + guided-diffusion stack is proven, open, and runs on a consumer GPU.**

- **Ship-D** (Bagazinski & Ahmed, MIT, 2023 — [arXiv:2305.08279](https://arxiv.org/abs/2305.08279), [github.com/noahbagz/ShipD](https://github.com/noahbagz/ShipD)) is the reference open dataset: **30,000 hulls, each defined by 45 parameters** (principal dimensions, midship, bow, stern, bulb), with meshes, point clouds, images, and 32 wave-drag coefficients per hull (8 speeds × 4 drafts, Michell integral). The parameterization reconstructs 12 real hulls from public CAD repositories — it covers practical design space, not just synthetic shapes. Caveat (authors' own): sampling favors coverage over realism, so generative models need realism filtering.
- **The killer pattern — algebraic feasibility.** Ship-D validity is **49 closed-form constraints on the 45-parameter vector, checkable in ~0.2 ms — ~10,000× faster than mesh-based checking** (1.77 s for an 80k-vertex mesh). This is what makes slider-rate validity gating physically possible. We adopt this pattern wholesale.
- **ShipGen** (JMSE 2023, [mdpi.com/2077-1312/11/12/2215](https://www.mdpi.com/2077-1312/11/12/2215)) — guided tabular DDPM: **99.5% feasible generation vs ~0.7% for random sampling (149×)**; in a head-to-head, unguided DDPM hit 0.511 feasibility vs **0.007 for a tabular GAN** — diffusion beats GANs for constraint-heavy parametric generation. Performance guidance from surrogate gradients steered samples to 91.4% lower wave drag (at Michell fidelity).
- **C-ShipGen** ([arXiv:2407.03333](https://arxiv.org/pdf/2407.03333)) — *conditional* guided diffusion: beat an NSGA-II baseline on resistance in all 5 test cases (>25% reductions) while holding displacement within 5% of target, **no retraining per objective**, and sampled **512 candidate hulls in ~2.5 s on an RTX 4090** (vs ~80 min for the NSGA-II run). This is the engine that makes "function sliders" real-time.
- **ShipHullGAN** (CMAME 411, 2023, [arXiv:2305.00210](https://arxiv.org/abs/2305.00210)) proves the multi-class generative idea at scale (52,591 validated hulls, geometric-moment shape-signature tensors) but its corpus is **not public** — useful as design precedent, not as a building block.

**Verdict:** reuse Ship-D's parameterization + constraint pattern; extend it for small craft; train ShipGen-style guided diffusion on top. **Hype flag:** every headline "drag reduction %" in this literature is measured against *linear potential-flow* labels, not RANS or tank data. Gains do not transfer 1:1 up the fidelity ladder — our own ladder must re-verify.

### 1.2 Fast hydrodynamics surrogates — MULTI-FIDELITY WINS; PINNs ARE NOT READY

- **Multi-fidelity is the proven architecture.** A two-fidelity **Co-Kriging** surrogate on DTMB 5415 (potential-flow NMShip + RANS naoe-FOAM, ~50 low- plus ~30–50 high-fidelity samples, 5-D design space) predicted its optimum to **~0.05% error after CFD re-validation, while single-fidelity Kriging was off by −5.98%** — and delivered ~5% real drag reduction vs <3%. Single-fidelity surrogates *win on paper and lose after verification*. A multi-fidelity **DNN** (transfer learning, SJTU) beat Kriging in the same loop (6.73% vs 5.59% reduction on DTMB 5415).
- **Adaptive sampling matters, batched.** On KCS with 8 design variables, EI-style sequential infill needed 66 RANS samples vs 80 one-shot and cut surrogate error near the optimum from 5.98–10.63% to **≤1.20%**. But one-point-per-cycle infill is too slow wall-clock — batch the infill. Realistic optimization gains on an already-good hull are **small single digits** (1.63% resistance on KCS); the honest pitch is *validated design freedom for novices*, not magic drag savings.
- **Neural operators are real but young.** **ShipNet** (MARIN/Damen, regDGCNN geometric deep learning) predicts hull surface pressure at R² ≈ 0.98 and wave elevation at R² ≈ 0.91 with a **~1500× speedup (0.15 s/case)** — genuinely interactive-rate — but was trained on only 420 potential-flow sims over two yacht families, with no physics constraints and no RANS baseline. DeepONet airfoil work shows 32,253× speedups from 40 training sims, but in a deliberately laminar 2-parameter regime. **Use neural operators as an acceleration tier once our own database is big enough; do not lead with them.**
- **PINNs: research track only.** The NeurIPS 2021 failure-modes paper ([arXiv:2109.01050](https://arxiv.org/abs/2109.01050)) shows standard PINNs fail on even moderately complex PDEs due to ill-conditioned loss landscapes; PINN-RANS work solves only canonical 2D flows *and requires boundary reference data* — it is reconstruction, not a forward solver. Nothing in the sweep shows a PINN beating a data-driven surrogate on free-surface hull flow. **PINNs are excluded from the plan of record.**
- **The humble fast tier survives scrutiny.** Michell integral + ITTC-1957 friction line remains the practical millisecond-scale physics tier used in every generative pipeline surveyed — it is what the sliders actually run on, with the surrogate spine learning the *correction* to higher fidelities.

### 1.3 The open-source validation stack — WORKABLE, WITH NAMED TRAPS

- **Capytaine** (BEM seakeeping, [capytaine.org](https://capytaine.org/stable/)) is alive (v2.3.1, Oct 2025), NREL-funded since 2022, GPLv3, and computes exactly what we need: added mass, radiation damping, diffraction/Froude-Krylov, RAOs, hydrostatic stiffness. Known traps from NREL's own accuracy study: the **default indirect BIE is inaccurate on thin plates — switch to the direct BIE**; the legacy 328×46 Green-function tabulation causes oscillations — use the finer 676×372 grid; convergence can need 10,000+ panels, so **automated mesh-sensitivity checks are mandatory**, and forward speed is approximate (pair with Holtrop/RANS for resistance).
- **OpenFOAM + snappyHexMesh batch automation is proven in production research** — SJTU's hull-optimization pipeline runs fully scripted blockMesh + snappyHexMesh (y+ ≈ 30, wall functions) with formal grid-convergence verification against KCS tank data. Budget the engineering effort here anyway: mesh-failure handling *is* the product work.
- **Calibration data exists and is free.** Tokyo 2015 workshop ([t2015.nmri.go.jp](https://t2015.nmri.go.jp/)) distributes IGES geometry + towing-tank data (resistance, self-propulsion, PIV, **added resistance in waves, free-running course keeping**) for JBC/KCS/ONRT; the Springer 2020 assessment documents exactly which quantities RANS predicts reliably. OpenFOAM V&V on KCS/DTC/KVLCC2/JBC is published (Islam & Guedes Soares 2019) with two hard warnings: **the uncertainty number you report depends materially on which V&V method you implement, and V&V is case-specific** — you cannot calibrate once on KCS and assume the bounds hold for novel hulls. Our ladder therefore reports per-design uncertainty, not a global badge.
- **MuJoCo/MJX**: no free surface; keep it only for mass properties, mooring/lifting loads, and contact — never hydrodynamics.

### 1.4 Sliders & interaction — THE PATTERN HAS A PUBLISHED PRECEDENT

Danhaive & Mueller's **performance-conditioned VAE** (Automation in Construction 2021) is the direct precedent: a high-dimensional structural design space compressed to a **2-D latent map the designer navigates as sliders, with performance maps precomputed over the latent grid**, and a percentile-normalized performance score that is *itself* a 0-to-1 knob. Demonstrated only on a single-objective 36-variable truss — the multi-objective, multi-physics hull version is ours to build, but the interaction model is validated. Combined with C-ShipGen-style conditioning (hundreds of candidates per second) and 0.2 ms feasibility checks, **the slider UX is technically de-risked end to end.**

### 1.5 LLM / text-to-CAD — TRANSLATOR YES, GEOMETRY AUTHOR NO

- The sobering result: frontier coding agents writing CadQuery from engineering briefs, validated by FEA against typed requirements, scored **0 strict passes in 400 first attempts**; with 10 rounds of structured feedback (blueprints + multi-view renders + FEA reports), mean requirement-pass climbed 38.8% → 60.5%. One-shot text-to-geometry is unsolved as of 2026.
- What *does* work: **LLM-as-UI for ship design** (Choi et al., Ocean Engineering 2026) — a **LoRA fine-tune on a single consumer GPU** reliably translates natural-language design requests into the structured parameters a design back-end needs; base models without fine-tuning were *not* reliable. And the MDO-agent literature (Designer/Modeler/Verifier/Optimizer loops) works semi-autonomously with humans at the boundary-condition step.
- The reusable pattern from the FEA-agent benchmark: **requirements as typed, executable pass/fail checkers** — grade designs against a physical contract, not against a gold mesh.

**Verdict:** the LLM translates mission → structured spec, names sliders, explains results, and orchestrates. It never authors geometry directly and never sits in the validation path. (Same governance rule as any serious autonomous system: **AI proposes, deterministic gates enforce.**)

### 1.6 Rules-as-code — THE GAP, AND THE MOAT

The sweep found **no credible open-source implementation** of ISO 12217 (small-craft stability), ISO 12215-5 (scantlings), or ES-TRIN checking — only forum-grade spreadsheets. Every serious tool is commercial and closed. This is the one layer we must build from the standards documents ourselves — and because it's the layer that makes designs *legal and insurable*, it is also the defensible moat. Executable-rule-checkers (the pattern from §1.5) are the implementation vehicle.

---

## 2 · System architecture

```
 NL mission ──► LLM Translator (LoRA) ──► Mission Spec (typed, versioned)
                                              │
        ┌─────────────────────────────────────┤
        ▼                                     ▼
  GENERATIVE CORE                       SLIDER SURFACE
  guided tabular diffusion              form sliders  = semantic grammar params
  (ShipGen/C-ShipGen recipe)            function knobs = conditional guidance
  45–90 param hull grammar              2-D latent map (PVAE precedent)
        │                                     │   every widget: <100 ms feedback
        ▼                                     ▼
  L0  ALGEBRAIC GATE      ~0.2 ms   49+ closed-form feasibility + developability
  L1  HYDRO/EMPIRICAL     ~ms       hydrostatics·GM · Michell+ITTC · Holtrop · energy budget
  L2  BEM SEAKEEPING      ~min      Capytaine (direct BIE) RAOs, added resistance
  L3  RANS CFD            ~hrs      OpenFOAM interFoam, scripted snappy, GCI per design
  R   RULES GATE          ~ms       ISO 12217 · ISO 12215-5 · ES-TRIN as executable checkers
        │
        ▼
  SURROGATE SPINE — multi-fidelity (L1→L2→L3) co-kriging / MF-DNN,
  batched-EI infill, per-prediction uncertainty; retrained as the DB grows
        │
        ▼
  PROVENANCE DB — every hull genome + every result + solver versions + mesh
  hashes + uncertainty; benchmarks (Wigley/KCS/JBC/DTMB 5415) as regression gates
```

**Three non-negotiable honesty rules** (each traceable to a research finding):
1. **Fidelity badges everywhere.** Every number shown carries its tier (L1/L2/L3) and an uncertainty band — because low-fidelity-guided gains demonstrably don't survive re-validation (§1.2), and V&V is case-specific (§1.3).
2. **Nothing ships un-re-validated.** Any design the user wants to keep is re-run up the ladder (trust-region re-validation) before export.
3. **The LLM is out of the loop.** Translation and explanation only; the gates are deterministic code.

---

## 3 · The phased build plan

Effort scale: ▪ = person-weeks, ▪▪ = 1–2 person-months, ▪▪▪ = a quarter+. Compute: consumer GPU throughout except L3 (batchable RANS — a workstation or small cloud burst).

### Phase 0 — Foundation & data spine ▪▪
Adopt Ship-D's `HullParameterization` and its 49-constraint pattern; extend the grammar for small craft (deadrise, chine, transom, outboard/pod geometry) and add **developable-surface constraints** (plywood/metal panel buildability — absent from all surveyed work, hard requirement for real boats). Stand up the provenance DB (PostgreSQL: genome, solver versions, mesh hashes, results, uncertainty). Build the benchmark harness skeleton around Wigley (analytic), KCS/JBC (Tokyo 2015 data), DTMB 5415.
**Gate 0:** round-trip 12+ known hulls through the grammar; constraint check <1 ms; DB reproduces any stored result bit-for-bit.

### Phase 1 — Deterministic ladder, L0+L1 ▪▪
Hydrostatics (volume, GM, trim), Michell + ITTC-1957, Holtrop-Mennen, and the **mission-physics models the literature ignores**: weight/CG budget and a solar-energy model (panel area × latitude yield vs hotel + propulsion load — for an electric boat this couples directly into displacement and is a first-class objective, not a post-check). Baseline optimizer: NSGA-II directly on grammar parameters (no learning needed yet).
**Gate 1:** Wigley wave resistance matches the analytic/tank curve within published Michell error bars; Holtrop reproduces its own validation set; a full mission evaluation (all L1 physics) completes in <50 ms.

### Phase 2 — High-fidelity tiers, L2+L3 ▪▪▪ ← *most engineering risk lives here*
Capytaine with the known traps pre-fixed (direct BIE, fine Green-function tabulation, automated panel-convergence sweeps); scripted OpenFOAM (blockMesh + snappyHexMesh, y+ ≈ 30, wall functions) with automated mesh-quality triage and GCI computed **per design**, not assumed.
**Gate 2:** KCS/JBC resistance, sinkage, trim within the Tokyo-2015 scatter band with documented grid uncertainty (target ≤ ~2.5%, the published bar); KCS added-resistance-in-waves within workshop scatter via Capytaine; ≥95% of a 200-random-valid-hull batch meshes and converges unattended.

### Phase 3 — Surrogate spine ▪▪▪
Multi-fidelity surrogates (co-kriging first — proven at 50+50 samples; MF-DNN as the challenger) learning L3 from L1/L2, with **batched** EI infill and per-prediction uncertainty. Out-of-distribution detection: a query far from training support must *say so* and trigger real physics instead of extrapolating.
**Gate 3:** ≤1–2% surrogate error near optima on the benchmark hulls (the published sequential-sampling bar); calibration plots show honest uncertainty; OOD queries reliably escalate to L2/L3.

### Phase 4 — Generative core + slider surface ▪▪▪ ← *the product moment*
Train guided tabular diffusion (ShipGen recipe: feasibility classifier on deliberate invalid samples + surrogate-gradient guidance; C-ShipGen conditioning for target displacement/speed/beam). Build the UI: **form sliders** bound to semantic grammar parameters, **function knobs** (target speed, range, payload, Energy/NM percentile) driving conditional generation, a 2-D latent map for browsing hull families, every widget answering in <100 ms from L0+L1+surrogate, with fidelity badges and uncertainty bands rendered as first-class UI.
**Gate 4:** ≥99% of generated hulls pass L0 (the published 99.5% bar); slider-to-feedback p95 < 100 ms; a designated non-expert produces a hull that passes the full ladder unassisted.

### Phase 5 — Natural-language mission front end ▪▪
LoRA fine-tune (single consumer GPU — published as sufficient) translating mission language into the typed Mission Spec; agentic orchestration for the long-running jobs (L2/L3 campaigns, infill rounds) with the executable-requirement-checker pattern grading outcomes. Explanation surface: *why this hull, which constraint binds, what the uncertainty means.*
**Gate 5:** ≥90% of a held-out mission-brief test set translates to correct specs; zero pathways for the LLM to mutate geometry or override a gate.

### Phase 6 — Rules-as-code + manufacturing export ▪▪▪ ← *the moat*
Implement ISO 12217-1/-3 stability assessment, ISO 12215-5 scantlings, and ES-TRIN (Danube) checks as typed executable checkers with clause-level citations in every verdict. Manufacturing back end: developable panel unrolling → DXF nesting, STEP/IGES export, bill of materials, build-hours estimate.
**Gate 6:** verdict parity with hand calculations by a qualified reviewer on ≥3 reference designs; exported panels re-fold to the hull within tolerance.

### Phase 7 — The flywheel ▪▪ then continuous
Every session's physics results append to the DB; scheduled surrogate retraining with benchmark **regression gates** (a retrained model that degrades on KCS/JBC/5415 never deploys); neural-operator tier (ShipNet-style regDGCNN) added *only when* the database is large enough to train one honestly — this is where the 1500×-speedup literature becomes usable rather than aspirational.
**Gate 7:** surrogate error decreases release-over-release on a frozen benchmark suite; full mission→validated-hull wall-clock drops with each cycle.

---

## 4 · Build vs. reuse (one line each)

| Layer | Reuse | Build ourselves |
|---|---|---|
| Hull grammar | Ship-D 45-param + 49 constraints | small-craft params, developability, energy/weight models |
| Generation | ShipGen/C-ShipGen recipes (open) | retraining on extended grammar, realism conditioning |
| Fast physics | Michell, ITTC, Holtrop (public formulations) | integration + calibration harness |
| Seakeeping | Capytaine | direct-BIE config, convergence automation, forward-speed pairing |
| CFD | OpenFOAM + snappyHexMesh | unattended meshing triage, per-design GCI, batch orchestration |
| Surrogates | co-kriging/MF-DNN methods (published) | the trained models, OOD guards, retraining flywheel |
| Sliders/UI | PVAE interaction pattern (published) | the entire multi-objective product surface |
| NL front end | LoRA recipe (published) | mission-spec schema, fine-tuning corpus, guardrails |
| Rules | — nothing exists — | ISO 12217 / 12215-5 / ES-TRIN as executable checkers |
| Benchmarks | Tokyo 2015, DTMB 5415, Wigley (free) | the regression-gate harness |

## 5 · Top risks, honestly

1. **Unattended CFD robustness** (Phase 2) — the literature proves scripted pipelines work *in labs on known hulls*; making them survive arbitrary generated geometry is the largest unknown. Mitigation: mesh-triage automation is a first-class deliverable, and the surrogate spine reduces how often L3 must run.
2. **Fidelity-gap disappointment** — headline generative gains are potential-flow-only; users will see slider promises shrink after re-validation. Mitigation: uncertainty bands and fidelity badges from day one; never display an unvalidated number as truth.
3. **Rules liability** — a wrong ISO verdict has real-world consequences. Mitigation: clause-level citations, qualified-reviewer parity gate, and explicit "assessment aid, not certification" framing until a notified body relationship exists.
4. **Grammar coverage** — 45 parameters cover ships; small craft (multihulls, planing forms) need grammar extensions that no public dataset labels. Mitigation: Phase 0 scope; generate + label our own data through the ladder (that's what it's for).

---

*Sources: 24 primary documents fetched and claim-extracted; core claims verified 3-0 by adversarial panel. Key anchors: Ship-D (arXiv:2305.08279; github.com/noahbagz/ShipD) · ShipGen (JMSE 11(12):2215) · C-ShipGen (arXiv:2407.03333) · ShipHullGAN (CMAME 411:116051) · Co-Kriging DTMB 5415 (Ocean Eng., S0029801821015523) · SJTU sequential-sampling KCS (Ocean Eng. 2024) · MF-DNN (Chin. J. Ship Res. 19(6)) · ShipNet (arXiv:2606.15356) · DeepONet airfoils (arXiv:2302.00807) · PINN failure modes (arXiv:2109.01050, NeurIPS 2021) · PINN-RANS (Phys. Fluids 34:075117) · Capytaine (capytaine.org; NREL OMAE 2024 accuracy study) · OpenFOAM V&V (Ocean Eng., Islam & Guedes Soares 2019) · Tokyo 2015 (t2015.nmri.go.jp; Springer 978-3-030-47572-7) · PVAE design subspaces (Autom. Constr., S0926580521001151) · CAD-Coder (arXiv:2505.19713) · FEA-feedback CAD agents (arXiv:2605.17448) · MDO LLM agent (arXiv:2511.17511) · LLM-as-UI ship design (Ocean Eng., S0029801826011789).*
