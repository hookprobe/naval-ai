"""EVIDENCE PROMOTION: a receipt may never grow into a mechanism.

WHY THIS FILE EXISTS, and it is a measured incident, not a style rule.

`navalai/contract.py` labels every prescribed number with how much it is
worth — DERIVED, EMPIRICAL, RECEIPT ONLY, INPUT — and `tests/test_contract.py`
enforces that the label is PRESENT and spelled correctly. Nothing enforced
what the sentence AFTER the label is allowed to say. A label is cheap to
keep and cheap to hollow out: `"RECEIPT ONLY: measured on 4 points"` becomes
`"RECEIPT ONLY: scale helps because the background cell ..."` in one edit,
and the label still passes every existing check while the sentence has been
promoted from an observation to a physical law.

The concrete case is the mesh-scale CROSSOVER (`docs/research/CROSSOVER.md`).
It is this campaign's strongest empirical result — a 1.75% background density
bump changes max skewness, the SIGN depends on baseline mesh health
(+13%, +41%, -29%, -58% sorted by baseline skewness), it flips ONCE between
4.592 and 5.803, and it predicted BOTH directions 6/6 out of sample across
three hull families (`d92d548`). It is also, twice over, NOT a mechanism:

  * MECHANISM 1, "tightest feature / background cell", REFUTED BY
    COUNTEREXAMPLE (`57da605`) — the wave-piercing hull has the tightest
    feature in the set by 12x and scale HELPED it 55%, the exact opposite of
    what the rule predicts;
  * MECHANISM 2, `panel_twist_deg_per_m`, REFUTED BY PERMUTATION — 15
    metrics, 6 hulls, all 20 label splits enumerated, family-wise p = 0.700
    against a mean of 1.40 separators under the null and 1 observed.

PREDICTIVE != CAUSAL. Both refutations previously lived only in commit
messages and in `docs/audit/STATUS.md`, which CLAUDE.md classes as a ROLLING
channel — and a refutation kept only in a rolling log gets re-proposed by the
next session that reads the prediction and not the test. `635eb07` moved the
record to `docs/research/CROSSOVER.md`. THIS FILE IS THE EXECUTABLE HALF: the
record can now be checked, not merely read.

Three fences, each proved in BOTH directions (docs/LESSONS.md defect class 3
— "a guard that was never made to fire"): every scanner here is fed a crafted
violation it must reject and a clean neighbour it must accept, in `tmp_path`,
so no fence in this file rests on the real tree happening to be clean.

And one anti-pattern guarded explicitly (defect class 1, "an unmeasurable
value scored as a passing one"): a scanner that finds NOTHING passes every
assertion about what it found. `test_the_basis_scanner_actually_reaches_the`
`_strings_it_guards` fails if the scan comes back thin, so a broken walk can
never read as a clean tree.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: The four kinds `navalai/contract.py` labels a prescribed number with.
#: Mirrored here as STRINGS on purpose: this file is a fence over the
#: vocabulary, so importing the constants would make it agree with a
#: renamed constant instead of noticing the rename.
BASIS_LABELS = ("DERIVED", "EMPIRICAL", "RECEIPT ONLY", "INPUT")

#: The two kinds that are NOT derivations and therefore may not claim one.
#: DERIVED and INPUT are exempt for opposite reasons: a DERIVED entry is
#: SUPPOSED to name the equation it inverted, and an INPUT entry names a
#: caller default. It is the middle two that get promoted.
UNDERIVED_LABELS = ("EMPIRICAL", "RECEIPT ONLY")

#: Language that turns a description into a causal claim. Deliberately
#: small and literal: a regex that tried to parse intent would fire on
#: honest prose, and a fence people route around is worse than none.
#: MEASURED against the tree as it stands: these phrases produce exactly
#: ONE hit across 17 basis strings, and that hit is real (see
#: `PINNED_MECHANISM_CLAIMS`).
CAUSAL_PHRASES = (
    "because",
    "mechanism",
    "caused by",
    "physical law",
    "explains",
    "explained by",
    "the cause of",
    "proves that",
    "is why",
)

#: Words that mark a crossover citation as an OBSERVATION rather than a
#: cause. Any live artefact that cites the mesh-scale crossover must carry
#: one of these in the same paragraph.
REFUTATION_MARKERS = (
    "refuted", "predictor", "predictive", "hypothesis",
    "receipt only", "not a mechanism", "unexplained", "empirical",
)

#: How the MESH-SCALE crossover — an EMPIRICAL predictor with both proposed
#: mechanisms REFUTED — is told apart from the four unrelated "crossover"s in
#: this tree (Holtrop's C_B crossover, the 2.61 m regime crossover, the
#: catamaran branch crossover, the small-craft 2 m band). A citation counts
#: only if it carries the crossover's own coordinates.
#:
#: This comment states the standing because THIS FILE IS SCANNED BY ITS OWN
#: FENCE, and the first run of it failed here. That is the fence working:
#: there is no exemption for the scanner, and a rule its author is exempt
#: from is a rule.
CROSSOVER_BAND_MARKERS = ("4.6", "5.8", "4.592", "5.803",
                          "baseline skew", "baseline mesh health")

#: ROLLING/IMMUTABLE HISTORICAL CHANNELS, excluded with a reason.
#:
#: `docs/audit/STATUS.md` is the machine-to-machine log and
#: `docs/GAP-REGISTER.md` is immutable by CLAUDE.md's own table ("the
#: register's prose as a current state" is listed as the WRONG source).
#: Both correctly contain the crossover stated as a live hypothesis on the
#: day it was one — MEASURED: three STATUS.md paragraphs cite the band with
#: no refutation marker, and all three predate `57da605`. A fence that
#: forced those to be edited would be deleting a historical finding to make
#: a test green, which is the defect this file exists to prevent, committed
#: by the file itself. What makes the history safe to read is that
#: `docs/research/CROSSOVER.md` exists and carries the refutation — which
#: is fence 3, and is why fence 3 is not optional.
HISTORICAL_CHANNELS = (
    "docs/audit/STATUS.md",
    "docs/GAP-REGISTER.md",
)

#: THE ONE MECHANISM CLAIM THAT STANDS, PINNED BY ITS SCOPE.
#:
#: `basis["n_layers"]` in `navalai/contract.py` says the derived layer count
#: "IS the mesh-success mechanism ON THOSE HULLS". That is a mechanism claim
#: inside a RECEIPT ONLY string, and it is allowed for two reasons that are
#: checkable rather than asserted:
#:
#:   1. it was PRE-DECLARED. `docs/audit/H011-H012-ROOT-CAUSE.md` §7 wrote
#:      the test before the data — "if h011 and h012 mesh at n = 6 or 5 with
#:      0 wrongly-oriented faces, the mechanism is the derived layer count" —
#:      and the measurement then came back that way (mesh at n=6, fail at
#:      n=7 with 13/12 wrong-oriented faces);
#:   2. it is SCOPED TO TWO HULLS and says so in the sentence. The same
#:      document states the limit in the same breath: "No admissible-region
#:      boundary is derivable from N=2."
#:
#: So it is pinned, not exempted. The scope tokens below are asserted to
#: still be in the string, which means the sentence cannot be widened into a
#: universal rule — deleting "on those hulls" or "h011/h012" fails this
#: file. Rewording it in any other way also fails it, by design: a new hit
#: appears and has to be justified here in front of a reader.
PINNED_MECHANISM_CLAIMS = (
    {
        "path": "navalai/contract.py",
        "label": "RECEIPT ONLY",
        "key": "n_layers_to_bridge",
        "scope_tokens": ("h011/h012", "on those hulls", "MEASURED"),
        "why": ("pre-declared in docs/audit/H011-H012-ROOT-CAUSE.md §7 and "
                "scoped to N=2 in the sentence itself"),
    },
)


# --------------------------------------------------------------------------
# scanners — plain functions so they can be pointed at a crafted tree
# --------------------------------------------------------------------------

def _render(node: ast.AST) -> str | None:
    """A string literal's text, with `{BASIS_*}` placeholders resolved.

    The basis strings are f-strings that open with the label as a NAME
    (`f"{BASIS_RECEIPT}: ..."`), so a scanner that only read `ast.Constant`
    would see them start with `{}` and skip every one of them — finding
    nothing, and passing. Non-basis interpolations collapse to `{}`, which
    is enough: a causal claim is made in prose, not in a format spec.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out: list[str] = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                out.append(v.value)
            elif isinstance(v, ast.FormattedValue):
                t = v.value
                if isinstance(t, ast.Name) and t.id.startswith("BASIS_"):
                    out.append({"BASIS_DERIVED": "DERIVED",
                                "BASIS_EMPIRICAL": "EMPIRICAL",
                                "BASIS_RECEIPT": "RECEIPT ONLY",
                                "BASIS_INPUT": "INPUT"}.get(t.id, "{}"))
                else:
                    out.append("{}")
        return "".join(out)
    return None


