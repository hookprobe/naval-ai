# Small-craft hydrodynamic scale limits — where the calculus stops mattering

Dated 2026-08-19. Two independent investigations, run in parallel and
cross-checked: a regime study from dimensionless physics grounded in this
repo's own L0/Holtrop measurements, and an independent published-evidence
sweep (USVs, model-basin practice, low-Re friction data) that never saw the
first study's conclusions. They agree at every anchor. The operator's
question, verbatim intent: *where does engineering mathematics materially
change the design decision, and where is it unnecessary precision?*

**Confidence labels used throughout:** [EXP] experimental/measured ·
[THY] theory-derived · [ROT] practice rule-of-thumb · [PROP] threshold
proposed here. All Re use ν = 1.19e-6 m²/s (sea, 15 °C, ITTC; fresh 15 °C
is 1.139e-6 — differences are <5% and never move a verdict). Everything
labelled "measured (repo)" was computed with this repo's own Holtrop
implementation, read-only.

The build-plan consequences live in `docs/BUILD-PLAN.md` §11.8 (the
validation ladder + the fidelity governor); the product-line consequence in
`PLM.md` §0.5 (the drone row, now quantified).

---

## 1 · Executive conclusion

**The drone-line blocker is real, is quantified below, and is not only
friction.** Three independent walls close at the small end:

1. **Reynolds wall [THY, anchored to EXP practice].** ITTC-57 is a fully
   turbulent correlation. The turbulent-validity window (Re ≥ 5e6 while
   Fn ≤ 0.45) **closes entirely below L ≈ 2.6 m** — there is *no speed* at
   which a 2.5 m hull is simultaneously inside both halves of the repo's
   L1. Even the repo's lenient wired policy (refuse only below transition
   onset 5e5) closes below **L ≈ 0.56 m**. Between 0.56 m and 2.6 m every
   displacement-mode operating point sits in the transition band, where the
   friction number carries up to a **factor-2.4 spread** (ITTC-57 vs
   Blasius laminar at Re 2.3e5) on the component that is 72–92% of total
   resistance.
2. **Environment wall [THY + EXP anchors].** Below ~1–2 m, calm-water
   resistance stops being the energy budget. Measured (repo Holtrop): a
   0.5 m hull at cruise (0.5 m/s) has R ≈ 0.06 N, while windage on a fixed
   non-scaling sensor/antenna area (~0.05–0.15 m²) in a 10 m/s wind is
   2–3 N (**30–50×**), and sea-state-3 surface orbital velocity (0.57 m/s)
   *exceeds* the cruise speed. Refining a number that is 2–3% of the
   operating force budget is spurious precision.
3. **Cube-law payload wall [THY].** Displacement ∝ L³ but the
   electronics+battery+comms floor (~3–10 kg for a mission-capable ASV
   [PROP]) does not scale. Geosim scaling of the repo's 12 m/6 t hull to
   0.5 m gives 0.43 kg total displacement — the payload floor alone forces
   a sub-1 m drone into deep immersion, near-zero freeboard, and mass
   fractions no hull-form calculus can recover.

**Minimum sensible maritime-drone size: ~2 m LWL, comfortable at 2.5–3 m**
(§14). A 1–1.5 m drone is buildable but must be designed as a sealed,
self-righting wave-follower whose energy budget is environment-dominated —
its hull-form optimization loop is not worth CFD. Below ~0.75 m,
hydrodynamic design refinement is pointless at every speed: use L0 +
margins, spend the engineering on watertightness, self-righting, and the
power budget.

The independent evidence sweep (Appendix A) lands on the same floor from
the other direction: RANS is *demonstrated* trustworthy at 3 m (Delft 372,
2–5% vs tank), *demonstrated* broken at 1 m (measured ≥30% friction error),
and the field statistic is 30+ Atlantic attempts by ≤2.4 m autonomous boats
with exactly one finisher — a boat that optimised survivability, not
resistance.

---

## 2 · Which dimensionless groups cannot be preserved — small craft vs KCS

This is the core reason "small boats behave differently from ships," and it
is the same reason towing tanks exist and struggle:

| Group | Scales as (fixed Fn) | KCS (230 m, Fn 0.26) | 12 m, Fn 0.26 | 1 m, Fn 0.26 | Consequence |
|---|---|---|---|---|---|
| **Fn** = V/√(gL) | preserved by choice | 0.26 | 0.26 | 0.26 | wave pattern geometrically similar [THY] |
| **Re** = VL/ν | ∝ L^1.5 | 2.1e9 | 2.4e7 | 6.9e5 | boundary-layer regime changes; 1 m is *transitional* [THY/EXP] |
| **We** = ρV²L/σ | ∝ L² | ~1e10 | ~2e6 | ~1e4 | surface tension enters near/below model scale [THY] |
| **λ_env/L** (real seas) | ∝ 1/L | 0.2–0.7 | 3–12 | 40–150 | ship pierces waves; small craft is a wave-follower [THY] |
| **payload/Δ** | ∝ 1/L³ | negligible | ~10% | >100% demand | mass budget dominates design [THY] |
| **windage/R_hull** | ~∝ 1/L–1/L² | negligible | O(0.5–1) at low speed | O(10–50) | aerodynamics dominates propulsion sizing [THY, measured §8] |

Fn and Re **cannot be simultaneously preserved** when scaling down (Re/Fn
similarity would require ν ∝ L^1.5 — no such fluid). Ships resolve this
with the ITTC-57/78 extrapolation *plus turbulence stimulators*; a
free-running drone has no stimulator and no extrapolation target — it
*lives* at model-scale Re. This inverts the KCS worldview: the small craft
is not a small ship; it is a permanently transitional-Re,
environment-dominated, weight-dominated object.

---

## 3 · The Fn / Re grids

Fn = V/√(gL) (bold = past Fn 0.45, Michell/Holtrop-1982 invalid):

| L [m] \ V [m/s] | 0.1 | 0.25 | 0.5 | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 | 4.0 | 5.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.30 | .058 | .146 | .292 | **.583** | **.875** | **1.17** | **1.46** | **1.75** | **2.33** | **2.92** |
| 0.50 | .045 | .113 | .226 | **.452** | **.677** | **.903** | **1.13** | **1.36** | **1.81** | **2.26** |
| 0.75 | .037 | .092 | .184 | .369 | **.553** | **.737** | **.922** | **1.11** | **1.48** | **1.84** |
| 1.0 | .032 | .080 | .160 | .319 | **.479** | **.639** | **.798** | **.958** | **1.28** | **1.60** |
| 1.5 | .026 | .065 | .130 | .261 | .391 | **.521** | **.652** | **.782** | **1.04** | **1.30** |
| 2.0 | .023 | .056 | .113 | .226 | .339 | .452 | **.565** | **.677** | **.903** | **1.13** |
| 3.0 | .018 | .046 | .092 | .184 | .277 | .369 | **.461** | **.553** | **.737** | **.922** |
| 5.0 | .014 | .036 | .071 | .143 | .214 | .286 | .357 | .428 | **.571** | **.714** |
| 7.0 | .012 | .030 | .060 | .121 | .181 | .241 | .302 | .362 | **.483** | **.603** |
| 10 | .010 | .025 | .050 | .101 | .151 | .202 | .252 | .303 | .404 | **.505** |
| 12 | .009 | .023 | .046 | .092 | .138 | .184 | .230 | .277 | .369 | **.461** |
| 15 | .008 | .021 | .041 | .082 | .124 | .165 | .206 | .247 | .330 | .412 |

