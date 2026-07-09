# Tooling notes — talking to the ESP32

Background and setup detail for the host-side (ThinkCentre / Debian) tooling. The
short version lives in the README; this is the "why" and the troubleshooting.

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
