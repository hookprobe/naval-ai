# RESEARCH RECORD — airborne wind traction (WindWing)

> **Role: RESEARCH / EVIDENCE.** What the airborne-wind literature and the
> marine-kite operators actually report, what cross-checks, and what is a vendor
> claim. The *plan* — preconditions, tier ladder, the LOAD gate, where the AI is
> not allowed — is `docs/BUILD-PLAN.md` §WindWing. The regulatory consequence is
> `docs/research/COMPLIANCE.md` §3.
>
> **Every marine-kite figure below is a vendor or press claim, not a
> measurement this project made.** The Airseas 20% → 16% gap is quoted precisely
> because it shows what such claims are worth.

---

## 1 · Makani — open, pledged, and most valuable for its failure data

**X issued a worldwide patent non-assertion pledge alongside the
open-sourcing**, so the freedom-to-operate caution is much smaller than feared
*for Makani specifically*: anyone may use the patents, designs, software and
research without fear of reprisal. It does **not** extend to Airseas, SkySails
or Beyond the Sea, who are live, commercial and patenting — a launch/recovery
mechanism review is still owed before commercialising hardware.

What is in the repository (`github.com/google/makani`, archived read-only
Nov 2022, Bazel, Debian Stretch/Docker): a flight simulator; `control/` with
separate hover, transition-in, crosswind and off-tether controllers;
`analysis/control/crosswind.py` generating the crosswind inner-loop gains;
`avionics/` firmware for winch, ground station, motors, servos, GPS; `config/`
producing JSON and compile-time C structs; `database/` aerodynamic tables;
`vis/` OpenGL visualiser. Avionics firmware is *"potentially not in a buildable
state"* after third-party code removal.

**What to take:** the *architecture* (separate controllers per flight phase),
the aero-database and configuration patterns, and above all the **failure
data**. The DOE review names two contributors to underperformance: worse than
expected aerodynamic performance of the **wing/tether system**, and inability to
fly circles as small as desired. Makani's own stated recommendation is to
iteratively verify aero performance gains against flight data and not
overestimate projected power — which is this repository's culture already.

**What not to take:** the M600 architecture. Onboard generation, 8 turbines,
~26–28 m span, 600 kW, conductive tether — that is a different problem. A boat
wants *traction*, and converting wind → generator → battery → inverter → motor →
propeller to deliver a force the tether was already delivering mechanically is a
chain of efficiencies paid for nothing.

**Not verified:** the repository was not cloned or built. Whether
`analysis/control/crosswind.py` is usable against a soft marine kite rather than
a rigid wing is unassessed.

---

## 2 · Loyd (1980) — the governing physics, and it is algebraic

The right shape for this repo's L0 cost class:

```
crosswind power     P ∝ ρ A v_w³ · C_L (C_L/C_D)²   [P_max = (2/27) ρ A v_w³ C_L(C_L/C_D)²]
crosswind traction  F ∝ ρ A v_w² · C_L (C_L/C_D)²
optimal reel-out speed = v_w / 3
static (parked)     F = ½ ρ A v_w² C_R
```

**A cross-check that passes.** The crosswind-over-static traction ratio is
≈ (4/9)(C_L/C_D)²·(C_L/C_R). At a soft-kite L/D ≈ 5 this gives roughly 10×, and
Airseas reports up to *"10× the traction of static flight"* from dynamic
figure-eight flying. Independent theory and a commercial measurement agree
within the precision either is quoted to. **That is the only quantitative
cross-check available before any code is written**, and it is the reason W0's
acceptance bar can be stated at all.

---

## 3 · Marine reality, from operators rather than models

| Source | Datum |
|---|---|
| Silent 60 catamaran | **9 m² kite, engines off, 4–5 knots** |
| Beyond the Sea | ~**100 kg/m²** traction in test (≈ 1 kN/m²); 100 m² automated SeaKite on the fishing vessel *Cap Kersaint*, operational 2026; 400 m² in development |
| Airseas Seawing | 1 000 m², flies to ~300 m, figure-eight at > 100 km/h, 100% automated; **projected 20% from modelling, 16% from trials** |
| LibertyKite | 40 m² sized for vessels over 12 m with high displacement |
| TU Delft (Eijkelhof, Rossi, Schmehl, *Wind Energ. Sci.* 11, 1287, 2026) | 150 m² MegAWES at 15 m/s: **circular** 1.85 MW at 2.94 MW/km² (best power, smallest area); **figure-eight down-loop** better power quality, peak-to-average **3.85** |
| Bristol / Kitemill KM1 | combining flight control with winch control ↑ simulated power **47%** vs an existing reel-out strategy |
| Fagiano et al., *Annual Rev. Control* / arXiv 2401.05950 | 360 m² kite on a moored spar: flight pattern is **insensitive** to platform motion, but **tether-force oscillation frequency can approach platform resonance**, causing fatigue. The proposed fix acts on the **path planner** |
| SkySails / Airseas (cargo) | 10–20% and ~16% fuel saving respectively — **both from cargo ships**, where the kite is small relative to displacement on a great-circle ocean route. **Transferring them to a 14 m catamaran is unsupported by anything in these sweeps** |

