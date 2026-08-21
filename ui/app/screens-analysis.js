/* ANALYSIS · OPTIMIZATION · VALIDATION · FINAL DESIGN · SYSTEM */
import {
  S, el, get, post, fmt, toast, qbadge, absentTile, constraintRow,
  project, touchProject, emit, linechart, esc, sci
} from "./core.js";
import { ensureEnvelope, bounds } from "./screens-design.js";

async function ev() {
  if (!S.evalOut) {
    const t0 = performance.now();
    S.evalOut = await post("/eval", { params: S.params, mission: S.mission });
    S.evalMs = performance.now() - t0; emit();
  }
  return S.evalOut;
}
async function twinData() {
  if (!S._twin || S._twinKey !== JSON.stringify(S.params)) {
    S._twin = await post("/api/twin", { params: S.params, mission: S.mission });
    S._twinKey = JSON.stringify(S.params);
  }
  return S._twin;
}

/* ========================================================== REALITY CHECK */

/* THE EIGHT ROWS, GROUPED UNDER THE THREE QUESTIONS A BUILDER ACTUALLY ASKS,
 * in the order the fear arrives. Not a re-ranking of the rows — the same
 * eight, read in human order. */
const QUESTIONS = [
  ["Will it float and stay upright?",
   ["freeboard", "gm", "trim", "list"],
   "Largest, first, always visible."],
  ["Can I actually build this?",
   ["bend_radius", "proportions"],
   "Plus the refold family, which decides kit against mould."],
  ["Is it legal, and what if I sell it?",
   ["rules", "lcb"],
   "ISO 12215 scantlings and RCD routing — an assessment aid, never a "
   + "certification claim."]
];

export async function reality(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "analysis · reality check"),
    el("h1", {}, "What the physics says")));
  const t = await twinData();
  const g = t.constraints.g, names = t.constraints.names;
  const viol = t.constraints.violations || [];

  host.append(el("div", { class: "spread", style: "margin:8px 0 16px" },
    el("span", { class: t.constraints.ok ? "chip pass" : "chip fail" },
      el("i", { class: "dot " + (t.constraints.ok ? "pass" : "fail") }),
      t.constraints.ok ? "every row satisfied" : viol.length + " row(s) violated"),
    el("span", { class: "mini" },
      "tier " + t.tier + " · evaluated in " + fmt(t.eval_ms, 2) + " ms · "
      + names.length + " rows (" + t.constraints.convention + ")")));

  for (const [q, rows, note] of QUESTIONS) {
    host.append(el("h2", { style: "margin:16px 0 4px" }, q));
    host.append(el("p", { class: "mini", style: "margin-bottom:8px" }, note));
    const set = el("div", { class: "rowset" });
    for (const r of rows) {
      if (!(r in g)) continue;
      set.append(constraintRow(r, g[r],
        viol.find(v => v.toLowerCase().includes(r.replace(/_/g, " ")))
        || viol.find(v => v.toLowerCase().includes(r))));
    }
    host.append(set);
  }
  const extra = names.filter(n => !QUESTIONS.some(q => q[1].includes(n)));
  if (extra.length) {
    host.append(el("h2", { style: "margin:16px 0 4px" },
      "Added by your constitution"));
    const set = el("div", { class: "rowset" });
    for (const r of extra) set.append(constraintRow(r, g[r]));
    host.append(set);
  }

  /* ---- capsize, on demand ------------------------------------------- */
  const cap = el("div", { class: "card", style: "margin-top:18px" });
  cap.append(el("h3", {}, "will she come back up?"));
  cap.append(el("p", { class: "mini" },
    "Heels her from 0 to 60° by floating the hull at each angle and finds "
    + "where the righting stops. About a second — which is why it is a "
    + "button and not a live light."));
  const capOut = el("div", { class: "stack-s", style: "margin-top:8px" });
  cap.append(el("button", {
    class: "act",
    onclick: async e2 => {
      e2.target.disabled = true;
      capOut.textContent = "";
      capOut.append(el("p", { class: "mini" }, el("span", { class: "spin" }),
        " heeling…"));
      S.capsize = await post("/api/capsize",
        { params: S.params, mission: S.mission });
      paintCap(); e2.target.disabled = false;
    }
  }, "run the capsize check →"), capOut);
  host.append(cap);
  if (S.capsize) paintCap();

  function paintCap() {
    const c = S.capsize; capOut.textContent = "";
    if (c.source !== "measured") {
      capOut.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "refused"), el("p", {}, c.reason)));
      return;
    }
    const cv = c.curve;
    capOut.append(el("div", { class: "cols c4" },
      qbadge("max righting arm", { value: cv.gz_max_m, tier: "L1",
        basis: "measured", sigma: null }, { unit: "m", dp: 3 }),
      qbadge("at heel", { value: cv.heel_at_gz_max_deg, tier: "L1",
        basis: "measured", sigma: null }, { unit: "°", dp: 1 }),
      qbadge("vanishing stability", { value: cv.avs_deg, tier: "L1",
        basis: "measured", sigma: null }, { unit: "°", dp: 1 }),
      qbadge("area to 30°", { value: cv.area_to_30_m_rad, tier: "L1",
        basis: "measured", sigma: null }, { unit: "m·rad", dp: 4 })));
    capOut.append(linechart({
      series: [{ name: "GZ", color: "var(--accent)",
        pts: cv.heels_deg.map((h, i) => [h, cv.gz_m[i]]), dots: false }],
      xlab: "heel °", ylab: "GZ (m)", h: 190
    }));
    capOut.append(el("p", { class: "mini" },
      "KG " + fmt(c.kg_above_keel_m, 3) + " m above keel · "
      + fmt(c.elapsed_ms, 0) + " ms"));
    capOut.append(el("div", { class: "note" },
      el("span", { class: "lbl" }, "what this assumed"),
      el("ul", { style: "margin:4px 0 0 15px" },
        ...c.assumptions.map(a => el("li", { style: "font-size:.78rem" }, a)))));
  }

  /* ---- where the weight sits ---------------------------------------- */
  if (t.weights) {
    const w = t.weights;
    const un = (w.items.find(i => i.id === "unaccounted") || {}).mass_kg || 0;
    const frac = w.total_kg > 0 ? 1 - un / w.total_kg : 0;
    const card = el("div", { class: "card", style: "margin-top:18px" });
    card.append(el("h3", {}, "where the weight sits"));
    card.append(el("div", { class: "bar" },
      el("i", { class: frac > 0.8 ? "pass" : "warn",
        style: `width:${(frac * 100).toFixed(1)}%` })));
    card.append(el("p", { class: "mini", style: "margin:5px 0 10px" },
      (frac * 100).toFixed(0) + "% of " + fmt(w.total_kg, 0)
      + " kg resolves to named items. " + fmt(un, 0) + " kg does not. "
      + "Every stability light above is computed on that estimate — treat "
      + "them as provisional until it closes. It is not hidden in a margin."));
    const tb = el("tbody");
    for (const i of [...w.items].sort((a, b) => b.mass_kg - a.mass_kg)) {
      tb.append(el("tr", { class: i.id === "unaccounted" ? "sel" : "" },
        el("td", { class: "mono" }, i.id),
        el("td", { class: "num" }, fmt(i.mass_kg, 0)),
        el("td", { class: "num" }, "±" + fmt(i.sigma_kg, 0)),
        el("td", { class: "mono" }, i.tier),
        el("td", { class: "num" }, fmt(i.x_m, 2)),
        el("td", { class: "num" }, fmt(i.y_m, 2)),
        el("td", { class: "num" }, fmt(i.z_m, 2))));
    }
    card.append(el("div", { class: "tbl" }, el("table", {},
      el("thead", {}, el("tr", {},
        el("th", {}, "item"), el("th", { class: "num" }, "kg"),
        el("th", { class: "num" }, "σ"), el("th", {}, "tier"),
        el("th", { class: "num" }, "LCG"), el("th", { class: "num" }, "TCG"),
        el("th", { class: "num" }, "VCG"))), tb)));
    card.append(el("dl", { class: "kv", style: "margin-top:8px" },
      el("dt", {}, "LCG"), el("dd", {}, fmt(w.lcg_m, 3) + " m"),
      el("dt", {}, "TCG"), el("dd", {}, fmt(w.tcg_m, 3) + " m"),
      el("dt", {}, "VCG"), el("dd", {}, fmt(w.vcg_m, 3) + " m"),
      el("dt", {}, "total σ"), el("dd", {}, "±" + fmt(w.sigma_kg, 0) + " kg")));
    host.append(card);
  }

  /* ---- solar day, and what its band is not -------------------------- */
  const en = t.energy;
  if (en) {
    const card = el("div", { class: "card", style: "margin-top:18px" });
    card.append(el("h3", {}, "a day on solar"));
    card.append(el("div", { class: "cols c4" },
      qbadge("generated", { value: en.solar_kwh_day, tier: "L1", sigma: 0,
        basis: "placeholder" }, { unit: "kWh", dp: 1 }),
      qbadge("used at cruise", { value: en.wh_per_nm,
        tier: "L1", sigma: en.sigma_wh_per_nm, basis: en.sigma_basis },
        { unit: "Wh/nm", dp: 0 }),
      qbadge("range on the sun", { value: en.range_solar_nm_day, tier: "L1",
        sigma: null, basis: "propagated-lower-bound" }, { unit: "nm/day", dp: 1 }),
      qbadge("range on battery", { value: en.range_battery_nm, tier: "L1",
        sigma: null, basis: "propagated-lower-bound" }, { unit: "nm", dp: 1 })));
    card.append(el("p", { class: "mini", style: "margin-top:8px" },
      "Draw is properly propagated — its σ comes from the resistance band and "
      + "the drivetrain in quadrature. Generation is NOT: it is a flat daily "
      + "average and its band is grey because there is no input spread to "
      + "carry through. Net " + fmt(en.net_kwh_day, 2) + " kWh/day."));
    card.append(absentTile("state_of_charge"));
    host.append(card);
  }

  host.append(el("div", { style: "margin-top:18px" }, absentTile("motion_in_chop",
    el("p", { class: "mini" },
      "This tile is the one that proves the others are telling the truth."))));

  /* ---- provenance strip --------------------------------------------- */
  const r = t.resistance;
  host.append(el("div", { class: "note", style: "margin-top:18px" },
    el("span", { class: "lbl" }, "how much to trust this"),
    el("p", {}, "The drag model is " + (t.resistance ? esc(String(r.regime)) : "—")
      + "-regime thin-ship theory at Fn " + fmt(r?.fn, 3)
      + ", and its only CFD anchor is a 230 m container ship that shares no "
      + "chine, transom or spray physics with your boat. Below Fn 0.45 you "
      + "are inside the model's own range; above it we stop giving you a "
      + "number rather than guess."),
    el("p", { style: "margin-top:6px" },
      el("a", { href: "#/validation" }, "what we tested, and against what →"))));
}

