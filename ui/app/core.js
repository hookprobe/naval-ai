/* Core: transport, state, and the two components every screen is built from.
 *
 * THE COMPONENT THAT MATTERS IS `qbadge`. Everything else here is plumbing.
 * `docs/BUILDER-UX.html` §00: colour on `basis`, NEVER on `tier`. A badge that
 * reads `tier` paints `freeboard_m` (sigma hard-coded 0.02) and the solar pair
 * (sigma typed as x0.25 / x0.35 in the server) as confident L1 green, and
 * `SIGMA_PLACEHOLDER` — documented in `navalai/energy.py` as "no input sigma
 * was supplied — DO NOT USE" — as green too. So `qbadge` switches on `basis`
 * and refuses to render a value it was not given.
 */

/* --------------------------------------------------------------- transport */
export async function get(path) {
  const r = await fetch(path);
  const t = await r.text();
  let j; try { j = JSON.parse(t); } catch { throw new Error(t.slice(0, 300)); }
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}
export async function post(path, body) {
  const r = await fetch(path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {})
  });
  const t = await r.text();
  let j; try { j = JSON.parse(t); } catch { throw new Error(t.slice(0, 300)); }
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

/* ------------------------------------------------------------------- state */
/* One store, persisted to localStorage. A "project" is a mission plus a
 * genome plus whatever has been measured about it — it is NOT a server
 * resource, because there is no project store in the backend and inventing
 * one in the UI would be a second home for the mission. */
const KEY = "navalai.projects.v1";

export const S = {
  projects: [], pid: null, manifest: null, level: 1,
  params: {}, mission: null, missionText: "", missionLocked: false,
  envelope: null, evalOut: null, evalMs: null,
  refold: null, capsize: null, build: null, sweep: null,
  pareto: null, search: null, compare: [],
  _subs: new Set()
};

export function sub(fn) { S._subs.add(fn); return () => S._subs.delete(fn); }
export function emit() { for (const f of S._subs) { try { f(); } catch (e) { console.error(e); } } }

export function project() { return S.projects.find(p => p.id === S.pid) || null; }

export function loadProjects() {
  try { S.projects = JSON.parse(localStorage.getItem(KEY) || "[]"); }
  catch { S.projects = []; }
  const last = localStorage.getItem(KEY + ".last");
  if (last && S.projects.some(p => p.id === last)) S.pid = last;
}
export function saveProjects() {
  try {
    localStorage.setItem(KEY, JSON.stringify(S.projects));
    if (S.pid) localStorage.setItem(KEY + ".last", S.pid);
  } catch { /* private mode: the session still works, it just will not persist */ }
}
export function touchProject(patch) {
  const p = project(); if (!p) return;
  Object.assign(p, patch, { updated: Date.now() });
  saveProjects();
}
export function openProject(id) {
  const p = S.projects.find(x => x.id === id); if (!p) return;
  S.pid = id;
  S.params = { ...(p.params || {}) };
  S.mission = p.mission || null;
  S.missionText = p.missionText || "";
  S.missionLocked = !!p.missionLocked;
  S.envelope = null; S.evalOut = null; S.refold = null; S.capsize = null;
  S.build = null; S.sweep = null; S.pareto = null;
  saveProjects(); emit();
}

/* ------------------------------------------------------------- formatting */
export const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : String(v));
  }
  for (const k of kids.flat()) {
    if (k == null || k === false) continue;
    n.append(k.nodeType ? k : document.createTextNode(String(k)));
  }
  return n;
};
export const esc = s => String(s ?? "").replace(/[&<>"]/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function fmt(v, dp = 2) {
  if (v == null || !isFinite(v)) return "—";
  const a = Math.abs(v);
  if (a !== 0 && (a < 1e-3 || a >= 1e6)) return v.toExponential(2);
  return v.toFixed(dp);
}

/** Scientific notation ONLY where it earns its place. A coefficient of
 *  3.711e-3 wants it; a friction fraction of 0.904 printed as 9.0400e-1 is
 *  fake precision dressed as rigour. */
export function sci(v, dp = 4) {
  if (v == null || !isFinite(v)) return "—";
  const a = Math.abs(v);
  return (a !== 0 && (a < 0.01 || a >= 1e5))
    ? v.toExponential(dp) : v.toFixed(dp);
}
export function toast(msg, ms = 2600) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.classList.add("on");
  clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove("on"), ms);
}

