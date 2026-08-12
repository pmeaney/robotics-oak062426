"""
================================================================================
Test 1 -- Z1 + Z2 Simultaneous Hold (no motion)
================================================================================
PURPOSE
    Energize the two vertical motors TOGETHER and hold -- no stepping. Validates
    that the power/ground/thermal system carries both verticals' simultaneous
    holding current cleanly, before they are asked to step together in Test 2.
    (In normal operation Z1 and Z2 are always on/off as a bonded pair.)

    While holding, MEASURE:
      * 3.3V logic rail  -> watch for a dip at the enable instant
      * serial console   -> watch for any ESP32 brownout reset (heartbeat stall)
      * driver temps      -> after ~1 min, feel for a HOT OUTLIER (marginal
                             connection or current-set/VREF error on that channel)

    PASS = both verticals lock with torque, no reset, rails steady, both drivers
           evenly warm.

SAFETY MODEL (shared across the test-script series)
    * Drivers come up DISABLED (EN driven high via value= at construction), so a
      floating boot-time GPIO can never enable a driver.
    * try/finally disables both drivers on any exit (normal, exception, Ctrl-C).
    * Gravity: start with the rail LOW -- when the test disables at the end, a
      non-self-locking drive may let the rail settle. Keep a hand near power.

WIRING (locked, ESP32 #1)  -- EN / STEP / DIR
    Z1 (vertical) : EN 25, STEP 26, DIR 33
    Z2 (vertical) : EN 13, STEP 27, DIR 14
    (X is not used in this test.)
    TMC2209 EN is ACTIVE-LOW:  0 = ENABLED (holding),  1 = DISABLED.
================================================================================
"""

from machine import Pin
import time

ENABLE_LEVEL  = 0    # EN LOW  = enabled
DISABLE_LEVEL = 1    # EN HIGH = disabled
DIR_DEFAULT   = 0    # known idle level; this test never steps

# ---- CONFIG ------------------------------------------------------------------
HOLD_SECONDS = 20    # keep short at first; extend once trusted
STAGGER_MS   = 5     # gap between enabling Z1 and Z2 (spreads inrush surge)

# ---- PIN MAP (only the two verticals) ----------------------------------------
MOTOR_PINS = {
    "Z1": {"en": 25, "step": 26, "dir": 33, "name": "Z1 (vertical)"},
    "Z2": {"en": 13, "step": 27, "dir": 14, "name": "Z2 (vertical)"},
}


class Stepper:
    """Minimal: safe init, enable, disable. No stepping in this test."""
    def __init__(self, en_pin, step_pin, dir_pin, name=""):
        self.name = name
        # Drive EN to DISABLED in the same call that makes it an output.
        self.en   = Pin(en_pin,   Pin.OUT, value=DISABLE_LEVEL)
        self.dir  = Pin(dir_pin,  Pin.OUT, value=DIR_DEFAULT)
        self.step = Pin(step_pin, Pin.OUT, value=0)

    def enable(self):
        self.en.value(ENABLE_LEVEL)

    def disable(self):
        self.en.value(DISABLE_LEVEL)


# Constructing the motors is the FIRST thing that happens -> both come up OFF.
motors = {n: Stepper(p["en"], p["step"], p["dir"], p["name"])
          for n, p in MOTOR_PINS.items()}


def disable_all():
    for m in motors.values():
        m.disable()


def hold_test():
    print("=" * 60)
    print("TEST 1 -- Z1 + Z2 SIMULTANEOUS HOLD (no motion)")
    print("WATCH: 3.3V rail dip, ESP32 reset (heartbeat stall), hot outlier.")
    print("Ctrl-C to abort.")
    print("=" * 60)
    try:
        # Staggered enable
        for n in ("Z1", "Z2"):
            motors[n].enable()
            print("  enabled {}".format(motors[n].name))
            time.sleep_ms(STAGGER_MS)

        print("\nBoth verticals holding. Measurement window open.\n")

        # Hold with a 1-second heartbeat (live brownout detector)
        for elapsed in range(1, HOLD_SECONDS + 1):
            time.sleep(1)
            print("  holding... {}/{}s".format(elapsed, HOLD_SECONDS))

        print("\nHold complete.")
    except KeyboardInterrupt:
        print("\nAborted by user (Ctrl-C).")
    finally:
        disable_all()
        print("Both motors disabled. Coils released.")
        print("=" * 60)


if __name__ == "__main__":
    hold_test()
