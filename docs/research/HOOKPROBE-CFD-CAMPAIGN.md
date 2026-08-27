# HOOKPROBE hull — calm-water CFD campaign (2026-08-26/27, Mac sim node)

Measured findings from the first owner-hull design campaign run through the
`make_case.py --stl` path. Every number below is calm water, fixed attitude,
8.0 t displacement, symmetric half-domain, transient interFoam, unless stated.
Single grid per run — NO GCI was performed, so absolute values carry
unquantified discretisation error; the deltas between hulls share a mesh
recipe and are the trustworthy quantity. Force histories evaluated with
`navalai.cfd.post.settled_drag` (doubles the symmetric half automatically).

Geometry lineage (all in `data/exports/hookprobe-concept/`, gitignored;
sha-stamped into each case.info):

- v1 `naval-ai-001-manual-modeling.blend` — owner's manual model. The raw
  export is a Solidify(0.3 m) double-skin shell and self-intersects at 459
  points (fin roots, stem, transom corners); it is REFUSED by the import
  gate. The CFD surface is the OUTER ENVELOPE: drop Solidify, apply
  Mirror+Subsurf(4), cap the sheer with one n-gon (`runs/hookprobe_inspect/`
  scripts). 12.0 m LOA trimaran-form: axe bow (11.5 deg waterline half-entry),
  deep centre keel-fin forward, two aft skegs, twin tunnels, motor pod
  planned in the centre channel behind the keel.
- v2 `naval-ai-002-drag-v2` — v1 + side-fin trailing edges tapered/extended
  (they were 0.24 m blunt slabs, WIDER at the tail than mid-chord), centre
  keel ridge slimmed toward the transom, stem sharpened below WL. 14 cage
  vertices.
- v3 `naval-ai-003-shoulder-v3` — v2 + aft shoulder eased: beam carried
  6-8 cm further aft at the y=-4.5/-5.15 cage rows, mid-shoulder leaned
  3-4 cm; all edits outside the fin/tunnel zone. 13 cage vertices.

## Resistance ledger @ 8 kn (4.1 m/s, Fn 0.38), 8 t, 40 s = 3.08 flow-throughs

    hull  total N   pressure N  viscous N  settled          case
    v1    3034.2    2425.3      609.0      NO (5.3% drift)  runs/hookprobe_cruise_n10
    v2    2997.6    2371.4      626.2      yes              runs/hookprobe_v2
    v3    2965.6    2341.1      624.5      yes              runs/hookprobe_v3

- Monotone improvement, -2.3% total / -3.5% pressure cumulative. Each step
  is WITHIN the 5-s-window scatter (~±2.5%), so individually unresolved —
  claimed only as a consistent direction across settled runs, per the
  resolvability discipline of JMSE 14(16):1483.
- Pressure (wave) drag is 78-80% of total at this Fn on every variant: the
  dominant wave system is the STERN system (plan-view wave maps in
  `runs/hookprobe_inspect/wave_plan.png`); transom rides 0.24 m immersed at
  8 t. Transom clearance is the remaining first-order lever; owner declined
  it (the stern serves the tunnel drive) — recorded as recommendation only.
- Viscous is 0.88x the ITTC-57 flat plate on 34.2 m^2 wetted (Re 4.45e7).
  Fins are 16.5 m^2 = 48% of wetted area (owner: fins mandatory).
- Effective power at 8 kn: P_E = R*V = 12.2-12.4 kW across variants.
- Ct COMPARISON PITFALL (unresolved): `settled_drag.ct` used inconsistent
  wetted-area denominators across these runs (34.2 vs 41.1 m^2 for nearly
  identical hulls). Compare NEWTONS at equal speed, not the ct field, until
  `stl_wetted_area` is reconciled.

## Tunnel (motor) inflow, centreline aft of the keel — the design's key claim

