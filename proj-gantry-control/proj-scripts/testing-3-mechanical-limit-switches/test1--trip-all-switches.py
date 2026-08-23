

# | Endstop | Axis / End | GPIO |
# |---------|-----------|------|
# | Z1T | Z1 vertical — top | 35 |
# | Z1B | Z1 vertical — bottom | 34 |
# | Z2T | Z2 vertical — top | 5 |
# | Z2B | Z2 vertical — bottom | 15 |
# | XZ1 | X endstop at Z1 vertical | 32 |
# | XZ2 | X endstop at Z2 vertical | 4 |

# test-s3t1-mech-limit-switch-all-six.py
# Set 3, Ticket 1 (S3T1) -- all six endstop switches, live read, standing still.
# Run: mpremote run test-s3t1-mech-limit-switch-all-six.py
#
# Follows S3T0 (single-channel read). Same NO wiring, same logic; this just
# watches all six channels at once, with no motors moving.
#
# TWO CHECKS:
#   1. Baseline -- with nothing pressed, all six read 1. Any 0 at startup =
#      wiring fault on that channel (or a stuck line). Fix before continuing.
#   2. Verify the map -- press each switch by hand; the changed channel prints
#      its label + GPIO. Confirm the label matches the switch you actually
#      pressed. A mismatch means that channel is miswired.
#
# Logic (NO): released = 1 (pull-up), pressed = 0 (shorted to GND). TRIGGERED = 0.
# Every channel has an external pull-up, so no internal pull is set here.
# No debounce: standing still at a low poll rate, the contacts have settled.

from machine import Pin
import time

# Confirmed map (S3T0 assignment).
PINS = [
    ("Z1T", 35),
    ("Z1B", 34),
    ("Z2T",  5),
    ("Z2B", 15),
    ("XZ1", 32),
    ("XZ2",  4),
]

POLL_HZ   = 4
PERIOD_MS = 1000 // POLL_HZ

chans = [(name, gpio, Pin(gpio, Pin.IN)) for name, gpio in PINS]

def st(v):
    return "pressed" if v == 0 else "released"

def snapshot(states):
    return "  ".join("{}={}".format(name, s) for (name, _, _), s in zip(chans, states))

print("S3T1: reading {} channels at {} Hz. released=1, pressed=0 (TRIGGERED=0). Ctrl-C to stop."
      .format(len(chans), POLL_HZ))
print("Press each switch; confirm the printed label matches the one you pressed.")
print("baseline (all should be 1): " + snapshot([p.value() for _, _, p in chans]))

last = None
try:
    while True:
        states = [p.value() for _, _, p in chans]
        if last is not None and states != last:
            for (name, gpio, _), s, s0 in zip(chans, states, last):
                if s != s0:
                    print("  {} (GPIO{}) : {} -> {}   <- changed".format(name, gpio, st(s0), st(s)))
            print("  state: " + snapshot(states))
        last = states
        time.sleep_ms(PERIOD_MS)
except KeyboardInterrupt:
    print("stopped")