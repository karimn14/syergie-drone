# Autonomous Pollination Drone — Architectural Review
### Date: February 9, 2026
### Author: Senior Robotics Systems Architect Review
### Hardware: Jetson Nano 4GB (B01) | Pixhawk (ArduPilot) | Jete FHD 1080p USB Cam

---

## 1. EXECUTIVE SUMMARY

**Stop overengineering the localization problem and start shipping a working spray cycle.** Your drone doesn't need to know *where it is in the world*; it only needs to know *where the flower is relative to itself* and hold position long enough to spray. The correct architecture is: a **$25 Matek 3901-L0X Optical Flow + LiDAR module** feeding Pixhawk for rock-solid GPS-denied hover, combined with a **lightweight YOLO detection + PID visual servoing loop** on the Jetson Nano commanding Pixhawk velocity offsets via MAVLink. That's it. No SLAM. No DIY optical flow. No dual-purpose camera gymnastics.

---

## 2. CRITICAL ANALYSIS — WHY YOUR IDEAS WILL LIKELY FAIL

### 2.1 Jetson Nano 4GB — The Hard Reality (Know Your Ceiling)

Before analyzing anything, let's pin down the actual compute budget:

| Resource            | Specification                  | Practical Limit                              |
|---------------------|--------------------------------|----------------------------------------------|
| GPU                 | 128-core Maxwell               | ~472 GFLOPS FP16. **No Tensor Cores.**       |
| CPU                 | 4x ARM A57 @ 1.43 GHz         | Comparable to a 2015 mid-range phone SoC.    |
| RAM                 | 4 GB LPDDR4 (shared CPU/GPU)  | OS + ROS + desktop = ~1.5 GB gone on boot.   |
| Available RAM       | ~2.0–2.5 GB                   | For ALL your processes combined.             |
| USB Bandwidth       | USB 3.0 shared bus             | 1080p@30fps ≈ 60 MB/s raw. Compression helps.|
| Power               | 5W / 10W (MAXN) modes         | Thermals throttle sustained GPU loads.       |

**The cardinal rule:** On a Jetson Nano, you get to do **ONE computationally hard thing well**, or **two easy things concurrently**. You do NOT get to do two hard things simultaneously without one of them becoming dangerously unreliable.

---

### 2.2 IDEA A: ESP32-S3 Cam as DIY Optical Flow Sensor → ❌ REJECT

**Concept:** Use an ESP32-S3-CAM module running optical flow algorithms (Lucas-Kanade or block matching) and output `OPTICAL_FLOW` MAVLink messages to Pixhawk.

**Why it will fail:**

| Factor               | Reality                                                                                                |
|-----------------------|--------------------------------------------------------------------------------------------------------|
| **Processing Power**  | ESP32-S3 has a dual-core 240 MHz Xtensa LX7. Optical flow on even 160x120 grayscale is ~15-20 FPS max with heavy optimization. PX4Flow (the gold standard DIY flow sensor) uses an STM32F4 at 168 MHz with a **dedicated camera interface (DCMI)** and hand-optimized assembly. You'd be reimplementing that from scratch. |
| **Camera Quality**    | The OV2640 on most ESP32-CAM boards has terrible motion blur, fixed focus, and a rolling shutter. Optical flow needs **low blur, high frame rate, global shutter ideally**. Your flow vectors will be noisy garbage under vibration. |
| **Lens/FOV**          | Optical flow for hover requires a **downward-facing, wide-angle lens** (>100° FOV). ESP32-CAM modules ship with ~65-75° lenses. You'd need to swap the lens, which is fiddly M12 work on a non-standard mount. |
| **Integration**       | Pixhawk expects `OPTICAL_FLOW_RAD` messages at 10+ Hz with gyro-compensated flow. You need to fuse an external gyro (BMI088 or ICM-42688) on the ESP32, sync timestamps, and calibrate. This is 3-6 months of embedded development for one sensor. |
| **Reliability**       | A DIY sensor with no formal calibration pipeline, no environmental testing, and no community support is an **unacceptable single point of failure** on a flying machine near crops. |
| **Cost Comparison**   | ESP32-S3-CAM (~$8) + IMU (~$5) + custom PCB + lens + 200 hours of firmware dev time vs. **Matek 3901-L0X ($22-28)**: a proven, plug-and-play module with PMW3901 optical flow + VL53L0X/VL53L1X rangefinder, already supported natively by ArduPilot. |

**Verdict:** This is a **science fair project, not an industrial solution.** You'd spend months building something worse than a $25 off-the-shelf module. Engineering time has a cost. Allocate it to the actual hard problem (visual servoing + spray control), not to reinventing a commodity sensor.

---

### 2.3 IDEA B: Single Camera for YOLO + Visual Odometry Simultaneously → ⚠️ DANGEROUS

