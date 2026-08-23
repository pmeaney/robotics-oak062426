# test5v1--z-home-and-measure.py
# Set 3, Ticket 5 (S3T5) -- Z beam home + squaring delta + travel measurement.
# Run: mpremote run test5--z-home-and-measure.py
#
# The beam is ONE rigid piece on two motors, so a limit = the FIRST of a pair to
# trip (your rule: either bottom switch = "bottom" for the whole beam). Sequence:
#   1. HOME:    drive Z1+Z2 DOWN together; first bottom switch (Z1B or Z2B) = bottom.
#   2. SQUARE:  nudge ONLY the lagging motor down to its own bottom switch; that step
#               count = squaring delta (out-of-square). Leaves the beam square at bottom.
#   3. TRAVEL:  back off up, then drive both UP together counting steps; first top
#               switch (Z1T or Z2T) = top. Count = beam travel (hard_stop). center = //2.
#   4. RETURN:  drive back DOWN to bottom + back off, so the beam ends LOW before the
#               drivers disable -- a high beam FREE-FALLS the moment coils release.
#
# Verticals: INVERT {"Z1": False, "Z2": True}, UP_DIR_LEVEL = 1 (verified anti-rack).
# Logic (NO): released = 1, pressed = 0. TRIGGERED = 0.
# Safety: drivers init DISABLED; try/finally disables on any exit; runaway ceilings on
#         every move (a NO switch with a broken wire reads idle and never trips, so the
#         beam would otherwise drive into the hard stop). Ctrl-C is NOT a reliable stop
#         -- keep a hand on the physical kill for this one.


# ❯ mpremote run test5--z-home-and-measure.py
# S3T5: Z beam home(bottom, first-touch) + squaring + travel.
#        Heavy beam, drives DOWN first. Ctrl-C is NOT a safe stop -- hand on the kill.
# [HOME]     driving DOWN to first bottom switch...
#   first bottom switch: Z2B -> beam bottom reached.
# [SQUARE]   nudged Z1 down 1440 steps to its switch -> squaring delta = 1440 steps.
# [TRAVEL]   driving UP to first top switch, counting...
#   first top switch: Z2T.
#   RESULT: Z beam travel (hard_stop) = 11246 steps, center = 5623 steps.
#           squaring delta = 1440 steps (lag corner: Z1).
# [RETURN]   driving back DOWN to bottom...
# ����������������������������������������������������������������Both Z drivers disabled.

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
BACKOFF_STEPS = 100         # release distance after a hit
MAX_STEPS     = 40000       # travel runaway ceiling (X was ~10.8k; generous headroom)
SQUARE_MAX    = 3000        # squaring-nudge ceiling (delta should be small)
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


def run():
    print("S3T5: Z beam home(bottom, first-touch) + squaring + travel.")
    print("       Heavy beam, drives DOWN first. Ctrl-C is NOT a safe stop -- hand on the kill.")
    try:
        for n in ("Z1", "Z2"):
            motors[n].enable(); time.sleep_ms(STAGGER_MS)

        # Pre-clear: if starting on a bottom switch, lift a little to release.
        if pressed(bsw):
            set_dir_both(True)
            for _ in range(BACKOFF_STEPS):
                pulse_both()

        # 1) HOME to bottom, first-touch
        print("[HOME]     driving DOWN to first bottom switch...")
        set_dir_both(False)
        steps = 0
        while True:
            hits = pressed(bsw)
            if hits:
                lead = hits[0]; break
            if steps >= MAX_STEPS:
                print("  no bottom switch in {} steps -> STOP, check wiring/direction.".format(steps)); return
            pulse_both(); steps += 1
        print("  first bottom switch: {} -> beam bottom reached.".format(BOTTOM[lead][0]))

        # 2) SQUARING delta -- nudge the lagging motor down to its own bottom switch
        lag = "Z2" if lead == "Z1" else "Z1"
        if bsw[lag].value() == TRIGGERED:
            delta = 0
            print("[SQUARE]   both bottom switches already tripped -> delta = 0 (square).")
        else:
            motors[lag].set_direction(False); time.sleep_us(20)
            delta = 0
            while bsw[lag].value() != TRIGGERED:
                if delta >= SQUARE_MAX:
                    print("  {} bottom switch not reached in {} nudge steps -> STOP, check it.".format(lag, delta)); return
                pulse_one(motors[lag]); delta += 1
            print("[SQUARE]   nudged {} down {} steps to its switch -> squaring delta = {} steps.".format(lag, delta, delta))

        # 3) TRAVEL to top, first-touch (count from square-bottom = 0, incl. back-off)
        travel = 0
        set_dir_both(True)
        for _ in range(BACKOFF_STEPS):
            pulse_both(); travel += 1
        print("[TRAVEL]   driving UP to first top switch, counting...")
        while True:
            hits = pressed(tsw)
            if hits:
                top_lead = hits[0]; break
            if travel >= MAX_STEPS:
                print("  no top switch in {} steps -> STOP, check wiring.".format(travel)); return
            pulse_both(); travel += 1
        print("  first top switch: {}.".format(TOP[top_lead][0]))
        print("  RESULT: Z beam travel (hard_stop) = {} steps, center = {} steps.".format(travel, travel // 2))
        print("          squaring delta = {} steps (lag corner: {}).".format(delta, lag if delta else "none"))

        # 4) RETURN down + back off, so the beam ends LOW before disable
        print("[RETURN]   driving back DOWN to bottom...")
        set_dir_both(False)
        r = 0
        while True:
            if pressed(bsw):
                break
            if r >= MAX_STEPS:
                print("  return did not reach bottom in {} steps.".format(r)); break
            pulse_both(); r += 1
        set_dir_both(True)
        for _ in range(BACKOFF_STEPS):
            pulse_both()
        print("  beam low, switches released.")

    except KeyboardInterrupt:
        print("aborted")
    finally:
        disable_all()
        print("Both Z drivers disabled.")


run()