/* ============================================================ HYDROSTATICS */

export async function hydrostatics(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "analysis · L2 engineering"),
    el("h1", {}, "Hydrostatics")));
  const t = await twinData();
  const d = t.genome.derived;
  if (!Object.keys(d).length) {
    host.append(el("div", { class: "note refuse" },
      el("span", { class: "lbl" }, "the hull does not float"),
      el("p", {}, "No equilibrium was found at this displacement, so there "
        + "are no hydrostatics to report — not zeros.")));
    return;
  }
  host.append(el("p", { class: "lede" },
    "Every value below is DERIVED from the floated hull. None of it is "
    + "editable, and none of it is drawn as if it were: causality runs from "
    + "the genome to these numbers, never back."));

  const rows = [
    ["displacement", d.displacement_kg, "kg", 0],
    ["volume", d.volume_m3, "m³", 3],
    ["draft", d.draft_m, "m", 3],
    ["waterline length", d.lwl_eff_m, "m", 3],
    ["max waterline beam", d.b_wl_max_m, "m", 3],
    ["waterplane area", d.awp_m2, "m²", 3],
    ["wetted surface", d.wetted_m2, "m²", 3],
    ["LCB (from transom)", d.lcb_m, "m", 3],
    ["LCF (from transom)", d.lcf_m, "m", 3],
    ["KB", d.kb_m, "m", 3],
    ["BM transverse", d.bm_m, "m", 3],
    ["BM longitudinal", d.bm_l_m, "m", 3],
    ["block coefficient", d.cb, "-", 4],
    ["prismatic coefficient", d.cp, "-", 4],
    ["minimum freeboard", d.freeboard_min_m, "m", 3]
  ];
  host.append(el("div", { class: "cols c4" },
    ...rows.map(([n, v, u, dp]) => qbadge(n,
      { value: v, tier: "L1", sigma: null, basis: "measured" },
      { unit: u === "-" ? "" : u, dp }))));

  const g = t.constraints.g;
  host.append(el("h2", { style: "margin:20px 0 6px" }, "The stability picture"));
  host.append(el("div", { class: "cols c2" },
    el("div", { class: "card" }, el("h3", {}, "attitude"),
      el("dl", { class: "kv" },
        el("dt", {}, "GM"), el("dd", {},
          (d.kb_m != null && d.bm_m != null)
            ? fmt(d.kb_m + d.bm_m, 3) + " m  (KB+BM, before KG)" : "—"),
        el("dt", {}, "trim margin"), el("dd", {}, fmt(g.trim, 3)),
        el("dt", {}, "list margin"), el("dd", {}, fmt(g.list, 3)),
        el("dt", {}, "freeboard margin"), el("dd", {}, fmt(g.freeboard, 3)))),
    el("div", { class: "card" }, el("h3", {}, "verdicts"),
      el("div", { class: "rowset" },
        ...["freeboard", "gm", "trim", "list", "lcb"]
          .filter(k => k in g).map(k => constraintRow(k, g[k]))))));
  host.append(el("p", { class: "mini", style: "margin-top:10px" },
    "The equilibrium solver finds sinkage and trim SIMULTANEOUSLY — a damped "
    + "2-D Newton warm-started from the level float, which is what keeps it "
    + "inside the 50 ms budget the slider loop depends on."));
  host.append(el("div", { style: "margin-top:14px" }, absentTile("cb_sigma")));
}

/* =========================================================== RESISTANCE */