Water fraction / U/U0 at prop-plane candidates, t=40 s, 8 kn:

    station        v1            v2            v3
    x=2.0 z=-0.4   1.000/0.99    1.000/0.99    0.991/1.00
    x=1.0 z=-0.4   0.999/1.04    1.000/1.07    0.999/1.06
    x=2.0 z=-0.2   0.999/0.70    0.981/0.75    0.997/0.75
    x=1.0 z=-0.2   0.993/0.78    0.999/0.84    0.999/0.84

The tunnel stays WET (>=0.98 water) and the deep layer arrives at 99-107% of
boat speed — the owner's "keel line wave into the motor" concept is
CONFIRMED at cruise. The near-surface deficit (fin/hull wake) improved
0.70->0.75 and 0.78->0.84 from the v2 fin-tail taper and was preserved by
v3. Design guidance: prop axis at or below z=-0.4 (0.4 m below static WL),
>=0.5 prop diameters behind the keel tail.

## How the water behaves vs speed — and what it costs to simulate

    speed   Fn    deltaT (settled)  wall-s per sim-s   outcome
    8 kn   0.38   3.2 ms            ~250-320           clean solve, 3.2-3.4 h
    10 kn  0.48   0.9-1.1 ms        ~880-980           solves; slices stay
                                                        pinned (run 2026-08-27)
    11 kn  0.53   collapses         —                  DIES at t~0.045 s at
                                                        n_layers 10, 8 AND 5

- The timestep is set by the FASTEST water in the tank (wave crests, spray),
  not the boat speed, so cost grows super-linearly: 8->10 kn (+25% speed)
  tripled wall-clock per simulated second. Budget rule of thumb for this
  mesh family: wall-clock per flow-through roughly QUADRUPLES from Fn 0.38
  to Fn 0.48. (Flow-through time itself shrinks as 1/U, which claws back a
  little.)
- At 8 kn the timestep RELAXES after the startup transient (1.8->3.2 ms);
  at 10 kn it stays pinned — the wave field remains energetic for the whole
  run. Alpha undershoot is also larger (min -0.09 vs -1e-4 at 8 kn) without
  being fatal: watch the deltaT trend, not the undershoot, as the divergence
  discriminator.
- 11 kn (5.66 m/s impulsive start) is UNREACHABLE regardless of layer
  stack: n=10, n=8, n=5 all died with deltaT -> 1e-105..1e-26 while one
  cell's Courant stayed ~10 — the documented pathological-cell signature.
  The fix is a VELOCITY RAMP on the inlet/initial field, which make_case.py
  does not expose; do not burn attempts on layer backoff above ~Fn 0.5.
  (On Apple Silicon the FPE trap surfaces as SIGILL "Illegal instruction: 4",
  not sigFpe — do not misread it as a broken binary. First observed the
  night the OS was updated, which made that misread very tempting.)
- 10-kn ledger row is owed by the in-flight run `runs/hookprobe_v3_10kn`
  (v3, n=8, end-time 32 s); append its settled numbers when it lands.
- n_layers interacts with SPEED: n=10 meshed AND solved at 4.1 m/s but died
  at 5.66 m/s (thinner speed-derived first layer). The mesh-quality bars
  (0 zeroVol / <=5 wrongOri / skew<20) passed on every mesh that later
  died — build-time bars still do not predict solve-time collapse.

## Stability & seakeeping indicators (hydrostatics, NOT wave CFD)

v2 @ 8 t: waterplane 21.58 m^2, I_T 14.38 m^4, I_L 150.7 m^4, KB 0.690 m,
BM_T 1.84 m -> GM_T 1.63/1.43/1.23/1.03 m at KG 0.9/1.1/1.3/1.5 m;
GM_L ~19 m; underwater lateral plane 12.0 m^2 (one side) + 3 fins;
waterline half-entry 11.5 deg. Verdict: stiffly stable, strong pitch
restoring, excellent wave-piercing entry — STATIC indicators only. Dynamic
validation (roll decay, added resistance in waves) needs wave-generation
machinery (waves2Foam-style relaxation zones) this pipeline does not have.

## Owner's methodology principle (2026-08-27), and how this campaign obeyed it

