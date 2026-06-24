
Electrical & IT System description:

A. 24v power supply -- pos (w/ 7 amp fuse) & neg to terminal block.
B. Terminal block -- 3 of 18 awg pos (w/ 2 amp fuse) & neg wires to the TMC2209 chip.
C. TMC2209 chip -- 3 of them, each receiving the 24v pos (VM) & neg (GND). 

  Product name: "Teyleten Robot TMC2209 V2.0 Stepper Motor Driver StepStick 2.5A UART Ultra Silent for Nano SKR V1.3/1.4 Ender 3 Control Board 3D Printer Parts Replace A4988"

  TMC2209 chip's right side, from top to bottom:
  C1-right. VM - to 24v  pos
  C2-right. GND - to 24v neg
  C3-right. A2 - to blue  wire of Nema 17 motor
  C4-right. A1 - to red   wire of Nema 17 motor
  C5-right. B2 - to green wire of  Nema 17 motor
  C6-right. B1 - to black wire of Nema 17 motor
  C7-right. VDD - To 3.3v pos mini-breadboard-style-terminal-block (wire runs through a 33 ohm resistor --  California JOS 100pcs 33 ohm Resistor 1/2w (0.5Watt) ±1% Tolerance Metal Film Fixed Resistor, Multiple Values of Resistance Optional(33 ohm, 33 R, 33 Ω))
  C8. GND - To neg mini-breadboard-style-terminal-block

  TMC2209 chip's left side, from top to bottom:
  C1-left. EN - to green wire to ESP32 Pin 13
  C2-left to C6 left. unused (MS1, MS2, PDN, PDN, CLK)
  C7-left. STEP - to yellow wire to ESP32 Pin 27
  C8-left. DIR - to white wire to ESP32 Pin 14

D. ESP32 chip - 1 of them so far 
  Note: In the next phase we'll add a second ESP32 for positioning sensors (level sensors, hall sensors + magnets as stoppers) 
  
  Product name: ELEGOO 3PCS ESP-32 Development Board USB-C, 2.4GHz Dual Mode WiFi+Bluetooth 4.2 Dual Core Microcontroller Support AP/STA/AP+STA, CP2102 Chip

  To Motor Driver Z1 - Pin 25 - EN
  To Motor Driver Z1 - Pin 26 - STEP
  To Motor Driver Z1 - Pin 33 - DIR
  
  To Motor Driver Z2 Pin 13 - EN
  To Motor Driver Z2 Pin 27 - STEP
  To Motor Driver Z2 Pin 14 - DIR
  
  To Motor Driver X  Pin 18 - EN
  To Motor Driver X  Pin 19 - STEP
  To Motor Driver X  Pin 23 - DIR

  USB-C - Thinkcentre pc running Linux desktop

E. mini-breadboard terminal block
  I use a 5x5 mini-breadboard as a mini block to make the following connections:

  pos rail: 
  1. ESP32 3.3v
  2. pos wire to TMC2209 number 1's VDD pin (note: a 33 ohm resistor bridges the pos wire)
  3. pos wire to TMC2209 number 2's VDD pin (note: a 33 ohm resistor bridges the pos wire)
  4. pos wire to TMC2209 number 3's VDD pin (note: a 33 ohm resistor bridges the pos wire)
  
  neg rail:  
  1. ESP32 GND
  2. neg wire to TMC2209 number 1's GND pin (the one next to VDD); 
  3. neg wire to TMC2209 number 2's GND pin (the one next to VDD); 
  4. neg wire to TMC2209 number 3's GND pin (the one next to VDD); 
  5. neg wire to neg rail of terminal block of the PSU

F. We also, as mentioned, use 3 of Nema 17 stepper motors.
G. Thinkcentre pc running Linux desktop
    Product: Lenovo ThinkCentre Micro Desktop, 16GB DDR4 RAM, 256GB SSD Drive, AMD Processor


---
Testing discussion:

Lets discuss the best approach to test them.
I want you to be my electrical engineering professor.

concluded tests:

one motor at a time: done
each chip: done (and vref set to 1.7)
each motor wire: done
context for testing discussion, upcoming tests:
now I propose, since currently the whole system is wired up... i have 3 motors, 3 drivers, 1 esp32...

