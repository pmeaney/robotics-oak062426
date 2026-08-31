# Gantry Control — System Design

The system design for the gantry control process: the goal and architecture, the shelf-config
computation (turning a shelf description into scan targets, and how steppers relate step counts
to real-world distance), and the safety model that guarantees the gantry never drives past a
limit switch.

> This document supersedes the "Test 7 v2" framing — this is not just a test, it's the system
> design for gantry control. The three source docs are combined below with their full content.

## Contents
- **Part 1 — Goal & Architecture** (formerly `test7v2--goal.md`)
- **Part 2 — Shelf Config Program** (formerly `shelf-config-program--spec.md`)
- **Part 3 — Safety Model** (formerly `gantry-safety-model.md`)

---

## Not yet implemented — calibration-vs-declared dimension check

**Status: planned, NOT in the current program(s).** Once we test **real distance vs steps**
(measure `steps_per_mm` — see Part 2's steps↔mm section), the setup program should compare the
**measured bounding box (converted to real-world units)** against the **dimensions the user
declared**, and warn if they're far off. Example message:

> "You said a 6 ft × 6 ft shelf — but these touch sensors are positioned at ~5 ft 9 in ×
>  5 ft 2 in. Confirm the shelf, the mounting, or the declared size."

This turns a silent mismatch (wrong YAML, shifted frame, mis-measured shelf) into an explicit
heads-up before any scanning runs on bad numbers. It depends on a trustworthy `steps_per_mm`,
which is why it waits until the real-distance-vs-steps test is done.
_(Reminder to run that real-distance-vs-steps test — possibly tomorrow.)_

---

# Part 1 — Goal & Architecture
*(source: `test7v2--goal.md`)*

### The one-line goal
Drive the gantries to specific (X, Y) positions derived from a shelf's dimensions (in a YAML
file), take a reading at each, and send the data back — with a one-time setup program that
calibrates the step counts first.

**Units: metric throughout** (mm for physical dimensions, steps for machine positions).

---

### Two programs, one split

#### 1. Runtime — command / response
The ESP32 holds a single `.py` file of functions. The PC tells it which to run; each function
may take an input and returns an output (status or result). No listener loop — request/response.

Commands the PC issues:
- **X axis motor:** move to a given step.
- **Y axis motors (Z1 + Z2):** move to a given step.
- **Take a reading** (LIDAR now; photogrammetry later).
- Each returns info back to the PC (status / result).

> A scan position is an **(X, Y) target**, so positioning the sensor commands **both** axes:
> the X motor for horizontal, the Y motors (Z1 + Z2 together) for vertical.

#### 2. Setup — calibration (one-time per install)
The PC tells the board: *"Calibrate yourself."* The board:
- Finds the overall rectangle (**bounding box**) by driving to the touch sensors.
- **First touch sensor = the limit** for that end. Also check the **second** one to record its
  **delta** (how out-of-square the pair is) — informational, not the limit.
- Sends the positional data (step counts) back to the PC.

The PC then:
- Knows the bounding box, and **updates the YAML** with it.

---

### From bounding box → per-cell scan positions (PC-side math)

The YAML already declares the shelf, e.g.:
> "5-row × 2-column shelf, equal spacing, 1830 mm tall × 1830 mm wide."

The PC then computes each cell's scan position:

1. Read the measured **bounding box** (step counts, X and Y) from calibration.
2. Read the **shelf layout** (rows, columns) from the YAML.
3. **Cell size in steps = box steps ÷ cell count per axis:**
   - `cell_w_steps = box_steps_x / columns`
   - `cell_h_steps = box_steps_y / rows`
4. **Each cell's bottom-center, in steps:**
   - X (center of column `c`, 0-indexed): `x = (c + 0.5) * cell_w_steps`
   - Y (bottom of row `r`, 0-indexed from the bottom): `y = r * cell_h_steps`
5. Result: one **(X, Y) bottom-center target per cell**, in steps — the grid the gantry visits.

