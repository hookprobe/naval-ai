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
> | what is this for, and what is the gap it fills? | this file, §0 |
> | what are we allowed to build, and who owns it? | this file |
> | what is built, in what order, against what bars? | `docs/BUILD-PLAN.md` |
> | what is green, red, or overdue? | `python -m navalai.gates`, `data/gate-ledger.json` |
> | what is still broken? | `python scripts/reconcile_gaps.py`, `docs/GAP-REGISTER.md` |
> | how do I work in this tree? | `CLAUDE.md`, `docs/LESSONS.md` |

## 0 · Vision — the one sentence

> **NavalAI generates the safest, most energy-efficient, BUILDABLE vessel for a
> specified mission and budget — and shows its evidence.**

Each word in it is load-bearing. *Safest* and *most energy-efficient* are
objectives the ladder measures; *buildable* is a constraint the manufacturing
back end enforces rather than a hope; *for a specified mission and budget* means
the mission is the INPUT, not a caption written after the fact; and *shows its
evidence* is the part that is hardest to copy and the part this repository has
already paid for.

### 0.1 The gap is NOT that "the industry lacks tools"

This project has claimed that in the past and it is false. CAD systems,
hydrostatic packages, RANS solvers and open-source naval-architecture
calculators all exist, many of them good and several of them free.

**The gap is that there is no broadly accessible, integrated, physics-aware
workflow in which a technically capable person can state a MISSION and receive a
safe, efficient, structurally realisable vessel together with a traceable
evidence trail.** Today that path is fragmented:

    CAD → hydrostatics → resistance → CFD → manual stability
        → manual structure → manual electrical → manual drawings

Every arrow in that chain is a hand-carried file, a re-keyed number and a lost
provenance. NavalAI collapses the chain into one governed pipeline, and the
governing is the product.

### 0.2 The evidence trail is the moat

Three mechanisms, all of them already in the tree and all of them gated, are
what would let a builder trust an output they did not compute themselves:

- **every quantity carries `{value, tier, sigma}`** — there are no bare numbers,
  and a tier is the name of the model that produced the number;
- **the ladder REFUSES what it cannot compute in-process** rather than
  substituting something cheaper (L3 raises `TierRequiresOperator` and names the
  operator route; a speed past the Michell envelope is badged `L1-INVALID`,
  which ranks BELOW L0 so it can never compare as a valid result);
- **a failing gate is RECORDED, never softened** — a missed bar goes into
  `data/gate-ledger.json` with a measured watermark, an owner and a review-by
  date (§3 step 5, and honesty rule 6).

An optimiser that reports a beautiful number is easy. An optimiser that reports
which model produced the number, how uncertain it is, and what it declined to
answer, is the thing a person can build a boat from.

### 0.3 Relationship to `docs/BUILD-PLAN.md` §1

That section states the same vision in SYSTEM-PLAN terms — the SELL → BUILD →
RUN loop, the evidence graph, the fleet-learning return path. **This sentence is
the platform-law statement and governs if the two ever diverge**; §1 is the plan
that realises it. A vision is what a product is allowed to be, which is this
file's question.

## 0.5 · The staircase to a working product (dated 2026-08-19, operator-directed)

The distinction that makes this schedulable: **the product loop does not
simulate.** Mission -> hull -> hydrostatics -> stability -> scantlings ->
panels -> report runs on the fast tiers (L0/L1 + rules, milliseconds to
seconds) and exists end-to-end today. CFD is a COMMISSIONING cost paid once
per method — the reliability rate of the unattended tier, and the one-time
calibration against tank data — not a per-design cost. After commissioning,
CFD spends only on novel keeps (active learning), by design.

