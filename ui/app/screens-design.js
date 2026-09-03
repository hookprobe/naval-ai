/* DESIGN: projects, mission, requirements, envelope, the studio, buildability. */
import {
  S, el, get, post, fmt, toast, qbadge, absentTile, constraintRow,
  project, touchProject, saveProjects, openProject, emit, sub, linechart
} from "./core.js";
import { Viewport } from "./viewport.js";

/* =========================================================== shared state */

export function bounds() {
  /* Track ends come from the COMPILED BOX when a policy has been compiled —
   * PU-1: "illegal is undraggable rather than rejected later". The ungoverned
   * grammar bounds are kept alongside so the clipped-away range can be drawn
   * as a ghost with its reason, which teaches instead of blocking silently. */
  const out = {};
  for (const p of (S.manifest?.params || [])) {
    out[p.name] = { lo: p.low, hi: p.high, ulo: p.low, uhi: p.high,
                    unit: p.unit, desc: p.desc, clipped: false };
  }
  const e = S.envelope;
  if (e && e.source === "measured") {
    e.names.forEach((n, i) => {
      if (!out[n]) return;
      out[n].lo = e.low[i]; out[n].hi = e.high[i];
      out[n].ulo = e.ungoverned_low[i]; out[n].uhi = e.ungoverned_high[i];
      out[n].clipped = (e.low[i] > e.ungoverned_low[i] + 1e-12)
                    || (e.high[i] < e.ungoverned_high[i] - 1e-12);
      out[n].edits = (e.edits || []).filter(x => x.param === n);
    });
  }
  return out;
}

/* ------------------------------------------------------ behavioural layer */
/* PU-1. Six intent controls, each driving several of the 16 grammar
 * parameters along a curated path. A parameter is composed as
 *     norm = clamp(0.5 + SUM_controls amp * (u - 0.5), 0, 1)
 * and then mapped onto the parameter's LEGAL span, so a policy-clipped bound
 * is a shorter track and never an out-of-bounds proposal. The expert switch
 * writes the same 16 numbers through the same /eval — there is no second
 * code path, which is what PU-1's done-when requires. */
export const BEHAVIOUR = [
  { id: "bow", label: "Bow attitude", lo: "Cuts through it", hi: "Rides over it",
    feel: "Wet ride against dry ride. This one moves buildability hard.",
    drives: { forefoot: 0.9, beta_bow: 0.8, sheer_rise: 0.7, flare: 0.8 },
    locked: "reverse-raked bow", lockAt: "hi", absent: "stem_rake" },
  { id: "room", label: "Room vs. range", lo: "More boat inside", hi: "Further per kWh",
    feel: "Drag and the solar day, in the same gesture as interior volume.",
    drives: { BWL: -0.7, D: -0.6, Cp: 0.6 } },
  { id: "planted", label: "Feels planted", lo: "Tippy but quick", hi: "Planted and steady",
    feel: "The GM light — and a ceiling, because too much GM is a violent roll.",
    drives: { BWL: 0.8, T: -0.5 } },
  { id: "bottom", label: "Bottom shape", lo: "Flat and simple", hi: "Vee, softer landing",
    feel: "Slam comfort against panel twist and sheet count.",
    drives: { beta_mid: 0.9, beta_len: 0.6 } },
  { id: "keel", label: "Keel line", lo: "Tracks straight", hi: "Turns easily",
    feel: "Directional stability. Small drag effect.",
    drives: { rocker: 0.9 } },
  { id: "stern", label: "Stern", lo: "Tucked and quiet", hi: "Carries weight aft",
    feel: "Where the battery can sit without burying the transom.",
    drives: { r_transom: 0.8, x_mb: 0.5 } }
];

export function behaviourToParams(u, b) {
  const acc = {};
  for (const ctl of BEHAVIOUR) {
    const uv = u[ctl.id] ?? 0.5;
    for (const [p, amp] of Object.entries(ctl.drives)) {
      acc[p] = (acc[p] ?? 0.5) + amp * (uv - 0.5);
    }
  }
  const out = {};
  for (const [p, n] of Object.entries(acc)) {
    const bd = b[p]; if (!bd) continue;
    const t = Math.max(0, Math.min(1, n));
    out[p] = bd.lo + t * (bd.hi - bd.lo);
  }
  return out;
}

function defaultParams(b) {
  const out = {};
  for (const [n, bd] of Object.entries(b)) out[n] = (bd.lo + bd.hi) / 2;
  // LWL IS A MISSION NUMBER, NOT A SHAPE ONE. Seeding it from the box
  // midpoint would silently design a different boat from the one the brief
  // describes, and the mission parser already mis-reads lengths often enough
  // (an air draft has landed in `lwl_hint_m`) that the two must not disagree
  // quietly as well.
  const hint = S.mission?.lwl_hint_m;
  if (hint != null && b.LWL) {
    out.LWL = Math.min(b.LWL.hi, Math.max(b.LWL.lo, Number(hint)));
  }
  return out;
}

/** SEED THE GENOME FROM THE COMPILED BOX, NOT FROM THE GRAMMAR MIDPOINT.
 *
 *  MEASURED while wiring the Digital twin: opening #/twin directly on a fresh
 *  project reported `roundness 0.5000` — a radiused bilge — on a project whose
 *  own constitution clips roundness to exactly [0, 0]. `ui/server.eval_payload`
 *  merges the caller's params over the GRAMMAR midpoint, which is the right
 *  default for the engineer's page and the wrong one here: it silently
 *  evaluated a hull the envelope forbids, and the unroller would then have
 *  refused it at the shop door with no explanation the user could connect to
 *  anything they did.
 *
 *  So every screen that consumes `S.params` seeds them through here first. */
