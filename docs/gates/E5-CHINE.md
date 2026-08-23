# Gate E5-CHINE — the hard-chine branch of the hull grammar

**Status: RED.** Not for want of evidence. The evidence was acquired, it is
public-domain and closed-form, and the kernel measurably cannot express it.

---

## Why this is a separate gate from E5

E5 is green: 53 published hulls, three independent source families, and the
kernel reproduces their six parameters to within a few parts in ten thousand.
Every hull in that corpus is **round-bilge or mathematical**.

NavalAI designs plywood stitch-and-glue boats. Those are **hard-chine by
construction**, and a chine is a *discontinuity in surface slope* — which is
exactly the thing no quantity in E5 can see. Displaced volume, waterplane
area, prismatic coefficient and the sectional-area curve are all integrals,
and an integral does not notice a corner: a sharp chine and a radiused bilge
of the same sectional area agree on every one of them.

So the two claims are kept apart, and this file is what stops the weaker one
being quoted as the stronger:

> **E5** — the kernel reproduces published round-bilge hull families.
> **E5-CHINE** — the kernel reproduces published hard-chine hull families.

`roundness = 0` in the grammar is a *claim* that the kernel draws a chine.
This gate tests the claim rather than trusting the parameter's name.

---

## The evidence acquired

**Fridsma, G., "A Systematic Study of the Rough-Water Performance of Planing
Boats", Davidson Laboratory / Stevens Institute of Technology, Report R-1275,
November 1969.** DTIC accession AD0708694; the document carries *"Approved for
public release; distribution is unlimited"* on its own cover.

This source is unusually strong, and the distinction matters. It is **not** a
body plan traced off a scan. Figure 1, *"Lines of Prismatic Models"*, **prints
the equations**:

```
chine planform    (x/9)^2 + (y/4.5)^2   = 1
keel profile      (x/9)^2 + (8y/4.5)^2  = 1
```

with a 9.00 in beam, a bow one beam long, model lengths 36/45/54 in
(L/b = 4, 5, 6), deadrise 10/20/30 deg, a depth of 5⅝ in, and vertical
topsides above the chine; the text (p. 9) states that "sections aft of the bow
were constant hard-chine prismatic forms". The geometry is therefore
**evaluated from published closed forms** — `geometry_status =
PUBLISHED_PARAMETRIC`, with no transcription and no digitisation anywhere in
the chain, exactly as the Wigley hull is handled in E5.

The design waterline is published too, which a planing hull otherwise lacks:
the report tests at load coefficients Δ/(w·b³) of 0.304, 0.608 and 0.912, so
the condition is *"floating at rest at a published load"*, not a draft this
project invented.

Five hulls: `fridsma_b10_lb5`, `b20_lb4`, `b20_lb5`, `b20_lb6`, `b30_lb5`.

**De Luca, F. and Pensa, C., "The Naples warped hard chine hulls systematic
series", Ocean Engineering 139 (2017) 205–236.** Open access, CC BY-NC-ND.
Used for its Table 1(a, b), p. 206 — a survey of the **deadrise distribution**
of eight systematic hard-chine series, each as three published numbers. That
table is what makes the warp test below possible without any offsets at all.

---

## Result 1 — the round-trip is REFUSED, and the number is the prismatic

Every Fridsma hull sits inside the genome's box on LWL, BWL, T, D and LCB.
Only one parameter is out, and it is out by a long way:

| | Cp |
|---|---|
| genome box ceiling (`limits.prismatic_target`) | **0.710** |
| what the kernel's SAC family can actually build | **≈ 0.848** |
| Fridsma prismatic planing hulls | **0.951 – 0.971** |

The kernel refuses in its own words:

```
sac: Cp 0.9500 unreachable at x_mb 0.540, r_transom 0.275
     with exponents in [-6.0, 8.0]
```

**Lifting the box bound would not fix it.** Sweeping `r_transom` and `x_mb`
across their whole ranges, the largest prismatic coefficient the kernel will
build is 0.848 — the sectional-area-curve family is a power law and cannot
approach a constant-section prism. That is the missing information stated
precisely: **the grammar has no parallel middle body.**

This is the *same* gap E5 found from the opposite direction. Series 60, a full
merchant form with a long parallel middle body, leaves the worst geometric
residual in the entire E5 corpus (16.6% of half-beam) for the same structural
reason. Two unrelated families, one missing gene.

