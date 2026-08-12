"""
================================================================================
Test 2 (spin) -- Z1 + Z2 spin SIMULTANEOUSLY, same direction, for 5 seconds
================================================================================
PURPOSE
    Prove the two verticals step AT THE SAME TIME (not one then the other), in the
    same direction, for a fixed duration. This is the minimal simultaneous-motion
    check before doing measured lifts.

HOW SIMULTANEITY WORKS
    A single loop pulses BOTH STEP pins together each iteration:
        raise Z1.STEP and Z2.STEP -> wait -> lower both -> wait -> repeat.
    Both motors advance one microstep per loop, so they move together. (Stepping
    one motor's full run and THEN the other is the sequential bug this avoids.)

TUNING
    * Wrong direction (rail lowers)      -> flip UP_DIR_LEVEL (0 <-> 1).
    * Motors RACK (one up, one down)     -> set exactly ONE motor's INVERT True.
    * A motor buzzes instead of turning  -> increase STEP_DELAY_US (slower).

SAFETY
    * Drivers come up DISABLED; try/finally disables on any exit.
    * Rail LOW to start, room to move, hands clear, power in reach.
    * NO limit switches: 5 s of stepping travels a real distance -- make sure
      there's room, or lower STEP rate / duration first.

WIRING (locked, ESP32 #1)  -- EN / STEP / DIR
    Z1 (vertical) : EN 25, STEP 26, DIR 33
    Z2 (vertical) : EN 13, STEP 27, DIR 14
    TMC2209 EN is ACTIVE-LOW:  0 = ENABLED,  1 = DISABLED.
================================================================================
"""

from machine import Pin
import time

ENABLE_LEVEL  = 0
DISABLE_LEVEL = 1

# ---- DIRECTION CONFIG (tune on first run) ------------------------------------
UP_DIR_LEVEL = 1              # DIR level that raises the rail (non-inverted motor)

# INVERT = {"Z1": False, "Z2": False}   # if they RACK, set ONE of these True
# Regarding INVERT-- First test results:
# Initially, both set to false caused racking: INVERT = {"Z1": False, "Z2": False}
# Then I set them to this, and they move down together: INVERT = {"Z1": True, "Z2": False}

# *** Therefore, be aware: ****
# Z1 and Z2 are mounted mirror-image, so the SAME dir signal spins them
# physically opposite. INVERT Z1 to make both move the rail as one piece.
# Verified: with GO_UP=True and this INVERT setting, the rail moves DOWN.

# Because this moves down, and the script is set to use "GO_UP", we'll use its opposite...
### going down:
# INVERT = {"Z1": True, "Z2": False}
# Going up:
INVERT = {"Z1": False, "Z2": True}

# ---- MOTION CONFIG -----------------------------------------------------------
SPIN_SECONDS  = 2            # how long to spin
STEP_DELAY_US = 1200         # half-period per pulse; larger = slower/safer
                             # rate ~= 1_000_000 / (2 * STEP_DELAY_US) steps/s
GO_UP         = True         # True = raise the rail, False = lower
STAGGER_MS    = 5

# ---- PIN MAP -----------------------------------------------------------------
MOTOR_PINS = {
    "Z1": {"en": 25, "step": 26, "dir": 33, "name": "Z1 (vertical)"},
    "Z2": {"en": 13, "step": 27, "dir": 14, "name": "Z2 (vertical)"},
}


class Stepper:
    def __init__(self, en_pin, step_pin, dir_pin, name="", invert=False):
        self.name = name
        self.invert = invert
        self.en   = Pin(en_pin,   Pin.OUT, value=DISABLE_LEVEL)   # come up OFF
        self.dir  = Pin(dir_pin,  Pin.OUT, value=0)
        self.step = Pin(step_pin, Pin.OUT, value=0)

    def enable(self):
        self.en.value(ENABLE_LEVEL)

    def disable(self):
        self.en.value(DISABLE_LEVEL)

    def set_direction(self, go_up):
        level = UP_DIR_LEVEL if go_up else (1 - UP_DIR_LEVEL)
        if self.invert:
            level ^= 1
        self.dir.value(level)


motors = {n: Stepper(p["en"], p["step"], p["dir"], p["name"], INVERT[n])
          for n, p in MOTOR_PINS.items()}


def disable_all():
    for m in motors.values():
        m.disable()


def spin_together(steppers, seconds, go_up, delay_us):
    """Pulse ALL steppers together for `seconds`. Both advance one step per loop."""
    for s in steppers:
        s.set_direction(go_up)
    time.sleep_us(20)                          # DIR setup before first pulse

    end = time.ticks_add(time.ticks_ms(), int(seconds * 1000))
    steps = 0
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        for s in steppers:                     # raise both STEP together
            s.step.value(1)
        time.sleep_us(delay_us)
        for s in steppers:                     # lower both STEP together
            s.step.value(0)
        time.sleep_us(delay_us)
        steps += 1
    return steps


def run():
    verticals = [motors["Z1"], motors["Z2"]]
    print("=" * 60)
    print("TEST 2 (spin) -- Z1 + Z2 SIMULTANEOUS, {}s, {}".format(
        SPIN_SECONDS, "UP" if GO_UP else "DOWN"))
    print("WATCH: both spin AT ONCE, same direction. STOP if they rack.")
    print("Ctrl-C to abort.")
    print("=" * 60)
    try:
        for n in ("Z1", "Z2"):
            motors[n].enable()
            print("  enabled {}".format(motors[n].name))
            time.sleep_ms(STAGGER_MS)

        print("\nSpinning both for {}s...".format(SPIN_SECONDS))
        n_steps = spin_together(verticals, SPIN_SECONDS, GO_UP, STEP_DELAY_US)
        print("Done. {} steps each.".format(n_steps))
    except KeyboardInterrupt:
        print("\nAborted by user (Ctrl-C).")
    finally:
        disable_all()
        print("Motors disabled.")
        print("=" * 60)


if __name__ == "__main__":
    run()