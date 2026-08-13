# Hull-generation generative-model papers — what is actionable for NavalAI

**STATUS: COMPLETE** (read 2026-08-13). Four papers.

This is a RESEARCH RECORD in the sense of `CLAUDE.md`: it records what four
papers MEASURE and SAY, with page/section/equation/table references, and marks
everything else as INFERENCE. **It carries no project status and no plan** — for
status ask `python -m navalai.gates`, for outstanding work
`python scripts/reconcile_gaps.py`, for order and ownership `docs/BUILD-PLAN.md`.

Papers live in `downloads/hull-examples/research-gate/` (gitignored downloads
tree). Text extracted with `pypdf` 6.14.2; all four PDFs have complete text
layers, no page rendering was needed.

## The three findings that matter most, up front

1. **⚠️ A misattribution to correct before it is relied on.** The figures
   "surface area up 2.1×, bottom-half surface 4.4×, Gaussian curvature 1.51×"
   are **from ShipGen (Bagazinski & Ahmed, JMSE 2023), not from ShipHullGAN.**
   ShipHullGAN reports no such numbers anywhere in its 28 pages. Exact values and
   the authors' own verdict ("**This is not desirable**") are in §2.1.
2. **No representation in these four papers can draw a DOUBLE CHINE**, and three
   of the four cannot represent a chine at all. Our measured gap is not closed by
   this literature. Table and reasoning in §5.0.
3. **A GAN trained on 30,000 feasible hulls generated feasible hulls 0.7% of the
   time** — against 0.67% for uniform random sampling, and 99.5% for guided
   diffusion with an explicit constraint classifier (ShipGen §4.1–4.2). Learning
   feasibility implicitly from examples did not work.

| § | Paper | Year | Model | Representation | Chine? |
|---|---|---|---|---|---|
| 1 | Khan, Goucher-Lambert, Kostas & Kaklis — **ShipHullGAN** | 2023 | DCGAN | body-plan offsets grid → NURBS loft | not addressed; C2 by construction |
| 2 | Bagazinski & Ahmed — **ShipGen** | 2023 | **diffusion (DDPM)** | **45-term analytic parameter vector** | **yes, one** |
| 3 | Yonekura, Omori, Qi & Suzuki | 2025 | cWGAN-GP | offsets from generalized Wigley | no |
| 4 | Trinh, Hamagami & Okamoto | 2024 | GAN + RaD | depth map, 1 px/m² | no |

---

## Paper 1 — ShipHullGAN

> Shahroz Khan, Kosa Goucher-Lambert, Konstantinos Kostas, Panagiotis Kaklis,
> "ShipHullGAN: A generic parametric modeller for ship hull design using deep
> convolutional generative model", *Computer Methods in Applied Mechanics and
> Engineering* **411** (2023) 116051.
> https://doi.org/10.1016/j.cma.2023.116051 — open access, CC BY-NC-ND.
> 28 pages. Affiliations: Strathclyde (NAOME), UC Berkeley (ME), Nazarbayev.
> File: `1-s2.0-S0045782523001755-main.pdf`.

### 1.1 THE SHAPE REPRESENTATION (§3.2–§3.3, Figs. 8–12) — the important part

**It is a BODY-PLAN GRID OF POINTS: a fixed-size table of cross-section
offsets.** Not a point cloud, not an SDF, not voxels, not a control net. The
paper explicitly considers and REJECTS SDF, voxels, point clouds and meshes
(§3.2, p. 9): they "often result in the loss of local geometric features" and
"commonly lack surface smoothness, which is crucial for several engineering
analyses". It also rejects a common NURBS representation as "not a trivial
task" to impose across different design classes (§3.2, p. 9), noting the
training hulls genuinely differ — Fig. 7 shows DTMB as ONE NURBS surface while
KCS and S-175 are multi-patch with different control-point counts.

The encoding procedure, verbatim in structure (§3.2, p. 10, Fig. 8):

1. Place the hull in its smallest axis-aligned bounding box, dimensions
   `L̄, B̄, D̄`.
2. Non-dimensionalise by `L̄` → box `1 × B̄/L̄ × D̄/L̄`. (Length-scaling only;
   B/L and D/L are therefore free and encoded IN the data.)
3. Split the hull longitudinally on the NON-UNIFORM partition
   **`[0, 0.1, 0.3, 0.8, 1]`** — `P1` bow, `P2` fore transition, `P3` wall-sided
   midship, `P4` stern.
4. Total cross-sections `E = 4Ē`; each of the four regions gets `E/4` EQUALLY
   SPACED cross-sections. This deliberately puts dense sections where the shape
   changes fast (P1, P2, P4) and sparse ones through the near-prismatic midbody
   (P3).
5. Each cross-section is divided into `N` points **equally spaced by ARC
   LENGTH** (Fig. 8(i,j)).

**Resolution: `E = 56` cross-sections × `N = 25` points per section** (§3.3,
p. 10). "We have experimented with different grid resolutions, but ... the
employed, relatively low, resolution of 25 × 56 grid points provides sufficient
surface reconstruction accuracy while preserving both local and global geometric
features" (§3.3, p. 10, citing Fig. 10).

The design becomes **three `[25 × 56]` matrices** — one each for x, y, z
coordinates of the grid (§3.3, Fig. 11) — i.e. the network sees the offsets
table as a 3-CHANNEL IMAGE and a convolutional network processes it exactly as
it would an RGB image. That is the whole trick of the paper: *an offsets table
is an image*.

**The bow trick is worth stealing on its own (§3.2, p. 10, Figs. 8(e–j)).**
Sections in `P2, P3, P4` are ordinary transverse planes. Sections in `P1` (the
bow, first 10% of length) are cut by **a family of planes ROTATING about a
vertical axis** sited at the intersection of the centreplane and the transverse
plane at x/L = 0.1. The stated reason: "to avoid multiply (usually doubly)
connected CSs resulting from intersections of the bulbous bow area with
transverse planes". Construction: build the deck curve `D_P1` over P1, split it
into E/4 arc-length-equal points, find the intersection point `p_int` of the
lines from its first and last points, and generate E/4 planes through `p_int`
and each deck point.

**Surface reconstruction (§3.2 p. 10, §4.1, Fig. 9).** Grid points out of the
generator → fit a curve through the points of each cross-section → interpolate a
surface across those curves → smooth, fair NURBS-ish hull. The claim in
contribution 2 (§1, p. 4) is that the encoding "ensures a smooth NURBS-based
reconstruction of designs resulting from the trained generator".

**Encoding accuracy** is reported in Fig. 10 as (c) one-sided Hausdorff distance
and (d) Gaussian curvature, original KCS vs. reconstruction. The text gives no
scalar; the numbers are in the figure only. **NOT ADDRESSED in text: a numeric
reconstruction-error bound.**

### 1.2 CAN IT EXPRESS A CHINE OR KNUCKLE? — the single most important question

**Answer: the paper never claims it can, never tests it, and there is no chined
hull anywhere in the work.**

Measured on the extracted text: the strings **`chine`, `knuckle`, `crease`,
`planing`, `hard chine`** occur **ZERO times** in the entire 28-page paper,
references included. So does any discussion of tangent discontinuity, G0/C0
continuity, or feature curves.

That is a factual absence. On top of it, three specific mechanisms in the
representation work AGAINST a chine — these are marked INFERENCE, but they are
mechanical, not speculative:

- **INFERENCE (strong): arc-length-equal section points cannot pin a chine.**
  `N = 25` points spaced by equal arc length along each section places NO point
  at the knuckle in general. A crease that falls between two samples is
  reconstructed as a smooth curve through neighbours, i.e. rounded off. Fixing a
  chine would need the sampling to be FEATURE-ANCHORED (a point forced onto the
  knuckle in every section), which the paper does not do.