| when (from 2026-08-19) | what works |
|---|---|
| **now** | a design pack a builder can be shown: standard-confirmed scantlings, stability with a real multihull criterion, cut files, the evidence trail — resistance carrying a DECLARED (uncalibrated) sigma |
| **+1 week** — the re-derived Gate 2M plan (the transient triplet was CANCELLED by the operator's math directive, 2026-08-19) | resistance calibrated the estimator's way: ONE estimator-settled medium KCS anchor (overnight, `post.settled_estimate`) + a coarse/medium Richardson delta declared as a band (basis approx) + CoKriging fusing dense L1 Michell with the 2U RANS rows + active selection, to the `WH_PER_NM_SIGMA_PRODUCT` = 0.10 target — see `docs/audit/STATUS.md` "the re-derived calibration plan" |
| **+2–3 weeks** — fortress001's queue (loading conditions, the 6D refold that is the Kit-Line's premise, tier E/F mass admission) | **Recreational v1**: mission -> buildable monohull or catamaran, plywood, with evidence — usable by a technically capable person |
| **later, separately** | the drone line — now QUANTIFIED (2026-08-19 regime study + independent evidence sweep, `docs/research/SMALL-CRAFT-REGIMES.md`; `docs/BUILD-PLAN.md` §11.8): minimum sensible drone is **2–3 m LWL** — three walls close below that: the fully-turbulent-Re × displacement-Fn window is EMPTY below L ≈ 2.6 m [THY, corroborated by ITTC's Re 5e6 stimulation floor and the 3 m Delft-372 validation anchor]; the environment dominates below ~1 m (windage 4–50× hull drag, SS3 orbital ≥ cruise speed — measured with the repo's own L0); and the cube-law payload floor bites at ~1.5–2.5 m [PROP]. Un-block list: a transitional friction line (±40%→±15% sigma), a windage/orbital environment estimator, and the rulebook gap (ISO/RCD scope starts at 2.5 m) — plus the mission layer. Deliberately descoped until v1 earns it |

**What the KCS anchor in that second row does and does not buy (added
2026-08-21, after the Gate 2M reframe).** It calibrates the SOLVER — free-surface
resolution, layer stack, y+, turbulence closure, grid convergence — at our own
operating point (KCS model scale is Fn 0.260 / Re 1.40e7; our 10 m at 5 kn is
Fn 0.260 / Re 2.26e7). It does NOT validate the physics our hulls have. KCS has
a bulbous bow and a round bilge; the SKUs are hard-chine sheet ply, and
`dR_chine` at Fn ~ 0.26 remains unvalidated against experiment. So "resistance
calibrated" in that row means *the numerics are anchored and the declared sigma
is earned*, not *the resistance of a plywood boat is validated*. The candidate
experiment for the second claim is Compton's 1986 USNA series
(`docs/audit/GATE2-PHYSICS-STACK.md`); the data is not yet held.

Two commissioning items gate the first two rows and are in flight as this is
written: the unattended-CFD reliability campaign on the shipped genome
(running), and the re-derived calibration lane — the single estimator-settled
medium KCS anchor plus the 2U solve rows the Mac is accumulating (the
weekend triplet stays cancelled; the estimator route replaces waiting-out
the drift bar). Status lives in `python -m navalai.gates` and
`docs/audit/STATUS.md`, never in this file.

## 1 · The platform ("one system")

Everything ships from one shared kernel — never per-product forks:

| Platform asset | Code | Truth mechanism |
|---|---|---|
| Hull grammar + typologies | `navalai/grammar.py`, `hull_ast.py` | L0 algebraic gate, <1 ms |
| Physics ladder L1→L3 | `hydrostatics/resistance/seakeeping/cfd` | benchmark anchors: Wigley (analytic 4LBT/9), Hulme, **DSYHS** (51 models, 742 points, MD5-verified) — and **KCS as SOLVER VERIFICATION ONLY**, demoted 2026-08-21. The rungs and what each does *not* prove: `docs/audit/GATE2-PHYSICS-STACK.md` |
| Surrogate spine | `surrogate.py`, `latent.py` | Forrester anchor, OOD refusal, frozen-benchmark regression gate |
| Generative core | `generative.py` (diffusion upgrade slot) | L0-feasible sampling, measured on the MODEL's raw draws — a feasibility figure measured on a rejection sampler with `grammar.check` inside its loop is true by construction and means nothing |
| Mission front end | `mission.py`, `translate.py` | held-out brief set, no geometry pathway |
| Rules tier R | `navalai/rules/` | clause provenance, fails closed, assessment-aid framing |
| Provenance | `db.py` (content-addressed) | append-only, solver-versioned |
| Agent shell | `agents.py` | typed messages, audit trail, Fitness=∞ gatekeeper |