`data/e5_hard_chine_roundtrip.json` also records a **nearest expressible**
hull for each fixture, with Cp clamped to what the kernel can build. Every one
of those records carries `is_pass: false`. It is a diagnostic — "how close can
this grammar get, and what does it get wrong" — and is never a result,
because a hull with a clamped Cp is not the hull the source describes.

---

## Result 2 — monohedral chines fit exactly, warped chines do not

The deadrise law in `navalai/geometry.py`:

```
beta(x) = beta_mid                                   x <= (1 - beta_len)·L
beta(x) = beta_mid + (beta_bow - beta_mid)·frac^2    forward of that
```

`beta_len` is bounded at 0.60, so **the deadrise is constant over at least the
after 40% of every hull this grammar can build**, and warps only forward.

Fitted to each published series (`scripts/e5_chine_warp.py`), deadrise in
degrees at the transom / 50% LWL / 75% LWL:

| series | published | best fit | max err | expressible |
|---|---|---|---|---|
| Series 62 (Clement & Blount 1963) | 12.5/13.0/19.2 | 12.5/13.0/19.2 | **0.00°** | YES |
| Keuning & Gerritsma 1982 | 25.0/26.0/30.7 | 25.0/25.5/30.7 | 0.53° | YES |
| Taunton & Alii 2010 | 22.5/22.5/35.3 | 23.1/23.9/32.3 | 3.02° | no |
| USCG (Kowalyshyn & Metcalf 2006) | 16.6/22.5/34.4 | 20.4/21.2/30.5 | 3.92° | no |
| Keuning & Alii 1993 | 30.0/31.2/35.8 | 25.0/25.7/33.5 | 5.51° | no |
| NSS (De Luca & Pensa 2017) | 13.2/22.3/38.5 | 20.0/20.9/30.2 | **8.27°** | no |
| NTUA (Grigoropoulos & Loukakis) | 10.0/22.5/38.0 | 18.6/19.5/29.3 | **8.69°** | no |

**2 of 7.** The split is not random — it is exactly monohedral versus warped.
A monohedral hull has constant deadrise aft, which is what the law assumes, so
Series 62 fits to *zero*. A warped hull's deadrise grows from the transom
onward, which is warp in precisely the region the law holds flat; the fit
drives `beta_bow` to its 50° ceiling and still lands 8° out.

Keuning & Alii 1993 fails for a different and simpler reason, kept separate
because it has a different fix: its deadrise is 30° and `beta_mid` is bounded
at **25°**, so a deep-V is outside the *box*, not outside the *law*.

**Why this one matters most for this product.** A warped bottom is what a
developable-panel hull naturally wants — the Naples parent was explicitly
"changed to obtain the plating as developable surfaces" so it could be built
from rigid panels. That is not an exotic form NavalAI can decline. It is
arguably the form NavalAI is *for*, and the grammar cannot draw it.

---

## What the genome is missing, in three lines

1. **A parallel middle body.** `x_mb` places a single maximum-area station, so
   the SAC cannot hold constant. Ceiling: Cp ≈ 0.848 against a real 0.95–0.97.
2. **An aft deadrise warp.** Deadrise is constant over ≥40% of the hull.
   Ceiling: 8–9° of error on any warped series.
3. **Deep-V deadrise.** `beta_mid` stops at 25°; published series reach 30°.

None of these was adjusted to make anything pass. Each is a bound or a
functional form, each is named with the file it lives in, and each is a
decision for the project owner rather than for this gate.

---

## What is NOT claimed

- Not that the kernel is wrong. It reproduces monohedral chine geometry
  exactly and round-bilge hulls to a few parts in ten thousand (see E5).
- Not that these hulls should be in scope. A prismatic planing boat at Cp 0.96
  is a different craft from a semi-displacement plywood cruiser, and the Cp
  bound descends from a displacement-hull design table. **The finding is that
  the envelope excludes them, stated with numbers, so the exclusion is a
  choice rather than an accident.**
- Not that the corpus is finished. It has one hard-chine family. NSS and
  Series 62 offsets would make it three; the acquisition status of each is in
  `data/e5_sources.md`.

---

## Reproducing it

```bash
python scripts/build_e5_chine.py                    # fixtures from Fig. 1
python -c "import sys;sys.path.insert(0,'.');\
from scripts.build_e5_chine import roundtrip;roundtrip()"
python scripts/e5_chine_warp.py                     # the deadrise survey
python -m pytest tests/test_e5_hard_chine.py -q
```
