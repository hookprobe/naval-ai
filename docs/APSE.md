# APSE — Adaptive Physics & Scaling Engine

Five modules, one gate (`tests/test_stageG.py`, 33 tests):

| module | owns |
|---|---|
| `navalai/similitude.py` | dimensionless state, scale transforms, scale-effect accounting, `PhysicalModel` |
| `navalai/extrapolate.py` | ITTC-78 model→ship, form-factor calibration, residuary sanity |
| `navalai/fidelity.py` | the real cost knob: mesh density → cells, steps, wall-clock, RAM; fail-fast admission |
| `navalai/planner.py` | Bayesian experiment selection: information gain per CPU-second |
| `navalai/evidence.py` | the Design Evidence Graph — why every number is the number it is |

---

## 1. The finding that reshaped the brief

The brief proposed treating **geometric scale as a search variable to make CFD
cheaper**: try 1:1, 1:20, 1:50, 1:100, keep the cheapest that clears a
confidence bar.

That premise is false for this pipeline, and the pipeline proves it.
`cfd.case.background_counts` takes **no `lwl` argument**. Every domain extent is
a multiple of Lwl and the tank depth is `max(0.6 L, 1.5 λ/2)` with
`λ/L = 2π Fn²`, so at fixed Froude number the mesh is Froude-similar.

**MEASURED** — three cases generated at Fn 0.26, `case.info` diffed:

| hull | Lwl [m] | Re | background cells |
|---|---:|---:|---:|
| 1:100 of the ship | 2.3000 | 2.492e+06 | **13608** |
| KCS model 1:31.6 | 7.2786 | 1.403e+07 | **13608** |
| KCS ship 1:1 | 230.0000 | 2.492e+09 | **13608** |

A 100:1 span of hull size, a 1000:1 span of Reynolds number, the same mesh to
the cell. The timestep is Courant-limited (`dt ~ dx/U`) and the run is a fixed
number of flow-throughs (`T ~ L/U`), so the **step count is scale-invariant too**.

> Shrinking the geometry costs exactly the same CPU and throws away Reynolds
> number (λ^1.5 — 354× at 1:50) and Weber number (λ²).

Model scale is what a **towing tank** is forced into, because a 230 m basin does
not exist. CFD has no such constraint. So scale is an *input* (set by the data
you are comparing against), and **mesh density is the cost variable**.

Guarded by `test_geometric_scale_buys_no_cpu` and `test_cost_does_not_depend_on_hull_size`.

---

## 2. Similitude

`Condition(lwl, speed, rho, nu, sigma_surface, g)` → `fn`, `re`, `we`, `wavelength`.

Froude exponents (`ship = model · λ^p`, same fluid), derived not tabulated:

| quantity | p | | quantity | p |
|---|---:|---|---|---:|
| length | 1 | | force | 3 |
| area | 2 | | moment | 4 |
| volume, mass | 3 | | pressure | 1 |
| velocity, time | ½ | | power | 3½ |
| frequency | −½ | | **acceleration** | **0** |

Accelerations are **unchanged** — the classic trap.
`rho_ratio` is applied only to mass/force/moment/pressure/power (a fresh-water
tank result for a seawater ship is 2.7 % light in force, and nothing in velocity).

`scale_effects(ship, model)` computes every group on **both conditions as given**
— so a tank that ran 2 % off the target speed, or in fresh water for a seawater
ship, shows up as a real mismatch rather than a clean λ^-1.5 that was never
achieved. It returns `admissible=False` with reasons when:

- `Re_model < 1e6` — below the accepted floor for a resistance model
  (ITTC 7.5-02-02-01); substantially laminar, and **no extrapolation undoes that**
- `Re_model < 5e6` — transition is set by the turbulence-stimulation device, not
  the hull; a CFD model at this Re has no such device
- `We_model < 200` — surface tension holds the free surface together; spray and
  crest breakup are not scaled and **cannot be corrected**

The distinction is deliberate: a Reynolds violation is *correctable* (that is
what ITTC-78 is for); a Weber violation is not. Collapsing both into one
"confidence" scalar would hide the difference that decides admissibility.

`PhysicalModel` is frozen; `with_()` returns a new instance and re-measures the
effects. Full scale (λ=1) is the default.

---

## 3. ITTC-78 extrapolation

```
C_Tm = R_Tm / (½ ρm Sm Um²)                    measured (tank or model CFD)
C_Fm = 0.075 / (log10 Re_m − 2)²               ITTC-57
C_R  = C_Tm − (1+k) C_Fm                       residuary — ASSUMED Re-invariant
C_Fs = 0.075 / (log10 Re_s − 2)²
ΔC_F = [105 (k_s/L_s)^⅓ − 0.64] × 1e-3         Bowden–Davison roughness
C_AA = cd_air (ρ_air/ρ_water) A_T / S          air
C_Ts = (1+k) C_Fs + C_R + ΔC_F + C_AA + C_A
```

