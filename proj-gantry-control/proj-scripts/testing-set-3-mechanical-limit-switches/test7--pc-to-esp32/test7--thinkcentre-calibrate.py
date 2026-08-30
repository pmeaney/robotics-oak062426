#!/usr/bin/env python3
# test7--thinkcentre-calibrate.py  --  S3T6 Stage 2, the "brain" half.
# =============================================================================
# Runs on the THINKCENTRE (plain CPython, NOT mpremote). Talks to the ESP32
# listener (esp32-command-listener.py) over USB serial with pyserial, using the
# line-based protocol that file documents. This program is in charge: it reads the
# human-declared shelf data, orders the ESP32 to home + measure, does ALL the
# coordinate math itself, runs a verify move, and writes calibration into the YAML.
#
# BRAIN / HANDS:
#   * This file owns prototype-shelf.yaml, the bounding box, soft stops, centers,
#     and the verify decision. The math lives here.
#   * The ESP32 only executes orders and reports raw numbers. It holds no map.
#   * The YAML write is the last, easy step -- and it happens HERE, on the brain.
#
# DEPENDENCIES:  pip install pyserial pyyaml
# TRANSPORT:     one order per line, one reply per order; every reply starts OK/ERR.
#                The ESP32 must already be in the listener loop before we open the port.
# =============================================================================

import sys
import time

# These are host-side libs (ThinkCentre), not MicroPython:
try:
    import serial            # pyserial
    import yaml              # PyYAML
except ImportError as e:
    sys.exit("missing dependency: {} -- run: pip install pyserial pyyaml".format(e))

PORT      = "/dev/ttyUSB0"   # adjust to your ESP32's port (dmesg / ls /dev/ttyUSB*)
BAUD      = 115200
YAML_PATH = "prototype-shelf.yaml"

# Policy the brain applies (see the YAML notes). ~40 steps/mm is provisional.
BUFFER_STEPS = 200           # soft-stop safety zone (~5 mm inset per side)
VERIFY_TOL   = 20            # a verify move must land within this many steps


class Link:
    """Thin wrapper over the serial line that speaks the order/reply protocol."""

    def __init__(self, port, baud):
        self.ser = serial.Serial(port, baud, timeout=120)   # long timeout: moves take a while

    def order(self, line):
        """Send one order, return the single reply line (stripped). Raises on ERR."""
        self.ser.reset_input_buffer()
        self.ser.write((line.strip() + "\n").encode())
        reply = self.ser.readline().decode(errors="replace").strip()
        if not reply:
            raise RuntimeError("no reply to: {}".format(line))
        if reply.startswith("ERR"):
            raise RuntimeError("ESP32 refused '{}' -> {}".format(line, reply))
        return reply

    def wait_ready(self):
        """The listener prints 'OK READY' once; swallow lines until we see it."""
        time.sleep(2)                    # opening the port resets the ESP32; let it boot
        deadline = time.time() + 10
        while time.time() < deadline:
            line = self.ser.readline().decode(errors="replace").strip()
            if line == "OK READY":
                return
        raise RuntimeError("ESP32 never sent OK READY (is the listener running?)")

    def close(self):
        try:
            self.order("DISABLE")        # always leave drivers off
        except Exception:
            pass
        self.ser.close()


def parse_kv(reply):
    """'OK MEASURE Z travel=11247 dtop=260' -> {'travel': '11247', 'dtop': '260'}."""
    out = {}
    for tok in reply.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k] = v
    return out


def calibrate(link, shelf):
    """Order the measurements, do the math here, return the gantry calibration dict."""
    # --- X ---
    link.order("HOME X")
    xm = parse_kv(link.order("MEASURE X"))
    travel_x = int(xm["travel"])

    # --- Z (beam, first-touch + deltas reported by the hands) ---
    zh = parse_kv(link.order("HOME Z"))
    zm = parse_kv(link.order("MEASURE Z"))
    travel_z = int(zm["travel"])
    delta_bottom = int(zh.get("delta", 0))
    delta_top    = int(zm.get("dtop", 0))

    # --- MATH lives here (brain), not on the ESP32 ---
    b = BUFFER_STEPS
    calib = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "axes": {
            "X":  {"hard_stop_steps": travel_x, "soft_stop_steps": travel_x - b, "center_steps": travel_x // 2},
            "Z1": {"hard_stop_steps": travel_z, "soft_stop_steps": travel_z - b, "center_steps": travel_z // 2},
            "Z2": {"hard_stop_steps": travel_z, "soft_stop_steps": travel_z - b, "center_steps": travel_z // 2},
        },
        "squaring": {"delta_bottom_steps": delta_bottom, "delta_top_steps": delta_top},
        "bounding_box": {
            "hard": {"x": [0, travel_x], "z": [0, travel_z]},
            "soft": {"x": [b, travel_x - b], "z": [b, travel_z - b]},
        },
    }

    # --- VERIFY: order a move to a computed interior point, confirm arrival ---
    target = travel_x // 2
    vm = parse_kv(link.order("MOVE X {}".format(target)))
    landed = int(vm.get("pos", -1))
    calib["verify"] = {"target": target, "landed": landed,
                       "ok": abs(landed - target) <= VERIFY_TOL}
    return calib


def main():
    with open(YAML_PATH) as f:
        doc = yaml.safe_load(f)
    shelf = doc.get("shelf", {})
    if not shelf:
        sys.exit("no shelf: section in {} -- declare it first (rows/cols/cell sizes).".format(YAML_PATH))

    link = Link(PORT, BAUD)
    try:
        link.wait_ready()
        print("ESP32 ready. Calibrating (hand on the 24V kill)...")
        calib = calibrate(link, shelf)
    finally:
        link.close()

    if not calib["verify"]["ok"]:
        sys.exit("verify move out of tolerance {} -> NOT written. Re-home and retry.".format(calib["verify"]))

    # --- write calibration back into the YAML (the done-gate) ---
    doc["gantry"] = calib
    with open(YAML_PATH, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)
    print("calibrated. travel_x={} travel_z={} box(soft x/z)={}/{} -> written to {}".format(
        calib["axes"]["X"]["hard_stop_steps"],
        calib["axes"]["Z1"]["hard_stop_steps"],
        calib["bounding_box"]["soft"]["x"],
        calib["bounding_box"]["soft"]["z"],
        YAML_PATH))


if __name__ == "__main__":
    main()
