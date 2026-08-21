# End-to-end alignment audit — 2026-08-21

**Ask:** align `docs/BUILD-PLAN.md`, the gates, `PLM.md`; validate the flow end
to end; one source of truth, no contradictions, ideas → design → production.

**Method:** ask the artefact that owns each question (`python -m navalai.gates`,
`scripts/reconcile_gaps.py`, the suites, and a LIVE run of the product flow),
never a document. Everything below was measured on this checkout, not read.

---

## 1 · A GATE NAME DECLARED TWICE — seven of eight letters

The physics ladder in `GATE2-PHYSICS-STACK.md` was numbered `2A`..`2H`. Seven
of those letters were **already executable gates in `navalai/gates.py` meaning
something else**:

| letter | the runner means | the document meant |
|---|---|---|
| 2A | CFD-admissibility screen | hydrostatics |
| 2B | Blender generation (negative result) | Wigley free surface |
| 2C | campaign classifier | DSYHS |
| 2D | refusal of pathological hulls | KCS / RANS |
| 2F | STL forensics | planing |
| 2G | **"the KCS STL is on disk"** | **waves / RAOs / added resistance** |
| 2H | surface repair on import | wind |

2G is the one that bites: the runner prints it SKIPPED when the gitignored
benchmark geometry is absent — loudly, by design — and a reader holding the
document's meaning reads that as *seakeeping is unverified*. `gates.py` itself
used both meanings a dozen lines apart.

This is the project's signature defect (A NUMBER DECLARED TWICE) applied to
identifiers. **FIXED:** the executable rows keep their letters (they are the
incumbents — README, the ledger and eleven test modules cite them); the physics
ladder moved to `2-PHYS-A`..`2-PHYS-H`. **FENCED:**
`test_no_document_renames_an_executable_gate_letter`.

## 2 · Sixteen documents with no authority role

`docs/BUILD-PLAN.md` §0 encodes the law *"one authority per question"* — and
`docs/audit/` (16 files) **had no row in the table at all**: no declared
authority, therefore no "must NOT contain" constraint. The collision in §1 was
introduced by a file in that directory. An unlisted document is an ungoverned
one.

**FIXED:** `docs/audit/*` and `docs/audit/STATUS.md` now have rows, and the
law gained its third clause — *a number lives in one place; so does a work
item; **and so does a gate NAME***.

## 3 · THE PRODUCT SEARCHED A DESIGN SPACE IT CANNOT BUILD

This is the ideas → design → production finding, and it was found by RUNNING
the flow rather than reading about it.

`scripts/demo_mission.py` **crashed at the manufacturing stage**: the optimiser
returned `roundness` 0.045 and `unroll.hull_panels` refused it — *"a radiused
bilge is not a two-panel developable shell."* Measured, not anecdotal:

    ungoverned Pareto front, flagship mission : unroll REFUSED 19 / 19
    60 draws from the same mission            : roundness > 0 on 60 / 60
                                                (median 0.541), refused 60 / 60

**The ladder was validating, badging and ranking a design space that is 100%
unbuildable in the one material this product is made of.** The 2026-08-21
reframe to plywood-only reached the BENCHMARK — Gate 2M demoted — and never
reached the SEARCH SPACE.

Why nothing caught it:

- `CONSTRAINT_NAMES` has `bend_radius` (can the ply bend that tight) but no row
  asking whether the shape can be made from flat sheet **at all**.
- `certify` DOES measure `non_developable_frac` — and feeds it only to the
  **CFD-candidacy score**. It ranked hulls without ever refusing one.
  **A receipt is not a bar.**
- `unroll` refuses at the shop door, which is the last possible moment.

**FIXED** in governance, where a product position belongs. `DesignDNA` gained
`construction` (`sheet-developable` | `moulded`), the reference constitution
declares the CNC kit path, and `compiler.box()` tightens `roundness` to 0 —
a BOUND, because developability is decidable before a drop of physics is
computed, so evaluations spent above 0 are pure waste.

**And it costs nothing, which is the part worth pinning.** The SAME 19 front
hulls with roundness forced to 0:

    ladder ok as drawn (roundness > 0) : 19 / 19
    ladder ok with roundness = 0       : 19 / 19
    unroll ACCEPTS with roundness = 0  :  0 / 19  ->  19 / 19
    hard-chine energy penalty          : +0.8 % median

### A near-miss worth recording

