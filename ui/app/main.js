/* Shell: navigation, the hash router, and the three disclosure levels.
 *
 * L1 MISSION      — a builder who has never heard of a prismatic coefficient.
 * L2 ENGINEERING  — geometry, hydrostatics, resistance, optimisation.
 * L3 VALIDATION   — meshes, y+, convergence, benchmarks, provenance.
 *
 * The level does not hide a FAILURE and it does not hide an ABSENCE; it hides
 * DETAIL. A red gate, an unaccounted 3298 kg and an unvalidated model are
 * visible at L1, because the one thing this product must never do is get
 * quieter about bad news as the audience gets less expert.
 */
import { S, loadProjects, sub, emit, el, get, toast, project } from "./core.js";
import * as D from "./screens-design.js";
import * as A from "./screens-analysis.js";

const NAV = [
  ["PROJECTS", [
    ["projects", "All projects", 1]]],
  ["DESIGN", [
    ["mission", "Mission", 1],
    ["requirements", "Requirements", 1],
    ["envelope", "Envelope", 1],
    ["hull", "Hull studio", 1],
    ["buildability", "Buildability", 1]]],
  ["ANALYSIS", [
    ["reality", "Reality check", 1],
    ["hydrostatics", "Hydrostatics", 2],
    ["resistance", "Resistance & power", 2],
    ["cfd", "CFD workspace", 3]]],
  ["OPTIMIZATION", [
    ["search", "Population & search", 2],
    ["pareto", "Pareto front", 2],
    ["compare", "Compare designs", 2]]],
  ["VALIDATION", [
    ["validation", "Benchmarks & physics", 1],
    ["gates", "Gates & ledger", 3]]],
  ["FINAL DESIGN", [
    ["build", "Build package", 1],
    ["twin", "Digital twin", 2]]],
  ["SYSTEM", [
    ["system", "Models, solvers, data", 3]]]
];

const SCREENS = {
  projects: D.projects, mission: D.mission, requirements: D.requirements,
  envelope: D.envelope, hull: D.hull, buildability: D.buildability,
  reality: A.reality, hydrostatics: A.hydrostatics, resistance: A.resistance,
  cfd: A.cfd, search: A.search, pareto: A.pareto, compare: A.compare,
  validation: A.validation, gates: A.gates, build: A.build, twin: A.twin,
  system: A.system
};

const LEVEL_NAME = { 1: "L1 · MISSION", 2: "L2 · ENGINEERING", 3: "L3 · VALIDATION" };

function drawRail() {
  const rail = document.getElementById("rail");
  const here = (location.hash.slice(2) || "projects").split("/")[0];
  rail.textContent = "";
  for (const [group, items] of NAV) {
    const visible = items.filter(([, , lvl]) => lvl <= S.level);
    if (!visible.length) continue;
    rail.append(el("div", { class: "rail-group" }, group));
    for (const [id, label, lvl] of visible) {
      const needs = gateFor(id);
      rail.append(el("a", {
        href: "#/" + id,
        class: (id === here ? "on " : "") + (needs ? "blocked" : ""),
        title: needs || label
      }, label, lvl > 1 ? el("span", { class: "tag" }, "L" + lvl) : null));
    }
  }
}

/** What a screen needs before it can say anything true. Not a lock — the
 *  screen still opens and explains what is missing, because a disabled link
 *  teaches nothing. */
function gateFor(id) {
  if (id === "projects" || id === "system" || id === "validation"
      || id === "gates" || id === "cfd") return null;
  if (!project()) return "no project open";
  if (["hull", "buildability", "reality", "hydrostatics", "resistance",
       "build", "twin", "search", "pareto", "compare"].includes(id)
      && !S.mission) return "no mission parsed yet";
  return null;
}

/* ONE RENDER WINS. Screens are async, and there are three things that can
 * start a route at once: the direct call at boot, the `hashchange` that boot's
 * own `location.hash = ...` fires, and the re-route when the manifest lands.
 * MEASURED: the Digital twin rendered its header TWICE — two routes each
 * cleared the host, both awaited, and both appended. A generation token makes
 * every await point a place a stale render gives up. */
let _gen = 0;

