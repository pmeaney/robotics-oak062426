# test0--z1b-single-read.py
# Ticket 0, Part B -- single A3144 channel, live read.
# Run: mpremote run test0--z1b-single-read.py
#
# GPIO34 = Z1B (Z1 vertical, bottom). Input-only pin; the channel already
# carries an external 10k pull-up, so no internal pull is set here.
# A3144 is active-low: idle = 1 (no field), magnet present = 0.
#
# Prints a fresh reading every poll (default 4x/sec) so you can watch the
# value flip as you move the magnet. "<- changed" flags each transition.
# Ctrl-C to stop.

# | Name | Location | GPIO |
# |------|----------|------|
# | Z1T | Z1 vertical — top | 35 | works
# | Z1B | Z1 vertical — bottom | 34 | not working
# | Z2T | Z2 vertical — top | 5 | works
# | Z2B | Z2 vertical — bottom | 15 | not working
# | XZ1 | Horizontal (X) endstop at the Z1 vertical | 32 | works
# | XZ2 | Horizontal (X) endstop at the Z2 vertical | 4 | not working

from machine import Pin
import time

NAME      = "Z1B"
GPIO      = 4
POLL_HZ   = 4                       # reads per second (>= 2 as needed)
PERIOD_MS = 1000 // POLL_HZ

sensor = Pin(GPIO, Pin.IN)

def label(v):
    return "(magnet)" if v == 0 else "(idle)"

print("Reading {} (GPIO{}) at {} Hz. Idle=1, magnet=0. Ctrl-C to stop."
      .format(NAME, GPIO, POLL_HZ))

last = None
try:
    while True:
        v = sensor.value()
        mark = "  <- changed" if (last is not None and v != last) else ""
        print("  {} = {} {}{}".format(NAME, v, label(v), mark))
        last = v
        time.sleep_ms(PERIOD_MS)
except KeyboardInterrupt:
    print("stopped")