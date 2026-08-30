# Test 7 — Run-Through Log

One running record of each step, its command(s), and what actually happened. Companion to
`README-test7.md` (which holds the plan/protocol); this file holds the results.

Format per step: **describe** → **command(s) + what/why** → **result** (including what
didn't work and the fix).

---

## Step 0 — Transport (PING)  ·  ✅ done

**Describe:** prove the two-machine serial link before anything else.

**Command:**
```
python3 -c "import serial,time; s=serial.Serial('/dev/ttyUSB0',115200,timeout=3); time.sleep(2); s.reset_input_buffer(); s.write(b'PING\n'); print(s.readline())"
```

**Result:** ✅ `OK PONG`. First attempt (without the `time.sleep(2)` settle) returned a
stray `OK READY` instead — opening the port resets the ESP32, so the PING raced the boot.
Adding the 2s settle + flush fixed it.

---

## Step 1 — STATUS (read switches, no motion)  ·  ✅ done

**Describe:** the ESP32 reports raw state of all six endstop switches on request. Proves the
board reads its pins and answers over the protocol. NO wiring: released=1, pressed=0.

**Commands:**
```
# a) redeploy the listener + reset (board runs whatever was last flashed)
mpremote fs cp test7--esp32-command-listener.py :main.py
mpremote reset

# b) query STATUS
python3 -c "import serial,time; s=serial.Serial('/dev/ttyUSB0',115200,timeout=3); time.sleep(2); print(s.readline()); s.write(b'STATUS\n'); print(s.readline())"
```

**Result:** ✅ `OK STATUS Z1B=1 Z2B=1 Z1T=1 Z2T=1 XZ1=1 XZ2=1` (all released).

**What didn't work → fix (important quirk):**
- The **first command tried did NOT work.** The originally-provided one-liner used
  `time.sleep(2); s.reset_input_buffer(); s.write(b'STATUS\n'); print(s.readline())` and read
  back `OK READY` instead of the STATUS reply.
- **Why:** a freshly-reset board emits `OK READY` FIRST, then the STATUS reply. The
  `reset_input_buffer()` raced that READY, and `readline()` returned the READY line, not STATUS.
- **The 2nd command worked as expected:** replacing the flush with an explicit
  `print(s.readline())` to consume the `OK READY` line first, THEN sending STATUS, returned
  the correct `OK STATUS ...`.
- **Rule of thumb:** right after a reset, read past the `OK READY` line before your query.
  (The real `test7--thinkcentre-calibrate.py` handles this in `wait_ready()`; only the bare
  one-liners trip on it.)
- On a run with no reset, the leading `readline()` just returns `b''` (times out, no READY) —
  harmless.

**Still to verify:** press one switch by hand and rerun — confirm exactly that channel flips
to `0` (proves the pin→switch map end to end, not just that reads work).

---

## Step 2 — DISABLE (drive EN pins off, no motion)  ·  ⬜ testing

**Describe:** serial-side safety command; drives all three motor EN pins (Z1/Z2/X) to
DISABLED (TMC2209 EN is active-low, so 1 = off). No motion. It's the command MOVE will rely
on, so prove it now.

**Commands:**
```
# a) redeploy the listener + reset (it now has a real DISABLE handler)
mpremote fs cp test7--esp32-command-listener.py :main.py
mpremote reset

# b) send DISABLE (read past OK READY first, since we just reset)
python3 -c "import serial,time; s=serial.Serial('/dev/ttyUSB0',115200,timeout=3); time.sleep(2); print(s.readline()); s.write(b'DISABLE'); print(s.readline())"
```
Expect: `OK READY` then `OK DISABLE`.

**Verify it actually did something (optional but good):** with drivers disabled the motor
shafts turn freely by hand; right after a `MOVE`/hold they'd resist. No electrical way to see
EN state over this protocol yet — the hand-check is the proof.

**Result:** _(fill in: reply seen? shafts free after DISABLE?)_
```bash
❯ python3 -c "import serial,time; s=serial.Serial('/dev/ttyUSB0',115200,timeout=3); time.sleep(2); print(s.readline()); s.write(b'DISABLE'); print(s.readline())"
b'OK READY\r\n'
b'OK READY\r\n'
~/l/robotics-oak062426/p/p/testing-set-3/test7--pc-to-esp32 main !32 ?2     venv-proj-esp32 11:53:33 AM
❯ 
```

Didnt work as expected...  try this:

---

## Step 3 — MOVE  ·  ⬜ todo
## Step 4 — HOME X / HOME Z  ·  ⬜ todo
## Step 5 — MEASURE X / MEASURE Z  ·  ⬜ todo
## Step 6 — Full calibrate run  ·  ⬜ todo
