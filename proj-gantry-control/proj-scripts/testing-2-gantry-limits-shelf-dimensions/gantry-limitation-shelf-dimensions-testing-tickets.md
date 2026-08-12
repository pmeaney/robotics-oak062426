# Gantry Limitation & Shelf-Dimensions — Testing Tickets

Test ladder for endstop bring-up through shelf-cell scan-path generation.
Follow in order — each ticket assumes the prior one passed.

## Conventions

**Endstop naming** (six A3144 Hall sensors):

| Name | Location | GPIO |
|------|----------|------|
| Z1T | Z1 vertical — top | 35 |
| Z1B | Z1 vertical — bottom | 34 |
| Z2T | Z2 vertical — top | 5 |
| Z2B | Z2 vertical — bottom | 15 |
| XZ1 | Horizontal (X) endstop at the Z1 vertical | 32 |
| XZ2 | Horizontal (X) endstop at the Z2 vertical | 4 |

`XZ1` / `XZ2` name the horizontal (X) endstops by which vertical they sit at (Z1 / Z2), not left/right — the label doesn't flip when the device is viewed from another side. The horizontal axis itself is still `X1` (used in Tickets 3–4).

> XZ1=32 / XZ2=4 is provisional — the two horizontal ends are symmetric, so confirm which physical end trips which channel during Ticket 1 and swap the two labels if reversed.

> **GPIO map confirmed** against the physical wiring (channels ch1–ch6 = 34 / 35 / 36 / 39 / 32 / 4).

**A3144 behavior (read before Ticket 1):**
- **Unipolar switch** — trips on one magnetic polarity only. If a magnet won't trip a sensor, *flip the magnet* before suspecting a wiring fault.
- **Active-low with the 10kΩ pull-up** — idle reads `1` (no field), detected reads `0` (field present).
- Per-channel conditioning already in place: 10kΩ pull-up, 1kΩ series, 10nF filter cap, 0.1µF decoupling.

**Zone color model** (defined/measured in Ticket 3, used onward):

| Zone | Meaning |
|------|---------|
| 🟢 Green | Normal full-speed operating band |
| 🟡 Yellow | Stopping zone — decelerate / halt |
| 🟠 Orange | Buffer — hard no-go margin |
| 🔴 Red | Point of potential mechanical damage |

---

## Ticket 0 — Pin map + first-sensor sanity check

**Depends on:** sensors physically installed (done).
**Goal:** Lock the ESP32 ↔ breadboard pin map for the six A3144 channels, then prove one channel end-to-end before scaling to all six.

### Part A — Assign the pins

Pins chosen to avoid the locked motor pins (25/26/33, 13/27/14, 18/19/23), the I2C bus reserved for the GY-521 (21/22), the flash pins (6–11), the USB/REPL pins (1/3), and the boot-strapping pins (0/2/12/15 — a Hall idling high through the 10kΩ pull-up on GPIO12 can block boot).

| Endstop | GPIO | Why |
|---------|------|-----|
| Z1T | 35 | input-only — fine here, channel already has an external 10kΩ pull-up |
| Z1B | 34 | input-only |
| Z2T | 5 | input-only |
| Z2B | 15 | input-only |
| XZ1 | 32 | full-capability GPIO |
| XZ2 | 4  | full-capability GPIO |

Per channel, confirm at the breadboard:
- **Signal** (node A, at the pull-up / after the 1kΩ series) → the assigned GPIO above.
- **Vcc** → 3.3V rail.
- **GND** → **main GND rail** — *not* the filtered signal node B. (This was a prior wiring fault; re-verify it here.)

**Part A done when**
- [ ] Pins above confirmed against the physical wiring (edit the table if any channel differs).
- [ ] Each channel's GND lands on the main rail, verified by eye/continuity.

### Part B — First A3144, by itself (Z1B)

Read a single channel live and confirm a clean transition before touching the other five.

```python
# test0--z1b-single-read.py
# Ticket 0, Part B -- single A3144 channel, live read.
# Run: mpremote run test0--z1b-single-read.py
#
# GPIO34 = Z1B (Z1 vertical, bottom). Input-only pin; the channel already
# carries an external 10k pull-up, so no internal pull is set here.
# A3144 is active-low: idle = 1 (no field), magnet present = 0.

from machine import Pin
import time

NAME = "Z1B"
GPIO = 34

sensor = Pin(GPIO, Pin.IN)

def label(v):
    return "(magnet)" if v == 0 else "(idle)"

print("Reading {} (GPIO{}). Idle=1, magnet=0. Ctrl-C to stop.".format(NAME, GPIO))

v = sensor.value()
print("  start: {} = {} {}".format(NAME, v, label(v)))   # confirms read path is live
last = v

try:
    while True:
        v = sensor.value()
        if v != last:                       # print only on edges
            print("  {} = {} {}".format(NAME, v, label(v)))
            last = v
        time.sleep_ms(50)                   # ~20 Hz poll
except KeyboardInterrupt:
    print("stopped")
```

**Part B procedure**
1. Run the script. The `start:` line should read `Z1B = 1 (idle)` immediately — that alone proves the read path (sensor → conditioning → GPIO → REPL) is live.
2. Bring a magnet to the Z1B sensor face — expect a single clean flip to `0 (magnet)`.
3. Withdraw — expect a single clean flip back to `1 (idle)`.
4. Watch for chatter (rapid 1/0 flips at the threshold). None expected — the 10nF filter + 0.1µF decoupling should keep the edge clean.
5. If it never trips, flip the magnet polarity before suspecting the wiring.

