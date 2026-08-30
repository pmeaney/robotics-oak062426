# Test 7 — PC ↔ ESP32 (calibration over serial)

Folder: `test7--pc-to-esp32`

This is **S3T6 Stage 2**: the calibration function built as the brain/hands split it was
always meant to be. Unlike every earlier test (one MicroPython file run with `mpremote`),
Test 7 is **two programs on two machines** that only work as a pair, talking over the USB
serial line with a simple line-based protocol.

- **Brain — ThinkCentre (CPython):** owns `prototype-shelf.yaml`, all of the coordinate math, the
  bounding box, and the verify decision. Reads the human-declared shelf data, orders the
  ESP32 to home + measure, does the math, verifies, and writes calibration back to the YAML.
- **Hands — ESP32 (MicroPython):** holds no map. Sits in a loop, executes one order at a
  time with the proven motion code, reports raw numbers. The endstop reflex stays local.

The YAML lives only on the brain. The ESP32 never reads or writes a file — it only speaks
the protocol. (If the ESP32 ever needs YAML, something is on the wrong side of the split.)

---

## Files (4)

| File | Machine | Runtime | Role |
|------|---------|---------|------|
| `test7--thinkcentre-calibrate.py` | ThinkCentre | CPython 3 | Brain: serial link, YAML read/write, box math, verify |
| `test7--esp32-command-listener.py` | ESP32 | MicroPython | Hands: listen loop, executes orders, reports numbers |
| `requirements.txt` | ThinkCentre | — | Host-side Python deps (see below) |
| `prototype-shelf.yaml` | ThinkCentre | — | The local DB — `shelf:` (read) + `gantry:` (written). Brain-side only |

Suggested layout so it's obvious which file runs where:

```
test7--pc-to-esp32/
├── host/
│   ├── test7--thinkcentre-calibrate.py
│   ├── requirements.txt
│   └── prototype-shelf.yaml               # read for shelf:, written for gantry:
└── esp32/
    └── test7--esp32-command-listener.py   # flashed as main.py, or launched first
```

> The YAML may already live at the project root rather than in `host/`. Wherever it is, point
> `YAML_PATH` in `test7--thinkcentre-calibrate.py` at it — just keep it on the ThinkCentre side.

---

## Python dependencies

**ThinkCentre (host) only** — install with pip:

```
pyserial
pyyaml
```

```bash
# If you're at the folder `robotics-oak062426/proj-gantry-control` then you'd run:
# pip install -r proj-scripts/testing-set-3-mechanical-limit-switches/test7--pc-to-esp32/requirements.txt 
# OR, if all else fails...
# python3 -m venv someVenvFolderName
# source someVenvFolderName/bin/activate
# pip install pyserial pyyaml
```

- `pyserial` — opens the USB serial port and speaks the line protocol to the ESP32.
- `pyyaml` — reads the `shelf:` section and writes the `gantry:` calibration block.

