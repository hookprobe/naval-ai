# Gap I13 — investigation, 2026-08-23

**State: OPEN. Not closable by an agent. Readiness now VERIFIED, which is the
part that was blocking and is no longer.**

I13 is Gate 4 clause 3: *"A designated non-expert produces a hull that passes
the full ladder unassisted."* It is a gap row
(`docs/GAP-REGISTER.md`), not a `Gate(...)` in `navalai/gates.py`, and
`scripts/reconcile_gaps.py:1379` is the checker.

## 1. The checker is a fabrication hazard, and that is the first finding

    Check("I13", "Gate 4 clause 3 has an artifact: a recorded non-expert "
                 "session producing a hull that passes the full ladder",
          lambda: has_code("tests/test_phase4.py", r"non-expert|unassisted"),
          gate="Gate 4"),

**The check greps a test file for a string.** Writing the word "non-expert" in
a comment in `tests/test_phase4.py` turns I13 green without any human ever
having used the system. A gap whose subject is a PERSON is being closed by a
regex over source code, which is the same defect class as the layer table that
reported the REQUESTED spec as achieved: the receipt does not measure the
thing it names.

This should be changed to test for the ARTEFACT — a session directory with a
transcript, metadata, a genome and a `certification.json` produced by the real
pipeline — before anyone tries to close it. Otherwise the first person to
close I13 will close it by accident.

## 2. Why this could not be closed in this session, despite a real non-expert

The project owner — a genuine non-naval-architect — supplied a plain-language
brief on 2026-08-23 (*16 x 4 x 3 m, 3 t, 100 kWh, 15 kW, 7-12 kn, houseboat
with living room, terrace, bathroom, kitchen*) and a hull was produced and put
through the real ladder (`docs/research/HOUSEBOAT-16M.md`). They then made the
fair observation that they are not a naval architect and had just specified a
hull.

**That is true, and it still is not an I13 session.** The contract's decisive
clauses are *"the participant must drive the NavalAI builder themselves"* and
*"the participant must interact with the actual NavalAI workflow/UI"*, and the
observer must not *design the hull for them*, *provide naval-architecture
answers*, or *operate the UI for them*. In that session an AI agent did all
three: it wrote the driver, chose Cp, `l_pmb`, deadrise and the arrangement,
ran a 10-point sweep, and explained hull speed, Froude number and the B/T band
before the participant ever met a system message. Every one of ~40 tool calls
is an observer intervention under the contract.

So the session answered a DIFFERENT question — *can a non-expert plus an
expert agent produce a validated hull?* (yes) — and not I13's, which is *can a
non-expert understand the system well enough to use it safely?* Declaring I13
green on it would be manufacturing evidence about a person, which
`docs/audit/STATUS.md` already warns against for this exact row.

## 3. What that session DOES provide: unfabricated evidence on vocabulary

This is real observational data and it is worth keeping, labelled for what it
is — mission comprehension only, not a usability session.

The brief contained **three terminology mismatches, all made by a real
non-expert, none of which the system would have caught:**

| the participant said | the system reads | consequence |
|---|---|---|
| "3 metres in height" | `D` = keel-to-sheer depth | 3.0 sits exactly on the gene ceiling and would pass SILENTLY as a 3 m deep canoe body with no cabin |
| "total displacement weight ~3 tonnes" | `displacement_target_kg` | off by ~4.7x; the 100 kWh battery alone is 750 kg. Refused, but only at B/T |
| "travel to around 7-12 knots" | `cruise_speed_kn`, one number | 7 kn is 9.0 kW; 12 kn is outside the L1 model entirely |

**The participant could not have self-diagnosed any of the three**, and two of
them (height, speed range) are not even representable in `MissionSpec`. That is
an I13-relevant finding about the mission front end: the vocabulary a customer
naturally uses does not map onto the contract, and the mismatch is silent.

## 4. Readiness: VERIFIED 2026-08-23, and this was worth checking first

A session cannot be booked against a broken build. Measured on this Mac:

    python -m ui.server            starts clean, port 8642
    GET  /                         200, 7.26 s FIRST load (startup prefit)
    POST /mission                  200, parses the I13 example mission:
                                   lwl_hint_m 8.0, crew 4, category C

So the builder UI is live and a real session is runnable now. Two notes for
the observer: the **7.3 s first page load** is startup work and will read as a
hang to a participant, and `POST /mission` returned `waters="river+coastal"`
— the DEFAULT — for a mission whose text said "inland", which is the defect in
`docs/research/HOUSEBOAT-16M.md` §5 arriving on the UI path too.

## 5. What a valid session requires, concretely

- A real non-naval-architect who has NOT seen this repository.
- 20-40 minutes, driving `http://127.0.0.1:8642` themselves.
- A plain-language mission handed over with NO naval architecture explained.
- An observer who logs and clarifies the TASK only — never a parameter, never
  a diagnosis, never the mouse. Every word of assistance recorded verbatim,
  because assistance is itself the finding.
- Evidence: transcript or screen recording, session metadata, the genome, a
  `certification.json` from the real pipeline, and the final pass/fail state.
- Failures and confusion PRESERVED. The UI is not fixed mid-session and the
  test is not re-run until someone passes.

The agent's role in a valid session is scribe and nothing else.

## 6. Recommended order

1. Fix the I13 checker (§1) so the row cannot close on a grep.
2. Run one real session (§5). One is enough; the gap asks for one.
3. Record it, pass or fail. A failed session is the valuable outcome and the
   contract says so.
