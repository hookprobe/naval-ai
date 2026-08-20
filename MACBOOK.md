# MacBook Pro (M5, ~24 GB) — simulation-node runbook

Purpose of this machine in the project: **the CFD tier** — everything else
runs on fortress001.

## 0 · PARALLEL-WORK CONTRACT (read first — updated 2026-08-18)

Two Claude sessions work this repo in parallel. **Git is the coordination
layer; this section is the partition.** Before ANY work: `git pull`; push
small commits often; never rebase published history.

**fortress001 (linux) owns, this window:** `navalai/`, `tests/`, `docs/`
— the code-forensics consolidation plan (`docs/CODE_CONSOLIDATION_PLAN.md`;
live progress in `docs/audit/STATUS.md`, which fortress001 updates and
pushes after every landed item). If a file in those paths must change from
the Mac, land measured DATA instead and file the code change as a note in
STATUS.md.

**macOS owns:** `runs/` (gitignored evidence), `data/gate2u-*.json` (new
campaign rows — the fence now requires a geometry hash per row),
`data/gate-ledger.json` rows **Gate 2M / Gate 2U / Gate 3E only** (the
`owner` field marks them), and this file's §below work order.

**Mac work order (in value order):**
1. `bash scripts/install-hooks.sh` (hooks are path-stale after the repo
   moved; verify `git config core.hooksPath` points inside THIS clone).
2. **Gate 2U 16-gene re-campaign** — `python scripts/mesh_robustness.py
   --n 25 --seed 0 --np 10 --solve 2 --json data/gate2u-16gene.json`;
   update the Gate 2U ledger row (watermark, `calibration_void` removed,
   `measured_on` names the 16-gene genome + STL hashes).
3. **Gate 2M calibration** — the runbook below (`make_case.py --triplet`
   … `gate2m.py`); update the Gate 2M ledger row with the measured E%D
   and GCI. NOTE: `scripts/make_case.py --case a..f` is the NEW canonical
   genome lane (mission→evaluate→manifest→case, floats at the certified
   attitude); use it for any genome-hull run.
4. **C-06 metal check** — one `make_case.py --case a` case through
   snappy+interFoam: confirm the trimmed-attitude mesh behaves (layer
   coverage, no snap pathology). Record the verdict in STATUS.md.
5. **Gate 3E re-measure** — `tests/test_phase3.py`'s two expected-fail
   tests say the bar may now be met; run the suite, and if the 0.15 bar
   is met, retire the pair per their own instructions (ledger + gates row
   + tests in ONE commit).