def basis_strings(*roots: Path) -> list[tuple[Path, int, str, str]]:
    """Every string literal that OPENS with a basis label.

    Opening with the label is `MeshPrescription`'s own contract ("no basis
    that does not open with one of these four words"), which is what makes
    this a scan of RECEIPTS rather than a grep for a word that also appears
    in every docstring discussing them.
    """
    found: list[tuple[Path, int, str, str]] = []
    for root in roots:
        for p in sorted(root.rglob("*.py")):
            try:
                tree = ast.parse(p.read_text(errors="replace"))
            except SyntaxError:                       # a file mid-edit
                continue
            for n in ast.walk(tree):
                s = _render(n)
                if not s:
                    continue
                for lab in BASIS_LABELS:
                    if s.startswith(lab + ":"):
                        found.append((p, getattr(n, "lineno", 0), lab, s))
                        break
    return found


def causal_hits(text: str) -> tuple[str, ...]:
    """The causal phrases present in `text`, as whole words."""
    low = text.lower()
    return tuple(ph for ph in CAUSAL_PHRASES
                 if re.search(r"(?<![a-z])" + re.escape(ph) + r"(?![a-z])",
                              low))


def promoted_basis_strings(*roots: Path) -> list[tuple[Path, int, str, str,
                                                       tuple[str, ...]]]:
    """UNDERIVED basis strings that have grown a causal claim."""
    out = []
    for p, ln, lab, s in basis_strings(*roots):
        if lab not in UNDERIVED_LABELS:
            continue
        hits = causal_hits(s)
        if hits:
            out.append((p, ln, lab, s, hits))
    return out


