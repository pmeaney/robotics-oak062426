"""
================================================================================
Test 3 -- Lift -> Lock -> Traverse (duration-based, one-way)
================================================================================
PURPOSE
    Run the unit's core choreography, open-loop:
        LIFT     : Z1 + Z2 spin UP together for LIFT_SECONDS
        LOCK     : verticals STOP stepping but stay ENABLED (hold the rail)
        TRAVERSE : X spins for TRAVERSE_SECONDS while the verticals hold
        STOP     : disable all three
    No return move; it lifts, locks, traverses out, then stops.

    Proves: the sequence/handoffs, and -- the key check -- that the LOCKED rail
    stays steady (no sag / back-drive) while X moves. This is the real combined
    load: two motors holding while one steps.

BUILT ON PROVEN CODE
    Uses the same duration-based spin_together() loop validated in the Test 2
    spin: it pulses every STEP pin in the given list together each iteration, so
    motors in the list move SIMULTANEOUSLY. Lift passes [Z1, Z2]; traverse passes
    [X].

DIRECTIONS
    * Verticals: carry over your VERIFIED settings from the Test 2 spin
      (INVERT relationship + UP_DIR_LEVEL) so GO_UP truly raises the rail. Do NOT
      change the Z1/Z2 invert relationship -- it's the proven anti-rack setting.
    * X: direction is UNCONFIRMED. X_FWD_LEVEL / INVERT["X"] are a guess; the
      first traverse tells you which way the carriage goes. Flip X_FWD_LEVEL if
      it runs the wrong way.

SAFETY  (you are the limit switch on BOTH axes -- no sensors yet)
    * Drivers come up DISABLED; try/finally disables all three on any exit.
    * Start with SMALL durations. Rail LOW with room to rise; carriage MID-track
      with room on BOTH sides (X direction is unknown on the first run).
    * Hands clear, power in reach. STOP on any rack, bind, or hard-stop contact.

WIRING (locked, ESP32 #1)  -- EN / STEP / DIR
    Z1 (vertical)   : EN 25, STEP 26, DIR 33
    Z2 (vertical)   : EN 13, STEP 27, DIR 14
    X  (horizontal) : EN 18, STEP 19, DIR 23
    TMC2209 EN is ACTIVE-LOW:  0 = ENABLED,  1 = DISABLED.
================================================================================
"""

from machine import Pin
import time

ENABLE_LEVEL  = 0
DISABLE_LEVEL = 1

# ==============================================================================
# DIRECTION CONFIG
# ==============================================================================
# --- Verticals: carry over from the working Test 2 spin. -----------------------
# UP_DIR_LEVEL is the raw DIR bit meaning "up" for a non-inverted motor.
# The INVERT relationship below is the VERIFIED anti-rack setting -- freeze it.
UP_DIR_LEVEL = 1

# --- X: forward level is a GUESS; confirm on first traverse. --------------------
X_FWD_LEVEL  = 1        # flip to 0 if the carriage goes the wrong way

# Per-motor invert. Z1/Z2 = your verified together-moving relationship.
# Set these to whatever the Test 2 spin proved. X normally stays False.
INVERT = {
    "Z1": False,     # <-- set to your VERIFIED Test 2 values
    "Z2": True,    # <-- set to your VERIFIED Test 2 values
    "X":  False,
}

# ==============================================================================
# MOTION CONFIG  (start SMALL, then lengthen once directions are confirmed)
# ==============================================================================
LIFT_SECONDS     = 2       # how long the verticals spin up
TRAVERSE_SECONDS = 2       # how long X traverses (short: X dir unconfirmed)
LOCK_DWELL_S     = 2       # pause after lift, verticals holding, to check steadiness
STEP_DELAY_US    = 1200    # half-period per pulse; larger = slower/safer
STAGGER_MS       = 5

# ==============================================================================
# PIN MAP
# ==============================================================================
MOTOR_PINS = {
    "Z1": {"en": 25, "step": 26, "dir": 33, "name": "Z1 (vertical)"},
    "Z2": {"en": 13, "step": 27, "dir": 14, "name": "Z2 (vertical)"},
    "X":  {"en": 18, "step": 19, "dir": 23, "name": "X  (horizontal)"},
}


