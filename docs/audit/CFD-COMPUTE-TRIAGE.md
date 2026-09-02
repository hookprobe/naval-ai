# CFD COMPUTE TRIAGE — the KCS campaign, stopped and justified

**Date:** 2026-09-02 · **Trigger:** operator directive — *"stop the KCS CFD
campaign; justify the compute before running it."* · **Action taken first:**
the solver was **stopped at t = 1.80 s of 60 s** (14 min of wall, ~2.3
CPU-hours spent, no checkpoint yet written; the mesh — ~15 min — is
preserved and `run-case.sh` resumes without re-meshing).

---

## 1. What was actually running — the matrix

There was **one case**, not a campaign. Nothing else was queued.

| | `runs/kcs_free1` |
|---|---|
| geometry | KCS, `data/benchmark_geom/kcs.stl`, sha `87062dbf…` (matches `CHECKSUMS.json`; `case.info` records `benchmark=kcs`) |
| cases | **1** (single grid — deliberately NOT the triplet) |
| speed / Fn | 2.196 m/s / 0.26 (KCS Case 2.1, the EFD condition) — one speed |
| condition | **free sinkage and trim** (`sixDoFRigidBodyMotion`, heave+pitch, KG = 0.2303 m) — the one condition difference the fixed runs identified |
| mesh | symmetric half-domain, 16 245 bg cells → ~230 k cells, `n_layers 5` (the measured-good count; the derived 7 is the documented killer) |
| ranks | 10 (the measured optimum on this M5; 15 is 20 % slower) |
| wall time | **~7.8 h measured** (1.80 s sim in 14 min, extrapolated) |
| CPU-hours | **~78** — the operator's "79 hours" figure is accurate for this single case |
| convergence criterion | `grid_result`: drift ≤ 5 % over the last fifth **and** ≥ 1.0 flow-throughs; `end_time 60 s = 4.02` flow-throughs; UNDER-RUN printed below 5.0 |
| quantities | C_T (total/pressure/viscous split), sinkage, trim |
| acceptance | C_T vs KRISO EFD 3.711e-3 within the 7-group Tokyo-2015 scatter (3.620–3.733e-3); sinkage vs −1.394e-2 m; trim vs −0.169° |
| Gate 2M clause | the **C_T-vs-EFD clause only**. The GCI clause needs a triplet and this run does not touch it. |

## 2. What becomes more trustworthy — category

**E (solver verification), with a sliver of F (evidence).** Nothing in
categories A–D moves. If this case completed perfectly, no UI screen, no
hull, no L0/L1 number, and no CFD *infrastructure* (mesh/refuse/harvest
machinery — all already exercised) becomes more capable. It is **not
category G** — it is the named next experiment of a RED gate with an owner
and a review date — but it is not product work either, and it was being
run *by default* rather than by decision. That default is the thing this
document ends.

## 3. Verification vs validation — confirmed, in three places

The distinction is already load-bearing in the tree, verbatim:

* `navalai/gates.py` — Gate 2M's scope: *"SOLVER VERIFICATION ONLY (not
  small-craft validation)"*.
* `ui/api.py:108` — the UI itself tells the user KCS *"shares no chine,
  transom or spray physics with these craft."*
* `docs/audit/ROUND3_FINAL.md` — *"Gate 2M green is not small-craft
  validation, and this document does not claim it."*

Nothing in this triage blurs it, and nothing needed correcting.

## 4. Are three cases required? — Yes for one clause, and it is not scheduled

Gate 2M has two clauses. **C_T-vs-EFD** needs one settled grid.
**Roache GCI** mathematically requires **three systematically refined
grids** — that is the minimum for an observed convergence order, not a
historical choice. But the ledger's own verify command budget for the
triplet is **~68.7 wall-hours ≈ 687 CPU-hours** (`docs/research/APSE.md`
§4: 21×, not 12× — the Courant-limited timestep scales with refinement),
and buying a GCI while the physical condition (fixed vs free tow) is
known-wrong would be a convergence study of the wrong experiment. So the
single free-trim case **is** the smallest valid next step, and the triplet
is **not scheduled** — it becomes worth pricing only if the free-trim C_T
lands near the scatter band.

## 5. Information per CPU-hour — the comparison the decision rests on

Per-case cost on this Mac is ~5–8 wall-hours *regardless of whose hull it
is* — a product hull does not mesh cheaper than KCS. So:

