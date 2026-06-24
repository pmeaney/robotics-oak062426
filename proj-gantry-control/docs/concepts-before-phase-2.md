# Concepts to know prior to Phase 2: Testing all 3 motors

> A project-specific primer. Written for a software engineer who has wired a 12V
> solar system but hasn't formally studied electronics. Wherever it helps, I lean
> on two kinds of analogy you already own: **plumbing/water** (good for current and
> voltage) and **software systems** (good for shared state, references, and
> contention).

---

## How to read this document

Almost every concept in your list is one facet of a single underlying story:
**how current flows in loops, and how the voltage drops it creates along the way
can quietly corrupt the "zero" that your logic depends on.** If you understand
three foundational ideas first, the eighteen concepts stop being eighteen things
to memorize and become one thing seen from different angles.

So before the list, read the **Foundations** section. Then each listed concept has
the five sub-items you asked for:

1. What it is in general / what to know about it
2. Context, related or opposing concepts, how it goes wrong and how it's solved
3. Whether it's dangerous if mis-applied
4. Its relevance to your project
5. Examples in your project — overview of gotchas, a zoom into the relevant parts,
   and explanations of any new sub-concepts that come up (these are flagged as
   **Sub-concepts to know** and explained inline).

A short **concept map** at the end shows how they all connect.

---

## Foundations (read this first)

These three ideas are the bedrock. Everything else is a consequence.

### Foundation 1 — Voltage is always a *difference between two points*

There is no such thing as "the voltage at a point" in isolation. Voltage is a
*difference*. When a multimeter says "3.3V," it secretly means "3.3V **relative to
wherever I put the black probe**." Move the black probe and the number changes.

The software analogy that makes this click: voltage is like a **timestamp measured
against an epoch**, or a **coordinate measured from an origin**. The number `1,700,000,000`
is meaningless until you say "seconds since the Unix epoch." Two services that
disagree about the epoch will exchange numbers that look fine individually but mean
totally different moments. Electrically, the shared epoch is called **ground** (or
**reference**), and two subsystems that don't share it will exchange voltages that
are equally meaningless to each other.

This single fact is the root of *common ground, common reference, logic reference,
ground bounce, and common-impedance coupling*. Hold onto it.

### Foundation 2 — Current always flows in a complete loop

Current never just "goes to" a load and stops. It leaves the supply's positive
terminal, goes through the load, and **must return** to the supply's negative
terminal. Out and back, always a loop. The water analogy: a pump pushes water out
through the pipes and the same water must return to the pump; there is no "using up"
the water.

The half people forget is the **return path** — the trip back to the negative
terminal, usually through ground/negative wiring. The return path carries exactly
as much current as the supply path, and it has just as much ability to cause
trouble. This is the root of *return currents, shared segment, and star vs daisy-chain
grounding*.

### Foundation 3 — Every real conductor has impedance, and current across impedance makes a voltage (Ohm's Law)

