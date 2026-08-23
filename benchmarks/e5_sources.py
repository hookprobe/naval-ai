"""Provenance for every hull in the E5 corpus. GATE E5.

ONE ROW PER SOURCE FAMILY, and the row is the only home for the citation.
A number in this repository lives in exactly one place; so does an attribution.

WHAT "INDEPENDENT" MEANS HERE, because the word does most of the work in the
E5 claim and is easy to inflate. Three counts are kept and they are NOT
interchangeable:

  hull instances     how many hulls the corpus contains
  source families    how many independent publications/institutions they
                     come from. Fifty-one hulls from one towing tank, drawn
                     by one grammar of hull form, are ONE family.
  parent geometries  how many genuinely distinct hull forms underlie them.
                     A systematic series varies one parent by stretching it;
                     twenty variants of a parent are twenty data points about
                     that parent, not twenty independent shapes.

Reporting only the first is the inflation this file exists to prevent.

ACCESS. Every source here is either public domain, CC0, CC BY, or evaluated
from a published closed form. Sources investigated and NOT used are recorded
too, with the reason -- an absent source and a rejected one look identical
afterwards, and the difference is the whole audit trail.
"""
from __future__ import annotations

FAMILIES = {
    "dsyhs": {
        "family": "Delft Systematic Yacht Hull Series",
        "institution": "Delft University of Technology, Ship Hydromechanics "
                       "Laboratory",
        "geometry_title": "Delft Systematic Yacht Hull Series Geometries data",
        "geometry_doi": "10.4121/21501330.v1",
        "geometry_url": "https://data.4tu.nl/articles/dataset/"
                        "Delft_Systematic_Yacht_Hull_Series_Geometries_data/"
                        "21501330",
        "geometry_licence": "CC0",
        "geometry_format": "3D IGES NURBS surfaces, one per model, model "
                           "scale, millimetres",
        "hydrostatics_title": "Delft Systematic Yacht Hull Series "
                              "hydrostatics data",
        "hydrostatics_doi": "10.4121/21501375.v1",
        "primary_publication":
            "Gerritsma, J., Moeyes, G. and Onnink, R., 'Test Results of a "
            "Systematic Yacht Hull Series', 5th HISWA Symposium on Yacht "
            "Architecture, Amsterdam, November 1977. Delft Ship "
            "Hydromechanics Laboratory Report 452-P.",
        "publication_url": "https://doi.org/10.6084/m9.figshare.21581568.v1",
        "parent_hull": "Sysser 1, which the primary publication states "
                       "'resembles closely the successful Standfast 43 "
                       "designed in 1970 by Frans Maas of Breskens' (p. 6).",
        "lcb_convention_original":
            "metres from 1/2 waterline length, upright condition "
            "(4TU hydrostatics 'Info' sheet, row lcb0). Negative is AFT.",
        "lcb_transformation":
            "LCB_pct = 100 * lcb0 / lwl0. Sign UNCHANGED: the source is "
            "already positive-forward. VERIFIED rather than assumed -- LCF "
            "is tabulated in the same units and sits further aft than LCB on "
            "every model, which is only true of a yacht canoe body if "
            "negative means aft.",
        "draft_convention":
            "tc0, the MAXIMUM CANOE-BODY draft (Info sheet). Appendages are "
            "excluded: the geometry release states the hulls are 'presented "
            "without keel and rudder'. NavalAI's T gene is the draft at the "
            "midship keel, which on a hull with rocker is not necessarily "
            "the same station; the difference is carried in the ledger, not "
            "absorbed.",
        "depth_source":
            "MEASURED from the published IGES surface as z_sheer - z_keel at "
            "amidships. The series was designed to a CONSTANT FREEBOARD, "
            "which is why the modelled top edge is a flat constant-z line "
            "(318.10 mm on Sysser 1, identical at all 41 stations), so this "
            "is a designed deck height and not an arbitrary trim. "
            "CORROBORATED by the primary publication, p. 14, which defines "
            "hull depth as 'the constant freeboard (1.15 m) plus the draught "
            "of the canoe body' at 10 m full scale: 1.944 m against 1.988 m "
            "measured, +2.3%. Both are recorded; neither is discarded.",
        "hard_chine_or_round_bilge": "round_bilge",
        "notes":
            "Fin-keel sailing yacht CANOE BODIES, appendages removed. Every "
            "model normalises to LWL = 10.000 m at full scale, so this family "
            "supplies NO length diversity whatever -- it varies beam, draft "
            "and prismatic at fixed length. That is a property of the series, "
            "and it is why the corpus does not stop here.",
    },
    "series60": {
        "family": "Series 60",
        "institution": "David Taylor Model Basin, for the Society of Naval "
                       "Architects and Marine Engineers",
        "geometry_title":
            "Todd, F.H., 'Series 60: Methodical Experiments with Models of "
            "Single-Screw Merchant Ships', DTMB Report 1712, US Government "
            "Printing Office, 1963.",
        "geometry_doi": "",
        "geometry_url": "https://archive.org/details/methodicalexperi00todd",
        "geometry_licence": "public domain (work of the US Government)",
        "geometry_format": "printed table of offsets, half-breadths as a "
                           "fraction of the maximum beam on each waterline",
        "primary_publication": "as above; Table 3, p. A-7 for the 0.60 block "
                               "coefficient parent, model 4210W.",
        "publication_url": "https://archive.org/details/methodicalexperi00todd",
        "parent_hull": "Model 4210W, the 0.60 block coefficient parent.",
        "lcb_convention_original":
            "percent of LBP from amidships. The report states its own sign "
            "rule in words: LCB is 'positive if forward of amidships and "
            "negative if aft'.",
        "lcb_transformation":
            "NONE REQUIRED -- the source convention is already this "
            "project's. Recorded explicitly because 'no conversion needed' "
            "and 'conversion never considered' are indistinguishable after "
            "the fact.",
        "draft_convention":
            "W.L. 1.00 is the designed load waterline; waterlines are "
            "fractions of it. The first column, headed 'Tan.', is the "
            "half-breadth of the flat of bottom and is read at z = 0 (these "
            "parents have no rise of floor).",
        "depth_source":
            "Top of the tabulated offsets, W.L. 1.50 = 1.5 T. The source "
            "tabulates no sheerline, so this is the extent of the published "
            "body and NOT a measured deck edge. Confidence MEDIUM.",
        "hard_chine_or_round_bilge": "round_bilge",
        "notes":
            "A methodical series publishes SHAPE, as fractions of L, B and "
            "T; it has no natural size. Instantiated at a length this "
            "project chose (see the fixture header), using the published "
            "L/B = 7.50 and B/H = 2.50. Transcribed from an OCR scan and "
            "validated against two published scalars the transcription does "
            "not contain.",
    },
    "wigley": {
        "family": "Wigley parabolic hull",
        "institution": "—",
        "geometry_title":
            "Wigley, W.C.S., 'A Comparison of Experiment and Calculated Wave "
            "Profiles and Wave Resistance for a Form having Parabolic "
            "Waterlines', Proc. Royal Society A, 144, 1934.",
        "geometry_doi": "10.1098/rspa.1934.0044",
        "geometry_url": "https://doi.org/10.1098/rspa.1934.0044",
        "geometry_licence": "closed form, evaluated (no transcription)",
        "geometry_format": "y = (B/2)(1 - (2x/L)^2)(1 - (z/T)^2)",
        "primary_publication": "as above.",
        "publication_url": "https://doi.org/10.1098/rspa.1934.0044",
        "parent_hull": "the analytic form itself.",
        "lcb_convention_original":
            "none needed: the form is symmetric about amidships, so LCB is "
            "exactly 0 by construction.",
        "lcb_transformation": "NONE. LCB = 0 exactly.",
        "draft_convention": "T is the design draft; the surface is defined "
                            "only for 0 <= z <= T.",
        "depth_source":
            "UNAVAILABLE. The form has no deck and no sheerline, and none is "
            "invented. This hull is PARTIAL evidence and is excluded from "
            "the gate's complete-hull count.",
        "hard_chine_or_round_bilge": "mathematical (neither)",
        "notes":
            "The only member of the corpus whose source truth cannot be "
            "disputed: volume 4LBT/9, Cp = Cm = 2/3, Cb = 4/9, LCB = 0 are "
            "exact. It therefore doubles as the correctness test of the "
            "independent measurement code itself.",
    },
}

