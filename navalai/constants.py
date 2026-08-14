"""Physical constants — THE one home (consolidation directive §18, R3.1).

The audit found four water densities, three fresh-water viscosities and two
gravities declared across seven modules with no file saying which convention
governs where. They were NOT all the same number retyped: they are DIFFERENT
CONVENTIONS (design fresh water vs 20 C CFD fluid vs ITTC 15 C tank water;
standard gravity vs the value OpenFOAM cases carry), and the defect was that
nothing declared them side by side with their scopes. This file does.

RULES:
  * every constant here carries its convention and its consumers;
  * EXACT VALUES ARE UNCHANGED by the consolidation — converging two
    conventions (e.g. holtrop's 1025.0 sea water against ITTC's 1026.0)
    changes physics results and pinned measurements, so it may only happen
    with a measured justification, not as a tidy-up;
  * no module may re-declare one of these literals; the single-source fence
    test greps for exactly that.
"""

# --- gravity ---------------------------------------------------------------

# ISO 80000-3 standard gravity. The g of the L1 physics: geometry, Froude
# numbers, hydrostatics, formlib.
G_STANDARD = 9.80665

# The value generated OpenFOAM cases write to constant/g, kept at 9.81 so the
# case dictionaries and the numbers derived FROM them (Fn in case.info, wave
# parameters) agree with the solver's own inputs. The 0.03% difference from
# G_STANDARD is documented, deliberate case-parity — not drift.
G_OPENFOAM = 9.81

# --- water: the L1 design condition ----------------------------------------

# Fresh water, the design convention of the whole L1 ladder (Danube brief).
# Round 1000 by convention, not by temperature table.
RHO_FRESH = 1000.0

# The kinematic viscosity the Michell/ITTC-57 tier has always shipped: the
# 15 C fresh value rounded to three figures. NOTE: similitude carries the
# unrounded ITTC 1.13902e-6 — a 0.09% difference that moves Re and Cf pins,
# so converging them is a measured change, recorded here until made.
NU_FRESH_15C_ROUNDED = 1.14e-6

# --- water: ITTC 15 C tank conventions (similitude / scaling) --------------

RHO_FRESH_15C = 999.0
NU_FRESH_15C = 1.13902e-6
RHO_SEA_15C_ITTC = 1026.0
NU_SEA_15C = 1.18831e-6

# --- water: the CFD case fluid (~20 C fresh) -------------------------------

RHO_FRESH_20C = 998.8
NU_FRESH_20C = 1.09e-6

# --- water: Holtrop-Mennen's sea condition ---------------------------------

# 1025.0, the round sea-water figure the 1982 regression is conventionally
# run with — one kg/m^3 under the ITTC 15 C table value above. Kept separate
# and named, per the rule at the top. The viscosity is likewise the ITTC
# value rounded to four significant figures — found by the §18 sweep AFTER
# the first fence landed, which is why the fence greps both spellings.
RHO_SEA_HOLTROP = 1025.0
NU_SEA_HOLTROP = 1.1883e-6