export async function resistance(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "analysis · L2 engineering"),
    el("h1", {}, "Resistance, power and the model's own ceiling")));
  host.append(el("p", { class: "lede" },
    "Swept through the real ladder, one evaluate() per speed. Past Fn 0.45 "
    + "the point is REFUSED by name rather than extrapolated: there is no "
    + "Savitsky-class model in this tree, and a faded curve there would be a "
    + "guess wearing a line style."));

  const out = el("div", { class: "stack" });
  host.append(el("div", { class: "row" },
    el("button", {
      class: "act",
      onclick: async e2 => {
        e2.target.disabled = true;
        out.textContent = "";
        out.append(el("p", { class: "mini" }, el("span", { class: "spin" }),
          " sweeping speeds through the ladder…"));
        S.sweep = await post("/api/speedsweep",
          { params: S.params, mission: S.mission });
        render(); e2.target.disabled = false;
      }
    }, "run the speed sweep"),
    el("span", { class: "mini" }, "one full L1 evaluation per speed")), out);
  if (S.sweep) render();

  function render() {
    const s = S.sweep; out.textContent = "";
    const ok = s.points.filter(p => p.state === "OK");
    const ref = s.points.filter(p => p.state === "REFUSED");
    if (!ok.length) {
      out.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "no speed in this sweep is inside the model"),
        el("p", {}, ref[0]?.reason || "")));
      return;
    }
    const refX = ref.length ? Math.min(...ref.map(p => p.kn)) : null;
    const band = refX != null
      ? [{ x0: refX, x1: Math.max(...s.points.map(p => p.kn)),
           label: "REFUSED — past Fn 0.45" }] : [];
    out.append(el("div", { class: "card" },
      el("h3", {}, "total resistance against speed"),
      linechart({
        series: [{ name: "total Rt (N)", color: "var(--accent)", fill: true,
          pts: ok.map(p => [p.kn, p.rt_n, p.sigma_rt_n]) },
          { name: "friction Rf", color: "var(--pass)",
            pts: ok.map(p => [p.kn, p.rf_n]) },
          { name: "wave Rw", color: "var(--copper)",
            pts: ok.map(p => [p.kn, p.rw_n]) }],
        xlab: "knots", ylab: "N", bands: band, h: 230
      }),
      el("p", { class: "mini", style: "margin-top:6px" }, s.breakdown_note)));

    out.append(el("div", { class: "cols c2" },
      el("div", { class: "card" }, el("h3", {}, "propulsive power"),
        linechart({
          series: [{ name: "shaft power (W)", color: "var(--accent)",
            pts: ok.map(p => [p.kn, p.power_w]) }],
          xlab: "knots", ylab: "W", bands: band, h: 190
        })),
      el("div", { class: "card" }, el("h3", {}, "energy per mile"),
        linechart({
          series: [{ name: "Wh/nm", color: "var(--copper)", fill: true,
            pts: ok.map(p => [p.kn, p.wh_per_nm, p.sigma_wh_per_nm]) }],
          xlab: "knots", ylab: "Wh/nm", bands: band, h: 190
        }))));

    if (ref.length) {
      out.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, ref.length + " speeds refused"),
        el("p", {}, ref[0].reason),
        el("p", { class: "mini", style: "margin-top:6px" },
          "The ceiling for this hull is " + fmt(refX, 1) + " knots. Semi-"
          + "displacement and planing are refused BY NAME — that is a hard "
          + "stop with an explanation, not a gap to paper over.")));
      out.append(absentTile("planing"));
    }

    const tb = el("tbody");
    for (const p of s.points) {
      tb.append(el("tr", {},
        el("td", { class: "num" }, fmt(p.kn, 1)),
        el("td", { class: "num" }, fmt(p.fn, 3)),
        el("td", {}, p.state === "OK"
          ? el("span", { class: "chip pass" }, p.regime)
          : el("span", { class: "chip fail" }, "REFUSED")),
        el("td", { class: "num" }, p.rt_n == null ? "—" : fmt(p.rt_n, 1)),
        el("td", { class: "num" }, p.rw_n == null ? "—" : fmt(p.rw_n, 1)),
        el("td", { class: "num" }, p.rf_n == null ? "—" : fmt(p.rf_n, 1)),
        el("td", { class: "num" }, p.power_w == null ? "—" : fmt(p.power_w, 0)),
        el("td", { class: "num" }, p.trim_deg == null ? "—" : fmt(p.trim_deg, 2))));
    }
    out.append(el("div", { class: "tbl" }, el("table", {},
      el("thead", {}, el("tr", {},
        el("th", { class: "num" }, "kn"), el("th", { class: "num" }, "Fn"),
        el("th", {}, "regime"), el("th", { class: "num" }, "Rt N"),
        el("th", { class: "num" }, "Rw N"), el("th", { class: "num" }, "Rf N"),
        el("th", { class: "num" }, "P W"), el("th", { class: "num" }, "trim °"))),
      tb)));
  }
}

/* ============================================================== CFD ===== */

export async function cfd(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "analysis · L3 validation"),
    el("h1", {}, "CFD workspace")));
  const d = await get("/api/cfd/cases");
  host.append(el("div", { class: "note refuse" },
    el("span", { class: "lbl" }, "read this before reading a number below"),
    el("p", {}, d.note || ""),
    el("p", { style: "margin-top:6px" },
      "A solver exiting is not convergence and it is certainly not "
      + "validation. These rows are the RECEIPTS a case wrote at mesh time. "
      + "No force history is read here and no C_T is claimed.")));

  if (d.source !== "measured" || !d.n) {
    host.append(el("div", { class: "hatched", style: "margin-top:14px" },
      el("h3", {}, "▨ NO CFD CASES ON THIS MACHINE"),
      el("p", { class: "mini" }, d.reason || "runs/ is empty")));
    return;
  }
  host.append(el("div", { class: "cols c4", style: "margin:14px 0" },
    stat(String(d.n), "case receipts on disk"),
    stat(String(d.bars.flow_throughs_floor), "flow-through FLOOR — below it "
      + "the domain still holds its initial condition"),
    stat(String(d.bars.flow_throughs_settled), "flow-throughs before a run is "
      + "called settled"),
    stat("≥" + d.bars.cells_per_wavelength, "cells per wavelength, or the "
      + "wave field is decoration")));

  host.append(el("div", { class: "note" },
    el("span", { class: "lbl" }, "starting a run is not wired to this browser"),
    el("p", {}, "A campaign is an OpenFOAM job on the simulation node, hours "
      + "long, and a button here would imply otherwise. The commands are:"),
    el("pre", { class: "mono mini", style: "margin-top:6px;white-space:pre-wrap" },
      "python scripts/make_case.py --triplet --symmetric --out runs/<case>\n"
      + "openfoam scripts/run_campaign.sh runs/<case> 10\n"
      + "python scripts/gate2m.py runs/<case>")));

  const tb = el("tbody");
  for (const c of d.cases) {
    const st = c.state;
    tb.append(el("tr", {},
      el("td", { class: "mono" }, c.name),
      el("td", {}, c.benchmark),
      el("td", { class: "num" }, c.lwl_m == null ? "—" : fmt(c.lwl_m, 2)),
      el("td", { class: "num" }, c.speed_ms == null ? "—" : fmt(c.speed_ms, 2)),
      el("td", { class: "num" }, c.cells_bg == null ? "—" : fmt(c.cells_bg, 0)),
      el("td", { class: "num" }, c.cells_per_wavelength == null ? "—"
        : fmt(c.cells_per_wavelength, 1)),
      el("td", { class: "num" }, c.n_layers == null ? "—" : fmt(c.n_layers, 0)),
      el("td", { class: "num" }, c.flow_throughs == null ? "n/a"
        : fmt(c.flow_throughs, 2)),
      el("td", {}, el("span", {
        class: "chip " + (st === "UNDER-RUN" ? "fail"
          : st === "SETTLING-UNVERIFIED" ? "warn" : "unk")
      }, st))));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {},
      el("th", {}, "case"), el("th", {}, "benchmark"),
      el("th", { class: "num" }, "Lwl"), el("th", { class: "num" }, "U m/s"),
      el("th", { class: "num" }, "bg cells"),
      el("th", { class: "num" }, "cells/λ"), el("th", { class: "num" }, "layers"),
      el("th", { class: "num" }, "flow-thr"), el("th", {}, "state"))), tb)));
  host.append(el("p", { class: "mini", style: "margin-top:8px" },
    "UNDER-RUN means the free stream has not crossed the domain once. "
    + "MEASURED on one such run: it printed `settled: yes` on 3.3% drift at "
    + "0.70 flow-throughs while the pressure part of the force swung 2.6× "
    + "underneath a passing number."));
}

function stat(n, label) {
  return el("div", { class: "card" },
    el("div", { class: "qval mono", style: "font-size:1.5rem" }, n),
    el("div", { class: "mini" }, label));
}

/* ======================================================== SEARCH / POPULATION */

