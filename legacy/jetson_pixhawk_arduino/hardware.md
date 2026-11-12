# 🛩️ Drone Sawit – Smart Palm Pollination Drone

A modular **agricultural drone** designed for **palm oil pollination automation** and environmental sensing, integrating **Jetson Orin Nano AI**, **Pixhawk flight controller**, and **multi-LiDAR awareness**.

---

## 📋 Bill of Materials (BOM)

| No. | Component | Description | Qty | Unit Price (IDR) | Total (IDR) |
|-----|------------|-------------|-----|------------------|--------------|
| 1 | **Frame** | Tarot Iron Man 680 Pro Hexacopter | 1 | 1,850,000 | 1,850,000 |
| 2 | **Motors** | A2212 1000KV Brushless Motor | 6 | 120,000 | 720,000 |
| 3 | **ESCs** | 30A Brushless ESC | 6 | 90,000 | 540,000 |
| 4 | **Propellers** | 1045 Propeller Pair (CW + CCW) | 3 | 50,000 | 150,000 |
| 5 | **Flight Controller** | Pixhawk 2.4.8 with GPS | 1 | 2,500,000 | 2,500,000 |
| 6 | **Battery** | 4S 10000mAh 25C LiPo | 1 | 2,200,000 | 2,200,000 |
| 7 | **Power Distribution** | PDB with XT60 / XT90 | 1 | 150,000 | 150,000 |
| 8 | **Onboard Computer** | Jetson Orin Nano 4GB Dev Board Suite | 1 | 6,000,000 | 6,000,000 |
| 9 | **Telemetry Module** | 915 MHz 500mW MAVLink | 1 | 750,000 | 750,000 |
| 10 | **Primary LiDAR** | Benewake CE30-C Solid-State LiDAR | 1 | 7,750,000 | 7,750,000 |
| 10a | **Auxiliary LiDARs** | Benewake TF-Luna (left, right, rear, downward) | 4 | 500,000 | 2,000,000 |
| 11 | **Sprayer System** | Custom sprayer + brackets | 1 | 1,500,000 | 1,500,000 |
| 12 | **Mounting Materials** | Cables, dampers, brackets | 1 | 300,000 | 300,000 |
| 13 | **Charger** | 4S-compatible Smart Charger | 1 | 1,000,000 | 1,000,000 |
| 14 | **Remote Control** | FlySky i6X + Receiver (6CH) | 1 | 1,100,000 | 1,100,000 |
| 15 | **Shipping + Contingency** | Spare props, unforeseen parts | 1 | 1,500,000 | 1,500,000 |

**💰 Total Estimated Cost:** ~ **IDR 27,035,000**

---

## ⚙️ Drone Specifications

- **Flight Time:** ~18–22 minutes  
- **Payload Capacity:** ~1.2–1.5 kg  
- **Max Takeoff Weight:** ~2.5 kg  
- **Motor Type:** 2312 Series Brushless (960–1000KV, ~850–950g thrust)  
- **Prop Size:** 9450–1045  
- **ESC:** 20A–30A BLHeli or equivalent  
- **Battery:** 4S 10000mAh LiPo (25C)  
- **Onboard AI:** Jetson Orin Nano (7–15W power draw)  
- **Sensors:** Benewake CE30-C + 4× TF-Luna  

---

## 🔗 Sourcing Links