/* ------------------------------------------------------- QUANTITY BADGE --- */
const GLYPH = {
  measured: "●", propagated: "●", "propagated-lower-bound": "▲",
  assumed: "◆", placeholder: "▨", absent: "▨", refused: "✕"
};
const BASIS_HELP = {
  measured: "propagated from the model that produced the value",
  propagated: "propagated from the model that produced the value",
  "propagated-lower-bound":
    "a propagated LOWER bound — the truth is worse than this, not better",
  assumed: "the band is a declared fraction of the value. It is a decoration, "
         + "not an uncertainty, and it says so",
  placeholder: "no input sigma reached the propagation. navalai/energy.py "
             + "documents this as: DO NOT USE",
  absent: "not measured. Deliberately left empty rather than filled with a "
        + "plausible number",
  refused: "non-finite — refused. A NaN is a refusal, not a number"
};

/** q: {value, tier, sigma, basis, state} as `ui/server._q` puts it on the wire.
 *  Pass `{basis:"absent"}` for a capability the backend does not have. */
export function qbadge(name, q, opts = {}) {
  const unit = opts.unit || "";
  const basis = q?.state ? "refused" : (q?.basis || "absent");
  const n = el("div", { class: "q", "data-basis": basis,
                        title: BASIS_HELP[basis] || basis });
  n.append(el("div", { class: "qname" },
    el("span", { class: "glyph" }, GLYPH[basis] || "▨"), name));
  let val;
  if (basis === "refused") val = q.state;
  else if (q?.value == null) val = opts.absentText || "no value";
  else val = fmt(q.value, opts.dp ?? 2) + (unit ? " " + unit : "");
  n.append(el("div", { class: "qval" }, val));
  const bits = [];
  if (q?.sigma != null && q.value != null) {
    bits.push((basis === "propagated-lower-bound" ? "≥ ±" : "±")
      + fmt(q.sigma, opts.dp ?? 2));
  }
  if (q?.tier) bits.push(q.tier);
  if (basis === "placeholder") bits.push("no band");
  if (opts.sub) bits.push(opts.sub);
  n.append(el("div", { class: "qband" }, bits.join("  ") || basis));
  return n;
}

/** An absence, rendered as an absence. Reads the server's ABSENT registry so
 *  the reason is never typed into the markup — the day the backend grows the
 *  capability, this tile disappears with it. */
export function absentTile(key, extra) {
  const a = (S.manifest?.absent || {})[key];
  if (!a) return el("div", { class: "hatched" },
    el("h3", {}, "NOT MEASURED"), el("p", { class: "mini" }, key));
  return el("div", { class: "hatched stack-s" },
    el("h3", {}, "▨ " + a.what.toUpperCase() + " — NOT MEASURED"),
    el("p", { class: "mini" }, a.why),
    el("p", { class: "mini" }, "What would close it: " + a.unblocked_by),
    extra || null);
}

/* -------------------------------------------------- CONSTRAINT ROW LIGHT --- */
/* `g <= 0` is satisfied; the value is the normalised margin, so 0 is exactly
 * at the limit. The bar shows HEADROOM — full bar means at the limit — which
 * is what links a slider to the thing it is about to break. */
export function constraintRow(name, g, why) {
  // THE BAR IS HEADROOM, AND THE DIRECTION MATTERS MORE THAN IT LOOKS.
  // `g <= 0` is satisfied and 0 is exactly at the limit, so the natural
  // rendering — fill proportional to |g| toward the limit — draws a FULL bar
  // for the safest row and an empty one for the row about to fail. A builder
  // reads a full bar as good. So the fill is the headroom REMAINING: full is
  // comfortable, empty is at the limit, and a violation is red and full.
  const bad = g > 0;
  const head = Math.max(0, Math.min(1, -g));       // 1 at g=-1, 0 at the limit
  const frac = bad ? 1 : head;
  const cls = bad ? "bad" : (head < 0.2 ? "near" : "ok");
  const r = el("div", { class: "crow " + cls });
  r.append(el("div", { class: "cn" }, name.replace(/_/g, " ")));
  r.append(el("div", { class: "cv" },
    bad ? "VIOLATED by " + fmt(g, 3)
        : (head * 100).toFixed(0) + "% headroom  ·  margin " + fmt(g, 3)));
  const t = el("div", { class: "track" });
  t.append(el("i", { class: "fill", style: `width:${(frac * 100).toFixed(1)}%` }));
  r.append(t);
  if (why) r.append(el("div", { class: "why" }, why));
  return r;
}

