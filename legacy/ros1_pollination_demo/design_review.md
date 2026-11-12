# ðŸ”¬ DESIGN REVIEW â€” Sprayer Control Architecture Pivot
### Date: February 17, 2026
### Reviewer Role: Senior Mechatronics Engineer & Systems Architect (UAV Payload Integration)
### Hardware Baseline: F450 Frame | Pixhawk 2.4.8 | Jetson Nano 4GB | Brushless EDF + Stepper Auger
### Scope: Critical analysis of the "Hybrid Control" architecture for the Coaxial Venturi Pollination Sprayer

---

## TABLE OF CONTENTS

```
1. EXECUTIVE SUMMARY ................................................ Section 1
2. CURRENT ARCHITECTURE â€” AS PROPOSED ................................ Section 2
3. CRITICAL ANALYSIS â€” HYBRID CONTROL SPLIT .......................... Section 3
   3.1  The Split Control Problem .................................... Section 3.1
   3.2  Synchronization & Latency Risk Analysis ...................... Section 3.2
   3.3  Weight & Complexity Overhead ................> **Post-Review Update (2025-02-17):** Option A (Full Pixhawk Control) has been adopted.
> All code, configs, and documentation have been updated accordingly.
> ESP32 and relay module removed from BOM. See updated files:
> - `config/ardupilot_params.param` - SERVO13/14 configured, RELAY removed
> - `ros_nodes/scripts/spray_logic_node.py` - Rewritten for mavros DO_SET_SERVO
> - `ros_nodes/launch/demo.launch` - mavros included, ESP32 serial removed
> - `diagrams/system_architecture.mmd` - AUX5/AUX6 path shown
> - `diagrams/state_machine.mmd` - Spray sub-states added
> - `MASTER_EXECUTION_GUIDE.md` - Day 3+ rewritten for Pixhawk servo setup
> - `ACTION_PLAN_SURVIVAL.md` - Architecture diagram updated
> - `esp32/sprayer_controller/sprayer_controller.ino` - Marked DEPRECATED...... Section 3.3
4. ARCHITECTURAL ALTERNATIVES â€” BRAINSTORMING ........................ Section 4
   4.1  Option A: Full Pixhawk (Replace Stepper with Servo/DC Motor). Section 4.1
   4.2  Option B: Full Independent ESP32 (Payload Island) ........... Section 4.2
   4.3  Option C: Jetson Direct GPIO (Minimal Hardware) ............. Section 4.3
   4.4  Comparison Matrix ............................................ Section 4.4
5. MECHANICAL REVIEW â€” COAXIAL VENTURI SPRAYER ....................... Section 5
   5.1  Gold Motor EDF + 20A ESC Analysis ........................... Section 5.1
   5.2  Coaxial "Recessed Tip" Venturi Validation ................... Section 5.2
   5.3  Powder Flow & Auger Coupling ................................ Section 5.3
6. WIRING & POWER SAFETY ............................................ Section 6
   6.1  System Grounding Strategy .................................... Section 6.1
   6.2  Optocoupler Requirement for ESC Signal ....................... Section 6.2
   6.3  Power Distribution Architecture .............................. Section 6.3
   6.4  EMI & Noise Mitigation ...................................... Section 6.4
7. RECOMMENDED FINAL ARCHITECTURE .................................... Section 7
8. UPDATED WIRING DIAGRAM ........................................... Section 8
9. IMPLEMENTATION ACTION ITEMS ....................................... Section 9
```

---

## 1. EXECUTIVE SUMMARY

**Verdict: The Hybrid Control approach (Pixhawk for Fan, ESP32 for Stepper) is functional but suboptimal for a prototype. The split introduces unnecessary synchronization complexity, an additional point of failure, and ~15â€“25g of dead weight for a task that can be solved more elegantly.**

The recommended path forward is **Option A (Full Pixhawk Control)** â€” replace the stepper motor with a continuous rotation servo (e.g., MG996R modified or a FeeTech FS5103R) to drive the auger, allowing Pixhawk to control both the EDF Fan (AUX Ch5) and the Feeder (AUX Ch6) directly via MAVLink `DO_SET_SERVO` commands from the Jetson Nano. This **eliminates the ESP32 entirely**, reduces wiring, saves weight, removes a communication path, and simplifies the failure mode analysis.

However, if precise powder dosing is critical and you need micro-stepping resolution in a later prototype, **Option B (Full ESP32 Payload Island)** is the cleaner fallback â€” move the ESC control to the ESP32 as well, so the entire payload subsystem is self-contained and decoupled from the flight controller.

**The current hybrid plan (Option "Current") is the worst of both worlds.** It has the complexity of two controllers, the synchronization risk of split buses, and the weight penalty of the ESP32 â€” but doesn't gain the precision of full stepper control because the timing is uncertain.

---

## 2. CURRENT ARCHITECTURE â€” AS PROPOSED

```
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚                     CURRENT PROPOSED ARCHITECTURE                    â”‚
    â”‚                        (Hybrid Control)                              â”‚
    â”‚                                                                      â”‚
    â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                                                     â”‚
    â”‚  â”‚ JETSON NANO â”‚                                                     â”‚
    â”‚  â”‚  (Master)   â”‚                                                     â”‚
    â”‚  â”‚             â”œâ”€â”€â”€â”€ UART/MAVLink â”€â”€â”€â”€â”€â”€â–ºâ”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”            â”‚
    â”‚  â”‚  "FIRE"     â”‚    (921600 baud)        â”‚  PIXHAWK    â”‚            â”‚
    â”‚  â”‚  Command    â”‚                         â”‚  2.4.8      â”‚            â”‚
    â”‚  â”‚  Issued     â”‚  DO_SET_SERVO(Ch5,PWM)  â”‚             â”‚            â”‚
    â”‚  â”‚             â”‚                         â”‚  AUX Ch5 â”€â”€â”€â”¼â”€â”€â–º ESC â”€â”€â–º EDF Fan
    â”‚  â”‚             â”‚                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â”‚
    â”‚  â”‚             â”‚                                                     â”‚
    â”‚  â”‚             â”œâ”€â”€â”€â”€ USB Serial â”€â”€â”€â”€â”€â”€â”€â”€â–ºâ”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”            â”‚
    â”‚  â”‚             â”‚    (115200 baud)        â”‚   ESP32-S3  â”‚            â”‚
    â”‚  â”‚  "FEED_ON"  â”‚                         â”‚             â”‚            â”‚
    â”‚  â”‚  Command    â”‚                         â”‚  GPIO â”€â”€â”€â”€â”€â”€â”¼â”€â”€â–º ULN2003 â”€â”€â–º Stepper
    â”‚  â”‚             â”‚                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â”‚
    â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                                     â”‚
    â”‚                                                                      â”‚
    â”‚  CONTROL PATHS:                                                      â”‚
    â”‚    Fan:    Jetson â†’ MAVLink â†’ Pixhawk â†’ AUX5 PWM â†’ ESC â†’ EDF       â”‚
    â”‚    Feeder: Jetson â†’ USB Serial â†’ ESP32 â†’ GPIO Step/Dir â†’ Stepper    â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 3. CRITICAL ANALYSIS â€” HYBRID CONTROL SPLIT

### 3.1 The Split Control Problem

**Issue:** You are using two fundamentally different communication buses and two different controllers for actuators that MUST work in concert. The Fan and the Feeder are not independent systems â€” they are a **single spray event** that requires coordinated timing.

| Aspect | Fan Path (MAVLink to Pixhawk) | Feeder Path (Serial to ESP32) |
|--------|-------------------------------|-------------------------------|
| **Bus** | UART @ 921600 baud | USB Serial @ 115200 baud |
| **Protocol** | MAVLink v2 (binary, checksummed) | ASCII text ("SPRAY_ON\n") |
| **Overhead** | MAVLink framing: 12-byte header + payload + CRC. `DO_SET_SERVO` â‰ˆ 27 bytes. | "FEED_ON\n" = 8 bytes + USB framing |
| **Transport Latency** | UART bit time: 27 bytes Ã· 921600 = **~0.03ms**. BUT MAVLink scheduler on Pixhawk has a message processing queue â‰ˆ **5â€“20ms** typical. | USB CDC enumeration overhead: **1â€“3ms** per packet. Serial buffer flush: **~1ms**. ESP32 `loop()` polling: **~1ms**. |
| **Processing Latency** | Pixhawk receives `DO_SET_SERVO` â†’ updates PWM output on next servo cycle (typically 50Hz = **20ms** period). Worst case: command arrives just after a cycle â†’ **up to 20ms delay**. | ESP32 reads serial â†’ `processCommand()` â†’ `digitalWrite()`: **<0.1ms**. |
| **Total Latency** | **5â€“40ms** from Jetson `send()` to ESC receiving PWM change | **2â€“5ms** from Jetson `write()` to stepper pin change |

**Key Finding:** The ESP32 path is actually **faster** than the Pixhawk path. If you send both commands simultaneously from Jetson, the stepper will start **before** the EDF fan spins up. This is the **opposite** of what you want.

### 3.2 Synchronization & Latency Risk Analysis

#### The Spray Sequence Physics

For the Coaxial Venturi to work correctly, the sequence MUST be:

```
    CORRECT SEQUENCE:
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    
    Time 0ms:       EDF Fan starts spinning
    Time 50-200ms:  EDF reaches operating RPM (airflow establishes)
    Time 200ms+:    Venturi suction is active in the coaxial tube
    Time 200ms+:    Stepper starts feeding powder into inner tube
    Time 200ms+:    Powder is entrained by airflow and ejected
    
    â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    
    WRONG SEQUENCE (Powder before Air):
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    
    Time 0ms:       Stepper starts (powder drops into tube)
    Time 0-50ms:    No airflow â†’ powder clumps in the nozzle
    Time 50ms+:     Fan starts â†’ initial air blast pushes clump out
    
    RESULT: Uneven spray burst, possible clog, wasted pollen.
    For dry pollen this is WORSE â€” clumping = pollination failure.
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

