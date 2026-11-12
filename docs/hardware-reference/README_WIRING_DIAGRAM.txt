# Drone Sawit Hardware Bill of Materials (BOM) & Wiring Reference

Below is a comprehensive table of all hardware components required to implement the Drone Sawit project, including example models/specs, functions, estimated costs, and wiring diagram references. This covers both essential and recommended optional hardware for robust, field-ready operation.

| #  | Component                | Example Model/Spec                | Function / Notes                                      | Est. Cost (USD) | Wiring Diagram Reference        |
|----|--------------------------|-----------------------------------|-------------------------------------------------------|-----------------|-------------------------------|
| 1  | Flight Controller        | Pixhawk 4 (PX4)                   | Autonomous flight, telemetry, safety                  | $180            | FC to ESCs, GPS, Telemetry     |
| 2  | Companion Computer       | NVIDIA Jetson Nano (4GB)          | AI inference, mission logic, GPS, logging, UI         | $130            | Jetson to Pixhawk, UART, USB   |
| 3  | Sprayer Controller       | Arduino Uno / STM32F103C8T6       | Spray actuation, feedback, safety monitoring          | $10–$20         | Arduino to Jetson, PWM, relay  |
| 4  | Ground Control Station   | Laptop/Tablet w/ QGroundControl   | Mission upload, telemetry, manual override            | $500+           | GCS to Telemetry Radio         |
| 5  | GNSS Module              | Ublox NEO-M8N/UM982 (RTK)         | Navigation, geotagging, RTK for high accuracy         | $30–$250        | GPS to Pixhawk, Jetson (UART)  |
| 6  | Telemetry Radio          | SiK 915MHz/433MHz, LTE, WiFi      | Drone ↔ GCS data link                                 | $30–$100        | Pixhawk/Jetson to GCS          |
| 7  | Sprayer Mechanism        | PWM-controlled pump & solenoid    | Precise chemical spraying, controlled by Arduino      | $50–$150        | Arduino PWM/relay to pump      |
| 8  | LiPo Battery             | 4S/6S, 10,000mAh+                 | Main power for drone, electronics                     | $80–$200        | Main power distribution        |
| 9  | ESCs & Motors            | 4× 40A ESC + 4× 3508 700KV BLDC   | Propulsion, maneuvering                               | $200–$400       | ESCs to motors, FC             |
| 10 | Frame & Arms             | Tarot 650/680mm Carbon            | Structural support                                    | $120–$200       | Mount all modules              |
| 11 | Camera (optional)        | Raspberry Pi Cam, USB/CSI         | Visual feedback, AI detection                         | $20–$50         | Jetson CSI/USB                 |
| 12 | SD Card                  | 32GB Class 10                     | Data logging, mission files, AI storage               | $10             | Jetson/FC/Arduino SD slot      |
| 13 | Cables & Connectors      | JST, Dupont, XT60, etc.           | Wiring and connectivity                               | $30             | All modules                    |
| 14 | Misc Sensors             | IMU, Barometer, Magnetometer      | Flight stabilization, orientation, altitude           | $10–$50         | FC sensor ports                 |
| 15 | Safety Switch            | Hardware kill switch               | Emergency stop for motors/sprayer                     | $5              | FC/Power to switch             |
| 16 | Buzzer/LEDs              | 5V Buzzer, RGB LEDs               | Status indication                                     | $5              | FC/Arduino GPIO                |
| 17 | Mounts/Brackets          | 3D printed/aluminum                | Secure mounting of electronics/payload                | $10–$50         | All modules                    |

**Optional/Advanced Components**

| #  | Component                | Example Model/Spec                | Function / Notes                                      | Est. Cost (USD) | Wiring Diagram Reference        |
|----|--------------------------|-----------------------------------|-------------------------------------------------------|-----------------|-------------------------------|
| 18 | RTK GNSS                 | UM982 Dual Antenna                | Centimeter-level accuracy, heading                    | $200–$400       | GPS to Pixhawk/Jetson          |
| 19 | Obstacle Avoidance       | TFmini LiDAR, Ultrasonic, Benewake CE30-C, LightWare SF40/C, TF-Luna array | Obstacle detection, safety, terrain following, advanced mapping | $20–$1,700      | FC/Jetson UART/I2C/Ethernet    |
| 19a | TF-Mini Plus LiDAR (Front) | Benewake TF-Mini Plus                | Frontal obstacle detection, long range                        | $11–$25         | Jetson UART (front)            |
| 19b | TF-Luna LiDAR (Left)       | Benewake TF-Luna                     | Left-side obstacle detection, short range                     | $5–$9           | Jetson UART (left)             |
| 19c | TF-Luna LiDAR (Right)      | Benewake TF-Luna                     | Right-side obstacle detection, short range                    | $5–$9           | Jetson UART (right)            |
| 19d | TF-Luna LiDAR (Rear)       | Benewake TF-Luna                     | Rear obstacle detection, short range                          | $5–$9           | Jetson UART (rear)             |
| 19e | TF-Luna LiDAR (Down)       | Benewake TF-Luna                     | Downward/altitude detection, landing assist                    | $5–$9           | Jetson UART (down)             |
| 19f | UART Multiplexer/Expander  | MAX14830, Jetson Nano UART HAT       | Multi-sensor UART expansion, wiring simplification             | $10–$30         | Jetson UART breakout           |
| 19g | Sensor Wiring Harness      | Custom JST/GH/DF13 cables            | Clean, secure sensor wiring                                    | $5–$10          | All sensors                    |