def _paragraphs(text: str) -> list[str]:
    """Blank-line-separated blocks.

    Works on Markdown prose and on contiguous `#` comment blocks alike,
    which is what lets one scanner cover both `docs/` and the comment that
    sits above a basis string.
    """
    out: list[str] = []
    cur: list[str] = []
    for line in text.splitlines():
        if line.strip():
            cur.append(line)
        elif cur:
            out.append("\n".join(cur))
            cur = []
    if cur:
        out.append("\n".join(cur))
    return out


def crossover_citations(files) -> list[tuple[Path, str, bool]]:
    """Every paragraph that cites the MESH-SCALE crossover.

    Returns (path, paragraph, is_marked). `is_marked` is True when the
    paragraph itself says the thing is an observation — that is the whole
    bar: cite it with its standing, or do not cite it.
    """
    out = []
    for p in files:
        try:
            t = p.read_text(errors="replace")
        except OSError:
            continue
        if "crossover" not in t.lower():
            continue
        for par in _paragraphs(t):
            low = par.lower()
            if "crossover" not in low:
                continue
            if not any(b.lower() in low for b in CROSSOVER_BAND_MARKERS):
                continue
            out.append((p, par,
                        any(m in low for m in REFUTATION_MARKERS)))
    return out


def _live_files() -> list[Path]:
    """Everything a session reads as CURRENT, minus the history channels."""
    excluded = {ROOT / rel for rel in HISTORICAL_CHANNELS}
    files: list[Path] = []
    for pat in ("*.md", "*.py"):
        for p in ROOT.rglob(pat):
            if ".git" in p.parts or p in excluded:
                continue
            files.append(p)
    return sorted(files)


# --------------------------------------------------------------------------
# fence 0 — the scanners reach what they claim to guard
# --------------------------------------------------------------------------

