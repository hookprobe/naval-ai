"""Provenance DB (BuildPlan Phase 0): every genome, every result, reproducible.

SQLite here (single-node prototype); the schema is deliberately PostgreSQL-
compatible so the swap is a connection string, not a redesign. Rules:
  - a hull is content-addressed by the SHA-256 of its CANONICAL parameter
    vector, and the canonical vector is what the row stores (see `canonical`)
  - every result row carries solver name+version, fidelity tier, uncertainty,
    and the code version that produced it
  - rows are append-only; re-runs append, never overwrite (honest history)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

import numpy as np

from . import __version__

SCHEMA = """
CREATE TABLE IF NOT EXISTS hull (
    hull_id TEXT PRIMARY KEY,          -- sha256 of canonical param json
    params_json TEXT NOT NULL,
    grammar_version TEXT NOT NULL,
    created_utc REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hull_id TEXT NOT NULL REFERENCES hull(hull_id),
    tier TEXT NOT NULL,                -- L0 | L1 | L2 | L3 | R (rules)
    solver TEXT NOT NULL,              -- e.g. 'michell+ittc57', 'capytaine'
    solver_version TEXT NOT NULL,
    quantity TEXT NOT NULL,            -- e.g. 'Rt_N@2.5m/s', 'GM_m'
    value REAL,
    uncertainty REAL,                  -- one-sigma, same units; NULL = unknown
    meta_json TEXT,                    -- mesh hash, grid, convergence info
    code_version TEXT NOT NULL,
    created_utc REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_result_hull ON result(hull_id, tier, quantity);
"""


# Decimals the content address is computed at. It lives here ONCE because it
# defines what "the same hull" means, and the id and the stored payload must
# agree about that or the address does not address the content.
CANON_DECIMALS = 10


def canonical(params: np.ndarray) -> list[float]:
    """The canonical form of a parameter vector: what gets hashed AND stored.

    THE ADDRESS AND THE PAYLOAD MUST BE THE SAME OBJECT (gap E9).
    `hull_id` hashed `round(v, 10)` while `add_hull` stored the RAW floats under
    `INSERT OR IGNORE`, so two vectors agreeing to 10 decimals shared one id and
    the FIRST one to arrive kept the row. MEASURED on the reference hull with
    LWL 10.0 vs 10.00000000001: identical 24-hex id, and `get_params` returned
    the earlier vector — the provenance DB, which is the evidence graph the
    whole honesty argument rests on, handed back a design that did not produce
    the results filed against it. A content address that does not address the
    stored content is worse than no address, because nothing downstream can
    tell. Storing the canonical form makes the collision a true identity: the
    two vectors are the same hull *by the definition the id uses*, and the row
    is that hull.
    """
    return [round(float(v), CANON_DECIMALS) + 0.0 for v in np.asarray(params).ravel()]


def hull_id(params: np.ndarray) -> str:
    return hashlib.sha256(
        json.dumps(canonical(params)).encode()).hexdigest()[:24]


class Provenance:
    def __init__(self, path: str | Path = "data/navalai.sqlite3"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(path))
        self.con.executescript(SCHEMA)

    def add_hull(self, params: np.ndarray, grammar_version: str = "chine-v1") -> str:
        # Store the SAME canonical vector that was hashed — see `canonical`.
        # `INSERT OR IGNORE` is only honest once these two agree: ignoring the
        # second insert is then discarding a byte-identical row, not silently
        # preferring whichever of two different designs arrived first.
        hid = hull_id(params)
        self.con.execute(
            "INSERT OR IGNORE INTO hull VALUES (?,?,?,?)",
            (hid, json.dumps(canonical(params)), grammar_version, time.time()),
        )
        self.con.commit()
        return hid

    def add_result(self, hid: str, tier: str, solver: str, solver_version: str,
                   quantity: str, value: float, uncertainty: float | None = None,
                   meta: dict | None = None) -> None:
        self.con.execute(
            "INSERT INTO result (hull_id,tier,solver,solver_version,quantity,"
            "value,uncertainty,meta_json,code_version,created_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (hid, tier, solver, solver_version, quantity, value, uncertainty,
             json.dumps(meta or {}), __version__, time.time()),
        )
        self.con.commit()

    def results(self, hid: str, tier: str | None = None) -> list[tuple]:
        q = "SELECT tier,solver,quantity,value,uncertainty,meta_json FROM result WHERE hull_id=?"
        args: list = [hid]
        if tier:
            q += " AND tier=?"
            args.append(tier)
        return list(self.con.execute(q, args))

    def get_params(self, hid: str) -> np.ndarray:
        row = self.con.execute(
            "SELECT params_json FROM hull WHERE hull_id=?", (hid,)).fetchone()
        if row is None:
            raise KeyError(hid)
        return np.array(json.loads(row[0]))

    def training_matrix(self, tier: str, quantity: str):
        """(X, y) of all hulls having a result for (tier, quantity) — flywheel feed."""
        rows = list(self.con.execute(
            "SELECT h.params_json, r.value FROM result r JOIN hull h "
            "ON h.hull_id = r.hull_id WHERE r.tier=? AND r.quantity=? "
            "AND r.value IS NOT NULL", (tier, quantity)))
        if not rows:
            return np.empty((0, 0)), np.empty(0)
        X = np.array([json.loads(p) for p, _ in rows])
        y = np.array([v for _, v in rows])
        return X, y
