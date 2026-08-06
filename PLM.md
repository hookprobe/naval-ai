# NavalAI Product Line Management (PLM)

> One validated design kernel. Many vessel products. Every claim gated.
> This file is the management layer any coding-agent session (or human)
> picks up to know WHAT we build, WHO owns it, and HOW work becomes truth.

## 1 · The platform ("one system")

Everything ships from one shared kernel — never per-product forks:

| Platform asset | Code | Truth mechanism |
|---|---|---|
| Hull grammar + typologies | `navalai/grammar.py`, `hull_ast.py` | L0 algebraic gate, <1 ms |
| Physics ladder L1→L3 | `hydrostatics/resistance/seakeeping/cfd` | benchmark anchors (Wigley, Hulme, KCS) |
| Surrogate spine | `surrogate.py`, `latent.py` | Forrester anchor, OOD refusal, frozen-benchmark regression gate |
| Generative core | `generative.py` (diffusion upgrade slot) | 100% L0-feasible sampling |
| Mission front end | `mission.py`, `translate.py` | ≥90% brief set, no geometry pathway |
| Rules tier R | `navalai/rules/` | clause provenance, fails closed, assessment-aid framing |
| Provenance | `db.py` (content-addressed) | append-only, solver-versioned |
| Agent shell | `agents.py` | typed messages, audit trail, Fitness=∞ gatekeeper |

**Platform law:** a product may *configure* the kernel (parameter subspaces,
rule profiles, mission presets); it may never bypass a gate or fork physics.

## 2 · Product lines (SKUs are configurations, not code)

| Line | Mission preset | Grammar subspace | Rules profile | Status |
|---|---|---|---|---|
| **Hull-Line v1** | any (research base) | full 15-param | ISO 12217/12215 subset | SHIPPED (gates green) |
| **Solar Liveaboard** | 6 t, Danube/Black Sea, cat C/D | sharp-chine, 9–14 m | + ES-TRIN (todo) | reference product; demo green |
| **Dayboat** | 1–3 t, cat D | pram/sharp-chine 4–7 m | cat D profile | latent (typology exists) |
| **Full-Vessel Line v2** | + interior/exterior arrangement + unsinkability | + arrangement grammar | + ergonomics tier E + flotation tier F | PLANNED — see `BuildPlan2-FullVessel.md` |
| **Kit-Line v3** | self-certifiable envelope: LH < 12 m, cat C/D | developable/plywood subspace (unchanged) | + policy profile `self-certifiable-eu` | PLANNED — see `BuildPlan3-MissionToOrder.md` |

**Delivery mode is a product property, decided by governance, not by sales.**
`BuildPlan3` §0: RCD Art. 20 lets **cat D**, and **cat C under 12 m built to
harmonised standards**, use Module A (self-certification, no notified body);
Art. 2(2)(a)(vii) puts **own-use builds outside the Directive** while they stay
own-use. The same envelope keeps the design AI clear of EU AI Act Art. 6(1)(b),
which requires third-party conformity assessment for the high-risk limb to bite.
Outside that envelope a SKU acquires a notified body AND a high-risk
classification in the same step.

Adding a product = one mission preset + one grammar subspace + one rules
profile. If it needs new physics or new grammar axes, that's a PLATFORM
change and goes through the lifecycle below.

## 3 · Lifecycle: requirement → retirement

1. **Requirement** — user need or field finding, stated with a measurable bar.
2. **Research** — deep-research sweep; claims verified; recorded in the plan
   doc with citations (pattern: `NavalArchAI-BuildPlan.md` §1).
3. **Decision** — chief architect locks approach + gate definition in the
   plan; divergences from prior plans get a *measured receipt* (`ALIGNMENT.md`).
4. **Implementation** — code + gate test in the same change; the test
   comment names the motivating incident.
5. **Gate** — GREEN only by meeting the bar; METAL-GATED / REVIEW-GATED when
   evidence needs hardware or a qualified human. Never soften a bar to pass.
6. **Evidence** — benchmark + field results land in provenance/baselines;
   regression gates keep them honest forever.
7. **Retirement** — dead parameters, superseded stand-ins (e.g. GMM when
   diffusion lands), stale rules: removed with a note, never left ambiguous.

## 4 · Roles (each mappable to an agent session or a human)

| Role | Owns | Machine |
|---|---|---|
| **chief-architect** | plans, gates, platform law, this file | fortress001 |
| **cfd-engineer** | OpenFOAM campaigns, GCI, KCS calibration | Mac (simulation node) |
| **verification** | test suite, gate ladder, regression honesty | fortress001 |
| **ml-engineer** | diffusion upgrade, LoRA translator, surrogate retrains | Mac |
| **compliance** | rules tier, clause parity review queue (Gate 6R) | human-gated |
| **ergonomics-architect** | arrangement grammar + tier E (v2, planned) | either |
| **governance-architect** | `navalai/policy/`, legal envelope, delivery-mode routing (v3, planned) | either |
| **supply-architect** | component contract, catalog curation, BOM closure (v3, planned) | either |