#### Latency Analysis Under Hybrid Control

When the Jetson Nano's spray logic node fires, let's trace what happens:

```python
# In spray_logic_node.py (current code, conceptual update for hybrid)
def _do_spray(self):
    # These two lines execute ~microseconds apart on Jetson
    self.mavlink_send_servo(channel=5, pwm=1800)  # Fan ON via MAVLink
    self.serial_send("FEED_ON\n")                  # Stepper ON via ESP32
```

| Event | Fan Path (MAVLink) | Feeder Path (Serial) |
|-------|-------------------|---------------------|
| Jetson sends command | T+0ms | T+0ms (effectively simultaneous) |
| Command arrives at controller | T+5â€“20ms (MAVLink queue) | T+2â€“5ms (USB CDC) |
| Controller processes command | T+5â€“40ms (next servo cycle) | T+2â€“5ms (instant GPIO) |
| Actuator begins physical motion | T+50â€“200ms (EDF spool-up to operational RPM) | T+3â€“6ms (stepper first step) |
| Actuator at operating point | T+200â€“500ms (full airflow) | T+10â€“50ms (auger turning) |

**CRITICAL FINDING:**

The stepper motor will begin feeding powder **50â€“200ms BEFORE** the EDF fan establishes airflow. This means:

1. **Dry pollen falls into the inner tube with no Venturi suction** â†’ gravity-fed clumping.
2. **When airflow finally arrives**, it hits a pre-loaded clump â†’ **uneven burst** instead of steady stream.
3. **Pollen waste** is unacceptable â€” oil palm pollen is collected by hand, limited supply.

#### Is This Acceptable?

**No.** For a prototype demonstrating concept viability, this timing mismatch could be mitigated with a software delay (start the fan first, wait 300ms, then start the feeder). But this software delay is fragile â€” it assumes a fixed EDF spool-up time that varies with battery voltage, temperature, and mechanical load. In your current architecture, you'd need to:

```python
# Workaround (fragile):
self.mavlink_send_servo(channel=5, pwm=1800)   # Fan ON
time.sleep(0.3)                                  # â† BLOCKING sleep. BAD in a ROS callback.
self.serial_send("FEED_ON\n")                    # Stepper ON
```

This `sleep()` blocks the ROS callback thread, freezing your state machine for 300ms. During that 300ms, you're not processing new camera frames, not updating visual servoing, and not monitoring safety conditions. **On a flying drone, 300ms of blindness is dangerous.**

A better approach is a non-blocking timer in the state machine, but this adds state complexity:

```
SPRAY state â†’ sub-states: SPRAY_FAN_START â†’ SPRAY_FAN_WAIT(300ms) â†’ SPRAY_FEED_START â†’ SPRAY_ACTIVE â†’ SPRAY_STOP
```

This works but is the kind of complexity that should make you question the architecture.

### 3.3 Weight & Complexity Overhead of the ESP32

| Component | Weight | Purpose |
|-----------|--------|---------|
| ESP32-S3 DevKitC | ~10g | Stepper control only |
| USB Cable (Jetson â†’ ESP32) | ~8g (short cable) | Communication |
| ULN2003 Driver Board | ~5g | Stepper driving (for 28BYJ-48) |
| OR: A4988 + Breakout | ~3g | Stepper driving (for NEMA 17) |
| Wiring (ESP32 â†’ Driver â†’ Stepper) | ~5g | Power + signal |
| **Total** | **~28â€“31g** | **Just to turn an auger** |

**For context on an F450 frame:**

- F450 typical AUW (All-Up Weight) with 4S LiPo, Pixhawk, Jetson: ~1200â€“1500g.
- 30g is ~2% of AUW. Not catastrophic, but on a weight-sensitive platform where every gram affects flight time, it's meaningful.
- **The real cost isn't weight â€” it's complexity:**
  - Additional USB device to enumerate on boot (can fail).
  - Additional serial protocol to maintain (ESP32 firmware).
  - Additional power rail to manage (ESP32 3.3V logic).
  - Additional firmware to flash and version-control.
  - Additional failure mode: ESP32 crashes mid-spray â†’ stepper locks/runs away.
  - Your existing `sprayer_controller.ino` needs significant rewrite (currently relay-based, not stepper-based).

**Verdict on ESP32 for one stepper:** It's engineering overkill. You're using a dual-core 240MHz microcontroller with WiFi/BT/USB to generate step pulses. A $0.50 555 timer could do this (exaggeration, but the point stands).

---

## 4. ARCHITECTURAL ALTERNATIVES â€” BRAINSTORMING

### 4.1 Option A: Full Pixhawk Control (Eliminate ESP32)

**Concept:** Replace the stepper motor + driver with a **Continuous Rotation Servo** (e.g., FeeTech FS5103R, MG996R modified, or DS3218 digital servo). Pixhawk drives both:

- **AUX Channel 5** â†’ ESC â†’ EDF Fan (air source)
- **AUX Channel 6** â†’ Continuous Servo â†’ Auger (powder feeder)

Both actuators are commanded via MAVLink `DO_SET_SERVO` from Jetson Nano.

```
    OPTION A â€” FULL PIXHAWK CONTROL
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚ JETSON NANO â”‚â”€â”€ UART/MAVLink â”€â”€â”€â”€â”€â”€â”€â”€â–ºâ”‚  PIXHAWK    â”‚
    â”‚  (Master)   â”‚   (921600 baud)         â”‚  2.4.8      â”‚
    â”‚             â”‚                         â”‚             â”‚
    â”‚  DO_SET_SERVO(Ch5, 1800)              â”‚  AUX Ch5 â”€â”€â”€â”¼â”€â”€â–º 20A ESC â”€â”€â–º EDF Fan
    â”‚  DO_SET_SERVO(Ch6, 1600)              â”‚  AUX Ch6 â”€â”€â”€â”¼â”€â”€â–º Continuous Servo â”€â”€â–º Auger
    â”‚             â”‚                         â”‚             â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

    ELIMINATED: ESP32, USB cable, ULN2003/A4988 driver board
    ADDED:      One continuous rotation servo (~$3-8)
```