- **INFERENCE (strong): "fit a curve on the points for each CS" is a smooth
  fit.** §3.2/§4.1 describe fitting one curve per section and interpolating a
  surface across sections. Nothing in the paper introduces a knot multiplicity,
  a segment break, or a per-section feature parameter that would let the fitted
  curve hold a tangent discontinuity. The paper's own stated objectives for the
  representation are smoothness and fairness (§3.2 p. 9: designs must not "lack
  surface smoothness"); a chine is precisely the feature that objective
  penalises.
- **INFERENCE (moderate): the surface is interpolated ACROSS sections too**, so
  even a per-section knuckle would need to be longitudinally consistent
  (section-to-section) to survive into a chine LINE rather than a set of
  unrelated kinks.

**This is a crucial negative result for NavalAI and should be read as one.**
ShipHullGAN's "generic" is generic over DISPLACEMENT MERCHANT AND NAVAL
MONOHULLS — container ships, tankers, bulk carriers, a naval combatant, a
megayacht — every one of them round-bilge or wall-sided. Its generality runs
**orthogonal** to ours: it spans a family we barely touch (large, smooth,
bulbous-bowed displacement hulls) and does not touch the family that defines our
SKUs (small chined planing/semi-planing craft). Adopting it wholesale would not
close our measured gap of "only two of the five equivalent hull forms" — because
the two double-chine forms it would need to express are exactly the forms its
representation is least equipped for.

### 1.3 GENERALITY — the training set (§3.1, Figs. 4–6)

- **52,591 designs.** The paper states no equivalent public ship-hull dataset
  exists (§3.1, p. 6, and contribution 1, §1 p. 4). The dataset is NOT released
  in the paper text.
- Composition, as stated:
  - **FORMDATA systematic series [ref 43]** — "approximately 5000 different hull
    forms, but of only three basic ship hull types, referred to as U, N and V",
    varied by three form coefficients: midship section coefficient `CM`, fore
    block coefficient `CBF`, aft block coefficient `CBA`. Described as
    "conventional, mainly wall-sided hull forms" from a 1960s analysis of
    existing merchant ships.
  - **Synthetic variations of parent hulls** (Fig. 4, Fig. 5): KCS, KVLCC2,
    VLCC, JBC, DTC, DTMB (5415), Bulker, Global-S, Megayacht, Series-60, S-175.
    Generated by the parametric approach of ref [11], holding "length, beam and
    width ... constant" and varying non-dimensional shape parameters in [0,1].
  - Abstract: "container ships, tankers, bulk carriers, tugboats, and crew supply
    vessels".
- **Does it span chined AND round-bilge? NO — round-bilge/wall-sided only, on
  the evidence given.** Every named family is a displacement monohull. No
  hard-chine series (no Series 62, no Fridsma, no NTUA, no DSYHS), no catamaran,
  no planing craft. This is stated by enumeration, not by the authors.
- Fig. 6 shows the distribution of wave resistance `Cw` and volume `▽` across
  the training set, but the paper is explicit that these "do not play any direct
  role in the output of ShipHullGAN, as training is performed with only design
  geometries" (§3.1, p. 9). **The model is unconditioned on performance.**

### 1.4 The shape-signature tensor (SST) and geometric moments (§3.4)

This is the second genuinely portable idea, and unlike the network it is pure
mathematics we could use today.

- `SST = (P(G), M(G))` (Eq. 2): the geometric encoding of a design **plus a
  lumped geometric-moment vector**.
- Geometric moments (Eq. 3): `M_{p,q,r}(G) = ∭ x^p y^q z^r ρ dx dy dz`, with
  `ρ = 1` inside the hull, 0 outside. Order `s = p+q+r`; `n_M = (s+1)(s+2)/2`
  elements at order s. `M_{0,0,0} = V`; first-order moments give the centroid;
  second-order moments assemble the inertia tensor. Computed via **Gauss's
  divergence theorem**, converting volume integrals to surface integrals
  (§3.4.1, p. 13).
- **Geometric moment INVARIANTS (GMIs), §3.4.2.** Central moments (Eq. 5) are
  translation-invariant; scaling by λ gives `μ̂ = λ^{p+q+r+3} μ` (Eq. 6), so
  `MI_{p,q,r} = μ_{p,q,r} / (μ_{0,0,0})^{1+(p+q+r)/3}` (Eq. 7) is invariant to
  uniform scaling AND translation. By construction `MI_{0,0,0} = 1` and the
  first-order invariants vanish.
- **§3.4.3 is the physics argument, and it is a real derivation, not hand-waving.**
  The sectional area curve `S(x) = ∫_{Ω(x)} dy dz` is a function of 2D
  zeroth-order moments. Slender-body wave resistance (Vossers' integral; Tuck,
  Wehausen) depends on `S'(x)`, the longitudinal rate of change of sectional
  area, because it sets the Kelvin source strength. With `m_p = ∫_0^L x^p S'(x)
  dx` and `S(0) = S(L) = 0`, integration by parts gives (Eqs. 8–9):

      m_p = −p ∫_0^L x^{p−1} S(x) dx = −p · M_{p−1,0,0}

  i.e. **the p-th moment of S'(x) IS (−p times) the (p−1)-order longitudinal
  geometric moment of the hull.** So a moment vector carries the SAC information
  that classical hull-form design has always used.
- **The authors state the limit honestly (§3.4.3, p. 14):** "one cannot expect
  that every physical QoI of integral character is strongly connected with the
  GMs ... viscous-pressure resistance is expressed as an integral over the wetted
  surface ... nevertheless, it depends on local properties of the surface, such
  as smoothness and curvature, which can act as turbulence generators by
  triggering flow separation." Moments capture the wave-making side, not the
  viscous side. Worth quoting back at anyone who over-sells this.
- **Order used: s ≤ 4, `n_M = 35` components** (§3.4.4, p. 14), justified by refs
  [30,56] as "sufficient for capturing geometric features and the associated
  physics (Cw)". Higher orders "become more susceptible to noise".
- **How the moments enter the tensor (§3.4.4, Fig. 12):** the 35 GMIs are
  appended as the LAST ROW of each coordinate matrix, zero-padded across the
  remaining 22 of 57 columns, making each channel `[25 × 57]`. Table 1 lists all
  35 GMIs for DTC, Series-60 and S-175 — a usable reference set. Note many are
  exactly 0.00 by port/starboard symmetry (all odd-y invariants).

### 1.5 Diversity: the space-filling term (§3.5–§3.6)

- Problem stated: a GAN trained on a MULTI-CLASS dataset clusters, producing
  designs only in neighbourhoods of the training clusters (§3.5, p. 14).
- Fix: an **Audze–Eglais space-filling criterion** [ref 18] added to the loss —
  a repulsive-potential analogy over generated designs (Eq. 10):

      S = Σ_{i=1}^{m−1} Σ_{j=i+1}^{m}  1 / ‖x_j − x_i‖²₂

  minimised to spread designs uniformly.
- Augmented loss (Eq. 11): `min_G max_D  L_adv(D,G) + Γ_G · S`.
- **Scheduling matters and they say why (§3.6, p. 15):** `Γ_G` starts at 0 so the
  model first learns to make REALISTIC designs, then diversity "kicks in".
  Escalation (Eq. 12): `Γ_G = Γ'_G (t/T)^p`.

### 1.6 Architecture (§3.7)

- **Discriminator D**: input layer taking the three `[25 × 57]` matrices, then 6
  convolutional layers. Dropout p = 0.5 after the input layer. Leaky ReLU after
  each conv layer; batch normalisation before ReLU on layers 2, 4, 5. Sigmoid on
  the last layer. Downsampling by STRIDES, not pooling (cites [13] for accuracy
  and stability).
- **Generator G**: transpose of D — 5 transposed-convolutional layers plus input,
  projection and reshape layers (Fig. 13).

Training: Adam, 500 epochs, min batch 128, learning rate 2e-4, gradient decay
0.5, on a dual 24-core Xeon Gold 6226 / Quadro RTX 6000 / 128 GB machine.
**G has 9.7 M and D has 9.6 M learnable parameters** (§3.7.1, p. 16). Generator's
last layer is tanh, so output is normalised to [−1, 1].

### 1.7 LATENT SPACE — how 20 dimensions were chosen (§3.7.2, Figs. 14–15)

This is the most methodologically transferable part of the paper after the
encoding, because the procedure does not depend on the network.

1. **PCA gives an upper bound.** They run PCA on the training geometries and read
   off the number of eigenvalues for a target variance: "**30 latent features in
   z can capture 99% of geometric variance**" (Fig. 14). Because a GAN's
   nonlinear layers should need fewer variables than a linear method, **30 is
   taken as an UPPER BOUND on |z|**.
2. **Then reduce iteratively against three metrics**, each with a formula:
   - **MMD** (Eq. 13) — maximum mean discrepancy between the training and
     generated distributions, with a radial kernel `k(x,y) = exp(−‖x−y‖²/2θ²)`,
     **θ = 0.1** (Eq. 14). High MMD ⇒ generator fails to cover the training
     space ⇒ possible mode collapse.
   - **SC**, sparseness at the centre (Eq. 15) — mean distance of generated
     designs from their own centroid: `SC = (1/m) Σ ‖x_centroid − x_i‖₂`. A
     diversity measure.
   - **Novelty** (Eq. 16) — `(1/m) Σ_i min_{x_j ∈ X} ‖x_i^GAN − x_j‖₂`, the mean
     nearest-neighbour distance from a generated design to the TRAINING set.
3. **Measured trade-off (Fig. 15):** diversity and novelty rise with |z| up to
   about **20** and then plateau; MMD falls rapidly and is already low at **5**.
   **|z| = 20 is chosen as the balance**, and the trained generator is then used
   "as a parametric modeller with 20 parameters ranging between −1 and 1" (§4.1,
   p. 18).

**Interpretability: NOT ADDRESSED.** The paper shows per-variable variation
videos (§4.1, footnote links) but makes no claim that any latent coordinate
corresponds to a naval-architecture quantity. There is no disentanglement study,
no mapping from z to Cb/Cp/LCB.

**Coverage claim (§4.2, Fig. 20):** t-SNE of training vs. generated designs.
Generated designs "cover well the entire convex hull enclosing the designs in
the training dataset", and some lie OUTSIDE that convex hull, which the authors
(following [16]) read as novelty. They add the correct caveat that t-SNE cluster
distances/sizes/orientations "may not have any physical meaning".

Shape-signature method: yes — the SST (§1.4 above) IS the shape-signature
method, and the GMIs are what the paper credits for validity and for the
diversity advantage over a plain GAN.

### 1.8 GEOMETRIC VALIDITY — tested, not enforced (§4.2, §4.2.1)

Be precise about this, because it is the clause that matters for us:

- **Self-intersection is CHECKED AFTER GENERATION, not structurally prevented.**
  "We randomly sampled 30,000 designs over ten runs and searched for
  self-intersecting geometries ... **no self-intersections were found in any of
  the 300,000 tested designs**" (§4.2, p. 20). They attribute this to the
  convolutional architecture, the training, and the GMIs in the SST — i.e. to an
  EMPIRICAL property of a trained model, not to a guarantee.
- **Ablation (§4.2.1, Fig. 22):** the same architecture WITHOUT space-filling and
  GMIs produces **≈ 4.32 % invalid (self-intersecting) designs**, and "most
  invalid designs ... have self-intersecting surfaces near the bow", a LOCAL
  feature. Diversity/novelty differences vs. plain GAN are significant at
  p = 3.7354e−09 and 2.1315e−09.
- **Plausibility is a separate and worse story (§4.2, Fig. 19):** even with zero
  self-intersections, "some of the ShipHullGAN-generate designs may be
  implausible from a practical point of view ... visual inspection of large
  numbers of randomly sampled designs resulted in **less than 1 out of 70
  instances with questionable designs**." The proposed remedy is explicitly
  downstream: "such designs can be eliminated by setting appropriate design
  constraints and/or employing the physical solver to rule out such designs
  during design optimisation." **That is a filter, and the filter is VISUAL.**
- **WATERTIGHTNESS: NOT ADDRESSED.** The paper never discusses closure of the
  hull (deck, transom, centreplane), manifoldness, or export to a solver-ready
  closed surface. The reconstruction is a lofted NURBS surface patch over the
  cross-sections; whether it closes is not stated.
- **Physical constraints (displacement, stability): handled OUTSIDE the model,
  as optimisation constraints only** — see §1.9. Stability (GM, righting arm) is
  **NOT ADDRESSED anywhere in the paper**. Nor is structure, nor is any
  regulatory envelope, despite §2.1 listing "Constraints" as a known problem.

### 1.9 VALIDATION — what it is measured against (§4.3, Table 2)

**There is no experimental validation, and no CFD validation, in this paper.**

- **Solver**: "a software package based on linear potential flow theory using
  Dawson (double-model) linearisation" [ref 62]. Rankine sources. Domain 1 Lpp
  upstream, 3 Lpp downstream, 1.5 Lpp sideways. Free surface `[20 × 70]` panels,
  hull `[50 × 180]` panels. **Fr = 0.28.** (§4.3.1, p. 23.)
- **Quantity**: wave-resistance coefficient `Cw = 2R_w/(ρU²S)` ONLY. No viscous
  component, no total resistance, no sinkage/trim, no seakeeping.
- **Optimiser**: Jaya Algorithm [61], 500 iterations, 3 runs averaged (stochastic).
- **Results (Table 2, p. 24):**

  | | KCS | opt. (Fig. 23) | KVLCC | opt. (Fig. 24) | Crew supply | opt. (Fig. 25) |
  |---|---|---|---|---|---|---|
  | L_wl (m) | 232.5 | 229.6 | 325.5 | 320.7 | 34.7 | 34.7 |
  | B_wl (m) | 32.2 | 31.8 | 58 | 58 | 6 | 5.8 |
  | T (m) | 10.8 | 10.5 | 20.8 | 20.8 | 0.9 | 0.9 |
  | ∇ (m³) | 53811 | 51370 | 314446 | 301852 | 56.8 | 55.4 |
  | Cw | 2.48e−03 | **5.93e−04** | 6.81e−03 | **2.65e−03** | 2.66e−03 | **1.03e−03** |

  That is a claimed **−76 %, −61 % and −61 %** in Cw. **No number in that table
  was ever measured against an experiment or a RANS solve.**
- **To their credit, the authors state the caveats themselves (§4.3.1, p. 23,
  numbered list) and they are exactly the right ones:** (1) the optimised hulls
  are not variations of the parents so the comparison is not like-for-like;
  (2) only WAVE resistance is optimised and "the obtained optimised designs
  possess a larger wetted surface, increasing the frictional resistance
  component" — so total resistance may not improve at all; (3) potential-flow
  codes "may not provide reliable performance evaluation, primarily when the
  design under consideration is composed of unconventional features", and they
  plan CFD in future work (§5.1).

  **Read caveat (3) together with the headline claim and the paper self-refutes
  its own optimisation result:** the model's selling point is that it generates
  UNCONVENTIONAL designs, and the solver used to score them is stated to be
  unreliable exactly on unconventional designs. A gradient-free optimiser run for
  500 iterations against such a solver will find its blind spots. **This is a
  textbook out-of-distribution surrogate failure and the paper does not measure
  it.**
- **Encoding-fidelity validation** (Fig. 10) is the one place a geometric error is
  reported — one-sided Hausdorff distance and Gaussian curvature, original vs.
  reconstructed KCS. Figure-only; no scalar in the text. Surface fairness is
  argued by ISOPHOTE (zebra-stripe) inspection (§4.1, Fig. 16c), with a claim of
  "C2 continuity" — asserted, not measured.

### 1.10 Reconstruction pipeline, stated exactly (§4.1) — this is directly reusable

1. Sample `z ∈ [−1,1]^20`.
2. Generator emits three `[25 × 57]` matrices (x, y, z of grid points).
3. **Discard the last row** — it is the GMI row and is not geometry.
4. Fit a **cubic NURBS curve** through the 25 points of each cross-section
   (Fig. 16a).
5. **Skin/loft** a **bicubic NURBS surface** through the 56 cross-section curves
   (Fig. 16b).
6. Inspect fairness by isophote mapping (Fig. 16c).

Step 4–5 are the reason a chine cannot survive: a cubic NURBS interpolation
through 25 arc-length points, lofted bicubically, is a C2 construction by
default (and the paper claims C2 for the result). **INFERENCE:** a chine is a G0
feature; producing one from this pipeline would require either a repeated knot
at a feature parameter in every section curve, or splitting the loft into
separate surfaces above and below the chine. Neither exists in the paper.

**Data availability: "Data will be made available on request."** The 52,591-hull
dataset is NOT downloadable. Code availability is NOT ADDRESSED.

---

## Paper 2 — ShipGen (NOT a GAN — a diffusion model)

> Noah J. Bagazinski, Faez Ahmed (MIT, Dept. of Mechanical Engineering),
> "ShipGen: A Diffusion Model for Parametric Ship Hull Generation with Multiple
> Objectives and Constraints", *Journal of Marine Science and Engineering*
> **11** (2023) 2215. https://doi.org/10.3390/jmse11122215 — open access, CC BY.
> 32 pages. Received 2 Oct 2023, published 22 Nov 2023.
> Academic editors: Kaklis, Wan, Kostas and Khan — i.e. the ShipHullGAN authors
> edited this paper; the two works are adjacent and aware of each other.
> File: `jmse-11-02215.pdf`.

**Title/authorship confirmed from the PDF, and two corrections to the brief:**
this is **not** a GAN — it is a **denoising diffusion probabilistic model
(DDPM)** operating on a **tabular parametric design vector**, not on geometry.
A CTGAN appears only as a BENCHMARK that it beats. Second correction, and it is
the important one: **the 2.1× / 4.4× / 1.51× surface-area-and-curvature numbers
are from THIS paper, not from ShipHullGAN.** ShipHullGAN reports no such
figures anywhere (verified over its full text). Anything attributing them to
Khan et al. is misattributed and should be corrected before it is relied on.

### 2.1 ⚠️ THE MOST CONSEQUENTIAL RESULT IN THE SET — performance guidance made the boat worse

Priority item (5), confirmed with exact figures. §4.3.2, p. 21, and Table 4, p. 16.

Verbatim (§4.3.2, p. 21):

> "Among these samples, the wave drag coefficients and displaced volumes showed
> significant improvements in their performance. **These improvements were at the
> expense of a relative increase in the surface area and Gaussian curvature.**
> The generated samples had wave drag coefficients for any single speed/draft
> condition that was, on average, **91.4% lower** than the average wave drag
> coefficients of the Ship-D dataset hulls. For the displaced volumes, these
> generated hulls had an average **114× increase** in displaced volume in the
> bottom 50% of the hull depth and an average **47.9× increase** in the total
> displaced volume of the hull. The generated hulls had, on average, **2.1× more
> total surface area, 4.4× more surface area in the bottom 50% of the hull, and
> 1.51× more double curvature** compared to the Ship-D hulls. **This is not
> desirable.**"

Table 4 (p. 16) gives the underlying numbers. Note the mean/std columns are on a
normalised, LOGARITHMIC scale (Eqs. 5–11); the right-hand column is the ratio in
TRUE units:

| Performance objective | Ship-D mean | Ship-D std | Generated mean | Generated std | Scale factor Y_gen/Y_DS |
|---|---|---|---|---|---|
| Wave drag C_w | −73.40 | 17.38 | −107.45 | 23.90 | **0.086** |
| Surface Area 50% | −1.71 | 0.53 | −1.07 | 0.19 | **4.365** |
| Surface Area 100% | −1.09 | 0.45 | −0.76 | 0.19 | **2.138** |
| Volume 50% | 4.78 | 0.81 | 2.72 | 0.59 | 114.815 |
| Volume 100% | 3.80 | 0.62 | 2.12 | 0.43 | 47.863 |
| Volume MaxBox | −0.407 | 0.010 | −0.384 | 0.072 | 0.948 |
| Gaussian curvature | 2.43 | 0.529 | 2.61 | 0.24 | **1.514** |

So the precise figures are **2.138× total surface area, 4.365× lower-half
surface area, 1.514× average Gaussian curvature**, against **0.086× wave drag**
(= −91.4%) and **47.863×** total displaced volume. MaxBox ratio fell 5.2%
(0.948).

**Read what this actually says, because it is a warning aimed straight at us.**
Seven objectives were guided SIMULTANEOUSLY with randomly-drawn weights per
sample (§4.3.2, p. 20: "Each objective in these samples was randomly weighted"),
and surface area and curvature were AMONG the seven guided objectives — they
were being minimised — **and they still went up by 2.1× and 1.5×.** The wave-drag
and volume gradients simply dominated. The mechanism is visible in the geometry:
§4.3.2 p. 21 notes "**A major difference in these generated hulls was their
higher length-to-beam ratios**". A long thin hull is exactly what minimises
Michell wave drag while maximising wetted area — the optimiser found the
slenderness corner of the design space and rode it.

Three consequences for NavalAI, stated plainly:

1. **A wave-drag objective without a wetted-area/friction counterweight is not an
   objective, it is a bug.** Michell wave drag is scaled here by `LOA²`
   (Eq. 3) — deliberately NOT by wetted surface (§3.1.2, p. 7: "the wetted
   surface area of the hulls can vary greatly. Instead, the length overall (LOA)
   is used"). Normalising drag by a length instead of by wetted area REMOVES the
   penalty that would otherwise restrain area growth. If any NavalAI objective
   normalises resistance by anything other than wetted area, this failure mode is
   available to it.
2. **Curvature is a MANUFACTURING cost and it is not currently in our objective
   vector.** ShipGen measures it precisely for that reason (§2.4 below).
3. **The authors say "This is not desirable" and publish it anyway.** By this
   project's standard (a failing gate is information) that is the right conduct
   and the result is more useful than the headline.

Repeated in §5 (p. 26, line ~1031): "surface area, Gaussian curvature, and
MaxBox of the generated samples did not improve".

### 2.2 The 1-in-150 and the four-orders-of-magnitude claims — BOTH CONFIRMED

Priority item (2). §3.1.1, p. 6, verbatim:

> "On an Intel Core i9-10980XE Processor ... the construction and checking of a
> hull mesh with approximately **80,000 vertices was 1.77 s**. Comparatively, the
> **algebraic constraints checked the design feasibility of a parametric hull in
> 0.000199 s**. This is a **ten-thousand-fold increase in speed** when checking
> design feasibility with the algebraic constraints. **A uniform random sampling
> of the design parameters leads to the generation of a feasible hull in
> approximately 1 per 150 tries.**"

- **1-in-150: CONFIRMED**, stated exactly.
- **Four orders of magnitude: CONFIRMED as claimed**, with one arithmetic note —
  1.77 / 0.000199 = **8894×**, which the paper rounds up to "ten-thousand-fold".
  Call it ~8.9×10³, i.e. between 3.9 and 4 orders of magnitude. Mesh
  construction and checking is stated as `O(N log N)` in the number of vertices.
- The abstract's **"149× improvement over random sampling"** is the same fact
  from the other end: guided diffusion at 99.5% feasible against random sampling
  at 1/150 = 0.667%, and 99.5/0.667 = 149.

**Why this matters to us more than it looks.** The 1-in-150 figure is a
measurement of a property NavalAI's grammar also has: **a box-bounded parametric
space is overwhelmingly infeasible under uniform sampling, and feasibility is a
JOINT condition on parameters, not a per-parameter range.** ShipGen's response is
not to shrink the box — it is to derive **49 closed-form algebraic constraints**
that decide watertightness and self-intersection WITHOUT building a mesh. That is
a design pattern we can adopt directly (see (a) in §5).

### 2.3 THE PARAMETERISATION — and it HAS A CHINE (§3.1, Appendix B Fig. A5)

**This is the answer to the chine question, and it is a positive one.**

Ship-D hulls are defined by **45 parameters** fed to "a set of algebraic
equations to define and characterize the surface of the hull" (§3.1, p. 5). This
is an ANALYTIC KERNEL of exactly the kind NavalAI already has — not a neural
representation. Parameter groups (§3.1, p. 5):

- Principal dimensions (LOA, beam at main deck, depth…)
- **"Cross-section of the parallel midbody (e.g., deadrise angle, chine radius)"**
- Geometry of bow and stern taper
- Geometry of bulbs at bow and stern

Full list transcribed from Fig. A5 (p. 29). The **midship cross-section group** is
the part we should read closely:

| Variable | Meaning | Units / scaling | Range in dataset |
|---|---|---|---|
| `Bc` | **Beam at chine** | fraction of LOA | 0.05 < Bc < 0.5 |
| `Beta` | **Deadrise angle** | degrees | 0.0 < Beta < 45.0 |
| `Rc` | **Radius of chine** | fraction of Bc (strictly positive) | 0.0 < Rc < 1.0 |
| `Rk` | **Radius of keel** | fraction of Dd (may be ±) | −1.0 < Rk < 1.0 |

and the **transom** repeats the same four:

| `Beta_trans` | deadrise angle for transom | degrees | 0 < Beta_trans < 60 |
| `Bc_trans` | beam at transom chine | fraction of LOA | 0 < Bc_trans < 0.5 |
| `Rc_trans` | transom chine radius | fraction of Bc_trans | 0 < Rc_trans < 0.5 |
| `Rk_trans` | transom keel radius | fraction of Dd·(1−SK) | −1.0 < Rk_trans < 1.0 |

Other principal terms: `LOA` (fixed at 10 m in the dataset), `Lb` bow-taper
length, `Ls` stern-taper length, `Bd` beam at midship deck, `Dd` depth of hull,
`Bs` beam at stern deck, `WL` design draft. Bow shape is a parabola
`BOW(z) = Az² + Bz + C`; the longitudinal station at which midship beam is
reached is another parabola `DELTA_BOW(z)`; **drift angle** is a third parabola
`DRIFT(z) = Az² + Bz + C` in degrees as a function of height. Stern mirrors this
with `DELTA_STERN(z)`, `TRANS(A)` transom slope, `SK` stern-keel intersect,
`Kappa_STERN`, plus **two BOOLEAN bits** `bit_EP_S` / `bit_EP_T` selecting
ellipse-vs-parabola for the lower and upper stern taper. Bulbs are switched by
`bit_BB` / `bit_SB` and shaped by `Lbb, Hbb, Bbb, Lbbm, Rbb` (bow) and
`Kappa_SB, Lsb, HsbOA, Hsb, Bsb, Lsbm, Rsb` (stern).

**THE KEY IDEA, and it is directly adoptable into our kernel: the chine is a
FILLET WITH A RADIUS, and the radius is a continuous parameter.** The midship
section is built as keel-fillet (`Rk`) → straight deadrise run at angle `Beta` →
**chine fillet of radius `Rc` at beam `Bc`** → topside to the gunwale. `Rc` is
expressed as a FRACTION of `Bc` over (0, 1). Therefore:

- `Rc → 0` is a **hard chine** (a knuckle);
- `Rc → 1` is a **fully rounded bilge**;
- everything in between is a **radiused/soft chine**.

**This unifies hard chine and round bilge as one continuous construction rather
than two representations.**

⚠️ **A FIRST-DRAFT INFERENCE HERE WAS WRONG AND IS CORRECTED, because the
codebase refutes it.** I initially wrote that a filleted chine is developable
because a circular-arc fillet is cylindrical. It is not, in general: the fillet
is swept along a chine line that is CURVED in plan and along a bottom that is
WARPED in deadrise, so the filleted strip is doubly curved. `navalai/hull_ast.py`
states this explicitly and treats it as settled — "a radiused bilge is a fillet,
the filleted strip is doubly curved, and a doubly curved strip is not developable
from flat sheet; this typology is sheet-built, so the bilge is a chine or it is a
different typology" — and `unroll.hull_panels` refuses any `roundness > 0` on
exactly that ground. **A measurement beats a document; the code is the
measurement here.** ShipGen's `Rc` does not make a bilge cuttable from sheet.

**And NavalAI ALREADY HAS this parameter.** `grammar.PARAMS` carries `roundness`,
`geometry` draws the fillet, and `hull_ast.Pin` pins it to exactly 0.0 for the
two sheet-built typologies. So `Rc` is NOT a new idea for us — the genuinely new
things in ShipGen's midship group are narrower and worth naming precisely:
(i) the chine is parameterised by BEAM AND HEIGHT AT THE CHINE (`Bc`, with `Dc`
DERIVED from `Rk`, `Beta`, `Bc`) rather than by a bilge shape, and (ii) the SAME
four parameters are repeated at the transom (`Bc_trans`, `Beta_trans`,
`Rc_trans`, `Rk_trans`) so the chine's beam, height, hardness and deadrise all
vary longitudinally between two controlled stations.

**Be honest about the limit, though: ShipGen has ONE chine too.** There is a
midship chine and a transom chine and the section is interpolated between them,
but there is no second chine line above the first. **So ShipGen ALSO cannot draw
the two DOUBLE-CHINE forms** of the five equivalent hull forms. What it can do
that we cannot is (i) place the chine's hardness on a continuum, and (ii) let the
chine's beam, height and deadrise VARY LONGITUDINALLY between midship and transom
— a warped/twisted planing bottom. Those are two real capabilities, and neither
requires a neural network.

**Also note what it lacks:** `Beta` and `Beta_trans` are the ONLY deadrise
controls, so deadrise varies linearly-ish between two stations; there is no
spray rail, no step, no tunnel, no multihull. And the dataset fixes `LOA = 10 m`
— every hull is non-dimensional and rescaled.

### 2.4 The 49 algebraic feasibility constraints (§3.1.1, Appendix B Fig. A6)

Priority item (1), and the second directly adoptable idea.

**"Feasible" is defined with exactly two criteria** (§3.1.1, p. 6, repeated
verbatim in Appendix B p. 28):

1. **The hull is watertight, meaning that there are no holes on its surface;**
2. **The hull surface is not self-intersecting.**

That is the WHOLE definition. It is purely geometric — **no displacement, no
stability, no strength, no regulatory, no performance content whatsoever.** Any
sentence that reads ShipGen's "99.5% feasible" as "99.5% of hulls are good boats"
is wrong: it means 99.5% of them are closed, non-self-intersecting surfaces.
Recall §3.1, p. 5: "As these designs are randomly sampled across the entire
feasible design space, they do not necessarily look like realistic hull designs
... Many of these hulls are relatively low performing; having high drag, low
displacement volumes, and high surface area."

The 49 constraints are the algebraic conditions under which those two criteria
hold. Their FLAVOUR is worth recording because it is the pattern to copy — they
are mostly **ordering and intersection conditions between construction features**:

- #0 `Lb + Ls < 1` — bow and stern tapers fit inside LOA.
- #2 the gunwale/chine-fillet intersection lies above the chine height `Dc`.
- #5 "`Dc` is defined algebraically with `Rk`, `Beta` and `Bc`" — i.e. chine
  HEIGHT is derived, not free, and must come out positive.
- #6 "The intersection of the chine fillet and the hull bottom is inboard of
  `Bc`. **This avoids jump discontinuities in the mesh.**"
- #7 the keel-radius/bottom intersection is inboard of the chine-radius/bottom
  intersection — i.e. **the two fillets must not overrun each other**.
- #8 `|Rk| > 1e-8` — avoid divide-by-zero.
- #10–15 the drift-angle parabola stays within [0°, 90°) at z = 0, z = Dd AND at
  its VERTEX if the vertex lies in range — a clean example of checking a
  polynomial's extremum inside the domain rather than only its endpoints.
- #16–23 bow-rake/keel-rise intersection is in range and every taper length is
  positive, again including at parabola vertices.
- #29–35 the identical family for the transom chine.
- #36–48 bulb radii smaller than `Rk`, bulb beam inside the local section, bulbs
  longitudinally clear of the taper start.

Transcription note: constraints #3, #4, #5, #31, #32, #33 render in the PDF text
as e.g. "`Rc > 1` – 'Chine radius is strictly positive'". The prose and the range
table both say strictly POSITIVE with `0 < Rc < 1`, so the "1" is a
PDF-extraction artefact of a superscript/footnote marker and should be read as
`Rc > 0`. Flagged rather than silently corrected.

**The structural lesson: every one of these 49 is a closed-form inequality on the
parameters, evaluated in 199 µs, and together they are SUFFICIENT for a
watertight non-self-intersecting hull.** Feasibility is decided BEFORE any
geometry is built. That is a strictly stronger position than generate-then-check.

### 2.5 Performance-prediction networks and OOD (§3, §4.3.1, Table 3)

Priority item (4).

Seven **residual neural networks**, one per objective, mapping the parametric
design vector → performance. Training fit (Table 3, p. 15):

| Objective | Training fit R² |
|---|---|
| Wave drag C_w | **0.973** |
| Surface Area 50% | 0.983 |
| Surface Area 100% | 0.982 |
| Volume 50% | 0.988 |
| Volume 100% | 0.986 |
| Volume MaxBox | **0.784** |
| Gaussian curvature | **0.765** |

- **R² = 0.973 for wave drag: CONFIRMED**, and Fig. 12 plots prediction vs.
  simulation for aggregate wave drag.
- The two WEAK ones are exactly the two that later misbehaved: **MaxBox 0.784 and
  Gaussian curvature 0.765.** The paper's own comment (§4.3.1, p. 19): they "had
  lower R² values, however, they are still sufficient for use with
  performance-guided DDPM sampling [44]." **That judgement is asserted with a
  citation, not measured** — and Table 4 then shows curvature going the wrong way
  by 1.51×. INFERENCE: a guidance gradient taken from an R² = 0.765 surrogate is
  a weak, biased gradient, and the objectives with strong surrogates won.
- **THE HEADLINE CAVEAT: these are TRAINING fits.** The table is headed "Training
  Fit: [R²]". **No held-out test set, no validation split, no cross-validation, no
  error bars, and no confidence interval is reported for any of the seven.**
- **OUT-OF-DISTRIBUTION BEHAVIOUR: NOT ADDRESSED as such.** The words
  out-of-distribution / extrapolation do not appear. But the paper measures its
  shadow twice without naming it:
  - §4.3.2, p. 21: the performance-guided samples "did not cover the same sample
    range of the design space as the Ship-D dataset hulls", and Fig. 14's caption
    says coverage "was skewed relative to the distribution of the Ship-D dataset
    as a result of the performance guidance."
  - Guidance pushed samples to high length-to-beam ratios, i.e. toward a corner of
    the space.

  **So the generated designs are, by the paper's own PCA, distributionally
  displaced from the training data — and their performance was then predicted by
  surrogates fitted on that training data, with no test-set error and no refusal
  mechanism.** They DID re-simulate the 839 feasible samples with "the same
  simulations used to create the original dataset" (§3, p. 15) — which is the
  right move and is why the 2.1×/1.51× regression was caught at all — but the
  GUIDANCE itself ran on unvalidated extrapolation.

### 2.6 The generative machinery and its measured feasibility (§3, §4.1–4.2)

Priority items (1) and (3).

- **Dataset: 30,000 feasible parameterised hulls — CONFIRMED** (§3.1, p. 5), plus
  **"an additional 20,000 design vectors (called invalid samples) that violate at
  least one feasibility constraint"** — CONFIRMED (§3.1.1, p. 6). The invalid
  samples exist to train the feasibility CLASSIFIER. Ship-D also carries **ten
  geometric measures at ten draft marks** (waterline length, waterplane area,
  wetted surface, LCF, waterplane I_L and I_T, displaced volume, LCB, VCB —
  by trapezoidal integration) and **32 wave-drag coefficients per hull**.
  Documented at https://decode.mit.edu/projects/ShipGen/.
- **Froude range: CONFIRMED — eight speeds, Fn = 0.10 to 0.45 in steps of 0.05**,
  crossed with **four drafts (25%, 33%, 50%, 67% of depth)** = 32 conditions
  (§3.1.2, p. 7). Stated as "typical operating conditions of traditional
  displacement hulls". **Fn 0.45 is the ceiling — this dataset does not reach
  planing speeds**, which matters for us.
- **Wave drag solver: the MICHELL INTEGRAL** (Eq. 2), chosen "for its relative
  computational efficiency and the accuracy it provides"; thin-ship linear
  theory. `C_w = R_w / (½ρU²·LOA²)` (Eq. 3), normalised by LOA² not wetted area
  (see §2.1 above — this is load-bearing).
- **Feasibility results (Tables 1–2):**

  | Generation method | Feasible | Coverage ratio |
  |---|---|---|
  | Uniform random sampling of parameters | **~0.67% (1 in 150)** | — |
  | CTGAN (GAN benchmark, trained on the 30k) | **0.7%** | 0.94 |
  | Interpolation, midway between two random dataset hulls | 93.1% | 0.965 |
  | Interpolation, hull to nearest neighbour | 93.8% | 1.059 |
  | Standard tabular DDPM (no guidance) | 51.1% | 0.984 |
  | **Classifier-guided DDPM, γ = 0.5** | **99.5%** | **> 0.9** |
  | Performance-guided DDPM (7 objectives), γ = 0.5 | 83.9% | skewed (Fig. 14) |

  **The CTGAN result deserves its own sentence: a GAN trained on 30,000 feasible
  hulls produced feasible hulls 0.7% of the time — "only marginally better than
  randomly sampling the design space"** (§4.1, p. 17). A generative model that
  learns feasibility IMPLICITLY, from examples, learned essentially nothing about
  it. Explicit algebraic constraints beat a trained GAN by a factor of ~142 on
  the exact task the GAN was trained for.
- **The 99.5% configuration, priority item (3):** classifier-guided DDPM with
  **classifier guidance weight γ = 0.5**. The classifier is a pretrained network
  that labels a design vector as satisfying all 49 constraints or violating at
  least one; its gradient `γ∇_{X_t} f_φ(y|X_t)` is injected at every denoising
  timestep (Eq. 15). **Measured by generating samples and CHECKING THEM AGAINST
  THE 49 ALGEBRAIC CONSTRAINTS** — i.e. against ground truth, not against the
  classifier. γ was tuned on a trade-off (Figs. 8, 9): feasibility exceeds 90%
  for γ > 0.3 and keeps rising, but **coverage falls as γ rises** — "To maintain
  a dataset coverage similar to the interpolation studies, γ should be ≤ 0.35."
  γ = 0.5 is the compromise, with "a dataset coverage ratio greater than 0.9".
  Realism and coverage are measured as **mean normalised Chamfer distance**
  between generated and dataset hulls, and their sum is maximised near γ ≈ 0.5.
- **Full guided sampling step (Eq. 15)** combines the standard DDPM update with
  BOTH the classifier gradient and the sum of seven weighted performance
  gradients `− Σ_{i=1}^{7} λ_i ∇_{X_t} P_i(X_t)`, subtracted to minimise.

### 2.7 Gaussian curvature as a manufacturing metric, and MaxBox (§3.1.2)

Priority item (6). Both are NEW metrics introduced by this paper and added to
Ship-D, and both are ideas NavalAI can use with no network at all.

**Gaussian curvature as manufacturing complexity** — the reasoning is explicitly
about SHEET MATERIAL, which is our unroller's problem exactly (§3.1.2, p. 7):

> "The average Gaussian curvature is calculated for these hulls to **assess the
> manufacturing complexity of the hull's surface**. As most large ships are
> constructed from **welded sheet steel or aluminum, bending a sheet along two
> principal axes of curvature is a difficult task** owing to both the sheet
> forming process and for welding the edge of a complex surface to another. By
> measuring the average double curvature of each hull, an understanding of the
> difficulty of manufacturing the hull surface is gained."

Computed by **finite differences of the principal curvature in the YZ plane and
the XY plane on a uniform grid of surface points**, then area-averaged (Eq. 4):

    GC = ∮_S [ dA / (R_XY(x,y,z) · R_YZ(x,y,z)) ] / (Total Surface Area)

Units 1/L², normalised by LOA².

**INFERENCE, and it is a tight one:** a developable surface has zero Gaussian
curvature everywhere, so this quantity is a **continuous, differentiable measure
of exactly what makes a panel un-unrollable.** NavalAI's unroller currently gives
a binary verdict (it refuses the rounded bilge). An area-averaged |K| would turn
that refusal into a graded cost that an optimiser can trade against, and it needs
no machine learning — it is finite differences on a surface we already build.

**MaxBox** (§3.1.2, p. 7): "the box with maximum volume that is completely
inscribed by the hull and that can be **vertically lowered into the hull through
the waterplane at the hull's top deck**." Rationale: a measure of usable
cargo-hold volume, and because the box is open at the deck "a crane can service
this entire volume". Computed per hull by **Nelder–Mead simplex** maximising box
volume subject to the hull surface and the deck waterplane. Stored as forward
(x) position, length, width, depth and volume, normalised by 1/LOA and 1/LOA³.
Used as objective 6 (`MaxBox* = −Volume_MaxBox`, Eq. 10) and noted as "not on a
logarithmic scale like the other measures".

**INFERENCE:** MaxBox is a crude but genuinely useful proxy for what
`navalai/arrangement.py` cares about — how much of the enclosed volume is
actually usable for a rectangular thing you must install. It is a
geometry-only computation, no learning involved.

### 2.8 The seven guided objectives (§3.1.2, Eqs. 5–11)

1. Aggregated sum of wave drag coefficients
2. Surface area of the hull up to 50% of total depth
3. Total surface area of the hull
4. (Volume 50%)
5. (Volume 100%)
6. Volume of the MaxBox
7. Gaussian curvature

Most are transformed to a logarithmic scale for training because "these
performance metrics span several orders of magnitude across the Ship-D dataset"
(§3.1.2, p. 8).

### 2.9 Validation of ShipGen against real hydrodynamics

**NONE.** As with ShipHullGAN, the only hydrodynamic quantity is a linear
potential-flow wave drag (here the Michell integral) and it is never compared to
towing-tank data, RANS, or any experiment in this paper. The re-simulation in
§4.3.2 checks generated hulls with **the same Michell code** that produced the
training labels, so it validates the SURROGATE against the SOLVER, not the solver
against reality. No uncertainty, no grid/discretisation study, no sigma on any
reported quantity.

---

## Paper 3 — Yonekura et al., performance-conditioned cWGAN-GP

> Kazuo Yonekura, Kotaro Omori, Xinran Qi, Katsuyuki Suzuki (Department of
> Systems Innovation, University of Tokyo), "Designing Ship Hull Forms Using
> Generative Adversarial Networks", *AI* **6**(6) (2025) 129.
> https://doi.org/10.3390/ai6060129 — open access, CC BY. 17 pages.
> Received 3 Apr 2025, published 18 Jun 2025.
> File: `ai-06-00129.pdf`.

### 3.1 The verdict asked for: performance-conditioning, NOT hull-form discovery

**The coordinator's suspicion is correct, and the paper is candid about it.**

The training set is **generated in its entirety from the generalized Wigley hull
form** — a closed-form analytic surface (§3.2, Eq. 2a–2i, p. 4–5):

    η = f(ξ,ζ) = [1 − ζ^Z1][1 − ξ^X1] + ζ^Z1 [1 − ζ^Z2][1 − ξ^X2]^X3

with `Cp = Cb/Cm`, `X1 = Cw/(1−Cw)`, `X2 = max(2, Cp/(1−Cp))`, `X3 = 1/Cp²`,
and `Z1`, `Z2`, `S` given by Eqs. (2g)–(2i). `η = f(ξ,ζ)` is "the y-coordinates
of `(x,z) = (ξ,ζ)`". The free parameters are just **six**: principal dimensions
`L, B, d` and coefficients of fineness `Cb, Cm, Cw`.

**Therefore: this paper is evidence that a conditional GAN can INVERT an analytic
hull family from performance targets. It is NOT evidence that a GAN discovers
hull forms.** Every training sample, and hence everything in the support of the
learned distribution, is a generalized Wigley hull. The network's achievement is
learning the inverse map (C_d, W, U) → (the six Wigley coefficients, expressed as
offsets), a map that could also be obtained by root-finding on the analytic
formula. The authors frame it exactly this way in the abstract — "demonstrate the
**feasibility** of generating hull geometries directly from performance
specifications" — and §1 explains the motivation is that "conventional hull-form
generation methods typically rely on geometric parameters such as the block
coefficient or midship section coefficient, **which may not directly correspond
to initial performance objectives**."

That motivation is legitimate and it is the transferable idea (see (b) in §5).
The generality claim is not.

### 3.2 Shape representation, and the chine question

**An OFFSETS TABLE again — and this one provably cannot hold a chine.**

- The hull is `d = { y_{i,j} = f(x_i, z_j) | i ∈ 1..20, j ∈ 1..40 }` — **20
  longitudinal stations × 40 vertical levels**, flattened. The generator outputs
  **R^1600** (§3.3, p. 6: "outputs the coordinates (y, z) ∈ R^1600"), i.e. the
  y and z arrays together.
- The 20 `x_i` stations are **FIXED for all data** and non-uniformly clustered
  toward the bow: {0.0, 0.2, 0.4, 0.45, 0.5, ..., 0.9, 0.925, 0.9375, 0.95,
  0.9625, 0.975, 0.9875, 1.0}. Same instinct as ShipHullGAN's `[0, 0.1, 0.3,
  0.8, 1]` partition — put stations where the shape changes.

**CHINE: NO, and here it is provable rather than inferred.** `η = f(ξ,ζ)` is a
**single-valued, C^∞ analytic function of (x, z)** built from products of powers.
Two consequences, both hard:

1. A section `y(z)` at fixed x is smooth and everywhere differentiable — a
   knuckle (tangent discontinuity in `dy/dz`) is **not in the image of Eq. (2)**
   for any parameter values.
2. Because y is a single-valued FUNCTION of (x,z), the representation cannot
   express any section with tumblehome-plus-flare reversal, a re-entrant form,
   or a multi-valued girth.

And the training distribution contains nothing else, so the generator's support
contains nothing else. The word "chine" does not appear in the paper in its naval
sense — all six textual occurrences are inside "machine" (verified). "Knuckle",
"deadrise", "planing" and "hard chine" do not appear at all.

### 3.3 The performance model — and it is NOT a learned surrogate

An important distinction, and a point in this paper's favour:
**there is no learned performance-prediction network here.** Performance is
computed by CLOSED-FORM NAVAL ARCHITECTURE, both to build the labels and to
score the output (§3.1, p. 3–4):

    C_d = (1 + K)·C_df + C_dw                                       (1)

- **Form factor** from ref [32]:
  `K = 0.11 + 0.128(B/d) − 0.0157(B/d)² − 3.1(C_b B/L) + 28.8(C_b B/L)²`.
- **Friction**: `C_df = 1.328 · Rn^(−1/2)`.
  ⚠️ **TECHNICAL FLAG (mine, INFERENCE):** that is the **Blasius LAMINAR
  flat-plate line**, not the ITTC-1957 correlation line
  `0.075/(log₁₀Rn − 2)²` that NavalAI uses. At a full-scale ship Reynolds number
  (~10⁹) Blasius gives roughly 4×10⁻⁵ against ITTC-57's ~1.5×10⁻³ — **more than
  an order of magnitude low**, which would make the frictional term nearly
  vanish and leave `C_d` dominated by wave drag. The paper neither justifies nor
  remarks on this. It does not invalidate the GAN result (the same formula makes
  the labels and scores the outputs, so the inverse map is self-consistent) but
  **no C_d value in this paper should be read as a ship's actual drag
  coefficient.**
- **Wave drag** is Michell's integral:
  `C_dw = (8/(π Fn⁴)) ∫₀^{π/2} [P(θ)² + Q(θ)²] sec³θ dθ`, with `P`, `Q` the usual
  amplitude functions integrating `∂f/∂x` over the centreplane.

**Out-of-distribution behaviour: BARELY ADDRESSED, but honestly flagged in one
sentence.** The strings "out-of-distribution" and "extrapolat*" do not occur.
The conclusions (§5, p. 15) say:

> "While the generated shapes are based on the generalized Wigley hull form and
> appear smooth and reasonable, we acknowledge that **we have not yet
> incorporated explicit constraints related to manufacturability, stability, or
> classification rules.** ... **The trained model may not have a rich
> generalization ability under extreme parameter conditions.**"

That is an acknowledgement, not a measurement, and there is **no refusal
mechanism**: the generator will emit a hull for any (C_d, W, U) you ask for.
The saving grace is architectural and worth copying: **§3.3 (p. 6) states "The
GAN model did not consider physics. The output data were not guaranteed to meet
the requirements. Hence, labels (C_d, W, U) were recalculated using the output
data and compared with the required labels."** The generative model PROPOSES; the
analytic physics VERIFIES. That is precisely NavalAI's stance.

### 3.4 Accuracy — and the headline number needs a caveat

MAPE `= (1/n) Σ |ĉ_i − c_i| / c_i`, where `ĉ` is recomputed from the generated
geometry and `c` is the requested label.

**Table 3 (p. 15) — SEPARATE models, one per speed class.** This is where the
abstract's "less than 0.08" comes from:

| Design speed | MAPE of C_d | MAPE of W | Total |
|---|---|---|---|
| High speed | 0.04347 | 0.07327 | 0.05837 |
| Medium speed | 0.07061 | 0.06144 | 0.06603 |
| Low speed | 0.08452 | 0.03362 | 0.05907 |

Note the low-speed `C_d` MAPE is **0.08452 — above 0.08**; the paper's own text
says "less than 0.09" (§4.3, p. 11) while the abstract says "less than 0.08 in
mean average percentage error". The abstract is describing the TOTAL column.

**Table 2 (p. 8) — the single INTEGRATED model trained on all data, and this is
the result that matters:**

| Design speed | MAPE of C_d | MAPE of W | Total |
|---|---|---|---|
| High speed | 0.03171 | 0.05069 | 0.04120 |
| Medium speed | **0.38770** | 0.05002 | 0.21886 |
| Low speed | **1.74973** | 0.08326 | 0.91650 |

**One model covering three speed classes produced a 175% mean error in drag
coefficient for low-speed ships.** The authors' diagnosis (§4.2, p. 8): "the
model was trained using all data that contained different data styles ... The
data include potential data imbalances among different ship types and the
challenge of capturing **multi-modal distributions within a single model**."

**This is the most useful result in the paper for NavalAI, and it cuts against
the generic-modeller thesis.** A conditional GAN over a MULTI-MODAL design space
degraded catastrophically on the least-represented mode, and the fix was to give
up on genericity and **train three separate models**. Our SKU range is
multi-modal in exactly this sense. Note also which quantity broke: `W`
(displacement, a direct geometric integral) stayed accurate at 0.05–0.08 in ALL
configurations, while `C_d` (a complicated functional of the shape) blew up —
the paper says so itself (§4.3, p. 11): "the MAPE of W is lower than that of C_d
... because W is directly related to the geometry, whereas the relationship
between C_d and ship hull geometry is complicated."

### 3.5 Model and training details

- **cWGAN-GP.** Wasserstein loss with gradient penalty
  `L = E_{x̃~Pg}[D(x̃)] − E_{x~Pr}[D(x)] + λ L_gp`, with
  `L_gp = E_{x̂}[(‖∇_x̂ D(x̂)‖₂ − 1)²]` enforcing 1-Lipschitz. Motivated by GAN
  training instability: "mode collapse [27] and gradient dissipation [29]"
  (§2, p. 3). Method borrowed from an **airfoil** generation task [12].
- **Generator**: fully-connected only (no convolutions) — latent vector of size
  **5** plus the 3-element label → 8, then (8,64) → (64,128) → (128,256) →
  (256,512) → (512,1024) → (1024,1600), Leaky ReLU throughout, dropout after the
  3rd and 5th layers (Fig. 2b).
- **Discriminator**: (1600,512) → (512,256) → (256,1), Leaky ReLU (Fig. 2c).
- **Training set: 4066 hulls total** (Table 1, p. 5) — 1552 high-speed,
  1594 medium, 920 low. Parameter grids per class, e.g. high speed
  B/L = {0.125}, d/L = {0.045}, C_m ∈ 0.85..0.97, C_w ∈ 0.50..0.60,
  C_b ∈ 0.68..0.78, at 25 kn; low speed at 15 kn with B/L 0.155–0.200,
  C_b 0.86–0.92. **Note B/L and d/L are nearly frozen within a class** — the
  variety is almost entirely in the three fineness coefficients.
- Adam, learning rate 1e−5, on an Intel Core i9 / 64 GB / RTX 4090, PyTorch.
- **NO TEST SET, NO HOLD-OUT, NO CROSS-VALIDATION** is reported anywhere. The
  MAPE is computed on generated samples scored against their own requested
  labels, which is a self-consistency check rather than generalisation error.
- **A "geometric penalty function" is referenced three times in §4.1 (p. 7) —
  models are trained "with" and "without" it — but IT IS NEVER DEFINED,
  FORMULATED, OR ABLATED anywhere in the paper.** NOT ADDRESSED; flagged because
  it is the one component that might have encoded geometric validity.
- **Geometric validity (watertight, non-self-intersecting): NOT ADDRESSED.** It
  is arguably moot — an offsets table on a fixed station grid, from a
  near-Wigley distribution, is structurally hard to self-intersect — but the
  paper makes no claim and runs no check.
- **Validation against real hydrodynamics: NONE.** No towing tank, no CFD, no
  reference hull. ("CFD" occurs once, in a reference title.)

---

## Paper 4 — Trinh, Hamagami & Okamoto — direct optimisation GAN

> Luan Thanh Trinh, Tomoki Hamagami (Yokohama National University), Naoya
> Okamoto (Japan Marine United Corporation), "3D Ship Hull Design Direct
> Optimization Using Generative Adversarial Network", *Journal of Advanced
> Computational Intelligence and Intelligent Informatics* **28**(3) (2024)
> 693–703. https://doi.org/10.20965/jaciii.2024.p0693 — open access, CC BY-ND.
> Received 7 Nov 2023, accepted 19 Feb 2024. Data and funding: Japan Marine
> United Corporation. File: `Fujipress_JACIII-28-3-23.pdf`.

Note this paper cites ShipHullGAN as "the closest study to our method" and
distinguishes itself: ShipHullGAN "emphasizes new designs over performance
optimization" (§2.2, p. 694).

**PDF extraction note:** this file's text layer mangles italic maths symbols
(`1 + ` = (1+k), `1 −C` = (1−t), `1 −F<` = (1−w), `G` = x, `GA`/`G6` = x_real /
x_fake, `8` = P, `_` = λ, `X` = δ, `U` = α). Symbols below are restored from
context; equation NUMBERS and all numeric values are as printed.

### 4.1 Shape representation — a DEPTH MAP, and no chine

**A single-channel depth map: a 2D image whose pixel value is the hull's
half-breadth.** (§3, p. 694–695.)

- Raw data: **301 very large crude oil carriers (VLCCs)** as polygonal meshes,
  from Japan Marine United. Mesh was rejected on cost grounds: "the mesh size
  increases the computational cost, rendering this approach unfeasible."
- "Owing to the **symmetrical structure of ship hulls**, depth maps can represent
  designs in detail and in the form of 2D arrays. In addition, depth maps do not
  cause many design errors when restored to 3D data."
- **Resolution: one pixel per SQUARE METRE.** Depth map and BSM are each
  `(48, 522, 1)`; stacked input is `(48, 522, 2)`.
- **Only the UNDERWATER part is used** (Fig. 1 caption), and — critically —
  "**The forward part of all hulls has the same shape, while the aft part
  includes the area of the stern which is systematically or locally deformed.**"

**CHINE: NO.** The words chine, knuckle and deadrise do not occur (the two
"chine" matches are inside "machine"). More fundamentally, a depth map is a
single-valued function `y = d(x, z)` on a regular 1 m grid — the same functional
limitation as Yonekura, plus a 1 metre quantisation. **INFERENCE:** a chine on a
small craft is a metre-scale or sub-metre feature; at 1 px/m it is below the
representation's resolution entirely. This representation is designed for a
300 m VLCC and does not transfer to a 10 m boat at any useful fidelity.

**The dataset is also the narrowest of the four**: 301 hulls that share an
IDENTICAL bow and midbody and differ only at the stern. This is not a hull-form
generator; it is **a stern-refinement tool for one ship type**, and the authors
frame it that way ("we do not aim to compete with [SBDO] for high accuracy or
detailed hydrodynamic analysis. Instead, we focused on providing designers with
instant reference ideas", §2.1, p. 694).

### 4.2 The performance-prediction model (PIEN) — priority item 1

**PIEN — Performance Indicator Estimation Network** (§4.2, p. 695–696).

- **Inputs**: the depth map (the same `(48, 522)` array). **Outputs**: three
  indicators, which are PROPULSION FACTORS, not resistance (§3, p. 695):
  - **(1+k)** — form factor, smaller is better;
  - **(1−t)** — thrust deduction, bigger is better;
  - **(1−w)** — wake fraction, smaller is better.
  The paper states the trade-off explicitly: (1+k) has "the greatest impact on
  the overall performance, twice that of (1−w). However, the improvement of
  (1+k) may cause (1−w) to worsen." (1−t) also matters but "optimizing (1−t)
  tends to change the design significantly and increase production costs."
- **Architecture: RepLKNet [33] + an LSTM layer** before the fully-connected
  head. The reasoning is unusually well argued (§4.2, p. 695–696) and is a
  genuine design insight: (i) the dataset is small, which favours a CNN's
  inductive bias over a ViT's; (ii) differences are LOCAL (stern), favouring
  CNNs; but (iii) the bow and midbody "do not contain much useful information ...
  because they have the same shape in our dataset. **However, their potential
  relationship with the stern has a high impact on the overall performance.**"
  So they need long-range dependency WITHOUT a transformer's data appetite —
  hence RepLKNet's large kernels plus LSTM.
- **Training data**: labels for the 301 hulls came from "hydrodynamic
  experiments" (§3, p. 695). **Whether those were towing-tank tests or CFD is
  NOT SPECIFIED anywhere in the paper.** Given §1 and §5.6 contrast the method
  against CFD "often taking several days to weeks", CFD is the likely source,
  but the paper does not say — NOT ADDRESSED.
- **Accuracy — and this is the best-validated model of the four.** Loss is RMSE
  over the three indicators; evaluation is **5-fold cross-validation (K1–K5)**
  with a reported TEST column. Table 2 (p. 698):

  | Fold | CNN (test) | CNN+LSTM (test) | ViT (test) | **Ours (test)** |
  |---|---|---|---|---|
  | K1 | 0.0531 | 0.0168 | 0.0311 | 0.0159 |
  | K2 | 0.0530 | 0.0167 | 0.0324 | 0.0148 |
  | K3 | 0.0676 | 0.0215 | 0.0359 | 0.0174 |
  | K4 | 0.0547 | 0.0687 | 0.0326 | 0.0153 |
  | K5 | 0.0685 | 0.0326 | 0.0378 | 0.0321 |
  | **Average** | 0.0594 | 0.0313 | 0.0339 | **0.0235** |

  Train average for "Ours" is 0.0152 against a test average of 0.0235 — a
  visible but modest generalisation gap. Note K5 (0.0321) is more than 2× K2
  (0.0148): **fold-to-fold spread is large relative to the mean**, which is what
  301 samples buys you. The paper does not report a standard deviation across
  folds, and no per-indicator breakdown is given — the RMSE is over all three at
  once, on normalised values.
- **OUT-OF-DISTRIBUTION BEHAVIOUR: NOT ADDRESSED.** The terms do not appear.
  There is no refusal mechanism, no confidence estimate, no applicability domain.
  **The nearest thing to an OOD control is structural and is actually rather
  good**: `Loss1` and the BSM together HARD-CONSTRAIN the generated design to
  stay near the original (see §4.4 below), so the generator cannot wander far
  from where PIEN was trained. That is containment by construction rather than
  by detection — worth noting as a design pattern, but it is not a refusal and
  the paper does not present it as an OOD measure.
- **Cost (Table 5, p. 700):** PIEN 3.21 M params / 0.12 GB / 0.08 s; main model
  5.76 M / 0.17 GB / 0.11 s; total 8.97 M / 0.29 GB / **0.19 s per sample** on
  an RTX 3070 Ti laptop GPU.

### 4.3 The relativistic average discriminator — priority item 2

**What problem it solved (§4.3, p. 697):** the authors want the discriminator to
police *surface quality* — "uneven surfaces or discontinuities" — not overall
ship-likeness.

The standard discriminator computes `D(x) = f(C(x))` with `f` sigmoid. The
**relativistic average discriminator (RaD)** [10, Jolicoeur-Martineau] instead
scores each sample RELATIVE to the average of the opposing set (Eqs. 1–2):

    D_Ra(x_r, x_f) = f( C(x_r) − E[C(x_f)] ) → 1
    D_Ra(x_f, x_r) = f( C(x_f) − E[C(x_r)] ) → 0

**The stated mechanism is the interesting part, and it generalises:**

> "When the model reached a certain level of training, the generator becomes
> capable of generating depth maps that closely resemble the original ship depth
> maps. As a result, **general shape features of ships start appearing in both
> x_r and x_f, and these features have already been incorporated into the
> learning process through Loss1. Using RaD, the general shape features can be
> effectively removed from [the] learning target of the discriminator.** Instead,
> the discriminator can focus more on detecting features pertaining to uneven
> surfaces, discontinuous surfaces, and other anomalous designs."

I.e. subtracting the opposing set's mean **cancels the signal that both sets
share**, leaving the discriminator to spend its capacity on the residual — which
here is exactly the defect signal. It is a division of labour: `Loss1` owns
"looks like the parent hull", `Loss3` owns "has no surface defects".

**Measured (§5.4, Table 4, p. 699)** with a purpose-built metric, the **shape
anomaly score (SAS)**, Eq. (10) — built on the premise that hull width should
increase monotonically from each end toward midships, summing
`max(d_{x,y} − d_{x+1,y}, 0)` over the forward half and
`max(d_{x+1,y} − d_{x,y}, 0)` over the after half, scaled by length:

| | Real designs | Standard D | **RaD** |
|---|---|---|---|
| SAS (test set) | 0 | 3.6e−6 | **9.6e−12** |

A ~375,000× reduction in the anomaly score. **INFERENCE:** SAS is a cheap
monotonicity check on an offsets table, and it is the only geometric-validity
metric in any of the four papers that is a real, computable NUMBER rather than a
visual inspection or a binary self-intersection test.

### 4.4 The two new generator losses — priority item 3, with formulations

All from §4.4, p. 697. `x_r` = original design, `x_f` = generated design.

**Loss1 — "restricts design variability"** (Eq. 3). Plain MSE/L1 between the two
depth maps fails, because "it causes the generator to try to create a design that
is identical to the original design to obtain a loss of zero." The fix is a
**deadband**: allow a free budget of change, and penalise only what exceeds it.

    Loss1 = E[ max( |x_f − x_r| − λ·E[x_r] , 0 ) ]        (3)

with **λ ∈ [0,1] "interpreted as the allowed percentage change"**, multiplied by
the mean value over all depth maps. **λ = 0.15** in the experiments (Table 1).
This is a hinge loss on geometric deviation and it is the mechanism by which
"new designs should not be too different from the original designs to optimize
production costs."

**Loss2 — "sets improvement targets" from PIEN** (Eqs. 4–6). Also a hinge, but
against a TARGET improvement rather than against zero. For an indicator `P` to be
REDUCED — (1+k), (1−w) — with `δ_P` the expected percentage improvement:

    Loss_P = E[ max( P_gen − P_orig + δ_P·E[P_orig] , 0 ) ]     (4)

For an indicator to be INCREASED — (1−t):

    Loss_{1−t} = E[ max( P_orig − P_gen + δ_{1−t}·E[P_orig] , 0 ) ]  (5)

Aggregated with weights `α ∈ [0,1]`:

    Loss2 = α_{1+k}·Loss_{1+k} + α_{1−t}·Loss_{1−t}
            + (1 − α_{1+k} − α_{1−t})·Loss_{1−w}                (6)

Settings: **α_{1+k} = 0.6, α_{1−t} = 0.2** (so 0.2 on wake fraction);
**δ_{1+k} = 0.15, δ_{1−t} = 0.05, δ_{1−w} = 0.05** (Table 1, p. 698).

**The design idea worth stealing: `max(·, 0)` on a TARGET, not on zero.** Both
losses go to zero once the design is "good enough" — within λ of the parent, or
δ better on the indicator — rather than pushing indefinitely. **INFERENCE:** that
is structurally the opposite of ShipGen's unbounded gradient descent on seven
objectives, and it is very plausibly why this paper does NOT report a
runaway-side-effect result of the 2.1×/1.51× kind. A satisficing objective cannot
run away.

**Loss3 — adversarial** (Eq. 7):

    Loss3 = −E_{x_r}[log(1 − D_Ra(x_r, x_f))] − E_{x_f}[log(1 − D_Ra(x_f, x_r))]

### 4.5 Training strategy — sigmoid-weighted learning (priority item 4)

§4.5, p. 697–698. The problem: three simultaneous losses give a complex search
space and local optima; but the common alternative — train on content loss first,
then bolt on adversarial loss — causes "a sudden shift in the learning objective,
leading to unstable training", with a cited example [36] where physical loss
"suddenly increases significantly and tends to explode".

**SWL** ramps `Loss2` in with a sigmoid schedule (Eqs. 8–9):

    Loss = γ1·Loss1 + γ2·s_B·Loss2 + γ3·Loss3               (8)
    s_B = 1 / (1 + e^{−v}),   v = β·(epoch/max_epoch) − β/2  (9)

with `γ1 = 1, γ2 = 1e−3, γ3 = 1` and `β = 14` (Table 1). Three stages named in
the text: **warm-up** (model learns mainly Loss1 + Loss3 to make valid designs;
Loss2 held at ~1e−4 to 0.02 so the objective never shifts abruptly),
**acceleration**, **stabilisation** (weight approaches 1).

**Note the structural similarity to ShipHullGAN's Eq. 12** (`Γ_G = Γ'_G (t/T)^p`,
space-filling ramped in after realism is learned). Two independent groups reached
the same conclusion: **learn to make VALID objects first, then optimise them.**
That is a real and transferable principle.