> **Physical dimensions (mm) are NOT required to find the cell-center grid.** With equal
> spacing, the grid comes purely from box-steps ÷ cell-counts. The mm values are used for:
> (a) a **sanity check** (does measured travel match the declared size?), and (b) **sensor
> range** (telling the LIDAR / photogrammetry how far the shelf is). Keep them as reference
> and inputs, not as a dependency of the cell math.

### Why bottom-center
Each cell's bottom-center is the **start location for that cell's scan** — where the LIDAR
(and eventually photogrammetry) begins for that cell. One bottom-center per cell → the gantry
visits each (X, Y) in turn and scans.

---

### Where the work lives (brain / hands)
- **Board (hands):** one `.py` file of functions — move-to-step (X and Y), read sensors, run
  the calibration measurement, return raw numbers. No coordinate math, no YAML.
- **PC (brain):** owns the YAML, does all the math (bounding box → steps-per-cell →
  per-cell (X, Y) bottom-center targets), decides what to command, records results.

### Transport (near term vs later)
- **Now (bench):** command the board over USB serial — request/response, one function per call.
- **Later (remote):** the same request/response model over the network (WiFi), so updates and
  commands can be pushed to customer sites without visiting — serial is the workbench, the
  network is the destination.

---

## Implementation Plan

### Architecture (decided)
```
Remote (SSH, later maybe a web UI)  ->  on-site Linux PC  ->  USB serial  ->  ESP32  ->  motors
```

Remote access is solved at the **SSH-to-the-PC** layer, which is free and rock-solid. Once
you're on the on-site PC you're local to the ESP32 over the USB cable. So **the ESP32 never
needs to be network-aware** — no WiFi, sockets, MQTT, or live link. It stays the dumbest
possible thing: take a command over the cable, move, report done.

This closes the transport question: **use mpremote to drive the board (request/response).**
No listener loop, no `kbd_intr`, no escape hatch, no sockets — none of the things that caused
the v1 trouble.

### Why request/response is enough
- The ESP32 only runs motors to a location and reports status. It needs no live info.
- The **LIDAR is connected to the on-site PC directly**, not the ESP32. It fires *after* a
  move completes.
- Sequencing is **move → wait for "done" → scan**: the move function **blocks until the motor
  arrives, then returns `"done"`**. The PC sees `done`, then fires the LIDAR. No timing
  estimates, no polling.
- Prototype scale (even ~10 customers) doesn't need streaming, a fixed command vocabulary, or
  fleet tooling. Those are 10+ / hardening concerns for later — handled at the SSH/PC layer if
  ever, still not on the ESP32.

### The pieces