#: Investigated and NOT used. Each row says why, so that a later session
#: re-treads the search only if the reason has changed.
REJECTED = {
    "NPL high speed round bilge series (Bailey, D., 'The NPL High Speed "
    "Round Bilge Displacement Hull Series', RINA Maritime Technology "
    "Monograph No. 4, 1976)":
        "ACCESS. The monograph is RINA copyright and is not available under "
        "any licence this project can use. The copies findable on "
        "document-sharing sites are neither authorised nor provenance-grade, "
        "and a scraped scan is exactly the evidence standard E5 exists to "
        "refuse. Wanted: it is a genuinely different hull-form grammar "
        "(high-speed round bilge, transom-sterned) at 2.54 m model length, "
        "which would add both a family and a length. Revisit if RINA "
        "publishes it or an institutional copy becomes citable.",
    "KCS (KRISO container ship, MOERI)":
        "OUT OF SCOPE BY LENGTH, not by quality. The geometry is already in "
        "this repository (data/benchmark_geom, MD5-verified) and is "
        "excellent evidence -- but at 232.5 m LWL it lies outside the "
        "genome's own box, which is bounded to 2.5-24 m by RCD Article "
        "3(2). It cannot be encoded, so it cannot be round-tripped, and "
        "including it as a 'failure' would be reporting the box's declared "
        "scope as a kernel defect.",
    "Series 60 parents at Cb 0.75 and 0.80 (models 4213W, 4214W-B4)":
        "OUT OF RANGE ON PRISMATIC. Published total prismatic 0.758 and "
        "0.805 against a genome bound of 0.710, which comes from the "
        "Froude-number prismatic table in navalai/limits.py. These are full "
        "cargo forms; the product does not claim to design them. Their "
        "offsets ARE transcribable and the tables are cited in "
        "docs/gates/E5.md should the bound ever move.",
    "Series 60 parent at Cb 0.65 (model 4211W, Table 4)":
        "OCR NOT PROVENANCE-GRADE. Wanted -- it is in range (published total "
        "prismatic 0.661) and would have doubled this family's parent "
        "geometries. But the scan of Table 4 loses the 'Max. half beam' row "
        "entirely, and without it the half-breadths cannot be un-normalised: "
        "the table gives each offset as a fraction of the maximum beam ON "
        "THAT WATERLINE, so the missing row is the scale of five of the eight "
        "columns. The same page also shows heavier character damage than "
        "Table 3 (9.000 for 0.000, a lost station label). Repairing that by "
        "inference is guesswork wearing a citation, which is the standard E5 "
        "exists to refuse. Recoverable from a clean scan or the printed "
        "report.",
    "Compton (1986) USNA semi-planing transom-stern series":
        "NOT YET ACQUIRED. It is the strongest known candidate for the "
        "HARD-CHINE gap that DSYHS and Series 60 both leave open, and the "
        "acquisition route is recorded in "
        "docs/audit/GATE2-PHYSICS-STACK.md. Nothing in the present corpus "
        "exercises chine, spray or transom-ventilation geometry.",
}


