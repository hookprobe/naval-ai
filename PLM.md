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
| Generative core | `generative.py` (diffusion upgrade slot) | L0-feasible sampling. The "100%" this row used to claim was measured on the REJECTION SAMPLER, which has `grammar.check` inside its loop, so it was true by construction; the model's own raw feasibility is the number that matters (gap D11) |
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
| **Full-Vessel Line v2** | + interior/exterior arrangement + unsinkability | + arrangement grammar | + ergonomics tier E + flotation tier F | V2.0 LANDED (`navalai/refdata/`, Gate V2.0); V2.1–V2.6 PLANNED — see `docs/BUILD-PLAN.md` Part V.b |

Adding a product = one mission preset + one grammar subspace + one rules
profile. If it needs new physics or new grammar axes, that's a PLATFORM
change and goes through the lifecycle below.

## 3 · Lifecycle: requirement → retirement

1. **Requirement** — user need or field finding, stated with a measurable bar.
2. **Research** — deep-research sweep; claims verified; recorded in the plan
   doc with citations (pattern: `docs/BUILD-PLAN.md` Part V.a §1).
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

Coordination: git is the handoff (pull → work → push). A role announces scope
in its commit messages. Cross-role platform changes need a plan-doc update in
the same push.

## 5 · Gate registry (single source: `python -m navalai.gates`)

GREEN = enforced by tests · METAL-GATED = needs hardware/software evidence ·
REVIEW-GATED = needs qualified human. RED = ran and missed its bar, kept red.

**No gate status or measurement is restated in this file.** The registry is
`navalai/gates.py`, the live status is `python -m navalai.gates`, and every RED
row's measured watermark, owner and review-by date is in
`data/gate-ledger.json`. This paragraph replaced three numbers, and the reason
is gap J1: one Gate 2M measurement was copied into README, PLM §5, PLM §6,
ALIGNMENT.md and `docs/BUILD-PLAN.md` Part V.f, then invalidated twice by our own
bug fixes — after which five different figures were in circulation and only one
of them was reproducible from any run directory. A management file that
restates a measurement becomes a fifth source of it.

Open RED rows as of 2026-08-06 — **names only, look up the numbers**: Gate 2M
(KCS calibration, cfd-engineer), Gate 2U (unattended meshing, cfd-engineer),
Gate 6R (ISO parity — compliance; flipped red 2026-08-06 when `is_complete()`
began requiring the dated editions the record admits it does not have).

## 6 · Roadmap board (update in place)

| Epic | Owner | State |
|---|---|---|
| Own-hull GCI triplet | cfd-engineer | **HELD, deliberately.** Blocked behind the open pressure-drag discrepancy (`docs/BUILD-PLAN.md` Part V.d R5.5): a GCI would converge onto a wrong number more precisely. Do not spend the compute until R5.5 closes. |
| Gate 2M: KCS calibration vs Tokyo-2015 | cfd-engineer | **RAN, and RED — see `data/gate-ledger.json` for the measured watermark, and the register §F for what is still wrong with it.** No figure is repeated here (gap J1). It did its job regardless of the value: the own-hull C_T/C_F ~ 9.8 is now known to be OUR SETUP and not the hull, which no own-hull GCI could ever have decided. Geometry: `benchmarks/kcs.py` carries the EFD and the scatter band from the proceedings PDF; the hull regenerates via `scripts/fetch_benchmark_geom.py` against the committed `data/benchmark_geom/CHECKSUMS.json`. |
| **Second benchmark anchor for the SKUs** (DTMB 5415 / DSYHS / Series 62) | cfd-engineer | QUEUED — KCS calibrates the instrument but shares none of the chine/transom/spray physics the product lines depend on; Gate 2M alone must not be read as small-craft validation. See `ALIGNMENT.md`. |
| L3→co-kriging wiring (first HF points into the spine) | ml-engineer | BLOCKED on Gate 2M |
| Guided tabular diffusion behind `HullFamilyModel` | ml-engineer | READY (PyTorch-MPS) |
| LoRA mission translator above the sanitizing seam | ml-engineer | READY (mlx-lm) |
| **Full-Vessel Line v2** (arrangement + ergonomics + unsinkability) | ergonomics-architect | **V2.0 LANDED** — `navalai/refdata/{ergonomics,flotation}.py`, Gate V2.0 GREEN: every constant carries `source` + `basis`, and everything BuildPlan 2 §1 marks paywalled is recorded ABSENT rather than filled in at a plausible value (`refdata.absent()`). V2.1–V2.6 unstarted; BuildPlan 3 R8 lists R2 and R3 as their preconditions. |
| Standards/books purchase queue (ISO 15085:2024, 12217-3, 9094; ABYC H-41; Panero & Zelnik; Larsson & Eliasson) | compliance | QUEUED — now itemised in code as `navalai.refdata.PURCHASE_QUEUE`, with `refdata.absent()` naming exactly which quantity each purchase unblocks. Nothing carries `basis='purchased'` yet, and a test asserts that. |
| ES-TRIN rules profile | compliance | QUEUED — the Solar Liveaboard is a Danube boat and it is the one SKU that requires it (gap G7, zero code). |
| ISO parity review (Gate 6R) | compliance | **RED as of 2026-08-06.** `is_complete()` now requires each standard's DATED edition, which the record does not have; see the ledger. Clearing it costs no compute — a reviewer writes two edition strings — and clearing it still does not open Gate 6, whose bar is verdict parity on >=3 reference designs (gap D9). |
| CI/CD enforcement of the gate ladder | verification | **DONE** — `.github/workflows/gates.yml` + `.githooks/pre-push` (install: `scripts/install-hooks.sh`). Also fixed a soft-green in the runner itself: pytest exits 0 when every test SKIPS, so a missing optional dep used to print GREEN having verified nothing. |
| Unattended-meshing robustness (plan Gate 2: >=95% of 200 random hulls) | cfd-engineer | **MEASURED, RED — Gate 2U**, watermark in the ledger. BuildPlan Risk #1 is a number instead of a worry. Two caveats travel with it: the sample is N=8, and the "converges" half of the bar has NEVER been measured — `--solve` exists and has not been run. Re-measure at N=200 when there is a spare machine-day. |
| Documentation as a gated artifact | verification | **DONE (2026-08-06).** README's gate table is GENERATED from `navalai.gates` and a test fails when they diverge; a second test forbids any of the five superseded Gate 2M figures appearing in README, PLM, MACBOOK or ALIGNMENT. Doc drift was a defect class here, not cosmetics — five documents each held their own copy of one measurement. |