Pinning roundness emptied the governed Pareto front (3 → 0) and my first
reading was "hard chine is infeasible for this mission". It was wrong:

    budget                governed, no pin    governed, PINNED
    pop 24  x 10 gens            3                   0
    pop 48  x 40 gens           28                  25
    pop 64  x 80 gens           62                  64

**A SEARCH-BUDGET artefact, one step from being written up as an empty design
space** — the same error as the earlier stageF "convergence defect", in the
opposite direction. The demo's pop 24 × 10 gens is itself under-powered.

## 3b · THE GOVERNANCE KERNEL IS UNWIRED — every caller is a test

Finding §3 led here, and this is the headline. Grepping every non-test caller
of the governance kernel in the tree:

    grep -rn "reference_policy\|compile_policy" --include='*.py' .
      | grep -v tests/ | grep -v navalai/policy/

returns **NOTHING that calls them.** The only hits outside `tests/` and the
policy package itself are DOCSTRINGS in `optimize.py` and `evaluate.py`
describing the parameter.

So: `navalai/policy/` is Gate V3.0 — the legal envelope, the design DNA, the
ratchet law, the parameter box, the appended constraint rows — implemented,
documented, and covered by 51 tests. **And nothing that ships ever compiles a
constitution.** Not `design_report.py`, not `certify.py`, not `ui/server.py`,
not `demo_mission.py`, not any script in `scripts/`. `optimize.py` and
`evaluate.py` both take `policy=None` and every real call site takes the
default.

**The legal envelope and the design DNA currently govern nothing that ships.**

That is why §3 happened at all: the constitution has declared the CNC sheet-
goods kit path since it was written, and the search never saw it, because the
search is never handed the compiled policy. Fixing the box (§3) was necessary
and is not sufficient — a bound nothing consumes is a receipt, which is the
same defect one level up.

### WIRED 2026-08-21, on operator instruction ("go ahead, fix everything")

Threaded through the four call sites that decide what the product proposes and
what it certifies, each `policy=None` by default so an ungoverned run executes
the same code and produces the same numbers:

| call site | what the constitution reaches |
|---|---|
| `evaluate.sample_valid(..., policy=)` | **the draw box** — the generative feed `agents.run_plm` fits its Genome on |
| `agents.run_plm(..., policy=)` | the feed above, plus the validator's appended rows |
| `certify(..., policy=)` | the appended rows (this lane is HANDED a hull, so the box does not apply) |
| `optimize.pareto_front(..., policy=)` | already accepted one; now actually given one |

MEASURED immediately after wiring, flagship mission, 30 draws each:

    ungoverned : roundness max 0.9937   unroll ACCEPTED  0/30
    governed   : roundness max 0.0000   unroll ACCEPTED 30/30

`sample_valid` is the load-bearing one and the reason is structural: it is
where the generative model is FITTED. Drawing ungoverned and rejecting
afterwards aims the model at the middle of an unbuildable space and then
discards its output one hull at a time in the LAST stage, the engineer agent,
with the audit trail reading "rejected" over and over. **A bound moves the aim;
a filter only moves the survivors.**

New CLI surface: `scripts/design_kit.py` (governed mission -> hull -> STL ->
stitch-and-glue panels -> nested BOM) and `python -m navalai.design_report
--constitution kit-line-v3`. `design_report` defaults to `none` so no number it
already printed moves silently.

### What the wiring did NOT fix, and it is the real blocker for cut files

Running the governed lane end to end produces a buildable hull and then
REFUSES to call the panels a cut file:

    STITCH AND GLUE: 2 developable panel(s)
      bottom-stbd  refold deviation max    21.2 mm  OVER the 5 mm bar
      topside-stbd refold deviation max   221.5 mm  OVER the 5 mm bar

That is **Gate 6D**, RED and ledgered (watermark 124.1 mm on the reference
hull). The panels are GEOMETRY, not release-grade cut files: refolded onto the
hull's moulded surface they miss by two orders of magnitude more than the
BuildPlan 12.3 bar. Cutting plywood to them would produce panels that do not
close on the chine. This is now printed with its bar beside it, because a
millimetre figure with no bar reads as a pass.

### The budget is part of the wiring, not a tuning knob

### The old caution, kept because it is why the budget default is what it is


