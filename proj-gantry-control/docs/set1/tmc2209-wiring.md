# TMC2209 wiring reference

Confirmed working pinout — single driver bring-up (Z1 motor, first successful test).

## ESP32 signal lines → TMC2209

| Wire color | From | To |
|---|---|---|
| Green | ESP32 GPIO13 | EN (active low) |
| Yellow | ESP32 GPIO27 | STEP |
| White | ESP32 GPIO14 | DIR |

## 24V power → TMC2209

| Wire color | From | To |
|---|---|---|
| Red | 24V PSU + (via terminal block, 2A fuse) | VM |
| Black | 24V PSU GND | GND |

## TMC2209 → motor coils

| Wire color | TMC2209 terminal | Coil |
|---|---|---|
| Red | A1 | Coil A |
| Blue | A2 | Coil A |
| Green | B1 | Coil B |
| Black | B2 | Coil B |

## ESP32 logic power → TMC2209

| Wire color | From | To |
|---|---|---|
| Red | ESP32 VDD (3.3V) via mini-breadboard rail, inline 33Ω resistor | VDD |
| Black | ESP32 GND | GND |

## Notes

- The 33Ω resistor sits inline on the VDD (logic, 3.3V) line only — never on VM (24V motor power).
- VM and VDD are this chip's silkscreen labels for what was earlier called VS and VIO — same function, different naming convention.
- Coil pairing: A1+A2 = one coil, B1+B2 = the other. Swapping a pair (e.g. A1↔A2) reverses spin direction without harm. Crossing coils (e.g. pairing A1 with B1) causes stalling/erratic behavior — don't do that.
- GPIO12 was avoided for DIR due to ESP32 boot-time pull-down behavior; GPIO14 was used instead.
- VREF should read ~1.7V for 1.2A RMS on these NEMA 17 motors (D42HS3417-24B22). Measured by probing VREF pin (positive) against 24V PSU ground (negative), with both ESP32 and 24V supply powered.