### 4.6 Results, and the side effect (§5.2, Table 3)

| Indicator | Train | Test |
|---|---|---|
| (1+k) form factor | +4.851% | **+5.251%** |
| (1−t) thrust deduction | +0.809% | +0.650% |
| (1−w) wake fraction | −5.693% | **−5.309%** |

**The headline "5.251% improvement" comes with a 5.309% DETERIORATION in wake
fraction** — the paper says so plainly and argues it nets out positive because
"the impact of (1−w) on the overall performance of the ship is only half that of
(1+k)", giving "**overall (1+k) has been improved by 2.626%**".

**This is the same lesson as ShipGen's 2.1× surface area, in milder form and with
the trade explicitly priced.** Guided generation moved the targeted objective and
paid for it in an untargeted-but-weighted one. Here it was ANTICIPATED (§3, p.
695 predicted it), BUDGETED (α = 0.2 on wake fraction), and REPORTED. That is the
better conduct of the two.

Other results: the edited region is "only approximately **9.6% of the width of
the hull**", concentrated at the stern (§5.2, Fig. 7). **BSM contribution
(§5.3):** without the BSM, average noise in empty (non-hull) regions was 0.02 per
pixel, "approximately 2% of the width of the hull", which corrupted PIEN's input
and was "difficult to remove using post-processing"; the BSM forces those regions
to 0 exactly. **SWL contribution (§5.5, Fig. 8):** fixed-weight combination got
stuck in a local optimum; staged addition caused Loss1 to "increase abruptly" when
Loss2 was added; SWL was best of the three.