#### Pros

| Pro | Detail |
|-----|--------|
| **Single communication bus** | Both actuators commanded via the same MAVLink channel. No synchronization risk between different buses. |
| **Guaranteed timing** | Both `DO_SET_SERVO` commands are processed in the same Pixhawk servo cycle (50Hz). Fan and feeder start within **<20ms** of each other (one servo period). |
| **Eliminated components** | No ESP32, no USB cable, no stepper driver board. Saves ~25-30g and removes 4 potential failure points. |
| **Simplified firmware** | No ESP32 firmware to maintain. Pixhawk servo output is configured entirely via parameters â€” no code required. |
| **PWM speed control** | Continuous servo speed is proportional to PWM deviation from center (~1500Âµs). 1500Âµs = stop, 1300Âµs = full CCW, 1700Âµs = full CW. This gives you **variable feed rate** for free. |
| **Pixhawk failsafe** | If MAVLink connection is lost, Pixhawk can set servo outputs to safe defaults (fan OFF, feeder STOP) via `SERVOx_TRIM` parameters. No separate watchdog needed. |
| **Simpler wiring** | Servo 3-wire (PWM/5V/GND) plugs directly into Pixhawk AUX rail. ESC signal wire plugs into AUX rail. Both share Pixhawk servo power bus. |

#### Cons

| Con | Detail | Severity | Mitigation |
|-----|--------|----------|------------|
| **No micro-stepping** | A continuous servo has no step resolution. Speed is analog (PWM-proportional) but position is uncontrolled. | **Medium** | For an auger, you need rotation speed, not angular position. Continuous rotation is actually ideal. The auger just needs to turn â€” how many degrees per step is irrelevant. |
| **Imprecise dosing** | Stepper gives precise volumetric dosing (X steps = Y mg of powder). Servo gives "run at this speed for this duration" â€” less repeatable. | **Medium** | For prototype, run servo at fixed speed for calibrated duration. Measure output mass empirically. Acceptable for proof-of-concept. For production, upgrade to stepper-based dosing later. |
| **Torque characteristics** | Continuous servos have decent torque (~5-13 kgÂ·cm for MG996R class) but are gear-reduced â€” they spin slowly (60-100 RPM max). A stepper (especially NEMA 17) can be geared for higher torque or speed flexibility. | **Low** | An auger for dry powder doesn't need high torque or speed. 30-60 RPM is likely ideal. A standard continuous servo provides this in the correct range. |
| **Servo holding torque** | When PWM = 1500Âµs (stop), a continuous servo has **minimal holding torque**. The auger could back-drive slightly. | **Low** | Dry powder in a vertical auger has high static friction. Back-driving is unlikely. If it occurs, keep a slight PWM offset (e.g., 1505Âµs) to maintain gentle holding force. |
| **Servo power from Pixhawk** | Pixhawk AUX servo rail can supply 5V, but current capacity depends on the BEC/power module. Adding a servo (stall current ~1-2.5A) could exceed the rail capacity. | **Medium** | Power the servo rail with a **separate 5V BEC** from the 4S LiPo, not from the Pixhawk internal regulator. Pixhawk only provides the signal; external BEC provides servo power. This is standard practice. |

#### Actuator Replacement Candidates

| Motor Type | Model | Speed | Torque | Voltage | Weight | Price | Verdict |
|-----------|-------|-------|--------|---------|--------|-------|---------|
| **Continuous Servo** | FeeTech FS5103R | ~60 RPM | 3 kgÂ·cm | 5V | 38g | ~$4 | âœ… Best for prototype |
| **Continuous Servo** | MG996R (modified) | ~55 RPM | 11 kgÂ·cm | 5V | 55g | ~$5 | âœ… Higher torque option |
| **Continuous Servo** | DS3218 (digital, 270Â°â†’cont.) | ~70 RPM | 20 kgÂ·cm | 6.8V | 60g | ~$8 | âš ï¸ Overkill, needs 6.8V |
| **Brushed DC + small ESC** | N20 Gear Motor (6V, 100RPM) | 100 RPM | 0.5 kgÂ·cm | 6V | 15g | ~$3 | âœ… Lightest, but needs separate ESC/MOSFET |
| **Brushed DC** | JGA25-370 (12V, 60RPM) | 60 RPM | 5 kgÂ·cm | 12V | 80g | ~$5 | âš ï¸ Heavy, needs H-bridge |

**Recommended for Option A:** **FeeTech FS5103R** or equivalent continuous rotation servo. Lightest, simplest wiring (direct to Pixhawk AUX), adequate torque for a powder auger, and PWM speed control for free.

---

### 4.2 Option B: Full Independent ESP32 (Payload Island)

**Concept:** Move the ESC control AWAY from Pixhawk. The ESP32 controls **both** the EDF Fan (via its own PWM output to the ESC) and the Stepper Motor. Pixhawk ONLY handles flight. The payload is a completely decoupled subsystem.

```
    OPTION B â€” FULL ESP32 PAYLOAD ISLAND
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     UART/MAVLink      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚ JETSON NANO â”‚â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–º  â”‚  PIXHAWK    â”‚
    â”‚  (Master)   â”‚   (Flight commands     â”‚  2.4.8      â”‚
    â”‚             â”‚    only â€” velocity,     â”‚             â”‚
    â”‚             â”‚    mode, arm/disarm)    â”‚  [Flies     â”‚
    â”‚             â”‚                         â”‚   Only]     â”‚
    â”‚             â”‚                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
    â”‚             â”‚
    â”‚             â”œâ”€â”€â”€â”€ USB Serial â”€â”€â”€â”€â”€â”€â”€â”€â–ºâ”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚             â”‚   (115200 baud)         â”‚   ESP32-S3  â”‚
    â”‚  "SPRAY"    â”‚                         â”‚  (Payload   â”‚
    â”‚  command    â”‚                         â”‚   Controller)â”‚
    â”‚             â”‚                         â”‚             â”‚
    â”‚             â”‚                         â”‚  PWM Pin â”€â”€â”€â”¼â”€â”€â–º 20A ESC â”€â”€â–º EDF Fan
    â”‚             â”‚                         â”‚  GPIO Pins â”€â”¼â”€â”€â–º ULN2003 â”€â”€â–º Stepper
    â”‚             â”‚                         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

    Pixhawk AUX channels: UNUSED for payload (all free for future expansion)
    ESP32: Full payload autonomy â€” handles spray timing internally
```

#### Pros

| Pro | Detail |
|-----|--------|
| **Perfect synchronization** | The ESP32 controls both actuators with microsecond-level timing. It can start the fan, wait for RPM stabilization, then start the stepper â€” all in deterministic firmware, no network latency. |
| **Flight controller isolation** | Pixhawk is not involved in payload actuation at all. A payload fault (ESC short, stepper jam) cannot affect flight stability. The MAVLink bus is never burdened with servo commands. |
| **Stepper precision retained** | You keep the full micro-stepping capability for precise powder dosing. |
| **Expandable** | ESP32 has many GPIOs. Future sensors (hopper level, nozzle pressure, flow rate) can be added to the payload controller without touching the flight stack. |
| **Clean separation of concerns** | Flight team works on Pixhawk params. Payload team works on ESP32 firmware. No coupling. Good for team development. |
| **Spray sequence as firmware state machine** | The ESP32 can implement the full spray sequence internally: `FAN_SPOOL â†’ FAN_READY â†’ FEED_START â†’ SPRAYING â†’ FEED_STOP â†’ FAN_COOLDOWN â†’ IDLE`. Jetson just says "SPRAY" and the ESP32 handles timing. |

#### Cons