export async function ensureParams() {
  if (!S.mission) return S.params;
  await ensureEnvelope();
  const b = bounds();
  const base = defaultParams(b);
  const out = { ...base };
  for (const [k, v] of Object.entries(S.params || {})) {
    const bd = b[k]; if (!bd) continue;
    out[k] = Math.min(bd.hi, Math.max(bd.lo, Number(v)));   // clip, never drop
  }
  S.params = out;
  return S.params;
}

export async function ensureEnvelope() {
  if (S.envelope) return S.envelope;
  S.envelope = await post("/api/envelope",
    { category: S.mission?.design_category || "C" });
  return S.envelope;
}

export async function evaluateNow() {
  const t0 = performance.now();
  const out = await post("/eval", { params: S.params, mission: S.mission });
  S.evalMs = performance.now() - t0;
  S.evalOut = out;
  touchProject({ params: { ...S.params } });
  emit();
  return out;
}

/* ================================================================ PROJECTS */

export async function projects(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "projects"),
    el("h1", {}, "Boats you are working on")));
  host.append(el("p", { class: "lede" },
    "A project holds a mission, a genome and everything measured about it. "
    + "It lives in this browser: there is no project store in the backend, "
    + "and inventing one here would make the mission exist in two places."));

  const form = el("div", { class: "card stack-s" });
  form.append(el("h3", {}, "start a new one"));
  const name = el("input", { type: "text", placeholder: "e.g. Danube liveaboard" });
  form.append(name);
  form.append(el("div", { class: "row" },
    el("button", {
      class: "act",
      onclick: () => {
        const id = "p" + Date.now().toString(36);
        S.projects.unshift({
          id, name: name.value.trim() || "untitled boat",
          created: Date.now(), updated: Date.now(),
          params: {}, mission: null, missionText: "", missionLocked: false,
          requirements: []
        });
        saveProjects(); openProject(id); location.hash = "#/mission";
      }
    }, "create project")));
  host.append(form);

  if (!S.projects.length) {
    host.append(el("div", { class: "note", style: "margin-top:14px" },
      el("span", { class: "lbl" }, "what happens next"),
      el("p", {}, "You describe the boat in one sentence. Naval-AI compiles "
        + "that into a legal envelope, generates hull candidates inside it, "
        + "runs the physics ladder, and either hands you a cut file or tells "
        + "you — with the measurement — why it will not.")));
    return;
  }
  const t = el("div", { class: "tbl", style: "margin-top:14px" });
  const tb = el("tbody");
  for (const p of [...S.projects].sort((a, b) => b.updated - a.updated)) {
    tb.append(el("tr", { class: p.id === S.pid ? "sel" : "" },
      el("td", {}, el("a", {
        href: "#/mission",
        onclick: () => openProject(p.id)
      }, p.name)),
      el("td", { class: "mono mini" }, p.mission
        ? `${fmt(p.mission.displacement_target_kg, 0)} kg · `
          + `${fmt(p.mission.cruise_speed_kn, 1)} kn · cat `
          + p.mission.design_category
        : "no mission"),
      el("td", {}, p.missionLocked
        ? el("span", { class: "chip pass" }, "🔒 locked")
        : el("span", { class: "chip warn" }, "draft")),
      el("td", { class: "mono mini" }, new Date(p.updated).toLocaleString()),
      el("td", {}, el("button", {
        class: "act danger",
        onclick: () => {
          if (!confirm("delete " + p.name + "?")) return;
          S.projects = S.projects.filter(x => x.id !== p.id);
          if (S.pid === p.id) S.pid = null;
          saveProjects(); location.reload();
        }
      }, "delete"))));
  }
  t.append(el("table", {},
    el("thead", {}, el("tr", {},
      el("th", {}, "project"), el("th", {}, "brief"), el("th", {}, "state"),
      el("th", {}, "updated"), el("th", {}, ""))),
    tb));
  host.append(t);
}

/* ================================================================= MISSION */

const PRESETS = [
  ["Comfortable cruising",
   "8 tonne solar-electric liveaboard, 11 m, Danube and Black Sea coastal, "
   + "cruise 5 knots, 4 crew"],
  ["Efficient exploration",
   "6 tonne solar-electric monohull, 10 m, coastal, cruise 5 knots, 2 crew"],
  ["Fast coastal",
   "3 tonne dayboat, 8 m, coastal, cruise 9 knots, 4 crew"],
  ["Utility / workboat",
   "5 tonne utility launch, 9 m, river, cruise 6 knots, 2 crew"],
  ["Long-range solar",
   "7 tonne solar-electric monohull, 12 m, coastal, cruise 4 knots, 2 crew"]
];

