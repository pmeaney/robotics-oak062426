# Robotics project

This project is based on a 3D printer structure and is used to position a gantry containing a sensor in 2D space, eventually 3D space.

## Required software


- ESP32 related

    - **mpremote** — runs MicroPython test files on the ESP32 over USB. Install globally with pipx: `pipx install mpremote`.

Everything else runs on the ESP32 as MicroPython using built-in modules only, so there is nothing to install on the board.

See `tooling-notes.md` for setup details and background.

## Testing overview

Open-loop motor validation (no sensors yet). Run in order; don't advance until the current test passes. **Z1 + Z2** are the synchronized verticals; **X** is the horizontal carriage.

- **test0--hold-test.py** — Three-motor hold, no motion. Validates power/ground/thermal under load.
- **test1--z1z2-holding.py** — Both verticals held together, no motion.
- **test2--z1z2-stepping.py** — Both verticals stepped together without belts attached; simultaneously, same direction for 5 seconds.  Next, belts attached, and it is run again to check direction
- **test3--lift-lock-traverse.py** — Full sequence: verticals lift and lock while X traverses.

Run a test with:

```bash
mpremote run test1--z1z2-holding.py
```