**Concept:** Use the front-facing Jete USB webcam on the Jetson Nano to run both YOLOv8-nano (object detection) and some form of visual odometry (VO) in parallel.

**Why it will likely degrade to the point of being unsafe:**

| Factor                    | Reality                                                                                              |
|---------------------------|------------------------------------------------------------------------------------------------------|
| **GPU Contention**        | YOLOv8-nano (TensorRT FP16) on Jetson Nano runs at ~15-25 FPS on 640x480. That alone consumes 60-80% of the Maxwell GPU. Adding ANY VO pipeline that touches the GPU (feature extraction, descriptor matching) will tank both to <10 FPS. Below 10 FPS, your visual servoing becomes a drunk person trying to catch a ball — oscillatory, late, dangerous. |
| **CPU Contention**        | If you run VO on CPU only (to avoid GPU fights), you need feature extraction (ORB/FAST), matching, and pose estimation. On ARM A57, this is ~50-80ms per frame for even a lightweight VO like `libviso2`. Your 4 CPU cores are already shared between ROS, MAVLink, camera driver, OS, and the YOLO pre/post-processing. |
| **RAM Pressure**          | YOLO model in TensorRT: ~200-400 MB GPU memory. VO feature maps + keyframes: ~300-500 MB. ROS + MAVLink + OS overhead: ~1.5 GB. **Total: 2.0-2.4 GB out of 4 GB shared.** You're one memory spike from OOM-killer nuking your detection node mid-flight. |
| **Camera Orientation**    | **Critical flaw:** Your camera is **front-facing** for flower detection. Optical flow / VO for hover stabilization needs a **downward-facing camera** looking at the ground. A front-facing camera pointed at a flower 1m away gives you ZERO information about lateral drift when the drone is hovering. The parallax geometry simply doesn't work for position hold. |
| **Single Point of Failure** | If the camera feed drops, glitches, or gets occluded by pollen/debris, you lose BOTH your targeting AND your stabilization simultaneously. That's a crash. |

**Verdict:** The camera orientation alone kills this idea for position hold. Even if you hypothetically solved that, the compute budget makes dual-pipeline unreliable. **Do NOT use the same sensor for two safety-critical functions on a system this resource-constrained.**

---

### 2.4 IDEA C: Full V-SLAM (ORB-SLAM3 / RTAB-Map) on Jetson Nano → ❌ REJECT (Overkill + Underpowered)

**Concept:** Run a full visual SLAM system to build a map of the plantation and localize within it.

**Why it's the wrong tool for the job:**