export async function mission(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "design · step 1"),
    el("h1", {}, "Tell us about the boat")));
  host.append(el("p", { class: "lede" },
    "In your own words. We will read it back before anything is committed — "
    + "the parser is keyword-based and it fails SILENTLY in ways that matter, "
    + "so free text seeds the form and never commits it."));

  const ta = el("textarea", { rows: 3 }, S.missionText
    || "Monohull, 4–6 people, solar, 1-tonne battery, 3 m total height, "
     + "stitch-and-glue plywood, Danube and Black Sea");
  host.append(el("div", { class: "card stack-s" },
    el("h3", {}, "the brief"), ta,
    el("div", { class: "row" },
      ...PRESETS.map(([n, txt]) => el("button", {
        class: "ghost", onclick: () => { ta.value = txt; }
      }, n)),
      el("button", { class: "ghost" }, "Custom")),
    el("div", { class: "row" },
      el("button", { class: "act", onclick: parse }, "read it back →"))));

  const out = el("div", { class: "stack", style: "margin-top:14px" });
  host.append(out);
  if (S.mission) render(S.mission);

  async function parse() {
    S.missionText = ta.value;
    const m = await post("/mission", { text: ta.value });
    S.mission = m; S.envelope = null;
    touchProject({ mission: m, missionText: ta.value });
    emit(); render(m);
  }

  function render(m) {
    out.textContent = "";
    out.append(el("div", { class: "card" },
      el("h3", {}, "here's what we understood — tap any line to correct it"),
      el("div", { class: "cols c3" },
        field("where", m.waters + " → design category " + m.design_category,
          "category sets the GM floor and the bottom plate thickness"),
        field("people", String(m.crew), "crew mass and the offset-load test"),
        field("all-up weight", fmt(m.displacement_target_kg, 0) + " kg",
          "the hull is floated to THIS mass"),
        field("cruise speed", fmt(m.cruise_speed_kn, 1) + " kn",
          "sets the Froude number every model is judged against"),
        field("waterline length",
          m.lwl_hint_m == null ? "not stated — we will choose it"
                               : fmt(m.lwl_hint_m, 2) + " m",
          "if a stray number landed here, fix it: '3 m total height' has "
          + "been read as a 3 m boat"),
        field("battery", (m.energy?.battery_kwh != null
          ? fmt(m.energy.battery_kwh, 1) + " kWh" : "default"),
          "energy store, not payload"))));

    const notes = (m.notes || "").split(";").map(s => s.trim()).filter(Boolean);
    if (notes.length) {
      out.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "we couldn't use these — set them by hand"),
        el("ul", { style: "margin:6px 0 0 16px" },
          ...notes.map(n => el("li", { style: "font-size:.83rem" }, n)))));
    }
    out.append(absentTile("air_draft"));

    out.append(el("div", { class: "row" },
      el("button", {
        class: "act",
        onclick: () => { location.hash = "#/requirements"; }
      }, "continue to requirements →"),
      el("span", { class: "mini" },
        "nothing is locked until you lock the brief on the envelope screen")));
  }
}

function field(k, v, why) {
  return el("div", { class: "q", "data-basis": "measured" },
    el("div", { class: "qname" }, k),
    el("div", { class: "qval", style: "font-size:.95rem" }, v),
    el("div", { class: "qband", style: "white-space:normal" }, why));
}

/* ============================================================ REQUIREMENTS */

/* CONSTRAINT CLASSIFICATION, AND THE ONE THING IT MUST NOT PRETEND.
 * HARD constraints are the rows the ladder can actually FAIL a design on —
 * there are exactly eight, plus whatever the constitution appends. SOFT
 * constraints are the objectives NSGA-II minimises — there are exactly three.
 * A requirement that maps to neither is NOT ENFORCED, and this screen says so
 * in those words instead of storing it and implying it will be honoured. */
const HARD_ROWS = {
  freeboard: ["stability", "the deck edge stays above water at the solved attitude"],
  gm: ["stability", "metacentric height against the category floor"],
  bend_radius: ["buildability", "can the required plywood bend that tight"],
  trim: ["stability", "bow-up / bow-down angle at rest"],
  list: ["stability", "transverse heel from an off-centre mass"],
  lcb: ["performance", "longitudinal centre of buoyancy against its band"],
  proportions: ["dimensions", "L/B and B/T inside their sourced bands"],
  rules: ["materials", "the ISO 12215 / 12217 assessment rows"]
};
const SOFT_OBJECTIVES = [
  ["energy", "Wh per nautical mile", "minimised — objective 1"],
  ["build", "shell + deck area (m²)", "minimised — objective 2, the proxy for cost"],
  ["stability", "|GM − band centre|", "minimised — GM is a BAND, not a maximisation"]
];

