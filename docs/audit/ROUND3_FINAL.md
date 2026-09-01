# ROUND 3 — FINAL: NavalAI as a product-development system

**Date:** 2026-09-01/02 · **Tree:** `master` · **Instruments:**
`python -m pytest tests/ -q`, `python -m navalai.gates`,
`python scripts/gap_sweep.py`, `python scripts/product_test.py`,
`python scripts/reconcile_gaps.py`.

Companion deliverables: `ROUND3_SYSTEM_MAP.md` (the 25 arrows),
`ROUND3_PRODUCT_TEST_MATRIX.md` (the seven missions).

---

## 1. The headline metric, and the instrument error that nearly buried it

**MISSION → VALID DESIGN RATE, via the product's own design route:**

| # | brief | feed (40 draws) | **SEARCH** | route | refused? |
|---|---|---|---|---|---|
| P1 | simple displacement monohull | 3 | **48** | mould | — |
| P2 | coastal houseboat | 3 | **48** | mould | — |
| P3 | catamaran | 7 | **48** | mould | — |
| P4 | tunnel-stern river cruiser | 0 | **41** | mould | — |
| P5 | hard-chine plywood launch | 2 | **45** | mould | — |
| P6 | wave-piercing cruiser | 2 | **48** | mould | — |
| P7 | 30 m / 40 kn / 500 t submarine | — | **0** | — | **yes, both routes** |

**6 of 6 feasible briefs deliver designs. The 7th is refused, with reasons,
by BOTH production routes** — the feed with an L0 tally (`freeboard.abs`
×2946, `freeboard.rel` ×2133, `L/B` ×1279 …), the search with *"no design
satisfied the brief in 1440 candidates … freeboard=1440, gm=1440, …"*. That
symmetry was checked explicitly, because a search that answers where the feed
refuses would be the worst false green available here.

Two corrections had to be made before that table could be believed, and both
were in the measuring instrument, not in the product:

* **`buildable = 0` on all seven missions was an artefact.** The harness
  called `buildability.shell_complexity` — a geometry metric defined only on
  the two-strip ruled surface, which therefore *refuses by design* any hull
  with `roundness > 0` — and labelled the refusal "not sheet-developable".
  It had committed the mislabelled-metric defect it exists to catch. The
  meter that answers the question is `kit_buildability`, and it answers with
  a **route**: `mould` or `sheet-kit`. A mould boat is a boat. Corrected,
  `buildable == all-rows-ok` for every mission.
* **The harness measured the sampler, not the product.** `P4 = 0` was a
  statement about uniform draws. NavalAI's design route is a *search*;
  `pareto_front` returns 41 designs for the same brief, carrying a real drawn
  tunnel (`tun_w` 0.065). Reporting the feed's yield as the product's rate
  would have libelled the system on the strength of the wrong instrument.

> The rate above is **valid designs**, meaning: L0-admissible, floating,
> hydrostatically solved, every constraint row satisfied, buildable by a named
> route, watertight at 80×16 and 200×40, and CFD-*admissible*. **Admissible is
> not validated.** No number in this document is a CFD result.

## 2. What was actually wrong — the defect class of Round 3

Every defect found this round has one shape: **the brief says something, the
parser hears it, and the design path then draws as though it had not been
said.** Not one was visible to a fully green test suite.

| # | brief said | parser heard | design path did | fixed |
|---|---|---|---|---|
| 1 | "plywood" | *nothing* — no field existed | drew `roundness ~ U[0,1]`; the unroller refuses `roundness > 0` **by name**, so every design served for a plywood brief was provably un-kittable and the kit meter *raised* instead of returning a number | `MissionSpec.build_method` + a compiled **box** |
| 2 | "protected prop" | `drive='tunnel'`, `features={'tunnel'}` | held `tun_w/tun_crown/tun_len` at no-op defaults — **40 of 40 hulls with no tunnel**, 9 of them then killed by `row:prop_space`, the exact constraint a tunnel exists to satisfy | feature bundles wired into `sample_valid` |
| 3 | "protected prop" | `drive='tunnel'` | left `prop_tunnel_recess_m` at its dataclass default `0.0`, so `min(declared, drawn)` credited **0.000 m** on hulls drawing 0.15–0.25 m of tunnel | unstated ≠ declared-zero, on the tunnel drive only |
| 4 | — | — | a CFD anchor record carried `stl_sha256` and `case_dir` and no genome, so a result could not name the design that produced it | `genome_sha256` in the harvester; `cfd_kb.same_design` |

