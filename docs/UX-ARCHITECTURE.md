# UX ARCHITECTURE — the running builder surface

**Authority: HOW THE SHIPPED INTERFACE IS BUILT.** Its component architecture,
its state machine, its data contract with the backend, and the reasoning behind
each. Written 2026-08-21 against the code in `ui/`, and every capability claim
in it was exercised over HTTP before it was written down.

**This file must NOT contain:** the builder-facing DESIGN (that is
`docs/BUILDER-UX.html`); the ORDER or the owner of the work (that is
`docs/BUILD-PLAN.md` §PU); a gate verdict or a status (that is
`python -m navalai.gates` and `data/gate-ledger.json`); a measurement it is not
the only home of.

---

## 0 · What already existed, and what this reuses

**The operator's instruction was to check what exists before writing
anything.** Three artefacts already covered part of this ground, and none of
them is superseded:

| Artefact | Owns | This document's relation to it |
|---|---|---|
| `docs/BUILDER-UX.html` — "The Lofting Floor" | **The design.** Four phases, ASCII wireframes, and the endpoint or field EVERY control binds to. Its §00 (`QuantityBadge`, colour on `basis`) is the atom of the whole system | **REUSED WHOLESALE, NOT RESTATED.** Its four phases became the DESIGN group of the navigation; its four badge registers became `core.qbadge`; its constraint-light-as-headroom-bar became `core.constraintRow`; its colour tokens are literally the token names in `ui/app/app.css`. Where this document extends it, §0.1 says so |
| `docs/BUILD-PLAN.md` §PU (PU-1 … PU-7) | **The order and the bars.** The only place the schedule lives | **RECONCILED, NOT REPLACED.** §11 maps every PU item to the code that now implements it and to the test that fences it. Nothing here reorders PU, and nothing here adds a work item to it |
| `ui/server.py` (703 lines) + `ui/index.html` | **The engineer's surface** — `/eval`, `/bounds`, `/mission`, `/generate`, `/pareto`, one slider per grammar parameter | **KEPT AND EXTENDED, NOT REWRITTEN.** PU says in as many words that the gap "is a mapping layer, not a rewrite". `ui/index.html` is pinned by `tests/test_stageF.py` down to the strings in it and is untouched; it moved from `/` to `/legacy` and is reachable from the new surface's SYSTEM screen |

### 0.1 · What this document adds that the blueprint does not carry

The blueprint is a design for **four builder-facing phases**. The operator's
brief asks for a **seven-group product** that also serves an engineer and a
researcher. The delta, and only the delta:

1. **Three disclosure levels** (L1 mission / L2 engineering / L3 validation)
   and the rule that governs them: *the level hides DETAIL, never a failure and
   never an absence.*
2. **Screens the blueprint has no phase for**: Projects, Requirements,
   Hydrostatics, Resistance, CFD workspace, Population & search, Pareto,
   Compare, Validation Center, Gates & ledger, Digital twin, System.
3. **A component and state architecture** — the blueprint describes behaviour,
   not modules, a render loop or a store.
4. **The absence registry as a served artefact** rather than as prose. The
   blueprint lists what is absent; this makes the list a single machine-readable
   home so a tile cannot outlive the gap it describes.

Nothing here supersedes the blueprint. One thing in it is **sharpened**: the
constraint light. The blueprint draws the bar with "full bar = at the limit",
and building it that way produced a screen where the SAFEST row had an empty bar
and the row about to fail had a full one — see §6.2.

---

## 1 · Personas, and what each is allowed to be told

