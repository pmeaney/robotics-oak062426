# Mechanical Touch Sensors — Hardware, Architecture & Tickets

*Single source of truth for Set 3. Absorbs the former `test-set-3-README.md` (hardware
reference) and the architecture/tickets doc — those overlapped and had begun to drift.*

**Subsystem:** Endstop / limit-switch positioning
**Purpose:** Preparation for the **calibration function** (S3T6). System-development testing
that must pass *before* calibration can be trusted — prove one switch (S3T0, done),
prove all six + map them (S3T1), prove the halt/homing/measurement primitives (S3T2–S3T5),
then build calibration on top (S3T6).
**Ownership:** ThinkCentre = brain (coordinate map, limit math, `prototype-shelf.yaml`) ·
ESP32 "SysM" = hands (executes orders + always-on endstop reflex)
**Status:** Six switches mounted. S3T0 (single-switch read) passed. **Not yet wired to
the ESP32; axis→pin assignment not yet decided** — both close out in S3T1.

### Stop vocabulary
- **Hard stop** — the physical switch (`TRIGGERED`). The wall. Expected during homing, a fault otherwise.
- **Soft stop** — the brain's step limit, set *inside* the hard stop. Derived, not measured: `soft_stop = hard_stop − buffer`.
- **Buffer** — the gap `hard_stop − soft_stop`; room so normal moves never reach the switch.
- **Back-off** — how far the gantry retreats *after* touching a stop (releases the switch when homing; retreats from a fault).

---

## 1. What this subsystem is (and why microswitches)

Six mechanical microswitches, one at each end of travel, that tell the gantry when it has
reached a physical limit. They do **three distinct jobs** (see §5) — safety reflex, homing
reference, and soft-limit backstop — and the firmware treats those as different events even
though they arrive on the same pins.

This replaces the earlier A3144 Hall-effect design. The switch is the more robust choice:

- **No heat-sensitive die.** A Hall die can be killed by soldering; a microswitch has no
  fragile silicon to cook.
- **Hard mechanical trip point.** A physical lever gives a deterministic, repeatable homing
  reference — better than a magnetic field that drifts with gap, magnet strength, and temperature.
- **Simpler bring-up.** Press the lever and it reads. No pole / gap / threshold to fuss with.
- **Audible click** decouples mechanical actuation from electrical readout — which removes
  the debugging opacity that made the Hall channels hard to isolate.

> Context: the A3144 failures on this bench traced mostly to solder-heat death and
> per-channel wiring faults, not the Hall sensing principle — itself an argument for the
> switch: fewer parts per channel to get wrong, no die to cook.

## 2. The switch — hardware reference

**Class:** SPDT snap-action micro limit switch — 3 terminals (COM / NO / NC), lever or
roller-lever actuator. Representative part: Omron **SS-5GL** / generic "3D-printer endstop"
microswitch. Sourced from a 5-pack + 2 carried over from the original 3D printer → 6 in
service, spare(s) on hand.

> **Confirm your exact model** and drop its datasheet values in — the figures below are
> typical for the class, not measured from your part.

| Spec | Typical (confirm your part) |
|------|-----------------------------|
| Configuration | SPDT snap-action, COM / NO / NC |
| Actuator | Lever / roller-lever |
| Contact rating | ~5 A @ 125–250 VAC |
| Our actual load | ~3.3 V, ~0.33 mA (dry / logic-level) |
| Operate force | ~0.5–1.5 N |
| Pretravel / overtravel | ~0.5 / ~1 mm (model-dependent) |
| Trip repeatability | ~0.01–0.05 mm |
| Mechanical life | ~1,000,000 operations |
| Contact bounce | ~1–5 ms |

**Reliability notes (the parts that actually matter here):**
- **Wetting current.** We switch only ~0.33 mA (3.3 V through the 10 kΩ pull-up) — low for
  a silver-contact switch; contacts can oxidise and go intermittent at sub-mA over time.
  Prefer a switch rated for low-level/logic loads or gold contacts. If a silver switch reads
  flaky, drop the pull-up to ~3.3 kΩ (≈1 mA wetting); the extra idle current is negligible.
- **Bounce.** ~1–5 ms of chatter. Invisible to a 4 Hz live read; but it *can* false-trigger a
  motion stop. The C104 handles this in hardware (see §3, τ≈1 ms) — add software debounce in
  S3T2 only if bounce still trips it.
- **Wear.** A contact/wear item (~1 M operations). Mount it to be pressed *gently* at the
  limit, not slammed.

