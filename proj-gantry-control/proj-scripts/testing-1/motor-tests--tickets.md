
# Motor Testing



## Test series 1 -- 

### Testing Notes -- Jul 09, 2026

Example of how I am running each test file on ESP32-- Via the mpremote tool:

```bash
mpremote run someFile.py
mpremote run test2--z1z2-stepping.py
```

#### Test2 --
Initially:
INVERT = {"Z1": False, "Z2": False}
Then set to this which caused downwardm movement.
INVERT = {"Z1": True, "Z2": False}
Because the script's intention was to "GO_UP", We simply switch the values around:
INVERT = {"Z1": False, "Z2": True}
And now, script 2, when run, will cause upward travel of the horizontal beam.

This causes the horizontal bar to move down.


#### Test3 --


## Test Series 1 -- Tickets

Open-loop motion validation for ESP32 #1 (motor controller). No sensors, no
feedback this phase — the goal is to confirm the three motors move in the expected
sequence and directions, and to measure how well the two verticals hold the rail
level with **no** correction. Each test is a separate, standalone script; run them
in order, and don't advance until the current one passes.

**Scripts:**
`test0--hold-test.py` · `test1--z1z2-holding.py` · `test2--z1z2-stepping.py` ·
`test3--lift-lock-traverse.py`