**Part B done when**
- [ ] Z1B idles at `1`, trips to `0` on magnet, returns to `1` on withdraw.
- [ ] No chatter at the threshold.
- [ ] Confidence that the read path (sensor → conditioning → GPIO → REPL) is sound before Ticket 1 scales it to all six.

---

## Ticket 1 — Individual A3144 bring-up (one sensor at a time)

**Depends on:** Ticket 0.
**Goal:** Confirm each of the six Hall sensors reports a clean, repeatable state change to a magnet, before any of them feeds motion logic.

**Procedure**
1. Run a live-read script that prints sensor state to the terminal at a steady rate (~5–10 Hz), each channel labeled by name.
2. For each sensor in turn — **Z1T, Z1B, Z2T, Z2B, XZ1, XZ2** — watch the idle reading (expect `1`), then slowly bring a magnet toward the sensor face until the value flips to `0`. Withdraw and confirm it returns to `1`.
3. Repeat with **different magnet strengths, sizes, and proximities**. Record roughly the distance / magnet type at which each sensor reliably trips.
4. If a sensor never trips, **flip the magnet** and retry before suspecting a fault.
5. Keep a little extra space between magnet and sensor face — stay well clear of physical contact (informal "red zone" here; formal zones come in Ticket 3).

**Done when**
- [ ] All six sensors show a clean `1 → 0 → 1` transition with no chatter/bounce at the threshold.
- [ ] Approximate reliable trip distance recorded per sensor, for the magnet you intend to actually mount.

---

## Ticket 2 — Endstop use-case test (per axis end + walk-back)

**Depends on:** Ticket 1.
**Goal:** Exercise each endstop in its real role — detect end-of-travel, then "walk back" the gantry that got too close.

**Sensors under test:** Z1T, Z1B, Z2T, Z2B, XZ1, XZ2.

**Procedure (per endstop)**
1. Command slow motion toward the endstop.
2. On trip (state → `0`), immediately stop the axis.
3. **Walk back:** reverse in small fixed increments until the sensor releases (state → `1`), then a little further for clearance.
4. Log: position/steps at trip, steps to release, final parked offset.

**Cases**
- Each vertical end individually: Z1T, Z1B, Z2T, Z2B.
- Horizontal gantry ends: XZ1, XZ2.
- Z1 + Z2 together — confirm each triggers/stops independently and the walk-back keeps them synced (remember the Z1 direction inversion from the mirror mount).

**Done when**
- [ ] Every endstop stops its axis on trip and cleanly walks back to a released, safe park.
- [ ] No axis overshoots into physical contact.
- [ ] Z1/Z2 stay synchronized through trip + walk-back.

---

## Ticket 3 — Zone characterization (green / yellow / orange / red)

**Depends on:** Ticket 2.
**Goal:** Convert raw trip points into a calibrated safety-zone map per axis (Z1, Z2, X1).

**Procedure**
1. For each axis, measure the usable travel between the **distal ends of the green zone** — the green-to-green span for Z1, Z2, and X1.
2. From each endstop trip point, define the offsets for:
   - 🟡 **Yellow** — where deceleration / stop begins.
   - 🟠 **Orange** — hard no-go buffer between stop and damage.
   - 🔴 **Red** — contact / potential damage.
3. Record each boundary as a per-axis distance and/or step count.
4. **Test each zone:** drive toward an end and confirm the controller respects yellow (stops), never enters orange under normal motion, and never reaches red.

**Done when**
- [ ] Green-zone span documented for Z1, Z2, X1.
- [ ] Yellow / orange / red boundaries defined per end and verified in motion.

---

## Ticket 4 — Center-find, shelf-dimension generation, and cell scan-path output

**Depends on:** Ticket 3 (green zones calibrated).
**Goal:** Use the green zones to center the gantry, generate shelf + cell geometry from user input, find each cell's bottom-center, build a vertical scan path per cell, and emit a data object for browser 3D reconstruction.

**Steps**
1. **Center-find** — using the green-zone spans, compute and move the horizontal gantry to system center on the **Y** and **X** axes.
2. **Shelf dimension input + generation**
   - User inputs: overall **height**, **width**, **number of columns**, and **shelf material width** (e.g. 1/2" or 3/4" wood).
   - Generate outer shelf dimensions → columns → **cells**. Assume equal cell distribution.
3. **Per-cell bottom-center** — from the generated geometry, compute and have the horizontal gantry find the bottom-center of each cell.
4. **Vertical scan path** (extend the cell-dimension function, or add a second function)
   - From each cell's bottom-center, step the gantry upward at a fixed increment (e.g. 1/4"): bottom-center zero scan → +1/4" scan → +1/4" scan → … → top-center zero scan.
5. **Output** — emit a single data object containing:
   - the shelf dimensions, and
   - per cell, the ordered list of scan locations,
   - structured so a browser (Three.js) can reconstruct a low-res 3D shelf diagram.

**Done when**
- [ ] Gantry centers reliably within the green zone on X and Y.
- [ ] Given user dimensions, output shows correct shelf → column → cell geometry (equal distribution).
- [ ] Each cell has a bottom-center and an ordered bottom→top scan-location list at the chosen increment.
- [ ] Output object round-trips into a 3D shelf render in the browser.