## 3. Wiring & signal conditioning

### Per-channel wiring — NO (normally-open)
- **COM → GND**
- **NO → node A** — the 10 kΩ pull-up node (where the A3144 OUT used to land)
- **Signal path:** node → GPIO, with 10 kΩ pull-up → 3.3 V (see conditioning below)
- **Dropped from the Hall rig:** the A3144, its 5 V feed, and the 0.1 µF *decoupling* cap
  (a passive switch has nothing to power)

### Polarity — confirmed (NO, idle-HIGH)
Idle = pull-up = **HIGH (1)**; pressed = shorted to GND = **LOW (0)**. Confirmed by
`test-0-mech-limit-switch-individual.py`.

**`TRIGGERED = 0`** — all firmware references this constant.

> **Fail-safe note (permanent, not pending):** NO wiring means a *broken signal wire reads
> idle* — it won't stop a move or a home. Accepted for bench bring-up. Switch to **NC**
> (inverts logic to `TRIGGERED = 1`) before the full-size unit if wire-break safety matters.
> This is why the S3T5 sanity ceiling exists (runaway-home guard).

### ⚠ Signal conditioning — confirm what's on the board
The two source docs disagreed; reconciled here to the best-supported reading:

- **Adopted:** 10 kΩ pull-up → 3.3 V, plus **100 nF (C104)** on the signal line (SIG → GND).
  C104 with the 10 kΩ gives τ ≈ 1 ms — doubles as hardware debounce. Backed by Doc1, the
  README's onboard-pads note, and the "we use a 104" call.
- **Retired as stale:** *1 kΩ series + 10 nF (103) filter* — Hall-rig carryover; the README's
  wiring section still listed it.

> **Confirm what's physically on the breadboard.** These aren't stackable at one node. This
> is the capacitor-role version of the 1k-vs-10k trap: **104 = decoupling** for the *active*
> Hall sensor (correctly dropped for a passive switch) vs **103 = signal filter**. Easy to
> conflate.

### If you use pre-built endstop *modules* instead of bare switches
Each module carries its own conditioning and breaks out to **S / G / V**:

| Pin | Meaning | Connect to |
|-----|---------|------------|
| **S** | Signal | a GPIO |
| **G** | Gnd | common ground |
| **V** | VCC — **3.3 V** | 3.3 V rail (**not 5 V**) |

> **V must be 3.3 V.** The onboard pull-up ties S to whatever V is; at 5 V, S idles above the
> ESP32's 3.3 V input limit.

Onboard pads (arrive **empty**; populate on the board for production, or on the breadboard
for prototyping):

| Pad | Role |
|-----|------|
| **10k** | Signal pull-up — holds S high while the switch is open |
| **1k** | **LED** current-limit resistor (~1.3 mA). **Not** in the signal path |
| **LED** | State indicator |
| **C104** (100 nF) | Signal noise / debounce cap |

> **Two different 1k roles — don't conflate.** The module's 1k limits *LED* current; a 1k on
> the breadboard would be *in series with the signal*. Same value, different job.
> **Don't stack conditioning:** module *or* bare switch per channel, never both — otherwise
> you double the pull-up and stack the filters.

## 4. Pin map — GPIO set fixed, axis assignment PROVISIONAL

The six GPIOs are chosen: **35, 34, 5, 15, 32, 4**. Which physical switch lands on which GPIO
is **not yet decided** — S3T1 confirms it empirically (press each switch, see which GPIO
flips). The table below is the *intended* assignment, to be verified/corrected by S3T1.

| Endstop | Axis / End | GPIO (intended) |
|--------|-----------|------|
| Z1T | Z1 vertical — top | 35 |
| Z1B | Z1 vertical — bottom | 34 |
| Z2T | Z2 vertical — top | 5 |
| Z2B | Z2 vertical — bottom | 15 |
| XZ1 | X endstop at Z1 vertical | 32 |
| XZ2 | X endstop at Z2 vertical | 4 |

- **Input-only GPIOs 34 and 35** have no internal pull-up — external pull-up is mandatory.
  (36/39 are also input-only, but the current set uses 5/15; the older 36/39 alternative is
  retired.)

## 5. The three roles of one switch

1. **Reflex** — "something got hit, stop now." Always on, dumb, fast, local to the ESP32.
2. **Homing** — "I drove into this switch on purpose to find zero." Expected, not a fault.
3. **Soft limit** — a *number in the brain*, not a switch. Once travel is known in steps, the
   ThinkCentre keeps every move inside `[0, max]` so a switch is never touched in normal
   operation. The switch is the backstop, not a positioning element.