Re = VL/ν (bold = below 5e5, laminar — friction line refused; italics =
5e5–5e6 transition band):

| L [m] \ V | 0.1 | 0.25 | 0.5 | 1.0 | 1.5 | 2.0 | 3.0 | 5.0 |
|---|---|---|---|---|---|---|---|---|
| 0.30 | **2.5e4** | **6.3e4** | **1.3e5** | **2.5e5** | **3.8e5** | *5.0e5* | *7.6e5* | *1.3e6* |
| 0.50 | **4.2e4** | **1.1e5** | **2.1e5** | **4.2e5** | *6.3e5* | *8.4e5* | *1.3e6* | *2.1e6* |
| 1.0 | **8.4e4** | **2.1e5** | **4.2e5** | *8.4e5* | *1.3e6* | *1.7e6* | *2.5e6* | *4.2e6* |
| 2.0 | **1.7e5** | **4.2e5** | *8.4e5* | *1.7e6* | *2.5e6* | *3.4e6* | 5.0e6 | 8.4e6 |
| 3.0 | **2.5e5** | *6.3e5* | *1.3e6* | *2.5e6* | *3.8e6* | 5.0e6 | 7.6e6 | 1.3e7 |
| 5.0 | **4.2e5** | *1.1e6* | *2.1e6* | *4.2e6* | 6.3e6 | 8.4e6 | 1.3e7 | 2.1e7 |
| 7.0 | *5.9e5* | *1.5e6* | *2.9e6* | 5.9e6 | 8.8e6 | 1.2e7 | 1.8e7 | 2.9e7 |
| 12 | *1.0e6* | *2.5e6* | 5.0e6 | 1.0e7 | 1.5e7 | 2.0e7 | 3.0e7 | 5.0e7 |
| 15 | *1.3e6* | *3.2e6* | 6.3e6 | 1.3e7 | 1.9e7 | 2.5e7 | 3.8e7 | 6.3e7 |

**Regime transitions in dimensionless terms** (not "hull speed = 1.34√L"):
transverse wake wavelength λ_t = 2πV²/g. λ_t = L/2 at **Fn 0.282**
(prismatic hump); λ_t = L at **Fn 0.399** (the "hull speed" interference
peak — the physical content of 1.34√L(ft)); the main resistance hump sits
near **Fn 0.5**, semi-displacement 0.45–0.65, dynamic-lift/planing beyond
**Fn ≈ 0.65–1.0** (equivalently volumetric Fn_∇ ≳ 1–1.5 for light hulls)
[THY + ROT; `docs/SMALLCRAFT_DESIGN_REGIMES.md` uses the same 0.45/0.65
naming].

---

## 4 · The Reynolds wall: where ITTC-57 dies

**The band** (matches `limits.RE_TRANSITION_BAND = (5e5, 5e6)`): flat-plate
transition onset Re ≈ 5e5, fully turbulent by ~5e6 [THY — Schlichting; the
repo correctly flags this as declared-not-transcribed]. Direct ITTC
corroboration found for the ceiling: **ITTC 7.5-02-05-01 (HSMV Resistance
Test, rev. 03, 2017) recommends turbulence stimulation "when the Reynolds
number is less than 5×10⁶ based on mean or effective wetted length"**
[EXP/procedural — verified from the PDF text]. Below Re 5e6 even a towing
tank does not trust natural turbulence.

**L·V products** (ν = 1.19e-6): Re = 5e5 ⇔ **L·V = 0.595 m²/s**; Re = 5e6
⇔ **L·V = 5.95 m²/s** (fresh: 0.570 / 5.70). Examples: a 1 m hull is
laminar-onset below 0.6 m/s and not fully turbulent until 5.95 m/s (Fn 1.9
— planing, so *never* in displacement mode); a 12 m hull is fully turbulent
above 0.50 m/s (~1 kn).

**The two window-closing lengths [THY, derived here — the load-bearing
numbers]:**

- **L < 2.6 m:** no speed satisfies (Re ≥ 5e6 AND Fn ≤ 0.45). Strict
  reading: full L1 (turbulent friction + displacement-regime wave theory)
  has an empty operating envelope.