export async function requirements(host) {
  const p = project();
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "design · step 2"),
    el("h1", {}, "Requirements")));
  host.append(el("p", { class: "lede" },
    "A hard requirement rejects designs. A soft one becomes something the "
    + "search trades against. Everything here names the row or the objective "
    + "that carries it — a requirement with neither cannot be enforced, and "
    + "this screen refuses to imply otherwise."));

  const m = S.mission;
  const mset = el("div", { class: "card stack-s" });
  mset.append(el("h3", {}, "mission numbers — these drive everything downstream"));
  const grid = el("div", { class: "cols c3" });
  const editable = [
    ["displacement_target_kg", "all-up mass", "kg", 0],
    ["cruise_speed_kn", "cruise speed", "kn", 1],
    ["lwl_hint_m", "waterline length", "m", 2],
    ["crew", "crew", "people", 0]
  ];
  for (const [k, label, unit, dp] of editable) {
    const inp = el("input", {
      type: "number", step: dp ? Math.pow(10, -dp) : 1,
      value: m[k] == null ? "" : m[k],
      onchange: e => {
        const v = e.target.value === "" ? null : Number(e.target.value);
        S.mission = { ...S.mission, [k]: v };
        S.envelope = null;
        touchProject({ mission: S.mission }); emit(); toast(label + " → " + v);
      }
    });
    grid.append(el("label", { class: "stack-s" },
      el("span", { class: "mini" }, label.toUpperCase() + " · " + unit), inp));
  }
  const cat = el("select", {
    onchange: e => {
      S.mission = { ...S.mission, design_category: e.target.value };
      S.envelope = null; touchProject({ mission: S.mission }); emit();
      toast("category " + e.target.value + " — GM floor and plate thickness move");
    }
  }, ...["A", "B", "C", "D"].map(c =>
    el("option", { value: c, selected: m.design_category === c }, "category " + c)));
  grid.append(el("label", { class: "stack-s" },
    el("span", { class: "mini" }, "DESIGN CATEGORY"), cat));
  mset.append(grid);
  host.append(mset);

  host.append(el("h2", { style: "margin:20px 0 6px" }, "HARD — these reject a design"));
  host.append(el("p", { class: "mini", style: "margin-bottom:8px" },
    "Exactly " + Object.keys(HARD_ROWS).length + " rows, and that is the "
    + "complete set of things this platform can fail a design on. There is no "
    + "ninth. A compiled constitution APPENDS rows; it never rewrites one."));
  const rs = el("div", { class: "tbl" });
  const body = el("tbody");
  for (const [row, [cat2, what]] of Object.entries(HARD_ROWS)) {
    body.append(el("tr", {},
      el("td", { class: "mono" }, row),
      el("td", {}, cat2),
      el("td", {}, what),
      el("td", {}, el("span", { class: "chip fail" }, "HARD"))));
  }
  for (const r of (S.envelope?.rows || [])) {
    body.append(el("tr", {},
      el("td", { class: "mono" }, r),
      el("td", {}, "governance"),
      el("td", {}, "appended by the compiled constitution — cannot be switched off"),
      el("td", {}, el("span", { class: "chip fail" }, "HARD"))));
  }
  rs.append(el("table", {}, el("thead", {}, el("tr", {},
    el("th", {}, "row"), el("th", {}, "category"), el("th", {}, "what it asks"),
    el("th", {}, "class"))), body));
  host.append(rs);

  host.append(el("h2", { style: "margin:20px 0 6px" }, "SOFT — these are traded"));
  host.append(el("div", { class: "cols c3" },
    ...SOFT_OBJECTIVES.map(([id, label, note]) =>
      el("div", { class: "card" },
        el("h3", {}, id),
        el("p", { style: "font-size:.88rem" }, label),
        el("p", { class: "mini", style: "margin-top:4px" }, note)))));

  host.append(el("div", { class: "note", style: "margin-top:16px" },
    el("span", { class: "lbl" }, "requirements with nowhere to land"),
    el("p", {}, "Cost, air draft, motion in a chop and noise are all things a "
      + "builder asks for and none of them has a row or an objective in this "
      + "tree. They are listed on the screens where they would appear, "
      + "hatched, with what would close them. Storing them here as if they "
      + "were enforced would be worse than not offering them.")));

  host.append(el("div", { class: "row", style: "margin-top:14px" },
    el("button", {
      class: "act", onclick: () => { location.hash = "#/envelope"; }
    }, "compile the envelope →")));
}

/* ================================================================ ENVELOPE */

