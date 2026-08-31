# Overview — System Design Sketch

A living sketch of where the whole system is heading. Not a spec — a north star for
why the current low-level work matters. Details firm up as each layer is proven.

---

## The end goal (in the operator's words)

> "You're installed in a new place, with a new shelf of some dimensions. It has some
> number of cells, in N columns and M rows. The shelves are T thickness. Do a *circuit*
> of the shelves once every H hours."

From that one instruction the system runs itself: on each circuit it visits every cell,
and per cell decides — **is anything there?** If yes, scan it. If no, log the cell empty
and move on.

Everything below exists to make that sentence executable.

## Coordinator — one brain

A single piece of software on the **ThinkCentre** (Python orchestrator) coordinates all
subsystems. Each subsystem is dumb and standalone; the coordinator sequences them:

- `motion` — gantry positioning (go to a step target)
- `lidar`  — perception (is something there? scan it)
- `gyro`   — leveling / squaring cross-check (later)

"Prove each layer" holds: every subsystem is proven alone, then the coordinator just
orchestrates already-proven parts. Subsystems don't call each other — only the
coordinator calls them.

## The layer cake

Each layer only talks to the one beneath it.

1. **Mission** — "circuit every H hours." Scheduler: wake, run one circuit, sleep.
   Owns the timer and the shelf definition.
2. **Circuit** — "visit every cell." Walks the rows × columns grid; at each cell says
   "go here, then look." Owns visit order and the empty/scanned log.
3. **Motion + Perception** — "go here" (gantry) and "look" (lidar). The subsystems that
   touch hardware.
4. **Reflex** — always-on endstop halt on the ESP32, underneath everything.

## Brain / hands split (established)

- **ThinkCentre = brain.** Owns the coordinate map, all limit math, the shelf +
  calibration data. Decides what moves happen and where, in steps.
- **ESP32 "SysM" = hands.** Executes a small order vocabulary (home axis, move axis by
  N steps, report status) plus the always-on endstop reflex. Holds no map.

## Data — `prototype-shelf.yaml` is the seed of the top layer

"New place, new shelf, N × M cells, T thickness" is literally editing that file.

- **shelf:** physical description (rows, columns, cell dimensions in mm) — human-authored.
- **gantry:** measured calibration (axis travel + center in steps) — written by calibration (S3T6), from the S3T4/S3T5 measure runs.
- The **mm → steps** bridge is exactly the translation the Circuit layer needs to turn
  "cell (row 2, col 4)" into "X = these steps, Z = these steps."

So the top layer isn't designed from scratch later — it fills slots that already exist.

## Subsystems

| Subsystem | Status | Notes |
|-----------|--------|-------|
| Gantry positioning | in progress | Reflex / homing / measure / calibrate tickets (S3T2–S3T6). Produces the movement primitives. |
| Gyro (GY-521) | queued | Leveling + squaring cross-check. Out of scope until called for. |
| LIDAR (RPLIDAR C1) | basic test done | Did a basic test scan months ago. Per-cell "present? scan : mark empty" logic lives in the Circuit layer, above the gantry. |

## Calibration (install-time routine)

The home+measure tickets (S3T4–S3T5) aren't standalone tests — they're the *steps of a routine the operator
runs on day one at every install*. Calibration composes those proven primitives; it does
no new low-level work.

**Two phases, by authorship (the two halves of the YAML):**
1. **Human declares** — operator edits `prototype-shelf.yaml`: shelf dimensions, columns,
   rows, thickness. What's physically present, which the machine can't measure. The README
   points them here.
2. **Machine discovers, then verifies** — homes, drives its own boundaries to measure
   travel in steps (discover), then double-checks: re-measures within tolerance and
   confirms a computed interior move lands where predicted (verify). Writes results back.

**Stop vocabulary:** *hard stop* = the physical switch (the wall). *Soft stop* = the
brain's step limit, set inside it. *Buffer* = the gap between them. *Back-off* = retreat
distance after touching a stop. Soft stop is derived (`hard_stop − buffer`), so
re-measuring the wall moves it automatically.

**Done-gate:** calibration is complete when the YAML `gantry:` block is fully populated
and verified. The Mission layer reads this on boot — null fields → refuse to run a
circuit, tell the operator to calibrate first. An un-calibrated machine never drives blind.

**Recalibration triggers (later, Mission-layer):** first install; moved to a new shelf;
crash that lost zero; long-term drift. "Something decides when calibration is stale" is a
Mission question, not a low-level one.

## Where the current work fits

S3T4–S3T5 produce the gantry's whole vocabulary: **home**, and **move to a step target
inside known bounds**. That's everything the Circuit walker needs from motion. Lidar and
gyro slot in later as coordinator modules next to `motion` — nothing in the current work
boxes them out.

- **S3T2** — X reflex stop (prove the halt)
- **S3T3** — Z dual reflex stop (any of 4 → both stop)
- **S3T4** — X home + measure (zero + travel)
- **S3T5** — Z home + measure (independent, squaring delta)

Once these pass, the movement functions can be built on proven primitives.
