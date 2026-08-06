# The pressure-force oscillation is a TANK MODE — but not the seiche

**Measured 2026-08-06 on this Mac.** Tool: `scripts/tank_resonance.py`.
Gate test: `tests/test_tank_resonance.py`.

    python scripts/tank_resonance.py runs/val_coarse5 --surface

## The question

`runs/val_coarse5` (symmetric KCS, `_NX_BASE` 57, `--n-layers 5`, 230725 cells,
19.81 s = 1.33 flow-throughs, mesh clean: 0 zero-volume cells, 0 wrongly
oriented faces, max skewness 8.93, Phase-1 volume constant to 7e-5) splits into
two halves that behave completely differently:

- **Viscous**: steady at 1.22-1.36x ITTC-57 for the whole run. A KCS form
  factor (1+k) of 1.10-1.15 is exactly that band, so the wall model is right.
- **Pressure**: oscillates between 0.27x and 5.92x the expected 20.8 N, and
  passes THROUGH ZERO into thrust. Per-second means: -7.07, -1.51, -29.23,
  -50.30, -59.35, -39.87, -5.78, **+14.42**, -10.53, -47.83, -62.05, -71.83,
  -40.69 N. No real hull drag does that.

The ship-wave period at Fn 0.26 is 2*pi*U/g = 1.41 s, so the oscillation
(~6 s) is domain-scale. The hypothesis on record was a **longitudinal seiche**,
T = 2L/sqrt(g h) = 7.75 s for this 32.75 m x 7.28 m tank.

## The verdict

**It is a tank mode, and the seiche formula is the WRONG tank mode.**

The disturbance is a free surface gravity wave whose WAVELENGTH the domain
selects (~11.5 m, on tank mode n=6, lambda = 2L/6 = 10.92 m) running UPSTREAM
against the stream and reflecting off the inlet and outlet. What the hull sees
go past is that wavelength **Doppler-shifted**:

    T = lambda / ( c(lambda) - U )        c from the full dispersion relation

That is a different prediction from `2L/sqrt(gh)` in the one way that matters:
it MOVES WITH SPEED. `2L/sqrt(gh)` does not.

## The deciding measurement: the same tank at two speeds

`make_case.py` derives tank depth as `max(1.0*Lwl, 1.5*pi*U^2/g)`, and at both
speeds the first term wins — so halving U leaves the domain **bit-identical**
(L = 32.7537 m, h = 7.2786 m) and changes only the flow. Depth could not be
swept: the generator exposes no depth knob, and it is not this work's file.

| run | U (m/s) | mesh | record | lambda measured | T measured | lambda/(c-U) | 2L/sqrt(gh) |
|---|---|---|---|---|---|---|---|
| `runs/val_coarse5`   | 2.196 | 230725 cells | 19.79 s | **11.44 m** | **5.53 s** | 5.64 s (−1.9%) | 7.75 s |
| `runs/seiche_u_half` | 1.098 | 102422 cells | 23.96 s | **11.50 m** | **3.67 s** | 3.66 s (+0.3%) | 7.75 s |

Three things fall out of those two rows:

1. **The wavelength did not move.** 11.44 -> 11.50 m across a factor of two in
   speed AND two different meshes (background scale 1.0 and 0.7). It is the
   DOMAIN that sets it, not the ship and not the cell size.
2. **The period did move**, and by exactly the Doppler shift — 0.3% and 1.9%,
   with no fitted parameter anywhere.
3. **The still-water seiche predicts 7.75 s at both speeds** and matches
   neither: 40% high at full speed, 111% high at half.

The measurement is of the FREE SURFACE, not of the forces: `alpha.water * V`
integrated per x-bin over the whole tank at every saved time, then
`eta'(x,t) = A(x) cos(wt) + B(x) sin(wt)` fitted after removing the snapshot
mean (which cancels the hull's own displaced volume and the steady Kelvin
pattern). Two independent checks confirm it is a real gravity wave rather than
a numerical mode: the measured intrinsic phase speed matches the dispersion
relation for the measured wavelength to **+0.9%** and **−0.2%**, and the
wavelength is resolved by **80** free-surface cells on the fine mesh
(`fs_dx` 0.14366 m) and **56** on the coarse one (0.20471 m) — nowhere near
the cell size, so it is not a grid artefact, and the two counts differ by 1.4x
while the measured wavelength differs by 0.5%.