**ESP32 (board):** *no installs.* MicroPython built-ins only — and specifically **no yaml**
(it doesn't exist on MicroPython, and the board never touches the file by design).

---

## Running it

# Test 7 — First-Run Steps

**What this is:** calibration split across two machines — the ThinkCentre (brain) sends
orders over USB serial and the ESP32 (hands) executes them. This file is just how to run
it the first time.

**Scaffold stage:** only `PING` works yet — the motion handlers (`HOME`/`MEASURE`/`MOVE`)
are still TODO. So prove the *link* first; full calibration comes once those are filled in.

**One gotcha — the serial port:** only one program can hold the port at a time. That's why
step 3 loads the listener as `main.py` and resets — so `mpremote` releases the port and the
host script can open it. (`mpremote run` would keep the port and block the host script.)

---

1. On the ThinkCentre, activate the venv and install deps:
   `pip install pyserial pyyaml`

2. Find the ESP32 port: `ls /dev/ttyUSB*`. This is your port. We'll assume it's
   `/dev/ttyUSB0` below — but if yours is different, replace `/dev/ttyUSB0` everywhere
   with your own similar-looking `ttyUSB` name.

3. Put the listener on the board as main.py, then reset it (this frees the port):
   `mpremote fs cp test7--esp32-command-listener.py :main.py`
   `mpremote reset`

4. Confirm the link — you want `OK READY` then `OK PONG`:
   ```
   python3 -c "import serial,time; s=serial.Serial('/dev/ttyUSB0',115200,timeout=3); time.sleep(2); s.reset_input_buffer(); s.write(b'PING\n'); print(s.readline())"
   ```

5. Once PING works: in `test7--thinkcentre-calibrate.py` set `PORT` to `/dev/ttyUSB0`, set
   `BAUD` to 115200, set `YAML_PATH` to your `prototype-shelf.yaml`, then run it:
   `python3 test7--thinkcentre-calibrate.py`
   (full calibration only works after the motion handlers are filled in.)
   
The host waits for the listener's `OK READY`, runs the calibration sequence, and — only if
the verify move lands within tolerance — writes the `gantry:` block into `prototype-shelf.yaml`.

**First thing to prove:** a bare `PING` → `OK PONG` round-trip over pyserial, before any
motion. That validates the whole transport with zero risk; then fill in one motion handler
at a time. Hand on the 24V kill once motion is live — Ctrl-C is still not a safe stop.

## Protocol (quick reference)

Line-based, ASCII, newline-terminated. One order per line, one reply per order; every reply
starts `OK` or `ERR`. Full vocabulary is documented in the listener's header comments.

```
PING            -> OK PONG
STATUS          -> OK STATUS Z1B=1 Z2B=1 ...
HOME X | Z      -> OK HOME Z lead=Z2B delta=281
MEASURE X | Z   -> OK MEASURE Z travel=11247 dtop=260
MOVE X <steps>  -> OK MOVE X pos=5405
DISABLE         -> OK DISABLE
ERR unknown | badarg | fault <detail> | runaway
```


# Test 7 — Build Plan (what's left to make it real)

The transport is proven (`PING` -> `OK PONG`). What remains is filling the listener's
stubbed handlers one at a time — cheapest and safest first — then the host orchestration.
Each rung: fill one handler, prove it with a one-liner over serial, then move to the next.
Same "prove the layer" rule as the rest of the project.

Status legend: [x] done · [ ] todo

- [x] **Transport** — `PING` -> `OK PONG` over pyserial. Link works end to end.

- [ ] **STATUS** (no motion) — read the six switch pins, format them.
      Proves pin reads over the protocol. Test: send `STATUS`, expect `OK STATUS Z1B=1 ...`.

- [ ] **DISABLE** (no motion) — drive all three EN pins to disabled.
      Your serial-side safety command. Test: send `DISABLE`, expect `OK DISABLE`.

- [ ] **MOVE <axis> <steps>** (first real motion) — small bounded move, reflex live,
      report resulting position. Test: `MOVE X 200`, expect `OK MOVE X pos=...`.
      Hand on the 24V kill from here on.

- [ ] **HOME X**, then **HOME Z** — drop in the proven S3T4 (X) / S3T5 (Z) homing.
      Reply with zero end (X) or lead switch + delta (Z).

- [ ] **MEASURE X / MEASURE Z** — proven travel + delta logic.
      Reply travel (+ dtop for Z).

- [ ] **Host settle fix** — in `test7--thinkcentre-calibrate.py` `wait_ready()`, add
      `time.sleep(2)` + `reset_input_buffer()` after opening the port, so it doesn't race
      the boot-reset that pyserial triggers when it opens the port.

- [ ] **Full run** — `python3 test7--thinkcentre-calibrate.py` drives the whole sequence
      (home + measure both axes, compute box, verify move, write the `gantry:` YAML block).

## Notes carried from bring-up
- Opening the serial port resets the ESP32 (DTR/RTS). Always settle ~2s and flush before
  the first order — that's why the run command uses `time.sleep(2)` + `reset_input_buffer()`.
- The ESP32 reports raw numbers only; all coordinate math lives on the ThinkCentre.
- Ctrl-C is not a safe stop; the 24V kill is. The endstop reflex stays local regardless.