/* ---------------------------------------------------------------- charts --- */
/* Inline SVG, no library. Engineering plots: real axes, real units, and a
 * REFUSED band drawn as a refusal rather than as a faded curve. */
export function linechart(opts) {
  const { w = 520, h = 210, series = [], xlab = "", ylab = "",
          bands = [], pad = { l: 46, r: 12, t: 10, b: 26 } } = opts;
  const all = series.flatMap(s => s.pts);
  if (!all.length) return el("div", { class: "muted" }, "no points");
  const xs = all.map(p => p[0]), ys = all.map(p => p[1]);
  const x0 = opts.x0 ?? Math.min(...xs), x1 = opts.x1 ?? Math.max(...xs);
  const y0 = opts.y0 ?? Math.min(0, Math.min(...ys));
  const y1 = opts.y1 ?? Math.max(...ys) * 1.05;
  const X = v => pad.l + (v - x0) / ((x1 - x0) || 1) * (w - pad.l - pad.r);
  const Y = v => h - pad.b - (v - y0) / ((y1 - y0) || 1) * (h - pad.t - pad.b);
  const P = [];
  for (const b of bands) {
    P.push(`<rect x="${X(b.x0)}" y="${pad.t}" width="${Math.max(0, X(b.x1) - X(b.x0))}"
      height="${h - pad.t - pad.b}" fill="var(--fail-bg)" opacity=".7"/>`);
    P.push(`<text x="${X(b.x0) + 5}" y="${pad.t + 12}" fill="var(--fail)">${esc(b.label)}</text>`);
  }
  for (let i = 0; i <= 4; i++) {
    const v = y0 + (y1 - y0) * i / 4;
    P.push(`<line class="gridline" x1="${pad.l}" x2="${w - pad.r}" y1="${Y(v)}" y2="${Y(v)}"/>`);
    P.push(`<text x="4" y="${Y(v) + 3}">${fmt(v, Math.abs(v) < 10 ? 2 : 0)}</text>`);
  }
  for (let i = 0; i <= 5; i++) {
    const v = x0 + (x1 - x0) * i / 5;
    P.push(`<text x="${X(v)}" y="${h - 8}" text-anchor="middle">${fmt(v, 1)}</text>`);
  }
  for (const s of series) {
    if (s.fill) {
      const up = s.pts.map(p => `${X(p[0])},${Y(p[1] + (p[2] || 0))}`).join(" ");
      const dn = [...s.pts].reverse().map(p => `${X(p[0])},${Y(p[1] - (p[2] || 0))}`).join(" ");
      P.push(`<polygon points="${up} ${dn}" fill="${s.color}" opacity=".14"/>`);
    }
    P.push(`<polyline fill="none" stroke="${s.color}" stroke-width="1.6"
      points="${s.pts.map(p => `${X(p[0])},${Y(p[1])}`).join(" ")}"/>`);
    if (s.dots) for (const p of s.pts)
      P.push(`<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="2.4" fill="${s.color}"/>`);
  }
  P.push(`<line class="axis" x1="${pad.l}" x2="${w - pad.r}" y1="${h - pad.b}" y2="${h - pad.b}"/>`);
  P.push(`<line class="axis" x1="${pad.l}" x2="${pad.l}" y1="${pad.t}" y2="${h - pad.b}"/>`);
  P.push(`<text x="${w - pad.r}" y="${h - 8}" text-anchor="end">${esc(xlab)}</text>`);
  P.push(`<text x="4" y="${pad.t + 2}">${esc(ylab)}</text>`);
  const box = el("div");
  box.innerHTML = `<svg viewBox="0 0 ${w} ${h}" width="100%"
     style="max-width:${w}px;display:block">${P.join("")}</svg>`;
  if (series.length > 1) {
    box.append(el("div", { class: "row", style: "margin-top:4px" },
      ...series.map(s => el("span", { class: "mini" },
        el("span", { style: `color:${s.color}` }, "── "), s.name))));
  }
  return box;
}
