# E5-CHINE — mathematical design note for the three geometry corrections

Written before the code, as required. Each section answers *why the limit
exists* before proposing a change, because a bound raised without knowing what
set it is a guess wearing a number.

---

## 1. Why the SAC caps near Cp 0.85, and what actually binds

### Current representation

`navalai/geometry.py` builds the sectional-area curve as two power-law
branches meeting at the maximum-area station `xm = x_mb·L`:

```
a(x) = R + (1-R)·h(x/xm ; pa)              x <  xm      (run-in from the transom)
a(x) = 1   -       h((x-xm)/(L-xm) ; pf)   x >= xm      (run-out to the stem)

h(s ; p) = s^p                for p >= 1
         = 1 - (1-s)^(2-p)    for p <  1
```

`R = r_transom` is the transom area ratio. The zeroth and first moments are
closed form, which is the whole point — `sac_exponents` solves `(pf, pa)`
against the two design targets `Cp` and `LCB` by two nested bisections,
cheaply enough to sit inside `grammar.check`.

### Why it fails

Write `h1(p) = ∫₀¹ h ds`. From the two branches:

```
h1 = 1/(p+1)          p >= 1
h1 = q/(q+1), q = 2-p p <  1
```

so over the permitted exponent range `p ∈ [-6, 8]`,

```
h1 ∈ [0.1111, 0.8889]      (1/9 at p = 8, 8/9 at p = -6)
```

and therefore

```
Cp = S/L = u·(R + (1-R)·h1a) + (1-u)·(1 - h1f),      u = x_mb
```

**MEASURED, maximising over the whole box and ignoring LCB: Cp = 0.9267.**
**MEASURED, with LCB pinned to a real hull and every other gene free: Cp = 0.890.**
(0.8476 is the same sweep with the keel-rise genes pinned at mid-box — a
ceiling measured at a configuration nothing runs, and it flattered the fix.)

The gap between those two numbers is the finding. **It is not the exponent
range that binds — it is the LCB target.** The family has exactly *two* shape
freedoms `(pf, pa)` and must satisfy *two* targets `(Cp, LCB)`. Driving Cp up
saturates both exponents at their bounds, and the longitudinal centre of
buoyancy is then whatever falls out. The kernel says so in its own words:

```
sac: LCB -1.850 %LWL unreachable at Cp 0.9000, x_mb 0.540
     (bracket +1.183 .. +8.594 %LWL)
```

Widening `[SAC_P_MIN, SAC_P_MAX]` would raise the *unconstrained* ceiling
toward 1 asymptotically — `h1 → 1` as `p → -∞` — but it buys the wrong thing.
`h(s) = s^50` is a curve that sits at zero until `s ≈ 0.9` and then leaps: the
resulting SAC is a prism with a *corner* at the shoulder, not a fair hull.
That fails the smoothness requirement, and it still leaves Cp and LCB fighting
over the same two knobs.

### New representation

Insert an explicit **parallel middle body**: a longitudinal interval over
which `a(x) = 1` exactly.

```
x1 = xm - λL/2 ,  x2 = xm + λL/2 ,  λ = l_pmb

a(x) = R + (1-R)·h(x/x1 ; pa)               0  <= x <  x1
a(x) = 1                                    x1 <= x <= x2
a(x) = 1 -       h((x-x2)/(L-x2) ; pf)      x2 <  x <= L
```

The moments stay closed form, so the solve is unchanged in kind:

```
S = x1·(R + (1-R)·h1a)  +  λL  +  (L-x2)·(1 - h1f)
M = x1²·(R/2 + (1-R)·h2a) + λL·xm + (L-x2)·[ x2·(1-h1f) + (L-x2)·(1/2 - h2f) ]
```

`λL·xm` is the middle body's own first moment: its centroid is `xm` by
construction, because the interval is centred there.

**This adds the third freedom, which is the actual fix.** The middle body
contributes area *symmetrically about `xm`*, so it moves Cp strongly and LCB
weakly — Cp and LCB stop competing for the same two exponents.

### New valid domain

```
λ = 0                    -> byte-identical to the present kernel
λ ∈ [0, 0.6]             -> x1 > 0 and x2 < L for every x_mb ∈ [0.40, 0.68],
                            since λ <= 2·min(x_mb, 1-x_mb) = 0.64 at worst
```

**MEASURED ceilings** (max over the box, LCB free):

| λ | max Cp |
|---|---|
| 0.0 | 0.9267 |
| 0.2 | 0.9413 |
| 0.4 | 0.9560 |
| 0.6 | 0.9707 |

which covers the Fridsma prismatic range of 0.951–0.971.

### Invariants preserved

- `a(0) = R`, `a(xm) = 1`, `a(L) = 0` — unchanged.
- `a` is continuous, and `C¹` at `x1` and `x2` whenever the branch exponents
  are ≥ 1 (the flat meets a curve with zero slope there).
- The moments remain exact, so `sac_exponents` stays two bracketed monotone
  bisections. No Newton step, no clamp, no fallback.
- **λ = 0 reproduces the current geometry exactly**, so every stored genome,
  every saved population and every baseline keeps its meaning.

---

## 2. Why deadrise stops warping at 0.60 L

### Current representation

```python
beta = full(beta_mid)
warp0 = L - beta_len·L
wz = x > warp0
beta[wz] += (beta_bow - beta_mid)·frac²,   frac = (x - warp0)/(beta_len·L)
```

### Why it fails

There is **no clamp and no piecewise limitation in the law itself**. The law
already warps over `[L - beta_len·L, L]` and would warp over the whole hull at
`beta_len = 1`. The limitation is *purely the declared bound* `beta_len ≤ 0.60`
in `grammar.PARAMS`, which freezes deadrise over at least the after 40%.