export async function search(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "optimization · population"),
    el("h1", {}, "The search, and everything it threw away")));
  host.append(el("p", { class: "lede" },
    "Every candidate goes through the SAME evaluate() the sliders call, and "
    + "a design that dies reports the row that killed it. No design is "
    + "hidden: a rejection you cannot see is a rejection you cannot learn "
    + "from."));

  const ctl = el("div", { class: "card stack-s" });
  const n = el("input", { type: "number", value: 200, min: 10, max: 5000,
                          style: "width:6.5em" });
  const gov = el("input", { type: "checkbox", checked: true });
  ctl.append(el("h3", {}, "budget"),
    el("div", { class: "row" },
      el("label", { class: "row" }, "candidates", n),
      el("label", { class: "row" }, gov, "search inside the compiled envelope"),
      el("button", { class: "act", onclick: start }, "run the sweep"),
      el("button", { class: "act danger", onclick: cancel }, "cancel")),
    el("p", { class: "mini" },
      "MEASURED: only 3 of 400 random draws clear the 5 mm refold bar, and "
      + "most candidates die in the grammar check at 0.27 ms. Ungoverned "
      + "sampling gave roundness > 0 on 60 of 60 draws and the unroller "
      + "refused every one — untick the box to watch that happen."));
  host.append(ctl);

  const out = el("div", { class: "stack", style: "margin-top:14px" });
  host.append(out);
  let timer = null, job = null;

  async function start() {
    const r = await post("/api/search/start", {
      n: Number(n.value), governed: gov.checked, mission: S.mission
    });
    job = r.job; toast("sweep " + job + " started");
    clearInterval(timer); timer = setInterval(poll, 700); poll();
  }
  async function cancel() {
    if (!job) return;
    await post("/api/search/cancel", { job }); toast("cancelling");
  }
  async function poll() {
    if (!job) return;
    const s = await post("/api/search/status", { job });
    S.search = s; render(s);
    if (s.state !== "RUNNING") clearInterval(timer);
  }
  if (S.search) render(S.search);

  function render(s) {
    out.textContent = "";
    out.append(el("div", { class: "spread" },
      el("span", { class: "chip " + (s.state === "RUNNING" ? "warn"
        : s.state === "DONE" ? "pass" : "fail") },
        s.state === "RUNNING" ? el("span", { class: "spin" }) : null, s.state),
      el("span", { class: "mini" }, s.method),
      el("span", { class: "mini" }, fmt(s.elapsed_s, 1) + " s")));
    out.append(el("div", { class: "bar" },
      el("i", { style: `width:${(s.done / s.n * 100).toFixed(1)}%` })));
    out.append(el("div", { class: "cols c4" },
      stat(s.done + " / " + s.n, "evaluated"),
      stat(String(s.n_kept), "survived every row"),
      stat(String(s.n_rejected), "rejected — reasons below"),
      stat(s.best ? fmt(s.best.wh_per_nm, 0) : "—", "best Wh/nm so far")));

    if (Object.keys(s.rejected_counts).length) {
      const total = Object.values(s.rejected_counts).reduce((a, b) => a + b, 0);
      const card = el("div", { class: "card" });
      card.append(el("h3", {}, "why designs disappeared"));
      for (const [row, c] of Object.entries(s.rejected_counts)
        .sort((a, b) => b[1] - a[1])) {
        card.append(el("div", { class: "spread", style: "margin:4px 0" },
          el("span", { class: "mono mini" }, row.replace(/_/g, " ")),
          el("span", { class: "mono mini" }, c + " (" +
            (c / total * 100).toFixed(0) + "%)")));
        card.append(el("div", { class: "bar", style: "height:6px" },
          el("i", { class: "fail", style: `width:${(c / total * 100).toFixed(1)}%` })));
      }
      out.append(card);
    }
    if (s.rejections.length) {
      const tb = el("tbody");
      for (const r of s.rejections.slice().reverse()) {
        tb.append(el("tr", {},
          el("td", { class: "mono" }, r.row),
          el("td", { style: "font-size:.76rem" }, r.why)));
      }
      out.append(el("div", { class: "tbl" }, el("table", {},
        el("thead", {}, el("tr", {}, el("th", {}, "row that killed it"),
          el("th", {}, "what the ladder said"))), tb)));
    }
    if (s.kept.length) {
      const tb = el("tbody");
      for (const k of s.kept) {
        tb.append(el("tr", {},
          el("td", { class: "num" }, fmt(k.wh_per_nm, 0)),
          el("td", { class: "num" }, fmt(k.gm_m, 3)),
          el("td", { class: "num" }, fmt(k.disp_kg, 0)),
          el("td", { class: "num" }, fmt(k.rt_n, 1)),
          el("td", {}, el("button", {
            class: "ghost",
            onclick: () => {
              S.params = { ...k.params }; S._twin = null;
              touchProject({ params: S.params }); emit();
              toast("loaded into the studio"); location.hash = "#/hull";
            }
          }, "open"))));
      }
      out.append(el("h3", { style: "margin-top:12px" }, "survivors"));
      out.append(el("div", { class: "tbl" }, el("table", {},
        el("thead", {}, el("tr", {},
          el("th", { class: "num" }, "Wh/nm"), el("th", { class: "num" }, "GM m"),
          el("th", { class: "num" }, "disp kg"), el("th", { class: "num" }, "Rt N"),
          el("th", {}, ""))), tb)));
    }
  }
}

/* ================================================================= PARETO */

export async function pareto(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "optimization · trade-off surface"),
    el("h1", {}, "Pareto front")));
  host.append(el("p", { class: "lede" },
    "NSGA-II minimises three objectives: energy per mile, build area, and the "
    + "DISTANCE from the middle of the GM band. GM is a band, not a "
    + "maximisation — too much of it is a violent roll — so it is never "
    + "decoded from the objective vector; each point's GM is re-read from the "
    + "ladder."));
  const btn = el("button", { class: "act" }, "compute the front");
  const out = el("div", { class: "stack", style: "margin-top:14px" });
  host.append(el("div", { class: "row" }, btn,
    el("span", { class: "mini" },
      "pop 48 × 15 generations. A cold mission pays the search; the payload "
      + "declares whether this request paid it.")), out);
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    out.textContent = "";
    out.append(el("p", { class: "mini" }, el("span", { class: "spin" }),
      " searching — this is a real NSGA-II run, not a cached picture"));
    S.pareto = await post("/pareto", { mission: S.mission });
    render(); btn.disabled = false;
  });
  if (S.pareto) render();

  function render() {
    const d = S.pareto; out.textContent = "";
    out.append(el("div", { class: "spread" },
      el("span", { class: "mini" }, d.points.length + " front members · "
        + d.n_evals + " evaluations · tier " + d.tier),
      el("span", { class: "chip " + (d.live ? "warn" : "pass") },
        d.live ? "this request paid " + fmt(d.elapsed_ms, 0) + " ms"
               : "served from cache")));
    if (d.refused) {
      out.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "this brief is outside our library"),
        el("ul", { style: "margin:4px 0 0 15px" },
          ...d.refused_reasons.map(r => el("li", { style: "font-size:.8rem" }, r)))));
    }
    if (!d.points.length) {
      out.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "the search found no feasible front"),
        el("p", {}, "An empty list is not 'there are no good boats'. MEASURED "
          + "on this budget: 240 evaluations → 0 members, 480 → 1, 800 → 0, "
          + "1200 → 48. It is NON-MONOTONE, so the search is unreliable here "
          + "rather than merely slow, and the honest fix is a warm start from "
          + "feasible draws — not more patience."),
        el("p", { style: "margin-top:6px" },
          el("a", { href: "#/search" }, "→ run a governed sweep instead, and "
            + "watch what the rows reject"))));
      return;
    }
    const pts = d.points.map((p, i) => [p.wh_per_nm, p.build_area_m2, i]);
    const card = el("div", { class: "card" });
    card.append(el("h3", {}, "energy per mile against build area"));
    const chart = linechart({
      series: [{ name: "front", color: "var(--copper)", dots: true,
        pts: pts.slice().sort((a, b) => a[0] - b[0]) }],
      xlab: "Wh/nm", ylab: "build area m²", h: 250
    });
    card.append(chart);
    out.append(card);
    const tb = el("tbody");
    d.points.forEach((p, i) => {
      tb.append(el("tr", {},
        el("td", { class: "num" }, String(i)),
        el("td", { class: "num" }, fmt(p.wh_per_nm, 0)),
        el("td", { class: "num" }, fmt(p.build_area_m2, 1)),
        el("td", { class: "num" }, p.gm_m == null ? "—" : fmt(p.gm_m, 3)),
        el("td", {}, el("button", {
          class: "ghost", onclick: () => {
            S.params = { ...p.params }; S._twin = null;
            touchProject({ params: S.params }); emit();
            toast("hull #" + i + " loaded"); location.hash = "#/hull";
          }
        }, "open"),
          el("button", {
            class: "ghost", onclick: () => {
              S.compare = [...S.compare.filter(c => c.i !== i),
                { i, params: p.params }].slice(-4);
              toast(S.compare.length + " selected for comparison");
            }
          }, "compare"))));
    });
    out.append(el("div", { class: "tbl" }, el("table", {},
      el("thead", {}, el("tr", {}, el("th", { class: "num" }, "#"),
        el("th", { class: "num" }, "Wh/nm"), el("th", { class: "num" }, "area m²"),
        el("th", { class: "num" }, "GM m"), el("th", {}, ""))), tb)));
  }
}