| Con | Detail | Severity | Mitigation |
|-----|--------|----------|------------|
| **Weight penalty** | ESP32 + driver boards + USB cable remain (~28-31g). | **Low-Medium** | Accept for prototype. Replace with custom PCB in V2. |
| **Additional firmware** | ESP32 needs robust firmware with watchdog, safety timeouts, and error handling. More code to maintain. | **Medium** | Your existing `sprayer_controller.ino` is a good starting point. Extend rather than rewrite. |
| **ESC signal from ESP32 GPIO** | ESP32 generates 50Hz PWM for the ESC using `ledc` peripheral. This works but requires careful timer configuration (16-bit timer, 50Hz, 1000-2000Âµs duty). | **Low** | Well-documented in ESP32 Arduino framework. `ledcWrite()` is reliable for servo/ESC PWM. |
| **Pixhawk AUX unused** | You have available Pixhawk AUX channels going to waste. | **None** | They remain available for future use (camera gimbal, lights, etc.). |
| **USB Serial single point of failure** | If the USB cable disconnects mid-spray, the ESP32 watchdog stops the spray (good), but you lose payload control until reconnected. | **Medium** | ESP32 watchdog already implemented in your code (2-second timeout â†’ auto-off). This is actually safer than a Pixhawk servo that defaults to last PWM value. |

#### ESP32 Spray Sequence (Firmware-Level Timing)

```cpp
// Conceptual spray sequence on ESP32 (Option B)
void executeSpraySequence() {
    // Phase 1: Spool up EDF fan
    setFanPWM(1400);              // Low speed start (soft-start)
    delay(100);
    setFanPWM(1600);              // Medium
    delay(100);
    setFanPWM(1800);              // Full operating speed
    delay(200);                    // Wait for airflow to stabilize
    
    // Phase 2: Begin powder feed
    startStepper(FEED_RPM);       // Auger turns, powder enters airstream
    
    // Phase 3: Spray active for configured duration
    delay(sprayDurationMs);        // e.g., 500ms
    
    // Phase 4: Stop feed first, then fan
    stopStepper();                 // Stop powder
    delay(200);                    // Let remaining powder clear the tube
    setFanPWM(1500);              // Fan OFF (neutral PWM)
    
    sendSerial("SPRAY_COMPLETE\n");
}
```

**This is the key advantage of Option B:** The spray timing is deterministic, hardware-local, and independent of any network latency.

---

### 4.3 Option C: Jetson Direct GPIO (Minimal Hardware)

**Concept:** Eliminate both Pixhawk AUX and ESP32. Jetson Nano drives the ESC and a small DC motor (replacing the stepper) directly via its GPIO pins.

```
    OPTION C â€” JETSON DIRECT
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚ JETSON NANO â”‚â”€â”€ UART/MAVLink â”€â”€â”€â”€â”€â”€â”€â”€â–º PIXHAWK (Flight only)
    â”‚             â”‚
    â”‚  GPIO PWM â”€â”€â”¼â”€â”€â–º ESC â”€â”€â–º EDF Fan
    â”‚  GPIO PWM â”€â”€â”¼â”€â”€â–º MOSFET â”€â”€â–º Small DC Motor â”€â”€â–º Auger
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

#### Why This Is NOT Recommended

| Issue | Detail |
|-------|--------|
| **Jetson GPIO PWM is software-based** | Jetson Nano has **no hardware PWM** on its 40-pin header (unlike Raspberry Pi). Software PWM via `Jetson.GPIO` is jittery (~Â±5% duty cycle variation). ESCs are sensitive to PWM timing â€” jitter causes motor speed oscillation. **Dangerous on a brushless motor.** |
| **Real-time constraints** | Jetson runs Linux (not RTOS). GPIO timing is subject to kernel scheduling delays. A GC pause, swap event, or ROS callback burst can cause a 10-50ms PWM glitch. |
| **Electrical risk** | Jetson GPIO is 3.3V, max 10-15mA. ESCs expect 3.3-5V PWM signal with low impedance. The Jetson signal may need a level shifter/buffer, adding complexity. |
| **Shared compute** | Every cycle spent on PWM generation is a cycle not spent on YOLO inference. This fights your compute budget. |

**Verdict:** âŒ Reject. Jetson Nano is a compute platform, not a real-time actuator controller. Leave PWM generation to dedicated hardware (Pixhawk or ESP32).

---

### 4.4 Comparison Matrix

| Criteria | Current (Hybrid) | Option A (Full Pixhawk) | Option B (Full ESP32) | Option C (Jetson Direct) |
|----------|:-----------------:|:-----------------------:|:---------------------:|:------------------------:|
| **Components eliminated** | None (baseline) | ESP32 + driver + USB cable | None | ESP32 + driver |
| **Weight saved** | 0g | ~25-30g | 0g | ~20g |
| **Communication buses** | 2 (MAVLink + Serial) | 1 (MAVLink only) | 2 (MAVLink + Serial) | 1 (MAVLink only) |
| **Sync risk (Fan vs Feed)** | âš ï¸ HIGH (different buses, 50-200ms skew) | âœ… LOW (<20ms, same servo cycle) | âœ… NONE (firmware-controlled) | âš ï¸ HIGH (software PWM jitter) |
| **Dosing precision** | High (stepper) | Medium (servo speed Ã— time) | High (stepper) | Low (DC motor speed varies) |
| **Failsafe quality** | âš ï¸ Two separate watchdogs | âœ… Pixhawk SERVOx_TRIM defaults | âœ… ESP32 watchdog (proven) | âŒ No hardware failsafe |
| **Firmware complexity** | High (ESP32 + ROS + MAVLink) | Low (MAVLink only) | Medium (ESP32 firmware) | Low but fragile |
| **Flight controller coupling** | Medium | Medium | None (full isolation) | Medium |
| **Prototype speed** | Medium | âœ… FAST | Medium | âŒ Slow (debug jitter) |
| **Production scalability** | Medium | Medium | âœ… Best (modular payload) | âŒ Poor |
| **PWM reliability** | âœ… (ESC from Pixhawk) | âœ… (both from Pixhawk) | âœ… (ESC from ESP32 ledc) | âŒ (software PWM) |
| **OVERALL RATING** | â­â­ | â­â­â­â­ (Prototype) | â­â­â­â­â­ (Production) | â­ |

---

## 5. MECHANICAL REVIEW â€” COAXIAL VENTURI SPRAYER

### 5.1 Gold Motor EDF + 20A ESC Analysis

#### EDF Inrush Current Concern

| Parameter | Typical Value | Concern |
|-----------|---------------|---------|
| Gold Motor EDF rated current | 8-15A continuous (varies by model) | Within ESC rating |
| EDF locked-rotor / stall current | **3-5Ã— rated** = 24-75A | âŒ EXCEEDS 20A ESC |
| Inrush at startup (0â†’full PWM) | **2-3Ã— rated** for ~100-500ms | âš ï¸ May trigger ESC overcurrent protection |
| Typical 20A ESC burst rating | 25-30A for 10s | Marginal if motor is larger |

**Critical Assessment:**

1. **If your "Gold Motor" EDF draws >12A continuous at operating RPM**, a 20A ESC has only ~60% headroom. Inrush during hard start will spike to 25-35A. Most 20A ESCs have overcurrent protection that triggers at ~25-30A â€” you may get a startup failure or ESC shutdown.

2. **The soft-start via PWM (your new plan) significantly helps.** Ramping from 1100Âµs â†’ 1400Âµs â†’ 1600Âµs â†’ 1800Âµs over 300ms keeps inrush current manageable. This is one of the strongest arguments for PWM control over relay on/off.

3. **However, "Vacuum motor" style EDFs are often higher current than hobby EDFs.** They have thicker windings optimized for static pressure (no forward airspeed cooling) rather than thrust. Verify the motor's actual current draw at operating voltage with a clamp meter before committing to the 20A ESC.

**Recommendation:**

| Scenario | ESC Sizing |
|----------|-----------|
| Motor draws â‰¤10A at 4S operating point | 20A ESC is fine (100% headroom) |
| Motor draws 10-15A | **Upgrade to 30A ESC** (~$3-5 more, same weight class) |
| Motor draws >15A | 30-40A ESC mandatory. Reconsider motor choice. |

> **Action Item:** Before mounting, bench-test the Gold Motor EDF with a watt meter (e.g., GT Power 150A) at 4S voltage. Measure steady-state current at your intended operating PWM. Add 50% margin for ESC selection.

### 5.2 Coaxial "Recessed Tip" Venturi Validation

#### The Concept Reviewed

```
    COAXIAL VENTURI SPRAYER â€” Cross Section
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    AIRFLOW DIRECTION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–º

    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚  OUTER TUBE (Air)                                    â”‚
    â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”‚
    â”‚  â”‚          AIR FROM EDF â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–º      â”‚      â”‚
    â”‚  â”‚                                            â”‚      â”‚
    â”‚  â”‚      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”              â”‚      â”‚
    â”‚  â”‚      â”‚  INNER TUBE (Powder) â”‚              â”‚      â”‚
    â”‚  â”‚      â”‚                      â”‚â—„â”€ "Recessed" â”‚      â”‚
    â”‚  â”‚      â”‚  Powder from Auger â”€â”€â”¤   Tip        â”‚      â”‚
    â”‚  â”‚      â”‚         â–¼            â”‚              â”‚      â”‚
    â”‚  â”‚      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜              â”‚      â”‚
    â”‚  â”‚                                            â”‚      â”‚
    â”‚  â”‚          AIR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–º         â”‚      â”‚
    â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â”‚
    â”‚                                                      â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                                     â”€â”€â”€â–º EXIT
                                                     (Mixed air + powder)

    The "Recessed Tip" means the inner tube ends 10-30mm BEFORE
    the outer tube. Air flowing past the inner tube's open end
    creates a low-pressure zone (Venturi/Bernoulli effect) that
    "sucks" powder out of the inner tube.