#### Board (ESP32) — one file: `robot.py`
A passive library of clean functions (imported and called; never loops, can't lock the board):
- `move_x(step)` — move X to an absolute step; block until arrived; return status.
- `move_y(step)` — move Y (Z1 + Z2) to an absolute step; block until arrived; return status.
- `home_and_measure()` — run the calibration measurement (first-touch limits + 2nd-touch
  delta); return the raw step counts.
- `status()` — report current state / switch readings.
Each **returns a value** (status or result); the caller prints it. No coordinate math, no YAML.

#### On-site PC (brain) — Python
- Owns `prototype-shelf.yaml`, all coordinate math, sequencing, and results.
- Drives the board via mpremote, e.g. `mpremote exec "import robot; print(robot.move_x(500))"`.
- Calibration: calls `home_and_measure()`, gets step counts, computes the bounding box, writes
  it to the YAML.
- Scan run: computes each cell's (X, Y) bottom-center (box-steps ÷ cell-counts), then per cell:
  `move_x` -> `move_y` -> wait for `done` -> fire the LIDAR (PC-side) -> record.

#### Remote
SSH to the on-site PC. Push updates with `mpremote fs cp robot.py`. Nothing on the ESP32
changes. Every customer site is the same code.

### Design rule to keep
Keep `robot.py` as clean functions with clear inputs and returned values (no scattered
side-effect prints). If a different transport is ever needed, the same functions get called by
a small dispatcher — swap the transport, keep the logic.

### Next step
Write `robot.py` (the real board-side library) — then the PC-side driver — and move on to the
LIDAR scans.

---

# Part 2 — Shelf Config Program
*(source: `shelf-config-program--spec.md`)*

A PC-side (on-site Linux) interactive script that asks the operator to describe a shelf, then
computes the **bottom-center of every cell** — the (X, Y) scan positions the gantry visits.
No hardware, no serial: pure computation. It turns "here's my shelf" into a list of targets.

---

### What the script does

1. **Prompt the operator** for the shelf parameters (below).
2. **Normalize units** — accept ft / in / cm / mm, convert everything to **mm** internally
   (the machine stays metric). The operator may *describe* shelves in imperial.
3. **Compute each cell's bottom-center** as (X, Y), using the measured bounding box in steps
   plus the row/column counts.
4. **Output** the list of per-cell bottom-center targets (and the intermediate values, so the
   operator can sanity-check).

### Prompts (what it asks the user)

- **Shelf outer measurements** — width and height, each with a **unit** (ft, in, cm, mm).
- **Columns and rows** — how many cells across (columns) and up (rows).
- **Structural width** — the thickness of the shelf structure on the **face that faces the
  horizontal gantry** (e.g. cardboard ¼", wood 2"). Captured now; see "equal-dimensions"
  default below for how it's used in v1.

> **Tell the user, on screen:** the current default assumes **equal-dimension cells** (every
> cell the same size). Custom / non-uniform cell widths are a **future version** — v1 just needs
> to prove it can accept two different prototype shelf sizes and place the scan points correctly.

### The two prototype shelves this must handle (illustration targets)

| # | Outer size | Columns × Rows | Structural width (front face) | Notes |
|---|-----------|----------------|-------------------------------|-------|
| A | 18 in × 12 in | 1 col × 2 rows | 1/4 in (cardboard) | small bench prototype |
| B | 6 ft × 6 ft | 3 cols × 4 rows | 2 in | larger prototype |


---

### The calculation (equal-dimension cells)

Inputs:
- Measured **bounding box in steps** from calibration: `travel_x`, `travel_y`.
- **columns**, **rows** from the operator.

Grid (steps come straight from the box; physical mm not needed to place the gantry):
```
cell_w_steps = travel_x / columns
cell_h_steps = travel_y / rows
```

Each cell's **bottom-center**, 0-indexed (column c from left, row r from bottom):
```
x = (c + 0.5) * cell_w_steps      # horizontal center of the column
y =  r        * cell_h_steps      # bottom edge of the row
```

Output: one `(x_steps, y_steps)` per cell = the scan start point for that cell (where the
LIDAR / photogrammetry begins).

### Role of the physical dimensions (mm)
Not required to place the gantry (the step grid comes from box ÷ counts). They are used for:
- **Sanity check** — does the measured box match the declared physical size?
- **Sensor range** — telling the LIDAR / photogrammetry how far the shelf is.
- **Structural width** — reserved for a future version that subtracts divider thickness so
  centers sit in the open cavity. **v1 ignores it for placement** (equal-dimension default),
  but captures it so v2 can use it.

### Relating shelf dimensions to the stepper motors (steps ↔ real-world mm)

The shelf is described in the real world (ft / in / cm / mm), but the gantry only knows
**steps**. What lets us tie the two together is a property of stepper motors: **a stepper moves
a fixed, repeatable distance per step.** Each step advances the shaft a fixed angle, and through
the belt + pulley that becomes a fixed distance the gantry travels. So one constant bridges the
two worlds:

```
mm    = steps / steps_per_mm
steps = mm * steps_per_mm
```

This is why a stepper can effectively *measure* real-world distance: count the steps between two
known physical points and you have measured the distance between them (in steps), which converts
to mm once `steps_per_mm` is known.

#### Getting `steps_per_mm`
- **Theoretical (from the mechanics):**
  `steps_per_mm = (motor_steps_per_rev * microsteps) / (pulley_teeth * belt_pitch_mm)`.
  Our belt/pulley is the **Zeelo GT2** kit — GT2 = **2 mm** tooth pitch, **20-tooth** pulleys,
  so **20 * 2 = 40 mm per revolution**. With a NEMA 17 (200 steps/rev):

  | Microsteps | steps/rev | steps_per_mm |
  |-----------:|----------:|-------------:|
  | 8          | 1600      | 40.0 |
  | 16         | 3200      | 80.0 |
  | 32         | 6400      | 160.0 |

  > Our rough measured value (~40 steps/mm, from 100 steps ≈ 2.5 mm) matches the **8×** row —
  > a good sign the mechanics are as specified. Confirm the TMC2209 microstep setting to lock it.

- **Measured (preferred, trusts reality):** command a known step count, measure the mm moved
  with a ruler: `steps_per_mm = steps_commanded / mm_measured`.
- **Best (endstop-anchored):** we already measure the step count between the two physical
  endstops during calibration (`travel_x`, `travel_y`). Tape-measure the physical distance
  between those same endstops once → `steps_per_mm = travel_steps / travel_mm`. A real,
  per-machine constant anchored to physical reference points.

#### The honest caveat: open-loop has no feedback
The gantry **assumes** it moved N steps' worth of distance; it doesn't *know*. The constant
holds only while no steps are skipped (stall, belt slip) and the mechanics stay rigid. This is
exactly why we **calibrate against the switches**: a physical switch gives ground truth at the
limits, re-anchoring position instead of blindly trusting the step count.

#### Why placement itself doesn't need mm
Because equal-dimension cell centers come from dividing the **step**-box by cell counts (all in
steps), the gantry can be positioned with no mm conversion at all. The steps↔mm relationship is
needed only to **talk to the physical world**: sanity-checking the measured box against the
declared shelf size, and telling the LIDAR / photogrammetry how far the shelf is.

### Scope (v1 vs later)
- **v1 (this):** equal-dimension cells; accept the two prototype shelves; convert imperial →
  mm; output bottom-center targets in steps. Illustration that two different shelf sizes work.
- **later:** custom / non-uniform cell widths, subtracting structural width from the usable
  cavity, and the min-cell-height rule for auto row/column counts.

### Where it fits
This is the PC (brain) turning the calibration's bounding box + the operator's shelf
description into the (X, Y) scan grid. The gantry (hands, `gantry_positioner.py`) then visits
each (X, Y) via `move_x` / `move_y`, and the PC fires the LIDAR at each stop.

---

# Part 3 — Safety Model
*(source: `gantry-safety-model.md`)*

How we guarantee the gantry never drives past a limit switch — our original approach, how
Marlin (mature 3D-printer firmware) solves the same problem, and the revised combined model we
adopt (top).

---

## Revised Approach — ADOPTED (ours + Marlin combined)

The guarantee that a switch is never driven past is **physical and lives on the board**; the
software layers above it mean that guarantee is almost never exercised in normal operation.
Four layers, outermost = last resort:

1. **Not-homed lockout (board).** Position is `None` until a calibration/home runs. `move_x`/
   `move_y` refuse with `ERR nohome` before then. An un-homed axis cannot move *at all* —
   stricter than Marlin, which allows un-homed moves toward the switch. Right call for a
   scanning robot that never needs manual jogging.

2. **PC soft limits (brain, YAML).** The PC knows the measured bounding box and only ever
   commands targets **inside** `[buffer, travel − buffer]` (~5 mm inset). Normal moves never
   even approach a switch. Primary guard; does the work ~all the time.

3. **Board range check (`ERR outofrange`) + board-side buffer.** `move_*` refuses any target
   outside `[0, travel]` — and, belt-and-suspenders, refuses targets within a buffer of a
   limit too. So even if the PC math is wrong, the board rejects the bad command *before
   moving*. Catches a buggy brain.

4. **Per-step hardware reflex (board).** Every step, before pulsing, the move checks the limit
   switch in the direction of travel. If it trips, the motor **stops that step**, position is
   marked lost (`_pos = None`), and it returns `ERR fault <switch>`. This is the 100%
   guarantee: the motor physically cannot drive through a switch. Worst case is ~1 step of
   overtravel *onto* the switch (into its mechanical over-travel), never *past* it.

**Key philosophy (from Marlin, adopted):** in normal operation a hardware switch should
**never** be touched. If one trips during a move, something already went wrong upstream — so
the correct reaction is **halt + treat position as lost + require re-home**, not "nudge and
continue." Our `ERR fault` does exactly this.

**Homing back-off (kept):** after homing, back off the switch (~`BACKOFF_STEPS`) *before*
setting zero, so the first real move doesn't re-trigger the switch. Marlin learned this the
hard way (`X_HOME_BUMP_MM`); we already do it.

**Never target a limit exactly:** the usable range is `[buffer, travel − buffer]`, never `0`
or `travel` exactly — otherwise a move to that coordinate kisses the switch. The buffer inset
lives on the PC; the board buffer (layer 3) is the backstop.

---

## Our Original Approach

Two protections, split by layer:

- **Soft limits (PC/YAML):** the PC computes cell targets inside the bounding box and never
  sends an out-of-bounds command. Primary guard — but only as good as the PC math + YAML
  values; a bug there could command past the wall. Not a 100% guarantee on its own.
- **Hard limits (board):** the move loop checks the endstop every step; a trip aborts the move
  and reports a fault. This is the physical backstop that makes it actually safe regardless of
  what the PC believes.
- **Not-homed refusal (board):** `move_*` returns `ERR nohome` until a home establishes zero.
- **Range check (board):** `move_*` returns `ERR outofrange` for targets outside `[0, travel]`.

Correct in shape, but the buffer/inset discipline and the "unexpected hit = re-home" reaction
weren't fully spelled out.

---

## Marlin's Approach (mature 3D-printer firmware)

Arrived at over years of bug reports; validates the layered model.

- **Software endstops (primary):** "moves will be clipped to the physical boundaries from
  [XYZ]_MIN_POS to [XYZ]_MAX_POS." The machine never generates a move past the box. ≈ our PC
  soft limit / `ERR outofrange`.
- **Hardware endstops (backstop):** electrically wired switches that cut movement when the
  physical limit is met.
- **"Unexpected hardware hit = something already failed."** Their conclusion: "The software
  endstops should have prevented that the hardware endstops could have been hit... The right
  reaction on an unexpected hardware endstop hit is to stop the current and all further moves."
  A hardware hit after homing means lost steps / a bug → halt, don't continue. ≈ our `ERR
  fault` + position-lost.
- **Homing back-off (`X_HOME_BUMP_MM`):** back off the switch before setting the min position,
  or returning there re-triggers it (issue #3886).
- **Don't arm a soft limit exactly at the switch (issue #2948):** returning to that coordinate
  would re-trigger the hardware endstop. → keep targets inset from the limit.
- **"Not homed = restricted movement" (issue #927):** use a homed flag; don't allow free
  motion (especially toward a switch) until homed. We take the stricter version: no motion at
  all until homed.

---

### One-line summary
The **switch is respected 100% by the per-step hardware reflex on the board** — the same
mechanism a decade of 3D printers rely on. The PC soft limits, board range check + buffer, and
not-homed lockout are the layers that ensure that backstop is essentially never reached in
normal operation.

---

# TODO / Roadmap (this iteration and beyond)

## Open parameters for THIS iteration (not yet specified)
- **Vertical scan increment.** At a cell's bottom-center home, the gantry raises Y by a fixed
  increment between LIDAR readings. Value is **TBD** — likely ~1/2 in, adjustable. Comes from
  the YAML spec or the operator. (2D LIDAR + incremental raises = a stack of slices per cell.)
- **Cell "safe top" standoff.** The inner scan loop stops short of the cell's physical top by a
  **standoff = the shelf beam structure width** (¼ in cardboard on the small prototype; ~1–2 in
  on the larger). Adjustable per customer shelf. Prevents scanning into / hitting the structure.

## Next build steps (in order)
1. **Gyro integration.** Basic stabilization to keep the horizontal gantry level — in service of
   LIDAR accuracy (a tilted beam degrades the reading), not a feature for its own sake.
2. **Per-cell scan loop** (the new core behavior):
   - **Outer loop:** visit each cell's **bottom-center** ("cell home").
   - **Inner loop at cell home:** repeat { take a 2D LIDAR reading (PC ← LIDAR over USB) →
     transmit to PC → raise Y by the scan increment } until the **safe top** (top − standoff).
   - The PC accumulates the stack of 2D slices per cell.

## "System done" for this iteration
Gantry control + basic gyro leveling (level horizontal beam for LIDAR accuracy) + LIDAR
positioning: cell-home → incremental upward moves → repeated capture-and-transmit per cell.

## Then: a SEPARATE, later system (out of scope here)
Map shelf dimensions + LIDAR data into a **basic 3D representation** — (A) the shelf, (B) the
contents (from LIDAR), optionally the stopper/endstop locations — rendered in **Three.js**.
Relatively basic 3D diagram; assembled from the per-cell slice stacks.

---

# Project Recap — Where We've Been and Where We're Going

A narrative of the whole arc, for context: how we built up electronics familiarity, why this
system-design phase exists, and the sequence that carries us to a finished scanning system.

## What we've done so far
- **Tested one NEMA stepper motor** — the first, minimal proof.
- **Tested three NEMA motors together — blew a fuse, then redesigned the fuse system.** The
  three-motor load exposed a weakness in the original protection scheme; we reworked it.
- **Tried Hall-effect sensors as endstops, then decided against them.** Archived those docs and
  programs rather than delete them.
- **Chose mechanical touch sensors instead.** Tested them, wired them up, connected them, and
  proved their software and hardware end-to-end.
- **Now, with familiarity built** across Test Sets 1–3 (motors, Hall sensors, touch sensors), we
  **revisit the system goals and architecture** — this document — to define the current
  iteration's design, parameters, spec, and programs.

## Where we're going (this iteration)
- **Integrate the gyro sensor** for basic stabilization — keeping the horizontal gantry level,
  which matters for LIDAR accuracy (a tilted beam degrades the reading).
- **Iterate the program around the per-cell scan pattern.** Each cell's **bottom-center is its
  "home."** From home, the gantry moves up by an increment (TBD — perhaps ~½"), takes another
  LIDAR reading (the system is 2D LIDAR), and transmits it to the PC. The PC accumulates a set of
  readings per cell. (Later, those become an approximate 3D rendering.) So this iteration adds
  two things together: **(A) gyro leveling** and **(B) incremental-move readings from each
  cell's home.**
- **The scan loop, per cell:**
  1. Arrive at the cell's home (bottom-center).
  2. Begin the reading loop: take a LIDAR reading (the PC connects to the LIDAR directly by USB),
     transmit it, then raise the gantry by an increment (from the YAML spec or the operator —
     our gantry-control program performs the move).
  3. Repeat until reaching the **safe top** of the cell — i.e. with a standoff equal to the
     shelf beam structure width (¼" cardboard on the small prototype; ~1–2" on the larger).
     That standoff is an adjustable variable set by the customer's shelf size.

## "System done" for this iteration
At that point the system has: **gantry control**, **basic gyro stabilization** (level horizontal
gantry, for LIDAR accuracy), and **LIDAR positioning** — cell home, then incremental upward moves
to repeatedly capture and transmit LIDAR data.

## The next system (separate, later)
Map the shelf dimensions and LIDAR data into a **basic 3D representation**: (A) the shelf, and
(B) its contents (from the LIDAR data) — and we could even include the stopper/endstop locations
in the rendering. A relatively basic 3D diagram in **Three.js**, assembled from the per-cell
reading stacks.
