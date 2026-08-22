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

## Set 3 — Mechanical Touch Sensors → Calibration

Endstop / limit-switch positioning. This set is **preparation for the calibration
function**: prove one switch, prove all six, prove the halt/homing/measurement primitives,
then build calibration on top of them.

### Test 0 — Single-switch live read
Read one endstop switch, standing still, and confirm it reports correctly (released = 1,
pressed = 0). Test each of the six channels by editing the pin number and re-running the
same script — one switch at a time, so a bad channel is unambiguous. Proves the wiring,
pull-up, and polarity per channel. *(Done: confirmed NO wiring, `TRIGGERED = 0`,
idle-HIGH.)*

### E1 — Reflex stop
Prove the gantry stops itself the instant a switch is hit, without asking the ThinkCentre.
Where Test 0 read one switch standing still, E1 reads all six *while a motor is moving*, and
a hit kills the motor within one step. This is the safety reflex — dumb, fast, local. Move
an axis slowly, trip switches by hand, confirm it halts and names which one fired.

### E2 — Homing
Prove the gantry can find a repeatable zero on its own. It drives to a switch (fast), backs
off, then creeps back in slow for a precise touch — that slow touch becomes position 0.
Home three times and confirm the same spot each time (±2 steps). Without a trustworthy
zero, everything downstream is built on sand.

### E3 — Travel measurement
Prove you can measure how far each axis actually travels, in steps. Home one end = 0, drive
to the far switch counting steps — that count is the axis length (the *hard stop*); center
is half of it. Run three times to confirm the number is stable, then write it into the YAML.
For Z, measure Z1 and Z2 separately and log the difference (out-of-square).
s-fi
### E4 — Boundary enforcement
Prove the machine won't crash itself in normal operation. The brain (ThinkCentre) does the
limit math and only ever sends in-bounds moves, staying inside the *soft stop* (hard stop
minus buffer). The ESP32 keeps a crude sanity check as a fuse, and the switch is the
last-resort backstop. Command a move that's too far; confirm the brain clamps it and the
switch is never touched.

### E5 — Calibration function
The payoff — one routine the operator runs at every new install. The human edits the YAML
(shelf size, rows, columns); the machine then homes, measures its boundaries (E2 + E3),
derives the soft stops and centers, and double-checks by moving to a computed point to
confirm it arrives where predicted. When the YAML is filled in and verified, the machine is
"calibrated" and allowed to run circuits. This is what E1–E4 were all preparation for.

**Through-line:** E1 stop → E2 zero → E3 measure → E4 stay safe → E5 tie it all into one
setup routine.