I propose I test each motor separately. Then perhaps I test 2 at a time. (is it worth running a combo of: 1,2; 1,3; 2,3; ?) Then perhaps I test all 3.




#######################################################################
#######################################################################
        CLAUDE ANSWER:    CLAUDE ANSWER:    CLAUDE ANSWER:
#######################################################################
Good — let me put on the professor hat, because the most important thing here is to be clear about what these next tests are actually *for*. You've already proven every motor, every driver, and every wire works in isolation. So none of the upcoming tests are really asking "does motor 2 spin?" You know it does. Every new test from here is probing the **shared resources** — the things that only exist when motors run together and that your isolated tests couldn't have exercised:

- the 24V rail and the 7A main fuse under combined draw
- the terminal block and shared power distribution (voltage drop, heating at a junction)
- the **common ground** path back to the PSU *and* to the ESP32 logic reference
- the 3.3V logic rail feeding three VDDs plus whatever else is on it
- the ESP32 generating three independent STEP trains at once (orchestration)

Keep that framing and the right test sequence falls out almost mechanically.

**On your pairwise question — no, don't run 1,2 / 1,3 / 2,3 as a forward sweep.** The full pairwise matrix is a *differential diagnosis* tool, not a progression. Here's the logic: if the failure mode is total current / rail sag, it's a function of *how many* motors (N), not *which* pair — so 2,3 tells you nothing that 1,2 didn't. The only time a specific pair matters is if one driver has a marginal shared connection (say motor 3's ground is loose) that only shows under combined load — and the all-three test catches that too. So run the full matrix *only* as a fallback: if all-three misbehaves, *then* you drop to pairs to isolate which channel is the offender. Running them all up front is over-testing.

For the single intermediate step, pick the **two vertical motors (Z1 + Z2)**. Not an arbitrary pair — that's your real operational pairing (synchronized lift), they may share the gantry load mechanically, and they're the ones that'll run matched profiles in production. Highest-value pair by far.

Now, the sequence — with one refinement that I think is the real insight:

1. **Each motor alone, re-confirmed in the fully-wired state.** You tested them isolated; now they're sharing a ground and a rail. Quick sanity pass.
2. **Energize all three — holding current, NOT stepping.** This is the step most people skip and it's the cleanest test you can run. Set all three EN active so the coils hold full current, and just let them sit. No software timing, no STEP trains — pure electrical/thermal/ground load. Holding is actually close to worst-case steady current (no back-EMF helping you), so if the power system or grounds are going to sag or heat, they'll show it here, with zero orchestration complexity to muddy the diagnosis.
3. **Z1 + Z2 stepping together.** Now add motion to your real pair.
4. **All three stepping.** Full system.

That step-2 trick decouples *"can the power/ground system hold three energized motors"* from *"can my code drive three channels."* When something goes wrong you immediately know which world you're in.

What to actually **measure** at each step — this is the EE substance, because "it ran" isn't a passing grade:

- **VM at the driver terminal block under load.** DMM minimum, scope if you have one. You're looking for droop, and especially a transient *dip* at the instant all three enable. Your 24V should stay 24V.
- **The 3.3V logic rail.** This is the #1 suspect for "works with one, resets with three." If three VDDs plus the ESP32 pull that rail down even briefly, the ESP32 brownouts and resets. Watch it.
- **ESP32 serial console stays alive** — no brownout reset, no watchdog reboot mid-test. A reset *is* the failure, even if the motors looked fine.
- **Driver temperature.** Three drivers at ~1.2A RMS each. Touch-test or IR after a minute of holding current. The TMC2209s will be warm; you're checking that none is an outlier (which would flag a marginal connection or a hot driver).
- **Total 24V current** if you have a clamp meter — sanity-check against that 7A fuse so you know your headroom.

Two gotchas to keep in your back pocket. First, **ground bounce / common-impedance coupling**: your motor return currents and your ESP32 logic share a ground — they have to, for STEP/DIR to have a common reference. If those high return currents flow through a shared segment, they can offset the logic reference and cause erratic behavior. Star-grounding (each driver's GND and the ESP32 GND returning to a common point at the PSU, not daisy-chained) is the mitigation. If step 4 gets flaky but steps 1–3 were clean, suspect grounding before you suspect code. Second, **staggered enable**: firing three EN lines simultaneously means three simultaneous inrush events on the PSU. If you see a startup dip in step 2, stagger the EN assertions by a few milliseconds in software — cheap fix, and good practice regardless.

So the short version: it's not 1→2→3-with-every-pair. It's *re-confirm each → hold all three (no motion) → run your real vertical pair → run all three*, watching the rails, the logic supply, and the ESP32's pulse the whole way. Pairs come out only if all-three trips.

Want me to sketch the energize-only hold test as a minimal MicroPython snippet — all three EN active, no stepping, with a clean disable on exit — so step 2 is just "run and measure"?





---



So, let's pause, and let's talk through concepts outlined below.  Feel free to let me know if you have any clarifying questions.

And remember-- you're a professor and here, you're basically writing me my own project-related textbook.

Background concept explanations:

Many of the concepts presented to me by ClaudeAI are new concepts to me.  Here is a list.

Please create a Markdown document entitled "Concepts to know prior to Phase 2: Testing all 3 motors".
Ensure you place both my entire Question and your entire Answer into the document, minus the technical aspects of the question's prompt (i.e., keep all 5 requested explanation-sub-items per list item).

Please explain each.  I need to learn as much as possible in this project, to be as explanatory as a textbook would be, on each topic (An introductory textbook of a HS or college class, for non STEM folks like myself.  Note: I am a SWE and I have wired up a 12v solar panel system previously.).  

Explanation-sub-items requested:
1. what it is in general. what to know about it.
2. context around the concept, or its related or opposing concept, it relevant. how it's can be problematic and solutions. 
3. if it can be dangerous if mis-applied
4. its relevance to my project.
5. examples in my project (or hypotheticals if need-be), with an overview (such as consequences of common gotchas & problems/solutions), a zoom into the relevant parts of my project related to the concept being explained, and an explanation of any sub-list-items which may come up within your explanation (that is-- when you bring up technical concepts in your explanation-- add those to a list of "sub-list-items to explain" within that list item.  That is, try to teach me new things during the explanation, and explain the concept of those new things too as their own indepentdent list items)
  
List items for explanation:
- common ground
- what VDD stands for. what VM stands for
- marginal shared connection 
- holding current vs stepping
- ground bounce
- common-impedance coupling
- return currents
- common reference
- shared segment
- logic reference
- star-grounding
- staggered enable
- startup dip
- grounding topology
- internal ground bond
-  shared impedance
- high vs low impendeance
-  " logic neg rail" and "rail" in that sense in general
-  






-----


IN this:

3. Danger if mis-applied. VM is genuinely dangerous in the sense that it's your
high-current rail — a short on VM dumps serious current (that's what your fuses guard).
VDD mistakes are usually damage-to-the-chip hazards (over-voltage on a logic pin) rather
than fire hazards. Mixing them up — e.g., accidentally bridging VM to VDD — would put 24V
onto a 3.3V net and destroy the ESP32 instantly, and possibly the PC behind it via USB.



What is meant by "24V onto a 3.3V net"? Go into more detail on that



->  a dedicated logic-ground wire
  Can I ground from my mini-breadboard-terminal block's ground rail? (the one shared by esp32 and all 3 of the tmc chips)... or is it better to solder a wire to the esp32's GND (or maybe gator-clip onto a unsheathed part of its jumper, or wire into an unsheathed part of its jumper with some sort of attachment point or mechanism)

.... is that this concept?


"7. Return currents" --> "5. Examples in your project.":
Overview / gotcha: Gotcha — sizing the positive wires correctly (you used 18 AWG with 2A per-leg fuses) but treating ground as "just ground." Ground carries the same amps; it deserves the same gauge. You've done this on the motor side; the thing to add is a dedicated (thin is fine) logic-reference return so logic current doesn't borrow the motor's return. 
Zoom-in: Motor return route (good, keep it): coil → driver → C2-right GND → terminal block neg → PSU neg, on 18 AWG. Logic return route (improve it): ESP32/driver-logic GND → neg rail → dedicated wire → PSU neg. Two separate returns meeting only at the star point.