```

#### Thermodynamic/Fluid Analysis

| Factor | Assessment | Rating |
|--------|------------|--------|
| **Venturi effect on dry powder** | The Venturi effect works on fluids (gases and liquids). Dry powder is NOT a fluid â€” it's a granular solid. The suction effect works on the **air in the inner tube**, which then drags powder particles by viscous entrainment. This is weaker than liquid suction. | âš ï¸ **Marginal** |
| **Particle size matters** | Oil palm pollen: ~20-50Âµm diameter. This is fine enough to be entrained by moderate airflow (similar to flour in a pneumatic conveyor). If your pollen is clumped (>200Âµm aggregates), the Venturi suction may be insufficient. | âœ… **Likely OK for fine pollen** |
| **Recess distance** | Too short (<5mm): Not enough low-pressure zone. Too long (>40mm): Turbulence fills in, pressure recovers. Sweet spot: **10-20mm recess** for tube diameters of 8-15mm outer, 4-6mm inner. | âœ… **Sound principle** |
| **Air velocity requirement** | For powder entrainment, you need minimum **5-15 m/s** airflow velocity at the inner tube exit. A small EDF can easily produce 10-30 m/s in a confined tube. | âœ… **Achievable** |
| **Clogging risk** | Dry powder in a narrow tube (4-6mm ID) is HIGHLY prone to clogging, especially if humid. Moisture causes pollen to swell and stick. | âš ï¸ **HIGH RISK** |
| **Gravity vs. Suction** | In a vertical configuration (inner tube pointing DOWN, exit pointing forward/down), gravity ASSISTS powder flow into the airstream. This is preferable to upward-facing configurations where gravity fights suction. | âœ… **Good if oriented correctly** |

#### Recommendations for the Venturi Design

1. **Inner tube diameter: â‰¥4mm ID.** Anything narrower clogs with powder. 5-6mm is safer.
2. **Recess distance: 15mm** as starting point. Test 10mm and 20mm variants.
3. **Inner tube tip geometry:** Chamfer or flare the inner tube exit at 30-45Â° â€” this acts as a nozzle diffuser and improves Venturi suction by directing more airflow across the exit plane.
4. **Anti-clog features:** 
   - Add a small vibration motor (phone vibrator, $0.50) taped to the inner tube/hopper. Constant vibration prevents powder bridging.
   - Desiccant packet in the hopper to absorb moisture.
   - Pre-sieve the pollen to remove clumps >100Âµm.
5. **Test methodology:** Before flight, bench-test with the following: EDF at operating PWM, inner tube loaded with measured pollen (0.5g). Time how long until the tube empties. Calculate flow rate (mg/s). This is your baseline dosing calibration.

### 5.3 Powder Flow & Auger Coupling

| Auger Parameter | Recommended Value | Rationale |
|----------------|-------------------|-----------|
| Auger diameter | 3-4mm (to fit inside 4-6mm ID tube) | Clearance for rotation without jamming |
| Pitch | 2-4mm | Lower pitch = finer dosing resolution, higher pitch = faster feed |
| Material | PLA/PETG (3D printed) | PETG preferred for smoother surface (less powder adhesion) |
| Rotation speed | 30-60 RPM | Too fast â†’ air pockets in powder column. Too slow â†’ insufficient feed rate. |
| Motor coupling | Flexible coupling or direct shaft insert | Rigid coupling + vibration = bearing wear. Flexible coupling absorbs misalignment. |

---

## 6. WIRING & POWER SAFETY

### 6.1 System Grounding Strategy

**CRITICAL: All subsystems MUST share a common ground (GND) reference.** Failure to do so causes:
- Floating logic levels â†’ random actuator triggers
- Ground loops â†’ motor noise couples into Pixhawk IMU â†’ flight instability
- USB communication errors â†’ ESP32 disconnects

```
    GROUNDING ARCHITECTURE
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    4S LiPo Battery (14.8V nominal)
         â”‚
         â”œâ”€â”€â”€â”€ GND (Battery Negative)
         â”‚         â”‚
         â”‚         â”œâ”€â”€â”€â”€ PDB (Power Distribution Board) GND Rail
         â”‚         â”‚         â”‚
         â”‚         â”‚         â”œâ”€â”€â”€â”€ ESC GND (Motor 1-4) â†â”€â”€ Flight ESCs
         â”‚         â”‚         â”‚
         â”‚         â”‚         â”œâ”€â”€â”€â”€ EDF ESC GND â†â”€â”€ Sprayer Fan ESC
         â”‚         â”‚         â”‚
         â”‚         â”‚         â”œâ”€â”€â”€â”€ 5V BEC #1 GND â”€â”€â–º Pixhawk Power Module
         â”‚         â”‚         â”‚         â”‚
         â”‚         â”‚         â”‚         â””â”€â”€â–º Pixhawk GND
         â”‚         â”‚         â”‚                  â”‚
         â”‚         â”‚         â”‚                  â””â”€â”€â–º Pixhawk AUX Rail GND
         â”‚         â”‚         â”‚                        (shared by servo signals)
         â”‚         â”‚         â”‚
         â”‚         â”‚         â”œâ”€â”€â”€â”€ 5V BEC #2 GND â”€â”€â–º Jetson Nano GND
         â”‚         â”‚         â”‚                          â”‚
         â”‚         â”‚         â”‚                          â””â”€â”€â–º USB GND
         â”‚         â”‚         â”‚                               (to ESP32 if used)
         â”‚         â”‚         â”‚
         â”‚         â”‚         â””â”€â”€â”€â”€ 5V BEC #3 GND â”€â”€â–º Servo Rail Power
         â”‚         â”‚               (if separate BEC    (for continuous servo
         â”‚         â”‚                for servo)          on AUX Ch6)
         â”‚         â”‚
         â”‚         â””â”€â”€â”€â”€ STAR GROUND POINT
         â”‚               All GND wires meet at ONE point on the PDB.
         â”‚               Do NOT daisy-chain grounds.
         â”‚
         â””â”€â”€â”€â”€ V+ (Battery Positive)
                  â”‚
                  â”œâ”€â”€â”€â”€ PDB V+ Rail â”€â”€â–º ESCs, BECs, etc.
                  â””â”€â”€â”€â”€ (NEVER connect directly to logic boards)


    âš ï¸  STAR TOPOLOGY IS ESSENTIAL
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    All ground returns come back to a SINGLE point on the PDB.
    This prevents ground loops where motor current flows through
    signal ground wires, injecting noise into the Pixhawk IMU
    or Jetson USB.