**Wiring (locked, ESP32 #1) — EN / STEP / DIR.** TMC2209 EN is active-low
(0 = enabled/holding, 1 = disabled).

| Axis | EN | STEP | DIR |
|------|----|------|-----|
| Z1 (vertical) | 25 | 26 | 33 |
| Z2 (vertical) | 13 | 27 | 14 |
| X (horizontal) | 18 | 19 | 23 |

**Safety model shared by every script:** drivers come up disabled (EN driven high
at construction, so a floating boot pin can't enable a driver); every run is wrapped
in `try/finally` so any exit — normal, exception, or Ctrl-C — disables all motors.
No limit switches exist yet, so **you are the end-stop**: keep step counts within
known travel and a hand near the power switch.

---

## Test 0 — Three-Motor Hold (no motion)

**Script:** `test0--hold-test.py`

### What & why
Energize the selected drivers and hold — no stepping. This is the foundation of the
series: it validates the power / ground / thermal system under load **before** any
motion or timing complexity is introduced. Holding current is close to the worst case
for steady draw (a stationary rotor makes no back-EMF, so the driver delivers full set
current continuously), so if anything in the shared rails or grounds is marginal, it
shows here with nothing else to confuse the diagnosis.

### How
The script comes up with all drivers disabled, then enables the configured motors with
a few-ms **stagger** (so their inrush events don't stack into one surge), holds for a
fixed duration with a **1-second heartbeat**, and disables on exit. No STEP pulses.

Run it first with `MOTORS_TO_ENERGIZE = ["Z2"]` (your validated-pins channel) to confirm
the rewire/star-ground didn't break what worked, then `["Z1", "Z2", "X"]` for the real
three-motor hold.

### Physical checks
- Each energized shaft **locks** — resists a gentle hand-turn.
- **Heartbeat keeps counting** — no ESP32 reset/reboot.
- **3.3V rail steady** at the enable instant (meter if possible).
- After ~1 min, **touch-test** the drivers: warm is fine, a **hot outlier** flags a
  marginal connection or a current-set (VREF) error on that channel.

### Pass
All energized motors hold with torque, no reset, rails steady, drivers evenly warm.

---

## Test 1 — Z1 + Z2 Simultaneous Hold (no motion)

**Script:** `test1--z1z2-holding.py` · **Depends on:** Test 0

### What & why
Energize the two verticals **together** and hold. You've spun each motor individually,
but never powered both verticals at once — and in operation they're always an on/off
pair jointly holding the one rail. This proves the power/ground/thermal system carries
**both** verticals locked simultaneously, cleanly, before they're asked to move together
in Test 2. It's the pair-specific version of Test 0, isolating the electrical question
from any motion/sync question.

### How
Same shape as Test 0, restricted to Z1 + Z2: staggered enable, hold with a heartbeat,
guaranteed disable on exit. No stepping.

### Physical checks
- **Both shafts lock** (gentle hand-turn resists on each).
- **No reset** (heartbeat intact); **3.3V steady** at enable.
- **Even warmth** after ~1 min — no hot outlier between the two.
- **Gravity:** start the rail low; on the end-of-test disable, a non-self-locking drive
  may let the rail settle. Hand near power.

### Pass
Both verticals lock with torque, no reset, 3.3V steady, both drivers evenly warm.

---

## Test 2 — Z1 + Z2 Synchronized Stepping (open-loop lift)

**Script:** `test2--z1z2-stepping.py` · **Depends on:** Test 1

### What & why
Step the two verticals **together** to raise (then lower) the rail. First simultaneous
motion. It answers three things:

1. **Direction convention** — which DIR raises the rail, and crucially whether Z1 and Z2
   need the **same or opposite** DIR to move it the same way. Mirror-mounted verticals
   commonly need one **inverted**.
2. **Open-loop sync quality** — with no feedback, does the rail rise acceptably level?
   This measures your **open-loop tilt baseline**, the number the future IMU leveling
   loop must handle.
3. **Clean motion under real load** — where step-skipping is most likely to appear.

> **Racking:** if one vertical goes up while the other goes down (wrong inversion), the
> rail twists — belts strain, frame binds, steps skip. The **first move must be tiny** so
> you can see a rack and stop before anything is stressed.

### How
The stepper is extended with direction handling (logical up/down + per-motor invert flag)
and a `step_together()` that pulses both STEP pins in lockstep on one shared loop (simple
interleave — fine at these rates). The run is **there-and-back**: enable both → step a
small count **up** → dwell → step the same count **down** to start → disable. Up-then-back
means you never walk into a hard stop.

**Tuning (first runs):** start `STEPS` small (100) and `STEP_DELAY_US` slow (1200), then —
both wrong way → flip `UP_DIR_LEVEL`; they rack → set one motor's `INVERT` to `True`; a
motor buzzes → increase `STEP_DELAY_US` (slower) or add a ramp. Scale `STEPS` up only after
direction is confirmed.

### Physical checks
- Correct direction, **no racking** — both motors raise the rail.
- **Rail rises level-ish** — measure both ends; record residual tilt (your baseline).
  Consistent tilt → mechanical asymmetry the IMU will fix; random tilt/skipping → rate or
  tension, **fix now** (lost steps corrupt position permanently).
- **Returns to start** after the down move — confirms no lost steps.
- Drivers evenly warm, 3.3V steady, no reset.

### Pass
Both verticals raise the rail together in the correct direction, no racking, small/
consistent tilt, no skipping, and the rail returns cleanly to start.

---

## Test 3 — Full Sequence: Lift → Lock → Traverse

**Script:** `test3--lift-lock-traverse.py` · **Depends on:** Tests 1 & 2 (with vertical
direction/invert tuned)

### What & why
Run the unit's full choreography open-loop: the verticals **lift** the rail and **lock**
(stay energized, holding), then the horizontal motor **traverses** the carriage along the
now-stable rail, then everything returns. First time all three run in one sequence, and
first time you hit the real combined load — **two motors holding while one steps.**

Two things are proven: (1) the **sequencing/handoffs** (lift finishes and the verticals
lock before X starts; X finishes before the return), and (2) the **locked rail is a steady
reference** — the verticals hold without sag, shift, or back-drive while X positions
against the rail. If the rail moved while X ran, X would be positioning against a moving
target; locking is what prevents that.

### How
Reuses the direction-aware stepper and `step_together()` from Test 2 (carry over the tuned
`UP_DIR_LEVEL` and vertical `INVERT`). Enables all three (staggered, all holding), then:
**lift** Z1+Z2 up → dwell (locked) → **traverse** X out → dwell → X back → **lower** Z1+Z2
to start → disable all. Up-then-down and out-then-back return everything to the starting
position. `try/finally` disables all three on any exit.

### Physical checks
- **Verticals hold solid during the X traverse** — the rail does **not** sag, shift, or
  back-drive while X moves. (Watch both rail ends.) This is the core check.
- **X traverses smoothly** against the steady rail — no binding, no skipping.
- **Combined load stable:** 3.3V steady, no ESP32 reset, all three drivers evenly warm
  (no hot outlier) under the two-hold-one-step condition.
- **Clean handoffs** — the console phase prints confirm ordering (lift → lock → traverse →
  lower).
- **Everything returns to start** — rail height and carriage position back where they began
  (no lost steps anywhere).

### Pass
Verticals lift and lock, hold the rail steady through the entire X traverse, X moves
cleanly, the combined load is electrically stable, the handoffs are correctly ordered, and
the full sequence returns everything to its starting position.

---

## After this series

Passing Test 3 clears the way for the sensor phase: the second ESP32 with its MPU-6050
IMUs (via the TCA9548A multiplexer) for closed-loop leveling, and the A3144 hall sensors +
magnets for homing and end-of-travel limits — which is what removes the "you are the
end-stop" caveat that governs this whole open-loop phase.
