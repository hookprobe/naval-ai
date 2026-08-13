# Audit report: PHYSICS MODELS (agent D, 2026-08-14)

## MODEL-TABLE
Format: `calc @file:line — equation | inputs | outputs[units] | validity | consumers | verdict`

**resistance.py**
1. `michell_rw` @resistance.py:580 — R_w = 4rho g^2/(pi U^2) int |I(theta)|^2 sec^3 dtheta | xs,zs,Y grid, U, rho, n_theta, separation | R_w [N] | slender + Fn<=0.45 (enforced only in total_resistance via flow_regime, NOT in michell_rw itself) | total_resistance, free_wave_spectrum, separation_sweep, experiments | REAL; lambda<->theta equivalence proven in-file
2. `_theta_grid` :485 — theta = 0.5pi*0.998*s^0.7 | n_theta | theta, sec | theta0=2.484e-3 fixed for all n -> documented -0.25..-0.48% asymptotic deficit (CATAMARAN_ASYMPTOTIC_RESIDUAL=0.0049) | REAL but grid-truncated; mechanism identified, not fixed
3. `catamaran_interference` :519 — 4cos^2(k_y s/2), k_y=k0 sec^2 sin | k0, theta, s | factor [0,4] | thin-ship; n_theta >= 880*max(1,s/Lwl) ENFORCED (raises) | REAL, exact within thin-ship
4. `bow_wave_rise` :763 — U^2/(2g) | U | rise [m] | stagnation UPPER bound, hull-blind | evaluate.py:890 -> vessel.bridge_deck_clearance_required_m | REAL but hull-blind
5. `wet_deck_clearance_g` :781 — rise - clearance | clearance, U | g-value | own steady wave only | NO production consumer (no clearance gene) | REAL, ORPHANED
6. `ittc57_cf` :857 — 0.075/(log10 Re-2)^2 | U, Lwl, nu/rho | C_F | RE_TRANSITION_ONSET=5e5 refuse, RE_FULLY_TURBULENT=3e6 warn-only; both declared-not-sourced | total_resistance, extrapolate x4 | REAL
7. `nu_water` :73 — 2-point interp (1000,1.14e-6)-(1025,1.1883e-6) | rho | nu | REAL, honest
8. `form_factor` Watanabe :865 — k=-0.095+25.6Cb/((L/B)^2 sqrt(B/T)) | floated Cb,L,B,T | FormFactor(k,k_raw,clamped,sigma) | calibrated L/B 6-8; clamp [0,0.45]; 27.3% of grammar hulls CLAMP, max raw k 2.09 | REGRESSION outside support on most of design box; sigma inflated to |k_raw-k|
9. `flow_regime` :193 — Fn, Re | FlowRegime(michell_ok, ittc57_ok, envelope) | REAL gatekeeper -> Evaluation.vessel.models_admitted
10. `total_resistance` :913 — R_w+(1+k)C_F qS; sigma=0.25R_w+... | grid 241x44, GRID_CONVERGED_TO=0.005 (ref 0.221%, population worst 0.673% — OUTSIDE bar) | evaluate.py:584 sole production path | REAL; 0.25 hump band DECLARED

**holtrop.py** — full 1982 transcription, well-guarded (domain_errors raises), envelope L/B 3.9-9.5, B/T 2.1-4.0, Cp 0.55-0.85, FN_MAX 0.45.
11. `total` :661 — NO production consumer (tests only); only `envelope_violations` :637 runs in production (evaluate.py:630, badge-only). Measured: 5.0% of 300 samples satisfy envelope (B/T the killer).
12. `half_angle_entrance` :303 — i_E regression; NEVER computed from geometry anywhere in repo; c1 carries (90-i_E)^-1.37565 ("weakest link").

**waves.py**
15. `jonswap` :37 — renormalised to m0=Hs^2/16 | REAL | 4 hard-coded presets WITHOUT source/basis tag (only untagged physics constants in repo)
16. `encounter_omega` :51 — omega_e signed; following-sea fold detected | REAL
17. `heave_response` :91 — S_r=|RAO(omega_e)|^2 S(omega) | RAO extrapolated FLAT outside set | tests only — NO production consumer (evaluate.revalidate uses seakeeping.heave_seakeeping directly)

**seakeeping.py**
18. `wagner_impact_cp` :357 — pi cot beta + (pi^2/2)(pi/2beta - 1)^2 | 0<beta<=90 enforced | NOT classical Wagner peak — 4.1x larger at beta=10; UNCALIBRATED (structure-only tests)
19. `slam_pressure`/`_band` :417/:453 — 0.5 rho V^2 Cp | NO production caller; cfd bowSlammingPressure instrument exists but analytic<->measured comparison never executed
20. `heave_rao` :165 — FK+diff / (-w^2(m+A33)+iwB33+C33); zero speed; BEM method='direct' pinned | REAL L2
21. `heave_seakeeping` :232 — 2-mesh sweep, refuses <2 meshes | evaluate.revalidate:1260 | REAL, measured sigma

**dynamics.py** — ZERO consumers outside itself/tests
22. `inertia` :64 — _OWN_GYRADIUS table: five unsourced gyradius pairs + silent (0.30,0.20) fallback | HEURISTIC P1, dead
23. `mooring` :108 — CD=1.0 approx, SF literals | HEURISTIC P1, dead
24. `lifting`/pendulum — textbook statics | REAL

