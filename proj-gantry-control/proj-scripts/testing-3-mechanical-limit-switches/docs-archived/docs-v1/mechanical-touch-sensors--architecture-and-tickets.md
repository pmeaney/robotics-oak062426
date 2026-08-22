# Mechanical Touch Sensor System — Architecture & Testing Tickets

**Subsystem:** Endstop / limit-switch positioning
**Purpose:** This ticket set is preparation for the **calibration function** (E5). It is system-development testing that must pass *before* calibration can be trusted — prove one switch (Ticket 0, done), prove all six, prove the halt/homing/measurement primitives, then build calibration on top of them.
**Ownership:** ThinkCentre = brain (coordinate map, limit math, `prototype-shelf.yaml`) · ESP32 "SysM" = hands (executes orders + always-on endstop reflex)
**Predecessor doc:** `mechanical-touch-sensors--testing-tickets.md` (electrical bring-up / channel proving)
**Status:** All 6 switches installed; Ticket 0 (single-switch read) passed. Architecture below; tickets append to the current set.

### Stop vocabulary
- **Hard stop** — the physical switch (`TRIGGERED`). The wall. Expected during homing, a fault otherwise.
- **Soft stop** — the brain's step limit, set *inside* the hard stop. Derived, not measured: `soft_stop = hard_stop − buffer`.
- **Buffer** — the gap `hard_stop − soft_stop`; room so normal moves never reach the switch.
- **Back-off** — how far the gantry retreats *after* touching a stop (releases the switch when homing; retreats from a fault).

---

## 1. What this subsystem is

Six mechanical microswitches, one at each end of travel, that tell the gantry when it has reached a physical limit. They do **three distinct jobs** (see §3) — safety reflex, homing reference, and soft-limit backstop — and the firmware must treat those as different events even though they arrive on the same pins.

This replaces the earlier A3144 Hall-effect endstop design. The switch's audible click decouples mechanical actuation from electrical readout, which removes the debugging opacity that made the Hall channels hard to isolate.

## 2. Sensor hardware

- **Switches:** GUBCUB micro limit switches on breakout PCBs (S / G / V pins, SMD pads unpopulated).
- **Quantity:** 5-pack + 2 carried over from the original 3D printer → 6 in service, spare(s) on hand.
- **Signal conditioning (breadboard, since pads are unpopulated):** external 10 kΩ pull-up (3.3 V → SIG), optional 100 nF (SIG → GND).
- **Rails:** V → 3.3 V, G → GND, S → SIG.
- **Input-only GPIOs (34/35/36/39) have no internal pull-ups — external pull-up is mandatory, not optional.**

### Pin map (verify)
| Endstop | Axis / End | GPIO |
|--------|-----------|------|
| Z1T | Z1 top | 35 |
| Z1B | Z1 bottom | 34 |
| Z2T | Z2 top | 5 |
| Z2B | Z2 bottom | 15 |
| XZ1 | X at beam Z1 | 32 |
| XZ2 | X at beam Z2 | 4 |

> Reconcile against the older list (34/35/36/39/32/4) — Z2 shows as 5/15 here vs 36/39 there. One is stale.

### Polarity — confirmed (NO, idle-HIGH)
Wired **normally-open**: switch COM → GND, NO → pull-up node (SIG). Idle = pull-up = **HIGH (1)**, pressed = shorted to GND = **LOW (0)**. Confirmed by `test0--z1b-switch-read.py`.

**`TRIGGERED = 0`** — all firmware references this constant.

## 3. The three roles of one switch

1. **Reflex** — "something got hit, stop now." Always on, dumb, fast, local to the ESP32.
2. **Homing** — "I drove into this switch on purpose to find zero." Expected, not a fault.
3. **Soft limit** — a *number in the brain*, not a switch. Once travel is known in steps, the ThinkCentre keeps every move inside `[0, max]` so a switch is never touched in normal operation. The switch is the backstop, not a positioning element.

The same GPIO event means *abort* / *success* / *impossible-fault* depending on mode. Meaning is assigned one layer up, by whatever order was executing when it fired.

## 4. Architecture (locked)

**Brain / hands split.**
- **ThinkCentre = brain.** Owns `prototype-shelf.yaml` (master calibration + shelf description), the coordinate map, and all limit math. Computes every move target in steps, always in-bounds, and only ever sends in-bounds orders.
- **ESP32 "SysM" = hands.** Executes a small vocabulary — *home axis*, *move axis by N steps*, *report position/status* — and reports back. It does not hold the coordinate map. The ESP32 never reads or writes the YAML.

**Three stop layers (outermost = last resort):**
1. **Brain soft limits** — targets computed inside `[min + margin, max − margin]`; the primary guard. The ESP32 never receives an out-of-bounds order.
2. **ESP32 sanity ceiling** — a crude per-axis absolute max + reject-negative, pushed once at startup. Not the map; a fuse against a garbled order or a runaway home.
3. **ESP32 endstop reflex** — always-on, hardwired, local. Fires the instant a pin reads `TRIGGERED`, disables drivers, reports fault. The physical backstop for anything layers 1–2 miss. Local because a safety stop can't wait on serial latency.

**Startup handshake:** ThinkCentre pushes *motion config* to the ESP32 — step speeds, homing approach/back-off distances, `INVERT` flags, per-axis sanity ceiling. It does **not** push soft limits; the walls stay in the brain.

**Dual-Z:** Z is two motors on one beam with four independent endstops. "Halt both motors on any trigger" is the default/fault behavior — but homing and squaring drive Z1 and Z2 **independently**, each stopping on its own switch, where an expected trigger means "sub-move done," not "abort." The Z1↔Z2 step delta at the top switches is the out-of-square measurement, cross-checked by the GY-521.

---