**Validation against real hydrodynamics: NONE in this paper.** The optimised
hulls' 5.251% improvement is **PIEN's own prediction re-read on the test split**
— it is never re-checked by the "hydrodynamic experiments" that produced the
training labels. This is the weakest validation link of the four papers: ShipGen
at least re-ran its Michell solver on the generated hulls, and Yonekura re-ran its
closed-form C_d. **Here the surrogate grades its own homework.** §6 (Future Work)
concedes the direction: "it will be necessary to incorporate the physical
relationships of the indices into the loss function ... to improve the accuracy
and reliability of the PIEN model."

---

# 5. Cross-cutting judgement

## 5.0 The chine question, answered across all four papers

This was the question I was asked to keep answering. The answer is uncomfortable
and it is the same in every paper.

| Paper | Representation | Resolution | Chine? | Double chine? |
|---|---|---|---|---|
| ShipHullGAN | body-plan grid of section offsets, lofted to bicubic NURBS | 25 pts × 56 sections | **Never mentioned, never tested; the pipeline is C2 by construction** | No |
| ShipGen | **45-term analytic parameter vector** → algebraic surface | n/a (analytic) | **YES — explicit chine with beam `Bc`, deadrise `Beta`, fillet radius `Rc`, repeated at the transom** | **No — one chine only** |
| Yonekura | offsets table `y = f(x,z)` from the generalized Wigley formula | 20 stations × 40 levels | **NO — provably; `f` is C^∞ analytic and single-valued** | No |
| Trinh | **depth map** (2D image, pixel = half-breadth) | **1 pixel per m²**, 48 × 522 | **NO — single-valued, and 1 m quantisation is coarser than a chine** | No |

