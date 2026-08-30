# test7--echo-probe.py -- MINIMAL proof that the board can RECEIVE a line from the
# host over USB serial. No motion, no command set. Just: PC sends a line -> board
# echoes it back. This isolates the one thing that failed all day (input path).
#
# Verified pattern (MicroPython docs / forums) for a board whose USB serial IS the
# REPL/stdio line (classic ESP32 + CP2102, like the ELEGOO):
#   * micropython.kbd_intr(-1)  -> stop the REPL from eating incoming bytes
#   * poll sys.stdin, read lines from sys.stdin.buffer (no blocking readline)
#
# Deploy as main.py, power-cycle, then from the host send a line and read the echo.

import sys
import select
import micropython

micropython.kbd_intr(-1)                 # REPL no longer intercepts input

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

def readline():
    buf = b""
    while True:
        if poll.poll(0):
            ch = sys.stdin.buffer.read(1)
            if ch in (b"\n", b"\r"):
                if buf:
                    return buf
            elif ch:
                buf += ch

sys.stdout.buffer.write(b"ECHO READY\n")
while True:
    line = readline()
    sys.stdout.buffer.write(b"GOT: " + line + b"\n")