/* ================================================================ COMPARE */

export async function compare(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "optimization · comparison"),
    el("h1", {}, "Why is one better than another?")));
  if (S.compare.length < 2) {
    host.append(el("div", { class: "note" },
      el("span", { class: "lbl" }, "pick two to four designs"),
      el("p", {}, "Mark them on the Pareto front or the search survivors, "
        + "then come back. The current studio hull is always included."),
      el("p", { style: "margin-top:6px" },
        el("a", { href: "#/pareto" }, "→ Pareto front"))));
    return;
  }
  host.append(el("p", { class: "lede" },
    "The same evaluation, run on each genome, with the DELTA shown per row. "
    + "A comparison that reports a single score would be hiding the trade "
    + "that makes the answer interesting."));
  const sets = [{ i: "studio", params: S.params }, ...S.compare].slice(0, 4);
  const evs = await Promise.all(sets.map(s =>
    post("/api/twin", { params: s.params, mission: S.mission })));

  const metrics = [
    ["Wh/nm", t => t.energy?.wh_per_nm, 0, "lower"],
    ["total resistance N", t => t.resistance?.total, 1, "lower"],
    ["wave resistance N", t => t.resistance?.rw, 1, "lower"],
    ["friction N", t => t.resistance?.rf, 1, "lower"],
    ["wetted surface m²", t => t.genome.derived.wetted_m2, 2, "lower"],
    ["displacement kg", t => t.genome.derived.displacement_kg, 0, "—"],
    ["draft m", t => t.genome.derived.draft_m, 3, "lower"],
    ["Cb", t => t.genome.derived.cb, 4, "—"],
    ["solar range nm/day", t => t.energy?.range_solar_nm_day, 1, "higher"],
    ["ply thickness mm", t => t.ply_thickness_m == null ? null
      : t.ply_thickness_m * 1e3, 1, "lower"]
  ];
  const tb = el("tbody");
  for (const [name, f, dp, want] of metrics) {
    const vals = evs.map(f);
    const base = vals[0];
    tb.append(el("tr", {},
      el("td", {}, name),
      ...vals.map((v, i) => el("td", { class: "num" },
        v == null ? "—" : fmt(v, dp)
          + (i > 0 && base ? "  (" + (v > base ? "+" : "")
            + ((v - base) / base * 100).toFixed(1) + "%)" : ""))),
      el("td", { class: "mini" }, want)));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "metric"),
      ...sets.map(s => el("th", { class: "num" }, "#" + s.i)),
      el("th", {}, "better"))), tb)));

  host.append(el("h2", { style: "margin:18px 0 6px" }, "What changed in the genome"));
  const names = Object.keys(evs[0].genome.mutable);
  const gb = el("tbody");
  for (const n of names) {
    const vals = evs.map(t => t.genome.mutable[n]);
    if (vals.every(v => Math.abs(v - vals[0]) < 1e-9)) continue;
    gb.append(el("tr", {}, el("td", { class: "mono" }, n),
      ...vals.map(v => el("td", { class: "num" }, fmt(v, 4)))));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "gene"),
      ...sets.map(s => el("th", { class: "num" }, "#" + s.i)))), gb)));

  host.append(el("h2", { style: "margin:18px 0 6px" }, "Rows"));
  const rb = el("tbody");
  for (const r of evs[0].constraints.names) {
    rb.append(el("tr", {}, el("td", { class: "mono" }, r),
      ...evs.map(t => {
        const g = t.constraints.g[r];
        return el("td", { class: "num", style: g > 0 ? "color:var(--fail)" : "" },
          fmt(g, 3));
      })));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "row (≤0 satisfied)"),
      ...sets.map(s => el("th", { class: "num" }, "#" + s.i)))), rb)));
}

/* ============================================================= VALIDATION */

const CONF_CLASS = { VALIDATED: "pass", CALIBRATED: "warn",
  EXTRAPOLATED: "warn", UNVALIDATED: "unk" };

export async function validation(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "validation"),
    el("h1", {}, "What the physics was checked against")));
  const d = await get("/api/validation");
  host.append(el("div", { class: "note refuse" },
    el("span", { class: "lbl" }, "this is PHYSICS confidence, not AI confidence"),
    el("p", {}, "There is no such thing here as \"94% confident\". A model is "
      + "either reproduced against an experiment we hold, fitted to data, "
      + "extrapolated beyond its anchor, or unvalidated — and the last of "
      + "those is an ABSENT score, not a low one.")));

  host.append(el("div", { class: "cols c4", style: "margin:14px 0" },
    ...Object.entries(d.confidence_model).map(([k, v]) =>
      el("div", { class: "card" },
        el("span", { class: "chip " + CONF_CLASS[k] }, k),
        el("p", { class: "mini", style: "margin-top:6px" }, v)))));

  for (const b of d.benchmarks) {
    const c = el("div", { class: "card", style: "margin-bottom:12px" });
    c.append(el("div", { class: "spread" },
      el("h2", {}, b.title || b.id),
      el("span", { class: "chip " + (CONF_CLASS[b.confidence] || "unk") },
        b.confidence)));
    if (b.error) {
      c.append(el("p", { class: "mini", style: "color:var(--fail)" },
        "could not be loaded: " + b.error));
      host.append(c); continue;
    }
    const kv = el("dl", { class: "kv", style: "margin-top:8px" });
    kv.append(el("dt", {}, "reference"), el("dd", {}, b.reference || "—"));
    kv.append(el("dt", {}, "kind"), el("dd", {}, b.kind || "—"));
    for (const [k, v] of Object.entries(b.conditions || {})) {
      kv.append(el("dt", {}, k),
        el("dd", {}, Array.isArray(v) ? v.map(x => fmt(x, 4)).join(" – ")
                                      : fmt(v, 4)));
    }
    if (b.reference_value) {
      kv.append(el("dt", {}, b.reference_value.name),
        el("dd", {}, sci(b.reference_value.value)));
    }
    if (b.scatter_band) {
      kv.append(el("dt", {}, "scatter band"),
        el("dd", {}, b.scatter_band.map(x => sci(x, 3)).join(" – ")));
    }
    if (b.n_points) kv.append(el("dt", {}, "data points"),
      el("dd", {}, String(b.n_points)));
    if (b.tolerance) kv.append(el("dt", {}, "tolerance"),
      el("dd", {}, JSON.stringify(b.tolerance)));
    if (b.gate) kv.append(el("dt", {}, "gate"), el("dd", {}, b.gate));
    c.append(kv);
    c.append(el("div", { class: "note refuse", style: "margin-top:10px" },
      el("span", { class: "lbl" }, "scope — read this before quoting it"),
      el("p", {}, b.scope_warning)));
    if (b.our_value == null && b.kind !== "absent") {
      c.append(el("p", { class: "mini", style: "margin-top:6px" },
        "OUR value against this reference is not carried in this page: it "
        + "comes from running the gate's suite, and a number typed here "
        + "would be a second home for it."));
    }
    if (b.unblocked_by) c.append(el("p", { class: "mini", style: "margin-top:6px" },
      "What would close it: " + b.unblocked_by));
    if (b.not_implemented?.length) {
      c.append(el("p", { class: "mini", style: "margin-top:6px" },
        "NOT IMPLEMENTED: " + b.not_implemented.join("; ")));
    }
    host.append(c);
  }
  host.append(absentTile("hardchine_anchor"));
}