| Persona | Knows | Enters at | Must never be shown |
|---|---|---|---|
| **The builder** (primary) | Boats, plywood, their own garage. Has never heard of a prismatic coefficient | Projects → Mission | A grammar parameter; a coefficient as a control; a green light over a typed sigma |
| **The naval architect** | Hydrostatics, Froude scaling, ISO 12215 | Hull studio, expert switch on | A number whose basis is not recoverable in two clicks |
| **The physics reviewer** | RANS, GCI, y+, validation envelopes | Validation → Gates | A gate verdict that no suite produced |
| **The operator** (this repo's owner) | All of it | System | A capability claim that the manifest does not back |

**One rule spans all four, and it is the product's whole argument:** the
interface hides the mathematics and refuses to hide the uncertainty. A builder
never sees a prismatic coefficient. They *do* see that 3298 kg is unaccounted
for, that the drag model was validated on a ship nothing like theirs, that
nobody has predicted how their bow behaves in a chop, and that their hull may
want a mould rather than a flat-pack.

---

## 2 · The primary journey

The operator's brief names fifteen stages. They map onto the screens as:

```
MISSION ─────────────► #/mission        free text → parse_mission → READ-BACK
REQUIREMENTS ────────► #/requirements   HARD rows vs SOFT objectives, named
   │                                     (a requirement with neither is NOT ENFORCED)
   ▼
HULL GENOME ─────────► #/envelope       compile_policy → the BOX. Nothing is a
PARAMETRIC GENERATION                    boat yet; this is the legal region
   │
   ▼
   ├───────────────► #/hull            six behavioural sliders over 16 genes,
   │                                    two-rate render loop, live vitals
   ├───────────────► #/buildability    refold FAMILY → kit / search / mould
   ├───────────────► #/reality         8 rows under 3 human questions
   ├───────────────► #/hydrostatics    derived, non-editable
   ├───────────────► #/resistance      speed sweep with the Fn 0.45 refusal
   └───────────────► #/cfd             real case receipts. No verdict claimed
   │
   ▼
AI OPTIMIZATION ─────► #/search        governed sweep; every death NAMED
PARETO FRONT ────────► #/pareto        NSGA-II, 3 objectives, GM re-read
FINALIST SELECTION ──► #/compare       2–4 designs, per-row delta
   │
   ▼
HIGH-FIDELITY ───────► #/validation    provenance + PHYSICS confidence
VALIDATION             #/gates         registry + expected-red ledger
   │
   ▼
BUILD PACKAGE ───────► #/build         route verdict FIRST, then the gated release
                       #/twin          the join: every field, its producer named
```

**The journey is not a wizard.** Every screen is reachable from the rail at any
time; a screen that cannot say anything true yet says exactly what is missing
and links to it (`main.gateFor`). A disabled link teaches nothing.

---

## 3 · Information architecture

Seven groups, matching the operator's navigation spec exactly:

```
PROJECTS      All projects                                      L1
DESIGN        Mission · Requirements · Envelope ·
              Hull studio · Buildability                        L1
ANALYSIS      Reality check L1 · Hydrostatics L2 ·
              Resistance & power L2 · CFD workspace L3
OPTIMIZATION  Population & search L2 · Pareto L2 · Compare L2
VALIDATION    Benchmarks & physics L1 · Gates & ledger L3
FINAL DESIGN  Build package L1 · Digital twin L2
SYSTEM        Models, solvers, data L3
```

The **L** column is the disclosure level at which the item appears in the rail.
Two placements are deliberate and worth defending:

- **Validation → Benchmarks is L1.** A builder is entitled to know that the
  only CFD anchor is a container ship. Demoting that to an expert screen would
  make the product quieter about bad news for the audience least able to
  discover it independently.
- **Build package is L1.** The route verdict — kit or mould — is the single
  most consequential thing the product tells a builder.

---

## 4 · Design system

**Dark engineering workspace, tabular figures, no gradients, no gauges.** The
tokens in `ui/app/app.css` carry the same NAMES as `docs/BUILDER-UX.html`
(`--ink`, `--panel`, `--accent`, `--copper`, `--pass/warn/fail/unknown`) so the
blueprint and the product are one system rather than two descriptions of one.
The blueprint is a document and defaults light; the workspace defaults dark.
Both honour `data-theme` and `prefers-color-scheme`.

- **Type**: system sans for prose, system mono (`ui-monospace`) for every
  number. `font-variant-numeric: tabular-nums` everywhere a column of figures
  appears. **No web font is fetched** — `tests/test_ui_surface.py::
  test_the_app_ships_no_external_asset` is the fence. A loopback design tool
  that goes blank without a network is a design tool that fails in a workshop.
- **Colour is never the only channel.** Every state also carries a glyph
  (`●` measured, `◆` assumed, `▲` lower-bound, `▨` absent, `✕` refused) and
  text.
- **Motion expresses an invariant or it does not exist.** A policy may only
  move a bound INWARD, so the envelope's bars only ever close in from the ends.
  There is no other animation, and specifically no "AI thinking" motion: the
  work is measured in milliseconds and the number is printed.

---

## 5 · Component architecture

No framework. Vanilla ES modules, no build step, served as static files from
`ui/app/` by the existing stdlib server. The existing stack is one HTML file
and one Python module; introducing a toolchain to add screens to it would cost
more than it returns and would put a build artefact between the code and what
the browser runs.

```
ui/app/
  index.html          shell: mast, rail, screen host, toast,
                      + a CLASSIC-script error trap (see §5.1)
  app.css             tokens, primitives, responsive rules
  core.js             transport · store · el() · qbadge · constraintRow
                      · absentTile · linechart
  viewport.js         Viewport: 3D + profile + plan + body plan, canvas 2D
  main.js             NAV table · hash router · disclosure levels · gateFor
  screens-design.js   projects · mission · requirements · envelope · hull ·
                      buildability   + the behavioural slider layer
  screens-analysis.js reality · hydrostatics · resistance · cfd · search ·
                      pareto · compare · validation · gates · build · twin ·
                      system
```

### 5.1 · The error trap is a classic script, on purpose

A module that fails to **evaluate** never installs its own handlers, so a trap
inside `main.js` cannot report `main.js` failing to parse. MEASURED during
implementation: a missing parenthesis in `screens-analysis.js` produced a
completely blank window — indistinguishable from a window that had measured
nothing, which is the one confusion this product may not create about itself.
The trap in `index.html` rendered `SyntaxError … screens-analysis.js:440:15`
into the screen instead. It stays.

### 5.2 · The atoms

**`qbadge(name, q, opts)` — the quantity badge.** Takes `{value, tier, sigma,
basis, state}` exactly as `ui/server._q` puts it on the wire and switches on
`basis`:

| basis | glyph | border | means |
|---|---|---|---|
| `measured` / `propagated` | ● | solid pass | σ propagated from the model that produced the value |
| `propagated-lower-bound` | ▲ | solid accent | the truth is WORSE than this, not better |
| `assumed` | ◆ | dashed warn | the band is a declared fraction of the value. A decoration, and it says so |
| `placeholder` | ▨ | grey, 45° hatch | no input σ reached the propagation. `navalai/energy.py`: *DO NOT USE* |
| `absent` | ▨ | grey, 45° hatch | not measured. Never filled with a plausible number |
| `state` set | ✕ | solid fail | non-finite — refused |

**Colour switches on `basis`, never on `tier`.** A badge reading `tier` renders
a typed sigma as confident L1 green, which is precisely the defect the audit
found in this tree.

**`constraintRow(name, g, why)` — the constraint light.** A bar, not a dot: a
dot says *pass*, a bar says *how close*, which is what links a slider to the
thing it is about to break. See §6.2 for the direction.

**`absentTile(key)` — an absence, rendered as an absence.** Reads the SERVED
registry. The reason is never in the markup; §7.2.

**`linechart(opts)` — inline SVG, no library.** Real axes, real units, and a
**REFUSED band** drawn as a red region with its reason, not as a faded curve.

### 5.3 · The viewport

`viewport.js` rasterises the quad mesh with a painter's algorithm in canvas 2D.
`panel_mesh()` is ~464 faces at 1.66 ms and `closed_mesh()` ~5232 at 49.75 ms —
both comfortably inside a frame — so a WebGL dependency would buy nothing this
hull needs.

- **Shading is on the surface NORMAL, not on depth.** Measured against the
  first implementation: a depth ramp made every hull look like the same loaf,
  and the chine, the flare and the deadrise — the three things a builder reads
  a hull by — were invisible. One fixed light, no specular, no shadows: nothing
  here claims to be a render.
- **The characteristic curves are drawn from `edge_curves()`**, which evaluates
  the keel, chine and sheer analytically. They are not traced out of the mesh,
  so they stay exact at the fast fidelity.
- **The waterline plane is sized to the BOAT** (0.60 × length, 1.15 × beam). A
  plane drawn to the scene bounds dominates the picture and says nothing extra.
- **Four views**: 3D (orbit/zoom), PROFILE, PLAN, BODY PLAN. The blueprint views
  read station offsets from `/api/sections`, which returns `Hull.section(i)` by
  STATION INDEX — the hull carries its own abscissae in `hull.x`, and inventing
  an x-grid would resample a curve the kernel already discretised.

---

## 6 · The data model the UI expects

### 6.1 · Endpoints

Existing, unchanged, still pinned by `tests/test_stageF.py` and
`tests/test_phase4.py`:

| route | shape |
|---|---|
| `POST /eval` | `{ok, tier, violations[], eval_ms, quantities{…_q}, weights_kg{…_q}}` |
| `GET /bounds` | `[{name, unit, low, high, desc}] × 16` |
| `POST /mission` | `MissionSpec` as JSON |
| `POST /generate` | conditioned pool draw |
| `GET·POST /pareto` | `{points[{params, wh_per_nm, build_area_m2, gm_m}], n_evals, refused, refused_reasons[], live, elapsed_ms}` |

New, in `ui/api.py` — a separate module, because `ui/server.py` is pinned to
its payload strings and PU calls this a mapping layer:

| route | returns | measured cost |
|---|---|---|
| `GET /api/manifest` | grammar params, the 8 constraint names, `ABSENT`, `REAL`, latency budgets, Fn ceiling, refold bar | instant |
| `POST /api/envelope` | `CompiledPolicy.box(cat)`: names, ungoverned bounds, compiled bounds, every `BoxEdit(param, edge, was, now, source)`, appended rows, disclaimer | instant |
| `POST /api/mesh` | `panel_mesh` (fast) or `closed_mesh` (fine) + `edge_curves` + `gen_ms` | 1.7 / 50 ms |
| `POST /api/sections` | station sections, keel/chine/sheer polylines, SAC | ~10 ms |
| `POST /api/capsize` | `GZCurve` + KG + assumptions | ~150 ms |
| `POST /api/refold` | `RefoldConvergence` + route + verdict meaning | **~12 s** |
| `POST /api/buildability` | `engineer.assess`: panels, ONE nest, layout, BOM, summary | **~5 s** |
| `POST /api/speedsweep` | per-speed Rt/Rw/Rf/P/Wh-per-nm, or `REFUSED` with the reason | ~11 ms × n |
| `GET /api/gates` | registry rows + the expected-red ledger verbatim + `suite_run: false` | instant |
| `GET /api/validation` | benchmark provenance + the four-register confidence model | instant |
| `GET /api/cfd/cases` | every `runs/*/case.info` receipt (112 on this node) | instant |
| `POST /api/search/{start,status,cancel}` | a real governed sweep, with every rejection named | job |
| `POST /api/twin` | the JOIN: genome, mission, rows, badges, weights, resistance, energy, rules, absences | ~20 ms |

### 6.2 · The contract every payload keeps

**`source` ∈ {`measured`, `absent`, `refused`, `mock`}, on every payload.** A
screen cannot decide whether its data is real; the payload must say, and the
front end renders the declaration rather than a default. Fenced by
`test_every_api_payload_declares_a_source`.

**A non-finite quantity is a refusal, not a number.** `evaluate.
non_developable_frac` is NaN *by design* when the meter could not run, exactly
so it cannot be read as "0% non-developable"; `_ff` turns it into `null`.
`NaN` is also not valid JSON (RFC 8259) and would take a whole screen down at
`JSON.parse`. Fenced by `test_no_payload_ships_a_nan`.

**`g <= 0` is satisfied; the value is the normalised margin; 0 is exactly at
the limit — and the convention travels on the wire**, because a reader who
assumes the other sign gets every light backwards.

**The direction of the headroom bar — a correction to the blueprint.** The
blueprint draws the constraint light with "full bar = at the limit". Built that
way, the safest row (`list`, margin −2.000) rendered as an EMPTY bar and the
row about to fail (`rules`, margin −0.010) rendered as a FULL one. A builder
reads a full bar as good. The shipped bar is therefore the headroom REMAINING:
full is comfortable, empty is at the limit, a violation is red and full. The
blueprint's numbers (87% / 71% / 20% / 0%) are consistent with this reading;
its caption is what misleads.

---

## 7 · Honesty architecture

### 7.1 · What is mocked

**Nothing.** No screen in this surface displays a fabricated number. Every
figure comes from `evaluate()`, `compile_policy()`, `hydrostatics`, `unroll`,
`engineer`, `benchmarks/*`, `data/gate-ledger.json` or a `runs/*/case.info`
receipt on disk.

Where the backend cannot answer, the answer is an **absence**, not a mock. The
one piece of state the browser owns is the **project list**, which is real and
local: `localStorage`, stated on the Projects screen in those words, because
there is no project store in the backend and inventing one in the UI would give
the mission a second home.

### 7.2 · The absence registry

`ui/api.ABSENT` is the one home of every declared hole, in the same shape
`navalai.refdata.absent()` already uses (`{what, why, unblocked_by}`) plus the
`surface` it appears on. It is SERVED on `/api/manifest`, and
`test_an_absence_is_declared_in_exactly_one_place` greps the front end to prove
none of the prose is typed into the markup. **The day a capability lands, its
tile disappears with it instead of going on claiming the gap** — which is this
project's signature defect (a thing declared twice) wearing a `<div>`.

Currently declared: stem rake / reverse bow · air draft · motion in a chop ·
solar sigma · Cb sigma · planing resistance · a hard-chine experimental anchor ·
assembly manual · BOM consumables · cost model · battery state of charge.

### 7.3 · Physics confidence, never AI confidence

Four registers, served with their definitions: **VALIDATED** (reproduced
against an experiment we hold, inside its envelope) · **CALIBRATED** (fitted to
data; honest inside the fit's population) · **EXTRAPOLATED** (the anchor exists
but this craft is outside its envelope) · **UNVALIDATED** (no anchor — an
ABSENT score, not a low one). There is no percentage anywhere.

KCS is served as **EXTRAPOLATED** with the scope line attached to the row
rather than to a footnote, and the hard-chine gap is a first-class ROW rather
than an omission.

### 7.4 · A gate verdict comes from running a suite

`/api/gates` serves the registry, the expected-red ledger verbatim (watermark,
units, bar, owner, `review_by`, `why_red`) and `suite_run: false` — and the
screen prints the command that would produce a verdict. **A green dot because a
page loaded is the dishonesty the ledger exists to prevent.** One ledger
watermark is deliberately the STRING `NONE`; it is rendered as that string.

### 7.5 · CFD is never "complete because a solver exited"

`/api/cfd/cases` reads 112 real receipts and classifies each by flow-throughs
against the two bars that matter: **1.0** (below it the free stream has not
crossed the domain and it still holds its initial condition) and **5.0**
(settled). No force history is read and no `C_T` is claimed — `scripts/
gate2m.py` is the only thing in this tree allowed to print that verdict, and it
refuses one it cannot support. Launching a run is NOT wired to the browser: it
is an hours-long job on the simulation node, and a button would imply
otherwise. The commands are printed instead.

---

## 8 · The state machine

```
                    ┌──────────┐
                    │ NO PROJECT│
                    └─────┬────┘
                          │ create
                    ┌─────▼─────┐
        ┌──────────►│ DRAFTING  │  mission text → parse → READ-BACK
        │           └─────┬─────┘  (parsed values are shown back, never committed)
        │  edit brief     │ compile_policy
        │           ┌─────▼─────┐
        └───────────┤ ENVELOPED │  the box exists. Sliders now have legal ends
                    └─────┬─────┘
                          │ lock the brief (hash freezes)
                    ┌─────▼─────┐
      ┌────────────►│  SHAPING  │◄──── load from search / pareto
      │             └─────┬─────┘
      │   slider          │  every frame:  FAST  (panel_mesh 1.7 ms + eval 11 ms)
      │   moves           │  on release:   FINE  (closed_mesh 50 ms + sections)
      │                   │
      │             ┌─────▼─────┐
      │             │  ROUTED   │  refold_convergence over a station FAMILY
      │             └──┬───┬──┬─┘
      │       PASSES   │   │  │  NON_DEVELOPABLE / REFUSED
      │                │   │  └──────────────► MOULD  (frames + patterns;
      │                │   │ REFINING                  the kit search is a JOB)
      │                │   └──────────────────► REFINE, do not route yet
      │           ┌────▼─────┐
      │           │ PACKAGED │  engineer.assess → ONE nest → BOM + layout
      │           └────┬─────┘
      │                │  release gate: every panel present · re-folds within
      │                │  the bar · units declared · thickness ISO-derived
      │           ┌────▼─────┐
      └───────────┤ RELEASE  │  export_dxf stamps REFOLD VERIFIED — server-side
                  └──────────┘
```

**Search / CFD run as jobs beside this machine, not inside it**:
`RUNNING → DONE | CANCELLED | FAILED`, polled, cancellable, with progress and
elapsed time printed. A CFD case's own states are the receipt's:
`UNDER-RUN | SETTLING-UNVERIFIED | RECEIPT ONLY` — deliberately **not**
`CONVERGED`, which is a claim only `gate2m.py` may make.

---

## 9 · Failure and absence states

| state | rendering | why this way |
|---|---|---|
| Constraint violated | red row, full bar, the ladder's own sentence | a violation with no reason is a wall |
| `unroll` refuses | full-screen refusal naming the mechanism | it is the last honest moment; the same refusal measured 19 of 19 on an ungoverned front |
| Fn > 0.45 | red BAND on the chart, point state `REFUSED`, the limit named | a faded curve there is a guess wearing a line style |
| Empty Pareto front | the measured non-monotonicity, and a link to the sweep | an empty list reads as "there are no good boats"; the truth is a gap in OUR search |
| No equilibrium | "the hull does not float at this displacement" | not zeros |
| Capability absent | 45° hatched tile, grey, with `unblocked_by` | never a plausible number |
| Screen throws | the exception, in the screen | a screen that renders empty on an error is indistinguishable from one that measured nothing |
| Module fails to parse | the SyntaxError, from the HTML-level trap | §5.1 |
| Screen has no input yet | "not ready", what is missing, a link to it | a disabled nav link teaches nothing |

---

## 10 · The two special workflows

### 10.1 · The behavioural slider layer (guided mode)

Six intent controls over sixteen genes. A parameter is composed as

```
norm(p) = clamp(0.5 + Σ_controls amp(p, c) · (u_c − 0.5), 0, 1)
value(p) = lo(p) + norm(p) · (hi(p) − lo(p))
```

where `lo`/`hi` are the **compiled box's** bounds, so a policy-clipped
parameter is a shorter track and never an out-of-bounds proposal. Two controls
may share a parameter (`BWL` is driven by *room vs range* and by *feels
planted*), which is why the composition is additive rather than a lookup.

- **`LWL` is not a behavioural control.** It is a mission number; it is seeded
  from `lwl_hint_m`, displayed in the studio as coming from the brief, and
  edited on Requirements — where editing it also recompiles the envelope.
- **The `⚙ expert` switch** swaps the six for the raw sixteen from
  `/api/manifest`, writing the same numbers through the same `/eval`. **No
  second code path** — that is what makes the abstraction trustworthy rather
  than a wall.
- **A pinned parameter shows a padlock with its reason inline**, not a greyed
  control: sheet-plywood construction clips `roundness` to exactly `[0, 0]`,
  and the padlock IS that fact.
- **The bow control ships short of its range**, with the reason: there is no
  stem-rake gene, so no reverse-raked bow is drawable. Drawing one the engine
  cannot produce would let a user design around it and meet a refusal at export.

### 10.2 · Autonomous mode — and why it is a SWEEP, not "generations"

`/api/search` runs a **governed uniform sweep over the compiled box, every
candidate through the same `evaluate()` the sliders call**, reporting which
constraint row killed each death.

It is deliberately not dressed as evolution, for two measured reasons:

1. **The sweep is the honest primitive here.** Only 3 of 400 random draws clear
   the 5 mm refold bar, and most candidates die in `grammar.check` at 0.27 ms —
   the recipe that works is a large seed sweep followed by a refine.
2. **NSGA-II at the server's live budget does not converge on this brief.**
   Measured: 240 evaluations → 0 front members, 480 → 1, 800 → 0, 1200 → 48.
   It is NON-MONOTONE, so the search is unreliable there rather than merely
   slow. The front therefore stays on `/pareto`, with `live` and `elapsed_ms`
   declared, and is never presented as a converged result.

The screen shows the survivors AND the rejections, with a per-row histogram of
what did the killing. **Never hide a failed design**: measured on 30 draws from
the panel's own default brief, 2 of 30 were feasible, 6 failed ONLY on bend
radius, and NO hull in the population reached the radius its own required ply
can take — best 1.40 m against a 1.44 m floor. That is a finding about the
product, and it is only visible if rejections carry their reason.

---

## 11 · Reconciliation with `docs/BUILD-PLAN.md` §PU

**This table claims implementation, not completion.** PU's done-when clauses
and its phase bar (gap I13 — a recorded non-expert session producing a hull
that passes the full ladder) are unchanged and are not this document's to move.

| PU | What it asks | Where it now lives | Fence |
|---|---|---|---|
| **PU-1** | six behavioural controls; ends from `CompiledPolicy.box`; `⚙ expert` swaps to the raw sliders with the same evaluation and no second path; a clipped bound shows as a locked end with its reason | `screens-design.BEHAVIOUR` / `behaviourToParams` / `bounds()` / `rawSlider` | `test_the_surface_never_invents_a_ninth_constraint_row` |
| **PU-2** | two-rate render loop; physics + fast mesh per frame, fine mesh on change, unroller never in the loop | `screens-design.hull`'s `schedule()`/`refresh(fast)`; `/api/mesh` exposes both rates and reports `gen_ms`; the unroller is reachable only from an explicit action | `tests/test_phase4.py` still owns the `<100 ms` bar |
| **PU-3** | "make it cuttable" is a JOB, not a control; the studio never implies it is instant; the result shows the measured TRADE | Build screen renders the two routes side by side with the measured trade (59 → 121 sheets, 1825 → 3679 hours, 412 → 595 Wh/nm, GM 0.82 → 2.55). **The job itself is NOT wired to the browser** and the screen says so, naming `scripts/design_kit.py` | — (see §12) |
| **PU-4** | route verdict reads the TREND, not one station count | `/api/refold` → `unroll.refold_convergence`; `route` is a pure function of `verdict`; `REFINING` routes to *refine*, never to *mould* | `test_the_route_verdict_never_reads_one_station_count` |
| **PU-5** | absent capabilities render as absent; none filled with a plausible number; colour on `basis` not `tier` | `ui/api.ABSENT` served; `core.absentTile`; `core.qbadge` switches on `basis` | `test_an_absence_is_declared_in_exactly_one_place` |
| **PU-6** | mass closure beside the stability lights, unaccounted mass listed by name, tiles above marked provisional | Reality check's mass table + closure bar; studio's vitals rail carries a compact copy | — |
| **PU-7** | the legal stage RENDERS P1-5's route, does not compute a second one; the five-year rule prints with its article; `NOTIFIED_BODY_REQUIRED` refuses to emit | Build screen's legal card reads `Evaluation.policy.route` and the compiled disclaimer; Art. 2(2)(a)(vii) and Art. 19(4) print with their numbers | — |

---

## 12 · What is NOT implemented, and why

Stated here so no reader has to infer it from an absence:

1. **The cuttable-hull search job is not submittable from the browser.** The
   recipe that works is a 76 420-draw seed sweep plus a (1+1)-ES; it runs for
   minutes and can fail. The Build screen shows the two routes and the measured
   trade and names `scripts/design_kit.py` rather than offering a button that
   would promise something instant. Wiring it is the same job machinery
   `/api/search` already has.
2. **Nothing starts an OpenFOAM run.** §7.5.
3. **The ZIP is not produced from the browser.** `export_dxf` runs on the
   simulation node and stamps `REFOLD VERIFIED` into the file. The release
   checklist is rendered and each check is individually explained; the gate is
   enforced server-side by the exporter raising, not by a disabled button.
4. **Cost is absent, and so is every BOM consumable** (glass cloth, fasteners,
   copper stitching wire). Declared, with what would close them.
5. **Free sinkage and trim are not drawn as an attitude.** The equilibrium
   solver returns `trim_deg` and the viewport accepts it; the studio currently
   passes 0 because `panel_mesh` cuts at `z = 0` by construction and rotating
   the mesh without re-cutting it would draw a waterline the hull is not
   actually floating on.
6. **The Compare screen re-evaluates rather than caching.** Four twins at ~20 ms
   is not worth a cache, and a cache here would be a second home for a number.

---

## 13 · Responsive behaviour, and one honest amputation

- **≥1280 px** — the full three-zone studio. This is where design happens.
- **768–1279 px** — the studio stacks; the viewport keeps 56vh.
- **<768 px** — **no studio.** Phones get Mission, Requirements, Reality check,
  Validation and Build. The sliders are not offered, and the screen says why:
  nobody lofts a boat on a phone, and a degraded control surface at that size
  produces hulls someone unpicks on a laptop afterwards.

Accessibility falls out of the honesty contract rather than being bolted on:
state is carried in shape and text as well as colour; numbers use tabular
figures; `prefers-reduced-motion` disables the (small) motion; the rail is a
`<nav>` with real links, so the browser's own affordances work.

---

## 14 · Success criteria, and how the surface meets them

| Criterion | Where it is met |
|---|---|
| A newcomer understands what the system does in 30 s | The masthead thesis + the Projects screen's "what happens next" |
| …how to design a boat in 2 min | Mission → read-back → Requirements → Envelope → six sliders |
| …how it knows the boat is good in 5 min | Reality check's three questions, then the provenance strip's link into Validation |
| An engineer can say where a number came from | `qbadge` basis + tooltip → Digital twin's badge grid → Validation's benchmark row |
| …whether it was experimentally validated | The four-register confidence model, with the scope line on the row |
| …whether CFD actually converged | CFD workspace: flow-throughs against the 1.0 and 5.0 bars, and no verdict claimed |
| …whether the hull is buildable | The refold FAMILY, and the route it implies |
| …why this design was chosen | Compare: per-metric delta, changed genes, per-row margins |

---

## 15 · Running it

```
source ~/.venvs/naval/bin/activate
python ui/server.py 8642          # prefit runs first; ~40 s
```

- `/app` — **the builder surface**
- `/` (and `/index.html`, `/legacy`) — the engineer's sixteen-slider page,
  unchanged. It keeps the root: it was briefly moved and
  `tests/test_phase4.py::test_http_server_smoke` failed on
  `assert "slider surface" in html`, which is an existing fence over an entry
  point this work was not asked to move. The routing changed rather than the
  assertion.
- `/api/manifest` — what the surface believes it can and cannot do

Tests: `python -m pytest tests/test_ui_surface.py -q` (14 tests, ~31 s).
