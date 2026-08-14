# Endstop Switches — Testing README

## Summary

We're replacing the six A3144 Hall-effect endstops with mechanical snap-action
micro limit switches. The switch is the more robust choice for this build:

- **No heat-sensitive die.** The A3144's die can be killed by soldering; a
  microswitch has no fragile silicon to cook, and the common endstop *modules*
  come pre-soldered on a PCB.
- **Hard mechanical trip point.** A physical lever gives a deterministic,
  repeatable reference for homing — better than a magnetic field that drifts with
  gap, magnet strength, and temperature.
- **Simpler bring-up.** Press the lever and it reads. No magnet pole / gap /
  threshold to fuss with.

The per-channel wiring, GPIO map, and active-low convention all carry over from
the Hall rig — the switch drops into the same node.

> Context: the A3144 failures on this bench traced mostly to solder-heat death and
> per-channel wiring faults, not the Hall sensing principle. That's itself an
> argument for the switch — fewer parts per channel to get wrong, and no die to cook.

---

## The switch

**Class:** SPDT snap-action micro limit switch — 3 terminals (COM / NO / NC),
lever or roller-lever actuator. Representative part: Omron **SS-5GL** / generic
"3D-printer endstop" microswitch.

> **Confirm your exact model** and drop its datasheet values into the table — the
> figures below are typical for this class, not measured from your specific part.

| Spec | Typical (confirm your part) |
|------|-----------------------------|
| Configuration | SPDT snap-action, COM / NO / NC |
| Actuator | Lever / roller-lever |
| Contact rating (power) | ~5 A @ 125–250 VAC |
| Our actual load | ~3.3 V, ~0.33 mA (dry / logic-level) |
| Operate force | ~0.5–1.5 N |
| Pretravel / overtravel | ~0.5 / ~1 mm (model-dependent) |
| Trip repeatability | ~0.01–0.05 mm |
| Mechanical life | ~1,000,000 operations |
| Contact bounce | ~1–5 ms |

---

## Reliability notes (the parts that actually matter here)

- **Wetting current.** We switch only ~0.33 mA (3.3 V through the 10 kΩ pull-up).
  That's low for a silver-contact power switch — contacts can oxidise and go
  intermittent at sub-mA over time. Prefer a switch rated for low-level/logic loads
  or with gold-plated contacts. If a standard silver switch reads flaky, drop the
  pull-up to ~3.3 kΩ (≈1 mA wetting); the extra idle current is negligible.
- **Bounce.** ~1–5 ms of contact chatter. Invisible to a live read (we poll at
  4 Hz), but it can false-trigger a motion stop — add a few-ms software debounce in
  Ticket 2.
- **Wear.** A switch is a contact/wear item (~1 M operations). Mount it to be
  pressed *gently* at the limit, not slammed.

---

## Module pinout & onboard pads

If you use the pre-built endstop **modules** (instead of a bare switch into the
breadboard), each board carries its own conditioning and breaks out to a 3-pin
interface. Three things to get right:

### The 3 pins — S / G / V

| Pin | Meaning | Connect to |
|-----|---------|------------|
| **S** | **S**ignal | a GPIO — reads the switch state |
| **G** | **G**nd | common ground |
| **V** | VCC — **3.3 V power** | the 3.3 V rail (**not 5 V**) |

> **V must be 3.3 V.** The onboard pull-up ties S up to whatever V is. Power the
> module at 5 V and S idles at 5 V — over the ESP32's 3.3 V input limit. At 3.3 V,
> S idles safely at 3.3 V.

### The onboard pads

Note: These pads arrive on the board empty.  In prototyping, we apply the 10k & C104 on the breadboard. However, in production we could solder them to the pads on the devboard itself

| Pad | Role |
|-----|------|
| **10k** | Signal pull-up — holds S high while the switch is open (confirm it's a pull-up on your board) |
| **1k** | LED current-limit resistor, in series with the LED — sets indicator brightness (~1.3 mA). **Not** in the signal path |
| **LED** | State indicator — lights to show the switch state at a glance |
| **C104** (100 nF) | Noise / debounce cap on the signal (or supply) line |

> **Two different 1k roles — don't conflate.** The module's 1k limits *LED* current.
> The 1k on your breadboard rig is *in series with the signal* (RC filter with the
> 10 nF). Same value, different job — this is your recurring 1k-vs-10k trap in a new costume.

> **Don't stack conditioning.** A module already has its own 10k + C104, so with a
> module you connect **S → GPIO, G → GND, V → 3.3 V** and skip the breadboard's
> per-channel 10k/1k/10nF below. Using both doubles the pull-up and stacks the
> filters. Pick one path per channel — module *or* bare switch, not both.

---

## Wiring (carries over from the Hall rig)

Per channel, **NO (normally-open):**

- **COM → GND**
- **NO → node A** — the existing 10 kΩ pull-up node, where the A3144 OUT used to land
- **Keep:** 10 kΩ pull-up → 3.3 V, 1 kΩ series, 10 nF filter, GPIO
- **Drop:** the A3144, its 5 V feed, and the 0.1 µF decoupling (passive switch —
  nothing to power)

**Logic (NO):** released = `1` (pull-up), pressed = `0` (shorted to GND) — identical
to the Hall convention, so nothing upstream changes.

**Fail-safe option (NC):** idle closed, so a broken wire reads "triggered" → safe
stop. Correct for a damage-prevention endstop, but it inverts the logic
(released = `0`, pressed = `1`) and needs the read flipped. Recommendation: **NO**
for bench bring-up, **NC** before the full-size unit.

### GPIO map (current)

| Name | Location | GPIO |
|------|----------|------|
| Z1T | Z1 vertical — top | 35 |
| Z1B | Z1 vertical — bottom | 34 |
| Z2T | Z2 vertical — top | 5 |
| Z2B | Z2 vertical — bottom | 15 |
| XZ1 | Horizontal (X) endstop at the Z1 vertical | 32 |
| XZ2 | Horizontal (X) endstop at the Z2 vertical | 4 |

---

## Test scripts

- **Single-channel live read:** `test0--z1b-switch-read.py` — GPIO34 (Z1B), polls at
  4 Hz, prints `released` / `pressed` with a marker on each transition.
- **Full procedures:** see the tickets doc
  (`gantry-limitation-shelf-dimensions-testing-tickets.md`). The magnet gestures in
  Ticket 0 Part B / Ticket 1 convert to "press the lever"; that conversion is pending
  a re-upload of the current (edited) doc.