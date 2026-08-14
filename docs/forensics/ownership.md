# Forensics — quantity/object ownership + duplicates + constants
(§4/§5/§16/§17), HEAD 3527a59. Full tables in agent record; verdicts here.

## Quantity table: everything CANONICAL with named cross-checks EXCEPT
- PV area: `deck_area*panel_packing` inlined TWICE in energy.py (:88 mass
  side, :236 energy side) — same-file duplicate.
- trim lever `weights.trim_angle_deg`: DEAD-in-ladder (zero production
  callers) while hydrostatics.py:557 header still claims it's what the
  ladder reports — stale ownership claim.
Prior duplicate findings RESOLVED at HEAD: 4x wetted → named roles; 3x
volume → declared cross-checks; 4x section builders → consolidated on
sample_section; ITTC-57 verified consolidated; weight_budget∥MassItem
bridged-and-fenced ("nothing moves numerically").

## STILL DUPLICATED (the residue, concentrated in cfd/post.py)
1. **Two ASCII-STL writers**: case._tris_to_ascii_stl ("THE one facet
   emitter" — file-locally true only) vs post._write_stl (3 callers:
   weld_vertices/mirror_half_hull/cap_planar_holes) — byte-near-identical.
2. **Two STL parsers, different weld semantics, one undocumented**:
   stl_forensics.load_stl (welded, canonical) vs post._read_stl_tris
   (tri-soup, rounds 7 decimals, no docstring/cross-ref; the rounding is
   load-bearing per case.py:1612).

## Constants (§17)
Fence holds inside navalai/. Residue: scripts/hull_form_audit.py:39
G=9.80665 stray (outside fence scope); **NU_SEA_15C names TWO numbers**
(holtrop alias 1.1883e-6 re-exported into resistance vs constants' ITTC
1.18831e-6; resistance.py:66 comment misattributes its anchor);
rho=1000.0 retyped in 7 resistance.py signature defaults (unfenced);
formlib.py:360 retypes 0.45 with comment-only identity to FN_MICHELL_MAX;
two freeboard floors (0.25 bar vs 0.30 box) each single-homed but
relationship undeclared.

## Objects (§5)
Mostly frozen + single-constructor. Flags: MissionSpec setattr paths
bypass __post_init__ (mitigated by idempotent clamp);
**ui/server._mission_from DROPS the energy key — HTTP missions can never
carry a non-default EnergySpec, and unlike every other clamp this is
unrecorded on the mission**; Evaluation mutable (policy writes ev.g);
ledger rows ad-hoc dicts (typed verdicts mitigate).