**Not one of the four can draw a DOUBLE CHINE.** ShipGen is the only one that
represents a chine at all, and it has exactly one — the same limitation NavalAI
has. **So the literature in this set does NOT contain the thing we most need.**
Our measured gap (two of five equivalent hull forms; the two double-chine forms
undrawable) is not closed by any of these papers, and no amount of training would
close it, because for three of the four the crease is outside the representation
entirely.

Stated the other way, and this is the strategically useful framing:
**ShipHullGAN's generality and ours are orthogonal.** It spans large smooth
displacement monohulls with bulbous bows — container ships, tankers, bulkers, a
naval combatant, a megayacht — and cannot crease. We draw chines and struggle
with round bilges. Its "generic" does not include our SKUs, and adopting its
representation would trade the one capability we have for one we do not need.

## 5.1 (a) REPRESENTATION IDEAS ADOPTABLE INTO AN ANALYTIC KERNEL — no network required

Highest-value category, and it is where three of the four papers actually pay.

**A1. Algebraic feasibility constraints evaluated BEFORE geometry is built.**
*(ShipGen §3.1.1, Appendix B Fig. A6.)* The single most transferable idea in the
set. 49 closed-form inequalities on the parameter vector, sufficient for
watertight + non-self-intersecting, at **199 µs against 1.77 s** for mesh-build-
and-check (~8900×). The FORM of the constraints is what to copy: they are
**ordering conditions between construction features** — "the chine fillet meets
the bottom inboard of `Bc`", "the keel fillet's intersection is inboard of the
chine fillet's", "the taper length is positive at the parabola's VERTEX, not just
at its endpoints". That last pattern — **check a polynomial's extremum inside the
domain, not only its ends** — is a class of bug our grammar can have wherever a
band is enforced at station endpoints.
Relevance is direct and already measured in our own tree: `hull_ast.py` records
that **4 of 4096** Builder draws type-checked and all 4 were then refused
downstream. That is our 1-in-150, worse. ShipGen's answer is not a smaller box;
it is explicit joint constraints that make the feasible set addressable.

