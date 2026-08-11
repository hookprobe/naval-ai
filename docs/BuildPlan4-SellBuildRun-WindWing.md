# BuildPlan 4 — SELL · BUILD · RUN, and the WindWing subsystem

> Research and decision document. PLM.md §3 lifecycle steps **2 (research)** and
> **3 (decision)**. No code is proposed as done; every gate below is a *proposed*
> gate with a bar, and nothing here may be quoted as a status.
> `python -m navalai.gates` remains the only status.
>
> Measured 2026-08-11 on `master` at `df70d00`, by four read-only audits with
> disjoint file ownership. Where a claim is transcribed rather than executed,
> it says so. Nothing was executed except the greps and file reads quoted.

---

## 0 · How to read this

This document answers three questions that arrived together:

1. Can NavalAI be organised as **SELL → BUILD → RUN**, and can that be made
   simple enough for a customer who is not a naval architect?
2. Can an airborne-wind traction subsystem (**WindWing**) be added, informed by
   Makani's open-source stack and the current marine-kite systems?
3. Can RUN be pushed down into HookProbeOS/HEQK to close an end-to-end loop?

The short answer to all three is yes, and the order matters more than the
content. **§2 is the load-bearing section**; if you read nothing else, read it.

A warning about this document's own genre. `docs/LESSONS.md` §"defect classes"
records that this repository's most expensive recurring failure is *prose
claiming capability the code lacks*, and the second is *a number declared
twice*. An architecture document is the highest-risk possible artifact for both.
So §1 states only what was measured, §9 lists what could not be verified, and
every forward-looking claim in §3–§7 is written as a **precondition list**
rather than as a design.

---

## 1 · What is true today (measured)

### 1.1 SELL

| Claim | State |
|---|---|
| A mission specification exists | **YES.** `mission.MissionSpec`, 9 fields, `mission.py:106-184`. |
| It is validated | **YES.** `clamp()` against `FIELD_RANGES`/`ENERGY_RANGES`, idempotent, rejects NaN/inf, records every clamp into `notes`. |
| It is a *frozen contract* with provenance | **NO.** Not `frozen=True`; both `parse_mission` and `translate.sanitize` mutate by `setattr` after construction. **No hash, no id, no timestamp, no version, no signature.** `db.hull_id` content-addresses *geometry*; nothing addresses the mission that asked for it. |
| The LLM has no code path to geometry | **YES, structurally** — geometry parameters are not fields of `MissionSpec`. The design-category ratchet (`translate.py:71-84`) lets an LLM only tighten a category, after a measured incident where an LLM returning "D" on an ocean brief relaxed the GM floor 0.60→0.35 silently. |
| …and it is tested | **WEAKLY.** `tests/test_phase5.py:80-84` asserts *name disjointness* between `MissionSpec` fields and `grammar.NAMES`. That is not a data-flow proof; it would pass if someone added a field a downstream caller decoded into a genome. The adversarial injection tests beside it are stronger and do fire. |
| Governance decides the admissible space | **YES, inside `evaluate`/`optimize`.** `navalai/policy/` compiles a `Constitution` to a `ParameterBox` + additive constraint rows, with a compile-time ratchet law that rejects a policy floor **equal** to the `limits.py` value ("POLICY IS NOT A RATCHET, IT IS A SECOND COPY", `compiler.py:766-775`). |
| …and the customer sees it | **NO.** `grep` for importers of `navalai.policy` returns `evaluate.py`, `optimize.py`, and tests. Not `ui/server.py`, not `translate.py`, not the demo. `legal.py` computes the RCD Article 20 delivery route — `own_use_kit` / `module_a_self_certified` / `notified_body_required`, with the five-year clause quoted verbatim — **and renders it to nobody.** |
| Feasibility negotiation | **ABSENT, not partial.** `translate.grade()` returns a PASS/FAIL list with clause provenance. Nothing ranks the failures, names the binding one, or proposes a relaxation. |
| Competing concepts A/B/C/D | **NO.** The nearest thing is the NSGA-II front at `GET /pareto`, which is unlabelled, uncosted, and — see §1.4 — answers the wrong mission. |
| Any notion of money | **NONE.** `grep -rniE "(price\|EUR\|€\|quote\|cost_per\|unit_cost\|hourly_rate\|labour_rate)"` over `*.py`: **zero hits meaning money.** Every "cost" in the package is CPU-seconds (`planner.py`, `fidelity.py`) or a physical quantity (`engineer.build_hours`, `ply_sheets`, `epoxy_kg`). `BomLine` has no price field and no currency. |
| An autonomous planner | **NOT WHAT THE NAME SUGGESTS.** `planner.py` plans *which rung of the validation ladder to run next*, scoring expected information gain in nats per CPU-second. It never sees a `MissionSpec`, a customer, or money, and it has **no production caller** — only `tests/test_stageG.py`. |

`BuildPlan3-MissionToOrder.md` agrees with all of this. Its §3 V3.1 (Mission
Intelligence), V3.3 (BOM closure), V3.5 (procurement), V3.6 (The Order) are
unbuilt and have no gate in `gates.py`; its §2.5 marks *"sheet count × sheet
price"* as `← NEW`. **The prose is honest here.** The ▪ marks on the V3.x
headings are an effort scale (person-weeks), not progress marks, and are easy
to misread as the latter.

### 1.2 BUILD

- **`pipeline.py` — the documented spine — has zero production callers.**
  777 lines, 11 typed stages, 7 terminals, forward-only transition graph,
  `Unmeasurable` guard, append-only `JsonlLog` with truncation detection,
  48 tests under Gate S. `Stage.` appears nowhere in `navalai/`, `scripts/` or
  `ui/` outside `pipeline.py` itself. `data/evolution/` contains only
  `gaps.jsonl`; there is no `archive.jsonl`. **Gate S is green on unused code.**
  `docs/END-TO-END-AUDIT.md` §1 already says this and specifies the wiring fix;
  I re-verified it independently.
- The engine that actually runs is `evaluate()` → `pareto_front()` →
  (`agents.run_plm`) → `engineer` → `unroll` → `export`. It has none of the
  guarantees the spine provides: no transition graph, so `engineered` can be
  emitted for a design with no successful hydrostatics; failures are free text;
  the audit trail is an in-memory list that dies with the process.
- **`evaluate()` is the single funnel** and adding a term there constrains
  NSGA-II automatically. `CONSTRAINT_NAMES` is one tuple of 8:
  `(freeboard, gm, bend_radius, trim, list, lcb, proportions, rules)`.
  `constraint_vector()` raises a real exception (not an `assert`, because
  `python -O` strips those) on any missing/extra/duplicate key.
- **Honesty rule 1 is true of four quantities, not of the object.**
  `Evaluation.badges` carries `(tier, sigma, basis)` for exactly
  `displacement`, `GM`, `resistance`, `wh_per_nm`. `gm_l_m`, `trim_deg`,
  `list_deg`, `ply_thickness_m`, `unaccounted_frac`, `hull_lwl_m` and the whole
  `g` vector are bare numbers. The badge guard itself is good: a non-finite
  value or sigma downgrades to `L{n}-INVALID`, which `tier_rank` ranks at −1,
  *below* L0, so it can never be promoted by comparison.
- **`evidence.EvidenceGraph` is well built and unpopulated.** Five node kinds,
  a typed `ALLOWED_SUPPORT` matrix that forbids a decision justifying a
  requirement, cycle rejection at insertion, weakest-link confidence over the
  ancestor set, `unsupported()`, JSON persistence. Its only callers are
  `tests/test_stageG.py` and `scripts/demo_apse.py`, where the graph is **six
  hand-typed nodes with hardcoded strings**. There is no function anywhere that
  takes an `Evaluation`, a `db.Provenance` id or a `Pipeline` genome and emits
  a graph.