| Factor                     | Reality                                                                                              |
|----------------------------|------------------------------------------------------------------------------------------------------|
| **ORB-SLAM3 on Nano**     | Monocular ORB-SLAM3 on Jetson Nano: **3-8 FPS** depending on scene complexity. With a USB webcam (no hardware sync, rolling shutter), expect the lower end. That's not real-time for flight control. It *will* lose tracking during fast maneuvers and take seconds to relocalize. |
| **RTAB-Map on Nano**      | RTAB-Map is designed for RGB-D or stereo cameras. With a single monocular USB camera, it falls back to monocular VO, which has **scale ambiguity** (it doesn't know if it moved 1cm or 1m). You'd need to fuse with IMU to resolve scale, adding complexity. RAM usage: 1-3 GB for the map database. On a 4GB shared-memory system, this is suicidal. |
| **You Don't Need a Map**  | SLAM answers: "Where am I in a persistent map?" Your drone needs to answer: "Where is the flower relative to me RIGHT NOW?" These are fundamentally different questions. You're building a library to look up a word when you just need to read the sign in front of you. |
| **Computational Overhead** | Even if SLAM ran perfectly, you STILL need YOLO for flower detection. SLAM + YOLO on a Jetson Nano = guaranteed <5 FPS combined, with RAM thrashing. |
| **Failure Modes**          | SLAM fails catastrophically in: repetitive textures (rows of palm trees = aliasing), sudden illumination changes (moving under canopy), fast rotation (motion blur). All three are **guaranteed** in your operating environment. |

**Verdict:** SLAM is a solution looking for a problem here. Your drone operates in a **reactive servoing loop**, not a **mapping and planning loop**. The compute cost is unjustifiable on this hardware for this mission profile.

---

## 3. FEASIBILITY MATRIX — IDEAS vs. REALITY

| Criteria                        | Idea A: ESP32 DIY Flow | Idea B: Single Cam Dual-Use | Idea C: Full V-SLAM | **Recommended** |
|---------------------------------|:----------------------:|:---------------------------:|:-------------------:|:------------------:|
| Dev Time                        | 3-6 months             | 1-2 months                  | 2-4 months          | **1-2 weeks**      |
| Jetson Nano GPU Load            | 0% (offloaded)         | 80-100% ⚠️                 | 60-90% ⚠️          | **40-60%** ✅      |
| Jetson Nano RAM Usage           | ~0 MB                  | 2.0-2.4 GB ⚠️              | 2.5-3.5 GB ❌      | **~1.0-1.5 GB** ✅ |
| Position Hold Reliability       | Low (uncalibrated)     | Very Low (wrong axis)       | Medium (fragile)    | **High** ✅        |
| Detection FPS                   | N/A                    | <10 FPS ⚠️                 | <5 FPS ❌           | **15-25 FPS** ✅   |
| Hardware Cost (additional)      | ~$15 + 200hrs labor    | $0                          | $0                  | **~$25-30** ✅     |
| Failure Graceful?               | No                     | No (dual failure)           | No (tracking loss)  | **Yes** ✅         |
| ArduPilot Native Support        | Custom firmware needed  | N/A                        | N/A                 | **Native** ✅      |
| Industrial Deployability        | ❌ Prototype only       | ❌ Unsafe                   | ❌ Research grade    | **✅ Field-ready** |

---

## 4. RECOMMENDED ARCHITECTURE — "The Pragmatic Stack"

### 4.1 Core Principle: Separation of Concerns

```
╔═══════════════════════════════════════════════════════════════════════╗
║                    ARCHITECTURAL PRINCIPLE                           ║
║                                                                     ║
║   POSITION HOLD  →  Handled by Pixhawk + Optical Flow (hardware)   ║
║   TARGET FINDING →  Handled by Jetson Nano + YOLO (software)       ║
║   APPROACH/AIM   →  Handled by Jetson Nano + Visual Servo (PID)    ║
║   SPRAY TRIGGER  →  Handled by Jetson Nano + GPIO/Relay            ║
║                                                                     ║
║   Each subsystem can fail independently without catastrophic loss.  ║
╚═══════════════════════════════════════════════════════════════════════╝
```

### 4.2 Hardware Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DRONE FRAME                                  │
│                                                                     │
│  ┌─────────────┐    ┌──────────────────────────────────────────┐   │
│  │   MATEK     │    │          JETSON NANO 4GB (B01)           │   │
│  │  3901-L0X   │    │                                          │   │
│  │             │    │  ┌──────────────┐  ┌─────────────────┐   │   │
│  │ [PMW3901    │    │  │ YOLOv8-nano  │  │ Visual Servo    │   │   │
│  │  Opt. Flow] │    │  │ (TensorRT    │  │ Controller      │   │   │
│  │ [VL53L1X    │    │  │  FP16)       │  │ (PID on pixel   │   │   │
│  │  ToF Range] │    │  │              │  │  error)         │   │   │
│  │             │    │  │ ~20 FPS      │  │                 │   │   │
│  │  Downward ↓ │    │  │ GPU: ~50%    │  │ CPU: ~5%        │   │   │
│  └──────┬──────┘    │  └──────┬───────┘  └────────┬────────┘   │   │
│         │            │         │                    │            │   │
│         │ I2C/SPI    │         │ BBox Center        │ Vel Cmd   │   │
│         │            │         ▼                    ▼            │   │
│         │            │  ┌──────────────────────────────────┐    │   │
│         │            │  │      ROS 2 / mavros / dronekit   │    │   │
│         │            │  │      (MAVLink over UART/USB)     │    │   │
│         │            │  └──────────────┬───────────────────┘    │   │
│         │            │                 │                         │   │
│         │            └─────────────────┼─────────────────────────┘   │
│         │                              │                             │
│         │           UART/Serial        │  MAVLink SET_POSITION_      │
│         │           (115200 baud)      │  TARGET_LOCAL_NED /         │
│         │                              │  MANUAL_CONTROL /           │
│         │                              │  RC_CHANNELS_OVERRIDE       │
│         ▼                              ▼                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    PIXHAWK (ArduPilot)                       │   │
│  │                                                              │   │
│  │  Flight Mode: GUIDED or LOITER (with Optical Flow enabled)  │   │
│  │                                                              │   │
│  │  Inputs:                                                     │   │
│  │    - Optical Flow (I2C/SPI from Matek) → Horizontal Vel Est │   │
│  │    - Rangefinder (from Matek VL53L1X)  → Altitude Est       │   │
│  │    - Barometer + IMU (internal)        → Attitude/Alt       │   │
│  │    - MAVLink Velocity Commands         → From Jetson        │   │
│  │                                                              │   │
│  │  Outputs:                                                    │   │
│  │    - Motor PWM (4x ESC)                                     │   │
│  │    - Relay/AUX PWM → Sprayer Trigger                        │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────┐         ┌────────────────┐                       │
│  │ Jete FHD     │  USB    │   SPRAYER       │                       │
│  │ 1080p Webcam │────────►│   MECHANISM     │                       │
│  │ (Front ↑→)   │  to     │                 │                       │
│  │              │  Jetson  │ Relay on Jetson │                       │
│  │ 640x480@30   │         │ GPIO or Pixhawk │                       │
│  └──────────────┘         │ AUX Channel     │                       │
│                           └────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Software Architecture — Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   JETSON NANO SOFTWARE STACK                    │
│                                                                 │
│   ┌─────────────┐                                              │
│   │ USB Camera  │  (v4l2 / GStreamer pipeline)                 │
│   │ 640x480@30  │  nvvidconv → GPU-accelerated resize          │
│   └──────┬──────┘                                              │
│          │ Frame (640x480 BGR)                                  │
│          ▼                                                      │
│   ┌──────────────────────┐                                     │
│   │ YOLO Detection Node  │  (TensorRT FP16, ~20 FPS)          │
│   │                      │                                     │
│   │ Input:  640x480 img  │                                     │
│   │ Output: [class_id,   │                                     │
│   │   confidence,        │                                     │
│   │   bbox(x,y,w,h)]    │                                     │
│   │                      │                                     │
│   │ Filter: class ==     │                                     │
│   │   "flower" AND       │                                     │
│   │   conf > 0.65        │                                     │
│   └──────┬───────────────┘                                     │
│          │ Detection Result (bbox center_x, center_y, area)    │
│          ▼                                                      │
│   ┌──────────────────────┐       ┌─────────────────────┐      │
│   │ Visual Servo Node    │       │  State Machine Node  │      │
│   │                      │◄─────►│                      │      │
│   │ Image Center:        │       │  States:             │      │
│   │   cx=320, cy=240     │       │   SEARCH  → rotate   │      │
│   │                      │       │   DETECT  → center   │      │
│   │ Error:               │       │   APPROACH→ forward  │      │
│   │   ex = cx - bbox_cx  │       │   ALIGN   → fine adj │      │
│   │   ey = cy - bbox_cy  │       │   SPRAY   → trigger  │      │
│   │   ez = target_area   │       │   RETREAT → back off │      │
│   │        - bbox_area   │       │                      │      │
│   │                      │       │ Timeout & safety     │      │
│   │ PID Controllers:     │       │ watchdog per state   │      │
│   │   pid_yaw(ex)→ωz    │       │                      │      │
│   │   pid_alt(ey)→vz    │       └──────────┬──────────┘      │
│   │   pid_fwd(ez)→vx    │                  │                  │
│   │                      │                  │                  │
│   └──────┬───────────────┘                  │                  │
│          │ Velocity Commands (vx, vy, vz, ωz)                  │
│          ▼                                                      │
│   ┌──────────────────────────────────────────────────────┐     │
│   │ MAVLink Interface (mavros / pymavlink / dronekit)    │     │
│   │                                                      │     │
│   │ Sends:                                               │     │
│   │   SET_POSITION_TARGET_LOCAL_NED                      │     │
│   │     type_mask: velocity only                         │     │
│   │     vx, vy, vz (m/s, body frame)                    │     │
│   │     yaw_rate (rad/s)                                 │     │
│   │                                                      │     │
│   │ OR: RC_CHANNELS_OVERRIDE (simpler, less elegant)     │     │
│   │     ch1(roll), ch2(pitch), ch3(throttle), ch4(yaw)   │     │
│   │                                                      │     │
│   │ Sprayer: MAV_CMD_DO_SET_RELAY or Jetson GPIO direct  │     │
│   └──────────────────────────────────────────────────────┘     │
│                                                                 │
│   Resource Budget:                                              │
│     GPU: ~50-60% (YOLO only)                                   │
│     CPU: ~30-40% (ROS + PID + MAVLink + camera driver)         │
│     RAM: ~2.5-3.0 GB total (OS 1.2 + ROS 0.3 + YOLO 0.5      │
│           + buffers 0.3 + headroom 0.2)                        │
│     Latency: Camera→Detection→Command ≈ 50-80ms               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. VISUAL SERVOING STRATEGY — "Precision Spraying Without SLAM"

### 5.1 Why Visual Servoing is the Correct Approach

Visual servoing (specifically **Image-Based Visual Servoing — IBVS**) answers the question: *"How do I move my camera so the target looks the way I want it to in the image?"*

You do NOT need to know:
- Where you are in the world (no GPS needed)
- What the 3D structure of the scene is (no SLAM needed)
- The exact distance to the target (estimated from bbox area)

You DO need to know:
- Where the target is in the image (YOLO gives this)
- Where you want it to be in the image (center of frame = aimed at target)
- How big it should look (bbox area = proxy for distance)

### 5.2 The Error Signals

```
    Image Frame (640 x 480)
    ┌─────────────────────────────────┐
    │                                 │
    │         Target: (320,240)       │
    │              ╋ ←── Image Center │
    │             ╱                   │
    │   error_x ╱   error_y          │
    │          ╱   │                  │
    │    ┌────╱────┤                  │
    │    │ ●──────►│ (bbox_cx,       │
    │    │ Flower  │  bbox_cy)       │
    │    │ BBox    │                  │
    │    └─────────┘                  │
    │                                 │
    │    error_z = TARGET_AREA -      │
    │              bbox_area          │
    │    (positive = too far,         │
    │     negative = too close)       │
    └─────────────────────────────────┘

    Mapping to Drone Commands:
    ─────────────────────────────────────────────
    error_x (horizontal pixel offset)
        → Yaw rate command (ωz)
        → "Turn left/right to center the flower"

    error_y (vertical pixel offset)
        → Altitude velocity (vz)
        → "Go up/down to center the flower"
        NOTE: Depends on camera tilt angle.
        If camera is angled down, ey maps
        partially to forward velocity too.

    error_z (bbox area difference)
        → Forward velocity (vx)
        → "Move closer/farther from the flower"
        TARGET_AREA ≈ area when flower fills
        ~30-40% of frame = good spray distance
    ─────────────────────────────────────────────
```

### 5.3 PID Controller Design

```python
# Pseudo-code for the Visual Servo Controller

# === TUNING PARAMETERS ===
# Start conservative. Tune in HIL test.

# Yaw PID (horizontal centering)
PID_YAW = PID(Kp=0.002, Ki=0.0001, Kd=0.0005)
#   Input:  error_x in pixels (-320 to +320)
#   Output: yaw_rate in rad/s (clamped to ±0.5 rad/s)

# Altitude PID (vertical centering)
PID_ALT = PID(Kp=0.003, Ki=0.0001, Kd=0.0008)
#   Input:  error_y in pixels (-240 to +240)
#   Output: vz in m/s (clamped to ±0.3 m/s)

# Forward PID (approach/distance control)
PID_FWD = PID(Kp=0.00001, Ki=0.000001, Kd=0.000005)
#   Input:  error_z = TARGET_AREA - bbox_area (in pixels²)
#   Output: vx in m/s (clamped to ±0.3 m/s)
#   Note: Much smaller gains — approach must be SLOW

# === SAFETY CLAMPS ===
MAX_YAW_RATE   = 0.5   # rad/s — prevent wild spinning
MAX_VZ         = 0.3   # m/s  — gentle altitude changes
MAX_VX         = 0.3   # m/s  — slow approach
MAX_VY         = 0.0   # m/s  — no lateral (front cam can't see lateral)
SPRAY_DISTANCE = 15000 # bbox area in pixels² (tune experimentally)
SPRAY_TOLERANCE = 50   # pixels — center error to allow spray
```

### 5.4 State Machine for Spray Mission

```
    ┌─────────┐
    │  IDLE   │  (Armed, waiting for mission start)
    └────┬────┘
         │ Mission command received
         ▼
    ┌─────────┐
    │ SEARCH  │  Rotate slowly (yaw) to scan for flowers
    │         │  Timeout: 30s → return to IDLE
    └────┬────┘
         │ YOLO detection: flower found (conf > 0.65)
         ▼
    ┌─────────┐
    │ ACQUIRE │  Lock onto highest-confidence detection
    │         │  Begin yaw + alt correction (coarse)
    │         │  Timeout: 10s → back to SEARCH
    └────┬────┘
         │ |error_x| < 80px AND |error_y| < 60px
         ▼
    ┌──────────┐
    │ APPROACH │  Activate forward PID (reduce error_z)
    │          │  Continue yaw + alt correction (fine)
    │          │  Timeout: 15s → RETREAT
    └────┬─────┘
         │ bbox_area > SPRAY_DISTANCE AND
         │ |error_x| < SPRAY_TOLERANCE AND
         │ |error_y| < SPRAY_TOLERANCE
         ▼
    ┌─────────┐
    │  SPRAY  │  HOLD position (zero all velocities)
    │         │  Trigger sprayer relay (500ms pulse)
    │         │  Log: timestamp, bbox, confidence
    │         │  Duration: 1-2 seconds
    └────┬────┘
         │ Spray complete
         ▼
    ┌──────────┐
    │ RETREAT  │  Command vx = -0.3 m/s for 2 seconds
    │          │  (Back away from sprayed flower)
    └────┬─────┘
         │ Retreat complete
         ▼
    ┌─────────┐
    │ SEARCH  │  (Look for next flower)
    └─────────┘

    GLOBAL SAFETY:
    ─────────────────────────────────────────
    - ANY state: if no detection for 3s → SEARCH
    - ANY state: if MAVLink heartbeat lost → HOVER (Pixhawk failsafe)
    - ANY state: if battery < 20% → RTL / LAND
    - ANY state: if rangefinder < 0.3m → CLIMB
    - APPROACH: if bbox_area > MAX_SAFE_AREA → RETREAT (too close!)
```

---

## 6. HARDWARE-IN-THE-LOOP (HIL) TEST PLAN

### 6.1 Test Objective

Validate the **full software pipeline** from camera detection to sprayer trigger, with the drone constrained (not flying), using a yellow ball as the target.

### 6.2 Physical Setup

```
    TEST RIG (Top View)
    ═══════════════════════════════════════════

                    Yellow Ball on Stick
                    (held by tester / on
                     a movable arm)
                         🟡
                         │
                    0.5–2.0 m
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                     │
    │    ┌──────────┐    │                     │
    │    │ Jete Cam │◄───┘                     │
    │    │ (front)  │     Drone on test stand  │
    │    └──────────┘     (props ON or OFF -   │
    │                      see phases below)   │
    │         DRONE                            │
    │    ┌──────────────┐                      │
    │    │   Pixhawk    │                      │
    │    │   Jetson     │                      │
    │    │   Battery    │                      │
    │    │   Sprayer    │  ← Spray indicator   │
    │    └──────────────┘    (LED or buzzer    │
    │                         instead of       │
    │                         actual spray)    │
    └──────────────────────────────────────────┘

    Test Stand Options:
    ──────────────────
    A) Zip-tied to a heavy wooden frame (safest)
    B) Suspended from ceiling with bungee cords
       (allows slight movement for response test)
    C) Hand-held (DANGEROUS — only for quick checks,
       PROPS MUST BE OFF)
```

### 6.3 HIL Test Architecture — What Runs Where

```
    ┌─────────────────────────────────────────────────────────┐
    │                   HIL TEST MODE                         │
    │                                                         │
    │  PIXHAWK: Armed in GUIDED mode (or LOITER)             │
    │           Props: OFF for Phase 1-3, ON for Phase 4     │
    │           Optical Flow: Connected but not critical     │
    │           (drone is stationary)                         │
    │                                                         │
    │  JETSON:  Full software stack running                   │
    │           Camera → YOLO → Visual Servo → MAVLink       │
    │                                                         │
    │  OVERRIDE: Visual servo outputs are LOGGED but          │
    │            velocity commands can be SCALED DOWN          │
    │            (multiply all outputs by 0.0 for Phase 1,   │
    │             0.3 for Phase 2, 1.0 for Phase 3+)         │
    │                                                         │
    │  MONITOR: SSH into Jetson, run rqt_image_view or       │
    │           custom OpenCV debug window showing:           │
    │           - Camera feed with YOLO bounding boxes       │
    │           - Crosshair at image center                  │
    │           - Error vectors (ex, ey, ez) as overlay      │
    │           - Current state machine state                │
    │           - PID outputs (vx, vy, vz, ωz)              │
    │           - Sprayer status (ARMED/TRIGGERED)           │
    └─────────────────────────────────────────────────────────┘
```

### 6.4 Test Phases

#### **Phase 1: Detection Validation (Props OFF, Motors DISARMED)**

| Test # | Action | Expected Result | Pass Criteria |
|--------|--------|----------------|---------------|
| 1.1 | Place yellow ball at 1.5m, centered | YOLO detects ball, bbox drawn on debug view | Detection confidence > 0.7 |
| 1.2 | Move ball left/right | `error_x` changes sign correctly, PID yaw output direction correct | Sign matches: ball-left → positive yaw cmd |
| 1.3 | Move ball up/down | `error_y` changes sign correctly, PID alt output direction correct | Sign matches: ball-up → positive vz cmd |
| 1.4 | Move ball closer/farther | `error_z` changes with bbox area, PID fwd output correct | Closer → negative vx (retreat), farther → positive vx |
| 1.5 | Remove ball entirely | State machine transitions from ACQUIRE → SEARCH after 3s timeout | Transition within 3±0.5s |
| 1.6 | Occlude ball partially | Detection maintained or gracefully lost | No false positives on other objects |
| 1.7 | Measure detection latency | Measure time from ball movement to error update | Camera-to-output latency < 100ms |

#### **Phase 2: MAVLink Command Validation (Props OFF, Motors DISARMED)**

| Test # | Action | Expected Result | Pass Criteria |
|--------|--------|----------------|---------------|
| 2.1 | Ball centered → Spray state | `SET_POSITION_TARGET_LOCAL_NED` received by Pixhawk via MAVLink | Confirmed in `mavros` topic echo or MAVLink inspector |
| 2.2 | Ball centered + close enough | Sprayer GPIO triggers (LED/buzzer indicator) | GPIO pin goes HIGH for 500ms ±50ms |
| 2.3 | Move ball after spray | State transitions to RETREAT then SEARCH | Correct state sequence logged |
| 2.4 | Continuous tracking | Move ball slowly in a circle | Commands follow ball smoothly, no oscillation > ±20% |

#### **Phase 3: Motor Response Test (Props ON, SECURED TO TEST STAND)**

> ⚠️ **DANGER: Props spinning. Wear safety glasses. Keep hands clear. Use a remote kill switch.**

| Test # | Action | Expected Result | Pass Criteria |
|--------|--------|----------------|---------------|
| 3.1 | Drone in GUIDED, hovering on stand | Stable motor output at hover throttle | Motor sounds stable, no oscillation |
| 3.2 | Move ball left | Drone attempts yaw left (audible motor diff) | Correct motor pair speeds up |
| 3.3 | Move ball up | Drone attempts to climb (all motors up) | Throttle increases measurably |
| 3.4 | Move ball closer | Drone attempts forward pitch | Front motors slow, rear speed up |
| 3.5 | Remove ball | All velocity commands zero, drone holds position | Motors return to symmetric hover |

#### **Phase 4: Tethered Flight Test (Props ON, BUNGEE/TETHER)**

Only after Phase 1-3 pass. Drone on 1m tether to heavy anchor.

| Test # | Action | Expected Result | Pass Criteria |
|--------|--------|----------------|---------------|
| 4.1 | Drone lifts off on tether, ball presented | Drone orients toward ball | Yaw follows ball |
| 4.2 | Ball at spray distance | Full spray cycle triggers | Sprayer activates, drone retreats after |

---

## 7. STEP-BY-STEP IMPLEMENTATION PLAN (2 Weeks)

### Week 1: Foundation & Detection

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| **Day 1** | **Matek 3901-L0X Integration** | Optical flow + rangefinder connected to Pixhawk via I2C. ArduPilot parameters configured: `FLOW_TYPE=5`, `RNGFND1_TYPE=12`, `RNGFND1_ADDR=41`. | Pixhawk `OPTICAL_FLOW_RAD` message visible in Mission Planner. Rangefinder alt visible. |
| **Day 2** | **Position Hold Test (No Jetson)** | Fly in LOITER mode indoors/under canopy. Optical flow provides position hold. | Drone holds position ±30cm for 30 seconds with no GPS. |
| **Day 3** | **Jetson-Pixhawk MAVLink Link** | `mavros` (ROS) or `pymavlink` running on Jetson, connected to Pixhawk via UART (`/dev/ttyTHS1` at 921600 baud). Heartbeat confirmed. | `rostopic echo /mavros/state` shows `connected: True`. Send `SET_MODE` command successfully. |
| **Day 4** | **Camera Pipeline** | GStreamer pipeline: `v4l2src → nvvidconv → appsink` at 640x480@30fps. ROS node publishing `sensor_msgs/Image`. Verified FPS with `rostopic hz`. | Sustained 30 FPS with < 50ms latency. No frame drops. |
| **Day 5** | **YOLO Deployment** | YOLOv8-nano trained on flower/yellow-ball dataset. Exported to TensorRT FP16 engine on Jetson. Detection node subscribes to camera topic, publishes detections. | ≥15 FPS detection on 640x480. Correct bounding boxes on yellow ball at 0.5–2.0m. GPU usage < 60% (`tegrastats`). |
| **Day 6** | **Visual Servo Node (Draft)** | PID controller node: subscribes to detections, computes velocity commands, publishes to `mavros/setpoint_velocity/cmd_vel`. Error visualization overlay. | Commands publish at ≥10 Hz. Direction correctness verified visually (overlay arrows). |
| **Day 7** | **State Machine Node (Draft)** | Finite state machine: IDLE → SEARCH → ACQUIRE → APPROACH → SPRAY → RETREAT. Transitions based on detection presence, error thresholds, and timeouts. | State transitions log correctly. Timeout recovery works. |

### Week 2: Integration & Testing

| Day | Task | Deliverable | Acceptance Criteria |
|-----|------|-------------|---------------------|
| **Day 8** | **Sprayer Integration** | GPIO pin on Jetson (or Pixhawk AUX channel) drives relay. ROS service `/trigger_spray` activates for configurable duration. | Relay clicks on command. Duration accurate ±50ms. |
| **Day 9** | **HIL Phase 1** (Detection Tests) | All tests from Phase 1 table above. | All 7 tests pass. |
| **Day 10** | **HIL Phase 2** (MAVLink Command Tests) | All tests from Phase 2 table above. PID tuning begins. | All 4 tests pass. Commands smooth. |
| **Day 11** | **PID Tuning Session** | Iterative tuning of Kp, Ki, Kd for yaw, alt, and forward PIDs. Use ball-on-stick at various positions. Record step response. | Settling time < 3s for 200px step. Overshoot < 20%. No steady-state oscillation. |
| **Day 12** | **HIL Phase 3** (Motor Response Tests) | Props on, drone secured. Verify motor response matches commands. **Safety gear mandatory.** | All 5 tests pass. Motor response matches expected direction. |
| **Day 13** | **System Integration & Stress Test** | Full pipeline running for 30 minutes continuously. Monitor RAM, CPU, GPU, temperature. Test edge cases: fast ball movement, occlusion, multiple objects. | No crashes, no memory leaks, no thermal throttle. FPS stays > 12 sustained. Temp < 80°C. |
| **Day 14** | **HIL Phase 4** (Tethered Flight) + Documentation | Tethered flight test. Full system documentation. Parameter backup. | Drone tracks ball, triggers spray, retreats. Video recorded. Documentation committed to repo. |

---

## 8. CRITICAL CONFIGURATION REFERENCE

### 8.1 ArduPilot Parameters for Optical Flow + Rangefinder

```
# === Optical Flow (Matek 3901-L0X) ===
FLOW_TYPE       = 5       # PMW3901 via I2C (or MSP, check Matek docs)
FLOW_ADDR       = 0x2A    # Default I2C address for Matek 3901
FLOW_ORIENT_YAW = 0       # 0 if connector faces forward. Adjust if rotated.
FLOW_POS_X      = 0.0     # Offset from CoG in meters (tune later)
FLOW_POS_Y      = 0.0
FLOW_POS_Z      = 0.0

# === Rangefinder (VL53L1X on Matek 3901-L0X) ===
RNGFND1_TYPE    = 12      # VL53L1X
RNGFND1_ADDR    = 41      # 0x29 in decimal
RNGFND1_MIN_CM  = 5
RNGFND1_MAX_CM  = 400     # 4m max for VL53L1X
RNGFND1_ORIENT  = 25      # Downward

# === EKF Configuration for Optical Flow ===
EK2_ENABLE      = 0       # Disable EKF2
EK3_ENABLE      = 1       # Use EKF3
EK3_SRC1_POSXY  = 0       # No GPS for position (flow provides velocity)
EK3_SRC1_VELXY  = 5       # Optical Flow for horizontal velocity
EK3_SRC1_POSZ   = 2       # Rangefinder for altitude (primary)
EK3_SRC1_VELZ   = 0       # None (baro + rangefinder fusion)
EK3_SRC1_YAW    = 1       # Compass (if available), or 8 for GSF

# === Flight Modes ===
FLTMODE1        = 5       # LOITER (uses optical flow for position hold)
FLTMODE4        = 4       # GUIDED (for Jetson commands)
```

### 8.2 Jetson Nano Optimization Checklist

```bash
# === Run at MAX Performance ===
sudo nvpmodel -m 0                    # MAXN mode (10W, all 4 cores)
sudo jetson_clocks                     # Max out CPU/GPU/EMC clocks

# === Disable GUI (save ~500MB RAM + GPU bandwidth) ===
sudo systemctl set-default multi-user.target
# (Reboot. Access Jetson via SSH only.)

# === GStreamer Camera Pipeline (GPU-accelerated) ===
# In your ROS node or OpenCV script:
GSTREAMER_PIPELINE = (
    "v4l2src device=/dev/video0 ! "
    "video/x-raw, width=640, height=480, framerate=30/1 ! "
    "videoconvert ! "
    "video/x-raw, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink drop=1"
)

# === Monitor Resources ===
tegrastats                             # GPU/CPU/RAM/Temp in real-time
sudo jtop                             # More readable (pip install jetson-stats)
```

---

## 9. RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Optical flow fails on low-texture ground (concrete, water) | Medium | High (position drift) | Test on actual plantation ground. Add texture (tape) to test surfaces. Consider downward LED illumination. |
| YOLO false positives (yellow objects that aren't flowers) | Medium | Medium (wasted spray) | Collect negative examples in training data. Add size/aspect ratio filters post-detection. |
| USB camera disconnects mid-flight (vibration, loose connector) | Medium | Critical (loss of targeting) | Secure USB cable with zip-ties and strain relief. Add watchdog: if no camera frames for 1s → HOVER. |
| Jetson Nano thermal throttle in tropical heat (35°C+ ambient) | High | High (FPS drop) | Add heatsink + 5V fan. Monitor temp in-loop. Throttle mission tempo if temp > 75°C. |
| PID oscillation during approach (windy conditions) | Medium | Medium (missed spray) | Start with very conservative gains. Add derivative filter. Test outdoors incrementally. |
| Sprayer mist interferes with camera (lens fog/droplets) | Medium | High (detection failure) | Mount camera ABOVE sprayer nozzle. Add small lens hood. Consider hydrophobic lens coating. |

---

## 10. FINAL RECOMMENDATION

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   BUY the Matek 3901-L0X ($25).                              ║
║   Let Pixhawk handle position hold (it's GOOD at this).      ║
║   Let Jetson Nano handle vision + servoing (it's GOOD at     ║
║   this ONE thing).                                             ║
║   Don't make either do the other's job.                        ║
║                                                                ║
║   Your drone doesn't need to know where it is.                ║
║   It needs to know where the FLOWER is.                        ║
║   Visual servoing gives you that directly.                     ║
║                                                                ║
║   Ship a working spray cycle in 2 weeks, not a research       ║
║   paper in 6 months.                                           ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

*Document Version: 1.0 | Review Date: 2026-02-09 | Classification: Internal Engineering*