**A2. Gaussian curvature as a GRADED manufacturing cost.**
*(ShipGen §3.1.2, Eq. 4.)* Area-averaged `1/(R_XY · R_YZ)`, finite-differenced on
a surface grid, normalised by LOA². The paper's rationale is sheet material and
welding — our exact problem. **This is the most valuable single import for the
`roundness` deadlock.** Right now `unroll.hull_panels` refuses any
`roundness > 0` and `hull_ast.Pin` pins it to exactly 0.0, so a sheet-built
typology occupies a measure-zero slice of the `roundness` axis: the answer is
binary and the optimiser gets no gradient. An area-averaged |K| turns
"developable / not developable" into a CONTINUOUS COST, which (i) lets a small
fillet be PRICED rather than refused, (ii) gives NSGA-II something to trade, and
(iii) is computable from geometry we already build, with zero learning.
**It does not soften the unroller's bar** — the refusal at the cutter stays; this
is a new measured quantity upstream of it, not a relaxation of an existing gate.

**A3. Non-uniform longitudinal station placement, and the ROTATING bow-plane
trick.** *(ShipHullGAN §3.2, Figs. 8(e–j); Yonekura §3.2.)* Both papers cluster
stations where shape changes fast; ShipHullGAN's `[0, 0.1, 0.3, 0.8, 1]` split
with E/4 sections in each region is a clean, stealable rule. The rotating-plane
construction for the bow — planes fanned about a vertical axis at x/L = 0.1
through arc-length-equal points on the deck curve — exists to avoid
**doubly-connected cross-sections** at a bulb. INFERENCE: the same degeneracy
arises for us at any re-entrant bow or a bulb/bustle, and this is a clean fix
that needs no network.

