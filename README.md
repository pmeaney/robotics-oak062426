# Robotics project

This project is based on a 3D printer structure and is used to position a gantry containing a sensor in 2D space, eventually 3D space.

## Required software


- ESP32 related

    - **mpremote** — runs MicroPython test files on the ESP32 over USB. Install globally with pipx: `pipx install mpremote`.

Everything else runs on the ESP32 as MicroPython using built-in modules only, so there is nothing to install on the board.

See `tooling-notes.md` for setup details and background.

Run a test with:

```bash
mpremote run some-file.py
```


# Ticket Sets — Overview

The same throughout: **prove each layer before adding complexity** — run in order, don't
advance until the current test passes, and add only one new variable at a time so any
failure points at exactly one cause.

- **Set 1** — Gantry motor validation (open-loop, no sensors)
- **Set 2** — *Archived* (Hall-effect sensors, declined)
- **Set 3** — Mechanical touch sensors + shelf-dimensions YAML + gantry motors → calibration

Upcoming:
- **Set 4** — Gyro
- **Set 5** — Lidar
- **Set 6** — Full System Integration: Bringing together Gantry, Touch Sensors, Gyro, and Lidar

---

## Set 1 — Gantry Motor Validation

Open-loop motor validation, no sensors. Proves the motors move correctly under their own
power, in order of increasing risk. Z1 + Z2 are the synchronized verticals; X is the
horizontal carriage.

### Test 0 — Three-motor hold
All three motors energized and holding position, no motion. Proves the boring-but-fatal
basics first: power delivery, grounding, and thermal behavior under load. If a driver
browns out or a motor overheats just from holding current, you find out here — before
anything moves and before it carries weight.

### Test 1 — Both verticals held together
Z1 and Z2 energized and holding as a pair, still no motion. Confirms the two motors that
must cooperate can both hold the beam without one sagging or fighting the other — the
baseline before stepping them.

### Test 2 — Both verticals stepped together
The first real movement. Z1 and Z2 step in sync, same direction, for five seconds — run
first **without belts** so nothing can rack or bind if a direction is wrong. Then belts on,
run again to verify real direction and that they track together. This is where the
mirror-mount `INVERT` setting gets proven safely.

### Test 3 — Lift, lock, traverse
The full coordinated sequence: the verticals lift and hold the beam locked in place while
X drives the carriage across. First test where all three motors work as a system and two
axes coordinate — vertical holds position while horizontal moves. Pass this and you have a
working three-axis gantry under open-loop control.

**Through-line:** hold all three → hold the pair → step the pair (beltless, then belted) →
coordinate all three.

---

## Set 2 — Hall-Effect Sensors *(archived)*

Superseded and not in use. This set covered A3144 Hall-effect endstops, which were
declined: the failure modes were opaque to debug (stuck-LOW channels that didn't match a
dead open-collector sensor pointed at wiring faults, not the parts). Replaced by mechanical
switches in Set 3 — the audible click decouples mechanical actuation from electrical
readout, which made faults isolable. Kept only for reference.

---

## Set 3 — Mechanical Touch Sensors + Shelf-Dimensions YAML + Gantry Motors → Calibration

Endstop / limit-switch positioning. This set is **preparation for the calibration
function**: prove the sensors read, prove the reflex halt, prove home + measurement, then
build calibration on top. (Soft-limit / boundary enforcement is brain-side — tracked
separately in `motion-control--tickets.md`, not here.)

### S3T0 — Single-switch live read *(done)*
Read one endstop switch, standing still; confirm released = 1, pressed = 0. Test each of the
six channels by editing the pin and re-running — one at a time, so a bad channel is
unambiguous. Proved wiring, pull-up, and polarity. (NO wiring, `TRIGGERED = 0`, idle-HIGH.)

### S3T1 — All-six read + pin/axis mapping *(done)*
Read all six at once, standing still: baseline all = 1, then press each switch and confirm
its label matches the one pressed. Proved every channel and locked the axis→pin map.

### S3T2 — X reflex stop
X steps slowly in place; hand-trip any switch and the motor halts within ~1 step and disables
— locally, no ThinkCentre. Proves the reflex mechanism alone (no homing, no back-off, no wall).

### S3T3 — Z dual reflex stop
Both Z motors step together; tripping any one of the four Z switches halts *both* within ~1
step. Proves the anti-racking "any → all" rule — a trip on one channel kills both motors.

### S3T4 — X home + measure
X finds a repeatable zero (two-stage: fast approach, back off, slow re-approach), then drives
to the far switch counting steps = travel (the *hard stop*); center is half. Back-off lives here.

### S3T5 — Z home + measure (independent)
Z1 and Z2 each home and measure travel independently, each stopping on its own switch. The
Z1↔Z2 step difference is the out-of-square (squaring) figure.

### S3T6 — Calibration function
The payoff — one routine the operator runs at every new install. The human edits the YAML
(shelf size, rows, columns); the machine homes + measures (S3T4/S3T5), derives the soft stops
and centers, and double-checks by moving to a computed point to confirm it arrives where
predicted. When the YAML is filled in and verified, the machine is "calibrated" and allowed to
run circuits. This is what S3T2–S3T5 were all preparation for.

**Through-line:** read one → read all six → X reflex → Z dual reflex → X home+measure →
Z home+measure → calibrate.