- `extrapolate.py` has **no production consumer** — only a test and a demo.
  (`docs/END-TO-END-AUDIT.md`'s "no orphan modules" line is generous here.)

### 1.3 Physics — what a kite would have to attach to

This is the section that most changes what is buildable, and it is the one I
most expected to be wrong.

- **There is no 6-DOF model. There are no equations of motion anywhere in the
  repository, at any tier.** `dynamics.py` is component-lumped inertia
  arithmetic with parallel-axis terms, plus two *static scalar* load cases
  (`mooring`, `lifting`). The MuJoCo path is a **1-DOF hinge** used only to
  cross-check the inertia pipeline against an analytic pendulum period.
  A time-varying 3-D force vector has nothing to integrate against.
- **Seakeeping is HEAVE ONLY.** `_body_from_hull` adds one translation DOF;
  the tier reports zero-speed quantities. **There is no roll or pitch RAO.**
- **There is no centre of lateral resistance.** `dynamics.py:98-99` integrates
  the underwater side-profile *area* and never takes its centroid. The heeling
  lever a kite needs (attachment point → CLR) is not computable today.
- **Hydrostatics solves against a MASS, not a force.** `solve_to_displacement`
  bisects the waterline to a target kg. A kite's *vertical* force component has
  no home; it can only enter as an equivalent negative mass.
- **The only heeling-moment balance in the codebase is in kg·m, not N·m.**
  `rules/iso12217.py:139-147`: `sin φ = m_crew·b / (disp_kg·GM)`. `g` cancels.
  **Substituting a kite side force in newtons there is a silent 9.8× error.**
- **Yaw and leeway: nothing.** No rudder, no lateral plane, no course-keeping.
  A kite's side force cannot be balanced by anything the model knows about.
- **Aerodynamics, in full, repo-wide:** `dynamics.RHO_AIR = 1.225`,
  `dynamics.CD_LATERAL = 1.0`, and one bluff-body mooring force. Repo-wide grep
  for `kite|tether|traction|apparent|aero` returns **zero** hits in code. The
  word "rig" appears once, in a comment on a flat kg/m outfit lump
  (`energy.py:34`) — precisely the LESSONS §8 trap where the word sits in a
  comment *on* the defect.
- **`energy.py` is a steady-state daily-average balance at one speed.** No
  timestep, no state variable, no SOC trajectory, no dispatch. The whole
  balance is eight lines (`energy.py:230-237`). The single force→power
  conversion is line 230; that is where a traction term must enter and there is
  no second candidate.
- `limits.py` owns **design and rule** bars. **Model-validity envelopes
  deliberately live beside their models** (`FN_MICHELL_MAX` in `resistance.py`,
  `SCOPE_MIN_HULL_LENGTH_M` in `rules/iso12217.py`, `L2_MESHES` in
  `seakeeping.py`). Treating `limits.py` as the single home for *all* bars
  would separate a bar from the model that gives it meaning.
- `weights.MassItem` **is** clean and is the right attachment point for kite,
  tether, winch and launch-arm mass: `(id, mass_kg, x_m, y_m, z_m, sigma_kg,
  tier, source, basis, …)` with documented axes, quadrature sigmas, and
  `dynamics.inertia` consuming it. One constraint: `_TIERS = ("L1","E","F","R")`
  raises on anything else, so a WindWing item must claim an existing tier or the
  tier set must be extended (and provenance/UI follow).

### 1.4 RUN

**Confirmed absent.** Grep for `sensor|telemetry|gnss|gps|nmea|mqtt|realtime|
as-built|onboard|field data` across `*.py *.json *.md *.sh *.yml` returns zero
hits meaning any of those things in `navalai/`, `tests/`, `scripts/` or `ui/`.
Every hit is a homonym — `runtime` always means a governance override,
`real-time` means a transient solver mode, `on-board` is a quoted ES-TRIN
chapter title. `db.py`'s `result` table has `tier ∈ {L0,L1,L2,L3,R}`; **there is
no tier value that could mean "measured on a real boat."**

The concept exists only in plan prose (`BuildPlan3` §193-197, §526-537), and
`docs/HLD.md:91` correctly labels the twin/fleet layer NOT BUILT. **Prose and
code agree here** — the good case.

### 1.5 Defects found during this investigation

Six, all verified against the tree at `df70d00`. They are listed because three
of them sit directly under WindWing's foundations.

| # | Defect | Evidence | Class |
|---|---|---|---|
| **D1** | **The shell-area fix is half-applied.** `energy.shell_area_m2()` exists to kill a bare `× 1.6` and its docstring says *"engineer.assess and the L1 weight path must plank the same boat."* `engineer.py:139` uses it. **`evaluate.py:406` still reads `hull.wetted_surface(0.0) * 1.6`.** So structure mass → displacement → KG → GM → every stability verdict runs on the disowned factor while the BOM plants a different boat. The docstring's own measurement: true ratio 1.6879 on the reference hull; **1.251–6.702 over 200 grammar hulls**, mean 2.062, up to **76%** error, −15.4% average — *and the optimiser searches exactly that box*, so the error varies systematically with the shape being chosen. The trailing comment `# computed once, not twice` is about caching and makes the line read as fixed. | `evaluate.py:406` vs `energy.py:37-66`, `engineer.py:139` | 2 (number declared twice) |
| **D2** | **Air density is declared three times with three values.** `dynamics.RHO_AIR = 1.225`, `extrapolate.py:91 rho_air = 1.226`, `cfd/case.py:208 _RHO_AIR = 1.2`. `tests/test_limits_single_source.py` is a literal blocklist and does not cover it. This is the exact constant WindWing needs. | grep | 2 |
| **D3** | **`GET /pareto` answers the wrong mission.** It runs `pareto_front(_mission_default, …)` and re-evaluates with `_mission_default`, then caches globally — while `/eval` and `/generate` were fixed to use the customer's mission. The trade-off surface a customer is shown is not their boat. | `ui/server.py:93,106` | 4 (prose/surface standing in for a verdict) |
| **D4** | **`energy_report` fails open on a non-positive net.** `max(wh_nm, 1e-9)` at `energy.py:236-237` means a design whose resistance is fully overcome returns ranges of order 10¹² NM instead of erroring. Latent today; **it becomes live the moment a traction term exists.** | `energy.py:236-237` | 1 (unmeasurable scored as passing) |
| **D5** | **A comment describes the pre-change code.** `translate.py:240` builds a 20-line argument on `FIELD_RANGES["crew"]` being `(1, 12)`; `mission.py:76` now reads `(1, 250)`, changed 2026-08-07 with its own justification. | `translate.py:240` vs `mission.py:76` | 7 (register text wrong about the code) |
| **D6** | **`docs/HLD.md` is stale in three places**, two of them load-bearing: it states `navalai/arrangement.py` is absent (it is 1484 lines, Gate V2.1 registered) and that no `policy/` module exists (four files, Gate V3.0 registered). §11 describes four live branches and a 40-conflict stalled merge in the present tense; `git branch` shows one. | `docs/HLD.md:197-201, 208-227` | 5 (citing evidence that no longer exists) |
| **D7** | **`master` currently has a failing test.** `tests/test_gate_integrity.py::test_the_readme_gate_table_agrees_with_the_runner` fails on a clean tree. The drift is benign — test counts only (Gate 0 `8→14`, Gate 1b `2→8`, Gate V3.0 `47→48`): tests were added without regenerating the table. Fix is one command, `python -m navalai.gates --readme --write`. Recorded because the mechanism worked exactly as designed — documentation drift was caught by a test rather than by a reader — and because a red test left standing erodes the signal that makes the rest of this machinery worth having. | measured 2026-08-11 on `df70d00`, tree clean but for this document | — (the guard firing correctly) |

**Recommendation: D1 is filed as a gap before anything in this plan starts.**
It is not cosmetic — it moves displacement and GM, which are two of the four
badged quantities, and WindWing's mass items land in the same model.

---

## 2 · The thesis: the flywheel is closed on itself

This is the finding that reorganises the whole request.

`flywheel.harvest()` draws random grammar vectors via `sample_valid()`, runs
`evaluate()` on each, and trains the surrogate on the resulting **L1 rows**. The
frozen deployment benchmark it must not regress against is **also** generated by
`evaluate()`. The module is admirably honest about it (`flywheel.py:183-201`):
the benchmark probes are not the benchmark hulls, "their truth is our own L1,
never the tank data", and only proportion transfers.

So the learning loop is: **our physics teaches a surrogate to imitate our
physics, and we measure the imitation.** The gating around it is genuinely
strong — a monotone high-water ratchet, absolute floors that bind on bootstrap,
a suite fingerprint so a mark cannot be carried across two benchmarks, a missing
baseline treated as a refusal rather than a pass. All of that is real. None of
it can discover that the physics is wrong.

Count the predicted-vs-observed comparisons in the repository:

| # | Predicted | "Observed" | Against reality? |
|---|---|---|---|
| 1 | L1 Michell/ITTC-57 | recorded L3 RANS drag | no — sim vs sim |
| 2 | GP surrogate | the ladder's own L1 | no — sim vs sim |
| 3 | recomputed Michell Cw | `benchmarks/wigley.REFERENCE_CW` | **no — our own frozen output** (HLD's open gap E2: *"an anchor made of your own output measures nothing"*) |
| 4 | our CFD C_T | KRISO EFD 3.711e-3 | **yes** — and a human runs it by hand |

**One of four touches a physical measurement, it is a containership tank test
run manually, and its gate is RED.**

That is the argument for SELL·BUILD·RUN, and it is stronger than an
architecture preference:

> **RUN is the only available source of an observation that NavalAI did not
> generate itself.**

Not autonomy. Not a nicer autopilot. *Evidence.* Every hour a delivered vessel
operates is a measurement of the L1 model at a condition no tank test covers,
on the exact hull family the SKUs ship. Airseas is the cautionary case in
public: modelling and land tests projected **20%** fuel saving; the sea-trial
projection came back **16%**. That 4-point gap is precisely the quantity a
closed loop exists to find, and precisely the quantity a closed-on-itself
flywheel cannot.

Everything in §3–§7 is ordered by how directly it serves opening that loop.

---

## 3 · SELL — mission intelligence, the contract, and the quote

The ask was "simple, streamlined, easy to use." The answer is not a better
chat interface. It is **three artifacts and one identity chain** (§7). SELL owns
the first artifact.

### 3.1 The Mission Contract — freeze it and hash it

`MissionSpec` becomes `frozen=True`, gains `schema_version`, `created_utc`, and
`mission_id = sha256(canonical_json)` using the same canonicalisation `db.py`
already applies to parameter vectors. Mutation moves to
`replace()`-style returns, so `parse_mission` and `sanitize` compose instead of
`setattr`-ing.

Why this is first, and why it is not bureaucracy: **you cannot compute a
predicted-vs-observed delta without knowing which promise was made.** A delta
engine (§6.4) needs to join an observation to the mission that specified it. The
chain is broken at the SELL end today, and it is the cheapest break to fix.

The clamp `notes` stay, but stop being the provenance channel — `translate.py`
already records that deciding anything by regexing that sentence *"would make
the row FAIL OPEN the day the wording changes."* Clamps become structured
records on the contract.

### 3.2 Feasibility negotiation is nearly free, because `Evaluation.g` exists

This is the most valuable thing in this section and it needs almost no new
machinery.

`Evaluation.g` is already *the one* inequality vector, `g ≤ 0 == feasible`,
ordered, complete, finite-checked, and consumed directly by NSGA-II. A
negotiation engine is a thin layer over it:

- **The binding constraint** is `argmax(g_i)` over the infeasible set. That is
  the sentence "your 9 kn cruise is what is blocking you", computed, not
  reasoned about.
- **The trade** is the sensitivity of the objective to relaxing a *requirement*
  — a shadow price. For the mission fields that enter as targets
  (`cruise_speed_kn`, `displacement_target_kg`, `lwl_hint_m`,
  `energy.battery_kwh`), a finite-difference re-solve at ±Δ gives
  ∂(objective)/∂(requirement) directly. At NSGA-II budgets already in use
  (pop 24 / gens 10 ≈ 1.2 s) a 4-field sensitivity sweep is seconds, not hours.
- **The output** is one ranked sentence per binding constraint with a number
  attached: *"cruise 9 kn → 7.5 kn recovers feasibility and saves €X"*, or
  *"cruise 9 kn is achievable if displacement target rises 640 kg."*

Two rules this must inherit, both already house law:

1. **Never relax a bar to make it pass** (honesty rule 6). The negotiator
   proposes changing the *mission*, never the *limit*. `policy/compiler.py`'s
   ratchet already encodes the direction of legitimate movement.
2. **A refusal must name what it refused.** `translate.grade()` already
   separates "broken checker" from "failed design" (gap E15). The negotiator
   must preserve that distinction or it will report a crashed constraint as an
   infeasible customer.

### 3.3 The quote — money must carry a tier, like every other quantity

There is no money in the codebase, so this is greenfield and can be built right
the first time. The design falls straight out of honesty rule 1 and out of the
shape `policy/base.PolicyValue` already uses (which requires `source` to be at
least 20 characters — a small, effective anti-handwave device):

```
PriceValue(value, currency, tier, source, quoted_on, sigma, note)
  tier ∈ ('quoted',    # a named supplier quote, with a date
          'listed',    # a public price list, with a URL and a date
          'estimated', # parametric, from build_hours / area / mass
          )
```

Rules, each with a test that feeds it the input it must reject:

- **A price with no tier is refused**, exactly as an unmeasurable mesh metric is
  fatal rather than defaulted to 0 (LESSONS §1). There is no default currency
  and no default price.
- **A quote has an expiry.** A `quoted` price older than its validity window
  degrades to `estimated` with the sigma that implies — a `quoted` price that
  has silently expired is the money version of the layer table that printed the
  requested spec as achieved.
- **Total cost carries a sigma**, aggregated in quadrature, and the quote to the
  customer states it. `engineer.EngineerReport` already produces the physical
  quantities (`ply_sheets`, `epoxy_kg`, `build_hours`, `nest_utilisation`); the
  missing half is exactly the `← NEW` line in BuildPlan 3 §2.5.
- **Cost closure** is a first-class metric: what fraction of the BOM's mass and
  line count is priced at `quoted`/`listed` vs `estimated`. A quote that is 30%
  closed is a different product from one that is 95% closed, and the customer
  is told which they have.

### 3.4 Concepts A/B/C/D

These are the Pareto front, labelled and costed. `pareto_front` exists and is
gated (Gate 1b). Three things are needed: **fix D3 so it answers the customer's
mission**, attach `PriceValue` totals, and name the concepts by what
distinguishes them rather than by index. The explanatory sentence the customer
reads ("Concept C is the best engineering solution; B gives more peak traction
but larger roll moments…") is an LLM *reading* the computed front — which is
exactly what honesty rule 3 permits: translate and explain, never compute.

### 3.5 Surface the governance answer

`policy/legal.py` already computes the delivery route with articles and the
five-year clause verbatim, and already records where BuildPlan 3 §0 is wrong
about category D rather than silently fixing it. `AiActConsequence.high_risk`
is deliberately always `None` because limb (a) is a legal judgement the project
refuses to make — that abstention is a feature and must survive to the customer
surface.

**Rendering this is zero new physics and it is the single most differentiating
thing SELL could show.** No competitor tells a customer, at concept stage,
"this configuration requires a notified body, here is the article."

---

## 4 · BUILD — what changes

BUILD is the most complete of the three engines. Three changes, in order:

1. **Wire `agents.py` onto `pipeline.py`.** `docs/END-TO-END-AUDIT.md` §1
   already specifies the mapping (`candidate → NEW → GENERATING`, etc.) and
   notes both halves exist and are tested. This is a wiring job, not a rewrite,
   and it converts Gate S from a gate on unused code into a gate on the product.
   The property it buys: `engineered` can no longer be emitted for a design
   whose hydrostatics never succeeded.
2. **Populate `EvidenceGraph` from `evaluate()` + `db.Provenance`.** That
   function *is* the Design Evidence Package. The graph's guarantees — cycle
   rejection, weakest-link confidence, `unsupported()` decisions — become real
   the moment something builds one from computed results instead of hand-typed
   strings. Confidence over the ancestor set is the number to put on the front
   of the package.
3. **Extend badges, or stop claiming rule 1.** Four badged quantities against a
   rule that says "every quantity". Either every field on `Evaluation` carries
   `{value, tier, sigma}` or the rule is restated to name the four. The former
   is better; the latter is honest. The current state is neither.

---

## 5 · WindWing — the airborne-wind subsystem

### 5.1 What the research actually says

**Makani is an unusually good resource, and X issued a worldwide patent
non-assertion pledge alongside the open-sourcing.** The FTO caution in the
brief is therefore much smaller than feared *for Makani specifically*: anyone
may use the patents, designs, software and research without fear of reprisal.
It does **not** extend to Airseas, SkySails or Beyond the Sea, who are live,
commercial and patenting — a launch/recovery mechanism review is still owed
before commercialising hardware.

What is in the repository (`github.com/google/makani`, archived read-only
Nov 2022, Bazel, Debian Stretch/Docker): flight simulator; `control/` with
separate hover, transition-in, crosswind and off-tether controllers;
`analysis/control/crosswind.py` generating the crosswind inner-loop gains;
`avionics/` firmware for winch, ground station, motors, servos, GPS; `config/`
producing JSON and compile-time C structs; `database/` aerodynamic tables;
`vis/` OpenGL visualiser. Avionics firmware is *"potentially not in a buildable
state"* after third-party code removal.

**What to take:** the *architecture* (separate controllers per flight phase),
the aero-database and configuration patterns, and above all the **failure
data**. The DOE review names two contributors to underperformance: worse than
expected aerodynamic performance of the **wing/tether system**, and inability
to fly circles as small as desired. Makani's own stated recommendation is to
iteratively verify aero performance gains against flight data and not
overestimate projected power — which is this repository's culture already.

**What not to take:** the M600 architecture. Onboard generation, 8 turbines,
~26–28 m span, 600 kW, conductive tether — that is a different problem. A boat
wants *traction*, and converting wind → generator → battery → inverter → motor →
propeller to deliver a force that the tether was already delivering mechanically
is a chain of efficiencies paid for nothing.

**The governing physics is Loyd (1980)**, and it is algebraic — the right shape
for this repo's L0 tier:

```
crosswind power     P ∝ ρ A v_w³ · C_L (C_L/C_D)²      [P_max = (2/27) ρ A v_w³ C_L(C_L/C_D)²]
crosswind traction  F ∝ ρ A v_w² · C_L (C_L/C_D)²
optimal reel-out speed = v_w / 3
static (parked)     F = ½ ρ A v_w² C_R
```

**A cross-check that passes.** The crosswind-over-static traction ratio is
≈ (4/9)(C_L/C_D)²·(C_L/C_R). At a soft-kite L/D ≈ 5 this gives roughly 10×,
and Airseas reports up to *"10× the traction of static flight"* from dynamic
figure-eight flying. Independent theory and a commercial measurement agree
within the precision either is quoted to. That is worth stating because it is
the only quantitative cross-check available before any code is written.

**Marine reality, from operators rather than from models:**

| Source | Datum |
|---|---|
| Silent 60 catamaran | **9 m² kite, engines off, 4–5 knots** |
| Beyond the Sea | ~**100 kg/m²** traction in test (≈1 kN/m²); 100 m² automated SeaKite on the fishing vessel *Cap Kersaint*, operational 2026; 400 m² in development |
| Airseas Seawing | 1000 m², flies to ~300 m, figure-eight at >100 km/h, 100% automated; **projected 20% from modelling, 16% from trials** |
| LibertyKite | 40 m² sized for vessels over 12 m with high displacement |
| TU Delft (Eijkelhof, Rossi, Schmehl, *Wind Energ. Sci.* 11, 1287, 2026) | 150 m² MegAWES at 15 m/s: **circular** 1.85 MW at 2.94 MW/km² (best power, smallest area); **figure-eight down-loop** better power quality, peak-to-average **3.85** |
| Bristol / Kitemill KM1 | combining flight control with winch control ↑ simulated power **47%** vs an existing reel-out strategy |
| Fagiano et al., *Annual Rev. Control* / arXiv 2401.05950 | 360 m² kite on a moored spar: flight pattern is **insensitive** to platform motion, but **tether-force oscillation frequency can approach platform resonance**, causing fatigue. The proposed fix acts on the **path planner**. |

### 5.2 The binding constraint is structure and stability, not aerodynamics

Take the 14 m / 6.8 t catamaran from the brief. At Beyond the Sea's measured
~1 kN/m², a 25 m² kite develops on the order of **25 kN ≈ 2.5 t — about 37% of
displacement** — as a dynamic, oscillating vector applied above deck near the
bow. The Silent 60 datum points the same way from the other side: 9 m² moved a
far heavier boat at 4–5 kn, so the useful sizes for a 6.8 t cat are in the
**10–25 m²** band, not the 40–60 m² the brief sketched.

Two consequences, and they invert the instinctive build order:

1. **The first WindWing gate is a LOAD gate, not a power gate.** "Does the
   vessel survive the kite" is answerable before "how much does the kite pull",
   it is the question that kills bad configurations early (the Fitness=∞ fast
   reject pattern this repo already uses), and it is the one a customer is
   actually buying an answer to.
2. **Peak-to-average tether force is the structural sizing driver.** That makes
   NavalAI's objective *different from every AWE company's*. They maximise
   cycle-averaged power; a boat wants mean thrust subject to a peak-load
   ceiling. TU Delft's result — circular wins power, figure-eight down-loop wins
   peak-to-average — therefore may resolve the **opposite way for a boat than
   for a power plant.** That is a real and defensible divergence, and it falls
   straight out of having a different objective, not out of better physics.

### 5.3 The defensible innovation — and its precondition

> **Choose the kite trajectory against the vessel's dynamic response, not
> against power.**

No airborne-wind company has the vessel's RAOs. No naval-architecture tool has
the kite. NavalAI is the only place both could live. The offshore-platform
result gives the mechanism: tether-force oscillation can collide with hull
resonance, and the fix belongs in the path planner. For a boat the constrained
problem is:

```
maximise   mean forward thrust
subject to peak tether tension  ≤ structural limit
           heel under kite load ≤ category limit (limits.CATEGORY_TABLE)
           excitation period    away from roll and pitch natural periods
           trim / list          within limits.TRIM_LIMIT_DEG / LIST_LIMIT_DEG
```

**This cannot be evaluated today and it is important to say so plainly.** The
third constraint needs roll and pitch RAOs; `seakeeping.py` is heave-only. The
second needs a heeling lever, which needs a centre of lateral resistance that
does not exist. Writing the trajectory optimiser before those exist would
produce a confident number with nothing behind it — the same failure as a GCI
triplet converging precisely onto a phase of the pressure oscillation.

**Precondition list, stated as work items rather than as assumptions:**

| | Precondition | Status | Why WindWing needs it |
|---|---|---|---|
| P1 | Centre of lateral resistance | absent | the heeling lever (attachment → CLR) |
| P2 | Roll + pitch RAOs | absent (heave only) | resonance avoidance; the whole §5.3 idea |
| P3 | A force-balance stability path | absent (`solve_to_displacement` takes a mass) | kite vertical force has no home |
| P4 | Environmental state on the mission | absent (`MissionSpec` has no wind, no sea state) | there is nothing to size a kite against |
| P5 | Rigid-body EOM | absent, at every tier | anything time-domain. **Its own lifecycle item, its own gate** — this is not "adding a subsystem" |
| P6 | Yaw/leeway balance | absent | side force cannot be balanced by anything the model knows |

### 5.4 The proposed tier ladder

Mirrors the existing L0→L3 discipline, with its own letter so a WindWing tier
can never be mistaken for a hull tier (the precedent is `flywheel`'s `"S1"`,
deliberately absent from `TIER_ORDER` so `tier_rank` returns −1):

| Tier | What | Cost | Depends on |
|---|---|---|---|
| **W0** | Loyd algebraic: traction and power from `(A, C_L, C_D, v_w, elevation)`; static and crosswind bounds | <1 ms | nothing |
| **W1** | Quasi-steady: + tether drag and sag, apparent wind from boat speed, cosine losses, elevation angle. **Tether drag is where Makani's measured shortfall lived — it is not a correction, it is the dominant loss** | ~ms | P4 |
| **W2** | Dynamic flight over a parameterised trajectory; peak/mean tension; excitation spectrum | ~s | P1, P2, P3, P5 |
| **W3** | CFD of the wing section | hrs | deferred — the existing OpenFOAM machinery is a free-surface marine solver, not an aero solver |

W0 and W1 are buildable now and are enough for the LOAD gate and for concept
sizing. **W2 is blocked behind P1/P2/P3/P5 and must be stated as blocked**, in
`data/gate-ledger.json`, rather than approximated.

### 5.5 The regulatory consequence nobody expects

`navalai/rules/iso12217.py` implements **ISO 12217-1 — *motor* craft ≥ 6 m.**
Its docstring is explicit that the scope of a standard is part of the standard
(gap G8), and its `R-SCP` guard *refuses* rather than defaulting to pass, after
a measured incident where the −1 category floors were applied to a 4.5 m hull
that −3 governs.

**ISO 12217-2 governs sailing boats** — craft propelled primarily by sail, 6 to
24 m — and applies a different stability assessment including wind-heeling
criteria. Fitting a traction kite raises a real question about which part
governs, and the repo holds and implements neither −2 nor −3.

So: **WindWing must extend `R-SCP`, not bypass it.** If a kite moves the craft
out of −1's scope, the rules tier must refuse to produce −1 findings for it,
exactly as it refuses for a 4.5 m hull. Producing a −1 verdict for a kite-rigged
craft would be the `gate2m.py`-printing-KCS-EFD-for-a-Wigley-hull defect, in the
tier whose whole job is provenance. Acquiring −2 is a **purchase**, and belongs
in `refdata.PURCHASE_QUEUE` beside the standards already queued, recorded via
`refdata.absent()` naming exactly what it unblocks.

### 5.6 Control architecture, and where the AI is not allowed

The brief's three-level split is right and matches the literature. Stated in
this project's vocabulary:

```
NavalAI (slow, cognitive)   deploy? size? pattern? — proposes, never actuates
        ↓
Governance / safety envelope (deterministic)  — refuses out-of-envelope requests
        ↓
Trajectory + winch controller (MPC/LQR, 10–50 Hz)
        ↓
Flight controller (PID inner loop, 100–500 Hz)   ← Makani's crosswind.py is the reference
        ↓
Emergency release (hardware, below software)
```

Honesty rule 3 already says LLMs translate and explain and have no code path to
geometry. **The RUN analogue is: no LLM has a code path to an actuator.** That
should be written as a rule and tested the way the geometry seam is — and,
learning from §1.1, tested as a *data-flow* property rather than as name
disjointness.

On the brief's one-wire/two-wire question: a single load-bearing tether with an
onboard flight computer and a free-spinning swivel is the architecture to
investigate first, because it makes the rotating interface trivial. SkySails'
published approach — steering lines to a control pod containing the autopilot
and sensors, driven by a tooth-belt actuator — is the proven marine variant, and
Airseas' pod carries three actuators. **Unlimited 360° rotation is not a
requirement**; it is a consequence of picking a circular pattern, and §5.2 says
the pattern should be an optimiser output anyway. Treat continuous rotation as a
*cost* (twist management) that the trajectory optimiser pays, not as a goal.

### 5.7 Governance: "aft wind only" is policy, not physics

The brief's instinct to hard-code downwind-only operation is right as a *policy*
and wrong as *physics* — and this repo already has the exact mechanism for that
distinction. `policy/dna.py` requires every `DesignDNA` field to carry
`basis='policy'` and its docstring quotes BuildPlan 3 §2.2 that these are
preference constraints, not safety constraints. A WindWing operating envelope
(true-wind sector, wind speed band, sea-state ceiling, altitude cap, tether
tension ceiling, harbour prohibition) belongs there, as policy, with the physics
left able to evaluate the full 0–360° envelope so the policy can be widened
later against evidence rather than rewritten against belief.

Design bars (max tether tension, max heel under kite load) go in `limits.py`.
The kite model's own validity envelope (the apparent-wind range its polar was
fitted over) goes **beside the model**, per the `FN_MICHELL_MAX` precedent.

---

## 6 · RUN — the operating layer

### 6.1 First, an honest correction about the regulatory frame

The brief leans on the IMO MASS Code. **It does not apply to this product.**
The Code was adopted by resolution MSC.595(111) in May 2026 and took effect
1 July 2026 as a **non-mandatory** instrument, applying to **cargo ships under
SOLAS Chapter I — generally over 500 GT on international voyages** — with a
mandatory version expected to be adopted by 2030 for force in 2032.

A 14 m recreational catamaran is governed by **Directive 2013/53/EU** (2.5–24 m
recreational craft), which `policy/legal.py` already implements at Article 20,
and by the ISO 12215/12217 series the rules tier already assesses against.

This matters because of defect class 4. Claiming MASS-Code alignment for a
craft outside its scope is prose standing in for a verdict, and this repo
already had that exact failure — `gate2m.py` printing KCS's EFD figure under a
header for a Wigley hull. **Use the MASS Code as a voluntary architecture
template** — its goal-based structure (operational modes, operating limitations,
risk assessment, connectivity, cybersecurity, fallback on limit exceedance) is
genuinely good and maps almost exactly onto the governance engine — and say
"voluntarily aligned with", never "compliant with".

### 6.2 Sensors: honesty rule 1, extended with time

Every reading carries `{value, tier, sigma, source, age}`. **Age is the new
term and it is the important one.** A stale sensor reading treated as current
is the runtime form of the repo's most expensive defect class — an unmeasurable
value scored as a passing one. A reading past its validity horizon must be
*refused*, not extrapolated, exactly as `${_MQ_SKEW:-0}` should have been fatal.

The tiering the brief proposes is right, and it has a direct precedent: a
surrogate answer at tier `S1` can never satisfy a ladder-tier requirement
because `tier_rank("S1")` is −1. Apply the same trick — **a forecast can never
satisfy a requirement for a measurement.**

```
T0 hard safety   bilge, fire, battery protection, motor temp, tether tension
T1 navigation    GNSS(+Galileo HAS), IMU, compass, log, depth
T2 perception    radar, AIS, camera
T3 environment   wind, pressure, temperature, irradiance, wave
T4 external      Copernicus Marine / ERA5, charts, traffic   ← ADVISORY ONLY
```

**Copernicus is strategic, never in the control loop.** Local sensors own
seconds-to-minutes; CMEMS/ERA5 own hours-to-days (ERA5 is hourly from 1940,
via the `cdsapi` client; Copernicus Marine has a Python toolbox/CLI). The
vessel must be fully operational with the internet off — cloud is for forecast,
fleet learning and supervision, not survival.

### 6.3 Autonomy as a degradable state, not a boolean

A0 manual → A5 mission autonomy, with the state a *function* of sensor
confidence, weather, traffic, battery, comms and navigation confidence, and
degradation automatic. This is the same idea as `tier_rank` and it should reuse
the vocabulary: an autonomy level is a claim about evidence quality, and a claim
that outruns its evidence must be refused rather than rounded up.

### 6.4 The delta engine — the smallest change that opens the flywheel

Everything above is architecture. **This is the part that pays for RUN.**

The minimum viable version is small:

1. `db.py` gains an **observation** row: `(vessel_id, mission_id, quantity,
   predicted, observed, condition, sigma_obs, source, t)`. Note it needs a
   *tier* value that means "measured on a real boat" — today there is none.
2. A generic `delta(quantity, predicted, observed, condition) → residual`,
   recorded against the design, never silently folded into a total. The
   precedent is `extrapolate.ShipPrediction`, written specifically so that
   collapsing components does not make a disagreement undiagnosable.
3. `flywheel` gains a second data source that is not `evaluate()`.

With that, the loop in §2 opens: a residual on `wh_per_nm` at a measured
condition is the first thing in this system's history that can tell it its
physics is wrong. And it directly serves the KCS problem — a fleet of real hulls
in the SKU family is a *second benchmark anchor*, which `ALIGNMENT.md` and
`PLM.md` both record as owed, and which KCS by construction can never be.

### 6.5 HookProbeOS / HEQK — stated as an assumption, because I have not seen it

**I have not read that repository and cannot audit it.** What follows is
therefore a requirement list, not a finding.

The capability-security posture is a genuine differentiator for one specific
reason: a weather-data parser and a camera pipeline are *the* two components in
a maritime stack most likely to be handling untrusted input, and neither has any
business being able to reach motor-control memory. If HEQK provides capability
isolation, secure IPC, device isolation, cryptographic identity, secure boot and
deterministic scheduling, then the partition set is:

```
SAFETY · NAV · SENSOR · ENERGY · WINDWING · MOTOR · COMMS · TELEMETRY
```

with SAFETY below everything and the emergency tether release **in hardware,
below software altogether**.

To take this further I need: the HEQK repository, its capability model, its
scheduling guarantees, and whether it currently runs on the intended target.
Until then this section is a specification, not a plan.

---

## 7 · The simple answer: three artifacts, one identity chain

The request was "simple, streamlined and easy to use". Concretely:

```
SELL  →  MISSION CONTRACT        one page, frozen, hashed, human-readable
                                 what you asked for + what governs it + what it costs (with tiers)
BUILD →  DESIGN EVIDENCE PACKAGE EvidenceGraph, populated from computed results
                                 what we built + why + how confident + what is unsupported
RUN   →  OPERATING ENVELOPE      what it may do, when it must stop, and
         + DELTA REPORT          how the real boat differs from the designed one
```

threaded by one identity chain:

```
mission_id  ──►  design_id  ──►  vessel_id  ──►  observation rows
(sha256 of      (db.hull_id,     (hull serial)   (measured, tier ≠ L*)
 the contract)   EXISTS TODAY)
```

**Only the middle link exists.** Fixing the two ends is cheap, mechanical, and
is the precondition for §2, §3.1, §6.4 and every claim about fleet learning.
That is the whole "simplify" answer: not fewer features — *one artifact per
phase and one identifier that survives all three*.

---

## 8 · Competitive position, stated honestly

The incumbents — NAPA (class-grade, shipyards), Bentley Maxsurf, Orca3D on
Rhino, CAESES, ShipConstructor, Paramarine, DELFTship — are geometry-and-
analysis tools for expert users. None of them takes a customer sentence, none
produces a quote, none operates the vessel afterwards, and none carries
provenance and uncertainty on every quantity as a structural property.

### 8.1 Compute Maritime / NeuralShipper — the closest competitor, and what it proves

`computemaritime.com` is a London deep-tech company positioned as *"Generative
AI for Maritime Design"*, and it is the nearest thing to a direct competitor
this project has. It should be studied rather than dismissed.

**What they have that we do not:**

| | Them | Us |
|---|---|---|
| Generative model | **ShipHullGAN** — deep convolutional GAN trained on **52,591 physically validated real designs** (containers, tankers, bulkers, tugs, crew supply). Shapes converted to a fixed-dimension **shape-signature tensor** built from **geometric moments**, which is what lets physics-informed terms into the representation. Published in *CMAME* 411 (2023) | `generative.py`: a GMM fitted to grammar-sampled synthetic vectors, diffusion as a planned drop-in |
| Geometry output | NURBS/CAD directly; they claim to be *"the first model to directly output a CAD model"*, arguing that *"even slight surface irregularities can significantly affect outcomes"* | analytic kernel + developable-panel unroll → DXF; STEP/IGES via CadQuery |
| CFD | Simcenter **STAR-CCM+**, integrated with Siemens Digital Industries Software | OpenFOAM, Gate 2M RED |
| Backing | NVIDIA AI-startup accelerator; £700k UK Clean Maritime Demonstration Competition; UK SHORE / Innovate UK; partners Siemens, HP, Rapid Fusion, BYD Naval Architects, University of Southampton | one repository and two machines |
| Delivered | **GenDSOM**: a 32.5 m twin-hull crew transfer vessel for offshore wind, 24 technicians + 4 crew; a hydrofoil component printed on a robotic large-format AM system | the SKUs are unbuilt |

That is a real lead on generative modelling, data, surface quality and
industrial partnership, and **the 52,591-design corpus is a moat this project
cannot close by scraping.** Say so plainly.

**What their own material shows is missing, and it is the whole thesis of §2.**

Their About page states the scope: *"concept development and detailed design"*,
justified by *"80% of a product's environmental impact is determined at the
design stage"*, with a value proposition of *"10% cheaper, 20% faster, and 50%
more efficient."* There is **no mention of sales or quoting, no digital twin, no
fleet data or telemetry, no in-service performance, no post-deployment
optimisation.** By their own description they are a **BUILD-phase tool** — the
same category as NAPA and Maxsurf, built AI-native. SELL and RUN are
uncontested.

And then the headline number. GenDSOM is reported as saving *"101,671 litres of
fuel and 258.7 tonnes of CO2 per vessel every year"*, an *"11.1% reduction in
annual fuel consumption and an 8.9% reduction in CO2 emissions"*, with a 106 kWh
energy surplus against a 34 kWh deficit for the baseline. What was physically
manufactured in that project was **a hydrofoil component**, not the vessel.

**So 101,671 litres per year is a simulation output, quoted to six significant
figures, for a boat that has not been operated.** Compare Airseas: 20% from
modelling and land tests, **16%** from sea trials. This project's own history
has the same shape — one Gate 2M measurement circulated as five different
figures until only one was reproducible from any run directory (gap J1).

That is not a criticism of their engineering, which is clearly strong. It is the
observation that **the entire field, incumbents and AI-native challengers alike,
reports design-stage predictions as achievements, and nobody is closing the loop
with operational evidence.** §2 says NavalAI's flywheel is closed on itself; the
competitive finding is that *everyone's is*. The difference available to this
project is that it already has the machinery to know it — gates, a ledger,
red-by-record, tier badges, refusals — and the others do not appear to.

### 8.2 What to take from them, in our own way

1. **Geometric moments as a shape representation.** Their shape-signature tensor
   is the strongest technical idea in their published work: moments are
   analytic, cheap, dimension-fixed, and physics-informed — which is exactly the
   L0 tier's cost class. Stage E measured that this project's 8-D latent costs
   **2–3× surrogate accuracy** against the full 15-parameter vector; a
   moment-based descriptor is a credible third option and can be evaluated
   against both on the existing benchmark. **Research item, not a decision.**
2. **Our generative model has the §2 defect too, and it is worse than the
   flywheel's.** `generative.py` fits a GMM to grammar-feasible vectors this
   system generated. PLM §1 already records the related trap — the "100% raw
   feasibility" claim was measured on a rejection sampler with `grammar.check`
   *inside its loop*, so it was true by construction (gap D11), and Gate 4F is
   RED on the honest number. Training on real hulls is how they escaped that.
   A public hull corpus is worth acquiring even at a fraction of 52,591.
3. **Surface quality is a real requirement, not vanity.** Their argument that
   irregular surfaces corrupt downstream analysis is correct, and this project
   has already been bitten by the geometric version of it (a mirrored-IGES mesh
   that died on the first timestep at 73 wrongly-oriented faces). Worth a
   fairness/continuity gate on emitted geometry.
4. **Their positioning line is a gift, and it can be beaten honestly:** 80% of
   impact is determined at design — **and 100% of it is measured in operation.**
   That is the SELL sentence, and RUN is what earns the right to say it.

### 8.3 The strategic conclusion

**Do not compete with NeuralShipper on generative hull modelling.** They have
52,591 designs, Siemens, NVIDIA and a government-funded consortium; that fight
is lost before it starts and winning it would not differentiate the product
anyway.

Compete where the segment and the lifecycle differ:

- **Segment.** They design 32.5 m commercial steel/composite vessels for
  offshore-wind operators, under class and SOLAS. This project designs 4–24 m
  plywood-native recreational craft under RCD 2013/53/EU and ISO 12217/12215,
  sold to an owner and cut on a CNC kit-cutter. Their AM-printed hydrofoil and
  our nested plywood DXF are at opposite ends of the cost spectrum, and
  developable-panel manufacturability is a constraint their generative model has
  no reason to carry.
- **Lifecycle.** SELL and RUN, which they explicitly do not do.
- **Evidence.** The honesty machinery, and eventually a fleet of instrumented
  hulls — which is the one asset a competitor cannot buy, and the one that
  answers the second-benchmark-anchor debt `ALIGNMENT.md` has been carrying.

**Where NavalAI is genuinely ahead:** the honesty machinery. Typed gate statuses
with a committed ledger; red-by-record so a miss cannot be edited away in prose;
tier badges that cannot be promoted by comparison; an OOD-refusing surrogate; a
ratchet that rejects a policy floor merely *equal* to a limit; a rules tier that
refuses out-of-scope verdicts rather than producing them. I have not seen that
combination in a commercial naval-architecture tool, and it is much harder to
copy than physics because it is a culture encoded as tests.

**Where NavalAI is behind, and it must be said:** the physics is weaker than the
incumbents today. Gate 2M is RED. Seakeeping is heave-only. There is no 6-DOF
model. The resistance model is Michell + ITTC-57 + Holtrop, all textbook, and
valid only to Fn 0.45. The second benchmark anchor the SKUs actually need is
owed. A NAPA user would be right to point at all of it.

**So the moat is not "better simulation."** It is (a) the honesty machinery,
(b) mission→quote→build→operate as one governed chain, and (c) if RUN lands, a
fleet of instrumented hulls in the SKU family — which is a benchmark anchor no
competitor can buy, and which is the one thing that would eventually make (a)'s
weakness go away.

---

## 9 · Ordered plan, with proposed gates

Each phase names its lifecycle role. Every gate below is **proposed**; per
PLM §3 step 4 it ships as code + test in one change, with the test comment
naming the motivating incident, and per LESSONS §3 the test feeds the guard the
verbatim input it must reject.

### Phase 0 — repair, then thread (days; no new physics)

| Item | Gate | Bar |
|---|---|---|
| D1 shell-area fix applied to the L1 path | extend **Gate L** | one shell-area expression in `navalai/`; a test asserting `evaluate` and `engineer.assess` plank the same boat to within 0 |
| D2 one air density | extend **Gate L** | one `RHO_AIR`; add it to `_BANNED` so the fence actually holds |
| D3 `/pareto` answers the caller's mission | extend **Gate F** | a request with a non-default mission returns a front whose members differ from the default's |
| D5, D6 stale comment and stale HLD | — | correction only |
| Mission contract frozen + hashed | **Gate M1** *(new)* | `MissionSpec` is frozen; two textually different briefs with identical semantics hash identically; any mutation attempt raises |

### Phase 1 — SELL becomes a product (weeks)

| Item | Gate | Bar |
|---|---|---|
| `PriceValue` with tier, source, expiry | **Gate Q1** *(new)* | a price with no tier is REFUSED; an expired `quoted` price degrades to `estimated` and its sigma grows; a test feeds it both |
| BOM pricing + cost closure metric | **Gate Q2** *(new)* | every `BomLine` priced or explicitly `absent()`; closure fraction reported; a 0%-closed quote cannot be presented as a quote |
| Feasibility negotiation over `Evaluation.g` | **Gate N1** *(new)* | on a deliberately infeasible mission, the named binding constraint is the true argmax of `g`; the proposal changes the *mission*, never a *limit* |
| Concepts A–D, labelled and costed | extend **Gate F** | ≥3 distinct concepts with totals and sigmas |
| Delivery route rendered to the customer | **Gate V3.6** (already planned) | a notified-body configuration cannot be presented as self-certifiable |

### Phase 2 — BUILD earns its guarantees

Wire `agents.py` onto `pipeline.py` (Gate S becomes a gate on the product);
populate `EvidenceGraph` from `evaluate()`; resolve the badge coverage question.

### Phase 3 — environmental state (precondition for everything wind)

`MissionSpec` gains wind and sea state. **This blocks all of WindWing** and
nothing in §5 can start before it.

### Phase 4 — WindWing W0/W1 and the LOAD gate

| Item | Gate | Bar |
|---|---|---|
| P1 centre of lateral resistance | **Gate P1** *(new)* | CLR of a known analytic section within tolerance |
| P3 force-balance stability path | **Gate P3** *(new)* | an applied external force at a height reproduces the existing kg·m offset-load result when converted — **the g-cancellation trap in §1.3 gets its own test** |
| W0 Loyd traction | **Gate W0** *(new)* | reproduces Loyd's published `P_max` and the `v_w/3` optimum; crosswind/static ratio lands in the 8–12× band the marine operators report |
| W1 + tether drag | **Gate W1** *(new)* | tether drag is a *reported component*, never folded into a total |
| **The LOAD gate** | **Gate WL** *(new)* | for a given (vessel, kite) the peak tether tension, heel and trim are computed and the configuration is **REFUSED** when any exceeds `limits`. Test feeds it the 25 m²-on-6.8 t case from §5.2, which must be refused |
| Scope guard extended | extend **Gate 6** | a kite-rigged craft does not receive ISO 12217-**1** findings; `iso12217_2_thresholds` recorded via `refdata.absent()` and added to `PURCHASE_QUEUE` |

### Phase 5 — roll and pitch RAOs (P2)

Extends `seakeeping.py` past heave. Precondition for §5.3. Needs its own anchor.

### Phase 6 — RUN spine and the delta engine

Observation rows in `db.py`; the generic delta; `flywheel` gains a non-
`evaluate()` data source. **This is where §2's loop opens** and it should be
scheduled as early as a single instrumented hull allows — it does not need
autonomy, only telemetry.

### Phase 7 — WindWing W2

Trajectory optimisation against vessel response. Blocked behind P1, P2, P3, P5.
Recorded as blocked in the ledger, with an owner and a review-by date.

---

## 10 · What could not be verified

- **Nothing in §1 was executed.** No `pytest`, no `python -m navalai.gates`, no
  imports. Every claim is static reading plus the greps quoted. No gate's
  current colour is asserted anywhere in this document.
- **Whether the ladder has ever run above L1 on this machine.**
  `data/navalai.sqlite3` (24 KB, last written 2026-08-07) was not queried, so
  whether any L2 or L3 row exists — i.e. whether `revalidate` has ever actually
  promoted a hull here — is unknown. This is the single most load-bearing thing
  left unchecked.
- **Whether `pipeline.py` has ever executed outside tests.** The absent
  `archive.jsonl` is strong evidence it has not, but that path is gitignored, so
  a run on fortress001 would leave no trace here.
- **HookProbeOS / HEQK were not read.** §6.5 is a requirement list.
- **The Makani repository was not cloned or built.** §5.1 is from its README and
  the published reviews. Whether `analysis/control/crosswind.py` is usable
  against a soft marine kite rather than a rigid wing is unassessed.
- **Every marine-kite figure in §5.1 is a vendor or press claim**, not a
  measurement this project made. The Airseas 20%→16% gap is quoted precisely
  because it shows what such claims are worth.
- **The 25 kN estimate in §5.2** is 25 m² × Beyond the Sea's reported ~1 kN/m².
  That coefficient is a peak from a vendor test at an unstated wind speed and
  unstated flight mode. It is used as an order-of-magnitude argument for gate
  *ordering*, and must not be quoted as a design load.

---

## 11 · Sources

Makani — [repository](https://github.com/google/makani) ·
[TU Delft on the open-sourcing](https://www.tudelft.nl/en/2020/lr/13-years-of-makani-airborne-wind-energy-knowledge-available-open-source) ·
[X patent non-assertion pledge](https://spectrum.ieee.org/exclusive-airborne-wind-energy-company-closes-shop-opens-patents) ·
[The Energy Kite report](https://archive.org/stream/theenergykite/20200901_MVP_TheEnergyKite_pt1_pt1words_djvu.txt)

Airborne-wind theory and control —
[Loyd, *Crosswind Kite Power* (1980)](https://awesco.eu/awe-explained/Loyd1980.pdf) ·
[Eijkelhof, Rossi & Schmehl, circular vs figure-of-eight, *WES* 11, 1287 (2026)](https://wes.copernicus.org/articles/11/1287/2026/) ·
[Kite–platform interaction offshore (arXiv 2401.05950)](https://arxiv.org/abs/2401.05950) ·
[Erhard & Strauch, control of towing kites (arXiv 1202.3641)](https://arxiv.org/pdf/1202.3641) ·
[Quaternion-based optimal control of SkySails (arXiv 1508.05494)](https://arxiv.org/pdf/1508.05494) ·
[Fagiano et al., *Autonomous AWE Systems*, Annual Rev. Control](https://www.annualreviews.org/doi/10.1146/annurev-control-042820-124658)

Marine kite systems —
[Airseas Seawing](https://airseas.com/en/seawing-system/) ·
[Seawing validation testing (16%)](https://maritime-executive.com/article/seawing-kite-completes-validation-testing-demonstrating-fuel-savings) ·
[Beyond the Sea SeaKite](https://beyond-the-sea.com/en/seakite/) ·
[Beyond the Sea — first fishing vessel](https://beyond-the-sea.com/en/beyond-the-sea-equips-a-fishing-vessel-for-the-first-time/) ·
[SkySails, how power kites work](https://skysails-power.com/how-power-kites-work/) ·
[Silent-Yachts kite demo](https://marineindustrynews.co.uk/silent-yachts-demos-kite-sailing-catamaran/) ·
[Bureau Veritas WPS-1/WPS-2 notations](https://marine-offshore.bureauveritas.com/magazine/wind-assisted-propulsion-takes-center-stage)

Regulation —
[IMO adopts the MASS Code](https://www.imo.org/en/mediacentre/pressbriefings/pages/imo-adopts-mass-code.aspx) ·
[IMO autonomous shipping FAQ](https://www.imo.org/en/mediacentre/hottopics/pages/autonomous-shipping.aspx) ·
[DNV on MSC 111](https://www.dnv.com/news/2026/imo-mcs-111-new-mass-code-adopted/) ·
[Recreational Craft Directive 2013/53/EU](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32013L0053) ·
[EN ISO 12217-2 (sailing craft)](https://ce-marking.help/directive/recreational-craft/standard/5843/en-iso-12217-22017)

Environmental data —
[ERA5 hourly single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) ·
[Copernicus Marine Toolbox](https://toolbox-docs.marine.copernicus.eu/en/v2.0.0/usage/quickoverview.html)

Competitors —
[Compute Maritime](https://www.computemaritime.com/) ·
[Compute Maritime — About (scope and claims)](https://www.computemaritime.com/about) ·
[Khan, Goucher-Lambert, Kostas & Kaklis, *ShipHullGAN*, CMAME 411 (2023)](https://arxiv.org/abs/2305.00210) ·
[Siemens Simcenter on the NeuralShipper integration](https://blogs.sw.siemens.com/simcenter/ship-design-with-generative-ai/) ·
[Siemens / Compute Maritime partnership](https://www.ship-technology.com/news/siemens-compute-maritime-generative-ai/) ·
[GenDSOM — the AI-designed crew transfer vessel](https://rapidfusion.co.uk/blogs/case-studies/compute-maritime-about-research-technology-careers-newsroom-contact-worlds-first-ai-designed-crew-transfer-vessel-revealed-by-compute-maritime-and-partners)
