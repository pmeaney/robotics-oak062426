# test0--z1b-single-read.py
# Ticket 0, Part B -- single A3144 channel, live read.
# Run: mpremote run test0--z1b-single-read.py
#
# GPIO34 = Z1B (Z1 vertical, bottom). Input-only pin; the channel already
# carries an external 10k pull-up, so no internal pull is set here.
# A3144 is active-low: idle = 1 (no field), magnet present = 0.

from machine import Pin
import time

NAME = "Z1B"
GPIO = 34

sensor = Pin(GPIO, Pin.IN)

def label(v):
    return "(magnet)" if v == 0 else "(idle)"

print("Reading {} (GPIO{}). Idle=1, magnet=0. Ctrl-C to stop.".format(NAME, GPIO))

v = sensor.value()
print("  start: {} = {} {}".format(NAME, v, label(v)))   # confirms read path is live
last = v

try:
    while True:
        v = sensor.value()
        if v != last:                       # print only on edges
            print("  {} = {} {}".format(NAME, v, label(v)))
            last = v
        time.sleep_ms(50)                   # ~20 Hz poll
except KeyboardInterrupt:
    print("stopped")