| Component | Example Source |
|------------|----------------|
| Frame | [Shopee - Tarot Iron Man 650 Frame](#) |
| Motors | [Tokopedia - DJI 2312 Motor](#) |
| ESCs | [Lazada - 20A ESC](#) |
| Propellers | [JSumo - 1045 Prop Set](#) |
| Flight Controller | [Rees52 - Pixhawk 2.4.8](#) |
| Battery | [HobbyKing - 4S 10000mAh LiPo](#) |
| Onboard Computer | [AliExpress - Jetson Orin Nano 4GB](#) |
| LiDARs | [eBay - Benewake TF-Luna](#) |
| Remote Controller | [Blibli - FlySky i6X](#) |

---

## 🧱 Integration Guide

### 1️⃣ Mechanical Assembly

1. Assemble Tarot 680 frame; lock foldable arms.  
2. Mount A2212 motors (CW/CCW correctly).  
3. Secure ESCs on arms or frame interior.  
4. Mount Pixhawk with vibration dampers.  
5. Place Jetson Orin Nano in protective enclosure.  
6. Mount LiDAR (front) and sprayer (under CG).  
7. Route all cables neatly and label connections.  
8. Attach propellers, confirm rotation direction.

---

### 2️⃣ Electrical Wiring

1. ESC signal → Pixhawk MAIN OUT (1–6).  
2. ESC power → Power Distribution Board.  
3. Battery → PDB (check polarity).  
4. Jetson Orin Nano → 5V/4A BEC regulator.  
5. Pixhawk Power Module → Battery → Pixhawk power port.  
6. GPS/Compass → Pixhawk GPS1 port.  
7. LiDAR → Jetson (UART/I2C) or Pixhawk directly.  
8. Telemetry radio → Pixhawk TELEM1.  
9. Jetson ↔ Pixhawk via UART (for MAVLink).

---

### 3️⃣ Software & Configuration

1. Flash **ArduCopter** or **PX4** to Pixhawk.  
2. Calibrate **accelerometer**, **compass**, **RC**, **ESC**, and **failsafe**.  
3. Set **motor order (1–6)** and verify spin directions.  
4. Configure flight modes: *Stabilize*, *AltHold*, *Loiter*, *Auto*.  
5. Install **JetPack**, **ROS2**, **MAVROS**, **OpenCV**, **YOLOv8** on Jetson.  
6. Establish MAVLink connection between Jetson ↔ Pixhawk.  
7. Connect sprayer control via **PWM relay** or **GPIO trigger**.

---

### 4️⃣ Power & Load Testing

1. Test power-up (props **off**).  
2. Verify Pixhawk LED + Jetson boot sequence.  
3. Connect Mission Planner → GPS, battery, sensor readouts.  
4. Test motor arming and throttle response.  
5. Perform hover test in Stabilize/Loiter.  
6. Validate flight time and current draw (~20 min goal).

---

### 5️⃣ AI Inference Pipeline (Jetson Orin Nano)

1. Mount CSI or USB camera on front.  
2. Install and run **YOLOv8 / custom model** for flower detection.  
3. Trigger sprayer via GPIO if detection confidence exceeds threshold.  
4. Log detections + timestamps (optional).  
5. Optional: Stream annotated video to Ground Control Station (GCS).

---

### 6️⃣ Safety Checklist

- ✅ Calibrate compass far from magnetic interference.  
- ✅ Use thread locker on screws.  
- ✅ Double-check battery polarity.  
- ✅ Enable failsafe (low battery, RC loss).  
- ✅ Use prop guards in dense plantation environments.  

---

## 🧩 Pixhawk Pin Assignment

| Function | Port / Pin | Direction | Device | Notes |
|-----------|-------------|------------|----------|--------|
| Motor 1–6 PWM | MAIN OUT 1–6 | Output | ESCs | Hexacopter (X) config |
| LiDAR Serial | SERIAL4 | I/O | TF-Luna | 115200 baud |
| Telemetry | TELEM1 | Bi-dir | Jetson | MAVLink (57600–921600 baud) |
| GPS+Compass | GPS1 | Input | GPS Module | I2C + Serial |
| Sprayer PWM | AUX OUT 1 | Output | Relay/Arduino | `SERVO9_FUNCTION = 58` |
| Power | POWER | Input | Power Module | Voltage/current monitor |
| Buzzer | BUZZER | Output | Optional | Prearm alerts |
| Safety Switch | SWITCH | Input | Optional | Firmware safety checks |

---

## 🔌 Jetson ↔ Pixhawk Wiring

| Jetson Pin | Pixhawk Port | Description |
|-------------|--------------|--------------|
| TX (/dev/ttyTHS1) | TELEM1 RX | MAVLink TX |
| RX (/dev/ttyTHS1) | TELEM1 TX | MAVLink RX |
| GND | GND | Common Ground |

---

## ⚙️ Example Pixhawk Parameters

```ini
SERIAL1_BAUD    = 921600         # TELEM1 (Jetson)
SERIAL1_PROTOCOL = 1             # MAVLink
SERIAL4_BAUD    = 115200         # TF-Luna
SERIAL4_PROTOCOL = 5             # Rangefinder
SERVO9_FUNCTION = 58             # Sprayer PWM Trigger