**Merge rule:** ledger rows are per-gate (row-scoped edits — conflicts
only if both machines touch the same gate; don't). `data/baselines.json`
is fortress001's (regenerated 2026-08-18). On conflict anywhere: the
MEASUREMENT wins over prose; if two measurements clash, keep both with
machine labels and file it in STATUS.md.

## 0b · CFD VALIDATION LIST (Mac-owned, drawn 2026-08-18 after pulling 80294b2)

Fortress001's own STATUS.md line 4 says **"NO CFD runs"** — everything below is
work only this machine can do. Items 1-5 are fortress's work order in §0,
restated with what each is BLOCKED ON and what it must PRODUCE. Items 6-8 are
obligations created by the vessel/geometry work in `f18fcba` that §0 predates.

**A number is not delivered until it is in `data/gate-ledger.json` with a
geometry hash and a `measured_on` that names the genome.** A run directory is
deleted by `clean-runs.sh --purge`; a ledger row is not (gap N6).

### 1 — Hooks. NOT NEEDED, verified.
`git config core.hooksPath` already resolves inside this clone
(`/Users/robobostes/Documents/naval-ai/.githooks`). §0 item 1 is satisfied; do
not re-run `install-hooks.sh` blindly and repoint anything.

### 2 — Gate 2U 16-gene re-campaign. HIGHEST VALUE, and the watermark is VOID.
The ledger row says so in its own words: the recorded watermark was
**measured on the 15-parameter genome (pre-roundness)**, and the 16th gene
changes the sampled population, so that number "stays as HISTORY" and no
comparison is legitimate until it is re-based here. **The figure itself is NOT
repeated here — read it from the `Gate 2U` row of `data/gate-ledger.json`,
which carries its units, its bar, its owner and its review_by. A sentence
carries none of those and cannot fail.** (`tests/test_gaps.py::
test_no_document_restates_a_ledger_watermark` refused an earlier draft of this
very section for quoting it — the fence works.)

    python scripts/mesh_robustness.py --n 25 --seed 0 --np 10 --solve 2 \
        --json data/gate2u-16gene.json

PRODUCES: a new watermark, `calibration_void` REMOVED, `measured_on` naming the
16-gene genome and the STL hashes. The fence now requires a geometry hash per
row — a row without one is refused.

WHY THE RE-CAMPAIGN IS STILL NOT COMPARABLE TO THE OLD BATCH: the GENOME
changed, 15 parameters to 16. That is the ledger row's own stated reason and it
is sufficient on its own.

**AND A CAUTION I WROTE HERE FIRST TIME ROUND WAS WRONG — CORRECTED BY
MEASUREMENT 2026-08-18.** I claimed every round-bilge hull would now mesh at 6x
the girth density because `hull_to_stl`'s default moved from a fixed `nz=16` to
`stl_girth_resolution(hull)` (16 hard chine / 96 filleted). It does not. THE CFD
CASE PATH NEVER READS THAT DEFAULT: `write_resistance_case` calls
`stl_resolution()`, and the probe's own receipt records what actually shipped --
`stl_nx_shipped=600`, `stl_nz_shipped=120`. 120 already exceeds the new 96, so
the change is INERT here by construction. It governs the BARE default, which is
what `evaluate.l3_case_evidence` writes when it checks whether a recorded RANS
campaign is about this hull -- a different job. Cell counts in this campaign move
because the genome moved, not because the tessellation did.

### 3 — Gate 2M calibration. Watermark is the string `NONE`.
Use the NEW canonical lane, not the old `--stl` path: `make_case.py --case a..f`
runs mission -> evaluate -> manifest -> case and floats at the CERTIFIED
attitude (C-06). Then `--triplet` for the GCI, then `scripts/gate2m.py`.
PRODUCES: measured E%D against KRISO EFD 3.711e-3, and a Roache GCI over a
SETTLED triplet. Budget it as ~21x the coarse grid (~68.7 h), not ~12x — the
timestep is Courant-limited so a sqrt(2) finer grid also takes sqrt(2) more
steps. Anchor COARSE; `--anchor fine` puts both coarser members under this
project's own >=20 cells-per-wavelength bar.

### 4 — C-06 metal check. Cheapest item with a real verdict.
One `make_case.py --case a` through snappy + interFoam. Confirm the
TRIMMED-ATTITUDE mesh behaves: layer coverage, no snap pathology, no
zero-volume cells. This is the first time the manifest's attitude reaches a
mesh, and the forensics measured the recorded-never-applied error at
**+122.9%** — so this check is what proves C-06 actually landed in metal.
Record the verdict in `docs/audit/STATUS.md` (fortress owns the file; land a
note, not a code change).

### 4b — C-06 METAL CHECK: FIRST RESULT, 2026-08-18. The attitude is fine; the DERIVED LAYER COUNT IS FATAL.

`make_case.py --case a` (5 m hard-chine dayboat, 903 kg, trim -0.0095) derives
`n_layers = 6`, and that mesh is REFUSED by `run-case.sh`'s own quality bar. Same
hull, same certified attitude, same everything — only `n_layers` differs:

    n_layers      wrongly-oriented   max skew   non-ortho max   cells    verdict
    6 (DERIVED)         16             6.615       96.67       548516   FATAL
    5 (--n-layers)       0             3.025       69.95       532740   CLEAN

Bars are 0 zero-volume, 5 wrongly-oriented, 20 skewness. Both meshes had ZERO
zero-volume cells; the derived one fails on wrongly-oriented faces alone, at 16
against a bar of 5 — WORSE than the n=7 KCS case that dies at t = 0.0072 s
(10 faces). The failure signature is the documented one: PARTIAL STACKS. At n=6
coverage is 84.3% with 5.12 of 6 layers achieved; at n=5 it is 85.6% with 4.3 of
5. Full stacks and no stacks both mesh; partial stacks fold cells.

**SO THE C-06 VERDICT SPLITS.** The manifest's trimmed attitude reaches a mesher
and behaves — that half passes, and it is the half C-06 claimed. What does NOT
work is the generator's own default: the canonical lane produces an unsolvable
mesh unless a human overrides the layer count it derived.

**AND THE FIX ALREADY EXISTS IN THE TREE, UNWIRED.** `navalai/cfd/case.py`
exports `layer_backoff_ladder`. `scripts/mesh_robustness.py` imports it and
exposes `--layer-backoff` / `--cap-layers`, so the CAMPAIGN lane recovers from a
bad derived count automatically. `scripts/make_case.py` — the lane C-06 made the
production path — has ZERO backoff or retry (grep: 0 matches). This is a wiring
gap, not a missing feature, and it is a NOTE FOR fortress001 rather than a change
from here: `navalai/` is theirs.

Also RECORDED, not a bar: the case-a STL enters the mesher with 7
self-intersections. `run-case.sh` prints them and continues, by design.

CAVEAT ON READING THIS AS A GREEN LIGHT: case a evaluates `ok=False` at L1. It is
a legitimate mesh-behaviour probe (escalation does not require feasibility) and
it is NOT evidence that case a is a good design.

### 5 — Gate 3E re-measure. OWNERSHIP CONTRADICTION, do not act unilaterally.
§0 grants macOS "Gate 2M / Gate 2U / Gate 3E only (the `owner` field marks
them)". The `owner` field on Gate 3E reads **`ml-engineer`**, not
`cfd-engineer` as 2M and 2U do. So the prose and the data disagree about who
owns this row. It is also not a CFD quantity at all — it is a surrogate error
bar. RESOLVE WITH FORTRESS BEFORE TOUCHING IT. The measurement itself
(0.1471 against the 0.15 bar) is a draw landing 1.9% inside a measured 1.97x
seed spread, which is why the previous session held it.

