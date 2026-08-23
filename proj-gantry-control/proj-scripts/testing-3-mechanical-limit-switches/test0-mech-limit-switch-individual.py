# test0--z1b-switch-read.py
# Ticket 0, Part B -- single endstop switch, live read.
# Run: mpremote run test0--z1b-switch-read.py
#
# GPIO34 = Z1B (Z1 vertical, bottom). Input-only pin; the channel keeps its
# external 10k pull-up, so no internal pull is set here.
#
# Wiring (NO / normally-open):  switch COM -> GND,  switch NO -> node A (pull-up node).
# Logic is unchanged from the Hall build: released = 1 (pull-up), pressed = 0 (shorted to GND).
# (If you wire NC instead, the logic inverts: released = 0, pressed = 1.)
#
# No debounce here on purpose: at a 4 Hz poll the contact has long settled.
# Add software debounce in Ticket 2 where a bounce could false-trigger a motion stop.

from machine import Pin
import time

NAME      = "Z1B"
GPIO      = 34
POLL_HZ   = 4                       # reads per second (>= 2 as needed)
PERIOD_MS = 1000 // POLL_HZ

sw = Pin(GPIO, Pin.IN)

def label(v):
    return "(pressed)" if v == 0 else "(released)"

print("Reading {} (GPIO{}) at {} Hz. Released=1, pressed=0. Ctrl-C to stop."
      .format(NAME, GPIO, POLL_HZ))

last = None
try:
    while True:
        v = sw.value()
        mark = "  <- changed" if (last is not None and v != last) else ""
        print("  {} = {} {}{}".format(NAME, v, label(v), mark))
        last = v
        time.sleep_ms(PERIOD_MS)
except KeyboardInterrupt:
    print("stopped")