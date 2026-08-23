/* The viewport: 3D hull, and the three blueprint projections beside it.
 *
 * NO 3D LIBRARY. The mesh is quads from `Hull.panel_mesh()` — measured at
 * 1.66 ms for ~464 faces — so a painter's-algorithm rasteriser in canvas 2D
 * draws it comfortably inside a frame, and a WebGL dependency would buy
 * nothing that this hull needs. The strict CSP on a published artifact and
 * the offline-by-default posture of a loopback server both argue the same way.
 *
 * THE TWO-RATE LOOP (PU-2) LIVES IN THE CALLER, NOT HERE. Measured on the Mac
 * node: evaluate() 11.35 ms, panel_mesh() 1.66 ms, closed_mesh() 49.75 ms,
 * unroll.hull_panels() 869 ms. So the studio draws the FAST mesh while a
 * slider is moving and settles to the fine one on release; the unroller is
 * never in the loop at all. This module just renders what it is handed and
 * reports what it cost.
 *
 * THE HULL IS THE TRIM INDICATOR. The backend solves sinkage and trim
 * simultaneously, so the waterline is drawn at the SOLVED attitude and the
 * numeric readout confirms it rather than leading it.
 */

export class Viewport {
  constructor(canvas) {
    this.c = canvas;
    this.ctx = canvas.getContext("2d");
    this.mesh = null;          // {verts, faces, edges}
    this.wl = null;            // solved waterline z (m)
    this.trim = 0;             // solved trim (deg)
    this.mode = "3d";
    this.yaw = -0.62; this.pitch = 0.36; this.zoom = 1;
    this.sections = null;
    this.stale = false;        // true while showing the fast mesh
    this.error = null;         // a refusal from the backend, DRAWN not hidden
    this._drag = null;
    canvas.addEventListener("pointerdown", e => {
      this._drag = { x: e.clientX, y: e.clientY };
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener("pointermove", e => {
      if (!this._drag) return;
      this.yaw += (e.clientX - this._drag.x) * 0.008;
      this.pitch = Math.max(-1.3, Math.min(1.3,
        this.pitch + (e.clientY - this._drag.y) * 0.006));
      this._drag = { x: e.clientX, y: e.clientY };
      this.draw();
    });
    canvas.addEventListener("pointerup", () => { this._drag = null; });
    canvas.addEventListener("wheel", e => {
      e.preventDefault();
      this.zoom = Math.max(0.35, Math.min(4, this.zoom * (e.deltaY > 0 ? 0.92 : 1.08)));
      this.draw();
    }, { passive: false });
    this._ro = new ResizeObserver(() => this.draw());
    this._ro.observe(canvas);
  }

  setMesh(m, opts = {}) {
    this.mesh = m;
    this.error = null;
    this.stale = !!opts.stale;
    if (opts.wl !== undefined) this.wl = opts.wl;
    if (opts.trim !== undefined) this.trim = opts.trim || 0;
    this.draw();
  }
  /* A FAILED MESH IS DRAWN, NOT SWALLOWED.
   *
   * MEASURED 2026-08-23 in the I13 usability session
   * (docs/audit/I13-SESSION-2026-08-23.md): POST /api/mesh returned 400 on
   * every request, and the ONLY place that said so was one line of small mono
   * text under the canvas whose resting value is an em dash. The participant
   * saw an empty stage in two browsers, asked "was it supposed to be like
   * this?", and the session was lost there. The observer needed source-reading
   * and curl to find a cause the server already knew and had put in the
   * response body.
   *
   * So the refusal goes where the hull would have been. */
  setError(msg) { this.error = msg || null; this.draw(); }
  setSections(s) { this.sections = s; this.draw(); }
  setMode(m) { this.mode = m; this.draw(); }

  _css(v) {
    return getComputedStyle(document.body).getPropertyValue(v).trim() || "#888";
  }

  _fit() {
    const c = this.c, dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth, h = c.clientHeight;
    if (c.width !== w * dpr || c.height !== h * dpr) {
      c.width = Math.max(1, w * dpr); c.height = Math.max(1, h * dpr);
    }
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { w, h };
  }

  draw() {
    const { w, h } = this._fit();
    const g = this.ctx;
    g.clearRect(0, 0, w, h);
    g.fillStyle = this._css("--sunk"); g.fillRect(0, 0, w, h);
    this._grid(g, w, h);
    if (this.error) { this._drawError(g, w, h); return; }
    if (!this.mesh) {
      g.fillStyle = this._css("--ink-3");
      g.font = "12px ui-monospace, monospace";
      g.fillText("no geometry — evaluate a hull", 16, 26);
      return;
    }
    if (this.mode === "3d") this._draw3d(g, w, h);
    else this._drawOrtho(g, w, h);
    if (this.stale) {
      g.fillStyle = this._css("--copper");
      g.font = "10px ui-monospace, monospace";
      g.fillText("FAST MESH · settling", 12, h - 12);
    }
  }

  _drawError(g, w, h) {
    const pad = 22, maxw = Math.max(120, w - pad * 2);
    g.fillStyle = this._css("--fail");
    g.font = "600 13px ui-monospace, monospace";
    g.fillText("THIS HULL COULD NOT BE DRAWN", pad, pad + 14);
    g.fillStyle = this._css("--ink-2");
    g.font = "12px ui-monospace, monospace";
    // wrap the backend's own words; it already said what is wrong
    const words = String(this.error).split(/\s+/);
    let line = "", y = pad + 40;
    for (const word of words) {
      const trial = line ? line + " " + word : word;
      if (g.measureText(trial).width > maxw && line) {
        g.fillText(line, pad, y); y += 17; line = word;
      } else line = trial;
      if (y > h - 34) break;
    }
    if (line && y <= h - 34) { g.fillText(line, pad, y); y += 17; }
    g.fillStyle = this._css("--ink-3");
    g.font = "11px ui-monospace, monospace";
    g.fillText("the geometry kernel refused these numbers — change a slider",
               pad, Math.min(h - 14, y + 10));
  }

  _grid(g, w, h) {
    g.strokeStyle = this._css("--rule-2"); g.lineWidth = 1;
    g.globalAlpha = 0.5;
    for (let x = 0; x < w; x += 46) { g.beginPath(); g.moveTo(x + .5, 0); g.lineTo(x + .5, h); g.stroke(); }
    for (let y = 0; y < h; y += 46) { g.beginPath(); g.moveTo(0, y + .5); g.lineTo(w, y + .5); g.stroke(); }
    g.globalAlpha = 1;
  }

  _bounds(V) {
    let lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    for (const v of V) for (let i = 0; i < 3; i++) {
      if (v[i] < lo[i]) lo[i] = v[i];
      if (v[i] > hi[i]) hi[i] = v[i];
    }
    return { lo, hi, c: lo.map((l, i) => (l + hi[i]) / 2),
             span: Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) || 1 };
  }

  /* ------------------------------------------------------------------ 3D */
  _draw3d(g, w, h) {
    const V = this.mesh.verts, F = this.mesh.faces;
    const b = this._bounds(V);
    const s = (Math.min(w, h) * 0.72 / b.span) * this.zoom;
    const cy = Math.cos(this.yaw), sy = Math.sin(this.yaw);
    const cp = Math.cos(this.pitch), sp = Math.sin(this.pitch);
    // Trim is applied as a rotation about the transverse axis through the
    // centre — the boat sits at the attitude the equilibrium solver found.
    const ct = Math.cos(this.trim * Math.PI / 180), st = Math.sin(this.trim * Math.PI / 180);
    const proj = v => {
      let x = v[0] - b.c[0], y = v[1] - b.c[1], z = v[2] - b.c[2];
      const x2 = x * ct - z * st, z2 = x * st + z * ct; x = x2; z = z2;
      const X = x * cy - y * sy, Y = x * sy + y * cy;
      const Z = z;
      return [w / 2 + X * s, h / 2 - (Z * cp - Y * sp) * s, Y * cp + Z * sp];
    };
    const P = V.map(proj);
    // SHADE ON THE SURFACE NORMAL, NOT ON DEPTH. A depth ramp makes every
    // hull look like the same loaf; a normal makes the chine, the flare and
    // the deadrise legible, which is the entire reason this viewport exists
    // rather than a table of coefficients. One fixed light, no specular, no
    // shadows — nothing here is claiming to be a render.
    const L = (() => { const v = [-0.45, -0.35, 0.82];
      const n = Math.hypot(...v); return v.map(c => c / n); })();
    const faces = [];
    for (const f of F) {
      let d = 0; for (const i of f) d += P[i][2];
      const a = V[f[0]], b1 = V[f[1]], c1 = V[f[f.length - 1]];
      const u = [b1[0] - a[0], b1[1] - a[1], b1[2] - a[2]];
      const v2 = [c1[0] - a[0], c1[1] - a[1], c1[2] - a[2]];
      let nx = u[1] * v2[2] - u[2] * v2[1],
          ny = u[2] * v2[0] - u[0] * v2[2],
          nz = u[0] * v2[1] - u[1] * v2[0];
      const nl = Math.hypot(nx, ny, nz) || 1;
      nx /= nl; ny /= nl; nz /= nl;
      const lam = Math.abs(nx * L[0] + ny * L[1] + nz * L[2]);
      faces.push([d / f.length, f, lam]);
    }
    faces.sort((a, c2) => a[0] - c2[0]);
    const hull = this._css("--accent"), edge = this._css("--rule");
    for (const [d, f, lam] of faces) {
      g.beginPath();
      g.moveTo(P[f[0]][0], P[f[0]][1]);
      for (let i = 1; i < f.length; i++) g.lineTo(P[f[i]][0], P[f[i]][1]);
      g.closePath();
      g.fillStyle = this._mix(hull, 0.22 + 0.78 * lam);
      g.fill();
      g.strokeStyle = edge; g.lineWidth = 0.25;
      g.globalAlpha = 0.55; g.stroke(); g.globalAlpha = 1;
    }
    // The characteristic curves, over the shaded shell. These are the lines a
    // builder actually reads a hull by, and they come from `edge_curves()` —
    // evaluated analytically, not picked out of the mesh.
    const E = this.mesh.edges || {};
    for (const [key, col, wdt] of [["keel", "--ink-2", 1.4],
                                   ["chine", "--copper", 1.8],
                                   ["sheer", "--ink", 1.4]]) {
      const pts = E[key]; if (!pts || !pts.length) continue;
      for (const sgn of [1, -1]) {
        g.strokeStyle = this._css(col); g.lineWidth = wdt;
        g.beginPath();
        pts.forEach((q, i) => {
          const pr = proj([q[0], sgn * q[1], q[2]]);
          i ? g.lineTo(pr[0], pr[1]) : g.moveTo(pr[0], pr[1]);
        });
        g.stroke();
        if (key === "keel") break;                 // the keel is on centreline
      }
    }
    // The design waterline, sized to the BOAT. A plane drawn to the scene
    // bounds dominates the picture and says nothing extra.
    if (this.wl != null) {
      const rx = (b.hi[0] - b.lo[0]) * 0.60, ry = (b.hi[1] - b.lo[1]) * 1.15;
      const corners = [[-rx, -ry], [rx, -ry], [rx, ry], [-rx, ry]]
        .map(([a, c2]) => proj([b.c[0] + a, b.c[1] + c2, this.wl]));
      g.beginPath(); g.moveTo(corners[0][0], corners[0][1]);
      corners.slice(1).forEach(p => g.lineTo(p[0], p[1]));
      g.closePath();
      g.strokeStyle = this._css("--copper"); g.lineWidth = 1;
      g.globalAlpha = 0.75; g.setLineDash([6, 5]); g.stroke();
      g.setLineDash([]); g.globalAlpha = 1;
    }
    this._legend(g, w, h, ["orbit: drag   ·   zoom: wheel",
      "copper = chine" + (this.wl != null ? "   ·   copper dash = waterline"
                                          : "   ·   no waterline solved")]);
  }

  _mix(hex, t) {
    // hex may be a css var value like "#63ACCE"
    const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
    if (!m) return hex;
    const n = parseInt(m[1], 16);
    const r = Math.round(((n >> 16) & 255) * t), gg = Math.round(((n >> 8) & 255) * t),
      b = Math.round((n & 255) * t);
    return `rgb(${r},${gg},${b})`;
  }

  /* ------------------------------------------- profile / plan / body plan */
  _drawOrtho(g, w, h) {
    const S = this.sections;
    const pad = 34;
    const ink = this._css("--ink-2"), acc = this._css("--accent"),
      cop = this._css("--copper"), dim = this._css("--ink-3");
    g.lineWidth = 1.2;
    if (this.mode === "body") {
      if (!S) return this._msg(g, "body plan needs station offsets");
      let ymax = 0, zlo = 1e9, zhi = -1e9;
      for (const sec of S.sections) for (const p of sec.pts) {
        ymax = Math.max(ymax, Math.abs(p[0])); zlo = Math.min(zlo, p[1]); zhi = Math.max(zhi, p[1]);
      }
      const sc = Math.min((w / 2 - pad) / (ymax || 1), (h - 2 * pad) / ((zhi - zlo) || 1));
      const cx = w / 2, cz = h - pad;
      const Y = v => cx + v * sc, Z = v => cz - (v - zlo) * sc;
      g.strokeStyle = dim; g.beginPath();
      g.moveTo(cx, pad); g.lineTo(cx, h - pad); g.stroke();
      S.sections.forEach((sec, i) => {
        // forward stations to starboard, aft to port — the convention a
        // body plan is read in
        const fwd = sec.x > S.lwl / 2, sign = fwd ? 1 : -1;
        g.strokeStyle = fwd ? acc : ink;
        g.beginPath();
        sec.pts.forEach((p, k) => {
          const X = Y(sign * Math.abs(p[0])), ZZ = Z(p[1]);
          k ? g.lineTo(X, ZZ) : g.moveTo(X, ZZ);
        });
        g.stroke();
      });
      if (this.wl != null && this.wl >= zlo && this.wl <= zhi) {
        g.strokeStyle = cop; g.setLineDash([5, 4]); g.beginPath();
        g.moveTo(pad, Z(this.wl)); g.lineTo(w - pad, Z(this.wl)); g.stroke();
        g.setLineDash([]);
      }
      this._legend(g, w, h, ["body plan", "fwd stations right (accent)",
        "aft left", "copper dash = waterline"]);
      return;
    }
    if (!S) return this._msg(g, "profile / plan need station offsets");
    const xs = S.keel.map(p => p[0]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    if (this.mode === "profile") {
      const zs = S.keel.map(p => p[1]).concat(S.sheer.map(p => p[2]));
      const zlo = Math.min(...zs), zhi = Math.max(...zs);
      const sc = Math.min((w - 2 * pad) / ((x1 - x0) || 1), (h - 2 * pad) / ((zhi - zlo) || 1));
      const X = v => pad + (v - x0) * sc, Z = v => h - pad - (v - zlo) * sc;
      const line = (pts, col, ix, iz) => {
        g.strokeStyle = col; g.beginPath();
        pts.forEach((p, k) => k ? g.lineTo(X(p[ix]), Z(p[iz])) : g.moveTo(X(p[ix]), Z(p[iz])));
        g.stroke();
      };
      line(S.keel, ink, 0, 1);
      line(S.chine, acc, 0, 2);
      line(S.sheer, ink, 0, 2);
      if (this.wl != null) {
        g.strokeStyle = cop; g.setLineDash([5, 4]); g.beginPath();
        g.moveTo(pad, Z(this.wl)); g.lineTo(w - pad, Z(this.wl)); g.stroke();
        g.setLineDash([]);
      }
      this._legend(g, w, h, ["profile", "accent = chine", "copper = waterline"]);
      return;
    }
    // plan
    let ymax = 0;
    for (const p of S.sheer) ymax = Math.max(ymax, Math.abs(p[1]));
    const sc = Math.min((w - 2 * pad) / ((x1 - x0) || 1), (h / 2 - pad) / (ymax || 1));
    const X = v => pad + (v - x0) * sc, Y = v => h / 2 - v * sc;
    for (const [pts, col] of [[S.sheer, ink], [S.chine, acc]]) {
      for (const sgn of [1, -1]) {
        g.strokeStyle = col; g.beginPath();
        pts.forEach((p, k) => k ? g.lineTo(X(p[0]), Y(sgn * p[1]))
                                : g.moveTo(X(p[0]), Y(sgn * p[1])));
        g.stroke();
      }
    }
    g.strokeStyle = dim; g.setLineDash([2, 4]); g.beginPath();
    g.moveTo(pad, h / 2); g.lineTo(w - pad, h / 2); g.stroke(); g.setLineDash([]);
    this._legend(g, w, h, ["plan", "accent = chine", "outer = sheer"]);
  }

  _msg(g, s) {
    g.fillStyle = this._css("--ink-3");
    g.font = "12px ui-monospace, monospace"; g.fillText(s, 16, 26);
  }
  _legend(g, w, h, lines) {
    g.fillStyle = this._css("--ink-3");
    g.font = "10px ui-monospace, monospace";
    lines.forEach((s, i) => g.fillText(s, 12, 18 + i * 13));
  }
}
