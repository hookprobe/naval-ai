# §7 — the meshability screen, criterion by criterion (2026-08-20)

The directive asks for a table with, per criterion: equation, physical
reason, source, measured evidence, false-positive rate, false-negative
rate. This document exists because **that table cannot honestly be
computed today**, and the reason is worth more than the table would be.

## The finding: the positive class is empty or invalid

An FP/FN rate needs a corpus with labelled failures. Every mesh corpus in
`data/` was examined:

| corpus | N | meshed (harness bar) | meshed (runner bar) | screen verdicts recorded | needed layer backoff |
|---|---|---|---|---|---|
| `gate2u-n74-mesh.json` | 74 | **74** | **74** | none (all null) | 9 |
| `gate2u-16gene-mesh.json` | 25 | 23 | 23 | yes | 0 (ladder pinned OFF) |
| `gate2u-campaign-backoff-mesh.json` | 16 | 13 | 14 | none (all null) | 10 |

Three things follow, and each blocks the table independently:

1. **With the shipped configuration, there are no failures to predict.**
   The 74-hull corpus ran with the layer ladder ON — the way the pipeline
   actually runs — and meshed 74 of 74. Nine hulls needed a backoff rung
   and got one. A predictor cannot be scored against an empty positive
   class.
2. **The corpus that HAS screen verdicts has an invalid label.** The
   25-hull campaign pinned `LAYER_BACKOFF=0` by design, so its two
   "failures" (h011, h012) are RUNG-0 outcomes. Block 1 then measured both
   meshing CLEAN at n=6 — 13 and 12 wrongly-oriented faces and skew 247 /
   9.9 at n=7, falling to 0 and 3.5 / 4.5. **They are not geometry
   failures.** Scoring the screen's ability to predict them is scoring it
   against a configuration artefact, which is exactly what the earlier
   "the screen is at chance" result did.
3. **The corpora WITH the ladder carry no screen verdicts at all** (null
   on every row), so even the 3 backoff-campaign failures cannot be
   attributed to a screen call.

## The second finding: two bars, and the record reads the softer one

`meshed` (harness) and `meshed_runner_bar` (what `run-case.sh` enforces)
DISAGREE on one hull of 16 — hull 8, which carries 2 wrongly-oriented
faces against the runner's fatal bar of 5. The harness calls it failed and
the runner would have run it. `scripts/mesh_robustness.py` already
documents this class ("two counts, one defect, and the gate and the record
read different ones"); what is new is that **a published rate depends on
which one is quoted**: 13/16 against 14/16. Any Gate 2U rate must name its
bar. The 74- and 25-hull corpora happen to agree, which is why this went
unnoticed.

## What the criteria are, and what is known about each

The screen's criteria and their bars live in `navalai/admissibility.py`
with their derivations. What can be stated honestly today:

- Their bars were **re-based on measured anchors** in the 2026-08-19 pass,
  and one criterion (`draft_over_hull_cell`) was **demoted to a pure
  receipt** for being 0-for-4 as a predictor. That demotion is the only
  criterion-level predictive measurement this project has made.
- The screen's aggregate call was measured **at chance** for rung-0
  checkMesh outcomes (BUILD-PLAN §11.8), on the invalid label above.
- The h011/h012 investigation scanned **83 descriptors** with the repo's
  own permutation instrument (20,000 permutations) and returned best
  family-wise p = 0.601 — no descriptor separated those two hulls from the
  23 that meshed. The best candidate beat the shipped screen on raw counts
  and was refused for having its threshold pinned to one failure's own
  coordinate.

## What would make the table computable

Not more criteria, and not a re-run of the same campaign:

1. **Screen verdicts recorded on a ladder-ON corpus.** The campaign runner
   must write `screen_verdict` and `screen_no_rescue` on every row of a
   run with the ladder enabled. The 74-hull corpus is otherwise ideal and
   would need only a re-score, not a re-mesh, if the genomes are recoverable.
2. **A label that means what the screen claims.** The screen predicts
   whether geometry is MESHABLE. The honest label is therefore "fails at
   EVERY rung" (`no_admissible_rung`), not "fails at rung 0". On present
   evidence that class has **zero** members in 74 hulls, which is itself
   the most important number in this document: with the ladder on, the
   shipped pipeline does not currently produce unmeshable geometry.
3. **If the class stays empty, the screen's job changes.** A predictor
   with nothing to predict is not a failing predictor; it is an
   unnecessary one — or, more usefully, a COST predictor rather than a
   feasibility one: which hulls will need a backoff rung (9 of 74 did) and
   therefore cost extra mesher time. That is a measurable target with a
   non-empty positive class, and it is the one this document recommends.

## Status

§7 is **BLOCKED ON EVIDENCE, not on work**, and deliberately not
satisfied with a table computed from a label that Block 1 invalidated.
The screen is unchanged; the directive's own instruction — "improve the
meshability screen only after understanding failures" — is being followed
by declining to improve it yet.
