# ROUND 3 — SYSTEM MAP: what actually executes, arrow by arrow

**Method.** Every row below was produced by RUNNING the pipeline, not by
reading it: `scripts/product_test.py` drives seven customer briefs end to end,
`scripts/gap_sweep.py` sweeps the seam properties, and the identity and timing
columns come from instrumented traces on this checkout. Where a column says
NONE, that is a measurement.

**Companion documents.** `docs/LIVE_SYSTEM_MAP.md` classifies every module
(production / gate / research / experiment); this file traces the ARROWS
between them and what each one carries. `ROUND3_PRODUCT_TEST_MATRIX.md` holds
the seven missions and their funnels.

---

## 1 · The arrows

| # | Producer → Consumer | Data | Identity | Units / tier | Failure mode | Gate |
|---|---|---|---|---|---|---|
| 1 | prose → `mission.parse_mission` | `MissionSpec` (16 fields) | none | kg, kn, m; declared | unparsed items land in `.notes`; an unreadable clearance is said out loud | 1 |
| 2 | `MissionSpec` → `VesselConfig` | topology, manning, s/L | none | ratio | **was silent** — "catamaran" produced a monohull until 2026-09-01 | 1M |
| 3 | `MissionSpec` → `grammar.features_for` | frozenset | none | — | a mission asking for a tunnel gets one; one that does not, does not | REACHABILITY |
| 4 | mission + policy → draw box | `(lo, hi)` over 36 genes | none | gene units | **was a conformance tolerance** on Cp until 2026-09-01 (§3.2) | 1, 1b |
| 5 | box → `evaluate.sample_valid` | `(X, y)` | none | — | `MissionInfeasible` with a refusal TALLY; bounded at 200 draws/sample | 1 |
| 6 | `hull_family` → `parents.seed_for_mission` | ≤¼ of the population | parent name | — | a distorted parent can leave the critic's band (round-2 F17) | P5 |
| 7 | genome → `morphology_search.search` | repaired genome | none | — | climbs the MISSION's family inside the MISSION's box | MORPH |
| 8 | genome → `geometry.Hull` | stations, SAC, sections | **none** (implicit: genome + `n_stations`) | m, m² | `GeometryError`, named | 0K |
| 9 | `Hull` → `form_coefficients` / `formcheck` | Cp, Cm, Cwp, Cb, LCB, LCF | — | — | measures the surface the ladder floats (round-1 F1) | DELIVERED-FORM |
| 10 | `Hull` → `hydrostatics.solve*` | float state, GM, BM, trim | — | m, kg, deg; L1 | non-convergence is a named violation | 2 |
| 11 | float state → `energy` / `weights` | mass budget, Wh/NM | — | kg, Wh/NM; L1 ±σ | scantling refusal returns as an `Evaluation` (round-2 F20) | 6 |
| 12 | float state → `resistance` | Rt ± σ, method receipt | — | N; L1 | validity flags + envelope receipts | 2, RT |
| 13 | `Hull` + spec → `propulsion.rows_for` | 2 constraint rows | — | kW, m | a lever the hull lacks contributes nothing (round-1 F4) | PROP |
| 14 | `Hull` + family → `morphology.critique` | `shape` row + findings | — | — | unmeasurable shape is `INFEASIBLE_G`, never a pass | MORPH |
| 15 | all of the above → `Evaluation` | 11 `g` rows, badges, targets | `params` (no hash) | mixed; L0/L1 | `binding_rows()` separates measured from unmeasurable | 1C |
| 16 | `Evaluation` → `optimize.pareto_front` | front + `binding` tally | — | — | empty front DIAGNOSES itself (`why_empty`) | 1b |
| 17 | genome + mission → `certify` | verdict, `cfd_candidate` | **`genome_sha256`** | — | ACCEPT / MARGINAL / REFUSE, reasons named | DC |
| 18 | `Evaluation` → `cfd/manifest` | the one vessel description | **`genome_sha256`** | SI, per-field | `n_stations` NOT recorded (§3.3) | VM |
| 19 | `Hull` → `cfd/case.hull_to_stl` | STL | **`stl_sha256`** + `_shipped` | m | watertight is FATAL; closure fixed round-3 | 2F |
| 20 | `Hull` + speed → `admissibility.screen` | meshability verdict | — | cells | reported by `certify`; does NOT cover closure | 2A, DC |
| 21 | case → `run-case.sh` → `cfd/post` | forces, GCI | `stl_sha256` | N; L3 | settled-drag verdict, drift bar | 2S, 2M |
| 22 | runs → `harvest_cfd_anchors` → `cfd_kb` | anchor book | `stl_sha256` only | N | **no genome id on a CFD record** (§3.3) | CFD-KB |
| 23 | `cfd_kb` → `resistance` | a NOTE | — | report tier | deliberately not applied | CFD-KB |
| 24 | `cfd_kb` → `cfd/preflight` → `planner` | refuse-or-proceed | `stl_sha256` | — | planner is RESEARCH; not on the production CFD decision | PREFLIGHT |
| 25 | `Hull` → `buildability` / `unroll` / `export` | panels, DXF, STEP | `genome_sha256` in the export receipt | m, mm | refuses a radiused bilge BY NAME | 0B, 6D, 6M |