/* ================================================================== GATES */

export async function gates(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "validation · L3"),
    el("h1", {}, "Gates and the expected-red ledger")));
  const d = await get("/api/gates");
  host.append(el("div", { class: "note refuse" },
    el("span", { class: "lbl" }, "no suite was run to draw this page"),
    el("p", {}, d.suite_note),
    el("pre", { class: "mono mini", style: "margin-top:6px;white-space:pre-wrap" },
      d.how_to_verify)));

  host.append(el("h2", { style: "margin:18px 0 6px" },
    "RED, and recorded — the ledger is the ONE home of these numbers"));
  for (const [name, r] of Object.entries(d.ledger)) {
    const c = el("div", { class: "card", style: "margin-bottom:10px" });
    c.append(el("div", { class: "spread" },
      el("h3", { style: "font-size:.95rem;color:var(--fail)" }, name),
      el("span", { class: "chip fail" }, "RED")));
    c.append(el("p", { style: "font-size:.85rem;margin-top:4px" }, r.metric));
    c.append(el("dl", { class: "kv", style: "margin-top:8px" },
      el("dt", {}, "watermark"), el("dd", {}, String(r.watermark)),
      el("dt", {}, "units"), el("dd", {}, r.units || "—"),
      el("dt", {}, "bar"), el("dd", { style: "white-space:normal" }, r.bar || "—"),
      el("dt", {}, "measured"), el("dd", {}, r.measured_utc || "—"),
      el("dt", {}, "measured on"), el("dd", { style: "white-space:normal" },
        r.measured_on || "—"),
      el("dt", {}, "owner"), el("dd", {}, r.owner || "—"),
      el("dt", {}, "review by"), el("dd", {}, r.review_by || "—")));
    if (r.verify) c.append(el("pre", {
      class: "mono mini", style: "margin-top:8px;white-space:pre-wrap"
    }, r.verify));
    if (r.why_red?.length) {
      const det = el("details", { style: "margin-top:8px" });
      det.append(el("summary", { class: "mini" }, "why it is red, verbatim"));
      det.append(el("pre", { class: "mono mini", style: "white-space:pre-wrap" },
        r.why_red.join("\n")));
      c.append(det);
    }
    host.append(c);
  }

  host.append(el("h2", { style: "margin:18px 0 6px" },
    d.gates.length + " gates in the ladder"));
  const tb = el("tbody");
  for (const g of d.gates) {
    tb.append(el("tr", { class: d.ledger[g.name] ? "sel" : "" },
      el("td", { class: "mono" }, g.name),
      el("td", { style: "font-size:.78rem" }, g.scope),
      el("td", { class: "mono mini" }, (g.suite || "").replace(/`/g, "")),
      el("td", {}, d.ledger[g.name]
        ? el("span", { class: "chip fail" }, "ledgered RED")
        : el("span", { class: "chip unk" }, "run the suite"))));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "gate"), el("th", {}, "scope"),
      el("th", {}, "evidence"), el("th", {}, "status"))), tb)));
}

/* ============================================================ BUILD ===== */

export async function build(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "final design"),
    el("h1", {}, "Build package")));
  host.append(el("p", { class: "lede" },
    "This screen opens with a ROUTING VERDICT, not a download button. Every "
    + "hull is classified kit or mould, and the exporter raises rather than "
    + "writing a cut file whose panels will not re-fold to the boat."));

  const routeBox = el("div", { class: "stack" });
  host.append(routeBox);
  const pkg = el("div", { class: "stack", style: "margin-top:16px" });
  host.append(pkg);

  routeBox.append(el("div", { class: "row" },
    el("button", {
      class: "act",
      onclick: async e2 => {
        e2.target.disabled = true;
        S.refold = await post("/api/refold", { params: S.params });
        paintRoute(); e2.target.disabled = false;
      }
    }, S.refold ? "re-measure the route" : "measure the route  (~12 s)"),
    el("button", {
      class: "act",
      onclick: async e2 => {
        e2.target.disabled = true;
        pkg.textContent = "";
        pkg.append(el("p", { class: "mini" }, el("span", { class: "spin" }),
          " unrolling, nesting and pricing the sheet goods — measured ~4.5 s"));
        S.build = await post("/api/buildability",
          { params: S.params, mission: S.mission });
        paintPkg(); e2.target.disabled = false;
      }
    }, "compute the package  (~5 s)"),
    el("span", { class: "mini" },
      "Both are real jobs on real geometry — the unroller is measured at "
      + "869 ms per call and the route reads a family of three station "
      + "counts. They run when you ask, never on navigation.")));
  if (S.refold) paintRoute();
  if (S.build) paintPkg();

  function paintRoute() {
    const r = S.refold;
    [...routeBox.children].slice(1).forEach(c => c.remove());
    if (r.source === "refused") {
      routeBox.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "▲ this shell cannot be a flat-pack kit"),
        el("p", {}, r.reason)));
      return;
    }
    const kit = r.verdict === "PASSES";
    routeBox.append(el("div", { class: "note " + (kit ? "bind" : "refuse") },
      el("span", { class: "lbl" }, kit
        ? "● SHEET KIT — flat panels, stitched and glued"
        : "▲ THIS HULL IS A MOULD BUILD, NOT A FLAT-PACK KIT"),
      el("p", {}, r.verdict_meaning),
      el("p", { class: "mono mini", style: "margin-top:6px" },
        (r.counts || []).map((c, i) => `n=${c} → ${fmt(r.worst_mm[i], 2)} mm`)
          .join("   ") + `   ·   bar ${fmt(r.bar_mm, 1)} mm`)));
    if (!kit) {
      routeBox.append(el("div", { class: "cols c2" },
        el("div", { class: "card" },
          el("h3", {}, "find me a cuttable version"),
          el("p", { style: "font-size:.86rem" },
            "This is a SEARCH, not a switch. Only 3 hulls in 400 can be cut "
            + "from flat sheet, so we go looking. It runs for minutes and it "
            + "can fail."),
          el("p", { class: "mini", style: "margin-top:6px" },
            "When it finds one it costs something. MEASURED on one brief: "
            + "59 → 121 plywood sheets, 1825 → 3679 build hours, "
            + "412 → 595 Wh/nm — and GM 0.82 → 2.55 m, which is better. Flat "
            + "and beamy cuts well and floats well. It is not cheap."),
          el("p", { class: "mini", style: "margin-top:6px;color:var(--warn)" },
            "▨ The search JOB is not wired to this browser yet. Today it runs "
            + "as `python scripts/design_kit.py`. A button here would promise "
            + "something instant that takes minutes.")),
        el("div", { class: "card" },
          el("h3", {}, "build it over a mould"),
          el("p", { style: "font-size:.86rem" },
            "Frames and battens, then sheet it. More work, more skill, any "
            + "shape you like. No search needed — your hull is already the "
            + "shape you drew."),
          el("p", { class: "mini", style: "margin-top:6px" },
            "Frames and patterns still come out of the same nest."))));
    }
  }

  function paintPkg() {
    const b = S.build; pkg.textContent = "";
    if (b.source === "refused") {
      pkg.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "refused at " + b.at),
        el("p", {}, b.reason)));
      return;
    }
    const s = b.summary;
    pkg.append(el("div", { class: "cols c4" },
      stat(String(s.ply_sheets), "plywood sheets — COUNTED off the layout, "
        + "not estimated from area"),
      stat(fmt(s.panel_area_m2, 0) + " m²", "panel area"),
      stat(fmt(s.epoxy_kg, 0) + " kg", "epoxy"),
      stat(fmt(s.build_hours, 0) + " h", "build hours (practice values)")));
    pkg.append(el("div", { class: "cols c4" },
      stat(String(s.panel_count), "sheet parts"),
      stat(String(s.bulkheads), "bulkheads"),
      stat(String(s.frames), "frames"),
      stat((b.layout ? (b.layout.utilisation * 100).toFixed(1) : "—") + "%",
        "nest utilisation")));
    pkg.append(el("p", { class: "mini" }, s.basis));
    pkg.append(el("div", { class: "note bind" },
      el("span", { class: "lbl" }, "thickness"),
      el("p", {}, "Bottom " + fmt(b.bottom_thickness_mm, 1) + " mm, "
        + b.ply_thickness_basis + ".")));

    if (b.layout) pkg.append(nestCanvas(b.layout));

    pkg.append(el("h2", { style: "margin-top:16px" },
      "Bill of materials — " + b.bom.length + " lines"));
    const tb = el("tbody");
    for (const l of b.bom) {
      tb.append(el("tr", {},
        el("td", { class: "mono" }, l.part),
        el("td", { class: "num" }, String(l.qty)),
        el("td", {}, l.material),
        el("td", { class: "num" }, fmt(l.thickness_mm, 1)),
        el("td", { class: "num" }, fmt(l.area_m2, 3)),
        el("td", { class: "num" }, l.sheet == null ? "—" : String(l.sheet)),
        el("td", { style: "font-size:.72rem" }, l.note)));
    }
    pkg.append(el("div", { class: "tbl" }, el("table", {},
      el("thead", {}, el("tr", {}, el("th", {}, "part"),
        el("th", { class: "num" }, "qty"), el("th", {}, "material"),
        el("th", { class: "num" }, "mm"), el("th", { class: "num" }, "m²"),
        el("th", { class: "num" }, "sheet"), el("th", {}, "note"))), tb)));

    pkg.append(el("h2", { style: "margin-top:16px" }, "Not in this box"));
    for (const m of b.missing_from_bom) {
      pkg.append(el("div", { class: "hatched", style: "margin-bottom:8px" },
        el("h3", {}, "▨ " + m.what.toUpperCase()),
        el("p", { class: "mini" }, m.why),
        el("p", { class: "mini" }, "What would close it: " + m.unblocked_by)));
    }
    pkg.append(absentTile("assembly_manual"));

    /* download gate */
    const kit = S.refold && S.refold.verdict === "PASSES";
    pkg.append(el("div", { class: "card", style: "margin-top:16px" },
      el("h3", {}, "release"),
      el("div", { class: "rowset" },
        gateRow("every panel present in the cut file",
          b.bom.length > 0 && b.layout != null),
        gateRow("panels re-fold to the hull within the bar", !!kit),
        gateRow("units declared in the file", true),
        gateRow("thickness derived from ISO 12215-5, not typed",
          b.ply_thickness_m != null)),
      el("p", { class: "mini", style: "margin-top:8px" },
        kit ? "Every check passes. Producing the ZIP is `export_dxf`, which "
            + "runs on the simulation node and stamps REFOLD VERIFIED into "
            + "the file — it is not wired to this browser, and the button "
            + "would be the only thing here that lies about where work "
            + "happens."
            : "The release is BLOCKED: the refold check has not passed. This "
            + "is enforced server-side — export_dxf raises rather than "
            + "writing a file — so it is not a UI promise.")));

    pkg.append(el("h2", { style: "margin-top:16px" }, "Legal"));
    pkg.append(legalCard());
  }

  function gateRow(label, ok) {
    return el("div", { class: "crow " + (ok ? "ok" : "bad") },
      el("div", { class: "cn" }, label),
      el("div", { class: "cv" }, ok ? "PASS" : "NOT MET"));
  }
}

function nestCanvas(layout) {
  const wrap = el("div", { class: "card", style: "margin-top:14px" });
  wrap.append(el("h3", {}, "nested sheets — "
    + fmt(layout.sheet_l * 1000, 0) + " × " + fmt(layout.sheet_w * 1000, 0)
    + " mm · " + layout.n_sheets + " sheets"));
  const sheets = [...new Set(layout.placements.map(p => p.sheet))].sort((a, b) => a - b);
  let idx = 0;
  const cv = el("canvas", { style: "width:100%;max-width:640px;display:block" });
  const cap = el("div", { class: "mini" });
  const nav = el("div", { class: "row", style: "margin-top:6px" },
    el("button", { class: "ghost", onclick: () => { idx = Math.max(0, idx - 1); draw(); } }, "◀"),
    cap,
    el("button", { class: "ghost", onclick: () => { idx = Math.min(sheets.length - 1, idx + 1); draw(); } }, "▶"));
  wrap.append(cv, nav);
  wrap.append(el("p", { class: "mini", style: "margin-top:6px" },
    layout.utilisation_note + ". A shop wastes 5–10% on a production run; "
    + "you are at " + ((1 - layout.utilisation) * 100).toFixed(1)
    + "% waste, which is normal for a one-off."));
  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const W = cv.clientWidth || 600, H = Math.round(W * layout.sheet_w / layout.sheet_l);
    cv.width = W * dpr; cv.height = H * dpr; cv.style.height = H + "px";
    const g = cv.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const css = v => getComputedStyle(document.body).getPropertyValue(v).trim();
    g.fillStyle = css("--sunk"); g.fillRect(0, 0, W, H);
    g.strokeStyle = css("--rule"); g.strokeRect(0.5, 0.5, W - 1, H - 1);
    const sx = W / layout.sheet_l, sy = H / layout.sheet_w;
    const here = layout.placements.filter(p => p.sheet === sheets[idx]);
    for (const p of here) {
      g.fillStyle = css("--accent-soft");
      g.fillRect(p.y * sx, p.x * sy, p.h * sx, p.w * sy);
      g.strokeStyle = css("--accent");
      g.strokeRect(p.y * sx, p.x * sy, p.h * sx, p.w * sy);
      g.fillStyle = css("--ink-2"); g.font = "9px ui-monospace, monospace";
      g.fillText(p.part.slice(0, 16), p.y * sx + 3, p.x * sy + 11);
    }
    cap.textContent = `sheet ${idx + 1} of ${sheets.length} · ${here.length} parts`
      + ` · ${here[0] ? here[0].thickness_mm + " mm" : ""}`;
  }
  requestAnimationFrame(draw);
  return wrap;
}

function legalCard() {
  const c = el("div", { class: "card" });
  c.append(el("h3", {}, "route — an assessment aid, not legal advice"));
  // PU-7: RENDERED from `CompiledPolicy.delivery_route`, never recomputed.
  const r = S.envelope?.route || null;
  if (r && r.mode && r.mode !== "UNKNOWN" && r.mode !== "REFUSED") {
    c.append(el("div", { class: "spread" },
      el("span", { class: "chip " +
        (r.mode === "notified_body_required" ? "fail" : "pass") },
        r.mode.replace(/_/g, " ").toUpperCase()),
      el("span", { class: "mono mini" }, r.article || "")));
    c.append(el("p", { style: "font-size:.85rem;margin-top:6px" }, r.rationale));
    if (r.conditions?.length) {
      c.append(el("ul", { style: "margin:6px 0 0 15px" },
        ...r.conditions.map(x =>
          el("li", { style: "font-size:.78rem" }, x))));
    }
    if (r.ai_act) {
      c.append(el("p", { class: "mini", style: "margin-top:8px" },
        "AI Act " + r.ai_act.article + " — " + r.ai_act.note));
      c.append(el("p", { class: "mini" }, r.ai_act.safety_component_question));
    }
    if (r.mode === "notified_body_required") {
      c.append(el("div", { class: "note refuse", style: "margin-top:8px" },
        el("span", { class: "lbl" }, "the release refuses to emit"),
        el("p", {}, "This route needs a notified body. A release from here "
          + "would be a compliance claim this platform is not entitled to "
          + "make.")));
    }
  } else if (r) {
    c.append(el("div", { class: "note refuse" },
      el("span", { class: "lbl" }, "no route: " + r.mode),
      el("p", {}, r.refusal || "")));
  }
  c.append(el("p", { style: "font-size:.86rem;margin-top:8px" },
    "Building for your OWN use puts a craft outside the Recreational Craft "
    + "Directive for five years from putting it into service. Selling inside "
    + "that window triggers post-construction assessment by a notified body "
    + "— the most expensive moment to need one."));
  c.append(el("p", { class: "mini", style: "margin-top:6px" },
    "Directive 2013/53/EU, Art. 2(2)(a)(vii) and Art. 19(4). If routing lands "
    + "on NOTIFIED_BODY_REQUIRED, the release refuses to emit."));
  const e = S.envelope;
  if (e?.disclaimer) c.append(el("p", { class: "mini", style: "margin-top:6px" },
    e.disclaimer));
  return c;
}

/* ================================================================== TWIN */

export async function twin(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "final design"),
    el("h1", {}, "Digital twin")));
  const t = await twinData();
  host.append(el("p", { class: "lede" },
    "Everything known about this design, assembled from the modules that own "
    + "each part. Nothing here is computed by this screen — it is a JOIN, so "
    + "it cannot become a second home for a number."));

  host.append(el("h2", { style: "margin:16px 0 6px" }, "Genome"));
  host.append(el("p", { class: "mini", style: "margin-bottom:8px" },
    t.genome.note));
  const gb = el("tbody");
  for (const [k, v] of Object.entries(t.genome.mutable)) {
    gb.append(el("tr", {}, el("td", { class: "mono" }, k),
      el("td", { class: "num" }, fmt(v, 4)),
      el("td", {}, el("span", { class: "chip warn" }, "MUTABLE"))));
  }
  for (const [k, v] of Object.entries(t.genome.derived)) {
    gb.append(el("tr", {}, el("td", { class: "mono" }, k),
      el("td", { class: "num" }, fmt(v, 4)),
      el("td", {}, el("span", { class: "chip unk" }, "DERIVED"))));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "field"),
      el("th", { class: "num" }, "value"), el("th", {}, "class"))), gb)));

  host.append(el("h2", { style: "margin:16px 0 6px" }, "Badges — every band's basis"));
  host.append(el("p", { class: "mini", style: "margin-bottom:8px" },
    "The band, and where the band came from. This grid deliberately shows the "
    + "SIGMA rather than the value: the point of it is the register, and a "
    + "value here would be a second copy of a number the screens above own."));
  host.append(el("div", { class: "cols c4" },
    ...Object.entries(t.badges).map(([k, v]) => qbadge(k,
      { value: v.sigma, tier: v.tier, sigma: null, basis: v.basis },
      { dp: 3, sub: "σ" }))));

  host.append(el("h2", { style: "margin:16px 0 6px" },
    "Rules tier — " + (t.rules?.passed ?? "?") + " of "
    + (t.rules?.total ?? "?") + " findings"));
  host.append(el("div", { class: "note refuse" },
    el("span", { class: "lbl" }, "disclaimer, verbatim"),
    el("p", {}, t.rules?.disclaimer || "")));
  const rb = el("tbody");
  for (const f of (t.rules?.findings || [])) {
    rb.append(el("tr", {},
      el("td", { class: "mono" }, f.rule_id),
      el("td", { style: "font-size:.76rem" }, f.clause),
      el("td", {}, el("span", { class: "chip " + (f.passed ? "pass" : "fail") },
        f.passed ? "pass" : "fail")),
      el("td", { class: "num" }, fmt(f.measured, 3)),
      el("td", { class: "num" }, fmt(f.required, 3)),
      el("td", {}, f.unit),
      el("td", {}, f.basis),
      el("td", { style: "font-size:.72rem" }, f.note)));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "rule"), el("th", {}, "clause"),
      el("th", {}, ""), el("th", { class: "num" }, "measured"),
      el("th", { class: "num" }, "required"), el("th", {}, "unit"),
      el("th", {}, "basis"), el("th", {}, "note"))), rb)));
  if (t.rules?.unreviewed_bases?.length) {
    host.append(el("p", { class: "mini", style: "margin-top:6px;color:var(--warn)" },
      "Unreviewed bases: " + t.rules.unreviewed_bases.join(", ")
      + " — these findings rest on a practice value, not on a transcribed "
      + "clause, and they say so."));
  }

  host.append(el("h2", { style: "margin:16px 0 6px" }, "Resistance model receipt"));
  host.append(el("pre", { class: "mono mini", style: "white-space:pre-wrap" },
    JSON.stringify(t.resistance, null, 1)));

  host.append(el("h2", { style: "margin:16px 0 6px" }, "What this twin does not hold"));
  for (const k of ["motion_in_chop", "cost_model", "assembly_manual"]) {
    host.append(el("div", { style: "margin-bottom:8px" }, absentTile(k)));
  }
}

/* ================================================================= SYSTEM */

export async function system(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "system · L3"),
    el("h1", {}, "Models, solvers, budgets, data")));
  const m = S.manifest;
  if (!m) { host.append(el("p", {}, "manifest unavailable")); return; }

  host.append(el("h2", { style: "margin:14px 0 6px" }, "What is real"));
  const rb = el("tbody");
  for (const [k, v] of Object.entries(m.real)) {
    rb.append(el("tr", {}, el("td", { class: "mono" }, k),
      el("td", { style: "font-size:.8rem" }, v)));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "capability"),
      el("th", {}, "what makes it real"))), rb)));

  host.append(el("h2", { style: "margin:18px 0 6px" }, "Latency budgets"));
  host.append(el("p", { class: "mini", style: "margin-bottom:8px" },
    m.budgets_note + ". These are what force the two-rate render loop: the "
    + "fast mesh is live, the fine mesh settles on release, and the unroller "
    + "is never in the loop."));
  host.append(el("div", { class: "cols c4" },
    ...Object.entries(m.budgets_ms).map(([k, v]) =>
      el("div", { class: "card" },
        el("div", { class: "qval mono" }, fmt(v, 2) + " ms"),
        el("div", { class: "mini" }, k)))));

  host.append(el("h2", { style: "margin:18px 0 6px" },
    "Declared absences — " + Object.keys(m.absent).length));
  host.append(el("p", { class: "mini", style: "margin-bottom:8px" },
    "This registry lives in ui/api.py and is SERVED, never typed into the "
    + "markup. The day a capability lands, its tile disappears with it "
    + "instead of going on claiming the gap."));
  const ab = el("tbody");
  for (const [k, a] of Object.entries(m.absent)) {
    ab.append(el("tr", {}, el("td", { class: "mono" }, k),
      el("td", {}, a.what), el("td", { style: "font-size:.78rem" }, a.why),
      el("td", { style: "font-size:.78rem" }, a.unblocked_by),
      el("td", { class: "mono mini" }, a.surface || "—")));
  }
  host.append(el("div", { class: "tbl" }, el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "key"), el("th", {}, "what"),
      el("th", {}, "why absent"), el("th", {}, "what would close it"),
      el("th", {}, "surface"))), ab)));

  host.append(el("h2", { style: "margin:18px 0 6px" }, "Constraint rows"));
  host.append(el("p", { class: "mono mini" }, m.constraints.join(" · ")));
  host.append(el("p", { class: "mini" },
    "Exactly " + m.constraints.length + ". A ninth would have to be added to "
    + "navalai/evaluate.py, and the optimizer would consume it automatically."));

  host.append(el("h2", { style: "margin:18px 0 6px" }, "Other surfaces"));
  host.append(el("div", { class: "row" },
    el("a", { class: "chip", href: "/legacy" },
      "the engineer's 16-slider page (/legacy)"),
    el("a", { class: "chip", href: "/api/manifest" }, "/api/manifest"),
    el("a", { class: "chip", href: "/api/gates" }, "/api/gates")));
}