Wiring it in CHANGES WHAT THE PRODUCT ACCEPTS, and that is an owner decision,
not a tidy-up. It is also not free, and the cost is measured (§3): under the
reference constitution the flagship mission needs a materially larger search
budget before the front fills — 0 members at pop 24 x 10 gens, 64 at pop 64 x
80 gens. Turning governance on and leaving the demo's budget at 24 x 10 would
present an EMPTY Pareto front as the product's answer.

### The recommended sequence, cheapest first

1. Raise the default search budget where a governed run is intended, using the
   measured table in §3 — never below the point where the unpinned and pinned
   fronts agree.
2. Give `design_report` and the UI an explicit constitution argument,
   defaulting to ungoverned so no existing number moves silently.
3. THEN make the reference constitution the default for the SKU lanes, and
   record the before/after front sizes as the receipt.

The architecture's own clause is what makes this safe to do incrementally:
every policy call site sits behind `if policy is not None`, so an ungoverned
run executes the same CODE, and deleting the constitution must leave every
physics result bit-identical.

## 4 · Contradictions between the plan and the reframe

Both in §11.4, both corrected in place with the superseding measurement beside
them (PLM §3 step 7):

- *"KCS is not demoted"* — **it is**, by operator direction, and the registry
  and ledger say so with a fence against drift.
- DSYHS marked **OWED** — it is **HELD**: 51 models, 742 points, publisher MD5.

`PLM.md` §1 still listed the anchors as "(Wigley, Hulme, KCS)"; it now names
DSYHS and marks KCS SOLVER VERIFICATION ONLY. §0.5's calibration row now says
what a KCS anchor buys (the numerics) and what it does not (a plywood boat's
resistance).

## 5 · The literature claim was refuted

See `GATE2-PHYSICS-STACK.md`. The forensic hunt concluded a structural absence
AND invented a mechanism for it; Compton's 1986 USNA series (hard chine *and*
round bilge, Fn 0.10–0.60) refutes both. Struck, not deleted. Lesson recorded:
**a negative result about the literature is a claim about the SEARCH.**

## 6 · Open, recorded, NOT fixed here

- **Gate RT is RED with no ledger route.** `test_resistance_is_bit_identical_to_the_golden`
  fails on arm64 by construction (530/4906 keys, one-ulp IEEE-legal moves;
  golden recorded on x86_64). The ledger only judges gates with `suite is None`,
  so a suite gate **cannot** be recorded expected-red. On this machine the
  ladder is therefore permanently non-zero and cannot distinguish this from a
  new regression. The honest fix is a per-architecture golden, not a softened
  test. Gate XP owns the cross-machine distinction and is GREEN.
- **`R-PBM nan/nan kN/m²` — investigated, and NOT a product defect.** The
  clause is fail-closed BY DESIGN: with no `lwl_m`, Eq (8)'s length-dependent
  floor cannot be computed, so `iso12215.assess` returns `passed=False` with
  the reason spelled out rather than assessing on the base pressure alone. The
  NaN is a refusal marker, not a fabricated number. `evaluate.py` passes
  `lwl_m=hs.lwl_eff` (the FLOATED effective length), so the supported lane is
  correct. The only affected surface is `scripts/demo_mission.py`, which omits
  the argument AND whose printer drops the finding's `detail`, so the refusal
  renders as a bare `nan/nan` with no reason. That script is marked LEGACY
  (C-27) "do not extend"; the printed refusal losing its reason is the defect,
  and it is cosmetic and confined to it.
- **The KCS coarse solve died** — pathological cell, `Time` frozen at 1.50613,
  `deltaT` 3.4e-09, Courant max pinned 4.993. Stopped. The monitor never
  warned: `pgrep` said RUNNING and the fatal-grep counted 0, both correct and
  both meaningless. See `docs/LESSONS.md`.
- 5 gap rows remain open (E5, F16, F17, I1, I13) of 123.

## 7 · What was verified green

    tests/test_end_to_end_flow.py            14 passed  (~2 min)
    tests/test_policy.py                     51 passed
    python -m navalai.gates                  all suites GREEN except Gate RT
                                             (above) and the four ledgered
                                             expected-reds: 2M, 2U, 4F, 6D
    scripts/reconcile_gaps.py                115 closed / 5 open of 123
    python -m navalai.design_report --case a  runs, refuses nothing silently

The end-to-end suite is the substantive check on PLM §0.5's *"exists end-to-end
today"*: mission → validated design → exported solid → CFD STL → L2 panel mesh
→ resistance-to-energy inversion → ISO rules → BOM → arrangement, each asserting
that the artefact is the SAME hull the ladder validated.