def test_the_basis_scanner_actually_reaches_the_strings_it_guards():
    """A scan that finds nothing passes every assertion about what it found.

    docs/LESSONS.md defect class 1, in its purest form: `${_MQ_SKEW:-0}`
    turned "could not measure" into a score of 0 against a bar of 20. A
    walk that silently stopped — a moved package, an f-string form this
    renderer does not handle — would turn "could not read the receipts"
    into "no receipt claims a mechanism". So the scan's own yield is a bar.

    MEASURED 2026-08-20: 17 basis strings across navalai/ and scripts/,
    covering all four labels. The floor is set below that, not at it, so
    normal drift does not fail this test — but a collapse does.
    """
    found = basis_strings(ROOT / "navalai", ROOT / "scripts")
    assert len(found) >= 12, (
        "the basis scan returned only %d strings; it found 17 when this "
        "fence was written, so it is the SCANNER that is broken, not the "
        "tree that is clean" % len(found))
    labels = {lab for _, _, lab, _ in found}
    assert labels == set(BASIS_LABELS), (
        "the scan missed a whole label kind: found %s, expected %s. A "
        "renderer that cannot see one form of basis string is a fence with "
        "a hole in exactly the shape of that form."
        % (sorted(labels), sorted(BASIS_LABELS)))
    assert any(lab == "RECEIPT ONLY" for _, _, lab, _ in found)


def test_the_crossover_scanner_actually_reaches_the_documents():
    """Fence 0 for the citation scan, for the same reason."""
    cites = crossover_citations(_live_files())
    assert len(cites) >= 3, (
        "only %d crossover citations found; there were 5 in the live tree "
        "when this was written" % len(cites))
    assert any(c[0].name == "CROSSOVER.md" for c in cites), (
        "the scan did not reach docs/research/CROSSOVER.md, which is the "
        "one document guaranteed to cite the crossover")


# --------------------------------------------------------------------------
# fence 1 — a RECEIPT ONLY / EMPIRICAL basis may not claim causation
# --------------------------------------------------------------------------

def test_no_underived_basis_string_claims_a_mechanism():
    """THE BAR. A receipt describes what happened; it may not say why.

    Reword `"RECEIPT ONLY: measured on 4 points"` into `"RECEIPT ONLY:
    scale helps BECAUSE the background cell ..."` and every existing check
    still passes — the label is intact, the vocabulary test is intact, and
    a number whose standing is one experiment now reads as a law. That edit
    fails here.

    The single standing exception is pinned in `PINNED_MECHANISM_CLAIMS`
    with its justification, and the next test asserts its scope survives.
    """
    hits = promoted_basis_strings(ROOT / "navalai", ROOT / "scripts")
    pinned_keys = {c["key"] for c in PINNED_MECHANISM_CLAIMS}
    unpinned = [h for h in hits if not any(k in h[3] for k in pinned_keys)]
    assert not unpinned, (
        "%d RECEIPT ONLY/EMPIRICAL basis string(s) now claim causation. A "
        "receipt is one experiment's measured envelope; if the evidence "
        "really supports a mechanism, meet the bar in "
        "docs/research/CROSSOVER.md SS5 and relabel it — do not reword the "
        "receipt.\n%s" % (len(unpinned), "\n".join(
            "  %s:%d [%s] %s\n     %s"
            % (h[0].relative_to(ROOT), h[1], h[2], list(h[4]),
               " ".join(h[3].split())[:300]) for h in unpinned)))


def test_the_pinned_mechanism_claim_keeps_the_scope_that_justifies_it():
    """The pinned claim is allowed because it is SCOPED. Check the scope.

    `basis["n_layers"]` may say the derived count IS the mesh-success
    mechanism only while it also says WHERE: on h011/h012, two hulls, from
    a pre-declared test. Widen it — drop "on those hulls", drop the hull
    names — and it becomes the universal rule
    docs/audit/H011-H012-ROOT-CAUSE.md SS7.4 explicitly refuses ("No
    admissible-region boundary is derivable from N=2"). This is the clause
    that makes the pin a pin rather than an exemption.
    """
    found = basis_strings(ROOT / "navalai", ROOT / "scripts")
    for claim in PINNED_MECHANISM_CLAIMS:
        matching = [(p, ln, lab, s) for p, ln, lab, s in found
                    if p == ROOT / claim["path"]
                    and lab == claim["label"] and claim["key"] in s]
        assert len(matching) == 1, (
            "the pinned claim %r is no longer findable in %s (%d matches). "
            "If it was deleted, delete its pin; if it moved, re-pin it — "
            "an exception nobody can locate is an exception nobody reviews."
            % (claim["key"], claim["path"], len(matching)))
        _, _, _, text = matching[0]
        missing = [t for t in claim["scope_tokens"] if t not in text]
        assert not missing, (
            "the pinned mechanism claim in %s lost its scope: %s. It is "
            "pinned ONLY because it is %s. Without the scope it is a "
            "universal rule on N=2 and this file refuses it.\n     %s"
            % (claim["path"], missing, claim["why"],
               " ".join(text.split())[:300]))


