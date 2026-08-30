#!/usr/bin/env python3
# test7--send.py -- send ONE command to the ESP32 listener and print its reply.
# Usage:  python3 test7--send.py DISABLE
#         python3 test7--send.py STATUS
#         python3 test7--send.py MOVE X 200
#
# Why this exists: hand-typing at `mpremote repl` talks to MicroPython, not to the
# listener (so DISABLE/STATUS come back as NameError). And bare pyserial one-liners
# keep tripping on the boot-reset (`OK READY` first) and missing newlines. This does
# all of that correctly, once:
#   - opens the port with pyserial (lets main.py run normally on the board)
#   - settles for the boot-reset the open triggers
#   - reads PAST the one-time `OK READY` handshake
#   - sends the command with a newline, prints the single reply line
#
# It does NOT drive motion logic -- it's just the clean way to poke one command.

import sys
import time
import serial

PORT = "/dev/ttyUSB0"      # change if yours differs (ls /dev/ttyUSB*)
BAUD = 115200

if len(sys.argv) < 2:
    sys.exit("usage: python3 test7--send.py <COMMAND> [args...]   e.g. DISABLE")

cmd = " ".join(sys.argv[1:])

s = serial.Serial(PORT, BAUD, timeout=3)
time.sleep(2)                                   # opening the port resets the ESP32; let it boot

# swallow the one-time OK READY (and any boot chatter) before sending our command
deadline = time.time() + 5
while time.time() < deadline:
    line = s.readline().decode(errors="replace").strip()
    if line == "OK READY":
        break
    if line == "":
        break                                   # no reset this run -> nothing to swallow

s.reset_input_buffer()
s.write((cmd + "\n").encode())
reply = s.readline().decode(errors="replace").strip()
print(reply if reply else "(no reply -- is main.py running? try a power-cycle)")
s.close()