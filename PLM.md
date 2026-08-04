# NavalAI Product Line Management (PLM)

> One validated design kernel. Many vessel products. Every claim gated.
> This file is the management layer any Claude Code instance (or human)
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

## 4 · Roles (each mappable to a Claude instance or a human)

| Role | Owns | Machine |
|---|---|---|
| **chief-architect** | plans, gates, platform law, this file | fortress001 |
| **cfd-engineer** | OpenFOAM campaigns, GCI, KCS calibration | Mac (simulation node) |
| **verification** | test suite, gate ladder, regression honesty | fortress001 |
| **ml-engineer** | diffusion upgrade, LoRA translator, surrogate retrains | Mac |
| **compliance** | rules tier, clause parity review queue (Gate 6R) | human-gated |
| **ergonomics-architect** | arrangement grammar + tier E (v2, planned) | either |

Coordination: git is the handoff (pull → work → push). A role announces scope
in its commit messages. Cross-role platform changes need a plan-doc update in
the same push.

## 5 · Gate registry (single source: `python -m navalai.gates`)

GREEN = enforced by tests · METAL-GATED = needs hardware/software evidence ·
REVIEW-GATED = needs qualified human. Current open items: Gate 2M (KCS
calibration — cfd-engineer, IN PROGRESS), Gate 6R (ISO parity — compliance).

## 6 · Roadmap board (update in place)

| Epic | Owner | State |
|---|---|---|
| Own-hull GCI triplet | cfd-engineer | **HELD at medium, deliberately.** The v2 outer mesh WORKS — coarse/medium are monotonic (−2639.4 → −2469.4 N; r measured 1.410 vs √2) after fixing the two v1 causes (unresolved free surface, non-systematic family). But a wetted-only y+ pass showed only **2.0% of wet hull faces inside 30 ≤ y+ ≤ 300**, and viscous drag is 2.62× ITTC-57 — the wall model is invalid where friction is made. The fine grid was NOT run: ~3 h to converge onto that buys a precise wrong number. Near-wall mesh sweep in progress; re-run the triplet once after adopting the winner. |
| Gate 2M: KCS calibration vs Tokyo-2015 | cfd-engineer | GEOMETRY + ACCEPTANCE DATA IN HAND. `benchmarks/kcs.py` carries the EFD (C_T 3.711e-3 @ Fn 0.26) and the 13-group scatter band, extracted from the proceedings PDF. Hull regenerates from `KCS.igs` via `iges2stl.py --sew-tol --mirror-y` + `cap_planar_holes`, validated to **-0.09% on displacement**. Runs once the own-hull triplet frees the cores. |
| **Second benchmark anchor for the SKUs** (DTMB 5415 / DSYHS / Series 62) | cfd-engineer | QUEUED — KCS calibrates the instrument but shares none of the chine/transom/spray physics the product lines depend on; Gate 2M alone must not be read as small-craft validation. See `ALIGNMENT.md`. |
| L3→co-kriging wiring (first HF points into the spine) | ml-engineer | BLOCKED on Gate 2M |
| Guided tabular diffusion behind `HullFamilyModel` | ml-engineer | READY (PyTorch-MPS) |
| LoRA mission translator above the sanitizing seam | ml-engineer | READY (mlx-lm) |
| **Full-Vessel Line v2** (arrangement + ergonomics + unsinkability) | chief-architect → ergonomics-architect | RESEARCH RUNNING → `BuildPlan2-FullVessel.md` |
| ES-TRIN rules profile; ISO parity review | compliance | QUEUED |
