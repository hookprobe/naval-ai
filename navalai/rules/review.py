"""Gate 6R — the parity review record.

Gate 6R is the one gate no amount of code can close by itself: it asks
whether our numeric thresholds match the standard text. REFRAMED 2026-08-19
(operator's direction): the gate is NOT blocked on a document purchase — it
is blocked on FIVE SPECIFIC pieces of clause text, enumerated in
docs/GATE-6R-REQUEST.md, which the operator sources however they source
them. This module records the attributable verdict once each piece is
verified, so `basis` on every RuleFinding derives from a review rather
than an assertion.

WHAT A CONFIRMATION HERE DOES AND DOES NOT MEAN

  DOES:     the threshold VALUE matches the standard text for that clause.
  DOES NOT: make the assessment a certification. Honesty rule 5 is unchanged
            and DISCLAIMER still applies — CE marking needs a Notified Body,
            and these are simplified implementations of a few clauses, not
            the whole standard.

Reviewing a threshold does not review the mechanics around it either; those
are exercised by the gate tests independently.

AND IT IS NOT THE QUESTION GATE 6 ASKS (gap D9). Gate 6R's scope is THRESHOLD
parity: does the number in our source equal the number in the standard text.
BuildPlan Gate 6's bar is VERDICT parity — the same verdict as a qualified
reviewer on at least three reference designs, hand-calculated. Zero reference
designs and zero hand calculations exist. A green 6R is therefore not evidence
for Gate 6, and the reviewer of record is the project owner reviewing his own
code, with no qualification recorded. Both facts are in `docs/GAP-REGISTER.md`
so a future reader does not have to re-derive them from this file.
"""

from __future__ import annotations

import re