async function route() {
  const my = ++_gen;
  const parts = (location.hash.slice(2) || "projects").split("/");
  const id = parts[0];
  const fn = SCREENS[id] || SCREENS.projects;
  const host = document.getElementById("screen");
  host.className = "screen";
  host.textContent = "";
  drawRail();
  const blocked = gateFor(id);
  if (blocked) {
    host.append(el("div", { class: "stack" },
      el("div", { class: "head" }, el("h1", {}, id)),
      el("div", { class: "note refuse" },
        el("span", { class: "lbl" }, "not ready"),
        el("p", {}, blocked + ". This screen would have to invent the missing "
          + "input to draw anything, so it does not."),
        el("p", { style: "margin-top:8px" },
          el("a", { href: "#/" + (project() ? "mission" : "projects") },
            project() ? "→ describe the mission" : "→ open or start a project")))));
    return;
  }
  try {
    // Any screen that reads the genome gets it seeded from the COMPILED BOX
    // first — see `ensureParams` for the measured incident.
    if (S.mission && !["projects", "mission", "system", "gates",
                       "validation", "cfd"].includes(id)) {
      await D.ensureParams();
      if (my !== _gen) return;
    }
    if (my !== _gen) return;
    await fn(host, parts.slice(1));
  } catch (e) {
    if (my !== _gen) return;
    console.error(e);
    host.append(el("div", { class: "note refuse" },
      el("span", { class: "lbl" }, "this screen failed"),
      el("p", {}, String(e.message || e)),
      el("p", { class: "mini", style: "margin-top:6px" },
        "The failure is shown rather than swallowed. A screen that renders "
        + "empty on an error is indistinguishable from one that measured "
        + "nothing.")));
  }
}

function chips() {
  const mc = document.getElementById("mission-chip");
  const p = project();
  if (!p) { mc.className = "chip unk"; mc.textContent = "no project"; return; }
  mc.className = "chip " + (S.missionLocked ? "pass" : "warn");
  mc.textContent = (S.missionLocked ? "🔒 " : "") + p.name
    + (S.mission ? "" : " · no mission");
  const ec = document.getElementById("eval-chip");
  ec.textContent = S.evalMs == null ? "— ms" : S.evalMs.toFixed(1) + " ms";
  ec.className = "chip " + (S.evalMs == null ? ""
    : S.evalMs < 100 ? "pass" : "warn");
  ec.title = "last evaluate() round trip. Gate 4's bar is 100 ms per widget "
    + "and tests/test_phase4.py enforces it.";
}

document.getElementById("level-btn").addEventListener("click", () => {
  S.level = S.level % 3 + 1;
  document.getElementById("level-btn").textContent = LEVEL_NAME[S.level];
  localStorage.setItem("navalai.level", String(S.level));
  drawRail();
  toast(S.level === 1 ? "L1 — mission language. Failures and absences stay visible."
    : S.level === 2 ? "L2 — engineering workspace."
    : "L3 — validation, provenance and solver detail.");
});

document.getElementById("theme-btn").addEventListener("click", () => {
  const now = document.documentElement.getAttribute("data-theme") === "dark"
    ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", now);
  localStorage.setItem("navalai.theme", now);
  emit();
});

window.addEventListener("hashchange", route);
sub(() => { chips(); drawRail(); });

/* A FAILURE MUST BE VISIBLE, INCLUDING ONE IN THIS FILE. A blank screen and
 * a screen that measured nothing look identical, and this product's whole
 * argument is that they must not. */
function fatal(what, e) {
  console.error(what, e);
  const host = document.getElementById("screen");
  if (!host) return;
  host.prepend(el("div", { class: "note refuse" },
    el("span", { class: "lbl" }, what),
    el("p", {}, String(e?.message || e)),
    el("p", { class: "mini", style: "margin-top:6px" },
      "Shown rather than swallowed.")));
}
window.addEventListener("error", e => fatal("uncaught error", e.error || e));
window.addEventListener("unhandledrejection", e => fatal("unhandled rejection",
  e.reason));

(function boot() {
  const th = localStorage.getItem("navalai.theme");
  if (th) document.documentElement.setAttribute("data-theme", th);
  S.level = Number(localStorage.getItem("navalai.level") || 1) || 1;
  document.getElementById("level-btn").textContent = LEVEL_NAME[S.level];
  loadProjects();
  const p = project();
  if (p) {
    S.params = { ...(p.params || {}) };
    S.mission = p.mission || null;
    S.missionText = p.missionText || "";
    S.missionLocked = !!p.missionLocked;
  }
  if (!location.hash) location.hash = "#/projects";
  // FIRST PAINT IS SYNCHRONOUS. The manifest is a fetch, and awaiting it
  // before drawing anything leaves the whole window empty for as long as the
  // backend takes — which is indistinguishable from a broken build.
  chips(); drawRail();
  get("/api/manifest").then(m => { S.manifest = m; route(); })
    .catch(e => {
      toast("backend unreachable: " + e.message, 8000);
      fatal("the backend did not answer /api/manifest", e);
      route();
    });
  route();
})();
