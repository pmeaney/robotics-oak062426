# Motor testing phase — test ladder & the phase that follows

> Scope note for this document. The **current phase is open-loop motion validation**:
> no sensors, no feedback. The goal is to confirm the three motors move in the expected
> sequence and directions, and to measure how well the two vertical motors hold the
> horizontal rail level *with no correction* — judged by eye and a spirit level, not by
> code. That uncorrected baseline is what makes the next phase (IMU-based leveling)
> designable. The second section summarizes that upcoming phase.

---

## Part 1 — The test ladder (current phase: motors only)

Each rung is independently verifiable before the next is attempted, in keeping with the
"prove each layer before adding complexity" principle. Rungs are ordered so that every
new rung adds exactly one source of potential failure.

### Rung 0 — Hold test (no motion)

All three motors energized (EN active) but **not stepping**. No STEP pulses at all.

**What it proves:** that the power, ground, and thermal system can carry three motors'
worth of steady current before any timing or motion complexity enters. Holding current
is close to the worst case for steady draw (a stationary rotor generates no back-EMF, so
the driver delivers full set current continuously), which makes this the cleanest possible
stress test of the rails and grounds.

**What to watch:** the 3.3V logic rail for a dip at the enable instant; the ESP32 console
for any brownout reset; each driver's temperature after ~a minute (looking for a hot
*outlier*, which would flag a marginal connection or a current-set error on that channel).

**Pass condition:** all three hold with torque, no reset, no hot outlier, rails steady.

---

### Rung 1 — Each motor solo (in the fully-wired state)

One motor at a time moves a known number of steps in one direction, then reverses. Run
for all three.

**What it proves:** that each EN/STEP/DIR triple lands on the correct driver and moves the
correct motor by the expected amount. Motor 1's pins are hardware-confirmed; Motors 2 and 3
are correct on paper but unproven on these exact pins — this rung (and Rung 0) closes that
gap.

**Key deliverable — lock the direction convention.** Determine and record what DIR level
raises vs. lowers each vertical, and which way the horizontal moves. This must be locked
before any coordinated move: a vertical running the wrong direction drives the gantry into
its end stop instead of lifting.

**Pass condition:** each motor moves the commanded steps, in the commanded direction, with
clean motion (no buzzing / skipping) under real load.

---

### Rung 2 — The two vertical motors, synchronized (Z1 + Z2)

Both vertical motors stepping together — same step count, same rate, same direction — to
raise the horizontal rail. This is the heart of the lift.

**What it really tests:** not "can both move" (already known), but whether the code can emit
two step trains closely enough in phase that the rail rises acceptably level **open-loop**,
with no IMU. This is also the rung that characterizes the *uncorrected* tilt — the baseline
the next phase needs.

**Build note (important for the next phase):** structure the sync as **independent targets
for Z1 and Z2 that happen to be equal**, not a single shared "both do N." Open-loop now means
the targets are identical. Next phase, IMU correction simply makes Z2's target slightly differ
from Z1's — an added input, not a rewrite.

**What to watch — distinguish mechanical from code issues:**
- *Consistent* tilt (same direction every lift) → a mechanical asymmetry (friction, belt
  tension, load distribution). This is what the IMU loop will correct next phase.
- *Random* tilt (varies run to run) → step skipping/slipping, usually step-rate or tension.
  Fix this mechanically or by slowing the rate **before** trusting the verticals — lost steps
  on one side corrupt position and can't be fully fixed by leveling later.
- Start the verticals **slow** under real gantry load; step-skipping is most likely to appear
  here, under actual weight. A buzz instead of motion = commanded faster than the load can
  accelerate; the fix is a slower start or a gentle acceleration ramp.

**Pass condition:** rail rises and the residual tilt is small and (ideally) consistent;
motion is clean under load.

---

### Rung 3 — Horizontal motor alone, as a positioning move

The single horizontal motor moves to a target position and back. Simpler than the verticals
(no sync partner).

**What it proves:** clean horizontal motion, and the start of thinking in **position** (a
target) rather than raw step counts.

**Pass condition:** horizontal axis reaches the target and returns, clean motion.

---

### Rung 4 — The full choreographed sequence (open-loop)

The end-goal motion, run open-loop: **lift (Z1 + Z2) → stop → horizontal move → stop.**

**What it proves:** the *sequence* and the *handoffs between phases* work. The IMU leveling
step will later slot in between lift-and-stop; for now this rung validates everything around
that slot so the leveling drops into a working sequence rather than a flaky one.

**Pass condition:** the sequence runs start to finish, each phase hands off cleanly to the
next, position is tracked throughout.

---

### Cross-cutting concerns — baked into every rung, not bolted on later

These belong in the scripts from the start; retrofitting them is painful.

