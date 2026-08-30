# test7--esp32-command-listener.py  --  S3T6 Stage 2, the "hands" half.
# =============================================================================
# WHAT THIS IS (and how Stage 2 differs from test6 / Stage 1)
# =============================================================================
# Every test so far (test0..test6) was ONE program running ON the ESP32, driving
# motors directly, with `mpremote run` just streaming its prints back. The ESP32
# was in charge and the ThinkCentre was a dumb terminal.
#
# Stage 2 flips that. The program in charge (calibration) runs on the THINKCENTRE
# -- the brain. But the brain has no GPIO; it can't touch a motor. So it has to
# TELL the ESP32 what to do over the serial line and read answers back. That
# conversation is the new thing Stage 2 introduces, and this file is the ESP32
# side of it: instead of "run a fixed script and exit," the ESP32 now sits in a
# loop, LISTENS for orders, executes each with the proven motion code, and REPLIES.
#
# This is the brain/hands split becoming real running code on two machines:
#   * ThinkCentre = brain: owns prototype-shelf.yaml, all coordinate math, the
#     bounding box, the verify decision. Decides WHAT and sends orders.
#   * ESP32 (this) = hands: holds NO coordinate map. Executes an order, reports
#     raw numbers, forgets. The always-on endstop reflex still lives here too.
#
# The YAML write is the easy last step, and it happens on the BRAIN, not here --
# this file never reads or writes a file. It only ever speaks the protocol below.
#
# =============================================================================
# TRANSPORT
# =============================================================================
# USB serial (the same link mpremote uses). In production this runs as main.py so
# the ESP32 boots straight into listen mode, and the ThinkCentre talks to it with
# pyserial. During bring-up you can drive it by typing lines into the REPL.
# One command per line, ASCII, newline-terminated. One reply line per command.
#
# =============================================================================
# PROTOCOL  (line-based; host -> ESP32 orders, ESP32 -> host replies)
# =============================================================================
# Every reply starts with "OK" or "ERR". Exactly one reply per order.
#
#   ORDER                 REPLY (example)                     MEANING
#   PING                  OK PONG                             liveness check
#   STATUS                OK STATUS Z1B=1 Z2B=1 ... XZ1=1     raw switch states
#   HOME X                OK HOME X zero=XZ2                  home X to its zero end
#   HOME Z                OK HOME Z lead=Z2B delta=281        beam first-touch + delta
#   MEASURE X             OK MEASURE X travel=10810           drive far end, count steps
#   MEASURE Z             OK MEASURE Z travel=11247 dtop=260  travel + top delta
#   MOVE X 5405           OK MOVE X pos=5405                  relative/absolute move (verify)
#   DISABLE               OK DISABLE                          drop all drivers
#
#   ERR unknown           -- order not recognized
#   ERR badarg            -- missing/negative/absurd argument (sanity ceiling)
#   ERR fault <detail>    -- a switch fired when it shouldn't have -> position lost
#   ERR runaway           -- target switch never tripped within the ceiling
#
# DESIGN NOTES
#   * The ESP32 reports raw measured numbers (steps, which switch, deltas). It does
#     NOT compute soft stops, centers, or the box -- that's the brain's math.
#   * The reflex is still local and always on: any unexpected trip aborts the move
#     and comes back as `ERR fault`, so a dropped serial link can't run the machine
#     into a wall (that stop never needed the host).
#   * Keep replies short and single-line so the brain can parse them trivially and
#     a garbled line is easy to reject and re-request.
# =============================================================================

import sys
from machine import Pin

# --- hardware (confirmed map) ------------------------------------------------
# Endstop switches: NO wiring, released=1 / pressed=0.
SWITCHES = [("Z1B", 34), ("Z2B", 15), ("Z1T", 35), ("Z2T", 5), ("XZ1", 32), ("XZ2", 4)]
S = {name: Pin(gpio, Pin.IN) for name, gpio in SWITCHES}

# Motor EN pins driven DISABLED at import so a boot never energizes a driver
# (TMC2209 EN is active-low: 1 = disabled). Used by DISABLE/MOVE in later steps.
EN = {"Z1": 25, "Z2": 13, "X": 18}
DISABLE_LEVEL = 1
_en = {n: Pin(g, Pin.OUT, value=DISABLE_LEVEL) for n, g in EN.items()}

# --- proven motion primitives live here (ported from test4/test5/test6) --------
# The homing, first-touch, squaring, and travel-count logic is already proven; in
# the full build those functions are pasted in above and called by the handlers.
# Stubs below mark exactly where each proven routine plugs in.

def cmd_ping(args):
    return "OK PONG"

def cmd_status(args):
    # raw switch states, released=1 / pressed=0
    return "OK STATUS " + " ".join("{}={}".format(n, S[n].value()) for n, _ in SWITCHES)

def cmd_home(args):
    # args = ["X"] or ["Z"];  call the proven S3T4 (X) / S3T5 (Z) homing.
    if not args or args[0] not in ("X", "Z"):
        return "ERR badarg"
    axis = args[0]
    # TODO: run proven homing; return lead switch + delta for Z, zero end for X.
    return "OK HOME {} (wire in proven homing)".format(axis)

def cmd_measure(args):
    if not args or args[0] not in ("X", "Z"):
        return "ERR badarg"
    axis = args[0]
    # TODO: run proven travel measurement; return travel (+ dtop for Z).
    return "OK MEASURE {} (wire in proven measure)".format(axis)

def cmd_move(args):
    if len(args) < 2:
        return "ERR badarg"
    axis = args[0]
    try:
        steps = int(args[1])
    except ValueError:
        return "ERR badarg"
    # TODO: sanity-ceiling the target, then step; return resulting position.
    return "OK MOVE {} pos={} (wire in proven move)".format(axis, steps)

def cmd_disable(args):
    for m in _en.values():
        m.value(DISABLE_LEVEL)          # active-low: 1 = disabled
    return "OK DISABLE"

DISPATCH = {
    "PING":    cmd_ping,
    "STATUS":  cmd_status,
    "HOME":    cmd_home,
    "MEASURE": cmd_measure,
    "MOVE":    cmd_move,
    "DISABLE": cmd_disable,
}


def handle(line):
    """Parse one order line and return exactly one reply line."""
    parts = line.strip().split()
    if not parts:
        return None                      # blank line -> no reply
    verb, args = parts[0].upper(), parts[1:]
    fn = DISPATCH.get(verb)
    if fn is None:
        return "ERR unknown"
    try:
        return fn(args)
    except Exception as e:               # never let a handler crash the listener
        return "ERR fault {}".format(e)


def listen():
    """Block on serial, one order at a time, reply on each. Drivers start DISABLED."""
    # Motor EN pins were driven DISABLED at import (top of file), so the board is
    # safe on boot, before any order arrives.
    print("OK READY")                    # handshake line the brain waits for
    while True:
        line = sys.stdin.readline()      # blocks for one newline-terminated order
        if not line:
            continue
        reply = handle(line)
        if reply is not None:
            print(reply)                 # single-line reply over the same serial


if __name__ == "__main__":
    listen()