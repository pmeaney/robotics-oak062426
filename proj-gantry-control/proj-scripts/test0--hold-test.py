"""
================================================================================
Test 0 -- Hold Test (no motion)
================================================================================

TITLE
    test0--hold-test.py
    Three-motor "energize and hold" test for ESP32 #1 (the motor controller).

DESCRIPTION
    Energizes the selected stepper drivers so their motors apply HOLDING torque,
    but sends NO step pulses -- the motors do not move. The drivers simply sit
    and draw their set holding current for a fixed duration, then are disabled.

PURPOSE
    This is the foundation test of the motor test script series. It validates the
    POWER / GROUND / THERMAL system under a three-motor load BEFORE any motion
    or step-timing complexity is introduced. Holding current is close to the
    worst case for steady draw (a stationary rotor produces no back-EMF, so the
    driver delivers its full set current continuously), which makes this the
    cleanest possible stress test of the 24V rail, the 3.3V logic rail, and the
    grounds -- with zero software-timing complexity to muddy a diagnosis.

    While the motors hold, MEASURE:
      * the 3.3V logic rail        -> watch for a dip at the enable instant
      * the ESP32 serial console   -> watch for any brownout reset / reboot
      * each driver's temperature  -> after ~1 min, feel for a HOT OUTLIER
                                      (one much hotter than its siblings flags a
                                       marginal connection or a current-set error)

    PASS = all selected motors hold with torque, no reset, no hot outlier,
           rails steady.

SAFETY MODEL (shared by every script in this test-script series)
    1. The very first thing the script does is construct the motor objects, and
       each constructor forces EN to the DISABLED level in the same instant it
       configures the pin -- so every driver comes up OFF regardless of how the
       GPIOs floated at boot. There is no window where a floating pin can enable
       a driver.
    2. DIR is set to a known level during construction (even though this test
       never steps) so no control pin is left in an undefined state.
    3. The whole run is wrapped in try / finally. However the run ends -- normal
       finish, an exception, or Ctrl-C -- the finally block disables every motor
       on the way out. Coils are never left energized by accident.

WIRING (locked, ESP32 #1)  -- EN / STEP / DIR per motor
    Z1 (vertical)   : EN 25, STEP 26, DIR 33
    Z2 (vertical)   : EN 13, STEP 27, DIR 14
    X  (horizontal) : EN 18, STEP 19, DIR 23
    NOTE: the TMC2209 EN pin is ACTIVE-LOW.
          EN = 0 (LOW)  -> driver ENABLED  (coils energized, holding torque)
          EN = 1 (HIGH) -> driver DISABLED (coils released)
================================================================================
"""

from machine import Pin
import time


# ------------------------------------------------------------------------------
# TMC2209 EN-pin logic levels (active-low -- see header). Naming these as
# constants keeps the active-low inversion in ONE place instead of scattering
# raw 0/1 values through the code where they're easy to get backwards.
# ------------------------------------------------------------------------------
ENABLE_LEVEL  = 0   # drive EN LOW  to ENABLE  the driver
DISABLE_LEVEL = 1   # drive EN HIGH to DISABLE the driver

# A safe, defined starting level for DIR. This test never steps, so the actual
# direction is irrelevant here -- we just refuse to leave the pin floating.
DIR_DEFAULT = 0


# ==============================================================================
# CONFIG -- the only things you normally change between runs.
# ==============================================================================

# Which drivers to energize this run, by name ("Z1", "Z2", "X").
#
#   * For the FIRST power-up after the rewire, consider ["Z2"] only. Z2 (pins
#     13/27/14) is your validated-pins channel, so energizing it alone first
#     confirms the new star ground and rewiring didn't break what already worked.
#   * Then set ["Z1", "Z2", "X"] for the real three-motor hold test.
MOTORS_TO_ENERGIZE = ["Z1", "Z2", "X"]

# How long to hold, in seconds. Keep the first run SHORT; extend once you trust
# it. (Holding current heats the drivers continuously, so don't leave it holding
# for long unattended.)
HOLD_SECONDS = 20

# Delay between enabling each motor, in milliseconds. Enabling all drivers in the
# same instant stacks three inrush events into one surge that can sag the rails
# (a "startup dip" -> possible brownout reset). Staggering the enables by a few
# ms spreads that surge out in time.
STAGGER_MS = 5


