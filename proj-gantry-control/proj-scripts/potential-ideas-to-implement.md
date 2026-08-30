# Potential Ideas to Implement

A parking lot for ideas worth keeping but *not* worth building yet. Nothing here is read by
any code. Move an item into a real ticket + config only when the layer that needs it exists.

---

## Self-calibration triggers (Mission-layer policy)

**Status:** idea only. Deferred — the Mission layer that would read this doesn't exist yet,
and calibration only needs to run manually for now.

The concept: recalibration shouldn't only be manual. Three kinds of trigger were sketched —

- **Event-driven** — a change to the shelf definition invalidates calibration → force a full recal.
- **Time-driven** — a schedule (e.g. weekly/monthly) catches drift you can't see. Needs a
  clock, so it lives on the ThinkCentre.

Two *weights* of calibration are worth keeping as a distinction whenever this is built:
- `rehome` — home each axis to refresh zero. Fast.
- `full` — rehome + re-measure travel + rebuild the bounding box. Slow.

**Dropped for now:** the *opportunistic* trigger (recalibrate at corner cells because the
beam is already near the switches) and its drift-sensor idea (compare fresh squaring delta
to stored, flag deviation). Genuinely clever, but it's elaborate machinery for a problem
(unnoticed long-term drift) that hasn't actually come up. The switches aren't expected to
change. Revisit if drift ever bites.

**When to revive:** once Stage 2 (the ThinkCentre calibration function) and a Mission/circuit
layer exist. At that point the config shape will be informed by real needs instead of guessed.

---

## (add future ideas below)