**A4. Longitudinally-varying chine parameters, pinned at two stations.**
*(ShipGen Fig. A5.)* `Bc`/`Beta`/`Rc`/`Rk` at midship AND `Bc_trans`/
`Beta_trans`/`Rc_trans`/`Rk_trans` at the transom, with the section interpolated
between. This is how a warped planing bottom is expressed with few parameters,
and it is a modest, well-defined extension.
**But be clear about what it does NOT do: it does not add a second chine.**

**A5. The shape anomaly score (SAS).** *(Trinh §5.4, Eq. 10.)* A monotonicity
check on the offsets table — half-breadth must increase from each end toward
midships — summed as `Σ max(d_x − d_{x+1}, 0)` forward and the reverse aft.
Cheap, closed-form, and it is the only NUMERIC geometric-validity metric in the
four papers. A useful cheap fairness gate.

**A6. MaxBox.** *(ShipGen §3.1.2.)* Largest rectangular prism inscribable in the
hull and lowerable vertically through the deck waterplane, by Nelder–Mead.
A geometry-only proxy for usable volume that could inform `arrangement.py`.
Lowest priority of the six; our arrangement model is already richer than a box.

**A7. Geometric moment invariants as a shape signature.** *(ShipHullGAN §3.4,
Eqs. 3–9.)* `MI_{p,q,r} = μ_{p,q,r}/(μ_{0,0,0})^{1+(p+q+r)/3}`, computed by the
divergence theorem, to 4th order = 35 components. The `m_p = −p·M_{p−1,0,0}`
identity linking the moments of `S'(x)` to the hull's longitudinal moments is
real mathematics, not a heuristic. Useful as a **shape-distance metric** —
"is this hull like that one?" — for OOD detection and for de-duplicating a design
archive, with no network anywhere. Caveat the authors give themselves: moments
capture wave-making, not viscous/separation physics.

## 5.2 (b) WHAT NEEDS A TRAINED MODEL — behind the `HullGenerator` Protocol

`navalai/generative.py` already defines the `HullGenerator` Protocol with two
implementations (`HullFamilyModel` GMM, `PPCAGenerator`), and its docstring
already names "guided tabular diffusion" as the planned upgrade on
"Ship-D-style data". These papers sharpen what that upgrade should be.

**B1. Guided tabular diffusion over the PARAMETER VECTOR — not over geometry.**
*(ShipGen.)* This is the right architecture for us and the papers make the case
empirically, not aesthetically:

| Method | Feasible-sample rate |
|---|---|
| Uniform random sampling | 0.67% |
| **CTGAN** trained on 30k feasible hulls | **0.7%** |
| Standard DDPM | 51.1% |
| **Classifier-guided DDPM (γ = 0.5)** | **99.5%** |

**A GAN trained specifically on feasible designs learned essentially nothing
about feasibility** — 0.7% versus random's 0.67%. That is a strong argument
against a GAN and for diffusion-with-explicit-guidance, and it says the
constraints must be EXPLICIT (a classifier trained on labelled violations) rather
than implicit in the data. Note our generator would operate on `grammar.PARAMS`,
so the whole analytic kernel, the unroller and the ladder stay downstream
untouched — the model proposes a parameter vector and nothing else.

**B2. A feasibility classifier trained on DELIBERATE NEGATIVES.**
*(ShipGen §3.1.1.)* 30,000 feasible + **20,000 deliberately infeasible** vectors.
We can generate our negatives for free from the grammar's own refusals — and per
`hull_ast.py` we currently produce ~4092 negatives per 4096 draws without trying.
The guidance gradient is what turns a 1-in-1000 sampler into a usable one.

