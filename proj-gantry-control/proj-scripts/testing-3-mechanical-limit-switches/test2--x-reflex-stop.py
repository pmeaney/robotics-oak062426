# test2--x-reflex-stop.py
# Set 3, Ticket 2 (S3T2) -- X reflex stop.
# Run: mpremote run test2--x-reflex-stop.py
#
# X steps in a slow back-and-forth sweep (stays put; won't wander to a rail, since
# no soft limits exist yet). All six endstops are polled once per step; tripping
# ANY of them by hand halts X within ~1 step and disables the driver -- locally,
# no ThinkCentre. Proves the reflex MECHANISM only: no homing, no back-off, no wall.
# Hand-trip switches with the carriage AWAY from the real endstops.
#
# Logic (NO): released = 1, pressed = 0. TRIGGERED = 0.
# Safety: driver starts DISABLED; all motion in try/finally so it disables on any exit.

from machine import Pin
import time

# --- X motor pins (EN active-low). Confirmed against Set 1 locked wiring. ---
X_EN, X_STEP, X_DIR = 18, 19, 23
ENABLE_LEVEL, DISABLE_LEVEL = 0, 1      # TMC2209 EN is active-low

# --- endstops (confirmed map, S3T1) ---
SWITCHES = [
    ("Z1T", 35), ("Z1B", 34),
    ("Z2T",  5), ("Z2B", 15),
    ("XZ1", 32), ("XZ2",  4),
]
TRIGGERED = 0

# --- motion params (tune to taste) ---
STEP_US     = 1200                       # per half-pulse; larger = slower
SWEEP_STEPS = 200                        # steps each direction before reversing

en   = Pin(X_EN,   Pin.OUT, value=DISABLE_LEVEL)   # start disabled
step = Pin(X_STEP, Pin.OUT, value=0)
dirp = Pin(X_DIR,  Pin.OUT, value=0)
sws  = [(name, Pin(gpio, Pin.IN)) for name, gpio in SWITCHES]

def tripped():
    for name, p in sws:
        if p.value() == TRIGGERED:
            return name
    return None

def pulse():
    step.value(1); time.sleep_us(STEP_US)
    step.value(0); time.sleep_us(STEP_US)

print("S3T2: X sweeping slowly. Hand-trip ANY switch to stop. Ctrl-C to abort.")
hit = None
swept = 0
try:
    en.value(ENABLE_LEVEL)
    while True:
        hit = tripped()                  # poll BEFORE stepping -> <=1 step overtravel
        if hit is not None:
            break
        pulse()
        swept += 1
        if swept >= SWEEP_STEPS:
            dirp.value(1 - dirp.value())  # reverse direction
            swept = 0
    print("  TRIGGERED by {} -> X halted within ~1 step.".format(hit))
except KeyboardInterrupt:
    print("aborted")
finally:
    en.value(DISABLE_LEVEL)
    print("X driver disabled.")