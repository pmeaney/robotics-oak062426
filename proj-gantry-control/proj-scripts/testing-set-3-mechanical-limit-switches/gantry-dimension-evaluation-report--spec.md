# Gantry Dimension Evaluation Report — Spec

A **commissioning sanity check**: before trusting the machine to scan, prove its *measured*
reality matches the operator's *declared* shelf, within tolerance. If they diverge too much, the
LIDAR-built 3D representation would be inaccurate — so this report is how we gain confidence the
system will produce accurate scans. Run it, read the deltas, adjust, re-run until it passes.

**Status: planned, NOT yet implemented.** Hard dependency below.

---

## Hard dependency: `steps_per_mm`
The two things being compared are in **different units**:
- Declared shelf = **mm** (operator's assumptions).
- ESP32 calibration = **steps** (machine's measured travel between endstops).

They can only be compared once we know **`steps_per_mm`** (the bridge). That constant comes from
the real-distance-vs-steps test (see the system-design doc's steps↔mm section) — **not measured
yet.** Until it is, this report cannot compute a physical (mm) error, only a meaningless step
delta. So: **measure `steps_per_mm` first, then this report becomes real.**

## Where it sits in the flow
1. **Shelf config program** — operator declares the shelf (assumptions, mm). Computes cell grid.
2. **ESP32 calibration** (`home_and_measure`) — machine measures travel + squaring deltas (steps).
3. **`steps_per_mm`** — measured once (the bridge).
4. **THIS report** — convert measured steps → mm, compare to declared mm, flag deltas beyond
   tolerance, print a verdict.

> Order note: the operator's shelf assumptions come first (step 1), the machine's measured
> reality second (step 2). The report grades reality against assumptions.

---

## What it checks (BOTH — decided)

### 1. Overall size
Declared box (shelf outer size → mm) vs measured box (travel_steps × steps_per_mm → mm), per axis.
- Catches: wrong declared size, shifted/mis-built frame, mis-measured shelf, wrong `steps_per_mm`.
- Output: `X off by N mm`, `Y off by N mm` vs the **size tolerance**.

### 2. Squaring / corners
The Z1-vs-Z2 deltas already captured by calibration (`dYbot`, `dYtop`), converted to mm.
- Catches: a racked / out-of-square / tilted frame — which directly degrades LIDAR accuracy.
- Output: `bottom delta N mm`, `top delta N mm` vs the **squaring tolerance**.
- (The gyro later helps level the beam; this report catches the mechanical error at commissioning.)

## Tolerances (SEPARATE — decided)
Two independent, explicitly-declared values (in the spec/YAML), because they grade very
different things:
- `size_tolerance_mm` — allowed error on overall span. (2 mm over a 1830 mm span = 0.1 %, tight
  for an open-loop belt gantry — see note below.)
- `squaring_tolerance_mm` — allowed corner-to-corner / out-of-square error.

The report grades PASS/FAIL against **these stated tolerances**, not a magic number.

## On FAIL (PRINT ONLY — decided)
The report **just prints**. It does **not** block scanning or gate the pipeline (prototype
simplicity). The operator reads it and decides whether to proceed, adjust, or re-run.
> Future option: promote to a gate (fail blocks scanning, with an override) once past prototype.

---

## Report shape (draft)
Name: **`GantryDimensionsEvaluationReport`** (a.k.a. gantry commissioning report).

```
GANTRY DIMENSION EVALUATION
Declared:  1830 x 1830 mm   (6 ft x 6 ft, 3 x 4 cells)
Measured:  1808 x 1795 mm   (10810 x 11247 steps @ 40.0 steps/mm)

Overall size:   X off 22 mm,  Y off 35 mm     [size tol 2 mm]      FAIL
Squaring:       bottom 8 mm,  top 6 mm         [square tol 2 mm]    FAIL
steps_per_mm:   40.0 (measured)  -- all mm conversions use this

VERDICT: FAIL (2 checks out of tolerance)
Likely causes: declared size wrong, frame not square, or steps_per_mm mis-measured.
```

## Reframe: precision matters LESS than it first appears

The LIDAR is the actual **measurement instrument** — the gantry only has to place it *roughly*
in the right spot. So gantry positioning error does **not** compound into the scan data the way
it would if the gantry itself were doing the measuring: a few mm of placement slop just means the
LIDAR sees the cell from a slightly-off vantage point, but it still captures the cell. Data
quality comes from the sensor, not the placement.

And the task is **coarse**: we mostly want "is this section of the cell roughly empty or full?"
(occupancy), **not** accurate scanned-shape geometry. Millimeter positioning is far more
precision than occupancy detection needs — being off by even ~1 cm can still correctly answer
"this cell is half full."

Two consequences for how to read this report:
- **The tolerances are aspirational, not a hard accuracy gate.** Failing 2 mm does not mean the
  system is broken — it means the gantry isn't a precision metrology tool, which it doesn't need
  to be. The report's real job is catching **gross** errors: a wildly out-of-square frame, a
  `steps_per_mm` off by ~2x (a microstepping mistake), or a shelf declared at completely the
  wrong size. It's a "something is seriously wrong" detector, not a "we're 3 mm off" grader.
- **The touch-sensor stoppers are the real safety net.** They physically bound the machine
  regardless of measurement precision, so sloppy numbers cost a little scan-placement accuracy
  (which the LIDAR absorbs) — never safety or overrun.

Net: keep the report as a sanity check, but set tolerances loose enough to flag *gross* problems.
Chasing tight precision here is effort the LIDAR + endstops make largely unnecessary.

## The report's real value (beyond pass/fail)
2 mm over a 6 ft span is **tight** for an open-loop belt-driven gantry — belt stretch alone can
eat that. So the report isn't only a gate; it's how we **discover the machine's real achievable
precision** and set an *honest* tolerance. First runs may reveal that ~5 mm is realistic and 2 mm
isn't — that's a valuable finding, not a failure. "Run until decent passage" = iterate hardware
+ tolerances until the numbers are trustworthy for LIDAR.

## Inputs / outputs (for implementation later)
- **Inputs:** declared shelf (mm, from shelf config), measured travel + deltas (steps, from
  calibration), `steps_per_mm`, `size_tolerance_mm`, `squaring_tolerance_mm`.
- **Output:** the printed report above + a PASS/FAIL verdict per check.
- Runs on the **PC** (pure computation). No hardware, no serial. Decoupled: feed it the numbers;
  it doesn't need to drive the machine.

## To confirm before implementing
- Measure `steps_per_mm` (the blocking prerequisite).
- Pick initial `size_tolerance_mm` and `squaring_tolerance_mm` (or start loose and tighten as the
  report reveals real precision).