Defect 2 is the instructive one: `apply_feature_bundles_inplace`'s own
docstring already records this defect **twice** — for the exploring stream,
then for `optimize.pareto_front`. The product feed was the third site and had
never been wired. A defect with a written history repeated itself in a
neighbouring file.

Two properties were preserved throughout and are worth naming, because they
are what made the fixes safe rather than merely correct:

* **Boxes, not rejections.** A build method compiles to a *bound* on the
  search, the governance kernel's own idiom ("a length ceiling becomes a
  BOUND, not a rejection"), applied to manufacturing. The search never spends
  evaluations outside the envelope.
* **Stream safety, twice over.** Feature bundles draw from a *spawned*
  generator, so the legacy core block consumes the same uniforms it always
  did; and the helper returns immediately on an empty feature set. Every
  existing seeded brief draws bit-identically. Narrowing a box changes no RNG
  position at all.

## 3. What was NOT fixed, and why that is the correct outcome

**§50 forbids closing the RED gates, and none were closed.** Classification
only:

| gate | watermark | bar | why it is red | class |
|---|---|---|---|---|
| **2M** | `NONE` — unreproducible | KCS EFD 3.711e-3 | the run that carried the old figure was deleted; the ledger records `NONE` rather than quoting a dead directory | **needs compute** (review 2026-09-06) |
| **2U** | 21.7 | — | mesh robustness against the bar it claims, not the checkMesh proxy | **needs compute** (review 2026-09-06) |
| **4F** | 79.33 | — | raw generator distribution | **needs data/training** |
| **6D** | 124.1 mm | 5.0 mm | **25× out.** Intrinsic shell twist, measured not to be unroller error: transverse seams move the metric < 0.1 mm | **needs kernel work** |
| **0E5C-CAP** | 3 of 7 series | 7 | recorded series evidence not yet expressible | **needs data** |

Gate 6D deserves a specific note, because the plywood fix ran straight into
it. `kit_buildability`'s docstring describes a low-twist corner measuring
4.6–5.0 mm. **That corner does not reproduce at mission-drawn proportions.**
Measured, hulls projected onto the documented corner (flare 0, forefoot 0,
warp ≤ +8°): **8.3–78 mm**. On the `formcheck` reference cases: 152–1475 mm.

This is *not* a refutation of the docstring — Gate 6D's own test records the
reference hull at **124.1 mm, 25× out, RED by record**, and the readings above
are consistent with it (several are *better* than the shipped watermark). The
corner is a joint corner including **proportions**, and three dials do not
define it. The honest conclusion: the sheet-kit product class is real in the
grammar and unreachable in production, and it is unreachable for a reason that
already has a red gate and an owner. **The bar was not touched. No threshold
was lowered anywhere in this round.**

Standing seam findings, unchanged at **3, all P3, all on the `split` stern**:
57 open edges at 80×16, 141 at 200×40, and BM off 0.532% against a 0.1% bar at
the shipped 41 stations. All three are contained by the same fact —
Gate REACHABILITY proves the `split` genes are **withheld from every
production draw**, so no shipped hull carries any of them, and
`write_resistance_case` refuses an open shell outright. They must be resolved
*before* that stern is promoted, not after.

## 4. State of the tree

* **Gap register:** 123 rows — 117 closed, 3 open, 1 needs-human, 2 retired.
  The open rows are compute (F16/F17, Gates 2M/2U, review 2026-09-06) and
  human judgement (I13/N6). **The register cannot be closed by code**, which
  is why the seam sweep exists: it targets the defect class the register does
  not model.
