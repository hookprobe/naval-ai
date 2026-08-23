"""PUBLISHED morphology targets: what each hull family MEASURES like.

WHY THIS FILE EXISTS. `downloads/hull-examples/*.png` is a taxonomy — it names
44 hull families and shows what they look like. It is not data: you cannot fit
geometry to a thumbnail. `formlib.FAMILIES` is the registry of those families
and it records that 22 of 31 are `Expressible.NO`. What neither of them carries
is the NUMBERS that distinguish one family from another.

This module is those numbers, transcribed from published systematic series with
their provenance, so that "does this hull look like a hard-chine planing boat"
becomes a measurement instead of an opinion.

THE DISTINCTION THAT MATTERS, and it is the one the 2026-08-23 failure turned
on: a paper ABOUT a hull is not hull training data. Only geometry, or a
published table of geometric descriptors, is. Every row here is the latter and
names its page.

WHAT THIS IS NOT. It is not offsets, so it cannot be used to score a shape
residual point-by-point. It bounds the DESCRIPTOR SPACE a family occupies,
which is what a morphology critic needs and what `navalai.morphology.describe`
produces. Offsets, where obtained, live in `tests/e5_*/` as they always have.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FamilyTargets:
    """The descriptor box a published family occupies. None = not tabulated."""

    key: str                       # matches formlib.FAMILIES where one exists
    source: str
    l_over_b: tuple[float, float] | None = None
    transom_area_ratio: tuple[float, float] | None = None   # A_T / A_X
    deadrise_transom_deg: tuple[float, float] | None = None
    deadrise_50_deg: tuple[float, float] | None = None
    deadrise_75_deg: tuple[float, float] | None = None
    length_displacement: tuple[float, float] | None = None  # L / vol^(1/3)
    chine_breadth_ratio: float | None = None                # B_CT / B_C
    note: str = ""


# ---------------------------------------------------------------------------
# HARD-CHINE PLANING. Table 1(a, b), De Luca & Pensa, "The Naples warped hard
# chine hulls systematic series", Ocean Engineering 139 (2017) 205-236, p. 206.
# Held at downloads/hull-examples/research-gate/SSN.pdf.
#
# THREE THINGS THIS TABLE SETTLES, and each contradicts something this codebase
# assumed:
#
# 1. THE TRANSOM IS NEARLY FULL. A_T/A_X runs 0.8-1.0 across seven of the nine
#    series and is 0.94 for the NSS parent. `grammar.PARAMS` caps `r_transom`
#    at 0.50, so EVERY published planing hull in this table is outside the box
#    -- not marginal, outside. The ceiling was found independently on
#    2026-08-23 when a barge stern proved unreachable; this is the published
#    confirmation.
# 2. DEADRISE IS A THREE-POINT WARP, quoted at the transom, 50% LWL and 75%
#    LWL, rising monotonically forward. The grammar warps ONE quadratic from
#    `beta_mid` to `beta_bow` over the forward `beta_len`, which is a
#    different law with a different shape, and cannot in general pass through
#    three prescribed points.
# 3. THE SPREAD IS WIDE AND REAL. beta_75 spans 19.2 deg (Clement & Blount) to
#    53.0 deg (Hubble-B). A single "planing hull" prior would be meaningless;
#    the family has sub-families and the table names them.
#
# Transcription note: the PDF's column headers extract out of order (L/B range,
# then B_CT/B_C, then L/vol^(1/3) range). The mapping used here is the one the
# VALUES support -- L/vol^(1/3) of 7.0-8.5 is a slender planing hull and 0.66
# is not, while B_CT/B_C of 0.66 is a plausible chine-breadth ratio and 7.0 is
# not. Re-check against the page before relying on a single row.
# ---------------------------------------------------------------------------

HARD_CHINE_PLANING: tuple[FamilyTargets, ...] = (
    FamilyTargets("nss_naples", "De Luca & Pensa 2017, Ocean Eng 139, Table 1",
                  l_over_b=(3.24, 4.83), transom_area_ratio=(0.94, 0.94),
                  deadrise_transom_deg=(13.2, 13.2), deadrise_50_deg=(22.3, 22.3),
                  deadrise_75_deg=(38.5, 38.5), length_displacement=(5.86, 7.49),
                  chine_breadth_ratio=0.95,
                  note="PARENT of the series; warped, developable plating"),
    FamilyTargets("clement_blount_1963", "De Luca & Pensa 2017, Table 1",
                  l_over_b=(2.00, 2.97), transom_area_ratio=(0.8, 0.8),
                  deadrise_transom_deg=(12.5, 12.5), deadrise_50_deg=(13.0, 13.0),
                  deadrise_75_deg=(19.2, 19.2), length_displacement=(7.00, 8.46),
                  chine_breadth_ratio=0.66),
    FamilyTargets("keuning_gerritsma_1982", "De Luca & Pensa 2017, Table 1",
                  l_over_b=(1.95, 2.99), transom_area_ratio=(0.8, 0.8),
                  deadrise_transom_deg=(25.0, 25.0), deadrise_50_deg=(26.0, 26.0),
                  deadrise_75_deg=(30.7, 30.7), length_displacement=(6.82, 8.36),
                  chine_breadth_ratio=0.66),
    FamilyTargets("keuning_1993", "De Luca & Pensa 2017, Table 1",
                  l_over_b=(3.29, 3.41), transom_area_ratio=(0.8, 0.8),
                  deadrise_transom_deg=(30.0, 30.0), deadrise_50_deg=(31.2, 31.2),
                  deadrise_75_deg=(35.8, 35.8), length_displacement=(7.00, 8.25),
                  chine_breadth_ratio=0.66),
    FamilyTargets("hubble_a_1974", "De Luca & Pensa 2017, Table 1",
                  l_over_b=(3.20, 4.00), transom_area_ratio=(0.10, 0.12),
                  deadrise_transom_deg=(14.6, 27.9), deadrise_50_deg=(14.8, 29.9),
                  deadrise_75_deg=(22.0, 38.0), length_displacement=(9.26, 10.0),
                  chine_breadth_ratio=0.35,
                  note="the ONE series with a fine transom; A_T/A_X ~ 0.1"),
    FamilyTargets("hubble_b_1974", "De Luca & Pensa 2017, Table 1",
                  l_over_b=(2.32, 4.00), transom_area_ratio=(1.0, 1.0),
                  deadrise_transom_deg=(16.3, 30.4), deadrise_50_deg=(21.2, 37.4),
                  deadrise_75_deg=(35.0, 53.0), length_displacement=(9.28, 10.0),
                  chine_breadth_ratio=1.00),
    FamilyTargets("kowalyshyn_metcalf_2006", "De Luca & Pensa 2017, Table 1",
                  l_over_b=(3.24, 4.98), deadrise_transom_deg=(16.6, 16.6),
                  deadrise_50_deg=(22.5, 22.5), deadrise_75_deg=(34.4, 34.4),
                  length_displacement=(4.50, 0.87), chine_breadth_ratio=0.96,
                  note="length-displacement pair extracts inconsistently; VERIFY"),
    FamilyTargets("taunton_2010", "De Luca & Pensa 2017, Table 1",
                  l_over_b=(3.77, 6.25), transom_area_ratio=(1.0, 1.0),
                  deadrise_transom_deg=(22.5, 22.5), deadrise_50_deg=(22.5, 22.5),
                  deadrise_75_deg=(35.3, 35.3), length_displacement=(6.25, 8.70),
                  chine_breadth_ratio=1.00),
    FamilyTargets("grigoropoulos_loukakis", "De Luca & Pensa 2017, Table 1",
                  l_over_b=(4.00, 6.18), deadrise_transom_deg=(10.0, 10.0),
                  deadrise_50_deg=(22.5, 22.5), deadrise_75_deg=(38.0, 38.0),
                  length_displacement=(7.00, 10.00)),
)

ALL: tuple[FamilyTargets, ...] = HARD_CHINE_PLANING
BY_KEY = {f.key: f for f in ALL}


def envelope(field: str, families=ALL) -> tuple[float, float] | None:
    """The union band for one descriptor across a set of published families."""
    lo, hi = [], []
    for f in families:
        v = getattr(f, field)
        if v is not None:
            lo.append(v[0])
            hi.append(v[1])
    return (min(lo), max(hi)) if lo else None