**Platform law:** a product may *configure* the kernel (parameter subspaces,
rule profiles, mission presets); it may never bypass a gate or fork physics.

## 2 · Product lines (SKUs are configurations, not code)

### 2.0 Two markets, one engine, and the difference is the mission layer

The vision in §0 is served by two product families that share nearly the whole
kernel — geometry, physics ladder, rules tier, arrangement, manufacturing — and
differ mainly in what a mission *is* and what the optimiser is asked to minimise:

| Family | Mission is stated as | Asked for |
|---|---|---|
| **Recreational / DIY** | people, range, speed, comfort, cost, coastal conditions | a safe, buildable vessel a competent builder can cut and assemble |
| **Autonomous marine drone** | payload, endurance, sea state, sensor package | an autonomous vessel sized to the payload and the mission duration |

The drone family does not have ONE objective. A fishing drone wants minimum
Wh/km; a research/survey platform wants maximum survey-km per kWh; a
surveillance platform wants maximum time-on-station. Some of them care about
**wake and acoustic disturbance**, which are not energy at all — a survey
platform that scares the thing it is measuring has failed its mission at a
perfectly good Wh/km.

**Nothing about the drone family ships today, and the honest reason is now
the ASSESSMENT and OBJECTIVE layers, not the vocabulary.** (Corrected
2026-08-18, C-28: the previous version of this paragraph denied a payload
vocabulary that has since landed.) `mission.PayloadSpec` declares the
mission equipment as first-class quantities — payload mass with an optional
position, `sea_state`, `endurance_h`, payload power draw — and an uncrewed
mission zeroes the crew provision with a recorded note. But these are
DECLARED requirements, not assessed ones: nothing in the tree can assess
operability in a declared sea state, and `optimize.HullProblem`'s three
objectives are still `wh_per_nm`, build panel area and distance from the GM
band — no time-on-station, no survey-km/kWh, no wake or acoustic term.
Adding the assessments and objectives is a platform change that goes
through §3 like anything else — and per §0 it must not become a fork.

### 2.1 Declared lines

| Line | Mission preset | Grammar subspace | Rules profile |
|---|---|---|---|
| **Hull-Line v1** | any (research base) | full 16-param | ISO 12217/12215 subset |
| **Solar Liveaboard** | 6 t, Danube/Black Sea, cat C/D | sharp-chine, 9–14 m | + ES-TRIN — **wired** (C-23 closed 2026-08-19): consulted by `evaluate()` on declared inland waters; the standard's own scope test governs (a 9–14 m craft receives the OUT-OF-SCOPE/RCD receipt; a ≥20 m or ≥100 m³ hull takes the implemented bars and fails ES-COV's coverage honesty until more chapters land) |
| **Dayboat** | 1–3 t, cat D | pram/sharp-chine 4–7 m | cat D profile |
| **Full-Vessel Line v2** | + interior/exterior arrangement + unsinkability | + arrangement grammar | + ergonomics tier E + flotation tier F |
| **Kit-Line v3** | the self-certifiable envelope (LH < 12 m, cat C/D), delivered as a CNC kit | unchanged | unchanged, one policy profile, one delivery mode |
| **Drone-Line** (declared, not built) | payload + endurance + sea state + sensor package | unchanged | uncrewed profile — **the applicable rules are not yet identified**, and the recreational-craft profile is the wrong one |

Adding a product = one mission preset + one grammar subspace + one rules
profile. If it needs new physics or new grammar axes, that is a PLATFORM change
and goes through the lifecycle below. The Drone-Line needs both a new mission
vocabulary and new objectives, so it is a platform change, not a preset.

The genome is **sixteen** parameters (`grammar.N_PARAMS`, verified 2026-08-13).
This row read "15-param" until then; it is one number and it lives in
`grammar.PARAMS`, so ask that rather than this table.

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