### Obstacle Avoidance Sensor Configurations

Drone Sawit supports the following recommended sensor configurations:

**1. Advanced LiDAR (Single Sensor)**
- **Benewake CE30-C**: 132°×9° FOV, 10–20m range, robust solid-state, connects via UART/Ethernet to Jetson. Mount forward for wide frontal coverage.
- **LightWare SF40/C**: 360°×1.5° FOV, up to 100m range, 2D spinning, connects via UART/USB. Mount top/center for full perimeter scan.

**2. Multi-Sensor (Quasi-360°) Array**
- **TF-Mini Plus (Front)**: 0–15 m, long-range frontal detection
- **TF-Luna (Left/Right/Rear/Down)**: ~0.2–5 m, side/rear/altitude awareness
- **Layout:**
  - Nose/front frame: TF-Mini Plus
  - Left arm: TF-Luna
  - Right arm: TF-Luna
  - Tail: TF-Luna
  - Center bottom: TF-Luna
- **Total weight:** ~31g (sensors) + wiring (<50g)
- **Integration:** Use UART multiplexer (e.g., MAX14830) or Jetson Nano UART expansion. Poll sensors in loop or ROS2 node. Sync to Pixhawk via MAVLink DISTANCE_SENSOR.

**3. Optional 360° Upgrades**
- Replace front TF-Mini Plus with RPLIDAR A1 for full 360° scan (adds ~170g)
- Use 8× TF-Luna in octagonal layout for maximum redundancy

**Wiring & Integration Notes:**
- All sensors require 5V and GND; UART TX/RX to Jetson or multiplexer
- For advanced LiDAR: Ethernet or UART to Jetson, ensure proper power supply
- Calibrate each sensor’s pose in UAV frame for accurate spatial mapping
- Modular—mix and match based on mission, payload, and budget

**See main README for diagrams and detailed recommendations.**
| 20 | Environmental Sensors    | Wind, Temp, Humidity              | Weather monitoring, AI input                          | $10–$50         | Jetson/Arduino I2C/SPI         |
| 21 | Power Distribution Board | MATEK FCHUB-6S                    | Voltage/current monitoring, safe power routing        | $30–$60         | Battery to all modules         |

---

## Wiring Diagram References

- **FC to ESCs/Motors:** PWM signal wires from Pixhawk to ESCs, power from battery.
- **Pixhawk to Jetson:** UART/USB for MAVLink telemetry and mission sync.
- **Jetson to Arduino:** UART/USB for spray command/control.
- **Pixhawk to GNSS:** Dedicated GPS port (UART).
- **Pixhawk/Jetson to Telemetry:** Telemetry radio connected via UART/USB.
- **Arduino to Pump/Solenoid:** PWM or relay driver circuit.
- **Power:** All electronics powered via main LiPo battery, with voltage regulators for 5V/3.3V as needed.
- **Safety Switch:** Inline with main power or signal lines for emergency cutoff.

---

**Estimated Total Cost:**
- Basic System: $900–$1,800 (varies by component quality and optional features)
- With RTK/Advanced Sensors: $1,200–$2,400+

For a schematic diagram, pinout, or CSV version for procurement, please request as needed.

---

Drone Sawit Wiring Quick Reference

1. Jetson Nano USB port (ttyUSB0) <-> Arduino Nano/Uno USB
2. Jetson Nano USB port (ttyACM0) <-> Pixhawk TELEM2
3. Arduino PWM pin 9 -> Sprayer relay/valve
4. Arduino analog pin A0 -> Flow sensor output
5. Arduino PWM pin 10 -> Gimbal servo (optional)
6. Arduino digital pin 12 -> Error LED (optional)
7. Power:
   - Jetson: 5V/4A or 12V/2A supply
   - Arduino: via USB or BEC (5V)
   - Pixhawk: via battery or power module

**Double check all grounds are connected!**

For full schematic, see project documentation or contact engineering.