def test_the_runtime_receipt_carries_the_same_words_the_scan_read():
    """Scan the OBJECT, not only the source.

    docs/LESSONS.md, 2026-08-20: "check the artefact, not the summary of
    it." A static scan of source is a summary of what a caller receives —
    it cannot see a string assembled at runtime, or a basis entry composed
    from a variable. So the same rule is applied to the dict a real
    `mesh_prescription` call actually returns.
    """
    from navalai.contract import mesh_prescription

    p = mesh_prescription(lwl_m=11.36, speed_ms=2.639, fn=0.25)
    assert p.basis, "the prescription returned no basis at all"
    bad = []
    for key, val in p.basis.items():
        if not isinstance(val, str):
            continue
        if not any(val.startswith(lab + ":") for lab in UNDERIVED_LABELS):
            continue
        hits = causal_hits(val)
        if hits and key != "n_layers":          # the pinned claim, above
            bad.append((key, hits, val))
    assert not bad, (
        "the runtime receipt claims causation where the source scan did "
        "not: %s" % [(k, h) for k, h, _ in bad])


def test_the_basis_fence_fires_on_a_crafted_promotion(tmp_path):
    """BOTH DIRECTIONS, on a tree built for the purpose.

    docs/LESSONS.md defect class 3: "every threshold ships with a test
    feeding it the VERBATIM input it must reject. A test showing a guard
    accepts a good case proves nothing about rejection." The violating file
    below is the real `mesh_density_evidence` string with one clause added —
    the exact edit this fence exists to stop.
    """
    pkg = tmp_path / "crafted"
    pkg.mkdir()
    (pkg / "clean.py").write_text(
        'BASIS_RECEIPT = "RECEIPT ONLY"\n'
        'basis = {}\n'
        'basis["mesh_density_evidence"] = (\n'
        '    "RECEIPT ONLY: a universal scale bump is refuted (the sign "\n'
        '    "flips with baseline mesh health, +41% to -58%). The '
        'conditional "\n'
        '    "form is an untested hypothesis on 4 points.")\n'
        'basis["cost"] = f"{BASIS_EMPIRICAL}: a FITTED cost model"\n')
    (pkg / "promoted.py").write_text(
        'BASIS_RECEIPT = "RECEIPT ONLY"\n'
        'basis = {}\n'
        'basis["mesh_density_evidence"] = (\n'
        '    "RECEIPT ONLY: a universal scale bump helps a strained mesh "\n'
        '    "because the background cell is coarse relative to the "\n'
        '    "tightest feature — that is the mechanism, and it explains "\n'
        '    "the sign flip as a physical law.")\n')
    (pkg / "fstring.py").write_text(
        'from navalai.contract import BASIS_RECEIPT\n'
        'basis = {}\n'
        'basis["n"] = f"{BASIS_RECEIPT}: n=5 held because the stack folds"\n')

    # the scan must see all three files (fence 0, applied to the fixture)
    assert len(basis_strings(pkg)) >= 4, "the crafted tree was not scanned"

    flagged = {h[0].name: set(h[4]) for h in promoted_basis_strings(pkg)}
    assert set(flagged) == {"promoted.py", "fstring.py"}, (
        "expected exactly the two crafted violations, got %s"
        % sorted(flagged))
    # the clean file must NOT be flagged — a fence that fires on honest
    # prose gets switched off within a day
    assert "clean.py" not in flagged
    assert {"because", "mechanism", "explains", "physical law"} <= \
        flagged["promoted.py"]
    # and the f-string form is caught, which is the form the real code uses
    assert "because" in flagged["fstring.py"], (
        "an f-string basis was not rendered; every real basis string in "
        "navalai/contract.py is an f-string, so this form is the fence")


# --------------------------------------------------------------------------
# fence 2 — the crossover is never cited as a mechanism
# --------------------------------------------------------------------------