export async function envelope(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "design · step 3"),
    el("h1", {}, "Your envelope")));
  const e = await ensureEnvelope();
  if (e.source !== "measured") {
    host.append(el("div", { class: "note refuse" },
      el("span", { class: "lbl" }, "the constitution did not compile"),
      el("p", {}, e.reason || "unknown")));
    return;
  }
  const narrowed = e.edits.length;
  host.append(el("p", { class: "lede" },
    "Your answers moved " + narrowed + " bound"
    + (narrowed === 1 ? "" : "s") + " inward. What is left is legal, "
    + "buildable by your method, and floats what you are carrying. This is a "
    + "BOUND, not a filter: the search never spends an evaluation outside it."));
  host.append(el("p", { class: "mini", style: "margin:-10px 0 14px" },
    "The box is now " + e.volume_fraction.toExponential(2) + " of the "
    + "ungoverned hyper-box by volume — but read that as what it is: "
    + e.volume_note + ". Sixteen span ratios multiplied together make a very "
    + "small number out of a very ordinary narrowing, and quoting it as a "
    + "percentage of \"the search space\" would be exactly the fake precision "
    + "this product exists to avoid."));

  const b = bounds();
  const card = el("div", { class: "card" });
  card.append(el("h3", {}, "was  →  is now"));
  for (const n of e.names) {
    const bd = b[n];
    const span = bd.uhi - bd.ulo || 1;
    const l = (bd.lo - bd.ulo) / span * 100, r = (bd.hi - bd.ulo) / span * 100;
    const clipped = bd.clipped;
    card.append(el("div", { class: "slab" },
      el("div", { class: "lab" },
        el("span", {}, n + (bd.unit && bd.unit !== "-" ? " · " + bd.unit : "")),
        el("span", { class: "rd" },
          clipped ? fmt(bd.lo, 2) + " – " + fmt(bd.hi, 2)
                  : "unchanged " + fmt(bd.lo, 2) + " – " + fmt(bd.hi, 2))),
      el("div", { class: "ghosttrack" },
        el("i", { class: "legal",
          style: `left:${l}%;width:${Math.max(0.6, r - l)}%` })),
      el("div", { class: "ends" },
        el("span", {}, fmt(bd.ulo, 2)), el("span", {}, fmt(bd.uhi, 2)))));
  }
  host.append(card);

  if (e.edits.length) {
    const t = el("div", { class: "tbl", style: "margin-top:14px" });
    t.append(el("table", {}, el("thead", {}, el("tr", {},
      el("th", {}, "parameter"), el("th", {}, "edge"),
      el("th", { class: "num" }, "was"), el("th", { class: "num" }, "now"),
      el("th", {}, "why — the source, verbatim"))),
      el("tbody", {}, ...e.edits.map(x => el("tr", {},
        el("td", { class: "mono" }, x.param),
        el("td", { class: "mono" }, x.edge),
        el("td", { class: "num" }, fmt(x.was, 3)),
        el("td", { class: "num" }, fmt(x.now, 3)),
        el("td", { style: "font-size:.78rem" }, x.source))))));
    host.append(el("h2", { style: "margin:18px 0 6px" }, "Why it narrowed"));
    host.append(el("p", { class: "mini", style: "margin-bottom:8px" },
      "Every move is recorded as a BoxEdit. A policy may only move a bound "
      + "INWARD and may only APPEND a constraint row — a floor that would "
      + "loosen a limits.py bar raises at compile time, and so does one "
      + "exactly equal to it."));
    host.append(t);
  }

  host.append(el("div", { class: "note bind", style: "margin-top:14px" },
    el("span", { class: "lbl" }, "the measurement behind this screen"),
    el("p", {}, "Sampling WITHOUT the compiled box produced roundness > 0 on "
      + "60 of 60 draws and the unroller refused all 60 — the search was "
      + "ranking a design space that was 100% unbuildable in plywood. With "
      + "the box, 30 of 30 unrolled. Governance here is not paperwork; it is "
      + "the difference between searching a real space and a fictional one.")));

  if (e.rows.length) {
    host.append(el("div", { class: "note", style: "margin-top:12px" },
      el("span", { class: "lbl" }, "⚑ extra checks added to your boat"),
      el("p", {}, e.rows.join(" · ")
        + " — appended to the eight base rows. They live in the studio and "
        + "cannot be switched off.")));
  }
  host.append(el("p", { class: "mini", style: "margin-top:10px" }, e.disclaimer));

  host.append(el("div", { class: "row", style: "margin-top:16px" },
    el("button", {
      class: "act",
      onclick: () => {
        S.missionLocked = true;
        touchProject({ missionLocked: true }); emit();
        toast("brief locked — the hash rides every later screen");
        location.hash = "#/hull";
      }
    }, S.missionLocked ? "re-lock and open the studio →" : "lock the brief →"),
    el("span", { class: "mini" },
      "locking freezes the mission that every later measurement is judged against")));
}

/* ================================================================== STUDIO */