---

## 2 · The performance ladder (§37)

MEASURED on this checkout, 12 m brief:

| stage | ms |
|---|---|
| L0 `grammar.check` | 0.241 |
| `Hull(x)` build | 0.068 |
| morphology critique | 0.451 |
| **L1 `evaluate`** | **13.186** |
| `form_descriptors` | 15.453 |
| `closed_mesh` 80×16 | 19.241 |
| `certify` (with `cfd_candidate`) | 184.692 |
| feed `sample_valid(25)` | 670 |
| search `pareto_front(48×15)` | 14 388 |

`L0 ≪ L1 ≪ certify ≪ search` holds, and nothing expensive sits in a cheap
stage: `evaluate` contains no subprocess, no CFD and no file I/O.

---

## 3 · Where the arrows are still weak

### 3.1 · Identity is genome-deep and stops at the STL

`contract.genome_sha256`, `certify` and `export` compute the SAME float64-byte
hash (verified equal); `db.hull_id` is a deliberately different rounded
identity for de-duplication. `case.info` carries `manifest_genome_sha256` on
the `--case` lane and `stl_sha256` / `stl_sha256_shipped` always — the two STL
hashes are DELIBERATE and documented (delivered bytes vs. after
`split_bow_region` regroups facets; the vertices are identical).

**What is missing**: no `geometry_hash` (geometry identity is genome + an
unrecorded `n_stations`), and **a CFD anchor record carries no genome id at
all** — `stl_sha256` and `case_dir` only. A CFD result therefore cannot be
traced back to the design that produced it, which is ROUND 3 §7's requirement.

### 3.2 · The box that emptied the design space — FIXED

`mission_cp_band` returned `prismatic_target(fn) ± PRISMATIC_TOLERANCE`, a
CONFORMANCE tolerance used as a SEARCH box, and its own constant says it is
"NOT A DESIGN BAND". The tree held two Cp-vs-Fn relations and the outlier was
the one bounding the search. Fixed at `1311daf`; see §3 of the product matrix
for the funnel before and after.

### 3.3 · Arrows that carry less than they claim

- **22** — a CFD record cannot name its genome.
- **18** — the manifest does not record `n_stations`, so two different
  surfaces from one genome are identity-identical.
- **24** — the theory-first preflight gates `planner` (classified RESEARCH)
  and the `--stl` CLI, not `certify.cfd_candidate`, which is what actually
  decides that a solve is worth buying.

---

## ADDENDUM — 2026-09-02: three arrows repaired, one weak arrow re-described

§3 of this map listed the weak arrows. Three of them carried traffic that was
being dropped, and the drop was invisible to a fully green suite.

| arrow | was | now |
|---|---|---|
| `mission → grammar box` | a brief's CONSTRUCTION METHOD had no field to land in; "plywood" reached nothing | `MissionSpec.build_method` → a compiled box (`roundness` pinned, flare/forefoot narrowed) |
| `mission → sample_valid` | a REQUESTED architecture was held at its no-op default: 40 of 40 tunnel briefs drew no tunnel | feature bundles wired in, on a SPAWNED generator so every existing seeded brief is bit-identical |
| `mission → propulsion credit` | `prop_tunnel_recess_m` unset ⇒ `min(declared, drawn)` = 0 on hulls drawing 0.15–0.25 m | unstated ≠ declared-zero, on the tunnel drive only |
| `CFD case → anchor book` | `stl_sha256` + `case_dir` only — a result could not name its design | `genome_sha256` carried from `case.info`; `cfd_kb.same_design` |
| `translate → vessel` | the degrade was NOTED, not PERFORMED | the refusal now sets the monohull floor and discards the prose inference |

**The map's own §3.1 gap is now half-closed, and the remaining half is
smaller than it was written.** A CFD anchor can name its design. The
`geometry_hash` noted as missing is *less* load-bearing than that entry
implied: `write_resistance_case` already cross-checks the manifest's
displacement against the STL it actually writes, and refuses a genome that
does not match the hull it is meshing ("the wrong manifest is two boats in one
directory"). What is genuinely unrecorded is `n_stations` — geometry
RESOLUTION, not geometry identity.

**One arrow was re-described rather than repaired**, because the repair is
Gate 6D's and §50 forbids closing it: `geometry → manufacturing`. The
sheet-kit product class is real in the grammar and unreachable in production.
Measured at the corner `kit_buildability`'s docstring names (flare 0,
forefoot 0, warp ≤ +8°): **8.3–78 mm** at mission-drawn proportions, 152–1475
mm on the `formcheck` reference cases, against a 5.0 mm bar. That is
consistent with — not a refutation of — Gate 6D's recorded 124.1 mm watermark;
several readings are BETTER than it. The corner is a joint corner including
**proportions**, and the three dials the docstring names do not define it.

**A new arrow was added to this map by the fix, and the sweep caught it
immediately**: `mission → ui.server.mission_key`. `build_method` joined the
cache key automatically (the key is derived from the dataclass) with no
alternative value declared, so *"does it move the key?"* had gone unasked.
Two briefs differing only in build method are different design problems and
must not share a fitted generator.