# The reviewer's own record. `reviewer` and `editions` are provenance: a
# confirmation that cannot say WHO checked WHICH edition is not a review, it
# is a rumour. Fill these with the reviewer's name and the dated edition they
# held (e.g. "ISO 12217-1:2022").
REVIEW = {
    "reviewer": "project owner (homepods <homepod@hotmail.com>)",
    "date": "2026-08-05",
    "editions": {
        "ISO 12217-1": "ISO 12217-1:2015 (Third edition, 2015-10-15)",
        # PINNED 2026-08-19 from the operator-sourced text. The 2008
        # edition is WITHDRAWN, replaced by ISO 12215-5:2019 — which
        # REORGANIZED the calculation (kAR via its own Table 9, kDYN
        # renaming). The equations in rules/iso12215.py are 2008(E)
        # equations and MUST NEVER be mixed with 2019 tables; upgrading
        # means replacing the module against the 2019 text wholesale.
        "ISO 12215-5": "ISO 12215-5:2008(E), First edition, 2008-04 "
                       "(withdrawn; replaced by ISO 12215-5:2019 — do "
                       "not mix editions)",
    },
    "scope": "threshold parity only; mechanics and clause mapping unchanged",
    # Every rule id the reviewer confirmed against the standard text.
    #
    # FOUR ROWS WERE REMOVED FROM THIS SET ON 2026-08-12, AND THAT IS THE
    # FINDING. Gate 6R was RED for one reason only — the two `editions` strings
    # were placeholders — so filling them in was all that stood between the
    # gate and GREEN. When the 2015 text was finally held and read, TWO of the
    # six "confirmed" rules did not match it, and not by a coefficient: by the
    # MODEL.
    #
    #   R-OLH  CATEGORY_TABLE carried the offset-load heel limit as a
    #          per-category constant (10/10/10/12 deg). 6.2.3 a) makes it a
    #          function of LENGTH ONLY, phi_O(R) = 11,5 + (24 - LH)^3/520, and
    #          Table 4 tabulates it: 22,7 deg at LH = 6 m. We were enforcing
    #          10 deg there — more than twice as strict, on the wrong variable.
    #   R-DFH  carried a fixed per-category floor. Annex A (A.1) computes
    #          hD(R) = (LH/15) * F1..F5 and CLAMPS it to Table A.1, so the
    #          requirement scales with hull length and a single number could
    #          not have been right at more than one length.
    #
    # So a green Gate 6R would have certified two thresholds that contradict
    # the standard they cite. The gate was asking "is the edition recorded?"
    # when the question it exists to ask is "do the numbers match the text?" —
    # and only the first of those can be closed by typing a string.
    #
    # R-GM is removed because it is NOT IN THE STANDARD AT ALL. A regex sweep
    # of all 86 pages of ISO 12217-1:2015 for an absolute metacentric-height
    # requirement returns ZERO hits: the standard governs offset-load heel,
    # downflooding and wave/wind resistance instead. Our GM floor is a useful
    # L1 feasibility bar and is kept — but it is ours, so it belongs with the
    # practice values below and its basis is 'approx'.
    #
    # R-PBM and R-TBM are removed because THERE IS NO 12215-5 TEXT TO HAVE
    # CONFIRMED THEM AGAINST — that edition is still a placeholder five lines
    # up. A confirmation recorded against a standard nobody held is the same
    # defect as an unmeasured metric scored as passing.
    "confirmed": frozenset({
        "R-CAT",   # design-category wave-height context
        "R-DFH",   # ISO 12217-1:2015 Annex A (A.1) + Table A.1
        "R-OLH",   # ISO 12217-1:2015 6.2.3 a) + Table 4
        # 2026-08-19, operator-sourced ISO 12215-5:2008(E) text (Gate 6R
        # items 1-4): Eq 7 factors (kDC §7.2 table, kL §7.4 Eq 3, kAR
        # §7.5 Eq 4 incl. kR and AD limits + Table 3 minima), Eq 8
        # minimum, Table 9 sigma_d = 0.5 sigma_uf, and Table E.2's
        # density+ply-count sigma_uf formulas — all implemented to the
        # text; golden values in tests/test_gapfix_product.py. The old
        # flat 10 kN/m2 floor and SIGMA_D_OKOUME = 15.0 are GONE.
        "R-PBM",
        "R-TBM",
    }),
    # Rules that are IMPLEMENTED but NOT confirmed, each with the reason. A
    # rule missing from both sets is an oversight; a rule here is a decision.
    "unconfirmed": {
        # R-PBM / R-TBM moved to `confirmed` 2026-08-19 — their old
        # entries here (recording exactly what the flat floor and the
        # constant sigma got wrong) are preserved in git history and in
        # the module docstring's re-shape note.
        "R-GM": (
            "NOT IN THE STANDARD. A regex sweep of all 86 pages of "
            "ISO 12217-1:2015 for an absolute metacentric-height requirement "
            "returns ZERO hits — the standard governs offset-load heel "
            "(6.2.3), downflooding (6.1, Annex A) and wave/wind resistance "
            "(6.3, 6.4) instead. Our GM floor is a useful L1 feasibility bar "
            "and is kept as one, but no standard blesses it, so it can never "
            "report basis='standard'."
        ),
        "R-MHS": (
            "THERE IS NOTHING TO CONFIRM IT AGAINST, AND THAT IS THE FINDING. "
            "R-MHS is the multihull stability refusal added 2026-08-14. "
            "ISO 12217-1:2015 gives habitable multihulls clause 6.6 (p. 27), "
            "which EN ISO 12217-1:2017 Annex ZA maps to BOTH RCD Annex I A 3.3 "
            "(inversion) and A 3.8 (escape) — and the BODY of 6.6 is behind the "
            "paywall (1 865 SEK) and past the free preview's page cut, so not "
            "one word of it is in this tree. The Directive's own sentence is "
            "qualitative ('sufficient buoyancy to remain afloat in the inverted "
            "position') and carries no number. The finding therefore asserts no "
            "threshold at all: it REFUSES, reports 0 of 1 criteria assessed, "
            "and names the three free national criteria "
            "(limits.MULTIHULL_RIGHTING_CRITERIA) that would apply once a "
            "righting-arm curve exists. A rule that states no number cannot be "
            "confirmed against a text, and must never read basis='standard'."
        ),
    },
    # Points the packet raised that a blanket "confirmed" does not by itself
    # resolve. Recorded so they are not lost behind a green gate.
    "interpretations": {
        "R-MHS/B_H": (
            "cl 6.6.3's 'hull breadth parameter' B_H is taken as the "
            "VESSEL overall beam (the breadth resisting inversion); the "
            "standard's §3 definition was not in the sourced text — "
            "verify against the page and correct here if it means the "
            "single-hull breadth."
        ),
        "R-PBM/kL": (
            "Eq (3)'s slope term arrived transcription-ambiguous; the "
            "implemented reading (1 - 0.167 nCG)/0.6 * x/LWL + 0.167 nCG "
            "is fixed by CONTINUITY — kL(0.6) = 1 exactly, matching the "
            "x/LWL > 0.6 branch; the alternative parse jumps 0.6 -> 1.0 "
            "at the boundary and is rejected on that ground. Verify "
            "against the printed page when it is next in hand."
        ),
        "R-PBM/kAR": (
            "The panel LONG dimension is unmodeled, so AD = b^2 (l = b), "
            "the smallest admissible design area and hence the largest "
            "kAR — conservative by Eq (4)'s direction. A declared panel "
            "layout supersedes this."
        ),
        "R-TBM/grain": (
            "Face grain is assumed ACROSS the stiffeners (build-practice "
            "orientation), so Table E.2's PARALLEL formula governs; the "
            "perpendicular formula is implemented for a declared layup."
        ),
        "R-TBM/N_ply": (
            "The ply count is mapped from sheet thickness by build "
            "practice (odd, clamped 5..15 per the standard's presumption) "
            "— the standard presumes N, it does not derive it. The "
            "mapping is OURS, basis approx; the strength FORMULA is the "
            "standard's."
        ),
        "R-CAT": (
            "Categories A and B both carry hs = 4.0 m in CATEGORY_TABLE. That "
            "is only coherent because the SENSES differ: ISO 12217-1 states A "
            "as waves EXCEEDING 4 m (a lower bound) and B as waves UP TO AND "
            "INCLUDING 4 m (an upper bound). The table stores a single scalar "
            "and therefore cannot express that distinction; it is used as "
            "CONTEXT reported to the user, never as a pass/fail bar, which is "
            "why the ambiguity is tolerable. If it ever becomes a bar, it must "
            "carry the sense with it."
        ),
        "R-DFH": (
            "The floor is confirmed, but the MEASUREMENT basis is ours: we "
            "assume the lowest opening sits at the sheer line. That is only "
            "conservative when no lower opening exists. Per-boat openings must "
            "still be declared."
        ),
    },
}

