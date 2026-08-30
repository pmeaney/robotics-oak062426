# test6--calibrate-bounding-box.py
# Set 3, Ticket 6 (S3T6) -- MEASUREMENT HALF: measure both axes, emit the bounding box.
# Run: mpremote run test6--calibrate-bounding-box.py
#
# Composes the proven X (S3T4) and Z (S3T5) measurements into one run and outputs the
# workspace as a RECTANGLE. First-touch defines every limit -- for the Z beam the two
# end-switches are slightly offset, so taking the FIRST to trip (not the second) keeps
# the box a true rectangle inscribed inside the reachable area, not a skewed trapezoid.
# The X axis (single motor) contributes clean left/right limits.
#
#   hard box = the four first-touch limits, in steps.
#   soft box = hard box inset by BUFFER_STEPS (~5 mm) per side -- the safe region normal
#              moves stay inside so a switch is never tapped.
#
# This is the MEASUREMENT half of calibration. Writing the shelf YAML, reading the
# human-declared shelf data, and the verify-move are the ThinkCentre's job (the brain
# owns the file + coordinate math) -- that's the separate stage-2 program.
#
# Order: Z first (homes the heavy beam low and HOLDS it), then X (carriage moves along
# the held beam). All three drivers stay enabled until the end.
#
# Verticals: INVERT {"Z1": False, "Z2": True}, UP_DIR_LEVEL = 1 (verified).
# Logic (NO): released = 1, pressed = 0. TRIGGERED = 0.
# Safety: drivers init DISABLED; try/finally disables all on any exit; runaway ceilings
#         on every move. Ctrl-C is NOT a reliable stop -- hand on the 24V kill.

# thinkcentre-calibrate.py
from machine import Pin
import time

ENABLE_LEVEL, DISABLE_LEVEL = 0, 1

MOTOR_PINS = {
    "Z1": {"en": 25, "step": 26, "dir": 33, "invert": False},
    "Z2": {"en": 13, "step": 27, "dir": 14, "invert": True},
    "X":  {"en": 18, "step": 19, "dir": 23, "invert": False},
}
UP_DIR_LEVEL = 1          # Z: raw level that raises the beam (per-motor invert applied)
X_HOME_DIR   = 0          # X: raw level toward XZ2 (home). Flip if X homes the wrong way.

SW = {
    "Z1B": 34, "Z2B": 15,   # bottom (Z)
    "Z1T": 35, "Z2T": 5,    # top (Z)
    "XZ2": 4,               # X home end
    "XZ1": 32,              # X far end
}
TRIGGERED = 0

STEP_DELAY_US = 1200
BACKOFF_STEPS = 400        # release distance ~10 mm
BUFFER_STEPS  = 200        # soft-stop safety zone ~5 mm (inset per side)
MAX_STEPS     = 40000      # travel runaway ceiling
SQUARE_MAX    = 4000       # squaring-nudge ceiling
STAGGER_MS    = 5


class Stepper:
    def __init__(self, en, step, dr, invert):
        self.invert = invert
        self.en   = Pin(en,   Pin.OUT, value=DISABLE_LEVEL)
        self.dir  = Pin(dr,   Pin.OUT, value=0)
        self.step = Pin(step, Pin.OUT, value=0)
    def enable(self):  self.en.value(ENABLE_LEVEL)
    def disable(self): self.en.value(DISABLE_LEVEL)
    def dir_raw(self, level):
        self.dir.value(level ^ (1 if self.invert else 0))


M = {n: Stepper(p["en"], p["step"], p["dir"], p["invert"]) for n, p in MOTOR_PINS.items()}
S = {n: Pin(g, Pin.IN) for n, g in SW.items()}
Z1, Z2, X = M["Z1"], M["Z2"], M["X"]
Zboth = [Z1, Z2]


def disable_all():
    for m in M.values():
        m.disable()

def trig(name):
    return S[name].value() == TRIGGERED

def pulse(steppers):
    for s in steppers: s.step.value(1)
    time.sleep_us(STEP_DELAY_US)
    for s in steppers: s.step.value(0)
    time.sleep_us(STEP_DELAY_US)


# ---------- Z (beam, first-touch) ----------
def z_dir(go_up):
    lvl = UP_DIR_LEVEL if go_up else (1 - UP_DIR_LEVEL)
    for s in Zboth: s.dir_raw(lvl)
    time.sleep_us(20)

def z_drive_until(names, go_up, start=0):
    z_dir(go_up)
    c = start
    while True:
        for nm in names:
            if trig(nm): return nm, c
        if c >= MAX_STEPS: return None, c
        pulse(Zboth); c += 1

def z_nudge(motor, sw_name, go_up):
    lvl = UP_DIR_LEVEL if go_up else (1 - UP_DIR_LEVEL)
    motor.dir_raw(lvl); time.sleep_us(20)
    n = 0
    while not trig(sw_name):
        if n >= SQUARE_MAX: return False, n
        pulse([motor]); n += 1
    return True, n