```

#### Specific Ground Connections

| Connection | Method | Wire Gauge | Notes |
|-----------|--------|------------|-------|
| Battery GND â†’ PDB | Direct solder | 12-14 AWG | Main return path |
| PDB â†’ Flight ESCs | Solder or XT30 | 14-16 AWG | 4Ã— motor ESCs |
| PDB â†’ EDF ESC | Solder or XT30 | 16 AWG | Sprayer fan (up to 20A) |
| PDB â†’ 5V BEC â†’ Pixhawk | Through power module | 18-20 AWG | Pixhawk power rail |
| PDB â†’ 5V BEC â†’ Jetson | Barrel jack or GPIO header | 18 AWG | Jetson 5V 4A supply |
| Pixhawk AUX GND â†’ ESC signal GND | Servo wire (included in ESC) | 22 AWG | PWM signal return |
| Jetson USB GND â†’ ESP32 GND | USB cable (automatic) | 24 AWG | USB spec includes GND |
| **CRITICAL: Pixhawk GND â†” Jetson GND** | **Shared through PDB** | â€” | Must be connected even if using separate BECs |

### 6.2 Optocoupler Requirement for ESC Signal

**Question: Do I need an optocoupler between Pixhawk AUX output and the EDF ESC signal wire?**

**Answer: No, not for a standard hobby ESC.**

| Factor | Analysis |
|--------|----------|
| **Signal levels** | Pixhawk AUX outputs 3.3V PWM. Standard hobby ESCs expect 3.3-5V PWM signal. Compatible. |
| **Ground sharing** | The ESC signal GND and Pixhawk AUX GND are the same rail (connected via the servo cable). No isolation needed when grounds are shared. |
| **When you WOULD need an optocoupler** | (1) If the ESC is on a separate battery (different ground potential). (2) If using an industrial motor controller with high-voltage feedback. (3) If extreme EMI isolation is needed (e.g., >50A motor controllers near sensitive analog sensors). |
| **Your case** | Single 4S LiPo, shared ground through PDB. Standard hobby ESC. No optocoupler needed. |

**However, consider these noise mitigation measures instead:**

1. **Twist the ESC signal wire with its ground wire** (or use shielded servo cable). This reduces inductively coupled noise from the motor phase wires.
2. **Add a 100nF ceramic capacitor** between the ESC signal pin and GND, as close to the ESC input as possible. This filters high-frequency noise.
3. **Keep the ESC signal wire physically separated** from the motor phase wires (the thick 3-wire cable from ESC to motor). Motor phase switching generates significant EMI at the PWM frequency Ã— pole count.
4. **If using a cheap ESC without built-in BEC**, the servo cable GND is the only connection â€” make sure it's robust (not a thin 26AWG wire dangling from a breadboard).

### 6.3 Power Distribution Architecture

```
    POWER DISTRIBUTION â€” 4S LiPo (14.8V nominal, 16.8V max)
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    4S LiPo (2200-5000mAh)
         â”‚
         â”œâ”€â”€â–º XT60 â†’ PDB (Power Distribution Board)
         â”‚         â”‚
         â”‚         â”œâ”€â”€â–º 4Ã— Flight ESC (14.8V direct) â”€â”€â–º 4Ã— Brushless Motors
         â”‚         â”‚    Total: ~40-80A peak (flight only)
         â”‚         â”‚
         â”‚         â”œâ”€â”€â–º 1Ã— Sprayer EDF ESC (14.8V direct) â”€â”€â–º Gold Motor EDF
         â”‚         â”‚    Peak: ~20-30A (consider 30A ESC)
         â”‚         â”‚
         â”‚         â”œâ”€â”€â–º BEC #1: 5V 3A (Mauch/Castle) â”€â”€â–º Pixhawk Power Module
         â”‚         â”‚    (Pixhawk + GPS + Matek 3901 + Telemetry)
         â”‚         â”‚    Load: ~500mA typical, 1A peak
         â”‚         â”‚
         â”‚         â”œâ”€â”€â–º BEC #2: 5V 5A â”€â”€â–º Jetson Nano (Barrel Jack 5V 4A)
         â”‚         â”‚    Load: 2-4A (MAXN mode + USB camera)
         â”‚         â”‚    âš ï¸ MUST be a high-quality switching BEC.
         â”‚         â”‚    Ripple > 100mV â†’ Jetson brownout/random crashes.
         â”‚         â”‚    Recommended: Pololu D36V50F5 (5V 5A step-down)
         â”‚         â”‚    or UBEC-type 5V/5A from Matek/Holybro.
         â”‚         â”‚
         â”‚         â””â”€â”€â–º BEC #3: 5V 3A â”€â”€â–º Pixhawk AUX Servo Rail
         â”‚              (Powers continuous servo on Ch6)
         â”‚              (ESC on Ch5 has its own BEC usually â€” check your ESC)
         â”‚              Load: 0.5-2.5A peak (servo stall)
         â”‚
         â”‚    âš ï¸ TOTAL SYSTEM POWER BUDGET (rough estimate):
         â”‚    â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
         â”‚    Flight motors:     60-100W (hover), 200W+ (maneuver)
         â”‚    Sprayer EDF:       50-100W (10-15A Ã— 5-7V after ESC loss)
         â”‚    Jetson Nano:       10-20W (5V Ã— 2-4A)
         â”‚    Pixhawk + sensors: 3-5W
         â”‚    Servo:             1-5W (intermittent)
         â”‚    â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
         â”‚    TOTAL:             ~124-230W typical
         â”‚    BATTERY:           4S 3000mAh = 44.4 Wh â†’ ~12-20 min flight
         â”‚                       4S 5000mAh = 74 Wh â†’ ~20-30 min flight
         â”‚                       (Sprayer adds ~15-25% to hover power draw)
