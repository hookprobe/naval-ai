# Handoff — for the session working on the kernel/grammar side

Written 2026-08-28 by the CFD session (hookprobe campaign). Everything here is
either (a) something only you can finish, or (b) something I changed in a file
you also touch, so you are not surprised by it.

---

## 1. BLOCKING: the shared push is stuck, and it is yours to release

`git push` currently fails the pre-push ladder for BOTH sessions:

```
FAILED tests/test_gate_integrity.py::test_every_test_file_is_owned_by_a_gate
       test files with no gate: ['tests/test_rho_x.py']
```

`tests/test_rho_x.py` (created 16:30) has no committed gate row. Your working
tree already HAS the fix — `navalai/gates.py` carries an uncommitted
`Gate("Gate RHO-X", ...)` — it just is not committed yet.

**To release it:**

```bash
python -m navalai.gates --readme --write     # regenerate, do not hand-edit
git commit navalai/gates.py README.md tests/test_rho_x.py -m "..."
```

I deliberately did NOT commit `README.md` even though I regenerated it, because
that regeneration contains your Gate RHO-X row next to my CFD-KB row and
sweeping your in-flight work into my commit is the 391-line incident in
`docs/LESSONS.md`. So README.md is sitting dirty in the tree with BOTH changes
in it — when you regenerate and commit, it will be correct for both of us.

---

## 2. Files I changed that you also have open

| file | what I did | why it matters to you |
|---|---|---|
| `navalai/cfd/case.py` | added `domain_x_bounds(lwl, speed)`; the block-mesh x extents and `nx` now follow it; the `layer_spec` assert compares the hull CELL, not cell COUNTS | committed (`fc4280e`). Fn <= 0.5 is bit-identical, so nothing you have measured moves |
| `navalai/gates.py` | added `Gate 2E` (domain/wavelength) | committed (`75f5f85`). Your Gate RHO-X row is uncommitted ON TOP of mine — no conflict, just commit it |
| `scripts/harvest_cfd_anchors.py` | `domain_wavelengths` field; `ct_trusted` now also requires >= 1.5; diverged histories REFUSED and evicted; NaN Ct -> None; density imported from `navalai.constants` | committed (`0019157`, `d2a8c3f`) |
| `data/cfd_anchors.json` | re-harvested: 11 records | committed. `hookprobe_v5_20kn` is now `ct_trusted: false` |
| `tests/test_cfd_kb.py` | +2 gate tests (10 -> 12) | committed. This is why README's CFD-KB row count changed |
| `README.md` | regenerated (contains YOUR row + MY count) | **NOT committed — yours to commit** |

I have not touched, and will not touch: `navalai/grammar.py`,
`navalai/geometry.py`, `navalai/morphology_search.py`, `navalai/propulsion.py`,
`navalai/resistance.py`, `scripts/hull_kb_reconstruct.py`, `docs/HULL-KB.md`,
`data/baselines.json`, `tests/test_dwl.py`, `tests/test_split.py`,
`tests/test_rho_x.py`.

---

## 3. Two CFD results that CHANGE what the kernel may cite

**a) The 20-kn anchor is retracted.** `hookprobe_v5_20kn` (66 630 N, Fn 0.96)
was run in a 53.2 m tank against its own 67.8 m wave — the box held 0.78 of ONE
wavelength, so the wave that makes the pressure drag could not form. It is
still IN the anchor book on purpose (a reader meeting the number elsewhere must
be able to find out why it is dead) but it is now `ct_trusted: false`. If
anything in the kernel, the priors, or `docs/HULL-KB.md` cites a 20-kn or
Fn ~0.95 hookprobe number, it is citing that run and must stop.

**b) There is no validated hookprobe result above Fn 0.48.** The re-run in the
corrected 147.5 m tank reached full speed and died at t=20.3 with forces still
decaying 3.7x; it is REFUSED by the harvester (its history carries the
blow-up: 1.19e198 N). The supported envelope for the hookprobe family is
Fn 0.24-0.48, and only the `calm_resistance` records inside it.

---

## 4. Open item that needs a kernel-side decision (not urgent)

`settled_drag.ct` uses each run's own STL wetted area, and v2 vs v3 read
42.14 vs 34.28 m^2 for the same hull one edit apart — because v2 is a
20 096-facet export and v3 is 152 126. The `ct_trusted` flag fences it for now
(facets >= 100 000), but if the kernel ever wants Ct rather than newtons, the
denominator needs one definition. Compare NEWTONS at equal speed until then.

---

## 5. What I am doing next (so we do not collide)

Staying inside: `navalai/cfd/*`, `scripts/harvest_cfd_anchors.py`,
`runs/hookprobe_*`, `docs/research/HOOKPROBE-CFD-CAMPAIGN.md`, and
`runs/hookprobe_inspect/*`.

Next CFD fix: the free-motion riding run died at t=6 in
`GAMGSolver::solveCoarsestLevel` with a HEALTHY timestep (0.0140 s, Courant
5.18) — a singular pressure matrix, consistent with mesh degeneration in the
morphing band as the motion grew, NOT a Courant collapse.

(An earlier note in this file blamed a 2.6% mass/buoyancy mismatch. That was
my error: I checked buoyancy at seawater density while the case runs FRESH
water — `transportProperties` rho 998.8, and `sixdof_properties` uses
RHO_FRESH_20C. They agree to 0.2 kg. The 6-DOF mass derivation is CORRECT and
needs no change from you.)

The hull rode the waves properly before it died — heave oscillating at the
4.5 s wave period with amplitude growing as the ramp built. Candidate fix is
widening the morphing band (outerDistance 2.01 m is absorbing +-60 mm heave
and 1.24 deg pitch).