def test_every_live_citation_of_the_crossover_carries_its_standing():
    """Cite the crossover WITH its standing, or do not cite it.

    The crossover earned the right to be used: 6/6 out of sample across
    three families. It did not earn the right to be explained — both
    candidate mechanisms are refuted, one by counterexample and one by
    permutation at family-wise p = 0.700. The failure mode is not somebody
    writing "the mechanism is X"; it is somebody quoting the 4.6-5.8 band
    in a new document with the caveat left behind, after which the next
    reader has a rule with no standing attached.

    MEASURED: 5 live citations before this fence existed, all 5 marked; 11
    after, once this file, its gate row and docs/research/CROSSOVER.md SS6 are
    counted — the scanner is not exempt from itself, and its own comment block
    failed the first run. The three UNMARKED citations are all in
    docs/audit/STATUS.md and all predate `57da605` — see HISTORICAL_CHANNELS
    for why they stay there rather than being edited.
    """
    unmarked = [(p, par) for p, par, ok in crossover_citations(_live_files())
                if not ok]
    assert not unmarked, (
        "%d live paragraph(s) cite the mesh-scale crossover without saying "
        "it is an empirical predictor with both mechanisms refuted. Add the "
        "standing or drop the citation; see docs/research/CROSSOVER.md.\n%s"
        % (len(unmarked), "\n".join(
            "  %s: %s" % (p.relative_to(ROOT), " ".join(par.split())[:220])
            for p, par in unmarked)))


def test_the_crossover_fence_fires_on_a_crafted_citation(tmp_path):
    """BOTH DIRECTIONS again, and the negative case matters as much.

    The unmarked document is the realistic accident: a new design note that
    quotes the band as a rule. The marked one is the same sentence written
    honestly. A fence that could not tell them apart would either be noise
    or be nothing.
    """
    bad = tmp_path / "unmarked.md"
    bad.write_text(
        "## Mesh scale rule\n\n"
        "Bump the background density 1.75% when baseline skewness is above "
        "the crossover at 4.6-5.8; below it, do not.\n")
    good = tmp_path / "marked.md"
    good.write_text(
        "## Mesh scale, as an empirical predictor\n\n"
        "The crossover near baseline skew 4.6-5.8 is a RECEIPT ONLY "
        "observation: it predicted 6/6 out of sample, and both proposed "
        "mechanisms are refuted. Do not write it as a rule.\n")
    unrelated = tmp_path / "unrelated.md"
    unrelated.write_text(
        "## Holtrop\n\nThe crossover moves with C_B, C_M and C_WP and sits "
        "near 195 for that hull.\n")

    cites = crossover_citations([bad, good, unrelated])
    names = {p.name: ok for p, _, ok in cites}
    assert names.get("unmarked.md") is False, (
        "the crafted unmarked citation was not caught")
    assert names.get("marked.md") is True
    assert "unrelated.md" not in names, (
        "the scanner fired on Holtrop's C_B crossover — the band markers "
        "are what separate the mesh-scale crossover from the four unrelated "
        "'crossover's in this tree, and they did not")


def test_the_history_exclusion_cannot_quietly_cover_a_live_document():
    """An exclusion list is a hole; keep it small, named, and real.

    Every excluded path must EXIST — a stale entry is a hole in the fence
    pointing at nothing, and a renamed live document would slip through one
    silently. And `docs/research/CROSSOVER.md` must never be excluded: it
    is the record the exclusions depend on for their justification.
    """
    for rel in HISTORICAL_CHANNELS:
        assert (ROOT / rel).exists(), (
            "%s is excluded from the crossover fence but does not exist. "
            "Either the file moved (re-point the exclusion) or the "
            "exclusion is dead (delete it)." % rel)
    assert "docs/research/CROSSOVER.md" not in HISTORICAL_CHANNELS
    assert len(HISTORICAL_CHANNELS) <= 2, (
        "the history exclusion has grown; each entry is a document the "
        "fence cannot see, so each one needs a reason written down")


# --------------------------------------------------------------------------
# fence 3 — the refutation record survives
# --------------------------------------------------------------------------

CROSSOVER_DOC = ROOT / "docs" / "research" / "CROSSOVER.md"