def measure_z():
    print("[Z]  home bottom (first-touch)...")
    if trig("Z1B") or trig("Z2B"):
        z_dir(True)
        for _ in range(BACKOFF_STEPS): pulse(Zboth)
    lead_b, _ = z_drive_until(["Z1B", "Z2B"], go_up=False)
    if lead_b is None:
        print("  Z: no bottom switch in {} steps -> STOP.".format(MAX_STEPS)); return None
    print("     first bottom: {}.".format(lead_b))
    lag_b = "Z2" if lead_b == "Z1B" else "Z1"
    if trig(lag_b + "B"):
        delta_b = 0
    else:
        ok, delta_b = z_nudge(M[lag_b], lag_b + "B", go_up=False)
        if not ok:
            print("  Z: {} not reached in squaring -> STOP.".format(lag_b + "B")); return None
    print("     delta_bottom = {} (lag {}).".format(delta_b, lag_b))

    travel = 0
    z_dir(True)
    for _ in range(BACKOFF_STEPS): pulse(Zboth); travel += 1
    lead_t, travel = z_drive_until(["Z1T", "Z2T"], go_up=True, start=travel)
    if lead_t is None:
        print("  Z: no top switch in {} steps -> STOP.".format(MAX_STEPS)); return None
    print("     first top: {}   travel_z = {}.".format(lead_t, travel))
    lag_t = "Z2" if lead_t == "Z1T" else "Z1"
    if trig(lag_t + "T"):
        delta_t = 0
    else:
        ok, delta_t = z_nudge(M[lag_t], lag_t + "T", go_up=True)
        if not ok:
            print("  Z: {} not reached in squaring -> STOP.".format(lag_t + "T")); return None
    print("     delta_top = {} (lag {}).".format(delta_t, lag_t))

    z_drive_until(["Z1B", "Z2B"], go_up=False)     # return low, stay enabled
    z_dir(True)
    for _ in range(BACKOFF_STEPS): pulse(Zboth)
    print("     Z beam low, held.")
    return {"travel": travel, "delta_bottom": delta_b, "delta_top": delta_t}


# ---------- X (single motor) ----------
def measure_x():
    print("[X]  home toward XZ2...")
    X.dir_raw(X_HOME_DIR); time.sleep_us(20)
    xz1_clear = not trig("XZ1")
    steps = 0
    while True:
        if trig("XZ2"): break
        if not xz1_clear and not trig("XZ1"): xz1_clear = True
        if xz1_clear and trig("XZ1"):
            print("  X: XZ1 tripped first -> X_HOME_DIR backwards. Flip it and rerun."); return None
        if steps >= MAX_STEPS:
            print("  X: no XZ2 in {} steps -> STOP.".format(steps)); return None
        pulse([X]); steps += 1
    print("     XZ2 reached (zero).")

    X.dir_raw(1 - X_HOME_DIR); time.sleep_us(20)
    travel = 0
    for _ in range(BACKOFF_STEPS): pulse([X]); travel += 1
    while True:
        if trig("XZ1"): break
        if travel >= MAX_STEPS:
            print("  X: no XZ1 in {} steps -> STOP.".format(travel)); return None
        pulse([X]); travel += 1
    print("     XZ1 reached   travel_x = {}.".format(travel))

    X.dir_raw(X_HOME_DIR); time.sleep_us(20)        # release XZ1
    for _ in range(BACKOFF_STEPS): pulse([X])
    return {"travel": travel}


def run():
    print("S3T6 (measurement half): measure Z + X, emit bounding box.")
    print("       Heavy beam. Ctrl-C is NOT a safe stop -- hand on the 24V kill.")
    try:
        for n in ("Z1", "Z2", "X"):
            M[n].enable(); time.sleep_ms(STAGGER_MS)

        z = measure_z()
        if z is None: return
        x = measure_x()
        if x is None: return

        tx, tz, b = x["travel"], z["travel"], BUFFER_STEPS
        print("  ==========================================================")
        print("  BOUNDING BOX (steps)")
        print("    hard   X: [0, {}]   Z: [0, {}]".format(tx, tz))
        print("    soft   X: [{}, {}]   Z: [{}, {}]   (inset {} ~5 mm)".format(b, tx - b, b, tz - b, b))
        print("    center X: {}   Z: {}".format(tx // 2, tz // 2))
        print("    squaring  delta_bottom = {}   delta_top = {}".format(z["delta_bottom"], z["delta_top"]))
        print("  ----------------------------------------------------------")
        print("  First-touch used for every limit -> the box is a true rectangle")
        print("  inscribed inside the reachable area (offset switches would skew it).")
        print("  ==========================================================")

    except KeyboardInterrupt:
        print("aborted")
    finally:
        disable_all()
        print("All drivers disabled.")


run()