- **L < 0.56 m:** no speed satisfies even (Re ≥ 5e5 AND Fn ≤ 0.45). The
  repo's wired policy (`resistance.flow_regime`: refuse below onset, report
  inside band) refuses *every* displacement-mode point. A 0.5 m drone has
  literally no admissible L1 operating point under current code — the
  descope note in `PLM.md` §0.5 ("the low-Reynolds/transition regime has no
  valid friction line here") was exactly right and now has a number.

**How big the error is [THY, computed]:** at Re 2.3e5 (0.5 m, Fn 0.25)
ITTC-57 gives C_F 6.64e-3 vs Blasius laminar 2.77e-3 — **2.4× apart**, on a
component that is ~92% of the total there. At Re 9e5 (1 m, Fn 0.35) the
spread is 3.4×. Where the truth sits depends on transition location — a
function of roughness, free-stream turbulence, pressure gradient, and
vibration, i.e., *not predictable from the genome*. This is why radio-yacht
work (IOM class, 1 m LWL: Re 5e5 at ~1.5 kn, 1e6 at ~3 kn) reports the boat
"lands in the difficult transition area" and standard ITTC-57 is explicitly
not trusted there (Appendix A rows 5–6).

**What a valid low-Re friction model needs [THY]:** below Re ≈ 3e5, honest
physics is Blasius C_F = 1.328/√Re (fully laminar) — note the
Prandtl–Schlichting transitional composite C_F = 0.455/(log₁₀Re)^2.58 −
1700/Re goes *negative* below Re ≈ 3e5, i.e., even the classic transitional
line is invalid there. In 5e5–5e6, a transitional line with an explicit
transition-point model is **mandatory**, and it must carry a declared
transition-location uncertainty that brackets laminar and turbulent — the
honest sigma is ±30–50% on C_F in mid-band [PROP]. Hughes' line
C_F0 = 0.066/(log₁₀Re − 2.03)² does **not** fix this: it is still a
turbulent line, 10–12% below ITTC-57 at these Re, nowhere near the laminar
floor.

---

## 5 · Wave resistance: when waves matter and where Michell is valid

**Wave share of total, measured (repo Holtrop) on a geosim family (L/B 5,
B/T 3, C_B 0.45, C_P 0.60):**

| L | Fn 0.25 wave share | Fn 0.35 wave share |
|---|---|---|
| 0.5 m | 8.5% | 28% |
| 1 m | 10.5% | 32% |
| 2 m | 12.5% | 37% |
| 5 m | 15.1% | 42% |
| 12 m | 17.7% | 46% |

Two conclusions, both quantitative: (a) **wave resistance matters above
Fn ≈ 0.30–0.35 at every size** — by Fn 0.35 it is a third of the total and
hull form matters; (b) **at fixed Fn, the smaller hull is *more*
friction-dominated** (C_F rises as Re falls while C_W is Fn-similar), so
the small end needs the *friction* model more and the *wave* model less —
the exact opposite of where the fancy math (Michell, CFD wave capture)
spends its effort. Below **Fn ≈ 0.20**, wave share is ≲5% at every size in
the grid [THY — Michell's low-Fn asymptote R_W ~ exp(−const/Fn²) collapses
super-exponentially], and any few-percent-accurate friction+form estimate
(L0) matches anything fancier to within the noise.

**Michell thin-ship validity [THY + EXP]:** linearized on hull slope —
trustworthy for **B/L ≲ 0.10–0.15** (the Wigley benchmark is B/L = 0.10,
T/L = 0.0625), degrading fast for fuller forms. Froude range: meaningful
**0.15 ≲ Fn ≤ 0.45** — below ~0.15, R_W is negligible *and* Michell's
hump/hollow oscillations have large relative error (harmless because
absolute R_W → 0); above 0.45 sinkage/trim/transom/dynamic lift take over
(the repo's `FN_MICHELL_MAX = 0.45` is the conventional and correct bar).
Michell contains **no Reynolds physics whatsoever**, so it is *not* the
small-scale problem — a 1 m slender hull's wave pattern at Fn 0.3 is as
Michell-computable as a 12 m one's (until We contaminates it, §6). **The
small-scale L1 failure is entirely in the friction half.**

---

## 6 · Surface tension / Weber number

Physical anchors [THY]: the gravity–capillary phase speed has a **minimum
c_min = (4gσ/ρ)^¼ ≈ 0.23 m/s** at wavelength λ_m ≈ 17 mm. Consequences:

- **V < 0.23 m/s: no steady wave pattern can exist at all.** A 0.3–0.5 m
  drone loitering at 0.1–0.2 m/s generates no Kelvin wake — wave resistance
  is not small, it is *qualitatively absent*. Any L1 wave number there is
  fiction; fortunately it's also negligible.
- **Contamination criterion:** transverse wavelength λ_t = 2πV²/g should be
  ≫ λ_m. At V = 0.25 m/s, λ_t = 4.0 cm — only 2.3× capillary: the whole
  wave system is gravity–capillary and Michell (pure gravity) misprices it.
  At V = 0.5 m/s, λ_t = 16 cm (9×) — mild contamination of the shortest
  divergent components; at V ≥ 1 m/s, λ_t = 64 cm — clean. **Practical
  bar: wave-resistance predictions below ~0.5 m/s boat speed are
  We-contaminated regardless of hull size** [THY; ROT for the 0.5 m/s
  figure].
- **Model-basin corroboration [EXP/procedural]:** ITTC HSMV 7.5-02-05-01
  discusses surface-tension scale effects on wetted area and spray
  (referencing the 18th ITTC, 1987): model spray forms sheets not droplets,
  biasing WSA high as models shrink — mitigation is "larger models, higher
  speeds." Tank practice rarely trusts wave resistance from models under
  ~1.5–2 m [ROT].

---

## 7 · Wave environment vs boat size; wave-piercing limits

Deep-water wind waves: λ = gT²/2π ≈ 1.56 T². Typical bands: short chop
T 2–3 s → λ 6–14 m; SS2–3 (Hs 0.3–0.9 m, T 3–5 s) → λ 14–39 m; SS4–5
(Hs 1.9–3 m, T 7–9 s) → λ 76–126 m.

**λ/L bands and what they mean [THY + ROT]:**

| λ/L | Behavior | Who lives here |
|---|---|---|
| ≲ 0.75 | waves are "texture"; ship platforms through | KCS short of storm swell |
| ~1–2 | **pitch/heave resonance** — worst motions, slamming; wave-piercing/fine bows earn their keep here | 7–15 m craft in chop; ships in storm seas |
| 2–5 | strong contouring with phase lag; added-resistance peak | 2–7 m craft in SS2–3 |
| ≳ 5 | **pure wave-follower**: the hull rides the surface, sees the local slope as gravity | every 0.5–2 m drone in every real sea |

A 0.5–2 m drone in even the shortest real chop (λ = 6 m) has λ/L = 3–12; in
SS3, λ/L = 20–80. **Piercing is geometrically impossible — there is nothing
to pierce; the hull is smaller than the wave's radius of curvature.** The
design consequences for tiny drones: (i) motions follow wave slope (±10–15°
pitch/roll cycling continuously — a sensor-gimbal problem, not a stability
problem); (ii) the real threats are **breaking waves**: post-Fastnet-79
capsize research shows a breaking wave of height ≳ 55–60% of LOA can invert
essentially any monohull regardless of static stability [EXP model tests,
ROT as a design number] — for a 1 m drone that is a 0.6 m breaker, common
at SS3, so **inversion is a certainty over mission durations, and
self-righting + a sealed hull is mandatory, not optional** (why every
fielded small ASV is self-righting/sealed — Appendix A rows 12–17);
(iii) submergence/green water is routine — buoyancy reserve and drainage
govern, not GZ curves.

**Wave-piercing tradeoffs (for the sizes where it exists, ~5–15 m up)
[ROT + EXP lineage — Delft axe-bow work, Incat WPC practice]:** a fine,
low-reserve-buoyancy bow reduces pitch excitation and slamming in
λ/L ≈ 1–2.5 at the cost of deck wetness, reduced reserve buoyancy (deep
immersion in the rare big wave → flooding-path risk), and broaching
tendency in following seas. Governing ratios: **H/L ≲ 0.05–0.08** for
piercing to stay dry enough [ROT]; **λ/L 1–2.5** is the benefit window;
meaningless below λ/L ≈ 3 — i.e., for <2 m drones in real seas a
"wave-piercing bow" is just lost reserve buoyancy and a wetter deck [PROP,
from the λ/L geometry]. **SWATH** at drone scale: decouples motions by
removing waterplane at severe cost in wetted area (friction ×1.5–2 at
exactly the scale where friction is already ~90% of resistance) and draft;
justified only when the payload demands platform stability, never for
energy [ROT].

---

## 8 · Weight dominance: Δ ∝ L³ against everything else

**Cube law [THY]:** geosim from 12 m/6 t: 5 m → 434 kg; 2 m → 27.8 kg;
1 m → 3.5 kg; 0.5 m → 0.43 kg; 0.3 m → 94 g. Against a fixed
mission-electronics floor (battery + nav + comms + sensor ≈ 3–10 kg
[PROP]): at 2 m the floor is ~15–35% of natural displacement (designable);
at 1 m it *exceeds* natural displacement; at 0.5 m the floor is ~10–20×
natural displacement (the "hull" is a fairing around a battery). **The
payload floor sets the real minimum size, independent of hydrodynamics:
L ≈ 1.5–2.5 m for a mission-capable ASV** [PROP, from the floor estimate].

**Does ±10% mass beat ±10% hull form? Measured (repo Holtrop):**

| L, Fn | +10% displacement → ΔR | +10% beam at const. displacement → ΔR |
|---|---|---|
| 0.5–12 m, Fn 0.25 | **+4.7…+4.8%** | +2.1…+2.5% |
| 0.5–12 m, Fn 0.35 | +5.1…+5.4% | +5.5…+7.1% |

At drone cruise speeds (Fn ≤ 0.25–0.30), **mass moves resistance ~2× more
than an aggressive form change**, at *every* size — and mass is also the
quantity a drone program controls worst (payload creep, battery swaps,
biofouling, water absorption). Above Fn 0.35 form catches up — but a small
drone at Fn 0.35+ is in the transition band where the model can't price the
form change anyway.

**The environmental forces dwarf both below ~2 m (measured, repo L0 +
windage estimate):** hull R at cruise vs windage on a non-scaling
0.05–0.15 m² topside at 10 m/s wind — 0.5 m: 0.06 N vs 2–3 N (**30–50×**);
1 m: 0.5 N vs 2–8 N (4–16×); 2 m: 3.2 N vs 8–33 N (2.5–10×); 5 m: parity at
Beaufort 3, windage ahead at Beaufort 5. And SS3 orbital velocity
(0.57 m/s) equals or exceeds cruise speed below ~1 m. **Below ~1 m, a ±10%
mass change, a ±1 Beaufort weather change, or a fouling season each move
the energy budget more than the entire difference between a crude and a
perfect hull.**

**Stability scaling [THY]:** GM ∝ L (geosim), but wave *slopes* don't scale
down, so the relative stability margin shrinks; small hulls compensate with
proportionally huge beam → roll period T_roll ∝ √L: ~1 s at 1 m, ~0.5 s at
0.3 m — violently stiff, snap-rolling with every wavelet (another
gimbal/sensor argument, and why GM-maximizing at small scale is wrong —
consistent with the repo's `GM_OVER_BEAM_MAX` finding). **Planing [THY]:**
a light drone's Fn_∇ is easily >1.5 at 2–3 m/s — a 1 m, 5 kg hull at 3 m/s
(Fn 0.96) is semi-planing — and the tree has **no model for it** (no
Savitsky; `docs/SMALLCRAFT_DESIGN_REGIMES.md` refuses PLANING by name,
correctly).

---

## 9 · Hull-form sensitivity (when form matters)

| Form question | Matters strongly | Matters weakly/not | Basis |
|---|---|---|---|
| Slenderness L/B | Fn 0.30–0.50 (wave share 30–50%) | Fn < 0.20 (wave <5%); <1 m at any Fn (environment noise) | measured §5 |
| Round bilge vs hard chine | Fn > 0.5 (chine runs cleaner); roll damping at all sizes | resistance below Fn 0.35 (few %) | ROT |
| Deep-V | slamming at Fn > 0.6 in waves | displacement speeds (pure wetted-area penalty) | ROT |
| Wave-piercing bow | λ/L 1–2.5, i.e., 5–15 m craft in chop | λ/L > 3 — all <2 m drones (§7) | THY geometry |
| Catamaran vs monohull | deck area/beam per displacement; interference in Fn 0.3–0.5 when s/L < ~0.4 (±10–20% of R_W — the repo's `michell_rw(separation)` prices this) | interference below Fn 0.25 (R_W itself small) | THY (Michell) + ROT |
| Flat-bottom | build cost; planing lift | anything at Fn < 0.3 except slamming exposure | ROT |
| Very-slender twin | platform motions for sensors | energy (wetted area ×1.5–2 at friction-dominated scale) | THY |

**The form-matters window is Fn 0.30–0.50 at L ≥ 2–3 m.** Outside it —
slower, or smaller — displacement, wetted area, and mass placement are the
only levers with signal above the noise floor.

---

## 10 · Structural scaling

Hydrostatic design pressure ∝ L (draft); slamming pressure ∝ V²; panel
stress at fixed thickness ∝ pressure × (span/t)². ISO 12215-5's own scope
is 2.5–24 m (mirroring RCD — `limits.RCD_HULL_LENGTH_SCOPE_M`); below
2.5 m *the compliance tier has nothing to say*. At <2 m, required scantling
thickness falls below the **manufacturing floor** (min layup ~2–3 mm GRP;
the repo's `STOCK_PLY_THICKNESS_M` bottoms at 6 mm): structure is
gauge-limited, not load-limited, so scantling *calculus* is irrelevant — a
fixed floor + drop/handling/impact cases govern [ROT]. Structure mass
fraction therefore *rises* as L falls (floor thickness on ∝L² area against
∝L³ displacement) — another cube-law tax. **For <1.5 m drones the real
bottlenecks rank: (1) battery/payload mass fraction, (2) watertight
integrity + self-righting, (3) propulsion efficiency at low Re (prop-chord
Re is even lower than hull Re — efficiency drops from ~0.7 to ~0.4 below
chord Re ~1e5 [ROT]), (4) windage, (5) hull resistance — last** [PROP
ranking; 1, 4, 5 quantified in §8].

---

## 11 · Sensitivity (±5%, measured on repo Holtrop; conceptual where noted)

| Variable +5% | Fn 0.25 (all L) | Fn 0.35 (all L) | Fn > 0.5 (conceptual) |
|---|---|---|---|
| Speed | **+15…+19% R** | **+20…+25% R** | +10–15% [ROT] |
| Displacement | +2.4% | +2.6–2.7% | +5%+ [ROT] |
| Beam (const Δ) | +1.1–1.2% | +3.0–3.6% | strong [ROT] |
| Length (const Δ) | ~0 (friction↑ ≈ wave↓) | **−1.8…−3.1%** | ~0 [ROT] |
| LCB 1%L aft | +0.1–0.4% | ≤0.2% | trim-critical [ROT] |
| Wetted area | +3.5–4.5% | +2.7–3.5% | small |
| CG height | 0 (calm resistance) — stability/seakeeping only | | governs porpoising [ROT] |

**Dominance ordering:** speed ≫ displacement ≈ wetted area > beam > length
> LCB at cruise; beam and length rise to co-dominant only in the
Fn 0.30–0.50 window. Speed's 4:1 leverage over everything else is the
drone-line design lesson: *slow down before you reshape.*

---

## 12 · Where CFD actively misleads at small scale

The repo's L2/L3 is ship-practice RANS (fully turbulent wall treatment,
calibrated against KCS-class benchmarks). At small scale this inherits
**the same disease as ITTC-57, plus two new ones**:

1. **Fully turbulent RANS at transitional Re is wrong the same way ITTC-57
   is wrong** — it forces a turbulent boundary layer everywhere,
   overpredicting friction by up to ×2 below Re ~5e5 and by tens of percent
   through the band. A "high-fidelity" number that confirms the invalid
   empirical line is *correlated error masquerading as validation* — the
   most dangerous outcome for the flywheel. Transition-resolving models
   (γ–Re_θ / LCTM) exist but are calibration-hungry and unvalidated for
   free-surface hulls at these Re in this tree. **CFD below Re ≈ 2e6 is
   misleading unless transition-modeled and separately validated — refuse,
   don't run** [PROP; THY basis].
2. **Surface tension**: VOF without a surface-tension model cannot capture
   gravity–capillary wakes (any prediction with boat speed < ~0.5 m/s, §6);
   with one, mesh requirements at λ_m = 17 mm explode.
3. **The decision test fails anyway**: below ~2 m the decision variables
   (energy budget, survivability) are dominated by mass, windage, waves,
   and propulsor Re — a perfect calm-water R would not change the design.

**Where CFD is genuinely earning:** L ≥ 3 m and Fn 0.30–0.50
(form-sensitive, Re at least transitional-top), semi-planing 0.45–0.65 at
L ≥ 3 m (no L1 exists — CFD is the *only* tier), multihull interference
detail, and one-time commissioning/calibration of the empirical tiers at
5–15 m (the current plan).

---

## 13 · The "math doesn't matter" threshold — chosen and justified

**Criterion [PROP, grounded in repo measurement]:** a higher fidelity level
is justified only when the *expected correction* it could deliver exceeds
the product's decision-band sigma, **10%** on the energy decision variable
(Wh/NM), *and* the corrected value could plausibly cross a verdict
boundary. Justification against the candidates (1/2/5/10%): the repo
measured (`limits.WH_PER_NM_SIGMA_PRODUCT`, 2026-08-20) that the **nearest
verdict flip is 25.2% of Wh/NM away** (others 39–104%), so a ±10% band
keeps a ≥2.5× guard factor, while a paper-grade 2% GCI buys nothing any
current verdict can feel. For the drone line the same logic applies with a
*larger* effective sigma: input noise (mass ±10% → R ±5%; weather ±1
Beaufort → total force budget ±50%+ below 2 m) sets a floor **above** 10%,
so the "calculus doesn't matter" verdict below ~1.5 m is robust to any
plausible threshold choice.

---

## 14 · Main regime table

Typical mass = slender-hull natural displacement + payload-floor reality;
speed range = mission-sensible; sensitivity = hull-*form* leverage on the
decision variable.

| LWL | Typical mass | Sensible V (m/s) | Fn range | Re range | Dominant physics | Form sens. | Wave R | CFD? | Valid NavalAI tier | What breaks |
|---|---|---|---|---|---|---|---|---|---|---|
| **<0.3 m** | <0.5 kg + floor→impossible payload | <0.5 | any | <2e5 | laminar friction; capillary wake; windage ≫ hull R; wave-follower ×∞ | None | absent (V<c_min) or capillary | **Misleading** | **none** (L0 with laminar Cf only, as a toy) | everything: Re laminar, We-contaminated, Δ³ wall, no rules scope |
| **0.3–0.5 m** | 0.4–2 kg vs 3–10 kg floor | 0.3–0.8 | 0.15–0.45 | 1e5–4e5 | **laminar/early-transition friction (~90% of R)**; environment 10–50× hull R | None | <10%, We-tinged | Misleading | **none valid**; L0+Blasius+×2 margin [PROP] | ITTC-57 off ×2+; `flow_regime` refuses all points (window closes at 0.56 m); inversion certain — sealed/self-righting mandatory |
| **0.5–1 m** | 1–5 kg vs floor | 0.4–1.2 | 0.15–0.45(+) | 2e5–1.2e6 | transitional friction; wave-follower (λ/L>10); windage 4–30× | None–Low | 10–30% at Fn 0.35 | Misleading (untransitioned RANS) | **L0 + transitional line (to be built)**; L1 wave half OK ≥0.5 m/s, friction half refused/banded | ITTC-57 spread ×2.4–3.4; Fn 0.45 at 1.0–1.4 m/s squeezes the envelope; planing trivially reached with no model |
| **1–2 m** | 4–30 kg; payload floor designable at top of band | 0.5–2 | 0.1–0.45 | 6e5–3.4e6 | transition-band friction 65–90%; environment 2–15× at cruise | Low | 10–37% | Marginal (needs transition model) | L1 wave half valid; friction *reported-in-band* (repo policy); **transitional line mandatory** for honest sigma | full-turbulent window still closed (<2.6 m); ISO/RCD scope starts only at 2.5 m |
| **2–5 m** | 30–450 kg | 1–3 | 0.15–0.55 | 2e6–1.3e7 | turbulent-ish friction 60–85%; wave hump enters; environment ~1–3× at small end | **Medium** | 15–42% | Useful at Fn 0.3–0.5 for keeps | **Full L1 valid above L≈2.6 m** (window opens); L0 fine below Fn 0.25 | transition band still grazed below ~1 m/s; semi-planing >Fn 0.45 has no tier |
| **5–15 m** | 0.4–20 t | 2–6 | 0.15–0.50 | 7e6–6e7 | classic displacement regime; friction 55–85%; seakeeping λ/L ~1–5 | **Med–High** (Fn 0.3–0.5) | 15–46% | Yes — commissioning + novel keeps (current plan) | **L0/L1/CFD all in envelope** — the product's home turf | only Fn>0.45 (planing SKUs) and multihull-stability computation gaps |
| **Ship (KCS)** | 30,000 t+ | 6–13 | 0.1–0.3 | 1e9+ | turbulent friction + wave; the full ITTC-57/78 machinery, designed for exactly this | High | 20–40% | benchmark-grade | L1 + CFD (the calibration anchor) | nothing — this is the regime the toolchain was built from |

## 15 · Regime × model table

| Regime | Mathematical model | CFD? | Why |
|---|---|---|---|
| Fn < 0.20, Re > 5e6 | L0 empirical (friction + form factor + margin) | No | wave <5%, friction line exact-enough; nothing can move Wh/NM 10% |
| Fn < 0.20, Re 5e5–5e6 | L0 with **transitional Cf** + widened sigma | No | same, but friction needs the right line; CFD adds correlated error |
| Fn 0.20–0.45, Re > 5e6, B/L < 0.15 | **L1**: Michell + ITTC-57 + form factor (current stack) | Only for novel keeps / calibration | wave share 15–46%: form matters, L1 prices it to ±10% after calibration |
| Fn 0.20–0.45, Re 5e5–5e6 | Michell (wave, valid) + **transitional friction line** (to build) | Only transition-modeled, validated — else refuse | the out-of-regime friction half is the dominant error; standard RANS shares the disease |
| Fn 0.20–0.45, Re < 5e5 | Blasius laminar + Michell, ×1.5–2 friction margin [PROP] | **Refuse** | laminar; no correlation data exists; the precision is unusable anyway |
| Fn 0.45–0.65 | none in tree (sourced semi-displacement series needed) | CFD is the only honest tier at L ≥ 3 m | transom/trim/lift physics absent from L1 |
| Fn > 0.65 | Savitsky-class (not built) | CFD or model test | dynamic-lift regime |
| V < 0.5 m/s absolute | drop the wave term (report as absent/capillary) | Never | We-contaminated; below c_min = 0.23 m/s no wave system exists |

## 16 · The fidelity governor (conceptual — DO NOT IMPLEMENT from this sketch)

Implement only after review against §14/§15; every gate maps to an existing
repo seam, and the two that don't are new physics that must be built and
measured first.

```
select_hydrodynamic_model(LWL, disp, V, hull_form, H_wave, lambda_wave):
  Fn = V/sqrt(g·LWL);  Re = V·LWL/nu;  lam_t = 2·pi·V²/g

  # 0. Environment gate — before any fidelity question       [NEW PHYSICS]
  if lambda_wave/LWL > 5 or windage_est(V_wind)/R_L0 > 2 or u_orbital(H,T) > 0.5·V:
      -> ANALYTICAL  (calm-water refinement cannot change the decision;
                      flag ENERGY_BUDGET_IS_ENVIRONMENTAL)

  # 1. Wave-system existence / We gate                       [NEW PHYSICS]
  if V < 0.23: wave term = ABSENT;   if V < 0.5: wave term = CAPILLARY_CONTAMINATED

  # 2. Friction-regime gate (the drone blocker)     [seam: RE_TRANSITION_BAND]
  if Re < 5e5:            friction = LAMINAR_LINE (Blasius), sigma ×2  -> ANALYTICAL only
  elif Re < 5e6:          friction = TRANSITIONAL_LINE, sigma ±30–50%
                          CFD allowed ONLY if transition-modeled AND validated, else BARRED
  else:                   friction = ITTC-57 (+form factor)

  # 3. Froude-regime gate                              [seam: FN_MICHELL_MAX]
  if Fn <= 0.20:                      -> ANALYTICAL (L0)      # wave <5%
  elif Fn <= 0.45 and B/L <= 0.15:    -> EMPIRICAL  (L1)      # Michell in-envelope
  elif Fn <= 0.45:                    -> EMPIRICAL, sigma widened (thin-ship strain)
  elif Fn <= 0.65:                    -> LOW_FIDELITY_CFD if LWL>=3 else REFUSE
  else:                               -> FULL_CFD or REFUSE (no Savitsky in tree)

  # 4. Decision-worthiness gate                [seam: WH_PER_NM_SIGMA_PRODUCT]
  upgrade one level ONLY if expected_correction > 0.10
  AND distance_to_nearest_verdict_flip < 2.5 × that correction
```

## 17 · Explicit answers per ASV size

- **0.5 m:** detailed modeling **never** changes the decision. At every
  speed the friction line is laminar/transitional (Re ≤ 4e5 below Fn 0.45),
  environment is 10–50× hull drag, and mass beats form 2:1. Build to
  L0+Blasius with ×2 resistance margin; spend everything on sealing,
  self-righting, and battery fraction.
- **1 m:** almost never. The Fn ≤ 0.45 window ends at 1.4 m/s where Re is
  only 1.2e6; a transitional friction line changes the *number* by ±30–50%
  but the *decision* (battery size) is already margined for weather that
  moves it more. Justified only for a wake/acoustic-signature mission
  objective (CFD-only physics, outside all current tiers).
- **2 m:** the crossover. At 1–2 m/s (Fn 0.23–0.45, Re 1.7–3.4e6) — the
  transition band's upper half; a transitional line tightens sigma from
  ±40% to ±15% [PROP] — this *can* cross the 10% bar for endurance-critical
  missions. CFD still not decision-worthy unless transition-modeled.
- **5 m:** L1 fully valid above 1.2 m/s. Detailed modeling (a CFD keep)
  justified in Fn 0.30–0.50 (2.1–3.5 m/s) where form sensitivity is Medium
  and wave share 25–42%; below 1.5 m/s (Fn < 0.21) L0 is within a few % of
  anything.
- **7 m:** as 5 m with a wider window (Fn 0.30–0.50 = 2.5–4.1 m/s);
  multihull interference (if cat) worth one Michell separation sweep, CFD
  only for a novel keep.
- **12 m:** the product's home. CFD per the current plan (commissioning +
  calibration + novel keeps). Below 2.7 m/s (Fn 0.25) empirical is within
  the product sigma of anything fancier — do not spend CFD there.

## 18 · Minimum sensible maritime-drone size — the four-wall intersection

| Wall | Bites below | Basis |
|---|---|---|
| Full L1 validity window (Re ≥ 5e6 ∧ Fn ≤ 0.45) | **2.6 m** | [THY, derived §4] |
| Payload floor vs Δ ∝ L³ (3–10 kg electronics) | **1.5–2.5 m** | [PROP §8] |
| Sustained way vs SS2–3 orbital + Beaufort-4 windage (needs ≥1–1.5 m/s at Fn ≤ 0.35) | **~2 m** | [THY §8] |
| Breaking-wave inversion (0.55–0.6·LOA breaker common at SS3) | design response (self-righting), not a size fix, below ~4 m | [EXP/ROT §7] |
| Wired-policy L1 envelope non-empty | 0.56 m | [THY §4] |

**Recommendation: 2.0–3.0 m LWL, ~30–150 kg, cruise 1–1.5 m/s (Fn
0.20–0.30, Re 2–4.5e6)** — inside the Michell envelope, top of the
transition band (honest with a transitional friction line + declared
sigma), payload-feasible, able to make way at SS3, self-righting by design.
A 0.5 m drone is a sensor float, not a vessel-design problem.

## 19 · Repo impact

- `limits.RE_TRANSITION_BAND (5e5, 5e6)` — **confirmed** by ITTC
  7.5-02-05-01's Re < 5e6 stimulation clause; the repo's "declared, not
  transcribed" caveat can now cite that procedure for the ceiling. The
  band's product consequence is sharpened: window-closing lengths 2.6 m /
  0.56 m.
- `resistance.flow_regime` — the policy (refuse < 5e5, report in band) is
  right for the current ≥4 m box; **inadequate for any drone line at
  1–2 m**, where "reported, not refused" spans the entire operating
  envelope. The owed "measured decision about the bar" becomes mandatory at
  drone go-ahead.
- **Defect found and FIXED 2026-08-19** (`navalai/holtrop.py`):
  `holtrop.envelope_violations` carried **no Reynolds clause** — every band
  was dimensionless in hull proportions, so nothing about *size* was
  checked, and `holtrop.total` returned `valid=True, tier="L1H"` for a
  0.5 m hull at Re 2.3e5 that `resistance.flow_regime` refuses. The L1H
  badge could contradict L1. Fixed: the envelope now takes `re` and refuses
  below `RE_TURBULENT_MIN` (= `RE_TRANSITION_BAND[1]`, an alias not a
  second number), verified in both directions.
- `extrapolate.py` (ITTC-78) — unaffected at ship scale, but its C_R
  Re-invariance assumption is *maximally* violated for model↔drone lambda;
  do not use it to "extrapolate" drone predictions from larger-hull
  calibrations.
- `PLM.md` §0.5 drone descope — the stated reason ("no valid friction
  line") was correct and is now quantified; friction is only wall 1 of 3,
  so a transitional friction line alone does not un-block the line. The
  §0.5 row now carries the numbers and the un-block list.
- `limits.RCD_HULL_LENGTH_SCOPE_M (2.5, 24)` — the entire rules tier has
  nothing to say below 2.5 m; the drone line needs a different rulebook.
- `limits.WH_PER_NM_SIGMA_PRODUCT = 0.10` — adopted as the
  fidelity-worthiness threshold (§13); generalizes to the governor's
  gate 4.

## 20 · "Where calculus doesn't matter" — quantitative summary

| Row | Regime | Quantitative argument |
|---|---|---|
| 1 | Any size, Fn ≤ 0.20 | wave share <5–8% (measured, §5); L0 friction+form is within ~3% of L1/CFD on the total — under the 10% sigma by 3× |
| 2 | V < 0.5 m/s absolute | wave system capillary-contaminated (λ_t ≤ 16 cm vs λ_m 1.7 cm) and <10% of R anyway; below 0.23 m/s it does not exist [THY] |
| 3 | L < 1 m, all speeds | environment/hull-R ratio 4–50× (windage) and orbital u ≥ cruise V; form deltas (±5% B → ±1–3% R) are 10–100× under the operating noise floor |
| 4 | L < 2 m mass trades | ±10% mass = ±5% R at cruise ≥ 2× any legal form change; mass is also the uncontrolled input — model the *weight budget*, not the wave pattern |
| 5 | Structure < 2 m | gauge floor > required scantling: the safety factor is set by handling/impact, not calculated loads |
| 6 | CFD in 5e5 < Re < 2e6 | fully-turbulent RANS reproduces ITTC-57's own bias (up to ×2 vs laminar): higher cost, same wrongness — worse than not running it |

**Where calculus *does* matter:** Fn 0.30–0.50 at L ≥ 2.6 m (form moves
3–7% per 5% parameter against a 30–46% wave share — reaches the 10% bar),
semi-displacement/planing at any product size (no valid cheap model exists
— the honest gap), and the transitional friction line itself for the
1–2.5 m band (a ±40%→±15% sigma tightening, the single highest-value piece
of new physics for the drone line).

---

## Appendix A · The independent evidence sweep

Run blind to the study above; gathered published/experimental evidence
only. Fn/Re marked (calc.) are computed from published length/speed with
ν ≈ 1.1–1.2e-6 m²/s; everything else is as published.

### A.1 Findings table

| # | Source / craft | Size | Speed / Fn / Re | What was measured / established | Implication for the CFD-usefulness boundary |
|---|---|---|---|---|---|
| 1 | **ITTC 7.5-02-02-01 Resistance Test** (rev. 04, 2017) — [ittc.info PDF](https://www.ittc.info/media/8001/75-02-02-01.pdf) | ships' models, tank practice | ITTC-57 line | "The model should generally be as large as possible for the size of the towing tank"; blockage corrections validated only for **3.5 m < L < 9 m** models; turbulence stimulation must be reported for every test | Standard basin practice implicitly assumes multi-metre models; a 0.5–2 m ASV is *below* the size window the validated correction machinery was built for |
| 2 | **ITTC 7.5-01-01-01 Ship Models** (rev. 04, 2017) — [ittc.info PDF](https://www.ittc.info/media/9571/75-01-01-01.pdf) | model manufacture standard | studs 1.6–3.2 mm dia. at 12–25 mm; wires 0.5–1.0 mm at 5%Lpp | Explicit warning: there are "typical combinations of model/appendage length and Froude number where **most of the model would remain in the laminar flow regime**" even with care | The ITTC itself flags short-hull/low-Fn combinations as a laminar-regime problem zone — exactly the operating point of a 1–2 m displacement ASV |
| 3 | **ITTC 7.5-02-05-01 HSMV Resistance Test** — [ittc.info PDF](https://ittc.info/media/1279/75-02-05-01.pdf) | HSMV models | threshold **Re = 5×10⁶** | Below Re 5e6 turbulence must be artificially stimulated; trip wires not recommended on high-speed models; sand strips preferred on slender catamarans | Re = 5e6 at displacement-typical Fn ≈ 0.35 requires **L ≈ 3 m** (calc.). A 1 m hull would need ~5.7 m/s (Fn ≈ 1.8) to reach it — the entire 0.5–2 m displacement band sits below the turbulent-flow threshold |
| 4 | **Toki, geosim correlation-line analysis**, J. JASNAOE — [J-Stage PDF](https://www.jstage.jst.go.jp/article/jjasnaoe/8/0/8_0_71/_pdf) | geosim models **2.26–7.53 m** | model Re ~1e6–1e7 | Residual-resistance deviations **systematically positive for the smallest models (2.26, 2.71 m)**, negative for the largest; Fr < 0.11 data rejected outright for scatter | Even professional basins see systematic small-model bias at 2–3 m and unusable scatter at low speed |
| 5 | **Klaka (2022), roughness on a 1 m model yacht** (IOM class) — [onemetre.net PDF](https://onemetre.net/race/surface%20finish/Klaka%20roughness%20for%20modelyachts-v8-full%20version.pdf) | 1.0 m hull | **Re ≈ 4e5–2e6** — "close to, or within, the laminar flow range" | Ship/yacht roughness-friction formulae "are **not applicable** to model sailing yachts"; whether flow is laminar depends on *environmental* turbulence (Tu 0.08%→3% moves transition Re from 2.8e6 to 1e5) | At 1 m the *flow regime itself is indeterminate* — it flips with ambient turbulence. Any single-regime CFD is wrong part of the time; predictions carry irreducible environmental uncertainty |
| 6 | **Drag measurements on an International One Metre yacht** — [radiosailingtechnology.com](https://radiosailingtechnology.com/index.php/hulls/drag-measurements-on-an-international-one-metre-yacht) | 1.0 m | Re 5e5 @ ~1.5 kn; 1e6 @ ~3 kn | Measured skin friction **≥30% higher than anticipated** from standard lines; surface tension noted as affecting waterline forces and wave formation | Direct measured failure of standard friction prediction on a 1 m hull; first appearance of Weber-number contamination |
| 7 | **Capillary/scale-effect literature** — [Annual Reviews](https://www.annualreviews.org/doi/pdf/10.1146/annurev.fluid.32.1.241); [Re/We scale-effect analysis](https://arxiv.org/pdf/2002.04531) | — | capillary length ≈ 1.5–1.7 cm | Surface tension negligible only for wavelengths several × 1.7 cm; small free-surface experiments require explicit Re/We screening | Divergent/short wave components and spray sheets on sub-metre hulls are in the gravity-capillary band — the wave pattern is not Froude-scalable |
| 8 | **Insel & Molland (1992) / Molland et al. (1994) Southampton catamaran series** — [RINA paper](https://www.researchgate.net/publication/283995317_An_investigation_into_the_resistance_components_of_high_speed_displacement_catamarans), [Ship Science Rep. 71](https://www.researchgate.net/publication/284260790_Resistance_experiments_on_a_systematic_series_of_high_speed_displacement_catamaran_forms_Variation_of_length-displacement_ratio_and_breadth-draught_ratio) | 1.6 m NPL-derived demihulls | Fn 0.2–1.0; s/L 0.2–0.5 | Hull-interference resistance real, measurable, spacing-dependent; strongest **Fn 0.4–0.6**; optimum s/L ≈ 0.3–0.4 | Interference is a genuine wave-making effect in exactly the Fn range where 1.5–3 m cat ASVs cruise — and even these 1.6 m tests needed turbulence stimulation for the friction baseline |
| 9 | **Delft 372 catamaran benchmark** — [particulars](https://www.researchgate.net/figure/Delft-Catamaran-main-particulars-372-original-model-and-conditions_tbl1_259621572), [interference CFD validation](https://www.sciencedirect.com/science/article/abs/pii/S0029801821001220), [calm-water CFD validation](https://neptech.co/wp-content/uploads/2025/06/CFD_Report-DELFT_372-Calm-Water-EN.pdf) | Lpp = 3.0 m | Fn 0.2–0.8; Re up to ~1e7 (calc.) | The community's standard small-cat validation case: RANS resistance, sinkage, trim repeatedly validated to ~2–5% against tank data | **3 m is the demonstrated size at which model test + RANS agree reliably — the best-documented lower anchor of "CFD works and is worth doing"** |
| 10 | **Twin-hull USV, tank + STAR-CCM+** — [J. Marine Eng. (Iran)](http://marine-eng.ir/browse.php?a_id=1063&sid=1&slc_lang=en) | small twin-hull USV | 2 displacements × 4 speeds | CFD vs tank "eligible match"; max-payload weight growth raised total resistance only 17% | RANS matches tank for a small cat USV *when tested properly*; displacement changes matter more than hull-line detail at this size |
| 11 | **Parametric optimal USV hull design**, Ocean Eng. 2021 — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0029801821008660); [trimaran NACA study](https://www.researchgate.net/publication/374371982_Numerical_Study_of_Resistance_Trimaran_Unmanned_Surface_Vehicle_Based_on_NACA_Foil) | USV scale (metres) | design Fn range | Optimised hulls claim wave-resistance reductions to ~50% at high speed; trimaran side-hull placement changes resistance by tens of % | Wave-making/configuration is where CFD finds *large* gains at USV scale (Froude-governed, not Re-governed). Mostly CFD-only claims — treat as upper bounds |
| 12 | **WAM-V 16 (RobotX standard craft)** — [Robonation specs](https://robonation.org/app/uploads/sites/2/2021/07/2022-RobotX-16-WAM-V-Specs.pdf) | ~4.9–5.3 m cat, 344 kg | to 11 kn → Fn ≈ 0.8, Re ≈ 2e7 (calc.) | Design solution is **mechanical wave adaptation** (inflatable pontoons + articulating suspension), not optimised rigid hull lines | The flagship 5 m research USV class solved seakeeping by *suspension* — conceding that at this size wave response, not calm-water drag, is the binding constraint |
| 13 | **Clearpath Heron (ex-Kingfisher)** — [manual](https://oceanai.mit.edu/herons/docs/Heron_USV_UserManual.pdf) | 1.35 m cat, 28 kg | 3.3 kn max → Fn ≈ 0.47, Re ≈ 2e6 (calc.) | Design driven by portability, shallow draft, anti-fouling; no resistance validation published | Sits where cat interference peaks and friction is transitional — yet nobody optimised, because the power budget is payload/hotel loads and endurance, not drag lines |
| 14 | **Liquid Robotics Wave Glider** — [how it works](https://www.liquid-robotics.com/wave-glider/how-it-works/), [speed prediction](https://robotics.usc.edu/publications/downloads/pub/736/), [dynamics ID, JMSE 2022](https://doi.org/10.3390/jmse10040520) | ~3 m float | 0.8–2.0 kn → Fn ≈ 0.14, Re ≈ 2e6 (calc.) | Achieved speed best predicted from **significant wave height (R = 0.61)** — an environmental regression, not a resistance curve; survived hurricanes | At ~3 m/2 kn, speed-through-water is an environmental variable; CFD is useful for the *propulsor*, not the hull lines |
| 15 | **Saildrone Explorer** — [hurricane missions](https://www.saildrone.com/missions/atlantic-hurricane-monitoring), [SD 1045 record](https://www.saildrone.com/news/guinness-record-highest-windspeed-recorded-by-usv-hurricane-sam) | 7 m monohull | avg 3 kn (Fn ≈ 0.19); 34.5 kn peak surfing | Engineering went to a wing surviving >110 mph and **self-righting**; survived a Cat-4 hurricane eye | The most successful long-endurance ASV line optimised survivability and station-keeping; 3 kn average was accepted, not fought |
| 16 | **Sailbuoy / Microtransat record** — [Microtransat](https://en.wikipedia.org/wiki/The_Microtransat_Challenge), [microtransat.org](https://www.microtransat.org/), [sailbuoy.no](https://sailbuoy.no/the-sailbuoy-technology) | ≤2.4 m class; SB Met = 2.0 m, 60 kg | ~1–2 kn (Fn ≈ 0.1–0.2, Re ≈ 1e6 calc.) | **>30 Atlantic attempts, all but one failed** (2010–2018); the sole finisher is a ballasted, self-righting, near-unsinkable 2 m boat that "floats on 12 m waves like a cork" | The starkest field statistic in the band: at ≤2.4 m in real ocean, attrition ~97%, and the winner traded hydrodynamic refinement for robustness |
| 17 | **SERDP surf-zone USV program** — [serdp-estcp.mil](https://serdp-estcp.mil/projects/details/d9b9ecd5-c2a1-41cb-9798-8c1ac0d9eaf9) | 1.8 m/10 kg; 3 m/55 kg | SSV ~10 m/s → Fn ≈ 2.4 (planing) | Iterated hull forms for breaking-wave survival: converged on **semi-submersible, self-righting** (1.8 m) and **wave-piercing, self-righting** (3 m); conventional fast hulls failed in surf | Under the harshest relative-wave conditions, sub-3 m design converges to submergence-tolerant, self-righting forms — reserve buoyancy and inversion recovery replace hull-line optimisation |
| 18 | **Wave-piercing hull literature** — [UCL wet-deck slamming](https://discovery.ucl.ac.uk/id/eprint/10076973/1/babak%20Wet-deck%20Slamming_18June2019-accepted%20copy.pdf), [centrebow design](https://www.researchgate.net/publication/280562198_CENTREBOW_DESIGN_FOR_WAVE-PIERCING_CATAMRANS), [USNI 1997](https://www.usni.org/magazines/proceedings/1997/november/achilles-heel-wave-piercer-hull-form) | Incat-class WPCs + models | — | Wave-piercers need a **centrebow purely for reserve buoyancy** to prevent deck-diving; deep bow submergence → large slam loads and whipping | The concept's failure mode is loss of reserve buoyancy under relative-wave excursions; on a 1–2 m ASV it degrades to a semi-submersible unless designed to *accept* submergence and self-right |
| 19 | **γ–Re_θ transition modelling** — [Menter/Langtry calibration](https://arc.aiaa.org/doi/10.2514/6.2009-1142) | CFD methodology | below Re ~ a few ×1e6 | Fully-turbulent RANS "overpredicts drag in laminar regions and cannot reproduce the transition location"; model-scale ship flow is "in between" regimes | For sub-3 m hulls credible CFD is *transition-resolving* CFD — and its boundary condition (ambient Tu, row 5) is unknowable at sea. This bounds achievable accuracy regardless of mesh |

### A.2 Synthesis — what the evidence (not the theory) says

**(a) Minimum size where hull-form optimisation measurably pays:**
~2.5–3 m at Fn ≳ 0.3; the payoff is Froude-governed (wave-making,
multihull configuration), never friction. Validated to 2–5% at 3 m
(Delft 372) — *strong evidence*. Between 1.5 and 3 m, wave/configuration
CFD can rank variants if the craft transits at Fn 0.35+, but the friction
half of any absolute prediction is unreliable — *some evidence*. Below
~1.5 m, no published case of a validated hull-form optimisation delivering
a field-confirmed gain; the careful 1 m study found predictions off ≥30% —
*strong evidence of absence at ≤1 m; thin between 1 and 1.5 m*.

**(b) Where calm-water resistance stops being the design driver:** for
endurance/ocean missions, everywhere below ~7 m; for all missions, below
~2.5 m in unsheltered water. Every long-endurance success (Wave Glider,
Sailbuoy, Saildrone) optimised energy capture, self-righting, and
submergence tolerance and *accepted* low speed; Microtransat's ~97%
attrition is a field statistic, not a theory — *strong evidence*. The
useful simulations at these sizes are seakeeping/slamming/self-righting and
propulsor design, not calm-water resistance — *some evidence*.

**(c) Where model-scale/CFD predictions are shown unreliable:** below
Re ≈ 5e6 (~3 m at displacement Fn) per ITTC's own procedures and the geosim
bias record; severely below Re ≈ 1–2e6 (~1 m: ≥30% measured friction error,
regime flipping with ambient turbulence, surface-tension contamination) —
*strong at the anchors (3 m validated; 1 m broken); the exact crossover
between them is interpolation — some evidence*.

**Caveats:** the "≥30% friction excess" figure is from a
measurement-based but non-peer-reviewed source; Southampton-series model
length (1.6 m) is cited from secondary sources; USV optimisation percentage
gains (row 11) are mostly CFD-only claims — upper bounds.

---

## Honest uncertainty

The 5e5/5e6 band edges are classical flat-plate values, not hull-specific
[THY/ROT]; the 55–60%-LOA breaking-wave inversion figure is model-test
lineage applied outside its yacht-size support [ROT]; the payload floor
(3–10 kg) and windage-area floor (0.05–0.15 m²) are engineering estimates
[PROP]; small-USV seakeeping literature is thin — the λ/L band edges (5,
2.5) are geometry-argued, not experimentally mapped for <2 m craft; the
transitional-line sigma tightening (±40%→±15%) is a projection, not a
measurement. The two studies' agreement at the 2.6–3 m floor is the
strongest single result: it was reached independently from theory and from
the published record.