# Practice values that are OURS, not ISO. Listed so nobody later reads a green
# Gate 6R as blessing them — no standard governs these.
NOT_FROM_STANDARD = ("FREEBOARD_FLOOR_M", "PLY_THICKNESS_M",
                     "BEND_RADIUS_RATIO", "TRIM_LIMIT_DEG", "LIST_LIMIT_DEG")


def basis_for(rule_id: str) -> str:
    """'standard' once a reviewer has confirmed the rule, else 'approx'.

    Rule modules call this instead of hard-coding a basis string, so the
    reviewed/unreviewed state has exactly one source and a finding can never
    claim 'standard' without a corresponding entry above.
    """
    return "standard" if rule_id in REVIEW["confirmed"] else "approx"


# An edition string has to name a DATED edition, because that is the only part
# of it a later auditor can go and check. "ISO 12217-1" identifies a standard;
# "ISO 12217-1:2022" identifies the text somebody actually held.
_EDITION_YEAR = re.compile(r"\b(19|20)\d{2}\b")

#: The standards this tree IMPLEMENTS, and therefore must name a dated edition
#: for before Gate 6R may be green. ONE declaration, checked by
#: `edition_defects`: `navalai/rules/iso12215.py` and `navalai/rules/iso12217.py`
#: are the two modules that apply standard thresholds, and a third would have to
#: appear here as well as on disk. Keeping the list here rather than globbing the
#: directory is deliberate — `ergonomics.py` and `estrin.py` also live there and
#: are NOT ISO standards, so a glob would either over- or under-report.
REQUIRED_STANDARDS = ("ISO 12215-5", "ISO 12217-1")
_PLACEHOLDER = ("not recorded", "tbd", "todo", "unknown", "?")


def edition_defects(record: dict | None = None) -> list[str]:
    """Every reason the record cannot name WHICH document was reviewed.

    Returned as words rather than a bool so the gate ledger and any operator
    can see what is missing without reading this file.
    """
    rec = REVIEW if record is None else record
    out: list[str] = []
    editions = rec.get("editions") or {}
    if not editions:
        return ["no editions recorded at all"]
    # A MISSING STANDARD WAS NOT A DEFECT UNTIL 2026-08-20, and that is the
    # hole that mattered: this loop only ever inspected the entries PRESENT,
    # so a record naming one of the two implemented standards returned
    # `edition_defects() == []` and `is_complete() == True`. MEASURED with
    # editions={"ISO 12217-1": "ISO 12217-1:2015"}: no defects, complete —
    # Gate 6R would have gone GREEN with ISO 12215-5 entirely unrecorded.
    # Found by the guard test written while PROMOTING that gate, which is the
    # only reason it did not ship green with a hole in it.
    for standard in REQUIRED_STANDARDS:
        if standard not in editions:
            out.append(f"{standard}: implemented by this tree "
                       f"(navalai/rules/) and named by NO edition entry")
    for standard, edition in sorted(editions.items()):
        text = str(edition or "").strip()
        if not text:
            out.append(f"{standard}: edition is empty")
        elif any(p in text.lower() for p in _PLACEHOLDER):
            out.append(f"{standard}: edition is a placeholder ({text!r})")
        elif not _EDITION_YEAR.search(text):
            out.append(f"{standard}: edition names no year ({text!r}) — an "
                       f"undated edition cannot be re-checked")
    return out


def is_complete(record: dict | None = None) -> bool:
    """True when the record is attributable — the gate's real precondition.

    A confirmation with no reviewer and no edition cannot be audited, so it
    does not count. This is what stops Gate 6R going green because someone
    edited a set literal.

    THE EDITIONS CLAUSE WAS MISSING, AND THE MODULE SAID SO ITSELF (gap D8,
    audit 2026-08-05). The docstring above `REVIEW` reads "a confirmation that
    cannot say WHO checked WHICH edition is not a review, it is a rumour" —
    and then this function checked `reviewer` and `confirmed` and NOT
    `editions`, which both read "edition not recorded — set this". Gate 6R was
    GREEN on a record that admits in its own field values that it cannot name
    the document it checked.

    Adding the clause FLIPS GATE 6R RED. That is honesty rule 6 working as
    designed, not a regression: the red is recorded in `data/gate-ledger.json`
    with an owner and a review-by date, and it clears the moment a reviewer
    writes the two dated editions in.
    """
    rec = REVIEW if record is None else record
    return (bool(rec.get("reviewer")) and bool(rec.get("confirmed"))
            and not edition_defects(rec))