def family_of(hull_id: str) -> str:
    for key in FAMILIES:
        if hull_id.startswith(key):
            return key
    raise KeyError(f"no source family registered for {hull_id!r}")


#: Sources used by GATE E5-CHINE. Kept apart from `FAMILIES` because only one
#: of them yields hull fixtures; the rest supply published PARAMETERS, which
#: is a different kind of evidence and must not be counted as geometry.
HARD_CHINE_SOURCES = {
    "fridsma_R1275": {
        "family": "Fridsma R-1275 prismatic planing models",
        "citation":
            "Fridsma, G., 'A Systematic Study of the Rough-Water Performance "
            "of Planing Boats', Davidson Laboratory, Stevens Institute of "
            "Technology, Report R-1275, November 1969. DTIC AD0708694.",
        "access": "approved for public release, distribution unlimited",
        "geometry_status": "PUBLISHED_PARAMETRIC",
        "what_it_gives":
            "Five hull fixtures. Figure 1 PRINTS the equations of the chine "
            "planform and the keel profile, and the text states the sections "
            "aft of the bow are constant hard-chine prismatic forms, so the "
            "geometry is EVALUATED, never digitised. The design waterline "
            "comes from the published load coefficients.",
        "limitation":
            "Constant deadrise (monohedral) and a prismatic body: Cp "
            "0.951-0.971, far above anything the kernel will build. It is a "
            "planing hull, not the semi-displacement form this product "
            "mainly targets.",
    },
    "nss_deluca_pensa_2017": {
        "family": "Naples Systematic Series",
        "citation":
            "De Luca, F. and Pensa, C., 'The Naples warped hard chine hulls "
            "systematic series', Ocean Engineering 139 (2017) 205-236. "
            "doi:10.1016/j.oceaneng.2017.04.038",
        "access": "open access, CC BY-NC-ND",
        "geometry_status": "PUBLISHED_PARAMETERS_ONLY",
        "what_it_gives":
            "Table 1(a, b), p. 206: the DEADRISE DISTRIBUTION of eight "
            "systematic hard-chine series at the transom, 50% and 75% LWL, "
            "plus A_T/A_X and chine-breadth ratios. That table is the whole "
            "basis of the warp survey in scripts/e5_chine_warp.py, and it "
            "needs no offsets. Table 3 gives full principal particulars for "
            "C1-C5 at several load conditions.",
        "limitation":
            "NO OFFSET TABLE. The sections appear only as Figs. 3 and 4, "
            "which makes them IMAGE_ONLY, so NSS yields no hull fixture. "
            "Also worth counting honestly: C2-C5 are C1 with depth and "
            "breadth scaled by the same factor, keeping homothetic sections "
            "and therefore IDENTICAL hull coefficients -- that is ONE parent "
            "geometry with four affine derivatives, not five shapes.",
        "why_it_matters":
            "The parent was explicitly 'changed to obtain the plating as "
            "developable surfaces' so it could be built from rigid panels. A "
            "warped hard chine on developable plating is what NavalAI is "
            "for, and it is the family the grammar misses by 8.3 degrees.",
    },
    "radojcic_kalajdzic_simic_2019": {
        "family": "review (not a hull source)",
        "citation":
            "Radojcic, D., Kalajdzic, M. and Simic, A., 'Power Prediction "
            "Modeling of Conventional High-Speed Craft', Springer, 2019, "
            "ISBN 978-3-030-30606-9.",
        "access": "book",
        "geometry_status": "NONE",
        "what_it_gives":
            "Classification, and one correction that matters to the "
            "independence count: Sect. 3.3 records that Series 62 (Clement & "
            "Blount 1963, beta 12.5 deg), Keuning & Gerritsma 1982 (25 deg) "
            "and Keuning et al. 1993 (30 deg) are ONE series tested over "
            "three decades -- Series 62, later PHF, now DSDS (Delft "
            "Systematic Deadrise Series). Three rows of the warp survey are "
            "therefore deadrise variants of a single family.",
        "limitation":
            "No offsets. Its Table 3.1 does not extract from the PDF (the "
            "table body renders in a form pypdf cannot order), and the body "
            "plans it reproduces are figures. It is a review of regression "
            "power-prediction models, not a geometry source.",
    },
    "pacuraru_galati_2022": {
        "family": "CFD study, Galati",
        "citation":
            "Pacuraru, F., Mandru, A. and Bekhit, A., 'CFD Study on "
            "Hydrodynamic Performances of a Planing Hull', J. Mar. Sci. Eng. "
            "10 (2022) 1523. MDPI, open access CC BY.",
        "access": "open access, CC BY",
        "geometry_status": "NONE",
        "what_it_gives":
            "Corroboration only. Its validation geometry is LOA 2.611 m, "
            "which is the NSS C1 model, and it cites Mancini's CFD "
            "validation against the same series.",
        "limitation":
            "No offsets, no body plan, no lines. It is a CFD paper: relevant "
            "to a future chine-PHYSICS gate, not to E5-CHINE, which is about "
            "geometry.",
    },
}