"Known water behaviour should be known PRIOR to any simulation; simulation is
for what we don't know — complex foils, fins, tunnels." Concretely: spend
theory first, CFD second, and use the theory as the cross-check that the CFD
is sane. This campaign's split, for reuse on the next hull:

KNOWN BEFORE SOLVING (check, don't discover):
- Kelvin wake: transverse wavelength lambda = 2*pi*U^2/g (10.8 m at 4.1 m/s
  — the computed wake MATCHED; that match is a validation anchor).
- Viscous drag: ITTC-57 line on wetted area (CFD read 0.88x flat plate).
- Hump behaviour vs Froude number; displacement scaling of wave drag;
  hydrostatics (GM, entry angle, displacement curves) — all pre-computable
  from the STL in seconds.
- Planing craft (Fn > ~0.9): Savitsky empirical method BEFORE any CFD.

SIMULATION WAS FOR (no formula exists):
- Tunnel inflow quality at the prop plane (wet? how fast? how uniform?).
- Fin wake structure and what a trailing-edge taper buys.
- The stern-wave system of THIS hull's shoulder/transom combination.
- Which cell folds first when the start is too violent (found empirically,
  three times).

## Mission statement and phase plan (owner, 2026-08-27)

The boat is a PLYWOOD, SOLAR-POWERED cruiser; the mission target is
continuous low-speed running (~4-5 kn, ~1.2-2.3 kW input — see the solar
reframe in `docs/research/PROPULSION-INTEGRATION.md` §6, which holds the
propulsion/energy conclusions). The 8 t / 8-10 kn runs in this document are
deliberate STRESS-VALIDATION of the hull, not the operating point: validate
at the hard condition, operate at the easy one.

Phases, in order:
1. Calm-water hull validation (THIS DOCUMENT) — v1/v2/v3 complete; 10-kn
   point owed below; a 5-kn measured point (cheap: large timesteps) anchors
   the solar operating point.
2. v4: owner adds rudder + central pod/duct (E-POD or rim drive) in
   Blender; A/B vs v3 answers duct augmentation, rudder appendage drag,
   pod inflow. Modeling rules that keep it meshable: ONE closed outer
   envelope (union everything; my export keeps only the outer skin); no
   gaps under ~10 cm (a 1-2 cm rudder gap is unmeshable — attach or gap
   honestly); no features thinner than ~6 cm except trailing edges.
3. Rough-sea simulation AFTER hull validation: waves2Foam-style inlet
   relaxation zones (per JMSE 14(16):1483, the owner's chosen method
   reference), head seas with pitch+heave free (wave-cutting / anti-pitch),
   beam seas with roll+heave free (anti-roll, the fins' dynamic exam),
   wave-by-wave statistics, differences claimed only beyond combined
   uncertainty. Toolchain check owed BEFORE the phase starts: does a wave
   solver build against OpenFOAM v2606 on this Mac?

## Reusable recipe for the NEXT owner hull

1. Export outer envelope from Blender headless (drop Solidify, Subsurf 4,
   cap sheer, ~150k tris); `surfaceCheck -checkSelfIntersection` MUST be
   clean — closedness alone is not enough, and the import gate will refuse.
2. Float to target displacement by sectioning (scripts in
   `runs/hookprobe_inspect/`), rotate bow->+x, hull from x=0, WL at z=0.
3. `make_case.py --stl ... --symmetric --transient --n-layers 10` at
   Fn<=0.4; drop to n=8 near Fn 0.5; expect no solve above Fn ~0.5 without
   a ramp. `--n-layers 3` gives 5-15% layer coverage on this hull family —
   a wall model without a boundary-layer mesh is a different simulation.
4. Post: `settled_drag` for forces; wave maps via the interface-cell
   extraction in `runs/hookprobe_inspect/wave_post.py` (the ParaView 3D
   isosurface is broken on refineMesh hanging nodes — documented; slices
   and thresholds work, see `pv_scene.py` for the state-file generator).