`ittc57_cf` and `form_factor` are **imported from `resistance.py`**, never
restated — the same single-source rule that `limits.py` exists to enforce.

**The load-bearing assumption, stated out loud.** `C_R` is *not* independent of
Reynolds number; it absorbs the whole 3-D viscous-pressure and wave-breaking
difference between scales, and (1+k) is measured at model Re and applied at ship
Re. This is the largest error in ship-resistance prediction, and it is why
full-scale CFD is worth doing: **at λ = 1 the procedure collapses to the
identity and the assumption is never invoked** (`test_extrapolation_is_the_identity_at_full_scale`).

Uncertainty is propagated in quadrature over measurement, form factor,
roughness, and Re-invariance. The form factor enters **twice with opposite
signs** (subtracted at model Re, added back at ship Re), so its sensitivity is
`(C_Fs − C_Fm)` — much smaller than either term. Treating (1+k) as a flat 10 %
on `C_Ts` would overstate the band by roughly an order of magnitude.

### Form factor as calibration — and as a sponge

`calibrate_form_factor(cond, ct)` inverts one measured `C_T` into `k` via
`(1+k) = C_T/C_F` with `C_R ≈ 0`. (1+k) is a **shape property** that survives
both Froude and Reynolds scaling, so one expensive CFD point calibrates L1 at
every scale and speed. **The validity condition is not optional**: `C_R ≈ 0`
holds only as Fn → 0 (Prohaska fits over Fn 0.1–0.2 and extrapolates to zero).

`residuary_check` catches the failure mode. Worked, on numbers this project
already has — KCS EFD `C_Tm = 3.711e-3` at Fn 0.26, `C_Fm = 2.832e-3`:

| (1+k) | C_R | share of C_T | verdict |
|---:|---:|---:|---|
| 1.10 | 0.596e-3 | 16.1 % | plausible |
| **1.27** | **0.114e-3** | **3.1 %** | **implausibly small** |

A (1+k) of 1.27 for KCS is worth re-deriving before it is used as a calibration
constant: it is well above the ~1.1 Tokyo-2015 uses for this hull, and at that
value almost no wave-making is left at a Froude number where KCS demonstrably
makes waves. The likelier reading is that it absorbed a **friction shortfall** —
which is the known state of our own mesh (y+ median 2475, 32 % layer coverage on
the old grid). The check does not refuse it; it refuses to let it pass unremarked.

---

## 4. Fidelity and cost

Every constant is measured from `runs/` logs, not assumed.

`runs/kcs_sym` — 241,946 cells, symmetric, np=10, one unbroken ExecutionTime
segment, 3145 steps to t = 13.739 s:

| window t [s] | steps | dt_avg [ms] | wall/sim-s | wall per cell-step |
|---|---:|---:|---:|---:|
| 0.00 → 2.43 | 786 | 3.095 | 241.7 | 3.09 µs |
| 2.43 → 5.85 | 786 | 4.341 | 229.9 | 4.13 µs |
| 5.85 → 9.52 | 786 | 4.680 | 109.9 | 2.13 µs |
| 9.52 → 13.74 | 786 | 5.362 | 90.1 | 2.00 µs |

1. Cost per cell-step is roughly **constant**, and `runs/kcs_iso` at 637k cells
   (2.6× larger) sits in the same band (2.56–2.96 µs). Wall time is **linear in
   cell count** — which is what lets one measured constant predict an unrun grid.
2. The run gets **cheaper as it settles**: dt grows 3.1 → 5.4 ms. Costing a run
   at its opening rate over-budgets it ~2.7×.

```
dt    = 0.47 · maxAlphaCo(2) · fs_dz / U        COURANT_EFFICIENCY measured
sim   = flow_throughs · 4.5 · Lwl / U
wall  = 2.835e-6 · cells · steps · NP_SPEEDUP[10]/speedup(np)
cells = background_counts(density, symmetric) · 17.78
```

`CELL_STEP_S` is already a **np=10 rate**, so the parallel correction is a
*ratio* of speedups — it must not be divided by the speedup again (that
under-predicts by 1.7×). It reproduces the measured sweep: np=5 → 1.672× slower,
np=15 → 1.204× slower than np=10 (`test_parallel_correction_reproduces_the_measured_np_sweep`).

**RAM is the one assumed number** (1.5 kB/cell, 50 % sigma). No run recorded RSS.
`CostEstimate.basis['ram']` says `ASSUMED … owed`, so a RAM refusal is never
quoted as measured. One `/usr/bin/time -l` closes it.

### Correction to a budget in CLAUDE.md