Integrating rather than contouring is deliberate. `scripts/render_case.py`
records that ParaView CANNOT contour this mesh — the z-only `refineMesh` rounds
leave hanging-node polyhedra. A volume integral does not care.

## Why Fn 0.26 is the worst case

T(lambda) = lambda/(c−U) has a minimum, and it is where `dT/dlambda = 0`, i.e.
at c = 2U — precisely where the GROUP velocity c/2 equals U and the wave's
energy holds station in the tank. There,

    lambda_block = 8 pi U^2 / g          T_min = 8 pi U / g = 4 ship-wave periods

At Fn 0.26 that is lambda 12.35 m against a tank mode at 10.92 m: **they nearly
coincide**, so the wavelength the tank selects is also the one whose energy
cannot drain either way. That is why the oscillation is so clean and so violent
at the design point. At half speed they are 3.09 m and 10.92 m apart, and the
pressure history correspondingly refuses to yield a single period at all
(41.7% of the detrended variance, below the 50% bar).

The curve is also FLAT near its minimum: at Fn 0.26, tank modes n=4..8 predict
5.76 / 5.64 / 5.65 / 5.75 / 5.94 s. **No 19.79 s record separates them**, and
the tool reports the FAMILY, never a mode number.

## What was refuted, and how

- **Still-water seiche, T = 2L/sqrt(gh) = 7.75 s.** Refuted by the speed
  sweep (it cannot move with U, and the measurement moved 5.53 -> 3.67 s), and
  independently by the mode shape: the standing score is 0.34 and 0.17 where a
  standing wave is 1. *Caveat, stated because it cuts against the argument: a
  tank mode in a CURRENT is not a clean standing wave either — its upstream
  and downstream components share a frequency but not a wavelength — so a low
  standing score refutes the still-water form specifically, not "a tank mode".*
- **Transom ventilation** (the other candidate on record; the KCS transom
  measures 100% wetted where it should ventilate). Refuted: the wave is
  coherent over the ENTIRE tank including 10 m ahead of the bow, its wavelength
  is speed-independent, and it obeys the free-surface dispersion relation.
  Nothing local to the stern does any of those three.
- **A first, wrong reading of this same data: "the trapped band, lambda =
  8 pi U^2/g".** At Fn 0.26 the measured wavelength (11.44 m) sits 7% from the
  blocking wavelength (12.35 m) and c/U came out 1.94 against a predicted 2.00,
  which looked conclusive. It was a coincidence of the design point: that model
  predicts lambda scaling as U^2, so half speed should have given 3.09 m, and
  the measurement gave 11.50 m. **One speed was not enough to tell the two
  apart, and the second speed cost four minutes of compute.**

## What the record could NOT say

A period needs cycles. Every other run in the repository was checked and every
one of them REFUSES:

| run | record | why no period |
|---|---|---|
| `runs/beach` | 10.38 s, 0.70 flow-throughs | best sinusoid explains 33.1% (bar 50). Its leading candidate at 5.63 s needs 11.3 s of record; an unbounded FFT returns 10.40 s — the record length |
| `runs/wigley` | 9.98 s, 0.66 flow-throughs | 20.2%. Unbounded FFT returns 10.00 s — the record length |
| `runs/lts` | 'time' 10..2000, dt 10 | pseudo-time. Refused outright |
| `runs/lowfn` | — | no `force*.dat` was ever written |
| `runs/val_coarse` | 4 samples | diverged at t = 0.0072 s |
| `runs/kcs_gci2/coarse` | 1.95 s, 0.13 flow-throughs | fits 0.82 s at 65.9%, matches no candidate: UNEXPLAINED |

`runs/beach` is the calibration point for the 50% bar, and it is not academic.
At the old 25% bar the tool returned "seiche n=3, 4.05 s" for it — on the SAME
tank at the SAME speed where 19.79 s of record gives 5.95 s. **A short record
does not find a different mechanism; it finds whatever it is allowed to find.**