# ==============================================================================
# MOTOR PIN MAP -- locked wiring. Do not edit without also updating the system
# description doc, so the two never drift out of sync.
# ==============================================================================
MOTOR_PINS = {
    "Z1": {"en": 25, "step": 26, "dir": 33, "name": "Z1 (vertical)"},
    "Z2": {"en": 13, "step": 27, "dir": 14, "name": "Z2 (vertical, validated pins)"},
    "X":  {"en": 18, "step": 19, "dir": 23, "name": "X  (horizontal)"},
}


# ==============================================================================
# Minimal stepper abstraction.
#
# For Test 0 this only needs to: configure its pins, come up DISABLED, hold a
# known DIR, and enable/disable on command. Later tests will extend this SAME
# class with a step() method -- keeping the safe-init and enable/disable logic in
# one place so every script inherits identical safety behavior.
# ==============================================================================
class Stepper:
    def __init__(self, en_pin, step_pin, dir_pin, name=""):
        self.name = name

        # Configure the pins as outputs. CRITICAL: the `value=` argument sets the
        # pin's level in the same call that makes it an output, so EN is driven to
        # DISABLED atomically -- there is no instant where it's an output at an
        # undefined level.
        self.en   = Pin(en_pin,   Pin.OUT, value=DISABLE_LEVEL)  # come up OFF
        self.dir  = Pin(dir_pin,  Pin.OUT, value=DIR_DEFAULT)    # known direction
        self.step = Pin(step_pin, Pin.OUT, value=0)              # idle low; unused here

        self.enabled = False

    def enable(self):
        """Energize the driver -> motor applies holding torque."""
        self.en.value(ENABLE_LEVEL)
        self.enabled = True

    def disable(self):
        """Release the driver -> coils de-energized, motor spins freely."""
        self.en.value(DISABLE_LEVEL)
        self.enabled = False


# ==============================================================================
# BOOT-SAFE SETUP
#
# Constructing the motors is the FIRST thing this script does. Because each
# constructor forces EN to DISABLE_LEVEL, every driver is guaranteed OFF before
# any other logic runs.
# ==============================================================================
motors = {
    name: Stepper(p["en"], p["step"], p["dir"], p["name"])
    for name, p in MOTOR_PINS.items()
}


def disable_all():
    """Disable every motor. Idempotent -- safe to call any number of times."""
    for m in motors.values():
        m.disable()


def hold_test():
    """
    The hold test itself:
      1. (boot already left everything disabled)
      2. staggered-enable the selected motors
      3. hold for HOLD_SECONDS, printing a 1-second heartbeat so you can see the
         ESP32 is still alive (a sudden stop in the heartbeat = it reset)
      4. disable everything -- guaranteed by the finally block
    """
    print("=" * 60)
    print("TEST 0 -- HOLD TEST (no motion)")
    print("Energizing selected motors. WATCH FOR:")
    print("  * a dip on the 3.3V logic rail at the enable instant")
    print("  * any ESP32 reset (the heartbeat below would stop/restart)")
    print("  * a hot-outlier driver after ~1 minute (touch-test)")
    print("Press Ctrl-C to abort at any time.")
    print("=" * 60)

    try:
        # --- Staggered enable -----------------------------------------------
        # Enable one motor at a time, a few ms apart, to avoid one big combined
        # inrush surge.
        for name in MOTORS_TO_ENERGIZE:
            m = motors[name]
            m.enable()
            print("  enabled {}".format(m.name))
            time.sleep_ms(STAGGER_MS)

        print("\nAll selected motors holding. Measurement window is open.\n")

        # --- Hold, with a 1-second heartbeat --------------------------------
        # The heartbeat does double duty: it paces the hold, and it's your live
        # proof the ESP32 hasn't browned out -- if the counter freezes or the
        # board reboots mid-count, that IS the failure.
        for elapsed in range(1, HOLD_SECONDS + 1):
            time.sleep(1)
            print("  holding... {}/{}s".format(elapsed, HOLD_SECONDS))

        print("\nHold duration complete.")

    except KeyboardInterrupt:
        # Ctrl-C still falls through to `finally` below; this just prints a clean
        # message instead of a traceback.
        print("\nAborted by user (Ctrl-C).")

    finally:
        # This block ALWAYS runs -- normal exit, exception, or Ctrl-C -- so the
        # coils are never left energized.
        disable_all()
        print("All motors disabled. Coils released.")
        print("=" * 60)


# ==============================================================================
# ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    hold_test()
