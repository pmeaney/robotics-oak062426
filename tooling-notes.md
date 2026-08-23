# Tooling notes — talking to the ESP32

Background and setup detail for the host-side (ThinkCentre / Debian) tooling. The
short version lives in the README; this is the "why" and the troubleshooting.


# Running Code on the ESP32 — mpremote & Stopping Safely

## What mpremote is

`mpremote` is the official MicroPython remote-control tool. It runs on the
**ThinkCentre** (the host) and talks to the **ESP32** over USB serial. Install it
once with pipx: `pipx install mpremote`. Nothing is installed on the board itself —
our test scripts use only built-in MicroPython modules.

## The command we use

```bash
mpremote run some-file.py
```

`run` copies the script into the board's **RAM** and executes it there, streaming
the board's `print()` output back to your terminal. It does **not** persist the
script to the board's flash — re-running just re-sends it. That's ideal for the
iterate-and-test workflow this project uses.

## ⚠ The Ctrl-C caveat (matters for every motion test)

**Ctrl-C is not a reliable motor stop.** With `mpremote run`, Ctrl-C acts on the
*host-side tool*, and it is only best-effort at forwarding an interrupt to the board
over serial. In practice it can detach mpremote's terminal — output stops — while
the script keeps running on the ESP32 and **the motor keeps moving**. Observed on
this bench: Ctrl-C silenced the terminal but the gantry finished its move.

Our scripts wrap motion in `try/finally` so that a `KeyboardInterrupt` *on the board*
disables the drivers. But that only fires if the interrupt actually reaches the
board. When mpremote detaches first, it never does.

**Treat Ctrl-C as "probably stops it," never as your safety stop.**

## The stop you can trust

A stop that has to travel over serial can't be a safety stop — anything that drops
the link (Ctrl-C, unplugged USB, a crashed host) leaves the motor running. The
trustworthy stops are the ones that don't depend on the host:

- **The endstop reflex** — local to the ESP32, always on. This is why the S3T2 /
  S3T3 reflex tests matter beyond being checkboxes.
- **A physical kill** — a hand-operated switch in the motor power line (or one that
  pulls the drivers' EN line to disabled). Host-independent. Add this before faster
  or heavier runs (especially the Z beam).

## Recovery commands (after an abort)

Only **one** mpremote session can own the serial port at a time. If a run is stuck,
a second command can't grab the port until the first process is gone — so realistic
recovery is: kill the stuck mpremote, reconnect, stop the board, force drivers off.

| Command | Purpose / when |
|---------|----------------|
| `mpremote repl` | Interactive REPL. **Ctrl-C** here interrupts running code more directly; **Ctrl-D** soft-resets (stops the program); **Ctrl-X** exits mpremote. |
| `mpremote reset` | Hard-reset the board — stops any running program. Caveat: on reset, GPIOs return to default until a script re-asserts them, so **follow with `disable-all.py`**. |
| `mpremote run disable-all.py` | Forces every driver EN pin to DISABLED. Run after any abort/reset to guarantee drivers are off. (Port must be free first.) |
| `mpremote exec "<code>"` | One-liner on the board — the no-file version of a quick disable if you don't have the script handy. |

**After-abort habit:** stop the board (`repl` + Ctrl-C, or `reset`), then
`mpremote run disable-all.py` to be certain the coils are released.

## Files referenced here

- `disable-all.py` — enables nothing; drives all three EN pins (Z1 25, Z2 13, X 18)
  to DISABLED. Your after-abort safety net.

  

## The one rule: one program owns the serial port

The ESP32 shows up on Debian as a serial device, `/dev/ttyUSB0` (it uses a CP2102
USB-UART chip). **Only one program can hold that port at a time** — screen, Thonny,
and mpremote all want it. Most "it won't connect" problems trace back to this: another
program is still holding the port.

Symptom:

```
mpremote: failed to access /dev/ttyUSB0 (it may be in use by another program)
```

Confirm the port exists and see what's using it:

```bash
ls /dev/ttyUSB*          # should list /dev/ttyUSB0
sudo lsof /dev/ttyUSB0   # shows any process holding it
```

## screen — the first tool we used

For the earliest tests (one motor at a time), we used **screen** as a raw serial
terminal into the MicroPython REPL:

```bash
screen /dev/ttyUSB0 115200
```

This drops you into the live REPL on the board — you type commands, or paste small
snippets, and they run immediately. It's great for a single interactive poke: bring up
one motor, toggle a pin, see what happens.

**Why we moved on:** screen has no concept of "send a file." You paste code into the
REPL, which is fine for one quick script but awkward once there are several test files
to run and re-run. (Pasting whole files into a REPL can also mangle indentation unless
you use paste mode — Ctrl-E, paste, Ctrl-D.)

**The gotcha that bites everyone:** closing the terminal window does **not** exit
screen. It leaves the session *detached* and still holding `/dev/ttyUSB0`, which then
blocks mpremote. Always exit screen cleanly:

- **Ctrl-A** then **K**, confirm `y` — kills the session and frees the port.

If you forgot and a session is stuck:

```bash
screen -ls                      # list sessions (note the name)
screen -X -S <name> quit        # kill a detached session
screen -wipe                    # clean up dead ones
```

## mpremote — what we use now

**mpremote** is the current tool. It's built for exactly this workflow: running
MicroPython files on the board from your PC.

The key command runs a *local* file directly on the ESP32 without copying it into the
board's flash — output streams back to your terminal:

```bash
mpremote run test1--z1z2-holding.py
```

Edit the file locally, re-run, repeat. That's the whole loop, and it's why mpremote
beats screen once you have multiple test files.

Other useful commands:

```bash
mpremote ls                              # list files stored on the board
mpremote devs                            # list serial devices mpremote can see
mpremote connect /dev/ttyUSB0 ls         # target the port explicitly
mpremote cp somefile.py :somefile.py     # copy a file ONTO the board's flash
```

`run` (execute a local file, nothing persists) is what you want for testing. `cp` is
only for when you want a file to *stay* on the board — e.g. eventually saving one as
`main.py` so it runs on boot.

### Installing mpremote

mpremote is a *tool*, not a project library, so it's installed **globally**, not inside
a project venv. On Debian it isn't in apt, so use pipx:

```bash
sudo apt install pipx
pipx ensurepath
pipx install mpremote
# open a NEW terminal so PATH updates, then confirm:
mpremote --version
```

> Why global, not a venv: keeping tools out of venvs means they're always available and
> don't break when a project folder is moved (a moved venv stops working because its
> paths are baked in). Libraries your code *imports* belong in a venv; tools you *run*
> belong in pipx.

## Quick troubleshooting

- **"no device found" / "in use"** → another program owns the port. Close Thonny, exit
  screen cleanly (Ctrl-A K), or `sudo lsof /dev/ttyUSB0` and stop whatever's holding it.
- **No `/dev/ttyUSB0` at all** → cable or power. Many USB cables are charge-only (no
  data lines); try another cable/port and check the board's power LED.
- **Permission denied on the port** → your user needs the `dialout` group:
  `sudo usermod -aG dialout $USER`, then log out and back in.
- **Ctrl-C during a test** → mpremote stops the running program; the test scripts'
  `try/finally` still disables the motors on the way out. Verify this releases the
  coils cleanly the first time you rely on it.
