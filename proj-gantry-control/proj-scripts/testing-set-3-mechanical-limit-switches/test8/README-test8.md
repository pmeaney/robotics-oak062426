# Set 3 · Test 8 — New-Strategy Programs (PC brain / ESP32 hands)

**What this test set is:** the code that realizes the *new strategy* — the PC (brain) drives
the ESP32 (hands) via mpremote request/response. Everything before (Test 0–7) built electronics
familiarity and the design; Test 8 is where the new-strategy programs get written and proven.

`gantry_positioner.py` is the first artifact here (to be tried on hardware soon).

---

## Why this doc exists (the honest inventory)
After a long design stretch it's easy to lose track of what is actually *code* vs *design*. This
is the straight answer: for the new strategy, we have thorough design, one written-but-unproven
board file, and zero *proven* new-strategy code yet. Test 8 closes that gap.

## Where things actually stand

### Proven code — old approach (board does everything, standalone via mpremote)
- `test0`–`test6` — the Set 3 progression: switch reads, reflex stops, homing, travel
  measurement, bounding-box measurement. Run on the ESP32 standalone. Proven on hardware.

### Written but NOT yet proven — new strategy
- `gantry_positioner.py` — the board-side function library (`move_x`, `move_y`,
  `home_and_measure`, `status`). Written for the new strategy (passive functions the PC calls),
  assembled from proven pieces — but **has never run on hardware.** Written, unproven.

### Design / spec only — no code yet
- **PC-side driver (the "brain")** — reads YAML, does the math, drives the board via mpremote,
  sequences the scan. Described in the system-design doc; no code.
- **Shelf config program** — prompts, unit conversion, cell-center math. Fully spec'd; no code.
- **Gantry dimension evaluation report** — spec'd; no code; correctly blocked on `steps_per_mm`.

## Mapping to the new strategy
The strategy is: **PC (brain) drives ESP32 (hands) via mpremote request/response.**
- **Hands side:** `gantry_positioner.py` exists, unproven.
- **Brain side:** nothing exists yet — no PC program at all.
- **The two pure-math PC programs** (shelf config, evaluation report): specs only.

So: thorough *design*, one *written-but-unproven* board file, and *zero proven* new-strategy
code. The recent work was design and decision-making — the right work; it stopped us thrashing —
but it hasn't become running programs yet.

---

## How Test 8 proceeds (split by risk)

### Low-risk, buildable now — pure PC math, no hardware, easy to verify
- **Shelf config program** — prompts for the shelf, converts imperial → mm, computes each
  cell's bottom-center in steps. Verify against known answers (the two prototype shelves). Zero
  hardware, zero risk. **This is the first concrete new-strategy program we can write and fully
  test on the desk.**
- **Gantry dimension evaluation report** — also pure PC math, **except** it is blocked on
  `steps_per_mm` (can't convert measured steps → mm without it). Build after that measurement.

### Needs hardware to prove — bench session, 24V kill in hand
- **`gantry_positioner.py`** — run `home_and_measure()` first (hand on the kill), confirm the
  numbers match known values (travelX ~10810, travelY ~11247, deltas ~260–320), then the moves.
- **PC-side driver** — the brain that calls `gantry_positioner.py` over mpremote and sequences
  calibration + scans.

## Blocking prerequisite
Measure **`steps_per_mm`** (the real-distance-vs-steps test). It unblocks the evaluation report
and the mm sanity checks. Placement math itself does not need it (cell centers come from
steps ÷ counts).

## Recommended next step
Write the **shelf config program** now — the first runnable new-strategy program, fully testable
on the desk with the two prototype shelves as known-answer cases. Then, at the bench, prove
`gantry_positioner.py`. Then the PC driver ties them together.

## Test 8 artifacts (checklist)
- [ ] `gantry_positioner.py` proven on hardware (written; unproven)
- [ ] Shelf config program (spec ready; no code)
- [ ] `steps_per_mm` measured (blocking prerequisite)
- [ ] Gantry dimension evaluation report (spec ready; blocked on steps_per_mm)
- [ ] PC-side driver / sequencer (design only)