```

### 6.4 EMI & Noise Mitigation

| Source | Affected System | Mitigation |
|--------|----------------|------------|
| Flight ESCs (PWM switching at 8-32kHz) | Pixhawk IMU, barometer | âœ… Already handled by Pixhawk vibration damping mount. Keep Pixhawk away from ESC wires. |
| EDF ESC (high-current switching) | Pixhawk compass, USB camera | Twist EDF motor wires. Add ferrite ring on EDF ESC power cable. Keep >10cm from Pixhawk compass. |
| Stepper motor (back-EMF spikes) | ESP32, Pixhawk | Add 100nF + 10ÂµF capacitors at ULN2003/A4988 power input. Flyback diodes (usually built into driver). |
| Continuous servo (brushed motor inside) | Pixhawk AUX signals | Add 100nF cap across servo power pins. Not a major concern â€” servo current is low. |
| Jetson Nano (switching regulator, USB) | Pixhawk TELEM serial | Use shielded cable for MAVLink UART. Or use USB (which has shielding built in). |
| 5V BEC switching noise | All 5V devices | Use quality BEC with <50mV ripple. Add LC filter (10ÂµH + 100ÂµF electrolytic) at BEC output if needed. |

---

## 7. RECOMMENDED FINAL ARCHITECTURE

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                                                                          â•‘
â•‘     RECOMMENDED ARCHITECTURE: OPTION A (FULL PIXHAWK) â€” FOR PROTOTYPE   â•‘
â•‘                                                                          â•‘
â•‘     With OPTION B (FULL ESP32) noted as the upgrade path for V2.        â•‘
â•‘                                                                          â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

### Why Option A for the Prototype

1. **Speed to demo.** You have a working Pixhawk, working MAVLink, and working spray logic node. Adding a second `DO_SET_SERVO` command is 2 lines of code. Buying a continuous servo and plugging it into AUX Ch6 is 30 minutes of work. This is the fastest path to a spraying drone.

2. **Dosing precision is not your bottleneck.** Right now, you don't know if the Venturi design works AT ALL. You need to validate airflow + powder entrainment. Whether the auger delivers 50mg or 60mg per spray is irrelevant if the powder clogs in the tube. A continuous servo is sufficient for proof-of-concept.

3. **Fewer failure modes.** The ESP32 adds a USB connection, a firmware image, a serial protocol, and a separate power domain â€” all for a single stepper motor. For a flying prototype where you're simultaneously debugging YOLO detection, visual servoing, and optical flow hover, minimizing variables is paramount.

4. **Synchronized timing.** Both actuators fire from the same Pixhawk servo cycle. The fan-before-feeder timing can be implemented cleanly in the ROS state machine:
   - State `SPRAY_FAN_START`: Send `DO_SET_SERVO(Ch5, 1800)` â†’ fan PWM.
   - State `SPRAY_FAN_WAIT`: Timer = 300ms (non-blocking ROS timer).
   - State `SPRAY_FEED_START`: Send `DO_SET_SERVO(Ch6, 1600)` â†’ servo turns auger.
   - State `SPRAY_ACTIVE`: Timer = 500ms (spray duration).
   - State `SPRAY_FEED_STOP`: Send `DO_SET_SERVO(Ch6, 1500)` â†’ servo stops.
   - State `SPRAY_FAN_COOLDOWN`: Timer = 200ms, then `DO_SET_SERVO(Ch5, 1000)` â†’ fan off.

### When to Switch to Option B

Upgrade to Option B (Full ESP32 Payload Island) when:
- The Venturi is proven and you need **repeatable dosing** (stepper micro-stepping).
- You want **closed-loop spray control** (e.g., hopper weight sensor, flow rate feedback).
- You're moving from prototype to **field trials** and need payload reliability isolation.
- You have a second team member who can own the ESP32 firmware independently.

### Final BOM Delta

| Item | Current Plan | Recommended (Option A) | Change |
|------|-------------|----------------------|--------|
| ESP32-S3 DevKitC | âœ… Keep | âŒ **Remove** | Save ~10g, $5 |
| ULN2003/A4988 Driver | âœ… Keep | âŒ **Remove** | Save ~5g, $2 |
| USB Cable (Jetsonâ†’ESP32) | âœ… Keep | âŒ **Remove** | Save ~8g |
| Stepper Motor (28BYJ-48 or NEMA 17) | âœ… Keep | âŒ **Remove** | Save 28-200g |
| Continuous Rotation Servo | â€” | âœ… **ADD** (FeeTech FS5103R) | Add ~38g, $4 |
| ESC | 20A | âš ï¸ **Verify or upgrade to 30A** | $3-5 more |
| Separate 5V BEC for Servo Rail | â€” | âœ… **ADD** (if AUX rail not powered) | ~5g, $5 |

**Net weight change:** Save **~5-170g** (depending on NEMA 17 vs 28BYJ-48) with the continuous servo swap.

---

## 8. UPDATED WIRING DIAGRAM

```
    RECOMMENDED WIRING â€” OPTION A (FULL PIXHAWK CONTROL)
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    4S LiPo â”€â”€â–º XT60 â”€â”€â–º PDB
                          â”‚
        â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
        â”‚                 â”‚                               â”‚
        â–¼                 â–¼                               â–¼
    4Ã— Flight ESC    5V BEC #1                       5V BEC #2
    (Motor 1-4)      (Pixhawk Power)                 (Jetson Nano)
        â”‚                 â”‚                               â”‚
        â”‚                 â–¼                               â–¼
        â”‚            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
        â”‚            â”‚  PIXHAWK    â”‚              â”‚  JETSON NANO â”‚
        â”‚            â”‚  2.4.8      â”‚              â”‚  4GB (B01)   â”‚
        â”‚            â”‚             â”‚              â”‚              â”‚
        â”‚            â”‚  TELEM2 â—„â”€â”€â”€â”¼â”€â”€ UART â”€â”€â”€â”€â”€â”€â”¤  UART TX/RX â”‚
        â”‚            â”‚             â”‚  (MAVLink    â”‚  (or USB)    â”‚
        â”‚            â”‚             â”‚   921600)    â”‚              â”‚
        â”‚            â”‚             â”‚              â”‚  USB â—„â”€â”€â”€â”€â”€â”€â”€â”¤â”€â”€ Jete 1080p
        â”‚            â”‚  MAIN 1-4 â”€â”€â”¼â”€â”€â–º ESCs     â”‚     Webcam   â”‚
        â”‚            â”‚             â”‚              â”‚              â”‚
        â”‚            â”‚  AUX Ch5 â”€â”€â”€â”¼â”€â”€â–º 20-30A ESC â”€â”€â–º EDF Fan  â”‚
        â”‚            â”‚  (PWM)      â”‚   (Signal only.            â”‚
        â”‚            â”‚             â”‚    ESC power from PDB)     â”‚
        â”‚            â”‚             â”‚                             â”‚
        â”‚            â”‚  AUX Ch6 â”€â”€â”€â”¼â”€â”€â–º Continuous Servo â”€â”€â–º Auger
        â”‚            â”‚  (PWM)      â”‚   (FeeTech FS5103R)       â”‚
        â”‚            â”‚             â”‚   (Power from 5V BEC #3    â”‚
        â”‚            â”‚             â”‚    or AUX rail BEC)        â”‚
        â”‚            â”‚             â”‚                             â”‚
        â”‚            â”‚  I2C â—„â”€â”€â”€â”€â”€â”€â”¼â”€â”€ Matek 3901-L0X          â”‚
        â”‚            â”‚             â”‚   (Optical Flow +          â”‚
        â”‚            â”‚             â”‚    Rangefinder)            â”‚
        â”‚            â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                             â”‚
        â”‚                                                        â”‚
        â””â”€â”€â”€â”€ GND â”€â”€ ALL GROUNDS MEET AT PDB (STAR TOPOLOGY) â”€â”€â”€â”˜


    WIRE CONNECTIONS DETAIL:
    â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    AUX Ch5 â†’ ESC:
      Signal (white/orange): Pixhawk AUX5 signal pin â†’ ESC PWM input
      GND (brown/black):     Pixhawk AUX5 GND pin â†’ ESC GND
      (No 5V from ESC BEC to Pixhawk if using separate power module)

    AUX Ch6 â†’ Servo:
      Signal (orange):       Pixhawk AUX6 signal pin â†’ Servo signal wire
      VCC (red):             External 5V BEC â†’ Servo VCC (NOT from Pixhawk regulator)
      GND (brown):           Pixhawk AUX6 GND â†’ Servo GND â†’ BEC GND
```

---

## 9. IMPLEMENTATION ACTION ITEMS

### Immediate (This Week)

| # | Task | Priority | Time Est. |
|---|------|----------|-----------|
| 1 | **Bench-test EDF motor current draw** with watt meter at 4S. Record continuous current at intended operating PWM. Decide 20A vs 30A ESC. | ðŸ”´ Critical | 1 hour |
| 2 | **Buy a continuous rotation servo** (FeeTech FS5103R or equivalent). Test that it spins the auger at 30-60 RPM with adequate torque for your powder. | ðŸ”´ Critical | 1-2 days (shipping) |
| 3 | **Configure Pixhawk AUX channels.** Set `SERVO9_FUNCTION=0` (Manual), `SERVO10_FUNCTION=0` (Manual) to enable AUX5 and AUX6 as pass-through servo outputs. Note: AUX1=SERVO9, AUX2=SERVO10, ... AUX5=SERVO13, AUX6=SERVO14 in ArduPilot. | ðŸŸ¡ High | 30 min |
| 4 | **Update `ardupilot_params.param`** with new servo parameters. Remove `RELAY_PIN=54` (no longer using relay). Add `SERVO13_FUNCTION=0`, `SERVO13_MIN=1000`, `SERVO13_MAX=2000`, `SERVO13_TRIM=1000` (fan off default). Add `SERVO14_FUNCTION=0`, `SERVO14_MIN=1000`, `SERVO14_MAX=2000`, `SERVO14_TRIM=1500` (servo stop default). | ðŸŸ¡ High | 15 min |
| 5 | **Update `spray_logic_node.py`** to remove ESP32 serial code and replace with MAVLink `DO_SET_SERVO` commands via `mavros`. | ðŸŸ¡ High | 2-3 hours |
| 6 | **Bench-test the Venturi** with EDF + auger + powder. Confirm powder entrainment before mounting on drone. | ðŸ”´ Critical | 2-4 hours |
| 7 | **Buy/build a separate 5V BEC** for the Pixhawk AUX servo rail (if not already powered by an ESC BEC). | ðŸŸ¡ High | 1-2 days |

### ArduPilot Parameter Updates

```
# â”€â”€â”€ NEW: Sprayer Actuator Channels â”€â”€â”€
# AUX5 (SERVO13) â†’ EDF Fan ESC
SERVO13_FUNCTION,0         # Pass-through (manual control via MAVLink)
SERVO13_MIN,1000           # ESC minimum (motor off)
SERVO13_MAX,2000           # ESC maximum (full speed)
SERVO13_TRIM,1000          # Default: motor OFF (safety)
SERVO13_REVERSED,0