## Tickets

> Numbered E1–E4 to append cleanly to the current set; renumber as needed. Ordered by "prove the layer first."

### Ticket E1 — Endstop reflex stop
**Objective:** Any switch trigger halts *both* axes within ≤1 step and disables all drivers, without consulting the ThinkCentre.
**Approach:** Poll all six pins once per step iteration inside the motion loop (no IRQ — poll-in-loop gives ≤1 step overtravel and avoids MicroPython ISR/alloc constraints). On trigger: break the loop, disable drivers in `finally`, report which pin fired.
**Script:** `test-e1--reflex-stop.py` (one slow move per axis; trip each switch by hand mid-move).
**Pass:**
- Tripping any switch stops motion within 1 step.
- Correct (axis, end) reported for all 6 channels.
- Drivers end disabled every time (verified via `finally`).

### Ticket E2 — Per-axis homing (two-stage)
**Objective:** A repeatable zero for each axis, on order from the ThinkCentre.
**Approach:** Fast approach toward the min-end switch until trigger → back off a fixed release distance → slow re-approach → the slow bump is zero. Motion is *event-terminated* (move until trigger), so the step count is the measured output, not a commanded count — the intended exception to duration-based motion.
**Script:** `test-e2--home-axis.py` (one axis via arg; drivers init disabled, `try/finally`).
**Pass:**
- Homing lands on the switch, backs off, and releases it (pin reads idle after back-off).
- Repeat 3×; zero repeatable within ±2 steps (tighten later if needed).
- Z homed as Z1 and Z2 **independently**.

### Ticket E3 — Travel + center measurement
**Objective:** Record axis length and center in steps. *(The requested max/center ticket.)*
**Approach:** Home the min end = 0 → drive toward the max switch counting steps until trigger → that count is axis length → center = length / 2. For Z, capture Z1 and Z2 separately and log the delta (out-of-square).
**Script:** `test-e3--measure-travel.py`.
**Pass:**
- Length recorded for X, Z1, Z2.
- Repeat 3×; spread within tolerance (e.g. ≤ a few steps) before the numbers are trusted.
- Z1↔Z2 delta logged and sanity-checked against the GY-521.
- ESP32 reports counts over serial; the **ThinkCentre writes value / center / measured_at into `prototype-shelf.yaml`** (ESP32 never writes the file).

### Ticket E4 — Boundary enforcement + persistence
**Objective:** Normal moves stay well short of the switches; a bad order can't crash the machine.
**Approach:**
- **Brain (soft stop):** ThinkCentre computes every target inside the soft stop (`hard_stop − buffer`) from the YAML; out-of-bounds moves are never generated. Primary guard.
- **Hands (sanity ceiling):** ESP32 rejects negative targets and anything past a crude per-axis absolute max (pushed at startup). Catches a garbled order and aborts a runaway home — live risk while polarity is unconfirmed, since a NO-wired disconnected switch reads idle and won't stop a home.
- **Reflex (E1):** physical backstop if both miss.
- **Fault path:** a switch firing while *not* homing/squaring → ESP32 halts, reports fault → ThinkCentre treats position as lost → re-home (open-loop steppers lose position after a crash).
**Script:** `test-e4--boundary.py` (command moves that would exceed limits; confirm the brain clamps and the ceiling rejects).
**Pass:**
- ThinkCentre never emits an out-of-bounds target; switches don't fire during normal moves.
- ESP32 rejects a negative / absurd target and aborts a runaway home.
- Unexpected trigger → fault state + re-home required.
- Calibration survives a power cycle (persisted in `prototype-shelf.yaml`, read on startup).

### Ticket E5 — Calibration function
**Objective:** One operator-run routine that turns a fresh install into a trusted coordinate model. This is what E1–E4 were preparation for.
**Why it comes last:** it *composes* the proven primitives — it does no new low-level work. E1–E4 must pass first; calibration built on unproven halt/homing/measurement can't be trusted.

**Two phases (by authorship):**
1. **Human declares** — operator follows the README, edits `prototype-shelf.yaml`: shelf dimensions, columns, rows, thickness. What's physically present, which the machine can't measure.
2. **Machine discovers, then verifies** — homes each axis (E2), drives its boundaries to measure `hard_stop_steps` (E3), derives `soft_stop = hard_stop − buffer` and `center`, then **double-checks**: re-measures within tolerance *and* commands a move to a computed interior point (e.g. cell center) and confirms it arrives as predicted. Writes results to the YAML.

**Done-gate:** calibration is complete when the YAML `gantry:` block is fully populated and verified. The Mission layer reads this on boot — if those fields are null, refuse to run a circuit and tell the operator to calibrate first. An un-calibrated machine never drives blind.

**Recalibration triggers (Mission-layer, later — noted not specced):** first install (obvious); moved to a new shelf (operator re-runs by hand); crash that lost zero (re-home vs. full recal); long-term drift (belt tension). "Something decides when calibration is stale" is a Mission question, not an E-ticket one.

**Script:** `test-e5--calibrate.py` (full routine on the prototype shelf; end-to-end).
**Pass:**
- Reads the human-declared shelf section without error.
- Discovers `hard_stop_steps` for X, Z1, Z2 (Z independently); derives soft stop + center.
- Verification move to a computed interior point arrives within tolerance.
- YAML `gantry:` block fully populated + `measured_at` set; done-gate flips to calibrated.

---

## Open items
- **Pin map** — Z2 as 5/15 vs 36/39; reconcile.
- **Tuning values** — filled during the tickets, then stored in the YAML as *policy* (not measured):
  - `buffer_steps` — soft-stop margin inside the hard stop (from E3 overshoot behavior).
  - `backoff_steps` — retreat distance after touching a stop (from E2 release behavior).
