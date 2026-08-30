# S3T6 — Calibration: Design Summary

Where S3T6 landed after this round of decisions. S3T6 is the capstone of Set 3 — it turns
the proven per-axis primitives (S3T2–S3T5) into a trusted, persisted coordinate model.

---

## Split into two stages

S3T6 crosses the brain/hands boundary, so it's built in two stages rather than one leap.

### Stage 1 — Measurement half (all on the ESP32)
`test6--calibrate-bounding-box.py`. Composes the proven X (S3T4) and Z (S3T5) measurements
into one standalone run and prints the workspace as a rectangle. No serial protocol, no file.
Its numbers live only in RAM for that run and are printed as text — deliberately throwaway,
because it's a *measurement test*, not the source of truth.

### Stage 2 — Calibration function (ThinkCentre orchestrates the ESP32)
Not built yet. The ThinkCentre (brain) reads the human-declared shelf data from the YAML,
orders the ESP32 (hands) to home + measure each axis over serial, computes the soft stops /
centers / bounding box, runs a verify-move, and **writes the result into the YAML**. This is
where measured numbers become the machine's persisted truth.

**The core difference:** Stage 1's box is a number on screen; Stage 2's box is a fact the
machine acts on — so Stage 1 can let the ESP32 do the math, but Stage 2 must keep it in the
brain, where the coordinate model and the YAML live.

---

## The bounding box (first-touch = a true rectangle)

Every axis limit is defined by the **first** switch encountered, not the second.

- For the Z beam (two motors), the paired end-switches are slightly offset, so one trips
  before the other. Taking the first-touch as the limit — and measuring the gap to the
  second as the squaring delta — keeps the usable region a **rectangle inscribed inside**
  the reachable area. Using the second switch would tilt it into a trapezoid.
- X (single motor) contributes clean left/right limits with no such ambiguity.

Output:
- **hard box** = the four first-touch limits, in steps.
- **soft box** = hard box inset by a ~5 mm buffer per side — the safe region normal moves
  stay inside so a switch is never tapped in routine operation.
- **squaring deltas** (bottom + top) reported for information and cross-check.

Tuning values banked this round: `BACKOFF_STEPS = 400` (~10 mm release distance) and
`buffer = ~5 mm` (~200 steps). Both rest on a rough ~40 steps/mm for Z (from 100 steps ≈
2.5 mm); real steps/mm — and a possibly different X value — get nailed down in Stage 2.

---

## Self-calibration triggers (new `calibration:` block in the YAML)

Three kinds of trigger, kept as Mission-layer *policy* — a section parallel to `shelf:`
(description) and `gantry:` (measured data), not mixed into either.

| Trigger | Kind | Scope | Notes |
|---------|------|-------|-------|
| `on_shelf_change` | event-driven | full | any edit to `shelf:` invalidates calibration |
| `on_schedule` | time-driven | full | e.g. weekly; catches unseen drift (ThinkCentre owns the clock) |
| `opportunistic` | opportunistic | rehome | at corner cells, where the beam is already near the switches |

**Two weights of calibration:**
- `rehome` — home each axis to refresh zero. Fast; used opportunistically.
- `full` — rehome + re-measure travel + rebuild the bounding box. Slow; used for the event
  and schedule triggers.

**Opportunistic timing = `after_scan`:** scan the corner cell first on trusted numbers, then
refresh calibration on the way out. Never recalibrate *before* the scan — that would disturb
position and scan against unvalidated numbers.

**Opportunistic doubles as a drift sensor.** A rehome re-finds the switches, so it can compare
the fresh squaring delta against the stored one:
- past `warn_threshold_steps` (~40 ≈ 1 mm) → log a warning (a breadcrumb trail of creep).
- past `escalate_threshold_steps` (~200 ≈ 5 mm) → request a `full` recal on the next circuit.

It **never self-corrects** — the action stays a simple rehome; the flag is only a warning that
a full recal or a mechanical look is due. And it's a *proxy*: it audits the corner it's at, not
the whole workspace — the right trade for a cost-free check.
