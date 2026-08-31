# Shelf Config Program — Spec

A PC-side (on-site Linux) interactive script that asks the operator to describe a shelf, then
computes the **bottom-center of every cell** — the (X, Y) scan positions the gantry visits.
No hardware, no serial: pure computation. It turns "here's my shelf" into a list of targets.

---

## What the script does

1. **Prompt the operator** for the shelf parameters (below).
2. **Normalize units** — accept ft / in / cm / mm, convert everything to **mm** internally
   (the machine stays metric). The operator may *describe* shelves in imperial.
3. **Compute each cell's bottom-center** as (X, Y), using the measured bounding box in steps
   plus the row/column counts.
4. **Output** the list of per-cell bottom-center targets (and the intermediate values, so the
   operator can sanity-check).

## Prompts (what it asks the user)

- **Shelf outer measurements** — width and height, each with a **unit** (ft, in, cm, mm).
- **Columns and rows** — how many cells across (columns) and up (rows).
- **Structural width** — the thickness of the shelf structure on the **face that faces the
  horizontal gantry** (e.g. cardboard ¼", wood 2"). Captured now; see "equal-dimensions"
  default below for how it's used in v1.

> **Tell the user, on screen:** the current default assumes **equal-dimension cells** (every
> cell the same size). Custom / non-uniform cell widths are a **future version** — v1 just needs
> to prove it can accept two different prototype shelf sizes and place the scan points correctly.

## The two prototype shelves this must handle (illustration targets)

| # | Outer size | Columns × Rows | Structural width (front face) | Notes |
|---|-----------|----------------|-------------------------------|-------|
| A | 18 in × 12 in | 1 col × 2 rows | 1/4 in (cardboard) | small bench prototype |
| B | 6 ft × 6 ft | 3 cols × 4 rows | 2 in | larger prototype |


---

## The calculation (equal-dimension cells)

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

## Role of the physical dimensions (mm)
Not required to place the gantry (the step grid comes from box ÷ counts). They are used for:
- **Sanity check** — does the measured box match the declared physical size?
- **Sensor range** — telling the LIDAR / photogrammetry how far the shelf is.
- **Structural width** — reserved for a future version that subtracts divider thickness so
  centers sit in the open cavity. **v1 ignores it for placement** (equal-dimension default),
  but captures it so v2 can use it.

## Relating shelf dimensions to the stepper motors (steps ↔ real-world mm)

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

### Getting `steps_per_mm`
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

### The honest caveat: open-loop has no feedback
The gantry **assumes** it moved N steps' worth of distance; it doesn't *know*. The constant
holds only while no steps are skipped (stall, belt slip) and the mechanics stay rigid. This is
exactly why we **calibrate against the switches**: a physical switch gives ground truth at the
limits, re-anchoring position instead of blindly trusting the step count.

### Why placement itself doesn't need mm
Because equal-dimension cell centers come from dividing the **step**-box by cell counts (all in
steps), the gantry can be positioned with no mm conversion at all. The steps↔mm relationship is
needed only to **talk to the physical world**: sanity-checking the measured box against the
declared shelf size, and telling the LIDAR / photogrammetry how far the shelf is.

## Scope (v1 vs later)
- **v1 (this):** equal-dimension cells; accept the two prototype shelves; convert imperial →
  mm; output bottom-center targets in steps. Illustration that two different shelf sizes work.
- **later:** custom / non-uniform cell widths, subtracting structural width from the usable
  cavity, and the min-cell-height rule for auto row/column counts.

## Where it fits
This is the PC (brain) turning the calibration's bounding box + the operator's shelf
description into the (X, Y) scan grid. The gantry (hands, `gantry_positioner.py`) then visits
each (X, Y) via `move_x` / `move_y`, and the PC fires the LIDAR at each stop.
