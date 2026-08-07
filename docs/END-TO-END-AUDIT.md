# End-to-end flow audit — mission sentence to build-ready output

> Measured 2026-08-07 on consolidated `master`, statically (four agents were
> concurrently editing the physics and rules modules, so a live run would have
> read a moving tree). Companion to `docs/HLD.md` and `docs/STAGE-PLAN.md`.

---

## 1 · The headline: there are TWO lifecycles in one product

This is the cardinal defect of this codebase — **a thing declared twice** —
applied not to a number but to the lifecycle itself.

| | `navalai/agents.py` | `navalai/pipeline.py` |
|---|---|---|
| Role | **the actual driver** | **the documented spine** |
| Entry | `run_plm(mission_text, n_designs, batch)` | `Pipeline` |
| States | 4 informal strings: `candidate` / `validated` / `rejected` / `engineered` | 11 typed `Stage` + 7 `Terminal` |
| Transition guard | none | forward-only; illegal edges **raise** `IllegalTransition` |
| Terminal uniqueness | not enforced | exactly one per genome, enforced |
| Archive | in-memory `Audit` | append-only `JsonlLog`, `LogTruncated` if the file shrinks |
| Unmeasured metric | not modelled | `Unmeasurable` — a guard with no evidence refuses |
| Reaches manufacturing | **yes** (`engineer` → `unroll`: panels, nest, BOM) | n/a |
| Production callers | it *is* the entry point | **ZERO** |

**MEASURED: `Stage.` does not appear anywhere in `navalai/`, `scripts/` or
`ui/` outside `pipeline.py` itself.** The only production imports of
`navalai.pipeline` take `JsonlLog` (a logging utility, reused by `gaps.py`) —
never the lifecycle. The 11-state spine is 777 lines, proven by 48 tests under
Gate S, and **nothing in the product walks a genome through it.**

That is register gap A4's shape — *"a NON-TEST caller of X"* — applied to the
spine that the HLD documents as the backbone.

### Why this is not cosmetic

The properties `pipeline.py` exists to guarantee are exactly the ones
`agents.py` cannot offer:

- `agents.py` can emit `engineered` for a design with **no equivalent of
  `HYDROSTATICS` having succeeded**, because there is no transition graph. That
  is gap **B9**'s shape — *a hull with no floated state gets a mesh built for
  it* — with a manufacturing BOM attached instead of a mesh.
- A failure in `agents.py` is a `rejected` message with free text. In
  `pipeline.py` a non-`SUCCESS` terminal **requires a reason** or the
  transition raises, because "a failure with no reason is a genome abandoned
  with paperwork".
- `Audit` is in-memory and dies with the process. `JsonlLog` is append-only and
  detects truncation.

**So the product's real flow is the one with none of the guarantees, and the
guarantees are all in the flow nothing calls.**

### The fix is a wiring job, not a rewrite

Both halves already exist and are tested. `agents.py`'s four kinds map onto the
spine without inventing anything:

```
 _builder    emits 'candidate'  ->  Stage.NEW -> GENERATING
 _validator  emits 'validated'  ->  VALIDATING -> HYDROSTATICS  (or a Terminal
             emits 'rejected'   ->  FAILED_GEOMETRY / FAILED_HYDROSTATICS, WITH a reason)
 _engineer   emits 'engineered' ->  MANUFACTURING -> SCORING -> ARCHIVED -> SUCCESS
```

The stages `agents.py` has no step for (MESHING, CFD, SEA_STATE, ERGONOMICS)
are the ones that are compute-bound or unbuilt — and a genome that has not
reached them should say so through the spine rather than skip silently to
`engineered`.

**This is S1 work and it is the highest-value wiring in the repository:** it
converts an untracked in-memory audit into the evidence graph the whole honesty
argument depends on.

---

## 2 · The documented demo stops one step short of the claim

`scripts/demo_mission.py` is the artefact a reader runs to see the product. Its
actual sequence:

```
translate(mission_text)        mission -> typed MissionSpec + Requirements
  -> evaluate(x, m)            L0 + L1, constraint vector, badges
  -> pareto_front(...)         NSGA-II over the grammar
  -> rules: iso12217 + iso12215 (tier R, with the disclaimer)
  -> heave_coeffs(...)         an L2 Capytaine spot-check, 3 frequencies
  -> db.Provenance(...)        hull id + L1 results recorded
  -> ENDS
```

It never calls `unroll` (panels, nesting, DXF), `engineer` (BOM, sheet count)
or `export` (STEP/IGES). The project's headline claim is *"…before it exports
as build-ready geometry"*, and the script that demonstrates the project stops
before that clause.

The capability is **not** missing — `agents.run_plm` reaches it, because
`engineer.py` imports `unroll`. So this is a demonstration gap, not a
capability gap, and it is cheap to close. But a reader who runs the demo
concludes the manufacturing tail does not exist.

---

## 3 · Seams that are correctly closed (verified, no action)

Recording these so the audit is not read as uniformly negative — the parts that
are wired are wired well:

- **The LLM seam.** `translate.sanitize` clamps ranges, whitelists strings, and
  ratchets the design category one way only (`min()` over `'A' < 'B' < 'C' <
  'D'`). No path from natural language to geometry. Gate 5.
- **Export refuses unvalidated designs.** `export.refuse_unvalidated` is called
  by `export_step`, `export_iges` and `export_dxf` — gap A5, closed.
- **The ladder is climbable and refuses honestly.** `evaluate.revalidate`
  escalates to L2 and refuses L3 with `TierRequiresOperator`; L3 is READ from
  recorded evidence and never solved in-process (Gates R3, R4).
- **No orphan modules.** Every module in `navalai/` has at least one production
  consumer — including the five APSE modules carried over in the consolidation.
  `policy/` is the only name with none, and that is because BuildPlan 3's
  governance kernel is not built yet.

---

## 4 · What this changes in the stage plan

`docs/STAGE-PLAN.md` S1 is "make the checks unfakeable". These two findings
belong in it, and they raise its value:

| Finding | Stage | Why there |
|---|---|---|
| Two lifecycles; the spine has no production caller | **S1** | until the driver and the guarantees are the same object, every downstream claim about a genome's history is made by the half without an archive |
| The demo stops before manufacturing | **S1** | one-line-of-sight fix; it is what a reader uses to judge whether the claim is true |

Neither is a new capability. Both are the same request the register makes of
every other finding: **make the thing that is claimed be the thing that runs.**