### 6 — THE CATAMARAN INTERFERENCE TERM HAS NO EXPERIMENTAL ANCHOR.
New in `f18fcba`: `separation` now reaches `total_resistance`, so every
catamaran number this project reports is affected by an interference factor
that has NEVER been checked against water. Insel & Molland (1992) and Molland
et al. (1996) appear in `resistance.py` as reference COMMENTS and were never
transcribed. Self-consistency is not validation.

CFD CAN SETTLE THIS, and it is the highest-value NEW measurement available:
run two demihulls at a fixed s/L and compare against 2x the isolated demihull.
The prediction to test is sharp — measured on the analytic side, the
interference ratio bottoms at **0.7483 at s/L 0.300, Fn 0.25** (-25.2% against
two independent hulls) and rises to **+59.7% at Fn 0.40, s/L 0.200**. A CFD
point at either extreme is worth more than another KCS decimal.

### 7 — Free sinkage and trim is REACHABLE FOR THE FIRST TIME.
`manifest.free_motion` exists and `make_case.py --free-motion` consumes it, so
the G7 fix is finally on the wire. KCS Case 2.1 is towed FREE and we have
always solved FIXED; the viscous half being right (1.161x ITTC-57) localises
the remaining error to exactly what sinkage and trim move. `KG_ABOVE_KEEL_M =
0.2303` is now in `benchmarks/kcs.py` beside its EFD acceptance data (sinkage
-1.394e-2 m, trim -0.169 deg), so the number that used to exist only in a
comment is available. **CAVEAT: for a MULTIHULL, KG is a single-hull KG with
no bridge deck, so multihull GM is an UPPER estimate — do not use a free-motion
catamaran run to certify stability.**

### 8 — Second benchmark anchor: NTUA Series is a live candidate.
KCS shares no chine, transom or spray physics with the SKUs, so Gate 2M green
is not small-craft validation. The NTUA Series (double-chine planing, LOA
4.00-7.00 m, L/B 1.00-4.23, with model-test resistance, CG rise and dynamic
trim) is in our size band and IS chined. Caveat: it is a planing series and
`FN_MICHELL_MAX` is 0.45, so most of it lies outside our only validated
resistance model — its value is as a CFD/geometry anchor, not an L1 one.

## 1 · Get the repo onto the Mac

