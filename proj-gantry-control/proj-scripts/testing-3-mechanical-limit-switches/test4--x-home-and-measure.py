# test4--x-home-and-measure.py
# Set 3, Ticket 4 (S3T4) -- X home + measure (single-speed).
# Run: mpremote run test4--x-home-and-measure.py
#
# Homes X to the XZ2 end (= zero), backs off to release the switch, then drives to
# the far switch (XZ1) counting steps = travel (the hard stop). center = travel//2.
# Single-speed approach (no fast/slow two-stage yet). Reports travel + center; run
# it a few times and compare the travel numbers -- that spread is your repeatability.
# Does NOT write the YAML (calibration S3T6 does that); this just measures + prints.
#
# Direction is a GUESS: HOME_DIR_LEVEL drives X toward XZ2. If homing trips XZ1
# instead, it's backwards -- the script aborts and tells you to flip it.
#
# Safety:
#  * driver init DISABLED; all motion in try/finally -> disable on any exit.
#  * runaway ceiling: if a target switch never trips (wrong dir, or a NO switch
#    with a broken wire reading idle), the move aborts instead of crashing a rail.
#  * the just-hit switch stays pressed for the first steps of a retreat -- back-off
#    ignores it on purpose (a trip means different things in different phases).
#
# Logic (NO): released = 1, pressed = 0. TRIGGERED = 0.

##################################################
####### Output from running this script:
#
# ❯ mpremote run test4--x-home-and-measure.py
#
# S3T4: X home (-> XZ2) + measure (-> XZ1), single-speed. Ctrl-C to abort.
# [HOME]     driving toward XZ2...
#   XZ2 tripped -> zero set.
# [BACKOFF]  100 steps off XZ2 -> XZ2 released.
# [MEASURE]  driving toward XZ1, counting...
#   XZ1 tripped.
#   RESULT: X travel (hard_stop) = 10811 steps,  center = 5405 steps.
#   backed off XZ1. Rerun and compare travel to gauge repeatability.
# X driver disabled.


from machine import Pin
import time

ENABLE_LEVEL, DISABLE_LEVEL = 0, 1        # TMC2209 EN is active-low

# --- X motor (locked Set 1 wiring; X invert = False) ---
X_EN, X_STEP, X_DIR = 18, 19, 23
HOME_DIR_LEVEL = 0        # DIR bit that drives X toward XZ2 (home). Flip 0<->1 if it goes wrong way.

# --- X endstops (confirmed map) ---
XZ2_PIN = 4               # home end (zero)
XZ1_PIN = 32              # far end
TRIGGERED = 0

# --- motion params ---
STEP_DELAY_US = 1200      # half-period per pulse; larger = slower
BACKOFF_STEPS = 100       # retreat after a hit to release the switch
MAX_STEPS     = 100000    # runaway ceiling per move (sanity guard)

en   = Pin(X_EN,   Pin.OUT, value=DISABLE_LEVEL)   # start disabled
dirp = Pin(X_DIR,  Pin.OUT, value=0)
stp  = Pin(X_STEP, Pin.OUT, value=0)
xz2  = Pin(XZ2_PIN, Pin.IN)
xz1  = Pin(XZ1_PIN, Pin.IN)


def pulse():
    stp.value(1); time.sleep_us(STEP_DELAY_US)
    stp.value(0); time.sleep_us(STEP_DELAY_US)


def home_to_xz2():
    """Drive toward XZ2 until it trips. Abort if we drive INTO XZ1 (wrong dir) or runaway."""
    dirp.value(HOME_DIR_LEVEL)
    time.sleep_us(20)
    xz1_clear = (xz1.value() != TRIGGERED)     # if we start on XZ1, don't false-abort
    steps = 0
    while True:
        if xz2.value() == TRIGGERED:
            return "ok", steps
        if not xz1_clear and xz1.value() != TRIGGERED:
            xz1_clear = True                   # left the start switch -> now arm wrong-dir check
        if xz1_clear and xz1.value() == TRIGGERED:
            return "wrong_dir", steps          # drove into the far switch
        if steps >= MAX_STEPS:
            return "runaway", steps
        pulse(); steps += 1


def step_toward_xz1(n):
    """Step toward XZ1 exactly n times, ignoring switches (used for back-off)."""
    dirp.value(1 - HOME_DIR_LEVEL)
    time.sleep_us(20)
    for _ in range(n):
        pulse()


def measure_to_xz1(start_count):
    """Continue toward XZ1 counting until it trips. travel counts from the XZ2 zero."""
    steps = start_count                        # dir already set toward XZ1 by back-off
    while True:
        if xz1.value() == TRIGGERED:
            return "ok", steps
        if steps >= MAX_STEPS:
            return "runaway", steps
        pulse(); steps += 1


def run():
    print("S3T4: X home (-> XZ2) + measure (-> XZ1), single-speed. Ctrl-C to abort.")
    try:
        en.value(ENABLE_LEVEL)

        # 1) HOME to XZ2 = zero
        print("[HOME]     driving toward XZ2...")
        status, s = home_to_xz2()
        if status == "wrong_dir":
            print("  XZ1 tripped first -> HOME_DIR_LEVEL is backwards. Flip it (0<->1) and rerun.")
            return
        if status == "runaway":
            print("  no switch in {} steps -> check direction / XZ2 wiring.".format(s))
            return
        print("  XZ2 tripped -> zero set.")

        # 2) BACK OFF to release XZ2 (these steps count toward travel: they head to XZ1)
        step_toward_xz1(BACKOFF_STEPS)
        rel = "released" if xz2.value() != TRIGGERED else "STILL PRESSED (raise BACKOFF_STEPS)"
        print("[BACKOFF]  {} steps off XZ2 -> XZ2 {}.".format(BACKOFF_STEPS, rel))

        # 3) MEASURE to XZ1
        print("[MEASURE]  driving toward XZ1, counting...")
        status, travel = measure_to_xz1(BACKOFF_STEPS)
        if status == "runaway":
            print("  XZ1 not reached in {} steps -> check XZ1 wiring.".format(travel))
            return
        center = travel // 2
        print("  XZ1 tripped.")
        print("  RESULT: X travel (hard_stop) = {} steps,  center = {} steps.".format(travel, center))

        # 4) tidy: release XZ1 so nothing sits jammed on the lever
        step_toward_xz1_reverse = HOME_DIR_LEVEL
        dirp.value(step_toward_xz1_reverse)
        time.sleep_us(20)
        for _ in range(BACKOFF_STEPS):
            pulse()
        print("  backed off XZ1. Rerun and compare travel to gauge repeatability.")

    except KeyboardInterrupt:
        print("aborted")
    finally:
        en.value(DISABLE_LEVEL)
        print("X driver disabled.")


run()