# AUX6 (SERVO14) â†’ Continuous Rotation Servo (Auger)
SERVO14_FUNCTION,0         # Pass-through (manual control via MAVLink)
SERVO14_MIN,1000           # Servo full CW
SERVO14_MAX,2000           # Servo full CCW
SERVO14_TRIM,1500          # Default: servo STOP (center = stop for cont. servo)
SERVO14_REVERSED,0

# REMOVE: Old Relay Configuration
# RELAY_PIN,54             # â† DELETE THIS (no longer using relay)
# RELAY_DEFAULT,0          # â† DELETE THIS
```

### Updated ROS Spray Logic (Conceptual)

```python
# In spray_logic_node.py â€” Replace serial ESP32 with MAVLink servo commands
# Using mavros service calls:

import rospy
from mavros_msgs.srv import CommandLong
from mavros_msgs.msg import OverrideRCIn

class SprayLogicNode:
    def __init__(self):
        # ... existing init code ...
        
        # REMOVE: self.ser = serial.Serial(...)
        # ADD: MAVLink servo control via mavros
        rospy.wait_for_service('/mavros/cmd/command')
        self.cmd_srv = rospy.ServiceProxy('/mavros/cmd/command', CommandLong)
    
    def set_servo(self, channel, pwm):
        """
        Set a Pixhawk servo output via MAVLink DO_SET_SERVO.
        channel: 13 for AUX5 (fan), 14 for AUX6 (feeder)
        pwm: 1000-2000 microseconds
        """
        try:
            self.cmd_srv(
                broadcast=False,
                command=183,          # MAV_CMD_DO_SET_SERVO
                param1=channel,       # Servo channel number
                param2=pwm,           # PWM value
                param3=0, param4=0, param5=0, param6=0, param7=0
            )
        except rospy.ServiceException as e:
            rospy.logerr(f"Servo command failed: {e}")

    def _do_spray(self):
        """Execute spray sequence with timed fan-before-feeder."""
        self.spray_count += 1
        rospy.loginfo(f"ðŸ’¦ SPRAY #{self.spray_count} â€” Fan Spool Up")
        
        # Phase 1: Start EDF fan (soft-start ramp)
        self.set_servo(13, 1400)    # Low speed
        rospy.Timer(rospy.Duration(0.1), lambda e: self.set_servo(13, 1600), oneshot=True)
        rospy.Timer(rospy.Duration(0.2), lambda e: self.set_servo(13, 1800), oneshot=True)
        
        # Phase 2: Start feeder after 300ms (airflow established)
        rospy.Timer(rospy.Duration(0.3), lambda e: self._start_feed(), oneshot=True)
    
    def _start_feed(self):
        rospy.loginfo("ðŸ’¨ Airflow ready â€” Starting powder feed")
        self.set_servo(14, 1650)    # Servo CW at moderate speed
    
    def _stop_spray(self):
        rospy.loginfo("ðŸ›‘ SPRAY OFF")
        self.set_servo(14, 1500)    # Stop feeder first
        rospy.Timer(rospy.Duration(0.2), lambda e: self.set_servo(13, 1000), oneshot=True)  # Fan off after 200ms
```

---

## 10. RISK REGISTER (Updated for Option A)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Continuous servo torque insufficient for auger | Low | High (spray fails) | Bench test before mounting. If weak, upgrade to MG996R (11 kgÂ·cm). |
| Powder clogs in inner tube | High | High (spray fails) | Add vibration motor. Use desiccant. Pre-sieve pollen. Test 4-6mm ID tubes. |
| EDF inrush current trips ESC | Medium | Medium (spray aborted) | Soft-start PWM ramp (1400â†’1600â†’1800 over 200ms). Upgrade to 30A ESC. |
| Servo back-drives auger (gravity) | Low | Low (small powder leak) | Apply slight PWM offset (1505Âµs instead of 1500Âµs) when "stopped". |
| Pixhawk AUX rail power insufficient | Medium | Medium (servo stutters) | Use external 5V BEC on AUX rail. Do NOT rely on Pixhawk internal regulator. |
| MAVLink command dropped under load | Low | Medium (spray misfires) | Send `DO_SET_SERVO` commands 3Ã— in rapid succession (idempotent). Monitor `mavros` diagnostics. |
| EDF vibration affects Pixhawk IMU | Medium | High (flight instability) | Vibration-isolate Pixhawk (foam/gel mount). Mount EDF as far from Pixhawk as possible. Monitor `VIBE` messages in logs. |

---

## 11. CONCLUSION

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                                                                      â•‘
â•‘  YOUR DRONE NEEDS TO SPRAY POLLEN, NOT WIN AN ARCHITECTURE AWARD.   â•‘
â•‘                                                                      â•‘
â•‘  For the prototype:                                                  â•‘
â•‘    â†’ Use Option A (Full Pixhawk).                                   â•‘
â•‘    â†’ Buy a $4 continuous servo.                                     â•‘
â•‘    â†’ Delete the ESP32 from your BOM.                                â•‘
â•‘    â†’ Focus on the REAL hard problem: "Does the Venturi work?"       â•‘
â•‘                                                                      â•‘
â•‘  For production V2:                                                  â•‘
â•‘    â†’ Upgrade to Option B (ESP32 Payload Island).                    â•‘
â•‘    â†’ Add stepper for precise dosing.                                â•‘
â•‘    â†’ Add closed-loop feedback (hopper weight, flow sensor).         â•‘
â•‘    â†’ Design a custom PCB to replace the DevKitC.                    â•‘
â•‘                                                                      â•‘
â•‘  The fastest path to "drone sprays pollen on a flower" is:          â•‘
â•‘    Pixhawk AUX5 â†’ ESC â†’ Fan.                                       â•‘
â•‘    Pixhawk AUX6 â†’ Servo â†’ Auger.                                   â•‘
â•‘    Jetson â†’ MAVLink â†’ DO_SET_SERVO Ã— 2.                            â•‘
â•‘    Done.                                                             â•‘
â•‘                                                                      â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

---

*Document Version: 1.0 | Review Date: 2026-02-17 | Reviewer: Senior Mechatronics Systems Architect | Classification: Internal Engineering*
*Next Review: After EDF bench test and Venturi powder validation*

---

> **Post-Review Update (2025-02-17):** Option A (Full Pixhawk Control) has been adopted.
> All code, configs, and documentation have been updated accordingly.
> ESP32 and relay module removed from BOM. See updated files:
> - `config/ardupilot_params.param` â€” SERVO13/14 configured, RELAY removed
> - `ros_nodes/scripts/spray_logic_node.py` â€” Rewritten for mavros DO_SET_SERVO
> - `ros_nodes/launch/demo.launch` â€” mavros included, ESP32 serial removed
> - `diagrams/system_architecture.mmd` â€” AUX5/AUX6 path shown
> - `diagrams/state_machine.mmd` â€” Spray sub-states added
> - `MASTER_EXECUTION_GUIDE.md` â€” Day 3+ rewritten for Pixhawk servo setup
> - `ACTION_PLAN_SURVIVAL.md` â€” Architecture diagram updated
> - `esp32/sprayer_controller/sprayer_controller.ino` â€” Marked DEPRECATED