```bash
git clone git@github.com:hookprobe/naval-ai.git && cd naval-ai
```

(Offline fallback: `~/naval-ai-transfer.bundle` on fortress001 —
`git clone naval-ai-transfer.bundle naval-ai`.) Push Gate-2M results back on
a branch; fortress001 pulls them into the provenance DB.

## 2 · Base toolchain (arm64-native, no Rosetta needed)

Note for zsh (the macOS default): `#` is NOT a comment on an interactive
command line — never paste trailing `# ...` text, it becomes arguments.
Code blocks below are comment-free for that reason.

```zsh
xcode-select --install
brew install python@3.12 git
python3.12 -m venv ~/.venvs/naval && source ~/.venvs/naval/bin/activate
pip install numpy scipy pytest pymoo capytaine mujoco cadquery
python -m pytest tests/ -q
python -m navalai.gates
```

Expected: the suite green in a few minutes, then the gate table.

No test count and no gate count is written here on purpose (gap J8). This file
promised "93 passed, 14 GREEN gates" long after both had moved — the counts
are a function of the tree, so ask the tree: `python -m navalai.gates` is the
registry's single source, and `data/gate-ledger.json` carries every RED row's
measured watermark, owner and review-by date.

Two skips are EXPECTED on a fresh clone and are not failures: the KCS
benchmark geometry is not redistributed, so Gate 2G reports SKIPPED until you
run `python scripts/fetch_benchmark_geom.py` against the IGES you obtained
(see §4.1 below). That skip used to be invisible; it is a gate row now.

All of these publish macOS arm64 wheels (capytaine, mujoco, pymoo: PyPI;
CadQuery via the cadquery-ocp arm64 wheels). If `cadquery` pip resolution
fails on a brand-new Python, fall back to `pip install cadquery-ocp-novtk
cadquery` or conda-forge.

## 3 · OpenFOAM (the reason this machine exists)

Native Apple Silicon build — gerlero/openfoam-app (OpenFOAM v2606-era,
bundles OpenMPI, installs via Homebrew):

```zsh
brew install --no-quarantine gerlero/openfoam/openfoam
openfoam
```

`openfoam` (no arguments) opens an OpenFOAM session; run this INSIDE it —
all four must resolve:

```zsh
which interFoam blockMesh snappyHexMesh mpirun
```

One-shot alternative without entering the session:

```zsh
openfoam bash -c 'which interFoam blockMesh snappyHexMesh mpirun'
```

Docker fallback (if the app route misbehaves): `gerlero/openfoam-docker-arm`
or `docker run -it opencfd/openfoam-default` (arm64 images exist).

## 4 · The Gate 2M campaign (run in this order)

1. **Benchmark geometry**: download KCS (and optionally JBC) IGES + tank data
   from the Tokyo 2015 workshop site (t2015.nmri.go.jp). Model scale
   (KCS: 1:31.6, L≈7.28 m) — matches the published validation practice.
   Then `python scripts/fetch_benchmark_geom.py --iges downloads/KCS.igs`,
   which runs the measured conversion recipe and checks the result against
   `data/benchmark_geom/CHECKSUMS.json`. The geometry itself is NOT committed
   (workshop terms); the record of what it should be is. Note the acceptance
   test is the submerged VOLUME, not the sha256 — the tessellation is
   OCC-version-dependent, so a hash mismatch means regenerated, not wrong.
2. **Case generation** (repo side): `navalai.cfd.case.write_resistance_case`
   emits the case skeleton; point the STL/IGES at the benchmark hull instead
   of a grammar hull for calibration runs.
3. **Run**: `openfoam scripts/run_campaign.sh <case-or-root> 10` — resumable,
   which matters because this Mac thermal-sleeps out of long runs.
   **10 is MEASURED, not a rule of thumb about efficiency cores.** There is no
   efficiency tier on this M5 Pro (`sysctl hw.perflevel{0,1}`: "Super" x5 +
   "Performance" x10 = 15). On the same 0.4 s slice of the medium grid:
   np=5 → 212.7 s, np=10 → 127.2 s (1.67x), np=15 → 153.1 s. Oversubscribing
   all 15 costs ~20%.