CLAUDE.md budgets the GCI triplet at "medium ~3× coarse and fine ~8×". Those are
**cell** ratios (2.79× and 7.79×) and correct as such — but not **cost** ratios.
The timestep is Courant-limited, so a √2 finer grid also takes √2 more steps:

```
cost = cells × steps = 2.79 × 1.414 = 3.9×   (not 3×)
                       7.79 × 2.0   = 15.6×  (not 8×)
```

A full triplet is **~21× the coarse grid, not ~12×** — a 75 % under-budget if the
cell ratio is used as a time estimate.

### Admission (fail fast, before meshing)

Refuses on: wall + 1σ over ceiling (a 50/50 chance of blowing the budget is not
"within budget" — on this Mac an over-run is a *lost* run, not a slow one); RAM
over ceiling; **< 20 cells per wavelength** (physics, not cost — the bar that
stops the cheapness search running away to free); tank seiche on the wave period;
> 6 h without resumability (`pmset -g log`, Thermal Emergency Sleep 2026-08-04).

`cheapest_admissible` scans density **ascending** and takes the first hit. That
is the cheapest only because cost is non-decreasing in density — pinned by
`test_cost_is_monotone_in_density_so_ascending_search_is_correct`.

### Tank length resonance (seiche)

```
T_seiche = 2 L_tank / √(g h)
```

No hull term — it is a property of the **box**, so no hull or mesh change removes
it. With depth floor binding (h = 0.6 L) and the domain at 4.5 L:

```
T_seiche / √(L/g) = 2·4.5/√0.6 = 11.62        T_wave / √(L/g) = 2π Fn
```

Their **ratio is a function of Froude number alone** — so it is Froude-similar and
**survives scaling exactly**. Shrinking the model carries the resonance along
into every case, unchanged (`test_seiche_is_froude_similar_and_survives_scaling`).

Depth is already sized against the wave; **length is not**. Measured on
`runs/kcs_sym`: seiche 10.0 s vs a 1.41 s wave period — 7.1× apart, so *not*
frequency contamination. But the run had reached only t = 13.7 s = **1.4 seiche
periods**, so any force average from that log crosses an incompletely damped tank
oscillation. Those are two different findings and the check separates them.

---

## 5. The planner

Gaussian beliefs, closed-form expected information gain — no sampling:

```
1/σ_post² = 1/σ_prior² + 1/σ_exp²
I         = ln(σ_prior / σ_post)          [nats]
score     = Σ_q I_q / cost
```

Three behaviours fall out of the arithmetic that a rule table would get wrong:

- **An experiment vaguer than your belief scores ~0.** Once L2 has pinned a
  quantity to 5 %, an L1 estimate at 25 % adds nothing — nobody writes that rule.
- **Diminishing returns are automatic.** The second identical CFD run gains
  `ln√2 = 0.35` nats where the first gained much more.
- **"Do I actually need CFD?" is answered by arithmetic.** No CFD tier informs
  GM, so CFD's gain on initial stability is exactly zero and it is never selected
  — at any budget (`test_stability_question_never_selects_cfd`).

Refusals are **returned, not raised**, so a rejected option keeps its cost and
reason for comparison instead of vanishing.

`QUESTION_QUANTITIES` maps an engineering question to the quantities it needs;
the tier is then *discovered* from the uncertainty arithmetic rather than
hard-coded.

**It deliberately does not choose a geometric scale** — §1 shows scale has no
effect on the objective, so searching it would return an arbitrary answer dressed
as an optimum.

### Two flaws found in adversarial review, both fixed

1. **Zero-centred quantities.** `σ_exp = σ_rel · value` collapses to zero for a
   quantity believed to be 0 (a trim angle, a list angle), making *any*
   experiment return it as exactly known and satisfying every target on it
   vacuously. `Belief.scale` now supplies the magnitude relative uncertainty
   bites on; with no scale declared, a zero-valued belief is *infinitely*
   uncertain — it fails loudly rather than quietly.
2. **Multi-quantity experiments.** Scoring per (experiment, quantity) but
   retiring the experiment after crediting one made the planner buy a second
   tier for information the first had already produced. An experiment is now
   scored by **total** gain across every quantity it informs, charged once, and
   credited to all of them.

---

## 6. Design Evidence Graph

```
Requirement → Decision → Assumption → Experiment → Evidence → Confidence
```

`db.Provenance` records *what* was computed. The DEG records *why the design is
shaped the way it is*. Two queries earn it:

- `unsupported()` — every decision with no path to any evidence. **The honest
  agenda.** On a real project it is never empty.
- `explain()` — the chain behind one node, as text a reviewer can argue with.

**Confidence is the weakest link, deliberately.** A decision resting on a 97 %
experiment and a 60 % assumption is a 60 % decision. Averaging would let a pile
of cheap confirmations bury one load-bearing guess — laundering a tier-0
assumption into a tier-3 result, which is exactly what honesty rule 1 forbids.