**B3. Performance-conditioned generation (mission → hull), with a re-check.**
*(Yonekura.)* "Give me a hull with this displacement at this speed" is exactly
NavalAI's mission-first framing. The transferable pattern is Yonekura's, and it
is already our stance: **§3.3, p. 6 — "The GAN model did not consider physics.
The output data were not guaranteed to meet the requirements. Hence, labels were
recalculated using the output data and compared with the required labels."**
The model proposes; the analytic physics disposes. Adopt the loop, not the claim.

**B4. Curriculum on the loss: learn VALID first, optimise second.** Reached
independently by ShipHullGAN (Eq. 12, `Γ_G = Γ'_G(t/T)^p`, space-filling ramped
in after realism) and Trinh (Eqs. 8–9, sigmoid-weighted ramp on the performance
loss, with warm-up/acceleration/stabilisation). Two groups, same conclusion.

**B5. Hinge losses against a TARGET rather than unbounded descent.**
*(Trinh Eqs. 3–5.)* `max(|x_f − x_r| − λ·E[x_r], 0)` and
`max(P_gen − P_orig + δ·E[P_orig], 0)`: both go to zero once "good enough" is
reached. **INFERENCE, and I think it is the key structural difference in the
set:** Trinh's satisficing objectives did not produce a runaway side effect,
while ShipGen's unbounded multi-objective descent produced 2.1× surface area and
1.51× curvature. A satisficing objective cannot run away. If we ever put a
generative model in a guidance loop, the objectives should be hinged.

**B6. Latent-dimension selection by PCA-upper-bound then metric-guided
reduction.** *(ShipHullGAN §3.7.2.)* PCA at 99% variance gives an upper bound
(30); reduce while watching MMD (coverage), sparseness-at-centre (diversity) and
novelty; settle where diversity plateaus (20). Method-only, applies to our
existing PPCA/GMM latents today.

## 5.3 (c) WHAT WE MUST NOT ADOPT — naming the conflict precisely

**C1. A learned model that DEFINES a physical quantity.** ShipGen's seven
residual networks predict wave drag, areas, volumes, MaxBox and curvature and
those predictions STEER generation. NavalAI's rule is that geometry comes from
the mathematical kernel and a learned model may not define Cp, LCB, displacement,
stability or resistance. **Displacement and wetted area are exact integrals of a
surface we already have — predicting them with a network at R² = 0.98 is
strictly worse than computing them, and it launders an exact quantity into an
approximate one.** A surrogate is admissible only as a search accelerator whose
every kept design is re-validated up the ladder. Note Yonekura's paper is
CLEAN on this axis: it computes performance in closed form.

**C2. Reporting a TRAINING fit as the accuracy of a model used out of
distribution.** ShipGen's Table 3 is explicitly headed "Training Fit: [R²]" with
**no test split anywhere**, and Fig. 14 then shows the guided samples are
distributionally displaced from the training set. That is a surrogate quoted at
its in-sample accuracy while being used out of sample. Under our honesty rules a
quantity carries `{value, tier, sigma}`; **an R² with no held-out set supports no
sigma at all**, and "sufficient for use with performance-guided sampling" (§4.3.1)
is an assertion with a citation, not a measurement — and the 1.51× curvature
regression is what it cost. Yonekura reports no test set either. Only Trinh does
5-fold cross-validation with a test column, and it is the one to imitate.

**C3. Surrogates with NO REFUSAL PATH.** None of the four papers has one. No
applicability domain, no OOD detector, no confidence gate; every model answers
every query. ShipGen actively guides INTO the region where its surrogates are
least supported. Our rule — surrogates refuse OOD queries rather than
extrapolate — has no counterpart in this literature and must not be relaxed to
match it. *(A7 above, GMIs as a shape signature, is a plausible ingredient for
building the refusal these papers lack.)*

**C4. Wave resistance as the objective, normalised by anything but wetted area.**
ShipGen scales `C_w` by `LOA²` and explicitly declines to use wetted surface
(§3.1.2) — removing the term that restrains area growth — and got 2.1× the
surface area. ShipHullGAN optimised `C_w` alone and concedes "the obtained
optimised designs possess a larger wetted surface, increasing the frictional
resistance component" (§4.3.1). **This one is already partly guarded in our tree**
— `evaluate.py` computes `hs.wetted` and passes it into `total_resistance`, so
friction is priced inside resistance — but **wetted area is not itself an
objective and curvature is absent from the objective vector entirely.** That is
the exposure the coordinator identified and it is real, just narrower than
"resistance is unguarded": the risk is not mis-scaled drag, it is that
manufacturing cost has no term at all.

**C5. Visual inspection as a validity filter.** ShipHullGAN's plausibility
control is "less than 1 out of 70 instances with questionable designs" judged by
eye, with the remedy deferred to "appropriate design constraints and/or ...
the physical solver". Not a gate. `admissibility.py` and the ladder are.

**C6. "Feasible" meaning only watertight-and-non-self-intersecting.** ShipGen's
99.5% is a strong result about SURFACE TOPOLOGY and nothing else — the paper says
its own dataset hulls "do not necessarily look like realistic hull designs" and
are "relatively low performing". Do not let that number migrate into a strategy
document as a design-quality claim. It is not one, and the paper is honest about
it.

**C7. Abandoning the analytic kernel for a learned representation.** Beyond the
governance rules, the chine table in §5.0 makes this a capability regression:
three of the four representations cannot express a crease at all.

## 5.4 (d) WOULD ANY OF THIS MEET THIS PROJECT'S VALIDATION BAR?

**No. None of the four papers would pass Gate 2M as this project defines it, and
three of the four would not pass a much weaker bar.**

What our bar requires, and what is present:

| Requirement | ShipHullGAN | ShipGen | Yonekura | Trinh |
|---|---|---|---|---|
| Compared to EXPERIMENT (tank/EFD) | ✗ | ✗ | ✗ | ✗ |
| Compared to RANS / any viscous solver | ✗ | ✗ | ✗ | ✗ |
| Discretisation/grid convergence (GCI) | ✗ | ✗ (n/a) | ✗ (n/a) | ✗ |
| Uncertainty / sigma on any reported quantity | ✗ | ✗ | ✗ | ✗ |
| Held-out test set for the surrogate | n/a | **✗** | ✗ | **✓ (5-fold CV)** |
| Generated designs re-checked by the ORIGINAL solver | ✗ | **✓** | **✓** | ✗ |
| OOD refusal | ✗ | ✗ | ✗ | ✗ |
| Reproducible artefacts (data/code) | ✗ ("on request") | **✓ (Ship-D public)** | ✗ | ✗ |

**What is missing, specifically:**

1. **No experimental anchor anywhere in the four papers.** Every hydrodynamic
   number is potential flow: Dawson double-model linearisation (ShipHullGAN),
   Michell's integral (ShipGen, Yonekura), or an unstated source (Trinh).
   Nothing is compared to a towing tank. For contrast, our Gate 2M is blocked on
   matching KCS EFD `C_T = 3.711e−3` within a scatter band — a bar none of these
   papers attempts.
2. **No uncertainty on any quantity.** Rule 1 (`{value, tier, sigma}`) is
   unsatisfiable from anything reported here. Every number in these papers would
   enter our tree as tier-L0/L1 at best, with sigma unknown.
3. **The headline results are solver-limited in ways the authors document.**
   ShipHullGAN's −76% `C_w` is measured by a solver its own §4.3.1 says "may not
   provide reliable performance evaluation, primarily when the design ... is
   composed of unconventional features" — i.e. exactly the designs it makes. A
   500-iteration Jaya search against such a solver finds its blind spots. This is
   the same failure class as our own `gate2m.py` incident, where a second GCI
   implementation printed PASS on a diverging triplet: **the scoring function was
   trusted outside its domain of validity.**
4. **Trinh's optimisation result is graded by the surrogate that produced it.**
   The +5.251% is PIEN's own prediction, never re-checked against the
   "hydrodynamic experiments" that made the labels. ShipGen and Yonekura at least
   re-ran their solvers on the outputs.
5. **Validation of the ENCODING is reported only as figures.** ShipHullGAN's
   Hausdorff distance and Gaussian curvature comparisons (Fig. 10) carry no
   scalar in the text, and surface fairness is argued by zebra-stripe inspection
   with an asserted "C2 continuity".

**Where the papers are BETTER than their reputation, and it should be said:**
ShipGen publishes a result that embarrasses its own method — 2.1× surface area,
1.51× curvature, "**This is not desirable**" — and Trinh publishes a 5.309%
deterioration alongside a 5.251% improvement. **Both are exactly the conduct this
project demands (a failing gate is information), and both are more useful to us
than the headline claims.** Yonekura publishes a 175%-error table for the
configuration that did not work. That is three of four papers reporting their own
negative results, which is better than the field's norm.

---

# 6. What I would do next

Ordered, with the cheapest and most certain first. None of items 1–3 requires
training anything.

1. **Add area-averaged Gaussian curvature as a measured geometric quantity**
   (ShipGen Eq. 4: finite-difference `R_XY`, `R_YZ` on a surface grid,
   area-average, normalise by LOA²). Highest value per unit effort in this whole
   review. It converts the `roundness` pin from a measure-zero binary refusal
   into a priced continuum, gives NSGA-II a manufacturing gradient it currently
   does not have, and is computed from geometry we already build.
   **It does not touch `unroll.hull_panels`' refusal** — that bar stays where it
   is; this is a new upstream measurement, not a softened gate.
2. **Put a manufacturing-complexity term in the objective vector.** The 2.1× /
   4.4× / 1.51× result is the empirical case for it, and it is the specific
   exposure named in the brief. Wetted area is already priced inside
   `total_resistance` via `hs.wetted`, so the true hole is curvature/panel
   development, not drag scaling — state it that way so we fix the right thing.
3. **Write algebraic feasibility constraints in the ShipGen style, and measure
   our own 1-in-N.** `hull_ast.py` already records 4/4096 type-checking with all
   4 refused downstream. Reproduce ShipGen's two measurements on OUR kernel:
   the uniform-sampling feasible rate, and the time ratio between an algebraic
   check and a build-and-check. Copy the constraint FORM — feature-ordering
   inequalities, and extremum checks inside the domain rather than at endpoints.
4. **Decide the double-chine question on its own merits, because this literature
   does not answer it.** No paper here draws a second chine. If the two
   double-chine equivalent hull forms are needed, that is a KERNEL extension we
   design ourselves; the only prior art on offer is ShipGen's
   "chine = (beam, height, deadrise, fillet radius) at two longitudinal
   stations", which generalises to N chines in the obvious way but has not been
   done by anyone in this set. **Do not wait for a generative model to supply
   it — none of them can.**
5. **Consider guided tabular diffusion behind `HullGenerator`, and skip the GAN.**
   The CTGAN-at-0.7% result is the decisive number. If we do this, the
   feasibility classifier trained on deliberate negatives is the load-bearing
   part, not the diffusion model.
6. **Keep the refusal requirement, and consider GMIs as its mechanism.** Nothing
   in this literature refuses a query. A 4th-order GMI vector is a compact,
   affine-invariant shape signature and a natural basis for a
   distance-to-training-set applicability domain.
7. **NOT READ / NOT DONE, declared:** I did not attempt to obtain the Ship-D
   dataset from https://decode.mit.edu/projects/ShipGen/ (no network access used
   in this task); its 45-parameter documentation and the 49 constraints in
   Appendix B Fig. A6 are the artefacts worth fetching next, and Fig. A6's
   entries are transcribed above only as one-line summaries, not as formulae.
   ShipHullGAN's Figs. 10, 14, 15, 20–21 and ShipGen's Figs. 8–13 carry numbers
   only in the plots; no figure was digitised — where the text gave no scalar I
   have said so rather than reading a value off a chart.

---

*Sources: `downloads/hull-examples/research-gate/` — `1-s2.0-S0045782523001755-main.pdf`,
`jmse-11-02215.pdf`, `ai-06-00129.pdf`, `Fujipress_JACIII-28-3-23.pdf`.
Text extracted with `pypdf` 6.14.2; all four PDFs had complete text layers.
Symbol restoration in the Trinh paper is noted inline at §4. This document
records what the papers say and what I inferred, marked; it carries no project
status — for that ask `python -m navalai.gates` and
`python scripts/reconcile_gaps.py`.*