**extrapolate.py** — ittc78 :156 full procedure + sigma quadrature; roughness (Bowden-Davison, deliberately unclamped); C_AA C_D=0.8 declared; Prohaska calibrate. Consumer: scripts/demo_apse.py ONLY.
**similitude.py** — Condition fn/re/we/wavelength; FROUDE_EXPONENTS derived in-file; scale_effects floors basis='approx'. REAL.
**fidelity.py** — cost model not physics ladder. `density_for_wave_resolution` :183 HARD-CODES 54.0 while sibling reads background_counts (57) — STALE COPY, live drift, the exact defect its docstring narrates fixing. `seiche_period` :340 SUPERSEDED/refuted by tank_resonance measurement (5.53 s vs 7.75 s) yet fidelity.admit still refuses runs on it. BYTES_PER_CELL=1500 ASSUMED (badged).
**scripts/tank_resonance.py** — full dispersion, Doppler apparent_period, blocking min, LSQ dominant_period with refusals; REAL; refutes fidelity.seiche_period.

## MULTIHULL-INTERFERENCE
- WAVE interference PRESENT/CORRECT/WIRED: 4cos^2(k_y s/2); phase verified 3 ways; theta-average=2; evaluate.py:584 passes separation (previously did not — every prior catamaran scored as one isolated demihull).
- Theta sign-flip FIXED+ENFORCED (>=880*max(1,s/L) raises; measured 1.2% sign-changing error at 220).
- E17 waterline node correctly EXCLUDED (+237% R_w measured; 6 um kernel decay at sec~318 documented).
- VISCOUS form interference ABSENT (Insel & Molland cited, not transcribed); one demihull's Watanabe k applied to whole vessel; surfaced in caveats. NO experimental anchor for ANY multihull number.
- n_hulls>2: taxonomy exists, no resistance model (two-hull hard-coded).

## DUPLICATES
- ITTC-57 C_F: FOUR implementations (resistance:862, holtrop:471 deliberate+asserted-identical, cfd/case:477 inline with FIFTH nu=1.09e-6, extrapolate imports resistance's).
- g: 9.80665 x4 + cfd/case 9.81 (deliberate) + tank_resonance reads constant/g (correct).
- nu: four fresh/salt pairs, THREE different fresh-water values.
- rho_water: 1000 / 1025 / 999.0/1026.0 / 1026 default.
- rho_air: 1.225/1.226/1.2 — audited, deliberate, accept.
- form_factor name collision: resistance (Watanabe dataclass) vs holtrop (1+k1 float).
- fidelity nx base 54.0 vs background_counts 57 — live drift.
- Seiche: fidelity still-water vs tank_resonance Doppler — data refutes model, refusals still issued from refuted one.

## GAPS
- G4-P0 Catamaran viscous form-interference absent; no experimental anchor for any multihull number. (resistance.py:33-43)
- G4-P0 Michell grid bar 0.005 met on ref hull only; population worst 0.673%. (resistance.py:292-303)
- G8-P0 fidelity.seiche_period refuted by measurement yet fidelity.admit still refuses runs on it.
- G0-P1 slam_pressure/_band no production caller; analytic<->CFD comparison never executed.
- G0-P1 wet_deck_clearance_g orphaned (no clearance gene) — catamaran's governing failure mode unchecked.
- G4-P1 Wet-deck slam wiring absent both sides; wagner divergence worst exactly there.
- G0-P1 dynamics.py zero importers — dead code w/ weakest constants.
- G0-P1 waves.heave_response (encounter transform) no production consumer.
- G8-P1 fidelity 54.0 literal drift.
- G4-P1 holtrop.total never runs in production (5% envelope satisfaction); Gate 1 "Holtrop" clause satisfied by badge+tests only.
- G4-P2 Entrance angle never computed from geometry (Particulars.ie_deg -> regression).
- G4-P2 No planing model (Savitsky); Fn>0.45 returns badged-invalid with sigma=answer.
- G4-P2 No transitional friction; band reachable (LWL 4m @ 1kn), warn-only.
- G4-P2 Watanabe extrapolates on ~all hulls, clamps 27.3%.
- G4-P2 wagner uncalibrated (4.1x classical).
- G8-P2 five nu / four C_F.
- G4-P3 JONSWAP presets unsourced (only untagged constants).
- G4-P3 RAO flat extrapolation stated, unmeasured.
- G4-P3 trimaran: taxonomy without model.
- G4-P4 theta-grid truncation -0.48% (mechanism known).

## UNKNOWNS
- Mission speeds ever exceed FN_MICHELL_MAX in practice — UNKNOWN.
- benchmarks/wigley.py grid vs PRODUCTION_GRID post-E8 — UNKNOWN.
- 880-node catamaran runtime vs Gate 1 50 ms bar in CI (claimed 24.3 ms in-file) — unverified.
- holtrop_envelope_violations gate-colour effect — gates.py not traced.
- JONSWAP preset provenance — UNKNOWN.
- demo_apse.py in CI (sole extrapolate/similitude/fidelity consumer) — UNKNOWN.