The same GPIO event means *abort* / *success* / *impossible-fault* depending on mode. Meaning
is assigned one layer up, by whatever order was executing when it fired.

## 6. Architecture (locked)

**Brain / hands split.**
- **ThinkCentre = brain.** Owns `prototype-shelf.yaml`, the coordinate map, all limit math.
  Computes every move target in steps, always in-bounds, and only ever sends in-bounds orders.
- **ESP32 "SysM" = hands.** Executes a small vocabulary — *home axis*, *move axis by N steps*,
  *report position/status* — and reports back. Holds no coordinate map. Never reads/writes the YAML.

**Three stop layers (outermost = last resort):**
1. **Brain soft limits** — targets computed inside `[min + margin, max − margin]`; primary guard.
2. **ESP32 sanity ceiling** — a crude per-axis absolute max + reject-negative, pushed at
   startup. Not the map; a fuse against a garbled order or a runaway home.
3. **ESP32 endstop reflex** — always-on, hardwired, local. Fires the instant a pin reads
   `TRIGGERED`, disables drivers, reports fault. Local because a safety stop can't wait on serial.

**Startup handshake:** ThinkCentre pushes *motion config* — step speeds, homing
approach/back-off distances, `INVERT` flags, per-axis sanity ceiling. It does **not** push
soft limits; the walls stay in the brain.

**Dual-Z:** Z is two motors on one beam with four independent endstops. "Halt both motors on
any trigger" is the default/fault behavior — but homing and squaring drive Z1 and Z2
**independently**, each stopping on its own switch, where an expected trigger means "sub-move
done." The Z1↔Z2 step delta at the top switches is the out-of-square measurement, cross-checked
by the GY-521.

---

## Tickets

> Two tiers: **S3T0 / S3T1** prove the sensors *read* (standing still); **S3T2–S3T6** prove the
> endstop *functions* (motion, measurement, calibration).

### S3T0 — Single-channel read *(done)*
Read one switch, standing still; confirm released = 1, pressed = 0. Test each channel by
editing the pin and re-running. Proved wiring, pull-up, and polarity per channel.
**Script:** `test-0-mech-limit-switch-individual.py`. **Result:** NO, `TRIGGERED = 0`, idle-HIGH.

### S3T1 — All-six read + pin/axis mapping
**Objective:** Prove all six channels read once wired, and *decide the axis→pin map*.
**Approach:** Read all six pins at once, standing still. Baseline: nothing pressed → all six
read 1 (any 0 = wiring fault on that channel). Then press each switch by hand; the changed
channel names its GPIO — that *is* the mapping. Rename labels to Z1T/Z1B/Z2T/Z2B/XZ1/XZ2 as
confirmed.
**Script:** `test-1-mech-limit-switch-all-six.py` (prints on change; no motion; no debounce).
**Pass:**
- Baseline reads 1 on all six.
- Each switch, pressed, flips exactly its own channel to 0.
- Axis→pin map confirmed and written into §4 (replacing the provisional table).

### S3T2 — Endstop reflex stop
**Objective:** Any switch trigger halts *both* axes within ≤1 step and disables all drivers,
without consulting the ThinkCentre.
**Approach:** Poll all six pins once per step iteration inside the motion loop (no IRQ —
poll-in-loop gives ≤1 step overtravel and avoids MicroPython ISR/alloc constraints). On
trigger: break the loop, disable drivers in `finally`, report which pin fired.
**Script:** `test-s3t2--reflex-stop.py` (one slow move per axis; trip each switch by hand mid-move).
**Pass:**
- Tripping any switch stops motion within 1 step.
- Correct (axis, end) reported for all 6 channels.
- Drivers end disabled every time (verified via `finally`).

### S3T3 — Per-axis homing (two-stage)
**Objective:** A repeatable zero for each axis, on order from the ThinkCentre.
**Approach:** Fast approach toward the min-end switch until trigger → back off a fixed release
distance → slow re-approach → the slow bump is zero. Motion is *event-terminated* (move until
trigger), so the step count is the measured output, not a commanded count — the intended
exception to duration-based motion.
**Script:** `test-s3t3--home-axis.py` (one axis via arg; drivers init disabled, `try/finally`).
**Pass:**
- Homing lands on the switch, backs off, and releases it (pin reads idle after back-off).
- Repeat 3×; zero repeatable within ±2 steps (tighten later if needed).
- Z homed as Z1 and Z2 **independently**.