* **Gate SWEEP:** 13 probes, 3 declared P3 findings, no new seam defect. A
  probe that raises becomes a finding — never a silent skip.
* The `cache` probe caught defect 1's own side effect the moment it landed:
  `build_method` joined `ui.server.mission_key` automatically (the key is
  derived from the dataclass) with no alternative value declared, so *"does it
  move the key?"* had gone unasked. That is the instrument working.

## 5. What is owed next, in order

1. **Gates 2M and 2U are up for review 2026-09-06** — both are compute, both
   on the Mac simulation node. 2M's next experiment is **free sinkage and
   trim**; `rigidBodyMotion` is wired and `KG_ABOVE_KEEL_M` landed, so what
   remains is the run. Do **not** spend another 16 h on a longer solve: at
   3.40 flow-throughs drift is 0.31% and C_T is flat.
2. **A second benchmark anchor.** KCS shares no chine, transom or spray
   physics with the SKUs. Gate 2M green is *not* small-craft validation, and
   this document does not claim it.
3. **The CFD learning loop** (Gen 0 → CFD → KB → Gen 1) is now *traceable* —
   defect 4 gave a result the ability to name its design — but is **not yet
   demonstrated**. Proving that a harvested anchor measurably changes the next
   generation is owed, and is not claimed here.
4. **The `split` stern**: close the surface and resolve the BM discretisation
   *before* promoting it out of withheld.

---

## 6. Final validation — what was actually run, and what it said

| instrument | result |
|---|---|
| `python -m navalai.gates` | **EXIT 0.** Every gate GREEN except the five RED-by-record ones |
| `python -m pytest tests/ -q` | 2163 passed, 14 skipped (the one failure it found is fixed below) |
| `python scripts/gap_sweep.py` | 13 probes, 3 declared P3 findings, no new seam defect |
| `python scripts/product_test.py` | 6 of 6 feasible briefs deliver; the 7th refused by both routes |
| `python scripts/reconcile_gaps.py` | 123 rows — 117 closed, 3 open, 1 needs-human, 2 retired |

The five REDs are 4F, 2M, 2U, 6D and 0E5C-CAP — exactly the five §50 names,
each carrying its watermark, owner and review date. **None was closed and no
bar was moved anywhere in this round.**

### Two defects the final validation itself found

Running the instruments end to end found two things that reading them could
not. Both are recorded here because they are the argument for running them.

**1. The product's front door had no tests and no gate.**
`test_every_test_file_is_owned_by_a_gate` failed on the new CLI test file, and
the reason it was new is the finding: `docs/PRODUCTION_CORE.md` lists
`design_report.py` as core, *"the CLI face"*, and **nothing in `tests/`
imported it.** That is exactly how `--reference` came to be declared,
documented in `--help`, and never read, while `--mission` certified the
*reference hull* under a header naming the user's brief — a 2643 kg hull and a
`VERDICT: REFUSE` for a 1.8 t plywood launch, none of it about the boat that
was asked for. The CLI now designs (2240 kg, fairness 278.8 → 28.0, wetted
19.0 → 13.1 m², `MARGINAL`), and **Gate CLI** owns it.

**2. The gate registry carried this codebase's own recurring defect.**
The ladder printed Gate 0E5C-CAP's scope and its ledger entry *on the same
line*, and they disagreed: scope *"2 of 7 … no aft deadrise warp … beta_mid
capped at 25 deg"* against a ledger recording *"3 of 7 series expressible"*
and, in its own words, *"the count moved 2 → 3 of 7 on exactly this."* The
scope described the PRE-fix state on three counts, and the stale copy is the
one the ladder **prints**. A number declared twice, in the one place a reader
goes to find out what is true. The scope now states the clause and names the
ledger as the single home of the count — the gate stays RED, and nothing about
its bar moved.

Neither was visible to a green suite. The first needed the fence to be *run*;
the second needed the scope and the ledger to be *printed together*.
