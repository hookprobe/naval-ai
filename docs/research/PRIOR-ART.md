# RESEARCH RECORD — prior art, tooling, market and competitors

> **Role: RESEARCH / EVIDENCE.** The literature sweeps behind the platform's
> architectural choices, the tooling verdicts (what to reuse, what to build),
> the component-data and manufacturing findings, and an honest competitive
> reading. It is the reasoning that justifies `docs/BUILD-PLAN.md`; it carries
> no plan and no status of its own.
>
> **Provenance caveat, recorded because it cannot be checked from this tree.**
> The two earliest sweeps lead with *"24 primary sources, 11 claims
> adversarially verified 3-0"* and *"50 sources, 76 votes, 71 upheld, 5
> refuted"*. **Neither has an artifact anywhere in the repository.** Two of the
> five refuted claims are named; the other three are not. A third sweep
> (2026-08-06, 28 searches, 8 primary documents) ran with **no adversarial
> panel at all** — the consultant endpoint was unreachable, which is recorded
> rather than hidden — and tags every claim **[P]** (primary text fetched) or
> **[S]** (search summary; a lead, not a threshold).

---

## 1 · Generative hull representation — solved enough to reuse

**The parametric-hull + guided-diffusion stack is proven, open, and runs on a
consumer GPU.**