### The sizing consequence, and it inverts the instinctive build order

Take a 14 m / 6.8 t catamaran. At Beyond the Sea's reported ~1 kN/m², a 25 m²
kite develops on the order of **25 kN ≈ 2.5 t — about 37% of displacement** — as
a dynamic, oscillating vector applied above deck near the bow. The Silent 60
datum points the same way from the other side: 9 m² moved a far heavier boat at
4–5 kn, so the useful sizes for a 6.8 t cat are in the **10–25 m²** band, not
the 40–60 m² an early sketch proposed.

**Caveat on the 25 kN figure, stated because it will otherwise be quoted as a
design load:** ~1 kN/m² is a peak from a vendor test at an unstated wind speed
and unstated flight mode. It is used as an order-of-magnitude argument for gate
*ordering* only.

Two consequences:

1. **The first WindWing gate is a LOAD gate, not a power gate.** "Does the
   vessel survive the kite" is answerable before "how much does the kite pull",
   it kills bad configurations early (the Fitness=∞ fast-reject pattern this
   repo already uses), and it is the question a customer is actually buying an
   answer to.
2. **Peak-to-average tether force is the structural sizing driver**, which makes
   this project's objective *different from every AWE company's*. They maximise
   cycle-averaged power; a boat wants mean thrust subject to a peak-load
   ceiling. TU Delft's result — circular wins power, figure-eight down-loop wins
   peak-to-average — may therefore **resolve the opposite way for a boat than
   for a power plant.** That is a real and defensible divergence, and it falls
   out of having a different objective, not out of better physics.

---

## 4 · Control architecture, from the literature

The three-level split matches the published systems:

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

**On the one-wire / two-wire question:** a single load-bearing tether with an
onboard flight computer and a free-spinning swivel is the architecture to
investigate first, because it makes the rotating interface trivial. SkySails'
published approach — steering lines to a control pod containing the autopilot
and sensors, driven by a tooth-belt actuator — is the proven marine variant, and
Airseas' pod carries three actuators. **Unlimited 360° rotation is not a
requirement**; it is a consequence of picking a circular pattern, and the
pattern should be an optimiser output anyway. Treat continuous rotation as a
*cost* (twist management) the trajectory optimiser pays, not as a goal.

---

## 5 · Where the defensible innovation is, and what it needs first

> **Choose the kite trajectory against the vessel's dynamic response, not
> against power.**

No airborne-wind company has the vessel's RAOs. No naval-architecture tool has
the kite. The offshore-platform result (Fagiano et al.) gives the mechanism:
tether-force oscillation can collide with hull resonance, and the fix belongs in
the path planner. For a boat the constrained problem is

```
maximise   mean forward thrust
subject to peak tether tension  ≤ structural limit
           heel under kite load ≤ category limit (limits.CATEGORY_TABLE)
           excitation period    away from roll and pitch natural periods
           trim / list          within limits.TRIM_LIMIT_DEG / LIST_LIMIT_DEG
```

**This cannot be evaluated today**, and the preconditions are recorded as work
items in `docs/BUILD-PLAN.md` §WindWing rather than assumed here. Writing the
trajectory optimiser before they exist would produce a confident number with
nothing behind it.

---

## 6 · Sources

Makani — [repository](https://github.com/google/makani) ·
[TU Delft on the open-sourcing](https://www.tudelft.nl/en/2020/lr/13-years-of-makani-airborne-wind-energy-knowledge-available-open-source) ·
[X patent non-assertion pledge](https://spectrum.ieee.org/exclusive-airborne-wind-energy-company-closes-shop-opens-patents) ·
[The Energy Kite report](https://archive.org/stream/theenergykite/20200901_MVP_TheEnergyKite_pt1_pt1words_djvu.txt)

Theory and control —
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

Standards for a kite-rigged craft —
[EN ISO 12217-2 (sailing craft)](https://ce-marking.help/directive/recreational-craft/standard/5843/en-iso-12217-22017)
