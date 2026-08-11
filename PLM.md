# NavalAI Product Line Management (PLM)

> **Role: PLATFORM LAW.** One validated design kernel, many vessel products,
> and the lifecycle by which work becomes truth. This file answers WHAT the
> platform is made of, WHAT a product is allowed to be, WHO owns what, and HOW
> a change is admitted.
>
> **Narrowed 2026-08-11 to §1–§4, and the narrowing is the point.** It used to
> carry a gate registry (§5) and a roadmap board (§6). Both were second copies:
> the registry is `navalai/gates.py`, live status is `python -m navalai.gates`,
> every RED row's watermark/owner/review-by is `data/gate-ledger.json`, and the
> roadmap is `docs/BUILD-PLAN.md` §16. §5 opened with the sentence *"No gate
> status or measurement is restated in this file"* and was false of itself in
> five places, which is precisely the failure mode a management file is prone
> to. It is not restated here because it is not here at all.
>
> | Question | Ask |
> |---|---|
> | what are we allowed to build, and who owns it? | this file |
> | what is built, in what order, against what bars? | `docs/BUILD-PLAN.md` |
> | what is green, red, or overdue? | `python -m navalai.gates`, `data/gate-ledger.json` |
> | what is still broken? | `python scripts/reconcile_gaps.py`, `docs/GAP-REGISTER.md` |
> | how do I work in this tree? | `CLAUDE.md`, `docs/LESSONS.md` |

## 1 · The platform ("one system")

Everything ships from one shared kernel — never per-product forks:

| Platform asset | Code | Truth mechanism |
|---|---|---|
| Hull grammar + typologies | `navalai/grammar.py`, `hull_ast.py` | L0 algebraic gate, <1 ms |
| Physics ladder L1→L3 | `hydrostatics/resistance/seakeeping/cfd` | benchmark anchors (Wigley, Hulme, KCS) |
| Surrogate spine | `surrogate.py`, `latent.py` | Forrester anchor, OOD refusal, frozen-benchmark regression gate |
| Generative core | `generative.py` (diffusion upgrade slot) | L0-feasible sampling, measured on the MODEL's raw draws — a feasibility figure measured on a rejection sampler with `grammar.check` inside its loop is true by construction and means nothing |
| Mission front end | `mission.py`, `translate.py` | held-out brief set, no geometry pathway |
| Rules tier R | `navalai/rules/` | clause provenance, fails closed, assessment-aid framing |
| Provenance | `db.py` (content-addressed) | append-only, solver-versioned |
| Agent shell | `agents.py` | typed messages, audit trail, Fitness=∞ gatekeeper |

**Platform law:** a product may *configure* the kernel (parameter subspaces,
rule profiles, mission presets); it may never bypass a gate or fork physics.

## 2 · Product lines (SKUs are configurations, not code)

| Line | Mission preset | Grammar subspace | Rules profile |
|---|---|---|---|
| **Hull-Line v1** | any (research base) | full 15-param | ISO 12217/12215 subset |
| **Solar Liveaboard** | 6 t, Danube/Black Sea, cat C/D | sharp-chine, 9–14 m | + ES-TRIN |
| **Dayboat** | 1–3 t, cat D | pram/sharp-chine 4–7 m | cat D profile |
| **Full-Vessel Line v2** | + interior/exterior arrangement + unsinkability | + arrangement grammar | + ergonomics tier E + flotation tier F |
| **Kit-Line v3** | the self-certifiable envelope (LH < 12 m, cat C/D), delivered as a CNC kit | unchanged | unchanged, one policy profile, one delivery mode |

Adding a product = one mission preset + one grammar subspace + one rules
profile. If it needs new physics or new grammar axes, that is a PLATFORM change
and goes through the lifecycle below.

**What is built of each line is not stated here** — it moved, and it belongs to
`python -m navalai.gates` and `docs/BUILD-PLAN.md`. A line listed above is a
declared configuration of the kernel, not a claim that it ships.

## 3 · Lifecycle: requirement → retirement

1. **Requirement** — user need or field finding, stated with a measurable bar.
2. **Research** — deep-research sweep; claims verified; recorded in
   `docs/research/` with citations and with the verification that *actually
   happened*, not the one intended.
3. **Decision** — chief architect locks the approach and the gate definition in
   `docs/BUILD-PLAN.md`; divergences from prior plans get a *measured receipt*
   (`ALIGNMENT.md`).
4. **Implementation** — code + gate test in the same change; the test comment
   names the motivating incident, and the test feeds the guard the verbatim
   input it must reject.
5. **Gate** — GREEN only by meeting the bar; METAL-GATED / REVIEW-GATED when
   evidence needs hardware or a qualified human. Never soften a bar to pass.
6. **Evidence** — benchmark and field results land in provenance/baselines;
   regression gates keep them honest forever.
7. **Retirement** — dead parameters, superseded stand-ins, stale rules: removed
   **with a note, never left ambiguous**, and a superseded measurement is struck
   through *with the superseding measurement beside it*.

## 4 · Roles (each mappable to an agent session or a human)

| Role | Owns | Machine |
|---|---|---|
| **chief-architect** | plans, gates, platform law, this file | fortress001 |
| **cfd-engineer** | OpenFOAM campaigns, GCI, benchmark calibration | Mac (simulation node) |
| **verification** | test suite, gate ladder, regression honesty | fortress001 |
| **ml-engineer** | diffusion upgrade, LoRA translator, surrogate retrains | Mac |
| **compliance** | rules tier, clause parity review queue, the purchase queue, the AI Act and battery-passport questions | human-gated |
| **ergonomics-architect** | arrangement grammar + tier E | either |
| **governance-architect** | `navalai/policy/`, the legal envelope, delivery-mode routing | either |
| **supply-architect** | the component contract, catalog curation, closure metrics | either |

Coordination: git is the handoff (pull → work → push). A role announces scope in
its commit messages. Cross-role platform changes need a plan update in the same
push.