Coordination: git is the handoff (pull → work → push). A role announces scope
in its commit messages. Cross-role platform changes need a plan-doc update in
the same push.

## 5 · Gate registry (single source: `python -m navalai.gates`)

GREEN = enforced by tests · METAL-GATED = needs hardware/software evidence ·
REVIEW-GATED = needs qualified human. RED = ran and missed its bar, kept red.
Current open items: **Gate 2M RED** (KCS C_t -151% vs EFD), **Gate 2U RED**
(unattended meshing 75% vs the >=95% bar), Gate 6R (ISO parity — compliance).

## 6 · Roadmap board (update in place)

| Epic | Owner | State |
|---|---|---|
| Own-hull GCI triplet | cfd-engineer | **HELD at medium, deliberately.** The v2 outer mesh WORKS — coarse/medium are monotonic (−2639.4 → −2469.4 N; r measured 1.410 vs √2) after fixing the two v1 causes (unresolved free surface, non-systematic family). But a wetted-only y+ pass showed only **2.0% of wet hull faces inside 30 ≤ y+ ≤ 300**, and viscous drag is 2.62× ITTC-57 — the wall model is invalid where friction is made. The fine grid was NOT run: ~3 h to converge onto that buys a precise wrong number. Near-wall mesh sweep in progress; re-run the triplet once after adopting the winner. |
| Gate 2M: KCS calibration vs Tokyo-2015 | cfd-engineer | **RAN, and RED.** C_t 9.33e-3 vs EFD 3.711e-3 (E%D -151%), outside the scatter band; only 16.3% of wetted faces in the y+ band. Kept RED, not softened. It did its job: the own-hull C_T/C_F ~ 9.8 is now known to be OUR SETUP, not the hull. Next: fix the near-wall mesh, then re-measure. Prior status for the record — `benchmarks/kcs.py` carries the EFD (C_T 3.711e-3 @ Fn 0.26) and the 13-group scatter band, extracted from the proceedings PDF. Hull regenerates from `KCS.igs` via `iges2stl.py --sew-tol --mirror-y` + `cap_planar_holes`, validated to **-0.09% on displacement**. Runs once the own-hull triplet frees the cores. |
| **Second benchmark anchor for the SKUs** (DTMB 5415 / DSYHS / Series 62) | cfd-engineer | QUEUED — KCS calibrates the instrument but shares none of the chine/transom/spray physics the product lines depend on; Gate 2M alone must not be read as small-craft validation. See `ALIGNMENT.md`. |
| L3→co-kriging wiring (first HF points into the spine) | ml-engineer | BLOCKED on Gate 2M |
| Guided tabular diffusion behind `HullFamilyModel` | ml-engineer | READY (PyTorch-MPS) |
| LoRA mission translator above the sanitizing seam | ml-engineer | READY (mlx-lm) |
| **Full-Vessel Line v2** (arrangement + ergonomics + unsinkability) | ergonomics-architect | PLAN PUBLISHED — `BuildPlan2-FullVessel.md` (research: 50 sources, 71/76 votes upheld); next: V2.0 refdata spine |
| **Mission→Order Line v3** (governance · procurement · manufacturing · twin) | governance-architect | PLAN PUBLISHED — `BuildPlan3-MissionToOrder.md` (sweep 2026-08-06: 28 searches, 8 primary docs fetched; **no adversarial panel — consultant endpoint down**, so every claim carries a [P]/[S] tag and [S] claims may not become gate thresholds). Next: V3.0 governance kernel. Hold the line on its structural gate — **delete the constitution and every physics result must be bit-identical**, else we have built a second constraint engine and re-created the `limits.py` drift bug at platform scale. |
| Standards/books purchase queue (ISO 15085:2024, 12217-3, 9094; **ISO 12215-7 multihull loads — now TOP, it blocks any catamaran SKU**; **ABYC E-11/E-13**; DNV-RP-A204; ISO 19030-1/-2; ABYC H-41; Panero & Zelnik; Larsson & Eliasson) | compliance | QUEUED (basis='approx' floors ship meanwhile) |
| ES-TRIN rules profile; ISO parity review | compliance | QUEUED |
| CI/CD enforcement of the gate ladder | verification | **DONE** — `.github/workflows/gates.yml` + `.githooks/pre-push` (install: `scripts/install-hooks.sh`). Also fixed a soft-green in the runner itself: pytest exits 0 when every test SKIPS, so a missing optional dep used to print GREEN having verified nothing. |
| Unattended-meshing robustness (plan Gate 2: >=95% of 200 random hulls) | cfd-engineer | **MEASURED, RED — Gate 2U.** 75.0% at N=8 (`scripts/mesh_robustness.py`). 2 of 8 sampled valid hulls produced zero-volume cells or wrongly oriented faces, both fatal to interFoam on timestep 1. BuildPlan Risk #1 is now a number, not a worry. Re-measure at N=200 when there is a spare machine-day. |
