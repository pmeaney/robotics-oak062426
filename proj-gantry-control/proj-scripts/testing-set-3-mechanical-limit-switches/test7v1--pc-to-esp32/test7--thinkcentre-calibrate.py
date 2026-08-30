# test7--esp32-command-listener.py  --  S3T6 Stage 2, the "hands" half.
# =============================================================================
# Reads orders from the host over USB serial and replies, one line at a time.
# Runs as main.py so the board boots into listen mode; the ThinkCentre (brain)
# talks to it with pyserial. The board holds NO map -- it executes orders and
# reports raw numbers. Endstop reflex stays local.
#
# I/O NOTE (why UART, not sys.stdin):
#   `sys.stdin.readline()` does NOT reliably receive host bytes on this board when
#   running as main.py, and `mpremote run` streams output only (no stdin channel).
#   The reliable primitive is reading UART0 directly -- the same UART the USB-serial
#   is wired to. We read/buffer bytes until a newline, then dispatch.
#
# PROTOCOL (line-based; one order per line, one reply per order; reply starts OK/ERR):
#   PING            -> OK PONG
#   STATUS          -> OK STATUS Z1B=1 Z2B=1 Z1T=1 Z2T=1 XZ1=1 XZ2=1
#   HOME X | Z      -> OK HOME ...        (stub for now)
#   MEASURE X | Z   -> OK MEASURE ...     (stub for now)
#   MOVE X <steps>  -> OK MOVE X pos=...  (stub for now)
#   DISABLE         -> OK DISABLE
#   ERR unknown | badarg | fault <detail> | runaway
# =============================================================================

from machine import Pin, UART
import time

# --- serial link: UART0 is the USB-serial port on this board ------------------
uart = UART(0, 115200)
uart.init(115200, bits=8, parity=None, stop=1, timeout=10)

def send(line):
    uart.write(line + "\r\n")

# --- hardware (confirmed map) ------------------------------------------------
SWITCHES = [("Z1B", 34), ("Z2B", 15), ("Z1T", 35), ("Z2T", 5), ("XZ1", 32), ("XZ2", 4)]
S = {name: Pin(gpio, Pin.IN) for name, gpio in SWITCHES}

EN = {"Z1": 25, "Z2": 13, "X": 18}
DISABLE_LEVEL = 1
_en = {n: Pin(g, Pin.OUT, value=DISABLE_LEVEL) for n, g in EN.items()}   # boot = disabled

# --- handlers ----------------------------------------------------------------
def cmd_ping(args):
    return "OK PONG"

def cmd_status(args):
    return "OK STATUS " + " ".join("{}={}".format(n, S[n].value()) for n, _ in SWITCHES)

def cmd_home(args):
    if not args or args[0] not in ("X", "Z"):
        return "ERR badarg"
    return "OK HOME {} (stub)".format(args[0])

def cmd_measure(args):
    if not args or args[0] not in ("X", "Z"):
        return "ERR badarg"
    return "OK MEASURE {} (stub)".format(args[0])

def cmd_move(args):
    if len(args) < 2:
        return "ERR badarg"
    try:
        steps = int(args[1])
    except ValueError:
        return "ERR badarg"
    return "OK MOVE {} pos={} (stub)".format(args[0], steps)

def cmd_disable(args):
    for m in _en.values():
        m.value(DISABLE_LEVEL)
    return "OK DISABLE"

DISPATCH = {
    "PING": cmd_ping, "STATUS": cmd_status, "HOME": cmd_home,
    "MEASURE": cmd_measure, "MOVE": cmd_move, "DISABLE": cmd_disable,
}

def handle(line):
    parts = line.strip().split()
    if not parts:
        return None
    verb, args = parts[0].upper(), parts[1:]
    fn = DISPATCH.get(verb)
    if fn is None:
        return "ERR unknown"
    try:
        return fn(args)
    except Exception as e:
        return "ERR fault {}".format(e)

# --- listen loop: read UART bytes, buffer to newline, dispatch ---------------
def listen():
    send("OK READY")
    buf = b""
    while True:
        chunk = uart.read()                  # returns available bytes, or None
        if not chunk:
            time.sleep_ms(10)
            continue
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            reply = handle(line.decode(errors="replace"))
            if reply is not None:
                send(reply)

if __name__ == "__main__":
    listen()