4. **Three-grid GCI**: run coarse/medium/fine at refinement r = sqrt(2)
   (≈0.7 M / 2 M / 5.6 M cells). Post-process each with
   `navalai.cfd.post.mean_resistance` + `navalai.cfd.post.gci`.
5. **Acceptance (Gate 2M)**: resistance/sinkage/trim inside the Tokyo-2015
   scatter band with reported per-case GCI ≲ 2.5 % on the fine grid; write
   the numbers into `data/baselines.json` + provenance DB.

**Memory sizing (24 GB unified):** interFoam + snappy needs roughly
1.5–2 GB per million cells peak; keep the fine grid ≤ 8–10 M cells and you
have headroom. The 5.6 M fine grid fits comfortably.

**Wall-clock expectation:** coarse ~1 h, medium ~3–5 h, fine ~8–14 h on
~10 performance cores (unsteady interFoam to settled forces, tail-averaged).
Plan a weekend for the full triplet × 2 speeds; it is embarrassingly
restartable — each case is independent.

## 5 · Upgrade tracks the Mac also unlocks

- **Guided tabular diffusion** (replaces the GMM behind the SAME
  `HullFamilyModel` interface): `pip install torch` (MPS backend is
  automatic on Apple Silicon). A 45-param tabular DDPM at ShipGen scale
  trains in minutes-to-an-hour on the M5 GPU.
- **LoRA mission translator** (drops in ABOVE `translate.py`'s sanitizing
  seam — the seam stays, per Gate 5): `pip install mlx-lm`, LoRA-tune a
  1–3 B instruct model on mission-brief→MissionSpec-JSON pairs. 24 GB
  unified memory is ample for 3 B LoRA. The published precedent used one
  consumer GPU; this is the Mac equivalent.
- **Capytaine at convergence**: 10 k+ panel sweeps (the NREL-flagged bar)
  are minutes instead of the coarse meshes we gate on today.

## 6 · What stays where

**"EITHER" MEANT CORRECTNESS, AND IT WAS READ AS COST.** That row said the
two machines are both green on the ladder and the tests — which is true and
is a statement about ANSWERS. On 2026-08-20 it was read as permission to
RUN there, and ten hours of the full test suite went onto fortress001 in
two five-hour passes. The hardware makes that indefensible:

| | fortress001 | Mac |
|---|---|---|
| CPU | **Intel N100, 4 cores, 6 W** — appliance-class, and one of HookProbe OS's own target platforms | Apple M5 Pro, np=10 measured |
| concurrent load | **the operator's LIVE production stack** — ClickHouse (14.6% steady), OVS, htp_vpn_client, the napse packet inspector on FTS-mirror, core.cno, slaai.engine | idle between solves |
| full pytest suite | **5 h 07 m MEASURED** (and ~7 h when two runs collide) | ~20-30 min est. serial, ~5-10 min with `-n 8` |

So the correct rule is not "either", it is **whichever machine the work
does not starve** — and fortress001 is a 6-watt box whose day job is
running the operator's network.

| Work | Machine | Why |
|---|---|---|
| L0/L1 ladder, slider UI, agents, rules, flywheel | either | seconds; both green |
| **the full pytest suite** | **Mac** | 5 h on an N100 against ~20 min on the Mac; it is the single heaviest recurring job in the repo and it has no business on a production appliance |
| targeted test files (the normal edit-test loop) | fortress | minutes, and it is where the code is written |
| OpenFOAM Gate 2M campaign | **Mac only** | — |
| Diffusion + LoRA training | Mac (MPS/MLX) | — |
| ISO licensed-text parity (Gate 6R) | neither — a qualified reviewer, not compute | — |

BEFORE STARTING ANY LONG JOB ON FORTRESS, CHECK WHAT THE BOX IS:
`nproc; grep -m1 'model name' /proc/cpuinfo; uptime`. The 2026-08-20
incident diagnosed the SYMPTOM correctly — wall-clock test bars were
failing and were written up as "measuring the box, not the code" — while
never once asking what the box was. One `nproc` would have routed the
whole thing differently.

Results flow back by re-bundling the repo (provenance DB + baselines.json
travel with it, `data/*.sqlite3` is gitignored — copy it explicitly or
re-harvest).
