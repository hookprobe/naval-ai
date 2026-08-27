# Hull Design Knowledge Base — method and index

**Written 2026-08-25.** The records themselves live in **`data/hull_kb.json`**
(one home; this file explains method and carries no record content).

## What this is

The owner's directive (2026-08-25) reframed hull generation: *stop treating
the reference images as examples of what a hull looks like; treat them as
observations from which the system must infer the underlying geometric
construction rules* — and **prove reconstruction before attempting novelty**.

`downloads/hull-examples/` (~24 geometry-bearing images + ~25 research PDFs)
is the training corpus. Every image was inspected visually on 2026-08-25 and
transcribed into `data/hull_kb.json`: per-image feature records, a taxonomy
**derived from** (not imposed on) the corpus, and the recurring longitudinal
transition rules — the actual design grammar the references teach.

Because `downloads/` is **gitignored**, the KB is written to stand without the
images (gap J5's shape: an analysis must not silently depend on a file only
one machine has). Image paths are recorded as local-only provenance.

## What the corpus taught (one paragraph each)

1. **A hull is a field of sections under independent longitudinal laws** —
   beam(x), deadrise(x), chine height(x), flare(x), rocker(x), sheer(x),
   coordinated but never one section scaled. The spearhead and box failures
   are exactly what single-curve scaling produces (`hull_kb.json →
   transition_rules.section_field`).
2. **Vertical plane → horizontal plane.** Bows in this corpus are
   vertical-plane dominated (deep-V entry, axe stem, zero-to-negative flare);
   sterns flatten toward the horizontal (planing flat, wide transom, wet
   deck). Deadrise warps continuously; only lab models are prismatic.
3. **The teardrop plan** — fine entry (<9–12° labelled on three independent
   sheets), max beam at ~0.55–0.65 L from the bow, taper to a narrower
   immersed transom — recurs from the owner's hand sketch to the AMEL 50.
4. **Chines are curves with behaviour** (rise, terminate, change hardness),
   not bow-to-stern constants.
5. **The owner's design line is a topology change**: axe bow (deepest point,
   stem raked 20° aft) morphing into twin demihulls + wet deck. Lines
   exchange roles along the length. A single-surface genome cannot say this;
   an inner section boundary can (`scripts/hookprobe_hull.py` docstring).
6. **Slenderness costs transverse stability and nothing recovers it free**:
   added hulls, spray rails, tri-hedral tunnels or SWATH — the corpus shows
   all four answers.

## Where the generator falls short of the corpus (pointer, not a copy)

The code-level gap audit of 2026-08-25 (sampler pins the seven post-hoc genes
to zero, so every trained model has only seen conventional forms; `formlib`
expressibility verdicts stale since the 2026-08-24 flare/stem genes; no
spray-rail / stem-rake / inner-boundary primitives; plausibility bands
calibrated on one morphological family) is recorded in
**`docs/ml-hull-generation.md`** §4–§9 and the Gate 0E5C-CAP row — those
stay the one home of each finding. This KB adds the *corpus side*: which
observed family needs which missing primitive
(`hull_kb.json → records[].expressibility`).

## Reconstruction protocol (the loop this KB drives)

    reference record → feature analysis (hull_kb.json)
      → parametric interpretation (genome where expressible;
        direct lines → sections → loft where not)
      → generated hull STL → multi-view render
      → descriptor + visual comparison → correction → repeat

Reconstruction targets chosen (one per family tier, `reconstruction_target:
true` in the KB): the slender solar cruiser (in-genome), the 24° deep-V
(in-box deadrise, warp residual to be measured), and the hookprobe axe→cat
hybrid (out-of-genome, via the lines→loft path). Tool:
`scripts/hull_kb_reconstruct.py`; renders land in `renders/hull_kb/`
(gitignored, regenerable); the measured comparison table is appended to this
file when a target passes or fails visual validation.

The morphology critic's family bias is a **known defect** while it stands: a
WAVY-PLAN/SPEARHEAD flag raised against a deliberate wave-piercer is recorded
in the comparison table, not obeyed.

## Reconstruction results (measured, 2026-08-25)

`python scripts/hull_kb_reconstruct.py --target all` — all three targets
BUILT; full numbers in `renders/hull_kb/reconstruction-report.json`
(regenerable). Summary, measured against each KB record's intent:

| target | family | intent → measured | verdict |
|---|---|---|---|
| cruiser (hull-example-004) | slender displacement, IN-genome | entry <12° → **11.8°**; beam_transom 0.35 → **0.349**; convexity ≥0.80 → **0.805**; round bilge → roundness 0.9 sections; critique **1.0, zero flags** | **RECONSTRUCTED.** Residual: max beam sits at 0.45 L-from-bow vs the drawing's ~0.55 — the SAC law resists pushing the beam peak aft of mid; recorded, not hidden |
| deep-V 24° (hull-designs-gemini cell 1) | warped hard-chine planing | deadrise mid 24° → **24.0° exact**; warped → **27.1° at 75% fwd / 14.0° at transom** (a true warped V — evidence Gate 0E5C-CAP's pre-`beta_run` verdict needs re-measuring); hard chine → roundness 0 | **PARTIAL.** `beam_transom` saturates at **0.469** against the published 0.8–1.0 planing band — the `r_transom ≤ 0.50` ceiling, measured; WAVY-PLAN 0.634 persists (aft hollow from the beam-from-area coupling). The grammar cannot yet carry a full planing transom |
| hookprobe (owner schematic) | hybrid axe→twin-demihull, OUT-of-genome | 1 flow body forward → 2 aft → **measured 1 → 2, split between x/L 0.30–0.50 fwd of transom**; watertight+manifold → **True**; floats 14 002 kg, GM 2.87 m, draft 1.055 m at stem vs 0.575 midships (the axe signature) | **RECONSTRUCTED** (by `scripts/hookprobe_hull.py`, outside the genome — which is the point: the KB records exactly which family still needs the inner-boundary primitive) |

Renders (profile/plan/body-plan/perspective per genome target; four mesh
views for hookprobe): `renders/hull_kb/*.png`, inspected visually against
the source images during the correction loop (three rounds for the cruiser:
the first had a hollow aft waterline and a kinked parallel-midbody joint the
descriptors alone under-reported — the render caught it, which is the
protocol's point).

## naval-ai-concept.stl (measured, 2026-08-25)

The owner's end-to-end test artifact: `python scripts/naval_ai_concept.py`
→ `data/exports/naval-ai-concept.stl` + `naval-ai-concept-report.json`
(both regenerable build artifacts; the SCRIPT is the tracked design).
Coastal/inland axe-bow → twin-demihull vessel, 16 m / 14 t, designed
**wake-first**: the propulsor sizes the stern channel (3 fixed-point
iterations; disc 0.592 m from the loading bar at 6 kn thrust, channel
0.444 m so the disc overlaps 12.5% of D into each demihull — the owner's
starting value, CFD ranking of 5/10/15/20% owed).

**All ten §29 failure conditions PASS at the 6 kn continuous cruise**:
watertight+manifold; GM 2.44 m; disc fits (0.592 vs 1.338 m of room); tip
0.37 m above the skeg plane (protected) and submerged at rest; morph
divergence 3.1° vs the ≤10° funnel bar; draft over skegs 1.02 m (≤1.5
shallow-water bar); cruise 11.4 kW upper-band = 76% of the 15 kW motor
(≤80% continuous); topology measured 1 flow body forward → 2 aft.
At 7 kn the same chain measures 117% of continuous rating and the
`motor_power` check REFUSES — 7 kn is sprint, not cruise, on this motor;
that refusal is the pipeline doing its job. Drag is carried as an ITTC-57
friction × (1.15–1.45) form-factor BAND (1480–1866 N at 6 kn; 1505–1897
Wh/nm electric), never a single claimed number. The hb19 RANS anchor
LANDED (2026-08-27 re-read of `runs/hb19_7kn`, settled at 2.22
flow-throughs, drift 1.7%): total 1733 N at 7 kn — ~1.57x the L1
prediction — split 1350 N pressure / 384 N viscous, i.e. **78% pressure**
at Fn 0.33, the same wave-dominated split the hookprobe campaign measured
at Fn 0.38 (78-80%). On bluff-stern forms the drag lever is AFT: transom
clearance and an eased aft shoulder — which the design side can now
express (`dwl`/`rb_transom`, the designed waterline). The 1.57x is a
single-grid number (no GCI) and stays a research anchor, not an L1
correction; the Coandă-attachment hypothesis stays OWED to CFD.

**OPEN — the owner's split-position correction.** Same day: "the deep v
hull needs to extend for about 70-80% of the length and the demihull the
rest." The shipped artifact still uses the kernel split (single body =
forward 32% only). Two attempts to move it (x_split 0.28 with x_full
0.06 / 0.10) were REFUSED by the watertightness check — 8 then 635
measured self-intersections, spread over x/L 0.0–0.4 at all heights: the
wet-deck/arch loft in `scripts/hookprobe_hull.py` folds when the tunnel
opens over a short span, even though the narrow wake-first channel clears
the ≤10° divergence bar (8.2° measured). The fix is kernel work (re-derive
the arch morph for short transitions), recorded in the script's `build()`
comment; a folded artifact was not shipped in its place.