## The fix, if it is the tank — and it is

Not solver tuning. Not deepening the tank.

1. **Absorb, do not reflect.** The inlet is `fixedValue U` and the outlet
   `outletPhaseMeanVelocity` + `zeroGradient p_rgh`; both are perfectly
   reflecting for gravity waves. A relaxation/damping zone over the last
   1-1.5 Lwl at each end is the mechanism that removes the energy. ESI v2606
   has no `verticalDamping` fvOption (that is an OpenFOAM.org facility —
   checked, not present, and recorded in `navalai/cfd/case.py`); the options
   are its `waveModels` absorption BC with a `constant/waveProperties`, or an
   explicit momentum sink over a `cellZone`.
2. **Or dissipate, the reference's way.** The Wolf Dynamics KCS deck has no
   damping model either — it leaves 2.31 Lpp of run-out coarsening 32x and
   lets numerical dissipation eat the waves. This project already pulled the
   refined wake forward to −1.0 Lwl for that reason, leaving 1.5 Lwl of
   run-out; the measurement above says 1.5 Lwl at 32x is not enough for an
   11.5 m wave.
3. **Domain sizing, secondary.** This project's domain is 1.5-2.6x smaller
   than the DTCHull reference on every axis (worst in half-width, 0.50, and
   depth, 0.39). Lengthening the tank moves the mode wavelengths (2L/n) but
   does NOT remove the mode — the ends still reflect — and it costs cells
   cubically. Absorption first.
4. **Do not chase it with run length.** The oscillation had not decayed at
   1.33 flow-throughs and had not decayed at 24 s. Its energy has nowhere to
   go; more seconds is more of the same.

Until one of those lands, **no C_T from this domain is a resistance number.**
`gate2m.py runs/val_coarse5` already returns NO RESULT, exit 2 (16.6% drift at
1.33 flow-throughs), and the −95.0% E%D is a phase of this oscillation.

## Compute spent

10.5 minutes of machine time, all of it on this Mac at np=10:

- `postProcess -func writeCellVolumes/writeCellCentres` on `runs/val_coarse5`
  — ~40 s. No re-solve: the fields for t = 4, 6, 8, 14, 16, 18 had survived.
- `runs/seiche_u_half`, generation + mesh + 9 s of solve — ~90 s mesh, 152 s
  solve. 102422 cells, `--scale 0.7 --symmetric --transient --n-layers 5`.
  checkMesh: 0 zero-volume cells, 4 incorrectly-oriented faces (bar 5), max
  skewness 5.69 (bar 20).
- Same case resumed 9 -> 24 s — 267 s. At 8.90 s the fit sat at 4.21 s against
  a scan capped at 4.45 s, i.e. against its own bound; 24 s was needed before
  anything could be concluded, and it cost 4.5 minutes.
- `postProcess` on it — ~60 s.

Mass was conserved on both runs (Phase-1 0.800306 -> 0.800242 on the half-speed
case, 8e-5), alpha stayed bounded, and `pmset -g log | grep -i thermal` is
clean over the session.

Note what `runs/seiche_u_half` is NOT: at U = 1.098 one flow-through is 29.83 s,
so 24 s is **0.80 flow-throughs**. It is a period measurement — a timescale, and
a tank mode is excited by the impulsive start rather than by a settled wake.
Nothing in it is a resistance number and `tank_resonance.py` prints that warning
itself.

## Still open

- **What exactly fixes lambda at 11.5 m?** Tank mode n=6 (2L/6 = 10.92 m) is
  the closest candidate and the measurement is 5% above it. It is also,
  numerically, the domain half-width (1.5 Lwl = 10.918 m) — L/3 and the
  half-width are the same number in this domain, and two runs on ONE domain
  cannot separate them. **A domain-LENGTH sweep would**, and it is the next
  experiment: at fixed U, 2L/n moves with L and the half-width does not.
- **A wetted-only (alpha.water-masked) y+** is still owed, unrelated but
  still owed.