export async function hull(host) {
  host.className = "screen flush";
  await ensureParams();
  const b = bounds();
  const p = project();
  const u = p.behaviour || Object.fromEntries(BEHAVIOUR.map(c => [c.id, 0.5]));
  let expert = !!p.expert;

  const wrap = el("div", { class: "studio" });
  const left = el("div", { class: "pane left stack-s" });
  const stage = el("div", { class: "stage" });
  const right = el("div", { class: "pane right stack-s" });
  wrap.append(left, stage, right);
  host.append(wrap);
  host.append(el("div", { class: "no-studio", style: "padding:22px" },
    el("div", { class: "note" },
      el("span", { class: "lbl" }, "shaping needs a bigger screen"),
      el("p", {}, "Nobody lofts a boat on a phone, and a degraded control "
        + "surface at this size produces hulls someone unpicks on a laptop "
        + "afterwards. The mission, the reality check and the build package "
        + "all work here — the sliders do not."))));

  /* ---- stage --------------------------------------------------------- */
  const bar = el("div", { class: "stage-bar" });
  const canvas = el("canvas");
  const foot = el("div", { class: "stage-foot" }, "—");
  stage.append(bar, canvas, foot);
  const vp = new Viewport(canvas);
  const seg = el("div", { class: "seg" });
  for (const [id, lab] of [["3d", "3D"], ["profile", "PROFILE"],
                           ["plan", "PLAN"], ["body", "BODY"]]) {
    seg.append(el("button", {
      class: id === "3d" ? "on" : "",
      onclick: e => {
        [...seg.children].forEach(c => c.classList.remove("on"));
        e.target.classList.add("on"); vp.setMode(id);
      }
    }, lab));
  }
  bar.append(seg, el("span", { style: "flex:1" }),
    el("button", {
      class: "ghost",
      onclick: () => { expert = !expert; touchProject({ expert }); drawLeft(); }
    }, "⚙ expert"));

  /* ---- the two-rate render loop (PU-2) -------------------------------- */
  let pending = null, fineTimer = null, gen = 0;
  async function refresh(fast) {
    const my = ++gen;
    try {
      const [ev, mesh, secs] = await Promise.all([
        post("/eval", { params: S.params, mission: S.mission }),
        post("/api/mesh", { params: S.params, fidelity: fast ? "fast" : "fine" }),
        fast ? Promise.resolve(vp.sections)
             : post("/api/sections", { params: S.params, n: 13 })
      ]);
      if (my !== gen) return;                     // a newer frame won
      S.evalOut = ev; S.evalMs = ev.eval_ms; emit();
      const wl = ev.quantities ? waterlineZ(ev) : null;
      vp.setMesh(mesh, { stale: fast, wl, trim: 0 });
      if (!fast && secs) vp.setSections(secs);
      foot.textContent =
        `eval ${fmt(ev.eval_ms, 2)} ms · ${fast ? "panel_mesh" : "closed_mesh"} `
        + `${fmt(mesh.gen_ms, 2)} ms · ${mesh.verts.length} verts · `
        + `${mesh.faces.length} faces`;
      drawRight();
    } catch (e) {
      // THE STAGE REPORTS ITS OWN FAILURE. Until 2026-08-23 this line was the
      // only evidence a request had failed, and it is 11px of mono text under
      // a canvas -- so a 400 from /api/mesh read as an empty screen. See
      // docs/audit/I13-SESSION-2026-08-23.md: a participant lost a session to
      // exactly this, in two browsers, with the cause sitting in the response
      // body the whole time.
      if (my !== gen) return;
      vp.setError(e.message);
      foot.textContent = "refresh failed: " + e.message;
    }
  }
  function schedule() {
    touchProject({ params: { ...S.params }, behaviour: { ...u } });
    if (pending) return;
    pending = requestAnimationFrame(() => { pending = null; refresh(true); });
    clearTimeout(fineTimer);
    fineTimer = setTimeout(() => refresh(false), 260);
  }

  function waterlineZ(ev) {
    // The hull mesh is in keel-origin coordinates and `panel_mesh` cuts at
    // z = 0, which IS the design waterline. Drawing it there is a fact about
    // the mesh, not an assumption about the float.
    return 0;
  }

  /* ---- left pane: shape ---------------------------------------------- */
  function drawLeft() {
    left.textContent = "";
    left.append(el("div", { class: "rail-group", style: "padding-left:0" },
      expert ? "GRAMMAR — 16 PARAMETERS" : "SHAPE"));
    if (expert) {
      left.append(el("p", { class: "mini" },
        "The engineer's surface. Same /eval, same constraint rows, no second "
        + "code path — that is what makes the six-slider abstraction "
        + "trustworthy rather than a wall."));
      for (const [n, bd] of Object.entries(b)) {
        left.append(rawSlider(n, bd));
      }
    } else {
      for (const ctl of BEHAVIOUR) left.append(behaviourSlider(ctl));
      left.append(el("div", { class: "note", style: "margin-top:10px" },
        el("span", { class: "lbl" }, "length comes from your brief"),
        el("p", {}, "LWL " + (S.mission?.lwl_hint_m == null
          ? "is being chosen inside the envelope"
          : fmt(S.mission.lwl_hint_m, 2) + " m")
          + ". Change it on the Requirements screen, where changing it also "
          + "recompiles the envelope.")));
    }
    left.append(buildMeter());
  }

  function behaviourSlider(ctl) {
    const slab = el("div", { class: "slab" });
    const rd = el("span", { class: "rd" }, Math.round((u[ctl.id] ?? 0.5) * 100) + "%");
    slab.append(el("div", { class: "lab" }, el("span", {}, ctl.label), rd));
    const inp = el("input", {
      type: "range", min: 0, max: 1, step: 0.01, value: u[ctl.id] ?? 0.5,
      oninput: e => {
        u[ctl.id] = Number(e.target.value);
        rd.textContent = Math.round(u[ctl.id] * 100) + "%";
        Object.assign(S.params, behaviourToParams(u, b));
        schedule();
      }
    });
    slab.append(inp);
    slab.append(el("div", { class: "ends" },
      el("span", {}, ctl.lo), el("span", {}, ctl.hi)));
    slab.append(el("div", { class: "mini" }, ctl.feel));
    if (ctl.absent) {
      const a = (S.manifest?.absent || {})[ctl.absent];
      slab.append(el("div", { class: "lockwhy" }, "🔒",
        el("span", {}, (a ? a.what : ctl.locked)
          + " — the grammar cannot draw it, so this control ships short of "
          + "the range you might expect. It is not hidden; it does not exist.")));
    }
    const pinned = Object.keys(ctl.drives).filter(k => b[k]
      && Math.abs(b[k].hi - b[k].lo) < 1e-9);
    if (pinned.length) {
      slab.classList.add("locked");
      slab.append(el("div", { class: "lockwhy" }, "🔒",
        el("span", {}, pinned.join(", ") + " is pinned by your build method — "
          + "the compiled box clipped it to a single value.")));
    }
    return slab;
  }

  function rawSlider(n, bd) {
    const slab = el("div", { class: "slab" });
    const rd = el("span", { class: "rd" }, fmt(S.params[n], 3));
    slab.append(el("div", { class: "lab" },
      el("span", { title: bd.desc }, n), rd));
    if (bd.clipped) {
      const span = bd.uhi - bd.ulo || 1;
      slab.append(el("div", { class: "ghosttrack" },
        el("i", { class: "legal", style:
          `left:${(bd.lo - bd.ulo) / span * 100}%;`
          + `width:${Math.max(0.6, (bd.hi - bd.lo) / span * 100)}%` })));
    }
    const step = (bd.hi - bd.lo) / 200 || 0.001;
    slab.append(el("input", {
      type: "range", min: bd.lo, max: bd.hi, step,
      value: Math.min(bd.hi, Math.max(bd.lo, S.params[n] ?? (bd.lo + bd.hi) / 2)),
      disabled: bd.hi - bd.lo < 1e-12,
      oninput: e => {
        S.params[n] = Number(e.target.value);
        rd.textContent = fmt(S.params[n], 3);
        schedule();
      }
    }));
    slab.append(el("div", { class: "ends" },
      el("span", {}, fmt(bd.lo, 2)), el("span", {}, bd.unit || ""),
      el("span", {}, fmt(bd.hi, 2))));
    if (bd.clipped && bd.edits?.length) {
      slab.append(el("div", { class: "lockwhy" }, "🔒",
        el("span", {}, bd.edits[bd.edits.length - 1].source.slice(0, 150) + "…")));
    }
    return slab;
  }

  /* ---- buildability meter, directly under the sliders that break it --- */
  function buildMeter() {
    const box = el("div", { class: "card sunk", style: "margin-top:6px" });
    box.append(el("h3", {}, "buildability"));
    const bar2 = el("div", { class: "bar" });
    const txt = el("div", { class: "mini" }, "not measured yet");
    box.append(bar2, txt);
    const btn = el("button", {
      class: "act", style: "margin-top:8px",
      onclick: async () => {
        btn.disabled = true; txt.textContent = "measuring the family…";
        try {
          S.refold = await post("/api/refold", { params: S.params });
          paint();
        } catch (e) { txt.textContent = "refused: " + e.message; }
        btn.disabled = false;
      }
    }, "measure refold  (~12 s) →");
    box.append(btn);
    box.append(el("p", { class: "mini", style: "margin-top:6px" },
      "A family, not one number. 3° of flare alone moved refold error from "
      + "~4.7 mm to 26.8 mm against a 5 mm bar — you have to feel that in the "
      + "same gesture that causes it."));
    function paint() {
      const r = S.refold; if (!r) return;
      // A MEASUREMENT NAMES ITS DESIGN, AND THE BOX BELIEVES THE NAME.
      // Until 2026-09-03 this box painted whatever S.refold held: measure
      // hull A, drag a slider to hull B, and hull A's refold verdict kept
      // rendering under hull B's viewport. /eval//mesh//sections had a
      // generation counter; refold had nothing. The server now stamps
      // every derived payload with the canonical genome hash (`design`),
      // so staleness is an IDENTITY comparison, not a timing guess — and
      // the stale result is KEPT and labelled, never silently deleted:
      // evidence about the previous revision is still evidence.
      const cur = S.evalOut && S.evalOut.design;
      if (r.design && cur && r.design !== cur) {
        bar2.textContent = ""; bar2.append(el("i", { class: "warn",
          style: "width:100%;opacity:.35" }));
        txt.textContent = "STALE — measured for a previous hull revision. "
          + "Re-measure for this hull.";
        return;
      }
      if (r.source === "refused") {
        bar2.textContent = ""; bar2.append(el("i", { class: "fail",
          style: "width:100%" }));
        txt.textContent = "REFUSED — " + r.reason; return;
      }
      const bar_mm = r.bar_mm, worst = r.worst_mm?.[r.worst_mm.length - 1];
      const frac = worst == null ? 0 : Math.min(1, bar_mm / Math.max(worst, 1e-9));
      bar2.textContent = "";
      bar2.append(el("i", {
        class: r.verdict === "PASSES" ? "pass"
             : r.verdict === "REFINING" ? "warn" : "fail",
        style: `width:${(frac * 100).toFixed(0)}%`
      }));
      txt.textContent = r.verdict + " · "
        + (r.counts || []).map((c, i) => `n=${c} ${fmt(r.worst_mm[i], 1)}`).join(" · ")
        + ` mm  (bar ${fmt(bar_mm, 1)} mm)`;
    }
    if (S.refold) paint();
    sub(paint);          // hull edits emit(); the meter re-judges identity
    return box;
  }

  /* ---- right pane: vitals -------------------------------------------- */
  function drawRight() {
    right.textContent = "";
    const ev = S.evalOut;
    right.append(el("div", { class: "rail-group", style: "padding-left:0" },
      "VITALS"));
    if (!ev) { right.append(el("p", { class: "mini" }, "evaluating…")); return; }
    const q = ev.quantities || {};
    right.append(el("div", { class: "stack-s" },
      qbadge("displacement", q.displacement_kg, { unit: "kg", dp: 0 }),
      qbadge("GM", q.GM_m, { unit: "m", dp: 2 }),
      qbadge("freeboard", q.freeboard_m, { unit: "m", dp: 2 }),
      qbadge("resistance", q.Rt_N, { unit: "N", dp: 1 }),
      qbadge("energy", q.wh_per_nm, { unit: "Wh/nm", dp: 0 }),
      qbadge("solar day", q.solar_kwh_day, { unit: "kWh", dp: 1 }),
      qbadge("solar range", q.range_solar_nm_day, { unit: "nm/day", dp: 1 }),
      qbadge("block coeff", q.cb, { dp: 3 })));
    right.append(el("div", { class: "rail-group", style: "padding-left:0" },
      ev.ok ? "ALL ROWS SATISFIED" : "ROWS VIOLATED"));
    right.append(el("div", { class: ev.ok ? "chip pass" : "chip fail" },
      el("i", { class: "dot " + (ev.ok ? "pass" : "fail") }),
      ev.ok ? "feasible at L1" : ev.violations.length + " violation(s)"));
    if (!ev.ok) {
      right.append(el("ul", { style: "margin:6px 0 0 15px" },
        ...ev.violations.map(v =>
          el("li", { style: "font-size:.76rem;color:var(--fail)" }, v))));
    }
    if (ev.weights_kg) {
      const tot = ev.weights_kg.total?.value || 0;
      const un = ev.weights_kg.unaccounted?.value || 0;
      const frac = tot > 0 ? 1 - un / tot : 0;
      right.append(el("div", { class: "card sunk", style: "margin-top:8px" },
        el("h3", {}, "mass accounted for"),
        el("div", { class: "bar" },
          el("i", { class: frac > 0.8 ? "pass" : "warn",
                    style: `width:${(frac * 100).toFixed(0)}%` })),
        el("p", { class: "mini", style: "margin-top:4px" },
          (frac * 100).toFixed(0) + "% accounted · " + fmt(un, 0)
          + " kg NOT YET ACCOUNTED FOR. Every check above rests on this. "
          + "It is listed, never absorbed into a margin.")));
    }
    right.append(el("div", { class: "row", style: "margin-top:8px" },
      el("a", { href: "#/reality", class: "chip" }, "reality check →"),
      el("a", { href: "#/build", class: "chip" }, "build →")));
  }

  drawLeft();
  refresh(false);
}

