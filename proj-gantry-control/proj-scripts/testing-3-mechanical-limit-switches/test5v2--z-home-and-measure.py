# test5v2--z-home-and-measure.py
# Set 3, Ticket 5 (S3T5) -- Z beam home + squaring (both ends) + travel.
# Run: mpremote run test5--z-home-and-measure.py
#
# The beam is ONE rigid piece on two motors, so a limit = the FIRST of a pair to
# trip (either bottom switch = "bottom" for the whole beam). Sequence:
#   1. HOME:        drive both DOWN; first bottom switch (Z1B/Z2B) = bottom.
#   2. SQUARE bot:  nudge the lagging motor DOWN to its bottom switch -> delta_bottom.
#                   Leaves the beam square at the bottom.
#   3. TRAVEL:      drive both UP counting; first top switch (Z1T/Z2T) = top.
#                   count = beam travel (hard_stop). center = //2.
#   4. SQUARE top:  nudge the lagging motor UP to its top switch -> delta_top.
#                   Leaves the beam square at the top too (re-level).
#   5. REPORT:      travel + both deltas.
#   6. RETURN:      drive back DOWN + back off, so the beam ends LOW before disable
#                   (a high beam FREE-FALLS the instant coils release).
#
# delta_bottom vs delta_top are a useful cross-check: on a rigid beam with true-mounted
# switches they should be in the same ballpark. (We print both; no auto-warning.)
#
# Verticals: INVERT {"Z1": False, "Z2": True}, UP_DIR_LEVEL = 1 (verified anti-rack).
# Logic (NO): released = 1, pressed = 0. TRIGGERED = 0.
# Safety: drivers init DISABLED; try/finally disables on any exit; runaway ceilings on
#         every move. Ctrl-C is NOT a reliable stop -- hand on the 24V kill.


# ❯ mpremote run test5v2--z-home-and-measure.py
# S3T5: Z beam home(bottom) + squaring(both ends) + travel.
#        Heavy beam, drives DOWN first. Ctrl-C is NOT a safe stop -- hand on the 24V kill.
# [HOME]     driving DOWN to first bottom switch...
#   first bottom switch: Z2B -> beam bottom reached.
# [SQUARE B] nudged Z1 down 322 steps -> delta_bottom = 322 steps.
# [TRAVEL]   driving UP to first top switch, counting...
#   first top switch: Z2T.
# [SQUARE T] nudged Z1 up 258 steps -> delta_top = 258 steps.
#   ----------------------------------------------------------
#   RESULT
#     Z beam travel (hard_stop) = 11246 steps   center = 5623 steps
#     delta_bottom = 322 steps (lag: Z1)
#     delta_top    = 258 steps (lag: Z1)
#   ----------------------------------------------------------
# [RETURN]   driving back DOWN to bottom...
# [RETURN]   beam low, switches released.
# Both Z drivers disabled.


from machine import Pin
import time

ENABLE_LEVEL, DISABLE_LEVEL = 0, 1

MOTOR_PINS = {
    "Z1": {"en": 25, "step": 26, "dir": 33},
    "Z2": {"en": 13, "step": 27, "dir": 14},
}
UP_DIR_LEVEL = 1
INVERT = {"Z1": False, "Z2": True}

BOTTOM = {"Z1": ("Z1B", 34), "Z2": ("Z2B", 15)}
TOP    = {"Z1": ("Z1T", 35), "Z2": ("Z2T",  5)}
TRIGGERED = 0

STEP_DELAY_US = 1200        # half-period per pulse; larger = slower
BACKOFF_STEPS = 400         # release distance ~= 5 mm at the rough ~40 steps/mm seen on Z
MAX_STEPS     = 40000       # travel runaway ceiling
SQUARE_MAX    = 4000        # squaring-nudge ceiling (delta should be modest)
STAGGER_MS    = 5


class Stepper:
    def __init__(self, en, step, dr, invert):
        self.invert = invert
        self.en   = Pin(en,   Pin.OUT, value=DISABLE_LEVEL)
        self.dir  = Pin(dr,   Pin.OUT, value=0)
        self.step = Pin(step, Pin.OUT, value=0)
    def enable(self):  self.en.value(ENABLE_LEVEL)
    def disable(self): self.en.value(DISABLE_LEVEL)
    def set_direction(self, go_up):
        level = UP_DIR_LEVEL if go_up else (1 - UP_DIR_LEVEL)
        if self.invert:
            level ^= 1
        self.dir.value(level)


motors = {n: Stepper(p["en"], p["step"], p["dir"], INVERT[n]) for n, p in MOTOR_PINS.items()}
bsw = {n: Pin(BOTTOM[n][1], Pin.IN) for n in motors}
tsw = {n: Pin(TOP[n][1],    Pin.IN) for n in motors}
Z1, Z2 = motors["Z1"], motors["Z2"]
both = [Z1, Z2]


def disable_all():
    for m in motors.values():
        m.disable()

def pressed(sw):
    return [n for n in sw if sw[n].value() == TRIGGERED]

