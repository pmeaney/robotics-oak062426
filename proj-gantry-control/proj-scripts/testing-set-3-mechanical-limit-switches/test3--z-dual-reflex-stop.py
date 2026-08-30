# test3--z-dual-reflex-stop.py
# Set 3, Ticket 3 (S3T3) -- Z dual reflex stop.
# Run: mpremote run test3--z-dual-reflex-stop.py
#
# Both Z motors step together (synced, no racking). All endstops are polled once
# per step; tripping ANY switch by hand halts BOTH Z within ~1 step and disables
# both drivers -- locally, no ThinkCentre. This is the anti-racking "any -> all"
# rule: a trip on one channel kills a DIFFERENT motor too. Proves the reflex
# MECHANISM only -- no homing, no measurement.
#
# The beam sweeps up/down in place so it stays put. If a sweep happens to reach a
# real Z endstop, that just fires the same reflex and stops -- harmless. Still,
# start the beam mid-travel with room up and down, and keep a hand near power
# (on disable, a non-self-locking drive may let the beam settle).
#
# Logic (NO): released = 1, pressed = 0. TRIGGERED = 0.
# Verticals: INVERT {"Z1": False, "Z2": True}, UP_DIR_LEVEL = 1 -> beam rises
#            (verified anti-rack setting from Set 1 Test 2).
# Safety: drivers init DISABLED; all motion in try/finally -> disable on any exit.

from machine import Pin
import time

ENABLE_LEVEL, DISABLE_LEVEL = 0, 1        # TMC2209 EN is active-low

# --- Z motors (locked Set 1 wiring) ---
MOTOR_PINS = {
    "Z1": {"en": 25, "step": 26, "dir": 33},
    "Z2": {"en": 13, "step": 27, "dir": 14},
}
UP_DIR_LEVEL = 1
INVERT = {"Z1": False, "Z2": True}        # verified: beam rises together, no racking

# --- endstops (confirmed map, S3T1) ---
SWITCHES = [
    ("Z1T", 35), ("Z1B", 34),
    ("Z2T",  5), ("Z2B", 15),
    ("XZ1", 32), ("XZ2",  4),
]
TRIGGERED = 0

# --- motion params (tune to taste) ---
STEP_DELAY_US = 1200                       # half-period per pulse; larger = slower
SWEEP_STEPS   = 200                        # steps each direction before reversing
STAGGER_MS    = 5


class Stepper:
    def __init__(self, en, step, dr, invert):
        self.invert = invert
        self.en   = Pin(en,   Pin.OUT, value=DISABLE_LEVEL)   # come up OFF
        self.dir  = Pin(dr,   Pin.OUT, value=0)
        self.step = Pin(step, Pin.OUT, value=0)

    def enable(self):  self.en.value(ENABLE_LEVEL)
    def disable(self): self.en.value(DISABLE_LEVEL)

    def set_direction(self, go_up):
        level = UP_DIR_LEVEL if go_up else (1 - UP_DIR_LEVEL)
        if self.invert:
            level ^= 1
        self.dir.value(level)


motors    = {n: Stepper(p["en"], p["step"], p["dir"], INVERT[n]) for n, p in MOTOR_PINS.items()}
sws       = [(name, Pin(gpio, Pin.IN)) for name, gpio in SWITCHES]
verticals = [motors["Z1"], motors["Z2"]]


def tripped():
    for name, p in sws:
        if p.value() == TRIGGERED:
            return name
    return None


def disable_all():
    for m in motors.values():
        m.disable()


print("S3T3: Z1+Z2 sweeping together. Hand-trip ANY switch -> BOTH stop. Ctrl-C to abort.")
hit   = None
swept = 0
go_up = True
try:
    for n in ("Z1", "Z2"):                 # staggered enable (spread inrush)
        motors[n].enable()
        time.sleep_ms(STAGGER_MS)
    for m in verticals:
        m.set_direction(go_up)
    time.sleep_us(20)                       # DIR setup before first pulse

    while True:
        hit = tripped()                     # poll BEFORE stepping -> <=1 step overtravel
        if hit is not None:
            break
        for m in verticals:                 # raise both STEP together
            m.step.value(1)
        time.sleep_us(STEP_DELAY_US)
        for m in verticals:                 # lower both STEP together
            m.step.value(0)
        time.sleep_us(STEP_DELAY_US)
        swept += 1
        if swept >= SWEEP_STEPS:            # reverse both together
            go_up = not go_up
            for m in verticals:
                m.set_direction(go_up)
            time.sleep_us(20)
            swept = 0

    print("  TRIGGERED by {} -> both Z halted within ~1 step.".format(hit))
except KeyboardInterrupt:
    print("aborted")
finally:
    disable_all()
    print("Both Z drivers disabled.")