/* =========================================================== BUILDABILITY */

export async function buildability(host) {
  host.append(el("div", { class: "head" },
    el("span", { class: "eyebrow" }, "design · buildability"),
    el("h1", {}, "Can this be cut from flat sheet?")));
  host.append(el("p", { class: "lede" },
    "The verdict is the DIRECTION, not the value. A shortfall that FALLS "
    + "under refinement is the station polyline's sagitta — a measurement "
    + "artefact. One that RISES is double curvature — a property of the boat. "
    + "Only the second is a reason to change the hull."));

  const out = el("div", { class: "stack" });
  host.append(el("div", { class: "row" },
    el("button", {
      class: "act",
      onclick: async () => {
        out.textContent = "";
        out.append(el("p", { class: "mini" },
          el("span", { class: "spin" }), " measuring the station family…"));
        S.refold = await post("/api/refold", { params: S.params });
        render();
      }
    }, "measure the family  (~12 s)"),
    el("span", { class: "mini" },
      "runs the unroller at 41 / 81 / 161 stations — three full developable "
      + "unwraps against the hull sampled at 4001 stations")),
    out);
  if (S.refold) render();

  function render() {
    const r = S.refold;
    out.textContent = "";
    // same identity rule as the studio's buildability meter — see paint()
    const cur = S.evalOut && S.evalOut.design;
    if (r.design && cur && r.design !== cur) {
      out.append(el("div", { class: "note" },
        el("span", { class: "lbl" }, "STALE"),
        el("p", {}, "This refold family was measured for a previous hull "
          + "revision. The numbers below are kept as evidence about that "
          + "revision — re-measure for the current hull."),
      ));
    }
    if (r.source === "refused") {
      out.append(el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "REFUSED"),
        el("p", {}, r.reason),
        el("p", { class: "mini", style: "margin-top:6px" },
          "This is the unroller refusing at the shop door, which is the last "
          + "possible honest moment. A radiused bilge is not a two-panel "
          + "developable shell — the governance box exists to keep the "
          + "search out of that region in the first place.")));
      return;
    }
    const cls = r.verdict === "PASSES" ? "pass"
      : r.verdict === "REFINING" ? "warn" : "fail";
    out.append(el("div", { class: "spread" },
      el("span", { class: "chip " + cls },
        el("i", { class: "dot " + cls }), r.verdict),
      el("span", { class: "mini" }, "bar " + fmt(r.bar_mm, 1) + " mm · measured in "
        + fmt(r.elapsed_ms, 0) + " ms")));
    out.append(el("p", {}, r.verdict_meaning));

    const pts = (r.counts || []).map((c, i) => [c, r.worst_mm[i]]);
    out.append(el("div", { class: "card" },
      el("h3", {}, "refold deviation against station count"),
      linechart({
        series: [{ name: "worst deviation", pts, color: "var(--copper)", dots: true },
                 { name: "bar", pts: pts.map(p => [p[0], r.bar_mm]),
                   color: "var(--pass)" }],
        xlab: "stations", ylab: "mm", h: 200
      }),
      el("p", { class: "mini", style: "margin-top:6px" },
        "ratios " + (r.ratios || []).map(x => fmt(x, 3)).join(" · ")
        + (r.order != null ? " · observed order " + fmt(r.order, 2)
                           : " · order not named (ratios too uneven)"))));

    out.append(el("div", { class: "note " + (cls === "fail" ? "refuse" : "bind") },
      el("span", { class: "lbl" }, "route: " + r.route.toUpperCase()),
      el("p", {}, r.route === "kit"
        ? "Flat panels, stitched and glued. The download gate can open."
        : r.route === "search"
        ? "Part of this shortfall is the measurement, not the boat. Refine "
          + "before routing to a mould."
        : "Your panels will not lie flat. Forced onto a sheet and bent back "
          + "to shape they miss the hull. Cut this as a kit and the seams "
          + "will not close."),
      r.route === "mould" ? el("p", { class: "mini", style: "margin-top:8px" },
        "Finding a cuttable version is a SEARCH, not a switch: only 3 of 400 "
        + "random hulls clear the 5 mm bar, and a local search seeded 120 mm "
        + "away did not reach it in 900 s. When it finds one it costs "
        + "something — measured, on one brief: 59 → 121 plywood sheets, "
        + "1825 → 3679 build hours, 412 → 595 Wh/nm, GM 0.82 → 2.55 m.")
        : null));

    out.append(el("div", { class: "row" },
      el("a", { class: "act", href: "#/build" }, "open the build package →")));
  }
}