- **Ship-D** (Bagazinski & Ahmed, MIT, 2023 — [arXiv:2305.08279](https://arxiv.org/abs/2305.08279),
  [github.com/noahbagz/ShipD](https://github.com/noahbagz/ShipD)) is the
  reference open dataset: **30 000 hulls, each defined by 45 parameters**
  (principal dimensions, midship, bow, stern, bulb), with meshes, point clouds,
  images, and 32 wave-drag coefficients per hull (8 speeds × 4 drafts, Michell
  integral). The parameterisation reconstructs 12 real hulls from public CAD
  repositories, so it covers practical design space rather than synthetic
  shapes. Authors' own caveat: sampling favours coverage over realism, so
  generative models need realism filtering.
- **The killer pattern — algebraic feasibility.** Ship-D validity is **49
  closed-form constraints on the 45-parameter vector, checkable in ~0.2 ms —
  ~10 000× faster than mesh-based checking** (1.77 s for an 80k-vertex mesh).
  This is what makes slider-rate validity gating physically possible, and it is
  adopted wholesale as the L0 tier.
  *Measured correction to this project's own use of it:* the grammar was built
  with **15** parameters, not 45–90, and carries **9 live** closed-form
  constraints, not 49 (gap E4). Quote the built number, not the paper's.
- **ShipGen** (JMSE 2023, [mdpi.com/2077-1312/11/12/2215](https://www.mdpi.com/2077-1312/11/12/2215))
  — guided tabular DDPM: **99.5% feasible generation vs ~0.7% for random
  sampling (149×)**; in a head-to-head, unguided DDPM hit 0.511 feasibility vs
  **0.007 for a tabular GAN** — diffusion beats GANs for constraint-heavy
  parametric generation. Performance guidance from surrogate gradients steered
  samples to 91.4% lower wave drag, at Michell fidelity.
- **C-ShipGen** ([arXiv:2407.03333](https://arxiv.org/pdf/2407.03333)) —
  *conditional* guided diffusion: beat an NSGA-II baseline on resistance in all
  5 test cases (> 25% reductions) while holding displacement within 5% of
  target, **no retraining per objective**, and sampled **512 candidate hulls in
  ~2.5 s on an RTX 4090** (vs ~80 min for the NSGA-II run).
- **ShipHullGAN** (CMAME 411, 2023, [arXiv:2305.00210](https://arxiv.org/abs/2305.00210))
  proves the multi-class generative idea at scale (52 591 validated hulls,
  geometric-moment shape-signature tensors) but its corpus is **not public** —
  design precedent, not a building block. See §7.

**Hype flag:** every headline "drag reduction %" in this literature is measured
against *linear potential-flow* labels, not RANS or tank data. Gains do not
transfer 1:1 up the fidelity ladder — the ladder must re-verify.

---

## 2 · Surrogates — multi-fidelity wins; PINNs are not ready

- **Multi-fidelity is the proven architecture.** A two-fidelity **co-kriging**
  surrogate on DTMB 5415 (potential-flow NMShip + RANS naoe-FOAM, ~50 low- plus
  ~30–50 high-fidelity samples, 5-D design space) predicted its optimum to
  **~0.05% error after CFD re-validation, while single-fidelity kriging was off
  by −5.98%** — and delivered ~5% real drag reduction vs < 3%. **Single-fidelity
  surrogates win on paper and lose after verification.** A multi-fidelity DNN
  (transfer learning, SJTU) beat kriging in the same loop (6.73% vs 5.59%).
- **Adaptive sampling matters, batched.** On KCS with 8 design variables,
  EI-style sequential infill needed 66 RANS samples vs 80 one-shot and cut
  surrogate error near the optimum from 5.98–10.63% to **≤ 1.20%**. But
  one-point-per-cycle infill is too slow in wall-clock — batch the infill.
  Realistic optimisation gains on an already-good hull are **small single
  digits** (1.63% resistance on KCS); the honest pitch is *validated design
  freedom for novices*, not magic drag savings.
- **Neural operators are real but young.** **ShipNet** (MARIN/Damen, regDGCNN)
  predicts hull surface pressure at R² ≈ 0.98 and wave elevation at R² ≈ 0.91
  with a **~1500× speedup (0.15 s/case)** — genuinely interactive-rate — but was
  trained on only 420 potential-flow sims over two yacht families, with no
  physics constraints and no RANS baseline. DeepONet airfoil work shows 32 253×
  speedups from 40 training sims, in a deliberately laminar 2-parameter regime.
  **Use neural operators as an acceleration tier once the database is big
  enough; do not lead with them.**
- **PINNs: research track only.** The NeurIPS 2021 failure-modes paper
  ([arXiv:2109.01050](https://arxiv.org/abs/2109.01050)) shows standard PINNs
  fail on even moderately complex PDEs due to ill-conditioned loss landscapes;
  PINN-RANS work solves only canonical 2-D flows *and requires boundary
  reference data* — reconstruction, not a forward solver. Nothing in the sweep
  shows a PINN beating a data-driven surrogate on free-surface hull flow.
  **Excluded from the plan of record.**
- **The humble fast tier survives scrutiny.** Michell integral + ITTC-1957
  friction line remains the practical millisecond-scale physics tier used in
  every generative pipeline surveyed — it is what the sliders run on, with the
  surrogate spine learning the *correction* to higher fidelities.

---

## 3 · The open-source validation stack — workable, with named traps

- **Capytaine** (BEM seakeeping, [capytaine.org](https://capytaine.org/stable/))
  is alive (v2.3.1, Oct 2025), NREL-funded since 2022, GPLv3, and computes added
  mass, radiation damping, diffraction/Froude-Krylov, RAOs and hydrostatic
  stiffness. Known traps from NREL's own accuracy study: the **default indirect
  BIE is inaccurate on thin plates — switch to the direct BIE**; the legacy
  328×46 Green-function tabulation causes oscillations — use the finer 676×372
  grid; convergence can need 10 000+ panels, so **automated mesh-sensitivity
  checks are mandatory**; forward speed is approximate, so pair with
  Holtrop/RANS for resistance.
- **OpenFOAM + snappyHexMesh batch automation is proven in production
  research** — SJTU's hull-optimisation pipeline runs fully scripted blockMesh +
  snappyHexMesh (y+ ≈ 30, wall functions) with formal grid-convergence
  verification against KCS tank data. Budget the engineering effort anyway:
  mesh-failure handling *is* the product work. (What that actually cost here is
  `docs/research/CFD.md` §4.)
- **Calibration data exists and is free.** Tokyo 2015
  ([t2015.nmri.go.jp](https://t2015.nmri.go.jp/)) distributes IGES geometry plus
  towing-tank data (resistance, self-propulsion, PIV, **added resistance in
  waves, free-running course keeping**) for JBC/KCS/ONRT; the Springer 2020
  assessment documents which quantities RANS predicts reliably. OpenFOAM V&V on
  KCS/DTC/KVLCC2/JBC is published (Islam & Guedes Soares 2019) with two hard
  warnings: **the uncertainty number you report depends materially on which V&V
  method you implement, and V&V is case-specific** — you cannot calibrate once
  on KCS and assume the bounds hold for novel hulls. Hence per-design
  uncertainty, not a global badge.
- **MuJoCo/MJX:** no free surface. Keep it for mass properties, mooring/lifting
  loads and contact — never hydrodynamics.

---

## 4 · Sliders and interaction — the pattern has a published precedent

Danhaive & Mueller's **performance-conditioned VAE** (Automation in
Construction 2021) is the direct precedent: a high-dimensional structural design
space compressed to a **2-D latent map the designer navigates as sliders, with
performance maps precomputed over the latent grid**, and a
percentile-normalised performance score that is *itself* a 0-to-1 knob.
Demonstrated only on a single-objective 36-variable truss — the multi-objective,
multi-physics hull version is ours to build, but the interaction model is
validated. Combined with C-ShipGen-style conditioning and 0.2 ms feasibility
checks, **the slider UX is technically de-risked end to end.**

*Measured against that precedent here:* compressing 15 parameters to an 8-D
latent costs **2–3× surrogate accuracy** (Stage E). A geometric-moment
descriptor (§7) is a credible third option and can be evaluated against both on
the existing benchmark.

---

## 5 · LLMs in engineering — translator yes, geometry author no; orchestrator yes, reasoner no

- The sobering result: frontier coding agents writing CadQuery from engineering
  briefs, validated by FEA against typed requirements, scored **0 strict passes
  in 400 first attempts**; with 10 rounds of structured feedback (blueprints +
  multi-view renders + FEA reports), mean requirement-pass climbed 38.8% →
  60.5%. **One-shot text-to-geometry is unsolved as of 2026.**
- What *does* work: **LLM-as-UI for ship design** (Choi et al., Ocean
  Engineering 2026) — a **LoRA fine-tune on a single consumer GPU** reliably
  translates natural-language design requests into the structured parameters a
  back end needs; base models without fine-tuning were *not* reliable. The
  MDO-agent literature (Designer/Modeler/Verifier/Optimizer loops) works
  semi-autonomously with humans at the boundary-condition step.
- The reusable pattern: **requirements as typed, executable pass/fail
  checkers** — grade designs against a physical contract, not against a gold
  mesh.
- **EngiAI** [P] ([arXiv:2605.19743](https://arxiv.org/abs/2605.19743))
  benchmarks LLM-driven engineering workflows (topology optimisation,
  simulation, manufacturing export, HPC orchestration) with a hierarchical
  supervisor routing to seven specialised agents:
  - Frontier models reached **96–97% task completion** on the well-structured
    workflow; a 4B open model managed **55%**.
  - **Conditional reasoning was the failure mode**: on one domain the best model
    reached only **53%**, and on 36 failed runs **all four models failed
    identically by selecting the opposite conditional branch**.
  - Retrieval was **necessary, not optional** — scores collapsed to near zero
    without it, and an empty index degraded performance substantially.
  - Multi-step instruction following **decayed over long workflows** (one model
    dropped from 100% to 50% depending on prompt style).

**Correlated failure across independent models on the same conditional branch is
the decisive result: redundant agents do not vote their way out of it.** That is
the evidence for the platform law — agents orchestrate and explain, deterministic
code decides — and against a fleet of autonomous component agents.

---

## 6 · Rules-as-code, component data, manufacturing and the market

### Rules-as-code is the gap and the moat

The sweep found **no credible open-source implementation** of ISO 12217
(small-craft stability), ISO 12215-5 (scantlings) or ES-TRIN checking — only
forum-grade spreadsheets. Every serious tool is commercial and closed. This is
the one layer that must be built from the standards documents, and because it is
the layer that makes designs *legal and insurable*, it is also the defensible
moat.

### The click-to-order bottleneck is the catalog, not the CAD

- **Instant-quote manufacturing is solved for machined parts** [S]: Xometry's
  engine takes STEP/DXF/STL, runs ML geometry analysis, returns price, lead time
  and automated DFM feedback against 4 500+ manufacturers; Protolabs returns
  automated design analysis within hours. *Geometry in → priced, manufacturable
  order out* is proven and commercial.
- **Distributed CNC kit manufacturing is proven at building scale** [P]
  (WikiHouse manufacturing guide, fetched): designs ship as **DXF/DWG nested on
  2440 × 1220 mm sheets with named, colour-coded layers** (labels, screw marks,
  internal cuts, external profiles, pocket mills); **0.25 mm offsets baked in**
  so an 18 mm slot is cut 18.5 mm; **T-bone corners** to avoid fillet
  interference; incoming sheet thickness policed at **17.1–18.1 mm** with
  sub-17.4 mm sheets demoted to facing panels; **20–40 minutes per sheet**;
  **0.5–1 t of waste per house**; microfactory setup **£50–100k** against
  £15–50m for a traditional factory.
- **Boat kits are an existing industry** [S]: CLC, Fyne Boat Kits, Pygmy,
  Denman, Dudley Dix (including a CNC kit for a 47 ft plywood catamaran) already
  sell CNC-cut okoume kits, and several will **cut a customer's own DXF** in
  their own stock. The manufacturing network for a plywood kit boat does not
  need to be built — it needs to be addressed.
- **Nesting has a fresh open-source solver** [P]: *sparrow*
  ([arXiv:2509.13329](https://arxiv.org/abs/2509.13329), built on **jagua-rs**,
  Apache-2.0, github.com/JeroenGar/jagua-rs) solves 2-D irregular strip packing
  by decomposing into a sequence of feasibility problems and "consistently
  outperforms the state of the art — in some cases by an unexpectedly wide
  margin". Quantitative tables were not extractable from the PDF and remain
  **owed**. Commercial true-shape nesters quote **5–10% waste** [S] as the
  achievable band.
- **And then the catalog stops being free.** There is **no open marine component
  data standard**. ETIM and eCl@ss [S] are rich and attribute-typed but scoped to
  electrical/technical goods; **IMPA** [S] is 6-digit ship-*stores* coding
  (~50 000 codes, CSV licence) for consumables, not engineering components with
  performance curves; UNSPSC is procurement taxonomy, not specification. Nothing
  gives a motor's efficiency-vs-RPM curve, its controller's CAN protocol, or its
  bolt pattern in machine-readable form. Published propulsive-efficiency figures
  were found **only** for Torqeedo and Oceanvolt (Torqeedo 10 kW pod ≈ 56%,
  Oceanvolt 15 kW ServoProp ≈ 51%) [S].

**Verdict:** component data is a **curation cost, not an AI cost**. The plywood
kit path needs no catalog at all, which is why it is the shortest real path to a
boat you can order. (The one legislated future data source — the EU battery
passport — is in `docs/research/COMPLIANCE.md` §6.)

### Energy claims must be gated against measured evidence, not brochures

The reference mission ("cross the Mediterranean entirely on solar") is exactly
the claim most likely to be false, so the anchors matter:

- A well-integrated array on a **12 m catamaran peaks around 6 kW and yields
  ~20–30 kWh on a good day** [S]; Sunreef Eco quotes up to 30 kWh [S].
- Silent Yachts' current flagship: **17 kWp of solar, 350 kWh of storage** [S].
- The honest one: a **Silent 62 crossed the Atlantic (~3 800 nm) burning
  ~5 500 L of fuel**, battery-powered for 72% of the journey — ~40% less fuel
  than a comparable 60 ft motor catamaran [S]. **The flagship solar yacht burned
  fuel to cross an ocean.** Any "unlimited autonomy" output must survive
  comparison with that number or be labelled as what it is.
- A watermaker producing 3 600 L/day draws **~14 kWh** [S] — over half a 12 m
  cat's entire daily solar yield, for one appliance.

### The market shape

Configure-price-quote for boats already exists [S] — Infor/Godlan/Missoun/
SWIFTSELL sell CTO configurators feeding ERP, with 3-D visualisation and
automatic production documentation, and SAP variant configuration [S] has done
super-BOM → order-BOM explosion for decades. Naval-architecture software (NAPA,
Maxsurf, Orca3D, ShipConstructor, AVEVA, CAESES, Paramarine, DELFTship) [S]
covers geometry and analysis. **Nobody joins them.** A configurator picks from a
catalog a human engineered; a CAD tool draws what a human decided. The gap —
*mission → governed, physics-validated, novel design → its own orderable BOM* —
is the same shape as the rules-as-code gap: unclaimed because it is genuinely
hard, and defensible for the same reason.

---

## 7 · The closest competitor, and what it proves

`computemaritime.com` (Compute Maritime / NeuralShipper) is a London deep-tech
company positioned as *"Generative AI for Maritime Design"*. It should be
studied rather than dismissed.

**What they have that this project does not:**

| | Them | Us |
|---|---|---|
| Generative model | **ShipHullGAN** — deep convolutional GAN trained on **52 591 physically validated real designs** (containers, tankers, bulkers, tugs, crew supply). Shapes converted to a fixed-dimension **shape-signature tensor** built from **geometric moments**, which is what lets physics-informed terms into the representation. *CMAME* 411 (2023) | `generative.py`: a GMM fitted to grammar-sampled synthetic vectors, diffusion as a planned drop-in |
| Geometry output | NURBS/CAD directly; they claim to be *"the first model to directly output a CAD model"*, arguing *"even slight surface irregularities can significantly affect outcomes"* | analytic kernel + developable-panel unroll → DXF; STEP/IGES via CadQuery |
| CFD | Simcenter **STAR-CCM+**, integrated with Siemens Digital Industries Software | OpenFOAM |
| Backing | NVIDIA AI-startup accelerator; £700k UK Clean Maritime Demonstration Competition; UK SHORE / Innovate UK; partners Siemens, HP, Rapid Fusion, BYD Naval Architects, University of Southampton | one repository and two machines |
| Delivered | **GenDSOM**: a 32.5 m twin-hull crew transfer vessel for offshore wind, 24 technicians + 4 crew; a hydrofoil component printed on a robotic large-format AM system | the SKUs are unbuilt |

That is a real lead on generative modelling, data, surface quality and
industrial partnership, and **the 52 591-design corpus is a moat this project
cannot close by scraping.** Say so plainly.

**What their own material shows is missing.** Their About page states the scope:
*"concept development and detailed design"*, justified by *"80% of a product's
environmental impact is determined at the design stage"*, with a value
proposition of *"10% cheaper, 20% faster, and 50% more efficient."* There is **no
mention of sales or quoting, no digital twin, no fleet data or telemetry, no
in-service performance, no post-deployment optimisation.** By their own
description they are a **BUILD-phase tool** — the same category as NAPA and
Maxsurf, built AI-native. SELL and RUN are uncontested.

**And then the headline number.** GenDSOM is reported as saving *"101 671 litres
of fuel and 258.7 tonnes of CO2 per vessel every year"*, an *"11.1% reduction in
annual fuel consumption and an 8.9% reduction in CO2 emissions"*, with a 106 kWh
energy surplus against a 34 kWh deficit for the baseline. What was physically
manufactured in that project was **a hydrofoil component**, not the vessel.

**So 101 671 litres per year is a simulation output, quoted to six significant
figures, for a boat that has not been operated.** Compare Airseas: 20% from
modelling and land tests, **16%** from sea trials. This project's own history has
the same shape — one Gate 2M measurement circulated as five different figures
until only one was reproducible from any run directory (gap J1).

That is not a criticism of their engineering, which is clearly strong. It is the
observation that **the entire field, incumbents and AI-native challengers alike,
reports design-stage predictions as achievements, and nobody is closing the loop
with operational evidence.**

### What to take from them, in our own way

1. **Geometric moments as a shape representation.** Their shape-signature tensor
   is the strongest technical idea in their published work: moments are
   analytic, cheap, dimension-fixed and physics-informed — exactly the L0 cost
   class. **Research item, not a decision.**
2. **Our generative model has the closed-loop defect too, and worse.**
   `generative.py` fits a GMM to grammar-feasible vectors this system generated.
   The related trap is already on record — a "100% raw feasibility" claim
   measured on a rejection sampler with `grammar.check` *inside its loop*, true
   by construction (gap D11). Training on real hulls is how they escaped that. A
   public hull corpus is worth acquiring even at a fraction of 52 591.
3. **Surface quality is a real requirement, not vanity.** Their argument that
   irregular surfaces corrupt downstream analysis is correct, and this project
   has been bitten by the geometric version of it (a mirrored-IGES mesh that
   died on the first timestep at 73 wrongly-oriented faces). Worth a
   fairness/continuity gate on emitted geometry.
4. **Their positioning line is a gift, and it can be beaten honestly:** 80% of
   impact is determined at design — **and 100% of it is measured in operation.**

---

## 8 · Build vs reuse, one line each

| Layer | Reuse | Build ourselves |
|---|---|---|
| Hull grammar | Ship-D parameterisation + closed-form constraint pattern | small-craft params, developability, energy/weight models |
| Generation | ShipGen/C-ShipGen recipes (open) | retraining on the extended grammar, realism conditioning |
| Fast physics | Michell, ITTC, Holtrop (public formulations) | integration + calibration harness |
| Seakeeping | Capytaine | direct-BIE config, convergence automation, forward-speed pairing |
| CFD | OpenFOAM + snappyHexMesh | unattended meshing triage, per-design GCI, batch orchestration |
| Surrogates | co-kriging / MF-DNN methods (published) | the trained models, OOD guards, retraining flywheel |
| Sliders/UI | PVAE interaction pattern (published) | the entire multi-objective product surface |
| NL front end | LoRA recipe (published) | mission-spec schema, fine-tuning corpus, guardrails |
| Nesting | *sparrow* / jagua-rs (Apache-2.0), evaluated against an in-house baseline | kerf/thickness offsets, layer conventions, scarph splitting |
| Rules | — nothing exists — | ISO 12217 / 12215-5 / ES-TRIN as executable checkers |
| Benchmarks | Tokyo 2015, DTMB 5415, Wigley (free) | the regression-gate harness |
| Governance | PROV-O / SysML v2 as **export** formats | the in-process compiler (never a second runtime) |

---

## 9 · Sources

Generative and surrogate — Ship-D (arXiv:2305.08279; github.com/noahbagz/ShipD) ·
ShipGen (JMSE 11(12):2215) · C-ShipGen (arXiv:2407.03333) ·
ShipHullGAN (CMAME 411:116051; arXiv:2305.00210) ·
Co-Kriging DTMB 5415 (Ocean Eng., S0029801821015523) ·
SJTU sequential-sampling KCS (Ocean Eng. 2024) · MF-DNN (Chin. J. Ship Res. 19(6)) ·
ShipNet (arXiv:2606.15356) · DeepONet airfoils (arXiv:2302.00807) ·
PINN failure modes (arXiv:2109.01050, NeurIPS 2021) · PINN-RANS (Phys. Fluids 34:075117).

Validation stack — Capytaine (capytaine.org; NREL OMAE 2024 accuracy study) ·
OpenFOAM V&V (Ocean Eng., Islam & Guedes Soares 2019) ·
Tokyo 2015 (t2015.nmri.go.jp; Springer 978-3-030-47572-7).

Interaction and LLMs — PVAE design subspaces (Autom. Constr., S0926580521001151) ·
CAD-Coder (arXiv:2505.19713) · FEA-feedback CAD agents (arXiv:2605.17448) ·
MDO LLM agent (arXiv:2511.17511) · LLM-as-UI ship design (Ocean Eng., S0029801826011789) ·
EngiAI (arXiv:2605.19743) · RAGulating Compliance (arXiv:2508.09893).

Manufacturing, catalog and market — WikiHouse manufacturing guide ·
sparrow / jagua-rs (arXiv:2509.13329, Apache-2.0) · Xometry / Protolabs ·
CLC / Fyne / Dix CNC kit industry · ETIM / eCl@ss / IMPA ·
Torqeedo & Oceanvolt propulsive efficiency ·
Silent Yachts / Sunreef solar and Atlantic-crossing figures ·
CPQ / SAP variant configuration.

Competitors — [Compute Maritime](https://www.computemaritime.com/) ·
[About (scope and claims)](https://www.computemaritime.com/about) ·
[Siemens Simcenter on the NeuralShipper integration](https://blogs.sw.siemens.com/simcenter/ship-design-with-generative-ai/) ·
[Siemens / Compute Maritime partnership](https://www.ship-technology.com/news/siemens-compute-maritime-generative-ai/) ·
[GenDSOM crew transfer vessel](https://rapidfusion.co.uk/blogs/case-studies/compute-maritime-about-research-technology-careers-newsroom-contact-worlds-first-ai-designed-crew-transfer-vessel-revealed-by-compute-maritime-and-partners).