A perfect wire would have zero resistance. Real wire, real connectors, real solder
joints all have a small but nonzero **impedance** (think "resistance" for now;
we'll refine the word later). Ohm's Law says:

> **V = I × R**  — voltage drop equals current times resistance.

So whenever current `I` flows through a conductor with resistance `R`, a voltage `V`
appears *across that conductor*. A "ground wire" carrying 1.2A through 0.05Ω develops
1.2 × 0.05 = 0.06V (60mV) from one end to the other. That means the two ends of your
"ground" are **not at the same voltage** while current flows. You wired solar, so
you've met this already: it's the same reason a long run of thin wire from panel to
charge controller "loses voltage." That loss is `I × R` along the wire.

This is the root of *ground bounce, IR drop, shared impedance, and why grounds want
to be low-impedance*.

> **Sub-concept to know — IR drop.** "IR drop" is just engineers pronouncing the
> formula: I (current) times R (resistance) equals the voltage *dropped* across a
> conductor. When someone says "you've got IR drop on your ground," they mean
> "current flowing through your ground wire is creating a voltage along it, so your
> ground isn't at the same potential everywhere." It's not a defect — it's physics —
> but you manage it by keeping `R` small (thick, short wire) and not forcing big and
> small currents to share the same `R`.

With those three in hand, here are your eighteen.

---

## 1. Common ground

**1. What it is.** A *common ground* is a single shared 0V reference node that every
part of your system connects to, so that everybody agrees on what "zero volts" means.
It's Foundation 1 made physical: the shared epoch all your voltages are measured from.

**2. Context, opposing concept, failure & fix.** The opposing situation is two
subsystems with *separate, unconnected* grounds — they "float" relative to each other,
and a signal sent from one to the other is interpreted against the wrong zero, so it
reads as garbage. The fix is simply to tie their grounds together. The related-but-distinct
ideas are **common reference** (the general principle) and **logic reference** (the
specific ground your digital chips use) — both covered below. A subtle failure mode is
having a common ground that exists but is *poorly routed* (through a long, shared, or
high-impedance path) — it's "common" but not "clean," which is what most of this
document is really about.

**3. Danger if mis-applied.** Mostly a *correctness* hazard rather than a safety one:
without common ground, signals misbehave. But there's a real safety edge: when you
*create* a common ground you also create a path for fault current. If a high-voltage
rail accidentally touches the common ground, that fault now has somewhere to go — which
can be good (a fuse blows) or bad (current flows somewhere you didn't intend, e.g. into
a USB-connected PC). So "tie everything to common ground" is correct, but *where* and
*how* you tie it matters.

**4. Relevance to your project.** Your ESP32 outputs STEP/DIR/EN as 3.3V-or-0V signals
measured against the ESP32's ground. Each TMC2209 decides "is STEP high or low?" by
comparing the incoming voltage to *its own* ground. If those two grounds aren't the
same node, the comparison is meaningless. The fact that your single-motor tests stepped
cleanly is *proof* that a common ground already exists in your wiring.

**5. Examples in your project.**
- **Overview / gotcha:** The classic beginner gotcha is "I powered the motor from the
  24V supply and the logic from USB, and nothing worked" — because the two halves never
  shared a ground. You avoided that gotcha; your grounds are joined. Your *next-level*
  gotcha is that the joining happens through a less-than-ideal path (see
  *internal ground bond* and *common-impedance coupling*).
- **Zoom-in:** Trace it in your description. ESP32 GND → the **neg mini-breadboard rail**
  → each driver's logic GND (C8-right) → tied inside each module to the motor GND (C2-right)
  → terminal block neg → 24V PSU neg. That whole chain is one electrical node: your common
  ground. It's real, but it currently reaches the PSU *through the drivers* rather than by
  a dedicated wire.

---

## 2. What VDD stands for / what VM stands for

**1. What it is.** These are pin-name conventions for supply voltages.
- **VM** = *Voltage, Motor* (sometimes printed **VMOT**). The high-power rail that
  actually drives the motor coils — your **24V**.
- **VDD** = the positive **logic/digital supply** voltage. The "DD" is an old CMOS
  naming convention (paired with **VSS** for the negative/ground rail). On your TMC2209
  it's the **3.3V** you feed in to tell the chip "my control signals swing between 0V and
  3.3V."

**2. Context, related concepts, failure & fix.** The important mental split is
**two supply domains**: a *high-power motor domain* (VM, amps, 24V) and a
*low-power logic domain* (VDD, milliamps, 3.3V). They cohabit one chip but do very
different jobs. A common gotcha is feeding VDD the wrong voltage: feed 5V where the
controller expects 3.3V logic and your signal "high" thresholds shift, or worse, you
push 5V back toward a 3.3V-only ESP32 pin. The fix is to source VDD from the *same logic
rail your controller uses* — which you do (3.3V from the ESP32).

> **Sub-concept to know — VSS.** The companion to VDD. **VSS** = *Voltage, Source-Source*,
> the negative/ground rail of the logic domain (0V). When you see "VDD and VSS," read it
> as "logic positive and logic ground." Your driver's logic GND pin is its VSS even if the
> silkscreen just says GND.
>
> **Sub-concept to know — VREF.** Not in your list but it's right next to VM/VDD in
> importance. **VREF** = *Voltage Reference*, a small analog voltage (you set ~1.7V) that
> tells the driver how much coil current to deliver. It's neither power nor logic — it's a
> dial. Misread it as a supply and you'll be confused; it's an instruction.

**3. Danger if mis-applied.** VM is genuinely dangerous in the sense that it's your
high-current rail — a short on VM dumps serious current (that's what your fuses guard).
VDD mistakes are usually *damage-to-the-chip* hazards (over-voltage on a logic pin) rather
than fire hazards. Mixing them up — e.g., accidentally bridging VM to VDD — would put 24V
onto a 3.3V net and destroy the ESP32 instantly, and possibly the PC behind it via USB.

**4. Relevance to your project.** Every TMC2209 in your build has both: VM (C1-right) at
24V and VDD (C7-right) at 3.3V, with separate grounds that are bonded inside the module.
Keeping the two domains clearly labeled in your own head prevents the single most
destructive wiring error possible here.

**5. Examples in your project.**
- **Overview / gotcha:** The dangerous gotcha is a stray strand of the 24V (VM) wire
  touching the 3.3V (VDD) rail. Because your grounds are common and your PC is on the USB,
  that fault could travel a long way. Physical tidiness on the VM terminals is a safety
  measure, not just aesthetics.
- **Zoom-in:** Your VDD feed is interesting — it runs **through a 33Ω resistor** before
  reaching the driver's VDD pin. That resistor is a deliberate current-limiter on the logic
  supply line: if something goes wrong on the VDD pin, the 33Ω limits how much current can
  flow (Ohm's law again: even a dead short to ground through 33Ω from 3.3V is only ~100mA),
  protecting the ESP32's regulator. It's a small, cheap insurance policy on the logic domain.

---

## 3. Marginal shared connection

**1. What it is.** A *marginal* connection is one that is electrically **borderline** —
good enough to work under light conditions, but not solidly good. "Marginal" = on the
margin, on the edge of failing. A *marginal shared connection* is such a borderline
joint that several circuits depend on at once (e.g. a ground point three drivers share).

**2. Context, related concepts, failure & fix.** The opposing idea is a *solid* (low-resistance,
mechanically sound) connection. Marginal connections come from loose screw terminals,
oxidized/corroded contacts, cold solder joints, a wire strand half-clamped, or
undersized wire. The treachery is **load-dependence**: at low current the small extra
resistance is invisible; at high current the same resistance produces real voltage drop
and heat, so the fault only shows up when you scale up. This is *exactly* the pattern that
makes a system "work with one motor, misbehave with three." Fixes: re-seat and torque
terminals, clean contacts, use proper gauge, and — for diagnosis — wiggle-test under load
while watching for flicker.

**3. Danger if mis-applied.** Yes, mildly. A marginal connection carrying high current
becomes a **hot spot** (power dissipated = I²R, concentrated at the bad joint). Loose
high-current terminals are a classic cause of melted connectors and, in bad cases, fire.
This is the same lesson from solar work: a loose lug on a battery terminal gets hot.

**4. Relevance to your project.** Your whole testing philosophy ("prove each layer")
is partly a hunt for marginal connections. They're invisible in isolation tests and only
surface under combined load — which is precisely the regime Phase 2 enters.

**5. Examples in your project.**
- **Overview / gotcha:** Suppose driver 3's GND screw on the terminal block is a quarter-turn
  loose. Motors 1 and 2 alone? Fine. All three energized? That marginal joint now carries
  more return current, drops more voltage, heats up, and driver 3 may reset, stutter, or
  read STEP unreliably. You'd wrongly suspect your *code* when the culprit is a screw.
- **Zoom-in:** Your highest-risk shared connections are the **neg mini-breadboard rail**
  (all three logic grounds plus ESP32 ground meet here) and the **terminal block neg** (all
  three motor returns plus the PSU). A marginal joint at either of those shared points
  affects everything downstream of it. Before Phase 2, physically re-seat those.
- **Diagnostic tie-in:** This is *why* the full pairwise test matrix (1&2, 1&3, 2&3) exists
  as a fallback — if all-three misbehaves, swapping which pair runs can reveal that one
  specific channel's shared connection is the marginal one.

---

## 4. Holding current vs stepping

**1. What it is.** Two operating states of a stepper motor.
- **Holding current:** the motor is *energized but not moving*. Current sits in the coils
  to clamp the rotor in place (this produces *holding torque*). It's a steady, DC-like draw.
- **Stepping:** the motor is *actively moving*. The driver rapidly switches current
  between coils in sequence to advance the rotor one step at a time. Current is dynamic and
  the moving rotor generates **back-EMF** that opposes the supply.

**2. Context, related concepts, failure & fix.** The useful insight is counter-intuitive:
**holding is close to the worst case for steady current draw**, because a *stationary* rotor
generates no back-EMF to push back against the supply, so the driver delivers the full set
current continuously. Moving motors actually draw *less* average current at speed (back-EMF
helps). This makes "energize, don't step" a beautifully clean test: maximum steady electrical
and thermal load, zero software-timing complexity.

> **Sub-concept to know — back-EMF.** EMF = electromotive force = voltage. A spinning motor
> is also a generator: its motion induces a voltage that *opposes* the supply voltage driving
> it. That's **back-EMF** ("back" = backwards-pushing). It's why a motor draws a big inrush
> when stalled/starting (no back-EMF yet) and less once spinning. You met a cousin of this in
> solar if you've seen inductive spikes; here it's the rotor acting as a generator.

**3. Danger if mis-applied.** Holding current means coils are powered while the motor sits
still — **the drivers and motors run warm continuously** even when nothing moves. Leaving a
system in holding indefinitely is a thermal consideration (and a wasted-power one). The
practical danger is forgetting to *disable* (EN off) at the end of a run and cooking the
drivers over hours.

**4. Relevance to your project.** Your Phase 2 plan should *start* with an
energize-and-hold test (all three EN active, no STEP pulses). It isolates "can my power and
ground system carry three motors' worth of steady current and heat" from "can my code drive
three step trains," so that if something fails you instantly know which world the fault is in.

**5. Examples in your project.**
- **Overview / gotcha:** A gotcha here is forgetting that *holding* is when you measure the
  hard numbers. Touch-test each TMC2209 after a minute of holding — they'll be warm at your
  1.2A RMS / VREF ≈ 1.7V setting; an *outlier* that's much hotter than its siblings flags a
  marginal connection or a current-set error on that channel.
- **Zoom-in:** In code, "hold" = set EN active and simply do nothing; "step" = toggle the
  STEP pin. A clean test routine enables all three, waits, lets you measure, then *disables on
  exit* so you don't leave coils energized. Your three EN pins are 13 (M1), 25 (M2), 18 (M3).

---

## 5. Ground bounce

**1. What it is.** *Ground bounce* is when the voltage of your "ground" momentarily **shifts**
because current is flowing through the ground conductor's impedance. Foundation 3 in motion:
`V = I × R` along the ground wire means the ground at one point lifts above ground at another
while current flows — and if that current is *changing fast*, inductance makes the bounce
sharper still.

**2. Context, related concepts, failure & fix.** It's the dynamic, transient cousin of
plain IR drop. Related: *common-impedance coupling* (the mechanism by which one circuit's
bounce becomes another circuit's noise) and *shared segment* (where it happens). It "bounces"
because currents in motors switch on and off, so the offset wobbles up and down rather than
sitting steady. The fix is to keep ground impedance low (thick, short) and — crucially — to
**not route a sensitive circuit's reference through a segment carrying big switching currents**
(that's what star-grounding achieves).

**3. Danger if mis-applied.** Not a fire hazard; a *reliability* hazard. Enough ground bounce
and a logic input sitting near its threshold can be misread (a HIGH looks LOW for an instant),
or a microcontroller's brownout detector can trip. Intermittent, hard-to-reproduce glitches
are the signature.

**4. Relevance to your project.** With one motor, the bounce on your shared ground is tiny
(tens of millivolts) and your 3.3V logic has hundreds of millivolts of margin, so it's
invisible. With three motors switching simultaneously, the bounce roughly triples and the
switching edges line up — still likely fine at your slow step rates, but it's the precise
phenomenon that *could* make Phase 2 flaky if a shared ground segment is involved.

**5. Examples in your project.**
- **Overview / gotcha:** The gotcha is blaming software for a hardware bounce. If all-three
  stepping is glitchy but holding (no switching) is clean, suspect ground bounce on a shared
  segment, not your MicroPython.
- **Zoom-in:** Your at-risk segment is any wire that carries *both* motor return current *and*
  serves as the logic reference. Right now the only place motor return and logic reference
  share copper is *inside the drivers* (the internal bond) and, depending on routing, possibly
  a bit of the neg rail. Adding a dedicated logic-ground wire straight to the PSU neg (star
  point) gives the logic reference its own quiet path and removes it from the bounce.

> **Sub-concept to know — brownout / brownout reset.** A *brownout* is a momentary voltage sag
> below what a chip needs to run reliably (vs. a "blackout," full loss of power). The ESP32 has
> a built-in **brownout detector** that *deliberately resets* the chip if its supply dips too
> low, to avoid undefined behavior. A mid-test ESP32 reboot during Phase 2 is a brownout
> reset until proven otherwise — and it counts as a failed test even if the motors looked fine.

---

## 6. Common-impedance coupling

**1. What it is.** A specific, named noise mechanism: when **two circuits share a conductor**
that has some impedance, the current from circuit A flowing through that shared impedance
creates a voltage (Ohm's law) that circuit B *also sees*, because B is connected to the same
conductor. A's current has "coupled" into B through the **common impedance**. It is the precise
mechanism behind ground bounce affecting your logic.

**2. Context, related concepts, failure & fix.** This is the villain of the whole grounding
story. Related terms: *shared segment* (the physical conductor), *shared impedance* (its
`R`/`Z`), *return currents* (what's flowing through it). The opposing/solution concept is
**star-grounding**, which gives each circuit its own return path so they stop sharing a segment.
The software analogy is sharp: it's **shared mutable state**. Two threads (circuits) touching
one shared variable (the common conductor); one thread's writes (current) corrupt the other's
reads (reference). The fix in both worlds is the same in spirit: *don't share the resource* —
give each its own path (star ground) the way you'd give each thread its own copy or a proper
isolation boundary.

**3. Danger if mis-applied.** Reliability hazard, like ground bounce. The "mis-application" is
usually accidental: daisy-chaining grounds so high- and low-current circuits share a return.
Not a fire risk, but a debugging nightmare risk.

**4. Relevance to your project.** This is the single concept that motivated my advice to add a
dedicated logic-ground wire. Your three motors' return currents and your ESP32's voltage
reference *can* share impedance through the drivers' internal bond. At v0 scale the coupling is
small, but it's the textbook setup for the problem, and eliminating it is cheap.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — you can have a perfectly *correct* common ground that still
  suffers common-impedance coupling because the shared part of it carries motor current. "It's
  all connected" isn't the same as "it's cleanly connected."
- **Zoom-in:** The coupling point is the drivers' internal **GND bond** plus any shared neg-rail
  copper between "where motor return enters" and "where logic reference taps off." The remedy is
  a star ground: run logic-neg → PSU-neg as its own 22 AWG wire so the ESP32's reference no
  longer rides through copper that motor current flows in.

---

## 7. Return currents

**1. What it is.** The current flowing **back** to the supply's negative terminal to complete
the loop (Foundation 2). For every amp a motor coil pulls from 24V+, an amp returns through the
GND wiring to 24V−. The return path is not an afterthought — it carries the full current and is
where most ground problems live.

**2. Context, related concepts, failure & fix.** Beginners picture current as "delivered to"
a load and forget the return. The related concepts are the entire grounding family: return
currents are *what flows through* shared segments and shared impedances to cause bounce and
coupling. The fix-oriented idea is **controlling where return current flows** — you *want* heavy
motor return current to flow back on its own dedicated path (motor GND → terminal block → PSU),
not up through your logic ground.

**3. Danger if mis-applied.** Indirect. Ignoring return paths leads to undersized ground wiring
(it must handle the same current as the supply side — a solar lesson: your negative run is as
important as your positive run) and to accidental shared returns. Undersized ground wire = heat.

**4. Relevance to your project.** Three motors at up to ~1.2A RMS each means up to several amps
of return current converging on your terminal block neg and PSU neg. Designing those return
paths to be fat and dedicated, and keeping logic reference *off* them, is the core of a clean
Phase 2.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — sizing the positive wires correctly (you used 18 AWG with 2A
  per-leg fuses) but treating ground as "just ground." Ground carries the same amps; it deserves
  the same gauge. You've done this on the motor side; the thing to *add* is a dedicated (thin is
  fine) logic-reference return so logic current doesn't borrow the motor's return.
- **Zoom-in:** Motor return route (good, keep it): coil → driver → C2-right GND → terminal block
  neg → PSU neg, on 18 AWG. Logic return route (improve it): ESP32/driver-logic GND → neg rail →
  **dedicated wire** → PSU neg. Two separate returns meeting only at the star point.

---

## 8. Common reference

**1. What it is.** The general principle behind common ground: any two parts of a system that
exchange or compare voltages must share the **same baseline (reference) point** to agree on what
the numbers mean. "Common ground" is the specific case where that shared baseline is the 0V/ground
node. "Common reference" is the umbrella idea (Foundation 1, restated).

**2. Context, related concepts, failure & fix.** Opposing situation: two **floating** subsystems
with independent references — their voltages are mutually meaningless. Related: *logic reference*
(the reference digital chips use), *common ground* (the usual physical implementation). The fix
is to bond references together at a defined point. The software analogy: agreeing on a shared
coordinate origin or epoch before exchanging values; without it, every number is ambiguous.

**3. Danger if mis-applied.** Mostly correctness. But "bonding references" can create unintended
current paths (see *common ground*, danger note, and *ground loops* below), so *where* you bond
matters.

> **Sub-concept to know — floating.** A circuit is **floating** when its reference isn't tied to
> anything definite, so its voltage relative to other things is undefined and can drift. Your 24V
> PSU's negative output is likely floating relative to building earth (typical for an isolated
> supply) until something bonds it. Floating isn't inherently bad — sometimes it's desirable — but
> you need to know what's floating and what's referenced.

**4. Relevance to your project.** You now have *two* reference-defining forces: the drivers bond
logic-and-motor ground into one node, and the USB cable ties ESP32 ground to your PC's earth.
Understanding "what is my reference, and is it shared with everything that talks to it" is what
keeps signals valid as you add the second ESP32 and sensors later.

**5. Examples in your project.**
- **Overview / gotcha:** Future gotcha — when you add ESP32 #2 for sensors, it must share the
  *same* common reference as ESP32 #1 and the drivers, or cross-board signals (and any analog
  sensor readings) will be referenced to the wrong zero.
- **Zoom-in:** Today your common reference is the single ground node spanning ESP32, all driver
  logic and motor grounds, terminal block, and PSU neg, with the PC's earth tied in via USB.
  That's one coherent reference — good. Keep it one node as the system grows.

---

## 9. Shared segment

**1. What it is.** A specific **piece of conductor** (a wire, a trace, a length of rail) that lies
on the current path of **more than one circuit**. It's the physical place where common-impedance
coupling happens. "Segment" = a portion of a conductor between two connection points.

**2. Context, related concepts, failure & fix.** Directly tied to *common-impedance coupling*
(the effect) and *shared impedance* (the property of the segment). Opposing design: **separate
segments / dedicated paths**, achieved by star-grounding. A shared segment becomes a problem only
when (a) it carries significant current and (b) a sensitive reference taps off it. The fix is to
shorten it to near-zero (move the shared point right to the source) or eliminate the sharing.

**3. Danger if mis-applied.** Reliability, not safety — same family as bounce and coupling.

**4. Relevance to your project.** Your job before Phase 2 is to make sure no meaningful length of
conductor is shared between "heavy motor return" and "logic reference." The shorter that shared
segment, the smaller every coupling problem becomes.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — daisy-chaining grounds (driver → driver → driver → PSU) makes
  the wire between the *first* driver and the PSU a shared segment carrying *all three* motors'
  return current, with the others' references hanging off the far end. That long shared segment is
  the worst case.
- **Zoom-in:** In your build the (small) shared segment is the internal bond inside each driver
  plus whatever neg-rail copper sits between the motor-return entry and the logic tap. You can't
  remove the internal bond (it's inside the chip), but you *can* make the *logic* reference reach
  the PSU by a separate wire so the shared segment is as short as physically possible.

---

## 10. Logic reference

**1. What it is.** The specific ground (0V node) that your **digital logic** uses as its baseline
to define HIGH and LOW. For your ESP32, the logic reference is its GND pin: a "3.3V HIGH" on a
GPIO means 3.3V *above the ESP32's GND*. Every TMC2209 likewise judges STEP/DIR/EN against *its*
logic ground.

**2. Context, related concepts, failure & fix.** A specialization of *common reference* for the
digital domain. The opposing hazard: if the logic reference moves (ground bounce) or differs
between sender and receiver (no common ground), logic levels get misread. The fix is a **clean,
shared, low-impedance logic ground** — which is exactly why we separate it from motor-return
current.

> **Sub-concept to know — logic threshold / noise margin.** Digital inputs don't switch exactly at
> half the supply; they have a threshold band, and the gap between "guaranteed-read-as-LOW" and
> "guaranteed-read-as-HIGH" voltages is your **noise margin**. 3.3V logic gives you a few hundred
> millivolts of margin. Ground bounce eats into that margin; keeping it small keeps you safe.

**3. Danger if mis-applied.** Reliability. A wandering logic reference causes the exact
intermittent, "works-sometimes" bugs that are miserable to chase.

**4. Relevance to your project.** STEP/DIR/EN are the lifeblood of motor control, and they're all
referenced to logic ground. Protecting the integrity of that reference under three-motor load is
why the dedicated logic-ground wire is worth the two minutes.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — assuming "ground is ground." The *motor* ground and the *logic*
  ground are the same node electrically, but you want the *logic reference* to experience as
  little of the motors' current-induced bounce as possible.
- **Zoom-in:** Logic reference touches: ESP32 GND, each driver's C8-right logic GND, the neg rail,
  and the VDD-return for the 3.3V supply. Keep all of those on the quiet (logic) side of the star
  point.

---

## 11. Star-grounding

**1. What it is.** A grounding **topology** where every ground connection runs back to **one single
central point** (the "star center"), like spokes from a hub, instead of being chained one to the
next. Because each circuit gets its own spoke, one circuit's return current can't flow through
another circuit's ground path — it kills common-impedance coupling by construction.

**2. Context, related concepts, failure & fix.** Its opposite is **daisy-chain (series) grounding**,
where grounds hop device-to-device and downstream devices' returns pile onto the upstream wire,
creating long shared segments. Star is the fix; daisy-chain is the trap. A related higher-end
option is a **ground plane** (a solid copper sheet acting as a near-zero-impedance shared ground,
common on PCBs). The single rule of thumb: *high-current and low-current grounds should meet at one
point, and that point should be right at the supply.*

> **Sub-concept to know — daisy-chain grounding.** Grounds connected in a line: A→B→C→supply.
> Device C's return current flows through the B→supply and A→supply wire too, so the wire nearest
> the supply carries *everybody's* current, and devices farther out sit on top of that voltage. The
> software analogy is a linked list vs. a hub: in a daisy chain, the head node bears the whole
> list's traffic. Star grounding is the hub-and-spoke refactor.
>
> **Sub-concept to know — ground plane.** A large continuous area of copper used as ground. Its huge
> cross-section makes impedance tiny, so it behaves almost like an ideal single node. You'll meet it
> when you move from breadboards to a real PCB at v2.

**3. Danger if mis-applied.** Star grounding itself is safe; the *failure to use it* is what causes
trouble. One nuance: a "star" with a long, thin spoke is still better than a daisy chain but not
ideal — spokes should be short and adequately sized for their current.

**4. Relevance to your project.** Your **terminal block neg / PSU neg** is the natural star center.
Motor returns already converge there. The improvement is to bring the *logic* ground there too, as
its own spoke, rather than letting it reach the PSU through the drivers.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — building an *accidental daisy chain* by grounding driver 2 to
  driver 1, driver 3 to driver 2, and only driver 1 to the PSU. Wire each driver's ground back to
  the common point instead.
- **Zoom-in:** Target topology: PSU neg = star center. Spoke 1/2/3 = each driver's motor GND (18
  AWG). Spoke 4 = the logic neg rail (ESP32 + driver logic grounds), 22 AWG, dedicated. Everyone
  meets only at the center.

---

## 12. Staggered enable

**1. What it is.** Turning on multiple loads at **slightly different moments** rather than all at
once, to avoid a single large simultaneous surge of current. In firmware, you assert the three EN
pins a few milliseconds apart instead of in the same instant.

**2. Context, related concepts, failure & fix.** Tied to *startup dip* and **inrush current**. The
opposing approach is simultaneous enable, which stacks three inrush events into one big spike that
can sag the supply. The software analogy is the **thundering herd** problem — and the fix is the
same shape as **jitter/staggered backoff**: spread the starts out in time so the shared resource
(here, the PSU) isn't hammered all at once.

> **Sub-concept to know — inrush current.** The brief, larger-than-normal current a load pulls at
> the *instant* it's switched on, before it settles to steady state — caused by charging input
> capacitors and energizing coils that have no back-EMF yet. Three drivers enabling together means
> three inrush events superimposed.

**3. Danger if mis-applied.** Low risk. Over-staggering (huge delays) just makes startup feel
sluggish; it doesn't harm anything. Not staggering at all merely risks a startup dip/brownout, not
damage.

**4. Relevance to your project.** A cheap, optional reliability tweak. If your energize-all-three
hold test shows an ESP32 brownout reset at the moment of enable, staggering the three EN assertions
by a few milliseconds is the first, easiest fix to try.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — diagnosing a *startup-only* brownout as a code crash. If it only
  resets *at enable* and runs fine after, it's an inrush/startup-dip issue, and staggering is the
  remedy.
- **Zoom-in:** In MicroPython: enable pin 13, short `sleep_ms(5)`, enable pin 25, `sleep_ms(5)`,
  enable pin 18. Three small delays, problem dissolved — and good practice regardless.

---

## 13. Startup dip

**1. What it is.** A momentary **sag in supply voltage** at the instant loads switch on, caused by
inrush current pulling the supply down faster than it can respond, followed by a quick recovery. The
voltage "dips" then climbs back.

**2. Context, related concepts, failure & fix.** Caused by *inrush current* (above) meeting the
supply's limited ability to instantly deliver it. Worsened by simultaneous enable; mitigated by
*staggered enable*, by adequate supply headroom, and by **bulk capacitance** near the load (a
reservoir cap supplies the instantaneous surge so the rail doesn't sag). The opposing healthy state
is a "stiff" supply that holds voltage under transient load.

> **Sub-concept to know — bulk/decoupling capacitance.** A capacitor placed across the power rail
> acts as a small local energy reservoir: it dumps charge during a fast surge (smoothing the dip)
> and refills between surges. Many driver modules include one; adding a modest bulk cap across VM at
> the terminal block is a common stiffening trick if you ever see dips. (You already know caps from
> solar/charge-controller territory.)

**3. Danger if mis-applied.** The dip itself isn't dangerous, but a deep enough dip can **brownout-
reset** your ESP32 mid-operation — a reliability failure. No fire risk.

**4. Relevance to your project.** Your 24V supply with a 7A main fuse should have ample headroom for
three motors at ~1.2A each, so a damaging dip is unlikely — but the *logic* 3.3V rail (feeding three
VDDs plus the ESP32) is the more delicate one to watch, since a dip there is what reaches the
brownout detector.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — watching only the 24V rail and ignoring the 3.3V rail. The 3.3V
  logic rail is the usual suspect for "works with one, resets with three."
- **Zoom-in:** During the hold test, meter the 3.3V rail (and the 24V VM at a driver) while you
  enable. You're looking for a transient dip at the enable instant. If you see one on 3.3V, try
  staggered enable first, then consider a bulk cap.

---

## 14. Grounding topology

**1. What it is.** The overall **shape/arrangement** of how all your grounds are wired together —
the "map" of the ground network. "Topology" borrows the math word for *structure of connections*:
star, daisy-chain, ground plane, or hybrids of these.

**2. Context, related concepts, failure & fix.** This is the umbrella term over *star-grounding*
and *daisy-chain*. Choosing a topology is choosing how return currents are allowed to flow and
therefore how much common-impedance coupling you'll have. The failure is an *unplanned* topology
(grounds tied "wherever was convenient"), which usually degrades into accidental daisy chains. The
fix is to *decide* your topology on purpose — typically star at this scale.

**3. Danger if mis-applied.** A poor topology is a reliability hazard. One safety-adjacent failure
mode is the **ground loop** (next sub-concept), which can inject noise and, in mains-connected
systems, occasionally cause shock/equipment hazards — relevant because your PC ties earth into your
system.

> **Sub-concept to know — ground loop.** When ground is connected between two points by **more than
> one path**, forming a loop, stray currents (or differing earth potentials) can circulate around it
> and inject noise. Right now you have a *clean* situation: the PC provides the only earth tie and
> the PSU negative floats, so there's no loop. If you ever *also* bonded the PSU negative to earth,
> you'd create a loop (earth → PC → USB → ESP32 → ground network → PSU → earth). Keep PSU negative
> floating unless you have a specific reason not to.

**4. Relevance to your project.** You're at the perfect moment to *choose* a deliberate topology
(star) before Phase 2 bakes in habits. Doing it now, at breadboard scale, makes the v2 PCB design
straightforward later.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — letting the topology "just happen." Sketch it once: star center at
  PSU neg, dedicated spokes, logic ground as its own spoke, PC as the single earth tie, PSU neg
  floating. That one sketch prevents a dozen future mysteries.
- **Zoom-in:** Your current topology is "mostly star, with the logic reference reaching the center
  through the drivers." The single edit (dedicated logic-ground spoke) converts it to a clean star.

---

## 15. Internal ground bond

**1. What it is.** A connection **inside a component** that ties two (or more) of its ground pins
together, so pins that look separate on the outside are actually one electrical node internally. On
your TMC2209 modules, the *logic* ground (C8-right) and the *motor* ground (C2-right) are bonded
together inside the module (on the chip and/or the board's ground copper).

**2. Context, related concepts, failure & fix.** This is *why* your common ground exists even
without a dedicated wire — the bond bridges logic and motor grounds through the chip. It's also the
unavoidable little **shared segment** between motor return and logic reference, the seed of
common-impedance coupling. You can't remove an internal bond (it's inside the part), so the "fix" is
to make every *external* ground path so clean that the internal bond carries as little reference-
disturbing current as possible.

**3. Danger if mis-applied.** Not dangerous in itself; it's a design feature of the part. The trap
is *not knowing it's there* and assuming "logic ground and motor ground are isolated in this chip"
when they aren't — which could lead you to mis-reason about isolation or fault paths.

**4. Relevance to your project.** The internal bond is the reason a 24V-to-logic-ground fault inside
a driver would propagate to your logic side (and via USB toward the PC). It's also the reason your
single-motor test worked without a dedicated logic-ground wire. Knowing it exists explains both the
convenience and the caution.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — believing the two GND pins on the driver are electrically separate.
  They're one node. Wiring them as if they were isolated grounds wouldn't isolate anything.
- **Zoom-in:** Because C8-right and C2-right are bonded, your logic reference can reach the PSU
  *through the driver*. That's the path we're augmenting with a dedicated wire so the bond isn't the
  *only* route and doesn't have to carry reference duty under three-motor load.

---

## 16. Shared impedance

**1. What it is.** The **impedance of a conductor that two or more circuits share** — the actual
ohms (and a bit of inductance) of that shared segment. It's the multiplier in the coupling equation:
the voltage one circuit injects into another equals the *other* circuit's current times this shared
impedance (`V_noise = I_other × Z_shared`).

**2. Context, related concepts, failure & fix.** It's the quantitative heart of *common-impedance
coupling*. Bigger shared impedance → bigger injected noise. Two levers to shrink the problem: reduce
the *shared* part (don't share — star ground) or reduce the *impedance* (thicker, shorter conductor,
or a ground plane). Both appear throughout this document.

**3. Danger if mis-applied.** Reliability. The "mis-application" is unknowingly building large shared
impedance (long thin shared ground), which amplifies every coupling problem.

**4. Relevance to your project.** At v0, your shared impedance (the driver internal bond plus a little
rail copper) is small, so the injected noise is small — which is why you'll probably be fine. But the
principle is what guides every grounding decision as you scale to 6ft × 6ft with longer wire runs in
v2, where shared impedance grows with length.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — long ground runs in the bigger v2 frame. Length raises shared
  impedance, so a topology that's fine at 1.5ft can couple noticeably at 6ft if you let grounds share
  segments. Design the star now; it pays off at scale.
- **Zoom-in:** `V_noise ≈ I_motors × Z_shared`. Keep `Z_shared` near zero by giving logic its own
  short spoke and you make `V_noise` near zero regardless of how big `I_motors` gets.

---

## 17. High vs low impedance

**1. What it is.** **Impedance (Z)** is the general opposition to current flow. For DC it's basically
**resistance (R)**; for changing/AC signals it also includes **reactance** from capacitance and
inductance — hence the broader word "impedance" instead of "resistance."
- **Low impedance:** current flows easily; small voltage drop; "stiff," solid connection.
- **High impedance:** strongly opposes current; large voltage drop or nearly blocks flow; "weak"
  source or a deliberately non-loading input.

**2. Context, related concepts, failure & fix.** The key is that **what you want depends on the job**:
- *Power and ground* connections want **low** impedance (deliver current with minimal drop). A
  high-impedance ground is a bug.
- *Sensor/signal inputs* often want **high** input impedance (so they "sample" a voltage without
  drawing enough current to disturb it).
- A *floating* node behaves like it's connected through very high impedance to everything — which is
  why floating inputs drift and need pull-up/pull-down resistors to define them.

> **Sub-concept to know — reactance / why "impedance" not "resistance."** Resistance opposes current
> the same regardless of how fast it changes. Capacitors and inductors oppose *changing* current
> differently depending on frequency — that frequency-dependent opposition is **reactance**.
> "Impedance" = resistance + reactance combined. For your slow-changing motor/logic signals, thinking
> "resistance" is close enough 95% of the time; the word "impedance" just keeps the door open for the
> fast switching edges where inductance starts to matter (and where ground bounce gets sharper).
>
> **Sub-concept to know — pull-up / pull-down resistor.** A resistor that gently ties a logic line to
> a known level (HIGH via pull-up, LOW via pull-down) so a pin that would otherwise *float* at high
> impedance reads a definite value. This is why GPIO12's *built-in* pull-down at boot matters — you
> deliberately avoided it for control signals.

**3. Danger if mis-applied.** A high-impedance *ground or power* connection (e.g. a marginal joint)
causes voltage drop, heat, and instability — the same hazard family as marginal connections. A
*floating* high-impedance input causes erratic logic. Neither is a fire risk on its own, but the
heat from an unintended high-impedance high-current joint can be.

**4. Relevance to your project.** Two direct touch-points: (a) you want all your power and ground
paths **low-impedance** (solid terminals, adequate gauge) — that's the goal of clean grounding; and
(b) when you add level/hall sensors on ESP32 #2, you'll be reading **high-impedance** signal inputs
that must be properly referenced and sometimes pulled to a defined level.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — a corroded or loose ground terminal is a sneaky *high-impedance*
  spot in a place that's supposed to be *low*-impedance; it manufactures voltage drop and bounce
  exactly where you don't want it.
- **Zoom-in:** Your design targets low impedance with screw/lever terminals and proper gauge — good.
  Your hall sensors (A3144) and level sensors later are the high-impedance-input side of the coin;
  they'll need clean references and possibly pull resistors, which is the same grounding discipline
  applied to inputs.

---

## 18. "Logic neg rail," and "rail" in that sense generally

**1. What it is.** A **rail** is a conductor that **distributes one voltage to many places** — named
after physical bus bars/rails that power runs along. "The 24V rail," "the 3.3V rail," "the ground
rail." The **logic neg rail** is specifically the *negative/ground distribution conductor for the
logic side* — in your build, the **neg mini-breadboard-style terminal block** where the ESP32 ground
and all three drivers' logic grounds (and the VDD return) come together.

**2. Context, related concepts, failure & fix.** "Rail" is a convenience word for "shared
distribution node for a given voltage." Each rail is, in effect, one node — which is exactly why a
rail can become a *shared segment* if heavy and light currents both use it. Related: the *positive*
counterpart is the "logic pos rail" (your 3.3V rail) and the "motor rail" (24V). The common gotcha is
treating a rail as a perfect single point when, under current, different spots along it sit at
slightly different voltages (IR drop along the rail).

**3. Danger if mis-applied.** A rail asked to carry more current than its conductor/contacts can
handle becomes a hot, marginal, voltage-dropping mess — the marginal-connection hazard, spread along
a strip. Mini-breadboard rails in particular have modest current ratings; fine for logic, not for
motor current.

**4. Relevance to your project.** You have (at least) three rails to keep straight: the **24V motor
rail**, the **3.3V logic-pos rail**, and the **logic-neg (ground) rail**. The logic-neg rail is the
one we want to give a dedicated, low-impedance spoke to the PSU-neg star center.

**5. Examples in your project.**
- **Overview / gotcha:** Gotcha — accidentally routing motor-level current through a *mini-breadboard*
  rail rated for small currents. Keep the 24V/motor returns on the proper terminal block and 18 AWG;
  keep the mini-breadboard rails for logic-level current only.
- **Zoom-in:** Your **neg mini-breadboard rail** is the logic-neg rail. It ties ESP32 GND, the three
  drivers' C8-right logic grounds, and the 3.3V return together. The single improvement we keep
  returning to: run one dedicated 22 AWG wire from this rail to the PSU-neg star point so the logic-
  neg rail has a clean, low-impedance home that isn't routed through the drivers.

---

## Concept map — how these all connect

Read top-to-bottom; each layer is built from the one above.

```
FOUNDATIONS
  Voltage is a difference  ─┐
  Current flows in loops   ─┼──► everything below is a consequence
  V = I × R (IR drop)      ─┘

THE REFERENCE FAMILY (what "zero" means, and keeping it stable)
  common reference ──► common ground ──► logic reference
        │                                     ▲
        └── if not shared ──► floating ───────┘ (undefined zero = garbage signals)

THE CURRENT-PATH FAMILY (where return current flows)
  return currents ──► shared segment ──► shared impedance
        │                   │                  │
        │                   └──────────────────┴──► COMMON-IMPEDANCE COUPLING
        │                                                     │
        │                                            ground bounce (its dynamic form)
        ▼                                                     │
  grounding topology:  daisy-chain (bad)  vs  STAR (good) ◄───┘ (the fix)
        ▲
  internal ground bond (the unavoidable little shared segment inside each driver)

THE STARTUP FAMILY (transients at power-/enable-on)
  inrush current ──► startup dip ──► (brownout reset)
        └── fix ──► staggered enable / bulk capacitance

SUPPORTING VOCABULARY
  VM (motor supply) | VDD (logic supply) | VSS (logic ground) | VREF (current set dial)
  impedance: low (want for power/ground) vs high (want for signal inputs)
  rail: a shared distribution conductor for one voltage (e.g., your logic-neg rail)
  marginal connection: a borderline joint that fails only under load
  holding current vs stepping: steady worst-case load vs dynamic moving load
```

**The one-sentence summary of the whole document:** *keep every subsystem agreeing on the same clean
"zero" (the reference family) by making sure heavy motor return current and your delicate logic
reference never have to share the same piece of wire (the current-path family), and smooth out the
moment everything switches on (the startup family).*

---

## Appendix — Your original question

> So, let's pause, and let's talk through concepts. You're a professor, writing me my own
> project-related textbook.
>
> Please explain each concept below. Be as explanatory as an introductory textbook would be — aimed
> at a high-school or intro-college class for non-STEM folks — keeping in mind I'm a software
> engineer who has previously wired up a 12V solar panel system.
>
> **Explanation sub-items requested (for each concept):**
> 1. What it is in general; what to know about it.
> 2. Context around the concept, or its related/opposing concept if relevant; how it can be
>    problematic, and solutions.
> 3. Whether it can be dangerous if mis-applied.
> 4. Its relevance to my project.
> 5. Examples in my project (or hypotheticals if needed), with an overview (such as consequences of
>    common gotchas and problems/solutions), a zoom into the relevant parts of my project related to
>    the concept, and an explanation of any sub-list-items that come up within the explanation —
>    i.e., when new technical concepts appear, add and explain those too as their own items.
>
> **Concepts to explain:**
> common ground · what VDD stands for / what VM stands for · marginal shared connection · holding
> current vs stepping · ground bounce · common-impedance coupling · return currents · common
> reference · shared segment · logic reference · star-grounding · staggered enable · startup dip ·
> grounding topology · internal ground bond · shared impedance · high vs low impedance · "logic neg
> rail" and "rail" in that sense generally.