### S3T4 — Travel + center measurement
**Objective:** Record axis length and center in steps. *(The requested max/center ticket.)*
**Approach:** Home the min end = 0 → drive toward the max switch counting steps until trigger →
that count is axis length → center = length / 2. For Z, capture Z1 and Z2 separately and log
the delta (out-of-square).
**Script:** `test-s3t4--measure-travel.py`.
**Pass:**
- Length recorded for X, Z1, Z2.
- Repeat 3×; spread within tolerance (e.g. ≤ a few steps) before the numbers are trusted.
- Z1↔Z2 delta logged and sanity-checked against the GY-521.
- ESP32 reports counts over serial; the **ThinkCentre writes value / center / measured_at into
  `prototype-shelf.yaml`** (ESP32 never writes the file).

### S3T5 — Boundary enforcement + persistence
**Objective:** Normal moves stay well short of the switches; a bad order can't crash the machine.
**Approach:**
- **Brain (soft stop):** ThinkCentre computes every target inside the soft stop
  (`hard_stop − buffer`) from the YAML; out-of-bounds moves are never generated. Primary guard.
- **Hands (sanity ceiling):** ESP32 rejects negative targets and anything past a crude per-axis
  absolute max (pushed at startup). Catches a garbled order and aborts a runaway home — a real
  standing risk, since NO wiring means a disconnected switch reads idle and won't stop a home.
- **Reflex (S3T2):** physical backstop if both miss.
- **Fault path:** a switch firing while *not* homing/squaring → ESP32 halts, reports fault →
  ThinkCentre treats position as lost → re-home (open-loop steppers lose position after a crash).
**Script:** `test-s3t5--boundary.py` (command moves that would exceed limits; confirm the brain
clamps and the ceiling rejects).
**Pass:**
- ThinkCentre never emits an out-of-bounds target; switches don't fire during normal moves.
- ESP32 rejects a negative / absurd target and aborts a runaway home.
- Unexpected trigger → fault state + re-home required.
- Calibration survives a power cycle (persisted in `prototype-shelf.yaml`, read on startup).

### S3T6 — Calibration function
**Objective:** One operator-run routine that turns a fresh install into a trusted coordinate
model. This is what S3T2–S3T5 were preparation for.
**Why it comes last:** it *composes* the proven primitives — no new low-level work. S3T2–S3T5 must
pass first; calibration built on unproven halt/homing/measurement can't be trusted.

**Two phases (by authorship):**
1. **Human declares** — operator edits `prototype-shelf.yaml`: shelf dimensions, columns, rows,
   thickness. What's physically present, which the machine can't measure.
2. **Machine discovers, then verifies** — homes each axis (S3T3), drives its boundaries to measure
   `hard_stop_steps` (S3T4), derives `soft_stop = hard_stop − buffer` and `center`, then
   **double-checks**: re-measures within tolerance *and* commands a move to a computed interior
   point (e.g. cell center) and confirms it arrives as predicted. Writes results to the YAML.

**Done-gate:** calibration is complete when the YAML `gantry:` block is fully populated and
verified. The Mission layer reads this on boot — null fields → refuse to run a circuit and tell
the operator to calibrate first. An un-calibrated machine never drives blind.

**Recalibration triggers (Mission-layer, later — noted not specced):** first install; moved to a
new shelf (operator re-runs by hand); crash that lost zero (re-home vs. full recal); long-term
drift (belt tension).

**Script:** `test-s3t6--calibrate.py` (full routine on the prototype shelf; end-to-end).
**Pass:**
- Reads the human-declared shelf section without error.
- Discovers `hard_stop_steps` for X, Z1, Z2 (Z independently); derives soft stop + center.
- Verification move to a computed interior point arrives within tolerance.
- YAML `gantry:` block fully populated + `measured_at` set; done-gate flips to calibrated.

---

## Open items
- **Signal conditioning** (§3) — confirm 10k + 104 is what's on the breadboard (vs the retired
  1k + 10nF filter).
- **Axis→pin map** (§4) — provisional until S3T1 confirms it.
- **Tuning values** — filled during the tickets, then stored in the YAML as *policy* (not measured):
  - `buffer_steps` — soft-stop margin inside the hard stop (from S3T4 overshoot behavior).
  - `backoff_steps` — retreat distance after touching a stop (from S3T3 release behavior).