- **Safety scaffolding (no exceptions):** set all EN pins to disabled as the very first action
  at boot (before GPIO float can enable a driver); set DIR to a known level before any enable;
  wrap every run so that any crash, exception, or Ctrl-C **disables all motors on the way out**.
  Never let an exception leave coils energized.
- **A motor abstraction:** one small "stepper" concept that knows its EN/STEP/DIR pins and can
  "step N times this direction at this rate" and "disable." Keeps every rung to a few readable
  lines and lets the higher rungs survive lower-level changes (MicroPython→C++ later, or the
  arrival of the second ESP32).
- **Step rate / acceleration:** start slow. A stepper commanded faster than it can accelerate
  the load skips steps silently (buzz, not motion), corrupting position. "Add a gentle
  acceleration ramp" is the fix if skipping appears — most likely on the loaded verticals.
- **Position tracking:** each script keeps a running step-count of where it thinks each axis is.
  This is the seed of the eventual coordinate system and how Rung 4 knows where "lifted" and
  "horizontal target" are. Cheap now, foundational later.
- **Independent vertical targets:** (restated for emphasis) Z1 and Z2 always addressed as two
  targets, equal for now, so the IMU correction plugs in next phase as a value change.

### Deliberately out of scope this phase

- **No IMU / leveling feedback.** Leveling is a closed loop *on top of* working motion. Build it
  only after open-loop motion is trustworthy, or you'll debug motion and feedback at once.
- **No hall/homing/sensor code.** Those arrive with the second ESP32 next phase.
- **No boom stick / 3rd dimension.** Future addition, out of scope for the current unit.

---

## Part 2 — The upcoming phase (sensors + closed-loop validation)

The next phase adds the second ESP32 and its sensors, then re-runs the motion from this phase
*with* sensing and feedback. Where this captures the existing plan rather than new design, it is
noted as such.

### 2a. Assembly of the second ESP32's sensors

A second ESP32 is dedicated to **positioning and leveling sensors**, keeping motor control
(ESP32 #1) and sensing (ESP32 #2) on separate controllers.

Sensors to assemble (per the existing plan):

- **Level sensing — IMUs.** MPU-6050 IMUs (on GY-521 breakout boards). Two IMUs, one at each
  end of the horizontal rail — needed for both data integrity and safety redundancy at this
  physical scale. Because multiple MPU-6050s share the same I2C address, a **TCA9548A I2C
  multiplexer** is required to resolve the address conflict.
- **End-stop / homing — hall effect + magnets.** A3144 hall effect sensors paired with
  6×3mm N35 neodymium disc magnets, used as position stoppers/reference points. (Hall sensing
  was chosen over StallGuard sensorless homing for precision on a gantry.)

> Open detail: exact mounting positions, wiring pinout for ESP32 #2, and the multiplexer
> channel assignments are to be specified when this phase begins. The component selections
> above are settled; their physical integration is the work of 2a.

### 2b. Testing the phase-1 motion *with* the new sensors

Re-run the motion validated in Part 1, now with sensing and feedback layered on:

1. **Hall + magnet homing/end-stops.** Verify each hall sensor reliably detects its magnet and
   that the system can establish a known reference position and respect end-of-travel limits —
   so motion is bounded and repeatable rather than open-loop step-counting alone.
2. **IMU level reading.** Verify both IMUs report rail tilt correctly through the TCA9548A
   multiplexer, and that the two readings agree (the basis for both data integrity and the
   safety-redundancy check).
3. **Closed-loop leveling correction.** Add the feedback loop that uses IMU tilt to drive a
   *differential* between the two verticals (Z2 target nudged relative to Z1) — exactly the
   "independent equal targets" structure built in Rung 2, now with the targets driven apart by
   the correction. Per the existing plan, this runs as **Path A** for v0/v1: ESP32 #2 (sensors)
   → ThinkCentre (computes correction) → ESP32 #1 (motors), reusing the validated serial
   pipeline. Path B (direct ESP32-to-ESP32 link) is reserved as a v2 upgrade if latency becomes
   limiting.
4. **Full sequence, closed-loop.** The Part 1 Rung 4 sequence, now with the leveling step active
   between lift and stop: lift → **level via IMU feedback** → horizontal move → stop.

**Why this order:** Part 1 measures the *uncorrected* behavior; this phase adds the sensing that
*knows* position and tilt, then the feedback that *corrects* it. The baseline tilt characterized
in Rung 2 tells you how much correction the leveling loop must actually deliver.

### Still beyond this phase

- Sensor fusion of the LiDAR + depth cameras, point-cloud assembly, and Three.js visualization
  (later phases of the overall plan).
- The boom stick / third spatial dimension.
- v2 scale-up (6ft × 6ft), machined/printed plates, and the possible direct ESP32-to-ESP32
  leveling link.