def test_the_crossover_record_keeps_both_refutations():
    """The record is what makes the history readable; it may not thin out.

    `635eb07` moved these refutations out of commit messages and a rolling
    log into `docs/research/`, because CLAUDE.md routes "what was MEASURED,
    and what was refuted" there. A document that keeps the 6/6 prediction
    and loses the two refutations is strictly WORSE than no document: it
    reads as an endorsement.

    Every token below is a load-bearing part of a refutation, not a phrase
    from the prose around it.
    """
    assert CROSSOVER_DOC.exists(), (
        "docs/research/CROSSOVER.md is gone — the crossover refutation is "
        "back to living only in commit messages and a rolling log, which "
        "is the state 635eb07 was written to end")
    t = CROSSOVER_DOC.read_text()

    # both mechanisms, by name, with how each died
    for token, what in (
            ("REFUTED BY COUNTEREXAMPLE", "mechanism 1's manner of death"),
            ("REFUTED BY PERMUTATION", "mechanism 2's manner of death"),
            ("tightest feature", "mechanism 1's name"),
            ("panel_twist_deg_per_m", "mechanism 2's name"),
            ("wave-piercing", "the counterexample hull that killed "
                              "mechanism 1"),
            ("0.700", "the family-wise p that killed mechanism 2"),
            ("1.40", "the mean separators under permutation, against 1 "
                     "observed — the number that makes p=0.700 legible"),
    ):
        assert token in t, (
            "docs/research/CROSSOVER.md no longer carries %r (%s). A "
            "refutation that loses its evidence gets re-proposed."
            % (token, what))

    # and the standing, stated as a standing
    assert "PREDICTIVE != CAUSAL" in t or "PREDICTIVE" in t
    assert "EMPIRICAL PREDICTOR ONLY" in t


def test_the_crossover_record_keeps_the_observation_it_refutes_around():
    """A refutation record must keep the RESULT, or it is a retraction.

    The observation is real and is this campaign's strongest empirical
    finding. Deleting it while keeping the refutations would be the mirror
    error, and would lose a predictor that earned 6/6 out of sample.
    """
    t = CROSSOVER_DOC.read_text()
    for token in ("+13%", "+41%", "-29%", "-58%",   # the four deltas
                  "3.279", "4.592", "5.803", "10.757",   # their baselines
                  "6/6", "d92d548"):
        assert token in t, (
            "docs/research/CROSSOVER.md lost %r — the observation is REAL "
            "and survives; only the mechanisms are refuted" % token)


def test_the_crossover_record_keeps_the_bar_for_re_opening():
    """The five clauses are what stop the next re-proposal being cheap.

    Without them, "REFUTED" is an opinion and the next session's plausible
    story reopens it. With them, a new mechanism must be pre-declared,
    survive the wave-piercing counterexample, survive the SAME permutation
    instrument, break the size confound and predict out of sample.
    """
    t = CROSSOVER_DOC.read_text()
    for token, what in (
            ("BAR FOR RE-OPENING", "the section itself"),
            ("BEFORE the data", "clause 1: pre-declaration"),
            ("permutation test at family-wise p < 0.05",
             "clause 3: the same instrument, not a weaker one"),
            ("SIZE confound", "clause 4: all out-of-sample hulls are "
                              "12-13.5 m"),
            ("out of sample", "clause 5"),
    ):
        assert token in t, (
            "docs/research/CROSSOVER.md lost %r (%s) — without the bar, "
            "the refutation is prose" % (token, what))


def test_the_record_points_at_this_fence():
    """The document and the fence must know about each other.

    A record with no executable half drifts; a fence with no record is a
    string comparison nobody can justify. CROSSOVER.md names this file, and
    this test fails if that reference is dropped — which is the same
    two-way binding `navalai/gates.py` keeps between a gate row and its
    suite.
    """
    t = CROSSOVER_DOC.read_text()
    assert "tests/test_evidence_promotion.py" in t, (
        "docs/research/CROSSOVER.md no longer names the fence that enforces "
        "it; a reader has no way to find out the record is checked")


@pytest.mark.parametrize("phrase", CAUSAL_PHRASES)
def test_every_causal_phrase_is_detectable(phrase):
    """The vocabulary is only a fence if each word in it actually matches.

    A typo in `CAUSAL_PHRASES` — a trailing space, a smart quote — is a
    silent hole exactly the width of that phrase, and nothing else in this
    file would notice.
    """
    assert phrase in causal_hits("RECEIPT ONLY: measured, and %s x" % phrase)
    # and it must not fire on a word that merely contains it, which is what
    # the word-boundary lookarounds are for
    assert phrase not in causal_hits(
        "RECEIPT ONLY: measured, and z%sz x" % phrase)