`ALLOWED_SUPPORT` rejects a decision justifying a requirement — the most common
way a design argument quietly becomes self-supporting ("we chose L/B 9.5 because
we need 25 kn, and we need 25 kn because we chose 9.5"). Cycles are rejected at
insertion.

Confidence is computed as a minimum over the **ancestor set**, so it is
path-independent and linear. (The earlier recursion was correct — its visited set
tracked the current path, and diamonds recomputed to the same value — but it was
exponential on deep diamonds and a reviewer read its guard as crediting shared
subgraphs with 1.0. Rewritten so the question cannot arise.)

---

### The stated budget and the wave-resolution bar cannot both hold

Two of this project's own stated constraints conflict, and the conflict is now
pinned by `test_stated_budget_and_the_wave_resolution_bar_are_unsatisfiable_together`:

- **Stated budget:** coarse ~15 min, medium ≤ 2 h, fine ~4–5 h on 10 cores.
- **Stated bar:** ≥ 20 cells per wavelength, or "the whole run is decoration".

**MEASURED** at KCS Fn 0.26 with the current 4.5 Lwl domain:

| density | cells | wall | cells/λ | verdict |
|---:|---:|---:|---:|---|
| 0.5000 | 30,244 | 0.20 h | 10.2 | refused — wave field |
| 0.7071 | 87,833 | 1.18 h | 14.3 | refused — wave field |
| **1.0000** | **241,950** | **3.24 h** | **20.4** | **admit** |
| 1.4140 | 675,640 | 13.58 h | 28.8 | refused — 6 h ceiling |
| 2.0000 | 1,935,602 | 51.89 h | 40.8 | refused — 6 h ceiling |

The coarsest grid that resolves the wave field costs **3.24 h** — past the 2 h
*medium* budget and 13× the 15 min allowed for a *coarse* grid. Every cheaper
grid is refused on physics. `cheapest_admissible` returns `None` for both the
coarse and medium stated budgets.

The closed form says why, and it is the non-obvious part:

```
cells/wavelength = 2π Fn² · 4 nx / 4.5 = 5.585 · Fn² · nx      (Lwl cancels)
```

**Fn enters squared, so LOW-Froude cases are the expensive ones to resolve.** At
Fn 0.26 the scale-1 grid gives 20.4, just over the bar; at Fn 0.20 the same grid
gives 12.1 and would be refused.

Ways out, in order of honesty: run at a **higher Froude number** (Fn ≈ 0.31
resolves on the density-0.7071 grid, ~1.2 h), shorten the domain, or accept a
coarser wave field and say so in the badge. APSE does not pick — it refuses to
let the conflict be absorbed by whichever check happens to run first.

### Consequence for the planned GCI triplet

Building **upward** from density 1.0 (`--anchor coarse`): 3.24 + 13.58 + 51.89
= **68.7 h ≈ 2.9 days**, which matches CLAUDE.md's "~3 days" — and is 21.2× the
coarse grid, confirming §4 rather than the 3×/8× cell ratios.

Building **downward** from density 1.0 (`--anchor fine`, described in CLAUDE.md
as the cheap direction) is **inadmissible**: both coarser grids fall to 14.3 and
10.2 cells per wavelength, below this project's own bar. A GCI computed over
them would be a convergence study of an unresolved wave field.

## 7. Open, and honestly recorded

- **RAM per cell is assumed, never measured.** Everything else here is measured.
- **The √2 step does not refine z.** `test_z_bands_freeze_between_coarse_and_medium_MEASURED_DEFECT`
  pins a real defect found by this suite: the largest-remainder apportionment
  puts `nz_hull = 2` at *both* density 0.7071 and 1.0, so the interface cell
  height — and therefore dt — is **identical on the coarse and medium grids**. A
  GCI built on that pair bounds x–y discretisation only. At 0.7071 the two core
  z-bands are also 2 and 1, where CLAUDE.md records they must be equal.
- **`(1+k) = 1.27` for KCS is unreconciled** with a plausible residuary at
  Fn 0.26 (§3).
- The extrapolation's `C_R` Re-invariance band (10 %) is a stand-in until
  full-scale CFD measures it — which is what Gate 2M eventually enables.

## Extension points

- New similarity law: add to `Similarity` and a group to `scale_effects`.
- New tier: add rows to `TIER_SIGMA_REL` and a cost to `TIER_COST_S`; the planner
  picks it up with no other change.
- New engineering question: one row in `QUESTION_QUANTITIES`.
- Re-calibrate cost: `CELL_STEP_S`, `COURANT_EFFICIENCY`, `REFINE_FACTOR` are the
  three measured constants, each with the run it came from named in place.
