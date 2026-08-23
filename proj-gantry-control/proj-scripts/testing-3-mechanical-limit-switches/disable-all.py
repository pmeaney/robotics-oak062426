# disable-all.py
# After-abort / emergency safety: force every motor driver DISABLED. No motion.
# Run: mpremote run disable-all.py
# (The serial port must be free -- interrupt or reset a stuck script first.)
#
# TMC2209 EN is active-low, so 1 = DISABLED. This drives all three EN pins high.

from machine import Pin

EN_PINS = {"Z1": 25, "Z2": 13, "X": 18}
DISABLE_LEVEL = 1

for name, gpio in EN_PINS.items():
    Pin(gpio, Pin.OUT, value=DISABLE_LEVEL)
    print("disabled {} (EN GPIO{})".format(name, gpio))

print("all drivers disabled.")