def set_dir_both(go_up):
    for m in both:
        m.set_direction(go_up)
    time.sleep_us(20)

def pulse_both():
    Z1.step.value(1); Z2.step.value(1)
    time.sleep_us(STEP_DELAY_US)
    Z1.step.value(0); Z2.step.value(0)
    time.sleep_us(STEP_DELAY_US)

def pulse_one(m):
    m.step.value(1); time.sleep_us(STEP_DELAY_US)
    m.step.value(0); time.sleep_us(STEP_DELAY_US)

def drive_both_until(sw, go_up, start_count=0):
    """Drive both until any switch in `sw` trips. Returns (lead_name, count) or (None, count) on ceiling."""
    set_dir_both(go_up)
    c = start_count
    while True:
        hits = pressed(sw)
        if hits:
            return hits[0], c
        if c >= MAX_STEPS:
            return None, c
        pulse_both(); c += 1

def nudge_to(motor, sw_pin, go_up):
    """Step one motor toward its own switch until it trips. Returns (ok, count)."""
    motor.set_direction(go_up); time.sleep_us(20)
    n = 0
    while sw_pin.value() != TRIGGERED:
        if n >= SQUARE_MAX:
            return False, n
        pulse_one(motor); n += 1
    return True, n


def run():
    print("S3T5: Z beam home(bottom) + squaring(both ends) + travel.")
    print("       Heavy beam, drives DOWN first. Ctrl-C is NOT a safe stop -- hand on the 24V kill.")
    try:
        for n in ("Z1", "Z2"):
            motors[n].enable(); time.sleep_ms(STAGGER_MS)

        # Pre-clear: if starting on a bottom switch, lift to release.
        if pressed(bsw):
            set_dir_both(True)
            for _ in range(BACKOFF_STEPS):
                pulse_both()

        # 1) HOME to bottom (first-touch)
        print("[HOME]     driving DOWN to first bottom switch...")
        lead_b, _ = drive_both_until(bsw, go_up=False)
        if lead_b is None:
            print("  no bottom switch in {} steps -> STOP, check wiring/direction.".format(MAX_STEPS)); return
        print("  first bottom switch: {} -> beam bottom reached.".format(BOTTOM[lead_b][0]))

        # 2) SQUARE bottom -- nudge lagging motor DOWN to its bottom switch
        lag_b = "Z2" if lead_b == "Z1" else "Z1"
        if bsw[lag_b].value() == TRIGGERED:
            delta_b = 0
            print("[SQUARE B] both bottom switches already tripped -> delta_bottom = 0.")
        else:
            ok, delta_b = nudge_to(motors[lag_b], bsw[lag_b], go_up=False)
            if not ok:
                print("  {} bottom switch not reached in {} nudge steps -> STOP.".format(lag_b, delta_b)); return
            print("[SQUARE B] nudged {} down {} steps -> delta_bottom = {} steps.".format(lag_b, delta_b, delta_b))

        # 3) TRAVEL up (count from square-bottom, incl. back-off) to first top switch
        travel = 0
        set_dir_both(True)
        for _ in range(BACKOFF_STEPS):
            pulse_both(); travel += 1
        print("[TRAVEL]   driving UP to first top switch, counting...")
        lead_t, travel = drive_both_until(tsw, go_up=True, start_count=travel)
        if lead_t is None:
            print("  no top switch in {} steps -> STOP, check wiring.".format(MAX_STEPS)); return
        print("  first top switch: {}.".format(TOP[lead_t][0]))

        # 4) SQUARE top -- nudge lagging motor UP to its top switch (re-level at top)
        lag_t = "Z2" if lead_t == "Z1" else "Z1"
        if tsw[lag_t].value() == TRIGGERED:
            delta_t = 0
            print("[SQUARE T] both top switches already tripped -> delta_top = 0.")
        else:
            ok, delta_t = nudge_to(motors[lag_t], tsw[lag_t], go_up=True)
            if not ok:
                print("  {} top switch not reached in {} nudge steps -> STOP.".format(lag_t, delta_t)); return
            print("[SQUARE T] nudged {} up {} steps -> delta_top = {} steps.".format(lag_t, delta_t, delta_t))

        # 5) REPORT
        print("  ----------------------------------------------------------")
        print("  RESULT")
        print("    Z beam travel (hard_stop) = {} steps   center = {} steps".format(travel, travel // 2))
        print("    delta_bottom = {} steps (lag: {})".format(delta_b, lag_b if delta_b else "none"))
        print("    delta_top    = {} steps (lag: {})".format(delta_t, lag_t if delta_t else "none"))
        print("  ----------------------------------------------------------")

        # 6) RETURN low before disable
        print("[RETURN]   driving back DOWN to bottom...")
        drive_both_until(bsw, go_up=False)
        set_dir_both(True)
        for _ in range(BACKOFF_STEPS):
            pulse_both()
        print("[RETURN]   beam low, switches released.")

    except KeyboardInterrupt:
        print("aborted")
    finally:
        disable_all()
        print("Both Z drivers disabled.")


run()