class Stepper:
    def __init__(self, en_pin, step_pin, dir_pin, name="", invert=False,
                 fwd_level=1):
        self.name = name
        self.invert = invert
        self.fwd_level = fwd_level        # raw DIR bit meaning this axis's "forward"
        self.en   = Pin(en_pin,   Pin.OUT, value=DISABLE_LEVEL)   # come up OFF
        self.dir  = Pin(dir_pin,  Pin.OUT, value=0)
        self.step = Pin(step_pin, Pin.OUT, value=0)

    def enable(self):
        self.en.value(ENABLE_LEVEL)

    def disable(self):
        self.en.value(DISABLE_LEVEL)

    def set_direction(self, forward):
        """forward=True -> this axis's forward dir (up for Z, out for X)."""
        level = self.fwd_level if forward else (1 - self.fwd_level)
        if self.invert:
            level ^= 1
        self.dir.value(level)


# Verticals' forward level = UP_DIR_LEVEL; X's forward level = X_FWD_LEVEL.
FWD_LEVEL = {"Z1": UP_DIR_LEVEL, "Z2": UP_DIR_LEVEL, "X": X_FWD_LEVEL}

motors = {n: Stepper(p["en"], p["step"], p["dir"], p["name"],
                     INVERT[n], FWD_LEVEL[n])
          for n, p in MOTOR_PINS.items()}


def disable_all():
    for m in motors.values():
        m.disable()


def spin_together(steppers, seconds, forward, delay_us):
    """Pulse ALL given steppers together for `seconds` -> simultaneous motion."""
    for s in steppers:
        s.set_direction(forward)
    time.sleep_us(20)                          # DIR setup before first pulse

    end = time.ticks_add(time.ticks_ms(), int(seconds * 1000))
    steps = 0
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        for s in steppers:
            s.step.value(1)
        time.sleep_us(delay_us)
        for s in steppers:
            s.step.value(0)
        time.sleep_us(delay_us)
        steps += 1
    return steps


def run():
    verticals = [motors["Z1"], motors["Z2"]]
    x         = [motors["X"]]
    print("=" * 60)
    print("TEST 3 -- LIFT -> LOCK -> TRAVERSE")
    print("LIFT={}s  TRAVERSE={}s  DELAY_US={}".format(
        LIFT_SECONDS, TRAVERSE_SECONDS, STEP_DELAY_US))
    print("WATCH: rail must HOLD steady while X moves. X dir is unconfirmed --")
    print("       stop if the carriage heads for a hard stop.")
    print("Ctrl-C to abort.")
    print("=" * 60)
    try:
        # All three come up enabled and holding.
        for n in ("Z1", "Z2", "X"):
            motors[n].enable()
            print("  enabled {}".format(motors[n].name))
            time.sleep_ms(STAGGER_MS)
        time.sleep(1)

        # 1) LIFT -- verticals up together
        print("\n[LIFT]     Z1+Z2 up for {}s...".format(LIFT_SECONDS))
        n = spin_together(verticals, LIFT_SECONDS, forward=True, delay_us=STEP_DELAY_US)
        print("           done ({} steps each).".format(n))

        # 2) LOCK -- verticals stop stepping but stay ENABLED (holding)
        print("[LOCKED]   verticals holding. Dwell {}s -- confirm rail is steady."
              .format(LOCK_DWELL_S))
        time.sleep(LOCK_DWELL_S)

        # 3) TRAVERSE -- X moves while verticals HOLD
        print("[TRAVERSE] X for {}s (verticals holding)...".format(TRAVERSE_SECONDS))
        n = spin_together(x, TRAVERSE_SECONDS, forward=True, delay_us=STEP_DELAY_US)
        print("           done ({} steps).".format(n))

        print("\nSequence complete (lift -> lock -> traverse). Stopping.")
    except KeyboardInterrupt:
        print("\nAborted by user (Ctrl-C).")
    finally:
        disable_all()
        print("All motors disabled.")
        print("=" * 60)


if __name__ == "__main__":
    run()