| experiment | CPU-h | what it buys | queue |
|---|---|---|---|
| `kcs_free1` to completion | ~76 more | resolves ONE hypothesis: is the fixed/free condition the remaining C_T error? (viscous already verified at 1.161× ITTC-57 on `kcs_s1`) | A |
| KCS GCI triplet | ~687 | the gate's second clause — premature until the first clause's condition is right | A |
| **1 own-hull case → harvest → KB → Gen 1** | **~60–80** | **the flywheel demonstrated end-to-end** — ROUND 3 Stage 4, the actual product loop | **B** |
| 10 own-hull variants | ~600–800 | design-space anchors for the surrogate — valuable, second |
| L1/surrogate data | ~0 | milliseconds per hull; not CFD-bound at all |

The decisive fact: **the cheapest product-relevant CFD experiment (one
flywheel case) costs the same as finishing `kcs_free1`.** They compete for
the same overnight slot, and only one of them advances the product.

## 6. Is KCS blocking the product? — No, traced

`grep -rl "gate2m|Gate 2M|kcs"` over `ui/`, `evaluate.py`, `optimize.py`,
`certify.py`, `design_report.py` finds: an honesty *note* the UI displays,
an informational EFD-constants panel, and one comment. **No code path
gates on Gate 2M.** Mission → hull → hydrostatics → resistance → mesh →
buildability → export all run with 2M RED, and the UI already states the
validation status honestly. KCS must not — and does not — block product
commissioning.

## 7–9. The two queues

**Queue A — VERIFICATION** (KCS, benchmark meshes, GCI, reproducibility):
runs on *idle* machine time, never at the expense of Queue B, and never by
default. **Queue B — PRODUCT** (own hulls, flywheel anchors, design-space
exploration, hard-chine second anchor): holds priority for the Mac's
compute budget. A RED Queue-A result does not block Queue-B — dependency
traced above, none exists. KCS is kept, classified
**INFRASTRUCTURE / VERIFICATION**.

## 10–11. Smallest valid campaign, and what existing evidence already covers

Already minimal and already reused: the single case (not the 687 CPU-h
triplet), symmetric half-domain (2.6× saving), `np=10` (measured optimum),
resumable checkpoints every 6 s of sim (thermal-nap-proof), and the
**fixed-attitude evidence is NOT being re-bought** — `runs/kcs_s1`'s
measurements (viscous 1.161× ITTC-57, drift 0.31 % at 3.40 flow-throughs,
no tank oscillation) stand in `docs/research/CFD.md` §2 and the anchor
book, and are exactly why this run varies *only* the tow condition.
One real inefficiency found by the launch itself: `run_campaign.sh`
outside the OpenFOAM wrapper declared victory at t=0/0 — fixed (commit
`eeb2afe`), now FATAL.

## 12. The CFD budget rule (now required before any campaign)

Every future CFD launch states, before it runs: **purpose / gate / cases /
wall estimate / CPU-hours / expected evidence / downstream consumer.**
Filed for this case retroactively in §1 — which is the point: it was
launched on "the gate says CFD" and priced only afterwards.

## 13. DECISION: **DEFER**

* **Not STOP**: the case is built, meshed through every guard, and proven
  healthy (stable deltaT 1.8e-3, motion live). Deleting it would re-spend
  the mesh and the diagnosis. It is kept immutable at
  `runs/kcs_free1`; resume is one command:
  `openfoam bash scripts/run_campaign.sh runs/kcs_free1 10`.
* **Not CONTINUE**: category E, zero product dependency, and it competes
  for the same overnight slot as the flywheel case that demonstrates the
  actual product loop. ~2.3 CPU-hours are sunk; that is not a reason to
  spend 76 more today.
* **The gate stays RED, untouched.** Watermark `NONE`, owner
  cfd-engineer, review 2026-09-06. The review can record "experiment
  prepared, meshed, deferred by compute triage" — a true statement — and
  the run proceeds when the operator assigns the machine time, or on
  explicitly-approved idle time.

## 14. Next: product commissioning

The immediate work is the USER → UI → MISSION → HULL → HYDROSTATICS →
RESISTANCE → MESH → BUILDABILITY → SAVE → EXPORT trace, which costs
seconds of compute, not hours — and is also the artifact gap I13 needs a
human for at its far end.

---

## Addendum 2026-09-02: the DEFER now has a batch mechanism

`scripts/cfd_batch.sh <case> <wall-minutes> [np]` runs a slice, then stops
CLEANLY at a checkpoint (`stopAt writeNow` — the solver finishes its step
and writes at whatever time it reached, so nothing is lost between slices)
and restores the case for the next slice. Proven on the deferred case
itself: three slices chained t = 0 → 1.0388 → 1.4890 → 1.9086 s, resuming
to the timestep, mesh built once. The 78 CPU-hour case is therefore
~4 × 2-hour evening slices or one overnight — **when the operator assigns
the time**, which remains the DEFER's condition.
