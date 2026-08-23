# F17 / Gate 2U — Phase 1: does the 95% bar have a source?

Phase 1 of the F17 brief asks whether the requirement is authoritative before
any code is touched. It is not a rhetorical question here, and the answer
changes what the rest of the work should be.

**Nothing below changes the bar.** Two conflicts are recorded so the decision
can be made deliberately.

---

## 1. The cited source does not exist

`data/gate-ledger.json`, Gate 2U:

```
"bar": ">= 95% of 200 hulls (NavalArchAI-BuildPlan.md Phase 2)"
```

`NavalArchAI-BuildPlan.md` is **not in the tree**. It was deleted in commit
`9e445b6` — *"docs: one build plan, and twelve documents that each held a copy
of it"* — the restructure that produced `docs/BUILD-PLAN.md`.

So the bar cites a document that no longer exists, and nothing in the current
tree re-derives it. That is gap N6's shape (a watermark pointing at something
deleted) applied to a *requirement* rather than to a measurement.

**This does not make the bar wrong.** A superseded document can still record a
real product decision. It makes the bar UNSOURCED IN THIS TREE, which is a
different and fixable problem: someone has to say whether 95% was a product
acceptance requirement or an aspiration, and record the answer where it can
be found.

## 2. There are two gates and two rates, and 95% is attached to both

| | measures | measured |
|---|---|---|
| **Gate 2U** | meshes **and converges** unattended — `settled_drag`'s verdict | **21.7%** (5 of 23 runners, N=25) |
| **Gate 2U-A** | meshes **clean** — checkMesh only | **76%** (19 of 25 at the best fixed layer count) |

`docs/BUILD-PLAN.md` §11.7 attaches a ≥95% bar to **Gate 2U-A**; the ledger
attaches ≥95% to **Gate 2U**. Those are different denominators over the same
hulls, and a reader who conflates them will think the gap is 19 points when it
is 73.

## 3. The engineering plan already exists, and it already says it falls short

`docs/BUILD-PLAN.md` §11.7 is a written, costed plan for Gate 2U-A — a dense
two-sided layer-count search replacing the one-sided step-2 ladder. Its own
conclusion, in the plan:

> **The bar on 11.7-b is 92%, not 95%, and saying so is the point.** Across
> all five recorded arms, 23 of the 25 hulls have at least one count that
> meshes clean, against 19 at the best fixed count. A perfect search therefore
> reaches **92%** on this batch and Gate 2U-A's ≥95% bar is still not met —
> **hulls 4 and 14 pass at no count tried.** The search is not the close-out
> of Gate 2U-A; it is what makes the residual visible.

Costed there too: ~1.9 rungs/hull, so a 25-hull campaign goes ~40 min → ~77
min mesh-only — **1.9× for +16 percentage points**.

**So the best known mesh-side fix is already known to miss the mesh-side bar**,
and two hulls (8% of the batch) fail at *every* layer count tried. Those two
are the actual research question, and they are named.

---

## What Phase 1 establishes

1. The 95% bar's cited source is **deleted**; it is unsourced in this tree.
2. **95% is attached to two different gates** with rates 21.7% and 76%.
3. The best known mesh-side improvement reaches **92%**, is already specified
   and costed, and is already documented as insufficient.
4. **8% of hulls (4 and 14) mesh clean at no layer count** — an unexplained
   residual that no amount of search closes.

## The decision that must be made, by the owner

Not by this gate and not by an agent:

- **Is 95% a product acceptance requirement or was it aspirational?** If it
  stands, Gate 2U is a multi-week CFD robustness project and should be planned
  as one, starting from the two unexplained hulls rather than from the search.
  If it was aspirational, it must be **re-derived against what the mesher can
  demonstrably do** and re-recorded with its evidence — not simply lowered to
  meet the measurement.
- **Which gate does 95% govern** — mesh-clean (2U-A) or mesh-and-converge
  (2U)? They cannot both be the bar.

Until that is answered, Gate 2U stays RED with its measured watermark, which
is the correct state: a failing gate is information.

## What was NOT done

No bar was moved, no denominator redefined, no timeout raised, no sample
reduced. Phases 2–10 of the brief (failure taxonomy, root cause, robustness
architecture) are not started, because starting them before the contract is
settled risks engineering toward the wrong number.