A warped hull's deadrise grows from the transom forward — the Naples parent
runs 13.2° at the transom to 22.3° at midships — which is warp inside the
frozen region. No choice of the three genes reaches it.

### New representation

**No change to the functional form.** The bound moves:

```
beta_len : [0.15, 0.60]  ->  [0.15, 1.00]
beta_bow : [2.0,  50.0]  ->  [2.0,  70.0]
beta_mid : [0.0,  25.0]  ->  [0.0,  35.0]     (see §3)
```

At `beta_len = 1` the law becomes `beta(u) = beta_mid + (beta_bow - beta_mid)·u²`
with `u = x/L`, so `beta_mid` reads as the *transom* deadrise and the whole
bottom warps monotonically forward. That satisfies `β(0.75L) > β(0.50L)`
by construction and cannot oscillate — it is a single monotone quadratic.

### Why this is sufficient, measured rather than asserted

Fitted to the deadrise distributions of seven published series
(`scripts/e5_chine_warp.py`), worst error at the transom / 50% / 75% stations:

| bounds | worst error over 7 series |
|---|---|
| present | 8.69° |
| `beta_len ≤ 1.0` only | 5.00° |
| **all three bounds above** | **0.50°** |
| plus a free warp exponent (an 18th gene) | 0.00° |

The bound change alone clears the 1° bar on every published series. **The
extra gene is therefore not taken** — it would be freedom added without
evidence that anything needs it, and this project does not add genes to
NSGA-II dimensions on speculation.

### Invariants preserved

- Every existing genome has `beta_len ≤ 0.60`, so its deadrise field is
  unchanged. The domain grows; nothing inside it moves.
- `grammar.check` already enforces `deadrise.order` (`beta_bow >= beta_mid`),
  which keeps the warp monotone forward.
- Deadrise remains one smooth quadratic per hull — bounded, `C¹` at the warp
  start, and a single panel per side, which is what hard-chine developable
  construction needs.

---

## 3. Why beta_mid stops at 25°

### Why it fails

Unlike `LWL`, `BWL`, `T` and `D` — each of which carries a paragraph of
provenance in `grammar.PARAMS` — `beta_mid` carries none:

```python
("beta_mid", "deg", 0.0, 25.0, "deadrise at midship"),
```

There is no geometric validity argument, no mesh-robustness measurement and no
numerical-conditioning reason recorded anywhere. It is an **arbitrary
design-domain bound sitting in the geometry kernel**, which is the same defect
`grammar.PARAMS` fixed for the size box: *a bound with no naval-architecture
content must not refuse a hull that a sourced band accepts.*

Published hard-chine series reach well past it — 30° for Keuning et al. 1993,
38.5° at 75% LWL for the Naples series.

### New representation

Separate **capability** from **design domain**, which this tree already has a
layer for:

```
geometry kernel (grammar.PARAMS)   0° <= beta_mid <= 35°     what can be DRAWN
design search   (navalai/policy)   0° <= beta_mid <= 30°     what will be PROPOSED
```

35° is chosen so the kernel is not the thing that refuses a published hull;
the search envelope stays narrower because a deep-V is still `Candidacy.
EXCLUDED` in `formlib` for this product's speed regime, and that exclusion is
argued from physics rather than from a bound.

### Consequence that must be recorded, not hidden

`formlib` states this bound a **second time**:

```python
"deadrise_deg": _b(0.0, 25.0, Basis.MEASURED, "grammar.PARAMS beta_mid bounds")
```

A number declared twice is this repository's recurring defect. It is derived
from `grammar` rather than restated, so it cannot drift again.

`formlib._M_AFT_DEADRISE` — *"the warp is forward-only and deadrise is frozen
at beta_mid aft of the warp"* — becomes **false** at `beta_len = 1` and is
retired from the families that carry it. A registry that still declares a
limitation the kernel no longer has is worse than no registry.

---

## 4. What this costs, stated up front

Adding `l_pmb` takes the genome from **16 genes to 17**, and the tree treats
arity as part of a population's *identity* (`population.population_id` →
`a16/s0/n25`). Consequences, all of them detected rather than silent:

- `admissibility.calibration_is_current()` compares `grammar.N_PARAMS` against
  `CALIBRATION_GENOME_N_PARAMS = 16` **and** the bank's genome hash. It will
  return `False`, so Gate 2U's mesh screen correctly reports itself
  **uncalibrated** until a new campaign is run at a17. That is the probe doing
  its job; it is not a regression, and nothing is softened to hide it.
- `data/gate2u-a16-*.json` stay valid records of a16 hulls. They are not
  edited. A new bank is a new file at a17.
- Stored a16 populations keep their identity and their meaning.

---

## 5. Regression tests

| id | asserts |
|---|---|
| CAP-CHINE-01 | a valid hull at `Cp > 0.848`, and one near `Cp ≈ 0.95`, with volume, Cb, LCB, SAC monotonicity outside the flat, and section validity all checked — not merely "Cp went up" |
| CAP-CHINE-02 | deadrise reproduces the published NSS distribution (13.2 / 22.3 / 38.5°) within 1°, with `β(0.75L) > β(0.50L)` |
| CAP-CHINE-03 | a valid hull at `beta_mid >= 30°`, geometry and hydrostatics both sound |
| backward compatibility | `l_pmb = 0` reproduces the pre-change geometry exactly |

E5-CHINE's acceptance stays **capability-based**: the gate asks whether the
grammar contains the degrees of freedom to represent the published families,
not whether three fixtures pass.
