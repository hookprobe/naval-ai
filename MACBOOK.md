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

| Work | Machine |
|---|---|
| L0/L1 ladder, slider UI, agents, rules, flywheel, tests | either (both green) |
| OpenFOAM Gate 2M campaign | **Mac only** |
| Diffusion + LoRA training | Mac (MPS/MLX) |
| ISO licensed-text parity (Gate 6R) | neither — a qualified reviewer, not compute |

Results flow back by re-bundling the repo (provenance DB + baselines.json
travel with it, `data/*.sqlite3` is gitignored — copy it explicitly or
re-harvest).
